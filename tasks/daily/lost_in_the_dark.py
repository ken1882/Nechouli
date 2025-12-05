from module.logger import logger
from tasks.base.base_page import BasePageUI
from datetime import datetime, timedelta

class LostInTheDarkUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/games/lostinthedark/index.phtml')
        timer = datetime.now() + timedelta(minutes=5)
        while datetime.now() < timer:
            btn = self.page.locator('input[value="Return to Haunted Woods"]')
            if btn.count():
                logger.info("GG")
                break
            btn = self.page.locator('input[value="Enter at Your Own Risk!"]')
            if btn.count():
                self.device.click(btn, nav=True)
                continue
            btn = self.page.locator('input[value="Right"]')
            if btn.count():
                self.device.click(btn, nav=True)
                continue
        return True

if __name__ == '__main__':
    self = LostInTheDarkUI()
