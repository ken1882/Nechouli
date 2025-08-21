from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.base.utils import str2int
from module import jelly_neo as jn
from module.db import data_manager as dm
from datetime import datetime

class ShopWizardUI(BasePageUI):

    def main(self):
        if self.config.ShopWizard_EnableActivePriceUpdate:
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
            if item.get("price_timestamp", 0) > now_ts - dm.JN_CACHE_TTL/2:
                continue
            self.config.stored.ShopWizardRequests.add(i.name, 'price_update')
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
            if item.get("price_timestamp", 0) > now_ts - dm.JN_CACHE_TTL/2:
                break
            if item["name"] in added_names:
                continue
            self.config.stored.ShopWizardRequests.add(item["name"], 'price_update')
            added += 1
            added_names.add(item["name"])
            if added >= self.config.ShopWizard_PriceUpdateBatchSize:
                break

    def process_requests(self):
        while not self.config.stored.ShopWizardRequests.is_empty():
            req = self.config.stored.ShopWizardRequests.pop()
            name, src = req.split('@')
            mp = jn.get_item_details_by_name(name).get('market_price', 0)
            if mp == 0 or mp > 950000:
                logger.warning(f"Skipping {name} due to probably unavailable at shops (jn price={mp})")
                continue
            price = self.search_item_price(name)
            if not price:
                logger.warning(f"Failed to find price for {name}")
                return
            if src == 'price_update':
                jn.update_item_market_price(name, price)
            self.goto('https://www.neopets.com/shops/wizard.phtml')

    def search_item_price(self, name: str):
        logger.info(f"Searching for item: {name}")
        if self.check_blocked():
            return None
        self.page.locator('#shopwizard').fill(name)
        with self.page.expect_response("**/wizard.php") as resp:
                self.device.click('#submit_wizard')
                resp.value.finished()
        if self.check_blocked():
            return None
        self.device.wait_for_element('.wizard-results-text')
        depth = 0
        ret = 0
        while depth < self.config.ShopWizard_PriceUpdateRescans:
            self.device.wait_for_element('#resubmitWizard')
            rows = self.page.locator('.wizard-results-price')
            if rows.count():
                price = str2int(rows.first.text_content())
                if ret == 0 or price < ret:
                    ret = price
                    depth = 0
            logger.info(f"Found lowest price: {ret} for {name}, depth: {depth}")
            btn = self.page.locator('#resubmitWizard')
            self.device.scroll_to(loc=btn)
            with self.page.expect_response("**/wizard.php") as resp:
                self.device.click(btn)
                resp.value.finished()
            depth += 1
        return ret

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
