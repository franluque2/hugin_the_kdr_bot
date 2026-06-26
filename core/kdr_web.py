from aiohttp import web
from core import kdr_db as db
from config.config import RPG_STATS, WEB_PORT, BASE_URL, LEVEL_THRESHOLDS
import jinja2
import aiohttp_jinja2
import os
import asyncio
import aiohttp

import logging
import json
import os
import asyncio
import aiohttp
import re as re_mod

# Set up logging for web requests
logger = logging.getLogger('kdr_web')
logger.setLevel(logging.DEBUG)

# ── Card image hosting (GitHub raw) ──
CARD_IMAGE_BASE_URL = "https://raw.githubusercontent.com/JustBryant/hugin_images/refs/heads/main/card_images"
FALLBACK_CARD_IMAGE = f"{CARD_IMAGE_BASE_URL}/Cyber%20Dragon.jpg"

def get_card_image_url(card_name: str) -> str:
    """Build the GitHub raw image URL for a given card name."""
    from urllib.parse import quote
    return f"{CARD_IMAGE_BASE_URL}/{quote(card_name)}.jpg"

# Card data cache from local database file
CARD_CACHE = {}
CARD_DB = None
CARD_DB_PATH = os.path.join(os.getcwd(), 'card_database.json')

def _load_card_db():
    """Load cached card database (downloaded by LootPoolGenerator)."""
    global CARD_DB
    if CARD_DB is not None:
        return CARD_DB
    if os.path.isfile(CARD_DB_PATH):
        try:
            with open(CARD_DB_PATH, 'r', encoding='utf-8') as f:
                CARD_DB = json.load(f)
            logger.info(f"Loaded {len(CARD_DB)} cards from local database")
        except Exception as e:
            logger.error(f"Failed to load card database: {e}")
            CARD_DB = {}
    else:
        logger.warning("No card_database.json found — run LootPoolGenerator first")
        CARD_DB = {}
    return CARD_DB

def _normalize(name):
    """Normalize card name for local DB lookup (same as LootPoolGenerator)."""
    import html as _html
    name = _html.unescape(name)
    name = name.replace('\u2018', "'").replace('\u2019', "'")
    name = name.replace('\u201c', '"').replace('\u201d', '"')
    name = ' '.join(name.split())
    return name.strip().lower()

async def get_card_data(card_name):
    if not card_name:
        return {"name": "Unknown", "img": "", "description": "", "details": ""}
    if card_name in CARD_CACHE:
        return CARD_CACHE[card_name]
    
    _load_card_db()
    normalized = _normalize(card_name)
    card = CARD_DB.get(normalized)
    
    if card:
        raw_type = card.get('type', '')
        clean_type = re_mod.sub(r'\s*(?:LVL|Level|Rank|Link)\s*\d+\s*', '', raw_type, flags=re_mod.IGNORECASE)
        stats_line = f"[{clean_type}] " if clean_type else ""
        
        card_type = raw_type.lower()
        if 'spell' in card_type:
            category = "Spells"
        elif 'trap' in card_type:
            category = "Traps"
        elif any(x in card_type for x in ['fusion', 'synchro', 'xyz', 'link']):
            category = "Extra Deck"
        else:
            category = "Monsters"

        if category in ["Monsters", "Extra Deck"]:
            if 'attribute' in card:
                stats_line += f"{card['attribute']} "
            if 'race' in card:
                stats_line += f"{card['race']} "
        else:
            if 'race' in card:
                stats_line += f"{card['race']} "
        
        card_info = {
            "name": card['name'],
            "img": get_card_image_url(card['name']),
            "description": card['desc'],
            "details": stats_line.strip(),
            "atk": card.get('atk'),
            "def": card.get('def'),
            "level": card.get('level') or card.get('rank') or card.get('linkval'),
            "category": category
        }
        CARD_CACHE[card_name] = card_info
        return card_info
    
    # Card not found in local DB — use fallback
    CARD_CACHE[card_name] = {"name": card_name, "img": FALLBACK_CARD_IMAGE, "description": "Card data unavailable.", "details": "", "category": "Monsters"}
    return CARD_CACHE[card_name]

