import json
import os

# Assuming that this is the path to the config folder
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../..", "config")

def load_json_file(filename):
    with open(os.path.join(CONFIG_PATH, filename), "r") as file:
        return json.load(file)

def test_unique_skills_in_class_skills():
    static_classes_data = load_json_file("static_classes.json")
    class_skills_data = load_json_file("class_skills.json")
    class_skill_ids = {class_skill["id"] for class_skill in class_skills_data}

    for static_class in static_classes_data:
        unique_skills = static_class.get("unique_skills", [])
        for skill_id in unique_skills:
            if skill_id == "":
                continue
            assert skill_id in class_skill_ids, f"Skill ID {skill_id} from static_classes not found in class_skills"
