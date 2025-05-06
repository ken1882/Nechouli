from module.logger import logger
from tasks.base.base_page import BasePageUI
from urllib.parse import urljoin

class AltadorCouncilUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/altador/council.phtml')
        node = self.device.page.locator('tr > td > p > map > area')
        self.goto(urljoin(self.page.url, node.first.get_attribute('href')))
        self.device.click('input[value="Collect your gift"]', nav=True)
        return True

if __name__ == '__main__':
    self = AltadorCouncilUI()
