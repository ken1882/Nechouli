from module.logger import logger
from tasks.base.base_page import BasePageUI

class ForgottenShoreUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/pirates/forgottenshore.phtml')
        self.device.click('#shore_back')
        return True

if __name__ == '__main__':
    self = ForgottenShoreUI()
