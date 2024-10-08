import core.kdr_db as db
import core.kdr_db_build as db_build
import core.kdr_errors as kdr_errors
import core.kdr_messages as kdr_messages
import core.kdr_statics as statics

from discord.ext.commands.cog import Cog
from discord.ext.commands.bot import Bot
from discord import app_commands
from discord import Interaction, Attachment
from discord import Member
from discord import Interaction

from core.kdr_data import WinType, SpecialClassHandling
from core.kdr_elo import EloAdjustment
from config.config import OOPS, ROLE_ADMIN, DB_KEY_INSTANCE, ROLE_CODER, ROLE_OWNER, \
                            PATH_BUCKETS, PATH_BASE_CLASSES, PATH_STATIC_CLASSES, \
                            PATH_TREASURES, PATH_GENERIC_SKILLS, PATH_GENERIC_BUCKETS, \
                            PATH_BUCKET_SKILLS, PATH_CLASS_SKILLS
from config.secret_values import GUILD, SERVER_WHITELIST

import random

from enum import Enum

import json

class ShopStatuses(Enum):
    GoldCalculation = 0
    XpCalculation = 1
    PickSkill=2
    Train=3
    LevelStats=4
    PickTreasure=5
    BuyCards=6
    PayTip=7
    FinishShop=8



