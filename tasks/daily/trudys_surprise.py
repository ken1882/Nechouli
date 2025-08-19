from module.logger import logger
from tasks.base.base_page import BasePageUI
from tasks.daily.assets import assets_daily_trudys_surprise as assets

class TrudysSurpriseUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/trudys_surprise.phtml')
        canvas = self.device.wait_for_element('#trudyContainer')
        if not canvas.count():
            logger.warning("Canvas not found")
            return
        self.dismiss_popup()
        bb = canvas.bounding_box()
        self.device.scroll_to(0, bb['y']+100)
        frame = self.page.locator("#frameTest")
        if not frame.count():
            logger.warning("Slot frame not found")
            return
        self.dismiss_popup()
        depth = 0
        while True:
            if assets.play.match_template_luma(self.device.screenshot(), 0.6, direct_match=1):
                break
            elif assets.played.match_template_luma(self.device.screenshot(), 0.6, direct_match=1):
                logger.info("Already played today")
                return True
            self.device.wait(1)
            depth += 1
            if depth > 10:
                logger.warning("Failed to find play button")
                return False
        mx, my = assets.play.button_offset
        for i in range(5):
            dx = 50 + 10 * i
            dy = 20 + 10 * i
            self.device.click((int(mx+dx), int(my+dy)))
            self.device.wait(0.2)
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
