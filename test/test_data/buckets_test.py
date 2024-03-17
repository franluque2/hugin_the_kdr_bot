import json
import os

# Assuming that this is the path to the config folder
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../..", "config")

def load_json_file(filename):
    with open(os.path.join(CONFIG_PATH, filename), "r") as file:
        return json.load(file)

def test_bucket_list_ids_exist():
    base_classes_data = load_json_file("base_classes.json")
    buckets_data = load_json_file("buckets.json")
    for base_class in base_classes_data:
        if "bucket_list" in base_class:
            for category, ids in base_class["bucket_list"].items():
                for id_ in ids:
                    assert any(bucket["id"] == id_ for bucket in buckets_data), f"ID {id_} not found in buckets"

def test_unique_bucket_ids():
    buckets_data = load_json_file("buckets.json")
    bucket_ids = set()

    for bucket in buckets_data:
        bucket_id = bucket["id"]
        assert bucket_id not in bucket_ids, f"Duplicated bucket ID: {bucket_id}"
        bucket_ids.add(bucket_id)

def test_bucket_list_subcategory_ids_exist():
    base_classes_data = load_json_file("base_classes.json")
    buckets_data = load_json_file("buckets.json")
    bucket_ids = {bucket["id"] for bucket in buckets_data}

    for base_class in base_classes_data:
        if "bucket_list" in base_class:
            for category, ids in base_class["bucket_list"].items():
                for id_ in ids:
                    assert id_ in bucket_ids, f"ID {id_} from bucket_list not found in buckets"
