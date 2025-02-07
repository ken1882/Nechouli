from module.alas import AzurLaneAutoScript
from module.logger import logger


class Nechouli(AzurLaneAutoScript):
    pass

if __name__ == '__main__':
    src = Nechouli('src')
    src.loop()
