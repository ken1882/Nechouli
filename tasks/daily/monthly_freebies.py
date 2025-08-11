from module.logger import logger
from tasks.base.base_page import BasePageUI

class MonthlyFreebiesUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/freebies')
        return True

    def calc_next_run(self, s='monthly'):
        return super().calc_next_run(s)

if __name__ == '__main__':
    self = MonthlyFreebiesUI()
