from module.logger import logger
from tasks.base.base_page import BasePageUI

class AltadorCouncilUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/altador/council.phtml')
        node = self.page.locator('tr > td > p > map > area')
        if not node.count():
            logger.warning('You must complete the Altador Plot first to enter the council.')
            return
        self.goto(node.first.get_attribute('href'))
        self.device.click('input[type=submit]')

if __name__ == '__main__':
    self = AltadorCouncilUI()
