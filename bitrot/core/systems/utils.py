# core/systems/utils.py

import pygame
import math
import core.data.config
from core.data.config import GAME_OFFSET_X, GAME_WIDTH, GAME_HEIGHT, TILE_SIZE
from core.messages import display_message
from core.placement import find_free_tile
from core.data.localization import tr

def create_smooth_entity_mask(width=TILE_SIZE, height=TILE_SIZE, inset_x=2, inset_y=2):
    """Creates a smoothed, rounded collision mask that glides around corners and through 1-tile doorways."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    rect = pygame.Rect(inset_x, inset_y, max(2, width - inset_x * 2), max(2, height - inset_y * 2))
    pygame.draw.ellipse(surf, (255, 255, 255, 255), rect)
    return pygame.mask.from_surface(surf)

def teleport_player_to_chunk(game, dest_gx, dest_gy, dest_layer=1):
    if not getattr(game, 'player', None):
        return

    # Exit vehicle if seated
    if getattr(game.player, 'vehicle', None):
        game.player.exit_vehicle(game)

    current_map = game.map_manager.current_map_filename
    game.map_states.setdefault(current_map, {})

    chasing_zombies = [z for z in game.zombies if getattr(z, 'state', '') == 'chasing']
    game.map_states[current_map]['zombies'] = [z for z in game.zombies if z not in chasing_zombies]

    chasing_animals = []
    if hasattr(game, 'active_animals'):
        chasing_animals = [a for a in game.active_animals if getattr(a, 'state', '') == 'chasing']
        game.map_states[current_map]['active_animals'] = [a for a in game.active_animals if a not in chasing_animals]

    game.map_states[current_map]['items_on_ground'] = [i for i in game.items_on_ground if i not in chasing_animals]

    if hasattr(game, 'npcs'):
        game.map_states[current_map]['npcs'] = list(game.npcs)

    clean_containers = [c for c in game.containers if c != getattr(game.player, 'vehicle', None)]
    game.map_states[current_map]['containers'] = clean_containers

    if hasattr(game.map_manager, 'vehicles'):
        clean_vehicles = [v for v in game.map_manager.vehicles if v != getattr(game.player, 'vehicle', None)]
        game.map_states[current_map]['vehicles'] = clean_vehicles

    new_map = f"map_L{dest_layer}_{dest_gx}_{dest_gy}_map.csv"

    # Generate chunk on demand if needed
    if new_map not in game.map_manager.map_files:
        if hasattr(game, 'generator') and game.generator:
            game.generator.generate_chunk_on_demand(dest_gx, dest_gy)
            game.map_manager.refresh_maps()

    if new_map not in game.map_manager.map_files:
        display_message(tr('msg', "Failed to navigate to destination."))
        return

    game.load_map(new_map)

    # Restore or spawn state
    if new_map in game.map_states:
        game.items_on_ground = game.map_states[new_map].get('items_on_ground', [])
        game.zombies = game.map_states[new_map].get('zombies', [])
        if hasattr(game, 'active_animals'):
            game.active_animals = game.map_states[new_map].get('active_animals', [])
        if hasattr(game, 'npcs'):
            game.npcs.empty()
            for npc in game.map_states[new_map].get('npcs', []):
                game.npcs.add(npc)
        if 'containers' in game.map_states[new_map]:
            default_container_rects = [c.rect for c in game.containers]
            obstacle_container_rects = [r for r in default_container_rects if r in game.obstacles]
            game.obstacles = [obs for obs in game.obstacles if obs not in default_container_rects]
            game.containers = game.map_states[new_map]['containers']
            for c in game.containers:
                if c.rect in obstacle_container_rects and c.rect not in game.obstacles:
                    game.obstacles.append(c.rect)
        if 'vehicles' in game.map_states[new_map] and hasattr(game.map_manager, 'vehicles'):
            default_veh_rects = [v.rect for v in game.map_manager.vehicles]
            game.obstacles = [obs for obs in game.obstacles if obs not in default_veh_rects]
            game.map_manager.vehicles = game.map_states[new_map]['vehicles']
            for v in game.map_manager.vehicles:
                if v.rect not in game.obstacles:
                    game.obstacles.append(v.rect)
    else:
        game.items_on_ground = []
        game.zombies = []
        if hasattr(game, 'active_animals'):
            game.active_animals = []
        if hasattr(game, 'npcs'):
            game.npcs.empty()

        is_lobby = getattr(game, 'generator', None) and (dest_gx, dest_gy) == getattr(game.generator, 'lobby_chunk', None)
        if not is_lobby:
            from core.map.spawn_manager import spawn_initial_zombies
            if hasattr(game, 'current_zombie_spawns') and game.current_zombie_spawns:
                initial_zombies = spawn_initial_zombies(
                    game.obstacles,
                    game.current_zombie_spawns,
                    game.items_on_ground + [game.player],
                    limit=core.data.config.MAX_ZOMBIES_GLOBAL,
                    spawns_per_marker=core.data.config.ZOMBIES_PER_SPAWN,
                    game=game
                )
                game.zombies.extend(initial_zombies)

    h = len(game.map_data) if game.map_data else 0
    w = len(game.map_data[0]) if h > 0 else 0

    is_dest_lobby = getattr(game, 'generator', None) and (dest_gx, dest_gy) == getattr(game.generator, 'lobby_chunk', None)
    target_marker = 'P' if is_dest_lobby else 'P2'

    spawn_pos = None

    # 0. Check parsed player spawn
    if getattr(game, 'player_spawn', None):
        test_rect = pygame.Rect(game.player_spawn[0], game.player_spawn[1], TILE_SIZE, TILE_SIZE)
        if not any(test_rect.colliderect(ob) for ob in game.obstacles):
            spawn_pos = game.player_spawn

    # 1. Search for target spawn marker: 'P' for Lobby, 'P2' for other chunks (sand tile at Port_L1)
    if not spawn_pos and getattr(game, 'spawn_data', None):
        for y in range(min(h, len(game.spawn_data))):
            for x in range(min(w, len(game.spawn_data[y]))):
                char = game.spawn_data[y][x]
                if isinstance(char, str) and char.strip() == target_marker:
                    test_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if not any(test_rect.colliderect(ob) for ob in game.obstacles):
                        spawn_pos = (x * TILE_SIZE, y * TILE_SIZE)
                        break
            if spawn_pos:
                break

        # 1.5 Fallback if the exact marker tile is blocked by an obstacle
        if not spawn_pos:
            for y in range(min(h, len(game.spawn_data))):
                for x in range(min(w, len(game.spawn_data[y]))):
                    char = game.spawn_data[y][x]
                    if isinstance(char, str) and char.strip() == target_marker:
                        free_tile = find_free_tile(game.player.rect, game.obstacles, initial_pos=(x * TILE_SIZE, y * TILE_SIZE), max_radius=8)
                        if free_tile:
                            spawn_pos = free_tile
                            break
                if spawn_pos:
                    break

    # 2. If marker not found, locate the boat
    boat_tx, boat_ty = None, None
    if not spawn_pos:
        for y in range(h):
            for x in range(w):
                b_char = game.map_data[y][x] if y < len(game.map_data) and x < len(game.map_data[y]) else ''
                g_char = game.ground_data[y][x] if (getattr(game, 'ground_data', None) and y < len(game.ground_data) and x < len(game.ground_data[y])) else ''
                s_char = game.spawn_data[y][x] if (getattr(game, 'spawn_data', None) and y < len(game.spawn_data) and x < len(game.spawn_data[y])) else ''
                t_def = game.map_manager.get_tile_at(x, y)

                if (
                    (isinstance(b_char, str) and b_char.strip() in ('tp_boat', 'teleport_boat')) or
                    (isinstance(g_char, str) and g_char.strip() in ('tp_boat', 'teleport_boat')) or
                    (isinstance(s_char, str) and s_char.strip() in ('tp_boat', 'teleport_boat')) or
                    (t_def and (t_def.get('type') == 'maptile_teleport' or t_def.get('name') in ('tp_boat', 'teleport_boat') or 'boat' in t_def.get('name', '').lower()))
                ):
                    boat_tx, boat_ty = x, y
                    break
            if boat_tx is not None:
                break

    # 3. Locate the nearest walkable sand tile to the boat at Port_L1
    if not spawn_pos and boat_tx is not None and boat_ty is not None:
        sand_near_boat = []
        for dy in range(-15, 16):
            for dx in range(-15, 16):
                sx = boat_tx + dx
                sy = boat_ty + dy
                if 0 <= sx < w and 0 <= sy < h:
                    g_char = game.ground_data[sy][sx] if (getattr(game, 'ground_data', None) and sy < len(game.ground_data) and sx < len(game.ground_data[sy])) else ''
                    g_name = g_char.strip().lower() if isinstance(g_char, str) else ''
                    b_char = game.map_data[sy][sx] if sy < len(game.map_data) and sx < len(game.map_data[sy]) else ''
                    b_char = b_char.strip() if isinstance(b_char, str) else ''
                    b_def = game.map_manager.get_tile_at(sx, sy)

                    if b_char in ('', ' ') and not (b_def and b_def.get('is_obstacle', False)):
                        if 'sand' in g_name or 'beach' in g_name:
                            test_rect = pygame.Rect(sx * TILE_SIZE, sy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                            if not any(test_rect.colliderect(ob) for ob in game.obstacles):
                                dist = math.hypot(dx, dy)
                                sand_near_boat.append((dist, sx * TILE_SIZE, sy * TILE_SIZE))

        if sand_near_boat:
            sand_near_boat.sort(key=lambda c: c[0])
            spawn_pos = (sand_near_boat[0][1], sand_near_boat[0][2])

    # 4. Fallback directly near the boat (never center chunk!)
    if not spawn_pos and boat_tx is not None and boat_ty is not None:
        free_tile = find_free_tile(game.player.rect, game.obstacles, initial_pos=(boat_tx * TILE_SIZE, boat_ty * TILE_SIZE), max_radius=8)
        if free_tile:
            spawn_pos = free_tile

    # 5. Fallback on any free sand tile in the map
    if not spawn_pos:
        for y in range(h):
            for x in range(w):
                g_char = game.ground_data[y][x] if (getattr(game, 'ground_data', None) and y < len(game.ground_data) and x < len(game.ground_data[y])) else ''
                b_char = game.map_data[y][x] if y < len(game.map_data) and x < len(game.map_data[y]) else ''
                b_def = game.map_manager.get_tile_at(x, y)
                g_char = g_char.strip() if isinstance(g_char, str) else ''
                b_char = b_char.strip() if isinstance(b_char, str) else ''
                
                if b_char in (' ', '') and not (b_def and b_def.get('is_obstacle', False)):
                    if 'sand' in g_char.lower() or 'beach' in g_char.lower():
                        test_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        if not any(test_rect.colliderect(ob) for ob in game.obstacles):
                            spawn_pos = (x * TILE_SIZE, y * TILE_SIZE)
                            break
            if spawn_pos:
                break

    # Apply spawn position directly
    if spawn_pos:
        game.player.x = float(spawn_pos[0])
        game.player.y = float(spawn_pos[1])
        game.player.rect.topleft = (int(game.player.x), int(game.player.y))
    game.player.vx = 0
    game.player.vy = 0

    # Center camera directly on the player
    view_w = int(game.dynamic_w / game.zoom_level)
    view_h = int(game.dynamic_h / game.zoom_level)
    game.true_camera_x = game.player.rect.centerx - (view_w / 2)
    game.true_camera_y = game.player.rect.centery - (view_h / 2)
    game.camera_pan_x = 0
    game.camera_pan_y = 0

    # Refresh spatial grids
    if hasattr(game, 'spatial_manager'):
        game.spatial_manager.rebuild_zombie_grid()
        game.spatial_manager.rebuild_item_grid(force=True)
        game.spatial_manager.rebuild_container_grid()

    game.game_state = 'CHUNK_LOADING'
    display_message(tr('msg', "Arrived at destination."))


def resolve_stuck_in_obstacle(entity, obstacles, game):
    """Gently nudges an entity outward if it ever starts inside an obstacle."""
    if not obstacles or not hasattr(entity, 'rect'):
        return
    indices = entity.rect.collidelistall(obstacles)
    for idx in indices:
        obs = obstacles[idx]
        gx = obs.x // TILE_SIZE
        gy = obs.y // TILE_SIZE
        tile_def = game.map_manager.get_tile_at(gx, gy) if hasattr(game, 'map_manager') else None
        
        collides = False
        if tile_def and 'mask' in tile_def and getattr(entity, 'mask', None):
            offset = (obs.x - entity.rect.x, obs.y - entity.rect.y)
            if entity.mask.overlap(tile_def['mask'], offset):
                collides = True
        else:
            collides = True
            
        if collides:
            dx = entity.rect.centerx - obs.centerx
            dy = entity.rect.centery - obs.centery
            dist = math.hypot(dx, dy)
            push = 2.0
            if dist > 0.001:
                entity.x += (dx / dist) * push
                entity.y += (dy / dist) * push
            else:
                entity.x += push
            entity.rect.topleft = (round(entity.x), round(entity.y))

def capture_pause_screen(game):
    """Creates a black and white version of the current screen for the pause menu."""
    game.paused_surface = game.game_screen.copy()
    try:
        game.paused_surface = pygame.transform.grayscale(game.paused_surface)
    except AttributeError:
        bw = pygame.Surface(game.paused_surface.get_size())
        bw.fill((255, 255, 255))
        game.paused_surface.blit(bw, (0,0), special_flags=pygame.BLEND_RGB_MULT)

def get_scaled_mouse_pos(game):
    real_mouse_pos = pygame.mouse.get_pos()
    current_w, current_h = game.game_screen.get_size()
    scale = min(current_w / GAME_WIDTH, current_h / GAME_HEIGHT)
    scaled_w, scaled_h = int(GAME_WIDTH * scale), int(GAME_HEIGHT * scale)
    blit_x = (current_w - scaled_w) // 2
    blit_y = (current_h - scaled_h) // 2
    return ((real_mouse_pos[0] - blit_x) / scale, (real_mouse_pos[1] - blit_y) / scale)

def get_player_facing_tile(game):
    if not game.player: return None, None
    player_grid_x = game.player.rect.centerx // TILE_SIZE
    player_grid_y = game.player.rect.centery // TILE_SIZE
    facing_x, facing_y = getattr(game.player, 'facing_direction', (0, 1))
    return player_grid_x + facing_x, player_grid_y + facing_y

def find_interactable_tile(game):
    if not game.player: return None

    facing_x, facing_y = get_player_facing_tile(game)
    if facing_x is not None:
        t = game.map_manager.get_tile_at(facing_x, facing_y)
        if t and t.get('is_statable'):
                return (facing_x, facing_y)

    player_pos = game.player.rect.center
    p_grid_x = int(player_pos[0] // TILE_SIZE)
    p_grid_y = int(player_pos[1] // TILE_SIZE)
    
    best_tile = None
    best_dist = float('inf')
    
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tx, ty = p_grid_x + dx, p_grid_y + dy
            t = game.map_manager.get_tile_at(tx, ty)
            
            if t and t.get('is_statable'):
                    tile_center_x = (tx * TILE_SIZE) + (TILE_SIZE / 2)
                    tile_center_y = (ty * TILE_SIZE) + (TILE_SIZE / 2)
                    dist = math.hypot(player_pos[0] - tile_center_x, player_pos[1] - tile_center_y)
                    
                    if dist <= TILE_SIZE * 1.5 and dist < best_dist:
                        best_dist = dist
                        best_tile = (tx, ty)
    
    return best_tile

def find_nearby_containers(game):
    nearby_objects = []
    seen_ids = set()
    all_candidates = game.items_on_ground + game.containers + getattr(game, 'corpses', [])
    
    for obj in all_candidates:
        if id(obj) in seen_ids:
            continue
            
        if hasattr(obj, 'rect'):
            dist = math.hypot(game.player.rect.centerx - obj.rect.centerx, game.player.rect.centery - obj.rect.centery)
            if dist <= TILE_SIZE * 1.5:
                nearby_objects.append(obj)
                seen_ids.add(id(obj))
                
    return nearby_objects

def get_targeted_interactable(game):
    if not getattr(game, 'player', None): return None

    facing_x, facing_y = get_player_facing_tile(game)
    if facing_x is None: return None
    
    target_world_x = facing_x * TILE_SIZE + TILE_SIZE / 2
    target_world_y = facing_y * TILE_SIZE + TILE_SIZE / 2
    
    candidates = []
    px, py = int(game.player.rect.centerx // TILE_SIZE), int(game.player.rect.centery // TILE_SIZE)
    
    # 1. Stairs
    if hasattr(game, 'map_data') and 0 <= py < len(game.map_data) and 0 <= px < len(game.map_data[0]):
        current_t = game.map_manager.get_tile_at(px, py)
        if current_t and current_t.get('is_stair'):
            candidates.append({'type': 'stair', 'entity': (px, py), 'dist': -1}) 
    
    # 2. Facing Tile & Nearby Tiles
    best_tile = find_interactable_tile(game)
    if best_tile:
        tx, ty = best_tile
        tile_center_x = (tx * TILE_SIZE) + (TILE_SIZE / 2)
        tile_center_y = (ty * TILE_SIZE) + (TILE_SIZE / 2)
        dist = math.hypot(game.player.rect.centerx - tile_center_x, game.player.rect.centery - tile_center_y)
        candidates.append({'type': 'tile', 'entity': (tx, ty), 'dist': dist})
    
    if hasattr(game, 'map_data') and 0 <= facing_y < len(game.map_data) and 0 <= facing_x < len(game.map_data[0]):
        facing_t = game.map_manager.get_tile_at(facing_x, facing_y)
        if facing_t and facing_t.get('is_stair'):
             candidates.append({'type': 'tile', 'entity': (facing_x, facing_y), 'dist': 0.1})

    # 3. NPCs
    for npc in getattr(game, 'npcs', []):
        if not getattr(npc, 'is_friendly', False) or getattr(npc, 'aggro_timer', 0) > 0: continue
        dist = math.hypot(game.player.rect.centerx - npc.rect.centerx, game.player.rect.centery - npc.rect.centery)
        if dist < TILE_SIZE * 1.5:
            facing_dist = math.hypot(target_world_x - npc.rect.centerx, target_world_y - npc.rect.centery)
            candidates.append({'type': 'npc', 'entity': npc, 'dist': facing_dist})
            
    # 4. Vehicles
    for obj in getattr(game, 'containers', []):
        if getattr(obj, 'item_type', '') == 'vehicle':
            if getattr(game.player, 'vehicle', None) == obj:
                continue
            interact_rect = obj.rect.inflate(TILE_SIZE, TILE_SIZE)
            if interact_rect.colliderect(game.player.rect):
                facing_dist = math.hypot(target_world_x - obj.rect.centerx, target_world_y - obj.rect.centery)
                facing_rect = pygame.Rect(facing_x * TILE_SIZE, facing_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if obj.rect.colliderect(facing_rect):
                    facing_dist -= 1000 
                candidates.append({'type': 'vehicle', 'entity': obj, 'dist': facing_dist})

    for obj in find_nearby_containers(game):
        if getattr(obj, 'item_type', '') == 'vehicle':
            continue
        
        is_valid = False
        item_type = getattr(obj, 'item_type', '')
        if item_type in ['container', 'maptile_container', 'corpse']:
            is_valid = True
        elif type(obj).__name__ == 'Corpse':
            is_valid = True
            
        if is_valid:
            facing_dist = math.hypot(target_world_x - obj.rect.centerx, target_world_y - obj.rect.centery)
            facing_rect = pygame.Rect(facing_x * TILE_SIZE, facing_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if obj.rect.colliderect(facing_rect):
                facing_dist -= 500 
            candidates.append({'type': 'container', 'entity': obj, 'dist': facing_dist})

    if not candidates:
        return None
        
    candidates.sort(key=lambda x: x['dist'])
    return candidates[0]

def screen_to_world(game, screen_pos):
    screen_x, screen_y = screen_pos
    screen_x -= GAME_OFFSET_X
    zoom = getattr(game, 'zoom_level', 1.0)
    view_x = screen_x / zoom
    view_y = screen_y / zoom
    offset_x = getattr(game, 'offset_x', 0)
    offset_y = getattr(game, 'offset_y', 0)
    return (view_x - offset_x, view_y - offset_y)