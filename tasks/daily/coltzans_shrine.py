from module.logger import logger
from tasks.base.base_page import BasePageUI

class ColtzansShrineUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/desert/shrine.phtml')
        if self.is_new_account():
            return True
        self.device.click('input[value="Approach the Shrine"]', nav=True)
        return True

if __name__ == '__main__':
    self = ColtzansShrineUI()
