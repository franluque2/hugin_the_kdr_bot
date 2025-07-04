import pymongo
from config.config import DB_ADDRESS, DB_KEY_SERVER, \
    DB_KEY_INSTANCE, DB_KEY_PLAYER, CWD, \
    PATH_STATIC_CLASSES, PATH_BASE_CLASSES, \
    PATH_BUCKETS, PATH_GENERIC_BUCKETS, PATH_CLASS_SKILLS, \
    PATH_TREASURES, PATH_GENERIC_SKILLS, DEFAULT_ELO_RANKING
from core.kdr_data import categories_buckets_generic, categories_buckets_class, categories_secret
from core.kdr_modifiers import get_modifier
from config.config import RPG_STATS

from json import load as json_load

# db client
db_client = pymongo.MongoClient(DB_ADDRESS)

# db
kdr_db = db_client['KdrBot']

# main collection
coll_kdr = kdr_db['KDRS']

# static class collection
coll_classes_static = kdr_db['static_classes']

# base class collection
coll_classes_base = kdr_db['base_classes']

# user collection
coll_users = kdr_db['users']

# inventory collection
coll_inventory = kdr_db['inventory']

# buckets collection
coll_buckets = kdr_db['buckets']

# treasures collection
coll_treasures = kdr_db['treasures']

# generic skills collection
coll_skills_generic = kdr_db['skills_generic']

# skills collection
coll_skills = kdr_db['skills']

# generic buckets collection
coll_buckets_generic = kdr_db['buckets_generic']

# possible instance names
instance_name_ids = {}

""" Instances """


def check_instance_exist(gid, iid):
    instance_exists = coll_kdr.find_one({DB_KEY_SERVER: gid,
                                         DB_KEY_INSTANCE: iid,
                                         "ended":False})
    if instance_exists is None:
        return False
    return True


async def get_instance(sid, iid):
    return coll_kdr.find_one({DB_KEY_SERVER: sid,
                              DB_KEY_INSTANCE: iid})


async def get_instance_value(sid, iid, key):
    return coll_kdr.find_one({DB_KEY_SERVER: sid,
                              DB_KEY_INSTANCE: iid}) \
        .get(key)


async def set_instance_value(sid, iid, key, value, operation: str = "$set"):
    coll_kdr.update_one({DB_KEY_SERVER: sid,
                         DB_KEY_INSTANCE: iid},
                        {operation: {key: value}})


async def get_instance_list(sid, iid, key):
    return list(coll_kdr.find_one({DB_KEY_SERVER: sid,
                                   DB_KEY_INSTANCE: iid})
                .get(key))


""""""

""" Users """


def check_user_exist(pid, gid):
    # check if the user already exists
    user_exists = coll_users.find_one({DB_KEY_PLAYER: pid,
                                       DB_KEY_SERVER: gid})
    if user_exists is not None:
        return True
    return False


def check_user_exist_in_instance(pid, gid, iid):
    # check if the user already exists in that instance id
    user_exists = coll_users.find_one({DB_KEY_PLAYER: pid,
                                       DB_KEY_SERVER: gid})
    if user_exists is not None:
        if iid in user_exists.get("instances"):
            return True
    return False


async def check_user_current_round(pid, sid, iid):
    instance = coll_kdr.find_one({DB_KEY_SERVER: sid,
                                  DB_KEY_INSTANCE: iid})
    curr_rounds = list(instance.get('current_rounds'))
    active_round = instance.get('active_round')

    for match in curr_rounds[active_round]:
        if match[0] == pid or match[1] == pid:
            return True

    return False


async def get_users_value(pid, sid, key):
    player = coll_users.find_one({DB_KEY_PLAYER: pid,
                                  DB_KEY_SERVER: sid})
    return player.get(key)


async def set_users_value(pid, sid, key, value, operation: str = "$set"):
    coll_users.update_one({DB_KEY_PLAYER: pid,
                           DB_KEY_SERVER: sid},
                          {operation: {key: value}})
    
async def get_all_users(sid):
    return coll_users.find({DB_KEY_SERVER: sid})


""""""

""" Inventory """


async def get_inventory(pid, sid, iid):
    return coll_inventory.find_one({DB_KEY_SERVER: sid,
                                    DB_KEY_INSTANCE: iid,
                                    DB_KEY_PLAYER: pid})


async def get_inventory_value(pid, sid, iid, key):
    player = coll_inventory.find_one({DB_KEY_SERVER: sid,
                                      DB_KEY_INSTANCE: iid,
                                      DB_KEY_PLAYER: pid})
    return player.get(key)


