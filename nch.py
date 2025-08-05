from module.alas import AzurLaneAutoScript
from module.logger import logger



class Nechouli(AzurLaneAutoScript):

    def __init__(self, config_name: str = 'nechouli'):
        super().__init__(config_name)

    def loop(self):
        self.device.start_browser()
        self.device.page.goto('https://www.neopets.com/questlog/')
        self.device.wait(3) # quest won't start if not visited
        self.device.clean_redundant_pages()
        try:
            super().loop()
        except Exception as e:
            pass

    def restart(self):
        from tasks.base.base_page import BasePageUI
        t = BasePageUI(config=self.config, device=self.device)
        t.goto('https://www.neopets.com/questlog/')
        t.calc_next_run()

    def start(self):
        pass

    def stop(self):
        pass

    def goto_main(self):
        pass

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


if __name__ == '__main__':
    nch = Nechouli()
    nch.loop()
