from module.logger import logger
from module.base.utils import str2int
from module.db.models.neoitem import NeoItem
from module.db.data_map import SHOP_NAME
from module.base.utils import str2int
from module.exception import ScriptError
from tasks.base.base_page import BasePageUI
from playwright._impl._errors import Error as PlaywrightError
from playwright._impl._errors import TimeoutError
from copy import copy
import module.jelly_neo as jn
from module import captcha
import re
import os
from shutil import copy2

class RestockingUI(BasePageUI):
    goods: list[NeoItem]
    target: NeoItem
    last_captcha_url: str

    def main(self):
        self.check_inventory()
        self.update_np()
        if not self.has_enough_np():
            logger.warning("No enough NP to restock, skip restocking")
            return True
        if self.check_full():
            return None
        self.goods = []
        for shop_id in copy(self.config.Restocking_ShopList.split(',')):
            for _ in range(self.config.Restocking_RestockPerShop):
                if not self.has_enough_np():
                    logger.warning("No enough NP to restock, skip restocking")
                    return True
                try:
                    success = self.do_shopping(int(shop_id))
                except (TimeoutError, PlaywrightError) as e:
                    logger.error(f"Error occurred while shopping: {e}")
                    self.device.respawn_page()
                    continue
                if success:
                    self.inventory_free -= 1
                    if self.check_full():
                        return False
                    logger.info(f"Inventory free slots left: {self.inventory_free}")
                    self.device.wait(4) # neopets enforce 5 seconds cooldown between purchases
                elif success == None:
                    logger.info("Nothing to buy in shop, skipping")
                    break
                if self.config.stored.DailyQuestRestockTimesLeft.value and success:
                    self.config.stored.DailyQuestRestockTimesLeft.sub()
                    if self.config.stored.DailyQuestRestockTimesLeft.value <= 0:
                        logger.info("Completed daily quest restocking, stopping")
                        self.config.task_call('DailyQuest')
                        return True
        self.config.task_call('QuickStock')
        return True

    def check_inventory(self):
        self.goto('https://www.neopets.com/inventory.phtml')
        line = self.page.locator('.inv-total-count').text_content().strip()
        r = re.search(r"(\d+) / (\d+)", line)
        self.inventory_free = 0
        if r:
            cur, total = r.groups()
            self.inventory_free = int(total) - int(cur)

    def check_full(self):
        if self.inventory_free > self.config.QuickStock_KeepInventorySlot:
            return False
        logger.warning(
            f"Not enough inventory space: {self.inventory_free} slots available, "
            f"need at least {self.config.QuickStock_KeepInventorySlot+1} (by QuickStock setting)"
        )
        if self.config.stored.StockData.size and self.config.stored.StockData.is_full():
            logger.warning("Your shop stock is full, abort restocking")
            return True
        self.config.task_call('QuickStock')
        self.config.task_delay(minute=1)
        return True

    def calc_next_run(self, s=None):
        if not s:
            if self.config.Restocking_ActiveRestocking:
                return self.config.task_delay(minute=self.config.Restocking_ActiveRestockInterval)
            else:
                return self.config.task_cancel('Restocking')
        super().calc_next_run(s)

    def do_shopping(self, shop_id: int):
        self.goto(f"https://www.neopets.com/objects.phtml?type=shop&obj_type={shop_id}")
        self.scan_goods()
        shop_name = SHOP_NAME[shop_id]
        if not self.goods:
            logger.info(f"No goods found in {shop_name}")
            return None
        targets = self.get_profitable_goods()
        self.target = None
        for t in targets:
            if t.restock_price > self.config.Restocking_MaxCost:
                logger.info(f"Item {t.name} exceeds max cost, skipping")
                continue
            elif t.profit < self.config.Restocking_MinProfit:
                if self.config.DailyQuest_PurchaseUnprofitableItems and t.restock_price < 1000:
                    logger.info(f"Buying unprofitable cheap item {t.name} for daily quest")
                else:
                    logger.info(f"Item {t.name} profit {t.profit} is less than minimum profit {self.config.Restocking_MinProfit}, skipping")
                    continue
            else:
                for stocked in self.config.stored.StockData:
                    if stocked.name == t.name and stocked.quantity >= self.config.Restocking_MaxShopStock:
                        logger.info(f"Item {t.name} already fully stocked in your shop, skipping")
                        continue
            self.target = t
            break
        if not self.target:
            logger.info(f"No profitable goods found in {shop_name}")
            return None
        return self.buy_item()

    def buy_item(self, item:NeoItem=None):
        if not item:
            item = self.target
        logger.info(f"Buying item: {item.name} (Price/Profit: {item.restock_price} / {item.profit})")
        confirm_btn = self.page.locator('#confirm-link')
        while not confirm_btn.is_visible():
            self.device.click(item._locator, wait=0.1)
            if not confirm_btn.is_visible():
                bb = item._locator.bounding_box()
                mx, my = bb['x'] + 30, bb['y'] + 30
                self.device.click((mx, my), wait=0.1)
        self.device.click(confirm_btn)
        self.last_captcha_url = ''
        if item.profit >= self.config.Restocking_ImmediateProfit:
            return self.haggle(depth=999)
        return self.haggle()

    def scan_goods(self):
        self.goods = []
        nodes = self.page.locator(".shop-item")
        item_names =  set()
        for i, node in enumerate(nodes.all()):
            stock, price = node.locator('.item-stock').all()
            item = NeoItem(
                index=i,
                name=node.locator('.item-name').text_content(),
                quantity=str2int(stock.text_content().split()[0]),
                restock_price=str2int(price.text_content().split()[1]),
                _locator=node,
            )
            item.restock_price = str2int(node.text_content().split(':')[-1])
            self.goods.append(item)
            item_names.add(item.name)
        jn.batch_search(item_names)
        for item in self.goods:
            item.update_jn()

    def get_profitable_goods(self) -> list[NeoItem]:
        ret = []
        for good in self.goods:
            try:
                profit = good.market_price - good.restock_price
            except Exception:
                profit = 0
            if profit > 0:
                good.profit = profit
                ret.append(good)
        return sorted(ret, key=lambda x: x.profit, reverse=True)

    def haggle(self, offers=None, purposes=None, depth=0):
        offers = offers or []
        purposes = purposes or []
        if 'SOLD OUT' in self.page.content():
            logger.info("Failed to purchase item, reason: sold out")
            return False
        self.wait_for_captcha()
        page_content = self.page.content()
        if 'accept your offer' in page_content or 'has been added' in page_content:
            self.finalize_purchase(offers, purposes)
            return True
        elif 'SOLD OUT' in page_content:
            logger.info("Failed to purchase item, reason: sold out")
            return False
        elif 'Server Error' in page_content:
            logger.error("Server error occurred")
            return False
        purpose_node = self.page.locator('#shopkeeper_makes_deal')
        self.device.scroll_to(loc=purpose_node)
        text = purpose_node.text_content().strip()
        purposed_price = str2int(text)
        last_purpose = purposes[-1] if purposes else 10**8
        if purposed_price > last_purpose:
            purposed_price = str2int(' '.join(text.split()[-5:]))
            if not purposed_price:
                purposed_price = str2int(' '.join(text.split()[-8:]))
        purposes.append(purposed_price)
        bargain_price = self.eval_bargain_script(offers.copy(), purposes.copy(), depth)
        new_offers = offers.copy()
        new_offers.append(bargain_price)
        logger.info(f"Making offer with {bargain_price} NP")
        self.device.input_number('input[name=current_offer]', bargain_price)
        self.solve_captcha()
        while True:
            try:
                if 'accept your offer' in self.page.content():
                    return self.finalize_purchase(offers, purposes)
                elif 'SOLD OUT' in self.page.content():
                    logger.info("Item is sold out")
                    return False
                elif 'must select the correct pet' in self.page.content():
                    logger.info(f"Captcha failed, retry")
                    new_offers.pop()
                    if captcha.LAST_IMAGE_FILE:
                        out = f"{captcha.SAVE_DIR}/{os.path.basename(captcha.LAST_IMAGE_FILE)}_failed.png"
                        copy2(captcha.LAST_IMAGE_FILE, out)
                break
            except PlaywrightError: # page navigation interrupted
                self.device.wait(0.3)
        return self.haggle(new_offers, purposes.copy(), depth + 1)

    def finalize_purchase(self, offers, purposes):
        logger.info(f"Purchase done, offer history: {offers}, purpose history: {purposes}")
        return True

    def wait_for_captcha(self):
        url = '_'
        while url == self.last_captcha_url:
            self.device.wait(0.1)
            url = captcha.get_captcha_url(self.page)
        self.device.wait(1)
        self.last_captcha_url = url

    def has_enough_np(self):
        return self.update_np() >= self.config.ProfileSettings_MinNpKeep

    def eval_bargain_script(self, offers:list, purposes:list, depth=0):
        script = self.config.Restocking_BargainStrategyScript
        safe_globals = {
            '__builtins__': {
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'int': int,
                'float': float,
                'print': print,
                'len': len,
                'list': list,
                'type': type,
            },
            'offers': offers,
            'purposes': purposes,
            'depth': depth,
        }
        safe_locals = { 'return_value': None }
        wrapped_script = 'def wrapped_script():\n'
        wrapped_script += '\n'.join(f'  {line}' for line in script.splitlines())
        wrapped_script += '\nreturn_value = wrapped_script()\n'
        try:
            exec(wrapped_script, safe_globals, safe_locals)
            return int(safe_locals.get('return_value', 0))
        except Exception as e:
            raise ValueError(f"Script execution failed: {e}")

    def solve_captcha(self):
        pos = captcha.solve(self.page, debug=self.config.Restocking_EnableCaptchaDebug)
        if not pos:
            raise ScriptError("Failed to solve captcha")
        captcha_canvas = self.page.locator('input[type="image"][src*="/captcha_show.phtml"]')
        bb = captcha_canvas.bounding_box()
        mx, my = pos
        mx += bb['x']
        my += bb['y']
        my += 5 # offset due seems failed one slighty higher than expected
        logger.info(f"Clicking captcha at {mx}, {my}")
        self.page.mouse.click(mx, my)

    def on_failed_delay(self):
        self.config.task_delay(minute=3)

if __name__ == '__main__':
    self = RestockingUI()