async def set_inventory_value(pid, sid, iid, key, value, operation="$set"):
    coll_inventory.update_one({DB_KEY_SERVER: sid,
                               DB_KEY_INSTANCE: iid,
                               DB_KEY_PLAYER: pid},
                              {operation: {key: value}})


async def set_all_inventory_value(sid, iid, key, value, operation="$set"):
    coll_inventory.update_many({DB_KEY_SERVER: sid,
                                DB_KEY_INSTANCE: iid},
                               {operation: {key: value}})


async def delete_player_inventory(pid, sid, iid):
    coll_inventory.delete_one({DB_KEY_SERVER: sid,
                               DB_KEY_INSTANCE: iid,
                               DB_KEY_PLAYER: pid})


""""""

""" Base Classes """


async def check_class_picked(sid, iid, kdr_class):
    picked_classes = list(coll_kdr.find_one({DB_KEY_SERVER: sid,
                                             DB_KEY_INSTANCE: iid})
                          .get('picked_classes'))

    if kdr_class in picked_classes:
        return True
    return False


async def get_all_base_classes(altformat=None, blacklist=None):
    query = {}
    if blacklist is None:
        blacklist = []

    if altformat is None:
        query = {"altformat": {"$exists": False}}
    else:
        # Handle multiple altformats, including "default"
        altformats = altformat.split(";")
        query = {"$or": [{"altformat": af} for af in altformats if af != "default"]}
        
        # Add default content to the query if "default" is included
        if "default" in altformats:
            query["$or"].append({"altformat": {"$exists": False}})

    base_classes = coll_classes_base.find(query)
    # Filter out blacklisted classes
    filtered_classes = []
    for base_class in base_classes:
        if base_class['id'] in blacklist:
            continue
        if all(echo in blacklist for echo in base_class.get('echos', [])):
            continue
        filtered_classes.append(base_class)

    return filtered_classes


async def get_base_class_value(cid, key):
    return coll_classes_base.find_one({'id': {"$eq": cid}}).get(key)


""""""

""" Static Classes """


async def get_all_static_classes(altformat=None, blacklist=None):
    query = {}
    if blacklist is None:
        blacklist = []

    if altformat is None:
        {"altformat": {"$exists": False}}
    else:
        # Handle multiple altformats, including "default"
        altformats = altformat.split(";")
        query = {"$or": [{"altformat": af} for af in altformats if af != "default"]}
        
        # Add default content to the query if "default" is included
        if "default" in altformats:
            query["$or"].append({"altformat": {"$exists": False}})

    static_classes = coll_classes_static.find(query)

    # Filter out blacklisted classes
    filtered_classes = []
    for static_class in static_classes:
        if static_class['id'] in blacklist:
            continue
        if static_class.get('base') in blacklist:
            continue
        filtered_classes.append(static_class)

    return filtered_classes


async def get_static_class(cid):
    return coll_classes_static.find_one({'id': {"$eq": cid}})

async def get_static_class_by_name(name):
    return coll_classes_static.find_one({'name': {"$eq": name}})



async def get_static_class_value(cid, key):
    return coll_classes_static.find_one({'id': {"$eq": cid}}).get(key)


""""""

""" Buckets """


async def get_bucket(bid):
    return coll_buckets.find_one({'id': {"$eq": bid}})


async def get_bucket_value(bid, key):
    return coll_buckets.find_one({'id': {"$eq": bid}}).get(key)


async def get_all_buckets(altformat=None):
    query = {}
    if altformat is None:
        return coll_buckets.find({"altformat": {"$exists": False}})
    
    # Handle multiple altformats, including "default"
    altformats = altformat.split(";")
    query = {"$or": [{"altformat": af} for af in altformats if af != "default"]}
    
    # Add default content to the query if "default" is included
    if "default" in altformats:
        query["$or"].append({"altformat": {"$exists": False}})
    
    return coll_buckets.find(query)


""""""

""" Bucket Categories """


async def get_bucket_category(bid, altformat=None):
    try:
        if altformat is None:
            return coll_buckets_generic.find_one({"altformat": {"$exists": False}}).get(bid)
        
        # Handle multiple altformats, including "default"
        altformats = altformat.split(";")
        for af in altformats:
            if af == "default":
                result = coll_buckets_generic.find_one({"altformat": {"$exists": False}})
            else:
                result = coll_buckets_generic.find_one({"altformat": {"$eq": af}})
            
            if result and bid in result:
                return result.get(bid)
        
        # Fallback if no altformat matches
        return []
    except Exception as e:
        print(f"Error retrieving bucket category: {e}")
        return []


