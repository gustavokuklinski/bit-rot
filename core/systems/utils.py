import pygame
import math
from core.data.config import GAME_OFFSET_X, GAME_WIDTH, GAME_HEIGHT, TILE_SIZE

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
    all_candidates = game.items_on_ground + game.containers + game.corpses
    
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
    """
    Returns the highest priority interactable entity based on where the player is facing,
    with a forgiving search radius for analog stick users.
    """
    if not getattr(game, 'player', None): return None

    facing_x, facing_y = get_player_facing_tile(game)
    if facing_x is None: return None
    
    target_world_x = facing_x * TILE_SIZE + TILE_SIZE / 2
    target_world_y = facing_y * TILE_SIZE + TILE_SIZE / 2
    
    candidates = []
    
    px, py = int(game.player.rect.centerx // TILE_SIZE), int(game.player.rect.centery // TILE_SIZE)
    
    # 1. Stairs (Highest Priority if standing directly on them)
    if hasattr(game, 'map_data') and 0 <= py < len(game.map_data) and 0 <= px < len(game.map_data[0]):
        current_t = game.map_manager.get_tile_at(px, py)
        if current_t and current_t.get('is_stair'):
            candidates.append({'type': 'stair', 'entity': (px, py), 'dist': -1}) 
    
    # 2. Facing Tile & Nearby Tiles (Doors / Windows / Stairs)
    # To make this mobile-friendly, we search a 3x3 area around the player
    # and find the closest interactable tile. 
    best_tile = find_interactable_tile(game)
    if best_tile:
        tx, ty = best_tile
        # Calculate distance to prioritize it properly
        tile_center_x = (tx * TILE_SIZE) + (TILE_SIZE / 2)
        tile_center_y = (ty * TILE_SIZE) + (TILE_SIZE / 2)
        dist = math.hypot(game.player.rect.centerx - tile_center_x, game.player.rect.centery - tile_center_y)
        candidates.append({'type': 'tile', 'entity': (tx, ty), 'dist': dist})
    
    # Also explicitly check the facing tile if it's a stair (since find_interactable_tile only checks 'is_statable')
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
            dist = math.hypot(game.player.rect.centerx - obj.rect.centerx, game.player.rect.centery - obj.rect.centery)
            if dist < TILE_SIZE * 2.0:
                facing_dist = math.hypot(target_world_x - obj.rect.centerx, target_world_y - obj.rect.centery)
                veh_grid_rect = pygame.Rect(obj.rect.x, obj.rect.y, obj.rect.width, obj.rect.height)
                facing_rect = pygame.Rect(facing_x * TILE_SIZE, facing_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if veh_grid_rect.colliderect(facing_rect):
                    facing_dist -= TILE_SIZE 
                candidates.append({'type': 'vehicle', 'entity': obj, 'dist': facing_dist})
                
    if not candidates:
        return None
        
    # Sort by closest distance 
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