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


def _generate_container_items(tile_def, game=None):
    """
    Helper function to generate items for a container based on its loot table,
    accounting for global spawn multipliers, Player Luck, and Kill Count.
    """
    items = []
    capacity = tile_def.get('capacity', 0)
    if 'loot' not in tile_def:
        return items
        
    if not ITEM_TEMPLATES:
        load_item_templates_data()
        
    loot_pool = list(tile_def['loot'])
    random.shuffle(loot_pool)
    
    is_liquid_source = tile_def.get('allow_liquid', False)
    
    # 1. Base Global Multiplier
    dynamic_multiplier = ITEM_SPAWN_CHANCE_MULTIPLIER
    lucky_level = 0

    # 2. Dynamic Player Multipliers (Only applies if game/player context is passed)
    if game and hasattr(game, 'player') and game.player:
        # Luck: +5% total loot multiplier per level (Up to +50% at level 10)
        lucky_level = game.player.progression.get_lucky(game.player)
        luck_bonus = lucky_level * 0.05
        
        # Kills: +2% total loot multiplier per 100 kills (Capped at +50% / 2500 kills)
        zombies_killed = getattr(game, 'zombies_killed', 0)
        kill_bonus = min(0.5, zombies_killed * 0.0002)

        dynamic_multiplier *= (1.0 + luck_bonus + kill_bonus)
    
    for loot_entry in loot_pool:
        if capacity > 0 and len(items) >= capacity:
            break
            
        total_multiplier = dynamic_multiplier
        base_chance = loot_entry['chance']
        
        # 3. Rare Item Boost: High Luck increases the raw spawn chance of rare items (< 20% chance)
        if lucky_level > 0 and base_chance < 0.2:
            rare_bonus = (0.2 - base_chance) * lucky_level * 0.05
            base_chance += rare_bonus

        adjusted_chance = base_chance * total_multiplier
        
        if is_liquid_source:
            adjusted_chance = 1.0  
            total_multiplier = 1.0 
        
        if random.random() <= adjusted_chance:
            min_qty = int(loot_entry.get('min', 1))
            max_qty = int(loot_entry.get('max', 1))
            
            scaled_qty = min_qty + int(round((max_qty - min_qty) * min(1.0, total_multiplier)))
            qty = max(min_qty, min(max_qty, scaled_qty))
            
            if is_liquid_source:
                qty = max_qty
            
            if not is_liquid_source and total_multiplier <= 0.01 and random.random() > 0.5:
                qty = 0

            if qty <= 0:
                continue

            if 'type' in loot_entry:
                matching_items = []
                matching_weights = []
                
                # Fetch all items matching the category type and enforce spawn_chance > 0 OR liquid bypass
                for n, d in ITEM_TEMPLATES.items():
                    if d.get('type') == loot_entry['type'] and not n.endswith(' on'):
                        spawn_chance = d.get('spawn_chance', 1.0)
                        if spawn_chance > 0 or is_liquid_source:
                            matching_items.append(n)
                            # If it's a forced spawn (0%) via liquid source, assign it a generic weight of 1.0
                            matching_weights.append(spawn_chance if spawn_chance > 0 else 1.0)

                if matching_items:
                    for _ in range(qty):
                        if capacity > 0 and len(items) >= capacity: break
                        # Use random.choices to respect the individual rarity of items within this category
                        chosen_item = random.choices(matching_items, weights=matching_weights, k=1)[0]
                        new_item = Item.create_from_name(chosen_item)
                        
                        if new_item:
                            if is_liquid_source and getattr(new_item, 'capacity', None) is not None:
                                new_item.load = new_item.capacity
                            items.append(new_item)
                        
            elif 'item' in loot_entry and not loot_entry['item'].endswith(' on'):
                # Explicitly verify the item isn't disabled globally via spawn_chance="0" OR bypass if it's a liquid source
                target_name = loot_entry['item']
                template = ITEM_TEMPLATES.get(target_name)
                
                if template and (template.get('spawn_chance', 1.0) > 0 or is_liquid_source):
                    for _ in range(qty):
                        if capacity > 0 and len(items) >= capacity: break
                        new_item = Item.create_from_name(target_name)
                        
                        if new_item:
                            if is_liquid_source and getattr(new_item, 'capacity', None) is not None:
                                new_item.load = new_item.capacity
                            items.append(new_item)
                    
    return items


