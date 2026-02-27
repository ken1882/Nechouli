import re
from PIL import Image
from nch import Nechouli
from module.logger import logger
from tasks.base import base_page, base_flash
from module.exception import TaskError
from module.db.models import neopet, neoitem
from module.db.data_map import *
from module.db import data_manager as dm
from module.base.utils import (
    ensure_time,
    str2int,
    check_connection,
    kill_by_port,
    get_all_instance_addresses
)
import module.jelly_neo as jn
from tasks.daily.pet_cares import PetCaresUI
from tasks.daily.faerie_crossword import FaerieCrosswordUI
from tasks.daily.trudys_surprise import TrudysSurpriseUI
from tasks.daily.grave_danger import GraveDangerUI
from tasks.utility.restocking import RestockingUI
from tasks.daily.daily_quest import DailyQuestUI
from tasks.daily.scratchcard import ScratchcardUI
from tasks.utility import quick_stock
from tasks.utility import safety_deposit_box
from tasks.daily import pet_training
from tasks.daily import battledome
from threading import Thread

BaseFlash = base_flash.BaseFlash
BasePageUI = base_page.BasePageUI
Neopet = neopet.Neopet
NeoItem = neoitem.NeoItem
QuickStockUI = quick_stock.QuickStockUI
PetTrainingUI = pet_training.PetTrainingUI
SafetyDepositBoxUI = safety_deposit_box.SafetyDepositBoxUI
BattleDomeUI = battledome.BattleDomeUI

def reload_modules():
    global BaseFlash, BasePageUI, Neopet, NeoItem, PetTrainingUI, SafetyDepositBoxUI
    global QuickStockUI, BattleDomeUI
    from importlib import reload
    reload(base_page)
    reload(base_flash)
    reload(neopet)
    reload(neoitem)
    reload(pet_training)
    reload(safety_deposit_box)
    reload(quick_stock)
    reload(battledome)
    BaseFlash = base_flash.BaseFlash
    BasePageUI = base_page.BasePageUI
    Neopet = neopet.Neopet
    NeoItem = neoitem.NeoItem
    PetTrainingUI = pet_training.PetTrainingUI
    SafetyDepositBoxUI = safety_deposit_box.SafetyDepositBoxUI
    QuickStockUI = quick_stock.QuickStockUI
    BattleDomeUI = battledome.BattleDomeUI

def sc():
    Image.fromarray(device.screenshot()).save('test.png')

def chconf(k, v):
    profiles = get_all_instance_addresses()
    for p in profiles:
        alas = Nechouli(p)
        alas.config.cross_set(k, v)

class TestUI(BaseFlash, BasePageUI):
    pass


alas = Nechouli('nechouli2')
config, device = alas.config, alas.device
self = PetTrainingUI(config, device)

device.start_browser()
device.disable_stuck_detection()
device.screenshot_interval_set(0.1)
self.config.bind('PetTraining')


ACADEMY = {
    'pirate': {
        'url': 'https://www.neopets.com/pirates/academy.phtml?type=status',
        'max_level': 40,
    },
    'island': {
        'url': 'https://www.neopets.com/island/training.phtml?type=status',
        'max_level': 250,
    },
    'ninja': {
        'url': 'https://www.neopets.com/island/fight_training.phtml?type=status',
        'max_level': 9999,
    }
}

ATTR_CONF_TABLE = {
    'lv': 'level',
    'str': 'strength',
    'def': 'defense',
    'mov': 'movement',
    'hp': 'max_health',
}

ATTR_COURSE_TABLE = {
    'lv': 'Level',
    'str': 'Strength',
    'def': 'Defence',
    'mov': 'Agility',
    'hp': 'Endurance',
}

configs = self.config.PetTraining_Config.splitlines()
aca_pets = {
    'pirate': [],
    'island': [],
    'ninja': []
}
self.complete_times = []

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


self.config.stored.PendingTrainingFee.clear()
trained = []

academy = 'island'
pets = aca_pets[academy]

self.goto(ACADEMY[academy]['url'])
completed = self.page.locator('input[type=submit][value="Complete Course!"]')
while completed.count():
    logger.info("Completing course for %s academy", academy)
    self.device.click(completed.first, nav=True)
    self.goto(ACADEMY[academy]['url'])
    completed = self.page.locator('input[type=submit][value="Complete Course!"]')

self.scan_pets(pets, academy=academy)
for pet in pets:
    self.train_pet(pet, academy)

fees = self.scan_fee(academy)
if fees:
    trained.append(academy)
self.config.stored.PendingTrainingFee.add(*fees)

missings = {}
if self.config.stored.PendingTrainingFee:
    missings = self.fetch_training_fee()
    for aca in trained:
        logger.info(f"Paying training fee for {aca} academy")
        self.pay_training_fee(aca)
if missings and self.config.PetTraining_BuyFeeFromPlayers:
    msg = "Buying missing items from players:\n"
    reqs = []
    for item_name, amount in missings.items():
        reqs.append((item_name, 'training', amount))
        msg += f"{item_name}: {amount}\n"
    logger.info(msg)
    self.config.stored.ShopWizardRequests.bulk_add(reqs)
    self.config.task_call('ShopWizard')

for academy, pets in aca_pets.items():
    self.complete_times += self.scan_training_time(academy)
