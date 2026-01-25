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
                        
                        # [NEW] Parse your specific destructible tag
                        is_destructible = root.get('destructible', 'false').lower() == 'true'

                        sprite_node = root.find('visuals/sprite')
                        sprite_file = sprite_node.get('file') if sprite_node is not None else None
                        
                        if char and sprite_file:
                            image_path = f"{self.asset_folder}/{sprite_file}"
                            try:
                                image = pygame.image.load(image_path).convert_alpha()
                                image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
                                definition = {
                                    'name': root.get('name', 'Unknown'),
                                    'is_obstacle': is_obstacle,
                                    'destructible': is_destructible, # Store the flag
                                    'image': image,
                                    'type': root.get('type'),
                                    'state': root.get('state'),
                                    'is_statable': root.get('state') is not None,
                                    'rest': root.get('rest', 'false').lower() == 'true',
                                    'sleep': root.get('sleep', 'false').lower() == 'true',
                                    'light_state': root.get('light', 'off'), 
                                    'light_radius': int(root.get('light_radius', '0'))
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

                                # [SAFETY NET] If marked destructible (or is a tree) but missing properties, add defaults
                                # This ensures your new tag works immediately even if you forget <properties>
                                if definition['destructible'] or 'tree' in filename.lower():
                                    if 'health_max' not in definition:
                                        definition['health_min'] = 60
                                        definition['health_max'] = 100
                                    
                                    if 'drops' not in definition:
                                        definition['drops'] = [{
                                            'item': 'Log',
                                            'chance': 1.0, 
                                            'min_qty': 1, 
                                            'max_qty': 2
                                        }]
                                    
                                    # Force the flag to true if we detected it by filename (legacy support)
                                    definition['destructible'] = True

                                sound_node = root.find('sound')
                                if sound_node is not None:
                                    definition['sound_src'] = sound_node.get('src')

                                # ... (Keep Car/Container logic unchanged) ...
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
                                            definition['loot'].append({
                                                'item': item_node.get('item'),
                                                'chance': float(item_node.get('chance', '0'))
                                            })

                                if root.get('type') == 'maptile_container':
                                    capacity_node = root.find('capacity')
                                    if capacity_node is not None:
                                        definition['capacity'] = int(capacity_node.get('value'))
                                    loot_node = root.find('loot')
                                    if loot_node is not None:
                                        definition['loot'] = []
                                        for item_node in loot_node.findall('item'):
                                            definition['loot'].append({
                                                'item': item_node.get('item'),
                                                'chance': float(item_node.get('chance', '0'))
                                            })
                                
                                self.definitions[char] = definition
                            except pygame.error as e:
                                print(f"Error loading image {image_path} for tile '{char}': {e}")
                except ET.ParseError as e:
                    print(f"Warning: Could not parse XML file {filename}: {e}")