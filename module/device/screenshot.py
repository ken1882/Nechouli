import os
import cv2
import asyncio
import time
import numpy as np
from io import BytesIO
from PIL import Image
from datetime import datetime
from collections import deque
from playwright.sync_api import Page, Locator
from functools import cached_property
from module.base.utils import get_color, image_size, limit_in, save_image
from module.device.connection import Connection
from module.exception import RequestHumanTakeover, ScriptError
from module.logger import logger
from module.base.timer import Timer

class Screenshot(Connection):
    _screen_size_checked = False
    _screen_black_checked = False
    _minicap_uninstalled = False
    _screenshot_interval = Timer(0.1)
    _screenshot_target = None
    _last_save_time = {}
    image: np.ndarray

    def screenshot_playwright(self):
        target = self._screenshot_target or self.page
        ibytes = self.page.screenshot(full_page=False)
        img = Image.open(BytesIO(ibytes)).convert('RGB')
        if isinstance(target, Locator):
            box = target.bounding_box()
            if not box:
                raise RuntimeError("Failed to get bounding box for target.")
            x, y, w, h = int(box['x']), int(box['y']), int(box['width']), int(box['height'])
            img = img.crop((x, y, x + w, y + h))
        return np.asarray(img)

    @cached_property
    def screenshot_methods(self):
        return {
            'playwright': self.screenshot_playwright,
        }

    @cached_property
    def screenshot_method_override(self) -> str:
        return ''

    def screenshot(self) -> np.ndarray:
        self._screenshot_interval.wait()
        self._screenshot_interval.reset()

        for _ in range(2):
            if self.screenshot_method_override:
                method = self.screenshot_method_override
            else:
                method = self.config.DEVICE_SCREENSHOT_METHOD
            method = self.screenshot_methods.get(method, self.screenshot_playwright)

            self.image = method()

            # if self.config.Emulator_ScreenshotDedithering:
            #     # This will take 40-60ms
            #     cv2.fastNlMeansDenoising(self.image, self.image, h=17, templateWindowSize=1, searchWindowSize=2)
            # self.image = self._handle_orientated_image(self.image)

            if self.config.Error_SaveError:
                self.screenshot_deque.append({'time': datetime.now(), 'image': self.image})

            if self.check_screen_size() and self.check_screen_black():
                break
            else:
                continue

        return self.image

    @property
    def has_cached_image(self):
        return hasattr(self, 'image') and self.image is not None

    def _handle_orientated_image(self, image):
        """
        Args:
            image (np.ndarray):

        Returns:
            np.ndarray:
        """
        width, height = image_size(self.image)
        if width == 1280 and height == 720:
            return image

        # Rotate screenshots only when they're not 1280x720
        if self.orientation == 0:
            pass
        elif self.orientation == 1:
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif self.orientation == 2:
            image = cv2.rotate(image, cv2.ROTATE_180)
        elif self.orientation == 3:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        else:
            raise ScriptError(f'Invalid device orientation: {self.orientation}')

        return image

    @cached_property
    def screenshot_deque(self):
        try:
            length = int(self.config.Error_ScreenshotLength)
        except ValueError:
            logger.error(f'Error_ScreenshotLength={self.config.Error_ScreenshotLength} is not an integer')
            raise RequestHumanTakeover
        # Limit in 1~300
        length = max(1, min(length, 300))
        return deque(maxlen=length)

    @cached_property
    def screenshot_tracking(self):
        return []

    def save_screenshot(self, genre='items', interval=None):
        """Save a screenshot. Use millisecond timestamp as file name.

        Args:
            genre (str, optional): Screenshot type.
            interval (int, float): Seconds between two save. Saves in the interval will be dropped.

        Returns:
            bool: True if save succeed.
        """
        now = time.time()
        if interval is None:
            interval = 0.2

        if now - self._last_save_time.get(genre, 0) > interval:
            fmt = 'png'
            file = '%s.%s' % (int(now * 1000), fmt)

            folder = 'assets'
            folder = os.path.join(folder, genre)
            if not os.path.exists(folder):
                os.mkdir(folder)

            file = os.path.join(folder, file)
            self.image_save(file)
            self._last_save_time[genre] = now
            return True
        else:
            self._last_save_time[genre] = now
            return False

    def screenshot_last_save_time_reset(self, genre):
        self._last_save_time[genre] = 0

    def screenshot_interval_set(self, interval=None):
        """
        Args:
            interval (int, float, str):
                Minimum interval between 2 screenshots in seconds.
                Or None for Optimization_ScreenshotInterval, 'combat' for Optimization_CombatScreenshotInterval
        """
        if interval is None:
            origin = self.config.Optimization_ScreenshotInterval
            interval = limit_in(origin, 0.1, 0.3)
            if interval != origin:
                logger.warning(f'Optimization.ScreenshotInterval {origin} is revised to {interval}')
                self.config.Optimization_ScreenshotInterval = interval
            # Allow nemu_ipc to have a lower default
            if self.config.DEVICE_SCREENSHOT_METHOD == 'nemu_ipc':
                interval = limit_in(origin, 0.1, 0.2)
        elif interval == 'combat':
            origin = self.config.Optimization_CombatScreenshotInterval
            interval = limit_in(origin, 0.3, 1.0)
            if interval != origin:
                logger.warning(f'Optimization.CombatScreenshotInterval {origin} is revised to {interval}')
                self.config.Optimization_CombatScreenshotInterval = interval
        elif isinstance(interval, (int, float)):
            # No limitation for manual set in code
            pass
        else:
            logger.warning(f'Unknown screenshot interval: {interval}')
            raise ScriptError(f'Unknown screenshot interval: {interval}')

        if interval != self._screenshot_interval.limit:
            logger.info(f'Screenshot interval set to {interval}s')
            self._screenshot_interval.limit = interval

    def image_show(self, image=None):
        if image is None:
            image = self.image
        Image.fromarray(image).show()

    def image_save(self, file=None):
        if file is None:
            file = f'{int(time.time() * 1000)}.png'
        save_image(self.image, file)

    def check_screen_size(self):
        """
        Screen size must be 1280x720.
        Take a screenshot before call.
        """
        # Playwright default viewport size is 1280x720
        return True

    def check_screen_black(self):
        # TODO: Check if the screenshot is black
        return True
