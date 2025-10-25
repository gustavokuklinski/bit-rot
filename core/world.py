import pygame
import random
import os
import xml.etree.ElementTree as ET
import csv
from data.config import *
from core.entities.item import Item
from core.entities.zombie import Zombie
from core.placement import find_free_tile

class TileManager:
    """Manages tile definitions, loading them from XML and handling image assets."""
    def __init__(self, tile_folder='game/map/data', asset_folder='game/map/sprites'):
        self.tile_folder = tile_folder
        self.asset_folder = asset_folder
        self.definitions = {}
        self._load_definitions()

    def _load_definitions(self):
        """Parses all XML files in the tile folder to load tile definitions."""
        for filename in os.listdir(self.tile_folder):
            if filename.endswith('.xml'):
                filepath = os.path.join(self.tile_folder, filename)
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    if root.tag == 'map' and root.get('type') == 'maptile':
                        char = root.get('char')
                        is_obstacle = root.get('is_obstacle', 'false').lower() == 'true'
                        sprite_node = root.find('visuals/sprite')
                        sprite_file = sprite_node.get('file') if sprite_node is not None else None
                        
                        if char and sprite_file:
                            image_path = os.path.join(self.asset_folder, sprite_file)
                            try:
                                image = pygame.image.load(image_path).convert_alpha()
                                self.definitions[char] = {
                                    'is_obstacle': is_obstacle,
                                    'image': image
                                }
                                print(f"Loaded tile definition for '{char}' from {filename} {image_path}")
                            except pygame.error as e:
                                print(f"Error loading image {image_path} for tile '{char}': {e}")
                except ET.ParseError as e:
                    print(f"Warning: Could not parse XML file {filename}: {e}")

class MapManager:
    def __init__(self, map_folder='game/map/world'):
        self.map_folder = map_folder
        # Change the default filename to .csv
        self.current_map_filename = 'map_0_1_0_0.csv'
        self.map_files = self._discover_maps()

    def _discover_maps(self):
        maps = {}
        for filename in os.listdir(self.map_folder):
            # Change the check to end with .csv
            if filename.startswith('map_') and filename.endswith('.csv'):
                try:
                    # Change the replacement to .csv
                    parts = filename.replace('map_', '').replace('.csv', '').split('_')
                    if len(parts) == 4:
                        connections = tuple(int(p) for p in parts)
                        maps[filename] = connections
                except ValueError:
                    print(f"Warning: Could not parse map filename {filename}")
        return maps

    def get_current_map_connections(self):
        return self.map_files.get(self.current_map_filename)

    def transition(self, direction):
        connections = self.get_current_map_connections()
        if not connections:
            return None

        connection_index = -1
        opposite_index = -1
        if direction == 'top':
            connection_index = 0
            opposite_index = 2 # bottom
        elif direction == 'right':
            connection_index = 1
            opposite_index = 3 # left
        elif direction == 'bottom':
            connection_index = 2
            opposite_index = 0 # top
        elif direction == 'left':
            connection_index = 3
            opposite_index = 1 # right

        connection_id = connections[connection_index]
        if connection_id == 0:
            return None

        for filename, file_connections in self.map_files.items():
            if filename == self.current_map_filename:
                continue
            if file_connections[opposite_index] == connection_id:
                self.current_map_filename = filename
                return filename
        
        print(f"Warning: No map found for transition '{direction}' from {self.current_map_filename}")
        return None

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

    # Use dimensions from the base layout (assuming all layers match)
    map_height = len(base_layout)
    map_width = len(base_layout[0]) if map_height > 0 else 0

    if not map_height or not map_width:
        print("Error: Base map layout is empty.")
        return [], [], None, [], []

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
                    if tile_def['is_obstacle']:
                         print(f"Warning: Ground layer tile '{char}' at ({x},{y}) is marked as obstacle. Ground tiles should not be obstacles.")
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
                #elif char == '#': # Keep supporting '#' as a generic obstacle
                #     obstacles.append(rect)
                else:
                    print(f"Warning: Undefined base tile character '{char}' at ({x},{y}).")


    # 3. Process Spawn Layer (P, Z, I)
    if len(spawn_layout) != map_height or (map_height > 0 and len(spawn_layout[0]) != map_width):
        print("Warning: Spawn layout dimensions mismatch base layout.")
    for y, row in enumerate(spawn_layout):
        if y >= map_height: break
        for x, char in enumerate(row):
            if x >= map_width: break
            if char == 'P':
                if player_spawn:
                     print(f"Warning: Multiple player spawns defined. Using last one found at ({x},{y}).")
                player_spawn = (x * TILE_SIZE, y * TILE_SIZE)
            elif char == 'Z':
                zombie_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
            elif char == 'I':
                item_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
            # Ignore other characters in the spawn layer

    if not player_spawn:
        print("Warning: No player spawn ('P') defined in spawn layer. Player will spawn at default position.")
        # Optionally set a default spawn like center of map or (0,0)
        # player_spawn = (map_width * TILE_SIZE // 2, map_height * TILE_SIZE // 2)

    return obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns

