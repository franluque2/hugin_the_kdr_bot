from random import shuffle
from discord import Message, Thread, Embed
from core import kdr_db as db
from views.panels.panel_status import StatusPanel
from core.kdr_data import SpecialTypeHandling
import random


class AdditionalLootPanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread, extra_loot: list = [], extra_skills: list = []) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread
        self.extra_loot=extra_loot
        self.extra_skills=extra_skills

    async def get_additional_loot_panel(self) -> None:

        player_data = await db.get_inventory(self.pid, self.sid, self.iid)
        msg=""
        if len(self.extra_loot)>0:
            msg += f"You've gained the additional following loot:\n"
            for extraloot in self.extra_loot:
                for lootid in extraloot:
                    loot=await db.get_bucket(lootid)
                    if loot["cards"] is not None and len(loot["cards"])>0:
                        for card in loot["cards"][:-1]:
                            msg+=f"{card}, "
                        msg+=loot["cards"][-1]
            msg+="\n"
        skillembeds=[]
        if self.extra_skills is not None and len(self.extra_skills)>0:
            msg+="You've gained the additional following skill(s)\n"
            for extraskills in self.extra_skills:
                for skillid in extraskills:
                    skill=await db.get_skill(skillid)
                    skillname=skill["name"]
                    skilldesc=skill["description"]
                    skillimg=skill["img_url"]
                    if SpecialTypeHandling.GAMBLER_5050_SKILL.value in skill["special_code_flag"]:
                        if random.randint(1,2)==1:
                            msg+=f"Sadly, you lost the coin toss for {skillname}.\n"
                            await db.set_inventory_value(self.pid,self.sid,self.iid,"skills",skillid,"$pull")
                        else:
                            skillembed=Embed(title=skillname,description=skilldesc)
                            skillembed.set_thumbnail(url=skillimg)
                            skillembeds.append(skillembed)
                    else:
                        skillembed=Embed(title=skillname,description=skilldesc)
                        skillembed.set_thumbnail(url=skillimg)
                        skillembeds.append(skillembed)

        await self.thread.send(content=msg,embeds=skillembeds)
        return
