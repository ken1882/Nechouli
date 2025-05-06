from module.logger import logger
from tasks.base.base_page import BasePageUI

class FruitMachineUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/desert/fruitmachine.phtml')
        self.device.click('input[value="Spin, spin, spin!"]', nav=True)
        self.device.sleep(10)
        return True

if __name__ == '__main__':
    self = FruitMachineUI()
