# core/systems/load_manager.py

import os
import json
import re
import uuid
import pygame
from datetime import datetime
from core.data.config import *
import core.data.config
from core.entities.player.player import Player
from core.entities.zombie.zombie import Zombie
from core.entities.animal.animal import Animal
from core.entities.item.item import Item
from core.entities.npc.npc import NPC
from core.entities.vehicle.vehicle import Vehicle
from core.map.world_layers import load_all_map_layers, set_active_layer
from core.map.map_loader import parse_layered_map_layout
from core.map.spawn_manager import get_house_spawn_position, spawn_initial_zombies, manage_dynamic_npcs, spawn_l2_population, spawn_random_vehicles, spawn_animals
from core.map.procedural.generator import ProceduralGenerator
from core.map.world_time import WorldTime
from core.ui.assets import load_assets
from core.systems.quadtree import Quadtree

def load_map(game, map_filename):
    game.all_map_layers.clear()
    game.all_ground_layers.clear()
    game.all_spawn_layers.clear()
    game.layer_items.clear()
    game.layer_zombies.clear()
    game.map_manager.current_map_filename = map_filename
    
    # Pass the current map folder (save folder) to the loader
    game.all_map_layers, game.all_ground_layers, game.all_spawn_layers, game.all_roof_layers, game.all_light_layers = \
        load_all_map_layers(map_filename, base_path=game.map_manager.map_folder)

    if 1 not in game.all_map_layers:
        raise FileNotFoundError(f"Base map file {map_filename} (Layer 1) could not be loaded from {game.map_manager.map_folder}.")

    match = re.search(r'map_L(\d+)_', map_filename)
    layer_index = int(match.group(1)) if match else 1
    
    set_active_layer(game, layer_index, skip_cache_save=True)
    
    # [NEW] Fully parse the active chunk layer layout to extract physical barriers and containers
    base_layout = game.all_map_layers.get(layer_index)
    ground_layout = game.all_ground_layers.get(layer_index)
    spawn_layout = game.all_spawn_layers.get(layer_index)
    roof_layout = game.all_roof_layers.get(layer_index)
    light_layout = game.all_light_layers.get(layer_index)

    obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers, roofs, lights, npc_spawns = parse_layered_map_layout(
        base_layout, ground_layout, spawn_layout, roof_layout, light_layout, game.tile_manager
    )
    
    if base_layout:
        game.map_width_pixels = len(base_layout[0]) * TILE_SIZE
        game.map_height_pixels = len(base_layout) * TILE_SIZE

    game.obstacles = obstacles
    game.containers = containers
    game.renderable_tiles = renderable_tiles
    game.npc_spawn_points = npc_spawns
    game.current_zombie_spawns = zombie_spawns
    game.player_spawn = player_spawn

    # Extract map specific vehicles
    map_vehicles = [obj for obj in containers if isinstance(obj, Vehicle)]
    for v in map_vehicles:
        if v in containers:
            containers.remove(v)
        if v.rect in obstacles:
            obstacles.remove(v.rect)
    
    game.map_manager.vehicles = map_vehicles
    game.vehicles = map_vehicles

    # [CRITICAL] Ensure chunked logic evaluates to true!
    game.is_giant_map = False
    
    return None

