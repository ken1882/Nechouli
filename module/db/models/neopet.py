from module.db.models.base_model import BaseModel
from copy import deepcopy
from typing import Any, List, Optional, MutableMapping

class Neopet(BaseModel):
    name: str
    health: int
    max_health: int
    level: int
    hunger: int
    species: str
    color: str
    mood: str
    is_active: bool
    back_link: str
    locator: Any  # Playwright Locator or similar
    petpet: Optional[str]
    equipments: List[str]
    ailments: List[str]

    def __init__(self, **kwargs: Any) -> None:
        self.name = ""
        self.health = 0
        self.max_health = 0
        self.level = 0
        self.hunger = 0
        self.species = ""
        self.color = ""
        self.mood = ""
        self.is_active = False
        self.back_link = ""
        self.locator = None
        self.petpet = None
        self.equipments = []
        self.ailments = []
        super().__init__(**kwargs)

