import json
import os

# Assuming that this is the path to the config folder
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../..", "config")

def load_json_file(filename):
    with open(os.path.join(CONFIG_PATH, filename), "r") as file:
        return json.load(file)

def test_generic_bucket_ids_in_buckets():
    generic_buckets_data = load_json_file("generic_buckets.json")
    buckets_data = load_json_file("buckets.json")
    bucket_ids = {bucket["id"] for bucket in buckets_data}

    for generic_bucket in generic_buckets_data:
        for category in ["staples", "removal", "engine"]:
            for id_ in generic_bucket.get(category, []):
                assert id_ in bucket_ids, f"ID {id_} from generic_buckets not found in buckets"
