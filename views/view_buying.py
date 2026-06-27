import discord
import core.kdr_db as db
from discord import Message, Thread, ActionRow
from discord.ui.button import ButtonStyle
from views.panels.panel_status import StatusPanel
import views.view_selling as view_selling
import views.panels.panel_buying as panel_buying
import views.panels.panel_gamble as panel_gamble
from core.kdr_data import type_converter
from views.panels.panel_additional_loot import AdditionalLootPanel
from core.kdr_quests import complete_quest
from config.config import LEVEL_THRESHOLDS
import core.kdr_ansi as ansi
from core.kdr_web import get_shop_url


class BuyWindowButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, window, style: ButtonStyle = ButtonStyle.secondary):
        super().__init__(label=label, custom_id=custom_id, style=style)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.window = window

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player using this shop.", ephemeral=True)
            return
        await self.disable_view(interaction)
        await interaction.response.defer()
        cost = self.window["cost"]
        description = f"<@{self.pid}> just bought a window for **{cost}** gold containing:\n\n"
        for bucket in self.window["buckets"]:
            if bucket["cards"]:
                description += "### CARDS\n"
                description += f"**{' / '.join(bucket['cards'])}**\n\n"
            
            if bucket["skills"]:
                for skill in bucket["skills"]:
                    skillinfo = await db.get_skill_by_id(skill)
                    name = skillinfo["name"]
                    desc = skillinfo.get("description", "No description") or "No description available"
                    description += f"**{name}**\n{desc}\n\n"
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
            if bucket.get("recipes"):
                for recipe in bucket["recipes"]:
                    recipe_name = recipe if isinstance(recipe, str) else recipe.get("name", "")
                    if isinstance(recipe, str):
                        recipe_data = await db.get_recipe_by_name(recipe)
                        recipe_desc = recipe_data["description"] if recipe_data else ""
                    else:
                        recipe_desc = recipe.get("description", "")
                    await db.set_inventory_value(self.pid, self.sid, self.iid, 'recipes', {
                        "name": recipe_name,
                        "description": recipe_desc
                    }, operation="$push")
                    description += f"**Recipe: {recipe_name}**\n{recipe_desc}\n\n"
            await db.set_inventory_value(self.pid, self.sid, self.iid, 'loot', bucket['id'],
                                         operation="$push")
            
            extra_buckets=await db.get_bucket_value(bucket["id"],"extra_buckets")
            if extra_buckets is not None and len(extra_buckets)>0:
                takenbuckets=await db.get_inventory_value(self.pid,self.sid,self.iid,"loot")
                buckets=[]
                skills=[]
                for extra_bucket in extra_buckets:
                    if extra_bucket not in takenbuckets:
                        buckets.append(extra_bucket)
                        bucketinfo=await db.get_bucket(extra_bucket)
                        await db.set_inventory_value(self.pid, self.sid, self.iid, 'loot', bucketinfo['id'],
                            operation="$push")
                        
                        for skill in bucketinfo["skills"]:
                            skills.append(skill)
                            skillinfo = await db.get_skill_by_id(skill)
                            name = skillinfo["name"]
                            desc = skillinfo["description"]
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
                    shower=AdditionalLootPanel(self.pid,self.sid,self.iid,self.status_message,self.status_panel_generator,self.thread,buckets,skills)
                    await shower.get_additional_loot_panel()
        playergold = await db.get_inventory_value(self.pid, self.sid, self.iid, "gold")
        playergold -= self.window["cost"]
        description += "\nMake sure to check your character sheet!"
        await db.set_inventory_value(self.pid, self.sid, self.iid, "gold", playergold)
        offered_loot = await db.get_inventory_value(self.pid, self.sid, self.iid, "offered_loot")
        for offer in offered_loot[0]:
            if offer["name"] == self.window["name"]:
                offered_loot[0].remove(offer)
        await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", offered_loot)

        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())
        
        await interaction.followup.send(description.strip())
        shopper = panel_buying.BuyPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                        self.thread)
        await shopper.get_buy_panel()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class RerollShopButton(discord.ui.Button):
    def __init__(self, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, original_view: discord.ui.View, remaining: int):
        super().__init__(label=f"Reroll Shop ({remaining} left)", style=ButtonStyle.primary, custom_id="reroll_shop_btn")
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.original_view = original_view

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player using this shop.", ephemeral=True)
            return

        # Correct way to disable the current view properly
        for item in self.original_view.children:
            item.disabled = True
        await interaction.message.edit(view=self.original_view)

        await interaction.response.defer()
        
        # Verify CHA and Rerolls again (security check)
        inventory = await db.get_inventory(self.pid, self.sid, self.iid)
        cha = inventory.get("CHA", 0)
        used = inventory.get("shop_rerolls_used", 0)
        max_rerolls = cha // 3

        if used >= max_rerolls:
            await interaction.followup.send("You have no rerolls left for this shop phase.", ephemeral=True)
            return

        # Increment used rerolls
        await db.set_inventory_value(self.pid, self.sid, self.iid, "shop_rerolls_used", used + 1)
        
        # Clear offered loot to trigger a new generation
        await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", [])
        
        # Inform the player
        await interaction.followup.send(f"<@{self.pid}> used a CHA reroll! ({used + 1}/{max_rerolls})", ephemeral=False)
        
        # Update status message
        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())
        
        # Refresh the buy panel
        shopper = panel_buying.BuyPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                        self.thread)
        await shopper.get_buy_panel()


class BuyRandomWindowButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, window, style: ButtonStyle = ButtonStyle.secondary):
        super().__init__(label=label, custom_id=custom_id, style=style)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.window = window

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player using this shop.", ephemeral=True)
            return
        await interaction.response.defer()
        await self.disable_view(interaction)
        cost = self.window["cost"]
        description = f"<@{self.pid}> just bought a random window for {cost} gold containing:\n\n"
        for bucket in self.window["buckets"]:
            await db.set_inventory_value(self.pid, self.sid, self.iid, 'loot', bucket['id'],
                                         operation="$push")
            if bucket["cards"]:
                description += "### CARDS\n"
                description += f"**{' / '.join(bucket['cards'])}**\n\n"
            
            for skill in bucket["skills"]:
                skillinfo = await db.get_skill_by_id(skill)
                name = skillinfo["name"]
                desc = skillinfo.get("description", "No description") or "No description available"
                description += f"**{name}**\n{desc}\n\n"
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
            
            if bucket.get("recipes"):
                for recipe in bucket["recipes"]:
                    recipe_name = recipe if isinstance(recipe, str) else recipe.get("name", "")
                    if isinstance(recipe, str):
                        recipe_data = await db.get_recipe_by_name(recipe)
                        recipe_desc = recipe_data["description"] if recipe_data else ""
                    else:
                        recipe_desc = recipe.get("description", "")
                    await db.set_inventory_value(self.pid, self.sid, self.iid, 'recipes', {
                        "name": recipe_name,
                        "description": recipe_desc
                    }, operation="$push")
                    description += f"**Recipe: {recipe_name}**\n{recipe_desc}\n\n"
            
            extra_buckets=await db.get_bucket_value(bucket["id"],"extra_buckets")
            if extra_buckets is not None and len(extra_buckets)>0:
                takenbuckets=await db.get_inventory_value(self.pid,self.sid,self.iid,"loot")
                buckets=[]
                skills=[]
                for extra_bucket in extra_buckets:
                    if extra_bucket not in takenbuckets:
                        buckets.append(extra_bucket)
                        bucketinfo=await db.get_bucket(extra_bucket)
                        await db.set_inventory_value(self.pid, self.sid, self.iid, 'loot', bucketinfo['id'],
                            operation="$push")
                        
                        for skill in bucketinfo["skills"]:
                            skills.append(skill)
                            skillinfo = await db.get_skill_by_id(skill)
                            name = skillinfo["name"]
                            desc = skillinfo["description"]
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
                    shower=AdditionalLootPanel(self.pid,self.sid,self.iid,self.status_message,self.status_panel_generator,self.thread,buckets,skills)
                    await shower.get_additional_loot_panel()
                            

            await db.set_inventory_value(self.pid, self.sid, self.iid, 'loot', bucket['id'],
                                         operation="$push")
        playergold = await db.get_inventory_value(self.pid, self.sid, self.iid, "gold")
        playergold -= self.window["cost"]
        description += "\nMake sure to check your character sheet!"
        await db.set_inventory_value(self.pid, self.sid, self.iid, "gold", playergold)
        offered_loot = await db.get_inventory_value(self.pid, self.sid, self.iid, "offered_loot")
        if offered_loot and len(offered_loot) > 0:
            for offer in offered_loot[0]:
                if offer["name"] == self.window["name"]:
                    offered_loot[0].remove(offer)
            await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", offered_loot)

        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())
        
        await interaction.followup.send(description.strip())
        shopper = panel_buying.BuyPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                        self.thread)
        await shopper.get_buy_panel()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class ContinueButtonBuying(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, style: ButtonStyle = ButtonStyle.secondary):
        super().__init__(label=label, custom_id=custom_id, style=style)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player using this shop.", ephemeral=True)
            return

        await interaction.response.defer()

        # disable
        await self.disable_view(interaction)

        # Check if Gambler
        from core.kdr_data import SpecialClassHandling
        player_data = await db.get_inventory(self.pid, self.sid, self.iid)
        is_gambler = (SpecialClassHandling.CLASS_GAMBLER.value in player_data.get("modifiers", [])
                      or player_data.get("class") == "gambler")

        stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', stage)
        
        await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", [])
        await db.set_inventory_value(self.pid, self.sid, self.iid, "shop_rerolls_used", 0)

        if is_gambler:
            await interaction.followup.send(f"Wait! It's Gamble Time!", ephemeral=True)
            gambler = panel_gamble.GamblePanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                             self.thread)
            await gambler.get_gamble_panel()
        else:
            from views.panels.panel_end_shop_phase import EndShopPanel
            await interaction.followup.send(f"Finishing Shop!", ephemeral=True)
            ender = EndShopPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                 self.thread)
            await ender.get_end_shop_panel()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()

