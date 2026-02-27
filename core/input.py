import pygame
import sys
import math
import uuid
from core.data.config import *
import core.data.config
from core.systems.utils import get_player_facing_tile
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
    if (keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d] or
        keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]):
        if game.player and not game.player.is_sleeping:
            game.is_fast_forwarding = False

    mouse_buttons = pygame.mouse.get_pressed()
    
    # --- [MODIFIED] Dynamic Speed Calculation using XML Config ---
    base_move_speed = core.data.config.PLAYER_SPEED
    speed_multiplier = 1.0

    # Iterate over player traits and apply 'PLAYER_SPEED' modifiers defined in XML
    if game.player:
        for trait_id in game.player.traits:
            t_def = TRAIT_DEFINITIONS.get(trait_id)
            if t_def and 'config_modifiers' in t_def:
                # Look for a modifier specifically for PLAYER_SPEED
                mod = t_def['config_modifiers'].get('PLAYER_SPEED')
                if mod is not None:
                    speed_multiplier *= mod

    final_base_speed = base_move_speed * speed_multiplier
    current_speed = 0

    is_running = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
    game.player.is_running = is_running

    # Use Left CTRL, Right CTRL, or Right Mouse Button (index 2) to aim
    game.player.is_aiming = (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL] or mouse_buttons[2])

    if game.player.stamina <= 0:
        current_speed = final_base_speed / 3
    elif is_running:
        current_speed = final_base_speed
    elif game.player.is_aiming:
        current_speed = final_base_speed / 3.5
    else:
        current_speed = final_base_speed / 2

    dx, dy = 0, 0
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        dy -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        dy += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        dx -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        dx += 1

    new_facing = None
    if dx > 0: 
        new_facing = (1, 0)
    elif dx < 0: 
        new_facing = (-1, 0)
    elif dy > 0: 
        new_facing = (0, 1)
    elif dy < 0: 
        new_facing = (0, -1)
    
    if new_facing is not None and new_facing != game.player.facing_direction:
        game.player.facing_direction = new_facing

    if dx != 0 and dy != 0:
        dx /= math.sqrt(2)
        dy /= math.sqrt(2)

    game.player.vx = dx * current_speed
    game.player.vy = dy * current_speed

