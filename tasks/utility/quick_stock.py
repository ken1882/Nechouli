import re
from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.db.models.neoitem import NeoItem
from module.base.utils import str2int
from module.config.utils import get_server_next_update
import module.jelly_neo as jn

class QuickStockUI(BasePageUI):
    items: list[NeoItem]

    def main(self):
        self.items = []
        self._stocked = False
        self.goto("https://www.neopets.com/market.phtml?type=your")
        used, free = self.get_stock_capacity()
        self.free_stocks = free
        self.goto('https://www.neopets.com/quickstock.phtml')
        self.scan_all_items()
        self.process_actions()
        self.update_inventory_data()
        if self._stocked and free:
            self.update_stock_price()
        if self.config.QuickStock_WithdrawTill:
            self.withdraw_all_np()
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
            item = NeoItem(name=item_name, _locator=node, quantity=1, _act='deposit')
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
        deposit_list = [l.strip().lower() for l in (self.config.QuickStock_ForceDepositList or '').split('\n') if l.strip()]
        no_stock = self._kwargs.get('no_stock', False)
        for item in self.items:
            item.profit = item.market_price - item.restock_price
            if (
                any(re.search(regex, item.name, re.I) for regex in deposit_list)
                or item.profit >= self.config.QuickStock_DepositValue
            ):
                item._act = 'deposit'
                continue
            if item.category == 'cash':
                item._act = 'keep'
                continue
            if any(re.search(regex, item.name, re.I) for regex in blacklist):
                item._act = 'keep'
                continue
            if item.name.lower() in donate_list:
                item._act = 'donate'
                continue
            available_acts = [act.get_attribute('value') for act in item._locator.locator('input').all()]
            if item.category in keep_dict and keep_dict[item.category] > 0:
                if item.category == 'food' and item.market_price >= self.config.PetCares_MaxFeedValue:
                    if item.profit > self.config.QuickStock_RestockProfit and not no_stock:
                        item._act = 'stock'
                        self._stocked = True
                    else:
                        item._act = 'deposit'
                else:
                    item._act = 'keep'
                    keep_dict[item.category] -= 1
            elif item.profit > self.config.QuickStock_RestockProfit and not no_stock:
                item._act = 'stock'
                self._stocked = True
            elif 'closet' in available_acts:
                item._act = 'closet'
        row_height = 22
        viewport_height = 400
        viewport_y = 0
        cur_y = 100
        for item in self.items:
            acts = item._locator.locator('input').all()
            if item._act == 'stock':
                if self.free_stocks <= 0:
                    logger.warning(f"No free stocks available for item {item.name}, deposit instead")
                    item._act = 'deposit'
                else:
                    self.free_stocks -= 1
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

    def get_stock_capacity(self):
        stock_text = self.page.locator('center').first.text_content().split(':')
        if len(stock_text) < 3:
            logger.warning("Failed to parse stock capacity")
            self.config.stored.StockData.capacity = 0
            return 0, 0
        used, free = str2int(stock_text[-2]), str2int(stock_text[-1])
        logger.info(f"Stock capacity: {used+free} ({used}/{free})")
        self.config.stored.StockData.capacity = used + free
        return used, free

    def update_stock_price(self):
        self.goto("https://www.neopets.com/market.phtml?type=your")
        stocked_data = []
        self.device.scroll_to(0, 100)
        while True:
            rows = self.page.locator('form[action] > table > tbody > tr')
            if rows.count() < 3:
                logger.warning("No stocked items in your shop")
                break
            goods = rows.all()[1:-1]
            row_height = 80
            viewport_height = 400
            viewport_y = 0
            cur_y = 100
            for good in goods:
                cur_y += row_height
                if cur_y > viewport_y + viewport_height:
                    viewport_y = cur_y
                    self.device.scroll_to(0, viewport_y)
                cells = good.locator('td')
                name = cells.first.text_content().strip()
                item = NeoItem(name=name)
                item.update_jn()
                item.quantity = str2int(cells.nth(2).text_content().strip())
                stocked_data.append(item)
                item_data = jn.get_item_details_by_name(name)
                price = self.evaluate_price_strategy(item_data)
                old_price = 0
                input = cells.nth(4).locator('input')
                item.stocked_price = price
                try:
                    old_price = str2int(input.get_attribute('value'))
                except Exception as e:
                    logger.error(f"Failed to parse old price for {name}: {e}")
                    continue
                if price <= 0 or old_price == price:
                    continue
                logger.info(f"Setting price for {name} to {price}")
                input.fill(str(price))
            upd_btn = self.page.locator('input[type=submit][value="Update"]')
            self.device.click(upd_btn, nav=True)
            next_page = self.page.locator('input[name=subbynext]')
            if not next_page.count():
                break
            disabled = type(next_page.first.get_attribute('disabled')) is str
            if disabled:
                break
            self.device.click(next_page.first, nav=True)
        self.config.stored.StockData.set(stocked_data)

    def evaluate_price_strategy(self, item: dict):
        script = self.config.QuickStock_PriceStrategyScript
        safe_globals = {
            '__builtins__': {
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
            },
            'item': item,
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

    def update_inventory_data(self):
        self.goto('https://www.neopets.com/quickstock.phtml')
        self.scan_all_items()
        self.config.stored.InventoryData.set(self.items)
        logger.info(f"Updated inventory with {len(self.items)} items (size={self.config.stored.InventoryData.size}).")

    def withdraw_all_np(self):
        if not self.config.stored.StockData.capacity:
            logger.info("Shop not opened, cannot withdraw from till")
            return
        self.goto('https://www.neopets.com/market.phtml?type=till')
        money = str2int(self.page.locator('.content >> p > b').text_content())
        if money <= 0:
            logger.info("No NP in till to withdraw")
            return
        self.page.locator('input[name="amount"]').fill(str(money))
        self.device.click('input[type="submit"][value="Withdraw"]', nav=True)

    # def calc_next_run(self, *args):
    #     future = get_server_next_update('02:00')
    #     self.config.task_delay(target=future)
    #     # this task is normally called by other tasks so cancel itself after run
    #     self.config.task_cancel('QuickStock')

if __name__ == '__main__':
    self = QuickStockUI()
