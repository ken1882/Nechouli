from module.logger import logger
from tasks.base.base_page import BasePageUI

class AnchorManagementUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/pirates/anchormanagement.phtml')
        self.device.scroll_to(0, 50)
        self.device.click('#btn-fire', nav=True)

if __name__ == '__main__':
    self = AnchorManagementUI()
