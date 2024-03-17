import discord
import core.kdr_db as db
import core.kdr_statics as statics
from discord.ui.button import ButtonStyle
from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from views.panels.panel_end_shop_phase import EndShopPanel


class SkillClassButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, skill):
        super().__init__(label=label, custom_id=custom_id)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.skill = skill

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player picking a skill.", ephemeral=True)
            return
        # disable view
        await self.disable_view(interaction)
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'skills', self.skill['id'],
                                     operation="$push")
        if self.skill["special_code_flag"]!=-1:
            if hasattr(self.skill["special_code_flag"], "__len__"):
                for skill_flag in self.skill["special_code_flag"]:
                    await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', skill_flag,
                                        operation="$push")
            else:
                await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', self.skill['special_code_flag'],
                                        operation="$push")
        await interaction.response.send_message(f"<@{interaction.user.id}> selected: **{self.skill['name']}** , Remember to Mark it on your Sheet!")

        shop_stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        shop_stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', shop_stage)

        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())
        
        await db.set_inventory_value(self.pid,self.sid,self.iid,"got_tip_skill",True)

        ender = EndShopPanel(self.pid, self.sid,
                             self.iid, self.status_message, self.status_panel_generator, self.thread)
        await ender.get_end_shop_panel()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style=ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class SkillClassSelectView(discord.ui.View):
    def __init__(self, *, status_message, generator,timeout=1800):
        super().__init__(timeout=timeout)
        self.status_message = status_message
        self.generator = generator

    async def create_buttons(self, pid, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread, skills: list):
        id=0
        for c in skills:
            name = c['name']
            button = SkillClassButton(f'{name}', str(id), pid, sid, iid,
                                 status_message, status_panel_generator, thread, c)
            self.add_item(button)
            id+=1
