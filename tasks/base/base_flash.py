import time
import numpy as np
from module.logger import logger
from module.device.device import Device
from module.base.button import ButtonWrapper
from module.base.utils import random_rectangle_point
from random import randint
from playwright.sync_api import Page, Locator
from module.exception import *
from typing import Union

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

    def screenshot(self, target:Locator=None):
        return self.device.screenshot(target or self.find_flash())

    def playable_count(self):
        try:
            played = int(self.page.locator('.sent-cont').text_content().split()[-1].split('/')[0])
            self.played_times = played
            logger.info(f"Played times: {played}")
            return self.max_plays - played
        except Exception as err:
            logger.exception(f"Error getting playable count: {err}")
            return 0

    def play_game(self):
        self.device.click('.play-text', nav=True)

    def hover(self, x, y, random_x=(-10, 10), random_y=(-10, 10)):
        return self.device.hover(self.find_flash(), x, y, random_x, random_y)

    def press(self, key, delay=100, rand_delay=True):
        if rand_delay:
            delay += randint(-20, 50)
        return self.find_flash().press(key, delay=delay)

    def play(self, start_button:ButtonWrapper, timeout:int=60):
        times = self.playable_count()
        if times <= 0:
            logger.info("No more plays left.")
            return True
        self.play_game()
        while self.find_flash().count() == 0:
            logger.info("Waiting for ruffle/flash to load...")
            self.device.wait(1)
        self.device.scroll_to(0, 100)
        if not self.wait_until_game_loaded(start_button, timeout):
            logger.warning("Game did not load in time, assume unplayable.")
            return False
        try:
            while times > 0:
                self.start_game()
                times -= 1
        except Exception as e:
            logger.error(f"Error during game play: {e}")
            return False
        return True

    def wait_until_game_loaded(self, start_button:ButtonWrapper, timeout:int=60):
        curt = time.time()
        while True:
            if time.time() - curt > timeout:
                logger.warning("Game did not load in time.")
                return False
            time.sleep(1)
            self.screenshot()
            if start_button.match_template(self.device.image):
                logger.info("Game loaded.")
                return True

    def wait_for_button(self, button:ButtonWrapper, timeout:int=60, similarity:float=0.8):
        curt = time.time()
        while True:
            self.screenshot()
            if time.time() - curt > timeout:
                logger.warning(f"Button#{button.name} not found in time.")
                return False
            if button.match_template(self.device.image, similarity):
                logger.info(f"Button#{button.name} found.")
                return True

    def start_game(self):
        raise NotImplementedError("start_game method not implemented")

    def click(self, target:Union[ButtonWrapper, tuple[int,int]],
              mright=False, modifiers=[],
              random_x=(-10, 10), random_y=(-10, 10),
              debug=False, wait=True):
        """
        Clicks a button on the flash game.

        FYI: https://playwright.dev/python/docs/api/class-locator#locator-click

        Args:
            target (ButtonWrapper|tuple[int,int]): The target to click, either a button or a coordinate tuple.
            mright (bool): If True, click with right mouse button.
            modifiers (list): List of modifiers to apply.
            random_x (tuple): Random offset for x coordinate.
            random_y (tuple): Random offset for y coordinate.
            debug (bool): If True, draw a debug point on the clicked position.
            wait (bool): If True, wait for target button available before clicking.
        """
        if isinstance(target, ButtonWrapper):
            if wait:
                self.wait_for_button(target)
            x1, y1, x2, y2 = target.area
            mx = (x1 + x2) // 2
            my = (y1 + y2) // 2
            logger.info(f"Clicking on button: {target.name} at ({mx}, {my})")
        else:
            mx, my = target
            logger.info(f"Clicking at coordinates: ({mx}, {my})")
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

    def drag_to(self,
            src:tuple[int,int],
            dst:tuple[int,int],
            point_random: tuple[int] = (-10, -10, 10, 10)
        ):
        p1 = np.array(src) - random_rectangle_point(point_random)
        p2 = np.array(dst) - random_rectangle_point(point_random)
        logger.info(f"Dragging from {p1} to {p2}")
        return self.find_flash().drag_to(
            self.find_flash(),
            source_position={'x': int(p1[0]), 'y': int(p1[1])},
            target_position={'x': int(p2[0]), 'y': int(p2[1])}
        )

