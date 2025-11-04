import csv
import pygame
import random

from data.config import *
from core.entities.item.item import Item, Container
from core.entities.zombie.zombie import Zombie
from core.placement import find_free_tile

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

def parse_layered_map_layout(base_layout, ground_layout, spawn_layout, tile_manager):
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
    item_spawns = []
    containers = []

    # Use dimensions from the base layout (assuming all layers match)
    map_height = len(base_layout)
    map_width = len(base_layout[0]) if map_height > 0 else 0

    if not map_height or not map_width:
        print("Error: Base map layout is empty.")
        return [], [], None, [], [], []

    # 1. Process Ground Layer (Floor Tiles)
    if len(ground_layout) != map_height or (map_height > 0 and len(ground_layout[0]) != map_width):
        print("Warning: Ground layout dimensions mismatch base layout.")
    for y, row in enumerate(ground_layout):
         if y >= map_height: break # Prevent index error if mismatch
         for x, char in enumerate(row):
            if x >= map_width: break
            if char and char != ' ': # Ignore empty cells in ground layer
                if char in tile_manager.definitions:
                    tile_def = tile_manager.definitions[char]
                    #if tile_def['is_obstacle']:
                    #     print(f"Warning: Ground layer tile '{char}' at ({x},{y}) is marked as obstacle. Ground tiles should not be obstacles.")
                    pos_x, pos_y = x * TILE_SIZE, y * TILE_SIZE
                    rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
                    renderable_tiles.append((tile_def['image'], rect))
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
                        container = Container(name=tile_def['type'], items=items, capacity=capacity)
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
                    zombie_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
                elif char == 'I':
                    item_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
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
                        container = Container(name=tile_def['type'], items=items, capacity=capacity)
                        container.rect = rect
                        container.image = tile_def['image']
                        containers.append(container)
                # --- END CHANGE ---

    if not player_spawn:
        print("Warning: No player spawn ('P') defined in spawn layer. Player will spawn at a random available spawn point.")
        if possible_player_spawns:
            player_spawn = random.choice(possible_player_spawns)
        # Optionally set a default spawn like center of map or (0,0)
        # player_spawn = (map_width * TILE_SIZE // 2, map_height * TILE_SIZE // 2)


    return obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers