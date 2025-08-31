from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.base.utils import str2int
from module import jelly_neo as jn
from module.db import data_manager as dm
from module.db.models.neoitem import NeoItem
from datetime import datetime

class ShopWizardUI(BasePageUI):
    MAX_MARKET_PRICE = 999999

    def main(self):
        if (
            self.config.stored.ShopWizardRequests.is_empty()
            and self.config.ShopWizard_EnableActivePriceUpdate
        ):
            self.add_price_update_items()
        if self.config.stored.ShopWizardRequests.is_empty():
            logger.info("No requests to process, skipping Shop Wizard")
            return True
        self.goto('https://www.neopets.com/shops/wizard.phtml')
        self.process_requests()
        return True

    def add_price_update_items(self):
        added = 0
        added_names = set()
        now_ts = datetime.now().timestamp()
        for i in self.config.stored.StockData.items+self.config.stored.InventoryData.items:
            item = jn.get_item_details_by_name(i.name)
            if item.get('market_price', 0) >= self.MAX_MARKET_PRICE:
                logger.info(f"Skipping {i.name} price update due to too expensive to search")
                continue
            if item.get("price_timestamp", 0) > now_ts - dm.JN_CACHE_TTL/2:
                continue
            self.config.stored.ShopWizardRequests.add(i.name, 'price_update', 0)
            added += 1
            added_names.add(i.name)
            if added >= self.config.ShopWizard_PriceUpdateBatchSize:
                break
        if added >= self.config.ShopWizard_PriceUpdateBatchSize:
            return
        # update expiring items in jn cache
        jn.load_cache()
        cache = sorted(dm.ItemDatabase.values(), key=lambda x: x.get('price_timestamp', 0))
        for item in cache:
            if item.get('market_price', 0) >= self.MAX_MARKET_PRICE:
                logger.info(f"Skipping {item['name']} price update due to too expensive to search")
                continue
            if item.get("price_timestamp", 0) > now_ts - dm.JN_CACHE_TTL/2:
                break
            if item["name"] in added_names:
                continue
            self.config.stored.ShopWizardRequests.add(item["name"], 'price_update', 0)
            added += 1
            added_names.add(item["name"])
            if added >= self.config.ShopWizard_PriceUpdateBatchSize:
                break

    def process_requests(self):
        reqs = []
        while not self.config.stored.ShopWizardRequests.is_empty():
            req = self.config.stored.ShopWizardRequests.pop()
            name, src = req.split('@')
            src, amount = src.split('#') if '#' in src else (src, '0')
            amount = str2int(amount)
            if amount > 0 and self.update_np() <= self.config.ProfileSettings_MinNpKeep:
                logger.warning(f"Skipping {name} (x{amount}) buying due to insufficient NP")
                reqs.append((name, src, amount))
                continue
            try:
                amount -= self._process_request(name, src, amount)
            except Exception as e:
                logger.error(f"Error processing request {req}: {e}")
            if amount > 0:
                reqs.append((name, src, amount))
            self.goto('https://www.neopets.com/shops/wizard.phtml')
        for name, src, amount in reqs:
            self.config.stored.ShopWizardRequests.add(name, src, amount)

    def _process_request(self, name: str, src: str, amount: int):
        if self.config.stored.InventoryData.is_full(amount):
            logger.warning(f"Skipping {name} (x{amount}) buying due to full inventory")
            return 0
        shop_link, price = self.search_item(name)
        if not price:
            logger.warning(f"Failed to find price for {name}")
            return 0
        jn.update_item_market_price(name, price)
        brought = 0
        if src == 'training' and amount:
            if self.update_np() <= self.config.ProfileSettings_MinNpKeep:
                logger.warning(f"Skipping {name} buying due to insufficient NP")
                return 0
            else:
                brought += self.purchase_item(name, shop_link, amount)
                amount -= brought
                item = NeoItem(name=name)
                item.update_jn()
                self.config.stored.InventoryData.add(item)
                if brought:
                    self.config.task_call('PetTraining')
                else:
                    logger.warning(f"Failed to buy {name} from {shop_link}, amount: {amount}")
        return brought

    def search_item(self, name: str) -> tuple[str, int]:
        logger.info(f"Searching for item: {name}")
        if self.check_blocked():
            return None,None
        self.page.locator('#shopwizard').fill(name)
        with self.page.expect_response("**/wizard.php") as resp:
                self.device.click('#submit_wizard')
                resp.value.finished()
        if self.check_blocked():
            return None,None
        self.device.wait_for_element('.wizard-results-text')
        depth = 0
        ret_price = 0
        ret_shop = ''
        while depth < self.config.ShopWizard_PriceUpdateRescans:
            self.device.wait_for_element('#resubmitWizard')
            rows = self.page.locator('.wizard-results-price')
            if rows.count():
                r = rows.first
                price = str2int(r.text_content())
                if ret_price == 0 or price < ret_price:
                    ret_shop = r.locator('../a').get_attribute('href')
                    ret_price = price
                    depth = 0
            logger.info(f"Found lowest price: {ret_price} for {name}, depth: {depth}")
            if ret_price == 1:
                break
            btn = self.page.locator('#resubmitWizard')
            self.device.scroll_to(loc=btn)
            with self.page.expect_response("**/wizard.php") as resp:
                self.device.click(btn)
                resp.value.finished()
            depth += 1
        if ret_shop and not ret_shop.startswith('http'):
            ret_shop = 'https://www.neopets.com' + ret_shop
        return ret_shop, ret_price

    def purchase_item(self, name, shop_link, amount=1) -> int:
        self.goto(shop_link)
        segs = self.page.url.split('&')
        good_id = next((s for s in segs if s.startswith('buy_obj_info')), None)
        if not good_id:
            logger.error(f"Failed to find good_id for {name} in {shop_link}")
            return 0
        good_id = good_id.split('=')[1]
        goods = self.page.locator(f'a[href*="obj_info_id={good_id}"]')
        brought = 0
        self.page.on('dialog', lambda dialog: dialog.accept())
        while goods.count() and amount:
            node = goods.nth(0)
            self.device.scroll_to(loc=node)
            self.device.click(node, nav=True)
            amount  -= 1
            brought += 1
        return brought

    def check_blocked(self):
        content = self.page.content().lower()
        if "too many searches" in content:
            logger.warning("Shop Wizard blocked due to too many searches, will retry later")
            return True
        if "help you until you complete" in content:
            logger.warning("You're on a fairy quest, you'll manually complete it!")
            return True
        return False

    def calc_next_run(self, *args):
        if self.config.ShopWizard_EnableActivePriceUpdate:
            return self.config.task_delay(minute=self.config.ShopWizard_PriceUpdateInterval)
        self.config.task_cancel()

if __name__ == '__main__':
    self = ShopWizardUI()
