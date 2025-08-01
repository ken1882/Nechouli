from module.logger import logger
from tasks.base.base_page import BasePageUI

class DailyPuzzleUI(BasePageUI):

    def main(self):
        self.goto('https://www.jellyneo.net/?go=dailypuzzle')
        pan = self.device.page.locator('.large-7')
        ss = pan.locator('strong')
        answer = ss.nth(3).text_content().strip().lower()
        logger.info(f"Found answer: {answer}")
        self.goto('https://www.neopets.com/community/index.phtml')
        sel = self.device.page.locator('select[name=trivia_response]')
        if not sel.count():
            logger.warning("Puzzle looks like already answered today.")
            return True
        self.device.scroll_to(loc=sel)
        opts = sel.locator('option')
        for i in range(opts.count()):
            opt = opts.nth(i)
            if opt.text_content().strip().lower() == answer:
                sel.select_option(str(opt.get_attribute('value')))
        self.device.click('input[value="Submit"]')
        return True


if __name__ == '__main__':
    self = DailyPuzzleUI()
