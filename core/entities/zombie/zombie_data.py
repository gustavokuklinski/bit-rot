import os
import xml.etree.ElementTree as ET
from core.data.config import DATA_PATH, ZOMBIE_SPEED, ZOMBIE_INFECTION_CHANCE
import core.data.config

class ZombieData:
    ZOMBIE_TEMPLATES = []
    ZOMBIE_CLOTHES_POOL = {}
    ALL_ITEM_TEMPLATES = []

    @staticmethod
    def load_templates(folder=None):
        """Loads all zombie templates from XML files in a folder."""
        if folder is None:
            folder = os.path.join(DATA_PATH, 'zombie/')

        ZombieData.ZOMBIE_TEMPLATES = []
        ZombieData.ZOMBIE_CLOTHES_POOL.clear()
        ZombieData.ALL_ITEM_TEMPLATES.clear()

        try:
            # Load clothes data first
            clothes_data = {}
            clothes_folder = os.path.join(DATA_PATH, 'clothes/')
            if os.path.exists(clothes_folder):
                for filename in os.listdir(clothes_folder):
                    if filename.endswith('.xml'):
                        filepath = os.path.join(clothes_folder, filename)
                        try:
                            tree = ET.parse(filepath)
                            root = tree.getroot()
                            if root.tag == 'cloth':

                                clothe_type = root.get('id') # e.g., "head", "torso", "legs"
                                if not clothe_type:
                                    print(f"Warning: Clothe {filename} has no 'type' attribute, skipping.")
                                    continue

                                if clothe_type not in ZombieData.ZOMBIE_CLOTHES_POOL:
                                    ZombieData.ZOMBIE_CLOTHES_POOL[clothe_type] = []

                                properties = root.find('properties')
                                if properties is None: continue

                                # Build a dictionary of this clothe's properties
                                clothe_props = {
                                    'name': root.get('name'),
                                    'type': clothe_type,
                                    'defence': 0.0, # Default
                                    'speed': 0.0, # Default
                                    'sprite': None # Default
                                }
                                
                                def_node = properties.find('defence')
                                if def_node is not None:
                                    clothe_props['defence'] = float(def_node.get('value', 0))
                                    
                                spd_node = properties.find('speed')
                                if spd_node is not None:
                                    clothe_props['speed'] = float(spd_node.get('value', 0))
                                    
                                spr_node = properties.find('sprite')
                                if spr_node is not None:
                                    clothe_props['sprite'] = spr_node.get('file')

                                # Add this item to the global pool, sorted by its type
                                ZombieData.ZOMBIE_CLOTHES_POOL[clothe_type].append(clothe_props)
                        except Exception as e:
                            print(f"Error loading clothe from {filename}: {e}")

            items_folder = os.path.join(DATA_PATH, 'items/')
            if os.path.exists(items_folder):
                for filename in os.listdir(items_folder):
                    if filename.endswith('.xml'):
                        try:
                            item_path = os.path.join(items_folder, filename)
                            tree = ET.parse(item_path)
                            root = tree.getroot()
                            if root.tag == 'item':
                                item_name = root.get('name')
                                if item_name:
                                    ZombieData.ALL_ITEM_TEMPLATES.append(item_name)
                        except Exception as e:
                            print(f"Error parsing item XML {filename}: {e}")
                print(f"Loaded {len(ZombieData.ALL_ITEM_TEMPLATES)} item names for random loot.")
            else:
                print(f"Warning: Item folder not found at {items_folder}")
            
            
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    if filename.endswith('.xml'):
                        filepath = os.path.join(folder, filename)
                        try:
                            tree = ET.parse(filepath)
                            root = tree.getroot()
                            if root.tag == 'zombie':
                                template = {}
                                name_node = root.find('name')
                                stats_node = root.find('stats')
                                visuals_node = root.find('visuals')
                                xp_node = root.find('xp')
                                loot_node = root.find('loot')
                                clothes_node = root.find('clothes')
                                sound_node = root.find('sound')
                                template['name'] = name_node.get('value') if name_node is not None else 'Unknown Zombie'

                                health_node = stats_node.find('health')
                                template['min_health'] = int(health_node.get('min'))
                                template['max_health'] = int(health_node.get('max'))

                                speed_node = stats_node.find('speed')
                                template['min_speed'] = int(speed_node.get('min')) * ZOMBIE_SPEED
                                template['max_speed'] = int(speed_node.get('max')) * ZOMBIE_SPEED

                                attack_node = stats_node.find('attack')
                                template['min_attack'] = int(attack_node.get('min'))
                                template['max_attack'] = int(attack_node.get('max'))

                                infection_node = stats_node.find('infection')
                                template['min_infection'] = int(infection_node.get('min')) * ZOMBIE_INFECTION_CHANCE
                                template['max_infection'] = int(infection_node.get('max')) * ZOMBIE_INFECTION_CHANCE

                                template['sprites'] = {} # Use a dict to store multiple sprites
                                if visuals_node is not None:
                                    # Find all <sprite> tags
                                    for sprite_node in visuals_node.findall('sprite'):
                                        sprite_id = sprite_node.get('id') # e.g., "center", "left"
                                        sprite_file = sprite_node.get('file') # e.g., "zombie.png"
                                        if sprite_id and sprite_file:
                                            template['sprites'][sprite_id] = sprite_file
                                # Fallback for old templates
                                if not template['sprites'] and visuals_node is None: 
                                    old_sprite = root.find('sprite')
                                    if old_sprite is not None:
                                         template['sprite'] = old_sprite.text

                                template['min_xp'] = float(xp_node.get('min'))
                                template['max_xp'] = float(xp_node.get('max'))

                                template['loot'] = []
                                if loot_node is not None:
                                    for item_node in loot_node.findall('item'):
                                        template['loot'].append({
                                            'item': item_node.get('name'),
                                            'chance': float(item_node.get('chance'))
                                        })

                                # Instead of loading item lists, just get the tag names
                                template['clothes_slots'] = []
                                if clothes_node is not None:
                                    for slot_node in clothes_node:
                                        # slot_node.tag will be "head", "torso", etc.
                                        template['clothes_slots'].append(slot_node.tag)


                                template['sounds'] = {}
                                if sound_node is not None:
                                    hit_node = sound_node.find('hit')
                                    if hit_node is not None:
                                        template['sounds']['hit'] = hit_node.get('src')
                                    
                                    wander_node = sound_node.find('wander')
                                    if wander_node is not None:
                                        template['sounds']['wander'] = wander_node.get('src')
                                        
                                    dead_node = sound_node.find('dead')
                                    if dead_node is not None:
                                        template['sounds']['dead'] = dead_node.get('src')
                                        
                                    attack_node = sound_node.find('attack')
                                    if attack_node is not None:
                                        template['sounds']['attack'] = attack_node.get('src')

                                    steps_node = sound_node.find('steps') # Find the <steps> tag
                                    if steps_node is not None:
                                        template['sounds']['steps'] = steps_node.get('src')
                                
                                template['sex'] = root.find('sex').get('value') if root.find('sex') is not None else 'Random'
                                template['profession'] = root.find('profession').get('value') if root.find('profession') is not None else 'Civilian'
                                template['vaccine'] = root.find('vaccine').get('value') if root.find('vaccine') is not None else 'False'

                                ZombieData.ZOMBIE_TEMPLATES.append(template)
                                print(f"Loaded zombie template: {template['name']}")
                        except Exception as e:
                            print(f"Error loading zombie template from {filename}: {e}")
        except FileNotFoundError:
            print(f"Error: Zombie template folder not found: {folder}")