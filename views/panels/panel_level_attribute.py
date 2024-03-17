from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from config.config import LEVEL_THRESHOLDS, MAX_RPG_STAT_LEVEL
from core import kdr_db as db
import views.panels.panel_treasure as panel_treasure
from views.view_increase_stat import IncreaseStatView


class LevelAttributePanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_level_attribute_panel(self) -> None:

        player_inventory = await db.get_inventory(self.pid, self.sid, self.iid)
        xp = player_inventory["XP"]
        wins = player_inventory["wl_ratio"][0]
        losses=player_inventory["wl_ratio"][1]
        stage = player_inventory["shop_stage"]
        level = 0
        for threshold in LEVEL_THRESHOLDS:
            if xp >= threshold:
                level += 1

        STR = player_inventory["STR"]
        DEX = player_inventory["DEX"]
        CON = player_inventory["CON"]

        if STR + DEX + CON < level + wins + losses and not STR == DEX == CON == MAX_RPG_STAT_LEVEL:
            increase_view = IncreaseStatView()
            await increase_view.create_buttons(self.pid, self.sid, self.iid, self.status_message,
                                               self.status_panel_generator, self.thread, STR, DEX, CON)
            await self.thread.send(f"Select a Stat to Level Up\n\n"
                                   f"Current Stats: **STR**: {STR}  **DEX**: {DEX} **CON**: {CON}", view=increase_view)
            return

        stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', stage)
        treasure_panel = panel_treasure.TreasurePanel(self.pid, self.iid, self.sid, self.status_message,
                                       self.status_panel_generator, self.thread)
        await treasure_panel.get_treasure_panel()
