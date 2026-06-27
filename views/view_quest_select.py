import discord
import core.kdr_db as db
import random
from discord import Embed
from discord.ui.button import ButtonStyle
from config.config import QUESTS_TO_SHOW
from core.kdr_data import quest_type_weights
import core.kdr_ansi as ansi

class QuestButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, quest_info: dict, pid: str, sid, iid):
        super().__init__(label=label, custom_id=custom_id)
        self.quest_info = quest_info
        self.pid = pid
        self.sid = sid
        self.iid = iid

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.pid:
            await interaction.response.send_message("You are not the player picking a quest.", ephemeral=True)
            return

        await self.disable_view(interaction)
        
        # Save quest to player inventory
        quest_data = {
            "id": self.quest_info["id"],
            "name": self.quest_info["name"],
            "completed": False
        }
        await db.set_inventory_value(self.pid, self.sid, self.iid, "active_quest", quest_data)
        
        description = f"<@{self.pid}> has selected the quest: **{self.quest_info['name']}**!\nCheck your Quest status in your Shop panel."
        await interaction.response.send_message(description)
        
        # NEXT STEP: Pick starting loot (LowQualView)
        from views.view_class_select import LowSelectView
        lowselector = LowSelectView()
        # We need the player's class to get class-specific loot
        player_class = await db.get_inventory_value(self.pid, self.sid, self.iid, "class")
        await lowselector.create_low_view_picking(self.sid, self.iid, self.pid, player_class, interaction)

    async def disable_view(self, interaction: discord.Interaction):
        for button in self.view.children:
            if isinstance(button, discord.ui.Button):
                button.disabled = True
        self.style = ButtonStyle.primary
        await interaction.message.edit(content=interaction.message.content, view=self.view)
        self.view.stop()

class QuestSelectView(discord.ui.View):
    def __init__(self, *, timeout=1800):
        super().__init__(timeout=timeout)

    async def create_quest_view(self, sid, iid, pid, interaction):
        all_quests = await db.get_all_quests()
        if not all_quests:
            await interaction.followup.send("No quests available at this time.")
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.edit(archived=True, locked=True)
            return

        # Weighted random selection (with replacement, consistent odds per slot)
        num_to_show = min(QUESTS_TO_SHOW, len(all_quests))
        weights = [quest_type_weights.get(q.get("type", "regular"), 1) for q in all_quests]
        offered_quests = []
        seen_ids = set()
        for _ in range(num_to_show * 3):  # extra attempts to avoid dupes
            if len(offered_quests) >= num_to_show:
                break
            chosen = random.choices(all_quests, weights=weights, k=1)[0]
            if chosen["id"] not in seen_ids:
                seen_ids.add(chosen["id"])
                offered_quests.append(chosen)

        embeds = []
        # Header embed
        embeds.append(Embed(title="Pick a Quest", description="Complete this quest to earn special rewards!", color=discord.Color.blue()))
        
        for quest in offered_quests:
            rewards = quest.get("rewards", {})
            
            description_text = f"**Task:** {quest['description']}\n\n**REWARDS**\n"
            
            reward_items = []
            if "stats" in rewards:
                for stat, val in rewards["stats"].items():
                    reward_items.append(f"+{val} {stat.upper()}")
            
            if "gold" in rewards:
                reward_items.append(f"{rewards['gold']} Gold")
            
            skill_details = ""
            if "skills" in rewards:
                for skill_entry in rewards["skills"]:
                    if isinstance(skill_entry, dict):
                        skill_name = skill_entry.get("name", "Unknown")
                        skill_desc = skill_entry.get("description", "")
                        reward_items.append(f"Skill: {skill_name}")
                        skill_details += f"\n**{skill_name}**\n{skill_desc}\n"
                    else:
                        skill_info = await db.get_skill_by_id(skill_entry)
                        if skill_info:
                            reward_items.append(f"Skill: {skill_info['name']}")
                            desc = skill_info.get('description', 'No description') or 'No description available'
                            skill_details += f"\n**{skill_info['name']}**\n{desc}\n"

            card_details = ""
            if "cards" in rewards:
                for card_id in rewards["cards"]:
                    card_info = await db.get_treasure(card_id)
                    if card_info:
                        reward_items.append(f"Treasure: {card_info['name']}")
                        desc = card_info.get('description', 'No description') or 'No description available'
                        card_details += f"\n**{card_info['name']}**\n{desc}\n"

            description_text += " | ".join(reward_items)
            if skill_details or card_details:
                description_text += f"\n\n{skill_details}{card_details}"
            
            new_embed = Embed(title=quest['name'], description=description_text, color=discord.Color.teal())
            embeds.append(new_embed)
            
            button = QuestButton(label=quest["name"], custom_id=f"quest_{quest['id']}", quest_info=quest, pid=pid, sid=sid, iid=iid)
            self.add_item(button)

        await interaction.followup.send(embeds=embeds, view=self)
