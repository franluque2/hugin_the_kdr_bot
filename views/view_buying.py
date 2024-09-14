import discord
import core.kdr_db as db
from discord import Message, Thread, ActionRow
from discord.ui.button import ButtonStyle
from views.panels.panel_status import StatusPanel
import views.view_selling as view_selling
import views.panels.panel_buying as panel_buying
import views.panels.panel_tips as panel_tips
from core.kdr_data import type_converter
from views.panels.panel_additional_loot import AdditionalLootPanel
from config.config import LEVEL_THRESHOLDS


class BuyWindowButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, window):
        super().__init__(label=label, custom_id=custom_id)
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
        retmsg = f"<@{self.pid}> just bought a window for {cost} gold containing:\n"
        for bucket in self.window["buckets"]:
            if bucket["cards"] is not None:
                for card in bucket["cards"][:-1]:
                    retmsg += f"{card} /  "
                lastname = bucket["cards"][-1]
                retmsg += f"{lastname}\n"
            for skill in bucket["skills"]:
                skillinfo = await db.get_skill_by_id(skill)
                name = skillinfo["name"]
                desc = skillinfo["description"]
                retmsg += f"\n**{name}** : {desc}\n"
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
        retmsg += "\n Make sure to write it down in your Character Sheet!"
        await db.set_inventory_value(self.pid, self.sid, self.iid, "gold", playergold)
        offered_loot = await db.get_inventory_value(self.pid, self.sid, self.iid, "offered_loot")
        for offer in offered_loot[0]:
            if offer["name"] == self.window["name"]:
                offered_loot[0].remove(offer)
        await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", offered_loot)

        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())
        await interaction.followup.send(retmsg)
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


class BuyRandomWindowButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, window):
        super().__init__(label=label, custom_id=custom_id)
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
        retmsg = f"<@{self.pid}> just bought a random window for {cost} gold containing:\n"
        for bucket in self.window["buckets"]:
            await db.set_inventory_value(self.pid, self.sid, self.iid, 'loot', bucket['id'],
                                         operation="$push")
            if bucket["cards"] is not None:
                for card in bucket["cards"][:-1]:
                    retmsg += f"{card} /  "
                if len(bucket["cards"])>0:
                    lastname = bucket["cards"][-1]
                    retmsg += f"{lastname}\n"
            for skill in bucket["skills"]:
                skillinfo = await db.get_skill_by_id(skill)
                name = skillinfo["name"]
                desc = skillinfo["description"]
                retmsg += f"\n**{name}** : {desc}\n"
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
        retmsg += "\n Make sure to write it down in your Character Sheet!"
        await db.set_inventory_value(self.pid, self.sid, self.iid, "gold", playergold)

        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())
        await interaction.followup.send(retmsg)
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
                 thread: Thread):
        super().__init__(label=label, custom_id=custom_id)
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

        # disable
        await self.disable_view(interaction)
        await interaction.response.defer()

        stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', stage)
        await interaction.followup.send(f"Continuing to Tips!", ephemeral=True)
        await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", [])

        tipper = panel_tips.TipPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                     self.thread)
        await tipper.get_tip_panel()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class BuyView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, pid: str, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread, can_sell: bool, loot: list, categories_generic: list,
                             categories_class: list, categories_secret: list, original_panel, costreduction:int =0):

        playergold = await db.get_inventory_value(pid, sid, iid, "gold")
        playerclass = await db.get_inventory_value(pid, sid, iid, "class")
        roundnum=await db.get_instance_value(sid,iid,"active_round")


        row_buy_shown_class_count = 0

        for window in loot:
            raw_category = window["name"]
            category = type_converter[raw_category]
            cost = window["cost"]
            buy_window_btn = BuyWindowButton(f"Buy the shown {category} window for {cost} gold.", f"{raw_category}",
                                             pid, sid, iid, status_message, status_panel_generator, thread,
                                             window)
            if playergold < cost:
                buy_window_btn.disabled = True
            buy_window_btn.row = 0
            if (row_buy_shown_class_count < 3):
                buy_window_btn.row = 1
                row_buy_shown_class_count += 1
            self.add_item(buy_window_btn)
        playerlevel = 0

        xp=await db.get_inventory_value(pid, sid, iid, "XP")
        playerxp = xp if xp <= LEVEL_THRESHOLDS[-1] else LEVEL_THRESHOLDS[-1]

        for level in LEVEL_THRESHOLDS:
            if playerxp >= level:
                playerlevel += 1

        for cat in categories_generic:
            raw_category = cat[0]
            category = type_converter[raw_category]
            cost = cat[1] - costreduction
            window_objs = await panel_buying.get_shop_window_generic(pid, sid, iid, cat)
            if len(window_objs)>0:
                window = {"name": cat, "cost": cost, "buckets": window_objs}
                buy_window_btn = BuyRandomWindowButton(f"Buy a random {category} window for {cost} gold.",
                                                    f"{raw_category}_random",
                                                    pid, sid, iid, status_message, status_panel_generator, thread,
                                                    window)
                if (playergold < cost) or cat[3]>playerlevel:
                    buy_window_btn.disabled = True
                buy_window_btn.row = 2
                self.add_item(buy_window_btn)

        for cat in categories_class:
            raw_category = cat[0]
            category = type_converter[raw_category]
            cost = cat[1] - costreduction
            window_objs = await panel_buying.get_shop_window_class(pid, sid, iid, playerclass, cat)
            if len(window_objs)>0:
                window = {"name": cat, "cost": cost, "buckets": window_objs}
                buy_window_btn = BuyRandomWindowButton(f"Buy a random {category} window for {cost} gold.",
                                                    f"{raw_category}_random",
                                                    pid, sid, iid, status_message, status_panel_generator, thread,
                                                    window)
                if playergold < cost  or cat[3]>playerlevel:
                    buy_window_btn.disabled = True
                buy_window_btn.row = 3
                self.add_item(buy_window_btn)
        for cat in categories_secret:
            raw_category = cat[0]
            category = type_converter[raw_category]
            cost = cat[1] - costreduction
            if cat[3]<playerlevel:
                window_objs = await panel_buying.get_shop_window_secret(pid, sid, iid, cat)
                if len(window_objs)>0:
                    window = {"name": cat, "cost": cost, "buckets": window_objs}
                    buy_window_btn = BuyRandomWindowButton(f"Buy a random {category} Secret Card for {cost} gold.",
                                                        f"{raw_category}_random",
                                                        pid, sid, iid, status_message, status_panel_generator, thread,
                                                        window)
                    if playergold < cost:
                        buy_window_btn.disabled = True
                    buy_window_btn.row = 3
                    self.add_item(buy_window_btn)

        cont_button = ContinueButtonBuying("Continue to Tips.", "Continue",
                                           pid, sid, iid, status_message, status_panel_generator, thread)

        sell_button = view_selling.SellingButton("Sell a Skill or Treasure", "Selling",
                                    pid, sid, iid, status_message, status_panel_generator, thread, original_panel)
        sell_button.disabled = not can_sell

        cont_button.row = 4
        sell_button.row = 4

        self.add_item(cont_button)
        self.add_item(sell_button)
