from module.logger import logger
from tasks.base.base_page import BasePageUI

class GrumpyKingUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/medieval/grumpyking.phtml')
        if self.is_new_account():
            return True
        if 'outtolunch.gif' in self.page.content():
            logger.info("Grumpy King is unavailable, return after 1 hour")
            return False
        self.execute_script('king_autofill')
        self.device.click('button[type="submit"]', nav=True)
        return True

if __name__ == '__main__':
    self = GrumpyKingUI()
