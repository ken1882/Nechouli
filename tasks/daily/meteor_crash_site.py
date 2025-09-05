from module.logger import logger
from tasks.base.base_page import BasePageUI

class MeteorCrashSiteUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/moon/meteor.phtml')
        btn = self.page.locator('input[value="Take a chance"]')
        if not btn.count():
            logger.info("Seems meteor reward gained today")
            return True
        self.device.click(btn, nav=True)
        select = self.page.locator('select[name="pickstep"]')
        if not select.count():
            logger.info("Seems meteor reward gained today")
            return True
        select.select_option(value='1')
        self.device.click('input[name="meteorsubmit"]', nav=True)
        content = self.page.content().lower()
        if any([s in content for s in ['try again later', 'gone']]):
            logger.info("Gained nothing, will try again next hour")
            return False
        return True

    def on_failed_delay(self):
        return super().on_failed_delay()

if __name__ == '__main__':
    self = MeteorCrashSiteUI()
