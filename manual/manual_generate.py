#!/usr/bin/env python3
"""
Bit Rot Game Documentation Generator
Generates static HTML files from XML data.
All files work directly from file:// protocol.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import json
import urllib.parse

# Paths
BASE_DIR = Path(__file__).parent.parent
GAME_LIB = BASE_DIR / "game" / "lib"
DATA_DIR = GAME_LIB / "data"
SPRITES_DIR = GAME_LIB / "sprites"
OUTPUT_DIR = Path(__file__).parent
TEMPLATES_DIR = OUTPUT_DIR / "templates"

# Sprite subdirectory mapping
SPRITE_DIRS = {
    "items": "items",
    "clothes": "clothes",
    "vehicle": "vehicle",
    "craft": "items",  # Craft outputs are typically items
}

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "items").mkdir(exist_ok=True)
(OUTPUT_DIR / "clothes").mkdir(exist_ok=True)
(OUTPUT_DIR / "vehicles").mkdir(exist_ok=True)
(OUTPUT_DIR / "crafts").mkdir(exist_ok=True)


def get_sprite_path(sprite_name, item_type):
    """Get the correct sprite subdirectory based on item type."""
    if item_type == "cloth":
        subdir = "clothes"
    elif item_type == "vehicle":
        subdir = "vehicle"
    elif "body_" in sprite_name or "arms_" in sprite_name or "legs_" in sprite_name or "foot_" in sprite_name or "head_" in sprite_name or "hair_" in sprite_name or "facial_" in sprite_name or "hands_" in sprite_name or "util_" in sprite_name or "empty" in sprite_name:
        subdir = "clothes"
    elif sprite_name in ["car_ambulance.png", "car_jeep.png", "car_pickup.png", "car_truck.png"]:
        subdir = "vehicle"
    else:
        subdir = "items"

    return f"../game/lib/sprites/{subdir}"


def load_template(name):
    """Load a template file."""
    template_path = TEMPLATES_DIR / name
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def render_template(template, replacements):
    """Replace placeholders in template."""
    result = template
    for key, value in replacements.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def parse_item_xml(filepath):
    """Parse an item XML file and return structured data."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    data = {
        "name": root.get("name", "Unknown"),
        "type": root.get("type", "unknown"),
        "file": filepath.name,
        "properties": {},
        "spawn_chance": 0,
        "loot": [],
        "attributes": {},
        "sound": {},
        "sprite": None,
    }
    
    props = root.find("properties")
    if props is not None:
        for child in props:
            data["properties"][child.tag] = {k: v for k, v in child.attrib.items()}
            if child.tag == "sprite":
                data["sprite"] = child.get("file", "")
    
    spawn = root.find("spawn")
    if spawn is not None:
        data["spawn_chance"] = float(spawn.get("chance", 0))
    
    loot = root.find("loot")
    if loot is not None:
        for item in loot.findall("item"):
            data["loot"].append({
                "name": item.get("name", item.get("item", "Unknown")),
                "chance": float(item.get("chance", 0)),
            })
    
    attrs = root.find("attributes")
    if attrs is not None:
        for child in attrs:
            data["attributes"][child.tag] = child.get("value", 0)
    
    sound = root.find("sound")
    if sound is not None:
        for child in sound:
            data["sound"][child.tag] = child.get("src", "")
    
    if root.tag == "cloth":
        data["slot"] = root.get("id", "unknown")
        data["builder"] = root.get("builder", "false") == "true"
        if data["sprite"] is None and props is not None:
            sprite_elem = props.find("sprite")
            if sprite_elem is not None:
                data["sprite"] = sprite_elem.get("file", "")
    
    if root.tag == "vehicle":
        data["vehicle_type"] = root.get("type", "car")
        data["is_obstacle"] = root.get("is_obstacle", "false") == "true"
        data["capacity"] = root.findtext("capacity", default="0")
        
        visuals = root.find("visuals")
        if visuals is not None:
            sprite_elem = visuals.find("sprite")
            if sprite_elem is not None:
                data["sprite"] = sprite_elem.get("file", "")
        
        car = root.find("car")
        if car is not None:
            data["car"] = {child.tag: child.attrib for child in car}
    
    if root.tag == "recipe":
        data["craft_type"] = root.get("craft", "unknown")
        data["output"] = root.get("output", "")
        data["amount"] = root.get("amount", "1")
        data["time"] = root.get("time", "0")
        data["magazine"] = root.get("magazine", "")
        data["req_level"] = root.get("req_level", "")
        data["gain_xp"] = root.get("gain_xp", "")
        
        data["ingredients"] = []
        for ing in root.findall("ingredient"):
            data["ingredients"].append({
                "name": ing.get("name", "Unknown"),
                "amount": int(ing.get("amount", 1)),
                "destroy": ing.get("destroy", "false") == "true",
            })
        
        data["results"] = []
        for res in root.findall("result"):
            data["results"].append({
                "name": res.get("name", "Unknown"),
                "amount": int(res.get("amount", 1)),
                "chance": float(res.get("chance", 1)),
            })
    
    return data


def load_all_items():
    items = []
    items_dir = DATA_DIR / "items"
    if items_dir.exists():
        for xml_file in sorted(items_dir.glob("*.xml")):
            try:
                items.append(parse_item_xml(xml_file))
            except Exception as e:
                print(f"Error parsing {xml_file}: {e}")
    return items


def load_all_clothes():
    clothes = []
    clothes_dir = DATA_DIR / "clothes"
    if clothes_dir.exists():
        for xml_file in sorted(clothes_dir.glob("*.xml")):
            try:
                data = parse_item_xml(xml_file)
                if data["name"].lower().startswith("empty"):
                    continue
                clothes.append(data)
            except Exception as e:
                print(f"Error parsing {xml_file}: {e}")
    return clothes


