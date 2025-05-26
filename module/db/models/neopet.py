from module.db.models.base import BaseModel
from copy import deepcopy

class Neopet(BaseModel):
    def __init__(self, **kwargs):
        self.name = ''
        self.health = 0
        self.max_health = 0
        self.level = 0
        self.hunger = 0
        self.species = ''
        self.color = ''
        self.mood = ''
        self.is_active = False
        self.back_link = ''
        self.locator = None
        self.petpet = None
        self.equipments = []
        self.ailments = []
        super().__init__(**kwargs)

    def to_dict(self):
        ret = deepcopy(super().to_dict())
        ret.pop('locator', None)
        return ret
