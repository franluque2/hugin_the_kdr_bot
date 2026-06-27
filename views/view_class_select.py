import discord
import core.kdr_db as db
import core.kdr_statics as statics
from discord.ui.button import ButtonStyle
from core.kdr_data import categories_buckets_generic, SpecialClassHandling, rarity_converter, categories_buckets_class, KdrModifierNames
from core.kdr_modifiers import get_modifier
import random
from views.panels.panel_treasure import get_random_treasures
from views.panels.panel_buying import get_shop_window_class, get_shop_window_generic
from core.kdr_db import get_class_bucket_categories, get_generic_bucket_categories
from views.view_quest_select import QuestSelectView
from config.config import RPG_STATS, INITIAL_GENERIC_SKILLS_TO_SHOW
import core.kdr_ansi as ansi

from discord import Embed

class InitialGenericSkillButton(discord.ui.Button):
    def __init__(self, skill, pid, sid, iid):
        super().__init__(label=skill["name"], style=ButtonStyle.secondary)
        self.skill = skill
        self.pid = pid
        self.sid = sid
        self.iid = iid

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message("Not your choice.", ephemeral=True)
            return

        # Disable all buttons
        for item in self.view.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(view=self.view)

        # Give skill
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'skills', self.skill['id'], operation="$push")
        if self.skill["special_code_flag"] != -1:
            if hasattr(self.skill["special_code_flag"], "__len__"):
                for skill_flag in self.skill["special_code_flag"]:
                    await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', skill_flag, operation="$push")
            else:
                await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', self.skill['special_code_flag'], operation="$push")
        
        description = f"<@{self.pid}> has selected the initial skill: **{self.skill['name']}**!"
        await interaction.followup.send(description)
        
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.edit(archived=True, locked=True)

