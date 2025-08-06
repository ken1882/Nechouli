from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.config.utils import localt2nst, nst2localt
from datetime import datetime, timedelta
from random import randint

class SnowagerUI(BasePageUI):

    def main(self):
        self.ranges = (
            range(6, 7),
            range(14, 15),
            range(22, 23),
        )
        curt = localt2nst(datetime.now())
        if not self.is_hibernate() and not any(curt.hour in r for r in self.ranges):
            logger.info("Snowager is awake, will try again later")
            return False
        self.goto("https://www.neopets.com/winter/snowager.phtml")
        btn = self.page.locator('#process_snowager > button')
        if not btn.count():
            logger.info("Awake or already claimed today, skip")
            return False
        self.device.click(btn)
        return True

    def is_hibernate(self):
        curt = localt2nst(datetime.now())
        return (curt.month == 12) or (curt.month == 1 and curt.day <= 3)

    def calc_next_run(self, s='daily'):
        if s == 'daily':
            return super().calc_next_run()
        future = localt2nst(datetime.now())
        candidates = []
        for r in self.ranges:
            candidate = future.replace(hour=r.start, minute=0, second=0)
            # If we're already past or inside the awake window, push to next day.
            if candidate <= future:
                candidate += timedelta(days=1)
            candidates.append(candidate)
        future = min(candidates)
        r = nst2localt(future)
        next_run = datetime(r.year, r.month, r.day, r.hour, 0, randint(9, 59))
        self.config.task_delay(target=next_run)

if __name__ == '__main__':
    self = SnowagerUI()
