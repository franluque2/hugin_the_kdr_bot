from random import shuffle
from discord import Message, Thread, Embed
from core import kdr_db as db
from views.panels.panel_status import StatusPanel
import views.view_skill_class_select as skillselectview
import core.kdr_ansi as ansi


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
        embeds = []
        class_name = await db.get_inventory_value(self.pid, self.sid, self.iid, "class")
        class_skills_ids = list(await db.get_static_class_value(class_name, "unique_skills"))

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
                skill_img = skill.get("img_url", "")

                ansi_desc = ansi.wrap_ansi(f"{ansi.pink(skill_name, b=True)}\n{ansi.white(skill_desc)}")
                new_embed = Embed(title="CLASS SKILL OFFERED", description=ansi_desc)
                if skill_img:
                    new_embed.set_thumbnail(url=skill_img)
                embeds.append(new_embed)

            if len(skill_choices) >= 3:
                break
        await skill_view.create_buttons(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                        self.thread, skill_choices)
        
        await self.thread.send(embeds=embeds, view=skill_view)
