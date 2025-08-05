from module.logger import logger
from module.base.utils import str2int
from module.db.models.neoitem import NeoItem
from module.db.data_map import SHOP_NAME
from tasks.base.base_page import BasePageUI
from copy import copy
import module.jelly_neo as jn

class RestockingUI(BasePageUI):
    goods: list[NeoItem]

    def main(self):
        self.goods = []
        for shop_id in copy(self.config.Restocking_ShopList):
            self.do_shopping(shop_id)
        return True

    def check_inventory(self):
        pass

    def calc_next_run(self, *args):
        self.config.Restocking_DailyQuestTimesLeft = 0 # reset temp variable
        super().calc_next_run(*args)

    def do_shopping(self, shop_id: int):
        self.goto(f"https://www.neopets.com/objects.phtml?type=shop&obj_type={shop_id}")
        self.scan_goods()
        shop_name = SHOP_NAME[shop_id]
        if not self.goods:
            logger.warning(f"No goods found in {shop_name}")
            return
        targets = self.get_profitable_goods()
        if not targets:
            logger.info(f"No profitable goods found in {shop_name}")
            return
        target = None
        for t in targets:
            if t.restock_price > self.config.Restocking_MaxCost:
                logger.info(f"Item {t.name} exceeds max cost, skipping")
                continue

    def scan_goods(self):
        self.goods = []
        nodes = self.page.locator(".shop-item")
        item_names =  set()
        for i, node in enumerate(nodes):
            stock, price = node.locator('.item-stock').all()
            item = NeoItem(
                index=i,
                name=node.locator('.item-name').text_content(),
                quantity=str2int(stock.text_content().split()[0]),
                restock_price=str2int(price.text_content().split()[1]),
                _locator=node,
            )
            self.goods.append(item)
            item_names.add(item.name)
        jn.batch_search(item_names)
        for item in self.goods:
            item.update_jn()

    def get_profitable_goods(self):
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

if __name__ == '__main__':
    self = RestockingUI()
