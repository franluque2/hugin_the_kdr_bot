import random
import core.kdr_data as kdr_data
import core.kdr_errors as kdr_errors
import math

from random import randint
from json import load as json_load
from core import kdr_db as db
from config.config import CWD, PATH_INSTANCE_NAMES, GOLD_INTEREST_REQUIRED, \
    GOLD_INTEREST_GAINED, LOSS_STREAK_EXTRA_GOLD, GOLD_WIN_GAINED_PROFESSIONAL_DUELIST, \
    GOLD_WIN_GAINED, HEAVY_SACK_EXTRA_GOLD, GOLD_LOSS_GAINED
from discord import Interaction, Embed
from core.kdr_data import SpecialSkillHandling, KdrModifierNames
from core.kdr_modifiers import get_modifier

from config.secret_values import GUILD, SERVER_WHITELIST

""" Try Open JSON """


async def try_open_json(path: str = ""):
    file = None
    try:
        file = open(f'{CWD}{path}')
        return file, True
    except IOError as e:
        print(f"Couldn't open file ({e})")
        return file, False

""""""

""" Server Whitelisted Check"""


def server_whitelisted(interaction=Interaction):
    sid = interaction.guild_id
    is_whitelisted = sid in SERVER_WHITELIST
    if is_whitelisted:
        return True
    raise kdr_errors.ServerNotWhitelistedError()


""""""

""" Instance Exists Check """


async def instance_exists(interaction=Interaction):
    sid = interaction.guild_id
    iid=""
    if "options" in interaction.data:
        iid = interaction.data['options'][0]['value']
    if iid=="":
        player_kdrs=await db.get_users_value(str(interaction.user.id),sid,"instances")
        if len(player_kdrs)==1:
            iid=player_kdrs[0]
    # check if instance exists for this server
    if not db.check_instance_exist(sid, iid):
        raise kdr_errors.InstanceDoesNotExistError(iid)
    return True


""""""

""" Instance Started Check"""


async def instance_started(interaction=Interaction):
    pid, sid, iid = await get_player_data(interaction)
    res_started = await db.get_instance_value(sid, iid, 'started')
    if res_started:
        return True
    raise kdr_errors.InstanceNotStartedError(iid)


""""""

""" Instance Not Started Check"""


async def instance_not_started(interaction=Interaction):
    pid, sid, iid = await get_player_data(interaction)
    res_started = await db.get_instance_value(sid, iid, 'started')
    if res_started:
        raise kdr_errors.InstanceStartedError(iid)
    return True


""""""

""" Player Exists """


async def player_not_exist_instance(interaction=Interaction):
    # check if the user already exists in that instance id
    pid, sid, iid = await get_player_data(interaction)
    if db.check_user_exist_in_instance(pid, sid, iid):
        raise kdr_errors.PlayerAlreadyJoinedError(iid)
    return True


""""""

""" Player Has Character Sheet """


async def player_has_character_sheet(interaction=Interaction):
    # check if the user already exists in that instance id
    pid, sid, iid = await get_player_data(interaction)
    charsheetlink = await db.get_inventory_value(pid, sid, iid, 'sheet_url')
    if len(charsheetlink) != 0:
        return True
    raise kdr_errors.PlayerHasNoCharacterSheetError(iid)


""""""

""" Player Doesn't Exist """


async def player_exist_instance(interaction=Interaction):
    # check if the user already exists in that instance id
    pid, sid, iid = await get_player_data(interaction)
    if db.check_user_exist_in_instance(pid, sid, iid):
        return True
    raise kdr_errors.PlayerNotInInstanceError(iid)


""""""

""" Player Hasn't picked a class yet """


async def player_has_no_class_selection(interaction=Interaction):
    # check if the user already exists in that instance id
    pid, sid, iid = await get_player_data(interaction)
    classes = await db.get_inventory_value(pid, sid, iid, 'class')
    if len(classes) == 0:
        return True
    raise kdr_errors.PlayerHasClassAlreadyError(iid)


""""""

""" Player Has Class selected """


async def player_has_class_selection(interaction=Interaction):
    # check if the user already exists in that instance id
    pid, sid, iid = await get_player_data(interaction)
    classes = await db.get_inventory_value(pid, sid, iid, 'class')
    if len(classes) != 0:
        return True
    raise kdr_errors.PlayerHasNoClassError(iid)


""""""

""" Player In Round """


async def player_in_round(interaction=Interaction):
    pid, sid, iid = await get_player_data(interaction)
    res_user_round = await db.check_user_current_round(pid, sid, iid)
    if not res_user_round:
        raise kdr_errors.PlayerNotInRoundError(iid)
    return True


""""""

""" KDR Instance ID to Name """


