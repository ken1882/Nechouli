from module.logger import logger
from tasks.base.base_page import BasePageUI
from urllib.parse import urljoin
from playwright.sync_api import Locator
import re

class DailyQuestUI(BasePageUI):

    def main(self):
        self.claim_rewards()
        self.scan_quests()
        if not self.do_quests():
            self.config.task_delay(minute=5)
            return False
        self.claim_rewards()
        return True

    def claim_rewards(self):
        self.goto('https://www.neopets.com/questlog/')
        logger.info("Claiming daily quest rewards")
        loading = self.page.locator('#QuestLogLoader')
        while loading.is_visible():
            self.device.wait(0.3)
        quests = self.page.locator('.questlog-quest')
        idx = 0
        while quests.count():
            quest = quests.nth(idx)
            ok_btn = quest.locator('button')
            if ok_btn.is_disabled():
                idx += 1
                if idx >= quests.count():
                    break
                continue
            self.claim_and_close(ok_btn)
        extra = self.page.locator('#QuestLogBonusAlert')
        if extra.is_visible() and extra.text_content().strip():
            self.claim_and_close(extra)
        self.device.click(self.page.locator('.ql-label-reward').first)
        extra = self.page.locator('#QuestLogStreakAlert')
        self.device.wait(1) # wait for animation
        if extra.is_visible() and extra.text_content().strip():
            self.claim_and_close(extra)

    def claim_and_close(self, btn):
        self.device.click(btn)
        close_btn = self.page.locator('button').filter(has_text='Back to Quests').all()
        close_btn = self.device.wait_for_element(*close_btn)
        self.device.click(close_btn)

    def scan_quests(self):
        self.quests_queue = []
        quests = self.page.locator('.questlog-quest')
        for quest in quests.all():
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
            elif 'feed' in quest_content:
                self.quests_queue.append({
                    'type': 'feed',
                })
        logger.info(f"Quest queue size: {len(self.quests_queue)}")

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
        else:
            return None
        return ret

    def do_quests(self):
        for quest in self.quests_queue:
            if quest['type'] == 'wheel':
                self.goto(quest['url'])
                self.device.scroll_to(0, 100)
                self.device.wait(3) # wait for wheel canvas to load
                self.device.click('canvas')
                self.device.wait(10) # wheel spin
                self.device.click('canvas') # claim reward
            elif quest['type'] == 'purchase':
                self.config.stored.DailyQuestRestockTimesLeft.set(quest['times'])
                self.config.task_call('Restocking')
                return False
            elif quest['type'] == 'feed':
                self.config.task_call('PetCares')
                self.config.stored.DailyQuestFeedTimesLeft.set(1)
                self.config.task_delay(minute=60, task='PetCares')
                return False
        return True

    def calc_next_run(self, *args):
        if self.config.stored.DailyQuestFeedTimesLeft.value > 0:
            return self.config.task_delay(minute=61)
        elif self.config.stored.DailyQuestRestockTimesLeft.value > 0:
            return self.config.task_delay(minute=10)
        super().calc_next_run(*args)

    def on_failed_delay(self):
        self.config.task_delay(minute=5)

if __name__ == '__main__':
    self = DailyQuestUI()