class InitialGenericSkillSelectView(discord.ui.View):
    def __init__(self, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_view(self, sid, iid, pid, interaction):
        all_skills = list(await db.get_all_generic_skills())
        if not all_skills:
            await interaction.followup.send("No generic skills found.")
            return

        num_to_show = min(INITIAL_GENERIC_SKILLS_TO_SHOW, len(all_skills))
        offered = random.sample(all_skills, num_to_show)

        embeds = []
        # Header embed
        embeds.append(Embed(title="Pick a Starting Generic Skill", description="Choose one additional skill to start your journey.", color=discord.Color.blue()))
        
        for skill in offered:
            skill_name = skill["name"]
            skill_desc = skill.get("description", "No description available")
            skill_img = skill.get("img_url", "")

            # Create an individual embed for each skill
            new_embed = Embed(title=skill_name, description=skill_desc, color=discord.Color.from_rgb(255, 105, 180))
            if skill_img:
                new_embed.set_thumbnail(url=skill_img)
            embeds.append(new_embed)
            self.add_item(InitialGenericSkillButton(skill, pid, sid, iid))

        await interaction.followup.send(embeds=embeds, view=self)

class ClassButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, static_class_id: str, static_class_name: str, static_class_img_url: str, pid: str, sid, iid):
        super().__init__(label=label, custom_id=custom_id)
        self.static_class_id = static_class_id
        self.static_class_name = static_class_name
        self.static_class_img_url = static_class_img_url
        self.pid = pid
        self.sid = sid
        self.iid = iid

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player picking a class.", ephemeral=True)
            return
        await self.disable_view(interaction)
        embed = None
        if len(self.static_class_img_url) > 0:
            embed = discord.Embed(description=self.static_class_name)
            embed.set_image(url=self.static_class_img_url)

        class_picked = await db.check_class_picked(self.sid, self.iid, self.static_class_id)

        if class_picked:
            await interaction.response.send_message(f"This subclass has already been picked.",ephemeral=True)
            return
        
        static_class_info=await db.get_static_class(self.static_class_id)
        
        # Merge base cards from both static class and its parent base class
        all_base_cards = []
        if "base_cards" in static_class_info:
            all_base_cards.extend(static_class_info["base_cards"])
            
        base_class_id = static_class_info.get("base")
        if base_class_id:
            base_class_info = await db.get_base_class(base_class_id)
            if base_class_info and "base_cards" in base_class_info:
                # Add cards from base class if not already there
                for card in base_class_info["base_cards"]:
                    all_base_cards.append(card)
        
        if all_base_cards:
            await db.set_inventory_value(self.pid, self.sid, self.iid, "base_cards", all_base_cards)
            
        unique_effects = static_class_info.get("unique_effects", [])
        if unique_effects:
            player_modifiers = await db.get_inventory_value(self.pid, self.sid, self.iid, "modifiers") or []
            player_modifiers.extend(unique_effects)
            await db.set_inventory_value(self.pid, self.sid, self.iid, "modifiers", player_modifiers)
        
        # Only set gamble_threshold if the class actually has a gamble_ratio (Gambler)
        if "gamble_ratio" in static_class_info:
            generated_gamble = random.randint(static_class_info["gamble_ratio"][0], static_class_info["gamble_ratio"][1])
            await db.set_inventory_value(self.pid, self.sid, self.iid, "gamble_threshold", generated_gamble)
        else:
            await db.set_inventory_value(self.pid, self.sid, self.iid, "gamble_threshold", 0)
        
        description = f"<@{interaction.user.id}> selected: **{self.static_class_name}**!\n\nRemember to make a copy of the sheet, and share the url (to view) with the `character` command!"
        if static_class_info.get("url_sheet"):
            description += f"\n\n**Class Page:** {static_class_info['url_sheet']}"
        await interaction.response.send_message(description, embed=embed)
        
        #if SpecialClassHandling.CLASS_PIRATE.value in (static_class_info["unique_effects"]): REMOVED: Pirate no longer starts with treasures
        #    msg = "__**Yarr, welcome to the KDR laddie! Ye get all these treasures!**__:\n"
        #    offered_treasure = await get_random_treasures()
        #    embeds=[]
        #    for treasure in offered_treasure:
        #        treasure_name = treasure["name"]
        #        treasure_image = treasure["img_url"]
        #        rarity=rarity_converter[treasure["rarity"]]
        #        treasure_rarity=f"Rarity: {rarity}"
        #        new_embed=Embed(title=treasure_name,description=treasure_rarity)
        #        new_embed.set_thumbnail(treasure_image)
        #        embeds.append(new_embed)
        #        await db.set_inventory_value(self.pid, self.sid, self.iid, "treasures", treasure["id"], "$push")
        #    await interaction.followup.send(content=msg,embeds=embeds)
        if SpecialClassHandling.CLASS_SLIME.value in (static_class_info["unique_effects"]):
            await db.set_inventory_value(self.pid, self.sid, self.iid, "absorbed_classes", [])

        await db.set_inventory_value(self.pid, self.sid, self.iid, "class", self.static_class_id)

        modifiers=await db.get_instance_value(self.sid,self.iid,"modifiers")

        if not (modifiers and (get_modifier(modifiers,KdrModifierNames.ALLOW_DUPLICATES.value) is not None)):
            await db.set_instance_value(self.sid, self.iid, 'picked_classes', self.static_class_id, '$push')

        skip_loot = (SpecialClassHandling.CLASS_SLIME.value in (static_class_info["unique_effects"])
                     or SpecialClassHandling.CLASS_MIMIC.value in (static_class_info["unique_effects"]))
        if skip_loot:
            if SpecialClassHandling.CLASS_SLIME.value in (static_class_info["unique_effects"]):
                await interaction.followup.send("As a Slime, you absorb the class of your first opponent. You will receive their cards, skills, and loot after your first match.")
            elif SpecialClassHandling.CLASS_MIMIC.value in (static_class_info["unique_effects"]):
                await interaction.followup.send("As a Mimic, you copy your opponent's entire loadout. You do not have a Shop Phase.")
        else:
            quest_select_view = QuestSelectView()
            await quest_select_view.create_quest_view(self.sid, self.iid, self.pid, interaction)

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style=ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()

class LowQualButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, static_class_id: str, pid: str, sid, iid, windowbuckets):
        super().__init__(label=label, custom_id=custom_id)
        self.static_class_id = static_class_id
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.windowbuckets=windowbuckets


    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player picking loot.", ephemeral=True)
            return
        await self.disable_view(interaction)
        await interaction.response.defer()
        
        description = f"<@{self.pid}> just picked a window containing:\n"
        content_items = []
        for bucket in self.windowbuckets:
            if bucket["cards"] is not None:
                content_items.append(f"**{' / '.join(bucket['cards'])}**")
            for skill in bucket["skills"]:
                skillinfo = await db.get_skill_by_id(skill)
                name = skillinfo["name"]
                desc = skillinfo.get("description", "No description") or "No description available"
                content_items.append(f"**{name}**\n{desc}")
                await db.set_inventory_value(self.pid, self.sid, self.iid, 'skills', skillinfo['id'],
                                             operation="$push")
                if skillinfo["special_code_flag"] != -1:
                    if hasattr(skillinfo["special_code_flag"], "__len__"):
                        for skill_flag in skillinfo["special_code_flag"]:
                            await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', skill_flag,
                                                         operation="$push")
                    else:
                        await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers',
                                                     skillinfo['special_code_flag'],
                                                     operation="$push")
            await db.set_inventory_value(self.pid, self.sid, self.iid, 'loot', bucket['id'],
                                         operation="$push")
        
        full_content = description + "\n" + "\n\n".join(content_items) + "\n\n**Make sure to write it down in your Character Sheet!**"
        await interaction.followup.send(full_content)
        
        # NEXT STEP: Pick Generic Skill
        skill_select_view = InitialGenericSkillSelectView()
        await skill_select_view.create_view(self.sid, self.iid, self.pid, interaction)


    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style=ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()

