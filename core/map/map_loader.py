import csv
import pygame
import random

from core.data.config import *
from core.entities.item.item import Item, Container
from core.entities.item.item_data import ITEM_TEMPLATES, load_item_templates_data
from core.entities.zombie.zombie import Zombie
from core.placement import find_free_tile
from core.entities.vehicle.vehicle import Vehicle


def _generate_container_items(tile_def):
    """
    Helper function to generate items for a container based on its loot table,
    accounting for global and type-specific spawn multipliers to scale quantities.
    """
    items = []
    capacity = tile_def.get('capacity', 0)
    if 'loot' not in tile_def:
        return items
        
    if not ITEM_TEMPLATES:
        load_item_templates_data()
        
    # Randomize loot pool to handle items with 100% chance fairly
    loot_pool = list(tile_def['loot'])
    random.shuffle(loot_pool)
    
    for loot_entry in loot_pool:
        if capacity > 0 and len(items) >= capacity:
            break
            
        # 1. Determine the specific multiplier based on item type
        specific_mult = 1.0
        item_type_for_mult = None
        item_name = None
        
        if 'type' in loot_entry:
            item_type_for_mult = loot_entry['type']
        elif 'item' in loot_entry:
            item_name = loot_entry['item']
            if item_name in ITEM_TEMPLATES:
                item_type_for_mult = ITEM_TEMPLATES[item_name].get('type')
                
        if item_type_for_mult == 'weapon_melee': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_MELEE
        elif item_type_for_mult == 'weapon_ranged': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_RANGED
        elif item_type_for_mult == 'mobile': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_MOBILE
        elif item_type_for_mult == 'container': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_CONTAINER
        elif item_type_for_mult == 'backpack': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_BACKPACK
        elif item_type_for_mult == 'currency': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_CURRENCY
        elif item_type_for_mult == 'text': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_TEXT
        elif item_type_for_mult == 'utility': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_UTILITY
        elif item_type_for_mult == 'recipe': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_RECIPE
        elif item_type_for_mult == 'resource': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_RESOURCE
        elif item_type_for_mult == 'map': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_MAP
        elif item_type_for_mult == 'liquid': specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_LIQUID
        elif item_type_for_mult == 'consumable':
            specific_mult = ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE
            if item_name and item_name in ITEM_TEMPLATES:
                target_props = ITEM_TEMPLATES[item_name].get('properties', {})
                consumable_type = target_props.get('restore', {}).get('type', '')
                if 'food' in consumable_type: specific_mult *= ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_FOOD
                elif 'drink' in consumable_type: specific_mult *= ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_DRINK
                elif 'med' in consumable_type: specific_mult *= ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_MEDICATION
                elif 'ammo' in consumable_type: specific_mult *= ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_AMMO
                elif 'drug' in consumable_type: specific_mult *= ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_DRUGS

        # Combine global and specific multiplier
        total_multiplier = ITEM_SPAWN_CHANCE_MULTIPLIER * specific_mult
        
        # 2. Check chance to spawn anything at all from this entry
        adjusted_chance = loot_entry['chance'] * total_multiplier
        
        if random.random() < adjusted_chance:
            min_qty = int(loot_entry.get('min', 1))
            max_qty = int(loot_entry.get('max', 1))
            
            # 3. Calculate quantity based on total multiplier
            # If total_multiplier is 1.0+ -> max_qty
            # If total_multiplier is close to 0 -> min_qty
            scaled_qty = min_qty + int(round((max_qty - min_qty) * min(1.0, total_multiplier)))
            qty = max(min_qty, min(max_qty, scaled_qty))
            
            # 4. If total multiplier is extremely low (e.g. 1% * 1% = 0.0001), 
            # allow it to occasionally yield 'none' even if it hit the adjusted chance check.
            if total_multiplier <= 0.01 and random.random() > 0.5:
                qty = 0

            if qty <= 0:
                continue

            # 5. Spawn the determined quantity
            if 'type' in loot_entry:
                matching_items = [n for n, d in ITEM_TEMPLATES.items() if d.get('type') == loot_entry['type'] and not n.endswith(' on')]
                if matching_items:
                    for _ in range(qty):
                        if capacity > 0 and len(items) >= capacity: break
                        chosen_item = random.choice(matching_items)
                        new_item = Item.create_from_name(chosen_item)
                        if new_item: items.append(new_item)
                        
            elif 'item' in loot_entry and not loot_entry['item'].endswith(' on'):
                for _ in range(qty):
                    if capacity > 0 and len(items) >= capacity: break
                    new_item = Item.create_from_name(loot_entry['item'])
                    if new_item: items.append(new_item)
                    
    return items


