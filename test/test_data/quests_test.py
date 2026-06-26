import json
import os
import pytest

# Paths to the JSON files
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../class_examples")

def load_json_file(filename):
    path = os.path.join(CONFIG_PATH, filename)
    with open(path, "r") as file:
        return json.load(file)

def test_quest_schema():
    """Ensure all quests have required fields and valid reward/requirement structure."""
    quests = load_json_file("generic_quests.json")
    valid_stats = ["strength", "dexterity", "intelligence", "constitution", "luck"]
    
    for quest in quests:
        assert "id" in quest, f"Quest missing 'id': {quest.get('name', 'Unknown')}"
        assert "name" in quest, f"Quest ID {quest['id']} missing 'name'"
        assert "description" in quest, f"Quest {quest['name']} missing 'description'"
        
        # Requirements
        reqs = quest.get("requirements", {})
        if "stat" in reqs:
            assert reqs["stat"] in valid_stats, f"Invalid stat '{reqs['stat']}' in quest {quest['name']}"
            assert "stat_value" in reqs, f"Missing 'stat_value' for stat requirement in {quest['name']}"
        
        # Rewards
        rewards = quest.get("rewards", {})
        if "gold" in rewards:
            assert isinstance(rewards["gold"], int), f"Gold reward must be int in {quest['name']}"
        if "xp" in rewards:
            assert isinstance(rewards["xp"], int), f"XP reward must be int in {quest['name']}"

def test_quest_references():
    """Ensure all skill IDs referenced in quest rewards actually exist."""
    quests = load_json_file("generic_quests.json")
    
    # Load all skills
    bucket_skills = load_json_file("bucket_skills.json")
    class_skills = load_json_file("class_skills.json")
    generic_skills = load_json_file("generic_skills.json")
    all_skill_ids = {s["id"] for s in bucket_skills + class_skills + generic_skills}
    
    for quest in quests:
        rewards = quest.get("rewards", {})
        
        # Check Skills
        if "skills" in rewards:
            for sid in rewards["skills"]:
                assert sid in all_skill_ids, f"Quest {quest['name']} references non-existent Skill ID: {sid}"
                
        # Cards are plain card names (not references to treasures),
        # just verify they are non-empty strings
        if "cards" in rewards:
            for cid in rewards["cards"]:
                assert isinstance(cid, str) and len(cid) > 0, f"Quest {quest['name']} has invalid card name: '{cid}'"

def test_unique_ids_across_all_files():
    """Check for ID collisions across different data types if necessary, but primarily within files."""
    files_to_check = [
        "generic_quests.json",
        "buckets.json",
        "treasures.json",
        "base_classes.json",
        "static_classes.json"
    ]
    
    for filename in files_to_check:
        data = load_json_file(filename)
        ids = [item["id"] for item in data]
        duplicates = [i for i in ids if ids.count(i) > 1]
        assert not duplicates, f"Duplicate IDs found in {filename}: {set(duplicates)}"
