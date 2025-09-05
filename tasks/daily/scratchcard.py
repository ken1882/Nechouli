from module.logger import logger
from tasks.base.base_page import BasePageUI
from tasks.base.base_flash import BaseFlash
import tasks.daily.assets.assets_daily_scratchcard as assets

class ScratchcardUI(BaseFlash, BasePageUI):

    LocationUrlMap = {
        'desert': 'https://www.neopets.com/desert/sc/kiosk.phtml',
        'snow': 'https://www.neopets.com/winter/kiosk.phtml',
        'halloween': 'https://www.neopets.com/halloween/kiosk.phtml'
    }

    def main(self):
        self.frame = ''
        self.locator = 'ruffle-embed'
        self.cooldown = 60 * 4
        loc = self.config.Scratchcard_Location
        self.goto(self.LocationUrlMap[loc])
        buy = self.page.locator('input[type="submit"]')
        if 'come back later' in self.page.content() or buy.count() < 2:
            logger.warning(f'Temprorarily closed')
            return False
        text = self.page.locator('.content').first.text_content().lower()
        if 'time left before you can purchase one is:' in text:
            t = self.page.locator('.content >> p > b').nth(3).text_content()
            h, m = t.split(':')
            self.cooldown = int(h) * 60 + int(m) + 1
            logger.info(f"Next card available in {h}h {m}m")
        else:
            self.device.click(buy.nth(1), nav=True)
        if not self.config.Scratchcard_UseCard:
            return True
        if loc == 'desert':
            while True:
                cards = self.page.locator('img[alt="Click here to scratch this card"]')
                if not cards.count():
                    logger.info("No cards available")
                    return True
                self.device.click(cards.first, nav=True)
                self.play_desert()
                self.goto(self.LocationUrlMap[loc])
        return True

    def play_desert(self):
        self.device.scroll_to(0, 50)
        self.wait_for_button(assets.play, timeout=10, similarity=0.1)
        logger.info("Scratching the card...")
        slots_x = [250, 310, 370]
        slots_y = [100, 160, 260]
        loc = self.find_flash()
        for n in range(6):
            for i in range(10):
                for j in range(5):
                    sx = slots_x[n % 3] + i * 10
                    sy = slots_y[n // 3] + j * 10
                    sp = {'x': sx, 'y': sy}
                    tp = {'x': sx + 10, 'y': sy + 10}
                    loc.drag_to(loc, source_position=sp, target_position=tp)
                    loc.drag_to(loc, source_position=tp, target_position=sp)
        self.click((350, 380))
        self.page.wait_for_url(
            '**',
            timeout=self.config.Playwright_DefaultTimeout*1000,
            wait_until='domcontentloaded',
        )

    def calc_next_run(self, s=''):
        if s == 'failed':
            self.config.task_delay(minute=30)
            return
        self.config.task_delay(minute=self.cooldown)


if __name__ == '__main__':
    self = ScratchcardUI()
