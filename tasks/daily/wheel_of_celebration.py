from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.config.utils import localt2nst, nst2localt
from datetime import datetime


class WheelOfCelebrationUI(BasePageUI):

    def main(self):
        curt = localt2nst(datetime.now())
        if curt.month != 11 or curt.day > 22:
            logger.info("Anniversary event is over")
            self.config.task_cancel()
            return True
        self.goto('https://www.neopets.com/np26birthday/')
        btn = self.device.wait_for_element('#wheelButtonSpin', '#watchAdButtonContainer')
        if btn.get_attribute('id') == 'watchAdButtonContainer':
            logger.info("Already played today")
            return True
        self.device.click('#wheelButtonSpin')
        logger.info("Clicked spin button, waiting for result")
        while True:
            self.device.wait(1)
            result = self.page.locator('#clickToShowPrize')
            if not result.count() or not result.is_visible():
                continue
            if 'click on the wheel' in result.first.text_content():
                break
        self.device.click('#wheelCanvas')
        return True

if __name__ == '__main__':
    self = WheelOfCelebrationUI()