def load_all_vehicles():
    vehicles = []
    vehicles_dir = DATA_DIR / "vehicle"
    if vehicles_dir.exists():
        for xml_file in sorted(vehicles_dir.glob("*.xml")):
            try:
                vehicles.append(parse_item_xml(xml_file))
            except Exception as e:
                print(f"Error parsing {xml_file}: {e}")
    return vehicles


def load_all_recipes():
    recipes = []
    craft_dir = DATA_DIR / "craft"
    if craft_dir.exists():
        for xml_file in sorted(craft_dir.glob("*.xml")):
            try:
                recipes.append(parse_item_xml(xml_file))
            except Exception as e:
                print(f"Error parsing {xml_file}: {e}")
    return recipes


def get_spawn_class(chance):
    if chance >= 1:
        return "spawn-high"
    elif chance > 0.5:
        return "spawn-medium"
    elif chance > 0:
        return "spawn-low"
    else:
        return "spawn-none"


def get_spawn_text(chance):
    if chance >= 1:
        return "100%"
    elif chance > 0:
        return f"{int(chance * 100)}%"
    else:
        return "0% (crafted/loot only)"


def name_to_id(name):
    return name.lower().replace(" ", "-").replace("'", "")


def group_items_by_category(items):
    """Group items by their type/category, joining car_ prefixes."""
    categories = {}
    for item in items:
        cat = item.get("type", "unknown")
        # Group all car-related items together
        if cat.startswith("car_"):
            cat = "car_parts"
            
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    return categories


def group_clothes_by_slot(clothes):
    slots = {}
    for cloth in clothes:
        slot = cloth.get("slot", "unknown")
        if slot not in slots:
            slots[slot] = []
        slots[slot].append(cloth)
    return slots


def group_recipes_by_type(recipes):
    types = {"create": [], "repair": [], "dismantle": []}
    for recipe in recipes:
        craft_type = recipe.get("craft_type", "unknown")
        if craft_type in types:
            types[craft_type].append(recipe)
        else:
            types[craft_type] = [recipe]
    return types


def find_recipes_using_item(item_name, recipes):
    using = []
    for recipe in recipes:
        for ing in recipe.get("ingredients", []):
            ing_name = ing.get("name", "")
            if item_name in ing_name or ing_name == item_name:
                using.append(recipe)
                break
    return using


def get_recipe_page_id(recipe):
    output_name = recipe.get("output", "")
    if not output_name:
        results = recipe.get("results", [])
        if results:
            output_name = results[0].get("name", recipe.get("file", "recipe").replace(".xml", ""))
        else:
            output_name = recipe.get("file", "recipe").replace(".xml", "")
    return name_to_id(output_name)


def find_recipes_producing_item(item_name, recipes):
    producing = []
    for recipe in recipes:
        output = recipe.get("output", "")
        if output == item_name:
            producing.append(recipe)
        for res in recipe.get("results", []):
            if res.get("name") == item_name:
                producing.append(recipe)
                break
    return producing


def generate_index_html(items, clothes, vehicles, recipes):
    template = load_template("index.html")
    replacements = {
        "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ITEMS_COUNT": len(items),
        "CLOTHES_COUNT": len(clothes),
        "VEHICLES_COUNT": len(vehicles),
        "RECIPES_COUNT": len(recipes),
    }
    return render_template(template, replacements)


def generate_items_list_html(items, recipes):
    categories = group_items_by_category(items)
    
    category_names = {
        "backpack": "🎒 Backpacks",
        "camp": "⛺ Camping",
        "car_parts": "🚗 Car Parts & Keys",
        "charm": "🍀 Charms",
        "consumable_ammo": "🔫 Ammunition",
        "consumable_drink": "🥤 Drinks",
        "consumable_food": "🍎 Food",
        "consumable_drugs": "💊 Drugs & Medication",
        "consumable_medication": "💊 Drugs & Medication",
        "consumable_repair": "🔧 Repair Items",
        "container": "📦 Containers",
        "currency": "💰 Currency & Map",
        "map": "💰 Currency & Map",
        "mobile": "📱 Mobile Devices",
        "recipe": "📚 Recipe Magazines",
        "resource": "🪵 Resources",
        "text": "🆔 ID",
        "utility": "🔦 Utility Items",
        "weapon_melee": "⚔️ Melee Weapons",
        "weapon_ranged": "🔫 Ranged Weapons",
    }
    
    def generate_item_card(item):
        sprite_html = ""
        sprite = item.get("sprite")
        if sprite:
            sprite_html = f'<div class="item-sprite"><img src="../game/lib/sprites/items/{sprite}" alt="{item["name"]}" onerror="this.style.display=\'none\'"></div>'
        
        props = item.get("properties", {})
        stats_html = ""
        
        if "capacity" in props:
            stats_html += f'<p><span class="stat-label">Capacity:</span> {props["capacity"].get("value", "N/A")} slots</p>'
        if "weight" in props:
            weight = props["weight"].get("weight", "N/A")
            reduction = props["weight"].get("reduction", "")
            weight_str = f"{weight} kg" + (f" ({reduction} reduction)" if reduction else "")
            stats_html += f'<p><span class="stat-label">Weight:</span> {weight_str}</p>'
        if "durability" in props:
            dur = props["durability"]
            stats_html += f'<p><span class="stat-label">Durability:</span> {dur.get("min", 1)}-{dur.get("max", 100)}</p>'
        if "damage" in props:
            dmg = props["damage"]
            stats_html += f'<p><span class="stat-label">Damage:</span> {dmg.get("min", 0)}-{dmg.get("max", 0)}</p>'
        if "ammo" in props:
            stats_html += f'<p><span class="stat-label">Ammo:</span> {props["ammo"].get("type", "N/A")}</p>'
        if "knockback" in props:
            stats_html += f'<p><span class="stat-label">Knockback:</span> {props["knockback"].get("value", 0)}</p>'
        if "firing" in props:
            firing = props["firing"]
            stats_html += f'<p><span class="stat-label">Range:</span> {firing.get("distance", 0)}m</p>'
        if "key" in props:
            stats_html += f'<p><span class="stat-label">Unlocks:</span> {props["key"].get("key", "N/A")}</p>'
        
        loot_html = ""
        if item.get("loot"):
            loot_names = [f"{l['name']} ({int(l['chance']*100)}%)" for l in item["loot"][:3]]
            loot_html = f'<p style="color: var(--warning); font-size: 0.85em; margin-top: 10px;">🎁 Contains: {", ".join(loot_names)}</p>'
        
        spawn_class = get_spawn_class(item.get("spawn_chance", 0))
        spawn_text = get_spawn_text(item.get("spawn_chance", 0))
        item_id = name_to_id(item["name"])
        
        return f'''
        <a href="items/{item_id}.html" class="item-link">
        <div class="item-card">
            {sprite_html}
            <div class="item-name">{item["name"]}</div>
            <div class="item-type">{item.get("type", "unknown")}</div>
            <div class="item-stats">
                {stats_html}
                {loot_html}
            </div>
            <div class="spawn-chance {spawn_class}">Spawn: {spawn_text}</div>
        </div>
        </a>
        '''
    
    categories_html = ""
    for item_type, item_list in sorted(categories.items()):
        display_name = category_names.get(item_type, item_type)
        items_html = "".join(generate_item_card(item) for item in item_list)
        categories_html += f'''
        <div class="category">
            <div class="category-header">
                <h2>{display_name}</h2>
            </div>
            <div class="items-grid">
                {items_html}
            </div>
        </div>
        '''
    
    template = load_template("page.html")
    replacements = {
        "TITLE": "Bit Rot - Items Manual",
        "HEADER_TITLE": "📦 Items Database",
        "HEADER_SUBTITLE": "Complete list of all items in Bit Rot",
        "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "FILE_COUNT": len(items),
        "CONTENT": categories_html,
    }
    
    return render_template(template, replacements)


