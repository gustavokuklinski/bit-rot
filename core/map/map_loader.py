import csv
import pygame
import random

from core.data.config import *
from core.entities.item.item import Item, Container
from core.entities.zombie.zombie import Zombie
from core.placement import find_free_tile
from core.entities.vehicle.vehicle import Vehicle


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
    - ground_layout defines floor tiles (never obstacles).
    - base_layout defines walls and structural obstacles.
    - spawn_layout defines player, zombie, and item start positions.
    """
    obstacles = []
    renderable_tiles = [] # List to store (image, rect) tuples for drawing
    player_spawn = None
    zombie_spawns = []
    npc_spawns = []
    item_spawns = []
    containers = []
    roof_renderables = []
    map_lights = []
    # Use dimensions from the base layout (assuming all layers match)
    map_height = len(base_layout)
    map_width = len(base_layout[0]) if map_height > 0 else 0

    if not map_height or not map_width:
        print("Error: Base map layout is empty.")
        return [], [], None, [], [], [], []

    # 1. Process Ground Layer (Floor Tiles)
    if len(ground_layout) != map_height or (map_height > 0 and len(ground_layout[0]) != map_width):
        print("Warning: Ground layout dimensions mismatch base layout.")
    for y, row in enumerate(ground_layout):
         if y >= map_height: break # Prevent index error if mismatch
         for x, char in enumerate(row):
            if x >= map_width: break
            if char and char != ' ': # Ignore empty cells in ground layer
                
                # [FIX] Define position and rect here so they are available for use
                pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)

                if char in tile_manager.definitions:
                    tile_def = tile_manager.definitions[char]
                    
                    # --- START CHANGE ---
                    if tile_def['type'] == 'maptile_car':
                        # Create Vehicle Entity
                        stats = tile_def.get('car_stats', {})
                        cap = tile_def.get('capacity', 0)
                        vehicle = Vehicle(tile_def['name'], pos_x, pos_y, TILE_SIZE, TILE_SIZE, tile_def['image'], stats, capacity=cap)
                        
                        # Use the rect we created so it's the SAME object in both lists
                        vehicle.rect = rect 
                        
                        containers.append(vehicle) # Add to entities
                        
                        if tile_def['is_obstacle']:
                            obstacles.append(rect) # Add to physics
                        
                        # Do NOT add to renderable_tiles (entity draws itself)
                    
                    else:
                        # Standard Tile
                        renderable_tiles.append((tile_def['image'], rect))
                        if tile_def['is_obstacle']:
                            obstacles.append(rect) 
                        
                        if tile_def['type'] == 'maptile_container':
                            items = []
                            if 'loot' in tile_def:
                                for loot_item in tile_def['loot']:
                                    if random.random() < loot_item['chance']:
                                        items.append(Item.create_from_name(loot_item['item']))
                            capacity = tile_def.get('capacity', 0)
                            container = Container(name=tile_def.get('name', tile_def['type']), items=items, capacity=capacity)
                            container.rect = rect
                            container.image = tile_def['image']
                            containers.append(container)
                    
                    # renderable_tiles.append((tile_def['image'], rect)) 
                    
                else:
                    print(f"Warning: Undefined ground tile character '{char}' at ({x},{y}).")

    # 2. Process Base Layer (Walls, Obstacles)
    # This adds obstacle rects and potentially overwrites ground tiles if needed
    if len(base_layout) != map_height or (map_height > 0 and len(base_layout[0]) != map_width):
        print("Error: Base layout dimensions are inconsistent.") # Base MUST match expected size
        # Handle this error case as needed, maybe return empty
    for y, row in enumerate(base_layout):
        if y >= map_height: break
        for x, char in enumerate(row):
            if x >= map_width: break
            if char and char != ' ': # Ignore empty cells in base layer
                pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)

                if char in tile_manager.definitions:
                    tile_def = tile_manager.definitions[char]
                    
                    # Also check for cars in Base layer (where they usually are)
                    if tile_def['type'] == 'maptile_car':
                        stats = tile_def.get('car_stats', {})
                        cap = tile_def.get('capacity', 0)
                        vehicle = Vehicle(tile_def['name'], pos_x, pos_y, TILE_SIZE, TILE_SIZE, tile_def['image'], stats, capacity=cap)
                        vehicle.rect = rect 
                        containers.append(vehicle)
                        if tile_def['is_obstacle']:
                            obstacles.append(rect)
                    else:
                        renderable_tiles.append((tile_def['image'], rect)) # Add visuals
                        if tile_def['is_obstacle']:
                            obstacles.append(rect) # Add collision rect
                        if tile_def['type'] == 'maptile_container':
                            items = []
                            if 'loot' in tile_def:
                                for loot_item in tile_def['loot']:
                                    if random.random() < loot_item['chance']:
                                        items.append(Item.create_from_name(loot_item['item']))
                            capacity = tile_def.get('capacity', 0)
                            container = Container(name=tile_def.get('name', tile_def['type']), items=items, capacity=capacity)
                            container.rect = rect
                            container.image = tile_def['image']
                            containers.append(container)
                else:
                    print(f"Warning: Undefined base tile character '{char}' at ({x},{y}).")


    # 3. Process Spawn Layer (P, Z, I)
    possible_player_spawns = []
    if len(spawn_layout) != map_height or (map_height > 0 and len(spawn_layout[0]) != map_width):
        print("Warning: Spawn layout dimensions mismatch base layout.")
    for y, row in enumerate(spawn_layout):
        if y >= map_height: break
        for x, char in enumerate(row):
            if x >= map_width: break
            if char and char != ' ': # Ignore empty cells
                
                # --- START CHANGE ---
                # Check for spawn markers FIRST
                if char == 'P':
                    if player_spawn:
                         print(f"Warning: Multiple player spawns defined. Using last one found at ({x},{y}).")
                    player_spawn = (x * TILE_SIZE, y * TILE_SIZE)
                elif char == 'Z':
                    base_char = ground_layout[y][x]
                    tile_def = tile_manager.definitions.get(base_char)
                    
                    is_valid_spawn = True
                    if not tile_def:
                        is_valid_spawn = False # Don't spawn on empty space
                    elif tile_def['is_obstacle']:
                        is_valid_spawn = False # Don't spawn on obstacles
                    elif base_char.startswith('water_') or base_char.startswith('petrol_'):
                        is_valid_spawn = False # Don't spawn on forbidden tiles
                        
                    if is_valid_spawn:
                        zombie_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
                    else:
                        # Optional: Log why a spawn point was skipped
                        # print(f"Skipping zombie spawn at ({x},{y}), tile is '{base_char}'.")
                        pass
                elif char == 'I':
                    item_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
                elif char.strip() == 'NPC':
                    npc_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
                else:
                    # If not a standard spawn marker, it might be a player spawn point
                    possible_player_spawns.append((x * TILE_SIZE, y * TILE_SIZE))

                # NOW, also check if the character is a renderable tile
                if char in tile_manager.definitions:
                    pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                    rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
                    tile_def = tile_manager.definitions[char]
                    
                    renderable_tiles.append((tile_def['image'], rect)) # Add visuals
                    
                    if tile_def['is_obstacle']:
                        obstacles.append(rect) # Add collision rect
                        
                    if tile_def['type'] == 'maptile_container':
                        items = []
                        if 'loot' in tile_def:
                            for loot_item in tile_def['loot']:
                                if random.random() < loot_item['chance']:
                                    items.append(Item.create_from_name(loot_item['item']))
                        capacity = tile_def.get('capacity', 0)
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
                    
                    # 1. Add visual sprite (The lamp itself)
                    # We add it to renderable_tiles so it draws on the world
                    renderable_tiles.append((tile_def['image'], rect))
                 

                    # 2. Add Light Source Data
                    if tile_def.get('light_state') == 'on':
                        base_radius = tile_def.get('light_radius', 0) * TILE_SIZE
                           
                        random_radius = int(random.uniform(base_radius, base_radius * 2))
                        
                        is_active = random.choice([True, False])
                        map_lights.append({
                            'rect': rect,
                            # Convert tile radius to pixels (e.g., 10 tiles * 32px)
                            'radius': random_radius,
                            'active': is_active
                        })

    if len(roof_layout) != map_height or (map_height > 0 and len(roof_layout[0]) != map_width):
        print("Warning: Roof layout dimensions mismatch base layout.")

    for y, row in enumerate(roof_layout):
         if y >= map_height: break # Prevent index error if mismatch
         for x, char in enumerate(row):
            if x >= map_width: break
            if char and char != ' ': # Ignore empty cells
                if char in tile_manager.definitions:
                    tile_def = tile_manager.definitions[char]
                    pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                    rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
                    # Add to roof list WITH grid coordinates for the fade logic
                    roof_renderables.append((tile_def['image'], rect, (x, y)))
                else:
                    print(f"Warning: Undefined roof tile character '{char}' at ({x},{y}).")

    if not player_spawn:
        print("Warning: No player spawn ('P') defined in spawn layer. Player will spawn at a random available spawn point.")
        if possible_player_spawns:
            player_spawn = random.choice(possible_player_spawns)
        # Optionally set a default spawn like center of map or (0,0)
        # player_spawn = (map_width * TILE_SIZE // 2, map_height * TILE_SIZE // 2)


    return obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers, roof_renderables, map_lights, npc_spawns