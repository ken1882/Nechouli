from module.logger import logger
from tasks.base.base_page import BasePageUI

class QuickStockUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/quickstock.phtml')
        return True

if __name__ == '__main__':
    self = QuickStockUI()
