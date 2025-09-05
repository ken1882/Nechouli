from module.logger import logger
from tasks.base.base_page import BasePageUI

class FishingUI(BasePageUI):

    def main(self):
        self.fish()
        if not self.config.Fishing_SwapPets:
            return True
        self.goto('https://www.neopets.com/quickref.phtml')
        active_pet = self.page.locator('a[href="/quickref.phtml"] > b').inner_text()
        pets = [n.get_attribute('title') for n in self.page.locator('img[title]').all()]
        for p in pets:
            if p == active_pet:
                continue
            self.goto(f'https://www.neopets.com/process_changepet.phtml?new_active_pet={p}')
            self.fish()
        self.goto(f'https://www.neopets.com/process_changepet.phtml?new_active_pet={active_pet}')
        return True

    def fish(self):
        self.goto('https://www.neopets.com/water/fishing.phtml')
        self.device.scroll_to(0, 100)
        self.device.click('input[value="Reel In Your Line"]', nav=True)

    def calc_next_run(self, *args):
        self.config.task_delay(minute=self.config.Fishing_Interval)

if __name__ == '__main__':
    self = FishingUI()
