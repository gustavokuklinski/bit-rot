import os
import xml.etree.ElementTree as ET
from core.data.config import DATA_PATH

ITEM_TEMPLATES = {}

def load_item_templates_data(items_dir=DATA_PATH + 'items/'):
    global ITEM_TEMPLATES
    if ITEM_TEMPLATES:
        return
    if not os.path.isdir(items_dir):
        print(f"Warning: Item templates directory not found at '{items_dir}'")
        return
    for filename in os.listdir(items_dir):
        if not filename.endswith('.xml'):
            continue
        tree = ET.parse(f"{items_dir}/{filename}")
        root = tree.getroot()
        name = root.attrib.get('name')
        ttype = root.attrib.get('type')
        disposable_str = root.attrib.get('disposable', 'false')
        disposable = (disposable_str.lower() == 'true')
        
        liquid_str = root.attrib.get('liquid', 'false')
        liquid = (liquid_str.lower() == 'true')

        allow_liquid_str = root.attrib.get('allow_liquid', 'false')
        allow_liquid = (allow_liquid_str.lower() == 'true')
        
        allow_belt_str = root.attrib.get('allow_belt', 'false')
        allow_belt = (allow_belt_str.lower() == 'true')

        state = root.attrib.get('state')
        template = {'type': ttype, 'properties': {}, 'state': state, 'disposable': disposable, 'liquid': liquid, 'allow_liquid': allow_liquid, 'allow_belt': allow_belt}

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

            for node in props_node.findall('restore'):
                status_str = node.get('status')
                targets = parse_status_list(status_str) if status_str else ([global_status] if global_status else [])
                
                if targets:
                    template['effects'].append({
                        'type': 'restore',
                        'targets': targets,
                        'min': int(node.get('min', '0')),
                        'max': int(node.get('max', '0'))
                    })
                
                if not status_str and global_status:
                        template['properties']['restore'] = {
                        'min': node.get('min', '0'),
                        'max': node.get('max', '0')
                    }

            for node in props_node.findall('reduce'):
                status_str = node.get('status')
                targets = parse_status_list(status_str) if status_str else ([global_status] if global_status else [])
                
                if targets:
                    template['effects'].append({
                        'type': 'reduce',
                        'targets': targets,
                        'min': int(node.get('min', '0')),
                        'max': int(node.get('max', '0'))
                    })
                
                if not status_str and global_status:
                        template['properties']['reduce'] = {
                        'min': node.get('min', '0'),
                        'max': node.get('max', '0')
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


        ITEM_TEMPLATES[name] = template

    clothes_dir = DATA_PATH + 'clothes/'
    print(f"Loading clothes templates from: {clothes_dir}")
    if not os.path.isdir(clothes_dir):
        print(f"Warning: Clothes templates directory not found at '{clothes_dir}'")
    else:
        for filename in os.listdir(clothes_dir):
            if not filename.endswith('.xml'):
                continue
            try:
                tree = ET.parse(f"{clothes_dir}/{filename}")
                root = tree.getroot()
                if root.tag != 'cloth': continue
                
                name = root.attrib.get('name')
                if not name: continue
                
                template = {
                    'type': root.attrib.get('type'),
                    'properties': {}
                }
                
                builder_str = root.attrib.get('builder', 'false')
                template['builder'] = (builder_str.lower() == 'true')

                # NEW: Parsing the hide_cloth attribute to hide other clothes
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

                    weight_node = props_node.find('weight')
                    if weight_node is not None:
                        template['properties']['weight'] = {k: v for k, v in weight_node.attrib.items()}
                        
                if name in ITEM_TEMPLATES:
                    print(f"Warning: Duplicate item/cloth name '{name}'")
                ITEM_TEMPLATES[name] = template

            except Exception as e:
                print(f"Error parsing cloth {filename}: {e}")
    
    print(f"Loaded {len(ITEM_TEMPLATES)} total item/cloth templates.")