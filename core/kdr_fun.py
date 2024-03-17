from discord import Activity, Game, ActivityType
from discord.ext.commands.cog import Cog
from discord.ext.commands.bot import Bot
from discord import app_commands
from discord import Interaction
import core.kdr_errors as kdr_errors
import core.kdr_statics as statics
import core.kdr_special as specials

from config.config import ROLE_ADMIN, OOPS
from config.secret_values import GUILD

import random


class KDRFun(Cog):
    def __init__(self, client: Bot):
        self.client = client

    @app_commands.command(name="get_new_status", description="Changes the Status of Hugin!")
    @app_commands.guild_only()
    @app_commands.check(statics.server_whitelisted)
    @app_commands.checks.has_role(ROLE_ADMIN)
    async def get_new_status(self, interaction=Interaction):
        await get_random_status(self.client)
        await interaction.response.send_message(f"Hugin has changed her status!", ephemeral=True)

    @get_new_status.error
    async def command_error(self, interaction, error):
        if isinstance(error, kdr_errors.ServerNotWhitelistedError):
            await interaction.response.send_message(f"{OOPS} This Server is not allowed to perform this Command!", ephemeral=True)
            return
        raise error
    
    @app_commands.command(name="randomcard", description="Get a Random Monster!")
    @app_commands.guild_only()
    async def get_random_monster(self, interaction: Interaction, lvl: int):
        if lvl>12 or lvl<1:
            await interaction.response.send_message(f"{OOPS} LVL Must be between 1 and 12!", ephemeral=True)
            
        monster_panel_generator = specials.MonsterPanel(lvl)

        await interaction.response.send_message(content=f"Your Random Monster is",
                                           embed=await monster_panel_generator.get_monster())



async def setup(bot: Bot) -> None:
    await bot.add_cog(KDRFun(bot))


async def get_random_status(bot):
    randstatus = random.randint(1, 7)
    if randstatus == 1:
        await bot.change_presence(activity=Game(name="Runick Stun in Master Duel"))
    if randstatus == 2:
        await bot.change_presence(activity=Game(name="Live Twin Runick Spright at Nats"))
    if randstatus == 3:
        await bot.change_presence(activity=Game(name="Fur Hire Runick Spright at the WCQ"))
    if randstatus == 4:
        await bot.change_presence(activity=Activity(type=ActivityType.watching, name='Joshua Schmidt\'s latest builds'))
    if randstatus == 5:
        await bot.change_presence(
            activity=Activity(type=ActivityType.watching, name='my Opponent banish Kashtiratheosis'))
    if randstatus == 6:
        await bot.change_presence(activity=Activity(type=ActivityType.watching, name='videos on Capshell and Ipiria'))
    if randstatus == 7:
        await bot.change_presence(
            activity=Activity(type=ActivityType.watching, name='my one Fountain getting Cosmic\'d in the OCG'))