def handle_input(game):

    mouse_pos = game._get_scaled_mouse_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEWHEEL:
            # Check zoom first (global behavior)
            # Optimization: Check if mouse is colliding with any visible modal
            is_over_modal = False
            topmost_modal = None
            
            # Find topmost modal under mouse
            for modal in reversed(game.modals):
                if modal.get('rect') and modal['rect'].collidepoint(mouse_pos):
                    is_over_modal = True
                    topmost_modal = modal
                    break
            
            if not is_over_modal:
                 # Only zoom if mouse is NOT over any modal
                if event.y > 0:
                    game.zoom_level += 0.1
                elif event.y < 0:
                    game.zoom_level -= 0.1
                game.zoom_level = max(core.data.config.FAR_ZOOM, min(game.zoom_level, core.data.config.NEAR_ZOOM))
            else:
                # Handle scrolling for the topmost modal ONLY
                modal = topmost_modal
                if modal.get('type') == 'messages' and not modal.get('minimized', False):
                    content_rect = modal.get('content_rect') 
                    if content_rect and content_rect.collidepoint(mouse_pos):
                        active_tab = modal.get('active_tab', 'All')
                        active_log = game.message_logs.get(active_tab, [])
                        
                        line_height = font_small.get_height() + 2
                        total_text_height = len(game.message_log) * line_height # Note: logic might need active_log check
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
                        
                        line_height = font_small.get_height() + 2
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

        #if event.type == pygame.VIDEORESIZE:
        #    self.game_screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

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
                            # 1. Check for nearby NPC
                            found_npc = None
                            for npc in game.npcs:
                                dist = math.hypot(game.player.rect.centerx - npc.rect.centerx, game.player.rect.centery - npc.rect.centery)
                                if dist < TILE_SIZE * 1.5:
                                    found_npc = npc
                                    break
                            
                            if found_npc:
                                if not any(m['type'] == 'npc_dialog' for m in game.modals):
                                    pos_x = (GAME_WIDTH // 2) - (NPC_DIALOG_MODAL_WIDTH // 2)
                                    pos_y = (GAME_HEIGHT // 2) - (NPC_DIALOG_MODAL_HEIGHT // 2)
                                    game.modals.append({
                                        'id': str(uuid.uuid4()),
                                        'type': 'npc_dialog',
                                        'npc': found_npc,
                                        'dialogs': found_npc.get_dialog_options(), # Added dialog options
                                        'active_dialog_index': -1,                 # Added active dialog index
                                        'position': (pos_x, pos_y),
                                        'rect': pygame.Rect(pos_x, pos_y, NPC_DIALOG_MODAL_WIDTH, NPC_DIALOG_MODAL_HEIGHT),
                                        'minimized': False,
                                        'is_dragging': False,
                                        'drag_offset': (0, 0)
                                    })
                                return
                            
                            # 2. Check for nearby Vehicle
                            found_vehicle = None
                            for obj in game.containers:
                                if getattr(obj, 'item_type', '') == 'vehicle':
                                    dist = math.hypot(game.player.rect.centerx - obj.rect.centerx, game.player.rect.centery - obj.rect.centery)
                                    if dist < TILE_SIZE * 2.0:
                                        found_vehicle = obj
                                        break 
                            
                            if found_vehicle:
                                # Enter vehicle
                                game.player.enter_vehicle(found_vehicle, game)
                                
                                # Append vehicle options modal
                                if not any(m['type'] == 'vehicle' for m in game.modals):
                                    default_pos = (GAME_WIDTH // 2 - 200, GAME_HEIGHT // 2 - 200)
                                    pos = game.last_modal_positions.get('vehicle', default_pos) if hasattr(game, 'last_modal_positions') else default_pos
                                    
                                    new_modal = {
                                        'id': str(uuid.uuid4()),
                                        'type': 'vehicle',
                                        'vehicle': found_vehicle,
                                        'position': pos,
                                        'rect': pygame.Rect(pos[0], pos[1], VEHICLE_MODAL_WIDTH, VEHICLE_MODAL_HEIGHT),
                                        'minimized': False,
                                        'is_dragging': False, 
                                        'drag_offset': (0, 0), 
                                        'active_tab': 'Info'
                                    }
                                    game.modals.append(new_modal)
                                return

                            # 3. Check Stairs / Doors
                            from core.systems.utils import get_player_facing_tile
                            px, py = int(game.player.rect.centerx // TILE_SIZE), int(game.player.rect.centery // TILE_SIZE)

                            if 0 <= py < len(game.map_data) and 0 <= px < len(game.map_data[0]):
                                current_tile_char = game.map_data[py][px]
                                current_tile_def = game.tile_manager.definitions.get(current_tile_char)

                                if current_tile_def and current_tile_def.get('is_stair'):
                                    target_layer = current_tile_def.get('target_layer')

                                    if game.player.layer_switch_cooldown <= 0:
                                        if set_active_layer(game, target_layer):
                                            game.player.layer_switch_cooldown = 30
                                            return 

                            player_facing_grid_x, player_facing_grid_y = get_player_facing_tile(game)
                            if player_facing_grid_x is not None and player_facing_grid_y is not None:
                                tile = game.map_manager.get_tile_at(player_facing_grid_x, player_facing_grid_y)
                                if tile and tile.get('is_statable') and tile.get('type') == 'maptile':
                                    game.map_manager.toggle_door_state(player_facing_grid_x, player_facing_grid_y)

            handle_movement(game)
            if event.type == pygame.MOUSEBUTTONDOWN:
                handle_mouse_down(game, event, mouse_pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                handle_mouse_up(game, event, mouse_pos)
            elif event.type == pygame.MOUSEMOTION:
                handle_mouse_motion(game, event, mouse_pos)
        elif game.game_state == 'PAUSED':
            handle_keyboard_events(game, event)