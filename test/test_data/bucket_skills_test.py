import json
import os

# Assuming that this is the path to the config folder
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../..", "config")

def load_json_file(filename):
    with open(os.path.join(CONFIG_PATH, filename), "r") as file:
        return json.load(file)

def test_skills_in_bucket_skills():
    buckets_data = load_json_file("buckets.json")
    bucket_skills_data = load_json_file("bucket_skills.json")
    class_skills_data=load_json_file("class_skills.json")
    bucket_skill_ids = {bucket_skill["id"] for bucket_skill in bucket_skills_data}
    bucket_skill_ids.update({class_skill["id"] for class_skill in class_skills_data})
    for bucket in buckets_data:
        for skill_id in bucket.get("skills", []):
            assert skill_id in bucket_skill_ids, f"Skill ID {skill_id} from buckets not found in bucket_skills or class_skills"
