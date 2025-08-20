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
from tasks.utility.quick_stock import QuickStockUI
from tasks.utility.restocking import RestockingUI
from tasks.daily.daily_quest import DailyQuestUI

BaseFlash = base_flash.BaseFlash
BasePageUI = base_page.BasePageUI
Neopet = neopet.Neopet
NeoItem = neoitem.NeoItem

def reload_modules():
    global BaseFlash, BasePageUI, Neopet, NeoItem
    from importlib import reload
    reload(base_page)
    reload(base_flash)
    reload(neopet)
    reload(neoitem)
    BaseFlash = base_flash.BaseFlash
    BasePageUI = base_page.BasePageUI
    Neopet = neopet.Neopet
    NeoItem = neoitem.NeoItem

def sc():
    Image.fromarray(device.screenshot()).save('test.png')

class TestUI(BaseFlash, BasePageUI):
    pass


alas = Nechouli('nechouli')
config, device = alas.config, alas.device
self = DailyQuestUI(config, device)

device.start_browser()
device.disable_stuck_detection()
device.screenshot_interval_set(0.1)

self.goto('https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html')

self.goto('https://www.neopets.com/pirates/academy.phtml?type=status')
current_pets = []
rows = self.page.locator('.content >> table > tbody > tr > td')
rows = rows.all()
i = -1
while True:
    i += 1
    if i >= len(rows):
        break
    print(i)
    print(rows[i].text_content())
    pet_name = next((p.name for p in pets if p.name in rows[i].text_content()), None)
    if not pet_name:
        continue
    infos = rows[i+1].locator('b').all()
    if len(infos) < 5:
        logger.warning(f"Parse pet info failed for {pet_name} in {academy} academy")
        continue
    current_pets.append(Neopet(
        name=pet_name,
        level=str2int(infos[0].text_content()),
        strength=str2int(infos[1].text_content()),
        defense=str2int(infos[2].text_content()),
        movement=str2int(infos[3].text_content()),
        max_health=str2int(infos[4].text_content().split('/')[-1]),
    ))
msg = 'Current pet info:\n' + '\n'.join(
    f"{p.name} (Lv={p.level}, Str={p.strength}, Def={p.defense}, Mov={p.movement}, Hp={p.max_health})"
    for p in current_pets
)
logger.info(msg)

fees = []
images = self.page.locator('.content >> img[src*="images.neopets.com/items/"]')
for img in images.all():
    fees.append(NeoItem(
        name=img.locator('../..').text_content().strip(),
    ))