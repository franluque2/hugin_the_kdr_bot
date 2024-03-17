import core.kdr_db as db
from core.kdr_statics import try_open_json
from json import load as json_load
from config.config import DB_KEY_SERVER, DB_KEY_INSTANCE, \
    PATH_BUCKETS, PATH_BASE_CLASSES, PATH_STATIC_CLASSES, \
    PATH_TREASURES, PATH_GENERIC_SKILLS, PATH_GENERIC_BUCKETS, \
    PATH_BUCKET_SKILLS, PATH_CLASS_SKILLS

""" Build Base Classes Collection from JSON """


async def build_base_classes(file: dict) -> bool:
    for c in file:
        db.coll_classes_base.insert_one(c)

    return True


""""""

""" Build Static Classes Collection from JSON """


async def build_static_classes(file: dict) -> bool:
    for c in file:
        db.coll_classes_static.insert_one(c)
    return True


""""""

""" Build Bucket Collection from JSON """


async def build_buckets(file: dict) -> bool:
    for c in file:
        db.coll_buckets.insert_one(c)
    return True


""""""

""" Build Generic Bucket Collection from JSON """


async def build_generic_buckets(file: dict) -> bool:
    for c in file:
        db.coll_buckets_generic.insert_one(c)
    return True


""""""

""" Build Skills Collection from JSON """


async def build_skills(file_bucket_skills: dict, file_class_skills: dict, file_generic_skills: dict) -> bool:
    for c in file_bucket_skills:
        db.coll_skills.insert_one(c)
    for c in file_class_skills:
        db.coll_skills_generic.insert_one(c)
    for c in file_generic_skills:
        db.coll_skills.insert_one(c)
    return True


""""""

""" Build Treasures Collection from JSON """


async def build_treasures(file: dict) -> bool:
    for c in file:
        db.coll_treasures.insert_one(c)
    return True


""""""
