import pygame
import sys
import math
import uuid
from core.data.config import *
import core.data.config
from core.systems.utils import get_player_facing_tile
from core.events.keyboard import handle_keyboard_events
from core.events.mouse import handle_mouse_down, handle_mouse_up, handle_mouse_motion
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS
from core.ui.helpers.keybinds import keybind_manager

keys_held = {}

def is_action_held(game, action, keys, mouse_buttons):
    """Safely checks continuous input across Keyboard, Mouse, and Joystick."""
    kb_val = keybind_manager.kb_binds.get(action)
    
    if kb_val is not None:
        if kb_val < 0:  # It's a mouse button
            btn_idx = (-kb_val) - 1
            if 0 <= btn_idx < len(mouse_buttons) and mouse_buttons[btn_idx]:
                return True
        else:  # It's a normal keyboard key
            try:
                if keys[kb_val]:
                    return True
            except IndexError:
                pass

    joy_val = keybind_manager.joy_binds.get(action)
    if joy_val is not None and getattr(game, 'joystick_handler', None) and game.joystick_handler.active_controller:
        try:
            if game.joystick_handler.active_controller.get_button(joy_val):
                return True
        except pygame.error:
            pass

    return False

def handle_movement(game):
    
    if game.player.action_timer > 0:
        game.player.vx = 0
        game.player.vy = 0
        game.player.is_running = False
        return
    
    if getattr(game, 'chat_active', False):
        game.player.vx = 0
        game.player.vy = 0
        game.player.is_running = False
        return

    for modal in game.modals:
        if 'instance' in modal:
            if getattr(modal['instance'], 'search_active', False):
                game.player.vx = 0
                game.player.vy = 0
                game.player.is_running = False
                return

    keys = pygame.key.get_pressed()
    mouse_buttons = pygame.mouse.get_pressed()

    
    
    # --- Dynamic Speed Calculation using XML Config ---
    base_move_speed = core.data.config.PLAYER_SPEED
    speed_multiplier = 1.0

    if game.player:
        for trait_id in game.player.traits:
            t_def = TRAIT_DEFINITIONS.get(trait_id)
            if t_def and 'config_modifiers' in t_def:
                mod = t_def['config_modifiers'].get('PLAYER_SPEED')
                if mod is not None:
                    speed_multiplier *= mod

    final_base_speed = base_move_speed * speed_multiplier
    current_speed = 0

    # ---> 1. FETCH JOYSTICK DATA <---
    joy_lx, joy_ly = 0, 0
    joy_aim = False
    
    if getattr(game, 'joystick_handler', None):
        joy_lx, joy_ly = game.joystick_handler.get_movement_axes()
        if hasattr(game.joystick_handler, 'is_rt_pressed'):
            joy_aim = game.joystick_handler.is_rt_pressed()

    # ---> 2. APPLY RUNNING AND AIMING <---
    is_running = (is_action_held(game, 'run', keys, mouse_buttons) or keys[pygame.K_RSHIFT])
    game.player.is_running = is_running

    mouse_pos = game._get_scaled_mouse_pos()
    is_over_ui = game.context_menu.get('active', False)
    if not is_over_ui:
        for modal in game.modals:
            if modal.get('rect') and modal['rect'].collidepoint(mouse_pos):
                is_over_ui = True
                break

    game.player.is_aiming = (is_action_held(game, 'aim', keys, mouse_buttons) or keys[pygame.K_RCTRL] or mouse_buttons[2] or joy_aim) and not is_over_ui

    if game.player.stamina <= 0:
        current_speed = final_base_speed / 3
    elif is_running:
        current_speed = final_base_speed
    elif game.player.is_aiming:
        current_speed = final_base_speed / 3.5
    else:
        current_speed = final_base_speed / 2

    # ---------------------------------------------------------
    # MOVEMENT LOGIC: SEPARATE KEYBOARD AND JOYSTICK MATH
    # ---------------------------------------------------------
    
    # 3. Read Keyboard Input
    kb_dx, kb_dy = 0, 0
    if is_action_held(game, 'move_up', keys, mouse_buttons): kb_dy -= 1
    if is_action_held(game, 'move_down', keys, mouse_buttons): kb_dy += 1
    if is_action_held(game, 'move_left', keys, mouse_buttons): kb_dx -= 1
    if is_action_held(game, 'move_right', keys, mouse_buttons): kb_dx += 1

    dx, dy = 0, 0

    # 4. Apply the correct Math based on the input device
    if kb_dx != 0 or kb_dy != 0:
        dx, dy = kb_dx, kb_dy
        if dx != 0 and dy != 0:
            dx /= math.sqrt(2)
            dy /= math.sqrt(2)
    else:
        dx, dy = joy_lx, joy_ly
        magnitude = math.sqrt(dx**2 + dy**2)
        if magnitude > 1.0:
            dx /= magnitude
            dy /= magnitude
        dx *= 1.25
        dy *= 1.25

    # 5. Smooth Facing Direction
    if abs(dx) > 0.15 or abs(dy) > 0.15:
        new_facing = None
        if abs(dx) > abs(dy): 
            new_facing = (1, 0) if dx > 0 else (-1, 0)
        else: 
            new_facing = (0, 1) if dy > 0 else (0, -1)
        
        if new_facing is not None and new_facing != game.player.facing_direction:
            game.player.facing_direction = new_facing

    # 6. TELL THE ANIMATION ENGINE WE ARE MOVING
    if dx != 0 or dy != 0:
        game.player.is_moving = True
    else:
        game.player.is_moving = False

    # 7. Apply Final Velocity
    game.player.vx = dx * current_speed
    game.player.vy = dy * current_speed


