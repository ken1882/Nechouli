from module.logger import logger
from tasks.base.base_page import BasePageUI

class TombolaUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/island/tombola.phtml')
        if self.is_new_account():
            return True
        btn = self.page.locator('input[value="Play Tombola!"]')
        if not btn.count():
            logger.info('Tombola is not available')
            return False
        self.device.click(btn, nav=True)
        return True

if __name__ == '__main__':
    self = TombolaUI()
