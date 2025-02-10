from module.base.base import ModuleBase
from module.logger import logger
from datetime import datetime, timedelta
from time import sleep
from playwright.sync_api import sync_playwright

class BasePageUI(ModuleBase):

    def check_connection(self):
        if not self.device.pw:
            self.device.start_browser()
        return True

    def run(self):
        self.check_connection()
        try:
            self.main()
            self.calc_next_run_time()
        except Exception as e:
            logger.error(e)
        logger.info("Stopping task.")
        self.config.task_stop()

    def main(self):
        pass

    def calc_next_run_time(self):
        now = datetime.now()
        self.next_run = now + timedelta(days=1)
        return self.next_run
