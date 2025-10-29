# core/world_layers.py
import os
import re
import pygame
from data.config import *
from core.entities.item import Item
from core.entities.zombie import Zombie
from core.map.map_loader import load_map_from_file, parse_layered_map_layout
from core.map.tile_manager import TileManager
from core.map.spawn_manager import spawn_initial_items, spawn_initial_zombies

def resize_map_layer(layer_data, target_width, target_height, fill_value=''):
    """
    Resizes a map layer to the target dimensions.
    - Pads with `fill_value` if smaller.
    - Trims if larger.
    """
    # Get current dimensions
    current_height = len(layer_data)
    current_width = len(layer_data[0]) if current_height > 0 else 0

    # If it's already the correct size, do nothing
    if current_width == target_width and current_height == target_height:
        return layer_data

    print(f"Resizing layer from ({current_width}x{current_height}) to ({target_width}x{target_height})")

    # Create a new blank layer with the target dimensions
    new_layer = [[fill_value for _ in range(target_width)] for _ in range(target_height)]

    # Copy the old data into the new layer
    for y in range(min(current_height, target_height)):
        for x in range(min(current_width, target_height)):
            new_layer[y][x] = layer_data[y][x]
            
    return new_layer

def load_all_map_layers(base_map_filename):
    """
    Loads all map layers (1-9) associated with a base map name.
    e.g., "map_0_1_0_0.csv" will also load "map_0_1_0_0_layer2.csv", etc.
    
    Returns three dictionaries:
    {1: map_data, 2: map_data_l2}, {1: ground_data, 2: ground_data_l2}, ...
    """
    all_map_layers = {}
    all_ground_layers = {}
    all_spawn_layers = {}

    base_name_match = re.match(r'map_L(\d+)_P((?:\d+_)*\d+)', base_map_filename.replace('_map.csv', ''))
    if not base_name_match:
        print(f"CRITICAL: Base map filename does not match expected pattern: {base_map_filename}")
        return {}, {}, {}

    base_layer_num = int(base_name_match.group(1))
    base_connections_str = base_name_match.group(2)

    print(f"Loading all layers for base map: {base_map_filename}")

    # --- First, load the base layer (1) to determine the target dimensions ---
    base_map_file = os.path.join(MAP_DIR, base_map_filename)
    if not os.path.exists(base_map_file):
        print(f"CRITICAL: Base map file not found: {base_map_file}")
        return {}, {}, {}
        
    base_map_data = load_map_from_file(base_map_file)
    if not base_map_data or not base_map_data[0]:
        print(f"CRITICAL: Base map file is empty or invalid: {base_map_file}")
        return {}, {}, {}

    target_height = len(base_map_data)
    target_width = len(base_map_data[0])
    print(f"Base map dimensions set to: {target_width}x{target_height}")

    # --- Now, loop and load all layers, resizing them to match the base ---
    for i in range(1, 10): # i = 1, 2, 3, ..., 9
        
        # 1. Determine filenames for this layer using the new convention
        layer_prefix = f"map_L{i}_P{base_connections_str}"

        layer_map_file_relative = f"{layer_prefix}_map.csv"
        layer_ground_file_relative = f"{layer_prefix}_ground.csv"
        layer_spawn_file_relative = f"{layer_prefix}_spawn.csv"
        
        layer_map_file = os.path.join(MAP_DIR, layer_map_file_relative)
        
        # Check if the main map file for this layer exists. If not, we can stop.
        if not os.path.exists(layer_map_file):
            if i > 1: # Don't log for missing optional layers beyond 1
                print(f"Stopping layer search at {i}. File not found: {layer_map_file}")
            continue

        print(f"Loading layer {i} from {layer_map_file}")
        
        # Load the primary map data for the layer
        map_data = load_map_from_file(layer_map_file)
        if not map_data or not map_data[0]:
            print(f"Warning: Layer {i} map file is empty. Skipping.")
            continue
        
        # Resize it to match the base layer
        map_data = resize_map_layer(map_data, target_width, target_height)
        all_map_layers[i] = map_data

        # --- Load and resize optional ground and spawn layers ---
        layer_ground_file = os.path.join(MAP_DIR, layer_ground_file_relative)
        if os.path.exists(layer_ground_file):
            ground_data = load_map_from_file(layer_ground_file)
            if ground_data:
                ground_data = resize_map_layer(ground_data, target_width, target_height)
                all_ground_layers[i] = ground_data
        
        layer_spawn_file = os.path.join(MAP_DIR, layer_spawn_file_relative)
        if os.path.exists(layer_spawn_file):
            spawn_data = load_map_from_file(layer_spawn_file)
            if spawn_data:
                spawn_data = resize_map_layer(spawn_data, target_width, target_height, fill_value=' ') # Use space for empty spawn
                all_spawn_layers[i] = spawn_data

    return all_map_layers, all_ground_layers, all_spawn_layers

