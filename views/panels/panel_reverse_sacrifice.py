from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from core import kdr_db as db
from core.kdr_data import SpecialSkillHandling
import views.view_reverse_sacrifice as view_reverse_sacrifice
import random

class ReverseSacrificePanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_sacrifice_panel(self) -> None:
        # send to cog soon
        player_inventory = await db.get_inventory(self.pid, self.sid, self.iid)
        xp = player_inventory["XP"]
        modifiers = player_inventory["modifiers"]
        treasures = player_inventory["treasures"]
        skills = player_inventory["skills"]
        loot=player_inventory["loot"]

        loot_to_delete={}

        for i in range(3):
            loot_to_delete[i] = {}
            loot_to_delete[i]["name"] = i
            loot_to_delete[i]["id"] = i
            loot_to_delete[i]["buckets"] = await get_loot_to_sacrifice(self.pid, self.sid, self.iid)
            loot_to_delete[i]["skill"] = await get_skill_to_sacrifice(self.pid, self.sid, self.iid)
            loot_to_delete[i]["statdown"] = await get_stat_to_sacrifice(self.pid, self.sid, self.iid)



        reverse_sacrifice_view = view_reverse_sacrifice.ReverseSacrificeView()
        await reverse_sacrifice_view.create_buttons(self.pid, self.sid, self.iid, self.status_message,
                                        self.status_panel_generator, self.thread,loot_to_delete)
        await self.thread.send("To get to the next round, you must give up some of your inventory, choose one of the following:\n", view=reverse_sacrifice_view)
        

        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', 8)



async def get_loot_to_sacrifice(pid, sid, iid):
    buckets_taken = list(await db.get_inventory_value(pid, sid, iid, "loot"))
    returnbuckets = []

    ranchoices = random.sample(population=buckets_taken, k=4)

    for bucket in ranchoices:
        retbucket = await db.get_bucket(bucket)
        returnbuckets.append(retbucket)

    return returnbuckets

async def get_skill_to_sacrifice(pid, sid, iid):
    skills_taken = list(await db.get_inventory_value(pid, sid, iid, "skills"))
    ranchoices = random.choice(skills_taken)
    return ranchoices


async def get_stat_to_sacrifice(pid, sid, iid):
    STR = await db.get_inventory_value(pid, sid, iid, "STR")
    DEX = await db.get_inventory_value(pid, sid, iid, "DEX")
    CON = await db.get_inventory_value(pid, sid, iid, "CON")

    stats = []
    if STR >= 3:
        stats.append("STR")
    if DEX >= 3:
        stats.append("DEX")
    if CON >= 3:
        stats.append("CON")

    if stats:
        return random.choice(stats)
    return None