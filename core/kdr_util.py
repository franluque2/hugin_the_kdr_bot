from discord.ext.commands.cog import Cog
from discord.ext.commands.bot import Bot
from discord import app_commands
from discord import Interaction
from core import kdr_db as db, \
    kdr_messages, \
    kdr_errors, \
    kdr_statics as statics
from config.config import ROLE_ADMIN, OOPS, DB_KEY_SERVER, DB_KEY_INSTANCE, ABOUT_MSG
from config.secret_values import GUILD


class KDRUtil(Cog):
    def __init__(self, client: Bot):
        self.client = client

    """ Player List Active KDRs """
    #@app_commands.command(name="active", description="Shows a list of the current active KDR Instances.")
    #@app_commands.guild_only()
    #async def list_active_kdr(self, interaction=Interaction):
        # fetch data
    #    sid = interaction.guild_id
    #    query_list = list(db.coll_kdr.find({DB_KEY_SERVER: sid}))
    #    current_active = []
        # loop through each query
    #    for query in query_list:
            # append the instance id of that query
    #        current_active.append(query.get(DB_KEY_INSTANCE))
    #    await interaction.response.send_message(f"Current Active Instances:\n{current_active}")

    """ Player Get Current Match Data """
    @app_commands.command(name="getcurrentmatch", description="Get the necessary Data about your current KDR Match")
    @app_commands.guild_only()
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.player_in_round)
    @app_commands.check(statics.player_has_class_selection)
    @app_commands.check(statics.player_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def get_current_match_data(self, interaction=Interaction, iid: str = ""):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id

        if iid == "":
            player_kdrs = await db.get_users_value(pid, sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]

        round_results = await db.get_instance_value(sid, iid, 'round_results')
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')

        won, match_pos, opponent = \
            await statics.check_player_won_round(pid, round_results, current_rounds, active_round)

        opponent_class = await db.get_inventory_value(opponent, sid, iid, 'class')
        if len(opponent_class) == 0:
            await interaction.response.send_message('Your opponent hasn''t picked a class', ephemeral=True)
            return

        player_inventory = await db.get_inventory(pid, sid, iid)
        opponent_inventory = await db.get_inventory(opponent, sid, iid)

        match_data = {
            "is_ranked": await db.get_instance_value(sid, iid, 'is_ranked'),
            "active_round": active_round,
            "max_round": len(current_rounds),
            "pl_id": pid,
            "pl_class_name": (await db.get_static_class(player_inventory["class"]))["name"],
            "pl_total_wl": await db.get_users_value(pid, sid, 'total_winloss'),
            "pl_elo": await db.get_users_value(pid, sid, 'elo'),
            "pl_str": player_inventory["STR"],
            "pl_dex": player_inventory["DEX"],
            "pl_con": player_inventory["CON"],
            "pl_xp": player_inventory["XP"],
            "pl_gold": player_inventory["gold"],
            "pl_wl_ratio": player_inventory["wl_ratio"],
            "pl_loss_streak": player_inventory["loss_streak"],
            "pl_sheet_url": player_inventory["sheet_url"],
            "opp_id": opponent,
            "opp_class_name": (await db.get_static_class(opponent_class))["name"],
            "opp_total_wl": await db.get_users_value(opponent, sid, 'total_winloss'),
            "opp_elo": await db.get_users_value(opponent, sid, 'elo'),
            "opp_str": opponent_inventory["STR"],
            "opp_dex": opponent_inventory["DEX"],
            "opp_con": opponent_inventory["CON"],
            "opp_xp": opponent_inventory["XP"],
            "opp_gold": opponent_inventory["gold"],
            "opp_wl_ratio": opponent_inventory["wl_ratio"],
            "opp_loss_streak": opponent_inventory["loss_streak"],
            "opp_sheet_url": opponent_inventory["sheet_url"],
        }
        await interaction.response.send_message(kdr_messages.current_match(match_data),
                                                ephemeral=True, suppress_embeds=True)

    """ Learn how to play"""

    @app_commands.command(name="tutorial", description="Get a Description of what KDR is and how to play.")
    @app_commands.guild_only()
    async def get_tutorial(self, interaction=Interaction):
        # fetch data
        await interaction.response.send_message(f"__**What is KDR?**__ \n https://docs.google.com/document/d/1YlC9zVx4JgYpvwzPji7QHLu0pZ8VjWhXuTTLnpk-Gak/edit?usp=sharing", ephemeral=True)
        await interaction.followup.send(f"__**Using me**__ (no, not like that!) __**and setting up your Character sheet!**__:\nhttps://docs.google.com/document/d/1KSAqvNsn8h7E_rAzQzw4BlOsI5cNdm7AM_jCc0nkkTQ/edit?usp=sharing", ephemeral=True)

    @app_commands.command(name="about", description="Get Technical Information about Hugin!")
    @app_commands.guild_only()
    async def get_about_msg(self, interaction=Interaction):
        # fetch data
        await interaction.response.send_message(ABOUT_MSG, ephemeral=True)

    """ Command Errors """
    @get_current_match_data.error
    async def command_error(self, interaction, error):
        if isinstance(error, kdr_errors.InstanceDoesNotExistError):
            await interaction.response.send_message(f"{OOPS} KDR Instance {error} does not exist.",ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerNotInInstanceError):
            await interaction.response.send_message(f"{OOPS} You are not part of KDR Instance {error}",ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerAlreadyJoinedError):
            await interaction.response.send_message(f"{OOPS} You already joined KDR Instance {error}",ephemeral=True)
            return
        if isinstance(error, kdr_errors.InstanceStartedError):
            await interaction.response.send_message(f"{OOPS} {error} has already started.",ephemeral=True)
            return
        if isinstance(error, kdr_errors.InstanceNotStartedError):
            await interaction.response.send_message(f"{OOPS} {error} hasn't even started yet!",ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerHasClassAlreadyError):
            await interaction.response.send_message(f"{OOPS} You have already picked a class!",ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerNotInRoundError):
            await interaction.response.send_message(f"{OOPS} You are not playing in this round.",ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerHasNoClassError):
            await interaction.response.send_message(f"{OOPS} You have not picked a class yet.",ephemeral=True)
            return

        raise error

    @get_current_match_data.autocomplete('iid')
    async def autocomplete_iid(self, interaction: Interaction, current: str):
        iid_list=await db.get_users_value(str(interaction.user.id),interaction.guild_id,"instances")
        final_iid_list=[app_commands.Choice(name=x,value=x) for x in iid_list]
        return final_iid_list

async def setup(bot: Bot) -> None:
    await bot.add_cog(KDRUtil(bot))

