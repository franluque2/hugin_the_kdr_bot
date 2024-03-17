import discord
import core.kdr_db as db
from discord.ui.button import ButtonStyle
from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from views.panels.panel_end_shop_phase import EndShopPanel
from views.panels.panel_interface import panel_interpreter
from core.kdr_data import SpecialSkillHandling



class SellSelector(discord.ui.Select):
    def __init__(self, label: str, custom_id: str, pid: str, sid, iid,
                 status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, player_gold: int, sellable_skills: list, treasures: list, original_panel):
        super().__init__(placeholder=label, custom_id=custom_id)
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.sellable_skills = sellable_skills
        self.treasures = treasures
        self.player_gold = player_gold
        self.min_values = 1
        self.original_panel=original_panel

        shown_skills = []
        shown_treasures = []

        
        counter=0

        for i in sellable_skills:
            if i not in shown_skills:
                if counter>=24:
                    break
                self.add_option(label=i["name"], value=i["id"])
                shown_skills.append(i)
                counter+=1

        for i in treasures:
            if i not in shown_treasures:
                if counter>=24:
                    break
                self.add_option(label=i["name"], value=i["id"])
                shown_treasures.append(i)
                counter+=1

        self.max_values = counter

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player selling.", ephemeral=True)
            return
        await self.disable_view(interaction)
        playertreasures = list(await db.get_inventory_value(self.pid, self.sid, self.iid, "treasures"))
        playerskills = list(await db.get_inventory_value(self.pid, self.sid, self.iid, "skills"))
        playermodifiers = list(await db.get_inventory_value(self.pid, self.sid, self.iid, "modifiers"))

        sold_things = self.values
        sold_things_str = ""
        final_gold_gained = 0

        for i in sold_things:

            # do sellable treasures
            for sellabletreasure in self.treasures:

                # if item does not equal sellable treasure id, continue
                if i != sellabletreasure["id"]:
                    continue

                # normal treasure selling
                playertreasures.remove(i)
                final_gold_gained += sellabletreasure["sell_value"]
                treasurename = sellabletreasure["name"]
                sold_things_str += f"{treasurename} "

            # do sellable skills
            for sellableskill in self.sellable_skills:

                # if item does not equal sellable skill id, continue
                if i != sellableskill["id"]:
                    continue

                # if no code flag, do normal skill selling
                if sellableskill["special_code_flag"] == -1:
                    playerskills.remove(i)
                    final_gold_gained += sellableskill["sell_value"]
                    skillname = sellableskill["name"]
                    sold_things_str += f"{skillname} "
                    continue
                
                if sellableskill["special_code_flag"] != -1:
                    playerskills.remove(i)
                    final_gold_gained += sellableskill["sell_value"]
                    skillname = sellableskill["name"]
                    sold_things_str += f"{skillname} "

                    # if special code flag has len
                    if hasattr(sellableskill["special_code_flag"], "__len__"):
                        # loop through skill flags and remove each modifier
                        for skill_flag in sellableskill["special_code_flag"]:
                            playermodifiers.remove(skill_flag)
                        continue

                    # no len for special code flag, remove the modifier
                    playermodifiers.remove(sellableskill["special_code_flag"])

        await interaction.response.send_message(f"<@{interaction.user.id}> has sold {sold_things_str} "
                                                f"for a total of **{final_gold_gained}** Gold!")

        self.player_gold += final_gold_gained

        await db.set_inventory_value(self.pid, self.sid, self.iid, 'gold', self.player_gold)
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'skills', playerskills)
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'modifiers', playermodifiers)
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'treasures', playertreasures)
        await self.status_message.edit(content=f'<@{self.pid}>',
                                       embed=await self.status_panel_generator.get_message())
        
        interpreter=panel_interpreter(self.original_panel)
        await interpreter.get()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Select):
                button.disabled = True
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class EndSellButton(discord.ui.Button):
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
        self.original_panel=original_panel

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player selling.", ephemeral=True)
            return
        # disable view
        await self.disable_view(interaction)

        await interaction.response.send_message(
            f"<@{interaction.user.id}> has decided to not sell anything else!")
        interpreter=panel_interpreter(self.original_panel)
        await interpreter.get()

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
            if isinstance(button, discord.ui.Select):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class SellView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, pid, sid, iid,
                             status_message: Message, status_panel_generator: StatusPanel,
                             thread: Thread,
                             can_sell: bool, player_gold: int, sellable_skills: list, treasures: list, original_panel):
        if can_sell:
            sellselector = SellSelector(f'Selling', "sell", pid, sid, iid,
                                        status_message, status_panel_generator, thread, player_gold, sellable_skills,
                                        treasures, original_panel)
            self.add_item(sellselector)

        endsellbutton = EndSellButton(f'Do not sell anything', "sellall", pid, sid, iid,
                                      status_message, status_panel_generator, thread, original_panel)
        self.add_item(endsellbutton)