class KDRAdmin(Cog):
    def __init__(self, client: Bot):
        self.client = client

    """ Admin Reset KDR Build Data """

    @app_commands.command(name="resetdata", description="CAUTION. Resets ALL KDR class and item data in the database.")
    @app_commands.guild_only()
    @app_commands.check(statics.server_whitelisted)
    @app_commands.checks.has_any_role(ROLE_CODER, ROLE_OWNER)
    async def reset_kdr_data(self, interaction=Interaction):
        await db.clear_db_data()
        await interaction.response.send_message("KDR Data has been reset.")

    """ Admin Reset KDRS """

    @app_commands.command(name="resetkdrs", description="CAUTION. Resets ALL KDR data in the database.")
    @app_commands.guild_only()
    @app_commands.check(statics.server_whitelisted)
    @app_commands.checks.has_any_role(ROLE_CODER, ROLE_OWNER)
    async def reset_kdrs(self, interaction=Interaction):
        await db.clear_kdr_data()
        await interaction.response.send_message("KDR Data has been reset.")

    """ Admin Advance KDR Round"""

    @app_commands.command(name="nextround", description="Advances the KDR Round based on Instance ID.")
    @app_commands.describe(iid="The Instance ID of the KDR.")
    @app_commands.guild_only()
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.instance_exists)
    async def nextround(self, interaction=Interaction, iid: str = ""):
        # fetch data
        sid = interaction.guild_id
        pid = str(interaction.user.id)

        if iid == "":
            player_kdrs = await db.get_users_value(pid, sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]

        creatorid = await db.get_instance_value(sid, iid, 'creator_id')
        if str(creatorid)!=str(pid) and ROLE_ADMIN not in str(interaction.user.roles):
            await interaction.response.send_message(f"You cannot advance the round of a KDR you are not the owner of.",ephemeral=True)
            return

        res_started = await db.get_instance_value(sid, iid, 'started')

        if not res_started:
            await interaction.response.send_message(f"This KDR has not started.")
            return


        instance_name = await db.get_instance_value(sid, iid, DB_KEY_INSTANCE)
        player_names = await db.get_instance_list(sid, iid, 'player_names')
        curr_round = await db.get_instance_value(sid, iid, 'active_round')
        round_results = await db.get_instance_value(sid, iid, 'round_results')
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')
        isranked = await db.get_instance_value(sid, iid, 'is_ranked')

        curr_round += 1

        player_pings = ""
        for p in player_names:
            player_pings+=f"<@{p}> " 


        if curr_round >= len(current_rounds):
            msg=""
            msg+=f"{player_pings} "
            msg+=f"\nThe KDR `{instance_name}` has Ended! These are the final standings:\n\n"
            players=[]
            for player in player_names:
                playerdata=await db.get_inventory(player,sid,iid)
                players.append(playerdata)
            players=sorted(players,key=lambda x: x["wl_ratio"][0],reverse=True)
            for p in players:

                pname=p["id_player"]
                pwins=p["wl_ratio"][0]
                plosses=p["wl_ratio"][1]
                pclassid=p["class"]
                pelo=await db.get_users_value(pname,sid,"elo")
                pclass=await db.get_static_class_value(pclassid,"name")
                msg+=f"<@{pname}> ({pclass}) - **Wins**: {pwins}, **Losses**: {plosses}"
                if isranked:
                    msg+=f" **Elo Ranking After this KDR:** {int(pelo)}"
                msg+="\n"
                await db.set_users_value(pname,sid,"instances",iid,"$pull")
            await interaction.response.send_message(msg)
            await db.set_instance_value(sid,iid,"ended",True)
            return

        await db.set_instance_value(sid, iid, 'active_round', curr_round)

        await db.set_all_inventory_value(sid, iid, 'shop_phase', True)

        for p in player_names:
            current_shop_phase = await db.get_inventory_value(p, sid, iid, 'shop_stage')

            # Grant gold and xp anyways if player did not do shop phase
            if current_shop_phase == 0:
                xp = await db.get_inventory_value(p, sid, iid, 'XP')
                special_flags = await db.get_inventory_value(p, sid, iid, 'modifiers')
                await statics.update_gold(p, iid, sid, True, special_flags)
                xp += 2
                await db.set_inventory_value(p, sid, iid, 'XP', xp)
            await db.set_inventory_value(p, sid, iid, 'shop_stage', 0)
            player_data = await db.get_inventory(p, sid, iid)
            playermodifiers = player_data["modifiers"]
            for modifier in playermodifiers:
                if modifier == SpecialClassHandling.CLASS_MIMIC.value: #Mimics do not get a shop phase.
                    await db.set_inventory_value(p, sid, iid, 'shop_stage', 9)
                    await db.set_inventory_value(p, sid, iid, 'shop_phase', False)



        rounds=""
        num=0
        for i in current_rounds[curr_round]:
            rounds+=f"<@{i[0]}> vs <@{i[1]}>"
            if round_results[curr_round][num][1]!=WinType.INCOMPLETE.value:
                rounds+=f"- <@{current_rounds[curr_round][num][not round_results[curr_round][num][0]]}> wins "
            if round_results[curr_round][num][1]==WinType.WIN_2X0.value:
                rounds+=f"2-0"
            if round_results[curr_round][num][1]==WinType.WIN_2X1.value:
                rounds+=f"2-1"
            if round_results[curr_round][num][1]==WinType.WIN_DEFAULT.value:
                rounds+=f"by Default"
            num+=1
            rounds+="\n"

        # ping players and send response

        msg1 = f"The Next Round in KDR `{instance_name}` has Started!\n"
        msg2 = f'{player_pings}\n Check your current opponent with the `bracket` or `getcurrentmatch` command.'
        msg3 = f"Use the `bracket` command to view the current standings for this match at any time. \n"
        msg4 = f"{rounds}"
        await interaction.response.send_message(f"{msg1}\n{msg2}\n{msg3}\n{msg4}")

    """ Admin Force Finish KDR Round"""

    @app_commands.command(name="endround", description="Forcefully finishes all matches in the KDR Round based on Instance ID.")
    @app_commands.describe(iid="The Instance ID of the KDR.")
    @app_commands.guild_only()
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.instance_exists)
    async def forceendround(self, interaction=Interaction, iid: str = ""):
        # fetch data
        sid = interaction.guild_id
        pid = str(interaction.user.id)

        if iid == "":
            player_kdrs = await db.get_users_value(pid, sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]

        creatorid = await db.get_instance_value(sid, iid, 'creator_id')
        if str(creatorid)!=str(pid) and ROLE_ADMIN not in str(interaction.user.roles):
            await interaction.response.send_message(f"You cannot force finish the round of a KDR you are not the owner of.",ephemeral=True)
            return

        res_started = await db.get_instance_value(sid, iid, 'started')

        if not res_started:
            await interaction.response.send_message(f"This KDR has not started.")
            return


        instance_name = await db.get_instance_value(sid, iid, DB_KEY_INSTANCE)
        player_names = await db.get_instance_list(sid, iid, 'player_names')
        curr_round = await db.get_instance_value(sid, iid, 'active_round')
        round_results = await db.get_instance_value(sid, iid, 'round_results')
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')
        isranked = await db.get_instance_value(sid, iid, 'is_ranked')
        ismatchremaining=False

        msg=f"<@{pid}> has decided to Coinflip the remaining matches: These are the current standings:\n"
        players_to_ping=[]

        for y in range(len(current_rounds[curr_round])):
            match = current_rounds[curr_round][y]
            first_player, second_player = "", ""
            p1_wl, p2_wl = [], []
            fp = str(match[0])
            sp = str(match[1])
            # if match was already reported, continue
            if round_results[curr_round][y][1] != WinType.INCOMPLETE.value:
                continue

            #var to throw error if all matches are done
            ismatchremaining=True

            #coinflip the result
            npid=fp if random.randint(1,2)==1 else sp

            # if player is first player in match

            if fp == npid:
                # set the round results to first player losing
                round_results[curr_round][y] = (False, WinType.WIN_DEFAULT.value)
                # first player is player
                first_player = npid
                # second player is opponent
                second_player = sp
                p1_wl = await db.get_inventory_value(first_player, sid, iid, "wl_ratio")
                p2_wl = await db.get_inventory_value(second_player, sid, iid, "wl_ratio")
                # give player(first player) loss
                p1_wl[True] += 1
                # give opponent(second player) win
                p2_wl[False] += 1

            if sp == npid:
                round_results[curr_round][y] = (True, WinType.WIN_DEFAULT.value)
                first_player = fp
                second_player = npid
                p1_wl = await db.get_inventory_value(first_player, sid, iid, "wl_ratio")
                p2_wl = await db.get_inventory_value(second_player, sid, iid, "wl_ratio")
                # give player(second player) loss
                p2_wl[True] += 1
                # give opponent(first player) win
                p1_wl[False] += 1

            await db.set_inventory_value(first_player, sid, iid, "wl_ratio", p1_wl)
            await db.set_inventory_value(second_player, sid, iid, "wl_ratio", p2_wl)
            await db.set_instance_value(sid, iid, 'round_results', round_results)
            msg+=f"<@{second_player}> wins by default vs <@{first_player}> \n"
            players_to_ping.append(first_player)
            players_to_ping.append(second_player)
            

        if not ismatchremaining:
            await interaction.response.send_message(f"There are no matches left on this round.",ephemeral=True)
            return
        # ping players and send response
        for p in players_to_ping:
            msg+=f"<@{p}> "
        msg+=f"\n Remember to do your shop phases with `shop`, next round will begin soon!"

        await interaction.response.send_message(f"{msg}")


    """ Admin Delete KDR"""

    @app_commands.command(name="deletekdr", description="Delete KDR based on Instance ID.")
    @app_commands.describe(iid="The Instance ID of the KDR.")
    @app_commands.guild_only()
    @app_commands.check(statics.instance_exists)
    async def deletekdr(self, interaction=Interaction, iid: str = ""):
        # fetch data
        sid = interaction.guild_id
        pid = str(interaction.user.id)

        if iid == "":
            player_kdrs = await db.get_users_value(pid, sid, "instances")
            if len(player_kdrs) == 1:
                iid = player_kdrs[0]

        creatorid = await db.get_instance_value(sid, iid, 'creator_id')
        if str(creatorid)!=str(pid) and ROLE_ADMIN not in str(interaction.user.roles):
            await interaction.response.send_message(f"You cannot delete a KDR you are not the owner of.",ephemeral=True)
            return

        player_names = await db.get_instance_list(sid, iid, 'player_names')
        msg=""

        players_to_ping=[]
        players=[]
        for player in player_names:
            playerdata=await db.get_inventory(player,sid,iid)
            players.append(playerdata)
        for p in players:

            pname=p["id_player"]
            players_to_ping.append(pname)
            await db.set_users_value(pname,sid,"instances",iid,"$pull")
        
        
        for p in players_to_ping:
            msg+=f"<@{p}> "

        db.delete_kdr(sid,iid)
        msg=f"\n <@{pid}> has deleted KDR {iid}!"


        await interaction.response.send_message(f"{msg}")

    """ Admin Override Match Result """

    @app_commands.command(name="overrideresult", description="Override the result of an active KDR Match.")
    @app_commands.guild_only()
    @app_commands.checks.has_role(ROLE_ADMIN)
    @app_commands.check(statics.instance_started)
    @app_commands.check(statics.instance_exists)
    async def override_result(self, interaction: Interaction, iid: str,
                              first_player: Member, second_player: Member,
                              first_wins: int = 0, second_wins: int = 0):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        first_player = str(first_player.id)
        second_player = str(second_player.id)

        round_results = await db.get_instance_value(sid, iid, 'round_results')
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')
        is_kdr_ranked = await db.get_instance_value(sid, iid, 'is_ranked')

        won, match_pos = \
            await statics.check_player_won_round_by_ids(first_player, second_player, round_results, current_rounds)

        if first_wins == second_wins:
            await interaction.response.send_message('Ties cannot exist in KDR.', ephemeral=True)
            return

        if not (2 <= (first_wins + second_wins) <= 3):
            await interaction.response.send_message('KDR Matches are Best of 3.\n'
                                                    'The reported result does not '
                                                    'match the possible amount of matches.', ephemeral=True)
            return

        isfirstplayer=await statics.check__if_firstplayer_in_round(first_player,current_rounds,active_round)
        win_player_one = first_wins > second_wins if isfirstplayer else not first_wins > second_wins
        win_type = first_wins + second_wins - 1

        adjuster = EloAdjustment()

        p1_wl = await db.get_inventory_value(first_player, sid, iid, "wl_ratio")
        p2_wl = await db.get_inventory_value(second_player, sid, iid, "wl_ratio")
        p1_twl = await db.get_users_value(first_player, sid, 'total_winloss')
        p2_twl = await db.get_users_value(second_player, sid, 'total_winloss')

        if win_player_one:
            p1_wl[False] += 1
            p1_twl[False] += 1
            p1_wl[True] -= 1
            p1_twl[True] -= 1

            p2_wl[True] += 1
            p2_twl[True] += 1
            p2_wl[False] -= 1
            p2_twl[False] -= 1
        else:
            p1_wl[False] -= 1
            p1_twl[False] -= 1
            p1_wl[True] += 1
            p1_twl[True] += 1

            p2_wl[True] -= 1
            p2_twl[True] -= 1
            p2_wl[False] += 1
            p2_twl[False] += 1

        await db.set_inventory_value(first_player, sid, iid, "wl_ratio", p1_wl)
        await db.set_inventory_value(second_player, sid, iid, "wl_ratio", p2_wl)
        await db.set_users_value(first_player, sid, 'total_winloss', p1_twl)
        await db.set_users_value(second_player, sid, 'total_winloss', p2_twl)

        if is_kdr_ranked:
            await adjuster.swap_last_elo(first_player, second_player, sid, win_player_one)

        round_results[active_round][match_pos] = (win_player_one, win_type)

        await db.set_instance_value(sid, iid, 'round_results', round_results)
        await interaction.response.send_message(f'<@{pid}> has modified the match results as '
                                                f'<@{first_player}> {first_wins} '
                                                f'/ {second_wins} VS <@{second_player}>')
        


    """ Admin Override Class """

    @app_commands.command(name="setclass", description="Set a player's class.")
    @app_commands.describe(iid="The KDR ID", first_player="The Player to set the class of", classname="The class's EXACT name")
    @app_commands.guild_only()
    @app_commands.checks.has_role(ROLE_ADMIN)
    @app_commands.check(statics.instance_exists)
    async def override_class(self, interaction: Interaction, iid: str,
                              first_player: Member, classname:str):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        first_player = str(first_player.id)
        playerclass=await db.get_static_class_by_name(classname)

        await db.set_inventory_value(first_player,sid,iid,"class",playerclass["id"])
        generated_tip=random.randint(playerclass["tip_ratio"][0],playerclass["tip_ratio"][1])
        await db.set_inventory_value(first_player,sid,iid,"tip_threshold",generated_tip)
        await interaction.response.send_message(f'<@{pid}> has modified <@{first_player}>\'s class, they are now a {classname}. ')

        offered_classes = await db.get_instance_list(sid, iid, 'offered_classes')
        
        offered_classes.append(playerclass['id'])

        await db.set_instance_value(sid, iid, 'offered_classes', offered_classes)
        await db.set_instance_value(sid, iid, 'picked_classes', playerclass['id'], '$push')
 
    """ Admin Override Class to PICK """

    @app_commands.command(name="setofferedclass", description="Set a player's offered class.")
    @app_commands.describe(iid="The KDR ID", first_player="The Player to set the offered class of", classname="The class's EXACT name")
    @app_commands.guild_only()
    @app_commands.checks.has_role(ROLE_ADMIN)
    @app_commands.check(statics.instance_exists)
    async def override_class_offer(self, interaction: Interaction, iid: str,
                              first_player: Member, classname:str):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        first_player = str(first_player.id)
        playerclass=await db.get_static_class_by_name(classname)

        await db.set_inventory_value(first_player,sid,iid,"classes",[playerclass["base"]])
        await interaction.response.send_message(f'<@{pid}> has modified <@{first_player}>\'s offered class, they are now being offered {classname}. ')

        offered_classes = await db.get_instance_list(sid, iid, 'offered_classes')
        
        offered_classes.append(playerclass['base'])

        await db.set_instance_value(sid, iid, 'offered_classes', offered_classes)

    """ Admin Set Shop Phase Status """

    @app_commands.command(name="setshopstatus", description="Set a player's shop phase status.")
    @app_commands.describe(iid="The KDR ID", first_player="The Player to set the shop phase status of", shopstatus="The shop phase status")
    @app_commands.guild_only()
    @app_commands.checks.has_role(ROLE_ADMIN)
    @app_commands.check(statics.instance_exists)
    async def override_shop_status(self, interaction: Interaction, iid: str,
                              first_player: Member, shopstatus: ShopStatuses):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        first_player = str(first_player.id)

        shopphasestatus= not (shopstatus.value==8)

        await db.set_inventory_value(first_player,sid,iid,"shop_stage",shopstatus.value)
        await db.set_inventory_value(first_player,sid,iid,"shop_phase",shopphasestatus)

        await interaction.response.send_message(f'<@{pid}> has modified <@{first_player}>\'s shop status to {shopstatus.name}!')


    """ Admin Set Gold """

    @app_commands.command(name="setgoldvalue", description="Set a player's goldvalue.")
    @app_commands.describe(iid="The KDR ID", first_player="The Player to set the shop phase status of", goldval="The new gold value")
    @app_commands.guild_only()
    @app_commands.checks.has_role(ROLE_ADMIN)
    @app_commands.check(statics.instance_exists)
    async def override_gold_value(self, interaction: Interaction, iid: str,
                              first_player: Member, goldval: int):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        first_player = str(first_player.id)

        await db.set_inventory_value(first_player,sid,iid,"gold",goldval)

        await interaction.response.send_message(f'<@{pid}> has modified <@{first_player}>\'s gold to {goldval}!')



    """ Admin Clear Chat """

    #@app_commands.command(name="purge", description="Clears the channel messages. May take a while.")
    #@app_commands.guild_only()
    #@app_commands.checks.has_role(ROLE_ADMIN)
    #async def clear_chat(self, interaction=Interaction, limit: int = 1000000):
    #    await interaction.channel.purge(limit=limit)

    """ Admin Build Data """

    @app_commands.command(name="builddata", description="Builds the classes, treasures, buckets, etc based on files sent.")
    @app_commands.guild_only()
    @app_commands.check(statics.server_whitelisted)
    @app_commands.checks.has_any_role(ROLE_CODER, ROLE_OWNER)
    async def build_data(self,interaction: Interaction, basefile: Attachment,
                        staticfile: Attachment, bucketsfile: Attachment,
                        bucketskillsfile: Attachment, classskillfile: Attachment,
                        genericskillfile: Attachment, genericbucketfile: Attachment,
                        treasurefile: Attachment):

        msg = f"Rebuilding data..."
        await interaction.response.send_message(msg)
        baseclasses=None
        staticclasses=None
        buckets=None
        bucketskills=None
        classskills=None
        genericskills=None
        genericbuckets=None
        treasures=None
        if basefile.filename==PATH_BASE_CLASSES:
            baseclassesbytes=await basefile.read()
            baseclasses=json.loads(str(baseclassesbytes, 'utf-8'))
        else:
            await interaction.edit_original_response(f"Base Classes file not found or not named {PATH_BASE_CLASSES}")
            return

        if staticfile.filename==PATH_STATIC_CLASSES:
            staticclassesbytes=await staticfile.read()
            staticclasses=json.loads(str(staticclassesbytes, 'utf-8'))
        else:
            await interaction.edit_original_response(f"Static Classes file not found or not named {PATH_STATIC_CLASSES}")
            return
            
        if bucketsfile.filename==PATH_BUCKETS:
            bucketsbytes=await bucketsfile.read()
            buckets=json.loads(str(bucketsbytes, 'utf-8'))
        else:
            await interaction.edit_original_response(f"Buckets file not found or not named {PATH_BUCKETS}")
            return
        if bucketskillsfile.filename==PATH_BUCKET_SKILLS:
            bucketskillsbytes=await bucketskillsfile.read()
            bucketskills=json.loads(str(bucketskillsbytes, 'utf-8'))
        else:
            await interaction.edit_original_response(f"Bucket Skills file not found or not named {PATH_BUCKET_SKILLS}")
            return
        if classskillfile.filename==PATH_CLASS_SKILLS:
            classskillsbytes=await classskillfile.read()
            classskills=json.loads(str(classskillsbytes, 'utf-8'))
        else:
            await interaction.edit_original_response(f"Class Skills file not found or not named {PATH_CLASS_SKILLS}")
            return
        if genericskillfile.filename==PATH_GENERIC_SKILLS:
            genericskillsbytes=await genericskillfile.read()
            genericskills=json.loads(str(genericskillsbytes, 'utf-8'))
        else:
            await interaction.edit_original_response(f"Generic Skills file not found or not named {PATH_GENERIC_SKILLS}")
            return
        if genericbucketfile.filename==PATH_GENERIC_BUCKETS:
            genericbucketsbytes=await genericbucketfile.read()
            genericbuckets=json.loads(str(genericbucketsbytes, 'utf-8'))
        else:
            await interaction.edit_original_response(f"Generic Buckets file not found or not named {PATH_GENERIC_BUCKETS}")
            return
        if treasurefile.filename==PATH_TREASURES:
            treasuresbytes=await treasurefile.read()
            treasures=json.loads(str(treasuresbytes, 'utf-8'))
        else:
            await interaction.edit_original_response(f"Treasures file not found or not named {PATH_TREASURES}")
            return

        await interaction.edit_original_response(content=msg)

        if not await db_build.build_base_classes(baseclasses):
            raise kdr_errors.BuildDBDataError("Base Classes")
        msg += "\n*Built Base Classes*"
        await interaction.edit_original_response(content=msg)

        if not await db_build.build_static_classes(staticclasses):
            raise kdr_errors.BuildDBDataError("Static Classes")
        msg += "\n*Built Static Classes*"
        await interaction.edit_original_response(content=msg)

        if not await db_build.build_buckets(buckets):
            raise kdr_errors.BuildDBDataError("Buckets")
        msg += "\n*Built Buckets*"
        await interaction.edit_original_response(content=msg)

        if not await db_build.build_generic_buckets(genericbuckets):
            raise kdr_errors.BuildDBDataError("Generic Buckets")
        msg += "\n*Built Generic Buckets*"
        await interaction.edit_original_response(content=msg)

        if not await db_build.build_skills(bucketskills, classskills, genericskills):
            raise kdr_errors.BuildDBDataError("Skills")
        msg += "\n*Built Skills*"
        await interaction.edit_original_response(content=msg)

        if not await db_build.build_treasures(treasures):
            raise kdr_errors.BuildDBDataError("Treasures")
        msg += "\n*Built Treasures*"
        await interaction.edit_original_response(content=msg)

        msg += "\nFinished Building Data."
        await interaction.edit_original_response(content=msg)

    """ Admin Reset KDR PLAYERS"""

    @app_commands.command(name="resetplayers",
                          description="CAUTION. Resets ALL KDR player data in the database. ALL OF IT WILL BE LOST")
    @app_commands.guild_only()
    @app_commands.check(statics.server_whitelisted)
    @app_commands.checks.has_any_role(ROLE_CODER, ROLE_OWNER)
    async def reset_kdr_player_data(self, interaction=Interaction):
        await db.clear_user_data()
        await interaction.response.send_message("KDR Player Data has been reset.")

    """ Admin Join KDR Fake"""

    #@app_commands.command(name="joinfake", description="Joins an existing KDR match given the Instance ID.")
    #@app_commands.describe(iid="The Instance ID of the KDR.")
    #@app_commands.guild_only()
    #@app_commands.checks.has_role(ROLE_ADMIN)
    #@app_commands.check(statics.instance_not_started)
    #@app_commands.check(statics.instance_exists)
    #async def join_kdr_fake(self, interaction=Interaction, iid: str = "", name: str = ""):
    #    # return if no iid
    #    if len(iid) == 0 or len(name) == 0:
    #        return
