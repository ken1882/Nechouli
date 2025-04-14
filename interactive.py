from module.alas import AzurLaneAutoScript
from module.logger import logger
from tasks.base.base_page import BasePageUI

alas = AzurLaneAutoScript()
config, device = alas.config, alas.device
device.start_browser()
self = BasePageUI(config, device)