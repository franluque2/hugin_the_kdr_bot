from discord import Embed
from core import kdr_db as db
from config.config import GOLD_INTEREST_REQUIRED, GOLD_INTEREST_GAINED, LEVEL_THRESHOLDS
from core.kdr_modifiers import get_modifier
from core.kdr_data import KdrModifierNames
import math


class StatusPanel:
    def __init__(self, pid, iid, sid, pname):
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.playername = pname
        self.kdrname = None
        self.currround = None
        self.maxrounds = None
        self.currstr = None
        self.currdex = None
        self.currcon = None
        self.sheeturl = None
        self.classname = None
        self.classimg = None
        self.currgold = None
        self.currxp = None
        self.currlevel = None
        self.possible_interest = None

    async def get_message(self) -> Embed():
        await self.update_vals()
        title = f'Player Data for {self.playername} ({self.classname})'
        type = "rich"
        description = (f'You are Currently Level {self.currlevel+1} ({self.currxp} XP)\n'
                       f'Current Gold: {self.currgold}\n\n'
                       f'Your Sheet Link: [Character Sheet]({self.sheeturl})')
        ret_embed = Embed(title=title, type=type, description=description)
        ret_embed.set_thumbnail(url=self.classimg)
        ret_embed.add_field(name="Stats",
                            value=f'**STR**: {self.currstr}  **DEX**: {self.currdex}  **CON**: {self.currcon}')
        modifiers=await db.get_instance_value(self.sid,self.iid,"modifiers")
        if modifiers and (get_modifier(modifiers,KdrModifierNames.NO_INTEREST.value) is not None or get_modifier(modifiers,KdrModifierNames.LOSE_GOLD_AT_END.value) is not None):
            ret_embed.set_footer(text=f'You will gain no Interest at the end of the round.')
        else:    
            ret_embed.set_footer(text=f'Current Interest when the shop ends will be: {self.possible_interest}')
        return ret_embed

    async def update_vals(self):
        playerdata = await db.get_inventory(self.pid, self.sid, self.iid)

        classinfo = await db.get_static_class(playerdata["class"])

        playerlevel = 0

        playerxp = playerdata["XP"] if playerdata["XP"] <= LEVEL_THRESHOLDS[-1] else LEVEL_THRESHOLDS[-1]

        for level in LEVEL_THRESHOLDS:
            if playerxp >= level:
                playerlevel += 1

        self.kdrname = playerdata["id_player"]
        self.currround = (await db.get_instance_value(self.sid, self.iid, "active_round")) + 1
        self.maxrounds = len(list(await db.get_instance_value(self.sid, self.iid, "current_rounds")))
        self.currstr = playerdata["STR"]
        self.currdex = playerdata["DEX"]
        self.currcon = playerdata["CON"]
        self.sheeturl = playerdata["sheet_url"]
        self.classname = classinfo["name"]
        self.classimg = classinfo["url_picture"]
        self.currgold = int(playerdata["gold"])
        self.currxp = playerxp
        self.currlevel = playerlevel
        self.possible_interest = math.floor((playerdata[
                                          "gold"] / GOLD_INTEREST_REQUIRED) * GOLD_INTEREST_GAINED)
