import os
import time
from functools import wraps
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from module.config.config import AzurLaneConfig
from module.logger import logger
from module.base.utils import ensure_time

def retry(func):
    @wraps(func)
    def retry_wrapper(self, *args, **kwargs):
        for attempt in range(3):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.warning(f"Retrying {func.__name__} due to {e} (Attempt {attempt + 1}/3)")
                time.sleep(2)
        raise Exception(f"Function {func.__name__} failed after 3 retries. (Caused by {e.message})")
    return retry_wrapper

class Connection:
    config: AzurLaneConfig
    pw: Playwright
    page: Page
    context: Browser

    PROFILE_DIRECTORY = os.path.realpath(os.path.join(os.getcwd(), './profiles'))

    def __init__(self, config):
        self.config = config
        self.pw = None
        self.browser = None
        self.page = None
        self.url = ""

    @staticmethod
    def sleep(second):
        """
        Args:
            second(int, float, tuple):
        """
        time.sleep(ensure_time(second))

    def start_browser(self):
        if self.pw is None:
            self.pw = sync_playwright().start()

        kwargs = {
            'handle_sigint': False,
            'color_scheme': 'dark',
            'channel': self.config.Playwright_Browser,
            'headless': self.config.Playwright_Headless,
            'args': self.config.Playwright_ExtraChromiumArgs.split('\n'),
        }
        if self.config.Playwright_AutoOpenDevtools:
            kwargs['args'].append('--auto-open-devtools-for-tabs')

        self.context = self.pw.chromium.launch_persistent_context(
            os.path.join(self.PROFILE_DIRECTORY, self.config.config_name),
            **kwargs
        )
        self.page = self.context.new_page()
        if self.config.Playwright_AutoAcceptDialog:
            self.page.on('dialog', lambda dialog: dialog.accept())
        logger.info("Browser started.")

    def goto(self, url, page=None):
        if page is None:
            page = self.page
        logger.info(f"Navigating to {url}")
        page.goto(url)
