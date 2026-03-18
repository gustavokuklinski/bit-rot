import os
import xml.etree.ElementTree as ET
import pygame
import random
from core.data.config import DATA_PATH, SPRITE_PATH

class VehicleData:
    VEHICLE_TEMPLATES = []

    @staticmethod
    def load_templates():
        vehicle_path = os.path.join(DATA_PATH, 'vehicle')
        sprite_path = os.path.join(SPRITE_PATH, 'vehicle')
        
        VehicleData.VEHICLE_TEMPLATES = []

        if not os.path.exists(vehicle_path):
            print(f"Vehicle Warning: Folder not found at {vehicle_path}")
            return

        for filename in os.listdir(vehicle_path):
            if filename.endswith('.xml'):
                try:
                    filepath = os.path.join(vehicle_path, filename)
                    tree = ET.parse(filepath)
                    root = tree.getroot()

                    name = root.get('name')
                    # [NEW] Extract the spawn weight from the XML root attribute
                    spawn_weight = int(root.get('spawn_weight', 10))
                    
                    # Visuals
                    visuals = root.find('visuals')
                    images = {}
                    
                    if visuals is not None:
                        for sprite_node in visuals.findall('sprite'):
                            sprite_id = sprite_node.get('id', 'right') 
                            sprite_file = sprite_node.get('file')
                            
                            if sprite_file:
                                img_path = os.path.join(sprite_path, sprite_file)
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

                    # Seats
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

                    VehicleData.VEHICLE_TEMPLATES.append({
                        'name': name,
                        'spawn_weight': spawn_weight, # [NEW] Storing spawn_weight
                        'images': images,
                        'stats': stats,
                        'capacity': capacity,
                        'loot_table': loot_table
                    })

                except Exception as e:
                    print(f"Error parsing vehicle XML {filepath}: {e}")

    @staticmethod
    def get_random_definition():
        """[NEW] Selects a random vehicle based on weighted probability."""
        if not VehicleData.VEHICLE_TEMPLATES: 
            return None
            
        weights = [template.get('spawn_weight', 10) for template in VehicleData.VEHICLE_TEMPLATES]
        # random.choices uses the weights array and returns a list. We take [0] to get the item.
        return random.choices(VehicleData.VEHICLE_TEMPLATES, weights=weights, k=1)[0]

    @staticmethod
    def get_definition_by_name(name):
        """Finds a vehicle definition by its name (case-insensitive)."""
        if not name: return None
        target = name.lower().strip()
        for df in VehicleData.VEHICLE_TEMPLATES:
            if df['name'].lower().strip() == target:
                return df
        return None