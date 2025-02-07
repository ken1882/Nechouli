from module.logger import logger
from playwright.async_api import Page

class Control:
    def __init__(self, page: Page):
        self.page = page

    async def click(self, selector: str):
        """Click a UI element."""
        await self.page.locator(selector).click()
        logger.info(f"Clicked element: {selector}")

    async def input_text(self, selector: str, text: str):
        """Type text into an input field."""
        await self.page.locator(selector).fill(text)
        logger.info(f"Typed into {selector}: {text}")

    async def drag(self, start_selector: str, end_selector: str):
        """Drag one UI element to another."""
        start = await self.page.locator(start_selector).bounding_box()
        end = await self.page.locator(end_selector).bounding_box()
        await self.page.mouse.move(start["x"], start["y"])
        await self.page.mouse.down()
        await self.page.mouse.move(end["x"], end["y"])
        await self.page.mouse.up()
        logger.info(f"Dragged {start_selector} to {end_selector}")
