import pygame
import math
from core.data.config import *
import core.data.config
from core.entities.item.item import Item
from core.ui.helpers.main_menu import draw_menu
from core.ui.helpers.game_over import draw_game_over
from core.ui.inventory_modal import draw_inventory_modal, get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect, get_invcontainer_slot_rect, draw_belt_hud, get_belt_hud_slot_rect
from core.ui.container_modal import draw_container_view, get_container_slot_rect
from core.ui.status_modal import draw_status_modal
from core.ui.dropdown import draw_context_menu
from core.ui.nearby_modal import draw_nearby_modal
from core.ui.helpers.buttons import draw_inventory_button, draw_status_button, draw_nearby_button, draw_messages_button, draw_gear_button
from core.ui.tooltip import draw_tooltip
from core.ui.gear_modal import draw_gear_modal
from core.ui.messages_modal import draw_messages_modal
from core.ui.text_modal import draw_text_modal
from core.ui.mobile_modal import draw_mobile_modal
from core.ui.alerts import draw_player_alerts
from core.ui.vehicle_modal import draw_vehicle_modal

def draw_game(game):
    # Clear the main screen that holds the game and UI panels
    game.virtual_screen.fill(PANEL_COLOR)

    # --- World Rendering with Pixelated Zoom ---
    # 1. Create a temporary surface for the world view.
    zoom = game.zoom_level
    view_w = int(GAME_WIDTH / zoom)
    view_h = int(GAME_HEIGHT / zoom)


    world_view_surface = pygame.Surface((view_w, view_h))
    world_view_surface.fill(GAME_BG_COLOR) # Set the world background color

    # 2. Calculate a single camera offset to center the player.
    offset_x = view_w / 2 - game.player.rect.centerx
    offset_y = view_h / 2 - game.player.rect.centery

   

    light_mask = pygame.Surface((view_w, view_h))
    
    # Fill the mask with pitch black.
    light_mask.fill((12, 12, 12))
    ambient = int(game.world_time.current_ambient_light)

    light_texture = game.assets.get('light_texture')
    
    light_sources = []


    # [START MODIFICATION]
    mouse_pos = game._get_scaled_mouse_pos()

    # Check if mouse is over any UI modal to prevent aiming through it
    is_over_modal = False
    for modal in game.modals:
        if modal.get('rect') and modal['rect'].collidepoint(mouse_pos):
            is_over_modal = True
            break

    mouse_buttons = pygame.mouse.get_pressed()
    keys = pygame.key.get_pressed()
    
    # Only allow right-click aiming if NOT hovering over a modal
    right_click_aim = mouse_buttons[2] and not is_over_modal
    
    is_aiming = (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL] or right_click_aim)
    # [END MODIFICATION]

    # Panning Camera
    target_pan_x = 0
    target_pan_y = 0

    if is_aiming and game.player:
        # [START MODIFICATION]
        # 1. Get Mouse Position relative to the Player (Screen Center)
        # mouse_pos = game._get_scaled_mouse_pos() # Removed (moved up)
        
        # Player is conceptually at the center of the screen
        screen_center_x = GAME_WIDTH / 2
        screen_center_y = GAME_HEIGHT / 2
        
        dx = mouse_pos[0] - screen_center_x
        dy = mouse_pos[1] - screen_center_y
        
        # Distance in Screen Pixels
        mouse_dist_screen = math.hypot(dx, dy)
        
        # 2. Calculate Threshold (Fog of War Radius) in Screen Pixels
        # game.player_view_radius is in World Pixels.
        # On screen, World Pixels are multiplied by Zoom.
        pan_threshold_screen = game.player_view_radius * zoom
        
        # 3. Only pan if mouse is OUTSIDE the threshold
        if mouse_dist_screen > pan_threshold_screen:
            # Calculate max pan distance (e.g., 30% of the view dimension)
            pan_distance = min(view_w, view_h) * 0.3
            
            # Calculate offset based on aim angle
            # Note: -sin because screen Y is inverted vs standard math plane
            target_pan_x = math.cos(game.player.aim_angle) * pan_distance
            target_pan_y = -math.sin(game.player.aim_angle) * pan_distance
        # [END MODIFICATION]

    # Smoothly interpolate current pan towards target (Lerp)
    lerp_speed = 0.1
    game.camera_pan_x += (target_pan_x - game.camera_pan_x) * lerp_speed
    game.camera_pan_y += (target_pan_y - game.camera_pan_y) * lerp_speed

    # Calculate a single camera offset to center the player + Pan Offset.
    # We subtract the pan so the camera moves towards the aim direction relative to the player
    offset_x = view_w / 2 - game.player.rect.centerx - game.camera_pan_x
    offset_y = view_h / 2 - game.player.rect.centery - game.camera_pan_y



    if game.chat_active:
        chat_box_width = 400
        chat_box_height = 35
        chat_x = (GAME_WIDTH - chat_box_width) // 2
        chat_y = GAME_HEIGHT - 100
        
        chat_rect = pygame.Rect(chat_x, chat_y, chat_box_width, chat_box_height)
        
        # Background (Semi-transparent black)
        s = pygame.Surface((chat_box_width, chat_box_height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        game.virtual_screen.blit(s, (chat_x, chat_y))
        
        # Border
        pygame.draw.rect(game.virtual_screen, WHITE, chat_rect, 1)
        
        # Input Text
        if game.chat_input_text:
            txt_surf = font.render(game.chat_input_text, True, WHITE)
            game.virtual_screen.blit(txt_surf, (chat_rect.x + 5, chat_rect.y + 8))
            
            # Cursor (blinking)
            if int(pygame.time.get_ticks() / 500) % 2 == 0:
                cursor_x = chat_rect.x + 5 + txt_surf.get_width()
                pygame.draw.line(game.virtual_screen, WHITE, (cursor_x, chat_rect.y + 5), (cursor_x, chat_rect.bottom - 5))
        else:
            # Cursor at start if text is empty
            if int(pygame.time.get_ticks() / 500) % 2 == 0:
                pygame.draw.line(game.virtual_screen, WHITE, (chat_rect.x + 5, chat_rect.y + 5), (chat_rect.x + 5, chat_rect.bottom - 5))


    # 1. Add the player's base vision as a light source (Fog of War)
    if light_texture:
        try:
            radius_world_pixels = game.player_view_radius
            radius_view_pixels = int(radius_world_pixels / zoom) # or Zoom
            
            if radius_view_pixels > 0:
                player_vision_tex = pygame.transform.smoothscale(light_texture, (radius_view_pixels * PLAYER_FOW_RADIUS, radius_view_pixels * PLAYER_FOW_RADIUS))
                ambient_color = (ambient, ambient, ambient)
                player_vision_tex.fill(ambient_color, special_flags=pygame.BLEND_RGBA_MULT) 
                light_rect = player_vision_tex.get_rect()
                light_rect.center = (view_w / 2, view_h / 2)
                light_mask.blit(player_vision_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
        except Exception as e:
            print(f"Error drawing player vision: {e}")

    # 2. Get all dynamic light sources (lanterns)
    # (This section is correct)
    all_player_inventories = [game.player.belt, game.player.inventory]
    if game.player.backpack:
        all_player_inventories.append(game.player.backpack.inventory)
    if game.player.invcontainer and hasattr(game.player.invcontainer, 'inventory'):
        all_player_inventories.append(game.player.invcontainer.inventory)

    for inv in all_player_inventories:
        for item in inv:
            if getattr(item, 'state', 'off') == 'on':
                light_sources.append({'item': item, 'owner': 'player'})

    for item in game.items_on_ground:
         if getattr(item, 'state', 'off') == 'on':
            light_sources.append({'item': item, 'owner': 'ground'})
    
    # [NEW] Add Vehicle Lights - Checking both vehicles list AND containers
    if hasattr(game, 'vehicles'):
        for vehicle in game.vehicles:
            if getattr(vehicle, 'lights', 'off') == 'on' and vehicle.battery > 0:
                light_sources.append({'item': vehicle, 'owner': 'vehicle'})

    # Also check containers for vehicles (as vehicles behave as containers)
    for container in game.containers:
        if getattr(container, 'item_type', '') == 'vehicle':
             # Only add if not already added (avoid duplicates)
             if not any(ls['item'] == container for ls in light_sources):
                 if getattr(container, 'lights', 'off') == 'on' and container.battery > 0:
                     light_sources.append({'item': container, 'owner': 'vehicle'})

    if light_texture:
        # 3. Draw all dynamic lights (lanterns)
        # (This section is correct)
        for light_info in light_sources:
            light = light_info['item']
            
            # [FIX] Ensure we have a valid radius, using property for vehicles
            if hasattr(light, 'current_light_radius'):
                 radius_world_pixels = light.current_light_radius
            else:
                 radius_world_pixels = 0
            
            # Skip if 0 radius (lights off or no battery)
            if radius_world_pixels <= 0:
                continue
                
            radius_view_pixels = int(radius_world_pixels / zoom)
            
            if radius_view_pixels <= 0:
                continue

            try:
                scaled_light_tex = pygame.transform.scale(light_texture, (radius_view_pixels * 2, radius_view_pixels * 2))
                light_rect = scaled_light_tex.get_rect()
                
                if light_info['owner'] == 'player':
                    px_view = view_w / 2
                    py_view = view_h / 2
                    offset_lx = (game.player.facing_direction[0] * TILE_SIZE / zoom) * 0.75
                    offset_ly = (game.player.facing_direction[1] * TILE_SIZE / zoom) * 0.75
                    light_rect.center = (px_view + offset_lx, py_view + offset_ly)
                elif light_info['owner'] == 'vehicle':
                    # [NEW] Calculate center for vehicle
                    pos_x_view = light.rect.centerx + offset_x
                    pos_y_view = light.rect.centery + offset_y
                    light_rect.center = (pos_x_view, pos_y_view)
                else:
                    pos_x_view = light.rect.centerx + offset_x
                    pos_y_view = light.rect.centery + offset_y
                    light_rect.center = (pos_x_view, pos_y_view)
                
                light_mask.blit(scaled_light_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
            except Exception as e:
                print(f"Error drawing light: {e}")


    if light_texture:
        for light in game.map_lights:
            if not light.get('active', True): 
                continue
            # radius is already in pixels from map_loader
            radius_view_pixels = int(light['radius'])
            
            if radius_view_pixels <= 0: continue

            try:
                # Scale light texture
                scaled_light_tex = pygame.transform.scale(light_texture, (radius_view_pixels * 2, radius_view_pixels * 2))

                # Since we use BLEND_RGBA_ADD, we "dim" the light by multiplying it with a dark color.
                # 255 = 100% Intensity (Full White)
                # 100 = ~40% Intensity (Softer Light)
                # Adjust 'light_opacity' to change the strength (0 to 255)
                light_opacity = 80 
                scaled_light_tex.fill((light_opacity, light_opacity, light_opacity, 255), special_flags=pygame.BLEND_RGBA_MULT)

                light_rect = scaled_light_tex.get_rect()
                
                # Calculate screen position
                pos_x_view = light['rect'].centerx + offset_x
                pos_y_view = light['rect'].centery + offset_y
                
                light_rect.center = (pos_x_view, pos_y_view)
                
                # Blit to mask using ADD (adds the dimmed light values)
                light_mask.blit(scaled_light_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
            except Exception as e:
                pass


    # 3. Draw all world objects onto the temporary surface at 1:1 scale.
    
    # Draw Map Tiles (These are NOT distance-checked, they are lit by the mask)
    for image, rect in game.renderable_tiles:

        world_view_surface.blit(image, rect.move(offset_x, offset_y))
    
    for container in game.containers:
        dist = math.hypot(container.rect.centerx - game.player.rect.centerx, container.rect.centery - game.player.rect.centery)
        
        if dist > game.player_view_radius:
            continue
            
        draw_pos = container.rect.move(offset_x, offset_y)
        opacity = max(0, 255 * (1 - dist / game.player_view_radius))
        
        if getattr(container, 'image', None):
            try:
                temp_image = container.image.copy()
                temp_image.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
                world_view_surface.blit(temp_image, draw_pos)
            except Exception as e:
                print(f"Error drawing container image: {e}")
        else:
            # Fallback drawing
            color = getattr(container, 'color', WHITE)
            temp_surface = pygame.Surface(container.rect.size, pygame.SRCALPHA)
            temp_surface.fill((color[0], color[1], color[2], opacity))
            world_view_surface.blit(temp_surface, draw_pos)

    for item in game.items_on_ground:
        dist = math.hypot(item.rect.centerx - game.player.rect.centerx, item.rect.centery - game.player.rect.centery)
        
        if dist > game.player_view_radius:
            continue
            
        draw_pos = item.rect.move(offset_x, offset_y)
        opacity = max(0, 255 * (1 - dist / game.player_view_radius))
        
        if getattr(item, 'image', None):
            temp_image = item.image.copy()
            temp_image.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
            world_view_surface.blit(temp_image, draw_pos)
        else:
            color = getattr(item, 'color', WHITE)
            temp_surface = pygame.Surface(item.rect.size, pygame.SRCALPHA)
            temp_surface.fill((color[0], color[1], color[2], opacity))
            world_view_surface.blit(temp_surface, draw_pos)


    for p in game.projectiles:
        p.draw(world_view_surface, offset_x, offset_y)


    for zombie in game.zombies:
        # Check distance from player
        dist = math.hypot(zombie.rect.centerx - game.player.rect.centerx, zombie.rect.centery - game.player.rect.centery)
        
        # Don't draw zombie if it's outside the player's view radius
        if dist > game.player_view_radius:
            continue

        opacity = max(0, 255 * (1 - dist / game.player_view_radius))

        zombie.draw(world_view_surface, offset_x, offset_y, opacity)



    game.player.draw(world_view_surface, offset_x, offset_y, is_aiming)

    player_tile_x = game.player.rect.centerx // TILE_SIZE
    player_tile_y = game.player.rect.centery // TILE_SIZE
    # This hides a 3x3 grid (-1, 0, +1) centered on the player
    # roof_hide_radius = BASE_PLAYER_VIEW_RADIUS // TILE_SIZE

    roof_hide_radius = 3




    for image, rect, (tile_x, tile_y) in game.roof_tiles:
        dx = abs(tile_x - player_tile_x)
        dy = abs(tile_y - player_tile_y)
        
        # If the tile is within the radius, skip drawing it
        if dx <= roof_hide_radius and dy <= roof_hide_radius:
            continue
            
        world_view_surface.blit(image, rect.move(offset_x, offset_y))


    if game.hovered_container:
        hover_rect = game.hovered_container.rect.move(offset_x, offset_y)
        pygame.draw.rect(world_view_surface, YELLOW, hover_rect, 2)

    if game.hovered_interactable_tile_rect:
        hover_rect = game.hovered_interactable_tile_rect.move(offset_x, offset_y)
        pygame.draw.rect(world_view_surface, BLUE, hover_rect, 2)

    # Apply the light mask
    world_view_surface.blit(light_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # 4. Scale the entire world view surface up to the final game size.
    scaled_world = pygame.transform.scale(world_view_surface, (GAME_WIDTH, GAME_HEIGHT))

    # 5. Blit the scaled world onto the main virtual screen.
    game_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
    game.virtual_screen.blit(scaled_world, game_rect)

    # --- UI & Effects Rendering (Unaffected by Zoom) ---
    # Gun flash effect
    if game.player.gun_flash_timer > 0:
        center_x = GAME_OFFSET_X + GAME_WIDTH // 2
        center_y = GAME_HEIGHT // 2
        flash_distance = (TILE_SIZE * 1.4) * zoom 
        
        # Calculate new position based on aim angle
        # (Note: -sin because screen Y coordinates are inverted relative to math Y)
        flash_x = center_x + math.cos(game.player.aim_angle) * flash_distance
        flash_y = center_y - math.sin(game.player.aim_angle) * flash_distance
        
        # Smaller flash radius (was TILE_SIZE // 2)
        flash_radius = (TILE_SIZE // 5) * zoom 
        
        pygame.draw.circle(game.virtual_screen, WHITE, (int(flash_x), int(flash_y)), int(flash_radius))
        game.player.gun_flash_timer -= 1


    if game.player and game.player.chat_text and game.player.chat_timer > 0:
        # Player world pos on the view surface (unscaled)
        # view_w/2 - pan_x, view_h/2 - pan_y
        
        # Convert to screen coordinates
        player_view_x = (view_w / 2) - game.camera_pan_x
        player_view_y = (view_h / 2) - game.camera_pan_y
        
        screen_x = (player_view_x * zoom) + GAME_OFFSET_X
        screen_y = (player_view_y * zoom)
        
        # Bubble setup
        font_bubble = game.assets.get('font') or font
        text_surf = font_bubble.render(game.player.chat_text, True, BLACK)
        
        bubble_w = text_surf.get_width() + 20
        bubble_h = text_surf.get_height() + 10
        
        # Position above player head
        # 0.5 * TILE_SIZE * zoom centers it horizontally relative to the scaled tile
        bubble_x = screen_x - (bubble_w / 2) + (TILE_SIZE * zoom / 2)
        bubble_y = screen_y - bubble_h - 15 
        
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_w, bubble_h)
        
        # Draw Bubble
        pygame.draw.rect(game.virtual_screen, WHITE, bubble_rect, border_radius=8)
        
        # Triangle Pointer
        tri_center_x = screen_x + (TILE_SIZE * zoom / 2)
        tri_points = [
            (tri_center_x - 6, bubble_rect.bottom),
            (tri_center_x + 6, bubble_rect.bottom),
            (tri_center_x, bubble_rect.bottom + 8)
        ]
        pygame.draw.polygon(game.virtual_screen, WHITE, tri_points)
        
        # Text
        text_rect = text_surf.get_rect(center=bubble_rect.center)
        game.virtual_screen.blit(text_surf, text_rect)


    if game.game_state == 'PLAYING':
        draw_belt_hud(game.virtual_screen, game, game.player, game._get_scaled_mouse_pos())
        draw_player_alerts(game.virtual_screen, game.player)

    top_tooltip = None
    game.modal_buttons = []
    mouse_pos = game._get_scaled_mouse_pos()
    topmost_modal_id = game.modals[-1]['id'] if game.modals else None

    for modal in game.modals:
        

        modal['is_active'] = (modal['id'] == topmost_modal_id)
        
        if modal['type'] == 'status':
            buttons = draw_status_modal(game.virtual_screen, game.player, modal, game.assets, game.zombies_killed, mouse_pos)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'inventory':
            tooltip, *buttons = draw_inventory_modal(game.virtual_screen, game, game.player, modal, game.assets, game._get_scaled_mouse_pos())
            top_tooltip = tooltip or top_tooltip
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'gear':
            buttons = draw_gear_modal(game.virtual_screen, game, game.player, modal, game.assets, mouse_pos)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'container':
            buttons = draw_container_view(game.virtual_screen, game, modal['item'], modal, game.assets, mouse_pos)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'nearby':
            buttons = draw_nearby_modal(game.virtual_screen, game, modal, game.assets, mouse_pos)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'messages':
            result = draw_messages_modal(game.virtual_screen, game, modal, game.assets)
            if len(result) == 5:
                _, close_button, minimize_button, send_btn, input_box = result
                if send_btn: game.modal_buttons.append(send_btn)
                if input_box: game.modal_buttons.append(input_box)
            else:
                _, close_button, minimize_button = result # Fallback

            if close_button: game.modal_buttons.append(close_button)
            if minimize_button: game.modal_buttons.append(minimize_button)
        elif modal['type'] == 'text':
            _, close_button, minimize_button = draw_text_modal(game.virtual_screen, game, modal, game.assets)
            if close_button: game.modal_buttons.append(close_button)
            if minimize_button: game.modal_buttons.append(minimize_button)
        
        elif modal['type'] == 'mobile':
            buttons = draw_mobile_modal(game.virtual_screen, game, modal, game.assets)
            game.modal_buttons.extend(buttons)
        
        elif modal['type'] == 'vehicle':
            buttons = draw_vehicle_modal(game.virtual_screen, game, modal, game.assets, mouse_pos)
            game.modal_buttons.extend(buttons)
        

    game.status_button_rect = draw_status_button(game.virtual_screen)
    game.inventory_button_rect = draw_inventory_button(game.virtual_screen)
    game.nearby_button_rect = draw_nearby_button(game.virtual_screen)
    game.gear_button_rect = draw_gear_button(game.virtual_screen)
    game.messages_button_rect = draw_messages_button(game.virtual_screen)

    highlighted_rect = None
    highlighted_allowed = False
    if (game.is_dragging and game.dragged_item) or (game.drag_candidate and game.drag_candidate[0]):
        preview_item = game.dragged_item if game.is_dragging else game.drag_candidate[0]
        for modal in reversed(game.modals):
            if modal['type'] == 'inventory':


                if modal.get('active_tab', 'Inventory') == 'Inventory':
                    # Only check these slots if Inventory tab is active
                    for i in range(len(game.player.belt)):
                        slot = get_belt_slot_rect_in_modal(i, modal['position'])
                        if slot.collidepoint(game._get_scaled_mouse_pos()):
                            highlighted_rect = slot
                            highlighted_allowed = (preview_item.item_type != 'backpack')
                            break
                    if highlighted_rect:
                        break
                    for i in range(5):
                        slot = get_inventory_slot_rect(i, modal['position'])
                        if slot.collidepoint(game._get_scaled_mouse_pos()):
                            highlighted_rect = slot
                            highlighted_allowed = True
                            break
                    if highlighted_rect:
                        break
                    slot = get_backpack_slot_rect(modal['position'])
                    if slot.collidepoint(game._get_scaled_mouse_pos()):
                        highlighted_rect = slot
                        highlighted_allowed = (preview_item.item_type == 'backpack')
                        break
                        
                    slot = get_invcontainer_slot_rect(modal['position'])
                    if slot.collidepoint(game._get_scaled_mouse_pos()):
                        highlighted_rect = slot
                        dragged_type = getattr(preview_item, 'item_type', None)
                        dragged_ammo_type = getattr(preview_item, 'ammo_type', None)
                        highlighted_allowed = (
                            dragged_type == 'container' or
                            dragged_type == 'utility' or
                            (dragged_type == 'consumable' and dragged_ammo_type is not None)
                        )
                        break
                

            elif modal['type'] == 'gear':
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(game._get_scaled_mouse_pos()):
                            highlighted_rect = slot_rect
                            
                            # Check if the item belongs in this slot
                            item_slot = getattr(preview_item, 'slot', None)
                            if item_slot == 'hand': item_slot = 'hands' # Handle alias
                            
                            highlighted_allowed = (item_slot == slot_name)
                            break
                if highlighted_rect:
                    break

            elif modal['type'] == 'container':
                cont = modal['item']
                for i in range(min(cont.capacity, len(cont.inventory) + 16)):
                    slot = get_container_slot_rect(modal['position'], i)
                    if slot.collidepoint(game._get_scaled_mouse_pos()):
                        highlighted_rect = slot
                        highlighted_allowed = (len(cont.inventory) < cont.capacity) or (i < len(cont.inventory))
                        break
                if highlighted_rect:
                    break
            elif modal['type'] == 'messages':
                pass


        if not highlighted_rect:
            for i in range(5):
                slot = get_belt_hud_slot_rect(i)
                if slot.collidepoint(game._get_scaled_mouse_pos()):
                    highlighted_rect = slot
                    highlighted_allowed = (preview_item.item_type != 'backpack')
                    break


        if highlighted_rect:
            overlay = pygame.Surface((highlighted_rect.width, highlighted_rect.height), pygame.SRCALPHA)
            color = (50, 220, 50, 80) if highlighted_allowed else (220, 50, 50, 80)
            overlay.fill(color)
            game.virtual_screen.blit(overlay, highlighted_rect.topleft)
            pygame.draw.rect(game.virtual_screen, YELLOW if highlighted_allowed else RED, highlighted_rect, 2)

        if preview_item and getattr(preview_item, 'image', None):
            img = pygame.transform.scale(preview_item.image, (int(highlighted_rect.height * 0.9) if highlighted_rect else 40, int(highlighted_rect.height * 0.9) if highlighted_rect else 40))
            img_rect = img.get_rect()
            img_rect.topleft = (game._get_scaled_mouse_pos()[0] - game.drag_offset[0], game._get_scaled_mouse_pos()[1] - game.drag_offset[1])
            game.virtual_screen.blit(img, img_rect)
        elif preview_item:
            rect_w, rect_h = (int(highlighted_rect.width * 0.8), int(highlighted_rect.height * 0.8)) if highlighted_rect else (40, 40)
            preview_rect = pygame.Rect(game._get_scaled_mouse_pos()[0] - rect_w//2, game._get_scaled_mouse_pos()[1] - rect_h//2, rect_w, rect_h)
            s = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
            s.fill((*preview_item.color, 180))
            game.virtual_screen.blit(s, preview_rect.topleft)

    if top_tooltip:
        tip_rect = top_tooltip['rect']
        item = top_tooltip['item']
        frac = top_tooltip['frac']
        bar_color = top_tooltip['bar']

        tip_s = pygame.Surface((tip_rect.width, tip_rect.height), pygame.SRCALPHA)
        tip_s.fill((10, 10, 10, 220))
        game.virtual_screen.blit(tip_s, tip_rect.topleft)
        pygame.draw.rect(game.virtual_screen, WHITE, tip_rect, 1)

        name_surf = game.assets['font'].render(f"{item.name}", True, WHITE)
        type_surf = game.assets['font'].render(f"Type: {item.item_type}", True, GRAY)
        game.virtual_screen.blit(name_surf, (tip_rect.x + 8, tip_rect.y + 6))
        game.virtual_screen.blit(type_surf, (tip_rect.x + 8, tip_rect.y + 26))

        bar_x = tip_rect.x + 8
        bar_y = tip_rect.y + 42
        bar_w = tip_rect.width - 16
        bar_h = 10
        pygame.draw.rect(game.virtual_screen, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(max(0.0, min(1.0, frac)) * bar_w)
        pygame.draw.rect(game.virtual_screen, bar_color, (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(game.virtual_screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)

    if game.hovered_item and not game.context_menu['active']:
        draw_tooltip(game.virtual_screen, game.hovered_item, game._get_scaled_mouse_pos())

    if game.context_menu['active']:
        draw_context_menu(game.virtual_screen, game.context_menu, game._get_scaled_mouse_pos())

    #if is_aiming:
    #    pygame.mouse.set_cursor(game.assets.get('aim_cursor') or pygame.cursors.arrow)
    else:
        pygame.mouse.set_cursor(game.assets.get('custom_cursor') or pygame.cursors.arrow)


    if game.player.is_aiming:
        # [NEW] Draw Dynamic Reticle
        pygame.mouse.set_visible(False) # Hide default cursor
        
        reticle_img = game.assets.get('aim_reticle')
        if reticle_img:
            # Scale based on aim factor:
            # 1.0 (bad aim) -> 1.5x size
            # 0.0 (good aim) -> 0.5x size
            base_w = reticle_img.get_width()
            base_h = reticle_img.get_height()
            
            scale_mult = 1.5 + (game.player.current_aim_factor * 2.0)
            new_w = max(1, int(base_w * scale_mult))
            new_h = max(1, int(base_h * scale_mult))
            
            # Scale and Draw
            scaled_reticle = pygame.transform.scale(reticle_img, (new_w, new_h))
            rect = scaled_reticle.get_rect(center=game._get_scaled_mouse_pos())
            game.virtual_screen.blit(scaled_reticle, rect)
    else:
        # [NEW] Restore standard cursor
        pygame.mouse.set_visible(True)
        pygame.mouse.set_cursor(game.assets.get('custom_cursor') or pygame.cursors.arrow)


    # Set cursor
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL] or mouse_buttons[2]:
        pygame.mouse.set_cursor(game.assets.get('aim_cursor') or pygame.cursors.arrow)
    else:
        pygame.mouse.set_cursor(game.assets.get('custom_cursor') or pygame.cursors.arrow)