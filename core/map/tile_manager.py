import os
import xml.etree.ElementTree as ET
import pygame
from core.data.config import *
import core.data.config

class TileManager:
    """Manages tile definitions, loading them from XML and handling image assets."""
    def __init__(self, tile_folder=DATA_PATH + 'map/', asset_folder=SPRITE_PATH + 'map/'):
        self.tile_folder = tile_folder
        self.asset_folder = asset_folder
        self.definitions = {}
        self._load_definitions()

    def _load_definitions(self):
        """Parses all XML files in the tile folder to load tile definitions."""
        for filename in os.listdir(self.tile_folder):
            if filename.endswith('.xml'):
                filepath = f"{self.tile_folder}/{filename}"
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    if root.tag == 'map':
                        char = root.get('char')
                        is_obstacle = root.get('is_obstacle', 'false').lower() == 'true'
                        
                        # [NEW] Parse destructible tag
                        is_destructible = root.get('destructible', 'false').lower() == 'true'
                        
                        # [NEW] Parse allow_liquid tag
                        allow_liquid = root.get('allow_liquid', 'false').lower() == 'true'

                        is_stair = root.get('is_stair', 'false').lower() == 'true'
                        # Default to 0 if not specified
                        target_layer = int(root.get('target_layer', '0'))

                        sprite_node = root.find('visuals/sprite')
                        sprite_file = sprite_node.get('file') if sprite_node is not None else None
                        
                        if char and sprite_file:
                            image_path = f"{self.asset_folder}/{sprite_file}"
                            try:
                                image = pygame.image.load(image_path).convert_alpha()
                                image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
                                # [NEW] Create collision mask from the tile image
                                mask = pygame.mask.from_surface(image)

                                definition = {
                                    'name': root.get('name', 'Unknown'),
                                    'is_obstacle': is_obstacle,
                                    'destructible': is_destructible, 
                                    'allow_liquid': allow_liquid, # [ADDED] Store the flag
                                    'image': image,
                                    'mask': mask, # [ADDED] Store the mask in the definition
                                    'type': root.get('type'),
                                    'state': root.get('state'),
                                    'is_statable': root.get('state') is not None,
                                    'rest': root.get('rest', 'false').lower() == 'true',
                                    'sleep': root.get('sleep', 'false').lower() == 'true',
                                    'light_state': root.get('light', 'off'), 
                                    'light_radius': int(root.get('light_radius', '0')),
                                    'is_stair': is_stair,
                                    'target_layer': target_layer,
                                }

                                # Parse Explicit Health
                                props_node = root.find('properties')
                                if props_node is not None:
                                    health_node = props_node.find('health')
                                    if health_node is not None:
                                        definition['health_min'] = int(health_node.get('min', 1))
                                        definition['health_max'] = int(health_node.get('max', 1))

                                # Parse Explicit Drops
                                drop_node = root.find('drop')
                                if drop_node is not None:
                                    definition['drops'] = []
                                    for item_node in drop_node.findall('item'):
                                        definition['drops'].append({
                                            'item': item_node.get('item'),
                                            'chance': float(item_node.get('chance', 1.0)),
                                            'min_qty': int(item_node.get('min', 1)),
                                            'max_qty': int(item_node.get('max', 1))
                                        })

                                # [SAFETY NET] Defaults for destructibles/trees
                                if definition['destructible'] or 'tree' in filename.lower():
                                    if 'health_max' not in definition:
                                        definition['health_min'] = 60
                                        definition['health_max'] = 100
                                    
                                    if 'drops' not in definition:
                                        definition['drops'] = [{
                                            'item': 'Tree Trunk',
                                            'chance': 1.0, 
                                            'min_qty': 1, 
                                            'max_qty': 2
                                        }]
                                    
                                    definition['destructible'] = True

                                sound_node = root.find('sound')
                                if sound_node is not None:
                                    definition['sound_src'] = sound_node.get('src')

                                if root.get('type') == 'maptile_car':
                                    car_node = root.find('car')
                                    if car_node is not None:
                                        key_node = car_node.find('key')
                                        key_value = key_node.get('value', 'false') if key_node is not None else 'false'
                                        definition['car_stats'] = {
                                            'max_speed': car_node.find('max_speed').get('value', '10'),
                                            'key': key_value,
                                            'fuel': car_node.find('fuel').get('value', '0'),
                                            'motor': car_node.find('motor').get('value', '1'),
                                            'battery': car_node.find('battery').get('value', '1'),
                                            'seats': car_node.find('seats').get('value', '4') if car_node.find('seats') is not None else '4'
                                        }
                                        lights_node = car_node.find('lights')
                                        if lights_node is not None:
                                            definition['car_stats']['lights'] = lights_node.get('value', 'off')
                                            definition['car_stats']['lights_radius'] = lights_node.get('radius', '4')
                                        else:
                                            definition['car_stats']['lights'] = 'off'
                                            definition['car_stats']['lights_radius'] = '4'

                                    capacity_node = root.find('capacity')
                                    if capacity_node is not None:
                                        definition['capacity'] = int(capacity_node.get('value'))
                                    loot_node = root.find('loot')
                                    if loot_node is not None:
                                        definition['loot'] = []
                                        for item_node in loot_node.findall('item'):
                                            entry = {'chance': float(item_node.get('chance', '0'))}
                                            if item_node.get('type'):
                                                entry['type'] = item_node.get('type')
                                                entry['min'] = int(item_node.get('min', '1'))
                                                entry['max'] = int(item_node.get('max', '1'))
                                            elif item_node.get('item'):
                                                entry['item'] = item_node.get('item')
                                            definition['loot'].append(entry)

                                if root.get('type') == 'maptile_container':
                                    capacity_node = root.find('capacity')
                                    if capacity_node is not None:
                                        definition['capacity'] = int(capacity_node.get('value'))
                                    loot_node = root.find('loot')
                                    if loot_node is not None:
                                        definition['loot'] = []
                                        for item_node in loot_node.findall('item'):
                                            entry = {'chance': float(item_node.get('chance', '0'))}
                                            if item_node.get('type'):
                                                entry['type'] = item_node.get('type')
                                                entry['min'] = int(item_node.get('min', '1'))
                                                entry['max'] = int(item_node.get('max', '1'))
                                            elif item_node.get('item'):
                                                entry['item'] = item_node.get('item')
                                            definition['loot'].append(entry)
                                
                                self.definitions[char] = definition
                            except pygame.error as e:
                                print(f"Error loading image {image_path} for tile '{char}': {e}")
                except ET.ParseError as e:
                    print(f"Warning: Could not parse XML file {filename}: {e}")