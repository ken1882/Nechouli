from module.logger import logger
from tasks.base.base_page import BasePageUI

class DesertedTombUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/worlds/geraptiku/tomb.phtml')
        if self.is_new_account():
            return True
        self.device.click('input[value="Open the door..."]', nav=True)
        self.device.click('input[value="Continue on..."]', nav=True)
        return True

if __name__ == '__main__':
    self = DesertedTombUI()
