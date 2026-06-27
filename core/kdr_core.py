import discord


import core.kdr_statics as statics
import core.kdr_errors as kdr_errors
from core.kdr_data import WinType, SpecialClassHandling
from discord import app_commands
from discord import Interaction
from discord import ChannelType
from discord import Game, Activity, ActivityType, Member
from discord.app_commands import AppCommandError
from discord.ext.commands.cog import Cog
from discord.ext.commands.bot import Bot
from core import kdr_db as db, kdr_messages
import core.kdr_ansi as ansi
from discord import Embed
from views.view_class_select import ClassSelectView
from views.panels.panel_status import StatusPanel
from config.config import ROLE_ADMIN, OOPS, DB_KEY_SERVER, DB_KEY_INSTANCE, DEFAULT_ELO_RANKING
from config.secret_values import GUILD
from core.kdr_elo import EloAdjustment
from core.kdr_fun import get_random_status


class KDRCore(Cog):
    def __init__(self, client: Bot):import discord


import core.kdr_statics as statics
import core.kdr_errors as kdr_errors
from core.kdr_data import WinType, SpecialClassHandling
from discord import app_commands
from discord import Interaction
from discord import ChannelType
from discord import Game, Activity, ActivityType, Member
from discord.app_commands import AppCommandError
from discord.ext.commands.cog import Cog
from discord.ext.commands.bot import Bot
from core import kdr_db as db, kdr_messages
import core.kdr_ansi as ansi
from discord import Embed
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
                            modifiers="List of Modifiers to use this KDR, defailts to empty",
                            class_selection_number="Number of classes to offer, defaults to 1, be careful increasing",
                           isranked="Is the KDR Ranked? Defaults to False. KDR ADMIN ONLY")
    @app_commands.guild_only()
    async def new_kdr(self, interaction: Interaction, playernum:int=8, isprivate: bool = False, modifiers: str="", class_selection_number: int=1, isranked: bool = False):
        sid = interaction.guild_id
        pid=str(interaction.user.id)
        proles=interaction.user.roles
        await interaction.response.defer(ephemeral=True)
        if playernum%2!=0:
            await interaction.followup.send(f"{OOPS} Max Number of Players must be even.", ephemeral=True)
            return
        if isranked and ROLE_ADMIN not in str(proles):
            await interaction.followup.send(f"{OOPS} Only Admins may create a ranked KDR.", ephemeral=True)
            return
        hasplayerstartedkdr=await db.has_player_started_a_kdr(pid,sid)
        if hasplayerstartedkdr and ROLE_ADMIN not in str(proles):
            await interaction.followup.send(f"{OOPS} Non Admins may not create more than 1 KDR at a time!", ephemeral=True)
            return
        name_id = statics.generate_instance_name(sid)
        await db.add_new_kdr(sid, name_id, isranked,pid,playernum, class_selection_number, modifiers)
        msg = "Started a new KDR "
        if isranked:
            msg = f"Started a **ranked** KDR "
        
        msg+=f"for up to {playernum} players "

        if not isprivate:
            msg += f"with passcode `{name_id}`"
        
        await interaction.followup.send(msg)
        if isprivate:
            await interaction.followup.send(f"This KDR's Passcode is `{name_id}`", ephemeral=True)

    """ Start KDR """

    @app_commands.command(name="startkdr", description="Starts a new KDR given the Instance ID.")
    @app_commands.describe(
        iid="The Instance ID of the KDR.",
        rematch_count="The Number of times each player fights each other in the round robin OR the number of rounds in Swiss. Defaults to 1.",
        round_type="The type of rounds to use (Round Robin or Swiss). Defaults to Round Robin."
    )
    @app_commands.choices(
        round_type=[
            app_commands.Choice(name="Round Robin", value="Round Robin"),
            app_commands.Choice(name="Swiss", value="Swiss")
        ]
    )
    @app_commands.guild_only()
    @app_commands.check(statics.instance_not_started)
    @app_commands.check(statics.instance_exists)
    async def start_kdr(
        self,
        interaction: Interaction,
        iid: str = "",
        rematch_count: int = 1,
        round_type: app_commands.Choice[str] = None
    ):
        # Fetch data
        sid = interaction.guild_id
        pid = str(interaction.user.id)

        if iid == "":
            player_kdrs = await db.get_users_value(pid, sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]

        if rematch_count < 1:
            rematch_count = 1

        res_started = await db.get_instance_value(sid, iid, 'started')

        if res_started:
            await interaction.response.send_message("This KDR has already started.", ephemeral=True)
            return

        owner = await db.get_instance_value(sid, iid, "creator_id")
        if str(owner) != str(pid) and ROLE_ADMIN not in str(interaction.user.roles):
            await interaction.response.send_message("You cannot start a KDR you are not the owner of.", ephemeral=True)
            return

        instance_name = await db.get_instance_value(sid, iid, DB_KEY_INSTANCE)
        num_players = await db.get_instance_value(sid, iid, 'players')

        # Check for player condition
        if num_players % 2 != 0 or num_players <= 0:
            await interaction.response.send_message("There must be an even number of participants to start.", ephemeral=True)
            return

        # Default to "Round Robin" if no round_type is provided
        selected_round_type = round_type.value if round_type else "Round Robin"

        # Fetch players and generate round brackets
        player_names = await db.get_instance_list(sid, iid, 'player_names')
        rounds = ""

        if selected_round_type == "Round Robin":
            rounds = statics.create_balanced_round_robin(player_names, rematch_count)
        elif selected_round_type == "Swiss":
            rounds = statics.create_swiss_rounds(player_names, rematch_count)

        # Add the initialized rounds to the KDR
        await db.add_match_rounds_to_kdr(sid, iid, rounds)

        # Set instance to started
        await db.set_instance_value(sid, iid, 'started', True)
        await db.set_instance_value(sid, iid, 'active_round', 0)
        await db.set_instance_value(sid, iid, 'round_type', selected_round_type)
        await db.set_all_inventory_value(sid, iid, 'shop_phase', True)

        # Assign classes to all players — done once here so no duplicates
        # Skip players who already have classes (e.g. set via setofferedclass)
        for p in player_names:
            existing = await db.get_inventory_value(p, sid, iid, "classes")
            if existing and len(existing) > 0:
                continue
            p_choices = await statics.get_class_selection(sid, iid)
            if p_choices:
                await db.set_inventory_value(p, sid, iid, "classes", p_choices)

        # Ping players and send response
        player_pings = ""
        for p in player_names:
            player_pings += f"<@{p}> "

        description = (f"Match **{instance_name}** Started with {selected_round_type} rounds!\n\n"
                       f"{player_pings}\n"
                       "It's time to pick your class! You can now use the `pickclass` command.\n\n"
                       "Use the `bracket` command to view the current standings for this KDR at any time.")
        
        await interaction.response.send_message(description)

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
            await response.send_message("This KDR is already full.", ephemeral=True)
            return

        # mark if its users first game on server to send also a reminder to do /tutorial
        is_firstgame = False
        # check if user exists, and add
        if not db.check_user_exist(pid, sid):
            db.add_user_to_kdr(pid, sid, iid, [])
            is_firstgame = True
        else:
            db.update_user_to_kdr(pid, sid, iid, [])

        # check if last player
        if instance.get("players") == instance.get("max_players"):
            await response.send_message(f"<@{pid}> joined with {choices}.\nYou are the final player.\nThis match is ready to start.")
            return

        await response.send_message(f"<@{pid}> joined the KDR {iid}!")
        if is_firstgame:
            await interaction.followup.send(kdr_messages.first_game_join(), ephemeral=True)
    
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
            await response.send_message("You do not have any KDR Data on this server! Try joining a KDR first with `join`.", ephemeral=True)
            return


        player_instances=await db.get_users_value(pid,sid,"instances")
        total_wl=await db.get_users_value(pid,sid,"total_winloss")
        elo=int(await db.get_users_value(pid,sid,"elo"))
        
        description=f"Your current total Wins and Losses are {total_wl[0]}W / {total_wl[1]}L\n\n"
        if len(player_instances)>0:
            description+="You are currently a part of the following KDRs: \n"
            for instance in player_instances:
                description+=f"{instance} "
        if elo!=DEFAULT_ELO_RANKING:
            description+=f"\nYour current KDR Elo Ranking in this server is {elo}"

        await response.send_message(description, ephemeral=True)

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

        col_users=list(col_users.sort("elo",-1))
        if len(col_users)==0:
            await interaction.followup.send(f"{OOPS}\n No Users have Played in KDRs yet in this server.",ephemeral=True)
        filtered_users = [user for user in col_users if (int(user["elo"])) != DEFAULT_ELO_RANKING]
        filtered_users = filtered_users[:length]

        description=f"The KDR Elo Ranking top {length} for this server:\n"
        rank=1
        for player in filtered_users:
            playerid=player["id_player"]
            playerelo=int(player["elo"])
            description+=f"{rank} - <@{playerid}> (Elo: {playerelo})\n"
            rank+=1

        await interaction.followup.send(description, ephemeral=True)




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
            await response.send_message("This player has no KDR Data in this server", ephemeral=True)
            return


        player_instances=await db.get_users_value(pid,sid,"instances")
        total_wl=await db.get_users_value(pid,sid,"total_winloss")
        elo=int(await db.get_users_value(pid,sid,"elo"))
        
        description=f"The current total Wins and Losses for <@{pid}> are {total_wl[0]}W / {total_wl[1]}L\n\n"
        if len(player_instances)>0:
            description+="They are currently a part of the following KDRs: \n"
            for instance in player_instances:
                description+=f"{instance} "
        if elo!=DEFAULT_ELO_RANKING:
            description+=f"\nTheir current KDR Elo Ranking in this server is **{elo}**"

        await response.send_message(description, ephemeral=True)


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
            await response.send_message("This player has no KDR Data in that KDR", ephemeral=True)
            return

        status_panel_generator = StatusPanel(pid, iid, sid, player.name)

        await response.send_message(embed=await status_panel_generator.get_message(), ephemeral=True)



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
        
        await interaction.response.send_message("Creating Class Select Thread...", ephemeral=True)

        channel = await self.client.fetch_channel(interaction.channel_id)
        thread = await channel.create_thread(name=f'Class Selection for {interaction.user.name}',
                                             type=ChannelType.public_thread, auto_archive_duration=60)
        await thread.send(content=f'<@{pid}>', view=v, embeds=embeds)


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
            await interaction.response.send_message("You cannot see the bracket of a KDR you are not in.", ephemeral=True)
            return

        description=f"Round **{active_round+1}** of **{len(current_rounds)}** for KDR `{iid}`\n\n"
        missing_to_play=[]
        missing_shop_phase=[]

        for i in range(len(current_rounds[active_round])):
            description+=f"<@{current_rounds[active_round][i][0]}> vs <@{current_rounds[active_round][i][1]}> "
            if round_results[active_round][i][1]!=WinType.INCOMPLETE.value:
                description+=f"- <@{current_rounds[active_round][i][not round_results[active_round][i][0]]}> wins "
                if round_results[active_round][i][1]==WinType.WIN_2X0.value:
                    description+=f"2-0"
                if round_results[active_round][i][1]==WinType.WIN_2X1.value:
                    description+=f"2-1"
                if round_results[active_round][i][1]==WinType.WIN_DEFAULT.value:
                    description+=f"by Default"
            else:
                missing_to_play.append(current_rounds[active_round][i][0])
                missing_to_play.append(current_rounds[active_round][i][1])
            description+=f"\n"
        
        for player in kdr_players:
            did_not_do_shop_phase=await db.get_inventory_value(player,sid,iid,"shop_phase")
            if did_not_do_shop_phase:
                missing_shop_phase.append(player)

        if len(missing_to_play)>0:
            add_to_msg="The Following Players have not played: "
            for p in missing_to_play:
                add_to_msg+=f"<@{p}> "
            description+=add_to_msg
            description+=f"\n"

        if len(missing_shop_phase)>0:
            add_to_msg="The Following Players have not conducted their shop phase: "
            for p in missing_shop_phase:
                add_to_msg+=f"<@{p}> "
            description+=add_to_msg
            description+=f"\n"
        
        if len(missing_shop_phase)==0 and len(missing_to_play)==0:
            description+="\nAll players have finished their matches and shops this round, inform the creator or an admin to use the /nextround command!"

        await interaction.response.send_message(description)
        
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
            await interaction.response.send_message("The result for your match has already been reported.\nIf you feel that the result is incorrect, contact an Admin.", ephemeral=True)
            return

        classes = await db.get_inventory_value(opponent, sid, iid, 'class')
        if len(classes) == 0:
            await interaction.response.send_message("Your opponent hasn't picked a class", ephemeral=True)
            return

        if self_wins == opp_wins:
            await interaction.response.send_message("Ties cannot exist in KDR.", ephemeral=True)
            return

        if not (2 <= (self_wins + opp_wins) <= 3):
            await interaction.response.send_message("KDR Matches are Best of 3.\nThe reported result does not match the possible amount of matches.", ephemeral=True)
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

        # Slime: absorb opponent's class on victory (round 1 always absorbs)
        if player_won or active_round == 0:
            slime_modifiers = await db.get_inventory_value(pid, sid, iid, 'modifiers')
            if SpecialClassHandling.CLASS_SLIME.value in slime_modifiers:
                opp_class = await db.get_inventory_value(opponent, sid, iid, "class")
                if opp_class:
                    absorbed = list(await db.get_inventory_value(pid, sid, iid, "absorbed_classes") or [])
                    if opp_class not in absorbed:
                        absorbed.append(opp_class)
                        await db.set_inventory_value(pid, sid, iid, "absorbed_classes", absorbed)
                    opp_inv = await db.get_inventory(opponent, sid, iid)
                    if opp_inv:
                        if "base_cards" in opp_inv:
                            await db.set_inventory_value(pid, sid, iid, "base_cards", opp_inv["base_cards"])
                        if "skills" in opp_inv:
                            for sk in opp_inv["skills"]:
                                await db.set_inventory_value(pid, sid, iid, 'skills', sk, operation="$push")
                        if "loot" in opp_inv:
                            for bloot in opp_inv["loot"]:
                                await db.set_inventory_value(pid, sid, iid, 'loot', bloot, operation="$push")
                        if "treasures" in opp_inv:
                            for tr in opp_inv["treasures"]:
                                await db.set_inventory_value(pid, sid, iid, 'treasures', tr, operation="$push")

        # Get opponent name to avoid pinging them into threads
        opponent_name = "Opponent"
        opponent_user = self.client.get_user(int(opponent))
        if not opponent_user:
            try:
                opponent_user = await self.client.fetch_user(int(opponent))
            except:
                pass
        if opponent_user:
            opponent_name = f"**{opponent_user.display_name}**"
        else:
            opponent_name = f"**Player {opponent}**"

        await interaction.response.send_message(f"<@{pid}> has reported their match results as {self_wins} / {opp_wins} VS {opponent_name}.")

    """ Player Leave Match """

    @app_commands.command(name="leavekdr", description="Leave an active KDR and forfeit your matches.")
    @app_commands.guild_only()
    @app_commands.check(statics.player_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def leave_kdr(self, interaction: Interaction, iid: str = ""):
        # Fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        if iid == "":
            player_kdrs = await db.get_users_value(str(interaction.user.id), sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]

        round_results = await db.get_instance_value(sid, iid, 'round_results')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        round_type = await db.get_instance_value(sid, iid, 'round_type')  # Fetch the round type

        # Logic for Round Robin
        if round_type == "Round Robin":
            # Loop through all rounds and matches
            for x in range(len(current_rounds)):
                for y in range(len(current_rounds[x])):
                    match = current_rounds[x][y]
                    first_player, second_player = "", ""
                    p1_wl, p2_wl = [], []
                    fp = str(match[0])
                    sp = str(match[1])
                    # If player not in match or match was already reported, continue
                    if (fp != pid and sp != pid) or round_results[x][y][1] != WinType.INCOMPLETE.value:
                        continue
                    # If player is first player in match
                    if fp == pid:
                        # Set the round results to first player losing
                        round_results[x][y] = (False, WinType.WIN_DEFAULT.value)
                        # First player is player
                        first_player = pid
                        # Second player is opponent
                        second_player = sp
                        p1_wl = await db.get_inventory_value(first_player, sid, iid, "wl_ratio")
                        p2_wl = await db.get_inventory_value(second_player, sid, iid, "wl_ratio")
                        # Give player (first player) loss
                        p1_wl[True] += 1
                        # Give opponent (second player) win
                        p2_wl[False] += 1
                    if sp == pid:
                        round_results[x][y] = (True, WinType.WIN_DEFAULT.value)
                        first_player = fp
                        second_player = pid
                        p1_wl = await db.get_inventory_value(first_player, sid, iid, "wl_ratio")
                        p2_wl = await db.get_inventory_value(second_player, sid, iid, "wl_ratio")
                        # Give player (second player) loss
                        p2_wl[True] += 1
                        # Give opponent (first player) win
                        p1_wl[False] += 1

                    await db.set_inventory_value(first_player, sid, iid, "wl_ratio", p1_wl)
                    await db.set_inventory_value(second_player, sid, iid, "wl_ratio", p2_wl)
                    await db.set_instance_value(sid, iid, 'round_results', round_results)

        # Logic for Swiss
        elif round_type == "Swiss":
            # Loop through current and past rounds only
            for x in range(active_round + 1):
                for y in range(len(current_rounds[x])):
                    match = current_rounds[x][y]
                    fp, sp = str(match[0]), str(match[1])

                    # If player is not in the match or match was already reported, continue
                    if (fp != pid and sp != pid) or round_results[x][y][1] != WinType.INCOMPLETE.value:
                        continue

                    # Handle player leaving
                    if fp == pid:
                        round_results[x][y] = (False, WinType.WIN_DEFAULT.value)  # Opponent wins by default
                    elif sp == pid:
                        round_results[x][y] = (True, WinType.WIN_DEFAULT.value)  # Opponent wins by default

    # Remove player from the KDR
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

        creator_id = await db.get_instance_value(sid, iid, 'creator_id')
        if str(creator_id) == pid:
            await db.set_instance_value(sid, iid, 'creator_id', None)

        await db.set_instance_value(sid, iid, 'players', num_players)
        await db.set_instance_value(sid, iid, 'player_names', players)
        await db.set_instance_value(sid, iid, 'offered_classes', offered_classes)
        await db.set_users_value(pid, sid, 'instances', player_active_instances)
        if not instance_started:
            await db.delete_player_inventory(pid, sid, iid)
        else:
            msg += "They have forfeited any matches not yet started."
        
        await interaction.response.send_message(msg)

    """ Command Errors """

    @start_kdr.error
    @join_kdr.error
    @pick_class.error
    @report_result.error
    @leave_kdr.error
    @get_bracket.error
    @get_player_data.error
    @get_player_inventory.error
    @get_top_ranking.error
    async def command_error(self, interaction, error):
        description = ""
        if isinstance(error, kdr_errors.InstanceDoesNotExistError):
            description = f"KDR Instance {error} does not exist."
        elif isinstance(error, kdr_errors.PlayerNotInInstanceError):
            description = f"You are not part of KDR Instance {error}"
        elif isinstance(error, kdr_errors.PlayerAlreadyJoinedError):
            description = f"You already joined KDR Instance {error}"
        elif isinstance(error, kdr_errors.InstanceStartedError):
            description = f"{error} has already started."
        elif isinstance(error, kdr_errors.InstanceNotStartedError):
            description = f"{error} hasn't started yet!"
        elif isinstance(error, kdr_errors.PlayerHasClassAlreadyError):
            description = f"You have already picked a class!"
        elif isinstance(error, kdr_errors.PlayerNotInRoundError):
            description = f"You are not playing in this round."
        elif isinstance(error, kdr_errors.PlayerHasNoClassError):
            description = f"You have not picked a class yet."
        
        if description:
            await interaction.response.send_message(description, ephemeral=True)
            return
        
        if isinstance(error, kdr_errors.PlayerHasNoCharacterSheetError):
            description = "You do not have a character sheet in this KDR yet. Join the KDR and pick a class first!"
            await interaction.response.send_message(description, ephemeral=True)
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
        self.client = client

    """ Create New KDR """

    @app_commands.command(name="newkdr", description="Creates a new KDR with a random Instance ID.")
    @app_commands.describe(playernum="The Number of players in the KDR, Defaults to 8",
                        isprivate="Should the KDR ID be shown in a private Message? Defaults to False",
                            modifiers="List of Modifiers to use this KDR, defailts to empty",
                            class_selection_number="Number of classes to offer, defaults to 1, be careful increasing",
                           isranked="Is the KDR Ranked? Defaults to False. KDR ADMIN ONLY")
    @app_commands.guild_only()
    async def new_kdr(self, interaction: Interaction, playernum:int=8, isprivate: bool = False, modifiers: str="", class_selection_number: int=1, isranked: bool = False):
        sid = interaction.guild_id
        pid=str(interaction.user.id)
        proles=interaction.user.roles
        await interaction.response.defer(ephemeral=True)
        if playernum%2!=0:
            await interaction.followup.send(f"{OOPS} Max Number of Players must be even.", ephemeral=True)
            return
        if isranked and ROLE_ADMIN not in str(proles):
            await interaction.followup.send(f"{OOPS} Only Admins may create a ranked KDR.", ephemeral=True)
            return
        hasplayerstartedkdr=await db.has_player_started_a_kdr(pid,sid)
        if hasplayerstartedkdr and ROLE_ADMIN not in str(proles):
            await interaction.followup.send(f"{OOPS} Non Admins may not create more than 1 KDR at a time!", ephemeral=True)
            return
        name_id = statics.generate_instance_name(sid)
        await db.add_new_kdr(sid, name_id, isranked,pid,playernum, class_selection_number, modifiers)
        msg = "Started a new KDR "
        if isranked:
            msg = f"Started a **ranked** KDR "
        
        msg+=f"for up to {playernum} players "

        if not isprivate:
            msg += f"with passcode `{name_id}`"
        
        await interaction.followup.send(msg)
        if isprivate:
            await interaction.followup.send(f"This KDR's Passcode is `{name_id}`", ephemeral=True)

    """ Start KDR """

    @app_commands.command(name="startkdr", description="Starts a new KDR given the Instance ID.")
    @app_commands.describe(
        iid="The Instance ID of the KDR.",
        rematch_count="The Number of times each player fights each other in the round robin OR the number of rounds in Swiss. Defaults to 1.",
        round_type="The type of rounds to use (Round Robin or Swiss). Defaults to Round Robin."
    )
    @app_commands.choices(
        round_type=[
            app_commands.Choice(name="Round Robin", value="Round Robin"),
            app_commands.Choice(name="Swiss", value="Swiss")
        ]
    )
    @app_commands.guild_only()
    @app_commands.check(statics.instance_not_started)
    @app_commands.check(statics.instance_exists)
    async def start_kdr(
        self,
        interaction: Interaction,
        iid: str = "",
        rematch_count: int = 1,
        round_type: app_commands.Choice[str] = None
    ):
        # Fetch data
        sid = interaction.guild_id
        pid = str(interaction.user.id)

        if iid == "":
            player_kdrs = await db.get_users_value(pid, sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]

        if rematch_count < 1:
            rematch_count = 1

        res_started = await db.get_instance_value(sid, iid, 'started')

        if res_started:
            await interaction.response.send_message("This KDR has already started.", ephemeral=True)
            return

        owner = await db.get_instance_value(sid, iid, "creator_id")
        if str(owner) != str(pid) and ROLE_ADMIN not in str(interaction.user.roles):
            await interaction.response.send_message("You cannot start a KDR you are not the owner of.", ephemeral=True)
            return

        instance_name = await db.get_instance_value(sid, iid, DB_KEY_INSTANCE)
        num_players = await db.get_instance_value(sid, iid, 'players')

        # Check for player condition
        if num_players % 2 != 0 or num_players <= 0:
            await interaction.response.send_message("There must be an even number of participants to start.", ephemeral=True)
            return

        # Default to "Round Robin" if no round_type is provided
        selected_round_type = round_type.value if round_type else "Round Robin"

        # Fetch players and generate round brackets
        player_names = await db.get_instance_list(sid, iid, 'player_names')
        rounds = ""

        if selected_round_type == "Round Robin":
            rounds = statics.create_balanced_round_robin(player_names, rematch_count)
        elif selected_round_type == "Swiss":
            rounds = statics.create_swiss_rounds(player_names, rematch_count)

        # Add the initialized rounds to the KDR
        await db.add_match_rounds_to_kdr(sid, iid, rounds)

        # Set instance to started
        await db.set_instance_value(sid, iid, 'started', True)
        await db.set_instance_value(sid, iid, 'active_round', 0)
        await db.set_instance_value(sid, iid, 'round_type', selected_round_type)
        await db.set_all_inventory_value(sid, iid, 'shop_phase', True)

        # Assign classes to all players — done once here so no duplicates
        # Skip players who already have classes (e.g. set via setofferedclass)
        for p in player_names:
            existing = await db.get_inventory_value(p, sid, iid, "classes")
            if existing and len(existing) > 0:
                continue
            p_choices = await statics.get_class_selection(sid, iid)
            if p_choices:
                await db.set_inventory_value(p, sid, iid, "classes", p_choices)

        # Ping players and send response
        player_pings = ""
        for p in player_names:
            player_pings += f"<@{p}> "

        description = (f"Match **{instance_name}** Started with {selected_round_type} rounds!\n\n"
                       f"{player_pings}\n"
                       "It's time to pick your class! You can now use the `pickclass` command.\n\n"
                       "Use the `bracket` command to view the current standings for this KDR at any time.")
        
        await interaction.response.send_message(description)

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
            await response.send_message("This KDR is already full.", ephemeral=True)
            return

        # mark if its users first game on server to send also a reminder to do /tutorial
        is_firstgame = False
        # check if user exists, and add
        if not db.check_user_exist(pid, sid):
            db.add_user_to_kdr(pid, sid, iid, [])
            is_firstgame = True
        else:
            db.update_user_to_kdr(pid, sid, iid, [])

        # check if last player
        if instance.get("players") == instance.get("max_players"):
            await response.send_message(f"<@{pid}> joined with {choices}.\nYou are the final player.\nThis match is ready to start.")
            return

        await response.send_message(f"<@{pid}> joined the KDR {iid}!")
        if is_firstgame:
            await interaction.followup.send(kdr_messages.first_game_join(), ephemeral=True)
    
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
            await response.send_message("You do not have any KDR Data on this server! Try joining a KDR first with `join`.", ephemeral=True)
            return


        player_instances=await db.get_users_value(pid,sid,"instances")
        total_wl=await db.get_users_value(pid,sid,"total_winloss")
        elo=int(await db.get_users_value(pid,sid,"elo"))
        
        description=f"Your current total Wins and Losses are {total_wl[0]}W / {total_wl[1]}L\n\n"
        if len(player_instances)>0:
            description+="You are currently a part of the following KDRs: \n"
            for instance in player_instances:
                description+=f"{instance} "
        if elo!=DEFAULT_ELO_RANKING:
            description+=f"\nYour current KDR Elo Ranking in this server is {elo}"

        await response.send_message(description, ephemeral=True)

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

        col_users=list(col_users.sort("elo",-1))
        if len(col_users)==0:
            await interaction.followup.send(f"{OOPS}\n No Users have Played in KDRs yet in this server.",ephemeral=True)
        filtered_users = [user for user in col_users if (int(user["elo"])) != DEFAULT_ELO_RANKING]
        filtered_users = filtered_users[:length]

        description=f"The KDR Elo Ranking top {length} for this server:\n"
        rank=1
        for player in filtered_users:
            playerid=player["id_player"]
            playerelo=int(player["elo"])
            description+=f"{rank} - <@{playerid}> (Elo: {playerelo})\n"
            rank+=1

        await interaction.followup.send(description, ephemeral=True)




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
            await response.send_message("This player has no KDR Data in this server", ephemeral=True)
            return


        player_instances=await db.get_users_value(pid,sid,"instances")
        total_wl=await db.get_users_value(pid,sid,"total_winloss")
        elo=int(await db.get_users_value(pid,sid,"elo"))
        
        description=f"The current total Wins and Losses for <@{pid}> are {total_wl[0]}W / {total_wl[1]}L\n\n"
        if len(player_instances)>0:
            description+="They are currently a part of the following KDRs: \n"
            for instance in player_instances:
                description+=f"{instance} "
        if elo!=DEFAULT_ELO_RANKING:
            description+=f"\nTheir current KDR Elo Ranking in this server is **{elo}**"

        await response.send_message(description, ephemeral=True)


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
            await response.send_message("This player has no KDR Data in that KDR", ephemeral=True)
            return

        status_panel_generator = StatusPanel(pid, iid, sid, player.name)

        await response.send_message(embed=await status_panel_generator.get_message(), ephemeral=True)



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
        
        await interaction.response.send_message("Creating Class Select Thread...", ephemeral=True)

        channel = await self.client.fetch_channel(interaction.channel_id)
        thread = await channel.create_thread(name=f'Class Selection for {interaction.user.name}',
                                             type=ChannelType.public_thread, auto_archive_duration=60)
        await thread.send(content=f'<@{pid}>', view=v, embeds=embeds)


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
            await interaction.response.send_message("You cannot see the bracket of a KDR you are not in.", ephemeral=True)
            return

        description=f"Round **{active_round+1}** of **{len(current_rounds)}** for KDR `{iid}`\n\n"
        missing_to_play=[]
        missing_shop_phase=[]

        for i in range(len(current_rounds[active_round])):
            description+=f"<@{current_rounds[active_round][i][0]}> vs <@{current_rounds[active_round][i][1]}> "
            if round_results[active_round][i][1]!=WinType.INCOMPLETE.value:
                description+=f"- <@{current_rounds[active_round][i][not round_results[active_round][i][0]]}> wins "
                if round_results[active_round][i][1]==WinType.WIN_2X0.value:
                    description+=f"2-0"
                if round_results[active_round][i][1]==WinType.WIN_2X1.value:
                    description+=f"2-1"
                if round_results[active_round][i][1]==WinType.WIN_DEFAULT.value:
                    description+=f"by Default"
            else:
                missing_to_play.append(current_rounds[active_round][i][0])
                missing_to_play.append(current_rounds[active_round][i][1])
            description+=f"\n"
        
        for player in kdr_players:
            did_not_do_shop_phase=await db.get_inventory_value(player,sid,iid,"shop_phase")
            if did_not_do_shop_phase:
                missing_shop_phase.append(player)

        if len(missing_to_play)>0:
            add_to_msg="The Following Players have not played: "
            for p in missing_to_play:
                add_to_msg+=f"<@{p}> "
            description+=add_to_msg
            description+=f"\n"

        if len(missing_shop_phase)>0:
            add_to_msg="The Following Players have not conducted their shop phase: "
            for p in missing_shop_phase:
                add_to_msg+=f"<@{p}> "
            description+=add_to_msg
            description+=f"\n"
        
        if len(missing_shop_phase)==0 and len(missing_to_play)==0:
            description+="\nAll players have finished their matches and shops this round, inform the creator or an admin to use the /nextround command!"

        await interaction.response.send_message(description)
        
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
            await interaction.response.send_message("The result for your match has already been reported.\nIf you feel that the result is incorrect, contact an Admin.", ephemeral=True)
            return

        classes = await db.get_inventory_value(opponent, sid, iid, 'class')
        if len(classes) == 0:
            await interaction.response.send_message("Your opponent hasn't picked a class", ephemeral=True)
            return

        if self_wins == opp_wins:
            await interaction.response.send_message("Ties cannot exist in KDR.", ephemeral=True)
            return

        if not (2 <= (self_wins + opp_wins) <= 3):
            await interaction.response.send_message("KDR Matches are Best of 3.\nThe reported result does not match the possible amount of matches.", ephemeral=True)
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

        # Slime: absorb opponent's class on victory (round 1 always absorbs)
        if player_won or active_round == 0:
            slime_modifiers = await db.get_inventory_value(pid, sid, iid, 'modifiers')
            if SpecialClassHandling.CLASS_SLIME.value in slime_modifiers:
                opp_class = await db.get_inventory_value(opponent, sid, iid, "class")
                if opp_class:
                    absorbed = list(await db.get_inventory_value(pid, sid, iid, "absorbed_classes") or [])
                    if opp_class not in absorbed:
                        absorbed.append(opp_class)
                        await db.set_inventory_value(pid, sid, iid, "absorbed_classes", absorbed)
                    opp_inv = await db.get_inventory(opponent, sid, iid)
                    if opp_inv:
                        if "base_cards" in opp_inv:
                            await db.set_inventory_value(pid, sid, iid, "base_cards", opp_inv["base_cards"])
                        if "skills" in opp_inv:
                            for sk in opp_inv["skills"]:
                                await db.set_inventory_value(pid, sid, iid, 'skills', sk, operation="$push")
                        if "loot" in opp_inv:
                            for bloot in opp_inv["loot"]:
                                await db.set_inventory_value(pid, sid, iid, 'loot', bloot, operation="$push")
                        if "treasures" in opp_inv:
                            for tr in opp_inv["treasures"]:
                                await db.set_inventory_value(pid, sid, iid, 'treasures', tr, operation="$push")

        # Get opponent name to avoid pinging them into threads
        opponent_name = "Opponent"
        opponent_user = self.client.get_user(int(opponent))
        if not opponent_user:
            try:
                opponent_user = await self.client.fetch_user(int(opponent))
            except:
                pass
        if opponent_user:
            opponent_name = f"**{opponent_user.display_name}**"
        else:
            opponent_name = f"**Player {opponent}**"

        await interaction.response.send_message(f"<@{pid}> has reported their match results as {self_wins} / {opp_wins} VS {opponent_name}.")

    """ Player Leave Match """

    @app_commands.command(name="leavekdr", description="Leave an active KDR and forfeit your matches.")
    @app_commands.guild_only()
    @app_commands.check(statics.player_exist_instance)
    @app_commands.check(statics.instance_exists)
    async def leave_kdr(self, interaction: Interaction, iid: str = ""):
        # Fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        if iid == "":
            player_kdrs = await db.get_users_value(str(interaction.user.id), sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]

        round_results = await db.get_instance_value(sid, iid, 'round_results')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        round_type = await db.get_instance_value(sid, iid, 'round_type')  # Fetch the round type

        # Logic for Round Robin
        if round_type == "Round Robin":
            # Loop through all rounds and matches
            for x in range(len(current_rounds)):
                for y in range(len(current_rounds[x])):
                    match = current_rounds[x][y]
                    first_player, second_player = "", ""
                    p1_wl, p2_wl = [], []
                    fp = str(match[0])
                    sp = str(match[1])
                    # If player not in match or match was already reported, continue
                    if (fp != pid and sp != pid) or round_results[x][y][1] != WinType.INCOMPLETE.value:
                        continue
                    # If player is first player in match
                    if fp == pid:
                        # Set the round results to first player losing
                        round_results[x][y] = (False, WinType.WIN_DEFAULT.value)
                        # First player is player
                        first_player = pid
                        # Second player is opponent
                        second_player = sp
                        p1_wl = await db.get_inventory_value(first_player, sid, iid, "wl_ratio")
                        p2_wl = await db.get_inventory_value(second_player, sid, iid, "wl_ratio")
                        # Give player (first player) loss
                        p1_wl[True] += 1
                        # Give opponent (second player) win
                        p2_wl[False] += 1
                    if sp == pid:
                        round_results[x][y] = (True, WinType.WIN_DEFAULT.value)
                        first_player = fp
                        second_player = pid
                        p1_wl = await db.get_inventory_value(first_player, sid, iid, "wl_ratio")
                        p2_wl = await db.get_inventory_value(second_player, sid, iid, "wl_ratio")
                        # Give player (second player) loss
                        p2_wl[True] += 1
                        # Give opponent (first player) win
                        p1_wl[False] += 1

                    await db.set_inventory_value(first_player, sid, iid, "wl_ratio", p1_wl)
                    await db.set_inventory_value(second_player, sid, iid, "wl_ratio", p2_wl)
                    await db.set_instance_value(sid, iid, 'round_results', round_results)

        # Logic for Swiss
        elif round_type == "Swiss":
            # Loop through current and past rounds only
            for x in range(active_round + 1):
                for y in range(len(current_rounds[x])):
                    match = current_rounds[x][y]
                    fp, sp = str(match[0]), str(match[1])

                    # If player is not in the match or match was already reported, continue
                    if (fp != pid and sp != pid) or round_results[x][y][1] != WinType.INCOMPLETE.value:
                        continue

                    # Handle player leaving
                    if fp == pid:
                        round_results[x][y] = (False, WinType.WIN_DEFAULT.value)  # Opponent wins by default
                    elif sp == pid:
                        round_results[x][y] = (True, WinType.WIN_DEFAULT.value)  # Opponent wins by default

    # Remove player from the KDR
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

        creator_id = await db.get_instance_value(sid, iid, 'creator_id')
        if str(creator_id) == pid:
            await db.set_instance_value(sid, iid, 'creator_id', None)

        await db.set_instance_value(sid, iid, 'players', num_players)
        await db.set_instance_value(sid, iid, 'player_names', players)
        await db.set_instance_value(sid, iid, 'offered_classes', offered_classes)
        await db.set_users_value(pid, sid, 'instances', player_active_instances)
        if not instance_started:
            await db.delete_player_inventory(pid, sid, iid)
        else:
            msg += "They have forfeited any matches not yet started."
        
        await interaction.response.send_message(msg)

    """ Command Errors """

    @start_kdr.error
    @join_kdr.error
    @pick_class.error
    @report_result.error
    @leave_kdr.error
    @get_bracket.error
    @get_player_data.error
    @get_player_inventory.error
    @get_top_ranking.error
    async def command_error(self, interaction, error):
        description = ""
        if isinstance(error, kdr_errors.InstanceDoesNotExistError):
            description = f"KDR Instance {error} does not exist."
        elif isinstance(error, kdr_errors.PlayerNotInInstanceError):
            description = f"You are not part of KDR Instance {error}"
        elif isinstance(error, kdr_errors.PlayerAlreadyJoinedError):
            description = f"You already joined KDR Instance {error}"
        elif isinstance(error, kdr_errors.InstanceStartedError):
            description = f"{error} has already started."
        elif isinstance(error, kdr_errors.InstanceNotStartedError):
            description = f"{error} hasn't started yet!"
        elif isinstance(error, kdr_errors.PlayerHasClassAlreadyError):
            description = f"You have already picked a class!"
        elif isinstance(error, kdr_errors.PlayerNotInRoundError):
            description = f"You are not playing in this round."
        elif isinstance(error, kdr_errors.PlayerHasNoClassError):
            description = f"You have not picked a class yet."
        
        if description:
            await interaction.response.send_message(description, ephemeral=True)
            return
        
        if isinstance(error, kdr_errors.PlayerHasNoCharacterSheetError):
            description = "You do not have a character sheet in this KDR yet. Join the KDR and pick a class first!"
            await interaction.response.send_message(description, ephemeral=True)
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