def generate_instance_name(sid):
    """
    Generate a unique KDR instance name by combining 3-4 random words from a word list.
    :param sid: Server ID
    :return: Unique KDR instance name
    """
    # Load the word list from the JSON file
    with open(f'{CWD}{PATH_INSTANCE_NAMES}', 'r') as file:
        word_list = json_load(file)

    # Generate a unique name
    while True:
        # Combine 3-4 random words
        name_parts = random.sample(word_list, random.randint(3, 4))
        instance_name = ''.join(name_parts)

        # Check if the name is unique in the database
        if not db.check_instance_exist(sid, instance_name):
            return instance_name


""""""

""" KDR Player Data Interaction """


async def get_player_data(interaction=Interaction):
    sid = interaction.guild_id
    pid = str(interaction.user.id)

    iid=""
    if "options" in interaction.data:
        iid = interaction.data['options'][0]['value']
    else:
        player_kdrs=await db.get_users_value(pid,sid,"instances")
        if len(player_kdrs)==1:
            iid=player_kdrs[0]
    return pid, sid, iid


""""""

""" Get Random Class Selection """


async def get_class_selection(sid, iid):
    offered = []
    offered_classes = await db.get_instance_list(sid, iid, 'offered_classes')
    class_list = []
    modifiers = await db.get_instance_value(sid, iid, "modifiers")

    # Check for blacklist modifier
    blacklist = []
    if modifiers and get_modifier(modifiers, KdrModifierNames.BLACKLIST_CLASS.value) is not None:
        blacklist = get_modifier(modifiers, KdrModifierNames.BLACKLIST_CLASS.value).split(";")

    # Fetch base classes
    if modifiers and get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value) is not None:
        class_list = list(await db.get_all_base_classes(get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value), blacklist))
    else:
        class_list = list(await db.get_all_base_classes(blacklist=blacklist))

    # Fetch static classes
    static_classes = []
    if modifiers and get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value) is not None:
        static_classes = list(await db.get_all_static_classes(get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value), blacklist))
    else:
        static_classes = list(await db.get_all_static_classes(blacklist=blacklist))

    choicenum = await db.get_instance_value(sid, iid, 'class_choices')
    if choicenum is None:
        choicenum = 1
    random.shuffle(class_list)

    for c in class_list:
        if not (len(offered) < choicenum and len(static_classes) - len(offered_classes) > 0):
            break
        if offered_classes.count(c['id']) < len(c['echos']):
            offered.append(c['id'])
            offered_classes.append(c['id'])

    if not (modifiers and get_modifier(modifiers, KdrModifierNames.ALLOW_DUPLICATES.value) is not None):
        await db.set_instance_value(sid, iid, 'offered_classes', offered_classes)
    return offered


""""""

""" Get Final Class Selection """


async def get_final_class_selection(player_classes):
    msg = f"Let's get started with class selection! Please, select your class:"
    echos = []
    embeds=[]
    for x in player_classes:
        base_class_name = await db.get_base_class_value(x, 'name')
        class_echos = await db.get_base_class_value(x, 'echos')
        for c in class_echos:
            echo = await db.get_static_class(c)
            name = echo['name']
            img_url = echo['url_picture']
            sheet_url = echo['url_sheet']
            desc = echo['description']
            newembed=Embed(title=name,description=desc, url=sheet_url)
            newembed.set_footer(text=f"Faction: {base_class_name}")
            newembed.set_thumbnail(url=img_url)
            embeds.append(newembed)
            echos.append([echo['id'], name, img_url])

    return echos, msg, embeds


""""""

""" Update Shop Gold """


async def update_gold(pid, iid, sid, win, special_flags):
    gold = await db.get_inventory_value(pid, sid, iid, "gold")

    modifiers=await db.get_instance_value(sid,iid,"modifiers")

    loss_streak = await db.get_inventory_value(pid, sid, iid, "loss_streak")
    if modifiers and (get_modifier(modifiers,KdrModifierNames.LOSE_GOLD_AT_END.value) is not None):
        gold=0


    if loss_streak > len(LOSS_STREAK_EXTRA_GOLD) - 1:
        loss_streak = len(LOSS_STREAK_EXTRA_GOLD) - 1
    # interest
    if not (modifiers and (get_modifier(modifiers,KdrModifierNames.NO_INTEREST.value) is not None)):
        gold += math.floor((gold / GOLD_INTEREST_REQUIRED)) * GOLD_INTEREST_GAINED

    # win/loss gold
    if not (modifiers and (get_modifier(modifiers,KdrModifierNames.GOLD_PER_ROUND.value) is not None)):
        if win:
            if SpecialSkillHandling.SKILL_PROFESSIONAL_DUELIST.value in special_flags:
                gold += GOLD_WIN_GAINED_PROFESSIONAL_DUELIST
            else:
                gold += GOLD_WIN_GAINED
        else:
            gold += GOLD_LOSS_GAINED
            gold += LOSS_STREAK_EXTRA_GOLD[loss_streak]
    else:
        gold += int(get_modifier(modifiers,KdrModifierNames.GOLD_PER_ROUND.value))

    # heavy sack
    if SpecialSkillHandling.SKILL_HEAVY_SACK.value in special_flags:
        gold += HEAVY_SACK_EXTRA_GOLD*(special_flags.count(SpecialSkillHandling.SKILL_HEAVY_SACK.value))

    await db.set_inventory_value(pid, sid, iid, "gold", gold)


