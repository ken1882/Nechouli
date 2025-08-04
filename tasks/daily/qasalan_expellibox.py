from module.logger import logger
from tasks.base.base_page import BasePageUI
from datetime import datetime, timedelta
from urllib.parse import parse_qs, unquote_plus

class QasalanExpelliboxUI(BasePageUI):

    def main(self):
        self.goto('https://ncmall.neopets.com/games/giveaway/process_giveaway.phtml')
        result_text = self.page.locator('body').text_content()
        logger.info(f"Result:\n{unquote_plus(parse_qs(result_text)['msg'][0])}")
        return True

    def calc_next_run(self, *args):
        now = datetime.now()
        # technically can play every 7 hours 7 minutes,
        # but adds extra 3 minutes for sanity
        future = now + timedelta(hours=7, minutes=10)
        self.config.task_delay(target=future)
        return future

if __name__ == '__main__':
    self = QasalanExpelliboxUI()