def start_new_game(game, player_data, save_dir_name=None, spawn_entities=True):
    game.is_giant_map = False
    
    # 1. Clear Map & Layer Data
    game.all_map_layers = {}
    game.all_ground_layers = {}
    game.all_spawn_layers = {}
    game.all_roof_layers = {}
    game.all_light_layers = {}
    game.layer_spawn_triggers = {}
    game.triggered_spawns = set()
    
    # 2. Clear Entity & World State
    game.map_states = {}  
    game.spawn_point_grid = {}
    game.items_on_ground = []
    game.zombies = []
    game.obstacles = []
    game.containers = []
    game.renderable_tiles = []
    game.map_lights = []
    game.projectiles = []
    game.corpses = []
    game.splashes = []
    game.blood_stains = []
    game.npcs.empty()
    
    # 3. Clear Visual Caches
    if hasattr(game, '_tile_cache_surface'):
        game._tile_cache_surface = None
    game.tiles_dirty = True
    
    if hasattr(game, 'map_manager'):
        game.map_manager.map_files = {}
        game.map_manager.clear_cache() 

    if save_dir_name:
        save_name = save_dir_name
        regenerate_map = False
        should_initial_save = False
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_name = f"save_{timestamp}"
        regenerate_map = True
        should_initial_save = True
    game.current_save_folder_name = save_name
    
    save_path = os.path.join(get_writable_dir(), "game", "save", "game", save_name)
    map_path = os.path.join(save_path, "map")
    
    try:
        os.makedirs(map_path, exist_ok=True)
        game.logger.info(f"Created new save environment at: {map_path}")
    except OSError as e:
        game.logger.info(f"Error creating save directory: {e}")
        map_path = MAP_DIR 

    game.map_manager.map_folder = map_path

    if not save_dir_name:
        preset_name = game.player_setup_state.get('selected_config_preset', 'default')
        game.logger.info(f"Reloading game configuration from XML: {preset_name}.xml")
        core.data.config.load_settings(preset_name)

    if 'attributes' not in player_data:
        player_data['attributes'] = {} 

    gen_building_counts = game.player_setup_state.get('building_counts_config', None)
    gen_chunk_settings = game.player_setup_state.get('chunk_settings_config', None)
    
    generator = ProceduralGenerator(
        game, 
        output_folder=map_path,
        building_counts=gen_building_counts,
        chunk_settings=gen_chunk_settings
    )
    
    if save_dir_name:
            raw_seed = player_data.get('world_seed', "4-B1TR07")
    else:
            raw_seed = player_data.get('world_seed')
            if not raw_seed or raw_seed == "4-B1TR07":
                raw_seed = str(uuid.uuid4())
    
    world_seed = raw_seed
    game.world_seed = world_seed
    game.logger.info(f"Generating world with Seed Pattern: {world_seed}")
    
    start_map = generator.generate_world(seed_pattern=world_seed, regenerate=regenerate_map)
    game.map_manager.refresh_maps()

    if start_map:
        game.map_manager.current_map_filename = start_map
        game.logger.info(f"Starting map set to generated file: {start_map}")
    else:
        game.logger.info("Warning: Generator did not return a start map.")

    game.player_name = player_data.get('name', "Player")
    game.player = Player(player_data=player_data)
    game.zoom_level = core.data.config.START_ZOOM
    
    initial_loot = player_data.get('initial_loot', [])
    game.player.inventory = [Item.create_from_name(name) for name in initial_loot if Item.create_from_name(name)]

    game.zombies_killed = 0
    stat_pos = game.last_modal_positions.get('status', (65, 3))
    inv_pos = game.last_modal_positions.get('inventory', (1034, 256))
    nearby_pos = game.last_modal_positions.get('nearby', (1034, 494))
    msg_pos = game.last_modal_positions.get('messages', (3, 460))
    gear_pos = game.last_modal_positions.get('gear', (1034, 3))
    slots_pos = game.last_modal_positions.get('slots', (1034, 3))

    game.modals = [
        {
            'type': 'status', 
            'id': str(uuid.uuid4()), 
            'position': stat_pos,
            'rect': pygame.Rect(stat_pos, (STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0)
        },
        {
            'type': 'inventory', 
            'id': str(uuid.uuid4()), 
            'position': inv_pos,
            'rect': pygame.Rect(inv_pos, (INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'active_tab': 'Inventory'
        },
        {
            'type': 'gear', 
            'id': str(uuid.uuid4()), 
            'position': gear_pos,
            'rect': pygame.Rect(gear_pos, (GEAR_MODAL_WIDTH, GEAR_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0)
        },
        {
            'type': 'nearby', 
            'id': str(uuid.uuid4()), 
            'position': nearby_pos,
            'rect': pygame.Rect(nearby_pos, (NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'active_tab': 'Ground'
        },
        {
            'type': 'messages', 
            'id': str(uuid.uuid4()), 
            'position': msg_pos,
            'rect': pygame.Rect(msg_pos, (MESSAGES_MODAL_WIDTH, MESSAGES_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0)
        },
        {
            'type': 'slots', 
            'id': str(uuid.uuid4()), 
            'position': slots_pos,
            'rect': pygame.Rect(slots_pos, (SLOTS_MODAL_WIDTH, SLOTS_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0)
        }
    ]

    if getattr(core.data.config, 'UI_SHOW_TUTORIAL_DEFAULT', False):
        help_pos = game.last_modal_positions.get('help', (GAME_WIDTH / 2 - HELP_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - HELP_MODAL_HEIGHT / 2))
        game.modals.append({
            'type': 'help', 
            'id': str(uuid.uuid4()), 
            'position': help_pos,
            'rect': pygame.Rect(help_pos, (HELP_MODAL_WIDTH, HELP_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0)
        })
    
    game.map_states = {}
    
    # The load map handles everything now, bypass giant map logic
    load_map(game, game.map_manager.current_map_filename)
    
    if hasattr(game, 'map_width_pixels') and hasattr(game, 'map_height_pixels'):
        game.quadtree = Quadtree(pygame.Rect(0, 0, game.map_width_pixels, game.map_height_pixels))
    
    if spawn_entities:
        game.npc_spawn_points = []
        if game.current_layer_index in game.all_spawn_layers:
            spawn_layer = game.all_spawn_layers[game.current_layer_index]
            for y, row in enumerate(spawn_layer):
                for x, char in enumerate(row):
                    if char.strip() == 'NPC':
                        game.npc_spawn_points.append((x * TILE_SIZE, y * TILE_SIZE))
                    elif char.strip() == 'SNPC':
                        px, py = x * TILE_SIZE, y * TILE_SIZE
                        npc = NPC(px, py, game, is_static=True)
                        game.npcs.add(npc)

        if 1 in game.all_map_layers:
            game.logger.info("Initializing Layer 1 Population (Vehicles, Animals)...")
            spawn_random_vehicles(game, count=8)
            spawn_animals(game, target_layer=1)

        if 2 in game.all_map_layers:
            game.logger.info("Initializing Layer 2 Population (Zombies, Animals)...")
            spawn_l2_population(game, count=20, target_layer=2)
            spawn_animals(game, target_layer=2)

    # ---------------------------------------------------------
    # [NEW] Determine Player Spawn Position
    # ---------------------------------------------------------
    
    # Force a quick chunk update so that `game.roof_data` and map definitions 
    # are populated for our spawn scan to read
    if hasattr(game, 'map_manager') and hasattr(game.map_manager, 'update_chunks'):
        center_x = getattr(game, 'map_width_pixels', 1000) // 2
        center_y = getattr(game, 'map_height_pixels', 1000) // 2
        game.map_manager.update_chunks((center_x, center_y))

    house_spawn = get_house_spawn_position(game)

    if house_spawn:
        game.logger.info(f"House spawn point found at {house_spawn}. Setting player position.")
        game.player.x, game.player.y = house_spawn
        game.player.rect.topleft = house_spawn
    elif game.player_spawn:
        game.logger.info(f"Player spawn point found at {game.player_spawn}. Setting player position.")
        game.player.x, game.player.y = game.player_spawn
        game.player.rect.topleft = game.player_spawn
    else:
        game.logger.info("CRITICAL WARNING: No player spawn ('P') found in starting chunk!")
        game.player.x, game.player.y = (10 * TILE_SIZE, 10 * TILE_SIZE)
        game.player.rect.topleft = (10 * TILE_SIZE, 10 * TILE_SIZE)


    if spawn_entities:
        nearby_spawns = []
        GRID_SIZE_SPAWNS = getattr(game, 'SPAWN_GRID_SIZE', 512)
        p_grid_x = int(game.player.x // GRID_SIZE_SPAWNS)
        p_grid_y = int(game.player.y // GRID_SIZE_SPAWNS)
        
        for i in range(-2, 3): 
            for j in range(-2, 3):
                    cell = (p_grid_x + i, p_grid_y + j)
                    if cell in game.spawn_point_grid:
                        nearby_spawns.extend(game.spawn_point_grid[cell])
                        
        if nearby_spawns:
                if game.current_layer_index not in game.layer_spawn_triggers:
                    game.layer_spawn_triggers[game.current_layer_index] = set()
                
                for pos in nearby_spawns:
                    game.layer_spawn_triggers[game.current_layer_index].add(pos)

                initial_zombies = spawn_initial_zombies(
                game.obstacles, 
                nearby_spawns, 
                game.items_on_ground + [game.player],
                limit=1000, 
                spawns_per_marker=core.data.config.ZOMBIES_PER_SPAWN,
                map_width_px=game.map_width_pixels,
                map_height_px=game.map_height_pixels,
                player=game.player,
                obstacle_grid=getattr(game, 'cached_obstacle_grid', None),
                game=game
                )
                game.zombies.extend(initial_zombies)
                game.layer_zombies[game.current_layer_index] = game.zombies[:]
                game.logger.info(f"Initial Start Chunk Population: Spawned {len(initial_zombies)} zombies around player.")

        manage_dynamic_npcs(game)

    game.world_time = WorldTime(game)
    game.game_start_time = pygame.time.get_ticks()

    if should_initial_save:
        from core.systems.save_manager import save_game
        if game.current_save_folder_name is None:
                game.current_save_folder_name = save_name
        save_game(game)

def load_game(game, save_folder_name):
    save_path = os.path.join(get_writable_dir(), "game", "save", "game", save_folder_name)
    map_path = os.path.join(save_path, "map")
    
    game.logger.info(f"Loading game from {save_path}...")

    try:
        with open(os.path.join(save_path, "host.rot"), "r") as f:
            player_data = json.load(f)

        start_new_game(game, player_data, save_dir_name=save_folder_name, spawn_entities=False)
        
        game.zombies_killed = player_data.get('zombies_killed', 0)

        target_map = player_data.get('map_filename')
        if target_map and target_map != game.map_manager.current_map_filename:
            game.logger.info(f"Switching to saved map: {target_map}")
            load_map(game, target_map)
        
        game.map_manager.map_folder = map_path
        game.map_manager.refresh_maps()

        prog_data = player_data['progression']
        if hasattr(game.player.progression, 'attributes'):
            for key, value in prog_data.items():
                if key in game.player.progression.attributes:
                        game.player.progression.attributes[key] = value


        game.player.x = player_data['x']
        game.player.y = player_data['y']
        game.player.rect.topleft = (game.player.x, game.player.y)
        
        game.player.inventory = []
        for item_data in player_data['inventory']:
            if isinstance(item_data, dict):
                item = Item.from_dict(item_data)
            else:
                item = Item.create_from_name(item_data)
            if item: game.player.inventory.append(item)

        game.player.belt = []
        for item_data in player_data.get('belt', [None]*5):
            if item_data:
                if isinstance(item_data, dict):
                    game.player.belt.append(Item.from_dict(item_data))
                else:
                    game.player.belt.append(Item.create_from_name(item_data))
            else:
                game.player.belt.append(None)
        
        game.player.clothes = {}
        for slot, item_data in player_data.get('clothes', {}).items():
            if item_data:
                if isinstance(item_data, dict):
                    game.player.clothes[slot] = Item.from_dict(item_data)
                else:
                    game.player.clothes[slot] = Item.create_from_name(item_data)
            else:
                game.player.clothes[slot] = None
        
        game.player.quests = player_data.get('quests', [])
        game.player.completed_quests = player_data.get('completed_quests', [])
        # If your game code strictly requires dialog_history to be a set, use set(player_data.get('dialog_history', [])) here instead. 
        # But lists work fine natively with `in` checks.
        game.player.dialog_history = player_data.get('dialog_history', [])
        game.player.special_dialogs = player_data.get('special_dialogs', [])
        
        with open(os.path.join(save_path, "world.rot"), "r") as f:
            world_data = json.load(f)
        
        time_data = world_data.get('time', {})
        game.world_time.game_time_ms = time_data.get('game_time_ms', 0)
        game.world_time.day_count = time_data.get('day_count', 0)
        
        saved_containers = world_data.get('containers', [])
        saved_container_map = {f"{c['x']}_{c['y']}": c['inventory'] for c in saved_containers}

        for c in game.containers:
            if hasattr(c, 'rect'):
                key = f"{c.rect.x}_{c.rect.y}"
                if key in saved_container_map:
                    c.inventory = [] 
                    for i_data in saved_container_map[key]:
                        if isinstance(i_data, dict):
                            item = Item.from_dict(i_data)
                        else:
                            item = Item.create_from_name(i_data)
                        if item: c.inventory.append(item)

        raw_layer_triggers = world_data.get('layer_spawn_triggers', {})
        game.layer_spawn_triggers = {}
        for layer_str, coords_list in raw_layer_triggers.items():
            try:
                layer_int = int(layer_str)
                game.layer_spawn_triggers[layer_int] = set(tuple(c) for c in coords_list)
            except Exception as e:
                game.logger.info(f"Error restoring triggers for layer {layer_str}: {e}")
        
        game.items_on_ground = []
        saved_items = world_data.get('items', [])
        game.logger.info(f"Found {len(saved_items)} items to load from save file.")

        for i_data in saved_items:
            try:
                item = None
                data = i_data.get('data', {})
                
                if data.get('is_corpse') or (isinstance(data.get('name'), str) and data['name'].startswith('Corpse')):
                     from core.entities.zombie.corpse import Corpse
                     
                     name = data.get('name', 'Dead corpse')
                     image_path = data.get('image_path') 
                     
                     item = Corpse(name=name, image_path=image_path)
                     
                     if 'inventory' in data and data['inventory']:
                         item.inventory = [Item.from_dict(x) for x in data['inventory'] if x]
                     
                     item.x = int(i_data.get('x', 0))
                     item.y = int(i_data.get('y', 0))
                     item.rect.topleft = (item.x, item.y)
                     
                     game.items_on_ground.append(item)
                     continue 

                if 'data' in i_data:
                    if isinstance(i_data['data'], dict):
                        item = Item.from_dict(i_data['data'])
                    else:
                        item = Item.create_from_name(i_data['data'])
                else:
                    item = Item.create_from_name(i_data['name'])
                    
                if item:
                    item.x = int(i_data.get('x', 0))
                    item.y = int(i_data.get('y', 0))
                    item.rect.topleft = (item.x, item.y)
                    game.items_on_ground.append(item)
                else:
                    game.logger.info(f"Warning: Failed to recreate item: {i_data}")
            except Exception as e:
                game.logger.info(f"Error loading an item on ground: {e}")
        
        game.zombies = [] 
        zombies_path = os.path.join(save_path, "zombies.rot")
        
        if os.path.exists(zombies_path):
             game.logger.info("Loading zombies from zombies.rot...")
             with open(zombies_path, "r") as f:
                 zombie_list = json.load(f)
             
             for z_data in zombie_list:
                template = {
                    'name': z_data.get('name', 'Zombie'),
                    'sex': z_data.get('sex', 'Male'),
                    'health': z_data.get('max_health', 10), 
                    'speed': z_data.get('speed', 1.0),
                    'vaccine': str(z_data.get('vaccine', False)),
                    'min_xp': z_data.get('xp_value', 1), 
                    'max_xp': z_data.get('xp_value', 5),
                    'min_attack': z_data.get('min_attack', 1),
                    'max_attack': z_data.get('max_attack', 3),
                    'min_infection': z_data.get('min_infection', 0),
                    'max_infection': z_data.get('max_infection', 1),
                    'loot': z_data.get('loot_table', []),
                    'clothes': z_data.get('clothes', {}), 
                    'sprites': z_data.get('sprites', {})
                }
                
                z = Zombie(z_data['x'], z_data['y'], template)
                
                layer = z_data.get('layer', 1)
                z.layer = layer

                z.health = z_data.get('health', z.max_health)
                z.max_health = z_data.get('max_health', z.health)
                if 'id' in z_data and z_data['id']:
                    z.id = z_data['id']
                
                if 'inventory' in z_data:
                    z.inventory = [] 
                    for i_data in z_data['inventory']:
                        if isinstance(i_data, dict):
                            item = Item.from_dict(i_data)
                        else:
                            item = Item.create_from_name(i_data)
                        if item:
                            z.inventory.append(item)
                
                clothes_data = z_data.get('clothes', {})
                z.clothes = {}
                for slot, c_data in clothes_data.items():
                    if c_data:
                        if isinstance(c_data, dict):
                            z.clothes[slot] = Item.from_dict(c_data)
                        else:
                            z.clothes[slot] = Item.create_from_name(c_data)
                    else:
                        z.clothes[slot] = None

                if layer == game.current_layer_index:
                    game.zombies.append(z)
                else:
                    if not hasattr(game, 'layer_zombies'): game.layer_zombies = {}
                    if layer not in game.layer_zombies: game.layer_zombies[layer] = []
                    game.layer_zombies[layer].append(z)

        else:
             game.logger.info("zombies.rot not found. Attempting to load zombies from world.rot (legacy)...")
             for z_data in world_data.get('zombies', []):
                z = Zombie.create_random(z_data['x'], z_data['y']) 
                if z:
                    z.health = z_data['health']
                    game.zombies.append(z)

        animal_path = os.path.join(save_path, "animal.rot")
        if os.path.exists(animal_path):
             game.logger.info("Loading animals from animal.rot...")
             with open(animal_path, "r") as f:
                 animal_list = json.load(f)
             
             for a_data in animal_list:
                animal_type = a_data.get('name', 'Rat')
                layer = a_data.get('layer', 1)
                a = Animal(a_data['x'], a_data['y'], animal_type, game=game, layer=layer)
                
                a.health = a_data.get('health', a.max_health)
                a.max_health = a_data.get('max_health', a.health)
                
                if 'id' in a_data and a_data['id']:
                    a.id = a_data['id']
                
                if 'inventory' in a_data:
                    a.inventory = []
                    for i_data in a_data['inventory']:
                         if isinstance(i_data, dict):
                            item = Item.from_dict(i_data)
                         else:
                            item = Item.create_from_name(i_data)
                         if item: a.inventory.append(item)

                if layer == game.current_layer_index:
                    game.items_on_ground.append(a)
                else:
                    if not hasattr(game, 'layer_zombies'): game.layer_zombies = {}
                    if layer not in game.layer_zombies: game.layer_zombies[layer] = []
                    game.layer_zombies[layer].append(a)

        
        if 'modal_positions' in world_data:
            saved_positions = world_data['modal_positions']
            game.last_modal_positions.update(saved_positions)
            
            for modal in game.modals:
                m_type = modal['type']
                if m_type in saved_positions:
                    pos = saved_positions[m_type]
                    if isinstance(pos, (list, tuple)) and len(pos) == 2:
                        modal['position'] = (int(pos[0]), int(pos[1]))
                        modal['rect'].topleft = modal['position']

        if os.path.exists(os.path.join(save_path, "npc.rot")):
                with open(os.path.join(save_path, "npc.rot"), "r") as f:
                    npc_list = json.load(f)
                game.npcs.empty()
                for n_data in npc_list:
                    is_static = n_data.get('is_static', False)
                    layer = n_data.get('layer', 1)
                    npc = NPC(n_data['x'], n_data['y'], game, is_static=is_static, layer=layer)
                    npc.name = n_data.get('name', 'Survivor')
                    npc.health = n_data.get('health', 100)
                    npc.max_health = n_data.get('max_health', 100)
                    
                    npc.is_following = n_data.get('is_following', False)
                    npc.is_friendly = n_data.get('is_friendly', True)
                    
                    if 'id' in n_data and n_data['id']:
                        npc.id = n_data['id']
                    
                    if 'dialog_flags' in n_data:
                        npc.dialog_flags = set(n_data['dialog_flags'])

                    if npc.is_following:
                        npc.state = 'following'
                    
                    npc.inventory = []
                    for i_data in n_data.get('inventory', []):
                        if isinstance(i_data, dict):
                            item = Item.from_dict(i_data)
                        else:
                            item = Item.create_from_name(i_data)
                        if item: npc.inventory.append(item)
                    
                    w_data = n_data.get('equipped_weapon')
                    if w_data:
                        if isinstance(w_data, dict):
                            npc.equipped_weapon = Item.from_dict(w_data)
                        else:
                            npc.equipped_weapon = Item.create_from_name(w_data)

                    clothes_data = n_data.get('clothes', {})
                    npc.clothes = {}
                    for slot, c_data in clothes_data.items():
                        if c_data:
                            if isinstance(c_data, dict):
                                npc.clothes[slot] = Item.from_dict(c_data)
                            else:
                                npc.clothes[slot] = Item.create_from_name(c_data)
                    
                    if 'loot_table' in n_data:
                        npc.loot_table = n_data['loot_table']
                            
                    if layer == game.current_layer_index or npc.is_following:
                        game.npcs.add(npc)
                    else:
                        if not hasattr(game, 'layer_npcs'): game.layer_npcs = {}
                        if layer not in game.layer_npcs: game.layer_npcs[layer] = []
                        game.layer_npcs[layer].append(npc)
        
        if os.path.exists(os.path.join(save_path, "vehicles.rot")):
            with open(os.path.join(save_path, "vehicles.rot"), "r") as f:
                v_list = json.load(f)
                
            # Ensure proper initialization of vehicles lists
            if not hasattr(game.map_manager, 'vehicles'):
                game.map_manager.vehicles = []
            else:
                game.map_manager.vehicles.clear()
                
            if not hasattr(game, 'vehicles'):
                game.vehicles = []
            else:
                game.vehicles.clear()

            game.containers = [c for c in game.containers if not isinstance(c, Vehicle)]
            
            for v_data in v_list:
                vehicle_def = game.tile_manager.definitions.get(v_data.get('name').lower().replace(" ", "_"), None)
                v_img = vehicle_def['image'] if vehicle_def else None 
                v_w, v_h = TILE_SIZE, TILE_SIZE
                    
                vehicle = Vehicle(
                    name=v_data.get('name'),
                    x=v_data.get('x'),
                    y=v_data.get('y'),
                    width=v_w,
                    height=v_h,
                    image=v_img, 
                    stats={}, 
                    capacity=20,
                    facing=v_data.get('facing', 'right')
                )
                
                if hasattr(vehicle, 'inventory'):
                    vehicle.inventory = []
                    for i_data in v_data.get('inventory', []):
                        if isinstance(i_data, dict):
                            item = Item.from_dict(i_data)
                        else:
                            item = Item.create_from_name(i_data)
                        if item: vehicle.inventory.append(item)
                
                if 'equipment' in v_data:
                    loaded_equipment = v_data['equipment']
                    for slot, item_data in loaded_equipment.items():
                        if item_data:
                            if isinstance(item_data, dict):
                                item = Item.from_dict(item_data)
                            else:
                                item = Item.create_from_name(item_data)
                                
                            if item:
                                vehicle.equipment[slot] = item
                        else:
                            vehicle.equipment[slot] = None
                    
                    vehicle.update_stats_from_equipment()
                    
                if 'lights' in v_data:
                    vehicle.lights = v_data['lights']

                game.map_manager.vehicles.append(vehicle)
                game.vehicles.append(vehicle)
                game.containers.append(vehicle)
                game.obstacles.append(vehicle.rect)

        #game.game_state = 'PLAYING'
        game.logger.info("Game loaded successfully!")

    except Exception as e:
        game.logger.info(f"Error loading game: {e}")
        import traceback
        traceback.print_exc()
        game.game_state = 'MENU'