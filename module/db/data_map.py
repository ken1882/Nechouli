from collections import defaultdict

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