class CompleteQuestConfirmView(discord.ui.View):
    def __init__(self, pid, sid, iid, status_message, status_panel_generator, thread, original_view):
        super().__init__(timeout=120)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.original_view = original_view

    @discord.ui.button(label="Hand in Quest", style=ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message("Not your shop.", ephemeral=True)
            return

        await interaction.response.defer()

        quest_info, reward_msg = await complete_quest(self.pid, self.sid, self.iid)
        if not quest_info:
            await interaction.followup.send(reward_msg, ephemeral=True)
            return

        embed = discord.Embed(title=f"Quest Completed: {quest_info['name']}", color=discord.Color.gold())
        embed.description = f"Well done! You have completed your quest and earned the following rewards:\n{reward_msg}"
        await self.thread.send(embed=embed)
        
        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())
        
        # Refresh the buy panel to return to the shop
        shopper = panel_buying.BuyPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                        self.thread)
        await shopper.get_buy_panel()

    @discord.ui.button(label="Go Back", style=ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message("Not your shop.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Freshly generate the buy panel to restore the original view and embeds
        shopper = panel_buying.BuyPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                        self.thread)
        await shopper.get_buy_panel()

class CompleteQuestButton(discord.ui.Button):
    def __init__(self, pid, sid, iid, status_message, status_panel_generator, thread):
        super().__init__(label="Complete Quest", style=ButtonStyle.green, custom_id="complete_quest_btn")
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player using this shop.", ephemeral=True)
            return
            
        inventory = await db.get_inventory(self.pid, self.sid, self.iid)
        active_quest = inventory.get("active_quest")
        if not active_quest:
            await interaction.response.send_message("No active quest found.", ephemeral=True)
            return
            
        quest_info = await db.get_quest_by_id(active_quest["id"])
        if not quest_info:
            await interaction.response.send_message("Quest data missing from database.", ephemeral=True)
            return

        # Create confirmation embed with detailed reward info
        embed = discord.Embed(
            title=f"Hand in Quest: {quest_info['name']}?",
            description=f"**Task**: {quest_info['description']}\n\n**Handing this in will grant you:**",
            color=discord.Color.blue()
        )
        
        rewards = quest_info.get("rewards", {})
        
        if "stats" in rewards:
            stat_text = ""
            for stat, val in rewards["stats"].items():
                stat_text += f"**+{val} {stat.upper()}**\n"
            embed.add_field(name="Attributes", value=stat_text, inline=False)
            
        if "gold" in rewards:
            embed.add_field(name="Currency", value=f"**{rewards['gold']} Gold**", inline=True)
            
        if "skills" in rewards:
            skill_text = ""
            for skill_entry in rewards["skills"]:
                if isinstance(skill_entry, dict):
                    skill_text += f"**{skill_entry['name']}**\n{skill_entry.get('description', '')}\n"
                else:
                    skill_info = await db.get_skill_by_id(skill_entry)
                    if skill_info:
                        skill_text += f"**{skill_info['name']}**\n{skill_info.get('description', 'No description')}\n"
            if skill_text:
                embed.add_field(name="Skill Rewards", value=skill_text, inline=False)

        if "cards" in rewards:
            card_text = ""
            for card_id in rewards["cards"]:
                card_info = await db.get_treasure(card_id)
                if card_info:
                    card_text += f"**{card_info['name']}**\n{card_info.get('description', 'No description')}\n"
            if card_text:
                embed.add_field(name="Treasure Rewards", value=card_text, inline=False)

        confirm_view = CompleteQuestConfirmView(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator, self.thread, self.view)
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class BuyView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, pid: str, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread, can_sell: bool, loot: list, categories_generic: list,
                             categories_class: list, categories_secret: list, original_panel, costreduction:int =0):

        playergold = await db.get_inventory_value(pid, sid, iid, "gold")
        playerclass = await db.get_inventory_value(pid, sid, iid, "class")

        from core.kdr_data import SpecialClassHandling
        modifiers = await db.get_inventory_value(pid, sid, iid, "modifiers")
        if SpecialClassHandling.CLASS_SLIME.value in modifiers:
            absorbed = await db.get_inventory_value(pid, sid, iid, "absorbed_classes")
            if absorbed:
                playerclass = absorbed[-1]
        
        # Row mapping:
        # 0: Shown Class Loot
        # 1: Shown Generic Loot
        # 2: Random Class Loot
        # 3: Random Generic / Secret Loot
        # 4: System (Continue, Sell, Reroll)

        # 1. Process "Shown" Loot windows
        class_cat_ids = [c[0] for c in categories_class]
        
        shown_class_count = 0
        shown_generic_count = 0
        
        for window in loot:
            raw_category = window["name"]
            category_name = type_converter[raw_category]
            cost = window["cost"] - costreduction
            window["cost"] = cost
            
            is_class = raw_category in class_cat_ids
            style = ButtonStyle.primary if is_class else ButtonStyle.success
            
            # Use separate rows and limit to 2 per row for better spacing
            if is_class:
                row = 0 if shown_class_count < 2 else 0 # actually row 0 is fine
                shown_class_count += 1
            else:
                row = 1 if shown_generic_count < 2 else 1
                shown_generic_count += 1
            
            label = f"Buy Shown {category_name} ({cost}g)"
            buy_window_btn = BuyWindowButton(label, f"{raw_category}",
                                             pid, sid, iid, status_message, status_panel_generator, thread,
                                             window, style=style)
            
            if playergold < cost:
                buy_window_btn.disabled = True
            buy_window_btn.row = row
            self.add_item(buy_window_btn)

        # 2. Get Player Level for random/secret checks
        playerlevel = 0
        xp = await db.get_inventory_value(pid, sid, iid, "XP")
        playerxp = xp if xp <= LEVEL_THRESHOLDS[-1] else LEVEL_THRESHOLDS[-1]
        for level in LEVEL_THRESHOLDS:
            if playerxp >= level:
                playerlevel += 1

        # 3. Random Class Loot Buttons (Row 2)
        for cat in categories_class:
            raw_category = cat[0]
            category_name = type_converter[raw_category]
            cost = cat[1] - costreduction
            window_objs = await panel_buying.get_shop_window_class(pid, sid, iid, playerclass, cat)
            
            if len(window_objs) > 0:
                window = {"name": cat, "cost": cost, "buckets": window_objs}
                label = f"Random {category_name} ({cost}g)"
                buy_window_btn = BuyRandomWindowButton(label,
                                                    f"{raw_category}_random",
                                                    pid, sid, iid, status_message, status_panel_generator, thread,
                                                    window, style=ButtonStyle.primary)
                if (playergold < cost) or cat[3] > playerlevel:
                    buy_window_btn.disabled = True
                buy_window_btn.row = 2
                self.add_item(buy_window_btn)

        # 4. Random Generic Loot Buttons (Row 3)
        for cat in categories_generic:
            raw_category = cat[0]
            category_name = type_converter[raw_category]
            cost = cat[1] - costreduction
            window_objs = await panel_buying.get_shop_window_generic(pid, sid, iid, cat)
            
            if len(window_objs) > 0:
                window = {"name": cat, "cost": cost, "buckets": window_objs}
                label = f"Random {category_name} ({cost}g)"
                buy_window_btn = BuyRandomWindowButton(label,
                                                    f"{raw_category}_random",
                                                    pid, sid, iid, status_message, status_panel_generator, thread,
                                                    window, style=ButtonStyle.success)
                if (playergold < cost) or cat[3] > playerlevel:
                    buy_window_btn.disabled = True
                buy_window_btn.row = 3
                self.add_item(buy_window_btn)

        # 5. Secret Card Buttons (Row 3)
        for cat in categories_secret:
            raw_category = cat[0]
            category_name = type_converter[raw_category]
            cost = cat[1] - costreduction
            if cat[3] < playerlevel:
                window_objs = await panel_buying.get_shop_window_secret(pid, sid, iid, cat)
                if len(window_objs) > 0:
                    window = {"name": cat, "cost": cost, "buckets": window_objs}
                    label = f"Secret {category_name} ({cost}g)"
                    buy_window_btn = BuyRandomWindowButton(label,
                                                        f"{raw_category}_random",
                                                        pid, sid, iid, status_message, status_panel_generator, thread,
                                                        window, style=ButtonStyle.secondary)
                    if playergold < cost:
                        buy_window_btn.disabled = True
                    buy_window_btn.row = 3
                    self.add_item(buy_window_btn)

        # 6. System Buttons
        # Add Inspect Shop Button
        shop_url = get_shop_url(sid, iid, pid)
        inspect_btn = discord.ui.Button(label="Inspect Shop Content", url=shop_url, row=4)
        self.add_item(inspect_btn)

        from core.kdr_data import SpecialClassHandling
        inventory = await db.get_inventory(pid, sid, iid)
        is_gambler = (SpecialClassHandling.CLASS_GAMBLER.value in inventory.get("modifiers", [])
                      or inventory.get("class") == "gambler")
        cont_label = "Gamble!" if is_gambler else "Finish Shop"

        cont_button = ContinueButtonBuying(cont_label, "Continue",
                                           pid, sid, iid, status_message, status_panel_generator, thread,
                                           style=ButtonStyle.primary if is_gambler else ButtonStyle.secondary)

        sell_button = view_selling.SellingButton("Sell Skill/Treasure", "Selling",
                                    pid, sid, iid, status_message, status_panel_generator, thread, original_panel,
                                    style=ButtonStyle.danger if can_sell else ButtonStyle.secondary)
        sell_button.disabled = not can_sell

        cont_button.row = 4
        sell_button.row = 4

        self.add_item(cont_button)
        self.add_item(sell_button)

        inventory = await db.get_inventory(pid, sid, iid)
        active_quest = inventory.get("active_quest")
        if active_quest and not active_quest.get("completed"):
            quest_button = CompleteQuestButton(pid, sid, iid, status_message, status_panel_generator, thread)
            quest_button.row = 4
            self.add_item(quest_button)

        # CHA Reroll Logic
        cha = inventory.get("CHA", 0)
        used = inventory.get("shop_rerolls_used", 0)
        max_rerolls = cha // 3
        if max_rerolls > used:
            reroll_button = RerollShopButton(pid, sid, iid, status_message, status_panel_generator, thread, self, max_rerolls - used)
            reroll_button.row = 4
            self.add_item(reroll_button)
