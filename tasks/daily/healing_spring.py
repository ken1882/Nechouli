from module.logger import logger
from tasks.base.base_page import BasePageUI
from datetime import datetime, timedelta
from random import randint

class HealingSpringUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/faerieland/springs.phtml')
        self.device.click('input[value="Heal my Pets"]', nav=True)
        return True

    def calc_next_run(self, *args):
        future = datetime.now() + timedelta(minutes=30, seconds=randint(0, 59))
        self.config.task_delay(target=future)

if __name__ == '__main__':
    self = HealingSpringUI()

