import discord
import core.kdr_db as db
import core.kdr_statics as statics
from discord.ui.button import ButtonStyle
from discord import Message, Thread, Embed
from views.panels.panel_status import StatusPanel
import views.view_selling as view_selling
from views.panels.panel_end_shop_phase import EndShopPanel
from views.panels.panel_pick_class_skill import PickClassSkillPanel
import random


class GambleSelector(discord.ui.Select):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, gamble_threshold: int, gamble_count: int, player_gold: int, min_gamble: int, max_gamble: int):
        super().__init__(placeholder=label, custom_id=custom_id)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.gamble_threshold = gamble_threshold
        self.gamble_count = gamble_count
        self.player_gold = player_gold
        self.min_gamble = min_gamble
        self.max_gamble = max_gamble
        self.min_values = 1
        self.max_values = 1

        low_band = 1
        if max_gamble>=25:
            low_band=10
        high_band = max_gamble+1 if max_gamble+1 < player_gold else player_gold
        low_band=int(low_band)
        high_band=int(high_band)

        for i in range(low_band, high_band):
            self.add_option(label=str(i), value=i)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player gambling.", ephemeral=True)
            return
        # disable view
        await self.disable_view(interaction)
        gamble_value = int(self.values[0])
        await interaction.response.send_message(f"<@{interaction.user.id}> has gambled {gamble_value}!")

        shop_stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        shop_stage += 1

        self.player_gold -= gamble_value

        gamble_threshold = random.randint(self.min_gamble, self.max_gamble)

        msg = ""
        skill_panel=None

        if gamble_value >= gamble_threshold:
            msg += f"Congratulations! You Won, you gambled {gamble_value} and needed {gamble_threshold}! Have a Skill!\n\n"
            player_class = await db.get_inventory_value(self.pid, self.sid, self.iid, 'class')
            class_skills = await db.get_static_class_value(player_class, "unique_skills")
            if class_skills and self.gamble_count < len(class_skills):
                skillid = class_skills[self.gamble_count]
                skill = await db.get_skill(skillid)
                skillname = skill["name"]
                skilldesc = skill["description"]
                skillid = skill["id"]
                skillimg = skill["img_url"]
                skill_panel = Embed(title=skillname, description=skilldesc)
                skill_panel.set_thumbnail(url=skillimg)

                await db.set_inventory_value(self.pid, self.sid, self.iid, 'skills', skillid, "$push")
                if skill["special_code_flag"] != -1:
                    if hasattr(skill["special_code_flag"], "__len__"):
                        for skill_flag in skill["special_code_flag"]:
                            await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', skill_flag,
                                                         operation="$push")
                    else:
                        await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', skill['special_code_flag'],
                                                     operation="$push")

                self.gamble_count += 1

                if gamble_value <= (self.max_gamble / 2):
                    msg += f"And with such high stakes luck, betting half or less of what you needed! As a reward, have twice your gold, {2 * gamble_value} back!"
                    self.player_gold += (gamble_value * 2)
            else:
                msg += f"But there are no more skills to claim! Enjoy your spoils!\n"
                self.gamble_count += 1
                self.player_gold += (gamble_value * 3)
        else:
            msg += f"That is unfortunate, you bet {gamble_value} and needed {gamble_threshold}."
        if skill_panel is not None:
            await self.thread.send(content=msg, embed=skill_panel)
        else:
            await self.thread.send(content=msg)

        await db.set_inventory_value(self.pid, self.sid, self.iid, 'gold', self.player_gold)
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'gamble_count', self.gamble_count)
        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())

        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', shop_stage)

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


class NoGambleButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, originalpanel):
        super().__init__(label=label, custom_id=custom_id)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player about to Gamble.", ephemeral=True)
            return
        # disable view
        await self.disable_view(interaction)
        await interaction.response.send_message(f"<@{interaction.user.id}> decided not to gamble this round!")

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


class GambleView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, pid, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread, gamble_threshold: int, gamble_count: int, can_sell: bool, player_gold: int,
                             min_gamble: int, max_gamble: int, original_panel):

        if player_gold > 0:
            gambleselector = GambleSelector(f'Gamble', "gamble", pid, sid, iid,
                                            status_message, status_panel_generator, thread, gamble_threshold, gamble_count,
                                            player_gold, min_gamble, max_gamble)
            self.add_item(gambleselector)

        nogamblebutton = NoGambleButton(f'Pass on Gambling', "nogamble", pid, sid, iid,
                                        status_message, status_panel_generator, thread, original_panel)
        self.add_item(nogamblebutton)

        if can_sell:
            button = view_selling.SellingButton("Sell a Skill or Treasure", "Selling",
                                   pid, sid, iid, status_message, status_panel_generator, thread, original_panel)
            self.add_item(button)
