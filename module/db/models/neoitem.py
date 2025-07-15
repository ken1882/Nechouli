import re
from module.db.models.base_model import BaseModel
from module.config.config import AzurLaneConfig
from datetime import datetime
from typing import Any, List
import module.jelly_neo as jn

class NeoItem(BaseModel):
    # declare attributes for IDE & mypy -------------------------------
    name: str
    id: str
    market_price: float
    restock_price: float
    price_timestamp: float
    rarity: int
    category: str
    image: str
    restock_shop_link: str
    effects: List[str]

    def __init__(self, **kwargs: Any) -> None:
        # sensible defaults
        self.name = ""
        self.id = ""
        self.quantity = 0
        self.market_price = 0.0
        self.restock_price = 0.0
        self.price_timestamp = datetime(1999, 11, 15).timestamp()
        self.rarity = 0
        self.category = ""
        self.image = ""
        self.restock_shop_link = ""
        self.effects = []
        super().__init__(**kwargs)

    def update_jn(self):
        '''
        Update item data from jellyneo
        '''
        data = jn.get_item_details_by_name(self.name)
        if not data:
            return self
        self.id = data.get('id', self.id)
        self.image = data.get('image', self.image)
        self.market_price = data.get('market_price', self.market_price)
        self.restock_price = data.get('restock_price', self.restock_price)
        self.description = data.get('description', self.description)
        self.rarity = data.get('rarity', self.rarity)
        self.item_type = data.get('category', self.item_type)
        self.effects = data.get('effects', self.effects)
        return self

    def get_category(self):
        if 'food' in self.item_type.lower() or 'edible' in self.effects:
            return 'food'
        if 'playable' in self.effects:
            return 'toy'
        if 'readable' in self.effects:
            return 'book'
        if self.item_type.lower() == 'grooming':
            return 'grooming'
        return 'other'

    def is_edible(self, config: AzurLaneConfig) -> bool:
        if any(re.search(regex, self.name, re.I) for regex in config.PetCares_FeedBlacklist.split("\n") if regex):
            return False
        if all([e in self.effects for e in ['diseases','edible']]):
            return False
        return True
