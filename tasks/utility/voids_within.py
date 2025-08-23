from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.base.utils import str2int

class VoidsWithinUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/hospital/volunteer.phtml', timeout=180)
        done = False
        do_send = True
        if self.config.VoidsWithin_DelayForDailyFeed and self.config.stored.DailyQuestFeedTimesLeft.value:
            do_send = False
            logger.info("Delay dispatch for daily feed")
        for i in [5, 4, 3, 2, 1]:
            pane = self.page.locator(f'#Act{i}Pane')
            btn = self.page.locator(f'#Act{i}PaneBtn')
            if 'minimize' in pane.get_attribute('class'):
                self.device.scroll_to(loc=btn)
                if i != 1:
                    self.device.click(btn)
                    self.device.wait(0.5)
            joins = pane.locator('button[id*="VolunteerButton"]')
            for j in joins.all():
                done = False
                while True:
                    if 'error occurred' in self.page.content().lower():
                        return False
                    try:
                        done = self.process_shift(j, do_send)
                        break
                    except Exception as e:
                        logger.warning(f"Failed to process shift: {e}, retrying...")
                        self.device.wait(1)
                if done:
                    break
            if done:
                break
        if not do_send:
            logger.info("Delay task for to daily feed delay")
            self.config.task_delay(minute=60)
            return None
        self.goto('https://www.neopets.com/tvw/rewards/')
        node = self.device.wait_for_element('#PlotPointsEarned')
        self.config.stored.EarnedPlotPoints.set(str2int(node.text_content()))
        return True

    def process_shift(self, shift, send=True):
        if shift.text_content() == 'Cancel':
            return False
        if shift.text_content() == 'Complete':
            self.device.click(shift)
            back = self.device.wait_for_element('.popup-exit-icon')
            self.device.click(back)
            self.device.wait(0.5)
        if not send:
            return False
        self.device.click(shift)
        confirm = self.page.locator('button').filter(has_text='Ready')
        self.device.click(confirm)
        loading = self.page.locator('#VolunteerLoading')
        while loading.count():
            self.device.wait(0.1)
        p_count = self.config.VoidsWithin_AvailablePetsCount
        if p_count > 0:
            p_count = 1
        pets = self.page.locator('.vc-pet')
        while pets.count() < p_count: # bug that has no loading popup
            self.device.wait(1)
            pets = self.page.locator('.vc-pet')
        self.device.wait(3) # js render lag
        bans = [n.strip() for n in (self.config.VoidsWithin_DispatchBlacklist or '').splitlines() if n.strip()]
        for p in pets.all():
            flag_sent = False
            while not p.locator('.vc-image').count():
                self.device.wait(1)
            if p.locator('.volunteering').is_visible():
                continue
            if not p.locator('img').first.get_attribute('src'):
                continue
            depth = 0
            while 'selected' not in p.get_attribute('class'):
                self.device.click(p)
                self.device.wait(0.5)
                if p.locator('.volunteering').is_visible():
                    flag_sent = True
                    break
                depth += 1
                if depth > 20:
                    flag_sent = True
                    logger.warning(f"Pet {p.text_content()} is not selectable, skipping")
                    break
            pname = p.locator('.vc-name').text_content()
            if pname in bans:
                logger.info(f"Pet {pname} is in dispatch blacklist, skipping")
                continue
            if flag_sent:
                continue
            send = self.page.locator('button').filter(has_text='Join Volunteer Team')
            self.device.click(send)
            back = self.device.wait_for_element('.popup-exit-icon')
            self.device.click(back)
            break
        else:
            logger.info(f"All pets joined, exit")
            return True
        return False

    def calc_next_run(self, s=''):
        if s == 'failed':
            return self.config.task_delay(minute=1)
        self.config.task_delay(minute=60*6+1)


if __name__ == '__main__':
    self = VoidsWithinUI()