class ClassSelectView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, sid, iid, echos: list, pid):
        for c in echos:
            button = ClassButton(f'{c[1]}', f'{c[0]}', c[0], c[1], c[2], pid, sid, iid)
            ispicked= await db.check_class_picked(sid, iid, c[0])
            if ispicked:
                button.disabled = True
            self.add_item(button)


class LowSelectView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_low_view_picking(self, sid, iid, pid, player_class, interaction):
        loot = []
        msg = f"Heya! As a way to start your KDR with choices, you get a bit of Special Class loot!, get picking\n"

        # Fetch modifiers and determine kdr_format
        modifiers = await db.get_instance_value(sid, iid, "modifiers")
        kdr_format = None
        if modifiers and get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value) is not None:
            kdr_format = get_modifier(modifiers, KdrModifierNames.ALTERNATE_FORMAT.value)

        # Check if BOOTSTRAPS modifier is active
        if modifiers and get_modifier(modifiers, KdrModifierNames.NO_STARTING_LOOT.value) is not None:
            msg += f"\nJust Kidding :P , this KDR is without Starting Loot!.\n"
            await interaction.followup.send(msg)
            return  # Exit early, no loot offered

        # Fetch categories dynamically based on kdr_format
        categories_class = await get_class_bucket_categories(kdr_format)

        # Track already selected bucket IDs to avoid duplicates
        selected_bucket_ids = set()
        embeds = []

        for i in range(1, 3):
            shopwindowitems = []
            for _ in range(10):  # Retry up to 10 times to find unique buckets
                potential_items = await get_shop_window_class(pid, sid, iid, player_class, categories_class[0])
                unique_items = [item for item in potential_items if item["id"] not in selected_bucket_ids]

                if unique_items:
                    shopwindowitems = unique_items[:categories_class[0][2]]  # Limit to the required number of buckets
                    break

            for bucket in shopwindowitems:
                selected_bucket_ids.add(bucket["id"])

            shopwindow = {"id": i, "name": f"Window {i}", "buckets": shopwindowitems}
            loot.append(shopwindow)

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
            
            description_content = ansi.wrap_ansi("\n".join(ansi_lines))
            
            embeds.append(Embed(title=f"WINDOW {i}", description=description_content.strip(), color=discord.Color.blue()))

        for c in loot:
            button = LowQualButton(f'{c["name"]}', f'{c["id"]}', player_class, pid, sid, iid, c["buckets"])
            self.add_item(button)

        await interaction.followup.send(msg, embeds=embeds, view=self)


class SkillGiverView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)
    async def create_skill_giver_view(self, sid, iid, pid, interaction):
        loot = []
        msg=f""
        categories_class = []
        given_skills=[]
        embeds=[]
        skillnum=0
        
        generic_skills=[]
        modifiers = await db.get_instance_value(sid, iid, "modifiers")
        if modifiers and get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value) is not None:
            generic_skills = list(await db.get_all_generic_skills(get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value)))
        else:
            generic_skills = list(await db.get_all_generic_skills())

        random.shuffle(generic_skills)
        for skill in generic_skills:
            given_skills.append(skill)
            skill_name = skill['name']
            skill_desc = skill['description']
            skill_img = skill["img_url"]
            new_embed=Embed(title=skill_name,description=skill_desc, type="rich")
            new_embed.set_thumbnail(url=skill_img)
            embeds.append(new_embed)

            await db.set_inventory_value(pid, sid, iid, 'skills', skill['id'],
                                        operation="$push")

            if skill["special_code_flag"] != -1:
                if hasattr(skill["special_code_flag"], "__len__"):
                    for skill_flag in self.skill["special_code_flag"]:
                        await db.set_inventory_value(pid, sid, iid, 'modifiers', skill_flag,
                                                    operation="$push")
                else:
                    await db.set_inventory_value(pid, sid, iid, 'modifiers', skill['special_code_flag'],
                                                operation="$push")


            skillnum+=1
            if skillnum>=10:
                break        
        await interaction.followup.send("", view=self,embeds=embeds)


