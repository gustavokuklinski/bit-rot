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
    Discovers all map chunks, builds a world grid,
    and stitches them into a single giant map.
    """
    print("Starting giant map load...")
    map_files = game.map_manager.map_files
    if not map_files:
        raise Exception("No map files found by MapManager.")
        
    map_folder = game.map_manager.map_folder
    
    world_grid = {}
    layouts = {}
    to_process = []
    processed_files = set()
    
    min_x, max_x, min_y, max_y = 0, 0, 0, 0

    start_file = game.map_manager.current_map_filename
    if start_file not in map_files:
         raise Exception(f"Starting map file {start_file} not found in discovered maps.")
         
    start_info = map_files[start_file]
    
    world_grid[(0, 0)] = start_info
    to_process.append((0, 0, start_info))
    processed_files.add(start_file)
    
    print("Building world grid...")
    
    while to_process:
        (cx, cy, c_info) = to_process.pop(0)
        
        min_x, max_x = min(min_x, cx), max(max_x, cx)
        min_y, max_y = min(min_y, cy), max(max_y, cy)

        try:
            base_name = c_info['filename'].rsplit('_map.csv', 1)[0]
            base_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_map.csv"))
            ground_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_ground.csv"))
            spawn_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_spawn.csv"))
            roof_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_roof.csv"))
            light_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_light.csv"))

            if not base_layout or not ground_layout or not spawn_layout or not roof_layout or not light_layout:
                print(f"Warning: Missing layout files for {base_name}. Skipping chunk.")
                continue
                
            layouts[(cx, cy)] = (base_layout, ground_layout, spawn_layout, roof_layout, light_layout)
        except Exception as e:
            print(f"Error loading layouts for {c_info['filename']}: {e}")
            continue

        neighbors = [
            (0, 0, -1, 2), # Top
            (1, 1, 0, 3),  # Right
            (2, 0, 1, 0),  # Bottom
            (3, -1, 0, 1)  # Left
        ]
        
        for conn_idx, dx, dy, opp_idx in neighbors:
            conn_id = c_info['connections'][conn_idx]
            if conn_id == 0:
                continue
            
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in world_grid:
                continue 

            found_neighbor = False
            for filename, n_info in map_files.items():
                if filename in processed_files:
                    continue
                
                if n_info['layer'] == c_info['layer'] and n_info['connections'][opp_idx] == conn_id:
                    world_grid[(nx, ny)] = n_info
                    to_process.append((nx, ny, n_info))
                    processed_files.add(filename)
                    found_neighbor = True
                    break

    chunk_w, chunk_h = CHUNK_SIZE, CHUNK_SIZE
    grid_w = (max_x - min_x) + 1
    grid_h = (max_y - min_y) + 1
    
    mega_w, mega_h = grid_w * chunk_w, grid_h * chunk_h
    print(f"Creating {grid_w}x{grid_h} mega-map ({mega_w}x{mega_h} tiles)...")

    mega_base = [[' ' for _ in range(mega_w)] for _ in range(mega_h)]
    mega_ground = [['bg_grass' for _ in range(mega_w)] for _ in range(mega_h)]
    mega_spawn = [[' ' for _ in range(mega_w)] for _ in range(mega_h)]
    mega_roof = [[' ' for _ in range(mega_w)] for _ in range(mega_h)]
    mega_light_grid = [[' ' for _ in range(mega_w)] for _ in range(mega_h)]
    
    possible_player_spawns = []

    for (grid_x, grid_y), (base, ground, spawn, roof, light) in layouts.items():
        offset_x = (grid_x - min_x) * chunk_w
        offset_y = (grid_y - min_y) * chunk_h
        

        for r in range(chunk_h):
            for c in range(chunk_w):
                if r < len(base) and c < len(base[r]) and base[r][c] and base[r][c] != ' ':
                    mega_base[offset_y + r][offset_x + c] = base[r][c]
                    
                if r < len(ground) and c < len(ground[r]) and ground[r][c] and ground[r][c] != ' ':
                    mega_ground[offset_y + r][offset_x + c] = ground[r][c]
                    
                if r < len(spawn) and c < len(spawn[r]) and spawn[r][c] and spawn[r][c] != ' ':
                    char = spawn[r][c]
                    if char == 'P':
                        possible_player_spawns.append((offset_x + c, offset_y + r))
                        mega_spawn[offset_y + r][offset_x + c] = ' '
                    else:
                        mega_spawn[offset_y + r][offset_x + c] = char
                        
                if r < len(roof) and c < len(roof[r]) and roof[r][c] and roof[r][c] != ' ':
                    mega_roof[offset_y + r][offset_x + c] = roof[r][c]

                if light and r < len(light) and c < len(light[r]) and light[r][c] and light[r][c] != ' ':
                    mega_light_grid[offset_y + r][offset_x + c] = light[r][c]

    print("Parsing mega-layouts...")
    
    # [FIX] Unpack 9 values including game.npc_spawn_points
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
    
    if possible_player_spawns:
        gx, gy = random.choice(possible_player_spawns)
        game.player_spawn = (gx * TILE_SIZE, gy * TILE_SIZE)
        print(f"Selected player spawn from markers at: {game.player_spawn}")
    else:
        print("No 'P' markers found. Attempting to spawn in random chunk...")
        chunk_coords = list(layouts.keys())
        spawn_found = False
        
        if chunk_coords:
            random.shuffle(chunk_coords)
            
            for (g_x, g_y) in chunk_coords:
                chunk_pixel_x = (g_x - min_x) * chunk_w * TILE_SIZE
                chunk_pixel_y = (g_y - min_y) * chunk_h * TILE_SIZE
                
                center_x = chunk_pixel_x + (chunk_w * TILE_SIZE // 2)
                center_y = chunk_pixel_y + (chunk_h * TILE_SIZE // 2)
                
                spawn_rect = pygame.Rect(center_x, center_y, TILE_SIZE, TILE_SIZE)
                
                collision = False
                for obs in game.obstacles:
                    if spawn_rect.colliderect(obs):
                        collision = True
                        break
                
                if not collision:
                    game.player_spawn = (center_x, center_y)
                    print(f"Selected random chunk spawn at: {game.player_spawn} (Chunk {g_x},{g_y})")
                    spawn_found = True
                    break
        
        if not spawn_found:
             if _parsed_spawn:
                  game.player_spawn = _parsed_spawn
             else:
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

    pattern = re.compile(r'map_L(\d+)_P(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_map\.csv')
    base_name_match = pattern.match(base_map_filename)
    
    if not base_name_match:
        print(f"CRITICAL: Base map filename does not match expected pattern: {base_map_filename}")
        return {}, {}, {}, {}, {}

    base_pos_id = base_name_match.group(2)
    base_conn_tuple = base_name_match.groups()[2:]
    base_connections_str = "_".join(base_conn_tuple)

    if master_width is not None and master_height is not None:
        target_width = master_width
        target_height = master_height
    else:
        base_map_file = os.path.join(base_path, base_map_filename)
        if not os.path.exists(base_map_file):
            found_any = False
            for i in range(1, 10):
                any_layer_file = os.path.join(base_path, f"map_L{i}_P{base_pos_id}_{base_connections_str}_map.csv")
                if os.path.exists(any_layer_file):
                    base_map_file = any_layer_file
                    found_any = True
                    break
            if not found_any:
                 print(f"CRITICAL: No map files found at all for base prefix P{base_pos_id} in {base_path}.")
                 return {}, {}, {}, {}, {}
        
        base_map_data = load_map_from_file(base_map_file)
        if not base_map_data or not base_map_data[0]:
            print(f"CRITICAL: Base map file is empty or invalid: {base_map_file}")
            return {}, {}, {}, {}, {}

        target_height = len(base_map_data)
        target_width = 0
        for row in base_map_data:
            if row:
                target_width = len(row)
                break
        
        if target_width == 0:
            target_width = 100

    for i in range(1, 10):
        layer_prefix = f"map_L{i}_P{base_pos_id}_{base_connections_str}"

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
    # [FIX] Assign npc spawns to game
    game.npc_spawn_points = npc_spawns

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
    if game.player.layer_switch_cooldown > 0:
        return

    player = game.player
    
    try:
        tile_x = player.rect.centerx // TILE_SIZE
        tile_y = player.rect.centery // TILE_SIZE
    except (AttributeError, TypeError):
        return

    current_map_data = game.map_data
    if not current_map_data:
        return
        
    if not (0 <= tile_y < len(current_map_data) and 0 <= tile_x < len(current_map_data[0])):
        return
        
    tile_id = current_map_data[tile_y][tile_x]
    
    match = re.match(r'\[(\d)\]', tile_id)
    
    if match:
        target_layer = int(match.group(1))
        if 0 < target_layer <= 9 and target_layer != game.current_layer_index:
            if set_active_layer(game, target_layer):
                game.player.layer_switch_cooldown = 30
            else:
                print(f"Warning: Tile [ {target_layer} ] points to non-existent layer.")

def check_for_map_transition(game):
    if getattr(game, 'is_giant_map', False):
        return

    if hasattr(game.player, 'map_transition_cooldown') and game.player.map_transition_cooldown > 0:
        game.player.map_transition_cooldown -= 1
        return

    player = game.player
    direction = None

    if player.rect.right < 0:
        direction = 'left'
    elif player.rect.left > game.map_width_pixels:
        direction = 'right'
    elif player.rect.bottom < 0:
        direction = 'top'
    elif player.rect.top > game.map_height_pixels:
        direction = 'bottom'

    if not direction:
        return 

    old_map_filename = game.map_manager.current_map_filename
    new_map_filename = game.map_manager.transition(direction)

    if new_map_filename:
        print(f"Transitioning from {old_map_filename} to map: {new_map_filename}")

        # [FIX] Unpack 5 return values (previously 4)
        game.all_map_layers, game.all_ground_layers, game.all_spawn_layers, game.all_roof_layers, game.all_light_layers = \
            load_all_map_layers(new_map_filename, base_path=game.map_manager.map_folder)

        game.layer_items.clear()
        game.layer_zombies.clear()
        game.layer_spawn_triggers.clear()

        if not set_active_layer(game, game.current_layer_index):
            print(f"CRITICAL: Failed to set active layer {game.current_layer_index} on new map {new_map_filename}")
            if not set_active_layer(game, 1):
                print("CRITICAL: Failed to load layer 1 as fallback. Transition aborted.")
                return 

        if direction == 'left':
            player.rect.right = game.map_width_pixels - 5
            player.x = player.rect.x
        elif direction == 'right':
            player.rect.left = 5
            player.x = player.rect.x
        elif direction == 'top':
            player.rect.bottom = game.map_height_pixels - 5
            player.y = player.rect.y
        elif direction == 'bottom':
            player.rect.top = 5
            player.y = player.rect.y
            
        if not hasattr(game.player, 'map_transition_cooldown'):
            game.player.map_transition_cooldown = 0
        game.player.map_transition_cooldown = 30