from module.logger import logger
from tasks.base.base_page import BasePageUI

class ShopWizardUI(BasePageUI):

    def main(self):
        if self.config.stored.ShopWizardRequests.is_empty():
            logger.info("No requests to process, skipping Shop Wizard")
            return True
        self.goto('https://www.neopets.com/shops/wizard.phtml')
        if "help you until you complete" in self.page.content():
            logger.warning("You're on a fairy quest, you'll manually complete it!")
            return False
        return True

if __name__ == '__main__':
    self = ShopWizardUI()
