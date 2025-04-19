from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from core import kdr_db as db
from core.kdr_data import SpecialSkillHandling
from views.view_buying import BuyView
from core.kdr_data import type_converter, KdrModifierNames
from core.kdr_modifiers import get_modifier
from core.kdr_db import get_generic_bucket_categories, get_class_bucket_categories, get_secret_categories

from config.config import BANLIST_LINK, LEVEL_THRESHOLDS
import random


class BuyPanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_buy_panel(self) -> None:
        # Fetch player inventory and modifiers
        player_inventory = await db.get_inventory(self.pid, self.sid, self.iid)
        modifiers = await db.get_instance_value(self.sid, self.iid, "modifiers")
        kdr_format = None

        # Check if an alternate format is specified in modifiers
        if modifiers and get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value) is not None:
            kdr_format = get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value)

        offered_loot = player_inventory["offered_loot"]
        player_class = player_inventory["class"]
        special_flags = player_inventory["modifiers"]
        can_sell = len(player_inventory["treasures"]) > 0

        playerlevel = 0
        playerxp = player_inventory["XP"] if player_inventory["XP"] <= LEVEL_THRESHOLDS[-1] else LEVEL_THRESHOLDS[-1]

        for level in LEVEL_THRESHOLDS:
            if playerxp >= level:
                playerlevel += 1
        for skill in player_inventory["skills"]:
            skill_data = await db.get_skill_by_id(skill)
            if skill_data["is_sellable"]:
                can_sell = True

        msg = f""

        # Fetch full categories
        full_categories_generic = await get_generic_bucket_categories(kdr_format)
        full_categories_class = await get_class_bucket_categories(kdr_format)
        full_categories_secret = await get_secret_categories(kdr_format)

        if len(offered_loot) == 0:
            loot = []
            categories_generic = []
            categories_class = []

            for cat in full_categories_class:
                catid = cat[0]
                catname = type_converter[catid]
                msg += f"**{catname}**:\n\n"
                if cat[3] > playerlevel:
                    msg += f"This category of loot unlocks at level {cat[3] + 1}.\n"
                else:
                    shopwindowitems = await get_shop_window_class(self.pid, self.sid, self.iid, player_class, cat)
                    if len(shopwindowitems) == 0:
                        msg += f"You have bought out all your possible loot for this category\n"
                    else:
                        shopwindow = {"name": catid, "cost": cat[1], "buckets": shopwindowitems}
                        for bucket in shopwindowitems:
                            if bucket["cards"] is not None:
                                for card in bucket["cards"]:
                                    msg += f"{card} / "
                                msg = msg[:-3]
                                msg += f"\n"
                            for skill in bucket["skills"]:
                                skillinfo = await db.get_skill_by_id(skill)
                                name = skillinfo["name"]
                                desc = skillinfo["description"]
                                msg += f"\n**{name}** : {desc}\n"

                            shopwindow["cost"] += bucket["tax"]
                            if bucket["tax"] != 0:
                                tax = bucket["tax"]
                                msg += f"**Tax**: This Shown Category costs **{tax}** more!\n"
                            msg += f"\n"
                        loot.append(shopwindow)
                        categories_class.append(cat)

            for cat in full_categories_generic:
                catid = cat[0]
                catname = type_converter[catid]
                msg += f"**{catname}**:\n\n"
                if cat[3] > playerlevel:
                    msg += f"This category of loot unlocks at level {cat[3] + 1}.\n"
                else:
                    shopwindowitems = await get_shop_window_generic(self.pid, self.sid, self.iid, cat)
                    if len(shopwindowitems) == 0:
                        msg += f"You have bought out all your possible loot for this category\n"
                    else:
                        shopwindow = {"name": catid, "cost": cat[1], "buckets": shopwindowitems}
                        for bucket in shopwindowitems:
                            if bucket["cards"] is not None:
                                for card in bucket["cards"]:
                                    msg += f"{card} / "
                                msg = msg[:-3]
                                msg += f"\n"

                            for skill in bucket["skills"]:
                                skillinfo = await db.get_skill_by_id(skill)
                                name = skillinfo["name"]
                                desc = skillinfo["description"]
                                msg += f"\n**{name}** : {desc}\n"
                            shopwindow["cost"] += bucket["tax"]
                            msg += f"\n"
                            if bucket["tax"] != 0:
                                tax = bucket["tax"]
                                msg += f"**Tax**: This Shown Category costs **{tax}** more!\n"
                        loot.append(shopwindow)
                        categories_generic.append(cat)

            loot_offered = [loot, categories_generic, categories_class]
            await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", loot_offered)
        else:
            loot = offered_loot[0]
            categories_generic = offered_loot[1]
            categories_class = offered_loot[2]
            for window in loot:
                cat = type_converter[window["name"]]
                msg += f"**{cat}**:\n\n"
                for bucket in window["buckets"]:
                    if bucket["cards"] is not None:
                        for card in bucket["cards"]:
                            msg += f"{card} / "
                        msg = msg[:-3]
                        msg += f"\n"
                    for skill in bucket["skills"]:
                        skillinfo = await db.get_skill_by_id(skill)
                        name = skillinfo["name"]
                        desc = skillinfo["description"]
                        msg += f"\n**{name}** : {desc}\n"
                    if bucket["tax"] != 0:
                        tax = bucket["tax"]
                        msg += f"**Tax**: This Shown Category costs **{tax}** more!\n"
                msg += "\n"

        msg += f"\nRemember to check the KDR Banlist at {BANLIST_LINK} !\n"

        # Split msg into 2000-character chunks
        msg_lines = msg.split("\n")
        msg_ov = []
        buffer = ""
        for line in msg_lines:
            if len(buffer + line + "\n") > 1900:
                msg_ov.append(buffer)
                buffer = ""
            buffer += line
            buffer += "\n"

        if len(buffer) > 1:
            msg_ov.append(buffer)

        for msg_overflow in msg_ov[:-1]:
            await self.thread.send(msg_overflow)
        buy_view = BuyView()
        costreduction = 0
        if SpecialSkillHandling.SKILL_BARGAIN.value in special_flags:
            costreduction = 1
        await buy_view.create_buttons(self.pid, self.sid, self.iid, self.status_message,
                                      self.status_panel_generator, self.thread, can_sell, loot, categories_generic,
                                      categories_class, full_categories_secret, self, costreduction)

        await self.thread.send(msg_ov[-1:][0], view=buy_view)


