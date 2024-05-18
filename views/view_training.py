import discord
import core.kdr_db as db
from discord import Message, Thread
from discord.ui.button import ButtonStyle
from views.panels.panel_status import StatusPanel
import views.view_selling as view_selling
from config.config import LEVEL_THRESHOLDS
import views.panels.panel_pick_skill as panel_pick_skill
from views.panels.panel_level_attribute import LevelAttributePanel


class TrainingButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, gold_to_pay: int):
        super().__init__(label=label, custom_id=custom_id)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.gold_to_pay = gold_to_pay

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player using this shop.", ephemeral=True)
            return
        await self.disable_view(interaction)

        player_gold = await db.get_inventory_value(self.pid, self.sid, self.iid, 'gold')
        player_xp = await db.get_inventory_value(self.pid, self.sid, self.iid, 'XP')

        player_gold -= self.gold_to_pay
        for t in LEVEL_THRESHOLDS:
            if player_xp < t:
                player_xp = t
                break

        shop_stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        shop_stage -= 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', shop_stage)

        player_gold = await db.set_inventory_value(self.pid, self.sid, self.iid, 'gold', player_gold)
        player_xp = await db.set_inventory_value(self.pid, self.sid, self.iid, 'XP', player_xp)

        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())

        picker = panel_pick_skill.PickSkillPanel(self.pid, self.sid, self.iid,
                                                 self.status_message, self.status_panel_generator, self.thread)
        await picker.get_pick_skill_panel()
        await interaction.response.send_message(f"Trained!", ephemeral=True)

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class ContinueButtonTraining(discord.ui.Button):
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
        await interaction.response.defer(ephemeral=True)

        stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', stage)
        await interaction.followup.send(f"Continuing to Stat Leveling or Treasures!", ephemeral=True)
        increaser = LevelAttributePanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                        self.thread)
        await increaser.get_level_attribute_panel()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class TrainingView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, pid: str, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread, can_sell, can_train, gold_to_pay):
        btn_continue = ContinueButtonTraining("Continue to Stat Leveling.", "Continue",
                                              pid, sid, iid,
                                              status_message, status_panel_generator, thread)
        self.add_item(btn_continue)
        if can_train:
            trainbutton = TrainingButton(f"Spend {int(gold_to_pay)} gold to train to the next level.", "Training",
                                         pid, sid, iid, status_message, status_panel_generator, thread,
                                         gold_to_pay)
            #sellbutton = view_selling.SellingButton("Sell a Skill or Treasure", "Selling",
                                      # pid, sid, iid, status_message, status_panel_generator, thread, self)

            trainbutton.disabled = not can_train
            #sellbutton.disabled = not can_sell

            self.add_item(trainbutton)
            #self.add_item(sellbutton)
