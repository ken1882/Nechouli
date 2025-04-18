from module.logger import logger
from tasks.base.base_page import BasePageUI

class LunarTempleUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/shenkuu/lunar/')
        for node in self.page.locator('a[href]').all():
            if '?show=puzzle' not in node.get_attribute('href'):
                continue
            node.click()
        self.device.sleep(3)
        self.execute_script('lunar_temple')
        self.device.sleep(3)

if __name__ == '__main__':
    self = LunarTempleUI()