class LootGiverView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_loot_giving_view(self, sid, iid, pid, player_class, interaction):
        loot = []
        msg=f"Your Loot for this Reverse Run!: \n"
        categories_class = []
        for i in range(1,2):
            shopwindowitems = await get_shop_window_class(pid, sid, iid, player_class, categories_buckets_class[0])
            for bucket in shopwindowitems:
                if bucket["cards"] is not None:
                    for card in bucket["cards"][:-1]:
                        msg += f"{card} / "
                    lastname = bucket["cards"][-1]
                    msg += f"{lastname}\n"

                for skill in bucket["skills"]:
                    skillinfo = await db.get_skill_by_id(skill)
                    name = skillinfo["name"]
                    desc = skillinfo["description"]
                    msg += f"\n**{name}** : {desc}\n"
                    if skillinfo["special_code_flag"] != -1:
                        if hasattr(skillinfo["special_code_flag"], "__len__"):
                            for skill_flag in skillinfo["special_code_flag"]:
                                await db.set_inventory_value(pid, sid, iid, 'modifiers', skill_flag,
                                                            operation="$push")
                        else:
                            await db.set_inventory_value(pid, sid, iid, 'modifiers',
                                                        skillinfo['special_code_flag'],
                                                        operation="$push")

                msg += f"\n"
                await db.set_inventory_value(pid, sid, iid, 'loot', bucket['id'],
                                            operation="$push")

        for i in range(1,4):
            shopwindowitems = await get_shop_window_class(pid, sid, iid, player_class, categories_buckets_class[1])
            for bucket in shopwindowitems:
                if bucket["cards"] is not None:
                    for card in bucket["cards"][:-1]:
                        msg += f"{card} / "
                    lastname = bucket["cards"][-1]
                    msg += f"{lastname}\n"

                for skill in bucket["skills"]:
                    skillinfo = await db.get_skill_by_id(skill)
                    name = skillinfo["name"]
                    desc = skillinfo["description"]
                    msg += f"\n**{name}** : {desc}\n"
                    if skillinfo["special_code_flag"] != -1:
                        if hasattr(skillinfo["special_code_flag"], "__len__"):
                            for skill_flag in skillinfo["special_code_flag"]:
                                await db.set_inventory_value(pid, sid, iid, 'modifiers', skill_flag,
                                                            operation="$push")
                        else:
                            await db.set_inventory_value(pid, sid, iid, 'modifiers',
                                                        skillinfo['special_code_flag'],
                                                        operation="$push")

                msg += f"\n"
                await db.set_inventory_value(pid, sid, iid, 'loot', bucket['id'],
                                            operation="$push")
        for i in range(1,4):
            shopwindowitems = await get_shop_window_class(pid, sid, iid, player_class, categories_buckets_class[2])
            for bucket in shopwindowitems:
                if bucket["cards"] is not None:
                    for card in bucket["cards"][:-1]:
                        msg += f"{card} / "
                    lastname = bucket["cards"][-1]
                    msg += f"{lastname}\n"

                for skill in bucket["skills"]:
                    skillinfo = await db.get_skill_by_id(skill)
                    name = skillinfo["name"]
                    desc = skillinfo["description"]
                    msg += f"\n**{name}** : {desc}\n"
                    if skillinfo["special_code_flag"] != -1:
                        if hasattr(skillinfo["special_code_flag"], "__len__"):
                            for skill_flag in skillinfo["special_code_flag"]:
                                await db.set_inventory_value(pid, sid, iid, 'modifiers', skill_flag,
                                                            operation="$push")
                        else:
                            await db.set_inventory_value(pid, sid, iid, 'modifiers',
                                                        skillinfo['special_code_flag'],
                                                        operation="$push")

                msg += f"\n"
                await db.set_inventory_value(pid, sid, iid, 'loot', bucket['id'],
                                            operation="$push")
        for i in range(1,4):
            for cat in categories_buckets_generic:

                shopwindowitems = await get_shop_window_generic(pid, sid, iid, cat)
                for bucket in shopwindowitems:
                    if bucket["cards"] is not None:
                        for card in bucket["cards"][:-1]:
                            msg += f"{card} / "
                        lastname = bucket["cards"][-1]
                        msg += f"{lastname}\n"

                    for skill in bucket["skills"]:
                        skillinfo = await db.get_skill_by_id(skill)
                        name = skillinfo["name"]
                        desc = skillinfo["description"]
                        msg += f"\n**{name}** : {desc}\n"
                        if skillinfo["special_code_flag"] != -1:
                            if hasattr(skillinfo["special_code_flag"], "__len__"):
                                for skill_flag in skillinfo["special_code_flag"]:
                                    await db.set_inventory_value(pid, sid, iid, 'modifiers', skill_flag,
                                                                operation="$push")
                            else:
                                await db.set_inventory_value(pid, sid, iid, 'modifiers',
                                                            skillinfo['special_code_flag'],
                                                            operation="$push")

                    msg += f"\n"
                    await db.set_inventory_value(pid, sid, iid, 'loot', bucket['id'],
                                                operation="$push") 
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
          await interaction.followup.send(msg_overflow)
        await interaction.followup.send(msg_ov[-1:][0], view=self)
        
        quest_select_view = QuestSelectView()
        await quest_select_view.create_quest_view(sid, iid, pid, interaction)

