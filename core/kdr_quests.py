import core.kdr_db as db
from config.config import RPG_STATS
import random
from core.kdr_data import categories_buckets_generic, categories_buckets_class

async def give_quest_rewards(pid, sid, iid, quest_info):
    rewards = quest_info.get("rewards", {})
    reward_msg = ""
    
    # 1. Stats
    if "stats" in rewards:
        for stat, val in rewards["stats"].items():
            stat_key = stat.upper()
            if stat_key in RPG_STATS:
                current_val = await db.get_inventory_value(pid, sid, iid, stat_key)
                new_val = min(current_val + val, RPG_STATS[stat_key])
                await db.set_inventory_value(pid, sid, iid, stat_key, new_val)
                reward_msg += f"- +{val} {stat_key}\n"
                reward_msg += f"- +{val} {stat}\n"
    
    # 2. Gold
    if "gold" in rewards:
        current_gold = await db.get_inventory_value(pid, sid, iid, "gold")
        await db.set_inventory_value(pid, sid, iid, "gold", current_gold + rewards["gold"])
        reward_msg += f"- {rewards['gold']} Gold\n"
        
    # 3. Skills (existing IDs + inline new skills)
    if "skills" in rewards:
        for skill_entry in rewards["skills"]:
            if isinstance(skill_entry, dict):
                # Inline new skill: {"name": "...", "description": "..."}
                skill_id = skill_entry["name"].lower().replace(" ", "_").replace("'", "")
                # Give the skill directly (no DB entry needed — store in inventory)
                await db.set_inventory_value(pid, sid, iid, 'skills', skill_id, operation="$push")
                reward_msg += f"- Skill: {skill_entry['name']}\n"
            else:
                # Existing skill ID string
                skillinfo = await db.get_skill_by_id(skill_entry)
                if skillinfo:
                    await db.set_inventory_value(pid, sid, iid, 'skills', skillinfo['id'], operation="$push")
                    if skillinfo["special_code_flag"] != -1:
                        if hasattr(skillinfo["special_code_flag"], "__len__"):
                            for skill_flag in skillinfo["special_code_flag"]:
                                await db.set_inventory_value(pid, sid, iid, 'modifiers', skill_flag, operation="$push")
                        else:
                            await db.set_inventory_value(pid, sid, iid, 'modifiers', skillinfo['special_code_flag'], operation="$push")
                    reward_msg += f"- Skill: {skillinfo['name']}\n"

    # 4. Random Skill
    if rewards.get("random_skill"):
        all_skills = list(await db.get_all_generic_skills())
        if all_skills:
            skill = random.choice(all_skills)
            await db.set_inventory_value(pid, sid, iid, 'skills', skill['id'], operation="$push")
            if skill.get("special_code_flag", -1) != -1:
                if hasattr(skill["special_code_flag"], "__len__"):
                    for sf in skill["special_code_flag"]:
                        await db.set_inventory_value(pid, sid, iid, 'modifiers', sf, operation="$push")
                else:
                    await db.set_inventory_value(pid, sid, iid, 'modifiers', skill['special_code_flag'], operation="$push")
            reward_msg += f"- Random Skill: {skill['name']}\n"

    # 5. Cards
    if "cards" in rewards:
        reward_msg += "- Cards: " + ", ".join(rewards["cards"]) + "\n"
        for card in rewards["cards"]:
            await db.set_inventory_value(pid, sid, iid, "quest_cards", card, operation="$push")

    # 6. Random Treasure
    if rewards.get("treasure"):
        all_treasures = list(db.coll_treasures.find({}))
        if all_treasures:
            treasure = random.choice(all_treasures)
            await db.set_inventory_value(pid, sid, iid, 'treasures', treasure['id'], operation="$push")
            reward_msg += f"- Random Treasure: {treasure['name']}\n"

    # 7. Random Loot Pool
    loot_pool = rewards.get("loot_pool")
    if loot_pool:
        pool_type = loot_pool.get("type", "class")  # "class" or "generic"
        quality = loot_pool.get("quality", "low_qual")
        taken_buckets = set(await db.get_inventory_value(pid, sid, iid, "loot") or [])

        if pool_type == "generic":
            possible_buckets = await db.get_bucket_category(quality) or []
        else:
            # Class loot: get player's base class bucket_list
            player_class_id = await db.get_inventory_value(pid, sid, iid, "class")
            if player_class_id:
                static_class = await db.get_static_class(player_class_id)
                if static_class:
                    base_class_id = static_class.get("base_class_id") or static_class.get("base")
                    if base_class_id:
                        base_class = await db.get_base_class(base_class_id)
                        if base_class:
                            bucket_list = base_class.get("bucket_list", {})
                            possible_buckets = bucket_list.get(quality, [])
                        else:
                            possible_buckets = []
                    else:
                        possible_buckets = []
                else:
                    possible_buckets = []
            else:
                possible_buckets = []

        available = [b for b in possible_buckets if b not in taken_buckets]
        if available:
            chosen = random.choice(available)
            await db.set_inventory_value(pid, sid, iid, 'loot', chosen, operation="$push")
            reward_msg += f"- Random {pool_type.title()} Loot ({quality})\n"
        else:
            reward_msg += "- No available loot pools of that type.\n"

    # 8. Class Change (Mythic Reward)
    new_class_id = rewards.get("class_change") or rewards.get("class")
    if new_class_id:
        class_info = await db.get_static_class(new_class_id)
        if not class_info:
             class_info = await db.get_base_class(new_class_id)
        
        if class_info:
            await db.set_inventory_value(pid, sid, iid, "class", new_class_id)
            await db.set_inventory_value(pid, sid, iid, "loot", [])
            await db.set_inventory_value(pid, sid, iid, "offered_loot", [])
            await db.set_inventory_value(pid, sid, iid, "base_cards", [])
            
            all_base_cards = []
            if "base_cards" in class_info:
                all_base_cards.extend(class_info["base_cards"])
            if "base" in class_info:
                base_class_info = await db.get_base_class(class_info["base"])
                if base_class_info and "base_cards" in base_class_info:
                    all_base_cards.extend(base_class_info["base_cards"])
            if all_base_cards:
                for card in all_base_cards:
                    await db.set_inventory_value(pid, sid, iid, "base_cards", card, operation="$push")

            reward_msg += f"- CLASS CHANGE: You have been reborn as a **{class_info['name']}**!\n"
            reward_msg += "- Your inventory has been cleared to make room for your new power!\n"
        else:
            reward_msg += f"- CLASS CHANGE FAILED: Class ID {new_class_id} not found.\n"

    return reward_msg

async def complete_quest(pid, sid, iid):
    inventory = await db.get_inventory(pid, sid, iid)
    active_quest_data = inventory.get("active_quest")
    
    if not active_quest_data or active_quest_data["completed"]:
        return None, "You do not have an active quest to complete."
    
    quest_info = await db.get_quest_by_id(active_quest_data["id"])
    if not quest_info:
        return None, "Quest info not found."
    
    # Mark as completed
    active_quest_data["completed"] = True
    await db.set_inventory_value(pid, sid, iid, "active_quest", active_quest_data)
    
    # Add to completed list
    await db.set_inventory_value(pid, sid, iid, "completed_quests", active_quest_data["id"], operation="$push")
    
    # Give rewards
    reward_msg = await give_quest_rewards(pid, sid, iid, quest_info)
    
    return quest_info, reward_msg
