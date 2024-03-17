from random import shuffle
from discord import Message, Thread
from core import kdr_db as db
from views.panels.panel_status import StatusPanel
from core.kdr_data import SpecialSkillHandling, SpecialClassHandling, SpecialSkillNames
from views.view_tips import TipView
from views.view_gambler_gamble import GambleView
from views.panels.panel_end_shop_phase import EndShopPanel
from views.panels.panel_pick_class_skill import PickClassSkillPanel
import random


class TipPanel:
    def __init__(self, pid, sid, iid, status_message: Message, status_panel_generator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.status_message = status_message
        self.status_panel_generator = status_panel_generator
        self.thread = thread

    async def get_tip_panel(self) -> None:

        player_data = await db.get_inventory(self.pid, self.sid, self.iid)
        treasures = player_data["treasures"]
        player_gold = player_data["gold"]
        skills = player_data["skills"]
        tipval = player_data["tip_threshold"]
        total_tips = player_data["total_tips"]
        got_tip_skill = player_data["got_tip_skill"]

        can_sell = len(treasures) > 0
        for skill in skills:
            skill_data = await db.get_skill_by_id(skill)
            if skill_data["is_sellable"]:
                can_sell = True


        if SpecialClassHandling.CLASS_GAMBLER.value in player_data["modifiers"]:
            if total_tips < 3:
                gamble_view = GambleView()
                await gamble_view.create_buttons(self.pid, self.sid, self.iid,
                                                 self.status_message, self.status_panel_generator, self.thread, tipval,
                                                 total_tips,
                                                 can_sell, player_gold, 1, (total_tips+1) * 10, self)
                await self.thread.send(f"It's Time to Gamble Mr Gambler! You are Right now at Stage {total_tips}, you may bet any amount between **1** and {(total_tips+1)*10} to gamble on a roll, if it falls below what you bet you "

                                        f"will get your next skill!\n Also, as an incentive to gamble irresponsibly, if you bet half or less of what you would've needed to guarantee it (*{(total_tips+1)*10}*), you will get twice your gold back!",
                                       view=gamble_view)
                return

            await self.thread.send(f"You have gambled all you could Mr. Gambler! Your Luck is Legendary!")
            ender = EndShopPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                 self.thread)
            ender.get_end_shop_panel()
            return

        if got_tip_skill:
            await self.thread.send(f"You have already covered your tip quota! Thanks for your Patronage.")
            ender = EndShopPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                 self.thread)
            await ender.get_end_shop_panel()
            return

        if SpecialSkillHandling.SKILL_SUPER_SMOOTH_TALKER.value in player_data["modifiers"]:
            tipval -= 10
            tipval = tipval if tipval >= 0 else 0
            player_data["modifiers"].remove(SpecialSkillHandling.SKILL_SUPER_SMOOTH_TALKER.value)
            await db.set_inventory_value(self.pid, self.sid, self.iid, "tip_threshold", tipval)
            await db.set_inventory_value(self.pid, self.sid, self.iid, "modifiers", player_data["modifiers"])

        if (total_tips >= tipval):
            skillselector = PickClassSkillPanel(self.pid, self.sid, self.iid, self.status_message,
                                                self.status_panel_generator, self.thread)
            await skillselector.get_pick_class_skill_panel()
            return

        min_tip, max_tip = await db.get_static_class_value(player_data["class"], "tip_ratio")
        if SpecialSkillNames.SKILL_SUPER_SMOOTH_TALKER.value in player_data["skills"]:
            max_tip -= 10
            max_tip = max_tip if max_tip >= 0 else 0
            min_tip=max_tip if min_tip>max_tip else min_tip
            
        if (max_tip-total_tips)>=25 and min_tip>player_gold:
            await self.thread.send(f"You do not have enough gold to tip.")
            ender = EndShopPanel(self.pid, self.sid, self.iid, self.status_message, self.status_panel_generator,
                                 self.thread)
            await ender.get_end_shop_panel()
            return
        msg = get_tip_beg(total_tips, min_tip, max_tip)
        tips_view = TipView()
        await tips_view.create_buttons(self.pid, self.sid, self.iid,
                                       self.status_message, self.status_panel_generator, self.thread, tipval,
                                       total_tips,
                                       can_sell, player_gold, min_tip, max_tip, self)
        await self.thread.send(msg, view=tips_view)
        return


def get_tip_beg(tips_sofar: int, min_tip: int, max_tip: int) -> str:
    randchoice = random.randint(1, 9)

    if randchoice == 1:
        return (
            f"Times are tough here in the Extra Monster Zone, spare some change? So far you've tipped {tips_sofar}, "
            f"to get your class skill you would need to tip between **{min_tip}** and **{max_tip}** in total *({max_tip - tips_sofar} to guarantee it)*")
    if randchoice == 2:
        return (
            f"My Family abandoned me and my brothers due to not being \"real fusions\", and I need a bit of liquidity, mind providing some? So far you've tipped {tips_sofar}, "
            f"to get your class skill you would need to tip between **{min_tip}** and **{max_tip}** in total *({max_tip - tips_sofar} to guarantee it)*")
    if randchoice == 3:
        return (
            f"I did not know the King in Tyrant's Tirade had that history around him when we partnered up, mind helping me cover legal fees in the current lawsuit? So far you've tipped {tips_sofar}, "
            f"to get your class skill you would need to tip between **{min_tip}** and **{max_tip}** in total *({max_tip - tips_sofar} to guarantee it)*")
    if randchoice == 4:
        return (
            f"We are holding a memorial for Toad in the East, mind collaborating with a small donation? So far you've tipped {tips_sofar}, "
            f"to get your class skill you would need to tip between **{min_tip}** and **{max_tip}** in total *({max_tip - tips_sofar} to guarantee it)*")
    if randchoice == 5:
        return (
            f"Folgo and Rex ran away with all our advantage, figures thats what happens when you hire pirates. Wanna pitch in in hiring an investigator to track them? So far you've tipped {tips_sofar}, "
            f"to get your class skill you would need to tip between **{min_tip}** and **{max_tip}** in total *({max_tip - tips_sofar} to guarantee it)*")
    if randchoice == 6:
        return (
            f"I spent all my gems on Endymion and Dinomorphia in MD and then they released me costing a million gems. Could you help me with a donation to craft myself? So far you've tipped {tips_sofar}, "
            f"to get your class skill you would need to tip between **{min_tip}** and **{max_tip}** in total *({max_tip - tips_sofar} to guarantee it)*")
    if randchoice == 7:
        return (
            f"I saw a Naturia Beast the other day, I've reconsidered my position on nature. Want to help hire some hunters? So far you've tipped {tips_sofar}, "
            f"to get your class skill you would need to tip between **{min_tip}** and **{max_tip}** in total *({max_tip - tips_sofar} to guarantee it)*")
    if randchoice == 8:
        return (
            f"There is an Eradicator Epidemic Virus going around, but protection is expensive. Can you help your local spell deck with a donation to buy some? So far you've tipped {tips_sofar}, "
            f"to get your class skill you would need to tip between **{min_tip}** and **{max_tip}** in total *({max_tip - tips_sofar} to guarantee it)*")
    if randchoice == 9:
        return (
            f"Currently dealing with some pretty heavy emotional baggage from a small fight I had with Gigantic, I could use for a trip to the outdoors. Mind helping cover some of the costs? So far you've tipped {tips_sofar}, "
            f"to get your class skill you would need to tip between **{min_tip}** and **{max_tip}** in total *({max_tip - tips_sofar} to guarantee it)*")
