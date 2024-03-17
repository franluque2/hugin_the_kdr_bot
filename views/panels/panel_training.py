from discord import Message, Thread
from views.panels.panel_status import StatusPanel
from config.config import LEVEL_THRESHOLDS, GOLD_PER_XP, XP_PER_GOLD_SPENT
from core import kdr_db as db
from core.kdr_data import SpecialSkillHandling
import views.panels.panel_level_attribute as panel_level_attribute
from views.view_training import TrainingView


class TrainPanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_train_panel(self) -> None:
        # send to cog soon
        closestxpvalue = 0
        player_inventory = await db.get_inventory(self.pid, self.sid, self.iid)
        xp = player_inventory["XP"]
        playergold = player_inventory["gold"]
        modifiers = player_inventory["modifiers"]
        treasures = player_inventory["treasures"]
        skills = player_inventory["skills"]
        gxp = GOLD_PER_XP

        if SpecialSkillHandling.SKILL_SILVER_TONGUE.value in modifiers:
            gxp = gxp - 1

        for levelt in LEVEL_THRESHOLDS:  # 2 6 8 10
            if xp < levelt:
                closestxpvalue = levelt
                break

        can_sell = len(treasures) > 0
        for skill in skills:
            skill_data = await db.get_skill_by_id(skill)
            if skill_data["is_sellable"]:
                can_sell = True

        await db.set_inventory_value(self.pid, self.sid, self.iid, 'XP', xp)
        stage = await db.get_inventory_value(self.pid, self.sid, self.iid, 'shop_stage')
        stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', stage)

        can_train = (closestxpvalue - xp) / XP_PER_GOLD_SPENT <= (playergold / gxp)
        if (can_train) and xp < LEVEL_THRESHOLDS[-1]:
            gold_to_pay = ((closestxpvalue - xp) / XP_PER_GOLD_SPENT) * gxp

            # offer button to keep going to pay gold to reach next threshold
            train_view = TrainingView()
            await train_view.create_buttons(self.pid, self.sid, self.iid, self.status_message,
                                            self.status_panel_generator, self.thread,
                                            can_sell, can_train, gold_to_pay)
            await self.thread.send("Would you like to train?\n", view=train_view)
            return

        stage += 1
        await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', stage)

        leveler = panel_level_attribute.LevelAttributePanel(self.pid, self.sid, self.iid,
                                                            self.status_message, self.status_panel_generator,
                                                            self.thread)
        await leveler.get_level_attribute_panel()
