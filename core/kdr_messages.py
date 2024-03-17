from config.config import DEFAULT_ELO_RANKING


""" First Game Join Message """


def first_game_join():
    msg = f"This seems to be your first KDR in this server! " \
          f"If you do not know how to play, you can run the `tutorial` command"

    return msg


""""""

""" First Game Join Message """


def current_match(match: dict):

    msg = (f'<@{match["pl_id"]}> ({match["pl_class_name"]}) you are facing against '
           f'<@{match["opp_id"]}> ({match["opp_class_name"]})\n\n'
           f'it is round {match["active_round"] + 1} out of {match["max_round"]} \n'
           f'Your Player Data:\n'
           f'**STR**: {match["pl_str"]} **CON**: {match["pl_con"]} **DEX**: {match["pl_dex"]}\n'
           f'Current Gold: {match["pl_gold"]}\n'
           f'Current XP: {match["pl_xp"]}\n'
           f'Current Wins and Losses: {match["pl_wl_ratio"][0]}W /{match["pl_wl_ratio"][1]}L\n'
           f'Total Wins and Losses: {match["pl_total_wl"][0]}W /{match["pl_total_wl"][1]}L\n')

    if match["pl_loss_streak"] != 0:
        msg += f'Current Loss Streak of {match["opp_loss_streak"]}\n'
    if match["pl_loss_streak"] != DEFAULT_ELO_RANKING and match["is_ranked"]:
        msg += f'Current Elo Rating: {int(match["pl_elo"])}\n'
    if len(match["pl_sheet_url"]) > 0:
        msg += f'Character Sheet Link: {match["pl_sheet_url"]}\n'
    else:
        msg += f'You Have Not Setup your Character Sheet\'s Link with `setclassheet`\n'

    msg += (f'Your Opponent <@{match["opp_id"]}>\'s Player Data:\n'
            f'**STR**: {match["opp_str"]} **CON**: {match["opp_con"]} **DEX**: {match["opp_dex"]}\n'
            f'Current Gold: {match["opp_gold"]}\n'
            f'Current XP: {match["opp_xp"]}\n'
            f'Current Wins and Losses: {match["opp_wl_ratio"][0]}W /{match["opp_wl_ratio"][1]}L\n'
            f'Total Wins and Losses: {match["opp_total_wl"][0]}W /{match["opp_total_wl"][1]}L\n')

    if match["opp_loss_streak"] != 0:
        msg += f'Current Loss Streak of {match["opp_loss_streak"]}\n'
    if match["opp_elo"] != DEFAULT_ELO_RANKING and match["is_ranked"]:
        msg += f'Current Elo Rating: {int(match["opp_elo"])}\n'
    if len(match["opp_sheet_url"]) > 0:
        msg += f'Character Sheet Link: {match["opp_sheet_url"]}\n'
    else:
        msg += f'Your Opponent has not setup their Character Sheet\'s Link with `setclassheet`\n'

    return msg


""""""
