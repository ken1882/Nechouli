import re
from nch import Nechouli
from module.logger import logger
from tasks.base import base_page, base_flash
from module.exception import TaskError
from module.db.models import neopet, neoitem
from module.db.data_map import *
from module.base.utils import str2int
import module.jelly_neo as jn

from tasks.daily.pet_cares import PetCaresUI
from tasks.daily.faerie_crossword import FaerieCrosswordUI
from tasks.daily.trudys_surprise import TrudysSurpriseUI
from tasks.daily.grave_danger import GraveDangerUI
from tasks.utility.quick_stock import QuickStockUI
from tasks.utility.restocking import RestockingUI
from tasks.daily.daily_quest import DailyQuestUI

BaseFlash = base_flash.BaseFlash
BasePageUI = base_page.BasePageUI
NeoPet = neopet.Neopet
NeoItem = neoitem.NeoItem

def reload_modules():
    global BaseFlash, BasePageUI, NeoPet, NeoItem
    from importlib import reload
    reload(base_page)
    reload(base_flash)
    reload(neopet)
    reload(neoitem)
    BaseFlash = base_flash.BaseFlash
    BasePageUI = base_page.BasePageUI
    NeoPet = neopet.Neopet
    NeoItem = neoitem.NeoItem

class TestUI(BaseFlash, BasePageUI):
    pass


alas = Nechouli()
config, device = alas.config, alas.device
self = DailyQuestUI(config, device)


device.start_browser()
device.disable_stuck_detection()
device.screenshot_interval_set(0.1)
device.clean_redundant_pages()

i = 3
pane = self.page.locator(f'#Act{i}Pane')
btn = self.page.locator(f'#Act{i}PaneBtn')
self.device.scroll_to(loc=btn)
if i != 1:
    self.device.click(btn)
    self.device.wait(0.5)

joins = pane.locator('button[id*="VolunteerButton"]')