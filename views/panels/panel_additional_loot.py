from random import shuffle
from discord import Message, Thread, Embed
from core import kdr_db as db
from views.panels.panel_status import StatusPanel
from core.kdr_data import SpecialTypeHandling
import random
import core.kdr_ansi as ansi


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
        ansi_lines = []
        if len(self.extra_loot)>0:
            ansi_lines.append(ansi.green("--- [ ADDITIONAL LOOT ] ---", b=True))
            for extraloot in self.extra_loot:
                for lootid in extraloot:
                    loot=await db.get_bucket(lootid)
                    if loot["cards"] is not None and len(loot["cards"])>0:
                        ansi_lines.append(ansi.cyan("--- [ CARDS ] ---", b=True))
                        ansi_lines.append(ansi.white(' / '.join(loot['cards'])))
                    if loot["skills"] is not None and len(loot["skills"])>0:
                        ansi_lines.append(ansi.yellow("--- [ SKILLS ] ---", b=True))
                        for skill in loot["skills"]:
                            skillinfo=await db.get_skill_by_id(skill)
                            name = skillinfo["name"]
                            desc = skillinfo.get("description", "No description") or "No description available"
                            ansi_lines.append(ansi.pink(name, b=True))
                            ansi_lines.append(ansi.white(desc))
                            await db.set_inventory_value(self.pid,self.sid,self.iid,"skills",skill,"$push")

        skillembeds=[]
        if self.extra_skills is not None and len(self.extra_skills)>0:
            for extraskills in self.extra_skills:
                for skillid in extraskills:
                    skill=await db.get_skill_by_id(skillid)
                    skillname=skill["name"]
                    skilldesc=skill.get("description", "No description")
                    skillimg=skill["img_url"]
                    if SpecialTypeHandling.GAMBLER_5050_SKILL.value in skill["special_code_flag"]:
                        if random.randint(1,2)==1:
                            ansi_lines.append(ansi.red(f"Sadly, you lost the coin toss for {skillname}.", b=True))
                            await db.set_inventory_value(self.pid,self.sid,self.iid,"skills",skillid,"$pull")
                        else:
                            skillembed=Embed(title=skillname, description=skilldesc)
                            skillembed.set_thumbnail(url=skillimg)
                            skillembeds.append(skillembed)
                    else:
                        skillembed=Embed(title=skillname, description=skilldesc)
                        skillembed.set_thumbnail(url=skillimg)
                        skillembeds.append(skillembed)
        
        if ansi_lines:
            await self.thread.send(content=ansi.wrap_ansi("\n".join(ansi_lines)), embeds=skillembeds)
        elif skillembeds:
            await self.thread.send(embeds=skillembeds)
        return
