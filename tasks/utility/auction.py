from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.base.utils import str2int
from module import jelly_neo as jn
from module.db import data_manager as dm
from module.db.models.neoitem import NeoItem
from datetime import datetime

class AuctionUI(BasePageUI):

    @property
    def page(self):
        if not hasattr(self, '_page') or self._page is None:
            self._page = self.device.new_page()
        return self._page

    def run(self):
        self.config.Auction_IsRunningBackground = True
        super().run()

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

    def main(self):
        self.parse_config()
        while self.config.Auction_IsRunningBackground:
            self.update_bidded()

    def update_bidded(self):
        self.goto('https://www.neopets.com/auctions.phtml?type=leading')


if __name__ == '__main__':
    self = AuctionUI()
