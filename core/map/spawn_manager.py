# core/map/spawn_manager.py

import pygame
import random
import math
import core.data.config
from core.data.config import *
from core.entities.item.item import Item
from core.entities.zombie.zombie import Zombie
from core.entities.npc.npc import NPC

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
                # We allow specific map items to spawn even if "occupied" (e.g. on top of a rug)
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

    for npc in list(game.npcs):
        if hasattr(npc, 'is_following') and npc.is_following: continue
        dist_sq = (npc.rect.centerx - player_x)**2 + (npc.rect.centery - player_y)**2
        if dist_sq > NPC_DESPAWN_RADIUS**2:
            game.npcs.remove(npc)

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

                npc = NPC(px, py, game)
                game.npcs.add(npc)
                current_count += 1
                spawned_this_frame += 1

def spawn_static_npcs(game, building_tiles):
    for (tx, ty) in building_tiles:
        if random.random() < NPC_STATIC_SPAWN:
            px, py = tx * TILE_SIZE, ty * TILE_SIZE
            if not any(ob.collidepoint(px, py) for ob in game.obstacles):
                npc = NPC(px, py, game, is_static=True)
                game.npcs.add(npc)

def spawn_l2_population(game, count=10):
    if not game.map_data: return
    
    map_h = len(game.map_data)
    map_w = len(game.map_data[0]) if map_h > 0 else 0
    
    npc_count = 0
    zombie_count = 0
    target_npcs = 3
    target_zombies = count
    
    attempts = 0
    max_attempts = 1000
    
    while (npc_count < target_npcs or zombie_count < target_zombies) and attempts < max_attempts:
        attempts += 1
        rx = random.randint(0, map_w - 1)
        ry = random.randint(0, map_h - 1)
        
        tile = game.map_manager.get_tile_at(rx, ry)
        if not tile: continue
        
        t_name = tile.get('name', '').lower()
        is_path = 'path' in t_name or 'cave_l2' in t_name or 'dirty' in t_name or 'asphalt' in t_name
        is_building = 'floor' in t_name or 'wood' in t_name or 'tile' in t_name or 'carpet' in t_name

        if not is_path and not is_building:
            continue
            
        px, py = rx * TILE_SIZE, ry * TILE_SIZE
        rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)
        
        if any(ob.colliderect(rect) for ob in game.obstacles): continue
        
        if npc_count < target_npcs and is_building:
            npc = NPC(px, py, game, is_static=False) 
            game.npcs.add(npc)
            npc_count += 1
            continue
            
        if zombie_count < target_zombies and is_path:
            zombie = Zombie.create_random(px, py)
            game.zombies.append(zombie)
            zombie_count += 1

def spawn_initial_zombies(obstacles, zombie_spawns, items_on_ground, limit=1000, spawns_per_marker=None, map_width_px=None, map_height_px=None, player=None, obstacle_grid=None, grid_size=128, game=None):
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