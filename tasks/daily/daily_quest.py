from module.logger import logger
from tasks.base.base_page import BasePageUI
from urllib.parse import urljoin

class DailyQuestUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/questlog/')
        return True

if __name__ == '__main__':
    self = DailyQuestUI()
