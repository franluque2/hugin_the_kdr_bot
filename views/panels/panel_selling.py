from random import shuffle
from discord import Message, Thread
from core import kdr_db as db
from views.panels.panel_status import StatusPanel
from core.kdr_data import SpecialSkillHandling, SpecialClassHandling, SpecialSkillNames
from views.view_sell_panel import SellView
import random


class SellPanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, original_panel) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.original_panel=original_panel

    async def get_sell_panel(self) -> None:

        player_data = await db.get_inventory(self.pid, self.sid, self.iid)
        ptreasures = player_data["treasures"]
        player_gold = player_data["gold"]
        skills = player_data["skills"]

        sellable_skills = []

        if not len(ptreasures)>0:
            ptreasures=[]
        treasures=[]
        for ptreasure in ptreasures:
            treasurename=await db.get_treasure_value(ptreasure,"name")
            if SpecialSkillHandling.SKILL_PLUNDERED_BOOTY.value in player_data["modifiers"]:
               treasures.append({"id":ptreasure,"name":treasurename,"sell_value":3})
            else:
                treasures.append({"id":ptreasure,"name":treasurename,"sell_value":1})

        can_sell = len(treasures) > 0
        for skill in skills:
            skill_data = await db.get_skill_by_id(skill)
            if skill_data["is_sellable"]:
                skill_data["sell_value"]=1
                can_sell = True
                sellable_skills.append(skill_data)

        msg = f"Selling, you currently have {player_gold} gold"
        seller=SellView()
        await seller.create_buttons(self.pid, self.sid, self.iid,
                                                  self.status_message, self.status_panel_generator, self.thread,
                                                  can_sell, player_gold, sellable_skills, treasures,self.original_panel)
        await self.thread.send(msg, view=seller)
        return
