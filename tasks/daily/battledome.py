from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.base.utils import str2int
from datetime import datetime

class BattleDomeUI(BasePageUI):
    DIFFICULTY_MAP = {
        'Easy': 1,
        'Normal': 2,
        'Hard': 3,
    }

    def main(self):
        self.goto('https://www.neopets.com/dome/fight.phtml')
        self.device.scroll_to(0, 350)
        if not self.is_in_battle():
            if not self.select_pet():
                logger.error("Failed to select pet")
                return False
            cont = self.device.wait_for_element('.nextStep')
            self.device.click(cont)
            self.select_opponent()
            self.device.click('#bdFightStep3FightButton', nav=True)
        self.load_actions()
        won = True
        while won:
            won = self.process_battle()
            self.collect_rewards()
            if 'item limit' in self.page.content() and not self.config.BattleDome_GrindNP:
                logger.info("Daily item limit reached, stopping")
                return True
            if 'NP limit' in self.page.content():
                logger.info("Daily NP limit reached, stopping")
                return True
            self.config.load()
            logger.info("Next task: %s", self.config.get_next())
            if self.config.pending_task and self.config.pending_task[0].command != 'BattleDome':
                msg = "Other tasks available, replay after 5 minutes:\n"
                msg += '\n'.join([f"- {t}" for t in self.config.pending_task])
                logger.info(msg)
                self.config.task_delay(minute=5)
                return None
            self.device.click('#bdplayagain')
        logger.info("Stopped and canceled due to defeat")
        self.config.task_cancel()
        return True

    def select_pet(self):
        fighter = self.config.BattleDome_PetName
        pets = self.page.locator('.petThumbContainer')
        if not pets.count():
            logger.error("No pets found!")
            return False
        depth = 0
        while True:
            for pet in pets.all():
                name = pet.get_attribute('data-name')
                hidden = pet.locator('..').get_attribute('aria-hidden') or ''
                if name != fighter or hidden == 'true':
                    continue
                self.device.click(pet)
                break
            else:
                self.device.click('.bx-next')
                self.device.wait(0.5)
                depth += 1
                if depth > 10:
                    return False
                continue
            break
        status = self.page.locator('#bdFightPetInfo')
        if not status.count() or 'is ready' not in status.first.text_content():
            logger.error(f"Pet {fighter} is unable to fight!")
            return False
        step = self.device.wait_for_element('.nextStep')
        self.device.click(step)
        return True

    def select_opponent(self):
        oppo = self.config.BattleDome_Opponent
        row = self.page.locator('#npcTable').locator('td', has_text=oppo).locator('..')
        tou = self.DIFFICULTY_MAP.get(self.config.BattleDome_Difficulty, 1)
        self.device.click(row.locator(f'.tough{tou}'))

    def load_actions(self):
        self.actions = []
        configs = self.config.BattleDome_CombatOrder
        lines = [l.strip() for l in configs.split('\n') if l.strip()]
        lines = [l for l in lines if not l.startswith('#')]
        for line in lines:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 2:
                continue
            self.actions.append([p.lower() for p in parts])
        msg = f"Loaded {len(self.actions)} combat actions:\n"
        msg += '\n'.join([f"Turn#{idx+1}: {a}" for idx,a in enumerate(self.actions)])
        logger.info(msg)

    def process_battle(self):
        self.wait_and_start()
        while True:
            self.wait_for_turn()
            self.parse_status()
            w = self.determine_winner()
            if w == True:
                logger.info("Victory!")
                return True
            elif w == False:
                logger.info("Defeated!")
                return False
            else:
                pass
            if self.round > len(self.actions):
                logger.info("No more actions configured, ending battle")
                return False
            self.select_action()
            self.send_actions()

    def wait_and_start(self):
        btn = self.device.wait_for_element('#start')
        self.device.click(btn)

    def parse_status(self):
        self.round = str2int(self.page.locator('#flround').text_content())
        self.my_hp = str2int(self.page.locator('#p1hp').text_content())
        self.oppo_hp = str2int(self.page.locator('#p2hp').text_content())
        logger.info(f"Round {self.round}, HP Left: {self.my_hp} v.s. {self.oppo_hp}")

    def wait_for_turn(self):
        status = self.page.locator('#statusmsg')
        depth  = 0
        while True:
            t = status.text_content()
            if t == "Plan your next move...":
                break
            elif t.startswith("Winner"):
                return False
            self.device.wait(0.5)
            depth += 1
            if depth > 60:
                logger.error("Waited too long for turn")
                return False
        return True

    def select_action(self):
        a1,a2,a3 = self.actions[self.round-1]
        equips = self.page.locator('#p1equipment')
        if a1 != 'none':
            while 'block' not in (equips.get_attribute('style') or ''):
                self.device.click('#p1e1m')
                self.device.wait(0.5)
            for ab in equips.locator('img').all():
                name = ab.get_attribute('title').lower()
                if a1 == name:
                    self.device.click(ab)
                    break
        if a2 != 'none':
            while 'block' not in (equips.get_attribute('style') or ''):
                self.device.click('#p1e2m')
                self.device.wait(0.5)
            for ab in equips.locator('img').all():
                name = ab.get_attribute('title').lower()
                if a2 == name:
                    self.device.click(ab)
                    break
        if a3 != 'none':
            self.device.click('#p1am')
            for ab in self.page.locator('#p1ability >> td').all():
                name = (ab.get_attribute('title') or '').lower()
                if a3 == name:
                    self.device.click(ab)
                    break

    def send_actions(self):
        self.device.click('#fight')
        skip = self.page.locator('#skipreplay').first
        while (skip.get_attribute('class') or '').strip() != '':
            self.device.wait(0.5)
        self.device.click(skip)
        return True

    def determine_winner(self):
        if self.page.locator('.victory').is_visible():
            return True
        if self.page.locator('.defeatPlayAgain').first.is_visible():
            return False
        return None

    def collect_rewards(self):
        self.device.click('.collect')

    def is_in_battle(self):
        if 'arena.phtml' in self.page.url:
            return True
        return False


if __name__ == '__main__':
    self = BattleDomeUI()
