from enum import Enum


class WinType(Enum):
    WIN_2X0 = 1
    WIN_2X1 = 2
    WIN_DEFAULT = 3
    INCOMPLETE = -1


class SpecialClassHandling(Enum):
    CLASS_MIMIC = 1001
    CLASS_PIRATE = 1002
    CLASS_GAMBLER = 1003

class SpecialTypeHandling(Enum):
    GAMBLER_5050_SKILL = 3000

class SpecialSkillHandling(Enum):
    SKILL_PIRATE_SOUL = 1
    SKILL_GREED_IS_GOOD = 2
    SKILL_PROFESSIONAL_DUELIST = 3
    SKILL_HEAVY_SACK = 4
    SKILL_BARGAIN = 5
    SKILL_HIDDEN_WARES = 6
    SKILL_SILVER_TONGUE = 7
    SKILL_BINGO_MACHINE_GO = 8
    SKILL_SUPER_SMOOTH_TALKER = 9
    SKILL_PLUNDERED_BOOTY = 10


class SpecialSkillNames(Enum):
    SKILL_SUPER_SMOOTH_TALKER = "super_smooth_talker"

#KDR Modifier Names
class KdrModifierNames(Enum):
    LOSE_GOLD_AT_END="USEITORLOSEIT"
    GOLD_PER_ROUND="GOLDPERROUND"
    NO_INTEREST="NOINTEREST"
    NO_TRAINING="SKIPGYM"
    IGNORE_CLASSES="ANARCHY"
    REVERSE_RUN="REVERSERUN"
    ALTERNATE_FORMAT="ALTFORMAT"
    BLACKLIST_CLASS="BLACKLIST"
    ALLOW_DUPLICATES="ALLOWDUPES"

#Whether the kdr modifiers return a value
KDR_MODIFIERS = {
    "USEITORLOSEIT": False,
    "GOLDPERROUND": True,
    "NOINTEREST": False,
    "SKIPGYM": False,
    "ANARCHY": False,
    "REVERSERUN": False,
    "ALTFORMAT": True,
    "BLACKLIST": True,
    "ALLOWDUPES": False

}

type_converter = {
    "staples": "Staples",
    "removal": "Removal/Disruption",
    "engine": "Engine",
    "powercard": "Power Cards",
    "low_qual": "Class Low Quality",
    "mid_qual": "Class Mid Quality",
    "high_qual": "Class High Quality"
}

rarity_converter = {
    "common": "Common",
    "rare": "Rare",
    "ultra_rare": "Ultra Rare",
    "secret_rare": "Secret Rare",
    "super_rare": "Super Rare"
}

# Categories for Buckets, [category id, Cost, How many buckets to show, at which level does it unlock]
categories_buckets_generic = [["staples", 3, 3, 1], ["removal", 5, 3, 3], ["engine", 7, 2, 3]]
categories_buckets_class = [["low_qual", 10, 1, 0], ["mid_qual", 5, 2, 0], ["high_qual", 10, 2, 6]]
categories_secret=[] #["powercard", 10, 1, 2] removed for balance concerns
