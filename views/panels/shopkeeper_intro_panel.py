from discord import Message, Thread, Embed
from core import kdr_db as db
from config.shopkeepers import shopkeepers
import random
import numpy as np
import core.kdr_ansi as ansi

class ShopIntroPanel:
    def __init__(self, pid, sid, iid,
                 thread: Thread) -> None:
        self.pid = pid
        self.sid = sid
        self.iid = iid
        self.thread = thread

    async def get_shop_intro(self) -> None:
        shopname,greeting,greeting_loss,img_url=get_random_shopkeep()
        # Store the shopkeeper name for the web shop page
        await db.set_inventory_value(self.pid, self.sid, self.iid, "shopkeep_name", shopname)
        loss_streak=await db.get_inventory_value(self.pid,self.sid,self.iid,"loss_streak")
        text=greeting if loss_streak<2 else greeting_loss
        shopkeep=Embed(title=shopname,description=text)
        shopkeep.set_thumbnail(url=img_url)
        await self.thread.send(embed=shopkeep)
        return

def get_random_shopkeep():
    shopkeepers_to_shuffle=shopkeepers
    chances=[1/x["chance"] for x in shopkeepers_to_shuffle]
    chancesum=np.sum(chances)
    chances=[x/chancesum for x in chances]
    shopkeep=np.random.choice(a=shopkeepers_to_shuffle,p=chances,size=1).item(0)
    greetings=shopkeep["greetings"]
    greetings_loss_streak=shopkeep["greetings_loss_streak"]
    random.shuffle(greetings)
    random.shuffle(greetings_loss_streak)

    greeting=greetings[0]
    greeting_loss=greetings_loss_streak[0]
    return shopkeep["name"], greeting, greeting_loss, shopkeep["img_url"]

    