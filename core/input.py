import pygame
import sys
import math
import uuid
from core.data.config import *
import core.data.config
from core.systems.utils import get_player_facing_tile, get_targeted_interactable
from core.events.keyboard import handle_keyboard_events
from core.events.mouse import handle_mouse_down, handle_mouse_up, handle_mouse_motion
from core.map.world_layers import set_active_layer
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS

keys_held = {}
def handle_movement(game):
    if game.player.is_sleeping:
        return
    
    if game.player.action_timer > 0:
        game.player.vx = 0
        game.player.vy = 0
        game.player.is_running = False
        return
    
    if game.chat_active:
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

    # Turn off fast forward when movement keys are pressed
    if (keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]):
        if game.player and not game.player.is_sleeping:
            game.is_fast_forwarding = False

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
    joy_run, joy_aim = False, False
    
    # Check Hardware Joystick
    if getattr(game, 'joystick_handler', None):
        joy_lx, joy_ly = game.joystick_handler.get_movement_axes()
        joy_run, joy_aim = game.joystick_handler.get_action_states()

    # ---> 2. APPLY JOYSTICK STATES TO PLAYER <---
    is_running = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or joy_run)
    game.player.is_running = is_running

    # --- MODAL COLLISION CHECK TO DISARM AIMING ---
    mouse_pos = game._get_scaled_mouse_pos()
    is_over_ui = game.context_menu.get('active', False)
    if not is_over_ui:
        for modal in game.modals:
            if modal.get('rect') and modal['rect'].collidepoint(mouse_pos):
                is_over_ui = True
                break

    # Use Left CTRL, Right CTRL, Right Mouse Button (index 2) or Triggers to aim
    # Force disarm if the cursor is hovering over any Modal or the Context Menu is open
    game.player.is_aiming = (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL] or mouse_buttons[2] or joy_aim) and not is_over_ui

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
    if keys[pygame.K_w]: kb_dy -= 1
    if keys[pygame.K_s]: kb_dy += 1
    if keys[pygame.K_a]: kb_dx -= 1
    if keys[pygame.K_d]: kb_dx += 1

    dx, dy = 0, 0

    # 4. Apply the correct Math based on the input device
    if kb_dx != 0 or kb_dy != 0:
        # Keyboard was pressed: Apply the 1.414 division to prevent diagonal speed boosting
        dx, dy = kb_dx, kb_dy
        if dx != 0 and dy != 0:
            dx /= math.sqrt(2)
            dy /= math.sqrt(2)
    else:
        # Joystick is being used: The hardware already outputs a perfect circle
        dx, dy = joy_lx, joy_ly
        
        magnitude = math.sqrt(dx**2 + dy**2)
        if magnitude > 1.0:
            dx /= magnitude
            dy /= magnitude
            
        # BOOST JOYSTICK SPEED (25% faster than Keyboard)
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

    # --- NEW: LONG PRESS TRACKER ---
    # Initialize dynamic trackers if they don't exist yet
    if not hasattr(game, '_touch_start_time'):
        game._touch_start_time = 0
        game._touch_start_pos = (0, 0)
        game._long_press_triggered = False

    # Check for long-press continuously outside the Pygame event queue
    mouse_pressed = pygame.mouse.get_pressed()
    if mouse_pressed[0] and getattr(game, 'joystick_handler', None) and not game._long_press_triggered:
        current_time = pygame.time.get_ticks()
        # 500ms threshold for a long press
        if current_time - game._touch_start_time > 500: 
            # Calculate finger drift (jitter tolerance)
            mx, my = mouse_pos
            dist = math.hypot(mx - game._touch_start_pos[0], my - game._touch_start_pos[1])
            
            # FIX: Only trigger long-press if they haven't already started dragging an item
            if dist < 15 and not getattr(game, 'is_dragging', False):  
                game._long_press_triggered = True
                
                # Disarm the drag system safely so the item stays in the inventory
                game.drag_candidate = None 
                
                # Inject a synthetic Right-Click (Button 3) to trigger the context menu natively
                v_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 3, 'pos': mouse_pos})
                handle_mouse_down(game, v_event, mouse_pos)
    # -------------------------------


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
                if modal.get('type') == 'messages' and not modal.get('minimized', False):
                    content_rect = modal.get('content_rect') 
                    if content_rect and content_rect.collidepoint(mouse_pos):
                        active_tab = modal.get('active_tab', 'All')
                        active_log = game.message_logs.get(active_tab, [])
                        
                        line_height = font_14.get_height() + 2
                        total_text_height = len(game.message_log) * line_height
                        visible_height = content_rect.height
                        max_scroll_offset = max(0, total_text_height - visible_height)
                        current_offset = modal.get('scroll_offset_y', 0)

                        scroll_amount = event.y * line_height * 3 
                        new_offset = current_offset - scroll_amount 
                        modal['scroll_offset_y'] = max(0, min(new_offset, max_scroll_offset))

                elif modal.get('type') == 'text' and not modal.get('minimized', False):
                    content_rect = modal.get('content_rect')
                    if content_rect and content_rect.collidepoint(mouse_pos):
                        max_scroll_offset = modal.get('max_scroll_offset', 0) 
                        current_offset = modal.get('scroll_offset_y', 0)
                        
                        line_height = font_14.get_height() + 2
                        scroll_amount = event.y * line_height * 3 
                        new_offset = current_offset - scroll_amount 

                        modal['scroll_offset_y'] = max(0, min(new_offset, max_scroll_offset))

                elif modal.get('type') == 'mobile' and not modal.get('minimized', False) and modal.get('active_tab') == 'Map':
                    map_area = modal.get('map_area_rect')
                    if map_area and map_area.collidepoint(mouse_pos):
                        current_zoom = modal.get('map_zoom', 4)
                        if event.y > 0: 
                            modal['map_zoom'] = min(16, current_zoom + 1)
                        elif event.y < 0: 
                            modal['map_zoom'] = max(2, current_zoom - 1)
                
                elif modal.get('type') == 'big_map' and not modal.get('minimized', False):
                    map_area = modal.get('map_area_rect')
                    if map_area and map_area.collidepoint(mouse_pos):
                        current_zoom = modal.get('map_zoom', 6)
                        if event.y > 0: 
                            modal['map_zoom'] = min(32, current_zoom + 1)
                        elif event.y < 0: 
                            modal['map_zoom'] = max(2, current_zoom - 1)


        if game.game_state == 'PLAYING':
            handle_keyboard_events(game, event) 

            if event.type == pygame.KEYDOWN:
                if not game.chat_active:
                    if game.player.vehicle and event.key == pygame.K_SPACE:
                        game.player.vehicle.brake(brake_force=0.6, game=game)
                        return

                    if event.key == pygame.K_e:
                        if game.player.vehicle:
                            game.player.exit_vehicle(game)
                        else:
                            target = get_targeted_interactable(game)
                            if target:
                                if target['type'] == 'npc':
                                    found_npc = target['entity']
                                    if not any(m['type'] == 'npc_dialog' for m in game.modals):
                                        pos_x = (GAME_WIDTH // 2) - (NPC_DIALOG_MODAL_WIDTH // 2)
                                        pos_y = (GAME_HEIGHT // 2) - (NPC_DIALOG_MODAL_HEIGHT // 2)
                                        game.modals.append({
                                            'id': str(uuid.uuid4()),
                                            'type': 'npc_dialog',
                                            'npc': found_npc,
                                            'dialogs': found_npc.get_dialog_options(), 
                                            'active_dialog_index': -1,                 
                                            'position': (pos_x, pos_y),
                                            'rect': pygame.Rect(pos_x, pos_y, NPC_DIALOG_MODAL_WIDTH, NPC_DIALOG_MODAL_HEIGHT),
                                            'is_dragging': False,
                                            'drag_offset': (0, 0)
                                        })
                                elif target['type'] == 'vehicle':
                                    found_vehicle = target['entity']
                                    game.player.enter_vehicle(found_vehicle, game)
                                    if not any(m['type'] == 'vehicle' for m in game.modals):
                                        default_pos = (GAME_WIDTH // 2 - 200, GAME_HEIGHT // 2 + 120)
                                        pos = game.last_modal_positions.get('vehicle', default_pos) if hasattr(game, 'last_modal_positions') else default_pos
                                        
                                        new_modal = {
                                            'id': str(uuid.uuid4()),
                                            'type': 'vehicle',
                                            'vehicle': found_vehicle,
                                            'position': pos,
                                            'rect': pygame.Rect(pos[0], pos[1], VEHICLE_MODAL_WIDTH, VEHICLE_MODAL_HEIGHT),
                                            'is_dragging': False, 
                                            'drag_offset': (0, 0), 
                                            'active_tab': 'Info'
                                        }
                                        game.modals.append(new_modal)
                                elif target['type'] == 'stair':
                                    px, py = target['entity']
                                    current_tile_char = game.map_data[py][px]
                                    current_tile_def = game.tile_manager.definitions.get(current_tile_char)
                                    if current_tile_def and current_tile_def.get('is_stair'):
                                        target_layer = current_tile_def.get('target_layer')
                                        if game.player.layer_switch_cooldown <= 0:
                                            if set_active_layer(game, target_layer):
                                                game.player.layer_switch_cooldown = 30
                                elif target['type'] == 'tile':
                                    tx, ty = target['entity']
                                    tile = game.map_manager.get_tile_at(tx, ty)
                                    if tile and tile.get('is_statable') and tile.get('type') == 'maptile':
                                        game.map_manager.toggle_door_state(tx, ty)
                                    elif tile and tile.get('is_stair'):
                                        target_layer = tile.get('target_layer')
                                        if game.player.layer_switch_cooldown <= 0:
                                            if set_active_layer(game, target_layer):
                                                game.player.layer_switch_cooldown = 30
                                            return 

            handle_movement(game)
            if event.type == pygame.MOUSEBUTTONDOWN:
                ignore = False
                if getattr(game, 'joystick_handler', None) and not getattr(event, 'v_btn', False):
                    # FIX: Check if the handler actually has the 'is_over_controller' method
                    if hasattr(event, 'pos') and hasattr(game.joystick_handler, 'is_over_controller'):
                        if game.joystick_handler.is_over_controller(event.pos):
                            ignore = True
                
                if not ignore:
                    # --- NEW: START LONG PRESS TIMER ---
                    game._touch_start_time = pygame.time.get_ticks()
                    game._touch_start_pos = getattr(event, 'pos', mouse_pos)
                    game._long_press_triggered = False
                    # -----------------------------------
                    
                    handle_mouse_down(game, event, mouse_pos)
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                ignore = False
                if getattr(game, 'joystick_handler', None) and not getattr(event, 'v_btn', False):
                    # FIX: Check if the handler actually has the 'is_over_controller' method
                    if hasattr(event, 'pos') and hasattr(game.joystick_handler, 'is_over_controller'):
                        if game.joystick_handler.is_over_controller(event.pos):
                            ignore = True
                        
                if not ignore:
                    # FIX: REMOVED the destructive 'game.is_dragging = False' override here
                    # Letting the native drag handler cleanly resolve and bounce the item back!
                    handle_mouse_up(game, event, mouse_pos)
                    
            elif event.type == pygame.MOUSEMOTION:
                handle_mouse_motion(game, event, mouse_pos)
        elif game.game_state == 'PAUSED':
            handle_keyboard_events(game, event)