def generate_item_detail_html(item, recipes, all_items, vehicles):
    props = item.get("properties", {})
    
    stats_rows = ""
    stat_mappings = [
        ("capacity", "Capacity", lambda p: f"{p.get('value', 'N/A')} slots"),
        ("weight", "Weight", lambda p: f"{p.get('weight', 'N/A')} kg" + (f" ({p.get('reduction', '')} reduction)" if p.get('reduction') else "")),
        ("durability", "Durability", lambda p: f"{p.get('min', 1)}-{p.get('max', 100)}"),
        ("damage", "Damage", lambda p: f"{p.get('min', 0)}-{p.get('max', 0)}"),
        ("defence", "Defence", lambda p: f"{p.get('value', 0)} ({int(float(p.get('value', 0)) * 100)}%)"),
        ("knockback", "Knockback", lambda p: f"{p.get('value', 0)}"),
        ("ammo", "Ammo Type", lambda p: f"{p.get('type', 'N/A')}"),
        ("key", "Unlocks", lambda p: f"{p.get('key', 'N/A')}"),
        ("fuel", "Fuel Type", lambda p: f"{p.get('type', 'N/A')}"),
    ]
    
    for prop_name, label, formatter in stat_mappings:
        if prop_name in props:
            value = formatter(props[prop_name])
            stats_rows += f'''
            <div class="stat-row">
                <span class="label">{label}</span>
                <span class="value">{value}</span>
            </div>
            '''
    
    if "restore" in props:
        restore_data = props.get("restore", [])
        if isinstance(restore_data, dict):
            restore_data = [restore_data]
        for r in restore_data:
            if isinstance(r, dict):
                stats_rows += f'''
                <div class="stat-row">
                    <span class="label">Restores {r.get('status', 'unknown')}</span>
                    <span class="value">{r.get('min', 0)}-{r.get('max', 0)}</span>
                </div>
                '''
    
    if "reduce" in props:
        reduce_data = props.get("reduce", [])
        if isinstance(reduce_data, dict):
            reduce_data = [reduce_data]
        for r in reduce_data:
            if isinstance(r, dict):
                stats_rows += f'''
                <div class="stat-row">
                    <span class="label">Reduces {r.get('status', 'unknown')}</span>
                    <span class="value">{r.get('min', 0)}-{r.get('max', 0)}</span>
                </div>
                '''
    
    spawn_class = get_spawn_class(item.get("spawn_chance", 0))
    spawn_text = get_spawn_text(item.get("spawn_chance", 0))
    
    # Identify linked vehicles this key unlocks
    unlocks_html = ""
    vehicles_unlocked = [v for v in vehicles if v.get("car", {}).get("key", {}).get("value") == item["name"]]
    if vehicles_unlocked:
        v_links = []
        for v in vehicles_unlocked:
            v_name = v["name"]
            v_id = name_to_id(v_name)
            sprite = v.get("sprite", "empty.png")
            v_links.append(f'<a href="../vehicles/{v_id}.html" class="craft-item"><img src="../../game/lib/sprites/vehicle/{sprite}" style="width: 32px; height: 32px; image-rendering: pixelated; margin-right: 8px;"> {v_name.replace("car_", "").title()}</a>')
        
        unlocks_html = f'''
        <div class="used-in">
            <h3>🚗 Unlocks Vehicles</h3>
            <div class="craft-list">
                {''.join(v_links)}
            </div>
        </div>
        '''

    recipes_using = find_recipes_using_item(item["name"], recipes)
    crafts_using_html = ""
    if recipes_using:
        craft_links = []
        for r in recipes_using[:10]:
            output = r.get("output", "")
            if not output:
                results = r.get("results", [])
                if results:
                    output = results[0].get("name", "")
            if not output:
                output = r.get("name", "Unknown")
            craft_type = r.get("craft_type", "")
            recipe_id = get_recipe_page_id(r)
            craft_links.append(f'<a href="../crafts/{recipe_id}.html" class="craft-item">{output} ({craft_type})</a>')
        crafts_using_html = f'''
        <div class="crafts-using">
            <h3>🔨 Used in Crafting ({len(recipes_using)} recipes)</h3>
            <div class="craft-list">
                {''.join(craft_links)}
            </div>
        </div>
        '''
    
    recipes_producing = find_recipes_producing_item(item["name"], recipes)
    used_in_html = ""
    if recipes_producing:
        craft_links = []
        for r in recipes_producing[:10]:
            craft_type = r.get("craft_type", "").title()
            craft_links.append(f'<a href="../crafts/{name_to_id(r.get("output", r.get("name", "recipe")))}.html" class="craft-item">📜 {craft_type} Recipe</a>')
        used_in_html = f'''
        <div class="used-in">
            <h3>📜 How to Craft ({len(recipes_producing)} recipes)</h3>
            <div class="craft-list">
                {''.join(craft_links)}
            </div>
        </div>
        '''
    
    sprite = item.get("sprite", "empty.png")
    template = load_template("item-detail.html")
    sprite_path = get_sprite_path(sprite, item.get("type", ""))
    
    replacements = {
        "ITEM_NAME": item["name"],
        "ITEM_TYPE": item.get("type", "unknown"),
        "SPRITE": sprite,
        "SPRITE_PATH": sprite_path,
        "STATS_ROWS": stats_rows,
        "SPAWN_CLASS": spawn_class,
        "SPAWN_TEXT": spawn_text,
        "CRAFTS_USING": crafts_using_html,
        "USED_IN_CRAFTS": used_in_html + unlocks_html,
    }

    return render_template(template, replacements)


