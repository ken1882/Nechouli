import os
from module.base.base import ModuleBase
from module.logger import logger
from datetime import datetime, timedelta
from time import sleep
from playwright.sync_api import sync_playwright, Page
from playwright._impl._errors import TimeoutError, Error
from cached_property import cached_property
from module.config.utils import get_server_next_update
from module.exception import *

class BasePageUI(ModuleBase):

    @cached_property
    def page(self) -> Page:
        return self.device.page

    def check_connection(self):
        if not self.device.pw:
            self.device.start_browser()
        return True

    def run(self):
        self.check_connection()
        try:
            ok = self.main()
            self.dm.save()
            logger.info("Task finished, soft sleep for 5 seconds.")
            self.device.sleep(5)
            if ok:
                self.calc_next_run()
            else:
                self.calc_next_run('failed')
        except Exception as e:
            raise e

    def main(self):
        pass

    def calc_next_run(self, s='daily'):
        now = datetime.now()
        future = now
        if s == 'now':
            pass
        elif s == 'failed':
            return self.on_failed_delay()
        elif s == 'daily':
            return self.config.task_delay(server_update=True)
        elif s == 'monthly':
            future = get_server_next_update('00:00')
            if future.month != now.month:
                return future
            future = future + timedelta(days=31)
            future = future.replace(day=1)
        else:
            logger.warning(f'Unknown delay preset: {s}')
        self.config.task_delay(target=future)
        return future

    def on_failed_delay(self):
        future = datetime.now() + timedelta(hours=1)
        self.config.task_delay(target=future)
        return future

    def is_logged_in(self):
        if '/login/index.phtml' in self.device.page.url:
            return True
        if 'you are not logged in' in self.device.page.content():
            return True
        return False

    def goto(self, url):
        try:
            self.device.goto(url)
        except TimeoutError:
            logger.warning("Page load timeout, assume main content loaded.")
        except Error as e:
            logger.warning(f"Page load error: {e}, likely interrupted by login or maintenance.")
        if '/login/index.phtml' in self.device.page.url:
            logger.critical("You have to login first, launch with gui then navigate to https://www.neopets.com/home after you logged in.")
            ok = self.device.wait_until_element_found('#navPetMenuIcon__2020', timeout=60*60)
            if not ok:
                raise RequestHumanTakeover("No operation for 1 hour, exited.")
            return self.goto(url)

    def execute_script(self, script_name):
        path = os.path.join('tasks', 'scripts', f'{script_name}.js')
        if not os.path.exists(path):
            logger.error(f"Script {script_name} not found at {path}.")
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            result = self.page.evaluate(script_content)
            logger.info(f"Script {script_name} executed successfully.")
            return result
        except Exception as e:
            logger.exception(f"Failed to execute script {script_name}: {e}")
            return