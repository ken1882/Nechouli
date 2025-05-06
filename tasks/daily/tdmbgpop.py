from module.logger import logger
from tasks.base.base_page import BasePageUI

class TDMBGPOPUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/faerieland/tdmbgpop.phtml')
        self.device.click('input[value="Talk to the Plushie"]', nav=True)
        return True

if __name__ == '__main__':
    self = TDMBGPOPUI()
