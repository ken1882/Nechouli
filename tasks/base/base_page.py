import os
from module.base.base import ModuleBase
from module.base.utils import str2int
from module.logger import logger
from datetime import datetime, timedelta
from time import sleep
from playwright.sync_api import sync_playwright, Page
from playwright._impl._errors import TimeoutError
from module.config.utils import get_server_next_update
from module.exception import *
from playwright._impl._errors import Error as PlaywrightError

class BasePageUI(ModuleBase):

    @property
    def page(self) -> Page:
        return self.device.page

    def run(self):
        try:
            ok = self.main()
            self.dm.save()
            stime = self.config.ProfileSettings_TaskSoftTerminationTime
            logger.info(f"Task finished, soft sleep for {stime} seconds.")
            self.device.sleep(stime)
            if ok:
                self.calc_next_run()
            elif ok == False:
                self.calc_next_run('failed')
        except TimeoutError as e:
            self.device.respawn_page()
            logger.exception(e)
            self.calc_next_run('failed')
        except PlaywrightError as e:
            logger.error(f"Playwright error:")
            logger.exception(e)
            logger.error("Nechouli will skip this task, if this keeps happening, please report to dev.")
            self.device.respawn_page()
            return self.calc_next_run('failed')
        except Exception as e:
            raise e

    def main(self):
        pass

    def calc_next_run(self, s='daily'):
        now = datetime.now()
        future = now
        logger.info(f"Calculating next run time, preset: {s}")
        if not s or s == 'None':
            return
        elif s == 'now':
            pass
        elif s == 'failed':
            return self.on_failed_delay()
        elif s == 'daily':
            return self.config.task_delay(server_update=True)
        elif s == 'monthly':
            future = get_server_next_update('00:00')
            if future.month == now.month:
                future = future + timedelta(days=31)
                future = future.replace(day=1)
        else:
            logger.warning(f'Unknown delay preset: {s}')
        self.config.task_delay(target=future)

    def on_failed_delay(self):
        future = datetime.now() + timedelta(hours=1)
        self.config.task_delay(target=future)
        return future

    def is_logged_in(self):
        if '/login/index.phtml' in self.device.page.url:
            return False
        if 'you are not logged in' in self.device.page.content():
            return False
        if 'id="loginButton"' in self.device.page.content():
            return False
        return True

    def goto(self, url):
        try:
            self.device.goto(url)
        except TimeoutError:
            logger.warning("Page load timeout, assume main content loaded.")
        except PlaywrightError as e:
            logger.warning(f"Page load error: {e}, likely interrupted by login or maintenance. Retrying")
            self.device.wait(1)
            self.page.reload()
            return self.goto(url)
        if not self.is_logged_in():
            logger.critical("You have to login first, launch with gui then navigate to https://www.neopets.com/home after you logged in.")
            while True:
                try:
                    ok = self.device.wait_for_element('#navPetMenuIcon__2020', timeout=60*60)
                    if not ok:
                        raise RequestHumanTakeover("No operation for 1 hour, exited.")
                    break
                except PlaywrightError as e:
                    if 'navigation' in str(e):
                        logger.info("Page navigation interrupted, retrying...")
                        continue
            self.goto('https://www.neopets.com/questlog/') # quest won't start if not visited
            return self.goto(url)
        try:
            self.execute_script('remove_antiadb') # Remove annoying popup showing adblock detected
        except PlaywrightError:
            pass

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

    def reload(self):
        return self.goto(self.page.url)

    def is_node_loading(self, node):
        if 'Loading...' in node.inner_text():
            return True
        return False

    def update_np(self) -> int:
        node = self.page.locator('#npanchor')
        if not node.count():
            return self.config.stored.InventoryData.np or 0
        np = str2int(node.first.text_content()) or 0
        self.config.stored.InventoryData.np = np
        return np