def spawn_initial_items(obstacles, item_spawns):
    items_on_ground = []
    for pos in item_spawns:
        item = Item.generate_random()
        item.rect.topleft = pos
        collision = any(item.rect.colliderect(ob) for ob in obstacles)
        if not collision:
            items_on_ground.append(item)
        else:
            print(f"Warning: Could not spawn item at {pos} due to collision with obstacle.")
    return items_on_ground

def spawn_initial_zombies(obstacles, zombie_spawns, items_on_ground):
    zombies = []
    all_spawned_entities = list(items_on_ground)
    spacing_obstacles = []

    for pos in zombie_spawns:
        # Spawn one zombie per 'Z' marker, or adjust ZOMBIES_PER_SPAWN if needed
        # ZOMBIES_PER_SPAWN = 1 # Usually 1 per marker is intended
        # for _ in range(ZOMBIES_PER_SPAWN):
            zombie = Zombie.create_random(pos[0], pos[1]) # Create zombie first

            # Use current obstacles + already spawned items + temp spacing rects
            current_collision_rects = obstacles + [e.rect for e in all_spawned_entities] + spacing_obstacles

            # Try to place the zombie using find_free_tile logic if needed,
            # but usually spawning directly at 'pos' is intended if 'pos' is valid.
            # Check if the designated spot 'pos' itself is blocked
            spawn_rect = pygame.Rect(pos[0], pos[1], TILE_SIZE, TILE_SIZE)
            initial_collision = any(spawn_rect.colliderect(ob) for ob in obstacles)

            if not initial_collision:
                zombie.rect.topleft = pos # Place at the exact spot
                zombie.x, zombie.y = pos[0], pos[1]
                zombies.append(zombie)
                all_spawned_entities.append(zombie) # Add to list for next checks
                # Add a temporary larger rect to prevent others spawning too close
                spacing_obstacles.append(zombie.rect.inflate(TILE_SIZE // 2, TILE_SIZE // 2))
            else:
                 print(f"Warning: Zombie spawn point {pos} is blocked by an obstacle. Trying nearby...")
                 # Fallback: Try finding a free tile near the original pos
                 if find_free_tile(zombie.rect, obstacles, all_spawned_entities, initial_pos=pos):
                     zombie.x = zombie.rect.x
                     zombie.y = zombie.rect.y
                     zombies.append(zombie)
                     all_spawned_entities.append(zombie)
                     spacing_obstacles.append(zombie.rect.inflate(TILE_SIZE // 2, TILE_SIZE // 2))
                 else:
                     print(f"Warning: Could not find free space to spawn zombie near {pos}.")
    return zombies

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
    return layout # Return list (possibly empty if file not found/error)