import time
from module.logger import logger
from tasks.base.base_page import BasePageUI
from tasks.base.base_flash import BaseFlash
import tasks.games.assets.assets_games_fashion_fever as assets

class FashionFeverUI(BaseFlash, BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/games/game.phtml?game_id=805')
        return self.play(
            start_button=assets.start,
        )

    def start_game(self):
        x1, y1, x2, y2 = assets.start.area

if __name__ == '__main__':
    self = FashionFeverUI()
