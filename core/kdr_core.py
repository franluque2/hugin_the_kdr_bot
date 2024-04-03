import discord

import core.kdr_statics as statics
import core.kdr_errors as kdr_errors
from core.kdr_data import WinType
from discord import app_commands
from discord import Interaction
from discord import ChannelType
from discord import Game, Activity, ActivityType, Member
from discord.app_commands import AppCommandError
from discord.ext.commands.cog import Cog
from discord.ext.commands.bot import Bot
from core import kdr_db as db, kdr_messages
from views.view_class_select import ClassSelectView
from views.panels.panel_status import StatusPanel
from config.config import ROLE_ADMIN, OOPS, DB_KEY_SERVER, DB_KEY_INSTANCE, DEFAULT_ELO_RANKING
from config.secret_values import GUILD
from core.kdr_elo import EloAdjustment
from core.kdr_fun import get_random_status


class KDRCore(Cog):
    def __init__(self, client: Bot):
        self.client = client

    """ Create New KDR """

    @app_commands.command(name="newkdr", description="Creates a new KDR with a random Instance ID.")
    @app_commands.describe(playernum="The Number of players in the KDR, Defaults to 8",
                        isprivate="Should the KDR ID be shown in a private Message? Defaults to False",
                           isranked="Is the KDR Ranked? Defaults to False. KDR ADMIN ONLY")
    @app_commands.guild_only()
    async def new_kdr(self, interaction: Interaction, playernum:int=8, isprivate: bool = False, isranked: bool = False):
        sid = interaction.guild_id
        pid=interaction.user.id
        proles=interaction.user.roles
        await interaction.response.defer(ephemeral=True)
        if playernum%2!=0:
            await interaction.followup.send(f"{OOPS}\n Max Number of Players must be even.",ephemeral=True)
            return
        if isranked and ROLE_ADMIN not in str(proles):
            await interaction.followup.send(f"{OOPS}\n Only Admins may create a ranked KDR.",ephemeral=True)
            return
        hasplayerstartedkdr=await db.has_player_started_a_kdr(pid,sid)
        if hasplayerstartedkdr and ROLE_ADMIN not in str(proles):
            await interaction.followup.send(f"{OOPS}\n Non Admins may not create more than 1 KDR at a time!",ephemeral=True)
            return
        name_id = statics.generate_instance_name(sid)
        await db.add_new_kdr(sid, name_id, isranked,pid,playernum)
        msg = ""
        msg = "Started a new KDR "
        if isranked:
            msg = f"Started a **ranked** KDR "
        
        msg+=f"for up to {playernum} players "

        if not isprivate:
            msg += f"with passcode `{name_id}`"
        await interaction.followup.send(msg)
        if isprivate:
            await interaction.followup.send(
                f"This KDR's Passcode is `{name_id}` , make sure to write it down as this message will be deleted soon!",
                ephemeral=True)

    """ Start KDR """

    @app_commands.command(name="startkdr", description="Starts a new KDR given the Instance ID.")
    @app_commands.describe(iid="The Instance ID of the KDR.", rematch_count="The Number of times each player fights each other in the round robin. Defaults to 1.")
    @app_commands.guild_only()
    @app_commands.check(statics.instance_not_started)
    @app_commands.check(statics.instance_exists)
    async def start_kdr(self, interaction: Interaction, iid: str = "", rematch_count:int = 1):
        # fetch data
        sid = interaction.guild_id
        pid = str(interaction.user.id)

        if iid == "":
            player_kdrs = await db.get_users_value(pid, sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]
        
        if(rematch_count<1):
            rematch_count=1

        res_started = await db.get_instance_value(sid, iid, 'started')

        if res_started:
            await interaction.response.send_message(f"This KDR has already started.",ephemeral=True)
            return
        
        owner=await db.get_instance_value(sid,iid,"creator_id")
        if str(owner)!=str(pid) and ROLE_ADMIN not in str(interaction.user.roles):
            await interaction.response.send_message(f"You cannot start a KDR you are not the owner of.",ephemeral=True)
            return

        instance_name = await db.get_instance_value(sid, iid, DB_KEY_INSTANCE)
        num_players = await db.get_instance_value(sid, iid, 'players')

        # check for player condition
        if num_players % 2 != 0 or num_players <= 0:
            await interaction.response.send_message(f"There must be an even number of participants to start.",ephemeral=True)
            return

        # fetch players and generate round brackets
        player_names = await db.get_instance_list(sid, iid, 'player_names')
        rounds = statics.create_balanced_round_robin(player_names, rematch_count)
        db.add_match_rounds_to_kdr(sid, iid, rounds)

        # set instance id to started now
        await db.set_instance_value(sid, iid, 'started', True)
        await db.set_instance_value(sid, iid, 'active_round', 0)
        await db.set_all_inventory_value(sid, iid, 'shop_phase', True)

        # ping players and send response
        player_pings = ""
        for p in player_names:
            player_pings+=f"<@{p}> " 

        msg1 = f"Match '{instance_name}' Started!\n"
        msg2 = f'{player_pings}\n It''s time to pick your class! You can now use the `pickclass` command.'
        msg3 = f"Use the `bracket` command to view the current standings for this KDR at any time. \n"
        #msg4 = f"{rounds}"
        await interaction.response.send_message(f"{msg1}\n{msg2}\n{msg3}")

    """ Player Join KDR """

    @app_commands.command(name="join", description="Joins an existing KDR given the Instance ID.")
    @app_commands.describe(iid="The Instance ID of the KDR.")
    @app_commands.guild_only()
    @app_commands.check(statics.instance_not_started)
    @app_commands.check(statics.player_not_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def join_kdr(self, interaction: Interaction, iid: str = ""):
        # return if no iid
        if len(iid) == 0:
            return

        # locals
        choices = []
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        response = interaction.response

        # get instance
        instance = await db.get_instance(sid, iid)

        # return if instance full
        if instance.get("players") > instance.get("max_players"):
            await response.send_message(f"This KDR is already full.",ephemeral=True)
            return

        # generate classes
        choices = await statics.get_class_selection(sid, iid)
        if len(choices) == 0:
            await response.send_message(f'All classes have been offered.',ephemeral=True)
            return

        # mark if its users first game on server to send also a reminder to do /tutorial
        is_firstgame = False
        # check if user exists, and add
        if not db.check_user_exist(pid, sid):
            db.add_user_to_kdr(pid, sid, iid, choices)
            is_firstgame = True
        else:
            db.update_user_to_kdr(pid, sid, iid, choices)

        # check if last player
        if instance.get("players") == instance.get("max_players"):
            max_msg = f"<@{pid}> joined with {choices}.\nYou are the final player.\nThis match is ready to start."
            await response.send_message(max_msg)
            return

        await response.send_message(f"<@{pid}> joined the KDR {iid}!")
        if is_firstgame:
            await interaction.followup.send(kdr_messages.first_game_join(),
                                            ephemeral=True)
    
    """ Player Get Self Data """

    @app_commands.command(name="data", description="Get your KDR Player Data.")
    @app_commands.guild_only()
    async def get_data(self, interaction: Interaction):
        # locals
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        response = interaction.response


        # check if user exists, if not throw an error
        if not db.check_user_exist(pid, sid):
            await response.send_message(f"You do not have any KDR Data on this server! Try joining a KDR first with `join`",ephemeral=True)


        player_instances=await db.get_users_value(pid,sid,"instances")
        total_wl=await db.get_users_value(pid,sid,"total_winloss")
        elo=int(await db.get_users_value(pid,sid,"elo"))
        msg=f"<@{pid}>\n\n Your current total Wins and Losses are {total_wl[0]}**W** / {total_wl[1]}**L**\n\n"
        if len(player_instances)>0:
            msg+="You are currently a part of the following KDRs: \n"
            for instance in player_instances:
                msg+=f"`{instance}` "
        if elo!=DEFAULT_ELO_RANKING:
            msg+=f"\nYour current KDR Elo Ranking in this server is **{elo}**"

        await response.send_message(msg,ephemeral=True)

    """ Player Get Top Ranking """

    @app_commands.command(name="topranking", description="Get the top Ranking Elos in the Server.")
    @app_commands.guild_only()
    async def get_top_ranking(self, interaction: Interaction, length: int=10):
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        response = interaction.response

        await response.defer(ephemeral=True)

        col_users=await db.get_all_users(sid)
        
        if length>50: length=50

        col_users=list(col_users.sort("elo",-1).limit(length))
        if len(col_users)==0:
            await interaction.followup.send(f"{OOPS}\n No Users have Played in KDRs yet in this server.",ephemeral=True)


        msg=f"The KDR Elo Ranking top {length} for this server is as follows: \n"
        rank=1
        for player in col_users:
            playerid=player["id_player"]
            playerelo=int(player["elo"])
            if playerelo!=DEFAULT_ELO_RANKING:
                msg+=f"{rank} - <@{playerid}> (Elo: {playerelo})\n"
                rank+=1

        await interaction.followup.send(msg,ephemeral=True)




    """ Get Other Data """

    @app_commands.command(name="getplayerdata", description="Get KDR Player Data.")
    @app_commands.describe(player="The player to get the player data for")
    @app_commands.guild_only()
    async def get_player_data(self, interaction: Interaction, player: Member):
        # locals
        sid = interaction.guild_id
        response = interaction.response
        pid=str(player.id)


        # check if user exists, if not throw an error
        if not db.check_user_exist(pid, sid):
            await response.send_message(f"This player has no KDR Data in this server",ephemeral=True)


        player_instances=await db.get_users_value(pid,sid,"instances")
        total_wl=await db.get_users_value(pid,sid,"total_winloss")
        elo=int(await db.get_users_value(pid,sid,"elo"))
        msg=f"The current total Wins and Losses for <@{pid}> are {total_wl[0]}**W** / {total_wl[1]}**L**\n\n"
        if len(player_instances)>0:
            msg+="They are currently a part of the following KDRs: \n"
            for instance in player_instances:
                msg+=f"`{instance}` "
        if elo!=DEFAULT_ELO_RANKING:
            msg+=f"\nTheir current KDR Elo Ranking in this server is **{elo}**"

        await response.send_message(msg,ephemeral=True)


        """ Get Other Inventory """

    @app_commands.command(name="getplayerinventory", description="Get KDR Player Inventory.")
    @app_commands.describe(player="The player to get the inventory data for")
    @app_commands.describe(iid="The Instance ID of the KDR.")
    @app_commands.guild_only()
    async def get_player_inventory(self, interaction: Interaction, player: Member, iid: str):
        # locals
        sid = interaction.guild_id
        response = interaction.response
        pid=str(player.id)


        # check if user exists, if not throw an error
        if not db.check_user_exist_in_instance(pid, sid, iid):
            await response.send_message(f"This player has no KDR Data in that KDR",ephemeral=True)

        status_panel_generator = StatusPanel(pid, iid, sid, player.name)

        await response.send_message(content=f"Inventory Data for <@{pid}> in KDR `{iid}`",
                                           embed=await status_panel_generator.get_message(), ephemeral=True)



    """ Player Select Class """

    @app_commands.command(name="pickclass", description="Select a class for a KDR.")
    @app_commands.guild_only()
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.player_has_no_class_selection)
    @app_commands.check(statics.player_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def pick_class(self, interaction: Interaction, iid: str = ""):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        if iid=="":
            player_kdrs=await db.get_users_value(str(interaction.user.id),sid,"instances")
            if len(player_kdrs)==1:
                iid=player_kdrs[0]
        v = ClassSelectView()
        player_classes = await db.get_inventory_value(pid, sid, iid, 'classes')
        echos, msg, embeds = await statics.get_final_class_selection(player_classes)
        await v.create_buttons(sid, iid, echos, pid)
        await interaction.response.send_message(f"Creating Class Select Thread", ephemeral=True)

        channel = await self.client.fetch_channel(interaction.channel_id)
        thread = await channel.create_thread(name=f'Class Selection for {interaction.user.name}',
                                             type=ChannelType.public_thread, auto_archive_duration=60)
        await thread.send(f'<@{pid}>\n\n{msg}', view=v, embeds=embeds)


    @app_commands.command(name="bracket", description="Get the current bracket for the KDR.")
    @app_commands.guild_only()
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.instance_exists)
    async def get_bracket(self, interaction: Interaction, iid: str = ""):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id

        if iid=="":
            player_kdrs=await db.get_users_value(str(interaction.user.id),sid,"instances")
            if len(player_kdrs)==1:
                iid=player_kdrs[0]

        round_results = await db.get_instance_value(sid, iid, 'round_results')
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')
        kdr_players= await db.get_instance_value(sid, iid, 'player_names')

        if str(pid) not in kdr_players and ROLE_ADMIN not in str(interaction.user.roles):
            await interaction.response.send_message(f"You cannot see the bracket of a KDR you are not in.",ephemeral=True)
            return

        msg=f"It is round **{active_round+1}** of **{len(current_rounds)}** for KDR `{iid}`\n\n"
        missing_to_play=[]
        missing_shop_phase=[]

        for i in range(len(current_rounds[active_round])):
            msg+=f"<@{current_rounds[active_round][i][0]}> vs <@{current_rounds[active_round][i][1]}> "
            if round_results[active_round][i][1]!=WinType.INCOMPLETE.value:
                msg+=f"- <@{current_rounds[active_round][i][not round_results[active_round][i][0]]}> wins "
                if round_results[active_round][i][1]==WinType.WIN_2X0.value:
                    msg+=f"2-0"
                if round_results[active_round][i][1]==WinType.WIN_2X1.value:
                    msg+=f"2-1"
                if round_results[active_round][i][1]==WinType.WIN_DEFAULT.value:
                    msg+=f"by Default"
            else:
                missing_to_play.append(current_rounds[active_round][i][0])
                missing_to_play.append(current_rounds[active_round][i][1])
            msg+=f"\n"
        for player in kdr_players:
            did_not_do_shop_phase=await db.get_inventory_value(player,sid,iid,"shop_phase")
            if did_not_do_shop_phase:
                missing_shop_phase.append(player)

        if len(missing_to_play)>0:
            add_to_msg="The Following Players have not played: "
            for p in missing_to_play:
                add_to_msg+=f"<@{p}> "
            msg+=add_to_msg
            msg+=f"\n"

        if len(missing_shop_phase)>0:
            add_to_msg="The Following Players have not conducted their shop phase: "
            for p in missing_shop_phase:
                add_to_msg+=f"<@{p}> "
            msg+=add_to_msg
            msg+=f"\n"
        
        if len(missing_shop_phase)==0 and  len(missing_to_play)==0:
            msg+="\nAll players have finished their matches and shops this round, inform the creator or an admin to use the /nextround command!"
        await interaction.response.send_message(msg, ephemeral=True)

    """ Player Set Own Class Sheet"""

    @app_commands.command(name="setclasssheet", description="Set your class sheet's URL.")
    @app_commands.describe(iid="The Instance ID of the KDR.", sheeturl="The Share URL to your class sheet")
    @app_commands.guild_only()
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.player_has_class_selection)
    @app_commands.check(statics.player_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def set_class_sheet(self, interaction: Interaction, iid: str = "", sheeturl: str = ""):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        if iid=="" or iid==" ":
            player_kdrs=await db.get_users_value(str(interaction.user.id),sid,"instances")
            if len(player_kdrs)==1:
                iid=player_kdrs[0]
        if not(sheeturl.startswith("https://docs.google.com/spreadsheets/d/")):
            await interaction.response.send_message(f"{OOPS}\n{sheeturl} does not appear to be a valid link to a KDR Sheet!",ephemeral=True)
            return
        await db.set_inventory_value(pid, sid, iid, "sheet_url", sheeturl)

        await interaction.response.send_message(f"Updated your class sheet's link to {sheeturl}")

    """ Player Report Match Result """

    @app_commands.command(name="reportresult", description="Report the result of your last KDR Match.")
    @app_commands.guild_only()
    @app_commands.check(statics.player_has_character_sheet)
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.player_in_round)
    @app_commands.check(statics.player_has_class_selection)
    @app_commands.check(statics.player_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def report_result(self, interaction: Interaction, iid: str = "", self_wins: int = 0, opp_wins: int = 0):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        if iid=="":
            player_kdrs=await db.get_users_value(str(interaction.user.id),sid,"instances")
            if len(player_kdrs)==1:
                iid=player_kdrs[0]

        round_results = await db.get_instance_value(sid, iid, 'round_results')
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')
        is_kdr_ranked = await db.get_instance_value(sid, iid, 'is_ranked')
        won, match_pos, opponent = \
            await statics.check_player_won_round(pid, round_results, current_rounds, active_round)

        if round_results[active_round][match_pos][1] != WinType.INCOMPLETE.value:
            await interaction.response.send_message('The result for your match has already been reported.\n'
                                                    'If you feel that the result is incorrect, '
                                                    'contact an Admin.', ephemeral=True)
            return

        classes = await db.get_inventory_value(opponent, sid, iid, 'class')
        if len(classes) == 0:
            await interaction.response.send_message('Your opponent hasn''t picked a class', ephemeral=True)
            return

        if self_wins == opp_wins:
            await interaction.response.send_message('Ties cannot exist in KDR.', ephemeral=True)
            return

        if not (2 <= (self_wins + opp_wins) <= 3):
            await interaction.response.send_message('KDR Matches are Best of 3.\n'
                                                    'The reported result does not '
                                                    'match the possible amount of matches.', ephemeral=True)
            return

        isfirstplayer=await statics.check__if_firstplayer_in_round(pid,current_rounds,active_round)
        win_player_one = self_wins > opp_wins if isfirstplayer else not self_wins > opp_wins
        win_type = self_wins + opp_wins - 1

        adjuster = EloAdjustment()

        player_won = self_wins > opp_wins

        await adjuster.update_winloss(pid, sid, iid, player_won)
        await adjuster.update_losstreak(pid, sid, iid, player_won)
        await adjuster.update_winloss(opponent, sid, iid, not player_won)
        await adjuster.update_losstreak(opponent, sid, iid, not player_won)

        if is_kdr_ranked:
            await adjuster.update_elo(pid, opponent, sid, player_won)

        round_results[active_round][match_pos] = (win_player_one, win_type)

        await db.set_instance_value(sid, iid, 'round_results', round_results)
        await interaction.response.send_message(f'<@{pid}> has reported their match results as {self_wins} '
                                                f'/ {opp_wins} VS <@{opponent}>')

    """ Player Leave Match """

    @app_commands.command(name="leavekdr", description="Leave an active KDR and forfeit your matches.")
    @app_commands.guild_only()
    @app_commands.check(statics.player_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def leave_kdr(self, interaction: Interaction, iid: str = ""):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        if iid=="":
            player_kdrs=await db.get_users_value(str(interaction.user.id),sid,"instances")
            if len(player_kdrs)==1:
                iid=player_kdrs[0]

        round_results = await db.get_instance_value(sid, iid, 'round_results')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')

        # loop through rounds and matches
        for x in range(len(current_rounds)):
            for y in range(len(current_rounds[x])):
                match = current_rounds[x][y]
                first_player, second_player = "", ""
                p1_wl, p2_wl = [], []
                fp = str(match[0])
                sp = str(match[1])
                # if player not in match or match was already reported, continue
                if (fp != pid and sp != pid) or round_results[x][y][1] != WinType.INCOMPLETE.value:
                    continue
                # if player is first player in match
                if fp == pid:
                    # set the round results to first player losing
                    round_results[x][y] = (False, WinType.WIN_DEFAULT.value)
                    # first player is player
                    first_player = pid
                    # second player is opponent
                    second_player = sp
                    p1_wl = await db.get_inventory_value(first_player, sid, iid, "wl_ratio")
                    p2_wl = await db.get_inventory_value(second_player, sid, iid, "wl_ratio")
                    # give player(first player) loss
                    p1_wl[True] += 1
                    # give opponent(second player) win
                    p2_wl[False] += 1
                if sp == pid:
                    round_results[x][y] = (True, WinType.WIN_DEFAULT.value)
                    first_player = fp
                    second_player = pid
                    p1_wl = await db.get_inventory_value(first_player, sid, iid, "wl_ratio")
                    p2_wl = await db.get_inventory_value(second_player, sid, iid, "wl_ratio")
                    # give player(second player) loss
                    p2_wl[True] += 1
                    # give opponent(first player) win
                    p1_wl[False] += 1

                await db.set_inventory_value(first_player, sid, iid, "wl_ratio", p1_wl)
                await db.set_inventory_value(second_player, sid, iid, "wl_ratio", p2_wl)
                await db.set_instance_value(sid, iid, 'round_results', round_results)

        instance_started = await db.get_instance_value(sid, iid, 'started')
        players = await db.get_instance_value(sid, iid, 'player_names')
        player_active_instances = await db.get_users_value(pid, sid, 'instances')
        player_classes = await db.get_inventory_value(pid, sid, iid, 'classes')
        offered_classes = await db.get_instance_value(sid, iid, 'offered_classes')
        for c in player_classes:
            offered_classes.remove(c)

        num_players = await db.get_instance_value(sid, iid, 'players')
        num_players -= 1
        players.remove(pid)
        player_active_instances.remove(iid)
        msg = f"<@{pid}> has left KDR Match {iid}.\n"

        await db.set_instance_value(sid, iid, 'players', num_players)
        await db.set_instance_value(sid, iid, 'player_names', players)
        await db.set_instance_value(sid, iid, 'offered_classes', offered_classes)
        await db.set_users_value(pid, sid, 'instances', player_active_instances)
        if not instance_started:
            await db.delete_player_inventory(pid, sid, iid)
        else:
            msg += "They have forfeited any matches not yet started."
        await interaction.response.send_message(f'{msg}')

    """ Command Errors """

    @start_kdr.error
    @join_kdr.error
    @pick_class.error
    @report_result.error
    @set_class_sheet.error
    @leave_kdr.error
    @get_bracket.error
    @get_player_data.error
    @get_player_inventory.error
    @get_top_ranking.error
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
        if isinstance(error, kdr_errors.PlayerHasNoCharacterSheetError):
            await interaction.response.send_message(
                f"{OOPS} You Have Not Setup your Character Sheet\'s Link, do so with `setclassheet`.",ephemeral=True)
            return

        raise error

    @start_kdr.autocomplete('iid')
    @pick_class.autocomplete('iid')
    @report_result.autocomplete('iid')
    @get_bracket.autocomplete('iid')
    @leave_kdr.autocomplete('iid')
    async def autocomplete_iid(self, interaction: discord.Interaction, current: str):
        iid_list=await db.get_users_value(str(interaction.user.id),interaction.guild_id,"instances")
        final_iid_list=[app_commands.Choice(name=x,value=x) for x in iid_list]
        return final_iid_list

async def setup(bot: Bot) -> None:
    await bot.add_cog(KDRCore(bot))
    await get_random_status(bot)