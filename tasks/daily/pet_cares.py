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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pets = []
        self.items = []
        self.selected_pet = None

    def main(self):
        self.goto('https://www.neopets.com/home')
        self.scan_all_pets()
        self.feed_all_pets()
        self.unselect()

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
            self.pets.append(Neopet(
                name = name,
                health=int(node.get_attribute('data-health')),
                max_health=int(node.get_attribute('data-maxhealth')),
                hunger=int(HUNGER_LEVEL[node.get_attribute('data-hunger')]),
                level=int(node.get_attribute('data-level')),
                species=node.get_attribute('data-species'),
                color=node.get_attribute('data-color'),
                mood=node.get_attribute('data-mood'),
                is_active=node.get_attribute('data-active') == 'true',
                _locator=node,
            ))

    def unselect(self):
        if not self.selected_pet:
            return
        self.selected_pet = None
        self.device.click((10, 200)) # just click somewhere to unselect

    def select_pet(self, index):
        if index < 0 or index >= len(self.pets):
            raise TaskError(f'Invalid pet index: {index}')
        self.selected_pet = self.pets[index]
        logger.info(f'Selected pet: {self.selected_pet.name}')
        self.selected_pet.locator.click()

    def feed_all_pets(self):
        for i, pet in enumerate(self.pets):
            self.unselect()
            self.select_pet(i)
            self.device.wait_for_element('#petCareLinkFeed').click()
            while pet.hunger < HUNGER_LEVEL[self.config.PetCares_MaxFeedLevel]:
                logger.info(f'Feeding pet {pet.name} with hunger {HUNGER_VALUE[pet.hunger]}')
                ret = self.feed_pet()
                if ret < 0:
                    logger.warning('Stopped feeding due to no usable items.')
                    return
                pet.hunger = ret
                logger.info(f'Neopet {pet.name} hunger after feeding: {HUNGER_VALUE[pet.hunger]}')
                back_node = self.page.locator('#petCareResultBack')
                self.device.wait(1)  # prevent rapid clicking
                if back_node and back_node.count():
                    back_node.click()
                else:
                    logger.warning("No back button found after feeding, proceeding to next pet.")
                    break

    def feed_pet(self) -> int:
        items = [i for i in self.scan_usable_items() if i.is_edible(self.config)]
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
        while self.is_node_loading(result_node):
            self.device.sleep(0.3)
            result_node = self.device.wait_for_element('#petCareResult')
        logger.info(f'Result after using {item.name}: {result_node.inner_text()}')
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
            item = NeoItem(
                name=name,
                id=node.get_attribute('id'),
                image=node.get_attribute('data-image'),
                description=node.get_attribute('data-itemdesc'),
                rarity=node.get_attribute('data-rarity'),
                restock_price=node.get_attribute('data-itemvalue'),
                market_price=0,
                item_type=node.get_attribute('data-itemtype'),
                _locator=node,
            )
            item.node = node
            self.items.append(item)
        jn.batch_search(item_names)
        for item in self.items:
            item.update_jn()
        return self.items


if __name__ == '__main__':
    self = PetCaresUI()
