import discord
import core.kdr_db as db
from discord import Message, Thread
from discord.ui.button import ButtonStyle
from views.panels.panel_status import StatusPanel
from config.config import MAX_RPG_STAT_LEVEL
import views.panels.panel_level_attribute as level_attribute_panel


class IncreaseStatButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, stat: str, statval: int):
        super().__init__(label=label, custom_id=custom_id)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.stat = stat
        self.statval = statval

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player using this shop.", ephemeral=True)
            return
        await self.disable_view(interaction)

        await db.set_inventory_value(self.pid, self.sid, self.iid, self.stat, self.statval + 1)
        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())

        trainer = level_attribute_panel.LevelAttributePanel(self.pid, self.sid, self.iid,
                                                            self.status_message, self.status_panel_generator,
                                                            self.thread)
        await trainer.get_level_attribute_panel()
        await interaction.response.send_message(f"You Leveled Up {self.stat}!", ephemeral=True)

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class IncreaseStatView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, pid: str, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread, str: int, dex: int, con: int):
        levelup_STR = IncreaseStatButton(f"Level Up STR.", "str_lvlup",
                                         pid, sid, iid, status_message, status_panel_generator, thread,
                                         "STR", str)
        levelup_DEX = IncreaseStatButton(f"Level Up DEX", "dex_lvlup",
                                         pid, sid, iid, status_message, status_panel_generator, thread,
                                         "DEX", dex)
        levelup_CON = IncreaseStatButton(f"Level UP CON", "con_lvlup",
                                         pid, sid, iid, status_message, status_panel_generator, thread,
                                         "CON", con)

        levelup_STR.disabled = str >= MAX_RPG_STAT_LEVEL
        levelup_DEX.disabled = dex >= MAX_RPG_STAT_LEVEL
        levelup_CON.disabled = con >= MAX_RPG_STAT_LEVEL

        self.add_item(levelup_STR)
        self.add_item(levelup_DEX)
        self.add_item(levelup_CON)