def load_map_from_file(filepath):
    """Loads a map layout from a CSV file."""
    print(f"Attempting to load map from: {filepath}")  # Debug print
    layout = []
    try:
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            layout = list(reader)
            print(f"Successfully loaded {len(layout)} rows from {filepath}")  # Debug print
    except FileNotFoundError:
        print(f"Error: Map layer file not found: {filepath}")
    except Exception as e:
        print(f"Error reading map layer file {filepath}: {e}")
    return layout # Return list (possibly empty if file not found/error)

def parse_layered_map_layout(base_layout, ground_layout, spawn_layout, roof_layout, light_layout, tile_manager):
    """
    Creates lists of tiles, obstacles, and spawn points from layered map layouts.
    """
    obstacles = []
    renderable_tiles = [] 
    player_spawn = None
    zombie_spawns = []
    npc_spawns = []
    item_spawns = []
    containers = []
    roof_renderables = []
    map_lights = []
    
    map_height = len(base_layout)
    map_width = len(base_layout[0]) if map_height > 0 else 0

    if not map_height or not map_width:
        print("Error: Base map layout is empty.")
        return [], [], None, [], [], [], []

    # 1. Process Ground Layer
    if len(ground_layout) != map_height or (map_height > 0 and len(ground_layout[0]) != map_width):
        print("Warning: Ground layout dimensions mismatch base layout.")
    for y, row in enumerate(ground_layout):
         if y >= map_height: break 
         for x, char in enumerate(row):
            if x >= map_width: break
            if char and char != ' ': 
                pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)

                if char in tile_manager.definitions:
                    tile_def = tile_manager.definitions[char]
                    if tile_def['type'] == 'maptile_car':
                        stats = tile_def.get('car_stats', {})
                        cap = tile_def.get('capacity', 0)
                        loot_table = tile_def.get('loot')
                        vehicle = Vehicle(tile_def['name'], pos_x, pos_y, TILE_SIZE, TILE_SIZE, tile_def['image'], stats, capacity=cap, loot_table=loot_table)
                        vehicle.rect = rect 
                        containers.append(vehicle) 
                        if tile_def['is_obstacle']:
                            obstacles.append(rect)
                    else:
                        renderable_tiles.append((tile_def['image'], rect))
                        if tile_def['is_obstacle']:
                            obstacles.append(rect) 
                        
                        if tile_def['type'] == 'maptile_container':
                            capacity = tile_def.get('capacity', 0)
                            items = _generate_container_items(tile_def)
                            
                            container = Container(name=tile_def.get('name', tile_def['type']), items=items, capacity=capacity)
                            container.rect = rect
                            container.image = tile_def['image']
                            containers.append(container)
                else:
                    print(f"Warning: Undefined ground tile character '{char}' at ({x},{y}).")

    # 2. Process Base Layer
    if len(base_layout) != map_height or (map_height > 0 and len(base_layout[0]) != map_width):
        print("Error: Base layout dimensions are inconsistent.") 
    for y, row in enumerate(base_layout):
        if y >= map_height: break
        for x, char in enumerate(row):
            if x >= map_width: break
            if char and char != ' ': 
                pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)

                if char in tile_manager.definitions:
                    tile_def = tile_manager.definitions[char]
                    if tile_def['type'] == 'maptile_car':
                        stats = tile_def.get('car_stats', {})
                        cap = tile_def.get('capacity', 0)
                        loot_table = tile_def.get('loot')
                        vehicle = Vehicle(tile_def['name'], pos_x, pos_y, TILE_SIZE, TILE_SIZE, tile_def['image'], stats, capacity=cap, loot_table=loot_table)
                        vehicle.rect = rect 
                        containers.append(vehicle)
                        if tile_def['is_obstacle']:
                            obstacles.append(rect)
                    else:
                        renderable_tiles.append((tile_def['image'], rect)) 
                        if tile_def['is_obstacle']:
                            obstacles.append(rect) 
                        if tile_def['type'] == 'maptile_container':
                            capacity = tile_def.get('capacity', 0)
                            items = _generate_container_items(tile_def)
                            
                            container = Container(name=tile_def.get('name', tile_def['type']), items=items, capacity=capacity)
                            container.rect = rect
                            container.image = tile_def['image']
                            containers.append(container)
                else:
                    print(f"Warning: Undefined base tile character '{char}' at ({x},{y}).")


    # 3. Process Spawn Layer (P, Z, NPC, and Specific Items)
    possible_player_spawns = []
    if len(spawn_layout) != map_height or (map_height > 0 and len(spawn_layout[0]) != map_width):
        print("Warning: Spawn layout dimensions mismatch base layout.")
    for y, row in enumerate(spawn_layout):
        if y >= map_height: break
        for x, char in enumerate(row):
            if x >= map_width: break
            if char and char != ' ': 
                
                if char == 'P':
                    if player_spawn:
                         print(f"Warning: Multiple player spawns defined. Using last one found at ({x},{y}).")
                    player_spawn = (x * TILE_SIZE, y * TILE_SIZE)
                elif char == 'Z':
                    base_char = ground_layout[y][x]
                    tile_def = tile_manager.definitions.get(base_char)
                    is_valid_spawn = True
                    if not tile_def: is_valid_spawn = False 
                    elif tile_def['is_obstacle']: is_valid_spawn = False 
                    elif base_char.startswith('water_') or base_char.startswith('petrol_'):
                        is_valid_spawn = False 
                        
                    if is_valid_spawn:
                        zombie_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
                
                elif char.strip() == 'NPC': 
                    npc_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
                elif char.strip() == 'S':
                    pass
                elif char == 'VEH':
                    pass
                elif char == 'ANM':
                    pass
                else:
                    # Treat anything unknown as a fallback player spawn coordinate instead of an item
                    possible_player_spawns.append((x * TILE_SIZE, y * TILE_SIZE))

                # Check if the character is a renderable tile (e.g. specialized spawn markers)
                # [FIXED] Do not look up 'VEH' in definitions to avoid 'No template' errors
                if char != 'VEH' and char in tile_manager.definitions:
                    pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                    rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
                    tile_def = tile_manager.definitions[char]
                    renderable_tiles.append((tile_def['image'], rect)) 
                    if tile_def['is_obstacle']:
                        obstacles.append(rect)
                        
                    if tile_def['type'] == 'maptile_container':
                        capacity = tile_def.get('capacity', 0)
                        items = _generate_container_items(tile_def)
                                        
                        container = Container(name=tile_def.get('name', tile_def['type']), items=items, capacity=capacity)
                        container.rect = rect
                        container.image = tile_def['image']
                        containers.append(container)
    
    if light_layout:
         for y, row in enumerate(light_layout):
             if y >= len(light_layout): break
             for x, char in enumerate(row):
                if x >= len(row): break
                if char and char != ' ' and char in tile_manager.definitions:
                    tile_def = tile_manager.definitions[char]
                    pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                    rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
                    renderable_tiles.append((tile_def['image'], rect))
                    if tile_def.get('light_state') == 'on':
                        base_radius = tile_def.get('light_radius', 0) * TILE_SIZE
                        random_radius = int(random.uniform(base_radius, base_radius * 2))
                        is_active = random.choice([True, False])
                        map_lights.append({
                            'rect': rect,
                            'radius': random_radius,
                            'active': is_active
                        })

    if len(roof_layout) != map_height or (map_height > 0 and len(roof_layout[0]) != map_width):
        print("Warning: Roof layout dimensions mismatch base layout.")

    for y, row in enumerate(roof_layout):
         if y >= map_height: break 
         for x, char in enumerate(row):
            if x >= map_width: break
            if char and char != ' ': 
                if char in tile_manager.definitions:
                    tile_def = tile_manager.definitions[char]
                    pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                    rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
                    roof_renderables.append((tile_def['image'], rect, (x, y)))
                else:
                    print(f"Warning: Undefined roof tile character '{char}' at ({x},{y}).")

    if not player_spawn:
        print("Warning: No player spawn ('P') defined in spawn layer.")
        if possible_player_spawns:
            player_spawn = random.choice(possible_player_spawns)

    return obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers, roof_renderables, map_lights, npc_spawns