from discord import Object
from os import getcwd

# server
CLEAR_COMMANDS = False
CLEAR_COMMANDS_GLOBAL = False
OOPS = '__**Oops!**__\n'

# db
DB_ADDRESS = "mongodb://localhost:27017/"
DB_KEY_SERVER = 'id_server'
DB_KEY_INSTANCE = 'id_instance'
DB_KEY_PLAYER = 'id_player'

# current working directory and paths
CWD = getcwd()
PATH_INSTANCE_NAMES = '/config/instance_names.json'
PATH_STATIC_CLASSES = 'static_classes.json'
PATH_BASE_CLASSES = 'base_classes.json'
PATH_BUCKETS = 'buckets.json'
PATH_BUCKET_SKILLS = 'bucket_skills.json'
PATH_CLASS_SKILLS = 'class_skills.json'
PATH_GENERIC_BUCKETS = 'generic_buckets.json'
PATH_GENERIC_SKILLS = 'generic_skills.json'
PATH_TREASURES = 'treasures.json'

# roles
ROLE_ADMIN = "KDR-Admin"
ROLE_CODER = "DISTANT"
ROLE_OWNER = "Owners"
ROLE_PLAYER = "kdr-player"
ROLE_LFG = "kdr-lfg"


# kdr settings

# default elo rank
DEFAULT_ELO_RANKING = 1500

# level thresholds in which to give a level
LVL_THRESHOLDS = [2, 6, 8, 10, 14, 18, 22, 24, 28, 30]

# free xp given per round played
XP_PER_ROUND = 2

# gold paid per chunk of xp
GOLD_PER_XP = 5

# xp gained per chunk of gold spent
XP_PER_GOLD_SPENT = 2

# max level a stat can have
MAX_RPG_STAT_LEVEL = 12

# level thresholds in which to give a level
LEVEL_THRESHOLDS = [2, 6, 8, 10, 14, 18, 22, 24, 28, 30]

# gold cost to skip a skillpick and instead gain another stack of a skill
GOLD_COST_UPGRADE = 5

# gold needed per interest threshold
GOLD_INTEREST_REQUIRED = 5

# gold gained per interest threshold
GOLD_INTEREST_GAINED = 2

# gold gained per interest threshold with greed is good
GOLD_INTEREST_GAINED_GREED_IS_GOOD = 4

# gold gained on win
GOLD_WIN_GAINED = 10

# gold gained on loss
GOLD_LOSS_GAINED = 10

# gold gained with professional duelist
GOLD_WIN_GAINED_PROFESSIONAL_DUELIST = 15

# loss streak extra gold
LOSS_STREAK_EXTRA_GOLD = [0, 0, 4, 8, 10]

# gold in heavy sack
HEAVY_SACK_EXTRA_GOLD = 2

# ban list link
BANLIST_LINK = "https://sites.google.com/view/ygodungeonrun/banlist"


# Stuff for the About Message
DEV_ID=123870790713212934
CREATORS_IDS=[237634316731940876, 111522518451441664]
REPO_URL="https://github.com/franluque2/hugin_the_kdr_bot"
ABOUT_MSG=f"Hi, I am Hugin! A bot to run Roguelike Yugioh Experiences Known as KDRs! \n \
            Created and maintained by <@{DEV_ID}>\n \
            Based on the Game Design work of <@{CREATORS_IDS[0]}> and <@{CREATORS_IDS[1]}>\n\n\
            I am Open Source! Check me out at {REPO_URL}"