async def get_bucket_category_value(bid, key):
    return coll_buckets_generic.find_one({'id': {"$eq": bid}}).get(key)


async def get_all_bucket_categories():
    return coll_buckets_generic.find()

async def get_generic_bucket_categories(kdr_format=None):
    if kdr_format is None:
        return categories_buckets_generic

    altformats = kdr_format.split(";")
    for af in altformats:
        if af == "default":
            result = categories_buckets_generic
        else:
            result = coll_buckets_generic.find_one({"altformat": {"$eq": af}})
        
        if result is not None and "categories_generic" in result:
            return result["categories_generic"]

    return categories_buckets_generic


async def get_class_bucket_categories(kdr_format=None):
    if kdr_format is None:
        return categories_buckets_class

    altformats = kdr_format.split(";")
    for af in altformats:
        if af == "default":
            result = categories_buckets_class
        else:
            result = coll_buckets_generic.find_one({"altformat": {"$eq": af}})
        
        if result is not None and "categories_class" in result:
            return result["categories_class"]

    return categories_buckets_class


async def get_secret_categories(kdr_format=None):
    if kdr_format is None:
        return categories_secret

    altformats = kdr_format.split(";")
    for af in altformats:
        if af == "default":
            result = categories_secret
        else:
            result = coll_buckets_generic.find_one({"altformat": {"$eq": af}})
        
        if result is not None and "categories_secret" in result:
            return result["categories_secret"]

    return categories_secret


""""""

""" Skills """


async def get_skill(sid):
    return coll_skills.find_one({'id': {"$eq": sid}})


async def get_all_generic_skills(altformat=None):
    query = {}
    if altformat is None:
        return coll_skills_generic.find({"altformat": {"$exists": False}})
    
    # Handle multiple altformats, including "default"
    altformats = altformat.split(";")
    query = {"$or": [{"altformat": af} for af in altformats if af != "default"]}
    
    # Add default content to the query if "default" is included
    if "default" in altformats:
        query["$or"].append({"altformat": {"$exists": False}})
    
    return coll_skills_generic.find(query)


async def get_skill_by_id(skill_id):
    skill = coll_skills.find_one({'id': {"$eq": skill_id}})
    if skill is None:
        gen_skill = coll_skills_generic.find_one({'id': {"$eq": skill_id}})
        return gen_skill
    return skill


async def get_skill_value(sid, key):
    return coll_skills.find_one({'id': {"$eq": sid}}).get(key)


""""""

""" Treasure """


async def get_treasure(tid):
    return coll_treasures.find_one({'id': {"$eq": tid}})


async def get_treasure_by_name(name):
    return coll_treasures.find_one({'name': {"$eq": name}})


async def get_treasures_by_rarity(rarity, altformat=None):
    if altformat is None:
        return coll_treasures.find({"rarity": rarity, "altformat": {"$exists": False}})
    
    altformats = altformat.split(";")
    query = {"$or": [{"rarity": rarity, "altformat": {"$eq": af}} for af in altformats if af != "default"]}
    
    if "default" in altformats:
        query["$or"].append({"rarity": rarity, "$and": {"altformat": {"$exists": False}}})
    
    return coll_treasures.find(query)



async def get_treasure_value(tid, key):
    return coll_treasures.find_one({'id': {"$eq": tid}}).get(key)


""""""

""" KDR """


async def add_new_kdr(sid: int, iid: str, is_ranked: False, creatorid: str, maxplayers: int, class_choices: int = 1, modifiers: str = ""):
    uid = 1 + len(list(coll_kdr.find({DB_KEY_SERVER: sid})))
    altformats = []

    # Extract altformats from modifiers using get_modifier
    altformats = get_modifier(modifiers, "ALTFORMAT")

    instance = {
        DB_KEY_SERVER: sid,
        DB_KEY_INSTANCE: iid,
        'uid': str(uid),
        'started': False,
        'players': 0,
        'player_names': [],
        'current_rounds': [[]],
        'round_results': [[]],
        'active_round': -1,
        'missing_matches': [],
        'picked_classes': [],
        'offered_classes': [],
        'is_ranked': is_ranked,
        'creator_id': creatorid,
        'ended': False,
        'max_players': maxplayers,
        'class_choices': class_choices,
        'modifiers': modifiers,
        'altformats': altformats,
        'round_type': ''
    }

    coll_kdr.insert_one(instance)


