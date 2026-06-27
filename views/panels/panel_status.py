from discord import Embed
from core import kdr_db as db
from core.kdr_web import get_inventory_url
from config.config import GOLD_INTEREST_REQUIRED, GOLD_INTEREST_GAINED, LEVEL_THRESHOLDS, RPG_STATS
from core.kdr_modifiers import get_modifier
from core.kdr_data import KdrModifierNames
import math
import core.kdr_ansi as ansi


class StatusPanel:
    def __init__(self, pid, iid, sid, pname):
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.playername = pname
        self.kdrname = None
        self.currround = None
        self.maxrounds = None
        self.sheeturl = None
        self.classname = None
        self.classimg = None
        self.currgold = None
        self.currxp = None
        self.currlevel = None
        self.possible_interest = None
        self.stats = {}  # Store all stats here

    async def get_message(self) -> Embed:
        await self.update_vals()
        title = f"Player Data: {self.playername}"
        
        if not self.classname:
            return Embed(title=title, description="No inventory data found for this player in this KDR.")

        # Build stats string dynamically
        stats_str = "  ".join([f"{stat}: {self.stats.get(stat, 0)}" for stat in RPG_STATS])
        
        description = (f"Class: {self.classname}\n"
                       f"Level: {self.currlevel+1} ({self.currxp} XP)\n"
                       f"Gold: {self.currgold}\n\n"
                       f"--- Stats ---\n"
                       f"{stats_str}\n")
        
        description += f"\nCharacter Sheet: {self.sheeturl}"
        
        ret_embed = Embed(title=title, description=description)
        ret_embed.set_thumbnail(url=self.classimg)
        
        modifiers = await db.get_instance_value(self.sid, self.iid, "modifiers")
        if modifiers and (get_modifier(modifiers, KdrModifierNames.NO_INTEREST.value) is not None or get_modifier(modifiers, KdrModifierNames.LOSE_GOLD_AT_END.value) is not None):
            ret_embed.set_footer(text="No Interest gain at end of round.")
        else:
            ret_embed.set_footer(text=f"Interest when the shop ends will be: {self.possible_interest}")
        return ret_embed

    async def update_vals(self):
        playerdata = await db.get_inventory(self.pid, self.sid, self.iid)
        if not playerdata:
            return

        classinfo = await db.get_static_class(playerdata["class"])
        playerlevel = 0
        playerxp = playerdata["XP"] if playerdata["XP"] <= LEVEL_THRESHOLDS[-1] else LEVEL_THRESHOLDS[-1]
        for level in LEVEL_THRESHOLDS:
            if playerxp >= level:
                playerlevel += 1

        self.kdrname = playerdata["id_player"]
        self.currround = (await db.get_instance_value(self.sid, self.iid, "active_round")) + 1
        self.maxrounds = len(list(await db.get_instance_value(self.sid, self.iid, "current_rounds")))
        # Gather all stats dynamically
        self.stats = {stat: playerdata.get(stat, 0) for stat in RPG_STATS}
        self.sheeturl = get_inventory_url(self.sid, self.iid, self.pid)
        self.classname = classinfo["name"]
        self.classimg = classinfo["url_picture"]
        self.currgold = int(playerdata["gold"])
        self.currxp = playerxp
        self.currlevel = playerlevel
        self.possible_interest = math.floor((playerdata["gold"] / GOLD_INTEREST_REQUIRED) * GOLD_INTEREST_GAINED)
