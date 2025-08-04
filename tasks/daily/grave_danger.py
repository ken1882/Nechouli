from module.logger import logger
from tasks.base.base_page import BasePageUI
from datetime import datetime, timedelta

class GraveDangerUI(BasePageUI):

    def main(self):
        self.remaining_time = timedelta(hours=10) # max time required
        self.goto('https://www.neopets.com/halloween/gravedanger/index.phtml')
        self.device.scroll_to(0, 300)
        # check if already running
        if self.check_remaining_time():
            logger.info("Grave Danger is already running.")
            return True
        form = self.page.locator('form').filter(has_text='again')
        if form.count():
            self.device.click(form, nav=True)
        candidates = self.page.locator('div[id="gdSelection"] > div')
        if not candidates.count():
            logger.info("No petpet found, make sure petpet is equipped or is still running.")
            return True
        self.device.click(candidates.first, wait=1)
        self.device.click('div[id="gdSelection"] > button')
        btn = self.page.locator('button').filter(has_text='Yes')
        self.device.wait_for_element(btn)
        self.device.click(btn, nav=True)
        self.check_remaining_time()
        return True

    def check_remaining_time(self):
        self.device.wait(2) # wait for api response
        node = self.page.locator('#gdRemaining')
        if not node.count():
            return False
        remain_text = node.text_content().strip()
        digits = [int(s) for s in remain_text.split() if s.isdigit()]
        if len(digits) == 3:
            self.remaining_time = timedelta(hours=digits[0], minutes=digits[1], seconds=digits[2])
        elif len(digits) == 2:
            self.remaining_time = timedelta(minutes=digits[0], seconds=digits[1])
        else:
            self.remaining_time = timedelta(minutes=1)
        return True

    def calc_next_run(self, *args):
        now = datetime.now()
        future = now + self.remaining_time + timedelta(minutes=1)
        self.config.task_delay(target=future)
        logger.info(f"Next run scheduled at {future.strftime('%Y-%m-%d %H:%M:%S')}")
        return future

if __name__ == '__main__':
    self = GraveDangerUI()
