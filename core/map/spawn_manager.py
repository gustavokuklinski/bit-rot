import pygame
import random
import math
import core.data.config
from core.data.config import *
from core.entities.item.item import Item
from core.entities.zombie.zombie import Zombie
from core.entities.npc.npc import NPC

# --- Configuration for Dynamic Spawning ---
# Reduced max active NPCs to improve performance on slower systems
MAX_ACTIVE_NPCS = 2
NPC_SPAWN_RADIUS = 30 * TILE_SIZE  # Slightly reduced radius
NPC_DESPAWN_RADIUS = 50 * TILE_SIZE 
NPC_MIN_SPAWN_DIST = 15 * TILE_SIZE 

def spawn_initial_items(obstacles, item_spawns):
    items_on_ground = []
    occupied_tiles = set()
    for ob in obstacles:
        occupied_tiles.add((ob.x // TILE_SIZE, ob.y // TILE_SIZE))

    for pos in item_spawns:
        item = Item.generate_random()
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
    """
    Called every few frames to manage NPC population.
    1. Despawns NPCs that are too far.
    2. Spawns new NPCs if near a spawn point and under the limit.
    """
    if not game.player: return

    player_x, player_y = game.player.rect.centerx, game.player.rect.centery

    # 1. Despawn far NPCs
    # Using a reverse loop to remove safely
    for npc in list(game.npcs):
        # Don't despawn followers/friends
        if hasattr(npc, 'is_following') and npc.is_following:
            continue
            
        dist_sq = (npc.rect.centerx - player_x)**2 + (npc.rect.centery - player_y)**2
        if dist_sq > NPC_DESPAWN_RADIUS**2:
            game.npcs.remove(npc)

    # 2. Check if we need more NPCs
    current_count = len(game.npcs)
    if current_count >= MAX_ACTIVE_NPCS:
        return

    # 3. Spawn new NPCs near player
    spawn_points = getattr(game, 'npc_spawn_points', [])
    
    spawned_this_frame = 0
    limit_per_frame = 1 # Strictly limit new creations to prevent frame drops
    
    # Pre-calculate squared radius for faster comparison
    spawn_rad_sq = NPC_SPAWN_RADIUS**2
    min_spawn_rad_sq = NPC_MIN_SPAWN_DIST**2
    
    p_rect = game.player.rect
    # Create a simple rect for rough collision first (very fast)
    search_rect = pygame.Rect(
        p_rect.centerx - NPC_SPAWN_RADIUS, 
        p_rect.centery - NPC_SPAWN_RADIUS, 
        NPC_SPAWN_RADIUS * 2, 
        NPC_SPAWN_RADIUS * 2
    )

    valid_candidates = []
    
    # Collect candidates (only check basic bounds first)
    for pos in spawn_points:
        if search_rect.collidepoint(pos):
             valid_candidates.append(pos)
    
    if not valid_candidates: return

    random.shuffle(valid_candidates)

    for pos in valid_candidates:
        if current_count >= MAX_ACTIVE_NPCS: break
        if spawned_this_frame >= limit_per_frame: break

        px, py = pos
        dist_sq = (px - player_x)**2 + (py - player_y)**2

        # Check precise range
        if min_spawn_rad_sq < dist_sq < spawn_rad_sq:
            
            # Check if an NPC is already close to this spot (prevent stacking)
            too_crowded = False
            for npc in game.npcs:
                # 2 Tiles squared = (64*2)^2 roughly
                if (npc.rect.x - px)**2 + (npc.rect.y - py)**2 < (TILE_SIZE * 2)**2:
                    too_crowded = True
                    break
            
            if not too_crowded:
                npc = NPC(px, py, game)
                game.npcs.add(npc)
                current_count += 1
                spawned_this_frame += 1

def spawn_initial_zombies(obstacles, zombie_spawns, items_on_ground, limit=1000, spawns_per_marker=None, map_width_px=None, map_height_px=None, player=None):
    zombies = []
    SAFE_RADIUS_TILES = 35 
    safe_dist_px = SAFE_RADIUS_TILES * TILE_SIZE
    
    filtered_spawns = []
    marker_exclusion_zone = set()
    min_spacing_tiles = 5
    
    for pos in zombie_spawns:
        tx = int(pos[0] // TILE_SIZE)
        ty = int(pos[1] // TILE_SIZE)
        
        if (tx, ty) in marker_exclusion_zone:
            continue
            
        filtered_spawns.append(pos)
        
        for i in range(-min_spacing_tiles, min_spacing_tiles + 1):
            for j in range(-min_spacing_tiles, min_spacing_tiles + 1):
                marker_exclusion_zone.add((tx + i, ty + j))

    occupied_tiles = set()
    for ob in obstacles:
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
                zombie = Zombie.create_random(spawn_spot_px[0], spawn_spot_px[1])
                zombies.append(zombie)
            else:
                break 
                
    return zombies