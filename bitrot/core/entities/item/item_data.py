import os
import xml.etree.ElementTree as ET
from core.data.config import DATA_PATH
from core.systems.mod_manager import mod_manager

ITEM_TEMPLATES = {}

# In core/entities/item/item_data.py

def load_item_templates_data(items_dir=DATA_PATH + 'items/'):
    global ITEM_TEMPLATES
    if ITEM_TEMPLATES:
        return
    if not os.path.isdir(items_dir):
        print(f"Warning: Item templates directory not found at '{items_dir}'")
        return

    # --- 1. RECURSIVELY LOAD ITEMS (including subfolders) ---
   

    for root_dir, _, full_paths in mod_manager.vfs_walk(items_dir):
        for filepath in full_paths:
            if not filepath.endswith('.xml'):
                continue
            try:
                tree = ET.parse(filepath)
                root = tree.getroot()
            except Exception as e:
                print(f"Error parsing item XML {filepath}: {e}")
                continue

            name = root.attrib.get('name')
            ttype = root.attrib.get('type')
            disposable_str = root.attrib.get('disposable', 'false')
            disposable = (disposable_str.lower() == 'true')
            
            liquid_str = root.attrib.get('liquid', 'false')
            liquid = (liquid_str.lower() == 'true')

            allow_liquid_str = root.attrib.get('allow_liquid', 'false')
            allow_liquid = (allow_liquid_str.lower() == 'true')

            # Parse allow_type="[type1, type2]"
            allow_type_str = root.attrib.get('allow_type')
            allow_type = [t.strip().lower() for t in allow_type_str.replace('[', '').replace(']', '').split(',') if t.strip()] if allow_type_str else None

            # Parse disallow_type="[type1, type2]"
            disallow_type_str = root.attrib.get('disallow_type')
            disallow_type = [t.strip().lower() for t in disallow_type_str.replace('[', '').replace(']', '').split(',') if t.strip()] if disallow_type_str else None

            allow_belt_str = root.attrib.get('allow_belt', 'false')
            allow_belt = (allow_belt_str.lower() == 'true')

            allow_use_str = root.attrib.get('allow_use', 'false')
            allow_use = (allow_use_str.lower() == 'true')

            # Parse allow_use
            allow_use_str = root.attrib.get('allow_use', 'false')
            allow_use = (allow_use_str.lower() == 'true')

            spawn_amount_str = root.attrib.get('spawn_amount_global', '1')
            spawn_amount_global = int(spawn_amount_str)

            spawn_maptile_str = root.attrib.get('spawn_maptile')
            spawn_maptile = [t.strip() for t in spawn_maptile_str.replace('[', '').replace(']', '').split(',')] if spawn_maptile_str else []

            spawn_layer_str = root.attrib.get('spawn_layer')
            spawn_layer = [int(t.strip()) for t in spawn_layer_str.replace('[', '').replace(']', '').split(',')] if spawn_layer_str else []

            state = root.attrib.get('state')
            tip = root.attrib.get('tip')
            consume_time_str = root.attrib.get('consume_time', '1.0')
            consume_time = float(consume_time_str)

            safe_radius_str = root.attrib.get('safe_radius', '0')
            try:
                safe_radius = int(safe_radius_str)
            except (ValueError, TypeError):
                safe_radius = 0
            
            max_liquid = None
            props_node = root.find('properties')
            if props_node is not None:
                max_liq_node = props_node.find('max_liquid')
                if max_liq_node is not None:
                    try:
                        max_liquid = int(float(max_liq_node.get('value', '0')))
                    except (ValueError, TypeError):
                        max_liquid = None
            
            map_value = None
            props_node = root.find('properties')
            if props_node is not None:
                map_node = props_node.find('map')
                if map_node is not None:
                    map_value = map_node.get('value', '').strip()

            template = {
                'type': ttype, 
                'properties': {}, 
                'state': state, 
                'disposable': disposable, 
                'liquid': liquid, 
                'allow_liquid': allow_liquid, 
                'allow_type': allow_type,
                'disallow_type': disallow_type,
                'allow_belt': allow_belt,
                'allow_use': allow_use,
                'consume_time': consume_time,
                'tip': tip,
                'safe_radius': safe_radius,
                'max_liquid': max_liquid,
                'map_value': map_value,
                'spawn_amount_global': spawn_amount_global,
                'spawn_maptile': spawn_maptile,            
                'spawn_layer': spawn_layer                 
            }

            props_node = root.find('properties')
            if props_node is not None:
                for prop in props_node:
                    template['properties'][prop.tag] = {k: v for k, v in prop.attrib.items()}
                
                text_node = props_node.find('text')
                if text_node is not None:
                    template['text'] = "\n".join(line.strip() for line in text_node.text.strip().split('\n'))
                else:
                    template['text'] = None

                template['effects'] = []

                def parse_status_list(s):
                    if not s: return []
                    return [t.strip() for t in s.replace('[', '').replace(']', '').split(',')]

                global_status = None
                status_node = props_node.find('status')
                if status_node is not None:
                    global_status = status_node.get('value')
                    template['properties']['status'] = {'value': global_status}
                
                require_node = props_node.find('require')
                if require_node is not None:
                    template['properties']['require'] = {k: v for k, v in require_node.attrib.items()}

                max_liq_node = props_node.find('max_liquid')
                if max_liq_node is not None:
                    template['properties']['max_liquid'] = {'value': max_liq_node.get('value', '0')}

                fuel_node = props_node.find('fuel')
                if fuel_node is not None:
                    template['properties']['fuel_type'] = fuel_node.attrib.get('type')
                
                health_node = props_node.find('health')
                if health_node is not None:
                    template['health_min'] = int(health_node.get('min', '30'))
                    template['health_max'] = int(health_node.get('max', '30'))

                remove_node = props_node.find('remove')
                if remove_node is not None:
                    raw_items = remove_node.get('item', '')
                    items_list = [t.strip() for t in raw_items.replace('[', '').replace(']', '').split(',') if t.strip()]
                    template['remove_items'] = items_list
                    template['remove_time'] = float(remove_node.get('time', '1.5'))
                
                # Parse <place> node
                place_node = props_node.find('place')
                if place_node is not None:
                    template['place_items'] = []
                    template['place_time'] = float(place_node.get('time', '1.5'))
                    for p_item in place_node.findall('item'):
                        raw_items = p_item.get('item') or p_item.get('name') or ''
                        p_list = [t.strip() for t in raw_items.replace('[', '').replace(']', '').split(',') if t.strip()]
                        destroy_val = p_item.get('destroy', 'false').lower() == 'true'
                        try:
                            amt = int(p_item.get('amount', '1'))
                        except (ValueError, TypeError):
                            amt = 1
                        template['place_items'].append({
                            'items': p_list,
                            'destroy': destroy_val,
                            'amount': amt
                        })
                else:
                    template['place_items'] = []
                    template['place_time'] = 1.5

                for node in props_node.findall('restore'):
                    status_str = node.get('status')
                    targets = parse_status_list(status_str) if status_str else ([global_status] if global_status else [])
                    
                    if targets:
                        template['effects'].append({
                            'type': 'restore',
                            'targets': targets,
                            'value': int(node.get('value', '0'))
                        })
                    
                    if not status_str and global_status:
                        template['properties']['restore'] = {
                            'value': node.get('value', '0')
                        }

                for node in props_node.findall('reduce'):
                    status_str = node.get('status')
                    targets = parse_status_list(status_str) if status_str else ([global_status] if global_status else [])
                    
                    if targets:
                        template['effects'].append({
                            'type': 'reduce',
                            'targets': targets,
                            'value': int(node.get('value', '0'))
                        })
                    
                    if not status_str and global_status:
                        template['properties']['reduce'] = {
                            'value': node.get('value', '0')
                        }
                    
            spawn_node = root.find('spawn')
            if spawn_node is not None:
                template['spawn_chance'] = float(spawn_node.attrib.get('chance', '0'))

            repair_node = root.find('repair')
            if repair_node is not None:
                template['repair_list'] = []
                for repair_item in repair_node.findall('item'):
                    template['repair_list'].append(repair_item.get('name'))

            template['stats'] = None
            if ttype == 'charm':
                template['attribute_modifiers'] = {}
                attr_node = root.find('attributes')
                if attr_node is not None:
                    for attr in attr_node:
                        template['attribute_modifiers'][attr.tag] = float(attr.get('value', 0))

            loot_node = root.find('loot')
            if loot_node is not None:
                template['loot'] = []
                for loot_item_node in loot_node.findall('item'):
                    loot_item_name = loot_item_node.attrib.get('name')
                    if loot_item_name is None:
                        print(f"Missing 'name' attribute in loot for item: {name}")
                    loot_item_chance = float(loot_item_node.attrib.get('chance', '1.0'))
                    template['loot'].append({'name': loot_item_name, 'chance': loot_item_chance})
            
            template['sounds'] = {}
            sound_node = root.find('sound')
            if sound_node is not None:
                shoot_node = sound_node.find('shoot')
                if shoot_node is not None:
                    template['sounds']['shoot'] = shoot_node.get('src')
                
                reload_node = sound_node.find('reload')
                if reload_node is not None:
                    template['sounds']['reload'] = reload_node.get('src')
                
                noammo_node = sound_node.find('noammo')
                if noammo_node is not None:
                    template['sounds']['noammo'] = noammo_node.get('src')
                
                swing_node = sound_node.find('swing') 
                if swing_node is not None:
                    template['sounds']['swing'] = swing_node.get('src')

                explosion_node = sound_node.find('explosion')
                if explosion_node is not None:
                    template['sounds']['explosion'] = explosion_node.get('src')

            ITEM_TEMPLATES[name] = template

    # --- 2. RECURSIVELY LOAD CLOTHES (including subfolders) ---
    clothes_dir = os.path.join(DATA_PATH, 'clothes')
    if not os.path.exists(clothes_dir):
        alt_clothes = os.path.join(BASE_DIR, 'data.rot', 'lib', 'clothes')
        if os.path.exists(alt_clothes):
            clothes_dir = alt_clothes

    for root_dir, _, full_paths in mod_manager.vfs_walk(clothes_dir):
        for filepath in full_paths:
            if not filepath.endswith('.xml'):
                continue
            try:
                tree = ET.parse(filepath)
                root = tree.getroot()
                if root.tag != 'cloth':
                    continue
                
                name = root.attrib.get('name')
                if not name:
                    continue
                
                template = {
                    'type': root.attrib.get('type'),
                    'properties': {},
                    'consume_time': float(root.attrib.get('consume_time', '1.0'))
                }
                
                builder_str = root.attrib.get('builder', 'false')
                template['builder'] = (builder_str.lower() == 'true')

                hotbar_str = root.attrib.get('hotbar', 'false')
                template['hotbar'] = (hotbar_str.lower() == 'true')

                hide_cloth_str = root.attrib.get('hide_cloth')
                if hide_cloth_str:
                    template['properties']['hide_cloth'] = [t.strip() for t in hide_cloth_str.replace('[', '').replace(']', '').split(',')]

                template['properties']['slot'] = {'value': root.attrib.get('id')}
                
                props_node = root.find('properties')
                if props_node is not None:
                    dur_node = props_node.find('durability')
                    if dur_node is not None:
                        template['properties']['durability'] = {k: v for k, v in dur_node.attrib.items()}
                            
                    def_node = props_node.find('defence')
                    if def_node is not None:
                        template['properties']['defence'] = {'value': def_node.attrib.get('value', '0')}

                    spd_node = props_node.find('speed')
                    if spd_node is not None:
                        template['properties']['speed'] = {'value': spd_node.attrib.get('value', '0')}

                    cap_node = props_node.find('capacity')
                    if cap_node is not None:
                        template['properties']['capacity'] = {'value': cap_node.attrib.get('value', '0')}

                    spr_node = props_node.find('sprite')
                    if spr_node is not None:
                        template['properties']['sprite'] = {'file': spr_node.attrib.get('file')}

                loot_node = root.find('loot')
                if loot_node is not None:
                    template['loot'] = []
                    for loot_item_node in loot_node.findall('item'):
                        loot_item_name = loot_item_node.attrib.get('name')
                        if loot_item_name is None:
                            print(f"Missing 'name' attribute in loot for cloth: {name}")
                        loot_item_chance = float(loot_item_node.attrib.get('chance', '1.0'))
                        template['loot'].append({'name': loot_item_name, 'chance': loot_item_chance})
                        
                ITEM_TEMPLATES[name] = template

            except Exception as e:
                print(f"Error parsing cloth {filepath}: {e}")
    
    print(f"Loaded {len(ITEM_TEMPLATES)} total item/cloth templates.")