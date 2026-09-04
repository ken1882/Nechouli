from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.base.utils import str2int
from module import jelly_neo as jn
from module.db import data_manager as dm
from module.db.models.neoitem import NeoItem
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

class ShopWizardUI(BasePageUI):
    MAX_MARKET_PRICE = 999999
    FQUEST_PREFIX = "FQUEST_ITEM_"
    FQUEST_LOCK = "fquest_item_state"
    FQUEST_URL = "https://www.neopets.com/quests.phtml"
    SHOP_WIZARD_URL = "https://www.neopets.com/shops/wizard.phtml"

    def main(self):
        wizard_loaded = False
        auto_solve = self.config.ShopWizard_AutoSolveFaerieQuest
        if auto_solve and not self.get_username():
            self.goto(self.SHOP_WIZARD_URL)
            wizard_loaded = True
            if not self.get_username():
                logger.warning("Unable to identify the logged-in username; skipping faerie quest automation")
                auto_solve = False
            elif self.check_blocked():
                return True

        if (
            self.config.stored.ShopWizardRequests.is_empty()
            and self.config.ShopWizard_EnableActivePriceUpdate
        ):
            reqs = self.add_price_update_items()
            if reqs:
                self.config.stored.ShopWizardRequests.bulk_add(reqs)

        fquests = self.get_fquest_items() if auto_solve else {}
        own_key = self.fquest_key
        if own_key in fquests:
            if self.handle_faerie_quest():
                return True
            fquests = self.get_fquest_items()

        has_helper_work = any(
            key != own_key and '@' not in value
            for key, value in fquests.items()
        )
        if self.config.stored.ShopWizardRequests.is_empty() and not has_helper_work:
            logger.info("No requests to process, skipping Shop Wizard")
            return True

        if not wizard_loaded:
            self.goto(self.SHOP_WIZARD_URL)
        if self.check_blocked():
            return True
        if has_helper_work:
            self.process_fquest_requests()
        if not self.config.stored.ShopWizardRequests.is_empty():
            self.process_requests()
        return True

    @property
    def fquest_key(self):
        username = self.get_username()
        return f"{self.FQUEST_PREFIX}{username}" if username else ''

    def get_fquest_items(self):
        return dm.global_items(self.FQUEST_PREFIX)

    @staticmethod
    def parse_fquest_value(value: str):
        item_name, marker, result = value.partition('@')
        if not marker:
            return item_name, 'pending', None, None
        if not result:
            return item_name, 'claimed', None, None
        if not result.startswith('$') or '%' not in result:
            return item_name, 'invalid', None, None
        price, result_url = result[1:].split('%', 1)
        price = str2int(price)
        if price <= 0 or not result_url:
            return item_name, 'invalid', None, None
        return item_name, 'ready', price, result_url

    def set_fquest_value(self, key: str, value: str):
        with dm.dlock(self.FQUEST_LOCK):
            dm.global_set(key, value)

    def delete_fquest_value(self, key: str, expected: str = None):
        with dm.dlock(self.FQUEST_LOCK):
            if expected is not None and dm.global_get(key) != expected:
                return False
            dm.global_delete(key)
        return True

    def claim_fquest(self, key: str, item_name: str):
        with dm.dlock(self.FQUEST_LOCK):
            if dm.global_get(key) != item_name:
                return False
            dm.global_set(key, f"{item_name}@")
        return True

    def release_fquest(self, key: str, item_name: str):
        claimed = f"{item_name}@"
        with dm.dlock(self.FQUEST_LOCK):
            if dm.global_get(key) != claimed:
                return False
            dm.global_set(key, item_name)
        return True

    def publish_fquest_result(self, key: str, item_name: str, price: int, result_url: str):
        claimed = f"{item_name}@"
        with dm.dlock(self.FQUEST_LOCK):
            if dm.global_get(key) != claimed:
                return False
            dm.global_set(key, f"{claimed}${price}%{result_url}")
        return True

    def get_current_fquest_item(self):
        item = self.page.locator('#fq2 td.item b')
        if not item.count():
            return ''
        return item.first.inner_text().strip()

    def handle_faerie_quest(self):
        self.goto(self.FQUEST_URL)
        item_name = self.get_current_fquest_item()
        key = self.fquest_key
        quest_start = self.config.stored.FaerieQuestStartTime
        if not key:
            logger.warning("Unable to identify the quest owner's username")
            return bool(item_name)
        value = dm.global_get(key)

        if not item_name:
            if value is not None:
                self.delete_fquest_value(key, expected=value)
                logger.info("Removed stale faerie quest request for %s", self.config.config_name)
            if quest_start.is_set():
                quest_start.clear()
            return False

        parsed_item, state, price, result_url = self.parse_fquest_value(value or '')
        if parsed_item != item_name:
            self.set_fquest_value(key, item_name)
            quest_start.set()
            logger.info("Requested faerie quest item: %s", item_name)
            return True
        if not quest_start.is_set():
            quest_start.set()
        timeout = max(float(getattr(self.config, 'ShopWizard_FaerieQuestTimeout', 0) or 0), 0)
        if timeout and datetime.now() - quest_start.time >= timedelta(hours=timeout):
            logger.warning(
                "Faerie quest item %s exceeded timeout of %s hours; abandoning quest",
                item_name,
                timeout,
            )
            if self.abandon_faerie_quest(item_name):
                self.delete_fquest_value(key, expected=value)
                quest_start.clear()
                return False
            return True
        if state in ('pending', 'claimed'):
            logger.info("Waiting for a helper to find faerie quest item: %s", item_name)
            return True
        if state != 'ready':
            logger.warning("Resetting invalid faerie quest state for %s", item_name)
            self.set_fquest_value(key, item_name)
            return True

        if not self.validate_fquest_result(price, result_url):
            logger.warning("Invalid helper result for faerie quest item %s", item_name)
            self.set_fquest_value(key, item_name)
            return True

        if price > self.config.ShopWizard_QuestItemPriceThreshold:
            logger.warning(
                "Faerie quest item %s costs %s NP, above threshold %s; abandoning quest",
                item_name,
                price,
                self.config.ShopWizard_QuestItemPriceThreshold,
            )
            if self.abandon_faerie_quest(item_name):
                self.delete_fquest_value(key, expected=value)
                quest_start.clear()
                return False
            return True

        if self.config.stored.InventoryData.is_full(1):
            logger.warning("Cannot buy faerie quest item %s due to full inventory", item_name)
            return True
        wallet = self.update_np()
        if wallet - price < self.config.ProfileSettings_MinNpKeep:
            logger.warning(
                "Cannot buy faerie quest item %s for %s NP without spending below the NP reserve",
                item_name,
                price,
            )
            return True
        if self.purchase_item(item_name, result_url, 1) != 1:
            logger.warning("Failed to buy faerie quest item %s", item_name)
            return True

        self.goto(self.FQUEST_URL)
        if self.get_current_fquest_item() != item_name:
            logger.warning("Faerie quest changed after buying %s; retaining shared state", item_name)
            return True
        complete = self.page.locator('#complete_faerie_quest')
        if not complete.count():
            logger.warning("Unable to submit faerie quest item %s", item_name)
            return True
        self.device.click(complete.first, nav=True)
        if self.get_current_fquest_item() == item_name:
            logger.warning("Faerie quest submission did not complete for %s", item_name)
            return True
        self.delete_fquest_value(key, expected=value)
        quest_start.clear()
        logger.info("Completed faerie quest with %s", item_name)
        return False

    @staticmethod
    def validate_fquest_result(price: int, result_url: str):
        parsed = urlparse(result_url)
        if parsed.scheme not in ('http', 'https'):
            return False
        if parsed.hostname != 'www.neopets.com':
            return False
        query = parse_qs(parsed.query)
        link_price = str2int(query.get('buy_cost_neopoints', [''])[0])
        return price > 0 and link_price == price and bool(query.get('buy_obj_info_id', [''])[0])

    def abandon_faerie_quest(self, item_name: str):
        abandon = self.page.locator('#abandon_faerie_quest')
        if not abandon.count():
            logger.warning("Unable to find abandon button for faerie quest item %s", item_name)
            return False
        self.device.click(abandon.first)
        confirm = self.device.wait_for_element('#abandon_popup .yes_button')
        self.device.click(confirm, nav=True)
        if self.get_current_fquest_item() == item_name:
            logger.warning("Faerie quest abandonment did not complete for %s", item_name)
            return False
        return True

    def process_fquest_requests(self):
        for key, value in sorted(self.get_fquest_items().items()):
            if key == self.fquest_key or '@' in value:
                continue
            item_name = value
            if not self.claim_fquest(key, item_name):
                continue
            logger.info("Helping find faerie quest item %s for %s", item_name, key)
            published = False
            try:
                result_url, price = self.search_item(item_name)
                if result_url and price:
                    published = self.publish_fquest_result(key, item_name, price, result_url)
                    if published:
                        logger.info("Found faerie quest item %s for %s NP", item_name, price)
            except Exception as e:
                logger.error("Error searching for faerie quest item %s: %s", item_name, e)
            finally:
                if not published:
                    self.release_fquest(key, item_name)
            self.goto(self.SHOP_WIZARD_URL)
            if self.check_blocked():
                return

    def add_price_update_items(self):
        added_names = set()
        now_ts = datetime.now().timestamp()
        ret = []
        for i in self.config.stored.StockData.items+self.config.stored.InventoryData.items:
            item = jn.get_item_details_by_name(i.name)
            if item.get('market_price', 0) >= self.MAX_MARKET_PRICE:
                logger.info(f"Skipping {i.name} price update due to too expensive to search")
                continue
            if item.get("price_timestamp", 0) > now_ts - dm.JN_CACHE_TTL/2:
                continue
            ret.append((i.name, 'price_update', 0))
            added_names.add(i.name)
            if len(ret) >= self.config.ShopWizard_PriceUpdateBatchSize:
                break
        if len(ret) >= self.config.ShopWizard_PriceUpdateBatchSize:
            return ret
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
            ret.append((item["name"], 'price_update', 0))
            added_names.add(item["name"])
            if len(ret) >= self.config.ShopWizard_PriceUpdateBatchSize:
                break
        return ret

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
            self.goto(self.SHOP_WIZARD_URL)
        self.config.stored.ShopWizardRequests.bulk_add(reqs)

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
        query = parse_qs(urlparse(self.page.url).query)
        good_id = query.get('buy_obj_info_id', [''])[0]
        if not good_id:
            logger.error(f"Failed to find good_id for {name} in {shop_link}")
            return 0
        price = query.get('buy_cost_neopoints', [''])[0]
        logger.info(f"Buying {name} (x{amount}) for {price} NP")
        goods = self.page.locator(f'.bsp-item--featured[data-oii="{good_id}"] .bsp-item__buy')
        brought = 0
        while amount:
            if not goods.count():
                logger.warning(f"Failed to find pinned shop item {name} ({good_id})")
                break
            node = goods.first
            self.device.scroll_to(loc=node)
            self.device.click(node)
            confirm = self.device.wait_for_element('#bsp-buy-confirm')
            self.device.click(confirm)
            result = self.device.wait_for_element('#bsp-buy-success-popup', '#bsp-buy-error-popup')
            if result.get_attribute('id') != 'bsp-buy-success-popup':
                logger.warning(f"Failed to buy {name}: {result.inner_text()}")
                break
            logger.info(f"Bought {name}")
            ok = self.device.wait_for_element('#bsp-buy-success-ok')
            self.device.click(ok)
            amount  -= 1
            brought += 1
        return brought

    def check_blocked(self):
        content = self.page.content().lower()
        if "too many searches" in content:
            logger.warning("Shop Wizard blocked due to too many searches, will retry later")
            return True
        if "help you until you complete" in content:
            if self.config.ShopWizard_AutoSolveFaerieQuest:
                logger.info("Faerie quest detected; checking requested item")
                self.handle_faerie_quest()
            else:
                logger.warning("You're on a faerie quest, you have to manually complete it!")
            return True
        return False

    def calc_next_run(self, *args):
        if self.config.ShopWizard_EnableActivePriceUpdate:
            return self.config.task_delay(minute=self.config.ShopWizard_PriceUpdateInterval)
        self.config.task_cancel()

if __name__ == '__main__':
    self = ShopWizardUI()
