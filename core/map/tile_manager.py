import os
import xml.etree.ElementTree as ET
import pygame
from data.config import *

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
                        sprite_node = root.find('visuals/sprite')
                        sprite_file = sprite_node.get('file') if sprite_node is not None else None
                        
                        if char and sprite_file:
                            image_path = f"{self.asset_folder}/{sprite_file}"
                            try:
                                image = pygame.image.load(image_path).convert_alpha()
                                image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
                                definition = {
                                    'is_obstacle': is_obstacle,
                                    'image': image,
                                    'type': root.get('type')
                                }
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
                                print(f"Loaded tile definition for '{char}' from {filename}. Image loaded from: {image_path}")
                            except pygame.error as e:
                                print(f"Error loading image {image_path} for tile '{char}': {e}")
                except ET.ParseError as e:
                    print(f"Warning: Could not parse XML file {filename}: {e}")
