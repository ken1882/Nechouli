from nch import Nechouli
from module.logger import logger
from tasks.base.base_page import BasePageUI

alas = Nechouli()
config, device = alas.config, alas.device
device.start_browser()
self = BasePageUI(config, device)
