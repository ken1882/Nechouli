from module.logger import logger
from tasks.base.base_page import BasePageUI

class AppleBobbingUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/halloween/applebobbing.phtml')
        self.device.click('#bob_button', nav=True)

if __name__ == '__main__':
    self = AppleBobbingUI()
