import re
from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.db.models.neoitem import NeoItem
import module.jelly_neo as jn

class QuickStockUI(BasePageUI):
    items: list[NeoItem]

    def main(self):
        self.items = []
        self.goto('https://www.neopets.com/quickstock.phtml')
        self.scan_all_items()
        self.process_actions()
        return True

    def scan_all_items(self):
        self.items = []
        nodes = self.page.locator('form > table > tbody > tr')
        for node in nodes.all()[:-1]:
            available_acts = node.locator('input')
            if not available_acts.count():
                continue
            item_name = node.locator('td').first.text_content().strip()
            if item_name.lower() == 'check all':
                break
            item = NeoItem(name=item_name, _locator=node, _act='deposit')
            self.items.append(item)
        jn.batch_search(set(item.name for item in self.items))
        for item in self.items:
            item.update_jn()

    def get_keep_dict(self):
        lines = self.config.QuickStock_CategoryKeeps.split('\n')
        rows = [line.split(':') for line in lines if line.strip()]
        ret = {}
        for row in rows:
            if len(row) != 2:
                logger.warning(f"Invalid CategoryKeeps rule: {row}")
                continue
            category, keep = row
            try:
                ret[category.strip().lower()] = int(keep.strip())
            except ValueError:
                logger.warning(f"Invalid keep value rule: {row}")
        return ret

    def process_actions(self):
        keep_dict = self.get_keep_dict()
        blacklist = [l.strip() for l in (self.config.QuickStock_DepositBlacklist or '').split('\n') if l.strip()]
        donate_list = [l.strip() for l in (self.config.QuickStock_DonateNameList or '').split('\n') if l.strip()]
        deposit_list = [l.strip() for l in (self.config.QuickStock_ForceDepositList or '').split('\n') if l.strip()]
        for item in self.items:
            if item.category == 'cash':
                item._act = 'keep'
                continue
            if any(re.search(regex, item.name, re.I) for regex in deposit_list):
                item._act = 'deposit'
                continue
            if any(re.search(regex, item.name, re.I) for regex in blacklist):
                item._act = 'keep'
                continue
            if any(re.search(regex, item.name, re.I) for regex in donate_list):
                item._act = 'donate'
                continue
            available_acts = [act.get_attribute('value') for act in item._locator.locator('input').all()]
            if item.category in keep_dict and keep_dict[item.category] > 0:
                item._act = 'keep'
                keep_dict[item.category] -= 1
            elif item.market_price - item.restock_price > self.config.QuickStock_RestockProfit:
                item._act = 'stock'
            elif 'closet' in available_acts:
                item._act = 'closet'
        row_height = 24
        viewport_height = 400
        viewport_y = 0
        cur_y = 100
        for item in self.items:
            acts = item._locator.locator('input').all()
            for act in reversed(acts):
                aname = act.get_attribute('value')
                if aname == item._act:
                    logger.info(f"Performing action {aname} for item {item.name}")
                    act.click()
            cur_y += row_height
            if cur_y > viewport_y + viewport_height:
                viewport_y = cur_y
                self.device.scroll_to(0, viewport_y)
        self.page.on("dialog", lambda dialog: dialog.accept())
        btn = self.page.locator('input[type=submit][value="Submit"]')
        self.device.scroll_to(loc=btn)
        self.device.click(btn)


if __name__ == '__main__':
    self = QuickStockUI()
