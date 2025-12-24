from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.config.utils import localt2nst
from datetime import datetime

class AdventCalendarUI(BasePageUI):

    def main(self):
        curt = localt2nst(datetime.now())
        if curt.month != 12:
            logger.info("Not December, skip")
            self.config.task_cancel()
            return False
        self.goto('https://www.neopets.com/winter/adventcalendar.phtml')
        timer = 0
        logger.info("Waiting 10 seconds to see if has prize popup")
        while timer < 10:
            popup_prize = self.page.locator('#advent2021SQRaisha')
            if not popup_prize.count():
                break
            if popup_prize.is_visible():
                self.device.click(popup_prize)
                btn = self.device.wait_for_element('#bonusPrizeButton')
                self.device.click(btn)
                break
            self.device.wait(1)
            timer += 1
        btn = self.page.locator('button[type="submit"]', has_text="View Today's Prize")
        if btn.count() and btn.is_visible():
            logger.info("Already claimed today's prize.")
            return True
        btn = self.page.locator('button[type="submit"]', has_text="Collect My Prize")
        self.device.click(btn)
        return True

if __name__ == '__main__':
    self = AdventCalendarUI()
