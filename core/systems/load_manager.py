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
from core.entities.item.item import Item
from core.entities.npc.npc import NPC
from core.entities.vehicle.vehicle import Vehicle
from core.map.world_layers import load_all_map_layers, set_active_layer, load_giant_map
from core.map.map_loader import parse_layered_map_layout
from core.map.spawn_manager import spawn_initial_zombies, manage_dynamic_npcs, spawn_l2_population
from core.map.procedural.generator import ProceduralGenerator
from core.map.world_time import WorldTime
from core.ui.assets import load_assets

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
    
    set_active_layer(game, layer_index)
    return None

def start_new_game(game, player_data, save_dir_name=None, spawn_entities=True):
    """
    Initializes a game session.
    :param spawn_entities: If False, skips spawning initial zombies/NPCs (used when loading a save).
    """
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
    
    save_path = os.path.join("game", "save", "game", save_name)
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

    starter_items = ["Lantern off", "Matches", "Survivor Kit", "Mobile off", "Powerbank"]
    for name in starter_items:
            try:
                item = Item.create_from_name(name)
                if item and len(game.player.inventory) < game.player.get_total_inventory_slots():
                    if not any(i.name == name for i in game.player.inventory):
                        game.player.inventory.append(item)
            except: pass

    game.zombies_killed = 0
    stat_pos = game.last_modal_positions.get('status', (50, 50))
    inv_pos = game.last_modal_positions.get('inventory', (400, 50))
    nearby_pos = game.last_modal_positions.get('nearby', (1050, 360))
    gear_pos = game.last_modal_positions.get('gear', (830, 10))

    game.modals = [
        {
            'type': 'status', 
            'id': str(uuid.uuid4()), 
            'position': stat_pos,
            'rect': pygame.Rect(stat_pos, (STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'minimized': False
        },
        {
            'type': 'inventory', 
            'id': str(uuid.uuid4()), 
            'position': inv_pos,
            'rect': pygame.Rect(inv_pos, (INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'minimized': False,
            'active_tab': 'Inventory'
        },
        {
            'type': 'nearby', 
            'id': str(uuid.uuid4()), 
            'position': nearby_pos,
            'rect': pygame.Rect(nearby_pos, (NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'minimized': False,
            'active_tab': 'Ground'
        },
        {
            'type': 'gear', 
            'id': str(uuid.uuid4()), 
            'position': gear_pos,
            'rect': pygame.Rect(gear_pos, (GEAR_MODAL_WIDTH, GEAR_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'minimized': False
        }
    ]
    game.map_states = {}
    
    load_map(game, game.map_manager.current_map_filename)
    load_giant_map(game)
    
    # --- Entity Spawning Logic ---
    # Only execute spawning if spawn_entities is True.
    if spawn_entities:
        game.npc_spawn_points = []
        if game.current_layer_index in game.all_spawn_layers:
            spawn_layer = game.all_spawn_layers[game.current_layer_index]
            for y, row in enumerate(spawn_layer):
                for x, char in enumerate(row):
                    if char.strip() == 'NPC':
                        game.npc_spawn_points.append((x * TILE_SIZE, y * TILE_SIZE))
                    elif char.strip() == 'S':
                        px, py = x * TILE_SIZE, y * TILE_SIZE
                        npc = NPC(px, py, game, is_static=True)
                        game.npcs.add(npc)

        if game.current_layer_index == 2:
            game.logger.info("Initializing L2 (Cave) Population...")
            spawn_l2_population(game, count=20)
    else:
        # Even if not spawning, we might need to know potential points for dynamic logic later
        pass

    if game.player_spawn:
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
    save_path = os.path.join("game", "save", "game", save_folder_name)
    map_path = os.path.join(save_path, "map")
    
    game.logger.info(f"Loading game from {save_path}...")

    try:
        with open(os.path.join(save_path, "host.rot"), "r") as f:
            player_data = json.load(f)

        # Skip spawning entities because we will load them from file
        start_new_game(game, player_data, save_dir_name=save_folder_name, spawn_entities=False)
        
        game.zombies_killed = player_data.get('zombies_killed', 0)

        target_map = player_data.get('map_filename')
        if target_map and target_map != game.map_manager.current_map_filename:
            game.logger.info(f"Switching to saved map: {target_map}")
            load_map(game, target_map)
            load_giant_map(game)
        
        game.map_manager.map_folder = map_path
        game.map_manager.refresh_maps()

        layer_idx = game.current_layer_index
        base_layout = game.all_map_layers.get(layer_idx)
        ground_layout = game.all_ground_layers.get(layer_idx)
        spawn_layout = game.all_spawn_layers.get(layer_idx)
        roof_layout = game.all_roof_layers.get(layer_idx)
        light_layout = game.all_light_layers.get(layer_idx)

        obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers, roofs, lights, npc_spawns = parse_layered_map_layout(
            base_layout, ground_layout, spawn_layout, roof_layout, light_layout, game.tile_manager
        )

        map_vehicles = [obj for obj in containers if isinstance(obj, Vehicle)]
        for v in map_vehicles:
            if v in containers:
                containers.remove(v)
            if v.rect in obstacles:
                obstacles.remove(v.rect)
        
        game.obstacles = obstacles
        game.containers = containers
        game.renderable_tiles = renderable_tiles
        game.npc_spawn_points = npc_spawns

        prog_data = player_data['progression']
        if hasattr(game.player.progression, 'attributes'):
            for key, value in prog_data.items():
                if key in game.player.progression.attributes:
                        game.player.progression.attributes[key] = value
        if 'body_parts' in player_data:
            game.player.body_parts = player_data['body_parts']
            if hasattr(game.player, 'update_global_health'):
                game.player.update_global_health()
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

        if "backpack" in player_data:
                bp_data = player_data["backpack"]
                if isinstance(bp_data, dict):
                    game.player.backpack = Item.from_dict(bp_data)
                else:
                    game.player.backpack = Item.create_from_name(bp_data["name"])
                    if game.player.backpack:
                        game.player.backpack.inventory = [Item.create_from_name(name) for name in bp_data.get("inventory", [])]

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
        
        # --- ZOMBIES LOADING (FROM zombies.rot) ---
        game.zombies = [] 
        zombies_path = os.path.join(save_path, "zombies.rot")
        
        if os.path.exists(zombies_path):
             game.logger.info("Loading zombies from zombies.rot...")
             with open(zombies_path, "r") as f:
                 zombie_list = json.load(f)
             
             for z_data in zombie_list:
                # Reconstruct via Template to support Zombie(x, y, template) structure
                # We use the saved data as a 'template' to ensure the exact entity is recreated
                template = {
                    'name': z_data.get('name', 'Zombie'),
                    'sex': z_data.get('sex', 'Male'),
                    'profession': z_data.get('profession', 'Civilian'),
                    'health': z_data.get('max_health', 10), 
                    'speed': z_data.get('speed', 1.0),
                    'vaccine': str(z_data.get('vaccine', False)),
                    'loot': z_data.get('loot_table', []),
                    'clothes': z_data.get('clothes', {}), 
                    'sprites': {} 
                }
                
                z = Zombie(z_data['x'], z_data['y'], template)
                
                # Restore runtime stats
                z.health = z_data.get('health', z.max_health)
                z.max_health = z_data.get('max_health', z.health)
                if 'id' in z_data and z_data['id']:
                    z.id = z_data['id']
                
                # Restore Inventory
                if 'inventory' in z_data:
                    z.inventory = [] # Clear default items (like fresh ID card)
                    for i_data in z_data['inventory']:
                        if isinstance(i_data, dict):
                            item = Item.from_dict(i_data)
                        else:
                            item = Item.create_from_name(i_data)
                        if item:
                            z.inventory.append(item)
                
                game.zombies.append(z)

        else:
             game.logger.info("zombies.rot not found. Attempting to load zombies from world.rot (legacy)...")
             for z_data in world_data.get('zombies', []):
                z = Zombie.create_random(z_data['x'], z_data['y']) 
                if z:
                    z.health = z_data['health']
                    game.zombies.append(z)
        
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

        # --- NPC LOADING (FROM npc.rot) ---
        if os.path.exists(os.path.join(save_path, "npc.rot")):
                with open(os.path.join(save_path, "npc.rot"), "r") as f:
                    npc_list = json.load(f)
                game.npcs.empty()
                for n_data in npc_list:
                    is_static = n_data.get('is_static', False)
                    npc = NPC(n_data['x'], n_data['y'], game, is_static=is_static)
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
                    
                    # Restore Inventory
                    npc.inventory = []
                    for i_data in n_data.get('inventory', []):
                        if isinstance(i_data, dict):
                            item = Item.from_dict(i_data)
                        else:
                            item = Item.create_from_name(i_data)
                        if item: npc.inventory.append(item)
                    
                    # Restore Weapon
                    w_data = n_data.get('equipped_weapon')
                    if w_data:
                        if isinstance(w_data, dict):
                            npc.equipped_weapon = Item.from_dict(w_data)
                        else:
                            npc.equipped_weapon = Item.create_from_name(w_data)

                    # Restore Clothes
                    clothes_data = n_data.get('clothes', {})
                    npc.clothes = {}
                    for slot, c_data in clothes_data.items():
                        if c_data:
                            if isinstance(c_data, dict):
                                npc.clothes[slot] = Item.from_dict(c_data)
                            else:
                                npc.clothes[slot] = Item.create_from_name(c_data)
                    
                    # Restore Loot Table
                    if 'loot_table' in n_data:
                        npc.loot_table = n_data['loot_table']
                            
                    game.npcs.add(npc)
        
        if os.path.exists(os.path.join(save_path, "vehicles.rot")):
            with open(os.path.join(save_path, "vehicles.rot"), "r") as f:
                v_list = json.load(f)
                
            game.map_manager.vehicles = [] 
            
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
                    capacity=20
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
                game.containers.append(vehicle)
                game.obstacles.append(vehicle.rect)

        game.game_state = 'PLAYING'
        game.logger.info("Game loaded successfully!")

    except Exception as e:
        game.logger.info(f"Error loading game: {e}")
        import traceback
        traceback.print_exc()
        game.game_state = 'MENU'