from module.logger import logger
from tasks.base.base_page import BasePageUI
from datetime import datetime, timedelta

class IglooGarageSaleUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/winter/igloo.phtml')
        return True

    def calc_next_run(self, *args):
        if self.config.stored.IgsPurchasedCount.is_full():
            return super().calc_next_run()
        self.config.task_delay(minute=10)

if __name__ == '__main__':
    self = IglooGarageSaleUI()
