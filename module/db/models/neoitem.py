import re
from module.db.models.base_model import BaseModel
from playwright.sync_api import Locator
from datetime import datetime
from typing import Any, List, TYPE_CHECKING
import module.jelly_neo as jn

if TYPE_CHECKING:
    from module.config.config import AzurLaneConfig

class NeoItem(BaseModel):
    name: str
    id: str
    index: int
    market_price: float
    restock_price: float
    price_timestamp: float
    rarity: int
    image: str
    restock_shop_link: str
    parent_container: str
    effects: List[str]

    @classmethod
    def load_from_locator(cls, locator: Locator) -> 'NeoItem':
        return cls(
            name=locator.get_attribute('data-itemname'),
            id=locator.get_attribute('id'),
            image=locator.get_attribute('data-image'),
            description=locator.get_attribute('data-itemdesc'),
            rarity=locator.get_attribute('data-rarity'),
            restock_price=locator.get_attribute('data-itemvalue'),
            item_type=locator.get_attribute('data-itemtype'),
            market_price=0,
            _locator=locator
        )

    def __init__(self, **kwargs: Any) -> None:
        # sensible defaults
        self.name = ""
        self.description = ""
        self.id = ""
        self.index = 0
        self.quantity = 0
        self.market_price = 0
        self.restock_price = 0
        self.price_timestamp = datetime(1999, 11, 15).timestamp()
        self.rarity = 0
        self.image = ""
        self.restock_shop_link = ""
        self.parent_container = ""
        self.item_type = ""
        self.effects = []
        super().__init__(**kwargs)

    def update_jn(self, force=False):
        '''
        Update item data from jellyneo
        '''
        data = jn.get_item_details_by_name(self.name, force=force)
        if not data:
            return self
        self.id = data.get('id', self.id)
        self.image = data.get('image', self.image)
        self.market_price = data.get('market_price', self.market_price)
        self.restock_price = data.get('restock_price', 0) if self.restock_price == 0 else self.restock_price
        self.description = data.get('description', self.description)
        self.rarity = data.get('rarity', self.rarity)
        self.item_type = data.get('category', self.item_type)
        self.effects = data.get('effects', self.effects)
        self.price_timestamp = data.get('price_timestamp', self.price_timestamp)
        return self

    @property
    def category(self) -> str:
        if self.rarity == 500:
            return 'cash'
        if self.rarity == 200:
            return 'artifact'
        if 'food' in self.item_type.lower() or 'edible' in self.effects:
            return 'food'
        if 'playable' in self.effects:
            return 'toy'
        if 'readable' in self.effects:
            return 'book'
        if self.item_type.lower() == 'grooming':
            return 'grooming'
        return 'other'

    def is_edible(self, config: 'AzurLaneConfig') -> bool:
        conf = config.PetCares_FeedBlacklist or ""
        if any(re.search(regex, self.name, re.I) for regex in conf.split("\n") if regex):
            return False
        if all([e in self.effects for e in ['diseases','edible']]):
            return False
        return True

    def is_playable(self, config: 'AzurLaneConfig') -> bool:
        if 'openable' in self.effects:
            return False
        conf = config.PetCares_PlayBlackList or ""
        if any(re.search(regex, self.name, re.I) for regex in conf.split("\n") if regex):
            return False
        if 'playable' not in self.effects:
            return False
        return True

    def is_groomable(self, config: 'AzurLaneConfig') -> bool:
        if self.category != 'grooming':
            return False
        if 'openable' in self.effects:
            return False
        conf = config.PetCares_GroomBlackList or ""
        if any(re.search(regex, self.name, re.I) for regex in conf.split("\n") if regex):
            return False
        return True

    def __eq__(self, value) -> bool:
        if isinstance(value, NeoItem):
            return self.name == value.name
        return self.name == value
