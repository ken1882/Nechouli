from module.logger import logger
from tasks.base.base_page import BasePageUI
from datetime import datetime, timedelta

class AlmostAbandonedAtticUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/halloween/garage.phtml')
        return True

    def calc_next_run(self, *args):
        if self.config.stored.AaaPurchasedCount.is_full():
            return super().calc_next_run()
        future = datetime.now() + timedelta(minutes=7, seconds=15)
        self.config.task_delay(target=future)

if __name__ == '__main__':
    self = AlmostAbandonedAtticUI()
