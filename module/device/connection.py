import os
import time
import json
import re
from copy import deepcopy
from random import random
from functools import wraps
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from module.config.config import AzurLaneConfig
from module.logger import logger
from module.base.utils import ensure_time, str2int

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
    context: Browser
    _page: Page

    PROFILE_DIRECTORY = os.path.realpath(os.path.join(os.getcwd(), './profiles'))

    def __init__(self, config):
        self.config = config
        self.pw = None
        self.browser = None
        self.url = ""
        self._page = None

    @staticmethod
    def sleep(second):
        """
        Args:
            second(int, float, tuple):
        """
        time.sleep(ensure_time(second))

    @staticmethod
    def wait(second):
        """
        Wait for seconds plus randomized time, extra is around 0~20% of the given time.

        Args:
            second(int, float, tuple):
        """
        time.sleep(ensure_time(second) + max(random() / 2, second * random() / 5))

    @property
    def page(self) -> Page:
        return self._page

    @page.setter
    def page(self, page):
        self._page = page

    def expand_locale(self, path, key, locale):
        locale_path = os.path.join(path, '_locales', locale, 'messages.json')
        vocab = {}
        if not os.path.exists(locale_path):
            logger.warning(f"Locale file not found: {locale_path}")
            return key
        with open(locale_path, 'r') as f:
            vocab = json.load(f)
        r = re.match(r'__MSG_(\w+)__', key)
        if not r:
            logger.warning(f"Invalid manifest local key format: {key}")
            return key
        key = r.group(1)
        if key not in vocab or 'message' not in vocab[key]:
            logger.warning(f"Key not found in locale file: {key}")
            return key
        return vocab[key]['message']

    def get_extension_paths(self):
        ext_paths = []
        ext_dir = os.path.expandvars(self.config.Playwright_ExtensionDirectory)
        load_ext_names = self.config.Playwright_ExtensionNames.split('\n')
        for path in os.listdir(ext_dir):
            path = os.path.join(ext_dir, path).replace('\\', '/')
            version = str2int(path.split('/')[-1])
            if not version:
                versions = os.listdir(path)
                if not versions:
                    continue
                latest = max(versions, key=lambda x: str2int(x))
                path = os.path.join(path, latest)
            with open(os.path.join(path, 'manifest.json'), 'r') as f:
                manifest = json.load(f)
                ext_name = manifest['name']
                if ext_name.startswith('__MSG_'):
                    ext_name = self.expand_locale(path, ext_name, manifest['default_locale'])
                for name in deepcopy(load_ext_names):
                    if name.lower() not in ext_name.lower():
                        continue
                    logger.info(f"Loading extension: {ext_name} {manifest['version']}")
                    ext_paths.append(path)
                    load_ext_names.remove(name)
        if load_ext_names:
            logger.warning("Extensions not found:\n"+'\n'.join(load_ext_names))
        return [
            f"--load-extension={','.join(ext_paths)}",
            f"--disable-extensions-except={','.join(ext_paths)}",
        ]

    def start_browser(self):
        if self.pw is None:
            self.pw = sync_playwright().start()
        else:
            try:
                self.pw.stop()
            except Exception:
                pass

        kwargs = {
            'handle_sigint': False,
            'color_scheme': 'dark',
            'channel': self.config.Playwright_Browser,
            'headless': self.config.Playwright_Headless,
            'args': self.config.Playwright_ExtraChromiumArgs.split('\n'),
        }
        kwargs['args'].extend(self.get_extension_paths())
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
