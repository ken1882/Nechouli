from collections import defaultdict
from email.policy import default

HUNGER_LEVEL = defaultdict(lambda: 10, {
    "dying": 0,
    "starving": 1,
    "famished": 2,
    "very hungry": 3,
    "hungry": 4,
    "not hungry": 5,
    "fine": 6,
    "satiated": 7,
    "full up": 8,
    "very full": 9,
    "bloated": 10,
    "very bloated": 11,
})
HUNGER_VALUE = {v: k for k, v in HUNGER_LEVEL.items()}

SHOP_NAME = defaultdict(lambda: "", {
    1: "fresh_foods",
    2: "magic_shop",
    3: "toy_shop",
    4: "unis_clothing_shop",
    5: "grooming_parlour",
    7: "magical_bookshop",
    8: "collectable_card_shop",
    9: "battle_magic",
    12: "neopian_garden_centre",
    14: "chocolate_factory",
    15: "the_bakery",
    16: "smoothie_shop",
    20: "tropical_food",
    25: "neopian_petpet_shop",
    34: "coffee_cave",
    35: "slushie_shop",
    39: "faerie_foods",
    40: "faerieland_petpets",
    41: "neopian_furniture",
    42: "tyrannian_foods",
    44: "tyrannian_petpets",
    46: "huberts_hotdogs",
    50: "peopatra_petpets",
    55: "osiris_pottery",
    56: "merifoods",
    57: "ye_olde_petpets",
    61: "wintery_petpets",
    81: "brightvale_fruits",
    95: "exquisite_ambrosia",
    97: "legendary_petpets",
    101: "exotic_foods",
    103: "fanciful_fauna"
})
