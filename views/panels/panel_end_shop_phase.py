from random import shuffle
from discord import Message, Thread
from core import kdr_db as db
from views.panels.panel_status import StatusPanel
from core.kdr_data import SpecialSkillHandling
from config.config import GOLD_INTEREST_REQUIRED, GOLD_INTEREST_GAINED
import math


class EndShopPanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_end_shop_panel(self) -> None:
        playerdata = await db.get_inventory(self.pid, self.sid, self.iid)
        possible_interest = math.floor((playerdata[
                                     "gold"] / GOLD_INTEREST_REQUIRED)) * GOLD_INTEREST_GAINED

        stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', stage)

        await self.thread.send(
            f"And that is all for this Shop Phase! You will gain {possible_interest} Gold as interest on your gold at the start of the next shop phase")
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_phase', False)
        
        if isinstance(self.thread, Thread):
            await self.thread.edit(archived=True, locked=True)
