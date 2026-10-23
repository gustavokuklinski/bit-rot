# In core/ui/helpers/trait_config_loader.py

import os
import json
from core.data.config import *

def load_trait_definitions():
    from core.systems.mod_manager import mod_manager
    traits = {}
    filepath = mod_manager.get_override_path(os.path.join(DATA_PATH, 'player', 'traits.json'))

    if not os.path.exists(filepath):
        print(f"Warning: Traits JSON definition file not found at {filepath}")
        return {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        root = raw.get('player_traits', raw)

        nodes_to_parse = []
        for pid, pdata in root.get('professions', {}).items():
            nodes_to_parse.append((pid, pdata, True))

        for tid, tdata in root.get('traits', {}).items():
            nodes_to_parse.append((tid, tdata, False))

        for trait_id, t_dict, is_prof in nodes_to_parse:
            try:
                cost = int(t_dict.get('cost', 0))
            except (ValueError, TypeError):
                cost = 0

            trait_data = {
                'cost': cost,
                'stats': {},
                'attributes': {},
                'config_modifiers': {},
                'starting_levels': {},
                'conflicts': list(t_dict.get('disable', [])),
                'recipes': list(t_dict.get('recipe', t_dict.get('recipes', []))),
                'name': t_dict.get('name', trait_id),
                'tooltip': t_dict.get('tooltip', ''),
                'is_profession': is_prof
            }

            # Stats modifiers
            for sname, sval in t_dict.get('stats', {}).items():
                try:
                    trait_data['stats'][sname] = float(sval)
                except (ValueError, TypeError):
                    pass

            # Config modifiers
            for cname, cval in t_dict.get('config', {}).items():
                try:
                    trait_data['config_modifiers'][cname] = float(cval)
                except (ValueError, TypeError):
                    pass

            # Attributes & Starting Levels
            for aname, aval in t_dict.get('attributes', {}).items():
                if aname == 'level' and isinstance(aval, dict):
                    for lvl_attr, lvl_val in aval.items():
                        try:
                            trait_data['starting_levels'][lvl_attr] = int(lvl_val)
                        except (ValueError, TypeError):
                            pass
                else:
                    try:
                        trait_data['attributes'][aname] = float(aval)
                    except (ValueError, TypeError):
                        pass

            traits[trait_id] = trait_data

        print(f"Loaded {len(traits)} traits from traits.json.")

    except Exception as e:
        print(f"Error loading traits JSON: {e}")

    return traits

def load_config_data(filepath):
    from core.systems.mod_manager import mod_manager
    filepath = mod_manager.get_override_path(filepath)

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

save_config_xml = save_config_json

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