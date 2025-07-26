import numpy as np
from typing import Callable
from random import randint
from module.exception import *
from module.base.button import ClickButton
from module.base import utils
from cached_property import cached_property
from module.base.timer import Timer
from module.logger import logger
from module.config.config import AzurLaneConfig
from module.device.connection import Connection, retry
from playwright.sync_api import Locator

class Control(Connection):

    def handle_control_check(self, button):
        # Will be overridden in Device
        pass

    @cached_property
    def click_methods(self):
        return {}

    def draw_debug_point(self, x, y, radius=5, timeout=3000):
        return self.page.evaluate(f"""
            const marker = document.createElement('div');
            marker.style.width = '{radius*2}px';
            marker.style.height = '{radius*2}px';
            marker.style.backgroundColor = 'red';
            marker.style.position = 'fixed';
            marker.style.top = '{y - radius}px';
            marker.style.left = '{x - radius}px';
            marker.style.borderRadius = '50%';
            marker.style.zIndex = '9999';
            document.body.appendChild(marker);
            setTimeout(() => marker.remove(), {timeout});
        """)

    def wait_for_element(self,
                         *locators:list,
                         timeout:float=60,
                         wait_interval:float=1,
                         condition:Callable=None,
                         gone:bool=False) -> Locator:
        '''
        Wait until one of the selectors is met given condition.

        Args:
            locators (list): List of locators to execute.
            timeout (float): Timeout in seconds.
            wait_interval (float): Interval to wait between each check.
            condition (Callable): Condition to check. If None, will check if the element is visible and found.
            gone (bool): If True, will wait until the element is invisible.

        Returns:
            Locator: The first locator that meets the condition.
        '''
        if not condition:
            if gone:
                condition = lambda x: x.count() > 0 and not x.is_visible()
            else:
                condition = lambda x: x.count() > 0 and x.is_visible()
        while timeout > 0:
            node = None
            for selector in locators:
                try:
                    node = self.page.locator(selector)
                except Exception as e:
                    pass
                if node and condition(node):
                    return node
            timeout -= wait_interval
            self.sleep(wait_interval)
        return False

    def scroll_to(self, x:int=0, y:int=0, loc:Locator=None):
        if loc:
            bb = loc.bounding_box()
            if not bb:
                raise InvisibleElement
            x += bb['x']
            y += bb['y']
        return self.page.evaluate(f"window.scrollTo({x}, {y})")

    def click(self,
            target,
            x_mul=0.5, y_mul=0.5, nth=0, point_random=(-10, -10, 10, 10),
            delay=50, random_delay=(-20, 20),
            button='left', modifiers=[], debug=False,
            nav=None, wait=0.03,
        ):
        '''
        Click on a target.

        Args:
            target: Target to click on. Can be a tuple of (x, y), a string of selector, or a Locator object.
            nth (int): Which element to click if there are multiple elements
            x_mul (float): Which portion of the element to click on the x-axis. 0.5 means center of its width.
            y_mul (float): Which portion of the element to click on the y-axis. 0.5 means center of its height.
            point_random (tuple[int]): Random range to click around the target.
            delay (int): Delay between mouse down and mouse up.
            random_delay (tuple): Random delay to add to the delay.
            button ('left' | 'right' | 'middle'): Which mouse button to click.
            modifiers (list): Keyboard modifiers to hold while clicking.
            debug (bool): Draw a red dot on the clicked point.
            nav (bool | str): Wait for navigation loaded (if True) or to given url after clicking.
            wait (float): Wait time after clicking before returning.

        References:
            https://playwright.dev/python/docs/api/class-locator#locator-click
            https://playwright.dev/python/docs/api/class-mouse
        '''
        x, y = 0, 0
        loc = None
        if type(target) is tuple:
            x, y = target
        if type(target) is str:
            loc = self.page.locator(target)
        if type(target) is Locator:
            loc = target
        if type(point_random) == int:
            point_random = (-point_random, -point_random, point_random, point_random)
        if type(random_delay) == int:
            random_delay = (-random_delay, random_delay)
        mx, my = utils.random_rectangle_point(point_random)
        md = delay + randint(*random_delay)
        if loc and loc.count():
            if nth < 0:
                nth = max(0, loc.count() - nth)
            loc = loc.nth(nth)
            bb = loc.bounding_box()
            if not bb:
                raise InvisibleElement
            else:
                x = bb['x']
                y = bb['y']
                mx += int(bb['width'] * x_mul)
                my += int(bb['height'] * y_mul)
        if debug:
            self.draw_debug_point(mx+x, my+y)
        if loc and loc.count():
            logger.info(f"Clicking on {target} at ({mx+x}, {my+y})")
            loc.click(
                button=button,
                modifiers=modifiers,
                position={'x': mx, 'y': my},
                delay=md
            )
        else:
            if modifiers:
                raise ValueError("`page.mouse` does not support modifiers")
            logger.info(f"Clicking on Page at ({mx+x}, {my+y})")
            self.page.mouse.click(max(mx+x, 0), max(my+y, 0), button=button, delay=md)
        if nav:
            logger.info("Waiting for navigation")
        if nav == True:
            self.page.wait_for_url('**')
        elif nav and type(nav) == str:
            self.page.wait_for_url(nav)
        if wait > 0:
            self.wait(wait)

    def drag_to(self,
            locator_a: Locator,
            locator_b: Locator,
            speed: int = 1000,
            shake: tuple[int] = (0, 15),
            point_random: tuple[int] = (-10, -10, 10, 10),
            shake_random: tuple[int] = (-5, -5, 5, 5),
            swipe_duration: float = 0.1,
            shake_duration: float = 0.03,
            random_duration: tuple[int] = (-50, 50)
        ):
        '''
        Drag an entity from a to b.

        Args:
            locator_a (Locator): The entity to drag.
            locator_b (Locator): The entity to drag to.
            speed (int): Speed of the drag.
            shake (tuple[int]): Shake range after the drag.
            point_random (tuple[int]): Random range to click around the target.
            shake_random (tuple[int]): Random range to shake the entity.
            swipe_duration (float): Duration of each swipe.
            shake_duration (float): Duration of each shake.
            random_duration (tuple[int]): Random range to add to the duration.
        '''
        locator_a.hover()
        self.page.mouse.down()
        ba = locator_a.bounding_box()
        bb = locator_b.bounding_box()
        ax = (ba['x'] + ba['width'] * 0.5)
        ay = (ba['y'] + ba['height'] * 0.5)
        bx = (bb['x'] + bb['width'] * 0.5)
        by = (bb['y'] + bb['height'] * 0.5)
        p1 = np.array((ax, ay)) - utils.random_rectangle_point(point_random)
        p2 = np.array((bx, by)) - utils.random_rectangle_point(point_random)
        distance = np.linalg.norm(p2 - p1)
        duration = distance / speed
        steps = max(2, int(duration / swipe_duration))
        path = [(x, y, swipe_duration) for x, y in utils.random_line_segments(p1, p2, n=steps, random_range=point_random)]
        path += [
            (*p2 + shake + utils.random_rectangle_point(shake_random), shake_duration),
            (*p2 - shake - utils.random_rectangle_point(shake_random), shake_duration),
            (*p2, shake_duration)
        ]
        path = [(int(x), int(y), round(d+randint(*random_duration)/1000.0, 3)) for x, y, d in path]
        for wp in path:
            self.page.mouse.move(*wp[:2])
            self.sleep(max(0.003, wp[2]))
        self.page.mouse.up()
        return True