def generate_clothes_list_html(clothes):
    slots = group_clothes_by_slot(clothes)
    
    slot_names = {
        "body": "👕 Body (T-Shirts)",
        "arms": "🧥 Arms (Jackets & Vests)",
        "legs": "👖 Legs (Pants & Shorts)",
        "feet": "👟 Feet (Footwear)",
        "head": "🎩 Head (Hats & Masks)",
        "hands": "🧤 Hands",
        "facial": "🧔 Facial Hair",
        "hair": "💇 Hair Styles",
        "util": "🎒 Utility (Vests)",
    }
    
    def generate_cloth_card(cloth):
        props = cloth.get("properties", {})
        
        sprite_html = ""
        sprite = cloth.get("sprite")
        if sprite:
            sprite_html = f'<div class="item-sprite"><img src="../game/lib/sprites/clothes/{sprite}" alt="{cloth["name"]}" onerror="this.style.display=\'none\'"></div>'
        
        stats_html = ""
        if "defence" in props:
            def_val = float(props["defence"].get("value", 0))
            def_class = "defence-high" if def_val >= 0.5 else ("defence-medium" if def_val >= 0.1 else "defence-low")
            stats_html += f'<p><span class="stat-label">Defence:</span> <span class="{def_class}">{def_val} ({int(def_val*100)}%)</span></p>'
        if "capacity" in props:
            stats_html += f'<p><span class="stat-label">Capacity:</span> {props["capacity"].get("value", "N/A")} slots</p>'
        if "durability" in props:
            dur = props["durability"]
            stats_html += f'<p><span class="stat-label">Durability:</span> {dur.get("min", 1)}-{dur.get("max", 100)}</p>'
        if "weight" in props:
            weight = props["weight"].get("weight", "N/A")
            reduction = props["weight"].get("reduction", "")
            weight_str = f"{weight} kg" + (f" ({reduction} reduction)" if reduction else "")
            stats_html += f'<p><span class="stat-label">Weight:</span> {weight_str}</p>'
        
        builder_tag = '<span class="builder-tag">builder</span>' if cloth.get("builder", False) else ""
        spawn_class = get_spawn_class(cloth.get("spawn_chance", 0))
        spawn_text = get_spawn_text(cloth.get("spawn_chance", 0))
        item_id = name_to_id(cloth["name"])
        
        return f'''
        <a href="clothes/{item_id}.html" class="item-link">
        <div class="item-card">
            {sprite_html}
            <div class="item-name">{cloth["name"]} {builder_tag}</div>
            <div class="item-slot">{cloth.get("slot", "unknown")}</div>
            <div class="item-stats">
                {stats_html}
            </div>
            <div class="spawn-chance {spawn_class}">Spawn: {spawn_text}</div>
        </div>
        </a>
        '''
    
    slots_html = ""
    for slot_key, display_name in sorted(slot_names.items()):
        if slot_key in slots:
            clothes_html = "".join(generate_cloth_card(c) for c in slots[slot_key])
            slots_html += f'''
            <div class="category">
                <div class="category-header">
                    <h2>{display_name}</h2>
                </div>
                <div class="items-grid">
                    {clothes_html}
                </div>
            </div>
            '''
    
    template = load_template("page.html")
    replacements = {
        "TITLE": "Bit Rot - Clothes Manual",
        "HEADER_TITLE": "👕 Clothes & Armor",
        "HEADER_SUBTITLE": "Wearable items organized by body slot",
        "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "FILE_COUNT": len(clothes),
        "CONTENT": slots_html,
    }
    return render_template(template, replacements)


