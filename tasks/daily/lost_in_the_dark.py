from module.logger import logger
from tasks.base.base_page import BasePageUI
from datetime import datetime, timedelta

class LostInTheDarkUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/games/lostinthedark/index.phtml')
        timer = datetime.now() + timedelta(minutes=5)
        while datetime.now() < timer:
            btn = self.device.wait_for_element(
                'input[value="Enter at Your Own Risk!"]',
                'input[value="Right"]',
                'input[value="Continue"]',
                'input[value="Return to Haunted Woods"]',
            )
            if btn:
                if 'return' in (btn.get_attribute('value') or '').lower():
                    logger.info("GG")
                    break
                self.device.click(btn, nav=True)
                continue
        return True

if __name__ == '__main__':
    self = LostInTheDarkUI()
