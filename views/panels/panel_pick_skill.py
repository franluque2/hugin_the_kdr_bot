from random import shuffle
from discord import Message, Thread, Embed
from core import kdr_db as db
from core.kdr_modifiers import get_modifier
from views.panels.panel_status import StatusPanel
from views.view_skill_select import SkillSelectView
from core.kdr_data import KdrModifierNames, SpecialSkillHandling
from config.config import LEVEL_THRESHOLDS, GOLD_PER_XP
import views.panels.panel_training as panel_training


class PickSkillPanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_pick_skill_panel(self) -> None:

        special_flags = (await db.get_inventory_value(self.pid, self.sid, self.iid, "modifiers"))
        xp = await db.get_inventory_value(self.pid, self.sid, self.iid, "XP")
        playerskills = list(await db.get_inventory_value(self.pid, self.sid, self.iid, "skills"))
        gxp = GOLD_PER_XP
        modifiers=await db.get_instance_value(self.sid, self.iid, "modifiers")

        treasures = list(await db.get_inventory_value(self.pid, self.sid, self.iid, "treasures"))
        if SpecialSkillHandling.SKILL_SILVER_TONGUE.value in special_flags:
            gxp = GOLD_PER_XP - 1

        if xp in LEVEL_THRESHOLDS:
            skill_view = SkillSelectView(status_message=self.status_message,
                                         generator=self.status_panel_generator,
                                         timeout=5000)

            skill_choices = []
            offered_skills = await db.get_inventory_value(self.pid, self.sid, self.iid, 'offered_skills')
            msg = "__**Choose A Skill**__:\n"

            embeds=[]

            if len(offered_skills) == 0:
                if modifiers and get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value) is not None:
                    generic_skills = list(await db.get_all_generic_skills(get_modifier(modifiers,KdrModifierNames.ALTERNATE_FORMAT.value)))
                else:
                    generic_skills = list(await db.get_all_generic_skills())

                shuffle(generic_skills)
                for skill in generic_skills:
                    if playerskills.count(skill['id']) < skill['stackable_count']:
                        skill_choices.append(skill)
                        skill_name = skill['name']
                        skill_desc = skill['description']
                        skill_img = skill["img_url"]
                        new_embed=Embed(title=skill_name,description=skill_desc, type="rich")
                        new_embed.set_thumbnail(url=skill_img)
                        embeds.append(new_embed)


                    if len(skill_choices) >= 3:
                        await db.set_inventory_value(self.pid, self.sid, self.iid, 'offered_skills', skill_choices)
                        break
            else:
                skill_choices = offered_skills
                for skill in skill_choices:
                    skill_name = skill['name']
                    skill_desc = skill['description']
                    skill_img = skill["img_url"]
                    new_embed=Embed(title=skill_name,description=skill_desc,type="rich")
                    new_embed.set_thumbnail(url=skill_img)
                    embeds.append(new_embed)

            skill_upgrade_choices = []
            skill_upgrade_choices_with_dupes = []
            for skill in playerskills:
                skillval = await db.get_skill_by_id(skill)
                if playerskills.count(skill) < skillval['stackable_count']:
                    skill_upgrade_choices_with_dupes.append(skillval)
            [skill_upgrade_choices.append(x) for x in skill_upgrade_choices_with_dupes if
             x not in skill_upgrade_choices]
            can_sell = len(treasures) > 0
            for skill in playerskills:
                skill_data = await db.get_skill_by_id(skill)
                if skill_data["is_sellable"]:
                    can_sell = True
            await skill_view.create_buttons(self.pid, self.sid, self.iid,
                                            self.status_message, self.status_panel_generator, self.thread,
                                            skill_choices, skill_upgrade_choices, can_sell, gxp, self)
            await self.thread.send(msg, view=skill_view, embeds=embeds)
            return
        trainer = panel_training.TrainPanel(self.pid, self.sid,
                                            self.iid, self.status_message, self.status_panel_generator, self.thread)
        await trainer.get_train_panel()
