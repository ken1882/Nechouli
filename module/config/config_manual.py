from pywebio.io_ctrl import Output

import module.config.server as server


class ManualConfig:
    @property
    def LANG(self):
        return server.lang

    SCHEDULER_PRIORITY = """
    Restart
    > DesertedTomb > FaerieCrossword
    > AltadorCouncil > AnchorManagement > AppleBobbing > BankInterest > ColtzansShrine
    > DailyPuzzle > Fishing > ForgottenShore > FruitMachine > GiantJelly
    > GiantOmelette > GraveDanger > GrumpyKing > WiseKing > LunarTemple
    > NeggCave > MeteorCrashSite > PotatoCounter > RichSlorg > QasalanExpellibox
    > TDMBGPOP > Tombola > TrudysSurprise > Snowager > MoltaraQuarry
    > PetCares
    """

    """
    module.assets
    """
    ASSETS_FOLDER = './assets'
    ASSETS_MODULE = './tasks'
    ASSETS_RESOLUTION = (1280, 720)

    """
    module.base
    """
    COLOR_SIMILAR_THRESHOLD = 10
    BUTTON_OFFSET = (20, 20)
    BUTTON_MATCH_SIMILARITY = 0.85
    WAIT_BEFORE_SAVING_SCREEN_SHOT = 1

    """
    module.device
    """
    DEVICE_OVER_HTTP = False
    FORWARD_PORT_RANGE = (20000, 21000)
    REVERSE_SERVER_PORT = 7903

class OutputConfig(Output, ManualConfig):
    def __init__(self, spec, on_embed=None):
        if 'content' in spec:
            content = spec['content']
        super().__init__(spec, on_embed)
