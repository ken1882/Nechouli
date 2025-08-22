import re
from PIL import Image
from nch import Nechouli
from module.logger import logger
from tasks.base import base_page, base_flash
from module.exception import TaskError
from module.db.models import neopet, neoitem
from module.db.data_map import *
from module.base.utils import ensure_time, str2int, check_connection, kill_by_port
import module.jelly_neo as jn
from tasks.daily.pet_cares import PetCaresUI
from tasks.daily.faerie_crossword import FaerieCrosswordUI
from tasks.daily.trudys_surprise import TrudysSurpriseUI
from tasks.daily.grave_danger import GraveDangerUI
from tasks.utility.restocking import RestockingUI
from tasks.daily.daily_quest import DailyQuestUI
from tasks.utility import quick_stock
from tasks.daily import pet_training
from tasks.utility import safety_deposit_box

BaseFlash = base_flash.BaseFlash
BasePageUI = base_page.BasePageUI
Neopet = neopet.Neopet
NeoItem = neoitem.NeoItem
QuickStockUI = quick_stock.QuickStockUI
PetTrainingUI = pet_training.PetTrainingUI
SafetyDepositBoxUI = safety_deposit_box.SafetyDepositBoxUI

def reload_modules():
    global BaseFlash, BasePageUI, Neopet, NeoItem, PetTrainingUI, SafetyDepositBoxUI
    global QuickStockUI
    from importlib import reload
    reload(base_page)
    reload(base_flash)
    reload(neopet)
    reload(neoitem)
    reload(pet_training)
    reload(safety_deposit_box)
    reload(quick_stock)
    BaseFlash = base_flash.BaseFlash
    BasePageUI = base_page.BasePageUI
    Neopet = neopet.Neopet
    NeoItem = neoitem.NeoItem
    PetTrainingUI = pet_training.PetTrainingUI
    SafetyDepositBoxUI = safety_deposit_box.SafetyDepositBoxUI
    QuickStockUI = quick_stock.QuickStockUI

def sc():
    Image.fromarray(device.screenshot()).save('test.png')

class TestUI(BaseFlash, BasePageUI):
    pass


alas = Nechouli('nechouli2')
config, device = alas.config, alas.device
self = PetTrainingUI(config, device)

device.start_browser()
device.disable_stuck_detection()
device.screenshot_interval_set(0.1)
self.goto('https://www.neopets.com/pirates/academy.phtml?type=status')

self.config.bind('PetTraining')
ACADEMY = pet_training.ACADEMY
ATTR_CONF_TABLE = pet_training.ATTR_CONF_TABLE
ATTR_COURSE_TABLE = pet_training.ATTR_COURSE_TABLE
configs = self.config.PetTraining_Config.splitlines()
self.current_pets = []
aca_pets = {
    'pirate': [],
    'island': [],
    'ninja': []
}
for conf in configs:
    pet_name, academy, target_lv, target_str, target_def, target_mov, target_hp = conf.split(':')
    if academy not in ACADEMY:
        logger.error(f'Unknown academy: {academy}')
        continue
    aca_pets[academy].append(Neopet(
        name=pet_name,
        level=int(target_lv),
        max_health=int(target_hp),
        strength=int(target_str),
        defense=int(target_def),
        movement=int(target_mov),
    ))


for academy, pets in aca_pets.items():
    if not pets:
        continue
    self.goto(ACADEMY[academy]['url'])
    completed = self.page.locator('input[type=submit][value="Complete Course!"]')
    while completed.count():
        self.device.click(completed.first, nav=True)
        self.goto(ACADEMY[academy]['url'])
    self.scan_pets(pets, academy=academy)
    trained = False
    for pet in pets:
        trained = self.train_pet(pet, academy)
    if trained:
        for item in self.scan_fee():
            self.config.stored.PendingTrainingFee.add(item)
    if not trained:
        continue
    self.fetch_training_fee()
    self.goto(ACADEMY[academy]['url'])