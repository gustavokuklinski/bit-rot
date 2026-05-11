# core/map/map_loader.py

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
    accounting for global spawn multipliers to scale quantities.
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
    
    # Check if this is a liquid container
    is_liquid_source = tile_def.get('allow_liquid', False)
    
    for loot_entry in loot_pool:
        if capacity > 0 and len(items) >= capacity:
            break
            
        # 1. Use ONLY the global multiplier as requested
        total_multiplier = ITEM_SPAWN_CHANCE_MULTIPLIER
        
        # 2. Check chance to spawn anything at all from this entry
        adjusted_chance = loot_entry['chance'] * total_multiplier
        
        # Force guaranteed spawn rules if it's a liquid source
        if is_liquid_source:
            adjusted_chance = 1.0  
            total_multiplier = 1.0 
        
        if random.random() <= adjusted_chance:
            min_qty = int(loot_entry.get('min', 1))
            max_qty = int(loot_entry.get('max', 1))
            
            # 3. Calculate quantity based on total multiplier
            scaled_qty = min_qty + int(round((max_qty - min_qty) * min(1.0, total_multiplier)))
            qty = max(min_qty, min(max_qty, scaled_qty))
            
            # Force maximum quantity yield for liquids
            if is_liquid_source:
                qty = max_qty
            
            # 4. If total multiplier is extremely low, allow occasional empty yields
            if not is_liquid_source and total_multiplier <= 0.01 and random.random() > 0.5:
                qty = 0

            if qty <= 0:
                continue

            # 5. Spawn the determined quantity and enforce max load
            if 'type' in loot_entry:
                matching_items = [n for n, d in ITEM_TEMPLATES.items() if d.get('type') == loot_entry['type'] and not n.endswith(' on')]
                if matching_items:
                    for _ in range(qty):
                        if capacity > 0 and len(items) >= capacity: break
                        chosen_item = random.choice(matching_items)
                        new_item = Item.create_from_name(chosen_item)
                        
                        if new_item:
                            # [FIX] If it's a liquid source, force the item's stack size to its maximum
                            if is_liquid_source and getattr(new_item, 'capacity', None) is not None:
                                new_item.load = new_item.capacity
                            items.append(new_item)
                        
            elif 'item' in loot_entry and not loot_entry['item'].endswith(' on'):
                for _ in range(qty):
                    if capacity > 0 and len(items) >= capacity: break
                    new_item = Item.create_from_name(loot_entry['item'])
                    
                    if new_item:
                        # [FIX] If it's a liquid source, force the item's stack size to its maximum
                        if is_liquid_source and getattr(new_item, 'capacity', None) is not None:
                            new_item.load = new_item.capacity
                        items.append(new_item)
                    
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
                            
                            # --- FIX: Transfer Liquid & Infinite Source Flags ---
                            val = tile_def.get('allow_liquid', False)
                            container.allow_liquid = str(val).lower() in ['true', '1'] or val is True
                            container.is_maptile = True
                            container.item_type = 'maptile_container'
                            # --------------------------------------------------
                            
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
                            
                            # --- FIX: Transfer Liquid & Infinite Source Flags ---
                            val = tile_def.get('allow_liquid', False)
                            container.allow_liquid = str(val).lower() in ['true', '1'] or val is True
                            container.is_maptile = True
                            container.item_type = 'maptile_container'
                            # --------------------------------------------------
                            
                            containers.append(container)
                else:
                    print(f"Warning: Undefined base tile character '{char}' at ({x},{y}).")


    # 3. Process Spawn Layer (P, Z, NPC, and Specific Items)
    possible_player_spawns = []
    quest_item_spawns = []
    # Ensure ITEM_TEMPLATES is loaded for item checking
    if not ITEM_TEMPLATES:
        load_item_templates_data()
        
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
                
                elif char.strip() in ['NPC', 'SNPC']: 
                    npc_spawns.append((x * TILE_SIZE, y * TILE_SIZE, char.strip()))
                elif char.strip() == 'S':
                    pass
                elif char == 'VEH':
                    pass
                elif char == 'ANM':
                    pass
                elif char.startswith('QI_'): 
                    item_name = char[3:].strip()
                    if item_name in ITEM_TEMPLATES:
                        quest_item_spawns.append((x * TILE_SIZE, y * TILE_SIZE, item_name))
                    else:
                        print(f"Warning: Quest item '{item_name}' not found in templates.")
                else:
                    # [UPDATED] Clean up state tags like ' on' and ' off' to verify base item names
                    base_name = char.replace(' on', '').replace(' off', '').strip()
                    if base_name in ITEM_TEMPLATES:
                        item_spawns.append((x * TILE_SIZE, y * TILE_SIZE, char.strip()))
                    else:
                        # Treat anything truly unknown as a fallback player spawn coordinate instead of an item
                        possible_player_spawns.append((x * TILE_SIZE, y * TILE_SIZE))

                # Check if the character is a renderable tile (e.g. specialized spawn markers)
                # Do not look up 'VEH' in definitions to avoid 'No template' errors
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
                        
                        # --- FIX: Transfer Liquid & Infinite Source Flags ---
                        val = tile_def.get('allow_liquid', False)
                        container.allow_liquid = str(val).lower() in ['true', '1'] or val is True
                        container.is_maptile = True
                        container.item_type = 'maptile_container'
                        # --------------------------------------------------
                        
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

    for qx, qy, qname in quest_item_spawns:
        q_rect = pygame.Rect(qx, qy, TILE_SIZE, TILE_SIZE)
        placed = False
        
        for container in containers:
            # If a container shares this exact tile location
            if container.rect.colliderect(q_rect):
                q_item = Item.create_from_name(qname)
                if q_item:
                    # Push it into the container's inventory
                    if hasattr(container, 'inventory'):
                        container.inventory.append(q_item)
                    elif hasattr(container, 'items'): # Fallback structure
                        container.items.append(q_item)
                        
                placed = True
                print(f"  > Injected quest item '{qname}' into container '{container.name}' at ({qx}, {qy})")
                break
        
        # Fallback: if the container was destroyed or missing, safely drop it on the ground
        if not placed:
            item_spawns.append((qx, qy, qname))
            print(f"  > Dropped quest item '{qname}' on ground at ({qx}, {qy}) (Container not found)")

    if not player_spawn:
        print("Warning: No player spawn ('P') defined in spawn layer.")
        if possible_player_spawns:
            player_spawn = random.choice(possible_player_spawns)

    return obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers, roof_renderables, map_lights, npc_spawns