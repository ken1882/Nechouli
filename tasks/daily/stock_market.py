from sympy import expand
from module.logger import logger
from module.base.utils import str2int
from tasks.base.base_page import BasePageUI

class StockMarketUI(BasePageUI):

    def main(self):
        self.process_sells()
        purchased = self.process_buys()
        return purchased

    def process_sells(self):
        self.goto('https://www.neopets.com/stockmarket.phtml?type=portfolio')
        expands = self.page.locator('img[id]')
        if not expands.count():
            logger.info("No stocks to sell, skipping")
            return
        for e in expands.all():
            if 'disclosure' in e.get_attribute('id'):
                e.click()
        table = self.page.locator('#postForm')
        companies = table.locator('tr[id]')
        flag_sold = False
        for com in companies.all():
            for row in com.locator('tr').all()[1:]:
                cells = row.locator('td')
                code  = cells.nth(1).text_content()
                ratio = str2int(cells.nth(-2).text_content()) / 100.0
                if ratio < max(0, int(self.config.StockMarket_SellProfitRatio)):
                    continue
                logger.info(f'Selling {code} with {ratio:.2f} profit')
                shares = str2int(cells.nth(0).text_content())
                cells.nth(-1).locator('input').fill(str(shares))
                flag_sold = True
        if flag_sold:
            self.device.click('input[value="Sell Shares"]')

    def process_buys(self):
        self.goto('https://www.neopets.com/stockmarket.phtml?type=buy')
        bar = self.page.locator('center > div > marquee')
        candidates_bull = {}
        candidates_bear = {}
        price_range = range(15, 16) # only buy 15
        for p in price_range:
            candidates_bull[p] = set()
            candidates_bear[p] = set()
        msg = "Market status:\n"
        for cc in bar.locator('a').all():
            code,price,delta = str(cc.text_content()).split()
            price = str2int(price)
            delta = str2int(delta)
            msg  += f"{code} {price} {'+' if delta >= 0 else ''}{delta}\n"
            if delta < 0:
                if price in candidates_bear:
                    candidates_bear[price].add(code)
            else:
                if price in candidates_bull:
                    candidates_bull[price].add(code)
        logger.info(msg)
        quota = 1000
        inv_table = {}
        for p in price_range:
            if not candidates_bull[p]:
                continue
            if quota <= 0:
                break
            cn = len(candidates_bull[p])
            buys = 1000 // cn
            for c in candidates_bull[p]:
                inv_table[c] = buys
                quota -= buys
        if quota > 10:
            for p in price_range:
                if not candidates_bear[p]:
                    continue
                if quota <= 0:
                    break
                cn = len(candidates_bear[p])
                buys = quota // cn
                for c in candidates_bear[p]:
                    inv_table[c] = buys
                    quota -= buys
                if quota <= 0:
                    break
        if not inv_table.keys():
            logger.info("No good stocks to buy, skipping")
            return False
        inv_table[list(inv_table.keys())[0]] += quota
        logger.info(f'Buying shares: {inv_table}')
        for code, buys in inv_table.items():
            inps = self.page.locator('input[type=text]')
            inps.nth(1).fill(code)
            inps.nth(2).fill(str(buys))
            self.device.click('input[value="Buy Shares"]')
            self.goto('https://www.neopets.com/stockmarket.phtml?type=buy')
        return True

if __name__ == '__main__':
    self = StockMarketUI()
