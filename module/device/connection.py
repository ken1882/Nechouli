import asyncio
from functools import wraps
from playwright.async_api import async_playwright
from module.logger import logger
from module.base.decorator import retry

def retry(func):
    @wraps(func)
    async def retry_wrapper(self, *args, **kwargs):
        for attempt in range(3):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                logger.warning(f"Retrying {func.__name__} due to {e} (Attempt {attempt + 1}/3)")
                await asyncio.sleep(2)
        raise Exception(f"Function {func.__name__} failed after 3 retries.")
    return retry_wrapper

class Connection:
    def __init__(self, browser_type="chromium"):
        self.browser_type = browser_type
        self.playwright = None
        self.browser = None
        self.page = None
        self.current_url = ""

    async def start_browser(self):
        if self.playwright is None:
            self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(headless=False)
        self.page = await self.browser.new_page()
        logger.info("Browser started.")

    @retry
    async def open_page(self, url: str):
        if not self.page:
            await self.start_browser()

        logger.info(f'Opening page: {url}')
        await self.page.goto(url)
        self.current_url = await self.page.url()

    async def stop_browser(self):
        if self.browser:
            logger.info("Closing browser session.")
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.browser = None
        self.page = None
        self.playwright = None
        self.current_url = ""

    async def execute_js(self, script: str):
        return await self.page.evaluate(script)