def _rebuild_world_from_data(game):
    """
    (Internal) Clears and repopulates obstacles, entities, etc., from the
    CURRENTLY active game.map_data and game.spawn_data.
    """
    # Clear all current-layer entities
    game.obstacles.clear()
    game.containers.clear()
    game.items_on_ground.clear()
    game.zombies.clear()

    # Call parse_layered_map_layout to get the new world data
    obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers = \
        parse_layered_map_layout(game.map_data, game.ground_data, game.spawn_data, game.tile_manager)

    # Assign the new data to the game object
    game.obstacles = obstacles
    game.renderable_tiles = renderable_tiles
    game.containers = containers

    # Handle spawning of items and zombies (these functions will need to be moved to spawn_manager.py)
    # For now, we'll keep them here and assume they are imported or defined elsewhere if needed.
    game.items_on_ground = spawn_initial_items(game.obstacles, item_spawns)
    game.zombies = spawn_initial_zombies(game.obstacles, zombie_spawns, game.items_on_ground)

    # Note: Player spawn is handled in game.load_map, so we don't re-assign it here.

def set_active_layer(game, layer_index):
    """
    Switches the game's active map data to the specified layer and rebuilds the world.
    """
    if layer_index not in game.all_map_layers:
        print(f"Error: Attempted to switch to non-existent layer {layer_index}")
        return False

    print(f"Setting active layer to: {layer_index}")
    game.current_layer_index = layer_index
    
    # Set the game's main data properties to point to the new layer's data
    game.map_data = game.all_map_layers[layer_index]
    game.ground_data = game.all_ground_layers.get(layer_index, [])
    game.spawn_data = game.all_spawn_layers.get(layer_index, [])

    print(f"Active map_data shape: ({len(game.map_data)}, {len(game.map_data[0]) if game.map_data else 0})")
    print(f"Active ground_data shape: ({len(game.ground_data)}, {len(game.ground_data[0]) if game.ground_data else 0})")
    print(f"Active spawn_data shape: ({len(game.spawn_data)}, {len(game.spawn_data[0]) if game.spawn_data else 0})")
    
    # Rebuild obstacles, zombies, etc.
    _rebuild_world_from_data(game)
    
    return True

def check_for_layer_teleport(game):
    """
    Checks if player is on a teleport tile (e.g., [2]) and switches layers.
    Called every frame from update.py.
    """
    if game.player.layer_switch_cooldown > 0:
        return # Player is in cooldown

    player = game.player
    
    try:
        tile_x = player.rect.centerx // TILE_SIZE
        tile_y = player.rect.centery // TILE_SIZE
    except (AttributeError, TypeError):
        return # Player rect not ready

    # Get the tile ID from the CURRENTLY active map
    current_map_data = game.map_data
    if not current_map_data:
        return
        
    # Check bounds
    if not (0 <= tile_y < len(current_map_data) and 0 <= tile_x < len(current_map_data[0])):
        return # Player is out of bounds
        
    tile_id = current_map_data[tile_y][tile_x]
    
    # Check for teleporter tile like [1], [2], ... [9]
    match = re.match(r'\[(\d)\]', tile_id)
    
    if match:
        target_layer = int(match.group(1))
        
        # Check if target is valid and not the *current* layer
        if 0 < target_layer <= 9 and target_layer != game.current_layer_index:
            
            # Try to set the new layer
            if set_active_layer(game, target_layer):
                # Success! Set cooldown to prevent instant-return
                game.player.layer_switch_cooldown = 30 # 30 frames (approx 0.5 sec)
            else:
                print(f"Warning: Tile [ {target_layer} ] points to non-existent layer.")