import discord
from discord.ui.button import ButtonStyle
from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from views.panels.panel_selling import SellPanel


class SellingButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, original_panel):
        super().__init__(label=label, custom_id=custom_id)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.style=ButtonStyle.secondary
        self.original_panel=original_panel

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player using this shop.", ephemeral=True)
            return
        await self.disable_view(interaction)
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        seller=SellPanel(self.pid,self.sid,self.iid,self.status_message,self.status_panel_generator,self.thread,self.original_panel)
        await seller.get_sell_panel()
        await interaction.response.send_message("Getting Sell Panel", ephemeral=True )

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()
