import os
import re
import pygame
import random
from core.data.config import *
import core.data.config
from core.entities.item.item import Item
from core.entities.zombie.zombie import Zombie
from core.entities.zombie.corpse import Corpse
from core.map.map_loader import load_map_from_file, parse_layered_map_layout
from core.map.tile_manager import TileManager
from core.map.spawn_manager import spawn_initial_items, spawn_initial_zombies

def resize_map_layer(layer_data, target_width, target_height, fill_value=' '):
    """
    Resizes a map layer to the target dimensions.
    """
    current_height = len(layer_data)
    new_layer = [[fill_value for _ in range(target_width)] for _ in range(target_height)]
    
    for y in range(min(current_height, target_height)):
        current_row_width = len(layer_data[y])
        for x in range(min(current_row_width, target_width)):
            new_layer[y][x] = layer_data[y][x]
            
    return new_layer

def load_giant_map(game):
    """
    Loads the single big world map file. 
    Replaces the old logic that stitched multiple chunks together.
    """
    print("Starting giant map load...")
    map_files = game.map_manager.map_files
    if not map_files:
        raise Exception("No map files found by MapManager.")
        
    map_folder = game.map_manager.map_folder
    
    start_file = game.map_manager.current_map_filename
    if start_file not in map_files:
         # Fallback search if the exact filename isn't in the list but exists on disk
         if os.path.exists(os.path.join(map_folder, start_file)):
             print(f"Warning: {start_file} not in discovered list, but exists. Loading anyway.")
         else:
             raise Exception(f"Starting map file {start_file} not found in discovered maps.")
    
    # Load the single world map files
    base_name = start_file.rsplit('_map.csv', 1)[0]
    
    print(f"Loading world map from: {base_name}")
    
    base_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_map.csv"))
    ground_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_ground.csv"))
    spawn_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_spawn.csv"))
    roof_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_roof.csv"))
    light_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_light.csv"))

    if not base_layout:
        raise Exception("Error: World map file is empty or missing.")

    if not ground_layout: ground_layout = []
    if not spawn_layout: spawn_layout = []
    if not roof_layout: roof_layout = []
    if not light_layout: light_layout = []

    # Get dimensions directly from the loaded file
    mega_h = len(base_layout)
    mega_w = len(base_layout[0]) if mega_h > 0 else 0
    
    print(f"World map dimensions: {mega_w}x{mega_h} tiles.")

    # In this new system, the loaded file IS the mega map. 
    # We no longer need to copy it into a larger grid.
    mega_base = base_layout
    mega_ground = ground_layout
    mega_spawn = spawn_layout
    mega_roof = roof_layout
    mega_light_grid = light_layout

    # Extract possible player spawns from the loaded spawn layer
    possible_player_spawns = []
    for r in range(mega_h):
        for c in range(mega_w):
            if r < len(mega_spawn) and c < len(mega_spawn[r]):
                if mega_spawn[r][c] == 'P':
                    possible_player_spawns.append((c * TILE_SIZE, r * TILE_SIZE))
                    mega_spawn[r][c] = ' ' # Clear marker

    print("Parsing mega-layouts...")
    
    (game.obstacles, 
     game.renderable_tiles, 
     _parsed_spawn, 
     game.zombie_spawns, 
     game.item_spawns, 
     game.containers,
     game.roof_tiles,
     map_lights_list,
     game.npc_spawn_points) = parse_layered_map_layout(
         mega_base, mega_ground, mega_spawn, mega_roof, mega_light_grid, game.tile_manager
     )
    
    # [MEMORY OPTIMIZATION] 
    # Clear the huge render lists for giant maps to save RAM.
    # The new draw loop uses grid-based rendering (game.map_data) instead.
    if mega_w > 500 or mega_h > 500:
        print("Optimizing memory for giant map...")
        game.renderable_tiles = [] 
        game.roof_tiles = []
    
    if possible_player_spawns:
        game.player_spawn = random.choice(possible_player_spawns)
        print(f"Selected player spawn from markers at: {game.player_spawn}")
    else:
        print("No 'P' markers found. Defaulting to center.")
        game.player_spawn = (mega_w * TILE_SIZE // 2, mega_h * TILE_SIZE // 2)

    game.map_data = mega_base
    game.current_zombie_spawns = game.zombie_spawns
    
    game.all_map_layers[1] = mega_base
    game.all_ground_layers[1] = mega_ground
    game.all_spawn_layers[1] = mega_spawn

    game.all_light_layers[1] = mega_light_grid
    game.light_data = mega_light_grid
    game.map_lights = map_lights_list

    game.world_min_x = 0
    game.world_min_y = 0
    game.world_width_pixels = mega_w * TILE_SIZE
    game.world_height_pixels = mega_h * TILE_SIZE

    print("Adding world boundary obstacles...")
    game.obstacles.append(pygame.Rect(-100, -100, 100, game.world_height_pixels + 200))
    game.obstacles.append(pygame.Rect(game.world_width_pixels, -100, 100, game.world_height_pixels + 200))
    game.obstacles.append(pygame.Rect(-100, -100, game.world_width_pixels + 200, 100))
    game.obstacles.append(pygame.Rect(-100, game.world_height_pixels, game.world_width_pixels + 200, 100))

    print(f"Giant map load complete. Player spawn: {game.player_spawn}")

    game.is_giant_map = True
    game.map_width_pixels = game.world_width_pixels
    game.map_height_pixels = game.world_height_pixels

    print("Populating spawn point grid for giant map...")

    game.spawn_point_grid.clear()
    GRID_SIZE_SPAWNS = game.SPAWN_GRID_SIZE
    for sp_pos in game.current_zombie_spawns:
        grid_x = int(sp_pos[0] // GRID_SIZE_SPAWNS)
        grid_y = int(sp_pos[1] // GRID_SIZE_SPAWNS)
        cell = (grid_x, grid_y)
        if cell not in game.spawn_point_grid:
            game.spawn_point_grid[cell] = [sp_pos] 
        else:
            game.spawn_point_grid[cell].append(sp_pos)

def load_all_map_layers(base_map_filename, master_width=None, master_height=None, base_path=MAP_DIR):
    all_map_layers = {}
    all_ground_layers = {}
    all_spawn_layers = {}
    all_roof_layers = {}
    all_light_layers = {}

    # Regex for new single world map: map_L<layer>_world_map.csv
    world_pattern = re.compile(r'map_L(\d+)_world_map\.csv')
    world_match = world_pattern.match(base_map_filename)

    if not world_match:
        # Fallback check for exact filename matching if using custom names, 
        # or if caller passed full path, but strictly enforce no legacy chunk parsing here.
        if "world_map" not in base_map_filename:
             print(f"Note: Base map filename '{base_map_filename}' does not match standard world pattern.")
    
    # Load dimensions from Layer 1 first to determine target width/height
    base_map_file = os.path.join(base_path, base_map_filename)
    if not os.path.exists(base_map_file):
         print(f"CRITICAL: World map file not found: {base_map_file}")
         return {}, {}, {}, {}, {}

    base_map_data = load_map_from_file(base_map_file)
    if not base_map_data or not base_map_data[0]:
        print(f"CRITICAL: Base map file is empty or invalid: {base_map_file}")
        return {}, {}, {}, {}, {}

    if master_width is not None and master_height is not None:
        target_width = master_width
        target_height = master_height
    else:
        target_height = len(base_map_data)
        target_width = len(base_map_data[0]) if target_height > 0 else 0

    # Load Layers 1 through 9
    for i in range(1, 10):
        # Construct filename based on the new standard
        layer_prefix = f"map_L{i}_world"
        
        # If the base filename provided was somehow different (e.g. custom save),
        # we might need to handle that, but for now we assume standard naming 
        # for layers L2-L9 if L1 is standard.
        if "world_map" not in base_map_filename and i == 1:
             # Special case: Just load the provided filename for L1
             layer_map_file_relative = base_map_filename
             # Try to deduce suffix for others
             base_prefix = base_map_filename.rsplit('_map.csv', 1)[0]
             layer_ground_file_relative = f"{base_prefix}_ground.csv"
             layer_spawn_file_relative = f"{base_prefix}_spawn.csv"
             layer_roof_file_relative = f"{base_prefix}_roof.csv"
             layer_light_file_relative = f"{base_prefix}_light.csv"
        else:
             layer_map_file_relative = f"{layer_prefix}_map.csv"
             layer_ground_file_relative = f"{layer_prefix}_ground.csv"
             layer_spawn_file_relative = f"{layer_prefix}_spawn.csv"
             layer_roof_file_relative = f"{layer_prefix}_roof.csv"
             layer_light_file_relative = f"{layer_prefix}_light.csv"
        
        layer_map_file = os.path.join(base_path, layer_map_file_relative)
        layer_ground_file = os.path.join(base_path, layer_ground_file_relative)
        layer_spawn_file = os.path.join(base_path, layer_spawn_file_relative)
        layer_roof_file = os.path.join(base_path, layer_roof_file_relative)
        layer_light_file = os.path.join(base_path, layer_light_file_relative)

        map_data = load_map_from_file(layer_map_file)
        ground_data = load_map_from_file(layer_ground_file)
        spawn_data = load_map_from_file(layer_spawn_file)
        roof_data = load_map_from_file(layer_roof_file)
        light_data = load_map_from_file(layer_light_file)

        if not map_data and not ground_data and not spawn_data and not roof_data  and not light_data:
            continue
            
        if map_data:
            map_data = resize_map_layer(map_data, target_width, target_height, fill_value=' ')
            all_map_layers[i] = map_data
        
        if ground_data:
            ground_data = resize_map_layer(ground_data, target_width, target_height, fill_value=' ')
            all_ground_layers[i] = ground_data
        
        if spawn_data:
            spawn_data = resize_map_layer(spawn_data, target_width, target_height, fill_value=' ') 
            all_spawn_layers[i] = spawn_data

        if roof_data:
            roof_data = resize_map_layer(roof_data, target_width, target_height, fill_value=' ') 
            all_roof_layers[i] = roof_data
        
        if light_data:
            light_data = resize_map_layer(light_data, target_width, target_height, fill_value=' ')
            all_light_layers[i] = light_data

    return all_map_layers, all_ground_layers, all_spawn_layers, all_roof_layers, all_light_layers

def _rebuild_world_from_data(game):
    game.obstacles.clear()
    game.containers.clear()

    # [FIX] Unpack 9 variables
    obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers, roof_tiles, map_lights, npc_spawns = \
        parse_layered_map_layout(game.map_data, game.ground_data, game.spawn_data, game.roof_data, game.light_data, game.tile_manager)

    game.obstacles = obstacles
    game.renderable_tiles = renderable_tiles
    game.containers = containers
    game.roof_tiles = roof_tiles
    game.map_lights = map_lights
    game.npc_spawn_points = npc_spawns
    
    # [MEMORY OPTIMIZATION]
    # Clear render lists if huge
    map_h = len(game.map_data)
    map_w = len(game.map_data[0]) if map_h > 0 else 0
    if map_w > 500 or map_h > 500:
         game.renderable_tiles = []
         game.roof_tiles = []

    return item_spawns, zombie_spawns

def set_active_layer(game, layer_index):
    if layer_index not in game.all_map_layers:
        print(f"Error: Attempted to switch to non-existent layer {layer_index}")
        return False

    current_filename = game.map_manager.current_map_filename
    new_filename = re.sub(r'map_L(\d+)_', f'map_L{layer_index}_', current_filename)

    if new_filename in game.map_manager.map_files:
        game.map_manager.current_map_filename = new_filename
    else:
        game.map_manager.current_map_filename = new_filename

    if game.current_layer_index in game.layer_items:
        game.layer_items[game.current_layer_index] = game.items_on_ground[:]
    if game.current_layer_index in game.layer_zombies:
        game.layer_zombies[game.current_layer_index] = game.zombies[:]

    print(f"Setting active layer to: {layer_index}")
    game.current_layer_index = layer_index
    
    game.map_data = game.all_map_layers[layer_index]
    game.ground_data = game.all_ground_layers.get(layer_index, [])
    game.spawn_data = game.all_spawn_layers.get(layer_index, [])
    game.roof_data = game.all_roof_layers.get(layer_index, [])
    game.light_data = game.all_light_layers.get(layer_index, [])

    if not getattr(game, 'is_giant_map', False) and layer_index == 1:
        if game.map_data:
            game.map_height_pixels = len(game.map_data) * TILE_SIZE
            game.map_width_pixels = len(game.map_data[0]) * TILE_SIZE
        else:
            if game.map_data:
                game.map_height_pixels = len(game.map_data) * TILE_SIZE
                game.map_width_pixels = len(game.map_data[0]) * TILE_SIZE
            else:
                game.map_height_pixels = 0
                game.map_width_pixels = 0

    item_spawns, zombie_spawns = _rebuild_world_from_data(game)

    game.current_zombie_spawns = zombie_spawns
    game.layer_spawn_triggers.setdefault(layer_index, set())

    if getattr(game, 'is_giant_map', False) and layer_index == 1:
        pass
    else:
        game.spawn_point_grid.clear()
        GRID_SIZE_SPAWNS = game.SPAWN_GRID_SIZE 
        for sp_pos in game.current_zombie_spawns:
            grid_x = int(sp_pos[0] // GRID_SIZE_SPAWNS)
            grid_y = int(sp_pos[1] // GRID_SIZE_SPAWNS)
            cell = (grid_x, grid_y)
            if cell not in game.spawn_point_grid:
                game.spawn_point_grid[cell] = [sp_pos]
            else:
                game.spawn_point_grid[cell].append(sp_pos)

    if layer_index in game.layer_items:
        game.items_on_ground = game.layer_items[layer_index][:]
    else:
        game.items_on_ground = spawn_initial_items(game.obstacles, item_spawns)
        game.layer_items[layer_index] = game.items_on_ground[:]

    if layer_index in game.layer_zombies:
        game.zombies = game.layer_zombies[layer_index][:]
    else:
        game.zombies = []
        game.layer_zombies[layer_index] = []
    
    return True

def check_for_layer_teleport(game):
    # 1. Respect Cooldown (prevents instant bouncing back and forth)
    if game.player.layer_switch_cooldown > 0:
        return

    player = game.player
    
    # 2. Get Player Grid Position
    try:
        tile_x = int(player.rect.centerx // TILE_SIZE)
        tile_y = int(player.rect.centery // TILE_SIZE)
    except (AttributeError, TypeError):
        return

    current_map_data = game.map_data
    if not current_map_data:
        return
    
    # 3. Check Bounds
    if not (0 <= tile_y < len(current_map_data) and 0 <= tile_x < len(current_map_data[0])):
        return
        
    # 4. Get Tile Definition
    tile_char = current_map_data[tile_y][tile_x]
    tile_def = game.tile_manager.definitions.get(tile_char)
    
    # 5. Check 'is_stair' Attribute and Teleport
    if tile_def and tile_def.get('is_stair'):
        target_layer = tile_def.get('target_layer')
        
        if target_layer and target_layer != game.current_layer_index:
            print(f"Auto-teleport detected: Moving to Layer {target_layer}")
            if set_active_layer(game, target_layer):
                # Set a longer cooldown for auto-teleport to ensure player steps off the target stair
                game.player.layer_switch_cooldown = 60