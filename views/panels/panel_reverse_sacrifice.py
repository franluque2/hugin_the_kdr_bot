from discord import Message, Thread, Embed
from views.panels.panel_status import StatusPanel
from core import kdr_db as db
from core.kdr_data import SpecialSkillHandling
import views.view_reverse_sacrifice as view_reverse_sacrifice
from config.config import RPG_STATS
import random
import core.kdr_ansi as ansi

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

        loot_to_delete=[]

        for i in range(2):
            loot_to_delete.append({})
            loot_to_delete[i]["id"] = i
            loot_to_delete[i]["buckets"] = await get_loot_to_sacrifice(self.pid, self.sid, self.iid)
            loot_to_delete[i]["skill"] = await get_skill_to_sacrifice(self.pid, self.sid, self.iid)
            loot_to_delete[i]["statdown"] = await get_stat_to_sacrifice(self.pid, self.sid, self.iid)


        reverse_sacrifice_view = view_reverse_sacrifice.ReverseSacrificeView()
        embeds = []
        # Header embed
        embeds.append(Embed(title="Sacrifice Required", description="To get to the next round, you must give up some of your inventory. Choose one of the following:", color=discord.Color.red()))

        for window in loot_to_delete:
            ansi_lines = []
            if window["statdown"] is not None:
                ansi_lines.append(ansi.red(f"-3 {window['statdown'].upper()}", b=True))
            if window["skill"] is not None:
                skill = await db.get_skill_by_id(window["skill"])
                ansi_lines.append(ansi.yellow("--- [ SKILL TO LOSE ] ---", b=True))
                ansi_lines.append(ansi.pink(skill['name'], b=True))
                ansi_lines.append(ansi.white(skill['description']))

            for bucket in window["buckets"]:
                if bucket["cards"] is not None and len(bucket["cards"]) > 0:
                    ansi_lines.append(ansi.cyan("--- [ CARDS TO LOSE ] ---", b=True))
                    ansi_lines.append(ansi.white(' / '.join(bucket['cards'])))
                if bucket["skills"] is not None and len(bucket["skills"]) > 0:
                    ansi_lines.append(ansi.yellow("--- [ SKILLS TO LOSE ] ---", b=True))
                    for skill in bucket["skills"]:
                        skillinfo = await db.get_skill_by_id(skill)
                        name = skillinfo["name"]
                        desc = skillinfo.get("description", "No description") or "No description available"
                        ansi_lines.append(ansi.pink(name, b=True))
                        ansi_lines.append(ansi.white(desc))
            
            description_content = ansi.wrap_ansi("\n".join(ansi_lines))
            embeds.append(Embed(title=f"OPTION {window['id'] + 1}", description=description_content.strip(), color=discord.Color.orange()))
        
        await reverse_sacrifice_view.create_buttons(self.pid, self.sid, self.iid, self.status_message,
                                        self.status_panel_generator, self.thread,loot_to_delete)
        
        await self.thread.send(embeds=embeds, view=reverse_sacrifice_view)
        
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', 8)


def get_prioritized_sample(buckets_taken, low_qual, mid_qual, high_qual, k=4):
    high_candidates = [e for e in buckets_taken if e in high_qual]
    mid_candidates = [e for e in buckets_taken if e in mid_qual]
    low_candidates = [e for e in buckets_taken if e in low_qual]

    prioritized_groups = [high_candidates, mid_candidates, low_candidates]

    for group in prioritized_groups:
        if group:
            while True:
                ranchoices = random.sample(population=buckets_taken, k=k)
                if any(e in group for e in ranchoices):
                    return ranchoices
    return random.sample(population=buckets_taken, k=k)

async def get_loot_to_sacrifice(pid, sid, iid):
    buckets_taken = list(await db.get_inventory_value(pid, sid, iid, "loot"))
    returnbuckets = []
    playerclass=await db.get_inventory_value(pid, sid, iid, "class")
    cid = await db.get_static_class_value(playerclass, "base")
    buckets_taken = list(await db.get_inventory_value(pid, sid, iid, "loot"))
    possible_buckets_master = await db.get_base_class_value(cid, "bucket_list")
    classlowqual = list(possible_buckets_master["low_qual"])
    classmidqual = list(possible_buckets_master["mid_qual"])
    classhighqual = list(possible_buckets_master["high_qual"])

    ranchoices = get_prioritized_sample(buckets_taken, classlowqual, classmidqual,
                                        classhighqual, k=4)


    for bucket in ranchoices:
        retbucket = await db.get_bucket(bucket)
        returnbuckets.append(retbucket)

    return returnbuckets

async def get_skill_to_sacrifice(pid, sid, iid):
    skills_taken = list(await db.get_inventory_value(pid, sid, iid, "skills"))
    ranchoices = random.choice(skills_taken)
    return ranchoices


async def get_stat_to_sacrifice(pid, sid, iid):
    stats = []
    for stat in RPG_STATS:
        val = await db.get_inventory_value(pid, sid, iid, stat)
        if val is not None and val >= 3:
            stats.append(stat)
    if stats:
        return random.choice(stats)
    return None