""""""

""" Check Player Won Round """


async def check_player_won_round(pid, round_results, current_rounds, active_round):
    for i in range(len(current_rounds[active_round])):
        if pid in current_rounds[active_round][i]:
            first_player = current_rounds[active_round][i][0]
            second_player = current_rounds[active_round][i][1]
            opponent = second_player if pid == first_player else first_player
            match_pos = i
            result = round_results[active_round][i][0] if pid == first_player else not round_results[active_round][i][0]
            return result, match_pos, opponent
        
""" Check if Player is Firstplayer Won Round """


async def check__if_firstplayer_in_round(pid, current_rounds, active_round):
    for i in range(len(current_rounds[active_round])):
        if pid in current_rounds[active_round][i]:
            first_player = current_rounds[active_round][i][0]
            second_player = current_rounds[active_round][i][1]
            opponent = second_player if pid == first_player else first_player
            return pid == first_player


""""""

""""""

""" Get Matchpos from 2 player ids """

async def check_player_won_round_by_ids(pid1,pid2, round_results, current_rounds):
    active_round=0
    for j in range(len(current_rounds)):
        for i in range(len(current_rounds[j])):
            if pid1 in current_rounds[j][i] and pid2 in current_rounds[j][i]:
                first_player = current_rounds[j][i][0]
                match_pos = i
                result = round_results[j][i][0] if pid1 == first_player else not round_results[j][i][0]
                return result, match_pos


""""""




""" Create balanced Round Robin brackets """


def create_balanced_round_robin(players, rematch_count: int = 1):
    """ Create a schedule for the players in the list and return it"""
    s = []
    if len(players) % 2 == 1:
        players = players + [None]
    for i in range(rematch_count):
        # manipulate map (array of indexes for list) instead of list itself
        # this takes advantage of even/odd indexes to determine home vs. away
        n = len(players)
        map = list(range(n))
        mid = n // 2

        random.shuffle(players)
        for i in range(n - 1):
            l1 = map[:mid]
            l2 = map[mid:]
            l2.reverse()
            round = []
            for j in range(mid):
                t1 = players[l1[j]]
                t2 = players[l2[j]]
                if j == 0 and i % 2 == 1:
                    # flip the first match only, every other round
                    # (this is because the first match always involves the last player in the list)
                    round.append((t2, t1))
                else:
                    round.append((t1, t2))
            s.append(round)
            # rotate list by n/2, leaving last element at the end
            map = map[mid:-1] + map[:mid] + map[-1:]
    return s


def create_swiss_rounds(players, num_rounds):
    """
    Initialize Swiss rounds with placeholders.
    :param players: List of player IDs.
    :param num_rounds: Total number of rounds for the Swiss system.
    :return: List of rounds with the first round randomized.
    """
    rounds = []

    # Randomly shuffle players for the first round
    random.shuffle(players)
    first_round = []
    for i in range(0, len(players), 2):
        if i + 1 < len(players):
            first_round.append((players[i], players[i + 1]))
        else:
            first_round.append((players[i], None))  # Bye round for odd number of players
    rounds.append(first_round)

    # Add placeholders for future rounds
    for _ in range(1, num_rounds):
        rounds.append([])

    return rounds

def generate_next_swiss_round(players, scores, previous_rounds):
    """
    Generate the next Swiss round dynamically based on player scores.
    :param players: List of player IDs.
    :param scores: Dictionary of player scores {player_id: score}.
    :param previous_rounds: List of previous rounds to avoid repeat pairings.
    :return: List of pairings for the next round.
    """
    # Sort players by their scores in descending order
    sorted_players = sorted(players, key=lambda p: scores.get(p, 0), reverse=True)

    # Pair players with similar scores
    pairings = []
    used_players = set()
    print("sorted_players",sorted_players)
    while len(sorted_players) > 1:
        player1 = sorted_players.pop(0)  # Take the top player
        player2 = None

        # Find the next player with the closest score who hasn't been paired with player1
        for i, potential_opponent in enumerate(sorted_players):
            if potential_opponent not in used_players and (player1, potential_opponent) not in previous_rounds:
                player2 = sorted_players.pop(i)
                break

        # If no valid opponent is found, pair with the next available player
        if player2 is None and sorted_players:
            player2 = sorted_players.pop(0)

        pairings.append((player1, player2))
        used_players.add(player1)
        used_players.add(player2)

    # Handle odd number of players (bye round)
    if len(sorted_players) == 1:
        pairings.append((sorted_players[0], None))  # Bye round for the last player

    return pairings
