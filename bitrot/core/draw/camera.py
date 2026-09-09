import pygame
import math
from core.data.config import GAME_WIDTH, GAME_HEIGHT, TILE_SIZE
from core.ui.helpers.keybinds import keybind_manager

def update_camera(game):
    zoom = getattr(game, 'zoom_level', 1.0)
    
    left_encroachment = 0
    right_encroachment = 0
    dynamic_h = GAME_HEIGHT
    ignored_modals = {'big_map', 'npc_dialog', 'crafting'}
    
    for modal in getattr(game, 'modals', []):
        if 'rect' in modal and modal.get('type') not in ignored_modals:
            if modal['rect'].left >= GAME_WIDTH - 256:
                right_encroachment = max(right_encroachment, GAME_WIDTH - modal['rect'].left)
            if modal['rect'].right <= 256:
                left_encroachment = max(left_encroachment, modal['rect'].right)
            if modal['rect'].top >= GAME_HEIGHT - 256:
                dynamic_h = min(dynamic_h, modal['rect'].top)
                    
    final_w = max(GAME_WIDTH // 3, GAME_WIDTH - left_encroachment - right_encroachment)
    final_h = max(GAME_HEIGHT // 3, dynamic_h)

    game.dynamic_w = final_w
    game.dynamic_h = final_h
    game.viewport_left_offset = left_encroachment

    view_w = int(final_w / zoom)
    view_h = int(final_h / zoom)

    mouse_pos = game._get_scaled_mouse_pos()
    mouse_buttons = pygame.mouse.get_pressed()
    keys = pygame.key.get_pressed()

    joy_lx, joy_ly = 0, 0
    joy_run, joy_aim = False, False
    if getattr(game, 'joystick_handler', None):
        joy_lx, joy_ly = game.joystick_handler.get_movement_axes()
        if hasattr(game.joystick_handler, 'is_rt_pressed'):
            joy_aim = game.joystick_handler.is_rt_pressed()
        if game.joystick_handler.active_controller:
            joy_run_btn = keybind_manager.joy_binds.get('run')
            if joy_run_btn is not None:
                try:
                    joy_run = game.joystick_handler.active_controller.get_button(joy_run_btn)
                except pygame.error: pass

    is_running = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or joy_run)
    game.player.is_running = is_running
    is_aiming = (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL] or mouse_buttons[2] or joy_aim)
    game.player.is_aiming = is_aiming 

    target_pan_x, target_pan_y = 0, 0
    if game.player:
        adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
        world_mouse_pos = game.screen_to_world(adjusted_mouse_pos)
        dx = world_mouse_pos[0] - game.player.rect.centerx
        dy = world_mouse_pos[1] - game.player.rect.centery
        game.player.aim_angle = math.atan2(-dy, dx)

    dt_mult = getattr(game, 'dt_mult', 1.0)
    if not hasattr(game, 'camera_pan_x'): game.camera_pan_x = 0
    if not hasattr(game, 'camera_pan_y'): game.camera_pan_y = 0
    
    lerp_factor = 1.0 - math.pow(1.0 - 0.1, dt_mult)
    game.camera_pan_x += (target_pan_x - game.camera_pan_x) * lerp_factor
    game.camera_pan_y += (target_pan_y - game.camera_pan_y) * lerp_factor

    if game.player:
        game.true_camera_x = game.player.rect.centerx - (view_w / 2)
        game.true_camera_y = game.player.rect.centery - (view_h / 2)

    target_offset_x = -game.true_camera_x - game.camera_pan_x
    target_offset_y = -game.true_camera_y - game.camera_pan_y

    map_h = len(game.map_data) if hasattr(game, 'map_data') and game.map_data else 0
    map_w = len(game.map_data[0]) if map_h > 0 else 0
    map_pixel_w = map_w * TILE_SIZE
    map_pixel_h = map_h * TILE_SIZE

    if map_pixel_w > 0 and map_pixel_h > 0:
        if map_pixel_w < view_w: offset_x = (view_w - map_pixel_w) / 2 
        else: offset_x = max(view_w - map_pixel_w, min(0, target_offset_x))
            
        if map_pixel_h < view_h: offset_y = (view_h - map_pixel_h) / 2
        else: offset_y = max(view_h - map_pixel_h, min(0, target_offset_y))
    else:
        offset_x, offset_y = target_offset_x, target_offset_y

    if map_pixel_w >= view_w: game.true_camera_x = -offset_x - game.camera_pan_x
    if map_pixel_h >= view_h: game.true_camera_y = -offset_y - game.camera_pan_y

    screen_rect = pygame.Rect(-offset_x, -offset_y, view_w, view_h)
    game.offset_x, game.offset_y = offset_x, offset_y

    return view_w, view_h, zoom, final_w, final_h, offset_x, offset_y, screen_rect