async def get_shop_window_generic(pid, sid, iid, category):
    buckets_taken = list(await db.get_inventory_value(pid, sid, iid, "loot"))
    modifiers = await db.get_instance_value(sid, iid, "modifiers")
    if modifiers and get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value) is not None:
        possible_buckets = list(await db.get_bucket_category(category[0], get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value)))
    else:
        possible_buckets = list(await db.get_bucket_category(category[0]))
    returnbuckets = []

    for bucket in buckets_taken:
        if bucket in possible_buckets:
            possible_buckets.remove(bucket)

    if len(possible_buckets) <= category[2]:
        for bucket in possible_buckets:
            retbucket = await db.get_bucket(bucket)
            returnbuckets.append(retbucket)
        return returnbuckets

    ranchoices = random.sample(population=possible_buckets, k=category[2])
    for bucket in ranchoices:
        retbucket = await db.get_bucket(bucket)
        returnbuckets.append(retbucket)
    return returnbuckets


async def get_shop_window_secret(pid, sid, iid, category):
    buckets_taken = list(await db.get_inventory_value(pid, sid, iid, "loot"))
    modifiers = await db.get_instance_value(sid, iid, "modifiers")
    if modifiers and get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value) is not None:
        possible_buckets = list(await db.get_bucket_category(category[0], get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value)))
    else:
        possible_buckets = list(await db.get_bucket_category(category[0]))
    returnbuckets = []

    for bucket in buckets_taken:
        if bucket in possible_buckets:
            possible_buckets.remove(bucket)

    if len(possible_buckets) <= category[2]:
        for bucket in possible_buckets:
            retbucket = await db.get_bucket(bucket)
            returnbuckets.append(retbucket)
        return returnbuckets

    ranchoices = random.sample(population=possible_buckets, k=category[2])
    for bucket in ranchoices:
        retbucket = await db.get_bucket(bucket)
        returnbuckets.append(retbucket)
    return returnbuckets


async def get_shop_window_class(pid, sid, iid, cid_echo, category):
    cid = await db.get_static_class_value(cid_echo, "base")
    buckets_taken = list(await db.get_inventory_value(pid, sid, iid, "loot"))
    possible_buckets_master = await db.get_base_class_value(cid, "bucket_list")
    possible_buckets = list(possible_buckets_master[category[0]])

    modifiers = await db.get_instance_value(sid, iid, "modifiers")
    blacklist = []

    # Handle blacklist modifier
    if modifiers and get_modifier(modifiers, KdrModifierNames.BLACKLIST_CLASS.value) is not None:
        blacklist = get_modifier(modifiers, KdrModifierNames.BLACKLIST_CLASS.value).split(";")

    # Handle IGNORE_CLASSES modifier
    if modifiers and get_modifier(modifiers, KdrModifierNames.IGNORE_CLASSES.value) is not None:
        classes = None
        if modifiers and get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value) is not None:
            classes = await db.get_all_base_classes(get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value))
        else:
            classes = await db.get_all_base_classes()

        for c in classes:
            if c["id"] != cid and c["id"] not in blacklist:
                possible_buckets += c["bucket_list"][category[0]]
    else:
        # Filter out blacklisted buckets for the current base class
        if cid in blacklist:
            possible_buckets = []
        else:
            possible_buckets = [
                bucket for bucket in possible_buckets
                if bucket not in blacklist
            ]

    returnbuckets = []

    # Remove already taken buckets
    for bucket in buckets_taken:
        if bucket in possible_buckets:
            possible_buckets.remove(bucket)

    # If possible buckets are fewer than the required amount, return all
    if len(possible_buckets) <= category[2]:
        for bucket in possible_buckets:
            retbucket = await db.get_bucket(bucket)
            returnbuckets.append(retbucket)
        return returnbuckets

    # Randomly select buckets if more than required
    ranchoices = random.sample(population=possible_buckets, k=category[2])
    for bucket in ranchoices:
        retbucket = await db.get_bucket(bucket)
        returnbuckets.append(retbucket)
    return returnbuckets
