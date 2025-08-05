from module.logger import logger
from tasks.base.base_page import BasePageUI
from urllib.parse import urljoin
from playwright.sync_api import Locator
import re

class DailyQuestUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/questlog/')
        self.quests_queue = []
        self.scan_quests()
        if not self.do_quests():
            return False
        self.claim_rewards()
        return True

    def claim_rewards(self):
        self.goto('https://www.neopets.com/questlog/')
        quests = self.page.locator('.questlog-quest')
        while quests.count():
            quest = quests.first
            ok_btn = quest.locator('button')
            if ok_btn.is_disabled():
                continue
            self.device.click(ok_btn)
            close_btn = self.page.locator('button').filter(has_text='Back to Quests').all()
            close_btn = self.device.wait_for_element(*close_btn)
            self.device.click(close_btn)

    def scan_quests(self):
        quests = self.page.locator('.questlog-quest')
        for quest in quests:
            ok_btn = quest.locator('button')
            if not ok_btn.is_disabled():
                continue
            quest_content = quest.text_content().strip().lower()
            if 'wheel' in quest_content:
                q = self.parse_wheel_quest(quest)
                if not q:
                    logger.warning(f"Failed to parse wheel quest, content block:\n{quest_content}")
                    continue
                self.quests_queue.append(q)
            elif 'purchase item' in quest_content:
                done,req = re.search(r"\d\/\d", quest_content).group().split('/')
                times = int(req) - int(done)
                self.quests_queue.append({
                    'type': 'purchase',
                    'times': times
                })

    def parse_wheel_quest(self, quest:Locator) -> dict:
        wheel_text = quest.text_content().strip().lower()
        ret = {
            'type': 'wheel',
            'url': None
        }
        if 'mediocrity' in wheel_text:
            ret['url'] = 'https://www.neopets.com/prehistoric/mediocrity.phtml'
        elif 'excitement' in wheel_text:
            ret['url'] = 'https://www.neopets.com/faerieland/wheel.phtml'
        elif 'knowledge' in wheel_text:
            ret['url'] = 'https://www.neopets.com/medieval/knowledge.phtml'
        elif 'misfortune' in wheel_text:
            ret['url'] = 'https://www.neopets.com/halloween/wheel/index.phtml'
        return None

    def do_quests(self):
        for quest in self.quests_queue:
            if quest['type'] == 'wheel':
                self.goto(quest['url'])
                self.device.scroll_to(0, 100)
                self.device.wait(3) # wait for wheel canvas to load
                self.device.click('canvas')
                self.device.wait(7) # wheel spin
                self.device.click('canvas') # claim reward
            elif quest['type'] == 'purchase':
                self.config.Restocking_DailyQuestTimesLeft = quest['times']
                self.config.task_call('Restocking')
                return False
        return True

    def calc_next_run(self, *args):
        if self.config.Restocking_DailyQuestTimesLeft:
            return self.config.task_delay(minutes=10)
        super().calc_next_run(*args)

if __name__ == '__main__':
    self = DailyQuestUI()
