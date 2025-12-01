from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.base.utils import str2int
from module import jelly_neo as jn
from module.db import data_manager as dm
from module.db.models.neoitem import NeoItem
from datetime import datetime, timedelta
from random import random

class AuctionUI(BasePageUI):

    def parse_config(self):
        self.targets = {}
        raw = self.config.Auction_BiddingConfig
        lines = [l.strip() for l in raw.splitlines() if not l.strip().startswith('#') and l.strip()]
        for line in lines:
            name, max_bid, count = line.split(':')
            self.targets[name] = {
                'max_bid': str2int(max_bid),
                'count': str2int(count)
            }

    def is_holding_bid(self):
        wfield = self.page.locator('b', has_text='When?').first
        tbody = wfield.locator('../../..')
        first_row = tbody.locator('tr').nth(1)
        logger.info("Bid status: %s", first_row.text_content().strip())
        my_username = self.page.locator('.user').first.text_content()
        my_username = my_username.split(',')[1].split('|')[0].strip()
        return my_username in first_row.text_content()

    def get_time_left(self) -> int:
        heading = self.page.locator('center').nth(1).text_content()[:40]
        if '> 24 hours' in heading:
            return 24*60
        elif '8-24 hours' in heading:
            return 8*60
        elif '2-8 hours' in heading:
            return 2*60
        elif '30 min-2 hours' in heading:
            return 30
        elif '< 30 min' in heading:
            return 1
        return 0

    def main(self):
        if not self.config.Auction_AuctionId:
            logger.warning("No Auction IDs configured, cancelling task.")
            self.config.task_cancel()
            return
        last_bidded = 0
        self.goto(f'https://www.neopets.com/auctions.phtml?type=bids&auction_id={self.config.Auction_AuctionId}')
        time_left = self.get_time_left()
        logger.info("Time left in auction: %d minutes", time_left)
        while time_left < 30:
            field = self.page.locator('input[name="amount"]')
            if field.count() == 0:
                logger.info("No bidding field found, auction may have ended.")
                self.config.task_cancel()
                return
            current_bid = str2int(field.get_attribute('value'))
            last_bidded = current_bid + 5000
            if last_bidded > self.config.Auction_Budget:
                logger.info("Reached budget limit, stopping bidding.")
                self.config.task_cancel()
                return
            logger.info("Placing bid of %d NP", last_bidded)
            field.fill(str(last_bidded))
            self.device.click('input[value="Place a Bid"]', nav=True)
            self.goto(f'https://www.neopets.com/auctions.phtml?type=bids&auction_id={self.config.Auction_AuctionId}')
            while self.is_holding_bid():
                self.goto(f'https://www.neopets.com/auctions.phtml?type=bids&auction_id={self.config.Auction_AuctionId}', timeout=5)
                time_left = self.get_time_left()
                self.device.wait(random()*3)
                if time_left == 0:
                    break
            if time_left == 0:
                self.config.task_cancel()
                logger.info("Auction ended, stopping bidding.")
                break
        self.config.task_delay(minute=max(15, time_left // 2))

    def update_bidded(self):
        self.goto('https://www.neopets.com/auctions.phtml?type=leading')

if __name__ == '__main__':
    self = AuctionUI()
