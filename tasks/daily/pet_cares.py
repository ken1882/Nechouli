from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.exception import TaskError
from module.db.models.neopet import Neopet
from module.db.data_map import *

class PetCaresUI(BasePageUI):
    select_pet: Neopet
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pets = []
        self.items = []
        self.selected_pet = None

    def main(self):
        self.goto('https://www.neopets.com/home')
        self.scan_all_pets()
        self.feed_all_pets()

    def scan_all_pets():
        self.pets = []
        nodes = self.page.locator('.hp-carousel-nameplate')
        num = nodes.count()
        if not num:
            raise TaskError('No pets found')
        for node in nodes.all():
            name = node.get_attribute('data-name')
            if not name: # empty slot
                continue
            self.pets.append(Neopet(
                name = name,
                health=int(node.get_attribute('data-health')),
                max_health=int(node.get_attribute('data-maxhealth')),
                hunger=int(HUNGER_LEVEL[node.get_attribute('data-hunger')]),
                level=int(node.get_attribute('data-level')),
                species=node.get_attribute('data-species'),
                color=node.get_attribute('data-color'),
                mood=node.get_attribute('data-mood'),
                is_active=node.get_attribute('data-active') == 'true',
                locator=node,
            ))

    def select_pet(self, index):
        if index < 0 or index >= len(self.pets):
            raise TaskError(f'Invalid pet index: {index}')
        self.selected_pet = self.pets[index]
        logger.info(f'Selected pet: {self.selected_pet.name}')
        self.selected_pet.locator.click()

    def feed_all_pets(self):
        for i, pet in enumerate(self.pets):
            if pet.hunger >= HUNGER_LEVEL['full up']:
                continue
            logger.info(f'Feeding pet {pet.name} with hunger {HUNGER_VALUE[pet.hunger]}')
            self.select_pet(i)
            self.page.locator('#petCareLinkFeed').click()



if __name__ == '__main__':
    self = PetCaresUI()
