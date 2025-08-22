import re
from turtle import rt
from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.db.models.neoitem import NeoItem
from module.base.utils import str2int, lcs_multi
import module.jelly_neo as jn

class SafetyDepositBoxUI(BasePageUI):
    items: list[NeoItem]
    PAGE_LIMIT: int = 30

    def main(self):
        try:
            self.goto("https://www.neopets.com/safetydeposit.phtml")
            self.scan_all_item()
        finally:
            self.config.task_cancel()
        return True

    def scan_all_item(self):
        self.items = []
        while True:
            items = self.scan_page_items()
            if not items:
                break
            self.items += items
            self.goto(f'https://www.neopets.com/safetydeposit.phtml?category=0&obj_name=&offset={len(self.items)}')
        item_names = [i.name for i in self.items]
        jn.batch_search(item_names)
        for item in self.items:
            item.update_jn()
        self.config.stored.DepositData.set(self.items)
        return self.items

    def scan_page_items(self, include_data:bool=False) -> list[NeoItem]:
        ret = []
        table = self.page.locator('#boxform').locator('..')
        rows = table.locator('tr')
        if not rows.count():
            return ret
        for row in rows.all()[1:]:
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
        box = self.page.locator('input[name="obj_name"]')
        if not box.count():
            logger.warning("Search box not found, cannot search for items.")
            return []
        logger.info("Searching for item: %s", name)
        box.first.fill(name)
        submit = self.page.locator('input[type="submit"][value="Find"]')
        if not submit.count():
            logger.warning("Submit button not found, cannot search for items.")
            return []
        self.device.click(submit, nav=True)
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
        moved = False
        for kw in search_queue:
            results = self.search(kw)
            for r in results:
                if r.name not in required_items:
                    continue
                amount = min(required_items[r.name], r.quantity)
                r.locator.nth(5).locator('input').fill(str(amount))
                required_items[r.name] -= amount
                retrieved[r.name] = amount
                if amount > 0:
                    moved = True
            if moved:
                self.device.click('.submit_data', nav=True)
            if len(results) >= self.PAGE_LIMIT:
                unscanned.update([n for n in names if kw in n])
        for kw in unscanned:
            results = self.search(kw)
            for r in results:
                if r.name not in required_items:
                    continue
                amount = min(required_items[r.name], r.quantity)
                required_items[r.name] -= amount
                retrieved[r.name] = amount
        missings = {k: v for k, v in required_items.items() if v > 0}
        return retrieved, missings

if __name__ == '__main__':
    self = SafetyDepositBoxUI()
