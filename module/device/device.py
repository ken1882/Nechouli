import asyncio
import collections
import itertools
from module.device.control import Control
from module.device.screenshot import Screenshot
from module.logger import logger
from playwright.async_api import Page
from module.base.timer import Timer
from module.exception import (
    GameNotRunningError,
    GameStuckError,
    GameTooManyClickError,
)

def show_function_call():
    """
    Logs the stack trace of function calls.
    """
    import os
    import traceback
    stack = traceback.extract_stack()
    func_list = []
    for row in stack:
        filename, line_number, function_name, _ = row
        filename = os.path.basename(filename)
        func_list.append([filename, str(line_number), function_name])
    max_filename = max([len(row[0]) for row in func_list])
    max_linenum = max([len(row[1]) for row in func_list]) + 1

    def format_(file, line, func):
        file = file.rjust(max_filename, " ")
        line = f'L{line}'.rjust(max_linenum, " ")
        if not func.startswith('<'):
            func = f'{func}()'
        return f'{file} {line} {func}'

    func_list = [f'\n{format_(*row)}' for row in func_list]
    logger.info('Function calls:' + ''.join(func_list))

class Device(Control, Screenshot):
    def __init__(self, page: Page):
        """
        Args:
            page (Page): Playwright Page object.
        """
        self.page = page
        Control.__init__(self, page)
        Screenshot.__init__(self, page)
        self.detect_record = set()
        self.click_record = collections.deque(maxlen=30)
        self.stuck_timer = Timer(60, count=60).start()

    async def check_element_exists(self, selector: str) -> bool:
        """Check if a UI element exists."""
        exists = await self.page.locator(selector).count() > 0
        logger.info(f"Element {selector} exists: {exists}")
        return exists

    async def wait_for_element(self, selector: str, timeout: int = 5000):
        """Wait for an element to appear."""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            logger.info(f"Element {selector} appeared.")
        except Exception:
            logger.warning(f"Timeout waiting for element {selector}")

    async def detect_stuck(self):
        """
        Detects if the script is stuck waiting for an element.
        """
        reached = self.stuck_timer.reached()
        if not reached:
            return False

        show_function_call()
        logger.warning("Wait too long")
        logger.warning(f"Waiting for {self.detect_record}")
        self.detect_record.clear()
        self.stuck_timer.reset()

        if await self.page.evaluate("document.readyState") == "complete":
            raise GameStuckError("Wait too long")
        else:
            raise GameNotRunningError("Game is not running")

    def record_click(self, selector: str):
        """
        Records clicks to detect infinite loops.
        """
        self.click_record.append(selector)

    async def check_click_limit(self):
        """
        Detects excessive clicking on the same element.
        """
        first15 = itertools.islice(self.click_record, 0, 15)
        count = collections.Counter(first15).most_common(2)
        if count[0][1] >= 12:
            show_function_call()
            logger.warning(f"Too many clicks on: {count[0][0]}")
            logger.warning(f"History click: {[str(prev) for prev in self.click_record]}")
            self.click_record.clear()
            raise GameTooManyClickError(f"Too many clicks on: {count[0][0]}")

        if len(count) >= 2 and count[0][1] >= 6 and count[1][1] >= 6:
            show_function_call()
            logger.warning(f"Too many clicks between two buttons: {count[0][0]}, {count[1][0]}")
            logger.warning(f"History click: {[str(prev) for prev in self.click_record]}")
            self.click_record.clear()
            raise GameTooManyClickError(f"Too many clicks between two buttons: {count[0][0]}, {count[1][0]}")

    async def click_element(self, selector: str):
        """
        Clicks an element and records it.
        """
        self.record_click(selector)
        await self.page.locator(selector).click()
        logger.info(f"Clicked {selector}")

        await self.check_click_limit()

    async def input_text(self, selector: str, text: str):
        """
        Inputs text into a text field.
        """
        await self.page.locator(selector).fill(text)
        logger.info(f"Typed into {selector}: {text}")

    async def drag_element(self, start_selector: str, end_selector: str):
        """
        Drags one element to another.
        """
        start = await self.page.locator(start_selector).bounding_box()
        end = await self.page.locator(end_selector).bounding_box()
        await self.page.mouse.move(start["x"], start["y"])
        await self.page.mouse.down()
        await self.page.mouse.move(end["x"], end["y"])
        await self.page.mouse.up()
        logger.info(f"Dragged {start_selector} to {end_selector}")

    async def wait_until_stable(self, selector: str, timeout=5):
        """
        Waits until an element stops changing.
        """
        prev_image = await self.page.screenshot(type="png")
        timer = Timer(timeout)

        while not timer.reached():
            await self.page.wait_for_timeout(200)
            new_image = await self.page.screenshot(type="png")

            if prev_image == new_image:
                break
            prev_image = new_image

    async def handle_canvas_click(self, selector: str, x_offset: int, y_offset: int):
        """
        Clicks inside a canvas element at a specific offset.
        """
        bounding_box = await self.page.locator(selector).bounding_box()
        if bounding_box:
            x, y = bounding_box["x"] + x_offset, bounding_box["y"] + y_offset
            await self.page.mouse.click(x, y)
            logger.info(f"Clicked inside {selector} at ({x}, {y})")

    async def get_canvas_pixel_color(self, selector: str, x_offset: int, y_offset: int):
        """
        Gets the color of a pixel inside a canvas element.
        """
        script = f"""
        var canvas = document.querySelector('{selector}');
        var ctx = canvas.getContext('2d');
        var pixel = ctx.getImageData({x_offset}, {y_offset}, 1, 1).data;
        return `rgb(${pixel[0]}, ${pixel[1]}, ${pixel[2]})`;
        """
        color = await self.page.evaluate(script)
        logger.info(f"Pixel color at ({x_offset}, {y_offset}): {color}")
        return color
