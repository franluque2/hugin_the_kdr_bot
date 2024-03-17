from random import shuffle
from discord import Message, Thread
from core import kdr_db as db
from views.panels.panel_status import StatusPanel
import views.view_skill_class_select as skillselectview


class PickClassSkillPanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_pick_class_skill_panel(self) -> None:

        skill_view = skillselectview.SkillClassSelectView(status_message=self.status_message,
                                                          generator=self.status_panel_generator,
                                                          timeout=5000)

        playerskills = await db.get_inventory_value(self.pid, self.sid, self.iid, "skills")

        skill_choices = []
        msg = "__**Choose A Unique Class Skill**__:\n"
        class_skills_ids = list(
            await db.get_static_class_value(await db.get_inventory_value(self.pid, self.sid, self.iid, "class"),
                                            "unique_skills"))

        class_skills = []
        for id in class_skills_ids:
            val = await db.get_skill_by_id(id)
            class_skills.append(val)
        shuffle(class_skills)
        for skill in class_skills:
            if playerskills.count(skill['id']) < skill['stackable_count']:
                skill_choices.append(skill)
                skill_name = skill['name']
                skill_desc = skill['description']

                msg += f"**{skill_name}**: {skill_desc}\n\n"
            if len(skill_choices) >= 3:
                break
        await skill_view.create_buttons(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                        self.thread, skill_choices)
        await self.thread.send(msg, view=skill_view)
