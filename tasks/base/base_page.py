import os
from module.base.base import ModuleBase
from module.base.utils import str2int
from module.config.utils import deep_get
from module.logger import logger
from datetime import datetime, timedelta
from time import sleep
from playwright.sync_api import sync_playwright, Page
from playwright._impl._errors import TimeoutError
from module.config.utils import get_server_next_update
from module.exception import *
from playwright._impl._errors import Error as PlaywrightError
from module.device.device import Device
from threading import Thread

from dotenv import load_dotenv
load_dotenv()

class BasePageUI(ModuleBase):
    on_background: bool = False

    @property
    def page(self) -> Page:
        return self.device.page

    def run(self, **kwargs):
        self._kwargs = kwargs or {}
        self.task_name = self.config.task.command
        if deep_get(self.config.data, f'{self.task_name}.Scheduler.EnableBackground'):
            if self.config.Optimization_WhenTaskQueueEmpty == 'close_game':
                logger.critical("Cannot run background task when Optimization is set to `close game`")
                raise RequestHumanTakeover
            logger.info(f"Run task {self.task_name} in background mode")
            self.config.cross_set(f'{self.task_name}.Scheduler.IsRunningBackground', True)
            self.on_background = True
            Thread(target=self.run_background, daemon=True).start()
            self.config.task_cancel()
            return True
        try:
            ok = self.main()
            stime = self.config.ProfileSettings_TaskSoftTerminationTime
            logger.info(f"Task finished, soft sleep for {stime} seconds.")
            self.device.sleep(stime)
            if ok:
                self.calc_next_run()
            elif ok == False:
                self.calc_next_run('failed')
            self.page.unroute_all()
        except (TimeoutError, PlaywrightError, InvisibleElement) as e:
            logger.error(f"Playwright error:")
            logger.exception(e)
            logger.error("Nechouli will skip this task, if this keeps happening, please report to dev.")
            self.device.respawn_page()
            return self.calc_next_run('failed')
        except Exception as e:
            raise e
        finally:
            # sync cookies back to manual context
            if self.config.Playwright_Headless:
                self.debug_screenshot()
                self.device.browser.contexts[0].add_cookies(self.device.context.cookies())
        return True

    def update_background_status(self):
        self.config.load()
        return deep_get(self.config.data, f'{self.task_name}.Scheduler.IsRunningBackground', False)

    def run_background(self):
        self.device = Device(self.config) # playwright cannot share threads
        self.device.start_browser()
        ok = self.main()
        if ok:
            self.calc_next_run()
        elif ok == False:
            self.calc_next_run('failed')
        self.stop_background()
        logger.info(f"Background task {self.task_name} exited")

    def stop_background(self):
        self.config.cross_set(f'{self.task_name}.Scheduler.IsRunningBackground', False)
        self.config.task_enable()
        self.on_background = False
        self.page.close()
        self.device.stop()

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
            future = get_server_next_update('01:00')
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
        content = self.device.page.content().lower()
        if '/login/index.phtml' in self.device.page.url:
            return False
        if 'login to neopets' in content:
            return False
        if 'id="loginbutton"' in content:
            return False
        if 'forgot password?' in content:
            return False
        return True

    def is_new_account(self):
        if 'your account must' in self.device.page.content().lower():
            return True
        return False

    def goto(self, url, timeout=None):
        try:
            self.device.goto(url, self.page, timeout=timeout)
            while 'Maintenance Tunnels' in self.page.content():
                logger.warning("Site is under maintenance, waiting for 10 minutes before retrying...")
                self.device.sleep(600)
                self.page.reload()
            self.debug_screenshot()
        except TimeoutError:
            logger.warning("Page load timeout, retrying...")
            self.device.respawn_page()
            return self.device.goto(url, self.page, timeout=timeout)
        except PlaywrightError as e:
            logger.warning(f"Page load error: {e}, likely interrupted by login or maintenance. Retrying")
            self.device.respawn_page()
            return self.goto(url, timeout=timeout)
        if not self.is_logged_in():
            logger.info("Attempting neopass login")
            if self.login_neopass():
                return self.goto(url, timeout=timeout)
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
            # quest won't start if not visited
            self.goto('https://www.neopets.com/questlog/', timeout=timeout)
            return self.goto(url, timeout=timeout)
        try:
            # Remove annoying popups
            self.execute_script('remove_antiadb')
            self.execute_script('remove_popups')
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
            result = self.device.eval(script_content)
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
            return self.config.stored.NeoPoints.value or 0
        np = str2int(node.first.text_content()) or 0
        self.config.stored.NeoPoints.set(np)
        return np

    def debug_screenshot(self, fname=''):
        if not fname:
            fname = f"{self.config.config_name}_snapshot.png"
        path = os.path.join('config', fname)
        self.page.screenshot(path=path)

    def login_neopass(self):
        self.page.goto('https://www.neopets.com/login/')
        btn = self.device.wait_for_element('#neopass-method-login')
        self.device.click(btn)
        self.device.wait(1)
        self.device.click('.signin-btn', nav=True)
        if not self.is_logged_in():
            cred = os.getenv(f'NEOPASS_CRED_{self.config.config_name}')
            if not cred:
                raise RequestHumanTakeover("Neopass login failed: Missing credentials")
            email, *pwd = cred.split(':')
            logger.info(f"Login with {email}")
            pwd = ':'.join(pwd)
            e = self.page.locator('input[name="email"]')
            self.device.click(e)
            e.fill(email)
            p = self.page.locator('input[name="password"]')
            self.device.click(p)
            p.fill(pwd)
            btn = self.page.locator('button[type="submit"]', has_text='Sign In')
            self.device.click(btn, nav=True)
            self.device.wait(3)
        
        def _is_loaded():
            return self.page.locator('p', has_text='Main Account').count() > 0
        
        depth = 0
        while depth < 10:
            try:
                if _is_loaded():
                    break
            except Exception as e:
                pass
            depth += 1
            self.device.wait(1)
        else:
            return False
        self.device.click(self.page.locator('p', has_text='Main Account'))
        self.device.click(self.page.locator('button', has_text='Continue'), nav=True)
        return self.page.url.startswith('https://www.neopets.com')