import discord
import core.kdr_db as db
from discord import Message, Thread
from discord.ui.button import ButtonStyle
from views.panels.panel_status import StatusPanel
import views.panels.panel_treasure as panel_treasure
import views.panels.panel_buying as panel_buying
from views.panels.shopkeeper_intro_panel import ShopIntroPanel
from core.kdr_data import SpecialSkillHandling


class TreasureButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, treasure):
        super().__init__(label=label, custom_id=custom_id)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.treasure = treasure

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player using this shop.", ephemeral=True)
            return
        await self.disable_view(interaction)
        shop_stage = await db.get_inventory_value(self.pid, self.sid, self.iid, "shop_stage")

        shop_stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', shop_stage)
        await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_treasure", [])
        await db.set_inventory_value(self.pid, self.sid, self.iid, "treasures", self.treasure["id"], "$push")

        treasurename = self.treasure["name"]
        await interaction.response.send_message(f"You picked up a {treasurename}! Remember to mark it on your Sheet!")

        special_flags = list(await db.get_inventory_value(self.pid, self.sid, self.iid, 'modifiers'))

        if SpecialSkillHandling.SKILL_BINGO_MACHINE_GO.value in special_flags:
            next_treasures = panel_treasure.TreasurePanel(self.pid, self.sid,
                                                          self.iid, self.status_message, self.status_panel_generator,
                                                          self.thread)

            special_flags.remove(SpecialSkillHandling.SKILL_BINGO_MACHINE_GO.value)
            await db.set_inventory_value(self.pid, self.sid, self.iid, "modifiers", special_flags)

            await next_treasures.get_treasure_panel()
            return
        shopintro=ShopIntroPanel(self.pid,self.sid,self.iid,self.thread)
        await shopintro.get_shop_intro()

        shopper = panel_buying.BuyPanel(self.pid, self.sid,
                                        self.iid, self.status_message, self.status_panel_generator, self.thread)
        await shopper.get_buy_panel()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class TreasureView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, pid: str, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread, treasures):
        i = 0
        for treasure in treasures:
            treasurename = treasure["name"]
            treasureid = treasure["id"]
            treasure_button = TreasureButton(f"Get {treasurename}.", f"{i}",
                                             pid, sid, iid, status_message, status_panel_generator, thread,
                                             treasure)
            self.add_item(treasure_button)
            i += 1
