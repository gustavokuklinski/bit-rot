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
from core.entities.npc.npc import NPC
from core.placement import find_free_tile

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
    Loads the single big world map file and dynamically pulls in all available layers (L1, L2, L3, etc.).
    """
    print("Starting giant map load...")
    map_files = game.map_manager.map_files
    if not map_files:
        raise Exception("No map files found by MapManager.")
        
    map_folder = game.map_manager.map_folder
    start_file = game.map_manager.current_map_filename
    
    if start_file not in map_files:
         if os.path.exists(os.path.join(map_folder, start_file)):
             print(f"Warning: {start_file} not in discovered list, but exists. Loading anyway.")
         else:
             raise Exception(f"Starting map file {start_file} not found in discovered maps.")
    
    # Initialize dictionaries if they don't exist yet
    if not hasattr(game, 'all_map_layers'): game.all_map_layers = {}
    if not hasattr(game, 'all_ground_layers'): game.all_ground_layers = {}
    if not hasattr(game, 'all_spawn_layers'): game.all_spawn_layers = {}
    if not hasattr(game, 'all_roof_layers'): game.all_roof_layers = {}
    if not hasattr(game, 'all_light_layers'): game.all_light_layers = {}

    # Dynamically load up to 10 map layers
    for layer_idx in range(1, 10):
        # Replace the layer index safely (e.g., map_L1_world_map.csv -> map_L2_world_map.csv)
        layer_start_file = re.sub(r'L\d+', f'L{layer_idx}', start_file)
        base_name = layer_start_file.rsplit('_map.csv', 1)[0]
        map_path = os.path.join(map_folder, f"{base_name}_map.csv")
        
        if not os.path.exists(map_path):
            if layer_idx == 1:
                raise Exception(f"Starting map file {start_file} not found.")
            else:
                break # Reached the highest layer available, stop looping
                
        print(f"Loading world map layer {layer_idx} from: {base_name}")
        
        base_layout = load_map_from_file(map_path)
        ground_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_ground.csv"))
        spawn_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_spawn.csv"))
        roof_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_roof.csv"))
        light_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_light.csv"))

        if not base_layout:
            if layer_idx == 1:
                raise Exception("Error: World map base layout is empty or missing.")
            else:
                break

        if not ground_layout: ground_layout = []
        if not spawn_layout: spawn_layout = []
        if not roof_layout: roof_layout = []
        if not light_layout: light_layout = []

        # Store in game memory
        game.all_map_layers[layer_idx] = base_layout
        game.all_ground_layers[layer_idx] = ground_layout
        game.all_spawn_layers[layer_idx] = spawn_layout
        game.all_roof_layers[layer_idx] = roof_layout
        game.all_light_layers[layer_idx] = light_layout

        # Process initial physics and collisions only for the starting Layer (1)
        if layer_idx == 1:
            mega_h = len(base_layout)
            mega_w = len(base_layout[0]) if mega_h > 0 else 0
            
            print(f"World map layer 1 dimensions: {mega_w}x{mega_h} tiles.")

            possible_player_spawns = []
            for r in range(mega_h):
                for c in range(mega_w):
                    if r < len(spawn_layout) and c < len(spawn_layout[r]):
                        if spawn_layout[r][c] == 'P':
                            possible_player_spawns.append((c * TILE_SIZE, r * TILE_SIZE))
                            spawn_layout[r][c] = ' ' 

            print("Parsing Layer 1 mega-layouts...")
            
            (game.obstacles, 
             game.renderable_tiles, 
             _parsed_spawn, 
             game.zombie_spawns, 
             game.item_spawns, 
             game.containers,
             game.roof_tiles,
             map_lights_list,
             game.npc_spawn_points) = parse_layered_map_layout(
                 base_layout, ground_layout, spawn_layout, roof_layout, light_layout, game.tile_manager
             )
            
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

            game.map_data = base_layout
            game.ground_data = ground_layout
            game.spawn_data = spawn_layout
            game.roof_data = roof_layout
            game.light_data = light_layout
            game.current_zombie_spawns = game.zombie_spawns
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

            game.is_giant_map = True
            game.map_width_pixels = game.world_width_pixels
            game.map_height_pixels = game.world_height_pixels

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

    print(f"Giant map load complete. Successfully loaded {len(game.all_map_layers)} layers.")


def load_all_map_layers(base_map_filename, master_width=None, master_height=None, base_path=MAP_DIR):
    all_map_layers = {}
    all_ground_layers = {}
    all_spawn_layers = {}
    all_roof_layers = {}
    all_light_layers = {}

    chunk_pattern = re.compile(r'map_L(\d+)_(\d+)_(\d+)_map\.csv')
    chunk_match = chunk_pattern.match(base_map_filename)
    
    world_pattern = re.compile(r'map_L(\d+)_world_map\.csv')
    world_match = world_pattern.match(base_map_filename)

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

    # Expand search from Layer 1 up to Layer 10
    for i in range(1, 10):
        if chunk_match:
            gx = chunk_match.group(2)
            gy = chunk_match.group(3)
            layer_prefix = f"map_L{i}_{gx}_{gy}"
        elif world_match:
            layer_prefix = f"map_L{i}_world"
        else:
            base_prefix = base_map_filename.rsplit('_map.csv', 1)[0]
            layer_prefix = re.sub(r'L\d+', f'L{i}', base_prefix)

        layer_map_file_relative = f"{layer_prefix}_map.csv"
        layer_ground_file_relative = f"{layer_prefix}_ground.csv"
        layer_spawn_file_relative = f"{layer_prefix}_spawn.csv"
        layer_roof_file_relative = f"{layer_prefix}_roof.csv"
        layer_light_file_relative = f"{layer_prefix}_light.csv"

        layer_map_file = os.path.join(base_path, layer_map_file_relative)
        
        # Stop looping if this layer doesn't exist
        if not os.path.exists(layer_map_file):
            if i > 1:
                break
            continue

        layer_ground_file = os.path.join(base_path, layer_ground_file_relative)
        layer_spawn_file = os.path.join(base_path, layer_spawn_file_relative)
        layer_roof_file = os.path.join(base_path, layer_roof_file_relative)
        layer_light_file = os.path.join(base_path, layer_light_file_relative)

        map_data = load_map_from_file(layer_map_file)
        ground_data = load_map_from_file(layer_ground_file)
        spawn_data = load_map_from_file(layer_spawn_file)
        roof_data = load_map_from_file(layer_roof_file)
        light_data = load_map_from_file(layer_light_file)

        if not map_data and not ground_data and not spawn_data and not roof_data and not light_data:
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

    obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers, roof_tiles, map_lights, npc_spawns = \
        parse_layered_map_layout(game.map_data, game.ground_data, game.spawn_data, game.roof_data, game.light_data, game.tile_manager)

    game.obstacles = obstacles
    game.renderable_tiles = renderable_tiles
    game.containers = containers
    game.roof_tiles = roof_tiles
    game.map_lights = map_lights
    game.npc_spawn_points = npc_spawns
    
    if getattr(game, 'current_layer_index', 1) == 1:
        vehicles_list = getattr(game, 'vehicles', [])
        if not vehicles_list and hasattr(game, 'map_manager'):
            vehicles_list = getattr(game.map_manager, 'vehicles', [])
            
        for v in vehicles_list:
            if v not in game.containers:
                game.containers.append(v)
            if hasattr(v, 'rect') and v.rect not in game.obstacles:
                game.obstacles.append(v.rect)
    
    map_h = len(game.map_data)
    map_w = len(game.map_data[0]) if map_h > 0 else 0
    if map_w > 500 or map_h > 500:
         game.renderable_tiles = []
         game.roof_tiles = []

    return item_spawns, zombie_spawns

def set_active_layer(game, layer_index, skip_cache_save=False):
    if layer_index not in game.all_map_layers:
        print(f"Error: Attempted to switch to non-existent layer {layer_index}")
        return False

    current_filename = game.map_manager.current_map_filename
    
    # --- CACHE CURRENT LAYER TO MAP_STATES ---
    if not skip_cache_save and getattr(game, 'current_layer_index', None) is not None and getattr(game, 'map_data', None):
        if current_filename not in game.map_states:
            game.map_states[current_filename] = {}
            
        game.map_states[current_filename]['zombies'] = list(game.zombies)
        
        chasing_animals = []
        if hasattr(game, 'active_animals'):
            chasing_animals = [a for a in game.active_animals if getattr(a, 'state', '') == 'chasing']
            game.map_states[current_filename]['active_animals'] = [a for a in game.active_animals if a not in chasing_animals]
        
        chunk_npcs = []
        if hasattr(game, 'npcs'):
            for npc in game.npcs:
                if not getattr(npc, 'is_following', False):
                    chunk_npcs.append(npc)
            game.map_states[current_filename]['npcs'] = chunk_npcs
            
        game.map_states[current_filename]['items_on_ground'] = [i for i in game.items_on_ground if i not in chasing_animals]
        
        clean_containers = [c for c in game.containers if c != getattr(getattr(game, 'player', None), 'vehicle', None)]
        game.map_states[current_filename]['containers'] = clean_containers
        
        if hasattr(game.map_manager, 'vehicles'):
            clean_vehicles = [v for v in game.map_manager.vehicles if v != getattr(getattr(game, 'player', None), 'vehicle', None)]
            game.map_states[current_filename]['vehicles'] = clean_vehicles

    new_filename = re.sub(r'map_L(\d+)_', f'map_L{layer_index}_', current_filename)
    game.map_manager.current_map_filename = new_filename

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
            game.map_height_pixels = 0
            game.map_width_pixels = 0

    item_spawns, zombie_spawns = _rebuild_world_from_data(game)

    game.cached_obstacle_grid = {}
    game.cached_obstacle_count = -1
    game.current_zombie_spawns = zombie_spawns
    game.layer_spawn_triggers.setdefault(layer_index, set())

    if not getattr(game, 'is_giant_map', False):
        game.spawn_point_grid.clear()
        GRID_SIZE_SPAWNS = getattr(game, 'SPAWN_GRID_SIZE', 512) 
        for sp_pos in game.current_zombie_spawns:
            grid_x = int(sp_pos[0] // GRID_SIZE_SPAWNS)
            grid_y = int(sp_pos[1] // GRID_SIZE_SPAWNS)
            cell = (grid_x, grid_y)
            if cell not in game.spawn_point_grid:
                game.spawn_point_grid[cell] = [sp_pos]
            else:
                game.spawn_point_grid[cell].append(sp_pos)

    # --- RESTORE OR SPAWN NEW LAYER STATE ---
    if not skip_cache_save:
        chasing_animals = []
        if hasattr(game, 'active_animals'):
            chasing_animals = [a for a in game.active_animals if getattr(a, 'state', '') == 'chasing']
        
        followers = []
        if hasattr(game, 'npcs'):
            for npc in game.npcs:
                if getattr(npc, 'is_following', False):
                    followers.append(npc)

        if new_filename in game.map_states:
            game.items_on_ground = game.map_states[new_filename].get('items_on_ground', [])
            game.zombies = game.map_states[new_filename].get('zombies', [])
            if hasattr(game, 'active_animals'):
                game.active_animals = game.map_states[new_filename].get('active_animals', [])
                
            if hasattr(game, 'npcs'):
                game.npcs.empty()
                for npc in game.map_states[new_filename].get('npcs', []):
                    game.npcs.add(npc)
                    
            if 'containers' in game.map_states[new_filename]:
                default_container_rects = [c.rect for c in game.containers]
                obstacle_container_rects = [rect for rect in default_container_rects if rect in game.obstacles]
                
                game.obstacles = [obs for obs in game.obstacles if obs not in default_container_rects]
                
                game.containers = game.map_states[new_filename]['containers']
                for c in game.containers:
                    if c.rect in obstacle_container_rects and c.rect not in game.obstacles:
                        game.obstacles.append(c.rect)
                        
            if 'vehicles' in game.map_states[new_filename] and hasattr(game.map_manager, 'vehicles'):
                default_veh_rects = [v.rect for v in game.map_manager.vehicles]
                game.obstacles = [obs for obs in game.obstacles if obs not in default_veh_rects]
                
                game.map_manager.vehicles = game.map_states[new_filename]['vehicles']
                for v in game.map_manager.vehicles:
                    if v.rect not in game.obstacles:
                        game.obstacles.append(v.rect)
        else:
            game.items_on_ground = spawn_initial_items(game.obstacles, item_spawns)
            
            if hasattr(game, 'layer_zombies') and layer_index in game.layer_zombies and game.layer_zombies[layer_index]:
                game.zombies = list(game.layer_zombies[layer_index])
            else:
                game.zombies = spawn_initial_zombies(game.obstacles, zombie_spawns, game.items_on_ground)
                
            if hasattr(game, 'active_animals'):
                game.active_animals = []
            if hasattr(game, 'npcs'):
                game.npcs.empty()
            if hasattr(game, 'npc_spawn_points') and game.npc_spawn_points:
                
                for spawn_data in game.npc_spawn_points:
                    if len(spawn_data) == 3:
                        nx, ny, npc_type = spawn_data
                    else:
                        nx, ny = spawn_data
                        npc_type = 'NPC'
                        
                    is_static = (npc_type == 'SNPC')
                    
                    npc = NPC(nx, ny, game, is_static=is_static, layer=layer_index)
                    
                    if npc_type == 'NPC':
                        npc.is_friendly = False   
                        npc.is_static = False     
                    elif npc_type == 'SNPC':
                        npc.is_friendly = True    
                        npc.is_static = True      
                        
                    free_pos = find_free_tile(npc.rect, game.obstacles, max_radius=15, initial_pos=(nx, ny))
                    if free_pos:
                        npc.rect.topleft = free_pos
                        npc.x, npc.y = free_pos
                        game.npcs.add(npc)
        
        if hasattr(game, 'npcs'):
            for f_npc in followers:
                game.npcs.add(f_npc)
        
        if hasattr(game, 'active_animals'):
            game.active_animals.extend(chasing_animals)
            game.items_on_ground.extend(chasing_animals)

        if hasattr(game, 'player') and getattr(game.player, 'vehicle', None):
            veh = game.player.vehicle
            if veh not in game.containers:
                game.containers.append(veh)
            if hasattr(game.map_manager, 'vehicles') and veh not in game.map_manager.vehicles:
                game.map_manager.vehicles.append(veh)
            if veh.rect in game.obstacles:
                game.obstacles.remove(veh.rect)
    else:
        game.items_on_ground = spawn_initial_items(game.obstacles, item_spawns)
        
        if hasattr(game, 'layer_zombies') and layer_index in game.layer_zombies and game.layer_zombies[layer_index]:
            game.zombies = list(game.layer_zombies[layer_index])
        else:
            game.zombies = spawn_initial_zombies(game.obstacles, zombie_spawns, game.items_on_ground)

    game.layer_items[layer_index] = game.items_on_ground
    game.layer_zombies[layer_index] = game.zombies

    if hasattr(game, 'tiles_dirty'):
        game.tiles_dirty = True
    if hasattr(game, 'map_manager'):
        game.map_manager.clear_cache()
    
    return True

def check_for_layer_teleport(game):
    if game.player.layer_switch_cooldown > 0:
        return

    player = game.player
    try:
        tile_x = int(player.rect.centerx // TILE_SIZE)
        tile_y = int(player.rect.centery // TILE_SIZE)
    except (AttributeError, TypeError):
        return

    current_map_data = game.map_data
    if not current_map_data:
        return
    
    if not (0 <= tile_y < len(current_map_data) and 0 <= tile_x < len(current_map_data[0])):
        return
        
    tile_char = current_map_data[tile_y][tile_x]
    tile_def = game.tile_manager.definitions.get(tile_char)
    
    if tile_def and tile_def.get('is_stair'):
        target_layer = tile_def.get('target_layer')
        
        if target_layer and target_layer != game.current_layer_index:
            print(f"Auto-teleport detected: Moving to Layer {target_layer}")
            if set_active_layer(game, target_layer):
                game.player.layer_switch_cooldown = 60