def generate_clothes_detail_html(cloth, recipes):
    props = cloth.get("properties", {})
    stats_rows = ""
    stat_mappings = [
        ("defence", "Defence", lambda p: f"{p.get('value', 0)} ({int(float(p.get('value', 0)) * 100)}%)"),
        ("capacity", "Capacity", lambda p: f"{p.get('value', 'N/A')} slots"),
        ("durability", "Durability", lambda p: f"{p.get('min', 1)}-{p.get('max', 100)}"),
        ("weight", "Weight", lambda p: f"{p.get('weight', 'N/A')} kg" + (f" ({p.get('reduction', '')} reduction)" if p.get('reduction') else "")),
    ]
    
    for prop_name, label, formatter in stat_mappings:
        if prop_name in props:
            value = formatter(props[prop_name])
            stats_rows += f'''
            <div class="stat-row">
                <span class="label">{label}</span>
                <span class="value">{value}</span>
            </div>
            '''
    
    spawn_class = get_spawn_class(cloth.get("spawn_chance", 0))
    spawn_text = get_spawn_text(cloth.get("spawn_chance", 0))
    sprite = cloth.get("sprite", "empty.png")
    
    template = load_template("item-detail.html")
    sprite_path = get_sprite_path(sprite, "cloth")
    replacements = {
        "ITEM_NAME": cloth["name"],
        "ITEM_TYPE": f"{cloth.get('type', 'unknown')} - {cloth.get('slot', 'unknown')} slot",
        "SPRITE": sprite,
        "SPRITE_PATH": sprite_path,
        "STATS_ROWS": stats_rows,
        "SPAWN_CLASS": spawn_class,
        "SPAWN_TEXT": spawn_text,
        "CRAFTS_USING": "",
        "USED_IN_CRAFTS": "",
    }
    return render_template(template, replacements)


def generate_vehicles_list_html(vehicles):
    def generate_vehicle_card(vehicle):
        car = vehicle.get("car", {})
        loot = vehicle.get("loot", [])
        key_name = car.get("key", {}).get("value", "Unknown Key")
        
        capacity = vehicle.get("capacity", "N/A")
        capacity_val = capacity.get("value", "N/A") if isinstance(capacity, dict) else capacity
        
        specs = f'''
            <div class="spec-item">
                <span class="spec-label">Storage</span>
                <span class="spec-value">{capacity_val} slots</span>
            </div>
            <div class="spec-item">
                <span class="spec-label">Speed</span>
                <span class="spec-value">{car.get("max_speed", {}).get("value", "N/A")} m/s</span>
            </div>
            <div class="spec-item">
                <span class="spec-label">Seats</span>
                <span class="spec-value">{car.get("seats", {}).get("value", "N/A")}</span>
            </div>
            <div class="spec-item">
                <span class="spec-label">Fuel</span>
                <span class="spec-value">{int(float(car.get("fuel", {}).get("value", 0)) * 100)}%</span>
            </div>
        '''
        
        loot_html = ""
        for item in loot:
            chance = float(item.get("chance", 0))
            chance_class = "high" if chance >= 0.5 else ("medium" if chance >= 0.2 else "low")
            loot_html += f'''
                <div class="loot-item">
                    <span class="loot-name">{item["name"]}</span>
                    <span class="loot-chance {chance_class}">{int(chance * 100)}%</span>
                </div>
            '''
        
        name = vehicle["name"]
        if "ambulance" in name.lower():
            icon = "🚑"
        elif "truck" in name.lower():
            icon = "🚚"
        elif "jeep" in name.lower():
            icon = "🚙"
        elif "pickup" in name.lower():
            icon = "🛻"
        else:
            icon = "🚗"
        
        sprite_html = ""
        sprite = vehicle.get("sprite")
        if sprite:
            sprite_html = f'<div class="vehicle-sprite"><img src="../game/lib/sprites/vehicle/{sprite}" alt="{name}" onerror="this.style.display=\'none\'"></div>'
        
        vehicle_id = name_to_id(name)
        
        return f'''
        <a href="vehicles/{vehicle_id}.html" class="item-link">
        <div class="vehicle-card">
            <div class="vehicle-header">
                <div class="vehicle-name">{icon} {name.replace("car_", "").title()}</div>
                <div class="vehicle-type">{name} • {car.get("seats", {}).get("value", "N/A")} Seats</div>
            </div>
            <div class="vehicle-body">
                {sprite_html}
                <div class="key-requirement">
                    <h3>🔑 Required Key</h3>
                    <p><strong>{key_name}</strong></p>
                </div>
                <div class="specs">
                    <h3>📊 Specifications</h3>
                    <div class="spec-grid">
                        {specs}
                    </div>
                </div>
                <div class="loot-table">
                    <h3>🎁 Loot Table</h3>
                    {loot_html}
                </div>
            </div>
        </div>
        </a>
        '''
    
    vehicles_html = "".join(generate_vehicle_card(v) for v in vehicles)
    template = load_template("page.html")
    replacements = {
        "TITLE": "Bit Rot - Vehicles Manual",
        "HEADER_TITLE": "🚗 Vehicles",
        "HEADER_SUBTITLE": "Complete vehicle specifications and loot tables",
        "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "FILE_COUNT": len(vehicles),
        "CONTENT": f'<div class="vehicle-grid">{vehicles_html}</div>',
    }
    return render_template(template, replacements)


