from nch import Nechouli
from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.exception import TaskError
from module.db.models.neopet import Neopet
from module.db.models.neoitem import NeoItem
from module.db.data_map import *
from module.base.utils import str2int
import module.jelly_neo as jn

from tasks.daily.pet_cares import PetCaresUI
from tasks.daily.faerie_crossword import FaerieCrosswordUI
from tasks.daily.trudys_surprise import TrudysSurpriseUI

alas = Nechouli()
config, device = alas.config, alas.device
device.start_browser()
self = BasePageUI(config, device)