async def handle_inventory(request):
    from core.kdr_data import SpecialClassHandling
    sid_str = request.match_info.get('sid')
    iid = request.match_info.get('iid')
    pid_str = request.match_info.get('pid')
    
    # Try all reasonable combinations of int/str for sid and pid
    inventory = None
    
    # Generate variations
    sids = [sid_str]
    try:
        sids.append(int(sid_str))
    except (ValueError, TypeError):
        pass
        
    pids = [pid_str]
    try:
        pids.append(int(pid_str))
    except (ValueError, TypeError):
        pass
        
    # Search loop
    for s in sids:
        for p in pids:
            inventory = await db.get_inventory(str(p), s, iid)
            if inventory:
                break
        if inventory:
            break
            
    if not inventory:
        # Final fallback - search by iid and pid string only (sid often fails due to type)
        from core.kdr_db import coll_inventory
        inventory = coll_inventory.find_one({
            'id_instance': iid,
            'id_player': pid_str
        })

    if not inventory:
        return web.Response(text=f"Inventory for player {pid_str} in instance {iid} not found.", status=404)
        
    pid = str(inventory.get('id_player'))
    sid = inventory.get('id_server')
    iid = inventory.get('id_instance')

    # Mimic: redirect to current opponent's inventory instead
    modifiers = inventory.get('modifiers', [])
    if SpecialClassHandling.CLASS_MIMIC.value in modifiers:
        active_round = await db.get_instance_value(sid, iid, 'active_round')
        current_rounds = await db.get_instance_value(sid, iid, 'current_rounds')
        if active_round is not None and active_round < len(current_rounds):
            for match in current_rounds[active_round]:
                if pid in match:
                    opponent_pid = match[1] if pid == match[0] else match[0]
                    # Fetch opponent's inventory instead
                    opp_inv = await db.get_inventory(opponent_pid, sid, iid)
                    if opp_inv:
                        inventory = opp_inv
                        pid = str(opponent_pid)
                    break
    
    class_id = inventory.get('class')
    legendary_items = {"skill": None, "quest": None, "relic": None}
    modifiers = inventory.get('modifiers', [])
    absorbed_classes_data = []
    
    if class_id:
        class_info = await db.get_static_class(class_id)
        # Handle Legendary items
        # Skill: Object with name/description
        l_skill = class_info.get("legendary_skill")
        if isinstance(l_skill, dict) and l_skill.get("name"):
            legendary_items["skill"] = {
                "name": l_skill["name"],
                "description": l_skill.get("description", ""),
                "img": "https://ms.yugipedia.com//4/45/Skill-DULI-EN-VG.png"
            }
                
        # Quest/Relic: Simple descriptions (Strings)
        l_quest_desc = class_info.get("legendary_quest")
        if l_quest_desc and isinstance(l_quest_desc, str):
            legendary_items["quest"] = {
                "name": "Legendary Quest",
                "description": l_quest_desc,
                "img": "https://files.catbox.moe/u8u1qy.png"
            }
                
        l_relic_desc = class_info.get("legendary_relic")
        if l_relic_desc and isinstance(l_relic_desc, str):
            legendary_items["relic"] = {
                "name": "Legendary Relic",
                "description": l_relic_desc,
                "img": "https://files.catbox.moe/j7hld3.png"
            }
        
        # Slime: fetch absorbed classes' legendary items
        if SpecialClassHandling.CLASS_SLIME.value in modifiers:
            absorbed_ids = inventory.get('absorbed_classes', [])
            for ac_id in absorbed_ids:
                ac_info = await db.get_static_class(ac_id)
                if ac_info:
                    ac_entry = {"id": ac_id, "name": ac_info.get("name"), "skill": None, "quest": None, "relic": None}
                    l_sk = ac_info.get("legendary_skill")
                    if isinstance(l_sk, dict) and l_sk.get("name"):
                        ac_entry["skill"] = {"name": l_sk["name"], "description": l_sk.get("description", "")}
                    l_q = ac_info.get("legendary_quest")
                    if l_q and isinstance(l_q, str):
                        ac_entry["quest"] = {"name": "Legendary Quest", "description": l_q}
                    l_r = ac_info.get("legendary_relic")
                    if l_r and isinstance(l_r, str):
                        ac_entry["relic"] = {"name": "Legendary Relic", "description": l_r}
                    absorbed_classes_data.append(ac_entry)
    else:
        class_info = {"name": "No Class Selected", "url_picture": ""}

    # Fetch Skills
    regular_skills = []
    restrictive_skills = []
    
    # Starting regular skills from class if any
    if class_id:
        for s_entry in class_info.get('regular_skills', []):
            if isinstance(s_entry, dict) and s_entry.get("name"):
                regular_skills.append({
                    "name": s_entry["name"],
                    "description": s_entry.get("description", ""),
                    "img": s_entry.get("img") or "https://files.catbox.moe/j7hld3.png"
                })
            elif isinstance(s_entry, str):
                skill = await db.get_skill_by_id(s_entry)
                if skill:
                    regular_skills.append({
                        "name": skill.get("name"),
                        "description": skill.get("description"),
                        "img": skill.get("img_url", "https://files.catbox.moe/j7hld3.png")
                    })

    skill_ids = inventory.get('skills', [])
    for skill_id in skill_ids:
        skill = await db.get_skill_by_id(skill_id)
        if skill:
            skill_info = {
                "name": skill.get("name"),
                "description": skill.get("description"),
                "img": skill.get("img_url", "https://files.catbox.moe/j7hld3.png")
            }
            if skill.get("is_sellable", True):
                regular_skills.append(skill_info)
            else:
                restrictive_skills.append(skill_info)
            
    # Fetch Treasures
    treasure_list = []
    treasure_ids = inventory.get('treasures', [])
    t_counts = {}
    for t_id in treasure_ids:
        t_counts[t_id] = t_counts.get(t_id, 0) + 1
        
    # Get all treasure objects first
    treasure_objs = []
    for t_id, count in t_counts.items():
        treasure = await db.get_treasure(t_id)
        if treasure:
            treasure_objs.append((treasure, count))
            
    # Fetch card data in parallel
    if treasure_objs:
        tasks = [get_card_data(t[0].get("name")) for t in treasure_objs]
        cards_data = await asyncio.gather(*tasks)
        
        for (treasure, count), card_data in zip(treasure_objs, cards_data):
            t_name = treasure.get("name")
            treasure_list.append({
                "name": t_name,
                "description": card_data.get("description") or treasure.get("description") or "No description available.",
                "details": f"Treasure | {card_data.get('details')}" if card_data.get('details') else "Treasure",
                "img": treasure.get("img_url") or card_data.get("img") or "https://files.catbox.moe/j7hld3.png",
                "rarity": treasure.get("rarity"),
                "count": count,
                "level": card_data.get("level"),
                "atk": card_data.get("atk"),
                "def": card_data.get("def")
            })
    
    treasures = treasure_list
            
    # Fetch Cards from Loot Buckets and Class
    cards_list = []
    base_cards = inventory.get('base_cards', [])
    cards_list.extend(base_cards)
    
    quest_cards = inventory.get('quest_cards', [])
    cards_list.extend(quest_cards)
    
    loot_ids = inventory.get('loot', [])
    for b_id in loot_ids:
        bucket = await db.get_bucket(b_id)
        if bucket and bucket.get('cards'):
            cards_list.extend(bucket['cards'])
    
    # Group and fetch visual data (no duplicate tracking — cards don't need counts)
    categorized_cards = {
        "Monsters": [],
        "Spells": [],
        "Traps": [],
        "Extra Deck": []
    }
    unique_cards = list(dict.fromkeys(cards_list))
    tasks = [get_card_data(name) for name in unique_cards]
    card_visuals = await asyncio.gather(*tasks)
    
    for i, visual in enumerate(card_visuals):
        visual_copy = visual.copy()
        cat = visual_copy.get('category', 'Monsters')
        categorized_cards[cat].append(visual_copy)
    
    for cat in categorized_cards:
        categorized_cards[cat].sort(key=lambda x: x['name'])

    # XP and Level
    xp = inventory.get('XP', 0)
    playerlevel = 1
    for threshold in LEVEL_THRESHOLDS:
        if xp >= threshold:
            playerlevel += 1

    # Fetch Quests
    active_quest = inventory.get('active_quest')
    quest_data = None
    if active_quest:
        q_info = await db.get_quest_by_id(active_quest.get('id'))
        if q_info:
            quest_data = {
                "name": q_info.get("name"),
                "description": q_info.get("description"),
                "completed": active_quest.get("completed", False)
            }

    # Fetch Relic
    relic_data = None
    relic_id = inventory.get('relic')
    if relic_id:
        relic = await db.get_treasure(relic_id)
        if relic:
            r_name = relic.get("name")
            card_data = await get_card_data(r_name)
            relic_data = {
                "name": r_name,
                "description": card_data.get("description") or relic.get("description") or "No description available.",
                "details": f"Relic | {card_data.get('details')}" if card_data.get('details') else "Relic",
                "img": relic.get("img_url") or card_data.get("img") or "https://files.catbox.moe/j7hld3.png",
                "rarity": relic.get("rarity", "secret_rare"),
                "level": card_data.get("level"),
                "atk": card_data.get("atk"),
                "def": card_data.get("def")
            }

    # Resolve recipes — convert string names to full dicts
    raw_recipes = (class_info.get('recipes', []) if class_id else []) + inventory.get('recipes', [])
    recipes_list = []
    for r in raw_recipes:
        if isinstance(r, str):
            recipe_data = await db.get_recipe_by_name(r)
            if recipe_data:
                recipes_list.append({"name": recipe_data["name"], "description": recipe_data.get("description", "")})
            else:
                recipes_list.append({"name": r, "description": ""})
        else:
            recipes_list.append({"name": r.get("name", r), "description": r.get("description", "")})

    context = {
        'pid': pid,
        'sid': sid,
        'iid': iid,
        'class_name': class_info.get('name'),
        'class_img': class_info.get('url_picture'),
        'gold': inventory.get('gold', 0),
        'xp': xp,
        'level': playerlevel,
        'stats': {stat: inventory.get(stat, 0) for stat in RPG_STATS},
        'legendary': legendary_items,
        'absorbed_classes': absorbed_classes_data,
        'regular_skills': regular_skills,
        'restrictive_skills': restrictive_skills,
        'recipes': recipes_list,
        'treasures': treasures,
        'relic': relic_data,
        'categories': categorized_cards,
        'modifiers': modifiers,
        'quest': quest_data,
        'wl': inventory.get('wl_ratio') or [0, 0],
        'is_slime': SpecialClassHandling.CLASS_SLIME.value in modifiers if modifiers else False
    }
    
    return aiohttp_jinja2.render_template('inventory.html', request, context)


