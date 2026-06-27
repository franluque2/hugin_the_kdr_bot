from random import shuffle
from discord import Message, Thread, Embed
from core import kdr_db as db
from views.panels.panel_status import StatusPanel
from core.kdr_data import SpecialClassHandling
from views.view_gambler_gamble import GambleView
from views.panels.panel_end_shop_phase import EndShopPanel
import random
import core.kdr_ansi as ansi

class GamblePanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_gamble_panel(self) -> None:
        player_data = await db.get_inventory(self.pid, self.sid, self.iid)
        treasures = player_data["treasures"]
        player_gold = player_data["gold"]
        skills = player_data["skills"]
        gamble_threshold = player_data["gamble_threshold"]
        gamble_count = player_data["gamble_count"]

        can_sell = len(treasures) > 0
        for skill in skills:
            skill_data = await db.get_skill_by_id(skill)
            if skill_data["is_sellable"]:
                can_sell = True

        if (SpecialClassHandling.CLASS_GAMBLER.value in player_data.get("modifiers", [])
                or player_data.get("class") == "gambler"):
            if gamble_count < 3:
                gamble_view = GambleView()
                await gamble_view.create_buttons(self.pid, self.sid, self.iid,
                                                 self.status_message, self.status_panel_generator, self.thread, gamble_threshold,
                                                 gamble_count,
                                                 can_sell, player_gold, 1, (gamble_count+1) * 10, self)
                description = (f"It's Time to Gamble Mr Gambler! You are Right now at Stage {gamble_count}, you may bet any amount between 1 and {(gamble_count+1)*10} to gamble on a roll, if it falls below what you bet you "
                               f"will get your next skill!\n\nAlso, as an incentive to gamble irresponsibly, if you bet half or less of what you would've needed to guarantee it ({(gamble_count+1)*10}), you will get twice your gold back!")
                await self.thread.send(description, view=gamble_view)
                return

            await self.thread.send("You have gambled all you could Mr. Gambler! Your Luck is Legendary!")
        else:
            await self.thread.send("Thanks for shopping!")

        ender = EndShopPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                             self.thread)
        await ender.get_end_shop_panel()
        return
