from module.logger import logger
from tasks.base.base_page import BasePageUI

class RichSlorgUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/shop_of_offers.phtml?slorg_payout=yes')

if __name__ == '__main__':
    self = RichSlorgUI()