def add_user_to_kdr(pid, sid, iid, classes):
    user = {
        DB_KEY_SERVER: sid,
        DB_KEY_PLAYER: pid,
        'instances': [],
        'total_winloss': [0, 0],
        'elo': DEFAULT_ELO_RANKING,
        'previous_elo': DEFAULT_ELO_RANKING
    }

    user_inventory = {
        DB_KEY_SERVER: sid,
        DB_KEY_INSTANCE: iid,
        DB_KEY_PLAYER: pid,
        'class': '',
        'gold': 0,
        'XP': 0,
        'classes': classes,
        'skills': [],
        'loot': [],
        'treasures': [],
        'wl_ratio': [0, 0],
        'loss_streak': 0,
        'tip_threshold': 0,
        'total_tips': 0,
        'sheet_url': '',
        'shop_phase': False,
        'shop_stage': 0,
        'modifiers': [],
        'offered_skills': [],
        'offered_treasure': [],
        'offered_loot': [],
        'got_tip_skill': False,
        # Add all RPG stats dynamically
        **{stat: 0 for stat in RPG_STATS}
    }

    num_players = coll_kdr.find_one({DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid}).get("players")
    coll_users.insert_one(user)
    coll_inventory.insert_one(user_inventory)
    coll_users.update_one({DB_KEY_PLAYER: pid, DB_KEY_SERVER: sid}, {'$push': {'instances': iid}})
    coll_kdr.update_one({DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid},
                        {"$set": {'players': num_players + 1}})
    coll_kdr.update_one({DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid},
                        {"$push": {'player_names': pid}})


def update_user_to_kdr(pid, sid, iid, classes):
    coll_users.update_one({DB_KEY_PLAYER: pid, DB_KEY_SERVER: sid}, {'$push': {'instances': iid}})

    user_inventory = {
        DB_KEY_SERVER: sid,
        DB_KEY_INSTANCE: iid,
        DB_KEY_PLAYER: pid,
        'class': '',
        'gold': 0,
        'XP': 0,
        'classes': classes,
        'skills': [],
        'loot': [],
        'treasures': [],
        'wl_ratio': [0,0],
        'loss_streak': 0,
        'tip_threshold': 0,
        'total_tips': 0,
        'sheet_url': '',
        'shop_phase': False,
        'shop_stage': 0,
        'modifiers': [],
        'offered_skills': [],
        'offered_treasure': [],
        'offered_loot': [],
        'got_tip_skill': False,
        # Add all RPG stats dynamically
        **{stat: 0 for stat in RPG_STATS}
    }

    coll_inventory.insert_one(user_inventory)
    num_players = coll_kdr.find_one({DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid}).get("players")
    coll_kdr.update_one({DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid},
                        {"$set": {'players': num_players + 1}})
    coll_kdr.update_one({DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid},
                        {"$push": {'player_names': pid}})


async def add_match_rounds_to_kdr(sid, iid, rounds):
    curr_rounds = []
    curr_results = []
    for r in range(0, len(rounds)):
        curr_rounds.append([])
        curr_results.append([])
        curr_round = rounds[r]
        for m in range(0, len(curr_round)):
            curr_match = curr_round[m]
            curr_rounds[r].append((curr_match[0], curr_match[1]))
            curr_results[r].append((True, -1))

    coll_kdr.update_one({DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid},
                        {"$set": {'current_rounds': curr_rounds}})
    coll_kdr.update_one({DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid},
                        {"$set": {'round_results': curr_results}})


async def has_player_started_a_kdr(pid, sid):
    return bool(coll_kdr.find_one({'creator_id': pid,
                                   DB_KEY_SERVER: sid,
                                   'ended': False}))

def delete_kdr(sid,iid):
    coll_kdr.delete_one({DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid})

async def has_player_started_specific_kdr(pid, sid, iid):
    return bool(coll_kdr.find_one({'creator_id': pid,
                                   DB_KEY_SERVER: sid, DB_KEY_INSTANCE: iid}))


async def clear_db_data():
    coll_classes_base.delete_many({})
    coll_classes_static.delete_many({})
    coll_buckets.delete_many({})
    coll_buckets_generic.delete_many({})
    coll_skills.delete_many({})
    coll_skills_generic.delete_many({})
    coll_treasures.delete_many({})


async def clear_user_data():
    coll_users.delete_many({})

async def clear_kdr_data():
    coll_kdr.delete_many({})
    coll_inventory.delete_many({})

async def get_all_active_kdrs(sid):
    """
    Fetch all active KDRs for the given server ID.
    :param sid: Server ID
    :return: List of active KDRs
    """
    return list(coll_kdr.find({"id_server": sid, "started": True, "ended": False}))

