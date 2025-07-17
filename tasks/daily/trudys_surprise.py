from module.logger import logger
from tasks.base.base_page import BasePageUI

class TrudysSurpriseUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/trudys_surprise.phtml')
        canvas = self.device.wait_for_element('#trudyContainer')
        if not canvas.count():
            logger.warning("Canvas not found")
            return
        self.dismiss_popup()
        self.device.scroll_to(0, 200)
        frame = self.page.locator("#frameTest")
        if not frame.count():
            logger.warning("Slot frame not found")
            return
        self.dismiss_popup()
        self.device.wait(2)
        self.device.click(frame, y_mul=0.85)
        logger.info("Clicked, wait for result")
        self.device.wait_for_element('#trudyPrizeTitle', timeout=30)
        return True

    def dismiss_popup(self):
        popup = self.page.locator('#TrudysNoPassPopup')
        if not popup.count() or not popup.is_visible():
            return
        popup.locator('.popup-exit').click()

if __name__ == '__main__':
    self = TrudysSurpriseUI()