def generate_vehicles_detail_html(vehicle, all_items):
    car = vehicle.get("car", {})
    loot = vehicle.get("loot", [])
    
    # Pre-compute lookups
    sprite_lookup = {e["name"]: e.get("sprite") for e in all_items}
    type_lookup = {e["name"]: e.get("type", "") for e in all_items}

    def get_item_sprite_html(item_name):
        sprite = sprite_lookup.get(item_name)
        if not sprite:
            return ''
        item_type = type_lookup.get(item_name, "")
        if item_type == "cloth" or any(x in sprite for x in ["body_", "arms_", "legs_", "foot_", "head_", "hair_", "facial_", "hands_", "util_", "empty"]):
            subdir = "clothes"
        else:
            subdir = "items"
        return f'<img src="../../game/lib/sprites/{subdir}/{sprite}" alt="{item_name}" style="width: 32px; height: 32px; image-rendering: pixelated; vertical-align: middle; margin-right: 8px;">'

    capacity = vehicle.get("capacity", "N/A")
    capacity_val = capacity.get("value", "N/A") if isinstance(capacity, dict) else capacity
    
    specs = ""
    spec_items = [
        ("Storage Capacity", f"{capacity_val} slots"),
        ("Max Speed", f"{car.get('max_speed', {}).get('value', 'N/A')} m/s"),
        ("Fuel Level", f"{int(float(car.get('fuel', {}).get('value', 0)) * 100)}%"),
        ("Motor Condition", f"{int(float(car.get('motor', {}).get('value', 0)) * 100)}%"),
        ("Battery", f"{int(float(car.get('battery', {}).get('value', 0)) * 100)}%"),
        ("Lights Range", f"{car.get('lights', {}).get('radius', 'N/A')} tiles"),
        ("Seats", f"{car.get('seats', {}).get('value', 'N/A')}"),
        ("Obstacle", "Yes" if vehicle.get("is_obstacle", False) else "No"),
    ]
    
    for label, value in spec_items:
        specs += f'''
        <div class="stat-row">
            <span class="label">{label}</span>
            <span class="value">{value}</span>
        </div>
        '''
    
    key_name = car.get("key", {}).get("value", "Unknown Key")
    if key_name != "Unknown Key":
        key_id = name_to_id(key_name)
        key_sprite_html = get_item_sprite_html(key_name)
        key_html = f'''
        <div class="used-in">
            <h3>🔑 Required Key</h3>
            <div class="craft-list">
                <a href="../items/{key_id}.html" class="craft-item">{key_sprite_html} {key_name}</a>
            </div>
        </div>
        '''
    else:
        key_html = ""

    loot_html = ""
    for item in loot:
        chance = float(item.get("chance", 0))
        item_name = item["name"]
        item_id = name_to_id(item_name)
        sprite_html = get_item_sprite_html(item_name)
        
        loot_html += f'''
        <a href="../items/{item_id}.html" class="craft-item">
            {sprite_html} {item_name} <span style="margin-left: 5px; color: var(--warning); font-size: 0.85em;">({int(chance * 100)}%)</span>
        </a>
        '''

    if loot_html:
        loot_section = f'''
        <div class="used-in">
            <h3>🎁 Loot Table</h3>
            <div class="craft-list">
                {loot_html}
            </div>
        </div>
        '''
    else:
        loot_section = ""
    
    sprite = vehicle.get("sprite", "empty.png")
    name = vehicle["name"]

    template = load_template("item-detail.html")
    sprite_path = get_sprite_path(sprite, "vehicle")
    replacements = {
        "ITEM_NAME": f"{name.replace('car_', '').title()} ({name})",
        "ITEM_TYPE": f"Vehicle - {car.get('seats', {}).get('value', 'N/A')} seats",
        "SPRITE": sprite,
        "SPRITE_PATH": sprite_path,
        "STATS_ROWS": specs,
        "SPAWN_CLASS": "spawn-high",
        "SPAWN_TEXT": "100%",
        "CRAFTS_USING": key_html + loot_section,
        "USED_IN_CRAFTS": "",
    }
    
    return render_template(template, replacements)


