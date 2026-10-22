# core/ui/helpers/trait_config_loader.py
import os
import json
import xml.etree.ElementTree as ET
from core.data.config import *

def load_trait_definitions():
    traits = {}
    filepath = os.path.join(DATA_PATH, 'player', 'traits.xml')
    
    if not os.path.exists(filepath):
        print(f"Warning: Traits definition file not found at {filepath}")
        return {}

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        nodes_to_parse = []
        prof_node = root.find('profession')
        if prof_node is not None:
            for t in prof_node.findall('trait'): nodes_to_parse.append((t, True))
            
        traits_node = root.find('traits')
        if traits_node is not None:
            for t in traits_node.findall('trait'): nodes_to_parse.append((t, False))
            
        if prof_node is None and traits_node is None:
            for t in root.findall('trait'): nodes_to_parse.append((t, False))
        
        for trait_node, is_prof in nodes_to_parse:
            trait_id = trait_node.get('id')
            if not trait_id:
                continue
                
            try: cost = int(trait_node.get('cost', 0))
            except ValueError: cost = 0
                
            trait_data = {
                'cost': cost, 
                'stats': {}, 
                'attributes': {},
                'config_modifiers': {}, 
                'starting_levels': {},
                'conflicts': [],
                'recipes': [],
                'name': trait_node.get('name', trait_id),
                'tooltip': trait_node.get('tooltip'),
                'is_profession': is_prof 
            }
            
            stats_node = trait_node.find('stats')
            if stats_node is not None:
                trait_data['stats'] = {}
                for stat_name, val in stats_node.attrib.items():
                    try: trait_data['stats'][stat_name] = float(val)
                    except ValueError: pass

            for config_node in trait_node.findall('config'):
                set_str = config_node.get('set')
                if set_str:
                    clean_str = set_str.strip("[] ")
                    parts = clean_str.split(',')
                    for part in parts:
                        if ':' in part:
                            key, val = part.split(':')
                            try: 
                                trait_data['config_modifiers'][key.strip()] = float(val)
                            except ValueError: 
                                pass

            disable_str = trait_node.get('disable')
            if disable_str:
                clean_str = disable_str.strip("[] ")
                if clean_str:
                    parts = clean_str.split(',')
                    for part in parts:
                        t_id = part.strip()
                        if t_id: trait_data['conflicts'].append(t_id)

            attrs_node = trait_node.find('attributes')
            if attrs_node is not None:
                trait_data['attributes'] = {}
                level_str = attrs_node.get('level')
                if level_str:
                    clean_str = level_str.strip("[] ")
                    if clean_str:
                        parts = clean_str.split(',')
                        for part in parts:
                            if ':' in part:
                                attr_key, lvl_val = part.split(':')
                                try: trait_data['starting_levels'][attr_key.strip()] = int(lvl_val)
                                except ValueError: pass

                for attr_name, val in attrs_node.attrib.items():
                    if attr_name == 'level': continue
                    try: trait_data['attributes'][attr_name] = float(val)
                    except ValueError: pass
            
            for r_node in trait_node.findall('recipe'):
                mag = r_node.get('magazine')
                if mag: trait_data['recipes'].append(mag)

            traits[trait_id] = trait_data

        print(f"Loaded {len(traits)} traits from XML.")
        
    except Exception as e:
        print(f"Error loading traits XML: {e}")
        
    return traits

def load_config_data(filepath):
    if filepath.endswith('.xml'):
        filepath = os.path.splitext(filepath)[0] + '.json'
    if not os.path.exists(filepath):
        print(f"Config file not found: {filepath}")
        return {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        data = raw.get('world', raw.get('preferences', raw))
        return data
    except Exception as e:
        print(f"Error loading config {filepath}: {e}")
        return {}

def save_config_json(data, filepath):
    if filepath.endswith('.xml'):
        filepath = os.path.splitext(filepath)[0] + '.json'
    root_tag = "world" if "world" in os.path.basename(filepath).lower() else "preferences"
    out = {root_tag: data}

    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"Config saved to {filepath}")
    except Exception as e:
        print(f"Error saving config JSON: {e}")

save_config_json = save_config_json  # Seamless backward-compatibility alias

def _load_config_presets(state):
    preset_dir = os.path.join(get_writable_dir(), "data.rot", "save", "config")
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir, exist_ok=True)
    presets = ["world"] 
    try:
        files = [
            f for f in os.listdir(preset_dir) 
            if f.endswith('.json') and not f.startswith("preferences") and not f.startswith("keybinds") and not f.startswith("voip")
        ]
        for f in sorted(files):
            name = os.path.splitext(f)[0]
            if name != 'world' and name not in presets:
                presets.append(name)
    except Exception:
        pass
    state['config_preset_list'] = presets

TRAIT_DEFINITIONS = load_trait_definitions()