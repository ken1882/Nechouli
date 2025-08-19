from module.db.models.base_model import BaseModel
from copy import deepcopy
from typing import Any, List, Optional, MutableMapping
from playwright.sync_api import Locator

class Neopet(BaseModel):
    name: str
    health: int
    max_health: int
    strength: int
    defense: int
    movement: int
    intelligence: int
    level: int
    hunger: int
    species: str
    color: str
    mood: str
    is_active: bool
    petpet: Optional[str]
    equipments: List[str]
    ailments: List[str]
    assignments: str

    def __init__(self, **kwargs: Any) -> None:
        self.name = ""
        self.health = 0
        self.max_health = 0
        self.strength = 0
        self.defense = 0
        self.movement = 0
        self.intelligence = 0
        self.level = 0
        self.hunger = 0
        self.species = ""
        self.color = ""
        self.mood = ""
        self.is_active = False
        self.assignments = ""
        self.petpet = None
        self.equipments = []
        self.ailments = []
        super().__init__(**kwargs)

    def __eq__(self, value) -> bool:
        if isinstance(value, Neopet):
            return self.name == value.name
        return self.name == value
