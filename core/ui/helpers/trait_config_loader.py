import os
import xml.etree.ElementTree as ET
import xml.dom.minidom
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
        
        for trait_node in root.findall('trait'):
            trait_id = trait_node.get('id')
            if not trait_id:
                continue
                
            try:
                cost = int(trait_node.get('cost', 0))
            except ValueError:
                cost = 0
                
            trait_data = {
                'cost': cost, 
                'stats': {}, 
                'attributes': {},
                'config_modifiers': {}, # [NEW] Store dynamic config changes
                'starting_levels': {},
                'conflicts': [],
                'recipes': [],
                'name': trait_node.get('name', trait_id),
                'tooltip': trait_node.get('tooltip')
            }
            
            # Parse 'stats'
            stats_node = trait_node.find('stats')
            if stats_node is not None:
                trait_data['stats'] = {}
                for stat_name, val in stats_node.attrib.items():
                    try:
                        trait_data['stats'][stat_name] = float(val)
                    except ValueError:
                        pass

            # [NEW] Parse 'config' modifiers
            # Example: <config set="BASE_PLAYER_VIEW_RADIUS:0.65, PLAYER_SPEED:1.1" />
            config_node = trait_node.find('config')
            if config_node is not None:
                set_str = config_node.get('set')
                if set_str:
                    # Remove brackets just in case, split by comma
                    clean_str = set_str.strip("[] ")
                    parts = clean_str.split(',')
                    for part in parts:
                        if ':' in part:
                            key, val = part.split(':')
                            try:
                                # We store the float value (multiplier) keyed by the config variable name
                                trait_data['config_modifiers'][key.strip()] = float(val)
                            except ValueError:
                                print(f"Error parsing config modifier '{part}' in trait {trait_id}")

            disable_str = trait_node.get('disable')
            if disable_str:
                clean_str = disable_str.strip("[] ")
                if clean_str:
                    parts = clean_str.split(',')
                    for part in parts:
                        t_id = part.strip()
                        if t_id:
                            trait_data['conflicts'].append(t_id)

            # Parse 'attributes'
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
                                try:
                                    trait_data['starting_levels'][attr_key.strip()] = int(lvl_val)
                                except ValueError:
                                    pass

                for attr_name, val in attrs_node.attrib.items():
                    if attr_name == 'level': continue
                    try:
                        trait_data['attributes'][attr_name] = float(val)
                    except ValueError:
                        pass
            
            for r_node in trait_node.findall('recipe'):
                mag = r_node.get('magazine')
                if mag: trait_data['recipes'].append(mag)

            traits[trait_id] = trait_data

        print(f"Loaded {len(traits)} traits from XML.")
        
    except Exception as e:
        print(f"Error loading traits XML: {e}")
        
    return traits

# ... (rest of the file remains unchanged: load_config_data, save_config_xml, _load_config_presets) ...
def load_config_data(filepath):
    """Parses the config XML into a dictionary separated by blocks."""
    if not os.path.exists(filepath):
        print(f"Config file not found: {filepath}")
        return {}

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        data = {}
        
        for child in root:
            block_name = child.tag
            data[block_name] = {}
            for setting in child:
                key = setting.tag
                val = setting.get('value')
                display_name = setting.get('name', key)
                data[block_name][key] = {'value': val, 'name': display_name}
        return data
    except Exception as e:
        print(f"Error loading config {filepath}: {e}")
        return {}

def save_config_xml(data, filepath):
    root = ET.Element("config")
    for block_name, settings in data.items():
        block_node = ET.SubElement(root, block_name)
        for key, val_data in settings.items():
            if isinstance(val_data, dict):
                val = val_data.get('value', '')
                name = val_data.get('name', '')
                elem = ET.SubElement(block_node, key, value=str(val))
                if name:
                    elem.set('name', name)
            else:
                ET.SubElement(block_node, key, value=str(val_data))

    try:
        raw_xml = ET.tostring(root, 'utf-8')
        parsed = xml.dom.minidom.parseString(raw_xml)
        pretty_xml = parsed.toprettyxml(indent="    ")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(pretty_xml)
        print(f"Config saved to {filepath}")
    except Exception as e:
        print(f"Error saving config XML: {e}")

def _load_config_presets(state):
    preset_dir = "./game/save/config"
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)
    presets = ["default"] 
    try:
        files = [f for f in os.listdir(preset_dir) if f.endswith('.xml')]
        for f in files:
            name = f.replace('.xml', '')
            if name != 'default':
                presets.append(name)
    except Exception:
        pass
    state['config_preset_list'] = presets

TRAIT_DEFINITIONS = load_trait_definitions()