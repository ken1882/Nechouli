from module.logger import logger
from tasks.base.base_page import BasePageUI

class BankInterestUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/bank.phtml')
        self.device.click('#frmCollectInterest')


if __name__ == '__main__':
    self = BankInterestUI()
