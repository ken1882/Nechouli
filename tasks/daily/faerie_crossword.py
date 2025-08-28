from module.logger import logger
from tasks.base.base_page import BasePageUI
import json
import requests
import re

class FaerieCrosswordUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/games/crossword/index.phtml')
        if 'already solved' in self.page.content():
            logger.info("Crossword puzzle already solved today")
            return True
        answers = {}
        with open('assets/crossword-answer.json', 'r', encoding='utf-8') as f:
            answers = json.load(f)
        if not answers:
            logger.error("Missing file: assets/crossword-answer.json")
            return False
        loc = self.page.locator('input[value="Start today\'s puzzle!"]')
        if not loc.count():
            loc = self.page.locator('input[value="Continue today\'s puzzle!"]')
        self.device.click(loc, nav=True)
        index = 0
        listings = [None] * 15  # placeholder
        while index < len(listings):
            self.device.scroll_to(0, 250)
            listings = self.page.locator('td[valign="top"] > a')
            if not listings.count():
                logger.error("Unable to find crossword questions")
                return False
            listings = list(listings.all())
            listing = listings[index]
            question = listing.text_content().strip()
            question = re.match(r'^\d+\.\s*(.*)', question).groups()[0].lower()
            if question in answers:
                answer = answers[question]
                logger.info(f"Answering: {question} -> {answer}")
                listing.click()
                input_field = self.page.locator('input[name="x_word"]')
                if input_field.count():
                    input_field.fill(answer)
                    self.device.click('input[value="Go"]', nav=True, wait=0.3)
                    index += 1
                else:
                    logger.error("Input field not found for answer submission")
                    return False
            else:
                logger.warning(f"No answer found for question: {question}")
                self.record_missing_crossword(question)
                index += 1
        return True

    def on_failed_delay(self):
        self.config.task_delay(minute=1)

    def record_missing_crossword(self, question):
        with open('missing_crossword.txt', 'a') as f:
            f.write(f"{question}\n")

if __name__ == '__main__':
    self = FaerieCrosswordUI()
