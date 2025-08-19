import os, sys
import time
import json
import re
from copy import deepcopy
from random import random
from functools import wraps
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from module.config.config import AzurLaneConfig
from module.logger import logger
from module.base.utils import ensure_time, str2int, check_connection, get_start_menu_programs
import subprocess

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
    page: Page

    PROFILE_DIRECTORY = os.path.realpath(os.path.join(os.getcwd(), './profiles'))

    def __init__(self, config):
        self.config = config
        self.pw = None
        self.browser = None
        self.url = ""
        self.page = None

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
                try:
                    versions = os.listdir(path)
                    versions = [v for v in versions if 'manifest.json' in os.listdir(os.path.join(path, v))]
                    if not versions:
                        continue
                    latest = max(versions, key=lambda x: str2int(x))
                except Exception as e:
                    logger.warning(f"Error finding latest version in {path}: {e}")
                    continue
                path = os.path.join(path, latest)
            if not os.path.exists(os.path.join(path, 'manifest.json')):
                logger.warning(f"Manifest file not found in {path}")
                continue
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
            'locale': 'en-US'
        }
        if self.config.Playwright_AutoOpenDevtools:
            kwargs['args'].append('--auto-open-devtools-for-tabs')
        if self.config.Playwright_CustomUserAgent:
            kwargs['user_agent'] = self.config.Playwright_CustomUserAgent
        if not self.config.Playwright_UseDefaultProfile:
            kwargs['args'].extend(self.get_extension_paths())

        if self.config.Playwright_LaunchDedicatedBrowser:
            self.context = self.pw.chromium.launch_persistent_context(
                os.path.join(self.PROFILE_DIRECTORY, self.config.config_name),
                **kwargs
            )
            time.sleep(1)  # Give some time for the browser to start
            self.page = self.context.pages[0] if self.context.pages else self.new_page()
            self.page.goto("about:blank")
        else:
            address = self.config.Playwright_RemoteDebuggingAddress
            if not check_connection(address):
                port = address.split(':')[-1]
                logger.warning(f"Remote debugging address {address} is not reachable, try start manually")

                channel = self.config.Playwright_Browser
                profile_dir = os.path.join(self.PROFILE_DIRECTORY, self.config.config_name)

                extra_args = kwargs.get('args', []).copy()
                extra_args.append(f"--remote-debugging-port={port}")

                if not self.config.Playwright_UseDefaultProfile:
                    extra_args.append(f"--user-data-dir={profile_dir}")
                if self.config.Playwright_Headless:
                    extra_args.append('--headless=new')

                executable_path = ''
                if channel == 'msedge':
                    p = get_start_menu_programs('edge')
                    if not p:
                        raise ValueError("Microsoft Edge executable not found in your start menu")
                    executable_path = p[0]
                elif channel == 'chrome':
                    executable_path = self.pw.chromium.executable_path

                if not executable_path:
                    raise ValueError(f"Executable not found for browser channel: {channel}")

                cmd = [executable_path] + extra_args
                logger.info(f"Starting browser manually: {' '.join(cmd)}")
                subprocess.Popen(cmd)
                logger.info("Waiting 10 seconds for browser to start")
                time.sleep(10)

            self.browser = self.pw.chromium.connect_over_cdp(f"http://{address}")

            if self.config.Playwright_Headless:
                old_context = self.browser.contexts[0]
                self.context = self.browser.new_context(
                    user_agent=kwargs.get('user_agent', ''),
                    locale=kwargs.get('locale', 'en-US'),
                    viewport={'width': 1280, 'height': 800},
                    ignore_https_errors=True,
                    storage_state=old_context.storage_state()
                )
            else:
                self.context = self.browser.contexts[0]

            self.context.add_cookies([{
                "name": "lang",
                "value": "en",
                "domain": "www.neopets.com",
                "path": "/",
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax"
            }, {
                "name": "lang",
                "value": "en",
                "domain": ".neopets.com",
                "path": "/",
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax"
            }])

            if self.config.Playwright_UseDefaultProfile:
                self.page = self.new_page()
            else:
                self.page = self.context.pages[0] if self.context.pages else self.new_page()
            self.page.goto("about:blank")
        logger.info("Browser started.")

    def clean_redundant_pages(self, keeps:int=3):
        for p in self.context.pages:
            if p == self.page:
                continue
            p.close()
        for _ in range(keeps - 1):
            self.new_page()

    def goto(self, url, page=None):
        if page is None:
            page = self.page
        logger.info(f"Navigating to {url}")
        page.goto(url)

    def respawn_page(self):
        logger.info("Respawning page")
        if self.page:
            self.page.close()
        self.page = self.new_page()
        self.page.goto('https://www.neopets.com/questlog/')

    def new_page(self):
        page = self.context.new_page()
        if self.config.Playwright_AutoAcceptDialog:
            page.on('dialog', lambda dialog: dialog.accept())
        return page