def generate_crafts_list_html(recipes, items, clothes, vehicles):
    all_entities = items + clothes + vehicles
    sprite_lookup = {e["name"]: e.get("sprite") for e in all_entities}
    type_lookup = {e["name"]: e.get("type", "") for e in all_entities}

    def get_item_sprite_html(item_name):
        sprite = sprite_lookup.get(item_name)
        if not sprite:
            return ''
        item_type = type_lookup.get(item_name, "")
        if item_type == "cloth":
            subdir = "clothes"
        elif item_type == "vehicle":
            subdir = "vehicle"
        elif "body_" in sprite or "arms_" in sprite or "legs_" in sprite or "foot_" in sprite or "head_" in sprite or "hair_" in sprite or "facial_" in sprite or "hands_" in sprite or "util_" in sprite or "empty" in sprite:
            subdir = "clothes"
        elif sprite in ["car_ambulance.png", "car_jeep.png", "car_pickup.png", "car_truck.png"]:
            subdir = "vehicle"
        else:
            subdir = "items"
        return f'<img src="../game/lib/sprites/{subdir}/{sprite}" alt="{item_name}" style="width: 24px; height: 24px; image-rendering: pixelated; vertical-align: middle; margin-right: 5px;">'
    
    def parse_alternatives(name):
        if name.startswith("[") and "]" in name:
            content = name[1:name.index("]")]
            return [alt.strip() for alt in content.split(",")]
        return [name]
        
    def format_skills(skill_str):
        """Cleans up raw string data like [intelligence:1, maintenance:2]"""
        if not skill_str or skill_str == "[]": return ""
        cleaned = skill_str.replace("[", "").replace("]", "")
        parts = cleaned.split(",")
        formatted = []
        for p in parts:
            if ":" in p:
                k, v = p.split(":")
                formatted.append(f"{k.strip().title()} {v.strip()}")
            else:
                formatted.append(p.strip().title())
        return ", ".join(formatted)
    
    def generate_recipe_card(recipe):
        craft_type = recipe.get("craft_type", "unknown")
        badge_class = "dismantle" if craft_type == "dismantle" else ("repair" if craft_type == "repair" else "")
        
        ingredients_html = ""
        for ing in recipe.get("ingredients", []):
            destroy_class = "destroy-true" if ing.get("destroy", False) else "destroy-false"
            ing_name = ing["name"]
            alternatives = parse_alternatives(ing_name)
            ing_display = []
            for alt in alternatives:
                sprite_img = get_item_sprite_html(alt)
                ing_display.append(f'{sprite_img}{alt}' if sprite_img else alt)
            ing_name_html = " or ".join(ing_display)
            ingredients_html += f'''
                <div class="ingredient-item {destroy_class}">
                    <span class="item-name">{ing_name_html}</span>
                    <span class="item-amount">{ing["amount"]}x</span>
                </div>
            '''
        
        results_html = ""
        for res in recipe.get("results", []):
            chance = res.get("chance", 1)
            amount_str = f"{res['amount']}x" + (f" ({int(chance*100)}%)" if chance < 1 else "")
            res_name = res["name"]
            sprite_img = get_item_sprite_html(res_name)
            res_name_html = f'{sprite_img}{res_name}' if sprite_img else res_name
            results_html += f'''
                <div class="result-item">
                    <span class="item-name">{res_name_html}</span>
                    <span class="item-amount">{amount_str}</span>
                </div>
            '''
        
        magazine_html = ""
        if recipe.get("magazine"):
            magazine_html = f'<div class="magazine-req">📚 Requires: {recipe["magazine"]}</div>'
        
        skill_html = ""
        if recipe.get("req_level") and recipe["req_level"] != "[]":
            skill_html = f'<div class="skill-req">⭐ Requires: {format_skills(recipe["req_level"])}</div>'
        
        xp_html = ""
        if recipe.get("gain_xp") and recipe["gain_xp"] != "[]":
            xp_html = f'<div class="xp-gain">📈 XP Gain: {format_skills(recipe["gain_xp"])}</div>'
        
        meta_html = f'<span>⏱️ {recipe.get("time", 0)}s</span>'
        if recipe.get("amount"):
            meta_html += f' <span>📦 {recipe["amount"]}x output</span>'
        
        output_name = recipe.get("output", "")
        if not output_name:
            results = recipe.get("results", [])
            if results:
                output_name = results[0].get("name", recipe.get("file", "recipe").replace(".xml", ""))
            else:
                output_name = recipe.get("file", "recipe").replace(".xml", "")
        output_sprite = get_item_sprite_html(output_name)
        output_display = f'{output_sprite}{output_name}' if output_sprite else output_name
        
        recipe_id = name_to_id(output_name) if output_name else name_to_id(recipe.get("file", "recipe").replace(".xml", ""))
        
        return f'''
        <a href="crafts/{recipe_id}.html" class="item-link">
        <div class="recipe-card">
            <div class="recipe-header">
                <div>
                    <div class="recipe-name">{output_display}</div>
                    <div class="recipe-type">{recipe.get("type", "unknown")}</div>
                    <span class="craft-badge {badge_class}">{craft_type}</span>
                </div>
            </div>
            <div class="recipe-meta">
                {meta_html}
            </div>
            {magazine_html}
            {skill_html}
            <div class="ingredients">
                <h4>Ingredients</h4>
                {ingredients_html}
            </div>
            {results_html if results_html else ""}
            {xp_html}
        </div>
        </a>
        '''
    
    types = group_recipes_by_type(recipes)
    sections_html = ""
    type_names = {
        "create": ("✨ Create Recipes", "create"),
        "repair": ("🔨 Repair Recipes", "repair"),
        "dismantle": ("🔧 Dismantle Recipes", "dismantle"),
    }
    
    for craft_type, (display_name, _) in type_names.items():
        if types.get(craft_type):
            recipes_html = "".join(generate_recipe_card(r) for r in types[craft_type])
            sections_html += f'''
            <div class="category">
                <div class="category-header">
                    <h2>{display_name}</h2>
                    <span class="recipe-count">{len(types[craft_type])} recipes</span>
                </div>
                <div class="recipes-grid">
                    {recipes_html}
                </div>
            </div>
            '''
    
    template = load_template("page.html")
    replacements = {
        "TITLE": "Bit Rot - Crafting Manual",
        "HEADER_TITLE": "🔨 Crafting Recipes",
        "HEADER_SUBTITLE": "Complete crafting, repair, and dismantling guide",
        "TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "FILE_COUNT": len(recipes),
        "CONTENT": f'''
        <div class="legend">
            <h3>📖 Recipe Legend</h3>
            <div class="legend-grid">
                <div class="legend-item">
                    <div class="legend-color destroy"></div>
                    <span>Ingredient is consumed (destroyed)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color keep"></div>
                    <span>Ingredient is not consumed (tool)</span>
                </div>
            </div>
        </div>
        {sections_html}
        ''',
    }
    
    return render_template(template, replacements)


