import os
import xml.etree.ElementTree as ET
import xml.dom.minidom
from core.data.config import *

def load_trait_definitions():
    traits = {}
    # Assumes the file is at game/data/player/traits.xml
    # We use DATA_PATH from config.py
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
                
            trait_data = {'cost': cost}
            
            # Parse 'stats' modifiers (e.g., infection, stamina)
            stats_node = trait_node.find('stats')
            if stats_node is not None:
                trait_data['stats'] = {}
                for stat_name, val in stats_node.attrib.items():
                    try:
                        trait_data['stats'][stat_name] = float(val)
                    except ValueError:
                        pass

            # Parse 'attributes' modifiers (e.g., strength, lucky)
            attrs_node = trait_node.find('attributes')
            if attrs_node is not None:
                trait_data['attributes'] = {}
                for attr_name, val in attrs_node.attrib.items():
                    try:
                        trait_data['attributes'][attr_name] = float(val)
                    except ValueError:
                        pass
            
            traits[trait_id] = trait_data

        print(f"Loaded {len(traits)} traits from XML.")
        
    except Exception as e:
        print(f"Error loading traits XML: {e}")
        
    return traits

def load_config_data(filepath):
    """Parses the config XML into a dictionary separated by blocks."""
    if not os.path.exists(filepath):
        print(f"Config file not found: {filepath}")
        return {}

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        data = {}
        
        # Parse blocks: game, player, spawning, zombie, etc.
        for child in root:
            block_name = child.tag
            data[block_name] = {}
            for setting in child:
                # Assumes structure <setting_name value="..."/>
                key = setting.tag
                val = setting.get('value')
                display_name = setting.get('name', key)
                data[block_name][key] = {'value': val, 'name': display_name}
        return data
    except Exception as e:
        print(f"Error loading config {filepath}: {e}")
        return {}

def save_config_xml(data, filepath):
    """Saves the settings dictionary back to XML."""
    root = ET.Element("config")
    
    for block_name, settings in data.items():
        block_node = ET.SubElement(root, block_name)
        for key, val_data in settings.items():
            # [CHANGE] Handle the new dictionary structure
            if isinstance(val_data, dict):
                val = val_data.get('value', '')
                name = val_data.get('name', '')
                elem = ET.SubElement(block_node, key, value=str(val))
                if name:
                    elem.set('name', name)
            else:
                # Fallback for legacy/simple data
                ET.SubElement(block_node, key, value=str(val_data))

    try:
        raw_xml = ET.tostring(root, 'utf-8')
        # Pretty print hack
        parsed = xml.dom.minidom.parseString(raw_xml)
        pretty_xml = parsed.toprettyxml(indent="    ")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "w") as f:
            f.write(pretty_xml)
        print(f"Config saved to {filepath}")
    except Exception as e:
        print(f"Error saving config XML: {e}")

def _load_config_presets(state):
    """Loads list of config presets."""
    preset_dir = "./game/save/config"
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)
    
    presets = ["default"] # Always include default
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
