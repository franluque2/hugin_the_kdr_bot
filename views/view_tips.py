import discord
import core.kdr_db as db
import core.kdr_statics as statics
from discord.ui.button import ButtonStyle
from discord import Message, Thread
from views.panels.panel_status import StatusPanel
import views.view_selling as view_selling
from views.panels.panel_end_shop_phase import EndShopPanel
from views.panels.panel_pick_class_skill import PickClassSkillPanel


class TipSelector(discord.ui.Select):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, tipval: int, total_tips: int, player_gold: int, min_tip: int, max_tip: int):
        super().__init__(placeholder=label, custom_id=custom_id)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.tipval = tipval
        self.total_tips = total_tips
        self.player_gold = player_gold
        self.min_tip = min_tip
        self.max_tip = max_tip
        self.min_values = 1
        self.max_values = 1
        low_band = min_tip - total_tips if min_tip > total_tips else 1
        if low_band>player_gold:
            low_band=1
        high_band = player_gold if max_tip-total_tips > player_gold else max_tip-total_tips
        if high_band-low_band>25:
            low_band=10
        low_band=int(low_band)
        high_band=int(high_band)
        counter=0
        for i in range(low_band, high_band + 1):
            if counter>=24:
                break
            self.add_option(label=str(i), value=i)
            counter+=1

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player tipping.", ephemeral=True)
            return
        # disable view
        await self.disable_view(interaction)
        tip_value = self.values[0]
        await interaction.response.send_message(f"<@{interaction.user.id}> has tipped {tip_value}!")

        shop_stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        shop_stage += 1

        self.player_gold -= int(tip_value)
        self.total_tips += int(tip_value)

        await db.set_inventory_value(self.pid, self.sid, self.iid, 'gold', self.player_gold)
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'total_tips', self.total_tips)
        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())

        if self.total_tips >= self.tipval:
            picker = PickClassSkillPanel(self.pid, self.sid,
                                         self.iid, self.status_message, self.status_panel_generator, self.thread)
            await picker.get_pick_class_skill_panel()
            return

        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', shop_stage)

        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())

        ender = EndShopPanel(self.pid, self.sid,
                             self.iid, self.status_message, self.status_panel_generator, self.thread)
        await ender.get_end_shop_panel()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Select):
                button.disabled = True
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class NoTipButton(discord.ui.Button):
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
            await interaction.response.send_message(f"You are not the player tipping.", ephemeral=True)
            return
        # disable view
        await self.disable_view(interaction)
        await interaction.response.send_message(f"<@{interaction.user.id}> decided not to tip this round!")

        shop_stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        shop_stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', shop_stage)
        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())

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


class TipView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, pid, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread, tipval: int, total_tips: int, can_sell: bool, player_gold: int,
                             min_tip: int, max_tip: int, original_panel):

        if player_gold > 0:
            tipselector = TipSelector(f'Tip', "tip", pid, sid, iid,
                                      status_message, status_panel_generator, thread, tipval, total_tips, player_gold,
                                      min_tip, max_tip)
            self.add_item(tipselector)

        notipbutton = NoTipButton(f'Pass on Tipping', "notip", pid, sid, iid,
                                  status_message, status_panel_generator, thread)
        self.add_item(notipbutton)

        if can_sell:
            button = view_selling.SellingButton("Sell a Skill or Treasure", "Selling",
                                   pid, sid, iid, status_message, status_panel_generator, thread, original_panel)
            self.add_item(button)
