import pygame
import sys
import math
from data.config import *
from core.events.keyboard import handle_keyboard_events
from core.events.mouse import handle_mouse_down, handle_mouse_up, handle_mouse_motion

def handle_movement(game):
    keys = pygame.key.get_pressed()
    current_speed = 0

    is_running = (keys[pygame.K_LALT] or keys[pygame.K_RALT])
    game.player.is_running = is_running

    if game.player.stamina <= 0:
        # Exhausted speed
        current_speed = PLAYER_SPEED / 3
    elif is_running:
        # Running speed
        current_speed = PLAYER_SPEED
    else:
        # Normal walk speed
        current_speed = PLAYER_SPEED / 2


    dx, dy = 0, 0
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        dy -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        dy += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        dx -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        dx += 1


    if dx > 0: 
        game.player.facing_direction = (1, 0)
    elif dx < 0: 
        game.player.facing_direction = (-1, 0)
    elif dy > 0: 
        game.player.facing_direction = (0, 1)
    elif dy < 0: 
        game.player.facing_direction = (0, -1)

    # Normalize for diagonal movement
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
            if not any(modal.get('rect') and modal['rect'].collidepoint(mouse_pos) for modal in game.modals):
                 # Only zoom if mouse is NOT over any modal
                if event.y > 0:
                    game.zoom_level += 0.1
                elif event.y < 0:
                    game.zoom_level -= 0.1
                game.zoom_level = max(FAR_ZOOM, min(game.zoom_level, NEAR_ZOOM))
            else:
                # Mouse is over a modal, check if it's the messages modal content area
                for modal in reversed(game.modals): # Check topmost modal first
                    if modal.get('type') == 'messages' and not modal.get('minimized', False):
                        content_rect = modal.get('content_rect') # Get rect calculated in draw step
                        if content_rect and content_rect.collidepoint(mouse_pos):
                            # --- Calculate scroll limits within the handler ---
                            line_height = font_small.get_height() + 2
                            total_text_height = len(game.message_log) * line_height
                            visible_height = content_rect.height
                            max_scroll_offset = max(0, total_text_height - visible_height)
                            current_offset = modal.get('scroll_offset_y', 0)

                            # Adjust scroll offset (event.y is typically 1 or -1)
                            scroll_amount = event.y * line_height * 3 # Scroll 3 lines at a time
                            new_offset = current_offset - scroll_amount # Subtract because positive event.y is scroll up

                            # Clamp the new offset
                            modal['scroll_offset_y'] = max(0, min(new_offset, max_scroll_offset))
                            break # Found the modal, stop checking others

                    elif modal.get('type') == 'text' and not modal.get('minimized', False):
                        content_rect = modal.get('content_rect')

                    #if content_rect and content_rect.collidepoint(mouse_pos):
                    #    # Read the max_scroll from the modal (set during draw)
                    #    max_scroll_offset = modal.get('max_scroll_offset', 0)
                    #    current_offset = modal.get('scroll_offset_y', 0)
                    #
                    #    # Use the same line height as the draw function
                    #    line_height = font_small.get_height() + 2
                    #    scroll_amount = event.y * line_height * 3 # Scroll 3 lines
                    #
                    #    new_offset = current_offset - scroll_amount
                    #    modal['scroll_offset_y'] = max(0, min(new_offset, max_scroll_offset))
                    #    break 

                    elif modal.get('type') == 'mobile' and not modal.get('minimized', False) and modal.get('active_tab') == 'Map':
                        
                        map_area = modal.get('map_area_rect') # Rect stored by map_tab.py
                        if map_area and map_area.collidepoint(mouse_pos):
                            current_zoom = modal.get('map_zoom', 4)
                            if event.y > 0: # Scroll up
                                modal['map_zoom'] = min(16, current_zoom + 1) # Zoom in, max 16px
                            elif event.y < 0: # Scroll down
                                modal['map_zoom'] = max(2, current_zoom - 1) # Zoom out, min 2px
                            break # Handled scroll for this modal

        if event.type == pygame.VIDEORESIZE:
            game.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

        #mouse_pos = game._get_scaled_mouse_pos()

        if game.game_state == 'PLAYING':
            # Handle keyboard events more generally
            handle_keyboard_events(game, event) # Call existing handler for other keys

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e: # Interaction key
                    player_facing_grid_x, player_facing_grid_y = game.get_player_facing_tile()
                    if player_facing_grid_x is not None and player_facing_grid_y is not None:
                        tile = game.map_manager.get_tile_at(player_facing_grid_x, player_facing_grid_y)
                        if tile and tile.get('is_statable') and tile.get('type') == 'maptile':
                            # Assuming 'maptile' type for doors
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