def generate_crafts_detail_html(recipe, items, clothes, vehicles):
    all_entities = items + clothes + vehicles
    sprite_lookup = {e["name"]: e.get("sprite") for e in all_entities}
    type_lookup = {e["name"]: e.get("type", "") for e in all_entities}

    def get_item_sprite_html(item_name):
        sprite = sprite_lookup.get(item_name)
        if not sprite:
            return ''
        item_type = type_lookup.get(item_name, "")
        if item_type == "cloth":
            subdir = "clothes"
        elif item_type == "vehicle":
            subdir = "vehicle"
        elif "body_" in sprite or "arms_" in sprite or "legs_" in sprite or "foot_" in sprite or "head_" in sprite or "hair_" in sprite or "facial_" in sprite or "hands_" in sprite or "util_" in sprite or "empty" in sprite:
            subdir = "clothes"
        elif sprite in ["car_ambulance.png", "car_jeep.png", "car_pickup.png", "car_truck.png"]:
            subdir = "vehicle"
        else:
            subdir = "items"
        return f'<img src="../../game/lib/sprites/{subdir}/{sprite}" alt="{item_name}" style="width: 32px; height: 32px; image-rendering: pixelated; vertical-align: middle; margin-right: 5px;">'

    craft_type = recipe.get("craft_type", "unknown")
    
    output_name = recipe.get("output", "")
    if not output_name:
        results = recipe.get("results", [])
        if results:
            output_name = results[0].get("name", recipe.get("file", "recipe").replace(".xml", ""))
        else:
            output_name = recipe.get("file", "recipe").replace(".xml", "")
    
    ingredients_html = ""
    for ing in recipe.get("ingredients", []):
        destroy_class = "destroy-true" if ing.get("destroy", False) else "destroy-false"
        ing_name = ing["name"]
        sprite_img = get_item_sprite_html(ing_name.replace("[", "").replace("]", "").split(",")[0].strip())
        ingredients_html += f'''
        <div class="stat-row">
            <span class="label">{sprite_img}{ing_name}</span>
            <span class="value">{ing["amount"]}x {'(consumed)' if ing.get('destroy') else '(tool)'}</span>
        </div>
        '''

    results_html = ""
    for res in recipe.get("results", []):
        sprite_img = get_item_sprite_html(res["name"])
        results_html += f'''
        <div class="stat-row">
            <span class="label">{sprite_img}{res["name"]}</span>
            <span class="value">{res["amount"]}x</span>
        </div>
        '''

    if craft_type == "dismantle":
        stats_rows = f'''
        <div class="stat-row" style="background: rgba(248, 113, 113, 0.2); border-left: 3px solid #f87171;">
            <span class="label" style="color: #f87171; font-weight: bold;">📥 INGREDIENTS</span>
            <span class="value"></span>
        </div>
        {ingredients_html}
        <div class="stat-row" style="background: rgba(74, 222, 128, 0.2); border-left: 3px solid #4ade80;">
            <span class="label" style="color: #4ade80; font-weight: bold;">📤 RESULTS</span>
            <span class="value"></span>
        </div>
        {results_html}
        '''
    else:
        stats_rows = ingredients_html + (results_html if results_html else "")

    magazine_html = ""
    if recipe.get("magazine"):
        magazine_html = f'<p>📚 Requires: {recipe["magazine"]}</p>'

    xp_html = ""
    if recipe.get("gain_xp"):
        xp_html = f'<p>⭐ XP Gain: {recipe["gain_xp"]}</p>'

    sprite = sprite_lookup.get(output_name, "empty.png")

    template = load_template("item-detail.html")
    sprite_path = get_sprite_path(sprite, "craft")
    replacements = {
        "ITEM_NAME": output_name,
        "ITEM_TYPE": f"Recipe - {craft_type}",
        "SPRITE": sprite,
        "SPRITE_PATH": sprite_path,
        "STATS_ROWS": f'''
        <div class="stat-row">
            <span class="label">Craft Time</span>
            <span class="value">{recipe.get("time", 0)}s</span>
        </div>
        {stats_rows}
        ''',
        "SPAWN_CLASS": "spawn-none",
        "SPAWN_TEXT": "Crafting Recipe",
        "CRAFTS_USING": f'''
        <div class="used-in">
            <h3>📖 Requirements</h3>
            {magazine_html}
            {xp_html}
        </div>
        ''',
        "USED_IN_CRAFTS": "",
    }

    return render_template(template, replacements)


def main():
    print("📖 Bit Rot Static Site Generator")
    print("=" * 40)
    
    print("📂 Loading items...")
    items = load_all_items()
    print(f"   Found {len(items)} items")
    
    print("👕 Loading clothes...")
    clothes = load_all_clothes()
    print(f"   Found {len(clothes)} clothes")
    
    print("🚗 Loading vehicles...")
    vehicles = load_all_vehicles()
    print(f"   Found {len(vehicles)} vehicles")
    
    print("🔨 Loading recipes...")
    recipes = load_all_recipes()
    print(f"   Found {len(recipes)} recipes")
    
    print("\n📝 Generating main pages...")
    
    print("   → index.html")
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(generate_index_html(items, clothes, vehicles, recipes))
    
    print("   → items.html")
    with open(OUTPUT_DIR / "items.html", "w", encoding="utf-8") as f:
        f.write(generate_items_list_html(items, recipes))
    
    print("   → clothes.html")
    with open(OUTPUT_DIR / "clothes.html", "w", encoding="utf-8") as f:
        f.write(generate_clothes_list_html(clothes))
    
    print("   → vehicles.html")
    with open(OUTPUT_DIR / "vehicles.html", "w", encoding="utf-8") as f:
        f.write(generate_vehicles_list_html(vehicles))
    
    print("   → crafts.html")
    with open(OUTPUT_DIR / "crafts.html", "w", encoding="utf-8") as f:
        f.write(generate_crafts_list_html(recipes, items, clothes, vehicles))
    
    print("\n📄 Generating individual item pages...")
    for item in items:
        item_id = name_to_id(item["name"])
        html = generate_item_detail_html(item, recipes, items, vehicles)
        with open(OUTPUT_DIR / "items" / f"{item_id}.html", "w", encoding="utf-8") as f:
            f.write(html)
    print(f"   Generated {len(items)} item pages in items/")
    
    print("   Generating individual clothes pages...")
    for cloth in clothes:
        cloth_id = name_to_id(cloth["name"])
        html = generate_clothes_detail_html(cloth, recipes)
        with open(OUTPUT_DIR / "clothes" / f"{cloth_id}.html", "w", encoding="utf-8") as f:
            f.write(html)
    print(f"   Generated {len(clothes)} clothes pages in clothes/")
    
    print("   Generating individual vehicle pages...")
    for vehicle in vehicles:
        vehicle_id = name_to_id(vehicle["name"])
        html = generate_vehicles_detail_html(vehicle, items + clothes)
        with open(OUTPUT_DIR / "vehicles" / f"{vehicle_id}.html", "w", encoding="utf-8") as f:
            f.write(html)
    print(f"   Generated {len(vehicles)} vehicle pages in vehicles/")
    
    print("   Generating individual craft pages...")
    for recipe in recipes:
        output_name = recipe.get("output", "")
        if not output_name:
            results = recipe.get("results", [])
            if results:
                output_name = results[0].get("name", recipe.get("file", "recipe").replace(".xml", ""))
            else:
                output_name = recipe.get("file", "recipe").replace(".xml", "")
        
        recipe_id = name_to_id(output_name)
        html = generate_crafts_detail_html(recipe, items, clothes, vehicles)
        with open(OUTPUT_DIR / "crafts" / f"{recipe_id}.html", "w", encoding="utf-8") as f:
            f.write(html)
    print(f"   Generated {len(recipes)} craft pages in crafts/")
    
    print("\n✅ Documentation generated successfully!")
    print(f"   Output directory: {OUTPUT_DIR}")
    print(f"\n   Open {OUTPUT_DIR / 'index.html'} in a browser to view.")
    print(f"   All files work from file:// protocol.")


if __name__ == "__main__":
    main()