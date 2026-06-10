from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.db.models.neoitem import NeoItem
from module.base.utils import str2int, lcs_multi
import module.jelly_neo as jn

class SafetyDepositBoxUI(BasePageUI):
    items: list[NeoItem]
    PAGE_LIMIT: int = 30

    def _wait_for_load(self):
        self.device.wait(0.5) # js responsive
        while self.page.locator('.sdb-loading-overlay').count():
            self.device.wait(0.5)
    
    def main(self):
        self.goto("https://www.neopets.com/safetydeposit.phtml")
        self.scan_all_item()
        return True

    def scan_all_item(self):
        self._wait_for_load()
        self.items = []
        self.page.locator('.sdb-select').nth(1).select_option(value='90')
        self._wait_for_load()
        while True:
            items = self.scan_page_items()
            if not items:
                break
            self.items += items
            n_page = self.page.locator('.sdb-pagination-jump input[min="1"]')
            if n_page.count() and n_page.get_attribute('max') != n_page.input_value():
                self.device.click('.sdb-pagination-next')
                self._wait_for_load()
            else:
                break

        item_names = [i.name for i in self.items]
        jn.batch_search(item_names)
        for item in self.items:
            item.update_jn()
        self.config.stored.DepositData.set(self.items)
        return self.items

    def scan_page_items(self, include_data:bool=False) -> list[NeoItem]:
        rows = self.page.locator('tr:has(.sdb-item-name)')
        data = rows.evaluate_all("""rows => rows.map((row, index) => ({
            index,
            name: row.querySelector('.sdb-item-name')?.textContent?.trim() || '',
            quantity: row.querySelector('.sdb-qty-cell')?.textContent?.trim() || '',
            image: row.querySelector('.sdb-item-img')?.src || '',
        })).filter(item => item.name)""")
        if data:
            ret = [
                NeoItem(
                    name=item['name'],
                    quantity=str2int(item['quantity']),
                    image=item['image'],
                    _locator=rows.nth(item['index'])
                )
                for item in data
            ]
            for item in ret:
                logger.info("Found item: %s", item.name)
        else:
            ret = []
            table = self.page.locator('#boxform').locator('..')
            legacy_rows = table.locator('tr')
            if not legacy_rows.count():
                return ret
            for row in legacy_rows.all()[1:]:
                cells = row.locator('td')
                if cells.count() < 5:
                    continue
                name = cells.nth(1).text_content()
                rm_rarity_suffix = cells.nth(1).locator('span')
                if rm_rarity_suffix.count():
                    rm_rarity_suffix = rm_rarity_suffix.first.text_content()
                    if rm_rarity_suffix.startswith('('):
                        name = name[:-len(rm_rarity_suffix)].strip()
                logger.info("Found item: %s", name)
                amount = str2int(cells.nth(4).text_content())
                ret.append(NeoItem(
                    name=name,
                    quantity=amount,
                    _locator=cells
                ))
        if include_data:
            item_names = [i.name for i in ret]
            jn.batch_search(item_names)
            for item in ret:
                item.update_jn()
        return ret

    def _confirm_action(self) -> bool:
        confirm = self.page.locator('button:has-text("Confirm")')
        if confirm.count():
            self.device.click(confirm.first)
            ok = self.page.locator('button:has-text("OK")')
            try:
                ok.last.wait_for(state='visible', timeout=self.config.Playwright_DefaultTimeout * 1000)
                self.device.click(ok.last)
            except Exception:
                logger.warning("SDB action result popup did not appear.")
                return False
            self._wait_for_load()
            return True
        self.device.click('.submit_data', nav=True)
        self._wait_for_load()
        return True

    def search(self, name:str) -> list[NeoItem]:
        '''
        Search for items in the safety deposit box by name.

        Args:
            name (str): The name of the item to search for.

        Returns:
            list[NeoItem]: A list of NeoItem objects that match the name, only up to 30 items.
        '''
        if not self.page.url.startswith('https://www.neopets.com/safetydeposit.phtml'):
            self.goto('https://www.neopets.com/safetydeposit.phtml')
        self._wait_for_load()
        box = self.page.locator('.sdb-search-input')
        if not box.count():
            logger.warning("Search box not found, cannot search for items.")
            return []
        logger.info("Searching for item: %s", name)
        box.first.fill(name)
        submit = self.page.locator('.sdb-search-btn')
        if not submit.count():
            logger.warning("Submit button not found, cannot search for items.")
            return []
        self.device.click(submit)
        self._wait_for_load()
        return self.scan_page_items()

    def retrieve_items(self, required_items: dict[str,int]) -> tuple[dict, dict]:
        '''
        Retrieve items from the safety deposit box.

        Args:
            required_items (dict[str, int]): A dictionary where keys are item names and values are the quantities needed.

        Returns:
            tuple[dict, dict]: A tuple containing two dictionaries:
                - The first dictionary contains items that were successfully retrieved.
                - The second dictionary contains items that were not found or could not be retrieved.
        '''
        names = [item for item, val in required_items.items() if val > 0]
        search_queue = lcs_multi(names)
        retrieved = {}
        unscanned = set()
        for kw in search_queue:
            if all(v <= 0 for v in required_items.values()):
                break
            results = self.search(kw)
            moved = False
            for r in results:
                if r.name not in required_items:
                    continue
                amount = min(required_items[r.name], r.quantity)
                if amount <= 0:
                    continue
                if r.locator.locator('.np-stepper-input').count():
                    r.locator.locator('.np-stepper-input').fill(str(amount))
                    r.locator.locator('.sdb-action-select').select_option('inventory')
                    if not self._confirm_action():
                        continue
                else:
                    r.locator.nth(5).locator('input').fill(str(amount))
                    moved = True
                required_items[r.name] -= amount
                retrieved[r.name] = retrieved.get(r.name, 0) + amount
            if moved:
                self._confirm_action()
            if len(results) >= self.PAGE_LIMIT:
                unscanned.update([n for n in names if kw in n])
        for kw in unscanned:
            results = self.search(kw)
            moved = False
            for r in results:
                if r.name not in required_items:
                    continue
                amount = min(required_items[r.name], r.quantity)
                if amount <= 0:
                    continue
                if r.locator.locator('.np-stepper-input').count():
                    r.locator.locator('.np-stepper-input').fill(str(amount))
                    r.locator.locator('.sdb-action-select').select_option('inventory')
                    if not self._confirm_action():
                        continue
                else:
                    r.locator.nth(5).locator('input').fill(str(amount))
                    moved = True
                required_items[r.name] -= amount
                retrieved[r.name] = retrieved.get(r.name, 0) + amount
            if moved:
                self._confirm_action()
        missings = {k: v for k, v in required_items.items() if v > 0}
        return retrieved, missings

if __name__ == '__main__':
    self = SafetyDepositBoxUI()
