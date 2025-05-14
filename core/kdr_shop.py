import random

from discord.ext.commands.cog import Cog
from discord.ext.commands.bot import Bot
from discord import app_commands
from discord import Interaction, InteractionResponse
from discord import ChannelType, AllowedMentions
from core.kdr_data import WinType, SpecialClassHandling, SpecialSkillHandling, KdrModifierNames
from core.kdr_modifiers import get_modifier

import core.kdr_statics as statics
import core.kdr_errors as kdr_errors
from core import kdr_db as db

from config.config import OOPS
from config.secret_values import GUILD

from views.panels.panel_status import StatusPanel
from views.panels.panel_pick_skill import PickSkillPanel
from views.panels.panel_training import TrainPanel
from views.panels.panel_level_attribute import LevelAttributePanel
from views.panels.panel_treasure import TreasurePanel
from views.panels.panel_buying import BuyPanel
from views.panels.panel_tips import TipPanel
from views.panels.panel_end_shop_phase import EndShopPanel
from views.panels.shopkeeper_intro_panel import ShopIntroPanel
from views.panels.panel_reverse_sacrifice import ReverseSacrificePanel

from config.config import LEVEL_THRESHOLDS, XP_PER_ROUND


class KDRShop(Cog):
    def __init__(self, client: Bot):
        self.client = client

    """ Shop Command """

    @app_commands.command(name="shop", description="Open the Shop phase for a KDR.")
    @app_commands.guild_only()
    @app_commands.check(statics.player_has_character_sheet)
    @app_commands.check(statics.player_in_round)
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.player_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def shop(self, interaction=Interaction, iid: str = ""):
        sid = interaction.guild_id
        pid = str(interaction.user.id)

        if iid == "":
            player_kdrs = await db.get_users_value(str(interaction.user.id), sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]

        res_user_modifiers = await db.get_inventory_value(pid, sid, iid, 'modifiers')
        if SpecialClassHandling.CLASS_MIMIC.value in res_user_modifiers:
            await interaction.response.send_message("Mimics do not get a Shop Phase.", ephemeral=True)
            return

        res_user_shop = await db.get_inventory_value(pid, sid, iid, 'shop_phase')
        if not res_user_shop:
            await interaction.response.send_message("You have already finished your shop phase.")
            return

        round_results = await db.get_instance_value(sid, iid, 'round_results')
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')
        shop_stage = await db.get_inventory_value(pid, sid, iid, 'shop_stage')
        player_inventory = await db.get_inventory(pid, sid, iid)
        special_flags = await db.get_inventory_value(pid, sid, iid, 'modifiers')

        xp = player_inventory["XP"]
        playergold = player_inventory["gold"]
        playerskills = list(player_inventory["skills"])
        playermodifiers = list(player_inventory["modifiers"])

        debug_complete_match = False

        # Check if the player has a bye
        won, match_pos, opponent = \
            await statics.check_player_won_round(pid, round_results, current_rounds, active_round)

        if current_rounds[active_round][match_pos][1] is None:
            # Player gets a bye
            round_results[active_round][match_pos] = (True, WinType.WIN_DEFAULT.value)
            await db.set_instance_value(sid, iid, 'round_results', round_results)
            await interaction.response.send_message(
                "You received a bye this round and automatically won. Proceeding to the shop phase.",
                ephemeral=True
            )
            won = True
            opponent = None

        matchresult = round_results[active_round][match_pos][1]

        if active_round == (len(current_rounds) - 1):
            await interaction.response.send_message("There are no shops in the final round of a KDR.", ephemeral=True)
            return

        if matchresult == WinType.INCOMPLETE.value and not debug_complete_match:
            await interaction.response.send_message("The result for your match has not been inputted.\n "
                                                    "Use the `reportresult` command.", ephemeral=True)
            return

        await interaction.response.send_message('Creating Shop Thread', ephemeral=True)

        # Increase gold
        if shop_stage == 0:
            await statics.update_gold(pid, iid, sid, won, special_flags)
            shop_stage += 1
            await db.set_inventory_value(pid, sid, iid, 'shop_stage', shop_stage)

        channel = await self.client.fetch_channel(interaction.channel_id)
        if not channel.type == ChannelType.public_thread:
            thread = await channel.create_thread(
                name=f'Shop Phase for {interaction.user.name} round {active_round + 1}',
                type=ChannelType.public_thread,
                auto_archive_duration=60)
        else:
            thread = channel

        status_panel_generator = StatusPanel(pid, iid, sid, interaction.user.name)
        msg = f'<@{pid}>'
        if won:
            if opponent:
                msg += f', your last match against <@{opponent}> ended with your victory '
            else:
                msg += f', you received a bye this round and automatically won '
        else:
            msg += f', your last match against <@{opponent}> ended with your loss '

        if matchresult == WinType.INCOMPLETE or matchresult == WinType.WIN_DEFAULT:
            msg += f'by default'
        if matchresult == WinType.WIN_2X0:
            msg += f'2-0'
        if matchresult == WinType.WIN_2X1:
            msg += f'2-1'

        mentions_ctrl = AllowedMentions(everyone=False, users=[interaction.user])
        await thread.send(content=msg, allowed_mentions=mentions_ctrl)
        status_message = await thread.send(content="", embed=await status_panel_generator.get_message())

        await status_message.pin()

        # Mimic does not get a normal shop phase
        if SpecialClassHandling.CLASS_MIMIC.value in special_flags:
            # TODO, handle mimic
            await thread.send("Mimic gets handled here")
            return

        modifiers = await db.get_instance_value(sid, iid, 'modifiers')

        if modifiers and (get_modifier(modifiers, KdrModifierNames.REVERSE_RUN.value) is not None):  # Swap normal shop for Reverse Run "Shop"
            reverter = ReverseSacrificePanel(pid, sid, iid, status_message, status_panel_generator, thread)
            await reverter.get_sacrifice_panel()
            shop_stage = 9
            return

        # Increase xp
        if shop_stage == 1:
            if xp <= LEVEL_THRESHOLDS[-1]:
                xp += XP_PER_ROUND
                await db.set_inventory_value(pid, sid, iid, 'XP', xp)
                shop_stage += 1
                await db.set_inventory_value(pid, sid, iid, 'shop_stage', shop_stage)
                await status_message.edit(content=f'<@{pid}>', embed=await status_panel_generator.get_message())
            # Cleaning up just in case last shop phase was incomplete
            else:
                shop_stage += 1
                await db.set_inventory_value(pid, sid, iid, 'shop_stage', shop_stage)
            await db.set_inventory_value(pid, sid, iid, "offered_loot", [])

        if shop_stage == 2:
            picker = PickSkillPanel(pid, sid, iid, status_message, status_panel_generator, thread)
            await picker.get_pick_skill_panel()

        if shop_stage == 3:
            trainer = TrainPanel(pid, sid, iid, status_message, status_panel_generator, thread)
            await trainer.get_train_panel()

        if shop_stage == 4:
            level_panel = LevelAttributePanel(pid, sid, iid, status_message,
                                              status_panel_generator, thread)
            await level_panel.get_level_attribute_panel()

        if shop_stage == 5:
            treasure_panel = TreasurePanel(pid, iid, sid, status_message,
                                           status_panel_generator, thread)
            await treasure_panel.get_treasure_panel()

        if shop_stage == 6:
            shopintro = ShopIntroPanel(pid, sid, iid, thread)
            await shopintro.get_shop_intro()

            buyer = BuyPanel(pid, sid, iid, status_message,
                             status_panel_generator, thread)
            await buyer.get_buy_panel()

        if shop_stage == 7:
            tipper = TipPanel(pid, sid, iid, status_message,
                              status_panel_generator, thread)
            await tipper.get_tip_panel()

        # Button to enter sell mode no longer required

        if shop_stage == 8:
            ender = EndShopPanel(pid, sid, iid, status_message, status_panel_generator, thread)
            await ender.get_end_shop_panel()

        await interaction.edit_original_response(content="Created the Shop Thread")

    """ View Inventory """

    @app_commands.command(name="inventory", description="Opens your Inventory for a KDR.")
    @app_commands.guild_only()
    @app_commands.check(statics.player_has_character_sheet)
    @app_commands.check(statics.player_in_round)
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.player_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def inventory(self, interaction=Interaction, iid: str = ""):
        sid = interaction.guild_id
        pid = str(interaction.user.id)
        response = interaction.response

        if iid == "":
            player_kdrs=await db.get_users_value(str(interaction.user.id),sid,"instances")
            if len(player_kdrs)==1:
                iid=player_kdrs[0]

        status_panel_generator = StatusPanel(pid, iid, sid, interaction.user.name)

        await response.send_message(content=f"Your Inventory Data for `{iid}`",
                                           embed=await status_panel_generator.get_message(), ephemeral=True)


    """ Command Errors """

    @shop.error
    @inventory.error
    async def command_error(self, interaction, error):
        if isinstance(error, kdr_errors.InstanceDoesNotExistError):
            await interaction.response.send_message(f"{OOPS} KDR Instance {error} does not exist.")
            return
        if isinstance(error, kdr_errors.PlayerNotInInstanceError):
            await interaction.response.send_message(f"{OOPS} You are not in KDR {error}")
            return
        if isinstance(error, kdr_errors.InstanceNotStartedError):
            await interaction.response.send_message(f"{OOPS} {error} hasn't even started yet!")
            return
        if isinstance(error, kdr_errors.PlayerNotInRoundError):
            await interaction.response.send_message(f"{OOPS} You are not playing in this round.")
            return
        if isinstance(error, kdr_errors.PlayerHasNoCharacterSheetError):
            await interaction.response.send_message(
                f"{OOPS} You Have Not Setup your Character Sheet\'s Link, do so with `setclassheet`.")
            return

        raise error


    @shop.autocomplete('iid')
    @inventory.autocomplete('iid')
    async def autocomplete_iid(self, interaction: Interaction, current: str):
        iid_list=await db.get_users_value(str(interaction.user.id),interaction.guild_id,"instances")
        final_iid_list=[app_commands.Choice(name=x,value=x) for x in iid_list]
        return final_iid_list
    
async def setup(bot: Bot) -> None:
    await bot.add_cog(KDRShop(bot))
