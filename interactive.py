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
self = ScratchcardUI(config, device)

device.start_browser()
device.disable_stuck_detection()
device.screenshot_interval_set(0.1)
self.config.bind('Scratchcard')


logger.info(f"Run task {self.task_name} in background mode")
self.config.cross_set(f'{self.task_name}.Scheduler.IsRunningBackground', True)
self.on_background = True
Thread(target=self.run_background, daemon=True).start()

self.goto('https://www.neopets.com/dome/fight.phtml')
self.load_actions()

def fight():
    self.wait_for_turn()
    self.parse_status()
    w = self.determine_winner()
    if w == True:
        logger.info("Victory!")
        self.collect_rewards()
        self.device.click('#bdplayagain', nav=True)
        return True
    elif w == False:
        logger.info("Defeated!")
        return False
    else:
        pass
    if self.round > len(self.actions):
        logger.info("No more actions configured, ending battle")
        return False
    self.select_action()
    self.send_actions()
    self.wait_for_turn()

self.wait_and_start()
while not fight():
    pass

self.wait_and_start()

cards = self.page.locator('img[alt="Click here to scratch this card"]')
self.device.click(cards.first, nav=True)
canvas = self.page.locator('#container')
self.frame = ''

slots_x = [250, 310, 400]
slots_y = [100, 160, 260]
loc = self.find_flash()
for n in range(6):
    for i in range(10):
        for j in range(5):
            sx = slots_x[n % 3] + i * 10
            sy = slots_y[n // 3] + j * 10
            sp = {'x': sx, 'y': sy}
            tp = {'x': sx + 10, 'y': sy + 10}
            loc.drag_to(loc, source_position=sp, target_position=tp)
            loc.drag_to(loc, source_position=tp, target_position=sp)

self.click((350, 380))
self.page.wait_for_url(
    '**',
    timeout=self.config.Playwright_DefaultTimeout*1000,
    wait_until='domcontentloaded',
)