#
    #    # locals
    #    choices = []
    #    pid = name
    #    sid = interaction.guild_id
    #    response = interaction.response
#
    #    # get instance
    #    instance = await db.get_instance(sid, iid)
#
    #    # return if instance full
    #    if instance.get("players") > instance.get("max_players"):
    #        await response.send_message(f"This KDR is already full.", ephemeral=True)
    #        return
#
    #    # generate classes
    #    choices = await statics.get_class_selection(sid, iid)
    #    if len(choices) == 0:
    #        await response.send_message(f'All classes have been offered.', ephemeral=True)
    #        return
#
    #    # mark if its users first game on server to send also a reminder to do /tutorial
    #    is_firstgame = False
    #    # check if user exists, and add
    #    if not db.check_user_exist(pid, sid):
    #        db.add_user_to_kdr(pid, sid, iid, choices)
    #        is_firstgame = True
    #    else:
    #        db.update_user_to_kdr(pid, sid, iid, choices)
#
    #    # check if last player
    #    if instance.get("players") == instance.get("max_players"):
    #        max_msg = f"<@{pid}> joined with {choices}.\nYou are the final player.\nThis match is ready to start."
    #        await response.send_message(max_msg)
    #        return
#
    #    await response.send_message(f"<@{pid}> joined the KDR {iid}!")
    #    if is_firstgame:
    #        await interaction.followup.send(kdr_messages.first_game_join(),
    #                                        ephemeral=True)


    """ Admin Kick Player """

    @app_commands.command(name="kickplayer", description="Kick a player from an active kdr.")
    @app_commands.guild_only()
    @app_commands.describe(iid="The Passcode of the KDR", player="The Player to Kick from the KDR")
    @app_commands.check(statics.instance_exists)
    async def kick_player(self, interaction=Interaction, iid: str = "", player: Member=None):
        # fetch data
        pid = str(interaction.user.id)
        sid = interaction.guild_id
        if iid=="":
            player_kdrs=await db.get_users_value(str(interaction.user.id),sid,"instances")
            if len(player_kdrs)==1:
                iid=player_kdrs[0]

        creatorid = await db.get_instance_value(sid, iid, 'creator_id')
        if str(creatorid)!=str(pid) and ROLE_ADMIN not in str(interaction.user.roles):
            await interaction.response.send_message(f"You cannot kick a player from a KDR you are not the owner of.",ephemeral=True)
            return

        if player is None:
            await interaction.response.send_message(f"Player to kick cannot be empty.",ephemeral=True)
            return
        pid=str(player.id)
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
        msg = f"<@{pid}> has been kicked from KDR Match {iid}.\n"

        await db.set_instance_value(sid, iid, 'players', num_players)
        await db.set_instance_value(sid, iid, 'player_names', players)
        await db.set_instance_value(sid, iid, 'offered_classes', offered_classes)
        await db.set_users_value(pid, sid, 'instances', player_active_instances)
        if not instance_started:
            await db.delete_player_inventory(pid, sid, iid)
        else:
            msg += "They have forfeited any matches not yet started."
        await interaction.response.send_message(f'{msg}')


    """ Admin Force Join KDR to Player """

    @app_commands.command(name="forcejoin", description="Makes a player join an existing KDR given the Instance ID.")
    @app_commands.describe(iid="The Instance ID of the KDR.", player="The Player to Sign Up to the KDR")
    @app_commands.guild_only()
    @app_commands.checks.has_role(ROLE_ADMIN)
    @app_commands.check(statics.instance_not_started)
    @app_commands.check(statics.instance_exists)
    async def force_join_kdr(self, interaction=Interaction, iid: str = "", player: Member=None):
        # return if no iid
        if len(iid) == 0:
            return

        adminid=str(interaction.user.id)
        # locals
        choices = []
        sid = interaction.guild_id
        response = interaction.response
        pid=str(player.id)
        servername=interaction.guild.name

        # get instance
        instance = await db.get_instance(sid, iid)

        if len(instance.get("player_names"))>0 and (pid in instance.get("player_names")):
            await response.send_message(f"<@{pid}> is already in the KDR!.",ephemeral=True)
            return
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

        await response.send_message(f"<@{pid}> was added to the KDR {iid}!", ephemeral=True)
        await player.send(f"<@{adminid}> added you to KDR `{iid}` in the server `{servername}`.")
            
    """ Command Errors """

    @nextround.error
    @override_result.error
    @override_class.error
    @override_class_offer.error
    #@clear_chat.error
    @reset_kdr_data.error
    @reset_kdr_player_data.error
    @reset_kdrs.error
    @kick_player.error
    @force_join_kdr.error
    @override_shop_status.error
    @override_gold_value.error
    async def command_error(self, interaction, error):
        if isinstance(error, kdr_errors.InstanceDoesNotExistError):
            await interaction.response.send_message(f"{OOPS} KDR Instance {error} does not exist.", ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerNotInInstanceError):
            await interaction.response.send_message(f"{OOPS} You are not part of KDR Instance {error}", ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerAlreadyJoinedError):
            await interaction.response.send_message(f"{OOPS} You already joined KDR Instance {error}", ephemeral=True)
            return
        if isinstance(error, kdr_errors.InstanceStartedError):
            await interaction.response.send_message(f"{OOPS} {error} has already started.", ephemeral=True)
            return
        if isinstance(error, kdr_errors.InstanceNotStartedError):
            await interaction.response.send_message(f"{OOPS} {error} hasn't even started yet!", ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerHasClassAlreadyError):
            await interaction.response.send_message(f"{OOPS} You have already picked a class!", ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerNotInRoundError):
            await interaction.response.send_message(f"{OOPS} You are not playing in this round.", ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerHasNoClassError):
            await interaction.response.send_message(f"{OOPS} You have not picked a class yet.", ephemeral=True)
            return
        if isinstance(error, kdr_errors.PlayerHasNoCharacterSheetError):
            await interaction.response.send_message(
                f"{OOPS} You Have Not Setup your Character Sheet\'s Link, do so with `setclassheet`.", ephemeral=True)
            return
        if isinstance(error, kdr_errors.BuildDBDataError):
            await interaction.response.send_message(f"{OOPS} Building data: {error} failed.", ephemeral=True)
            return
        if isinstance(error, kdr_errors.ServerNotWhitelistedError):
            await interaction.response.send_message(f"{OOPS} This Server is not allowed to perform this Command!", ephemeral=True)
            return
        raise error


    @force_join_kdr.autocomplete('iid')
    @forceendround.autocomplete('iid')
    @override_class.autocomplete('iid')
    @override_class_offer.autocomplete('iid')
    @override_gold_value.autocomplete('iid')
    @override_shop_status.autocomplete('iid')
    @kick_player.autocomplete('iid')
    async def autocomplete_iid(self, interaction: Interaction, current: str):
        iid_list=await db.get_users_value(str(interaction.user.id),interaction.guild_id,"instances")
        final_iid_list=[app_commands.Choice(name=x,value=x) for x in iid_list]
        return final_iid_list
    

    @override_class.autocomplete('classname')
    async def autocomplete_class(self, interaction: Interaction, current: str):
        class_list=await db.get_all_static_classes()
        final_class_list=[app_commands.Choice(name=x["name"],value=x["name"]) for x in class_list]
        return final_class_list

async def setup(bot: Bot) -> None:
    await bot.add_cog(KDRAdmin(bot))
