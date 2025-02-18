import discord
import core.kdr_db as db
from discord import Message, Thread, ActionRow
from discord.ui.button import ButtonStyle
from views.panels.panel_status import StatusPanel
import views.panels.panel_reverse_sacrifice as panel_reverse_sacrifice
import views.panels.panel_tips as panel_tips
from core.kdr_data import type_converter
from views.panels.panel_additional_loot import AdditionalLootPanel
from config.config import LEVEL_THRESHOLDS
from views.panels.panel_end_shop_phase import EndShopPanel


class ReverseSacrificeButton(discord.ui.Button):
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
        statdown = self.window["statdown"]

        stat=await db.get_inventory_value(self.pid,self.sid,self.iid,statdown)
        stat-=3
        await db.set_inventory_value(self.pid,self.sid,self.iid,statdown,stat)
        retmsg = f"<@{self.pid}> has given up the following:\n"
        retmsg +=f"**-3 {statdown}**\n"
        lostskill=await db.get_skill_by_id(self.window["skill"])
        lostskillname = lostskill["name"]
        lostskilldesc = lostskill["description"]
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'skills', lostskill['id'],
                                     operation="$pull")

        retmsg += f"\n**{lostskillname}** : {lostskilldesc}\n"

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
                                             operation="$pull")
                if skillinfo["special_code_flag"] != -1:
                    if hasattr(skillinfo["special_code_flag"], "__len__"):
                        for skill_flag in skillinfo["special_code_flag"]:
                            await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', skill_flag,
                                                         operation="$pull")
                    else:
                        await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers',
                                                     skillinfo['special_code_flag'],
                                                     operation="$pull")
            await db.set_inventory_value(self.pid, self.sid, self.iid, 'loot', bucket['id'],
                                         operation="$pull")
            
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
                            operation="$pull")
                        
                        for skill in bucketinfo["skills"]:
                            skills.append(skill)
                            skillinfo = await db.get_skill_by_id(skill)
                            name = skillinfo["name"]
                            desc = skillinfo["description"]
                            await db.set_inventory_value(self.pid, self.sid, self.iid, 'skills', skillinfo['id'],
                                                        operation="$pull")
                            if skillinfo["special_code_flag"] != -1:
                                if hasattr(skillinfo["special_code_flag"], "__len__"):
                                    for skill_flag in skillinfo["special_code_flag"]:
                                        await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', skill_flag,
                                                                    operation="$pull")
                                else:
                                    await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers',
                                                                skillinfo['special_code_flag'],
                                                                operation="$pull")
                    shower=AdditionalLootPanel(self.pid,self.sid,self.iid,self.status_message,self.status_panel_generator,self.thread,buckets,skills)
                    await shower.get_additional_loot_panel()
        retmsg += "\n Make sure to write it down in your Character Sheet!"
        offered_loot = await db.get_inventory_value(self.pid, self.sid, self.iid, "offered_loot")
        for offer in offered_loot[0]:
            if offer["name"] == self.window["name"]:
                offered_loot[0].remove(offer)
        await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_loot", offered_loot)

        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())
        await interaction.followup.send(retmsg)

        ender = EndShopPanel(self.pid, self.sid,
                             self.iid, self.status_message, self.status_panel_generator, self.thread)
        await ender.get_end_shop_panel()


    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class ReverseSacrificeView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, pid: str, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread, loot: list):

        row_buy_shown_class_count = 0

        for window in loot:
            id=window["id"]+1
            buy_window_btn = ReverseSacrificeButton(f"Give up all things in Window {id}.", f"{id}",
                                             pid, sid, iid, status_message, status_panel_generator, thread,
                                             window)
            buy_window_btn.row = 0
            if (row_buy_shown_class_count < 3):
                buy_window_btn.row = 1
                row_buy_shown_class_count += 1
            self.add_item(buy_window_btn)
        playerlevel = 0