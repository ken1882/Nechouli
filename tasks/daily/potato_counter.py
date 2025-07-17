from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.base.utils import str2int

class PotatoCounterUI(BasePageUI):

    def main(self):
        while True:
            self.goto('https://www.neopets.com/medieval/potatocounter.phtml')
            if 'you can only' in self.page.content():
                logger.info("Max potato count reached, ending task")
                return True
            self.execute_script('potato')
            hint = self.device.wait_for_element('#potato-counter-overlay').text_content()
            ans = str2int(hint) or 0
            if ans <= 0 or ans > 99:
                logger.warning(f"Invalid potato count: {ans}, reloading page")
                self.reload()
                continue
            form = self.page.locator('form[action="potatocounter.phtml"]')
            form.locator('input[name="guess"]').fill(str(ans))
            self.device.click(form.locator('input[type="submit"]'), nav=True)
            self.device.sleep(1)
            again = self.page.locator('input[value="Play Again"]')
            if not again.count():
                break
        return True

if __name__ == '__main__':
    self = PotatoCounterUI()
