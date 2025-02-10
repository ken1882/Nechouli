from module.alas import AzurLaneAutoScript
from module.logger import logger



class Nechouli(AzurLaneAutoScript):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start_playwright(self):
        pass

    def daily_quest(self):
        from tasks.daily.daily_quest import DailyQuestUI
        DailyQuestUI(config=self.config, device=self.device).run()

if __name__ == '__main__':
    nch = Nechouli('nechouli')
    nch.loop()
