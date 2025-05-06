from module.logger import logger
from tasks.base.base_page import BasePageUI

class GiantOmeletteUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/prehistoric/omelette.phtml')
        self.device.click('button[tabindex="0"]', nav=True)
        return True

if __name__ == '__main__':
    self = GiantOmeletteUI()
