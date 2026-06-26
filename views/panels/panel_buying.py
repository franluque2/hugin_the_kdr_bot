from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from core import kdr_db as db
from core.kdr_data import SpecialSkillHandling, SpecialClassHandling
from views.view_buying import BuyView
from core.kdr_data import type_converter, KdrModifierNames
from core.kdr_modifiers import get_modifier
from core.kdr_db import get_generic_bucket_categories, get_class_bucket_categories, get_secret_categories

from config.config import BANLIST_LINK, LEVEL_THRESHOLDS
import random
import core.kdr_ansi as ansi
import discord
from discord import Embed


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

        # Slime: use the absorbed class for class loot display
        if SpecialClassHandling.CLASS_SLIME.value in special_flags:
            absorbed = player_inventory.get("absorbed_classes", [])
            if absorbed:
                player_class = absorbed[-1]  # Use most recently absorbed class

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

        embeds = []
        
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
                
                if cat[3] > playerlevel:
                    embed = Embed(title=catname, description=f"This category of loot unlocks at level {cat[3] + 1}.", color=discord.Color.blue())
                    embeds.append(embed)
                else:
                    shopwindowitems = await get_shop_window_class(self.pid, self.sid, self.iid, player_class, cat)
                    if len(shopwindowitems) == 0:
                        embed = Embed(title=catname, description="You have bought out all your possible loot for this category", color=discord.Color.blue())
                        embeds.append(embed)
                    else:
                        shopwindow = {"name": catid, "cost": cat[1], "buckets": shopwindowitems}
                        ansi_lines = []
                        for idx, bucket in enumerate(shopwindowitems):
                            if idx > 0:
                                ansi_lines.append(ansi.cyan(f"─" * 30, b=False))
                            if bucket["cards"]:
                                ansi_lines.append(ansi.cyan("--- [ CARDS ] ---", b=True))
                                cards_str = " / ".join(bucket["cards"])
                                ansi_lines.append(ansi.white(cards_str))
                            
                            if bucket["cards"] and bucket["skills"]:
                                ansi_lines.append(ansi.gray("-" * 20))
                                
                            if bucket["skills"]:
                                ansi_lines.append(ansi.yellow("--- [ SKILLS ] ---", b=True))
                                for skill in bucket["skills"]:
                                    skillinfo = await db.get_skill_by_id(skill)
                                    name = skillinfo["name"]
                                    desc = skillinfo.get("description", "No description") or "No description available"
                                    ansi_lines.append(ansi.pink(name, b=True))
                                    ansi_lines.append(ansi.white(desc))

                            if bucket.get("recipes"):
                                ansi_lines.append(ansi.pink("--- [ RECIPES ] ---", b=True))
                                for recipe in bucket["recipes"]:
                                    recipe_name = recipe if isinstance(recipe, str) else recipe.get("name", "")
                                    recipe_desc = "" if isinstance(recipe, str) else recipe.get("description", "")
                                    ansi_lines.append(ansi.pink(recipe_name, b=True))
                                    if recipe_desc:
                                        ansi_lines.append(ansi.white(recipe_desc))

                            shopwindow["cost"] += bucket["tax"]
                            if bucket["tax"] != 0:
                                ansi_lines.append(ansi.red(f"Tax: This Category costs {bucket['tax']} more!", b=True))
                        
                        description_content = ansi.wrap_ansi("\n".join(ansi_lines))
                        embed = Embed(title=catname, description=description_content.strip(), color=discord.Color.blue())
                        embeds.append(embed)
                        loot.append(shopwindow)
                        categories_class.append(cat)

            for cat in full_categories_generic:
                catid = cat[0]
                catname = type_converter[catid]
                
                if cat[3] > playerlevel:
                    embed = Embed(title=catname, description=f"This category of loot unlocks at level {cat[3] + 1}.", color=discord.Color.green())
                    embeds.append(embed)
                else:
                    shopwindowitems = await get_shop_window_generic(self.pid, self.sid, self.iid, cat)
                    if len(shopwindowitems) == 0:
                        embed = Embed(title=catname, description="You have bought out all your possible loot for this category", color=discord.Color.green())
                        embeds.append(embed)
                    else:
                        shopwindow = {"name": catid, "cost": cat[1], "buckets": shopwindowitems}
                        ansi_lines = []
                        for idx, bucket in enumerate(shopwindowitems):
                            if idx > 0:
                                ansi_lines.append(ansi.cyan(f"─" * 30, b=False))
                            if bucket["cards"]:
                                ansi_lines.append(ansi.cyan("--- [ CARDS ] ---", b=True))
                                cards_str = " / ".join(bucket["cards"])
                                ansi_lines.append(ansi.white(cards_str))
                            
                            if bucket["cards"] and bucket["skills"]:
                                ansi_lines.append(ansi.gray("-" * 20))
                                
                            if bucket["skills"]:
                                ansi_lines.append(ansi.yellow("--- [ SKILLS ] ---", b=True))
                                for skill in bucket["skills"]:
                                    skillinfo = await db.get_skill_by_id(skill)
                                    name = skillinfo["name"]
                                    desc = skillinfo.get("description", "No description") or "No description available"
                                    ansi_lines.append(ansi.pink(name, b=True))
                                    ansi_lines.append(ansi.white(desc))

                            if bucket.get("recipes"):
                                ansi_lines.append(ansi.pink("--- [ RECIPES ] ---", b=True))
                                for recipe in bucket["recipes"]:
                                    recipe_name = recipe if isinstance(recipe, str) else recipe.get("name", "")
                                    recipe_desc = "" if isinstance(recipe, str) else recipe.get("description", "")
                                    ansi_lines.append(ansi.pink(recipe_name, b=True))
                                    if recipe_desc:
                                        ansi_lines.append(ansi.white(recipe_desc))

                            shopwindow["cost"] += bucket["tax"]
                            if bucket["tax"] != 0:
                                ansi_lines.append(ansi.red(f"Tax: This Category costs {bucket['tax']} more!", b=True))
                        
                        description_content = ansi.wrap_ansi("\n".join(ansi_lines))
                        embed = Embed(title=catname, description=description_content.strip(), color=discord.Color.green())
                        embeds.append(embed)
                        loot.append(shopwindow)
                        categories_generic.append(cat)

            loot_offered = [loot, categories_generic, categories_class]
            await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", loot_offered)
        else:
            loot = offered_loot[0]
            categories_generic = offered_loot[1]
            categories_class = offered_loot[2]
            for window in loot:
                catname = type_converter[window["name"]]
                ansi_lines = []
                for idx, bucket in enumerate(window["buckets"]):
                    if idx > 0:
                        ansi_lines.append(ansi.cyan(f"─" * 30, b=False))
                    if bucket["cards"]:
                        ansi_lines.append(ansi.cyan("--- [ CARDS ] ---", b=True))
                        cards_str = " / ".join(bucket["cards"])
                        ansi_lines.append(ansi.white(cards_str))
                    
                    if bucket["cards"] and bucket["skills"]:
                        ansi_lines.append(ansi.gray("-" * 20))
                        
                    if bucket["skills"]:
                        ansi_lines.append(ansi.yellow("--- [ SKILLS ] ---", b=True))
                        for skill in bucket["skills"]:
                            skillinfo = await db.get_skill_by_id(skill)
                            name = skillinfo["name"]
                            desc = skillinfo.get("description", "No description") or "No description available"
                            ansi_lines.append(ansi.pink(name, b=True))
                            ansi_lines.append(ansi.white(desc))
                    
                    if bucket.get("recipes"):
                        ansi_lines.append(ansi.pink("--- [ RECIPES ] ---", b=True))
                        for recipe in bucket["recipes"]:
                            recipe_name = recipe if isinstance(recipe, str) else recipe.get("name", "")
                            recipe_desc = "" if isinstance(recipe, str) else recipe.get("description", "")
                            ansi_lines.append(ansi.pink(recipe_name, b=True))
                            if recipe_desc:
                                ansi_lines.append(ansi.white(recipe_desc))
                    
                    if bucket["tax"] != 0:
                        ansi_lines.append(ansi.red(f"Tax: This Category costs {bucket['tax']} more!", b=True))
                
                description_content = ansi.wrap_ansi("\n".join(ansi_lines))
                is_class = any(c[0] == window["name"] for c in full_categories_class)
                embed = Embed(title=catname, description=description_content.strip(), color=discord.Color.blue() if is_class else discord.Color.green())
                embeds.append(embed)

        banlist_msg = f"Remember to check the KDR Banlist at {BANLIST_LINK} !"
        
        # Send embeds in chunks if necessary
        for i in range(0, len(embeds), 10):
            current_embeds = embeds[i:i+10]
            if i + 10 >= len(embeds):
                # Last chunk, attach the view
                buy_view = BuyView()
                costreduction = 0
                if SpecialSkillHandling.SKILL_BARGAIN.value in special_flags:
                    costreduction = 1
                await buy_view.create_buttons(self.pid, self.sid, self.iid, self.status_message,
                                              self.status_panel_generator, self.thread, can_sell, loot, categories_generic,
                                              categories_class, full_categories_secret, self, costreduction)
                await self.thread.send(content=banlist_msg if i==0 else None, embeds=current_embeds, view=buy_view)
            else:
                await self.thread.send(content=banlist_msg if i==0 else None, embeds=current_embeds)


async def get_shop_window_generic(pid, sid, iid, category):
    buckets_taken = list(await db.get_inventory_value(pid, sid, iid, "loot"))
    modifiers = await db.get_instance_value(sid, iid, "modifiers")
    possible_buckets=[]
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
