from module.alas import AzurLaneAutoScript
from module.logger import logger
from module.base.utils import (
    str2int,
    kill_remote_browser,
    get_all_instance_addresses,
    check_connection
)
from module.db import data_manager as dm
from module import hardware as hw
from pathlib import Path
from datetime import datetime
import random
import os
import time

class Nechouli(AzurLaneAutoScript):

    def __init__(self, config_name: str = 'nechouli'):
        super().__init__(config_name)

    def loop(self):
        self.start()
        try:
            super().loop()
        except Exception as e:
            logger.exception(e)

    def restart(self):
        from tasks.base.base_page import BasePageUI
        t = BasePageUI(config=self.config, device=self.device)
        t.goto('https://www.neopets.com/questlog/')
        t.calc_next_run()

    @property
    def lock_file(self):
        p = Path('.nch-lock-'+hw.hardware_hash()[::4])
        p.touch(exist_ok=True)
        return p

    def start(self):
        logger.info("Starting Nechouli")
        wt = 3 + ((os.getpid() % 97) / 800.0)
        dm.JN_CACHE_TTL = self.config.ProfileSettings_JellyNeoExpiry * 3600
        while self.is_concurrent_limit_reached(start=True):
            wt = min(300+random.randint(0, 100), random.uniform(wt * 0.9, wt * 1.5))
            logger.warning(f"Concurrent limit reached, waiting for {round(wt, 3)} seconds")
            time.sleep(wt)
        while True:
            try:
                self.device.goto('https://www.neopets.com/questlog/')
            except Exception as e:
                logger.error(f"Failed to navigate to quest log: {e}")
                self.device.respawn_page()
                continue
            break
        loading = self.device.page.locator('#QuestLogLoader')
        logger.info("Waiting for quest log to load")
        depth = 0
        while loading.is_visible():
            self.device.wait(0.3)
            depth += 1
            if depth > 30:
                logger.warning("Quest log loading timeout, assume loaded")
                break
        self.device.wait(1) # quest won't start if not visited
        if self.config.Playwright_CleanPagesOnStart or self.config.Playwright_Headless:
            self.device.clean_redundant_pages()

    def stop(self):
        logger.info("Stopping Nechouli")
        killed = kill_remote_browser(self.config.config_name)
        logger.info(f"Killed browser process: {killed}")

    def is_concurrent_limit_reached(self, start=False):
        if self.config.Optimization_MaxConcurrentInstance <= 0:
            if start:
                self.device.start_browser()
            return False
        logger.info("Checking running instances")
        msg = ''
        addresses = []
        def _quickmath(
                n,
                magic=1.2,               # magic number
                backoff=(0.02, 0.08),    # retry jitter window (min,max) seconds
                safety=1.75,             # safety multiplier s
                tmin=3,
                tmax=86400,
            ):
            n = max(1, n)
            b = 0.5 * (backoff[0] + backoff[1])
            H = magic * n
            t = safety * n * (H + b)
            return max(tmin, min(tmax, t))

        instances = get_all_instance_addresses()
        with dm.dlock(self.lock_file, timeout=_quickmath(len(instances))):
            for profile_name, addr in instances.items():
                msg += f"{profile_name} ({addr})"
                if check_connection(addr, timeout=0.1):
                    addresses.append(addr)
                    msg += ': O\n'
                else:
                    msg += ': X\n'
            logger.info(f"Running count: {len(addresses)}\n{msg}")
            if len(addresses) >= self.config.Optimization_MaxConcurrentInstance:
                return True
            elif start:
                self.device.start_browser()
        return False

    def goto_main(self):
        self.device.goto('https://www.neopets.com/home')

    def altador_council(self):
        from tasks.daily.altador_council import AltadorCouncilUI
        AltadorCouncilUI(config=self.config, device=self.device).run()

    def anchor_management(self):
        from tasks.daily.anchor_management import AnchorManagementUI
        AnchorManagementUI(config=self.config, device=self.device).run()

    def apple_bobbing(self):
        from tasks.daily.apple_bobbing import AppleBobbingUI
        AppleBobbingUI(config=self.config, device=self.device).run()

    def bank_interest(self):
        from tasks.daily.bank_interest import BankInterestUI
        BankInterestUI(config=self.config, device=self.device).run()

    def coltzans_shrine(self):
        from tasks.daily.coltzans_shrine import ColtzansShrineUI
        ColtzansShrineUI(config=self.config, device=self.device).run()

    def daily_puzzle(self):
        from tasks.daily.daily_puzzle import DailyPuzzleUI
        DailyPuzzleUI(config=self.config, device=self.device).run()

    def deserted_tomb(self):
        from tasks.daily.deserted_tomb import DesertedTombUI
        DesertedTombUI(config=self.config, device=self.device).run()

    def faerie_crossword(self):
        from tasks.daily.faerie_crossword import FaerieCrosswordUI
        FaerieCrosswordUI(config=self.config, device=self.device).run()

    def fishing(self):
        from tasks.daily.fishing import FishingUI
        FishingUI(config=self.config, device=self.device).run()

    def forgotten_shore(self):
        from tasks.daily.forgotten_shore import ForgottenShoreUI
        ForgottenShoreUI(config=self.config, device=self.device).run()

    def fruit_machine(self):
        from tasks.daily.fruit_machine import FruitMachineUI
        FruitMachineUI(config=self.config, device=self.device).run()

    def giant_jelly(self):
        from tasks.daily.giant_jelly import GiantJellyUI
        GiantJellyUI(config=self.config, device=self.device).run()

    def giant_omelette(self):
        from tasks.daily.giant_omelette import GiantOmeletteUI
        GiantOmeletteUI(config=self.config, device=self.device).run()

    def grave_danger(self):
        from tasks.daily.grave_danger import GraveDangerUI
        GraveDangerUI(config=self.config, device=self.device).run()

    def grumpy_king(self):
        from tasks.daily.grumpy_king import GrumpyKingUI
        GrumpyKingUI(config=self.config, device=self.device).run()

    def wise_king(self):
        from tasks.daily.wise_king import WiseKingUI
        WiseKingUI(config=self.config, device=self.device).run()

    def lunar_temple(self):
        from tasks.daily.lunar_temple import LunarTempleUI
        LunarTempleUI(config=self.config, device=self.device).run()

    def negg_cave(self):
        from tasks.daily.negg_cave import NeggCaveUI
        NeggCaveUI(config=self.config, device=self.device).run()

    def meteor_crash_site(self):
        from tasks.daily.meteor_crash_site import MeteorCrashSiteUI
        MeteorCrashSiteUI(config=self.config, device=self.device).run()

    def potato_counter(self):
        from tasks.daily.potato_counter import PotatoCounterUI
        PotatoCounterUI(config=self.config, device=self.device).run()

    def rich_slorg(self):
        from tasks.daily.rich_slorg import RichSlorgUI
        RichSlorgUI(config=self.config, device=self.device).run()

    def qasalan_expellibox(self):
        from tasks.daily.qasalan_expellibox import QasalanExpelliboxUI
        QasalanExpelliboxUI(config=self.config, device=self.device).run()

    def tdmbgpop(self):
        from tasks.daily.tdmbgpop import TDMBGPOPUI
        TDMBGPOPUI(config=self.config, device=self.device).run()

    def tombola(self):
        from tasks.daily.tombola import TombolaUI
        TombolaUI(config=self.config, device=self.device).run()

    def trudys_surprise(self):
        from tasks.daily.trudys_surprise import TrudysSurpriseUI
        TrudysSurpriseUI(config=self.config, device=self.device).run()

    def snowager(self):
        from tasks.daily.snowager import SnowagerUI
        SnowagerUI(config=self.config, device=self.device).run()

    def moltara_quarry(self):
        from tasks.daily.moltara_quarry import MoltaraQuarryUI
        MoltaraQuarryUI(config=self.config, device=self.device).run()

    def pet_cares(self):
        from tasks.daily.pet_cares import PetCaresUI
        PetCaresUI(config=self.config, device=self.device).run()

    def fashion_fever(self):
        from tasks.games.fashion_fever import FashionFeverUI
        FashionFeverUI(config=self.config, device=self.device).run()

    def quick_stock(self):
        from tasks.utility.quick_stock import QuickStockUI
        QuickStockUI(config=self.config, device=self.device).run()

    def healing_spring(self):
        from tasks.daily.healing_spring import HealingSpringUI
        HealingSpringUI(config=self.config, device=self.device).run()

    def restocking(self):
        from tasks.utility.restocking import RestockingUI
        RestockingUI(config=self.config, device=self.device).run()

    def daily_quest(self):
        from tasks.daily.daily_quest import DailyQuestUI
        DailyQuestUI(config=self.config, device=self.device).run()

    def monthly_freebies(self):
        from tasks.daily.monthly_freebies import MonthlyFreebiesUI
        MonthlyFreebiesUI(config=self.config, device=self.device).run()

    def stock_market(self):
        from tasks.daily.stock_market import StockMarketUI
        StockMarketUI(config=self.config, device=self.device).run()

    def voids_within(self):
        from tasks.utility.voids_within import VoidsWithinUI
        VoidsWithinUI(config=self.config, device=self.device).run()

    def shop_wizard(self):
        from tasks.utility.shop_wizard import ShopWizardUI
        ShopWizardUI(config=self.config, device=self.device).run()

    def essence_collection(self):
        from tasks.daily.essence_collection import EssenceCollectionUI
        EssenceCollectionUI(config=self.config, device=self.device).run()

    def safety_deposit_box(self):
        from tasks.utility.safety_deposit_box import SafetyDepositBoxUI
        SafetyDepositBoxUI(config=self.config, device=self.device).run()

    def pet_training(self):
        from tasks.daily.pet_training import PetTrainingUI
        PetTrainingUI(config=self.config, device=self.device).run()

    def battle_dome(self):
        from tasks.daily.battledome import BattleDomeUI
        BattleDomeUI(config=self.config, device=self.device).run()

    def auction(self):
        from tasks.utility.auction import AuctionUI
        AuctionUI(config=self.config, device=self.device).run()

    def scratchcard(self):
        from tasks.daily.scratchcard import ScratchcardUI
        ScratchcardUI(config=self.config, device=self.device).run()


if __name__ == '__main__':
    nch = Nechouli()
    nch.loop()
