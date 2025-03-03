from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from core import kdr_db as db
from core.kdr_data import SpecialSkillHandling
from views.view_buying import BuyView
from core.kdr_data import categories_buckets_generic, categories_buckets_class, categories_secret, type_converter, KdrModifierNames
from core.kdr_modifiers import get_modifier

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
        # send to cog soon
        player_inventory = await db.get_inventory(self.pid, self.sid, self.iid)

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

        if len(offered_loot) == 0:
            loot = []
            categories_generic = []
            categories_class = []

            for cat in categories_buckets_class:
                catid = cat[0]
                catname = type_converter[catid]
                msg += f"**{catname}**:\n\n"
                if cat[3]>playerlevel:
                    msg+=f"This category of loot unlocks at level {cat[3]+1}.\n"
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
                            if bucket["tax"]!=0:
                                tax=bucket["tax"]
                                msg+=f"**Tax**: This Shown Category costs **{tax}** more!\n"
                            msg += f"\n"
                        categories_class.append(cat)

                        if SpecialSkillHandling.SKILL_BARGAIN.value in special_flags:
                            shopwindow["cost"] -= 1
                        loot.append(shopwindow)

            for cat in categories_buckets_generic:
                catid = cat[0]
                catname = type_converter[catid]
                msg += f"**{catname}**:\n\n"
                if cat[3]>playerlevel:
                    msg+=f"This category of loot unlocks at level {cat[3]+1}.\n"
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
                            if bucket["tax"]!=0:
                                tax=bucket["tax"]
                                msg+=f"**Tax**: This Shown Category costs **{tax}** more!\n"
                        categories_generic.append(cat)
                        if SpecialSkillHandling.SKILL_BARGAIN.value in special_flags:
                            shopwindow["cost"] -= 1
                        loot.append(shopwindow)
            loot_offered = [loot, categories_generic, categories_class]
            await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", loot_offered)
        else:
            loot = offered_loot[0]
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
                    if bucket["tax"]!=0:
                        tax=bucket["tax"]
                        msg+=f"**Tax**: This Shown Category costs **{tax}** more!\n"
                msg += "\n"
            categories_generic = offered_loot[1]
            categories_class = offered_loot[2]
        

        msg+=f"\nRemember to check the KDR Banlist at {BANLIST_LINK} !\n"


        # split msg in 2000 character messages:

        msg_lines=msg.split("\n")
        msg_ov=[]
        buffer=""
        for line in msg_lines:
            if len(buffer+line+"\n")>1900:
                msg_ov.append(buffer)
                buffer=""
            buffer+=line
            buffer+="\n"
           
        if len(buffer)>1:
            msg_ov.append(buffer)

        for msg_overflow in msg_ov[:-1]:
          await self.thread.send(msg_overflow)
        buy_view = BuyView()
        costreduction=0
        if SpecialSkillHandling.SKILL_BARGAIN.value in special_flags:
            costreduction=1
        await buy_view.create_buttons(self.pid, self.sid, self.iid, self.status_message,
                                      self.status_panel_generator, self.thread, can_sell, loot, categories_generic,
                                      categories_class,categories_secret, self, costreduction
                                      )

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

    modifiers=await db.get_instance_value(sid,iid,"modifiers")

    if modifiers and (get_modifier(modifiers,KdrModifierNames.IGNORE_CLASSES.value) is not None):
        classes=None
        if modifiers and (get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value) is not None):
            classes=await db.get_all_base_classes(get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value))
        else:
            classes=await db.get_all_base_classes()
        for c in classes:
            if c["id"]!=cid:
                possible_buckets+=c["bucket_list"][category[0]]
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