async def handle_shop(request):
    sid_str = request.match_info.get('sid')
    iid = request.match_info.get('iid')
    pid_str = request.match_info.get('pid')
    
    # Generate variations for database lookup (handling int/str IDs)
    sids = [sid_str]
    try: sids.append(int(sid_str))
    except: pass
    pids = [pid_str]
    try: pids.append(int(pid_str))
    except: pass

    inventory = None
    for s in sids:
        for p in pids:
            inventory = await db.get_inventory(p, s, iid)
            if inventory: break
        if inventory: break
    
    if not inventory:
        return web.Response(text="Player or Session not found.", status=404)

    offered_loot = inventory.get("offered_loot", [])
    if not offered_loot:
        return web.Response(text="No active shop offers found for this player.", status=404)

    # offered_loot structure: [loot_windows_list, categories_generic, categories_class]
    windows = offered_loot[0]
    
    processed_windows = []
    from core.kdr_data import type_converter

    for window in windows:
        window_name = type_converter.get(window["name"], window["name"])
        window_cost = window.get("cost", 0)
        
        # Process separate buckets in this window
        processed_buckets = []
        buckets_to_process = window.get("buckets", [])
        
        for bucket in buckets_to_process:
            bucket_data = None
            # Check if bucket is a dictionary or just an ID (string)
            if isinstance(bucket, str):
                # db.get_bucket is async def, but returns sync dict or coroutine wrapper
                bucket_data = await db.get_bucket(bucket)
                if not bucket_data:
                    # Direct query fallback
                    bucket_data = db.kdr_db['buckets'].find_one({'id': bucket})
            elif isinstance(bucket, dict):
                bucket_data = bucket

            # Skip if we couldn't resolve valid bucket data
            if not bucket_data or not isinstance(bucket_data, dict):
                continue

            bucket_cards = []
            bucket_skills = []
            
            # Resolve Cards
            card_names = bucket_data.get("cards")
            if card_names and isinstance(card_names, list):
                tasks = [get_card_data(name) for name in card_names]
                bucket_cards = await asyncio.gather(*tasks)
            
            # Resolve Skills
            skill_ids = bucket_data.get("skills")
            if skill_ids and isinstance(skill_ids, list):
                for skill_id in skill_ids:
                    skill = await db.get_skill_by_id(skill_id)
                    if skill:
                        bucket_skills.append({
                            "name": skill.get("name"),
                            "description": skill.get("description"),
                            "img": skill.get("img_url", "https://files.catbox.moe/j7hld3.png")
                        })
            
            # Resolve recipes — convert string names to display dicts
            bucket_recipes = []
            for r in bucket_data.get("recipes", []):
                if isinstance(r, str):
                    rd = await db.get_recipe_by_name(r)
                    if rd:
                        bucket_recipes.append({"name": rd["name"], "description": rd.get("description", "")})
                    else:
                        bucket_recipes.append({"name": r, "description": ""})
                else:
                    bucket_recipes.append({"name": r.get("name", r), "description": r.get("description", "")})
            
            processed_buckets.append({
                "id": bucket_data.get("id") or str(bucket_data.get("_id", "Pool")),
                "cards": bucket_cards,
                "skills": bucket_skills,
                "recipes": bucket_recipes
            })
        
        processed_windows.append({
            "name": window_name,
            "cost": window_cost,
            "buckets": processed_buckets
        })

    class_id = inventory.get('class')
    class_name = "Reborn Warrior"
    shopkeep_name = inventory.get('shopkeep_name', 'Merchant')
    if class_id:
        class_info = await db.get_static_class(class_id)
        if not class_info:
            class_info = await db.get_base_class(class_id)
        if class_info:
            class_name = class_info.get("name", "Unknown Class")

    context = {
        'class_name': class_name,
        'shopkeep_name': shopkeep_name,
        'windows': processed_windows,
        'player_id': pid_str,
    }
    
    return aiohttp_jinja2.render_template('shop.html', request, context)

async def start_web_server():
    app = web.Application()
    
    # Template lookup
    template_path = os.path.join(os.getcwd(), 'views', 'web_templates')
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(template_path))
    
    app.router.add_get('/inventory/{sid}/{iid}/{pid}', handle_inventory)
    app.router.add_get('/shop/{sid}/{iid}/{pid}', handle_shop)
    
    runner = web.AppRunner(app)
    await runner.setup()
    # We use 0.0.0.0 to allow external access if configured
    site = web.TCPSite(runner, '0.0.0.0', WEB_PORT)
    await site.start()
    print(f"Web server started on {BASE_URL}")

def get_inventory_url(sid, iid, pid):
    return f"{BASE_URL.rstrip('/')}/inventory/{sid}/{iid}/{pid}"

def get_shop_url(sid, iid, pid):
    return f"{BASE_URL.rstrip('/')}/shop/{sid}/{iid}/{pid}"
