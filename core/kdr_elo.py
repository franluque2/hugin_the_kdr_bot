from discord.ext.commands.cog import Cog
from discord.ext.commands.bot import Bot
from discord import app_commands
from discord import Interaction
from core.kdr_data import WinType

import core.kdr_statics as statics
import core.kdr_errors as kdr_errors
from core import kdr_db as db


class EloAdjustment:
    def __init__(self, k_factor=32):
        self.k_factor = k_factor

    def calculate_expected_score(self, rating_a, rating_b):
        expected_score_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
        expected_score_b = 1 - expected_score_a
        return expected_score_a, expected_score_b

    def update_ratings(self, rating_a, rating_b, outcome_a, outcome_b):
        expected_score_a, expected_score_b = self.calculate_expected_score(rating_a, rating_b)
        new_rating_a = rating_a + self.k_factor * (outcome_a - expected_score_a)
        new_rating_b = rating_b + self.k_factor * (outcome_b - expected_score_b)
        return new_rating_a, new_rating_b

    async def update_winloss(self, pid, sid, iid, won: bool = True):
        currwinloss = await db.get_inventory_value(pid, sid, iid, "wl_ratio")
        currwinloss[not won] += 1
        await db.set_inventory_value(pid, sid, iid, "wl_ratio", currwinloss)

        total_winloss = await db.get_users_value(pid, sid, 'total_winloss')
        total_winloss[not won] += 1

        await db.set_users_value(pid, sid, 'total_winloss', total_winloss)

    async def update_losstreak(self, pid, sid, iid, won: bool = True):
        losstreak = await db.get_inventory_value(pid, sid, iid, "loss_streak")
        if won:
            losstreak = 0
        else:
            losstreak += 1

        await db.set_inventory_value(pid, sid, iid, "loss_streak", losstreak)

    async def update_elo(self, pid, oppid, sid, matchresult_player_a_won: bool = True):
        pl_rating = await db.get_users_value(pid, sid, 'elo')
        opp_rating = await db.get_users_value(oppid, sid, 'elo')

        await db.set_users_value(pid, sid, 'previous_elo', pl_rating)
        await db.set_users_value(oppid, sid, 'previous_elo', opp_rating)

        pl_rating, opp_rating = self.update_ratings(pl_rating, opp_rating, matchresult_player_a_won,
                                                    not matchresult_player_a_won)
        await db.set_users_value(pid, sid, 'elo', pl_rating)
        await db.set_users_value(oppid, sid, 'elo', opp_rating)

    async def swap_last_elo(self, pid, oppid, sid, matchresult_player_a_won: bool = True):
        pl_rating = await db.get_users_value(pid, sid, 'previous_elo')
        opp_rating = await db.get_users_value(oppid, sid, 'previous_elo')

        pl_rating, opp_rating = self.update_ratings(pl_rating, opp_rating, matchresult_player_a_won,
                                                    not matchresult_player_a_won)
        await db.set_users_value(pid, sid, 'elo', pl_rating)
        await db.set_users_value(oppid, sid, 'elo', opp_rating)
