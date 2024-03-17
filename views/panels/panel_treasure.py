from discord import Message, Thread, Embed
from views.panels.panel_status import StatusPanel
from core import kdr_db as db
from core.kdr_data import SpecialSkillHandling, SpecialClassHandling, rarity_converter
from views.view_treasures import TreasureView
from views.panels.panel_buying import BuyPanel
from views.panels.shopkeeper_intro_panel import ShopIntroPanel
import random


class TreasurePanel():
    def __init__(self, pid, iid, sid, statusmessage: Message, statuspanelgenerator: StatusPanel,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.statusmessage = statusmessage
        self.statuspanelgenerator = statuspanelgenerator
        self.thread = thread

    async def get_treasure_panel(self) -> None:

        player_data = await db.get_inventory(self.pid, self.sid, self.iid)
        playermodifiers = player_data["modifiers"]
        offered_treasure = player_data["offered_treasure"]
        shop_stage = player_data["shop_stage"]

        if len(offered_treasure) == 0:
            offered_treasure = await get_random_treasures()
            await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_treasure", offered_treasure)

        treasuresgivenout = False

        # treasures = generate_treasures()
        for modifier in playermodifiers:
            if modifier == SpecialSkillHandling.SKILL_PIRATE_SOUL.value:
                # give all three treasures
                treasuresgivenout = True
                msg = "__**Yarr, yer a Pirate Laddie! Ye get all these treasures!**__:\n"
                embeds=[]
                for treasure in offered_treasure:
                    treasure_name = treasure["name"]
                    treasure_image = treasure["img_url"]
                    rarity=rarity_converter[treasure["rarity"]]
                    treasure_rarity=f"Rarity: {rarity}"
                    new_embed=Embed(title=treasure_name,description=treasure_rarity)
                    new_embed.set_thumbnail(url=treasure_image)
                    embeds.append(new_embed)
                    await db.set_inventory_value(self.pid, self.sid, self.iid, "treasures", treasure["id"], "$push")


                await self.thread.send(content=msg,embeds=embeds)
                shop_stage += 1
                await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', shop_stage)
                await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_treasure", [])
                shopintro=ShopIntroPanel(self.pid,self.sid,self.iid,self.thread)
                await shopintro.get_shop_intro()
                
                buyscreen = BuyPanel(self.pid, self.sid, self.iid, self.statusmessage, self.statuspanelgenerator,
                                     self.thread)
                await buyscreen.get_buy_panel()

        if not treasuresgivenout and (SpecialClassHandling.CLASS_PIRATE.value in playermodifiers):
            # give all three treasures
            treasuresgivenout = True

            msg = "__**Yarr, yer a Pirate Laddie! Ye get all these treasures!**__:\n"
            embeds=[]
            for treasure in offered_treasure:
                treasure_name = treasure["name"]
                treasure_image = treasure["img_url"]
                rarity=rarity_converter[treasure["rarity"]]
                treasure_rarity=f"Rarity: {rarity}"
                new_embed=Embed(title=treasure_name,description=treasure_rarity)
                new_embed.set_thumbnail(url=treasure_image)
                embeds.append(new_embed)
                await db.set_inventory_value(self.pid, self.sid, self.iid, "treasures", treasure["id"], "$push")


            await self.thread.send(content=msg,embeds=embeds)

            shop_stage += 1
            await db.set_inventory_value(self.pid, self.sid, self.iid, 'shop_stage', shop_stage)
            await db.set_inventory_value(self.pid, self.sid, self.iid, "offered_treasure", [])
            shopintro=ShopIntroPanel(self.pid,self.sid,self.iid,self.thread)
            await shopintro.get_shop_intro()
            buyscreen = BuyPanel(self.pid, self.sid, self.iid, self.statusmessage, self.statuspanelgenerator,
                                 self.thread)
            await buyscreen.get_buy_panel()

        if (not treasuresgivenout):
            treasurer = TreasureView()
            await treasurer.create_buttons(self.pid, self.sid, self.iid, self.statusmessage,
                                           self.statuspanelgenerator, self.thread, offered_treasure)
            msg = "__**Pick one Treasure!**__:\n"
            embeds=[]
            for treasure in offered_treasure:
                treasure_name = treasure["name"]
                treasure_image = treasure["img_url"]
                rarity=rarity_converter[treasure["rarity"]]
                treasure_rarity=f"Rarity: {rarity}"
                new_embed=Embed(title=treasure_name,description=treasure_rarity)
                new_embed.set_thumbnail(url=treasure_image)
                embeds.append(new_embed)
                
            await self.thread.send(content=msg, view=treasurer,embeds=embeds)


async def get_random_treasures():
    treasures = []
    chances = []
    common_treasures = await db.get_treasures_by_rarity("common")
    rare_treasures = await db.get_treasures_by_rarity("rare")
    super_rare_treasures = await db.get_treasures_by_rarity("super_rare")
    ultra_rare_treasures = await db.get_treasures_by_rarity("ultra_rare")

    for i in common_treasures:
        treasures.append(i)
        chances.append(8)

    for i in rare_treasures:
        treasures.append(i)
        chances.append(4)

    for i in super_rare_treasures:
        treasures.append(i)
        chances.append(2)

    for i in ultra_rare_treasures:
        treasures.append(i)
        chances.append(1)
    restreasures=[]
    for i in range(3):
        newtreasure=random.choices(population=treasures,weights=chances,k=1)
        while newtreasure[0] in restreasures:
            newtreasure=random.choices(population=treasures,weights=chances,k=1)
        restreasures.append(newtreasure[0])
    return restreasures
