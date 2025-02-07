import asyncio
from playwright.async_api import Page
from module.logger import logger
from module.base.timer import Timer

class Screenshot:
    def __init__(self, page: Page):
        """
        Args:
            page (Page): Playwright Page object.
        """
        self.page = page
        self._screenshot_interval = Timer(0.1)
        self._last_save_time = {}

    async def take_screenshot(self, filename: str = "screenshot.png"):
        """
        Takes a full-page screenshot.

        Args:
            filename (str): The file path to save the screenshot.
        """
        await self.page.screenshot(path=filename)
        logger.info(f"Screenshot saved: {filename}")

    async def capture_canvas(self, selector: str, filename: str = "canvas.png"):
        """
        Captures a screenshot of a canvas element.

        Args:
            selector (str): The CSS selector of the canvas element.
            filename (str): The file path to save the screenshot.
        """
        element = await self.page.locator(selector)
        await element.screenshot(path=filename)
        logger.info(f"Canvas screenshot saved: {filename}")

    async def check_black_screen(self, selector: str) -> bool:
        """
        Checks if a canvas element is completely black.

        Args:
            selector (str): The CSS selector of the canvas element.

        Returns:
            bool: True if the canvas is black, False otherwise.
        """
        script = f"""
        var canvas = document.querySelector('{selector}');
        var ctx = canvas.getContext('2d');
        var pixelData = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        return pixelData.every((value, index) => index % 4 !== 3 || value === 0);
        """
        is_black = await self.page.evaluate(script)
        logger.info(f"Canvas {selector} is black: {is_black}")
        return is_black

    async def save_screenshot(self, filename="screenshot.png", interval=None):
        """
        Saves a screenshot, enforcing a minimum interval between captures.

        Args:
            filename (str): The file path to save the screenshot.
            interval (float): Minimum time between two screenshots.
        """
        now = asyncio.get_event_loop().time()
        if interval and now - self._last_save_time.get(filename, 0) < interval:
            return False

        await self.take_screenshot(filename)
        self._last_save_time[filename] = now
        return True
