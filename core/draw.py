import pygame
import math
import random
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

    # World Rendering with Pixelated Zoom ---
    zoom = game.zoom_level
    view_w = int(GAME_WIDTH / zoom)
    view_h = int(GAME_HEIGHT / zoom)

    # ---------------------------------------------------------
    # 1. CALCULATE CAMERA PANNING HERE (BEFORE DRAWING)
    # ---------------------------------------------------------
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

    # Panning Camera Target Calculation
    target_pan_x = 0
    target_pan_y = 0

    if is_aiming and game.player:
        # Player is conceptually at the center of the screen
        screen_center_x = GAME_WIDTH / 2
        screen_center_y = GAME_HEIGHT / 2
        
        dx = mouse_pos[0] - screen_center_x
        dy = mouse_pos[1] - screen_center_y
        
        # Distance in Screen Pixels
        mouse_dist_screen = math.hypot(dx, dy)
        
        # Threshold (Fog of War Radius) in Screen Pixels
        pan_threshold_screen = game.player_view_radius
        
        # Only pan if mouse is OUTSIDE the threshold
        if mouse_dist_screen > pan_threshold_screen:
            # Calculate max pan distance (e.g., 30% of the view dimension)
            pan_distance = min(view_w, view_h) * 0.5
            
            # Calculate offset based on aim angle
            # Note: -sin because screen Y is inverted vs standard math plane
            target_pan_x = math.cos(game.player.aim_angle) * pan_distance
            target_pan_y = -math.sin(game.player.aim_angle) * pan_distance

    # Smoothly interpolate current pan towards target (Lerp)
    lerp_speed = 0.1
    game.camera_pan_x += (target_pan_x - game.camera_pan_x) * lerp_speed
    game.camera_pan_y += (target_pan_y - game.camera_pan_y) * lerp_speed

    # We subtract the pan so the camera moves towards the aim direction
    offset_x = view_w / 2 - game.player.rect.centerx - game.camera_pan_x
    offset_y = view_h / 2 - game.player.rect.centery - game.camera_pan_y

    # FRUSTUM CULLING OPTIMIZATION: Define the world-space viewport rectangle (screen_rect)
    # This rect is in world coordinates and represents what is currently visible.
    screen_rect = pygame.Rect(-offset_x, -offset_y, view_w, view_h)

    world_view_surface = pygame.Surface((view_w, view_h))

    # >>> START TILE RENDERING OPTIMIZATION (Tile Surface Caching) <<<

    # 1. Check/Rebuild Cache if the map chunks have changed (tiles_dirty) or a dynamic tile state has toggled.
    if not hasattr(game, '_tile_cache_surface'):
        game._tile_cache_surface = None
    
    # Check for full map chunk changes OR single dynamic tile changes (e.g., doors)
    dynamic_update_needed = getattr(game, 'dynamic_tiles_dirty', False)
    
    if getattr(game, 'tiles_dirty', True) or dynamic_update_needed: 
        if game.renderable_tiles:
            # Calculate the bounding box of all tiles to size the cache surface
            min_x = min(rect.x for _, rect in game.renderable_tiles)
            min_y = min(rect.y for _, rect in game.renderable_tiles)
            max_x = max(rect.right for _, rect in game.renderable_tiles)
            max_y = max(rect.bottom for _, rect in game.renderable_tiles)

            cache_w = max_x - min_x
            cache_h = max_y - min_y
            
            # Store the world coordinate of the cache's top-left corner
            game._tile_cache_world_origin = (min_x, min_y)

            # Create the cache surface. Use .convert() for speed.
            game._tile_cache_surface = pygame.Surface((cache_w, cache_h)).convert()
            game._tile_cache_surface.fill(PANEL_COLOR) 

            # Calculate offset for drawing onto the cache surface
            cache_offset_x = -min_x
            cache_offset_y = -min_y

            # Perform the expensive blit operations ONCE (when dirty)
            for image, rect in game.renderable_tiles:
                game._tile_cache_surface.blit(image, rect.move(cache_offset_x, cache_offset_y))
            
            # Mark the cache clean
            game.tiles_dirty = False
            if dynamic_update_needed:
                # Clear the dynamic flag after the rebuild
                game.dynamic_tiles_dirty = False 
        else:
            # Handle empty map case
            game._tile_cache_surface = pygame.Surface((1, 1)).convert()
            game._tile_cache_world_origin = (0, 0)
            game.tiles_dirty = False
            if dynamic_update_needed:
                game.dynamic_tiles_dirty = False
    
    # 2. Per-frame Optimized Blit from Cache
    if game._tile_cache_surface:
        cache_origin_x, cache_origin_y = game._tile_cache_world_origin
        
        # Calculate the source rectangle (the 'slice' of the map cache to display)
        source_x = screen_rect.x - cache_origin_x
        source_y = screen_rect.y - cache_origin_y
        source_w = view_w
        source_h = view_h
        source_rect_on_cache = pygame.Rect(source_x, source_y, source_w, source_h)
        
        # Blit the slice onto the world_view_surface at position (0, 0)
        world_view_surface.blit(game._tile_cache_surface, (0, 0), source_rect_on_cache)

    # >>> END TILE RENDERING OPTIMIZATION (Tile Surface Caching) <<<


    light_mask = pygame.Surface((view_w, view_h))
    
    # Fill the mask with pitch black.
    light_mask.fill((30, 30, 30))
    ambient = int(game.world_time.current_ambient_light)

    light_texture = game.assets.get('light_texture')
    
    light_sources = []

    # 1. Add the player's base vision as a light source (Fog of War)
    if light_texture:
        try:
            radius_world_pixels = game.player_view_radius
            radius_view_pixels = int(radius_world_pixels / zoom) # or Zoom
            
            if radius_view_pixels > 0:
                player_vision_tex = pygame.transform.smoothscale(light_texture, (radius_view_pixels * 2, radius_view_pixels * 2))
                ambient_color = (ambient, ambient, ambient)
                player_vision_tex.fill(ambient_color, special_flags=pygame.BLEND_RGBA_MULT) 
                light_rect = player_vision_tex.get_rect()
                light_rect.center = (view_w / 2, view_h / 2)
                # [FIX] Offset the fog of war slightly if panning, to keep player centered in the "light"
                # Actually, since view_w/2 is center of SCREEN, and offset_x handles the world movement,
                # we just need to draw this at the center of the surface, which is (view_w/2, view_h/2).
                # Wait! If we pan, the player is NOT at the center of the screen anymore.
                # The player is at: game.player.rect.centerx + offset_x
                
                player_screen_x = game.player.rect.centerx + offset_x
                player_screen_y = game.player.rect.centery + offset_y
                light_rect.center = (player_screen_x, player_screen_y)

                light_mask.blit(player_vision_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
        except Exception as e:
            print(f"Error drawing player vision: {e}")

    # 2. Get all dynamic light sources (lanterns)
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
    
    if hasattr(game, 'vehicles'):
        for vehicle in game.vehicles:
            if getattr(vehicle, 'lights', 'off') == 'on' and vehicle.battery > 0:
                light_sources.append({'item': vehicle, 'owner': 'vehicle'})

    for container in game.containers:
        if getattr(container, 'item_type', '') == 'vehicle':
             if not any(ls['item'] == container for ls in light_sources):
                 if getattr(container, 'lights', 'off') == 'on' and container.battery > 0:
                     light_sources.append({'item': container, 'owner': 'vehicle'})

    if light_texture:
        # 3. Draw all dynamic lights (lanterns)
        for light_info in light_sources:
            light = light_info['item']
            
            if hasattr(light, 'current_light_radius'):
                 radius_world_pixels = light.current_light_radius
            else:
                 radius_world_pixels = 0
            
            if radius_world_pixels <= 0: continue
                
            radius_view_pixels = int(radius_world_pixels / zoom)
            if radius_view_pixels <= 0: continue

            try:
                scaled_light_tex = pygame.transform.scale(light_texture, (radius_view_pixels * 2, radius_view_pixels * 2))
                light_rect = scaled_light_tex.get_rect()
                
                if light_info['owner'] == 'player':
                    # Calculate player screen pos dynamicially
                    px_view = game.player.rect.centerx + offset_x
                    py_view = game.player.rect.centery + offset_y
                    
                    offset_lx = (game.player.facing_direction[0] * TILE_SIZE / zoom) * 0.75
                    offset_ly = (game.player.facing_direction[1] * TILE_SIZE / zoom) * 0.75
                    light_rect.center = (px_view + offset_lx, py_view + offset_ly)
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
            
            # FRUSTUM CULLING ADDED FOR STATIC MAP LIGHTS
            if 'rect' in light and not screen_rect.colliderect(light['rect']):
                continue
            
            radius_view_pixels = int(light['radius'])
            if radius_view_pixels <= 0: continue

            try:
                scaled_light_tex = pygame.transform.scale(light_texture, (radius_view_pixels * 2, radius_view_pixels * 2))
                light_opacity = 80 
                scaled_light_tex.fill((light_opacity, light_opacity, light_opacity, 255), special_flags=pygame.BLEND_RGBA_MULT)

                light_rect = scaled_light_tex.get_rect()
                pos_x_view = light['rect'].centerx + offset_x
                pos_y_view = light['rect'].centery + offset_y
                light_rect.center = (pos_x_view, pos_y_view)
                light_mask.blit(scaled_light_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
            except Exception as e:
                pass

    # 3. Draw all world objects onto the temporary surface at 1:1 scale.
    
    for container in game.containers:
        if not screen_rect.colliderect(container.rect): continue # Frustum culling added
        dist = math.hypot(container.rect.centerx - game.player.rect.centerx, container.rect.centery - game.player.rect.centery)
        
        if dist > game.player_view_radius: continue
        
        draw_pos = container.rect.move(offset_x, offset_y)
        
        # Calculate fade factor (1.0 close to player, 0.0 at edge of view_radius)
        fade_factor = max(0.0, 1.0 - (dist / game.player_view_radius))
        # Optional "blurry" effect: use power to make the fade faster near the edge
        fade_factor = fade_factor ** 0.5 
        
        opacity = int(255 * fade_factor)
        
        if getattr(container, 'image', None):
            try:
                temp_image = container.image.copy()
                temp_image.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
                world_view_surface.blit(temp_image, draw_pos)
            except Exception as e: pass
        else:
            color = getattr(container, 'color', WHITE)
            temp_surface = pygame.Surface(container.rect.size, pygame.SRCALPHA)
            temp_surface.fill((color[0], color[1], color[2], opacity))
            world_view_surface.blit(temp_surface, draw_pos)

    for item in game.items_on_ground:
        if not screen_rect.colliderect(item.rect): continue # Frustum culling added
        dist = math.hypot(item.rect.centerx - game.player.rect.centerx, item.rect.centery - game.player.rect.centery)
        
        if dist > game.player_view_radius: continue
        
        draw_pos = item.rect.move(offset_x, offset_y)
        
        # Calculate fade factor
        fade_factor = max(0.0, 1.0 - (dist / game.player_view_radius))
        opacity = int(255 * fade_factor)
        
        if getattr(item, 'image', None):
            temp_image = item.image.copy()
            safe_opacity = max(0, min(255, opacity)) # Clamp (max/min check is good practice)
            temp_image.fill((255, 255, 255, safe_opacity), special_flags=pygame.BLEND_RGBA_MULT)
            world_view_surface.blit(temp_image, draw_pos)
        else:
            color = getattr(item, 'color', WHITE)
            temp_surface = pygame.Surface(item.rect.size, pygame.SRCALPHA)
            temp_surface.fill((color[0], color[1], color[2], opacity))
            world_view_surface.blit(temp_surface, draw_pos)

    for p in game.projectiles:
        if screen_rect.colliderect(p.rect): # Frustum culling added
            p.draw(world_view_surface, offset_x, offset_y)

    for zombie in game.zombies:
        if not screen_rect.colliderect(zombie.rect): continue # Frustum culling added
        dist = math.hypot(zombie.rect.centerx - game.player.rect.centerx, zombie.rect.centery - game.player.rect.centery)
        
        if dist > game.player_view_radius: continue
        
        # Calculate fade factor
        fade_factor = max(0.0, 1.0 - (dist / game.player_view_radius))
        opacity = int(255 * fade_factor)
        
        zombie.draw(world_view_surface, offset_x, offset_y, opacity)

    game.player.draw(world_view_surface, offset_x, offset_y, is_aiming)


    # --- NEW: Draw Persistent Blood Stains (Decals) ---
    if hasattr(game, 'blood_stains'):
        for stain in game.blood_stains:
            # Stains are drawn first (under temporary effects)
            stain_x = int(stain['pos'][0] + offset_x)
            stain_y = int(stain['pos'][1] + offset_y)
            stain_size = stain['size']
            stain_color = stain.get('color', (139, 0, 0))
            
            # Draw a simple circular decal
            # Multiple of these small circles placed along a line create the trail effect.
            pygame.draw.circle(world_view_surface, stain_color, 
                               (stain_x, stain_y), 
                               stain_size // 2)

    # --- Draw Hit Splashes (Blood Puff/Trail Effect) ---
    SPLASH_COLOR = (139, 0, 0) # Dark Red
    current_time = pygame.time.get_ticks()
    
    for splash in game.splashes:
        time_elapsed = current_time - splash['time']
        
        # Calculate fade factor (1.0 at start, 0.0 at end)
        fade_factor = max(0.0, 1.0 - (time_elapsed / splash['duration']))
        
        # Base opacity (starts darker, fades out)
        base_opacity = int(255 * fade_factor)
        
        # Calculate screen position in world view (the impact spot on the floor)
        impact_x = splash['pos'][0] + offset_x
        impact_y = splash['pos'][1] + offset_y

        # Draw more particles for a dramatic puff
        num_particles = 15 # Increased particle count for more splatter
        for i in range(num_particles):
            
            # Spread widens as it fades (simulating velocity)
            offset_dist = (1.0 - fade_factor) * (TILE_SIZE / 3) 
            
            # Add random variation to spread distance
            offset_dist *= random.uniform(0.7, 1.3)
            
            # Random angle for direction of splatter
            angle = math.radians(i * (360 / num_particles) + random.randint(-45, 45)) # Increased angle variance
            
            draw_x = impact_x + (math.cos(angle) * offset_dist)
            draw_y = impact_y + (math.sin(angle) * offset_dist)

            # Calculate individual particle size (starts at splash['radius'], shrinks slightly)
            particle_radius = int(splash['radius'] * random.uniform(1.0, 1.5) * (fade_factor * 0.5 + 0.5)) 
            
            if particle_radius > 0:
                # Create a temporary surface for the particle to control its opacity
                particle_surf = pygame.Surface((particle_radius * 2, particle_radius * 2), pygame.SRCALPHA)
                
                # Darken the color slightly as it trails away
                trail_color = (int(SPLASH_COLOR[0] * fade_factor), int(SPLASH_COLOR[1] * fade_factor), int(SPLASH_COLOR[2] * fade_factor), base_opacity)
                
                # Draw the particle with the dynamic color/opacity
                pygame.draw.circle(particle_surf, trail_color, 
                                   (particle_radius, particle_radius), 
                                   particle_radius)

                world_view_surface.blit(particle_surf, (int(draw_x - particle_radius), int(draw_y - particle_radius)))

    player_tile_x = game.player.rect.centerx // TILE_SIZE
    player_tile_y = game.player.rect.centery // TILE_SIZE
    roof_hide_radius = 3

    for image, rect, (tile_x, tile_y) in game.roof_tiles:
        if not screen_rect.colliderect(rect): continue # Frustum culling added
        dx = abs(tile_x - player_tile_x)
        dy = abs(tile_y - player_tile_y)
        if dx <= roof_hide_radius and dy <= roof_hide_radius: continue
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
    if game.player.gun_flash_timer > 0:
        center_x = GAME_OFFSET_X + GAME_WIDTH // 2
        center_y = GAME_HEIGHT // 2
        flash_distance = (TILE_SIZE * 1.4) * zoom 
        
        flash_x = center_x + math.cos(game.player.aim_angle) * flash_distance
        flash_y = center_y - math.sin(game.player.aim_angle) * flash_distance
        
        flash_radius = (TILE_SIZE // 5) * zoom 
        pygame.draw.circle(game.virtual_screen, WHITE, (int(flash_x), int(flash_y)), int(flash_radius))
        game.player.gun_flash_timer -= 1


    if game.player and game.player.chat_text and game.player.chat_timer > 0:
        player_view_x = game.player.rect.centerx + offset_x
        player_view_y = game.player.rect.centery + offset_y
        
        screen_x = (player_view_x * zoom) + GAME_OFFSET_X
        screen_y = (player_view_y * zoom)
        
        font_bubble = game.assets.get('font') or font
        text_surf = font_bubble.render(game.player.chat_text, True, BLACK)
        
        bubble_w = text_surf.get_width() + 20
        bubble_h = text_surf.get_height() + 10
        
        bubble_x = screen_x - (bubble_w / 2) + (TILE_SIZE * zoom / 2)
        bubble_y = screen_y - bubble_h - 15 
        
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_w, bubble_h)
        
        pygame.draw.rect(game.virtual_screen, WHITE, bubble_rect, border_radius=8)
        
        tri_center_x = screen_x + (TILE_SIZE * zoom / 2)
        tri_points = [
            (tri_center_x - 6, bubble_rect.bottom),
            (tri_center_x + 6, bubble_rect.bottom),
            (tri_center_x, bubble_rect.bottom + 8)
        ]
        pygame.draw.polygon(game.virtual_screen, WHITE, tri_points)
        
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
                _, close_button, minimize_button = result
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
                    for i in range(len(game.player.belt)):
                        slot = get_belt_slot_rect_in_modal(i, modal['position'])
                        if slot.collidepoint(game._get_scaled_mouse_pos()):
                            highlighted_rect = slot
                            highlighted_allowed = (preview_item.item_type != 'backpack')
                            break
                    if highlighted_rect: break
                    for i in range(5):
                        slot = get_inventory_slot_rect(i, modal['position'])
                        if slot.collidepoint(game._get_scaled_mouse_pos()):
                            highlighted_rect = slot
                            highlighted_allowed = True
                            break
                    if highlighted_rect: break
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
                            item_slot = getattr(preview_item, 'slot', None)
                            if item_slot == 'hand': item_slot = 'hands'
                            highlighted_allowed = (item_slot == slot_name)
                            break
                if highlighted_rect: break
            elif modal['type'] == 'container':
                cont = modal['item']
                for i in range(min(cont.capacity, len(cont.inventory) + 16)):
                    slot = get_container_slot_rect(modal['position'], i)
                    if slot.collidepoint(game._get_scaled_mouse_pos()):
                        highlighted_rect = slot
                        highlighted_allowed = (len(cont.inventory) < cont.capacity) or (i < len(cont.inventory))
                        break
                if highlighted_rect: break
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

    if game.player.is_aiming:
        pygame.mouse.set_visible(False) 
        reticle_img = game.assets.get('aim_reticle')
        if reticle_img:
            base_w = reticle_img.get_width()
            base_h = reticle_img.get_height()
            scale_mult = 1.5 + (game.player.current_aim_factor * 2.0)
            new_w = max(1, int(base_w * scale_mult))
            new_h = max(1, int(base_h * scale_mult))
            scaled_reticle = pygame.transform.scale(reticle_img, (new_w, new_h))
            rect = scaled_reticle.get_rect(center=game._get_scaled_mouse_pos())
            game.virtual_screen.blit(scaled_reticle, rect)
    else:
        pygame.mouse.set_visible(True)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL] or mouse_buttons[2]:
             pygame.mouse.set_cursor(game.assets.get('aim_cursor') or pygame.cursors.arrow)
        else:
             pygame.mouse.set_cursor(game.assets.get('custom_cursor') or pygame.cursors.arrow)