from module.logger import logger
from tasks.base.base_page import BasePageUI

class AnchorManagementUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/pirates/anchormanagement.phtml')

if __name__ == '__main__':
    self = AnchorManagementUI()
