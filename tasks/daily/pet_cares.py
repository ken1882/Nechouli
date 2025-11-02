from playwright.sync_api import Locator
from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.exception import TaskError
from module.base.utils import str2int
from module.db.models.neopet import Neopet
from module.db.models.neoitem import NeoItem
import module.jelly_neo as jn
from module.db.data_map import *
from typing import List, Any, MutableMapping

class PetCaresUI(BasePageUI):
    selected_pet: Neopet
    pets: List[Neopet]
    items: List[NeoItem]
    _last_action_result: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pets = []
        self.items = []
        self.selected_pet = None
        self._last_action_result = ''

    def main(self):
        self.goto('https://www.neopets.com/home')
        self.scan_all_pets()
        self.feed_all_pets()
        self.unselect()
        self.play_all_pets()
        self.unselect()
        self.groom_all_pets()
        self.unselect()
        self.select_pet(0)
        self.customise_pet()
        return True

    def scan_all_pets(self):
        self.pets = []
        nodes = self.page.locator('.hp-carousel-nameplate')
        num = nodes.count()
        if not num:
            raise TaskError('No pets found')
        for node in nodes.all():
            name = node.get_attribute('data-name')
            if not name: # empty slot
                continue
            if any(pet.name == name for pet in self.pets):
                continue
            bb = node.bounding_box()
            logger.info("Visibility check: %s", bb)
            if bb['x'] + bb['width'] < 100:
                continue
            data = {
                'name': name,
                'health': int(node.get_attribute('data-health')),
                'max_health': int(node.get_attribute('data-maxhealth')),
                'hunger': int(HUNGER_LEVEL[node.get_attribute('data-hunger')]),
                'level': int(node.get_attribute('data-level')),
                'species': node.get_attribute('data-species'),
                'color': node.get_attribute('data-color'),
                'mood': node.get_attribute('data-mood'),
                'is_active': node.get_attribute('data-active') == 'true',
                '_locator': node,
            }
            self.pets.append(Neopet(**data))
            if name in self.config.stored.PetsData:
                self.config.stored.PetsData[name].update(data)
            else:
                self.config.stored.PetsData.add(Neopet(**data))
        pet_names = [p.name for p in self.pets]
        for p in self.config.stored.PetsData:
            if p.name not in pet_names:
                logger.warning(f'Pet {p.name} not found on page, removing from storage')
                self.config.stored.PetsData.remove(p)

    def unselect(self):
        if not self.selected_pet:
            return
        self.selected_pet = None
        self.device.click((10, 200)) # just click somewhere to unselect

    def select_pet(self, index):
        if index < 0 or index >= len(self.pets):
            raise TaskError(f'Invalid pet index: {index}')
        self.selected_pet = self.pets[index]
        x_cycle = []
        while True:
            bb = self.selected_pet.locator.bounding_box()
            logger.info("Visibility check: %s", bb)
            ww = self.device.eval('window.innerWidth')
            if 100 <= bb['x'] + bb['width'] and bb['x'] <= ww*0.8:
                break
            dup_x = [x for x in x_cycle if abs(x - bb['x']) < 1]
            if len(dup_x) > 2 and abs(min(dup_x) - bb['x']) < 1:
                logger.warning("Pet selection seems stuck, try to proceed.")
                break
            x_cycle.append(bb['x'])
            self.device.click('button[class="slick-next slick-arrow"]')
            self.device.wait(0.5)
        logger.info(f'Selected pet: {self.selected_pet.name}')
        self.selected_pet.locator.click()

    def feed_all_pets(self):
        for i, pet in enumerate(self.pets):
            if not self.should_feed(i):
                logger.info(f'Pet {pet.name} does not need feeding, skipping.')
                continue
            self.unselect()
            self.select_pet(i)
            self.device.wait_for_element('#petCareLinkFeed').click()
            while self.should_feed():
                logger.info(f'Feeding pet {pet.name} with hunger {HUNGER_VALUE[pet.hunger]}')
                ret = self.feed_pet()
                if ret < 0:
                    logger.warning('Stopped feeding due to no usable items.')
                    return
                if pet.hunger != ret and self.config.stored.DailyQuestFeedTimesLeft.value:
                    self.config.stored.DailyQuestFeedTimesLeft.sub()
                pet.hunger = ret
                logger.info(f'Neopet {pet.name} hunger after feeding: {HUNGER_VALUE[pet.hunger]}')
                back_node = self.page.locator('#petCareResultBack')
                self.device.wait(1)  # prevent rapid clicking
                if back_node and back_node.count():
                    back_node.click()
                else:
                    logger.warning("No back button found after feeding, proceeding to next pet.")
                    break

    def should_feed(self, index:int=None) -> bool:
        if not self.selected_pet and index is None:
            raise TaskError('No pet selected for feeding check')
        pet = self.selected_pet if index is None else self.pets[index]
        if (
            self.config.stored.DailyQuestFeedTimesLeft.value > 0
            and pet.hunger < HUNGER_LEVEL['bloated']
        ):
            return True

        return pet.hunger < HUNGER_LEVEL[self.config.PetCares_MaxFeedLevel]

    def feed_pet(self) -> int:
        items = []
        for i in self.scan_usable_items():
            if not i.is_edible(self.config) or i.market_price >= self.config.PetCares_MaxFeedValue:
                continue
            items.append(i)
        if not items:
            logger.warning(f'No usable items found for pet {self.selected_pet.name}')
            return -1
        items = sorted(items, key=lambda x: x.market_price)
        result_node = self.use_item(items[0])
        result_text = result_node.inner_text().lower()
        return max([v for k, v in HUNGER_LEVEL.items() if k in result_text], default=10)

    def use_item(self, item: NeoItem) -> Locator:
        logger.info(f'Using item: {item.name} on pet {self.selected_pet.name}')
        item.locator.click()
        self.device.wait(0.5)
        self.device.wait_for_element('#petCareUseItem').click()
        result_node = self.device.wait_for_element('#petCareResult')
        depth = 0
        while self.is_node_loading(result_node):
            self.device.sleep(0.3)
            result_node = self.device.wait_for_element('#petCareResult')
            depth += 1
            if depth > 30:
                logger.warning("Timeout waiting for item use result, proceed anyway.")
                break
        depth = 0
        result_text = result_node.inner_text()
        # chance loading text not appeared but stuck with last action result
        while result_text == self._last_action_result:
            self.device.wait(0.3)
            result_node = self.device.wait_for_element('#petCareResult')
            result_text = result_node.inner_text()
            depth += 1
            if depth > 30:
                logger.warning("Timeout waiting for new item use result, proceed anyway.")
                break
        self._last_action_result = result_text
        logger.info(f'Result after using {item.name}: {result_text}')
        return result_node

    def scan_usable_items(self):
        self.items = []
        item_cnt   = None
        # wait until loaded
        while item_cnt == None:
            item_cnt = str2int(self.device.wait_for_element('.petCare-itemcount').inner_text() or '')
        if not item_cnt:
            logger.warning("No usable items found.")
            return []
        nodes = self.page.locator('.petCare-itemgrid-item')
        depth = 0
        while nodes.count() < item_cnt:
            self.device.sleep(1)
            depth += 1
            if depth > 30:
                logger.warning("Timeout waiting for all items to load, assume loaded.")
                break
        item_names = set()
        for node in nodes.all():
            name = node.get_attribute('data-itemname')
            if not name:
                continue
            item_names.add(name)
            item = NeoItem.load_from_locator(node)
            item.node = node
            self.items.append(item)
        jn.batch_search(item_names)
        for item in self.items:
            item.update_jn()
        return self.items

    def play_all_pets(self):
        for i, pet in enumerate(self.pets):
            self.unselect()
            self.select_pet(i)
            self.play_pet()
            self.device.wait(1)

    def groom_all_pets(self):
        for i, pet in enumerate(self.pets):
            self.unselect()
            self.select_pet(i)
            self.groom_pet()
            self.device.wait(1)

    def play_pet(self) -> bool:
        self.device.wait_for_element('#petCareLinkPlay').click()
        logger.info(f'Playing with pet {self.selected_pet.name}')
        items = [i for i in self.scan_usable_items() if i.is_playable(self.config)]
        if not items:
            logger.warning(f'No toys found for pet {self.selected_pet.name}')
            return False
        items = sorted(items, key=lambda x: x.market_price)
        self.use_item(items[0])
        return True

    def groom_pet(self) -> bool:
        self.device.wait_for_element('#petCareLinkGroom').click()
        logger.info(f'Grooming pet {self.selected_pet.name}')
        items = [i for i in self.scan_usable_items() if i.is_groomable(self.config)]
        if not items:
            logger.warning(f'No grooming items found for pet {self.selected_pet.name}')
            return False
        items = sorted(items, key=lambda x: x.market_price)
        self.use_item(items[0])
        return True

    def customise_pet(self) -> bool:
        node = self.device.wait_for_element('#petCareCustomiseLink')
        self.device.click(node, nav=True)
        self.device.wait_for_element('#npcma_loader')
        self.device.wait_for_element('#npcma_loader', gone=True)
        if not self.switch_closet():
            return False
        weared_items = self.scan_wearables()
        if not weared_items:
            self.switch_closet()
        else:
            item_name = self.takeoff_item(weared_items[0])
            if not item_name:
                return False
            if not self.save_customise():
                return False
            if not self.switch_closet():
                return False
            if not self.search_item(item_name):
                return False
            self.device.sleep(3) # probably long, depends on your network and closet size
        available_items = self.scan_wearables()
        if not available_items:
            logger.warning("No available items found after customisation.")
            return False
        src = available_items[0]
        dst = self.page.locator('#npcma_customMainContent')
        self.device.drag_to(src, dst)
        return self.save_customise()

    def switch_closet(self) -> bool:
        node = self.page.locator('.npcma-switch')
        if not node.count():
            logger.warning("No closet switch found.")
            return False
        self.device.click(node)
        self.device.sleep(2) # wait for switch animation
        return True

    def scan_wearables(self) -> list[Locator]:
        nodes = self.page.locator('.npcma-pet-content')
        if not nodes.count():
            logger.warning("No wearables found.")
            return []
        return [node for node in nodes.all() if node.is_visible()]

    def takeoff_item(self, item: Locator) -> str:
        item_name = item.inner_text().strip()
        takeoff_btn = item.locator('.npcma-icon-close')
        if not takeoff_btn.count():
            logger.warning(f"Unable to take off cloth {item_name}.")
            return ''
        logger.info(f'Taking off cloth: {item_name}')
        takeoff_btn.click()
        self.device.sleep(1)
        return item_name

    def save_customise(self) -> bool:
        save_btn = self.page.locator('.npcma-icon-save-snap')
        if not save_btn.count():
            logger.warning("No save button found in customisation.")
            return False
        self.device.click(save_btn)
        popup = self.device.wait_for_element('.npcma-align_center')
        self.device.sleep(2)
        self.device.click(popup.locator('.npcma-icon-close'))
        logger.info("Customisation saved successfully.")
        return True

    def search_item(self, item_name: str) -> Locator:
        search_input = self.page.locator('.header-search').locator('input')
        if not search_input.count():
            logger.warning("Search input not found.")
            return None
        search_input.fill(item_name)
        self.device.sleep(1)
        return True

if __name__ == '__main__':
    self = PetCaresUI()