def load_map_from_file(filepath):
    """Loads a map layout from a CSV file."""
    layout = []
    try:
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            layout = list(reader)
    except FileNotFoundError:
        print(f"Error: Map layer file not found: {filepath}")
    except Exception as e:
        print(f"Error reading map layer file {filepath}: {e}")
    return layout

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
                            
                            val_liq = tile_def.get('allow_liquid', False)
                            allow_liquid = str(val_liq).lower() in ['true', '1'] or val_liq is True
                            
                            val_open = tile_def.get('is_opened', False)
                            is_opened = str(val_open).lower() in ['true', '1'] or val_open is True

                            if allow_liquid or is_opened:
                                items = _generate_container_items(tile_def)
                                container = Container(name=tile_def.get('name', tile_def['type']), items=items, capacity=capacity)
                                container.is_opened = True
                            else:
                                container = Container(name=tile_def.get('name', tile_def['type']), items=[], capacity=capacity)
                                container.is_opened = False

                            container.rect = rect
                            container.image = tile_def['image']
                            container.allow_liquid = allow_liquid
                            container.is_maptile = True
                            container.item_type = 'maptile_container'
                            container.tile_def = tile_def
                            container.pre_loot = []
                            
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
                            
                            val_liq = tile_def.get('allow_liquid', False)
                            allow_liquid = str(val_liq).lower() in ['true', '1'] or val_liq is True
                            
                            val_open = tile_def.get('is_opened', False)
                            is_opened = str(val_open).lower() in ['true', '1'] or val_open is True

                            if allow_liquid or is_opened:
                                items = _generate_container_items(tile_def)
                                container = Container(name=tile_def.get('name', tile_def['type']), items=items, capacity=capacity)
                                container.is_opened = True
                            else:
                                container = Container(name=tile_def.get('name', tile_def['type']), items=[], capacity=capacity)
                                container.is_opened = False

                            container.rect = rect
                            container.image = tile_def['image']
                            container.allow_liquid = allow_liquid
                            container.is_maptile = True
                            container.item_type = 'maptile_container'
                            container.tile_def = tile_def
                            container.pre_loot = []
                            
                            containers.append(container)
                else:
                    print(f"Warning: Undefined base tile character '{char}' at ({x},{y}).")


    # 3. Process Spawn Layer (P, Z, NPC, and Specific Items)
    possible_player_spawns = []
    quest_item_spawns = []
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
                    base_name = char.replace(' on', '').replace(' off', '').strip()
                    if base_name in ITEM_TEMPLATES:
                        item_spawns.append((x * TILE_SIZE, y * TILE_SIZE, char.strip()))
                    else:
                        possible_player_spawns.append((x * TILE_SIZE, y * TILE_SIZE))

                if char != 'VEH' and char in tile_manager.definitions:
                    pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                    rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
                    tile_def = tile_manager.definitions[char]
                    renderable_tiles.append((tile_def['image'], rect)) 
                    if tile_def['is_obstacle']:
                        obstacles.append(rect)
                        
                    if tile_def['type'] == 'maptile_container':
                        capacity = tile_def.get('capacity', 0)
                        
                        val_liq = tile_def.get('allow_liquid', False)
                        allow_liquid = str(val_liq).lower() in ['true', '1'] or val_liq is True
                        
                        val_open = tile_def.get('is_opened', False)
                        is_opened = str(val_open).lower() in ['true', '1'] or val_open is True

                        if allow_liquid or is_opened:
                            items = _generate_container_items(tile_def)
                            container = Container(name=tile_def.get('name', tile_def['type']), items=items, capacity=capacity)
                            container.is_opened = True
                        else:
                            container = Container(name=tile_def.get('name', tile_def['type']), items=[], capacity=capacity)
                            container.is_opened = False

                        container.rect = rect
                        container.image = tile_def['image']
                        container.allow_liquid = allow_liquid
                        container.is_maptile = True
                        container.item_type = 'maptile_container'
                        container.tile_def = tile_def
                        container.pre_loot = []
                        
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
            if container.rect.colliderect(q_rect):
                q_item = Item.create_from_name(qname)
                if q_item:
                    if hasattr(container, 'pre_loot'):
                        container.pre_loot.append(q_item)
                    if hasattr(container, 'inventory'):
                        container.inventory.append(q_item)
                placed = True
                break
        
        if not placed:
            item_spawns.append((qx, qy, qname))

    if not player_spawn:
        if possible_player_spawns:
            player_spawn = random.choice(possible_player_spawns)

    return obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers, roof_renderables, map_lights, npc_spawns