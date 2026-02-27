import os
import xml.etree.ElementTree as ET
import pygame
import random
from core.data.config import *

class VehicleLoader:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VehicleLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if VehicleLoader._initialized:
            return
            
        self.vehicle_path = os.path.join(DATA_PATH, 'vehicle')
        self.sprite_path = os.path.join(SPRITE_PATH, 'vehicle')
        self.definitions = []
        self._load_definitions()
        VehicleLoader._initialized = True

    def _load_definitions(self):
        if not os.path.exists(self.vehicle_path):
            print(f"Vehicle path not found: {self.vehicle_path}")
            return

        for filename in os.listdir(self.vehicle_path):
            if filename.endswith('.xml'):
                self._parse_vehicle_xml(os.path.join(self.vehicle_path, filename))

    def _parse_vehicle_xml(self, filepath):
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            name = root.get('name')
            
            # Visuals
            visuals = root.find('visuals')
            images = {}
            
            if visuals is not None:
                for sprite_node in visuals.findall('sprite'):
                    sprite_id = sprite_node.get('id', 'right') # Default to bottom if ID missing
                    sprite_file = sprite_node.get('file')
                    
                    if sprite_file:
                        img_path = os.path.join(self.sprite_path, sprite_file)
                        if os.path.exists(img_path):
                            images[sprite_id] = pygame.image.load(img_path).convert_alpha()
                        else:
                            print(f"Vehicle sprite not found: {img_path}")

            # Stats
            car_node = root.find('car')
            stats = {}
            if car_node is not None:
                for child in car_node:
                    if child.tag == 'lights':
                        stats['lights'] = 'off' 
                        stats['lights_radius'] = child.get('radius', '8')
                    else:
                        val = child.get('value')
                        if val is not None:
                            stats[child.tag] = val
                        
            # Look for seats either as a root attribute or a root child node to fix the 4 seats issue
            # Check if it wasn't already loaded from within the <car> node
            if 'seats' not in stats:
                if 'seats' in root.attrib:
                    stats['seats'] = root.get('seats')
                else:
                    seats_node = root.find('seats')
                    if seats_node is not None:
                        stats['seats'] = seats_node.get('value', '4')

            # Capacity
            capacity_node = root.find('capacity')
            capacity = int(capacity_node.get('value', 20)) if capacity_node is not None else 20

            # Loot
            loot_table = []
            loot_node = root.find('loot')
            if loot_node is not None:
                for item in loot_node.findall('item'):
                    loot_table.append({
                        'item': item.get('item'),
                        'chance': float(item.get('chance', 0.0))
                    })

            self.definitions.append({
                'name': name,
                'images': images,
                'stats': stats,
                'capacity': capacity,
                'loot_table': loot_table
            })

        except Exception as e:
            print(f"Error parsing vehicle XML {filepath}: {e}")

    def get_random_definition(self):
        if not self.definitions: return None
        return random.choice(self.definitions)

    def get_definition_by_name(self, name):
        """Finds a vehicle definition by its name (case-insensitive)."""
        if not name: return None
        target = name.lower().strip()
        for df in self.definitions:
            if df['name'].lower().strip() == target:
                return df
        return None