from module.logger import logger
from tasks.base.base_page import BasePageUI

class VoidsWithinUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/hospital/volunteer.phtml')
        done = False
        for i in [5, 4, 3, 2, 1]:
            pane = self.page.locator(f'#Act{i}Pane')
            btn = self.page.locator(f'#Act{i}PaneBtn')
            self.device.scroll_to(loc=btn)
            if i != 1:
                self.device.click(btn)
                self.device.wait(0.5)
            joins = pane.locator('button[id*="VolunteerButton"]')
            for j in joins.all():
                done = self.process_shift(j)
                if done:
                    break
            if done:
                break
        return True

    def process_shift(self, shift):
        if shift.text_content() == 'Cancel':
            return False
        if shift.text_content() == 'Complete':
            self.device.click(shift)
            back = self.device.wait_for_element('.popup-exit-icon')
            self.device.click(back)
            self.device.wait(0.5)
        self.device.click(shift)
        confirm = self.page.locator('button').filter(has_text='Ready')
        self.device.click(confirm)
        loading = self.page.locator('#VolunteerLoading')
        while loading.count():
            self.device.wait(0.1)
        self.device.wait(1)
        pets = self.page.locator('.vc-pet')
        while pets.count() < 1: # bug that has no loading popup
            self.device.wait(1)
            pets = self.page.locator('.vc-pet')
        for p in pets.all():
            flag_sent = False
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

    def calc_next_run(self, *args):
        self.config.task_delay(minute=60*6+1)


if __name__ == '__main__':
    self = VoidsWithinUI()
