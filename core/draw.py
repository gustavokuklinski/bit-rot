import pygame
import math
import random
import time
from core.data.config import *
import core.data.config
from core.entities.item.item import Item
from core.ui.helpers.main_menu import draw_menu
from core.ui.helpers.game_over import draw_game_over
from core.ui.inventory_modal import draw_inventory_modal, get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect, draw_belt_hud, get_belt_hud_slot_rect
from core.ui.container_modal import draw_container_view, get_container_slot_rect
from core.ui.status_modal import draw_status_modal
from core.ui.dropdown import draw_context_menu
from core.ui.nearby_modal import draw_nearby_modal
from core.ui.helpers.buttons import draw_inventory_button, draw_status_button,draw_forward_button,draw_pause_button, draw_nearby_button, draw_messages_button, draw_gear_button, draw_crafting_button
from core.ui.tooltip import draw_tooltip
from core.ui.gear_modal import draw_gear_modal
from core.ui.messages_modal import draw_messages_modal
from core.ui.text_modal import draw_text_modal
from core.ui.mobile_modal import draw_mobile_modal
from core.ui.alerts import draw_player_alerts
from core.ui.vehicle_modal import draw_vehicle_modal
from core.ui.crafting_modal import CraftingModal
from core.ui.map_tab import draw_big_map_modal
from core.ui.npc_dialog_modal import draw_npc_dialog_modal

