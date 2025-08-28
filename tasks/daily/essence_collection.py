from module.logger import logger
from tasks.base.base_page import BasePageUI
from urllib.parse import urljoin
from datetime import datetime, timedelta

PLACES = [
    "https://www.neopets.com/altador/index.phtml",
    "https://www.neopets.com/medieval/brightvale.phtml",
    "https://www.neopets.com/medieval/index_evil.phtml",
    "https://www.neopets.com/faerieland/faeriecity.phtml",
    "https://www.neopets.com/faerieland/index.phtml",
    "https://www.neopets.com/halloween/index.phtml",
    "https://www.neopets.com/worlds/index_kikolake.phtml",
    "https://www.neopets.com/pirates/index.phtml",
    "https://www.neopets.com/moon/index.phtml",
    "https://www.neopets.com/tropical/index.phtml",
    "https://www.neopets.com/water/index.phtml",
    "https://www.neopets.com/medieval/index_farm.phtml",
    "https://www.neopets.com/medieval/index.phtml",
    "https://www.neopets.com/medieval/index_castle.phtml",
    "https://www.neopets.com/magma/caves.phtml",
    "https://www.neopets.com/magma/index.phtml",
    "https://www.neopets.com/island/index.phtml",
    "https://www.neopets.com/objects.phtml",
    "https://www.neopets.com/market_bazaar.phtml",
    "https://www.neopets.com/market_map.phtml",
    "https://www.neopets.com/market_plaza.phtml",
    "https://www.neopets.com/halloween/neovia.phtml",
    "https://www.neopets.com/desert/qasala.phtml",
    "https://www.neopets.com/worlds/index_roo.phtml",
    "https://www.neopets.com/desert/sakhmet.phtml",
    "https://www.neopets.com/shenkuu/index.phtml",
    "https://www.neopets.com/winter/index.phtml",
    "https://www.neopets.com/winter/icecaves.phtml",
    "https://www.neopets.com/winter/terrormountain.phtml",
    "https://www.neopets.com/halloween/index_fair.phtml",
    "https://www.neopets.com/worlds/index_geraptiku.phtml",
    "https://www.neopets.com/desert/index.phtml",
    "https://www.neopets.com/water/index_ruins.phtml",
    "https://www.neopets.com/prehistoric/index.phtml",
    "https://www.neopets.com/prehistoric/plateau.phtml",
    "https://www.neopets.com/space/hangar.phtml",
    "https://www.neopets.com/space/recreation.phtml",
    "https://www.neopets.com/space/index.phtml",
    "https://www.neopets.com/pirates/warfwharf.phtml",
]

class EssenceCollectionUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/tvw/')
        bonus = self.page.locator('button[tabindex="0"]').filter(has_text='Collect Reward')
        if bonus.count() and bonus.is_visible():
            self.device.click(bonus)
            btn = self.device.wait_for_element('button[title="Return to Hub"]')
            self.device.click(btn)
        for url in PLACES:
            self.goto(url)
            loader = self.page.locator('#mapH5Loading')
            st = datetime.now()
            while loader.count() and loader.is_visible():
                self.device.wait(0.3)
                if st + timedelta(seconds=10) < datetime.now():
                    logger.error("Map loading timeout, retry later")
                    return False
            self.device.wait(3) # random js lag
            nodes = self.device.page.locator('.tvw-essence')
            depth = 0
            while nodes.count():
                node = nodes.nth(0)
                self.device.scroll_to(0, 100)
                self.claim_and_close(node)
                depth += 1
                if depth > 10:
                    logger.warning(f"Failed to claim essence at {url}, retry later")
                    return False
        return True

    def claim_and_close(self, btn):
        bb = btn.bounding_box()
        self.device.click((bb['x']+20, bb['y']+20))
        close_btn = self.page.locator('button').filter(has_text='Keep Searching').all()
        close_btn = self.device.wait_for_element(*close_btn)
        if not close_btn:
            return
        self.device.click(close_btn)

if __name__ == '__main__':
    self = EssenceCollectionUI()
