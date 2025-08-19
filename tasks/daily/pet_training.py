from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.db.models.neopet import Neopet
from module.db.models.neoitem import NeoItem
from module.base.utils import str2int

ACADEMY = {
    'pirate': {
        'url': 'https://www.neopets.com/pirates/academy.phtml?type=status',
        'max_level': 40,
    },
    'island': {
        'url': 'https://www.neopets.com/island/training.phtml?type=status',
        'max_level': 250,
    },
    'ninja': {
        'url': 'https://www.neopets.com/island/fight_training.phtml?type=status',
        'max_level': 9999,
    }
}

ATTR_CONF_TABLE = {
    'lv': 'level',
    'str': 'strength',
    'def': 'defense',
    'mov': 'movement',
    'hp': 'max_health',
}

ATTR_COURSE_TABLE = {
    'lv': 'Level',
    'str': 'Strength',
    'def': 'Defence',
    'mov': 'Agility',
    'hp': 'Endurance',
}

class PetTrainingUI(BasePageUI):

    def main(self):
        configs = self.config.PetTraining_Config.splitlines()
        self.current_pets = []
        aca_pets = {
            'pirate': [],
            'island': [],
            'ninja': []
        }
        for conf in configs:
            pet_name, academy, target_lv, target_str, target_def, target_mov, target_hp = conf.split(':')
            aca_pets[academy].append(Neopet(
                name=pet_name,
                level=int(target_lv),
                max_health=int(target_hp),
                strength=int(target_str),
                defense=int(target_def),
                movement=int(target_mov),
            ))
        for academy, pets in aca_pets.items():
            if not pets:
                continue
            self.goto(ACADEMY[academy]['url'])
            completed = self.page.locator('input[type=submit][value="Complete Course!"]')
            if completed.count():
                self.device.click(completed.first, nav=True)
                self.goto(ACADEMY[academy]['url'])
            self.scan_pets(pets, academy=academy)
            trained = False
            for pet in pets:
                trained = self.train_pet(pet, academy)
                if trained:
                    self.config.stored.PendingTrainingFee.set(self.scan_fee())
        if trained:
            self.goto(ACADEMY[academy]['url'])
        return True

    def train_pet(self, desired_pet: Neopet, academy: str):
        attrs = [attr.strip().lower() for attr in self.config.PetTraining_TrainPriority.split('>')]
        target_course = ''
        pet = next((p for p in self.current_pets if p.name == desired_pet.name), None)
        if not pet:
            logger.warning(f"Pet {desired_pet.name} not found in current pets, skipping training.")
            return False
        for a in attrs:
            if self.is_capped(pet, academy, ATTR_CONF_TABLE[a]):
                continue
            target_course = a
            break
        if not target_course:
            logger.info(f"Pet {pet.name} is already capped in all attributes in {academy} academy, skipping training.")
            return False
        self.goto(ACADEMY[academy]['url'].split('?')[0] + '?type=courses')
        sel = self.page.locator('select[name=course_type]')
        self.device.scroll_to(loc=sel)
        sel.select_option(value=ATTR_COURSE_TABLE[target_course])
        sel_p = self.page.locator('select[name=pet_name]')
        sel_p.select_option(value=pet.name)
        self.device.click('input[type=submit][value="Start Course"]', nav=True)
        return True

    def scan_pets(self, pets: list[Neopet], academy: str) -> list[Neopet]:
        rows = self.page.locator('.content >> table > tbody > tr > td')
        rows = rows.all()
        i = -1
        while i < len(rows):
            i += 1
            pet_name = next((p.name for p in pets if p.name in rows[i].text_content()), None)
            if not pet_name:
                continue
            infos = rows[i+1].locator('b').all()
            if len(infos) < 5:
                logger.warning(f"Parse pet info failed for {pet_name} in {academy} academy")
                continue
        self.current_pets.append(Neopet(
            name=pet_name,
            level=str2int(infos[0].text_content()),
            strength=str2int(infos[1].text_content()),
            defense=str2int(infos[2].text_content()),
            movement=str2int(infos[3].text_content()),
            max_health=str2int(infos[4].text_content().split('/')[-1]),
        ))
        msg = 'Current pet info:\n' + '\n'.join(
            f"{p.name} (Lv={p.level}, Str={p.strength}, Def={p.defense}, Mov={p.movement}, Hp={p.max_health})"
            for p in self.current_pets
        )
        logger.info(msg)

    def scan_fee(self):
        fees = []
        images = self.page.locator('.content >> img[src*="images.neopets.com/items/"]')
        for img in images.all():
            fees.append(NeoItem(
                name=img.locator('../..').text_content().strip(),
            ))
        return fees

    def is_capped(self, pet: Neopet, academy: str, attr: str) -> bool:
        if academy not in ACADEMY:
            logger.error(f"Unknown academy: {academy}")
            return True
        if attr == 'level':
            return pet.level >= ACADEMY[academy]['max_level']
        # hard cap is 850
        if attr == 'strength':
            return pet.strength >= min(850, ACADEMY[academy]['max_level']*2)
        if attr == 'defense':
            return pet.defense >= min(850, ACADEMY[academy]['max_level']*2)
        try:
            v = getattr(pet, attr)
        except AttributeError:
            logger.error(f"Unknown attribute: {attr}")
            return True
        return v >= ACADEMY[academy]['max_level']*2


if __name__ == '__main__':
    self = PetTrainingUI()
