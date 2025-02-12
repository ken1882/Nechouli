# copy-paste to python interactive shell to test
import os
from playwright.sync_api import sync_playwright
from collections import defaultdict
import importlib

FEED_BLACKLIST = [
    r"poison",
    r"rotten",
    r"dung",
    r"glowing",
    r"clay",
    r"smelly",
]

MAX_FEED_VALUE = 1000
MAX_FEED_LEVEL = 8 # full up

HUNGER_LEVEL_MAP = defaultdict(lambda: 10, {
    "dying": 0,
    "starving": 1,
    "famished": 2,
    "very hungry": 3,
    "hungry": 4,
    "not hungry": 5,
    "fine": 6,
    "satiated": 7,
    "full up": 8,
    "very full": 9,
    "bloated": 10,
    "very bloated": 11,
})

pw = sync_playwright().start()
context = pw.chromium.launch_persistent_context(
    os.path.join(os.path.realpath(os.path.join(os.getcwd(), './profiles')), 'nechouli'),
    **{
        'channel': 'msedge',
        'headless': False,
        'handle_sigint': False,
        'color_scheme': 'dark',
        'args': [
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars'
        ]
    }
)
page = context.new_page()
page.goto('https://www.google.com')
