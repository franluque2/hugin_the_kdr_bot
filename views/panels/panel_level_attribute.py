from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from config.config import LEVEL_THRESHOLDS, MAX_RPG_STAT_LEVEL, RPG_STATS
from core import kdr_db as db
import views.panels.panel_treasure as panel_treasure
from views.view_increase_stat import IncreaseStatView
from core.kdr_data import KdrModifierNames
from core.kdr_modifiers import get_modifier


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
        losses = player_inventory["wl_ratio"][1]
        stage = player_inventory["shop_stage"]
        level = 0
        for threshold in LEVEL_THRESHOLDS:
            if xp >= threshold:
                level += 1

        # Gather all stat values dynamically
        stat_values = {stat: player_inventory.get(stat, 0) for stat in RPG_STATS}
        total_stats = sum(stat_values.values())

        modifiers = await db.get_instance_value(self.sid, self.iid, "modifiers")
        max_stat_level = max(RPG_STATS.values()) if RPG_STATS else MAX_RPG_STAT_LEVEL

        # Check if training is allowed and if any stat can be increased
        if not (modifiers and (get_modifier(modifiers, KdrModifierNames.NO_TRAINING.value) is not None)):
            if total_stats < level + wins + losses and not all(val == max_stat_level for val in stat_values.values()):
                increase_view = IncreaseStatView()
                # Pass stat values as keyword arguments
                await increase_view.create_buttons(
                    self.pid, self.sid, self.iid, self.status_message,
                    self.status_panel_generator, self.thread,
                    **{stat.lower(): val for stat, val in stat_values.items()}
                )
                # Build a dynamic stat display
                stat_display = "  ".join([f"**{stat}**: {val}" for stat, val in stat_values.items()])
                await self.thread.send(
                    f"Select a Stat to Level Up\n\nCurrent Stats: {stat_display}",
                    view=increase_view
                )
                return

        stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', stage)
        treasure_panel = panel_treasure.TreasurePanel(self.pid, self.iid, self.sid, self.status_message,
                                       self.status_panel_generator, self.thread)
        await treasure_panel.get_treasure_panel()
