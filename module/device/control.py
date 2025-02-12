import numpy as np
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

    def wait_until_element_found(self, selectors:list, timeout:int=60, wait_interval:float=1):
        '''
        Wait until one of the selectors is found.
        '''
        while timeout > 0:
            node = None
            for selector in selectors:
                try:
                    node = self.page.query_selector(selector)
                except Exception as e:
                    pass
                if node:
                    return node
            timeout -= wait_interval
            self.sleep(wait_interval)
        return False

    def scroll_to(self, x:int=0, y:int=0, loc=None):
        if loc:
            bb = loc.bounding_box()
            if not bb:
                raise InvisibleElement
            x = 0
            y = y + bb['y'] - 100
        return self.page.evaluate(f"window.scrollTo({x}, {y})")

    def click(self,
            x:float=None, y:float=None, loc:Locator=None,
            x_mul=0.5, y_mul=0.5, point_random=(-10, -10, 10, 10),
            delay=50, random_delay=(-20, 20),
            button='left', modifiers=[], debug=False
        ):
        '''
        https://playwright.dev/python/docs/api/class-locator#locator-click
        https://playwright.dev/python/docs/api/class-mouse
        '''
        if not x and not y and not loc:
            raise ValueError("Unspecified click target")
        if type(point_random) == int:
            point_random = (-point_random, -point_random, point_random, point_random)
        if type(random_delay) == int:
            random_delay = (-random_delay, random_delay)
        mx, my = utils.random_rectangle_point(point_random)
        mx += int(bb['width'] * x_mul)
        my += int(bb['height'] * y_mul)
        md = delay + randint(*random_delay)
        bb = loc.bounding_box()
        bx, by = 0, 0
        if not bb:
            raise InvisibleElement
        else:
            bx = bb['x']
            by = bb['y']
        if loc:
            if debug:
                self.draw_debug_point(mx+bx, my+by)
            return loc.click(
                button=button,
                modifiers=modifiers,
                position={'x': mx, 'y': my},
                delay=md
            )
        if modifiers:
            raise ValueError("`page.mouse` does not support modifiers")
        self.page.mouse.click(mx+bx, my+by, button=button, delay=md)

    def drag_to(self,
            locator_a, locator_b, speed=1000, shake=(0, 15), point_random=(-10, -10, 10, 10),
            shake_random=(-5, -5, 5, 5), swipe_duration=0.1, shake_duration=0.03,
            random_duration=(-50, 50)
        ):
        locator_a.hover()
        self.page.mouse.down()
        ba = locator_a.bounding_box()
        bb = locator_b.bounding_box()
        p1 = np.array((ba['x'], ba['y'])) - utils.random_rectangle_point(point_random)
        p2 = np.array((bb['x'], bb['y'])) - utils.random_rectangle_point(point_random)
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
            self.sleep(wp[2])
        self.page.mouse.up()
        return True