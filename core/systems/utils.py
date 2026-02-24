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

def screen_to_world(game, screen_pos):
    screen_x, screen_y = screen_pos
    screen_x -= GAME_OFFSET_X
    
    zoom = getattr(game, 'zoom_level', 1.0)
    
    # Scale screen coordinates down to the view's internal resolution
    view_x = screen_x / zoom
    view_y = screen_y / zoom
    
    # Subtract the camera offset to get the true world coordinates
    offset_x = getattr(game, 'offset_x', 0)
    offset_y = getattr(game, 'offset_y', 0)
    
    return (view_x - offset_x, view_y - offset_y)