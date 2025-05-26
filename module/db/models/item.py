from module.db.models import base
from datetime import datetime
class NeoItem(base.BaseModel):
    def __init__(self, **kwargs):
        self.name = ''
        self.id = ''
        self.price = 0
        self.restock_price = 0
        self.price_timestamp = datetime(1999, 11, 15).timestamp()
        self.rarity = 0
        self.category = ''
        self.image = ''
        self.restock_shop_link = ''
        self.effects = []
        super().__init__(**kwargs)
