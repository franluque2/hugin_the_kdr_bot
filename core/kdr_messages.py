from config.config import DEFAULT_ELO_RANKING, RPG_STATS


""" First Game Join Message """


def first_game_join():
    msg = f"This seems to be your first KDR in this server! " \
          f"If you do not know how to play, you can run the `tutorial` command"

    return msg


""""""

""" First Game Join Message """


def current_match(match: dict):
    player_stats_str = " ".join([f"{stat}: {match.get(f'pl_{stat.lower()}', 0)}" for stat in RPG_STATS])
    opponent_stats_str = " ".join([f"{stat}: {match.get(f'opp_{stat.lower()}', 0)}" for stat in RPG_STATS])

    description = (f"<@{match['pl_id']}> ({match['pl_class_name']}) vs <@{match['opp_id']}> ({match['opp_class_name']})\n\n"
                   f"Round {match['active_round'] + 1} of {match['max_round']}\n\n"
                   f"Your Data:\n"
                   f"{player_stats_str}\n"
                   f"Gold: {match['pl_gold']}\n"
                   f"XP: {match['pl_xp']}\n"
                   f"Wins/Losses: {match['pl_wl_ratio'][0]}W / {match['pl_wl_ratio'][1]}L\n"
                   f"Total W/L: {match['pl_total_wl'][0]}W / {match['pl_total_wl'][1]}L\n")

    if match["pl_loss_streak"] != 0:
        description += f"Current Loss Streak: {match['pl_loss_streak']}\n"
    if match["pl_elo"] != DEFAULT_ELO_RANKING and match["is_ranked"]:
        description += f"Elo Rating: {int(match['pl_elo'])}\n"
    
    description += f"Character Sheet: {match['pl_sheet_url']}\n\n"

    description += (f"Opponent Data:\n"
                    f"{opponent_stats_str}\n"
                    f"Gold: {match['opp_gold']}\n"
                    f"XP: {match['opp_xp']}\n"
                    f"Wins/Losses: {match['opp_wl_ratio'][0]}W / {match['opp_wl_ratio'][1]}L\n"
                    f"Total W/L: {match['opp_total_wl'][0]}W / {match['opp_total_wl'][1]}L\n")

    if match["opp_loss_streak"] != 0:
        description += f"Current Loss Streak: {match['opp_loss_streak']}\n"
    if match["opp_elo"] != DEFAULT_ELO_RANKING and match["is_ranked"]:
        description += f"Elo Rating: {int(match['opp_elo'])}\n"
    
    description += f"Character Sheet: {match['opp_sheet_url']}\n"

    return description


""""""
