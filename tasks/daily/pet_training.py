from module.logger import logger
from tasks.base.base_page import BasePageUI
from tasks.utility.quick_stock import QuickStockUI
from tasks.utility.safety_deposit_box import SafetyDepositBoxUI
from module.db.models.neopet import Neopet
from module.db.models.neoitem import NeoItem
from module.base.utils import str2int
from module.config.utils import nearest_future
from datetime import datetime, timedelta

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
        aca_pets = {
            'pirate': [],
            'island': [],
            'ninja': []
        }
        self.complete_times = []
        for conf in configs:
            pet_name, academy, target_lv, target_str, target_def, target_mov, target_hp = conf.split(':')
            if academy not in ACADEMY:
                logger.error(f'Unknown academy: {academy}')
                continue
            aca_pets[academy].append(Neopet(
                name=pet_name,
                level=int(target_lv),
                max_health=int(target_hp),
                strength=int(target_str),
                defense=int(target_def),
                movement=int(target_mov),
            ))
        self.config.stored.PendingTrainingFee.clear()
        trained = []
        msg = 'Goal training status:\n'
        msg += '\n'.join(
            (
                f"{p.name} Lv={p.level}, Str={p.strength}, "
                f"Def={p.defense}, Mov={p.movement}, Hp={p.max_health}, "
                f"Academy={academy}"
            )
            for academy, pets in aca_pets.items() for p in pets
        )
        logger.info(msg)
        for academy, pets in aca_pets.items():
            if not pets:
                continue
            self.goto(ACADEMY[academy]['url'])
            completed = self.page.locator('input[type=submit][value="Complete Course!"]')
            while completed.count():
                logger.info("Completing course for %s academy", academy)
                self.device.click(completed.first, nav=True)
                self.goto(ACADEMY[academy]['url'])
                completed = self.page.locator('input[type=submit][value="Complete Course!"]')
            self.scan_pets(pets, academy=academy)
            for pet in pets:
                self.train_pet(pet, academy)
            fees = self.scan_fee(academy)
            if fees:
                trained.append(academy)
            self.config.stored.PendingTrainingFee.add(*fees)
        missings = {}
        if self.config.stored.PendingTrainingFee:
            missings = self.fetch_training_fee()
            for aca in trained:
                logger.info(f"Paying training fee for {aca} academy")
                self.pay_training_fee(aca)
        if missings and self.config.PetTraining_BuyFeeFromPlayers:
            msg = "Buying missing items from players:\n"
            for item_name, amount in missings.items():
                self.config.stored.ShopWizardRequests.add(item_name, 'training', amount)
                msg += f"{item_name}: {amount}\n"
            logger.info(msg)
            self.config.task_call('ShopWizard')
            return False
        for academy, pets in aca_pets.items():
            self.complete_times += self.scan_training_time(academy)
        return True

    def train_pet(self, desired_pet: Neopet, academy: str):
        attrs = [attr.strip().lower() for attr in self.config.PetTraining_TrainPriority.split('>')]
        target_course = ''
        pet = next((p for p in self.current_pets if p.name == desired_pet.name), None)
        if not pet:
            logger.warning(f"Pet {desired_pet.name} not found in current pets, skipping training.")
            return False
        if pet.training:
            logger.info(f"Pet {pet.name} is already training, skipping.")
            return False
        for a in attrs:
            if self.is_capped(pet, academy, ATTR_CONF_TABLE[a]):
                continue
            target_course = a
            break
        if self.is_overstated(pet):
            if pet.level >= ACADEMY[academy]['max_level']:
                logger.info(f"Pet {pet.name} is capped at max level and overstated, skipping training.")
                return False
            target_course = 'lv'
        if not target_course:
            logger.info(f"Pet {pet.name} is already capped in all attributes in {academy} academy, skipping training.")
            return False
        logger.info(f"Training pet {pet.name} in {academy} academy for {target_course}.")
        self.goto(ACADEMY[academy]['url'].split('?')[0] + '?type=courses')
        sel = self.page.locator('select[name=course_type]')
        self.device.scroll_to(loc=sel)
        sel.select_option(value=ATTR_COURSE_TABLE[target_course])
        sel_p = self.page.locator('select[name=pet_name]')
        sel_p.select_option(value=pet.name)
        self.device.click('input[type=submit][value="Start Course"]', nav=True)
        return True

    def scan_pets(self, pets: list[Neopet], academy: str) -> list[Neopet]:
        self.current_pets = []
        rows = self.page.locator('.content >> table > tbody > tr > td')
        rows = rows.all()
        i = -1
        msg = 'Current pet info:\n'
        while i < len(rows)-1:
            i += 1
            pet_name = next((p.name for p in pets if p.name in rows[i].text_content()), None)
            if not pet_name or any(p.name == pet_name for p in self.current_pets):
                continue
            infos = rows[i+1].locator('b').all()
            if len(infos) < 5:
                logger.warning(f"Parse pet info failed for {pet_name} in {academy} academy")
                continue
            p = Neopet(
                name=pet_name,
                level=str2int(infos[0].text_content()),
                strength=str2int(infos[1].text_content()),
                defense=str2int(infos[2].text_content()),
                movement=str2int(infos[3].text_content()),
                max_health=str2int(infos[4].text_content().split('/')[-1]),
                training=False,
            )
            if 'currently studying' in rows[i].text_content():
                p.training = True
            self.current_pets.append(p)
            msg += f"{p.name} (Lv={p.level}, Str={p.strength}, Def={p.defense}, Mov={p.movement}, Hp={p.max_health})\n"
        if self.current_pets:
            logger.info(msg)

    def scan_fee(self, academy):
        self.goto(ACADEMY[academy]['url'])
        fees = []
        images = self.page.locator('.content >> img[src*="images.neopets.com/items/"]')
        for img in images.all():
            tr = img.locator('../..')
            td = tr.locator('../../..')
            fees.append(NeoItem(
                name=tr.text_content().strip(),
                _pay_bb=td.locator('input[type=submit][value="Pay"]').bounding_box(),
            ))
        return fees

    def is_overstated(self, pet: Neopet) -> bool:
        lv = pet.level
        attrs = ['max_health', 'strength', 'defense', 'movement']
        return any(getattr(pet, a) > lv*2 for a in attrs)

    def is_capped(self, pet: Neopet, academy: str, attr: str) -> bool:
        if academy not in ACADEMY:
            logger.error(f"Unknown academy: {academy}")
            return True
        if attr == 'level':
            return pet.level >= ACADEMY[academy]['max_level']
        # hard cap is 850
        if attr == 'strength':
            return pet.strength >= min(850, ACADEMY[academy]['max_level']*2, pet.level*2)
        if attr == 'defense':
            return pet.defense >= min(850, ACADEMY[academy]['max_level']*2, pet.level*2)
        try:
            v = getattr(pet, attr)
        except AttributeError:
            logger.error(f"Unknown attribute: {attr}")
            return True
        return v >= min(ACADEMY[academy]['max_level']*2, pet.level*2)

    def fetch_training_fee(self) -> dict[str, int]:
        logger.info("Running Quick Stock to update inventory data")
        QuickStockUI(self.config, self.device).run()
        required_items = {}
        for item in self.config.stored.PendingTrainingFee:
            if item.name not in required_items:
                required_items[item.name] = 0
            required_items[item.name] += 1
        for item in self.config.stored.InventoryData:
            if item.name in required_items:
                required_items[item.name] -= 1
        if all(v <= 0 for v in required_items.values()):
            logger.info("All required items are available for training.")
        else:
            logger.info("Some required items are missing for training, scanning SDB")
        # Scan Safety Deposit Box for missing items
        sdb = SafetyDepositBoxUI(self.config, self.device)
        _, missings = sdb.retrieve_items(required_items)
        if missings:
            msg = "Missing items for training:\n" + '\n'.join(
                f"{item}: {count}" for item, count in missings.items()
            )
            logger.warning(msg)
        return missings

    def pay_training_fee(self, academy: str):
        QuickStockUI(self.config, self.device).update_inventory_data()
        self.goto(ACADEMY[academy]['url'])
        fees = self.scan_fee(academy)
        logger.info(f"Found {len(fees)} pending fees to pay.")
        for fee in fees:
            for item in self.config.stored.InventoryData:
                if item.name != fee.name or item.quantity == 0:
                    continue
                self.device.scroll_to(0, 0)
                self.device.wait(0.3)
                item.quantity -= 1
                self.device.click(fee._pay_bb, nav=True)
                logger.info(f"Paid item {fee.name} for training fee.")
                self.config.stored.PendingTrainingFee.remove(fee)
                self.config.stored.InventoryData.remove(item)

    def scan_training_time(self, academy: str) -> list[datetime]:
        if academy not in ACADEMY:
            logger.error(f"Unknown academy: {academy}")
            return []
        self.goto(ACADEMY[academy]['url'])
        logger.info(f"Scanning training time for {academy} academy")
        training_times = []
        for t in self.page.locator('td', has_text='till course finishes').all():
            text = t.text_content().strip()
            segs = text.split(':')[-1].split(',')
            finish_time = datetime.now()
            logger.info(f"Training time left: {segs}")
            for seg in segs:
                if 'hr' in seg or 'hour' in seg:
                    finish_time += timedelta(hours=str2int(seg))
                elif 'min' in seg:
                    finish_time += timedelta(minutes=str2int(seg))
                elif 'sec' in seg:
                    finish_time += timedelta(seconds=str2int(seg))
            if finish_time > datetime.now():
                training_times.append(finish_time)
        return training_times

    def calc_next_run(self, s=''):
        if s:
            return super().calc_next_run(s)
        if not self.complete_times:
            return super().calc_next_run()
        next_time = nearest_future(self.complete_times)
        self.config.task_delay(target=next_time)

if __name__ == '__main__':
    self = PetTrainingUI()
