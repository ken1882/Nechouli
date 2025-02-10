import asyncio
import numpy as np
from module.base.button import ClickButton
from module.base import utils
from cached_property import cached_property
from module.base.timer import Timer
from module.logger import logger
from module.config.config import AzurLaneConfig
from module.device.connection import Connection

class Control(Connection):

    def handle_control_check(self, button):
        # Will be overridden in Device
        pass

    @cached_property
    def click_methods(self):
        return {}

    def click(self, button, control_check=True):
        """Method to click a button.

        Args:
            button (button.Button): AzurLane Button instance.
            control_check (bool):
        """
        if control_check:
            self.handle_control_check(button)
        x, y = utils.random_rectangle_point(button.button)
        x, y = utils.ensure_int(x, y)
        logger.info(
            'Click %s @ %s' % (utils.point2str(x, y), button)
        )
        method = self.click_methods.get(
            self.config.Emulator_ControlMethod,
            self.click_adb
        )
        method(x, y)

    def multi_click(self, button, n, interval=(0.1, 0.2)):
        self.handle_control_check(button)
        click_timer = Timer(0.1)
        for _ in range(n):
            remain = utils.ensure_time(interval) - click_timer.current()
            if remain > 0:
                self.sleep(remain)
            click_timer.reset()

            self.click(button, control_check=False)

    def long_click(self, button, duration=(1, 1.2)):
        """Method to long click a button.

        Args:
            button (button.Button): AzurLane Button instance.
            duration(int, float, tuple):
        """
        self.handle_control_check(button)
        x, y = utils.random_rectangle_point(button.button)
        x, y = utils.ensure_int(x, y)
        duration = utils.ensure_time(duration)
        logger.info(
            'Click %s @ %s, %s' % (utils.point2str(x, y), button, duration)
        )


    def swipe(self, p1, p2, duration=(0.1, 0.2), name='SWIPE', distance_check=True):
        self.handle_control_check(name)
        p1, p2 = utils.ensure_int(p1, p2)
        duration = utils.ensure_time(duration)
        # ADB needs to be slow, or swipe doesn't work
        duration *= 2.5
        logger.info('Swipe %s -> %s, %s' % (utils.point2str(*p1), utils.point2str(*p2), duration))

        if distance_check:
            if np.linalg.norm(np.subtract(p1, p2)) < 10:
                # Should swipe a certain distance, otherwise AL will treat it as click.
                # uiautomator2 should >= 6px, minitouch should >= 5px
                logger.info('Swipe distance < 10px, dropped')
                return


    def swipe_vector(self, vector, box=(123, 159, 1175, 628), random_range=(0, 0, 0, 0), padding=15,
                     duration=(0.1, 0.2), whitelist_area=None, blacklist_area=None, name='SWIPE', distance_check=True):
        """Method to swipe.

        Args:
            box (tuple): Swipe in box (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y).
            vector (tuple): (x, y).
            random_range (tuple): (x_min, y_min, x_max, y_max).
            padding (int):
            duration (int, float, tuple):
            whitelist_area: (list[tuple[int]]):
                A list of area that safe to click. Swipe path will end there.
            blacklist_area: (list[tuple[int]]):
                If none of the whitelist_area satisfies current vector, blacklist_area will be used.
                Delete random path that ends in any blacklist_area.
            name (str): Swipe name
            distance_check: (bool):
        """
        p1, p2 = utils.random_rectangle_vector_opted(
            vector,
            box=box,
            random_range=random_range,
            padding=padding,
            whitelist_area=whitelist_area,
            blacklist_area=blacklist_area
        )
        self.swipe(p1, p2, duration=duration, name=name, distance_check=distance_check)

    def drag(self, p1, p2, segments=1, shake=(0, 15), point_random=(-10, -10, 10, 10), shake_random=(-5, -5, 5, 5),
             swipe_duration=0.25, shake_duration=0.1, name='DRAG'):
        self.handle_control_check(name)
        p1, p2 = utils.ensure_int(p1, p2)
        logger.info(
            'Drag %s -> %s' % (utils.point2str(*p1), utils.point2str(*p2))
        )
        self.click(ClickButton(area=utils.area_offset(point_random, p2), name=name))
