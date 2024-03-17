import discord
import core.kdr_db as db
import core.kdr_statics as statics
from discord.ui.button import ButtonStyle
from core.kdr_data import SpecialClassHandling, rarity_converter
import random
from views.panels.panel_treasure import get_random_treasures
from discord import Embed


class ClassButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, static_class_id: str, static_class_name: str, static_class_img_url: str, pid: str, sid, iid):
        super().__init__(label=label, custom_id=custom_id)
        self.static_class_id = static_class_id
        self.static_class_name = static_class_name
        self.static_class_img_url = static_class_img_url
        self.pid = pid
        self.sid = sid
        self.iid = iid

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message(f"You are not the player picking a class.", ephemeral=True)
            return
        await self.disable_view(interaction)
        embed=discord.Embed()
        if len(self.static_class_img_url)>0:
            embed.set_image(url=self.static_class_img_url)

        class_picked = await db.check_class_picked(self.sid, self.iid, self.static_class_id)

        if class_picked:
            await interaction.response.send_message(f"This subclass has already been picked.",ephemeral=True)
            return
        
        static_class_info=await db.get_static_class(self.static_class_id)
        if len(static_class_info["unique_effects"])>0:
            player_modifiers=await db.get_inventory_value(self.pid,self.sid,self.iid,"modifiers")
            player_modifiers.append(*static_class_info["unique_effects"])
            await db.set_inventory_value(self.pid,self.sid,self.iid,"modifiers",player_modifiers)
        
        generated_tip=random.randint(static_class_info["tip_ratio"][0],static_class_info["tip_ratio"][1])
        await db.set_inventory_value(self.pid,self.sid,self.iid,"tip_threshold",generated_tip)
        await interaction.response.send_message(f"<@{interaction.user.id}> selected: **{self.static_class_name}**, remember to make a copy of the sheet, and share the url (to view) with the `setclassheet` command!", embed=embed) #
        
        if SpecialClassHandling.CLASS_PIRATE.value in (static_class_info["unique_effects"]):
            msg = "__**Yarr, welcome to the KDR laddie! Ye get all these treasures!**__:\n"
            offered_treasure = await get_random_treasures()
            embeds=[]
            for treasure in offered_treasure:
                treasure_name = treasure["name"]
                treasure_image = treasure["img_url"]
                rarity=rarity_converter[treasure["rarity"]]
                treasure_rarity=f"Rarity: {rarity}"
                new_embed=Embed(title=treasure_name,description=treasure_rarity)
                new_embed.set_thumbnail(treasure_image)
                embeds.append(new_embed)
                await db.set_inventory_value(self.pid, self.sid, self.iid, "treasures", treasure["id"], "$push")

            await interaction.followup.send(content=msg,embeds=embeds)
        if isinstance(interaction.channel, discord.Thread):
            await interaction.channel.edit(archived=True, locked=True)
        await db.set_inventory_value(self.pid, self.sid, self.iid, "class", self.static_class_id)
        await db.set_instance_value(self.sid, self.iid, 'picked_classes', self.static_class_id, '$push')

       

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style=ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()


class ClassSelectView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_buttons(self, sid, iid, echos: list, pid):
        for c in echos:
            button = ClassButton(f'{c[1]}', f'{c[0]}', c[0], c[1], c[2], pid, sid, iid)
            ispicked= await db.check_class_picked(sid, iid, c[0])
            if ispicked:
                button.disabled = True
            self.add_item(button)

