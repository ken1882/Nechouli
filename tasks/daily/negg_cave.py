from module.logger import logger
from tasks.base.base_page import BasePageUI

class NeggCaveUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/shenkuu/neggcave')
        html = self.page.evaluate("document.documentElement.outerHTML").replace('\\', '')
        self.goto('https://thedailyneopets.com/articles/negg-solver/')
        script = f"document.getElementById('PageSourceBox').value = `{html}`"
        self.page.evaluate(script)
        self.device.wait(1)
        answer = []
        while len(answer) < 1:
            self.page.locator('button[type=button]').click()
            self.device.wait(1)
            ans_imgs = self.page.locator('tr > td > img')
            for slot in ans_imgs.all():
                src = slot.get_attribute('src')
                num = int(src.split('/')[-1].split('.')[0])
                answer.append(num)
        logger.info(f'Negg Cave answer: {answer}')
        self.goto('https://www.neopets.com/shenkuu/neggcave')
        self.device.scroll_to(0, 100)
        shape_base = '#mnc_parch_ui_symbol_{:d}'
        color_base = '#mnc_parch_ui_color_{:d}'
        negg_grid  = '#mnc_grid_cell_{:d}_{:d}'
        last_shape, last_color = -1,-1
        for idx, num in enumerate(answer):
            shape = num % 3
            if shape != last_shape:
                self.page.locator(shape_base.format(shape)).click()
                self.device.wait(0.5)
            self.page.locator(negg_grid.format(idx // 3, idx % 3)).click()
            self.device.wait(0.5)
            last_shape = shape
        self.page.locator(shape_base.format(last_shape)).click() # unselct
        self.device.wait(1)
        for idx, num in enumerate(answer):
            color = num // 3
            if color != last_color:
                self.page.locator(color_base.format(color)).click()
                self.device.wait(0.5)
            self.page.locator(negg_grid.format(idx // 3, idx % 3)).click()
            self.device.wait(0.5)
            last_color = color
        self.device.wait(1)
        self.page.locator('#mnc_negg_submit_text').click()
        return True

if __name__ == '__main__':
    self = NeggCaveUI()