def draw_game(game):
    # Clear the main screen that holds the game and UI panels
    game.virtual_screen.fill(PANEL_COLOR)

    # World Rendering with Pixelated Zoom ---
    zoom = game.zoom_level
    view_w = int(GAME_WIDTH / zoom)
    view_h = int(GAME_HEIGHT / zoom)

    # [OPTIMIZATION] Cache the world view surface to avoid expensive reallocation every frame
    if not hasattr(game, 'cached_view_surface') or \
       game.cached_view_surface.get_width() != view_w or \
       game.cached_view_surface.get_height() != view_h:
        game.cached_view_surface = pygame.Surface((view_w, view_h))
        # Also create a scratch surface for particles to avoid allocs in loops
        game.particle_scratch = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    
    world_view_surface = game.cached_view_surface
    world_view_surface.fill((20, 20, 20)) 

    # ---------------------------------------------------------
    # 1. CALCULATE CAMERA PANNING
    # ---------------------------------------------------------
    mouse_pos = game._get_scaled_mouse_pos()

    # Check if mouse is over any UI modal
    is_over_modal = False
    for modal in game.modals:
        if modal.get('rect') and modal['rect'].collidepoint(mouse_pos):
            is_over_modal = True
            break

    mouse_buttons = pygame.mouse.get_pressed()
    keys = pygame.key.get_pressed()
    #right_click_aim = mouse_buttons[2] and not is_over_modal
    is_aiming = (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL])

    # Panning Camera Target Calculation
    target_pan_x = 0
    target_pan_y = 0

    if is_aiming and game.player:
        edge_margin = 80 # Pixels from the edge to trigger pan
        
        at_left_edge = mouse_pos[0] < edge_margin
        at_right_edge = mouse_pos[0] > GAME_WIDTH - edge_margin
        at_top_edge = mouse_pos[1] < edge_margin
        at_bottom_edge = mouse_pos[1] > GAME_HEIGHT - edge_margin

        if at_left_edge or at_right_edge or at_top_edge or at_bottom_edge:
            pan_distance = min(view_w, view_h) * 0.5
            target_pan_x = math.cos(game.player.aim_angle) * pan_distance
            target_pan_y = -math.sin(game.player.aim_angle) * pan_distance

    lerp_speed = 0.1
    game.camera_pan_x += (target_pan_x - game.camera_pan_x) * lerp_speed
    game.camera_pan_y += (target_pan_y - game.camera_pan_y) * lerp_speed

    offset_x = view_w / 2 - game.player.rect.centerx - game.camera_pan_x
    offset_y = view_h / 2 - game.player.rect.centery - game.camera_pan_y

    screen_rect = pygame.Rect(-offset_x, -offset_y, view_w, view_h)

    # ---------------------------------------------------------
    # 2. OPTIMIZED GRID RENDERING (VIEWPORT CULLING)
    # ---------------------------------------------------------
    # Instead of blitting a giant cached surface, we iterate only the visible tiles.
    
    tile_size = TILE_SIZE
    
    # Calculate visible grid bounds
    # We want visible WorldX from 0 to view_w (relative to screen)
    # WorldCoord = ScreenCoord - offset
    min_world_x = -offset_x
    min_world_y = -offset_y
    max_world_x = -offset_x + view_w
    max_world_y = -offset_y + view_h
    
    # Add buffer of 2 tiles to avoid popping at edges
    buffer_tiles = 2
    min_grid_x = max(0, int(min_world_x // tile_size) - buffer_tiles)
    min_grid_y = max(0, int(min_world_y // tile_size) - buffer_tiles)
    
    # Map Dimensions
    map_h = len(game.map_data) if game.map_data else 0
    map_w = len(game.map_data[0]) if map_h > 0 else 0
    
    max_grid_x = min(map_w, int(max_world_x // tile_size) + 1 + buffer_tiles)
    max_grid_y = min(map_h, int(max_world_y // tile_size) + 1 + buffer_tiles)
    
    ground_layer = getattr(game, 'ground_data', None)
    base_layer = getattr(game, 'map_data', None)
    roof_layer = getattr(game, 'roof_data', None)
    
    tm = game.tile_manager
    shaking_tiles = game.map_manager.shaking_tiles
    
    current_time = time.time()
    tiles_to_remove = []

    player_tile_x = game.player.rect.centerx // tile_size
    player_tile_y = game.player.rect.centery // tile_size
    roof_hide_radius = 3

    # Main Render Loop
    for gy in range(min_grid_y, max_grid_y):
        for gx in range(min_grid_x, max_grid_x):
            screen_px = int(gx * tile_size + offset_x)
            screen_py = int(gy * tile_size + offset_y)
            
            # --- Ground Layer ---
            if ground_layer:
                g_key = ground_layer[gy][gx]
                if g_key and g_key != ' ':
                    g_def = tm.definitions.get(g_key)
                    if g_def:
                        world_view_surface.blit(g_def['image'], (screen_px, screen_py))

            # --- Base Layer (Walls, Trees, Objects) ---
            if base_layer:
                b_key = base_layer[gy][gx]
                if b_key and b_key != ' ':
                     b_def = tm.definitions.get(b_key)
                     if b_def:
                         # Handle Shaking
                         draw_x, draw_y = screen_px, screen_py
                         if (gx, gy) in shaking_tiles:
                             if current_time - shaking_tiles[(gx, gy)] > 0.2:
                                 tiles_to_remove.append((gx, gy))
                             else:
                                 draw_x += random.randint(-2, 2)
                                 draw_y += random.randint(-2, 2)
                         
                         world_view_surface.blit(b_def['image'], (draw_x, draw_y))
            
            # --- Roof Layer ---
            

    # Clean up shaking tiles
    for k in tiles_to_remove:
        if k in game.map_manager.shaking_tiles:
            del game.map_manager.shaking_tiles[k]


    # --- [MOVED] Draw Persistent Blood Stains (Decals) ---
    if hasattr(game, 'blood_stains'):
        min_view_x = -offset_x - 100
        max_view_x = -offset_x + view_w + 100
        min_view_y = -offset_y - 100
        max_view_y = -offset_y + view_h + 100

        for stain in game.blood_stains:
            stain_wx, stain_wy = stain['pos']
            if not (min_view_x < stain_wx < max_view_x and min_view_y < stain_wy < max_view_y):
                continue

            stain_x = int(stain_wx + offset_x)
            stain_y = int(stain_wy + offset_y)
            pygame.draw.circle(world_view_surface, stain.get('color', (139, 0, 0)), (stain_x, stain_y), stain['size'] // 2)

    # [OPTIMIZATION] Low-Resolution Lighting
    low_res_w = view_w // 2
    low_res_h = view_h // 2
    light_mask_low = pygame.Surface((low_res_w, low_res_h))
    
    light_mask_low.fill((30, 30, 30))
    ambient = int(game.world_time.current_ambient_light)

    light_texture = game.assets.get('light_texture')
    light_sources = []

    # 1. Player Vision
    if light_texture:
        try:
            radius_world_pixels = game.player_view_radius
            radius_view_pixels = int(radius_world_pixels / zoom)
            
            if radius_view_pixels > 0:
                radius_low = radius_view_pixels // 2
                
                player_vision_tex = pygame.transform.scale(light_texture, (radius_low * 2, radius_low * 2))
                ambient_color = (ambient, ambient, ambient)
                player_vision_tex.fill(ambient_color, special_flags=pygame.BLEND_RGBA_MULT) 
                
                light_rect = player_vision_tex.get_rect()
                
                p_screen_x = (game.player.rect.centerx + offset_x) / 2
                p_screen_y = (game.player.rect.centery + offset_y) / 2
                
                light_rect.center = (p_screen_x, p_screen_y)
                light_mask_low.blit(player_vision_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
        except Exception as e:
            print(f"Error drawing player vision: {e}")

    # 2. Collect Light Sources
    all_player_inventories = [game.player.belt, game.player.inventory]
    if game.player.backpack: all_player_inventories.append(game.player.backpack.inventory)
    

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

    # 3. Draw Lights (Low Res)
    if light_texture:
        for light_info in light_sources:
            light = light_info['item']
            radius_world = getattr(light, 'current_light_radius', 0)
            if radius_world <= 0: continue
            
            if light_info['owner'] == 'player':
                 lx, ly = game.player.rect.centerx, game.player.rect.centery
            else:
                 lx, ly = light.rect.centerx, light.rect.centery
            
            # Culling Check
            if not screen_rect.inflate(radius_world*2, radius_world*2).collidepoint(lx, ly):
                continue
            
            radius_low = int((radius_world / zoom) / 2)
            if radius_low <= 0: continue

            try:
                scaled_light_tex = pygame.transform.scale(light_texture, (radius_low * 2, radius_low * 2))
                light_rect = scaled_light_tex.get_rect()
                
                if light_info['owner'] == 'player':
                    px_view = (game.player.rect.centerx + offset_x) / 2
                    py_view = (game.player.rect.centery + offset_y) / 2
                    offset_lx = (game.player.facing_direction[0] * TILE_SIZE / zoom) * 0.375 
                    offset_ly = (game.player.facing_direction[1] * TILE_SIZE / zoom) * 0.375
                    light_rect.center = (px_view + offset_lx, py_view + offset_ly)
                else:
                    pos_x_view = (light.rect.centerx + offset_x) / 2
                    pos_y_view = (light.rect.centery + offset_y) / 2
                    light_rect.center = (pos_x_view, pos_y_view)
                
                light_mask_low.blit(scaled_light_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
            except Exception: pass

        for light in game.map_lights:
            if not light.get('active', True): continue
            if 'rect' in light and not screen_rect.colliderect(light['rect']): continue
            
            radius_low = int(light['radius'] / 2)
            if radius_low <= 0: continue

            try:
                scaled_light_tex = pygame.transform.scale(light_texture, (radius_low * 2, radius_low * 2))
                light_opacity = 80 
                scaled_light_tex.fill((light_opacity, light_opacity, light_opacity, 255), special_flags=pygame.BLEND_RGBA_MULT)
                light_rect = scaled_light_tex.get_rect()
                
                pos_x_view = (light['rect'].centerx + offset_x) / 2
                pos_y_view = (light['rect'].centery + offset_y) / 2
                light_rect.center = (pos_x_view, pos_y_view)
                light_mask_low.blit(scaled_light_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
            except Exception: pass
    
    for container in game.containers:
        if not screen_rect.colliderect(container.rect): continue
        draw_pos = container.rect.move(offset_x, offset_y)
        if getattr(container, 'image', None):
             world_view_surface.blit(container.image, draw_pos)
        else:
             color = getattr(container, 'color', WHITE)
             pygame.draw.rect(world_view_surface, color, draw_pos)

    for item in game.items_on_ground:
        if not screen_rect.colliderect(item.rect): continue
        draw_pos = item.rect.move(offset_x, offset_y)
        if getattr(item, 'image', None):
            world_view_surface.blit(item.image, draw_pos)
        else:
            pygame.draw.rect(world_view_surface, getattr(item, 'color', WHITE), draw_pos)

    for p in game.projectiles:
        if screen_rect.colliderect(p.rect):
            p.draw(world_view_surface, offset_x, offset_y)

    for zombie in game.zombies:
        if not screen_rect.colliderect(zombie.rect): continue
        zombie.draw(world_view_surface, offset_x, offset_y, 255) 

    for npc in game.npcs:
        if not screen_rect.colliderect(npc.rect): continue
        npc.draw(world_view_surface, offset_x, offset_y, 255)

    game.player.draw(world_view_surface, offset_x, offset_y, is_aiming)

    player_tile_x = game.player.rect.centerx // tile_size
    player_tile_y = game.player.rect.centery // tile_size
    roof_hide_radius = 3

    if roof_layer:
        for gy in range(min_grid_y, max_grid_y):
            for gx in range(min_grid_x, max_grid_x):
                r_key = roof_layer[gy][gx]
                if r_key and r_key != ' ':
                    # Hide Roof Logic
                    dx = abs(gx - player_tile_x)
                    dy = abs(gy - player_tile_y)
                    if not (dx <= roof_hide_radius and dy <= roof_hide_radius):
                         r_def = tm.definitions.get(r_key)
                         if r_def:
                             screen_px = int(gx * tile_size + offset_x)
                             screen_py = int(gy * tile_size + offset_y)
                             world_view_surface.blit(r_def['image'], (screen_px, screen_py))

    SPLASH_COLOR = (139, 0, 0)
    current_time_ms = pygame.time.get_ticks()
    
    # Pre-configure scratch surface
    scratch = game.particle_scratch 
    
    for splash in game.splashes:
        time_elapsed = current_time_ms - splash['time']
        if time_elapsed > splash['duration']: continue
        
        fade_factor = max(0.0, 1.0 - (time_elapsed / splash['duration']))
        base_opacity = int(255 * fade_factor)
        impact_x = splash['pos'][0] + offset_x
        impact_y = splash['pos'][1] + offset_y

        num_particles = 10 
        for i in range(num_particles):
            offset_dist = (1.0 - fade_factor) * (TILE_SIZE / 3) * random.uniform(0.7, 1.3)
            angle = math.radians(i * (360 / num_particles) + random.randint(-45, 45))
            
            draw_x = impact_x + (math.cos(angle) * offset_dist)
            draw_y = impact_y + (math.sin(angle) * offset_dist)
            
            p_radius = int(splash['radius'] * random.uniform(1.0, 1.5) * (fade_factor * 0.5 + 0.5))
            if p_radius <= 0: continue
            
            scratch_rect = pygame.Rect(0, 0, p_radius*2, p_radius*2)
            scratch.fill((0,0,0,0), scratch_rect)
            
            trail_color = (int(SPLASH_COLOR[0] * fade_factor), int(SPLASH_COLOR[1] * fade_factor), int(SPLASH_COLOR[2] * fade_factor), base_opacity)
            
            pygame.draw.circle(scratch, trail_color, (p_radius, p_radius), p_radius)
            world_view_surface.blit(scratch, (int(draw_x - p_radius), int(draw_y - p_radius)), scratch_rect)

    # Roof rendering is now integrated into the main grid loop for better performance

    if game.hovered_container:
        hover_rect = game.hovered_container.rect.move(offset_x, offset_y)
        pygame.draw.rect(world_view_surface, YELLOW, hover_rect, 2)

    world_mouse_pos = game.screen_to_world(mouse_pos)
    for npc in game.npcs:
        # Optimization: Only check NPCs currently within the view
        if not screen_rect.colliderect(npc.rect): 
            continue
            
        if npc.rect.collidepoint(world_mouse_pos):
            # Check friendliness: Green if friendly, Red if hostile
            is_friendly = getattr(npc, 'is_friendly', True)
            color = (0, 255, 0) if is_friendly else (255, 0, 0)
            
            hover_rect = npc.rect.move(offset_x, offset_y)
            pygame.draw.rect(world_view_surface, color, hover_rect, 2)
            break # Only highlight one at a time
    

    for zombie in game.zombies:
        # Optimization: Only check zombies currently within the view
        if not screen_rect.colliderect(zombie.rect): 
            continue
        
        if zombie.rect.collidepoint(world_mouse_pos):
            hover_rect = zombie.rect.move(offset_x, offset_y)
            # Draw Purple outline for Zombies
            pygame.draw.rect(world_view_surface, (128, 0, 128), hover_rect, 2)
            break

    if game.hovered_interactable_tile_rect:
        hover_rect = game.hovered_interactable_tile_rect.move(offset_x, offset_y)
        pygame.draw.rect(world_view_surface, BLUE, hover_rect, 2)

    light_mask_upscaled = pygame.transform.scale(light_mask_low, (view_w, view_h))
    world_view_surface.blit(light_mask_upscaled, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # Final Scale to Screen
    scaled_world = pygame.transform.scale(world_view_surface, (GAME_WIDTH, GAME_HEIGHT))
    game_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
    game.virtual_screen.blit(scaled_world, game_rect)

    if game.player and game.player.is_sleeping:
        # Cover the whole virtual screen with black
        game.virtual_screen.fill((0, 0, 0))
        
        font = game.assets.get('font') or pygame.font.Font(None, 30)
        text_surf = font.render("Sweet Dreams. Press Space to Wake up.", True, (255, 255, 255))
        
        text_rect = text_surf.get_rect(center=(GAME_WIDTH // 2 + GAME_OFFSET_X // 2, GAME_HEIGHT // 2))
        
        # Adjust for the sidebar offset if necessary, usually centering on the whole screen is fine
        # creating a true center:
        text_rect.center = (game.virtual_screen.get_width() // 2, game.virtual_screen.get_height() // 2)
        
        game.virtual_screen.blit(text_surf, text_rect)

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
        # [CHANGED] Capture alert tooltip proxy instead of drawing immediately
        alert_tooltip = draw_player_alerts(game.virtual_screen, game.player)
        if alert_tooltip:
             game.hovered_item = alert_tooltip

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
        elif modal['type'] == 'big_map':
            buttons = draw_big_map_modal(game.virtual_screen, game, modal, game.assets)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'npc_dialog':
            buttons = draw_npc_dialog_modal(game.virtual_screen, modal, game)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'crafting':
            # Instantiate Logic on the fly (or you could store instance in modal dict)
            if 'instance' not in modal:
                modal['instance'] = CraftingModal(game.virtual_screen, modal, game.assets, game)
            
            # Ensure surface is up to date
            modal['instance'].surface = game.virtual_screen
            _, *buttons = modal['instance'].draw()
            game.modal_buttons.extend(buttons)
        
    game.pause_button_rect = draw_pause_button(game.virtual_screen)
    game.forward_button_rect = draw_forward_button(game.virtual_screen)
    game.status_button_rect = draw_status_button(game.virtual_screen)
    game.inventory_button_rect = draw_inventory_button(game.virtual_screen)
    game.nearby_button_rect = draw_nearby_button(game.virtual_screen)
    game.gear_button_rect = draw_gear_button(game.virtual_screen)
    game.messages_button_rect = draw_messages_button(game.virtual_screen)
    game.crafting_button_rect = draw_crafting_button(game.virtual_screen)

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

    #if game.hovered_item and not game.context_menu['active']:
    #    draw_tooltip(game.virtual_screen, game.hovered_item, game._get_scaled_mouse_pos())

    elif not game.context_menu['active']:
        ui_buttons = [
            (game.pause_button_rect, "Pause and Save (F2)"),
            (game.forward_button_rect, "Skip time (F3)"),
            (game.status_button_rect, "Player Status (H)"),
            (game.inventory_button_rect, "Inventory (I)"),
            (game.gear_button_rect, "Gear (G)"),
            (game.nearby_button_rect, "Nearby (N)"),
            (game.messages_button_rect, "Messages (M)"),
            (game.crafting_button_rect, "Crafting (C)")
        ]
        
        mouse_pos = game._get_scaled_mouse_pos()
        
        for rect, label in ui_buttons:
            if rect and rect.collidepoint(mouse_pos):
                # Use standard notification font or fallback to asset font
                font_tip = globals().get('font_notification', game.assets.get('font'))
                
                if font_tip:
                    text_surf = font_tip.render(label, True, WHITE)
                    padding = 8
                    width = text_surf.get_width() + padding * 2
                    height = text_surf.get_height() + padding * 2
                    
                    # Position tooltip near mouse but keep on screen
                    tip_x = mouse_pos[0] + 10
                    tip_y = mouse_pos[1] + 10
                    
                    if tip_x + width > VIRTUAL_SCREEN_WIDTH:
                        tip_x = mouse_pos[0] - width - 5
                    if tip_y + height > VIRTUAL_GAME_HEIGHT:
                        tip_y = mouse_pos[1] - height - 5
                    
                    tooltip_rect = pygame.Rect(tip_x, tip_y, width, height)
                    
                    # Draw consistent tooltip style (Dark background, White border)
                    pygame.draw.rect(game.virtual_screen, (0, 0, 0, 220), tooltip_rect)
                    pygame.draw.rect(game.virtual_screen, WHITE, tooltip_rect, 1)
                    game.virtual_screen.blit(text_surf, (tip_x + padding, tip_y + padding))
                break

    #if game.context_menu['active']:
    #    draw_context_menu(game.virtual_screen, game.context_menu, game._get_scaled_mouse_pos())

    if game.player.is_aiming:
        pygame.mouse.set_visible(False) 
        reticle_img = game.assets.get('aim_reticle')
        if reticle_img:
            base_w = reticle_img.get_width()
            base_h = reticle_img.get_height()
            scale_mult = 1.5 + (game.player.current_aim_factor * 3.5)
            new_w = max(1, int(base_w * scale_mult))
            new_h = max(1, int(base_h * scale_mult))
            scaled_reticle = pygame.transform.scale(reticle_img, (new_w, new_h))
            rect = scaled_reticle.get_rect(center=game._get_scaled_mouse_pos())
            game.virtual_screen.blit(scaled_reticle, rect)
    else:
        pygame.mouse.set_visible(True)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
             pygame.mouse.set_cursor(game.assets.get('aim_cursor') or pygame.cursors.arrow)
        else:
             pygame.mouse.set_cursor(game.assets.get('custom_cursor') or pygame.cursors.arrow)

    if hasattr(game, 'clock'):
        fps = int(game.clock.get_fps())
        fps_text = f"FPS: {fps}"
        font = game.assets.get('font')
        if font:
            fps_surface = font.render(fps_text, True, (0, 255, 0)) # Green color
            # Position 5 pixels from right and bottom edges
            fps_rect = fps_surface.get_rect(bottomright=(game.virtual_screen.get_width() - 5, game.virtual_screen.get_height() - 5))
            game.virtual_screen.blit(fps_surface, fps_rect)