from module.logger import logger
from tasks.base.base_page import BasePageUI

class TrudysSurpriseUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/trudys_surprise.phtml')
        canvas = self.page.locator('#trudyContainer')
        if not canvas.count():
            logger.warning("Canvas not found")
            return
        self.device.scroll_to(0, 200)
        frame = self.page.locator("#frameTest")
        if not frame.count():
            logger.warning("Slot frame not found")
            return
        self.device.click(frame, y_mul=0.85)
        logger.info("Clicked, wait for result")
        self.device.wait_for_element('#trudyPrizeTitle', timeout=30)

if __name__ == '__main__':
    self = TrudysSurpriseUI()
