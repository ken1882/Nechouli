from module.logger import logger
from tasks.base.base_page import BasePageUI

class WishingWellUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/wishing.phtml')
        self.page.locator('input[name="donation"]').fill('21')
        self.page.locator('input[name="wish"]').fill(self.config.WishingWell_Item)
        self.device.click('input[type="submit"][value="Make a Wish"]')
        return True

    def calc_next_run(self, *args):
        self.config.task_delay(minute=102) # run 7 times in 12 hours

if __name__ == '__main__':
    self = WishingWellUI()
