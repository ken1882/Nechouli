from module.logger import logger
from tasks.base.base_page import BasePageUI

class GiantJellyUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/jelly/jelly.phtml')
        self.device.click('input[value="Grab some Jelly"]', nav=True)
        return True

if __name__ == '__main__':
    self = GiantJellyUI()
