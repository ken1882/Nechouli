import time
from module.logger import logger
from module.device.device import Device
from module.base.button import ButtonWrapper
from random import randint
from playwright.sync_api import Page
from module.exception import *


class BaseFlash():
    # these properties will be in the inherited class (tasks)
    page: Page
    device: Device

    def __init__(self, *args, **kwargs):
        self.frame = '#game_frame'
        self.locator = 'ruffle-embed'
        self.max_plays = 3
        self.played_times = 3
        super().__init__(*args, **kwargs)

    def find_flash(self):
        if self.frame:
            return self.page.frame_locator(self.frame).locator(self.locator)
        return self.page.locator(self.locator)

    def playable_count(self):
        try:
            played = int(self.page.locator('.sent-cont').text_content().split()[-1].split('/')[0])
            self.played_times = played
            logger.info(f"Played times: {played}")
            return 3 - played
        except Exception as err:
            logger.exception(f"Error getting playable count: {err}")
            return 0

    def play_game(self):
        self.device.click('.play-text', nav=True)

    def click(self, x:int, y:int, button='left', modifiers=[], random_x=(-10, 10), random_y=(-10, 10), debug=False):
        dom = self.find_flash()
        if debug:
            bb = dom.bounding_box()
            cx = bb['x'] + x
            cy = bb['y'] + y
            self.device.draw_debug_point(self.page, cx, cy)
        return self.device.click(dom, x, y, button, modifiers, random_x, random_y)

    def hover(self, x, y, random_x=(-10, 10), random_y=(-10, 10)):
        return self.device.hover(self.find_flash(), x, y, random_x, random_y)

    def press(self, key, delay=100, rand_delay=True):
        if rand_delay:
            delay += randint(-20, 50)
        return self.find_flash().press(key, delay=delay)

    def play(self, start_button:ButtonWrapper, timeout:int=60):
        if self.playable_count() <= 0:
            logger.info("No more plays left.")
            return True
        while self.find_flash().count() == 0:
            logger.info("Waiting for ruffle/flash to load...")
            self.device.wait(1)
        if not self.wait_until_game_loaded(start_button, timeout):
            logger.warning("Game did not load in time, assume unplayable.")
            return False
        return self.start_game()

    def wait_until_game_loaded(self, start_button:ButtonWrapper, timeout:int=60):
        curt = time.time()
        while True:
            if time.time() - curt > timeout:
                logger.warning("Game did not load in time.")
                return False
            time.sleep(1)
            if start_button.match_template(self.device.image):
                logger.info("Game loaded.")
                return True

    def start_game(self):
        raise NotImplementedError("start_game method not implemented")

    def click(self, ui:ButtonWrapper,
              mright=False, modifiers=[],
              random_x=(-10, 10), random_y=(-10, 10), debug=False):
        """
        Clicks a button on the flash game.

        FYI: https://playwright.dev/python/docs/api/class-locator#locator-click

        Args:
            button (ButtonWrapper): The button to click.
            mright (bool): If True, click with right mouse button.
            modifiers (list): List of modifiers to apply.
            random_x (tuple): Random offset for x coordinate.
            random_y (tuple): Random offset for y coordinate.
            debug (bool): If True, draw a debug point on the clicked position.
        """
        x1, y1, x2, y2 = ui.area
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2
        mx = max(0, mx + randint(*random_x))
        my = max(0, my + randint(*random_y))
        canvas = self.find_flash()
        if debug:
            bb = canvas.bounding_box()
            self.device.draw_debug_point(mx+bb['x'], my+bb['y'])
        return canvas.click(
            button='left' if not mright else 'right',
            modifiers=modifiers,
            position={'x': mx, 'y': my}
        )
