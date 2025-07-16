from nch import Nechouli
from module.logger import logger
from tasks.base.base_page import BasePageUI
from tasks.daily.pet_cares import PetCaresUI
from module.exception import TaskError
from module.db.models.neopet import Neopet
from module.db.models.neoitem import NeoItem
from module.db.data_map import *
from module.base.utils import str2int
import module.jelly_neo as jn

alas = Nechouli()
config, device = alas.config, alas.device
device.start_browser()
self = BasePageUI(config, device)
self = PetCaresUI(config, device)
self.run()

def unselect():
    if not self.selected_pet:
        return
    self.selected_pet = None
    self.device.click((10, 200)) # just click somewhere to unselect

def scan_all_pets():
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

def select_pet(index):
    if index < 0 or index >= len(self.pets):
        raise TaskError(f'Invalid pet index: {index}')
    self.selected_pet = self.pets[index]
    logger.info(f'Selected pet: {self.selected_pet.name}')
    self.selected_pet.locator.click()

def feed_all_pets():
    for i, pet in enumerate(self.pets):
        if pet.hunger >= HUNGER_LEVEL['full up']:
            continue
        logger.info(f'Feeding pet {pet.name} with hunger {HUNGER_VALUE[pet.hunger]}')
        self.select_pet(i)
        self.device.wait_for_element('#petCareLinkFeed').click()

def scan_usable_items():
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

def use_item(item: NeoItem):
    item.locator.click()
    self.device.wait_for_element('#petCareUseItem').click()

self.goto('https://www.neopets.com/home')
scan_all_pets()
select_pet(0)
self.device.wait_for_element('#petCareLinkFeed').click()
items = [i for i in scan_usable_items() if i.is_edible(self.config)]
items = sorted(items, key=lambda x: x.market_price)