def handle_input(game):
    if getattr(game, 'joystick_handler', None):
        game.joystick_handler.update_cursor(game)

    mouse_pos = game._get_scaled_mouse_pos()

    # --- LONG PRESS TRACKER ---
    if not hasattr(game, '_touch_start_time'):
        game._touch_start_time = 0
        game._touch_start_pos = (0, 0)
        game._long_press_triggered = False

    mouse_pressed = pygame.mouse.get_pressed()
    if mouse_pressed[0] and getattr(game, 'joystick_handler', None) and not game._long_press_triggered:
        current_time = pygame.time.get_ticks()
        if current_time - game._touch_start_time > 500: 
            mx, my = mouse_pos
            dist = math.hypot(mx - game._touch_start_pos[0], my - game._touch_start_pos[1])
            if dist < 15 and not getattr(game, 'is_dragging', False):  
                game._long_press_triggered = True
                game.drag_candidate = None 
                v_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 3, 'pos': mouse_pos})
                handle_mouse_down(game, v_event, mouse_pos)
    # -------------------------------

    # FIXED: Continuous physics updating MUST run independently of the event queue!
    if game.game_state == 'PLAYING':
        handle_movement(game)

    for event in game.get_events():
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEWHEEL:
            is_over_modal = False
            topmost_modal = None

            for modal in reversed(game.modals):
                if modal.get('rect') and modal['rect'].collidepoint(mouse_pos):
                    is_over_modal = True
                    topmost_modal = modal
                    break
            
            if not is_over_modal:
                if not getattr(event, 'from_dpad', False):
                    if event.y > 0:
                        game.zoom_level += 0.1
                    elif event.y < 0:
                        game.zoom_level -= 0.1
                    game.zoom_level = max(core.data.config.FAR_ZOOM, min(game.zoom_level, core.data.config.NEAR_ZOOM))
            else:
                modal = topmost_modal
                if modal.get('type') == 'messages':
                    content_rect = modal.get('content_rect') 
                    if content_rect and content_rect.collidepoint(mouse_pos):
                        active_tab = modal.get('active_tab', 'All')
                        active_log = game.message_logs.get(active_tab, [])
                        
                        line_height = font_12.get_height() + 2
                        total_text_height = len(game.message_log) * line_height
                        visible_height = content_rect.height
                        max_scroll_offset = max(0, total_text_height - visible_height)
                        current_offset = modal.get('scroll_offset_y', 0)

                        scroll_amount = event.y * line_height * 3 
                        new_offset = current_offset - scroll_amount 
                        modal['scroll_offset_y'] = max(0, min(new_offset, max_scroll_offset))

                elif modal.get('type') == 'text':
                    content_rect = modal.get('content_rect')
                    if content_rect and content_rect.collidepoint(mouse_pos):
                        max_scroll_offset = modal.get('max_scroll_offset', 0) 
                        current_offset = modal.get('scroll_offset_y', 0)
                        
                        line_height = font_12.get_height() + 2
                        scroll_amount = event.y * line_height * 3 
                        new_offset = current_offset - scroll_amount 

                        modal['scroll_offset_y'] = max(0, min(new_offset, max_scroll_offset))

                elif modal.get('type') == 'mobile' and modal.get('active_tab') == 'Map':
                    map_area = modal.get('map_area_rect')
                    if map_area and map_area.collidepoint(mouse_pos):
                        current_zoom = modal.get('map_zoom', 4)
                        if event.y > 0: 
                            modal['map_zoom'] = min(16, current_zoom + 1)
                        elif event.y < 0: 
                            modal['map_zoom'] = max(2, current_zoom - 1)
                
                elif modal.get('type') == 'big_map':
                    map_area = modal.get('map_area_rect')
                    if map_area and map_area.collidepoint(mouse_pos):
                        current_zoom = modal.get('map_zoom', 6)
                        if event.y > 0: 
                            modal['map_zoom'] = min(32, current_zoom + 1)
                        elif event.y < 0: 
                            modal['map_zoom'] = max(2, current_zoom - 1)

        # --- UNIFIED ACTION DISPATCHER ---
        action_triggered = None
        if event.type == pygame.KEYDOWN:
            for action, val in keybind_manager.kb_binds.items():
                if val == event.key: action_triggered = action
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_val = -event.button
            for action, val in keybind_manager.kb_binds.items():
                if val == mouse_val: action_triggered = action
        elif event.type == pygame.JOYBUTTONDOWN:
            for action, val in keybind_manager.joy_binds.items():
                if val == getattr(event, 'button', None): action_triggered = action

        if game.game_state == 'PLAYING':
            handle_keyboard_events(game, event, action_triggered) 

            if event.type == pygame.MOUSEBUTTONDOWN:
                ignore = False
                if getattr(game, 'joystick_handler', None) and not getattr(event, 'v_btn', False):
                    if hasattr(event, 'pos') and hasattr(game.joystick_handler, 'is_over_controller'):
                        if game.joystick_handler.is_over_controller(event.pos):
                            ignore = True
                
                if not ignore:
                    game._touch_start_time = pygame.time.get_ticks()
                    game._touch_start_pos = getattr(event, 'pos', mouse_pos)
                    game._long_press_triggered = False
                    
                    handle_mouse_down(game, event, mouse_pos)
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                ignore = False
                if getattr(game, 'joystick_handler', None) and not getattr(event, 'v_btn', False):
                    if hasattr(event, 'pos') and hasattr(game.joystick_handler, 'is_over_controller'):
                        if game.joystick_handler.is_over_controller(event.pos):
                            ignore = True
                        
                if not ignore:
                    was_dragging = getattr(game, 'is_dragging', False)
                    origin = getattr(game, 'drag_origin', None)
                    dragged_item_ref = getattr(game, 'dragged_item', None)

                    handle_mouse_up(game, event, mouse_pos)

                    if was_dragging and not getattr(game, 'is_dragging', False):
                        if isinstance(origin, tuple) and len(origin) == 2:
                            origin_type, origin_index = origin
                            if origin_type in ('belt_hud', 'belt'):
                                game.player.belt[origin_index] = None 
                                if hasattr(dragged_item_ref, 'in_belt'):
                                    dragged_item_ref.in_belt = False
                    
            elif event.type == pygame.MOUSEMOTION:
                handle_mouse_motion(game, event, mouse_pos)
                
        elif game.game_state == 'PAUSED':
            handle_keyboard_events(game, event, action_triggered)