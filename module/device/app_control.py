from module.logger import logger
from playwright.async_api import Page

class AppControl:
    def __init__(self, page: Page):
        self.page = page

    async def app_start(self, url: str):
        """Start web automation by opening a page."""
        await self.page.goto(url)
        logger.info(f"Opened {url}")

    async def app_stop(self):
        """Stop the Playwright session."""
        await self.page.close()
        logger.info("App closed.")
