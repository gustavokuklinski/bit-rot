import pygame
import random
import math
import core.data.config
from core.data.config import *
from core.entities.item.item import Item
from core.entities.zombie.zombie import Zombie
from core.entities.npc.npc import NPC
from core.entities.vehicle.vehicle_loader import VehicleLoader
from core.entities.vehicle.vehicle import Vehicle

# Import Animal classes
from core.entities.animal.animal import Animal
from core.entities.animal.animal_loader import AnimalLoader

# --- Configuration for Dynamic Spawning ---
MAX_ACTIVE_NPCS = 2
NPC_SPAWN_RADIUS = 70 * TILE_SIZE
NPC_DESPAWN_RADIUS = 80 * TILE_SIZE
NPC_MIN_SPAWN_DIST = 50 * TILE_SIZE

def spawn_initial_items(obstacles, item_spawns):
    items_on_ground = []
    occupied_tiles = set()
    for ob in obstacles:
        occupied_tiles.add((ob.x // TILE_SIZE, ob.y // TILE_SIZE))

    for spawn_data in item_spawns:
        # Check if it is a specific item tuple (x, y, name)
        if len(spawn_data) == 3:
            x, y, name = spawn_data
            item = Item.create_from_name(name)
            if item:
                item.rect.topleft = (x, y)
                item.x = x
                item.y = y
                item_tile = (x // TILE_SIZE, y // TILE_SIZE)
                items_on_ground.append(item)
                occupied_tiles.add(item_tile)
        else:
            # Random Item Spawn (x, y)
            pos = spawn_data
            item = Item.generate_random()
            if item:
                item.rect.topleft = pos
                item.x = pos[0]
                item.y = pos[1]
                item_tile = (item.rect.x // TILE_SIZE, item.rect.y // TILE_SIZE)
                if item_tile not in occupied_tiles:
                    items_on_ground.append(item)
                    occupied_tiles.add(item_tile)
                    
    return items_on_ground

def _find_spawn_spot_near(initial_pos_px, occupied_tiles, map_width_px, map_height_px, max_radius=5):
    start_x_tile = initial_pos_px[0] // TILE_SIZE
    start_y_tile = initial_pos_px[1] // TILE_SIZE

    if map_width_px is None: map_width_px = 99999
    if map_height_px is None: map_height_px = 99999
    
    max_x_tile = map_width_px // TILE_SIZE
    max_y_tile = map_height_px // TILE_SIZE

    tile_coord = (start_x_tile, start_y_tile)
    if tile_coord not in occupied_tiles:
        if 0 <= tile_coord[0] < max_x_tile and 0 <= tile_coord[1] < max_y_tile:
            occupied_tiles.add(tile_coord)
            return (start_x_tile * TILE_SIZE, start_y_tile * TILE_SIZE)

    for radius in range(1, max_radius + 1):
        for i in range(-radius, radius + 1):
            for j in range(-radius, radius + 1):
                if abs(i) < radius and abs(j) < radius:
                    continue
                check_x_tile = start_x_tile + i
                check_y_tile = start_y_tile + j
                if not (0 <= check_x_tile < max_x_tile and 0 <= check_y_tile < max_y_tile):
                    continue
                tile_coord = (check_x_tile, check_y_tile)
                if tile_coord not in occupied_tiles:
                    occupied_tiles.add(tile_coord)
                    return (check_x_tile * TILE_SIZE, check_y_tile * TILE_SIZE)
    return None

def manage_dynamic_npcs(game):
    if not game.player: return
    player_x, player_y = game.player.rect.centerx, game.player.rect.centery
    
    # Initialize off-layer storage if needed
    if not hasattr(game, 'layer_npcs'):
        game.layer_npcs = {}

    # [FIX] Clean up NPCs from incorrect layers and move them to storage
    for npc in list(game.npcs):
        # 1. Default to layer 1 if attribute is missing
        if not hasattr(npc, 'layer'):
            npc.layer = 1
        
        if npc.layer != game.current_layer_index:
            # If it's a follower, bring it to the current layer
            if hasattr(npc, 'is_following') and npc.is_following:
                npc.layer = game.current_layer_index
            else:
                # Store NPC in layer_npcs before removing
                if npc.layer not in game.layer_npcs:
                    game.layer_npcs[npc.layer] = []
                
                # Check if already stored to avoid duplicates
                if npc not in game.layer_npcs[npc.layer]:
                    game.layer_npcs[npc.layer].append(npc)
                
                game.npcs.remove(npc)
                continue

        # 2. Distance Despawn Logic (skip followers)
        if hasattr(npc, 'is_following') and npc.is_following: continue
        
        dist_sq = (npc.rect.centerx - player_x)**2 + (npc.rect.centery - player_y)**2
        if dist_sq > NPC_DESPAWN_RADIUS**2:
            game.npcs.remove(npc)

    # [FIX] Restore NPCs for the current layer
    current_layer = game.current_layer_index
    if current_layer in game.layer_npcs:
        stored_npcs = game.layer_npcs[current_layer]
        # Move all stored NPCs back to game.npcs
        for npc in stored_npcs:
            if npc not in game.npcs:
                game.npcs.add(npc)
        # Clear storage for this layer so they are now "active"
        game.layer_npcs[current_layer] = []

    current_count = len(game.npcs)
    if current_count >= MAX_ACTIVE_NPCS: return

    spawn_points = getattr(game, 'npc_spawn_points', [])
    spawned_this_frame = 0
    limit_per_frame = 1 
    spawn_rad_sq = NPC_SPAWN_RADIUS**2
    min_spawn_rad_sq = NPC_MIN_SPAWN_DIST**2
    
    p_rect = game.player.rect
    search_rect = pygame.Rect(
        p_rect.centerx - NPC_SPAWN_RADIUS, 
        p_rect.centery - NPC_SPAWN_RADIUS, 
        NPC_SPAWN_RADIUS * 2, 
        NPC_SPAWN_RADIUS * 2
    )
    valid_candidates = [pos for pos in spawn_points if search_rect.collidepoint(pos)]
    if not valid_candidates: return

    random.shuffle(valid_candidates)

    for pos in valid_candidates:
        if current_count >= MAX_ACTIVE_NPCS: break
        if spawned_this_frame >= limit_per_frame: break

        px, py = pos
        dist_sq = (px - player_x)**2 + (py - player_y)**2

        if min_spawn_rad_sq < dist_sq < spawn_rad_sq:
            too_crowded = False
            for npc in game.npcs:
                if (npc.rect.x - px)**2 + (npc.rect.y - py)**2 < (TILE_SIZE * 2)**2:
                    too_crowded = True
                    break
            
            if not too_crowded:
                if game.current_layer_index == 2:
                    tx, ty = int(px // TILE_SIZE), int(py // TILE_SIZE)
                    tile = game.map_manager.get_tile_at(tx, ty)
                    if not tile: continue
                    t_name = tile.get('name', '').lower()
                    is_building = 'floor' in t_name or 'wood' in t_name or 'tile' in t_name or 'carpet' in t_name
                    if not is_building:
                        continue

                # Create NPC with current layer
                npc = NPC(px, py, game, layer=game.current_layer_index)
                
                # [FIX] Ensure NPCs spawned on L2 are friendly
                if game.current_layer_index == 2:
                    npc.is_friendly = True

                game.npcs.add(npc)
                current_count += 1
                spawned_this_frame += 1

def spawn_static_npcs(game, building_tiles):
    for (tx, ty) in building_tiles:
        if random.random() < NPC_STATIC_SPAWN:
            px, py = tx * TILE_SIZE, ty * TILE_SIZE
            if not any(ob.collidepoint(px, py) for ob in game.obstacles):
                npc = NPC(px, py, game, is_static=True, layer=game.current_layer_index)
                game.npcs.add(npc)

def spawn_l2_population(game, count=10, target_layer=None):
    """
    Populates L2 (or target_layer) with standard Zombies and NPCs.
    Can populate a non-active layer if target_layer is provided.
    """
    if target_layer is None:
        target_layer = game.current_layer_index

    # Use data from the specific layer
    if target_layer not in game.all_ground_layers:
        return

    map_data = game.all_ground_layers[target_layer]
    map_h = len(map_data)
    map_w = len(map_data[0]) if map_h > 0 else 0
    
    # Select storage list
    target_zombies = []
    is_active_layer = (target_layer == game.current_layer_index)
    
    if is_active_layer:
        # We append directly to game.zombies later
        pass 
    else:
        if not hasattr(game, 'layer_zombies'): game.layer_zombies = {}
        if target_layer not in game.layer_zombies: game.layer_zombies[target_layer] = []
        target_zombies = game.layer_zombies[target_layer]

    npc_count = 0
    zombie_count = 0
    desired_npcs = 3
    desired_zombies = count
    
    attempts = 0
    max_attempts = 1000
    
    defs = game.tile_manager.definitions

    # [FIX] Respect Global Zombie Configuration
    # If zombies are disabled in config OR per_chunk limit is 0, force desired_zombies to 0
    if (core.data.config.MAX_ZOMBIES_GLOBAL <= 0 or 
        core.data.config.ZOMBIES_PER_SPAWN <= 0 or 
        core.data.config.ZOMBIE_MAX_CHUNK <= 0):
        desired_zombies = 0

    while (npc_count < desired_npcs or zombie_count < desired_zombies) and attempts < max_attempts:
        attempts += 1
        rx = random.randint(0, map_w - 1)
        ry = random.randint(0, map_h - 1)
        
        # Check tile using the specific layer data
        t_char = map_data[ry][rx]
        t_def = defs.get(t_char)
        if not t_def: continue
        
        t_name = t_def.get('name', '').lower()
        is_path = 'path' in t_name or 'cave_l2' in t_name or 'dirty' in t_name or 'asphalt' in t_name
        is_building = 'floor' in t_name or 'wood' in t_name or 'tile' in t_name or 'carpet' in t_name

        if not is_path and not is_building:
            continue
            
        px, py = rx * TILE_SIZE, ry * TILE_SIZE
        
        # Simple obstacle check (Only valid if we are on active layer, otherwise skip strict collision)
        # For offline generation, we trust the tile type mostly.
        
        if npc_count < desired_npcs and is_building:
            # [FIX] Initialize NPC with correct layer
            npc = NPC(px, py, game, is_static=False, layer=target_layer) 
            
            # [FIX] Force friendly if populating L2 (Safe Zone)
            if target_layer == 2:
                npc.is_friendly = True

            if is_active_layer:
                game.npcs.add(npc)
            else:
                # [FIX] Store in layer_npcs if not active layer
                if not hasattr(game, 'layer_npcs'):
                     game.layer_npcs = {}
                if target_layer not in game.layer_npcs:
                     game.layer_npcs[target_layer] = []
                game.layer_npcs[target_layer].append(npc)
                
            npc_count += 1
            continue
            
        if zombie_count < desired_zombies and is_path:
            zombie = Zombie.create_random(px, py)
            if is_active_layer:
                game.zombies.append(zombie)
            else:
                target_zombies.append(zombie)
            zombie_count += 1

def spawn_animals(game, count=5, target_layer=None):
    """
    Spawns animals based on 'ANM' markers or random distribution.
    Rules:
      - Rat: Spawns in Layer 1 and 2.
      - Bat: Spawns only in Layer 2.
      - Cow: Spawns only in Layer 1.
    """
    # [FIX] Respect Global Animal Configuration
    if core.data.config.ANIMAL_SPAWN_COUNT <= 0:
        print(f"[ANIMAL] Spawn skipped: ANIMAL_SPAWN_COUNT={core.data.config.ANIMAL_SPAWN_COUNT}")
        return

    if target_layer is None:
        target_layer = game.current_layer_index
    
    print(f"[ANIMAL] Spawning {count} animals on layer {target_layer}")

    if not hasattr(game, 'layer_zombies'):
        game.layer_zombies = {}
    if target_layer not in game.layer_zombies:
        game.layer_zombies[target_layer] = []

    if target_layer == game.current_layer_index:
        if not hasattr(game, 'items_on_ground'): game.items_on_ground = []
        target_list = game.items_on_ground
    else:
        target_list = game.layer_zombies[target_layer]
    
    AnimalLoader.load_animals()
    
    valid_animal_types = []
    
    # Layer Logic
    if target_layer >= 1:
        valid_animal_types.append("Rat")
    
    if target_layer == 1:
        # --- NEW: Cow only spawns on L1 ---
        valid_animal_types.append("Cow")
        
    if target_layer == 2:
        valid_animal_types.append("Bat")
        
    if not valid_animal_types:
        return

    spawned_count = 0
    
    # 1. Scan for 'ANM' markers in the specific layer
    spawn_markers = []
    spawn_layer = None
    
    if hasattr(game, 'all_spawn_layers') and target_layer in game.all_spawn_layers:
         spawn_layer = game.all_spawn_layers[target_layer]
    
    if spawn_layer:
         h = len(spawn_layer)
         w = len(spawn_layer[0]) if h > 0 else 0
         for y in range(h):
             for x in range(w):
                 if spawn_layer[y][x] == 'ANM':
                     spawn_markers.append((x * TILE_SIZE, y * TILE_SIZE))
    
    if spawn_markers:
        print(f"  > Found {len(spawn_markers)} 'ANM' markers on layer {target_layer}")

    # [CHANGED] Filter existing animals to check overlaps
    existing_animals = [x for x in target_list if isinstance(x, Animal)]
    
    # 2. Spawn at Markers (only if needed and empty)
    random.shuffle(spawn_markers)
    for px, py in spawn_markers:
        if len(existing_animals) + spawned_count >= count: break 
        
        # Check if occupied by another animal
        rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)
        if any(isinstance(a, Animal) and a.rect.colliderect(rect) for a in existing_animals):
             continue

        a_type = random.choice(valid_animal_types)
        # [FIX] Pass game instance and target_layer to Animal
        animal = Animal(px, py, a_type, game=game, layer=target_layer)
        target_list.append(animal)
        spawned_count += 1
        
    # 3. Random Spawn (Ambient) - only if few markers or to reach count
    if spawned_count + len(existing_animals) < count:
        # Only try random spawning if we have map data for this layer
        if hasattr(game, 'all_ground_layers') and target_layer in game.all_ground_layers:
            map_data = game.all_ground_layers[target_layer]
            map_h = len(map_data)
            map_w = len(map_data[0]) if map_h > 0 else 0
            
            attempts = 0
            max_attempts = 100
            
            defs = game.tile_manager.definitions

            while spawned_count + len(existing_animals) < count and attempts < max_attempts:
                attempts += 1
                rx = random.randint(0, map_w - 1)
                ry = random.randint(0, map_h - 1)
                
                # Check for obstacle logic if on active layer
                if target_layer == game.current_layer_index:
                    px, py = rx * TILE_SIZE, ry * TILE_SIZE
                    rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)
                    if any(ob.colliderect(rect) for ob in game.obstacles): continue
                
                # Check tile validity
                t_char = map_data[ry][rx]
                t_def = defs.get(t_char)
                if not t_def or t_def.get('is_obstacle', False): continue

                # Only Rats spawn randomly ambiently in most layers
                chosen_type = "Rat" if "Rat" in valid_animal_types else random.choice(valid_animal_types)
                
                px, py = rx * TILE_SIZE, ry * TILE_SIZE
                # [FIX] Pass game instance and target_layer to Animal
                animal = Animal(px, py, chosen_type, game=game, layer=target_layer)
                target_list.append(animal)
                spawned_count += 1
    
    if spawned_count > 0:
        print(f"  > Spawned {spawned_count} animals on Layer {target_layer} (Markers: {len(spawn_markers)}).")

def spawn_random_vehicles(game, count=10):
    loader = VehicleLoader()
    if not loader.definitions:
        print("No vehicle definitions found. Skipping vehicle generation.")
        return

    valid_tiles = []
    layer_idx = game.current_layer_index
    
    # ---------------------------------------------------------
    # 1. Try to find 'VEH' markers in the Spawn Map first
    # ---------------------------------------------------------
    spawn_found = False
    
    spawn_layer = None
    if hasattr(game, 'all_spawn_layers') and layer_idx in game.all_spawn_layers:
         spawn_layer = game.all_spawn_layers[layer_idx]
    
    if spawn_layer:
        h = len(spawn_layer)
        w = len(spawn_layer[0]) if h > 0 else 0
        for y in range(h):
            for x in range(w):
                if spawn_layer[y][x] == 'VEH':
                    valid_tiles.append((x, y))
                    spawn_found = True
        
        if spawn_found:
            print(f"Found {len(valid_tiles)} 'VEH' markers in spawn map.")
    
    # ---------------------------------------------------------
    # 2. Fallback: Scan map for valid tiles (Roads or Dirty_01)
    # ---------------------------------------------------------
    if not spawn_found:
        if layer_idx not in game.all_ground_layers:
            return

        map_data = game.all_ground_layers[layer_idx]
        height = len(map_data)
        width = len(map_data[0]) if height > 0 else 0

        for y in range(height):
            for x in range(width):
                char = map_data[y][x]
                tile_def = game.tile_manager.definitions.get(char)
                if tile_def:
                    t_name = tile_def.get('name', '').lower()
                    if 'road' in t_name or 'dirty_01' in t_name:
                        valid_tiles.append((x, y))

        if not valid_tiles:
            print("No valid road/dirty tiles found for vehicle spawning.")
            return

        random.shuffle(valid_tiles)

    # ---------------------------------------------------------
    # 3. Spawn Vehicles
    # ---------------------------------------------------------
    spawned_count = 0
    limit = count if not spawn_found else len(valid_tiles) 

    for tx, ty in valid_tiles:
        if spawned_count >= limit: break
        
        definition = loader.get_random_definition()
        if not definition: break

        images = definition.get('images', {})
        random_facing = random.choice(['top', 'down', 'left', 'right'])
        
        # Grab a fallback image to calculate width and height (prefer the chosen facing)
        base_img = images.get(random_facing)
        if not base_img and images:
            base_img = next(iter(images.values()))
            
        w = base_img.get_width() if base_img else TILE_SIZE * 2
        h = base_img.get_height() if base_img else TILE_SIZE * 3
        
        px, py = tx * TILE_SIZE, ty * TILE_SIZE
        
        veh_rect = pygame.Rect(px, py, w, h)
        
        collision = False
        for ob in game.obstacles:
            if veh_rect.colliderect(ob):
                collision = True
                break
        
        if collision:
            continue

        vehicle = Vehicle(
            name=definition['name'],
            x=px, y=py,
            width=w, height=h,
            image=images,
            stats=definition['stats'],
            capacity=definition['capacity'],
            loot_table=definition['loot_table'],
            facing=random_facing
        )
        
        if not hasattr(game, 'vehicles'):
            game.vehicles = []
            
        game.vehicles.append(vehicle)
        game.containers.append(vehicle)
        game.obstacles.append(vehicle.rect)
        
        spawned_count += 1
        print(f"Spawned {vehicle.name} at ({px}, {py})")

def spawn_initial_zombies(obstacles, zombie_spawns, items_on_ground, limit=1000, spawns_per_marker=None, map_width_px=None, map_height_px=None, player=None, obstacle_grid=None, grid_size=128, game=None):
    # [FIX] Absolutely kill the spawner if global/chunk config is 0. Do not proceed to defaults.
    if core.data.config.MAX_ZOMBIES_GLOBAL <= 0 or core.data.config.ZOMBIES_PER_SPAWN <= 0:
        return []

    zombies = []
    SAFE_RADIUS_TILES = 1 
    safe_dist_px = SAFE_RADIUS_TILES * TILE_SIZE
    
    filtered_spawns = []
    marker_exclusion_zone = set()
    min_spacing_tiles = 15

    if not zombie_spawns: return []
    
    min_sx = min(s[0] for s in zombie_spawns) - (10 * TILE_SIZE)
    max_sx = max(s[0] for s in zombie_spawns) + (10 * TILE_SIZE)
    min_sy = min(s[1] for s in zombie_spawns) - (10 * TILE_SIZE)
    max_sy = max(s[1] for s in zombie_spawns) + (10 * TILE_SIZE)
    
    for pos in zombie_spawns:
        tx = int(pos[0] // TILE_SIZE)
        ty = int(pos[1] // TILE_SIZE)
        if (tx, ty) in marker_exclusion_zone: continue
        filtered_spawns.append(pos)
        for i in range(-min_spacing_tiles, min_spacing_tiles + 1):
            for j in range(-min_spacing_tiles, min_spacing_tiles + 1):
                marker_exclusion_zone.add((tx + i, ty + j))

    occupied_tiles = set()
    relevant_obstacles = []

    if obstacle_grid:
        start_grid_x = int(min_sx // grid_size)
        end_grid_x = int(max_sx // grid_size)
        start_grid_y = int(min_sy // grid_size)
        end_grid_y = int(max_sy // grid_size)
        
        for gx in range(start_grid_x, end_grid_x + 1):
            for gy in range(start_grid_y, end_grid_y + 1):
                cell = (gx, gy)
                if cell in obstacle_grid:
                    relevant_obstacles.extend(obstacle_grid[cell])
    else:
        relevant_obstacles = obstacles

    for ob in relevant_obstacles:
        if ob.right > min_sx and ob.left < max_sx and ob.bottom > min_sy and ob.top < max_sy:
            for x_tile in range(ob.left // TILE_SIZE, (ob.right + TILE_SIZE - 1) // TILE_SIZE):
                for y_tile in range(ob.top // TILE_SIZE, (ob.bottom + TILE_SIZE - 1) // TILE_SIZE):
                    occupied_tiles.add((x_tile, y_tile))
                
    for entity in items_on_ground:
        occupied_tiles.add((entity.rect.x // TILE_SIZE, entity.rect.y // TILE_SIZE))
    
    if player:
        occupied_tiles.add((player.rect.x // TILE_SIZE, player.rect.y // TILE_SIZE))

    if spawns_per_marker is None:
        try:
            spawns_per_marker = max(1, ZOMBIES_PER_SPAWN // 2)
        except NameError:
             spawns_per_marker = 3 

    for pos in filtered_spawns:
        if len(zombies) >= limit: break

        if player:
            dist = math.hypot(pos[0] - player.x, pos[1] - player.y)
            if dist < safe_dist_px:
                continue

        for _ in range(spawns_per_marker): 
            if len(zombies) >= limit: break
            
            spawn_spot_px = _find_spawn_spot_near(pos, occupied_tiles, map_width_px, map_height_px)
            
            if spawn_spot_px:
                if game and game.current_layer_index == 2:
                    gx = int(spawn_spot_px[0] // TILE_SIZE)
                    gy = int(spawn_spot_px[1] // TILE_SIZE)
                    tile = game.map_manager.get_tile_at(gx, gy)
                    
                    is_valid = False
                    if tile:
                        t_name = tile.get('name', '').lower()
                        if 'cave_l2' in t_name or 'path' in t_name or 'dirty' in t_name or 'asphalt' in t_name:
                             is_valid = True
                    
                    if not is_valid:
                        continue 

                zombie = Zombie.create_random(spawn_spot_px[0], spawn_spot_px[1])
                zombies.append(zombie)
            else:
                break 
                
    return zombies