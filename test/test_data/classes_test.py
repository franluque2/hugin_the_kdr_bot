import json
import os

# Assuming that this is the path to the config folder
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../..", "config")

def load_json_file(filename):
    with open(os.path.join(CONFIG_PATH, filename), "r") as file:
        return json.load(file)

def test_static_classes_ids_in_base_classes_echoes():
    static_classes_data = load_json_file("static_classes.json")
    base_classes_data = load_json_file("base_classes.json")
    base_class_echo_ids = set()

    for base_class in base_classes_data:
        base_class_echo_ids.update(base_class.get("echos", []))

    for static_class in static_classes_data:
        static_class_id = static_class["id"]
        if static_class_id=="mimic":
            continue #temp ignoring mimic since it hasn't been finished yet
        assert static_class_id in base_class_echo_ids, f"Static Class ID {static_class_id} not found in base_classes echoes"

def test_base_classes_echo_ids_in_static_classes():
    static_classes_data = load_json_file("static_classes.json")
    base_classes_data = load_json_file("base_classes.json")
    static_class_ids = {static_class["id"] for static_class in static_classes_data}

    for base_class in base_classes_data:
        for echo_id in base_class.get("echos", []):
            assert echo_id in static_class_ids, f"Echo ID {echo_id} from base_classes not found in static_classes"
