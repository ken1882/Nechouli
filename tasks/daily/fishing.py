from module.logger import logger
from tasks.base.base_page import BasePageUI

class FishingUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/water/fishing.phtml')
        self.device.scroll_to(0, 100)
        self.device.click('input[value="Reel In Your Line"]', nav=True)
        return True

if __name__ == '__main__':
    self = FishingUI()
