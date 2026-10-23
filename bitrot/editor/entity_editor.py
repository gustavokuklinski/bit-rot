import pygame
import os
import re
import json
import xml.etree.ElementTree as ET
from editor.config import GAME_ROOT, TILE_SIZE, get_data_dir, get_sprites_dir, LIB_ROOT
from editor.ui import (
    UITextBox, UIDropdown, UITextArea, UITheme, 
    draw_styled_button, register_tooltip, FocusManager
)

class UIToggle:
    def __init__(self, x, y, width, height, font, state=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        if isinstance(state, str):
            self.state = state.lower() in ["true", "1", "yes"]
        else:
            self.state = bool(state)

    @property
    def text(self): return "true" if self.state else "false"

    @text.setter
    def text(self, val):
        if isinstance(val, str):
            self.state = val.lower() in ["true", "1", "yes"]
        else:
            self.state = bool(val)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = not self.state
                return True
        return False

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        color = UITheme.SUCCESS if self.state else UITheme.DANGER
        hover = UITheme.SUCCESS_HOVER if self.state else UITheme.DANGER_HOVER
        draw_styled_button(surface, self.rect, "True" if self.state else "False", self.font, mouse_pos, color, hover)

class UIStepButton:
    def __init__(self, x, y, width, height, font, val, steps):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.steps = [str(s) for s in steps]
        self.text = str(val)
        
        if self.text not in self.steps:
            try:
                num_val = float(self.text)
                self.text = min(self.steps, key=lambda s: abs(float(s) - num_val))
            except ValueError:
                self.text = self.steps[0]

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                idx = self.steps.index(self.text)
                if event.button == 1: 
                    self.text = self.steps[(idx + 1) % len(self.steps)]
                    return True
                elif event.button == 3: 
                    self.text = self.steps[(idx - 1) % len(self.steps)]
                    return True
        return False

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        draw_styled_button(surface, self.rect, self.text, self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG, tooltip="L-Click: Up | R-Click: Down")

BOILERPLATES = {
    "Zombie": """{
  "zombies": {
    "common": {
      "spawn_weight": 70,
      "name": "RANDOM",
      "sex": "RANDOM",
      "xp": { "min": 1, "max": 10 },
      "stats": {
        "health": { "min": 10, "max": 50 },
        "speed": { "min": 1, "max": 2 },
        "attack": { "min": 1, "max": 10 },
        "infection": { "min": 1, "max": 5 }
      },
      "clothes": {
        "head": null,
        "util": null,
        "hair": null,
        "facial": null,
        "feet": null,
        "hand": null,
        "body": null,
        "arms": null,
        "legs": null
      },
      "visuals": {
        "center": "zombie.png",
        "left": "zombie_left.png",
        "right": "zombie_right.png"
      },
      "loot": [
        { "item": "Money WBRL", "min": 1, "max": 1, "chance": 1.0 },
        { "item": "Coin WBRL", "chance": 0.5 },
        { "item": "Rot Meat", "min": 1, "max": 1, "chance": 1.0 }
      ],
      "sound": {
        "hit": "zombie_hit.ogg",
        "wander": "zombie_wandering.ogg",
        "dead": "zombie_dead.ogg",
        "attack": "zombie_attack.ogg",
        "steps": "zombie_steps.ogg"
      }
    }
  }
}""",

    "NPC": """{
  "npcs": {
    "common": {
      "spawn_weight": 55,
      "is_friendly": false,
      "is_static": false,
      "spawn_zombies_multiplier": 1,
      "name": "RANDOM",
      "sex": "RANDOM",
      "stats": {
        "health": { "min": 10, "max": 80 },
        "speed": { "min": 1, "max": 1 },
        "attack": { "min": 1, "max": 15 },
        "infection": { "min": 1, "max": 5 }
      },
      "clothes": {
        "head": null,
        "util": null,
        "hair": null,
        "facial": null,
        "feet": null,
        "hand": null,
        "body": null,
        "arms": null,
        "legs": null
      },
      "visuals": {
        "center": "npc_zombie.png",
        "left": "npc_zombie_left.png",
        "right": "npc_zombie_right.png"
      },
      "loot": [
        { "item": "Rot Meat", "chance": 1.0 }
      ],
      "sound": {
        "hit": "npc_hit.ogg",
        "attack": "npc_attack.ogg",
        "dead": "npc_dead.ogg",
        "steps": "npc_steps.ogg"
      }
    }
  }
}""",

    "Animal": """{
  "animals": {
    "boar": {
      "name": "Boar",
      "type": "animal",
      "attack_player": false,
      "spawn_weight": 100,
      "spawn_layer": ["L1", "L2"],
      "spawn_zombies_multiplier": 1,
      "capacity": 3,
      "stats": {
        "health": { "min": 20, "max": 30 },
        "speed": { "min": 0.5, "max": 0.8 },
        "attack": { "min": 6, "max": 15 },
        "infection": { "min": 10, "max": 15 }
      },
      "visuals": {
        "center": "boar.png",
        "left": "boar.png",
        "right": "boar.png"
      },
      "loot": [
        { "item": "Rot Meat", "chance": 1.0 }
      ],
      "sound": {
        "hit": "animal_rat_hit.ogg",
        "attack": "animal_rat_attack.ogg",
        "dead": "animal_dead.ogg",
        "steps": "animal_rat_steps.ogg"
      }
    }
  }
}""",

    "Player": """{
  "player": {
    "name": "Player",
    "sex": "Male",
    "traits": [],
    "stats": {
      "health": 100.0,
      "stamina": 100.0,
      "water": 100.0,
      "food": 100.0,
      "anxiety": 0.0,
      "infection": 0.0,
      "defence": 0.0
    },
    "attributes": {
      "strength": 0.0,
      "fitness": 0.0,
      "melee": 0.0,
      "ranged": 0.0,
      "maintenance": 0.0,
      "lucky": 0.0,
      "agility": 0.0,
      "intelligence": 0.0
    },
    "visuals": {
      "center": "player.png",
      "left": "player_left.png",
      "right": "player_right.png"
    },
    "clothes": {
      "head": null,
      "util": null,
      "hair": null,
      "facial": null,
      "feet": null,
      "hand": null,
      "body": null,
      "arms": null,
      "legs": null
    }
  }
}""",

    "Vehicle": """<vehicle name="car_new" type="car" is_obstacle="true" spawn_weight="40">
    <capacity value="10" />
    <car>
        <max_speed value="8" /><key value="" /><fuel value="1.0" /><motor value="1.0" /><battery value="1.0" />
        <tire_front_left value="" /><tire_front_right value="" /><tire_back_left value="" /><tire_back_right value="" />
        <lights min="5" max="100" radius="8" /><seats value="4" /> 
    </car>
    <loot><item item="Car Tire" chance="0.3" /></loot>
    <visuals><sprite id="top" file="car_top.png" /><sprite id="down" file="car_down.png" /><sprite id="left" file="car_left.png" /><sprite id="right" file="car_right.png" /></visuals>
</vehicle>""",

    "Clothes": """<cloth name="New Cloth" type="cloth" id="body" builder="true">
    <properties><defence value="1" /><durability min="1" max="100" /><sprite file="" /><weight weight="0.0" /></properties>
    <spawn chance="1" />
</cloth>""",

    "Radio": """<radio name="New Radio" frequency="100.0" stream="[general]">
    <stream text="[STATIC]..." />
</radio>""",

    "Items": """<item name="New Item" type="general" allow_belt="false">
    <properties><weight weight="0.01" /><sprite file="" /><description text="" /></properties>
    <spawn chance="1" />
</item>""",

    "Map": """<map char="." name="New Map Tile" obstacle="false">
    <visuals>
        <sprite file="" />
    </visuals>
    <loot>
        <item type="container" min="1" max="1" chance="0.1" />
    </loot>
</map>"""
}

CATEGORY_EXTENSIONS = {
    "Zombie": ".json",
    "NPC": ".json",
    "Animal": ".json",
    "Player": ".json",
    "Vehicle": ".xml",
    "Clothes": ".xml",
    "Radio": ".xml",
    "Items": ".xml",
    "Map": ".xml"
}

def json_to_element_tree(data, category):
    root_tag = category.lower()
    entity_key = None
    entity_data = data

    for group_key in ["zombies", "npcs", "animals", "builds"]:
        if group_key in data and isinstance(data[group_key], dict) and data[group_key]:
            entity_key = list(data[group_key].keys())[0]
            entity_data = data[group_key][entity_key]
            break

    if "player" in data and isinstance(data["player"], dict):
        entity_key = "player"
        entity_data = data["player"]

    root = ET.Element(root_tag)
    if entity_key and entity_key != "player":
        root.set("type", str(entity_key))

    for k, v in entity_data.items():
        if k in ["stats", "clothes", "visuals", "sound", "loot", "properties"]: continue
        if isinstance(v, dict):
            child = ET.SubElement(root, k)
            for sub_k, sub_v in v.items(): child.set(sub_k, str(sub_v))
        elif isinstance(v, list):
            child = ET.SubElement(root, k)
            child.text = str(v)
        else:
            if v is not None: root.set(k, str(v))

    if "stats" in entity_data and isinstance(entity_data["stats"], dict):
        stats_el = ET.SubElement(root, "stats")
        for stat_name, stat_val in entity_data["stats"].items():
            s_child = ET.SubElement(stats_el, stat_name)
            if isinstance(stat_val, dict):
                for sk, sv in stat_val.items(): s_child.set(sk, str(sv))
            else:
                s_child.set("value", str(stat_val))

    if "clothes" in entity_data and isinstance(entity_data["clothes"], dict):
        clothes_el = ET.SubElement(root, "clothes")
        for slot, cloth_item in entity_data["clothes"].items():
            slot_el = ET.SubElement(clothes_el, slot)
            if cloth_item:
                ET.SubElement(slot_el, "cloth", {"name": str(cloth_item)})

    if "visuals" in entity_data and isinstance(entity_data["visuals"], dict):
        vis_el = ET.SubElement(root, "visuals")
        for sprite_id, sprite_file in entity_data["visuals"].items():
            ET.SubElement(vis_el, "sprite", {"id": str(sprite_id), "file": str(sprite_file)})

    if "sound" in entity_data and isinstance(entity_data["sound"], dict):
        sound_el = ET.SubElement(root, "sound")
        for snd_id, snd_file in entity_data["sound"].items():
            ET.SubElement(sound_el, str(snd_id), {"src": str(snd_file)})

    loot_list = entity_data.get("loot") or entity_data.get("initial_loot") or []
    if isinstance(loot_list, list):
        loot_el = ET.SubElement(root, "loot")
        for item_entry in loot_list:
            if isinstance(item_entry, dict):
                attribs = {lk: str(lv) for lk, lv in item_entry.items()}
                ET.SubElement(loot_el, "item", attribs)

    return ET.ElementTree(root)

def element_tree_to_json(tree, loot_rows, category):
    root = tree.getroot()
    entity_key = root.get("type", "common")

    entity_dict = {}
    for k, v in root.attrib.items():
        if k != "type":
            try:
                if v.lower() == "true": entity_dict[k] = True
                elif v.lower() == "false": entity_dict[k] = False
                elif "." in v: entity_dict[k] = float(v)
                else: entity_dict[k] = int(v)
            except ValueError:
                entity_dict[k] = v

    stats_dict = {}
    stats_el = root.find("stats")
    if stats_el is not None:
        for s in stats_el:
            stat_name = s.tag
            if "min" in s.attrib or "max" in s.attrib:
                s_dict = {}
                for sk, sv in s.attrib.items():
                    try: s_dict[sk] = int(sv) if sv.isdigit() else float(sv)
                    except: s_dict[sk] = sv
                stats_dict[stat_name] = s_dict
            elif "value" in s.attrib:
                try: stats_dict[stat_name] = float(s.get("value"))
                except: stats_dict[stat_name] = s.get("value")
    if stats_dict: entity_dict["stats"] = stats_dict

    clothes_dict = {slot: None for slot in ['head', 'util', 'hair', 'facial', 'feet', 'hand', 'body', 'arms', 'legs']}
    clothes_el = root.find("clothes")
    if clothes_el is not None:
        for slot_el in clothes_el:
            c = slot_el.find("cloth")
            if c is not None and c.get("name"):
                clothes_dict[slot_el.tag] = c.get("name")
    if clothes_el is not None: entity_dict["clothes"] = clothes_dict

    vis_dict = {}
    vis_el = root.find("visuals")
    if vis_el is not None:
        for sp in vis_el.findall("sprite"):
            vis_dict[sp.get("id", "center")] = sp.get("file", "")
    if vis_dict: entity_dict["visuals"] = vis_dict

    sound_dict = {}
    sound_el = root.find("sound")
    if sound_el is not None:
        for snd in sound_el: sound_dict[snd.tag] = snd.get("src", "")
    if sound_dict: entity_dict["sound"] = sound_dict

    loot_list = []
    for r in loot_rows:
        target_val = r["target"].text.strip()
        if not target_val: continue
        entry = {}
        if r["mode"].text == "type": entry["type"] = target_val
        else: entry["item"] = target_val

        min_val = r["min"].text.strip()
        max_val = r["max"].text.strip()
        chance_val = r["chance"].text.strip()

        if min_val:
            try: entry["min"] = int(min_val)
            except: entry["min"] = min_val
        if max_val:
            try: entry["max"] = int(max_val)
            except: entry["max"] = max_val
        if chance_val:
            try: entry["chance"] = float(chance_val)
            except: entry["chance"] = chance_val
        loot_list.append(entry)
    entity_dict["loot"] = loot_list

    cat_low = category.lower()
    if cat_low == "zombie": return {"zombies": {entity_key: entity_dict}}
    elif cat_low == "npc": return {"npcs": {entity_key: entity_dict}}
    elif cat_low == "animal": return {"animals": {entity_key: entity_dict}}
    elif cat_low == "player": return {"player": entity_dict}
    return {f"{cat_low}s": {entity_key: entity_dict}}

class EntityEditor:
    def __init__(self, y_offset, width, height, font, all_sprites):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        self.all_sprites = all_sprites 
        
        self.tab_bar_h = 36
        self.sidebar_w = 300
        
        # Dynamic discovery of categories from mod data directory
        self.categories = self._resolve_categories()
        self.active_category = list(self.categories.keys())[0] if self.categories else "Zombie"
        self.tree_structure = []
        self.folder_expanded = {}

        self.open_tabs = []
        self.active_tab_idx = -1
        self.tab_scroll_x = 0
        self.max_tab_scroll = 0
        self.dragging_tab_scroll = False
        self.tab_scroll_start_x = 0
        self.tab_scroll_start_offset = 0
        self.tab_thumb_rect = None
        self.close_confirm_dialog = None
        self.new_entity_dialog = None

        self.item_opts = [{"label": "None", "value": "", "icon": None}]
        self.item_type_opts = []
        self.cloth_opts = [{"label": "None", "value": "", "icon": None}]
        self.cloth_sprites = {} 
        self._build_options()
        
        self.sidebar_scroll = 0
        self.max_sidebar_scroll = 0
        self.dragging_sidebar = False
        self.sidebar_start_y = 0
        self.sidebar_start_offset = 0
        self.sidebar_thumb_rect = None

        self.dragging_form = False
        self.form_start_y = 0
        self.form_start_offset = 0
        self.form_thumb_rect = None
        
        cat_opts = [{"label": c, "value": c} for c in self.categories.keys()]
        self.category_dropdown = UIDropdown(10, self.y_offset + 38, self.sidebar_w - 20, 30, self.font, cat_opts, self.active_category)
        self.search_input = UITextBox(10, self.y_offset + 74, self.sidebar_w - 20, 28, self.font, "")
        self.new_btn = pygame.Rect(10, self.y_offset + 108, self.sidebar_w - 20, 30)

        self.save_btn = pygame.Rect(0, 0, 130, 35)
        self.duplicate_btn = pygame.Rect(0, 0, 130, 35)
        self.delete_btn = pygame.Rect(0, 0, 110, 35)
        self.code_btn = pygame.Rect(0, 0, 110, 35)
        self.add_loot_btn = pygame.Rect(0, 0, 120, 30)
        self.edit_sprite_btn = pygame.Rect(0, 0, 140, 30)
        
        self.refresh_file_list()
        first_row = next((r for r in self.get_visible_rows() if r["type"] == "file"), None)
        if first_row:
            self.open_tab_file(first_row["rel_path"])

    def _resolve_categories(self):
        """Dynamically scans existing data directories without creating any folders."""
        base_data = get_data_dir()
        vanilla_data = os.path.join(LIB_ROOT, 'data')

        known = {
            "Zombie": "zombie", "NPC": "npc", "Animal": "animals",
            "Player": "player", "Vehicle": "vehicle", "Clothes": "clothes",
            "Radio": "radio", "Items": "items", "Map": "map"
        }
        cats = {}

        # 1. Discover whatever actually exists in active mod
        if os.path.exists(base_data):
            try:
                for entry in sorted(os.listdir(base_data)):
                    full_p = os.path.join(base_data, entry)
                    if os.path.isdir(full_p):
                        matched = next((k for k, v in known.items() if v == entry.lower() or k.lower() == entry.lower()), entry.capitalize())
                        cats[matched] = full_p
            except OSError: pass

        # 2. Add remaining known categories pointing to mod or vanilla
        for label, folder in known.items():
            if label not in cats:
                mod_sub = os.path.join(base_data, folder)
                vanilla_sub = os.path.join(vanilla_data, folder)
                cats[label] = mod_sub if os.path.exists(mod_sub) else (vanilla_sub if os.path.exists(vanilla_sub) else mod_sub)
        return cats

    def reload_for_mod(self, all_sprites):
        """Called when active mod changes to refresh sprites, options, and file paths."""
        self.all_sprites = all_sprites
        self.categories = self._resolve_categories()
        if self.active_category not in self.categories:
            self.active_category = list(self.categories.keys())[0] if self.categories else "Zombie"
        self.category_dropdown.options = [{"label": c, "value": c} for c in self.categories.keys()]
        self.category_dropdown.selected_value = self.active_category
        self.category_dropdown._update_label()
        self._build_options()
        self.refresh_file_list()

    def _build_options(self):
        types = set(["container", "weapon", "food", "tool", "ammo", "medical", "material", "cloth", "general"])
        
        c_dir = self.categories.get("Clothes")
        if c_dir and os.path.exists(c_dir):
            for root_d, dirs, files in os.walk(c_dir):
                for f in files:
                    if f.endswith(".xml"):
                        try:
                            root = ET.parse(os.path.join(root_d, f)).getroot()
                            name = root.get("name")
                            t = root.get("type")
                            if t: types.add(t)
                            sprite_node = root.find("properties/sprite")
                            sprite_file = sprite_node.get("file") if sprite_node is not None else ""
                            if name:
                                icon = self.all_sprites.get(name)
                                self.cloth_opts.append({"label": name, "value": name, "icon": icon})
                                self.cloth_sprites[name] = sprite_file
                        except Exception: pass
                        
        i_dir = self.categories.get("Items")
        if i_dir and os.path.exists(i_dir):
            for root_d, dirs, files in os.walk(i_dir):
                for f in files:
                    if f.endswith(".xml"):
                        try:
                            root = ET.parse(os.path.join(root_d, f)).getroot()
                            name = root.get("name")
                            t = root.get("type")
                            if t: types.add(t)
                            if name: 
                                icon = self.all_sprites.get(name)
                                self.item_opts.append({"label": name, "value": name, "icon": icon})
                        except Exception: pass

        self.item_type_opts = [{"label": t, "value": t} for t in sorted(types)]

    def get_subfolders(self, cat_dir):
        folders = []
        if cat_dir and os.path.exists(cat_dir):
            try:
                for item in sorted(os.listdir(cat_dir), key=str.lower):
                    if os.path.isdir(os.path.join(cat_dir, item)):
                        folders.append(item)
            except OSError: pass
        return folders

    def get_subfolder_options(self, cat_name):
        cat_dir = self.categories.get(cat_name, "")
        folders = self.get_subfolders(cat_dir)
        return [{"label": "/ (Root)", "value": ""}] + [{"label": f, "value": f} for f in folders]

    def refresh_file_list(self):
        cat_dir = self.categories.get(self.active_category, "")
        self.tree_structure = []
        if not cat_dir or not os.path.exists(cat_dir): return

        try: entries = sorted(os.listdir(cat_dir), key=str.lower)
        except OSError: return

        for f in entries:
            fp = os.path.join(cat_dir, f)
            if os.path.isfile(fp) and (f.endswith('.xml') or f.endswith('.json')):
                self.tree_structure.append({"type": "file", "name": f, "subfolder": "", "rel_path": f})

        subfolders = self.get_subfolders(cat_dir)
        for s in subfolders:
            sub_path = os.path.join(cat_dir, s)
            sub_files = []
            try: sub_entries = sorted(os.listdir(sub_path), key=str.lower)
            except OSError: sub_entries = []
            for f in sub_entries:
                if f.endswith('.xml') or f.endswith('.json'):
                    sub_files.append({"type": "file", "name": f, "subfolder": s, "rel_path": f"{s}/{f}"})
            self.tree_structure.append({"type": "folder", "name": s, "files": sub_files})

    def get_visible_rows(self):
        query = self.search_input.text.strip().lower()
        rows = []
        for item in self.tree_structure:
            if item["type"] == "file":
                if not query or query in item["name"].lower():
                    rows.append({"type": "file", "name": item["name"], "subfolder": "", "rel_path": item["rel_path"], "indent": 15})
            elif item["type"] == "folder":
                folder_name = item["name"]
                matching = [f for f in item["files"] if not query or query in f["name"].lower() or query in folder_name.lower()]
                if query and not matching:
                    continue
                is_expanded = self.folder_expanded.get(folder_name, False) or bool(query)
                rows.append({"type": "folder", "name": folder_name, "expanded": is_expanded, "indent": 10})
                if is_expanded:
                    for cf in matching:
                        rows.append({"type": "file", "name": cf["name"], "subfolder": folder_name, "rel_path": cf["rel_path"], "indent": 28})
        return rows

    def get_current_sprite_path(self, tab):
        """Finds sprite path checking Mod first, then Vanilla fallback."""
        if not tab: return None
        base_img = None
        root = tab["tree"].getroot()

        for sprite in root.findall(".//visuals/sprite"):
            if sprite.get("id") in ["center", "top", "body"] or base_img is None:
                base_img = sprite.get("file")
                if sprite.get("id") in ["center", "top", "body"]: break

        if not base_img:
            sprite_node = root.find(".//sprite")
            if sprite_node is not None:
                base_img = sprite_node.get("file")

        if not base_img and tab["filename"] and tab["filename"] is not False:
            base_img = os.path.splitext(tab["filename"])[0]

        if not base_img: return None

        base_fname = os.path.basename(base_img)
        stem = os.path.splitext(base_fname)[0]
        candidates = [base_fname] if base_fname.endswith('.png') else [base_fname, f"{stem}.png"]

        # Search Mod sprites first, then Vanilla fallback
        search_roots = [get_sprites_dir(), os.path.join(LIB_ROOT, 'sprites')]
        subdirs = [tab["category"].lower(), 'items', 'clothes', 'zombie', 'player', 'npc', 'animals', 'vehicle', 'map', 'editor']

        for s_root in search_roots:
            if not os.path.exists(s_root): continue
            for sub in subdirs:
                for c_file in candidates:
                    p = os.path.join(s_root, sub, c_file)
                    if os.path.exists(p): return p

        target_name = base_fname if base_fname.endswith('.png') else f"{stem}.png"
        return os.path.join(get_sprites_dir(), tab["category"].lower(), target_name)

    def ensure_tab_visible(self, idx):
        if not (0 <= idx < len(self.open_tabs)): return
        start_x = self.sidebar_w
        view_w = self.width - start_x
        rel_x = 0
        target_left, target_right = 0, 0

        for i, tab in enumerate(self.open_tabs):
            fname = tab["filename"] or tab["filename_input"].text or "new_entity"
            modified = self.is_tab_modified(tab)
            display_name = f"*{fname}" if modified else fname
            text_w = self.font.size(display_name)[0]
            tab_w = max(90, text_w + 44)

            if i == idx:
                target_left, target_right = rel_x, rel_x + tab_w
            rel_x += tab_w + 2

        total_w = rel_x - 2 if rel_x > 0 else 0
        self.max_tab_scroll = max(0, total_w - view_w)

        if target_right > self.tab_scroll_x + view_w:
            self.tab_scroll_x = (target_right + 15) - view_w
        elif target_left < self.tab_scroll_x:
            self.tab_scroll_x = max(0, target_left - 15)

        self.tab_scroll_x = max(0, min(self.max_tab_scroll, self.tab_scroll_x))

    def get_current_tab(self):
        if 0 <= self.active_tab_idx < len(self.open_tabs):
            return self.open_tabs[self.active_tab_idx]
        return None

    def get_tab_snapshot(self, tab):
        return {
            "subfolder": tab.get("subfolder", ""),
            "fname": tab["filename_input"].text.strip(),
            "root_tag": tab["root_tag_input"].text.strip(),
            "fields": [(f["path"], f["attr"], f["input"].text.strip()) for f in tab["fields"]],
            "loot": [(r["mode"].text, r["target"].text, r["min"].text.strip(), r["max"].text.strip(), r["chance"].text.strip()) for r in tab["loot_rows"]]
        }

    def is_tab_modified(self, tab):
        if not tab.get("saved_snapshot"): return False
        return self.get_tab_snapshot(tab) != tab["saved_snapshot"]

    def _build_loot_row(self, mode="item", target="", min_val="1", max_val="1", chance_val="1.0", attr_name="item"):
        mode_opts = [{"label": "Item", "value": "item"}, {"label": "Type", "value": "type"}]
        opts = self.item_type_opts if mode == "type" else self.item_opts
        return {
            "mode": UIDropdown(0, 0, 85, 28, self.font, mode_opts, mode),
            "last_mode": mode,
            "target": UIDropdown(0, 0, 220, 28, self.font, opts, target, searchable=True),
            "min": UITextBox(0, 0, 45, 28, self.font, str(min_val)),
            "max": UITextBox(0, 0, 45, 28, self.font, str(max_val)),
            "chance": UITextBox(0, 0, 60, 28, self.font, str(chance_val)),
            "del_btn": pygame.Rect(0, 0, 30, 28),
            "attr_name": attr_name
        }

    def create_tab_structure(self, filename, tree, subfolder="", rel_path=None, is_json=False):
        root = tree.getroot()
        fields = []
        loot_rows = []
        detected_loot_tag = ["loot"]

        HEALTH_STEPS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        SPEED_STEPS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        STAT_STEPS = [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        def create_field(path, attr, val, opts=None):
            t_val = str(val).lower()
            tag_name = path.split('/')[-1].split('[')[0] if path else root.tag
            is_text_attr = attr.lower() in ["text", "#text", "description", "message"]

            if opts:
                ui_elem = UIDropdown(0, 0, 300, 28, self.font, opts, val, searchable=True)
            elif is_text_attr:
                ui_elem = UITextArea(0, 0, 360, 85, self.font, val)
            elif t_val in ["true", "false"]:
                ui_elem = UIToggle(0, 0, 100, 28, self.font, t_val == "true")
            elif tag_name == "health":
                ui_elem = UIStepButton(0, 0, 100, 28, self.font, val, HEALTH_STEPS)
            elif tag_name in ["speed", "max_speed"]:
                ui_elem = UIStepButton(0, 0, 100, 28, self.font, val, SPEED_STEPS)
            elif tag_name in ["attack", "xp", "infection"]:
                ui_elem = UIStepButton(0, 0, 100, 28, self.font, val, STAT_STEPS)
            else:
                ui_elem = UITextBox(0, 0, 300, 28, self.font, val)
            return {"path": path, "attr": attr, "input": ui_elem}

        def traverse(node, path):
            if node.tag in ["visuals", "sound"]: return
            if node.tag in ["loot", "drop"]:
                detected_loot_tag[0] = node.tag
                for item in node.findall("item"):
                    is_type = item.get("type") is not None
                    mode = "type" if is_type else "item"
                    if is_type:
                        target_val = item.get("type", "")
                        attr_name = "type"
                    else:
                        target_val = item.get("item")
                        attr_name = "item"
                        if target_val is None:
                            target_val = item.get("name", "")
                            attr_name = "name"

                    loot_rows.append(self._build_loot_row(
                        mode=mode,
                        target=target_val,
                        min_val=item.get("min", "1"),
                        max_val=item.get("max", "1"),
                        chance_val=item.get("chance", "1.0"),
                        attr_name=attr_name
                    ))
                return

            if "clothes" in path and node.tag in ['head', 'util', 'hair', 'facial', 'feet', 'hand', 'body', 'arms', 'legs']:
                cloth_node = node.find('cloth')
                val = cloth_node.get('name', '') if cloth_node is not None else ""
                child_path = f"{path}/{node.tag}[1]"
                fields.append(create_field(child_path, "cloth_name", val, opts=self.cloth_opts))
                return 

            for k, v in node.attrib.items():
                fields.append(create_field(path, k, v))
                
            if len(node) == 0:
                text_val = node.text.strip() if node.text else ""
                if text_val or not node.attrib:
                    fields.append(create_field(path, "#text", text_val))
                
            tag_counts = {}
            for child in node:
                tag = child.tag
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                child_path = f"{path}/{tag}[{tag_counts[tag]}]" if path else f"{tag}[{tag_counts[tag]}]"
                traverse(child, child_path)

        traverse(root, "")

        ext = ".json" if is_json else CATEGORY_EXTENSIONS.get(self.active_category, ".xml")
        fname_val = filename if filename is not False else f"new_{self.active_category.lower()}{ext}"
        tab = {
            "category": self.active_category,
            "subfolder": subfolder,
            "filename": filename,
            "rel_path": rel_path if filename is not False else False,
            "is_json": is_json,
            "filename_input": UITextBox(0, 0, 200, 30, self.font, fname_val),
            "root_tag_input": UITextBox(0, 0, 150, 30, self.font, root.tag),
            "root_tag": root.tag,
            "tree": tree,
            "fields": fields,
            "loot_rows": loot_rows,
            "loot_tag": detected_loot_tag[0],
            "form_scroll": 0,
            "max_form_scroll": 0
        }
        tab["saved_snapshot"] = self.get_tab_snapshot(tab)
        return tab

    def open_tab_file(self, rel_path):
        cat_dir = self.categories.get(self.active_category, "")
        for i, tab in enumerate(self.open_tabs):
            if tab["category"] == self.active_category and tab["rel_path"] == rel_path:
                self.active_tab_idx = i
                self.layout_form()
                self.ensure_tab_visible(self.active_tab_idx)
                return

        is_json = False
        if rel_path is False:
            ext = CATEGORY_EXTENSIONS.get(self.active_category, ".xml")
            is_json = (ext == ".json")
            bp = BOILERPLATES.get(self.active_category, BOILERPLATES["Items"])
            if is_json:
                try: tree = json_to_element_tree(json.loads(bp), self.active_category)
                except: tree = ET.ElementTree(ET.Element(self.active_category.lower()))
            else:
                tree = ET.ElementTree(ET.fromstring(bp))
            filename = False
            subfolder = ""
        else:
            path = os.path.join(cat_dir, rel_path)
            subfolder = os.path.dirname(rel_path).replace('\\', '/')
            filename = os.path.basename(rel_path)
            is_json = filename.endswith('.json')

            if is_json:
                try:
                    with open(path, 'r', encoding='utf-8') as jf:
                        j_data = json.load(jf)
                    tree = json_to_element_tree(j_data, self.active_category)
                except Exception as e:
                    print(f"Error loading JSON entity {rel_path}: {e}")
                    tree = ET.ElementTree(ET.Element(self.active_category.lower()))
            else:
                try: tree = ET.parse(path)
                except Exception as e:
                    print(f"Error loading XML entity {rel_path}: {e}")
                    tree = ET.ElementTree(ET.fromstring(BOILERPLATES.get("Items")))

        new_tab = self.create_tab_structure(filename, tree, subfolder=subfolder, rel_path=rel_path, is_json=is_json)
        self.open_tabs.append(new_tab)
        self.active_tab_idx = len(self.open_tabs) - 1
        self.layout_form()
        self.ensure_tab_visible(self.active_tab_idx)

    def request_close_tab(self, idx):
        if not (0 <= idx < len(self.open_tabs)): return
        tab = self.open_tabs[idx]
        if self.is_tab_modified(tab):
            self.close_confirm_dialog = {
                "idx": idx,
                "name": tab["filename"] or tab["filename_input"].text
            }
        else:
            self._force_close_tab(idx)

    def _force_close_tab(self, idx):
        self.open_tabs.pop(idx)
        if not self.open_tabs:
            self.active_tab_idx = -1
        elif self.active_tab_idx == idx:
            self.active_tab_idx = max(0, idx - 1)
        elif self.active_tab_idx > idx:
            self.active_tab_idx -= 1

        self.layout_form()
        self.ensure_tab_visible(self.active_tab_idx)

    def resize(self, width, height):
        self.width = width
        self.height = height
        self.layout_form()

    def layout_form(self):
        visible_rows = self.get_visible_rows()
        content_h = len(visible_rows) * 28 + 10
        self.max_sidebar_scroll = max(0, content_h - (self.height - self.y_offset - 145))
        
        tab = self.get_current_tab()
        if not tab: return
        
        form_x = self.sidebar_w
        current_y = self.y_offset + self.tab_bar_h + 20 - tab["form_scroll"]
        
        tab["filename_input"].rect.topleft = (form_x + 130, current_y)
        tab["root_tag_input"].rect.topleft = (form_x + 450, current_y)
        current_y += 60
        current_y += 30
        
        for row in tab["fields"]:
            row["input"].rect.topleft = (form_x + 460, current_y)
            if hasattr(row["input"], 'list_rect'):
                row["input"].list_rect.topleft = (form_x + 460, current_y + 28)
            current_y += row["input"].rect.height + 8
            
        has_loot = bool(tab["loot_rows"] or tab["category"] in ["Animal", "Zombie", "Vehicle", "NPC", "Clothes", "Map", "Player"])
        if has_loot:
            current_y += 20
            tab["loot_header_y"] = current_y
            current_y += 55
            
            for row in tab["loot_rows"]:
                row["mode"].rect.topleft = (form_x + 20, current_y)
                row["mode"].list_rect.topleft = (form_x + 20, current_y + 28)
                
                row["target"].rect.topleft = (form_x + 115, current_y)
                row["target"].list_rect.topleft = (form_x + 115, current_y + 28)
                
                row["min"].rect.topleft = (form_x + 345, current_y)
                row["max"].rect.topleft = (form_x + 400, current_y)
                row["chance"].rect.topleft = (form_x + 455, current_y)
                row["del_btn"].topleft = (form_x + 525, current_y)
                current_y += 35
                
            self.add_loot_btn.topleft = (form_x + 20, current_y)
            current_y += 45
        else:
            tab["loot_header_y"] = None
            
        current_y += 10
        self.save_btn.topleft = (form_x + 20, current_y)
        self.duplicate_btn.topleft = (form_x + 165, current_y)
        self.delete_btn.topleft = (form_x + 310, current_y)
        self.code_btn.topleft = (form_x + 435, current_y)

        preview_box_x = self.width - 170
        preview_box_y = self.y_offset + self.tab_bar_h + 15
        self.edit_sprite_btn.topleft = (preview_box_x, preview_box_y + 148)
        self.edit_sprite_btn.width = 140
        
        tab["max_form_scroll"] = max(0, current_y + tab["form_scroll"] - self.height + 40)

    def get_tab_rects(self):
        tab_rects = []
        cur_x = self.sidebar_w - self.tab_scroll_x
        tabs_y = self.y_offset
        
        for i, tab in enumerate(self.open_tabs):
            fname = tab["filename"] or tab["filename_input"].text or "new_entity"
            modified = self.is_tab_modified(tab)
            display_name = f"*{fname}" if modified else fname
            
            text_w = self.font.size(display_name)[0]
            tab_w = max(90, text_w + 44)
            
            tab_rect = pygame.Rect(cur_x, tabs_y, tab_w, self.tab_bar_h)
            close_rect = pygame.Rect(tab_rect.right - 20, tab_rect.y + 10, 16, 16)
            tab_rects.append({
                "index": i,
                "tab": tab,
                "rect": tab_rect,
                "close_rect": close_rect,
                "display_name": display_name,
                "modified": modified
            })
            cur_x += tab_w + 2
            
        total_w = (cur_x + self.tab_scroll_x) - self.sidebar_w
        view_w = self.width - self.sidebar_w
        self.max_tab_scroll = max(0, total_w - view_w)
        return tab_rects

    def save_current_tab(self):
        tab = self.get_current_tab()
        if not tab: return
        
        fname = tab["filename_input"].text.strip()
        if not fname: return
        ext = ".json" if tab.get("is_json") else CATEGORY_EXTENSIONS.get(tab["category"], ".xml")
        if not fname.endswith(('.xml', '.json')): fname += ext
        
        root = tab["tree"].getroot()
        root.tag = tab["root_tag_input"].text.strip() or tab["root_tag"]
        
        def get_node(parent, path_str):
            if not path_str: return parent
            curr = parent
            for p in path_str.split('/'):
                tag = p.split('[')[0]
                idx = int(p.split('[')[1][:-1]) - 1 if '[' in p else 0
                found = curr.findall(tag)
                if len(found) > idx: curr = found[idx]
            return curr

        for f in tab["fields"]:
            node = get_node(root, f["path"])
            if node is not None:
                val = f["input"].text.strip()
                if f["attr"] == "cloth_name":
                    node.clear() 
                    if val: ET.SubElement(node, "cloth", {"name": val})
                elif f["attr"] == "#text":
                    node.text = val
                else:
                    node.set(f["attr"], val)
                    
        cat_dir = self.categories[tab["category"]]
        sub = tab.get("subfolder", "")
        target_dir = os.path.join(cat_dir, sub) if sub else cat_dir
        
        # Generated only on user save action
        os.makedirs(target_dir, exist_ok=True)
        path = os.path.join(target_dir, fname)

        if fname.endswith('.json'):
            json_data = element_tree_to_json(tab["tree"], tab["loot_rows"], tab["category"])
            with open(path, 'w', encoding='utf-8') as jf:
                json.dump(json_data, jf, indent=2)
        else:
            loot_tag = tab.get("loot_tag", "loot")
            if tab["loot_rows"] or tab["category"] in ["Animal", "Zombie", "Vehicle", "NPC", "Clothes", "Map"]:
                loot_node = root.find(loot_tag)
                if loot_node is not None: loot_node.clear()
                else: loot_node = ET.SubElement(root, loot_tag)
                    
                for row in tab["loot_rows"]:
                    mode = row["mode"].text
                    target_val = row["target"].text.strip()
                    if not target_val: continue
                    attribs = {"type": target_val} if mode == "type" else {"item": target_val}
                    if row["min"].text.strip(): attribs["min"] = row["min"].text.strip()
                    if row["max"].text.strip(): attribs["max"] = row["max"].text.strip()
                    if row["chance"].text.strip(): attribs["chance"] = row["chance"].text.strip()
                    ET.SubElement(loot_node, "item", attribs)

            tree = ET.ElementTree(root)
            ET.indent(tree, space="    ", level=0)
            tree.write(path, encoding="utf-8", xml_declaration=True)
        
        old_rel = tab.get("rel_path")
        new_rel = f"{sub}/{fname}" if sub else fname
        if old_rel and old_rel != new_rel and tab["filename"] is not False:
            old_path = os.path.join(cat_dir, old_rel)
            if os.path.exists(old_path):
                try: os.remove(old_path)
                except Exception: pass
                
        tab["filename"] = fname
        tab["rel_path"] = new_rel
        tab["is_json"] = fname.endswith('.json')
        tab["saved_snapshot"] = self.get_tab_snapshot(tab)
        self.refresh_file_list()

    def duplicate_current_tab(self):
        tab = self.get_current_tab()
        if not tab or tab["filename"] is False: return

        base_name = tab["filename"]
        ext = os.path.splitext(base_name)[1]
        base_stem = os.path.splitext(base_name)[0]
        base_no_idx = re.sub(r'_\d+$', '', base_stem)
        
        cat_dir = self.categories[tab["category"]]
        sub = tab.get("subfolder", "")
        target_dir = os.path.join(cat_dir, sub) if sub else cat_dir

        counter = 1
        while True:
            dup_fname = f"{base_no_idx}_{counter}{ext}"
            if not os.path.exists(os.path.join(target_dir, dup_fname)):
                break
            counter += 1

        self.save_current_tab()
        src_path = os.path.join(target_dir, tab["filename"])
        dup_path = os.path.join(target_dir, dup_fname)
        with open(src_path, 'r', encoding='utf-8') as src:
            with open(dup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())

        self.refresh_file_list()
        new_rel = f"{sub}/{dup_fname}" if sub else dup_fname
        self.open_tab_file(new_rel)

    def delete_current_tab(self):
        tab = self.get_current_tab()
        if not tab: return
        if tab.get("rel_path") and tab["filename"] is not False:
            path = os.path.join(self.categories[tab["category"]], tab["rel_path"])
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass
        self._force_close_tab(self.active_tab_idx)
        self.refresh_file_list()

    def get_preview_image(self):
        tab = self.get_current_tab()
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        if not tab: return surf
        
        base_img = None
        root = tab["tree"].getroot()
        
        for sprite in root.findall(".//visuals/sprite"):
            if sprite.get("id") in ["center", "top", "body"] or base_img is None:
                base_img = sprite.get("file")
                if sprite.get("id") in ["center", "top", "body"]: break
        
        if not base_img:
            sprite_node = root.find(".//sprite")
            if sprite_node is not None: base_img = sprite_node.get("file")

        if not base_img and tab["filename"] and tab["filename"] is not False:
            base_img = os.path.splitext(tab["filename"])[0]
                
        def load_img(fname):
            if not fname: return None
            base_fname = os.path.basename(fname)
            stem = os.path.splitext(base_fname)[0]
            if stem in self.all_sprites: return self.all_sprites[stem]
            if base_fname in self.all_sprites: return self.all_sprites[base_fname]
            
            # Check Mod sprites first, then Vanilla fallback
            candidates = [base_fname] if base_fname.endswith('.png') else [base_fname, f"{stem}.png"]
            search_dirs = [get_sprites_dir(), os.path.join(LIB_ROOT, 'sprites')]
            subdirs = ['items', 'clothes', 'zombie', 'player', 'npc', 'animals', 'vehicle', 'map']
                
            for s_root in search_dirs:
                if not os.path.exists(s_root): continue
                for sub in subdirs:
                    for c_file in candidates:
                        p = os.path.join(s_root, sub, c_file)
                        if os.path.exists(p):
                            try:
                                img = pygame.image.load(p).convert_alpha()
                                return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                            except Exception: pass
            return None

        img = None
        item_name = root.get("name")
        if item_name and item_name in self.all_sprites: img = self.all_sprites[item_name]
        if not img: img = load_img(base_img)
        if img: surf.blit(img, (0, 0))
            
        layer_order = ['legs', 'feet', 'body', 'arms', 'head', 'facial', 'hair', 'util', 'hand']
        clothes_to_draw = []
        for f in tab["fields"]:
            if "clothes" in f["path"] and f["attr"] == "cloth_name":
                tag = f["path"].split('/')[-1].split('[')[0]
                if tag in layer_order:
                    c_name = f["input"].text.strip()
                    if c_name and c_name in self.cloth_sprites:
                        c_img = load_img(self.cloth_sprites[c_name])
                        if c_img: clothes_to_draw.append((layer_order.index(tag), c_img))
                            
        clothes_to_draw.sort(key=lambda x: x[0]) 
        for _, c_img in clothes_to_draw: surf.blit(c_img, (0, 0))
        return surf

    def handle_event(self, event):
        if self.new_entity_dialog:
            modal_rect = pygame.Rect(self.width//2 - 270, self.height//2 - 130, 540, 260)
            create_btn = pygame.Rect(modal_rect.x + 130, modal_rect.bottom - 45, 130, 34)
            cancel_btn = pygame.Rect(modal_rect.x + 280, modal_rect.bottom - 45, 110, 34)
            
            c_dd = self.new_entity_dialog["cat_dd"]
            s_dd = self.new_entity_dialog["sub_dd"]
            n_box = self.new_entity_dialog["name_box"]

            if c_dd.expanded and c_dd.handle_event(event):
                if c_dd.text != self.new_entity_dialog["last_cat"]:
                    self.new_entity_dialog["last_cat"] = c_dd.text
                    s_dd.options = self.get_subfolder_options(c_dd.text)
                    s_dd.selected_value = ""
                    s_dd._update_label()
                    ext = CATEGORY_EXTENSIONS.get(c_dd.text, ".xml")
                    n_box.text = f"new_{c_dd.text.lower()}{ext}"
                return True

            if s_dd.expanded and s_dd.handle_event(event): return True

            if c_dd.handle_event(event):
                if c_dd.text != self.new_entity_dialog["last_cat"]:
                    self.new_entity_dialog["last_cat"] = c_dd.text
                    s_dd.options = self.get_subfolder_options(c_dd.text)
                    s_dd.selected_value = ""
                    s_dd._update_label()
                    ext = CATEGORY_EXTENSIONS.get(c_dd.text, ".xml")
                    n_box.text = f"new_{c_dd.text.lower()}{ext}"
                return True

            if s_dd.handle_event(event): return True
            if n_box.handle_event(event): return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if create_btn.collidepoint(event.pos):
                    chosen_cat = c_dd.text or self.active_category
                    chosen_sub = s_dd.text
                    name = n_box.text.strip()
                    if name:
                        ext = CATEGORY_EXTENSIONS.get(chosen_cat, ".xml")
                        if not name.endswith(('.xml', '.json')): name += ext
                        
                        cat_dir = self.categories[chosen_cat]
                        target_dir = os.path.join(cat_dir, chosen_sub) if chosen_sub else cat_dir
                        
                        os.makedirs(target_dir, exist_ok=True)
                        full_p = os.path.join(target_dir, name)
                        rel_p = f"{chosen_sub}/{name}" if chosen_sub else name
                        
                        if not os.path.exists(full_p):
                            bp = BOILERPLATES.get(chosen_cat, BOILERPLATES["Items"])
                            with open(full_p, 'w', encoding='utf-8') as f:
                                f.write(bp)

                        self.active_category = chosen_cat
                        self.category_dropdown.selected_value = chosen_cat
                        self.category_dropdown._update_label()
                        self.refresh_file_list()
                        self.open_tab_file(rel_p)

                    self.new_entity_dialog = None
                    return True
                elif cancel_btn.collidepoint(event.pos):
                    self.new_entity_dialog = None
                    return True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.new_entity_dialog = None
                return True
            return True

        if self.close_confirm_dialog:
            modal_rect = pygame.Rect(self.width//2 - 280, self.height//2 - 95, 560, 190)
            btn_y = modal_rect.bottom - 46
            save_close_btn = pygame.Rect(modal_rect.x + 20, btn_y, 150, 34)
            close_nosave_btn = pygame.Rect(modal_rect.x + 185, btn_y, 240, 34)
            cancel_btn = pygame.Rect(modal_rect.x + 440, btn_y, 100, 34)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                idx = self.close_confirm_dialog["idx"]
                if save_close_btn.collidepoint(event.pos):
                    self.save_current_tab()
                    self._force_close_tab(idx)
                    self.close_confirm_dialog = None
                    return True
                elif close_nosave_btn.collidepoint(event.pos):
                    self._force_close_tab(idx)
                    self.close_confirm_dialog = None
                    return True
                elif cancel_btn.collidepoint(event.pos):
                    self.close_confirm_dialog = None
                    return True
            return True

        if event.type == pygame.KEYDOWN:
            if (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_w:
                if 0 <= self.active_tab_idx < len(self.open_tabs):
                    self.request_close_tab(self.active_tab_idx)
                    return True
            if (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_s:
                self.save_current_tab()
                return True

        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_sidebar = False
            self.dragging_form = False
            self.dragging_tab_scroll = False
            
        if event.type == pygame.MOUSEMOTION:
            if self.dragging_sidebar and self.sidebar_thumb_rect and self.max_sidebar_scroll > 0:
                dy = event.pos[1] - self.sidebar_start_y
                track_h = self.height - self.y_offset - 145
                thumb_h = self.sidebar_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    self.sidebar_scroll = max(0, min(self.max_sidebar_scroll, self.sidebar_start_offset + dy * (self.max_sidebar_scroll / track_space)))
                return True

            tab = self.get_current_tab()
            if tab and self.dragging_form and self.form_thumb_rect and tab["max_form_scroll"] > 0:
                dy = event.pos[1] - self.form_start_y
                track_h = self.height - self.y_offset - self.tab_bar_h
                thumb_h = self.form_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    tab["form_scroll"] = max(0, min(tab["max_form_scroll"], self.form_start_offset + dy * (tab["max_form_scroll"] / track_space)))
                    self.layout_form()
                return True

            if self.dragging_tab_scroll and self.max_tab_scroll > 0:
                dx = event.pos[0] - self.tab_scroll_start_x
                track_w = self.width - self.sidebar_w
                thumb_w = self.tab_thumb_rect.width if self.tab_thumb_rect else 40
                movable = track_w - thumb_w
                if movable > 0:
                    self.tab_scroll_x = max(0, min(self.max_tab_scroll, self.tab_scroll_start_offset + (dx / movable) * self.max_tab_scroll))
                return True

        if self.category_dropdown.expanded:
            if self.category_dropdown.handle_event(event):
                if self.category_dropdown.text != self.active_category:
                    self.active_category = self.category_dropdown.text
                    self.search_input.text = ""
                    self.folder_expanded.clear()
                    self.refresh_file_list()
                return True

        if self.category_dropdown.handle_event(event): return True

        if self.search_input.handle_event(event):
            visible_rows = self.get_visible_rows()
            self.max_sidebar_scroll = max(0, len(visible_rows) * 28 + 10 - (self.height - self.y_offset - 145))
            self.sidebar_scroll = max(0, min(self.sidebar_scroll, self.max_sidebar_scroll))
            return True

        tabs_view_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, self.tab_bar_h)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if tabs_view_rect.collidepoint(event.pos):
                if event.button == 4:
                    self.tab_scroll_x = max(0, self.tab_scroll_x - 40)
                    return True
                elif event.button == 5:
                    self.tab_scroll_x = min(self.max_tab_scroll, self.tab_scroll_x + 40)
                    return True
                elif event.button == 1:
                    if self.tab_thumb_rect and self.tab_thumb_rect.collidepoint(event.pos):
                        self.dragging_tab_scroll = True
                        self.tab_scroll_start_x = event.pos[0]
                        self.tab_scroll_start_offset = self.tab_scroll_x
                        return True
                    tab_rects = self.get_tab_rects()
                    for t_info in tab_rects:
                        if t_info["close_rect"].collidepoint(event.pos):
                            self.request_close_tab(t_info["index"])
                            return True
                        elif t_info["rect"].collidepoint(event.pos):
                            self.active_tab_idx = t_info["index"]
                            self.layout_form()
                            self.ensure_tab_visible(self.active_tab_idx)
                            return True

        tab = self.get_current_tab()
        if tab:
            dropdowns = [row["input"] for row in tab["fields"] if isinstance(row["input"], UIDropdown)]
            for r in tab["loot_rows"]:
                dropdowns.append(r["mode"])
                dropdowns.append(r["target"])

            for d in dropdowns:
                if getattr(d, 'expanded', False):
                    if d.handle_event(event): return True

            if tab["filename_input"].handle_event(event): return True
            if tab["root_tag_input"].handle_event(event): return True
            for row in tab["fields"]:
                if row["input"].handle_event(event): return True

            for row in tab["loot_rows"]:
                if row["mode"].handle_event(event):
                    if row["mode"].text != row["last_mode"]:
                        row["last_mode"] = row["mode"].text
                        row["target"].options = self.item_type_opts if row["last_mode"] == "type" else self.item_opts
                        row["target"].selected_value = ""
                        row["target"]._update_label()
                    return True
                if row["target"].handle_event(event): return True
                if row["min"].handle_event(event): return True
                if row["max"].handle_event(event): return True
                if row["chance"].handle_event(event): return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                FocusManager.clear_focus()
                mx, my = event.pos
                if mx > self.sidebar_w:
                    if self.form_thumb_rect and self.form_thumb_rect.collidepoint(mx, my):
                        self.dragging_form = True
                        self.form_start_y = my
                        self.form_start_offset = tab["form_scroll"]
                        return True
                        
                    if hasattr(self, 'add_loot_btn') and self.add_loot_btn.collidepoint(mx, my):
                        tab["loot_rows"].append(self._build_loot_row())
                        self.layout_form()
                        return True
                        
                    for i, row in enumerate(tab["loot_rows"]):
                        if row["del_btn"].collidepoint(mx, my):
                            tab["loot_rows"].pop(i)
                            self.layout_form()
                            return True
                            
                    if self.save_btn.collidepoint(mx, my):
                        self.save_current_tab()
                        return True
                    if self.duplicate_btn.collidepoint(mx, my):
                        self.duplicate_current_tab()
                        return True
                    if self.delete_btn.collidepoint(mx, my):
                        self.delete_current_tab()
                        return True
                    if self.code_btn.collidepoint(mx, my):
                        self.save_current_tab()
                        path = os.path.join(self.categories[tab["category"]], tab.get("rel_path", tab["filename"]))
                        return {"action": "open_in_code", "path": path}

                    if self.edit_sprite_btn.collidepoint(mx, my):
                        sprite_path = self.get_current_sprite_path(tab)
                        if sprite_path:
                            if not os.path.exists(sprite_path):
                                try:
                                    os.makedirs(os.path.dirname(sprite_path), exist_ok=True)
                                    pygame.image.save(pygame.Surface((16, 16), pygame.SRCALPHA), sprite_path)
                                except Exception: pass
                            return {"action": "open_in_art", "path": sprite_path}
                        
            if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] > self.sidebar_w:
                if event.button == 4:
                    tab["form_scroll"] = max(0, tab["form_scroll"] - 40)
                    self.layout_form()
                    return True
                elif event.button == 5:
                    tab["form_scroll"] = min(tab["max_form_scroll"], tab["form_scroll"] + 40)
                    self.layout_form()
                    return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx <= self.sidebar_w:
                if event.button == 1 and self.sidebar_thumb_rect and self.sidebar_thumb_rect.collidepoint(mx, my):
                    self.dragging_sidebar = True
                    self.sidebar_start_y = my
                    self.sidebar_start_offset = self.sidebar_scroll
                    return True
                if event.button == 4:
                    self.sidebar_scroll = max(0, self.sidebar_scroll - 40)
                    return True
                elif event.button == 5:
                    self.sidebar_scroll = min(self.max_sidebar_scroll, self.sidebar_scroll + 40)
                    return True
                if event.button == 1:
                    if self.new_btn.collidepoint(mx, my):
                        modal_rect = pygame.Rect(self.width//2 - 270, self.height//2 - 130, 540, 260)
                        cat_opts = [{"label": c, "value": c} for c in self.categories.keys()]
                        cat_dd = UIDropdown(modal_rect.x + 130, modal_rect.y + 55, 370, 30, self.font, cat_opts, self.active_category)
                        sub_opts = self.get_subfolder_options(self.active_category)
                        sub_dd = UIDropdown(modal_rect.x + 130, modal_rect.y + 100, 370, 30, self.font, sub_opts, "", searchable=True)
                        ext = CATEGORY_EXTENSIONS.get(self.active_category, ".xml")
                        n_box = UITextBox(modal_rect.x + 130, modal_rect.y + 145, 370, 30, self.font, f"new_{self.active_category.lower()}{ext}")
                        n_box.active = True
                        FocusManager.set_focus(n_box)
                        self.new_entity_dialog = {
                            "cat_dd": cat_dd,
                            "sub_dd": sub_dd,
                            "name_box": n_box,
                            "last_cat": self.active_category
                        }
                        return True

                    list_y = self.y_offset + 150 - self.sidebar_scroll
                    visible_rows = self.get_visible_rows()
                    for row in visible_rows:
                        r = pygame.Rect(10, list_y, self.sidebar_w - 30, 26)
                        if r.collidepoint(mx, my) and list_y > self.y_offset + 145:
                            if row["type"] == "folder":
                                f_name = row["name"]
                                self.folder_expanded[f_name] = not self.folder_expanded.get(f_name, False)
                                self.layout_form()
                                return True
                            elif row["type"] == "file":
                                self.open_tab_file(row["rel_path"])
                                return True
                        list_y += 28
        return False

    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect)
        mouse_pos = pygame.mouse.get_pos()
        
        list_view_rect = pygame.Rect(0, self.y_offset + 145, self.sidebar_w, self.height - self.y_offset - 145)
        surface.set_clip(list_view_rect)
        
        active_tab = self.get_current_tab()
        selected_rel = active_tab.get("rel_path") if active_tab else None
        
        visible_rows = self.get_visible_rows()
        list_y = self.y_offset + 150 - self.sidebar_scroll
        for row in visible_rows:
            r = pygame.Rect(10, list_y, self.sidebar_w - 30, 26)
            if row["type"] == "folder":
                icon = "[-] " if row.get("expanded") else "[+] "
                surface.blit(self.font.render(f"{icon}{row['name']}", True, UITheme.WARNING), (row["indent"], list_y + 4))
            else:
                if row["rel_path"] == selected_rel:
                    pygame.draw.rect(surface, UITheme.LIST_HOVER, r, border_radius=4)
                elif r.collidepoint(mouse_pos):
                    pygame.draw.rect(surface, UITheme.HOVER_BG, r, border_radius=4)
                    
                lbl = row["name"]
                if len(lbl) > 23: lbl = lbl[:21] + ".."
                surface.blit(self.font.render(lbl, True, UITheme.TEXT), (row["indent"], list_y + 4))
            list_y += 28
        surface.set_clip(None)
        
        sidebar_header_rect = pygame.Rect(0, self.y_offset, self.sidebar_w, 145)
        pygame.draw.rect(surface, UITheme.PANEL_BG, sidebar_header_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset), (self.sidebar_w, self.height), 2)
        surface.blit(self.font.render("Entity Manager", True, UITheme.WARNING), (20, self.y_offset + 12))
        
        self.category_dropdown.draw(surface)
        self.search_input.draw(surface)
        if not self.search_input.text and not self.search_input.active:
            surface.blit(self.font.render("Search entities...", True, UITheme.TEXT_DIM), (self.search_input.rect.x + 8, self.search_input.rect.y + 6))
        
        draw_styled_button(surface, self.new_btn, "+ New Entity", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)

        content_h = len(visible_rows) * 28 + 10
        self.max_sidebar_scroll = max(0, content_h - list_view_rect.height)
        if self.max_sidebar_scroll > 0:
            track_rect = pygame.Rect(self.sidebar_w - 8, list_view_rect.y, 8, list_view_rect.height)
            thumb_h = max(20, (list_view_rect.height / (list_view_rect.height + self.max_sidebar_scroll)) * list_view_rect.height)
            thumb_y = list_view_rect.y + (self.sidebar_scroll / self.max_sidebar_scroll) * (list_view_rect.height - thumb_h)
            self.sidebar_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.sidebar_thumb_rect, border_radius=4)

        tabs_view_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, self.tab_bar_h)
        pygame.draw.rect(surface, UITheme.PANEL_BG, tabs_view_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset + self.tab_bar_h - 1), (self.width, self.y_offset + self.tab_bar_h - 1))

        prev_clip = surface.get_clip()
        surface.set_clip(tabs_view_rect.clip(prev_clip) if prev_clip else tabs_view_rect)

        tab_rects = self.get_tab_rects()
        for t_info in tab_rects:
            tab_rect = t_info["rect"]
            close_rect = t_info["close_rect"]
            is_active = (t_info["index"] == self.active_tab_idx)
            is_modified = t_info["modified"]
            hovered = tab_rect.collidepoint(mouse_pos)
            
            if is_modified:
                color = (55, 48, 15) if is_active else ((48, 42, 18) if hovered else (38, 35, 18))
                border_color = UITheme.WARNING
                txt_color = UITheme.WARNING
            else:
                color = UITheme.BG if is_active else (UITheme.HOVER_BG if hovered else UITheme.PANEL_BG)
                border_color = UITheme.BORDER
                txt_color = UITheme.TEXT if is_active or hovered else UITheme.TEXT_DIM

            pygame.draw.rect(surface, color, tab_rect)
            pygame.draw.rect(surface, border_color, tab_rect, 1)

            if is_active:
                accent_bar = UITheme.WARNING if is_modified else UITheme.ACCENT
                pygame.draw.rect(surface, accent_bar, (tab_rect.x, tab_rect.y, tab_rect.width, 3))

            txt = self.font.render(t_info["display_name"], True, txt_color)
            surface.blit(txt, (tab_rect.x + 8, tab_rect.centery - txt.get_height()//2))

            c_hover = close_rect.collidepoint(mouse_pos)
            pygame.draw.rect(surface, UITheme.DANGER if c_hover else border_color, close_rect, border_radius=3)
            surface.blit(self.font.render("x", True, UITheme.TEXT), (close_rect.x + 4, close_rect.y + 1))
        surface.set_clip(prev_clip)

        if self.max_tab_scroll > 0:
            track_rect = pygame.Rect(self.sidebar_w, self.y_offset + self.tab_bar_h - 4, self.width - self.sidebar_w, 4)
            pygame.draw.rect(surface, UITheme.PANEL_BG, track_rect)
            thumb_w = max(30, int((tabs_view_rect.width / (tabs_view_rect.width + self.max_tab_scroll)) * track_rect.width))
            thumb_x = track_rect.x + (self.tab_scroll_x / self.max_tab_scroll) * (track_rect.width - thumb_w)
            self.tab_thumb_rect = pygame.Rect(thumb_x, track_rect.y, thumb_w, 4)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.tab_thumb_rect, border_radius=2)
        else:
            self.tab_thumb_rect = None

        tab = self.get_current_tab()
        if tab:
            form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset + self.tab_bar_h, self.width - self.sidebar_w, self.height - self.y_offset - self.tab_bar_h)
            surface.set_clip(form_view_rect)
            form_x = self.sidebar_w
            
            sub_lbl = f"Folder: {tab.get('subfolder') or '/'}"
            surface.blit(self.font.render(sub_lbl, True, UITheme.TEXT_DIM), (form_x + 20, tab["filename_input"].rect.y - 18))

            surface.blit(self.font.render("File Name:", True, UITheme.TEXT_DIM), (form_x + 20, tab["filename_input"].rect.y + 6))
            tab["filename_input"].draw(surface)
            
            surface.blit(self.font.render("Root Tag:", True, UITheme.TEXT_DIM), (form_x + 350, tab["root_tag_input"].rect.y + 6))
            tab["root_tag_input"].draw(surface)
            
            preview_rect = pygame.Rect(self.width - 180, self.y_offset + self.tab_bar_h + 20, 150, 150)
            pygame.draw.rect(surface, UITheme.PANEL_BG, preview_rect, border_radius=8)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, preview_rect, 2, border_radius=8)
            
            img = self.get_preview_image()
            if img:
                scaled_img = pygame.transform.scale(img, (120, 120))
                surface.blit(scaled_img, (preview_rect.centerx - 60, preview_rect.centery - 60))
            else:
                surface.blit(self.font.render("No Sprite", True, UITheme.TEXT_DIM), (preview_rect.centerx - 45, preview_rect.centery - 8))

            draw_styled_button(surface, self.edit_sprite_btn, "Edit Sprite", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)

            col_y = tab["filename_input"].rect.bottom + 15
            surface.blit(self.font.render("Node Path", True, UITheme.WARNING), (form_x + 20, col_y))
            surface.blit(self.font.render("Attribute", True, UITheme.WARNING), (form_x + 240, col_y))
            surface.blit(self.font.render("Value", True, UITheme.WARNING), (form_x + 460, col_y))
            
            path_x = form_x + 20
            attr_x = form_x + 240
            max_path_w = 210
            max_attr_w = 210

            for row in tab["fields"]:
                full_path = row["path"] or f"<{tab['root_tag']}>"
                clean_path = re.sub(r'\[\d+\]', '', full_path).replace("/", " > ")
                
                display_path = clean_path
                path_truncated = False
                if self.font.size(display_path)[0] > max_path_w:
                    path_truncated = True
                    while display_path and self.font.size(display_path + "...")[0] > max_path_w:
                        display_path = display_path[:-1]
                    display_path += "..."

                raw_attr = row["attr"]
                full_attr = "[Content]" if raw_attr == "#text" else ("[Cloth Item]" if raw_attr == "cloth_name" else raw_attr)
                display_attr = full_attr
                attr_truncated = False
                if self.font.size(display_attr)[0] > max_attr_w:
                    attr_truncated = True
                    while display_attr and self.font.size(display_attr + "...")[0] > max_attr_w:
                        display_attr = display_attr[:-1]
                    display_attr += "..."

                surface.blit(self.font.render(display_path, True, UITheme.TEXT_DIM), (path_x, row["input"].rect.y + 6))
                surface.blit(self.font.render(display_attr, True, UITheme.ACCENT), (attr_x, row["input"].rect.y + 6))
                row["input"].draw(surface)

                p_rect = pygame.Rect(path_x, row["input"].rect.y, max_path_w, 28)
                a_rect = pygame.Rect(attr_x, row["input"].rect.y, max_attr_w, 28)
                if path_truncated and p_rect.collidepoint(mouse_pos):
                    register_tooltip(mouse_pos, f"Node: {clean_path}")
                elif attr_truncated and a_rect.collidepoint(mouse_pos):
                    register_tooltip(mouse_pos, f"Attribute: {full_attr}")
                
            if tab.get("loot_header_y") is not None:
                header_title = "Drops:" if tab.get("loot_tag") == "drop" else "Loot Drops:"
                surface.blit(self.font.render(header_title, True, UITheme.WARNING), (form_x + 20, tab["loot_header_y"]))
                surface.blit(self.font.render("Kind", True, UITheme.TEXT_DIM), (form_x + 20, tab["loot_header_y"] + 25))
                surface.blit(self.font.render("Target (Item/Type)", True, UITheme.TEXT_DIM), (form_x + 115, tab["loot_header_y"] + 25))
                surface.blit(self.font.render("Min", True, UITheme.TEXT_DIM), (form_x + 345, tab["loot_header_y"] + 25))
                surface.blit(self.font.render("Max", True, UITheme.TEXT_DIM), (form_x + 400, tab["loot_header_y"] + 25))
                surface.blit(self.font.render("Chance", True, UITheme.TEXT_DIM), (form_x + 455, tab["loot_header_y"] + 25))
                
                for row in tab["loot_rows"]:
                    row["mode"].draw(surface)
                    row["target"].draw(surface)
                    row["min"].draw(surface)
                    row["max"].draw(surface)
                    row["chance"].draw(surface)
                    draw_styled_button(surface, row["del_btn"], "X", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
                    
                draw_styled_button(surface, self.add_loot_btn, "+ Loot", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)

            draw_styled_button(surface, self.save_btn, "Save File", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            if tab["filename"] is not False:
                draw_styled_button(surface, self.duplicate_btn, "Duplicate", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
                draw_styled_button(surface, self.delete_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
                draw_styled_button(surface, self.code_btn, "Code", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)
                
            for row in tab["fields"]:
                if isinstance(row["input"], UIDropdown): row["input"].draw_list(surface)
            for row in tab["loot_rows"]:
                row["mode"].draw_list(surface)
                row["target"].draw_list(surface)
                
            surface.set_clip(None)
            
            if tab["max_form_scroll"] > 0:
                track_rect = pygame.Rect(self.width - 8, form_view_rect.y, 8, form_view_rect.height)
                thumb_h = max(20, (form_view_rect.height / (form_view_rect.height + tab["max_form_scroll"])) * form_view_rect.height)
                thumb_y = form_view_rect.y + (tab["form_scroll"] / tab["max_form_scroll"]) * (form_view_rect.height - thumb_h)
                self.form_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
                pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.form_thumb_rect, border_radius=4)

        if self.category_dropdown.expanded:
            self.category_dropdown.draw_list(surface)

        if self.new_entity_dialog:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            
            modal_rect = pygame.Rect(self.width//2 - 270, self.height//2 - 130, 540, 260)
            pygame.draw.rect(surface, UITheme.PANEL_BG, modal_rect, border_radius=8)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, modal_rect, 2, border_radius=8)
            surface.blit(self.font.render("Create New Entity", True, UITheme.WARNING), (modal_rect.x + 20, modal_rect.y + 15))
            pygame.draw.line(surface, UITheme.BORDER, (modal_rect.x, modal_rect.y + 40), (modal_rect.right, modal_rect.y + 40))

            surface.blit(self.font.render("Category:", True, UITheme.TEXT_DIM), (modal_rect.x + 20, modal_rect.y + 60))
            self.new_entity_dialog["cat_dd"].draw(surface)

            surface.blit(self.font.render("Subfolder:", True, UITheme.TEXT_DIM), (modal_rect.x + 20, modal_rect.y + 105))
            self.new_entity_dialog["sub_dd"].draw(surface)

            surface.blit(self.font.render("File Name:", True, UITheme.TEXT_DIM), (modal_rect.x + 20, modal_rect.y + 150))
            self.new_entity_dialog["name_box"].draw(surface)

            btn_y = modal_rect.bottom - 45
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 130, btn_y, 130, 34), "Create", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 280, btn_y, 110, 34), "Cancel", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

            if self.new_entity_dialog["sub_dd"].expanded:
                self.new_entity_dialog["sub_dd"].draw_list(surface)
            if self.new_entity_dialog["cat_dd"].expanded:
                self.new_entity_dialog["cat_dd"].draw_list(surface)

        if self.close_confirm_dialog:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            
            modal_rect = pygame.Rect(self.width//2 - 280, self.height//2 - 95, 560, 190)
            pygame.draw.rect(surface, UITheme.PANEL_BG, modal_rect, border_radius=8)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, modal_rect, 2, border_radius=8)
            surface.blit(self.font.render("Unsaved Changes", True, UITheme.WARNING), (modal_rect.x + 20, modal_rect.y + 15))
            pygame.draw.line(surface, UITheme.BORDER, (modal_rect.x, modal_rect.y + 40), (modal_rect.right, modal_rect.y + 40))

            surface.blit(self.font.render("You have unsaved changes in:", True, UITheme.TEXT), (modal_rect.x + 25, modal_rect.y + 55))
            surface.blit(self.font.render(self.close_confirm_dialog["name"][:45], True, UITheme.WARNING), (modal_rect.x + 25, modal_rect.y + 82))

            btn_y = modal_rect.bottom - 46
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 20, btn_y, 150, 34), "Save & Close", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 185, btn_y, 240, 34), "Close Without Save", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 440, btn_y, 100, 34), "Cancel", self.font, mouse_pos, UITheme.BORDER, UITheme.BORDER_ACTIVE)