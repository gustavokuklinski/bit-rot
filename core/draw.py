import pygame
import math
import random
import time
from core.data.config import *
import core.data.config
from core.entities.item.item import Item
from core.entities.zombie.zombie import Zombie
from core.entities.npc.npc import NPC
from core.entities.animal.animal import Animal
from core.ui.helpers.main_menu import draw_menu
from core.ui.helpers.game_over import draw_game_over
from core.ui.inventory_modal import draw_inventory_modal, get_inventory_slot_rect, get_belt_slot_rect_in_modal # draw_belt_hud get_belt_hud_slot_rect
from core.ui.container_modal import draw_container_view, get_container_slot_rect
from core.ui.status_modal import draw_status_modal
from core.ui.dropdown import draw_context_menu
from core.ui.nearby_modal import draw_nearby_modal
from core.ui.helpers.buttons import draw_inventory_button, draw_status_button, draw_forward_button, draw_pause_button, draw_nearby_button, draw_messages_button, draw_gear_button, draw_crafting_button, draw_help_button, draw_slots_button
from core.ui.tooltip import draw_tooltip
from core.ui.help_modal import draw_help_modal
from core.ui.gear_modal import draw_gear_modal
from core.ui.messages_modal import draw_messages_modal
from core.ui.text_modal import draw_text_modal
from core.ui.mobile_modal import draw_mobile_modal
from core.ui.alerts import draw_player_alerts
from core.ui.vehicle_modal import draw_vehicle_modal
from core.ui.crafting_modal import CraftingModal
from core.ui.mobile_map_tab import draw_big_map_modal
from core.ui.npc_dialog_modal import draw_npc_dialog_modal
from core.ui.slots_modal import draw_slots_modal
from core.systems.utils import get_player_facing_tile, get_targeted_interactable
from core.data.localization import tr

def draw_game(game):
    # Clear the main screen
    game.game_screen.fill(PANEL_COLOR)
    if hasattr(game, 'virtual_controller') and game.virtual_controller.enabled:
        game.virtual_controller.draw(game.game_screen)

    # World Rendering with Pixelated Zoom
    zoom = getattr(game, 'zoom_level', 1.0)
    view_w = int(GAME_WIDTH / zoom)
    view_h = int(GAME_HEIGHT / zoom)

    if not hasattr(game, 'cached_view_surface') or \
       game.cached_view_surface.get_width() != view_w or \
       game.cached_view_surface.get_height() != view_h:
        game.cached_view_surface = pygame.Surface((view_w, view_h))
        game.particle_scratch = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    
    world_view_surface = game.cached_view_surface
    world_view_surface.fill((20, 20, 20)) 

    # 1. CALCULATE CAMERA PANNING
    mouse_pos = game._get_scaled_mouse_pos()

    is_over_modal = False
    if not getattr(game, 'hide_modals', False):
        for modal in game.modals:
            if modal.get('rect') and modal['rect'].collidepoint(mouse_pos):
                is_over_modal = True
                break

    mouse_buttons = pygame.mouse.get_pressed()
    keys = pygame.key.get_pressed()

    joy_lx, joy_ly = 0, 0
    joy_run, joy_aim = False, False
    if getattr(game, 'joystick_handler', None):
        joy_lx, joy_ly = game.joystick_handler.get_movement_axes()
        joy_run, joy_aim = game.joystick_handler.get_action_states()

    is_running = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or joy_run)
    game.player.is_running = is_running

    # Fixed typo and added right-click (mouse_buttons[2]) detection for panning
    is_aiming = (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL] or mouse_buttons[2] or joy_aim)

    target_pan_x = 0
    target_pan_y = 0

    if game.player:
        world_mouse_pos = game.screen_to_world(mouse_pos)
        dx = world_mouse_pos[0] - game.player.rect.centerx
        dy = world_mouse_pos[1] - game.player.rect.centery
        game.player.aim_angle = math.atan2(-dy, dx)

    if is_aiming and game.player:
        # Panning starts when the mouse is in the outer 5% of the screen (95% threshold)
        edge_margin_x = GAME_WIDTH * 0.02
        edge_margin_y = GAME_HEIGHT * 0.02
        
        at_left_edge = mouse_pos[0] < edge_margin_x
        at_right_edge = mouse_pos[0] > GAME_WIDTH - edge_margin_x
        at_top_edge = mouse_pos[1] < edge_margin_y
        at_bottom_edge = mouse_pos[1] > GAME_HEIGHT - edge_margin_y

        if at_left_edge or at_right_edge or at_top_edge or at_bottom_edge:
            pan_distance = min(view_w, view_h) * 0.5
            target_pan_x = math.cos(game.player.aim_angle) * pan_distance
            target_pan_y = -math.sin(game.player.aim_angle) * pan_distance

    dt_mult = getattr(game, 'dt_mult', 1.0)
    if not hasattr(game, 'camera_pan_x'): game.camera_pan_x = 0
    if not hasattr(game, 'camera_pan_y'): game.camera_pan_y = 0
    
    # 0.1 represents the original smoothing factor at exactly 60 FPS
    lerp_factor = 1.0 - math.pow(1.0 - 0.1, dt_mult)
    game.camera_pan_x += (target_pan_x - game.camera_pan_x) * lerp_factor
    game.camera_pan_y += (target_pan_y - game.camera_pan_y) * lerp_factor

    if game.player:
        game.true_camera_x = game.player.rect.centerx - (view_w / 2)
        game.true_camera_y = game.player.rect.centery - (view_h / 2)

    # Calculate the targeted view offset (invert for drawing math)
    target_offset_x = -game.true_camera_x - game.camera_pan_x
    target_offset_y = -game.true_camera_y - game.camera_pan_y

    # --- CLAMP CAMERA TO MAP BOUNDS ---
    map_h = len(game.map_data) if hasattr(game, 'map_data') and game.map_data else 0
    map_w = len(game.map_data[0]) if map_h > 0 else 0
    
    tile_size = TILE_SIZE
    map_pixel_w = map_w * tile_size
    map_pixel_h = map_h * tile_size

    # Only clamp if the map actually has bounds
    if map_pixel_w > 0 and map_pixel_h > 0:
        # X Axis Clamp
        if map_pixel_w < view_w:
            offset_x = (view_w - map_pixel_w) / 2 
        else:
            offset_x = max(view_w - map_pixel_w, min(0, target_offset_x))
            
        # Y Axis Clamp
        if map_pixel_h < view_h:
            offset_y = (view_h - map_pixel_h) / 2
        else:
            offset_y = max(view_h - map_pixel_h, min(0, target_offset_y))
    else:
        # Fallback if map layout isn't fully loaded
        offset_x = target_offset_x
        offset_y = target_offset_y

    # Force sync the tracked camera if it hit a clamp, preventing the deadzone from drifting!
    if map_pixel_w >= view_w:
        game.true_camera_x = -offset_x - game.camera_pan_x
    if map_pixel_h >= view_h:
        game.true_camera_y = -offset_y - game.camera_pan_y

    screen_rect = pygame.Rect(-offset_x, -offset_y, view_w, view_h)

    game.offset_x = offset_x
    game.offset_y = offset_y

    # 2. OPTIMIZED CHUNK RENDERING
    chunk_size = core.data.config.CHUNK_SIZE
    
    min_world_x = -offset_x
    min_world_y = -offset_y
    max_world_x = -offset_x + view_w
    max_world_y = -offset_y + view_h
    
    min_chunk_x = int(min_world_x // (chunk_size * tile_size))
    min_chunk_y = int(min_world_y // (chunk_size * tile_size))
    max_chunk_x = int(max_world_x // (chunk_size * tile_size)) + 1
    max_chunk_y = int(max_world_y // (chunk_size * tile_size)) + 1

    map_chunk_w = (map_w // chunk_size) + 1
    map_chunk_h = (map_h // chunk_size) + 1

    min_chunk_x = max(0, min_chunk_x)
    min_chunk_y = max(0, min_chunk_y)
    max_chunk_x = min(map_chunk_w, max_chunk_x + 1)
    max_chunk_y = min(map_chunk_h, max_chunk_y + 1)
    
    tm = game.tile_manager
    shaking_tiles = game.map_manager.shaking_tiles
    current_time = time.time()
    tiles_to_remove = []

    visible_chunks = []
    for cy in range(min_chunk_y, max_chunk_y):
        for cx in range(min_chunk_x, max_chunk_x):
            visible_chunks.append((cx, cy))
    
    center_cx = (min_chunk_x + max_chunk_x) / 2
    center_cy = (min_chunk_y + max_chunk_y) / 2
    
    visible_chunks.sort(key=lambda p: (p[0] - center_cx)**2 + (p[1] - center_cy)**2)

    for cx, cy in visible_chunks:
        chunk_surf = game.map_manager.get_chunk_surface(cx, cy, game.current_layer_index, 'world')
        if chunk_surf:
            dest_x = cx * chunk_size * tile_size + offset_x
            dest_y = cy * chunk_size * tile_size + offset_y
            world_view_surface.blit(chunk_surf, (dest_x, dest_y))

    for pos, start_t in shaking_tiles.items():
        gx, gy = pos
        screen_px = int(gx * tile_size + offset_x)
        screen_py = int(gy * tile_size + offset_y)
        
        if -tile_size < screen_px < view_w and -tile_size < screen_py < view_h:
            b_key = game.map_data[gy][gx]
            if b_key and b_key != ' ':
                b_def = tm.definitions.get(b_key)
                if b_def:
                    draw_x, draw_y = screen_px, screen_py
                    if current_time - start_t > 0.2:
                        tiles_to_remove.append(pos)
                    else:
                        draw_x += random.randint(-2, 2)
                        draw_y += random.randint(-2, 2)
                    world_view_surface.blit(b_def['image'], (draw_x, draw_y))
    
    for k in tiles_to_remove:
        if k in game.map_manager.shaking_tiles:
            del game.map_manager.shaking_tiles[k]

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

    # Light Mask Caching - Cache at zoom levels to avoid expensive transform.scale every frame
    if not hasattr(game, 'light_mask_cache'):
        game.light_mask_cache = {}

    # [OPTIMIZATION] Cleanup light_mask_cache to prevent memory bloat
    # Keep only the most recently used entries (max 20)
    MAX_LIGHT_CACHE_ENTRIES = 20
    if len(game.light_mask_cache) > MAX_LIGHT_CACHE_ENTRIES:
        # Remove oldest entries (keep last N)
        keys = list(game.light_mask_cache.keys())
        for key in keys[:-MAX_LIGHT_CACHE_ENTRIES]:
            del game.light_mask_cache[key]

    low_res_w = view_w // 2
    low_res_h = view_h // 2
    light_mask_low = pygame.Surface((low_res_w, low_res_h))

    light_mask_low.fill((30, 30, 30))
    ambient = int(game.world_time.current_ambient_light)

    light_texture = game.assets.get('light_texture')
    light_sources = []

    if light_texture:
        try:
            radius_world_pixels = game.player_view_radius
            radius_view_pixels = int(radius_world_pixels)

            if radius_view_pixels > 0:
                radius_low = radius_view_pixels // 2
                
                # Cache player vision texture at this radius
                cache_key = ('vision', radius_low)
                if cache_key not in game.light_mask_cache:
                    game.light_mask_cache[cache_key] = pygame.transform.scale(light_texture, (radius_low * 2, radius_low * 2))
                player_vision_tex = game.light_mask_cache[cache_key].copy()
                
                ambient_color = (ambient, ambient, ambient)
                player_vision_tex.fill(ambient_color, special_flags=pygame.BLEND_RGBA_MULT)

                light_rect = player_vision_tex.get_rect()

                p_screen_x = (game.player.rect.centerx + offset_x) / 2
                p_screen_y = (game.player.rect.centery + offset_y) / 2

                light_rect.center = (p_screen_x, p_screen_y)
                light_mask_low.blit(player_vision_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
        except Exception as e:
            print(f"Error drawing player vision: {e}")

    all_player_inventories = [game.player.belt, game.player.inventory]
    
    
    for inv in all_player_inventories:
        for item in inv:
            if getattr(item, 'state', 'off') == 'on':
                light_sources.append({'item': item, 'owner': 'player'})

    for item in game.visible_items:
         if getattr(item, 'state', 'off') == 'on':
            light_sources.append({'item': item, 'owner': 'ground'})
    
    if hasattr(game, 'vehicles'):
        for vehicle in game.vehicles:
            if getattr(vehicle, 'lights', 'off') == 'on' and vehicle.battery > 0:
                light_sources.append({'item': vehicle, 'owner': 'vehicle'})

    for container in game.visible_containers:
        if getattr(container, 'item_type', '') == 'vehicle':
             if not any(ls['item'] == container for ls in light_sources):
                 if getattr(container, 'lights', 'off') == 'on' and container.battery > 0:
                     light_sources.append({'item': container, 'owner': 'vehicle'})

    if light_texture:
        for light_info in light_sources:
            light = light_info['item']
            radius_world = getattr(light, 'current_light_radius', 0)
            if radius_world <= 0: continue

            if light_info['owner'] == 'player':
                 lx, ly = game.player.rect.centerx, game.player.rect.centery
            else:
                 lx, ly = light.rect.centerx, light.rect.centery

            if not screen_rect.inflate(radius_world*2, radius_world*2).collidepoint(lx, ly):
                continue

            radius_low = int(radius_world / 2)
            if radius_low <= 0: continue

            try:
                # Cache light source texture at this radius
                cache_key = ('light', radius_low)
                if cache_key not in game.light_mask_cache:
                    game.light_mask_cache[cache_key] = pygame.transform.scale(light_texture, (radius_low * 2, radius_low * 2))
                scaled_light_tex = game.light_mask_cache[cache_key]
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
                # Cache map light texture at this radius
                cache_key = ('map_light', radius_low)
                if cache_key not in game.light_mask_cache:
                    game.light_mask_cache[cache_key] = pygame.transform.scale(light_texture, (radius_low * 2, radius_low * 2))
                scaled_light_tex = game.light_mask_cache[cache_key].copy()
                light_opacity = 80
                scaled_light_tex.fill((light_opacity, light_opacity, light_opacity, 255), special_flags=pygame.BLEND_RGBA_MULT)
                light_rect = scaled_light_tex.get_rect()
                
                pos_x_view = (light['rect'].centerx + offset_x) / 2
                pos_y_view = (light['rect'].centery + offset_y) / 2
                light_rect.center = (pos_x_view, pos_y_view)
                light_mask_low.blit(scaled_light_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
            except Exception: pass
    
    # [OPTIMIZATION] strict view radius squared
    view_radius_sq = (game.player_view_radius + TILE_SIZE) ** 2

    # Draw Containers
    for container in game.visible_containers:
        if not screen_rect.colliderect(container.rect): continue
        
        # Strict Radius Check
        dx = container.rect.centerx - game.player.rect.centerx
        dy = container.rect.centery - game.player.rect.centery
        if (dx*dx + dy*dy) > view_radius_sq: continue

        draw_pos = container.rect.move(offset_x, offset_y)
        if getattr(container, 'image', None):
             world_view_surface.blit(container.image, draw_pos)
        else:
             color = getattr(container, 'color', WHITE)
             pygame.draw.rect(world_view_surface, color, draw_pos)

    # Draw Items
    for item in game.visible_items:
        if not screen_rect.colliderect(item.rect): continue
        
        # Strict Radius Check
        dx = item.rect.centerx - game.player.rect.centerx
        dy = item.rect.centery - game.player.rect.centery
        if (dx*dx + dy*dy) > view_radius_sq: continue

        draw_pos = item.rect.move(offset_x, offset_y)
        if getattr(item, 'image', None):
            world_view_surface.blit(item.image, draw_pos)
        else:
            pygame.draw.rect(world_view_surface, getattr(item, 'color', WHITE), draw_pos)

    # Draw Projectiles
    for p in game.projectiles:
        if screen_rect.colliderect(p.rect):
            p.draw(world_view_surface, offset_x, offset_y)

    # Draw Zombies, Animals, NPCs (via Quadtree)
    # [OPTIMIZATION] Distance-based with cached LOS checks
    visible_entities = game.quadtree.query(screen_rect.inflate(100, 100))
    
    view_radius_sq = (game.player_view_radius + TILE_SIZE) ** 2
    current_time = pygame.time.get_ticks()
    
    for entity in visible_entities:
        if isinstance(entity, (Zombie, NPC, Animal)):
            # Strict Radius Check
            dx = entity.rect.centerx - game.player.rect.centerx
            dy = entity.rect.centery - game.player.rect.centery
            dist_sq = dx*dx + dy*dy
            if dist_sq > view_radius_sq: continue

            if screen_rect.colliderect(entity.rect):
                # [OPTIMIZATION] Cached LOS check every 500ms
                opacity = 255
                
                if not hasattr(entity, 'last_los_draw_check'):
                    entity.last_los_draw_check = 0
                    entity.cached_los_draw_result = True
                
                if current_time - entity.last_los_draw_check > 500:
                    entity.last_los_draw_check = current_time
                    entity.cached_los_draw_result = game.player.has_line_of_sight(entity.rect, game.obstacles, game)
                
                if not entity.cached_los_draw_result:
                    opacity = 80  # Dark/silhouette for entities not in line of sight
                
                entity.draw(world_view_surface, offset_x, offset_y, opacity)

    game.player.draw_highlight_stairs(world_view_surface, game, offset_x, offset_y)
    game.player.draw(world_view_surface, offset_x, offset_y, is_aiming)

    player_tile_x = game.player.rect.centerx // tile_size
    player_tile_y = game.player.rect.centery // tile_size
    roof_hide_radius = 3

    if getattr(game, 'roof_data', None):
        hide_min_tx = player_tile_x - roof_hide_radius
        hide_max_tx = player_tile_x + roof_hide_radius
        hide_min_ty = player_tile_y - roof_hide_radius
        hide_max_ty = player_tile_y + roof_hide_radius
        
        min_grid_x = max(0, min_chunk_x * chunk_size)
        min_grid_y = max(0, min_chunk_y * chunk_size)
        max_grid_x = min(map_w, max_chunk_x * chunk_size)
        max_grid_y = min(map_h, max_chunk_y * chunk_size)

        for gy in range(min_grid_y, max_grid_y):
            for gx in range(min_grid_x, max_grid_x):
                r_key = game.roof_data[gy][gx]
                if r_key and r_key != ' ':
                    if not (hide_min_tx <= gx <= hide_max_tx and hide_min_ty <= gy <= hide_max_ty):
                        r_def = tm.definitions.get(r_key)
                        if r_def:
                             screen_px = int(gx * tile_size + offset_x)
                             screen_py = int(gy * tile_size + offset_y)
                             world_view_surface.blit(r_def['image'], (screen_px, screen_py))


    SPLASH_COLOR = (139, 0, 0)
    current_time_ms = pygame.time.get_ticks()
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

    if game.hovered_container:
        dx = game.hovered_container.rect.centerx - game.player.rect.centerx
        dy = game.hovered_container.rect.centery - game.player.rect.centery
        if (dx*dx + dy*dy) <= view_radius_sq:
            hover_rect = game.hovered_container.rect.move(offset_x, offset_y)
            pygame.draw.rect(world_view_surface, YELLOW, hover_rect, 2)

    world_mouse_pos = game.screen_to_world(mouse_pos)

    # Draw hover border on NPCs (Light Blue for all NPCs)
    for npc in game.npcs:
        if not screen_rect.colliderect(npc.rect): continue
        if npc.rect.collidepoint(world_mouse_pos):
            color = GRAY # Gray
            hover_rect = npc.rect.move(offset_x, offset_y)
            pygame.draw.rect(world_view_surface, color, hover_rect, 2)
            break
    
    for zombie in game.active_zombies:
        if not screen_rect.colliderect(zombie.rect): continue
        if zombie.rect.collidepoint(world_mouse_pos):
            hover_rect = zombie.rect.move(offset_x, offset_y)
            pygame.draw.rect(world_view_surface, (128, 0, 128), hover_rect, 2)
            break

    for animal in game.active_animals:
        if not screen_rect.colliderect(animal.rect): continue
        if animal.rect.collidepoint(world_mouse_pos):
            hover_rect = animal.rect.move(offset_x, offset_y)
            pygame.draw.rect(world_view_surface, (128, 0, 128), hover_rect, 2)
            break

    if game.hovered_interactable_tile_rect:
        hover_rect = game.hovered_interactable_tile_rect.move(offset_x, offset_y)
        pygame.draw.rect(world_view_surface, BLUE, hover_rect, 2)
    
    target = get_targeted_interactable(game)
    if target:
        target_color = (0, 255, 100) # Bright Green highlight
        if target['type'] in ['npc', 'vehicle']:
            hover_rect = target['entity'].rect.move(offset_x, offset_y)
            pygame.draw.rect(world_view_surface, target_color, hover_rect, 2)
        elif target['type'] in ['tile', 'stair']:
            tx, ty = target['entity']
            hover_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE).move(offset_x, offset_y)
            pygame.draw.rect(world_view_surface, target_color, hover_rect, 2)

    light_mask_upscaled = pygame.transform.scale(light_mask_low, (view_w, view_h))
    world_view_surface.blit(light_mask_upscaled, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    game_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
    if view_w == GAME_WIDTH and view_h == GAME_HEIGHT:
        game.game_screen.blit(world_view_surface, game_rect)
    else:
        scaled_world = pygame.transform.scale(world_view_surface, (GAME_WIDTH, GAME_HEIGHT))
        game.game_screen.blit(scaled_world, game_rect)


    if getattr(game.world_time, 'weather', 'CLEAR') == 'RAIN' or len(getattr(game, 'rain_particles', [])) > 0:
        if not hasattr(game, 'rain_particles'):
            game.rain_particles = []
            
        is_under_roof = False
        if getattr(game, 'roof_data', None) and game.player:
            px = int(game.player.rect.centerx // TILE_SIZE)
            py = int(game.player.rect.centery // TILE_SIZE)
            if 0 <= py < len(game.roof_data) and 0 <= px < len(game.roof_data[py]):
                r_key = game.roof_data[py][px]
                if r_key and r_key != ' ':
                    is_under_roof = True
            
        if getattr(game.world_time, 'weather', 'CLEAR') == 'RAIN' and getattr(game, 'current_layer_index', 1) != 2 and not (game.player and game.player.is_sleeping) and not is_under_roof:
            for _ in range(10): 
                game.rain_particles.append({
                    'x': random.randint(0, GAME_WIDTH + 200),
                    'y': random.randint(-50, 0),
                    'speed': random.randint(25, 35),
                    'length': random.randint(15, 30)
                })
        
        active_rain = []
        rain_color = (130, 150, 180)
        dt_mult = getattr(game, 'dt_mult', 1.0)
        for p in game.rain_particles:
            p['y'] += p['speed'] * dt_mult
            p['x'] -= (p['speed'] * 0.15) * dt_mult 
            
            start_pos = (int(p['x']), int(p['y']))
            end_pos = (int(p['x'] + p['speed'] * 0.15), int(p['y'] - p['length']))
            
            if not is_under_roof:
                pygame.draw.line(game.game_screen, rain_color, start_pos, end_pos, 1)
            
            if p['y'] < GAME_HEIGHT:
                active_rain.append(p)
        
        game.rain_particles = active_rain

    if game.player and game.player.is_sleeping:
        game.game_screen.fill((0, 0, 0))
        font = game.assets.get('font') or pygame.font.Font(None, 30)
        text_surf = font.render(tr('ui', "Sweet Dreams. Press Space to Wake up."), True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(game.game_screen.get_width() // 2, game.game_screen.get_height() // 2))
        game.game_screen.blit(text_surf, text_rect)

    if game.player.gun_flash_timer > 0:
        # [FIX] Calculate based on actual player world position + camera offset
        player_view_x = game.player.rect.centerx + offset_x
        player_view_y = game.player.rect.centery + offset_y
        
        screen_x = (player_view_x * zoom) + GAME_OFFSET_X
        screen_y = (player_view_y * zoom)

        flash_distance = (TILE_SIZE * 1.4) * zoom 
        
        flash_x = screen_x + math.cos(game.player.aim_angle) * flash_distance
        flash_y = screen_y - math.sin(game.player.aim_angle) * flash_distance
        
        flash_radius = (TILE_SIZE // 5) * zoom 
        pygame.draw.circle(game.game_screen, WHITE, (int(flash_x), int(flash_y)), int(flash_radius))
        game.player.gun_flash_timer -= getattr(game, 'dt_mult', 1.0)

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
        
        pygame.draw.rect(game.game_screen, WHITE, bubble_rect, border_radius=8)
        
        tri_center_x = screen_x + (TILE_SIZE * zoom / 2)
        tri_points = [
            (tri_center_x - 6, bubble_rect.bottom),
            (tri_center_x + 6, bubble_rect.bottom),
            (tri_center_x, bubble_rect.bottom + 8)
        ]
        pygame.draw.polygon(game.game_screen, WHITE, tri_points)
        
        text_rect = text_surf.get_rect(center=bubble_rect.center)
        game.game_screen.blit(text_surf, text_rect)

    if game.game_state == 'PLAYING':
        interactables = []
        # 1. Check NPCs
        for npc in game.npcs:
            if not npc.is_friendly or npc.aggro_timer > 0: continue
            if not screen_rect.colliderect(npc.rect): continue
            dist = math.hypot(game.player.rect.centerx - npc.rect.centerx, game.player.rect.centery - npc.rect.centery)
            if dist < TILE_SIZE * 1.5:
                interactables.append({'rect': npc.rect, 'tip': tr('tooltip', 'Press E to Talk\nRMB For Talk option')})
                
        # 2. Check Vehicles
        for obj in game.containers:
            if getattr(obj, 'item_type', '') == 'vehicle':
                if getattr(game.player, 'vehicle', None) == obj:
                    continue

                if not screen_rect.colliderect(obj.rect): continue
                dist = math.hypot(game.player.rect.centerx - obj.rect.centerx, game.player.rect.centery - obj.rect.centery)
                if dist < TILE_SIZE * 2.0:
                    # Safely extract vehicle stats
                    equip = getattr(obj, 'equipment', {})
                    motor_pct = int(getattr(obj, 'motor', 0.0) * 100)
                    fuel_val = int(getattr(obj, 'fuel', 0))
                    power_val = int(getattr(obj, 'battery', 0))
                    
                    # Count valid tires
                    tires_count = sum(1 for t in ['tire_fl', 'tire_fr', 'tire_bl', 'tire_br'] 
                                      if equip.get(t) and getattr(equip.get(t), 'durability', 0) > 0)
                    
                    # Determine Key status
                    if not getattr(obj, 'required_key_id', None):
                        key_status = tr('tooltip', "Not Req")
                    else:
                        key_status = tr('tooltip', "Yes") if equip.get('key') else tr('tooltip', "Missing")
                        
                    # Construct multi-line tooltip - UPDATE THESE LINES:
                    t_enter = tr('tooltip', "Press E to enter/exit vehicle")
                    t_engine = tr('tooltip', "Press Q to turn on/off engine")
                    t_rmb = tr('tooltip', "RMB for Vehicle Options and Trunk")
                    t_mot = tr('tooltip', "Motor")
                    t_fuel = tr('tooltip', "Fuel")
                    t_pow = tr('tooltip', "Power")
                    t_tire = tr('tooltip', "Tires")
                    t_key = tr('tooltip', "Key")
                    
                    # Store as structured data so the renderer can insert images
                    tip_data = {
                        'type': 'vehicle',
                        'text_lines': [t_enter, t_engine, t_rmb, ""],
                        'stats': [
                            {'icon': 'motor', 'text': t_mot, 'val': f"{motor_pct}%"},
                            {'icon': 'fuel', 'text': t_fuel, 'val': f"{fuel_val}"},
                            {'icon': 'power', 'text': t_pow, 'val': f"{power_val}"}, # Will fallback to text since no icon was provided
                            {'icon': 'tires', 'text': t_tire, 'val': f"{tires_count}/4"},
                            {'icon': 'key', 'text': t_key, 'val': f"{key_status}"}
                        ]
                    }
                    
                    interactables.append({'rect': obj.rect, 'tip': tip_data})

        # 3. Check Tiles (Doors, Windows, Stairs)
        fx, fy = get_player_facing_tile(game)
        if fx is not None:
            t = game.map_manager.get_tile_at(fx, fy)
            if t:
                is_stair = t.get('is_stair')
                is_statable = t.get('is_statable')
                if is_stair or is_statable:
                    dist = math.hypot(game.player.rect.centerx - (fx*TILE_SIZE + TILE_SIZE/2), game.player.rect.centery - (fy*TILE_SIZE + TILE_SIZE/2))
                    if dist < TILE_SIZE * 1.5:
                        tile_rect = pygame.Rect(fx * TILE_SIZE, fy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        if is_stair:
                            # Update this line:
                            interactables.append({'rect': tile_rect, 'tip': tr('tooltip', 'Press E\nto go Down/Up')})
                        else:
                            name = t.get('name', '').lower()
                            # Update these lines:
                            if 'window' in name:
                                interactables.append({'rect': tile_rect, 'tip': tr('tooltip', 'Press E or RMB\nto Open/Close')})
                            else:
                                interactables.append({'rect': tile_rect, 'tip': tr('tooltip', 'Press E or RMB\nto Open/Close')})
                                
        # Draw the '!' marks
        mouse_pos = game._get_scaled_mouse_pos()
        
        tooltip_to_draw = None
        
        for item in interactables:
            world_rect = item['rect']
            
            # Position '!' top middle of the entity/tile
            screen_x = ((world_rect.centerx + offset_x) * zoom) + GAME_OFFSET_X
            screen_y = ((world_rect.top + offset_y) * zoom) - 5
            
            box_rect = pygame.Rect(0, 0, 20, 20)
            box_rect.center = (screen_x, screen_y)
            
            pygame.draw.rect(game.game_screen, (0, 0, 0), box_rect)
            pygame.draw.rect(game.game_screen, (255, 255, 255), box_rect, 1)
            
            excl_surf = font_14.render("!", True, (255, 255, 255))
            excl_rect = excl_surf.get_rect(center=box_rect.center)
            game.game_screen.blit(excl_surf, excl_rect)
            
            if box_rect.collidepoint(mouse_pos):
                tooltip_to_draw = item['tip']

        # --- CRT FILTER OVERLAY ---
        # Only draw if enabled in the settings
        if getattr(core.data.config, 'UI_CRT_FILTER', True):
            # Cached to ensure zero performance hit during the main loop
            if not hasattr(game, 'crt_overlay') or game.crt_overlay.get_size() != (int(GAME_WIDTH), int(GAME_HEIGHT)):
                game.crt_overlay = pygame.Surface((int(GAME_WIDTH), int(GAME_HEIGHT)), pygame.SRCALPHA)
                
                # 1. Base Phosphor Tint (gives that faint vintage green/blue glow)
                game.crt_overlay.fill((15, 25, 15, 15))
                
                # 2. Authentic Scanlines
                for y in range(0, int(GAME_HEIGHT), 3):
                    pygame.draw.line(game.crt_overlay, (0, 0, 0, 45), (0, y), (int(GAME_WIDTH), y), 1)
                    
                # 3. Vignette (Darkened Edges)
                # Elegant approach: Draw math onto a tiny 32x32 surface, then smoothscale it up!
                tiny_v = pygame.Surface((32, 32), pygame.SRCALPHA)
                for y in range(32):
                    for x in range(32):
                        dx = (x - 15.5) / 15.5
                        dy = (y - 15.5) / 15.5
                        dist = (dx*dx + dy*dy)
                        # Cap opacity at ~160 so the edges aren't pitch black
                        alpha = min(255, max(0, int(dist * 160))) 
                        tiny_v.set_at((x, y), (0, 0, 0, alpha))
                
                vignette = pygame.transform.smoothscale(tiny_v, (int(GAME_WIDTH), int(GAME_HEIGHT)))
                game.crt_overlay.blit(vignette, (0, 0))

            # Apply the filter strictly to the game world before UI is drawn
            game.game_screen.blit(game.crt_overlay, (0, 0))
                
        if tooltip_to_draw:
            if isinstance(tooltip_to_draw, str):
                lines = tooltip_to_draw.split('\n')
                max_w = max((font_14.render(line, True, WHITE).get_width() for line in lines), default=0)
                
                tt_w = max_w + 10
                tt_h = len(lines) * 20 + 10
                
                # --- ELEGANT JOYSTICK FIX ---
                tt_x = mouse_pos[0] + 15
                tt_y = mouse_pos[1] + 15
                
                if tt_x + tt_w > GAME_WIDTH: tt_x = mouse_pos[0] - tt_w - 5
                if tt_y + tt_h > GAME_HEIGHT: tt_y = mouse_pos[1] - tt_h - 5
                
                tt_rect = pygame.Rect(tt_x, tt_y, tt_w, tt_h)
                
                # Temporary surface for transparent background
                tip_bg = pygame.Surface((tt_w, tt_h), pygame.SRCALPHA)
                tip_bg.fill((0, 0, 0, 220))
                game.game_screen.blit(tip_bg, (tt_x, tt_y))
                pygame.draw.rect(game.game_screen, WHITE, tt_rect, 1)
                
                curr_y = tt_y + 5
                for line in lines:
                    ls = font_14.render(line, True, WHITE)
                    game.game_screen.blit(ls, (tt_x + 5, curr_y))
                    curr_y += 20
                    
            elif isinstance(tooltip_to_draw, dict) and tooltip_to_draw.get('type') == 'vehicle':
                # Load and Cache images to prevent loading them every frame
                if not hasattr(game, 'vehicle_icons'):
                    game.vehicle_icons = {}
                    icon_paths = {
                        'fuel': 'game/lib/sprites/items/car_fuel_unit.png',
                        'motor': 'game/lib/sprites/items/car_motor.png',
                        'power': 'game/lib/sprites/items/car_battery.png',
                        'tires': 'game/lib/sprites/items/car_tire.png',
                        'key': 'game/lib/sprites/items/car_key_pickup.png'
                    }
                    for k, path in icon_paths.items():
                        try:
                            game.vehicle_icons[k] = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (16, 16))
                        except Exception:
                            game.vehicle_icons[k] = None

                lines = tooltip_to_draw['text_lines']
                max_w = max((font_14.render(line, True, WHITE).get_width() for line in lines), default=0)
                
                # Calculate the width of the dynamic stats line
                stats_w = 0
                for stat in tooltip_to_draw['stats']:
                    icon_img = game.vehicle_icons.get(stat['icon'])
                    if icon_img:
                        stats_w += 16 + 4  # 16px icon + spacing
                    else:
                        stats_w += font_14.render(stat['text'] + ": ", True, WHITE).get_width()
                    stats_w += font_14.render(stat['val'], True, WHITE).get_width() + 10
                
                max_w = max(max_w, stats_w)
                
                tt_w = max_w + 10
                tt_h = len(lines) * 20 + 20 + 10 # Extra 20 pixels for the stats line
                tt_x, tt_y = mouse_pos[0], mouse_pos[1]
                
                if tt_x + tt_w > GAME_WIDTH: tt_x = mouse_pos[0] - tt_w - 5
                if tt_y + tt_h > GAME_HEIGHT: tt_y = mouse_pos[1] - tt_h - 5
                
                tt_rect = pygame.Rect(tt_x, tt_y, tt_w, tt_h)
                
                tip_bg = pygame.Surface((tt_w, tt_h), pygame.SRCALPHA)
                tip_bg.fill((0, 0, 0, 220))
                game.game_screen.blit(tip_bg, (tt_x, tt_y))
                pygame.draw.rect(game.game_screen, WHITE, tt_rect, 1)
                
                # Draw main text lines
                curr_y = tt_y + 5
                for line in lines:
                    ls = font_14.render(line, True, WHITE)
                    game.game_screen.blit(ls, (tt_x + 5, curr_y))
                    curr_y += 20
                
                # Draw inline icons and values
                curr_x = tt_x + 5
                for stat in tooltip_to_draw['stats']:
                    icon_img = game.vehicle_icons.get(stat['icon'])
                    
                    if icon_img:
                        game.game_screen.blit(icon_img, (curr_x, curr_y))
                        curr_x += 20
                    else:
                        text_s = font_14.render(stat['text'] + ": ", True, WHITE)
                        game.game_screen.blit(text_s, (curr_x, curr_y + 2))
                        curr_x += text_s.get_width()
                    
                    val_s = font_14.render(stat['val'], True, WHITE)
                    game.game_screen.blit(val_s, (curr_x, curr_y + 2))
                    curr_x += val_s.get_width() + 10

        #draw_belt_hud(game.game_screen, game, game.player, game._get_scaled_mouse_pos())
        alert_tooltip = draw_player_alerts(game.game_screen, game.player)
        if alert_tooltip:
             game.hovered_item = alert_tooltip

    top_tooltip = None
    game.modal_buttons = []
    mouse_pos = game._get_scaled_mouse_pos()
    topmost_modal_id = game.modals[-1]['id'] if game.modals else None

    for modal in game.modals:
        modal['is_active'] = (modal['id'] == topmost_modal_id)
        
        if modal['type'] == 'status':
            buttons = draw_status_modal(game.game_screen, game.player, modal, game.assets, game.zombies_killed, mouse_pos, game)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'inventory':
            tooltip, *buttons = draw_inventory_modal(game.game_screen, game, game.player, modal, game.assets, game._get_scaled_mouse_pos())
            top_tooltip = tooltip or top_tooltip
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'gear':
            buttons = draw_gear_modal(game.game_screen, game, game.player, modal, game.assets, mouse_pos)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'container':
            buttons = draw_container_view(game.game_screen, game, modal['item'], modal, game.assets, mouse_pos)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'nearby':
            buttons = draw_nearby_modal(game.game_screen, game, modal, game.assets, mouse_pos)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'slots':
            buttons = draw_slots_modal(game.game_screen, game, game.player, modal, game.assets, mouse_pos)
            game.modal_buttons.extend(buttons)

        elif modal['type'] == 'messages':
            result = draw_messages_modal(game.game_screen, game, modal, game.assets)
            if len(result) == 5:
                _, close_button, minimize_button, send_btn, input_box = result
                if send_btn: game.modal_buttons.append(send_btn)
                if input_box: game.modal_buttons.append(input_box)
            else:
                _, close_button, minimize_button = result
            if close_button: game.modal_buttons.append(close_button)
            if minimize_button: game.modal_buttons.append(minimize_button)
        elif modal['type'] == 'text':
            _, close_button, minimize_button = draw_text_modal(game.game_screen, game, modal, game.assets)
            if close_button: game.modal_buttons.append(close_button)
            if minimize_button: game.modal_buttons.append(minimize_button)
        elif modal['type'] == 'mobile':
            buttons = draw_mobile_modal(game.game_screen, game, modal, game.assets)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'vehicle':
            buttons = draw_vehicle_modal(game.game_screen, game, modal, game.assets, mouse_pos)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'big_map':
            buttons = draw_big_map_modal(game.game_screen, game, modal, game.assets)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'npc_dialog':
            buttons = draw_npc_dialog_modal(game.game_screen, modal, game)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'help': 
            _, close_button, minimize_button = draw_help_modal(game.game_screen, game, modal, game.assets)
            if close_button: game.modal_buttons.append(close_button)
            if minimize_button: game.modal_buttons.append(minimize_button)
        elif modal['type'] == 'crafting':
            if 'instance' not in modal:
                modal['instance'] = CraftingModal(game.game_screen, modal, game.assets, game)
            modal['instance'].surface = game.game_screen
            _, *buttons = modal['instance'].draw()
            game.modal_buttons.extend(buttons)

    game.pause_button_rect = draw_pause_button(game.game_screen)
    game.forward_button_rect = draw_forward_button(game.game_screen)
    game.status_button_rect = draw_status_button(game.game_screen)
    game.inventory_button_rect = draw_inventory_button(game.game_screen)
    game.nearby_button_rect = draw_nearby_button(game.game_screen)
    game.gear_button_rect = draw_gear_button(game.game_screen)
    game.slots_button_rect = draw_slots_button(game.game_screen)
    game.messages_button_rect = draw_messages_button(game.game_screen)
    game.crafting_button_rect = draw_crafting_button(game.game_screen)
    game.help_button_rect = draw_help_button(game.game_screen)
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
                            highlighted_allowed = (preview_item.item_type)
                            break
                    if highlighted_rect: break
                    for i in range(5):
                        slot = get_inventory_slot_rect(i, modal['position'])
                        if slot.collidepoint(game._get_scaled_mouse_pos()):
                            highlighted_rect = slot
                            highlighted_allowed = True
                            break
                    if highlighted_rect: break
                    
                    
            elif modal['type'] == 'gear':
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(game._get_scaled_mouse_pos()):
                            highlighted_rect = slot_rect
                            item_slot = getattr(preview_item, 'slot', None)
                            if item_slot == 'hand': item_slot = 'hands'
                            
                            # --- NEW CODE: Allow containers in util slots ---
                            is_util_slot = slot_name in ['util', 'util2', 'util3']
                            is_container = getattr(preview_item, 'item_type', '') == 'container'
                            is_util_item = item_slot == 'util'
                            highlighted_allowed = (item_slot == slot_name) or (is_util_slot and (is_container or is_util_item))
                            # ------------------------------------------------
                            
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
            elif modal['type'] == 'slots':
                for slot_data in modal.get('slot_rects', []):
                    if slot_data['rect'].collidepoint(game._get_scaled_mouse_pos()):
                        highlighted_rect = slot_data['rect']
                        cont = slot_data['container']
                        i = slot_data['index']
                        highlighted_allowed = (len(cont.inventory) < cont.capacity) or (i < len(cont.inventory))
                        break
                if highlighted_rect: break
            elif modal['type'] == 'messages':
                pass

        #if not highlighted_rect:
        #    for i in range(5):
        #        slot = get_belt_hud_slot_rect(i)
        #        if slot.collidepoint(game._get_scaled_mouse_pos()):
        #            highlighted_rect = slot
        #            highlighted_allowed = (preview_item.item_type)
        #            break

        if highlighted_rect:
            overlay = pygame.Surface((highlighted_rect.width, highlighted_rect.height), pygame.SRCALPHA)
            color = (50, 220, 50, 80) if highlighted_allowed else (220, 50, 50, 80)
            overlay.fill(color)
            game.game_screen.blit(overlay, highlighted_rect.topleft)
            pygame.draw.rect(game.game_screen, YELLOW if highlighted_allowed else RED, highlighted_rect, 2)

        if preview_item and getattr(preview_item, 'image', None):
            img = pygame.transform.scale(preview_item.image, (int(highlighted_rect.height * 0.9) if highlighted_rect else 40, int(highlighted_rect.height * 0.9) if highlighted_rect else 40))
            img_rect = img.get_rect()
            img_rect.topleft = (game._get_scaled_mouse_pos()[0] - game.drag_offset[0], game._get_scaled_mouse_pos()[1] - game.drag_offset[1])
            game.game_screen.blit(img, img_rect)
        elif preview_item:
            rect_w, rect_h = (int(highlighted_rect.width * 0.8), int(highlighted_rect.height * 0.8)) if highlighted_rect else (40, 40)
            preview_rect = pygame.Rect(game._get_scaled_mouse_pos()[0] - rect_w//2, game._get_scaled_mouse_pos()[1] - rect_h//2, rect_w, rect_h)
            s = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
            s.fill((*preview_item.color, 180))
            game.game_screen.blit(s, preview_rect.topleft)

    if top_tooltip:
        tip_rect = top_tooltip['rect']
        item = top_tooltip['item']
        frac = top_tooltip['frac']
        bar_color = top_tooltip['bar']

        tip_s = pygame.Surface((tip_rect.width, tip_rect.height), pygame.SRCALPHA)
        tip_s.fill((10, 10, 10, 220))
        game.game_screen.blit(tip_s, tip_rect.topleft)
        pygame.draw.rect(game.game_screen, WHITE, tip_rect, 1)

        name_surf = game.assets['font'].render(f"{tr('item', item.name)}", True, WHITE)
        type_surf = game.assets['font'].render(f"Type: {item.item_type}", True, GRAY)
        game.game_screen.blit(name_surf, (tip_rect.x + 8, tip_rect.y + 6))
        game.game_screen.blit(type_surf, (tip_rect.x + 8, tip_rect.y + 26))

        bar_x = tip_rect.x + 8
        bar_y = tip_rect.y + 42
        bar_w = tip_rect.width - 16
        bar_h = 10
        pygame.draw.rect(game.game_screen, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(max(0.0, min(1.0, frac)) * bar_w)
        pygame.draw.rect(game.game_screen, bar_color, (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(game.game_screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)

    elif not game.context_menu['active']:
        ui_buttons = [
            (game.pause_button_rect, tr('ui', "Pause and Save (F2)")),
            (game.forward_button_rect, tr('ui', "Skip time (F3)")),
            (game.status_button_rect, tr('ui', "Player Status (H)")),
            (game.inventory_button_rect, tr('ui', "Inventory (I)")),
            (game.gear_button_rect, tr('ui', "Gear (G)")),
            (getattr(game, 'slots_button_rect', None), tr('ui', "Slots Overview (Y)")),
            (game.nearby_button_rect, tr('ui', "Nearby (N)")),
            (game.messages_button_rect, tr('ui', "Messages (M)")),
            (game.crafting_button_rect, tr('ui', "Crafting (C)")),
            (getattr(game, 'help_button_rect', None), tr('ui', "Help and Tutorial (?)"))
        ]
        
        mouse_pos = game._get_scaled_mouse_pos()
        
        for rect, label in ui_buttons:
            if rect and rect.collidepoint(mouse_pos):
                font_tip = globals().get('font_14', game.assets.get('font'))
                if font_tip:
                    text_surf = font_tip.render(label, True, WHITE)
                    padding = 8
                    width = text_surf.get_width() + padding * 2
                    height = text_surf.get_height() + padding * 2
                    
                    tip_x = mouse_pos[0] + 10
                    tip_y = mouse_pos[1] + 10
                    
                    if tip_x + width > GAME_WIDTH:
                        tip_x = mouse_pos[0] - width - 5
                    if tip_y + height > GAME_HEIGHT:
                        tip_y = mouse_pos[1] - height - 5
                    
                    tooltip_rect = pygame.Rect(tip_x, tip_y, width, height)
                    
                    pygame.draw.rect(game.game_screen, (0, 0, 0, 220), tooltip_rect)
                    pygame.draw.rect(game.game_screen, WHITE, tooltip_rect, 1)
                    game.game_screen.blit(text_surf, (tip_x + padding, tip_y + padding))
                break

    if game.player.is_aiming:
        pygame.mouse.set_visible(False) 
        reticle_img = game.assets.get('aim_reticle')
        if reticle_img:
            reticle_spread_base = 5
            if game.player.active_weapon and game.player.active_weapon.item_type == 'weapon_ranged':
                w_dist = getattr(game.player.active_weapon, 'distance', 10)
                reticle_spread_base = w_dist / 1.5

            base_w = reticle_img.get_width()
            base_h = reticle_img.get_height()
            scale_mult = 2.5 + (game.player.current_aim_factor * reticle_spread_base)
            new_w = max(1, int(base_w * scale_mult))
            new_h = max(1, int(base_h * scale_mult))
            scaled_reticle = pygame.transform.scale(reticle_img, (new_w, new_h))
            rect = scaled_reticle.get_rect(center=game._get_scaled_mouse_pos())
            game.game_screen.blit(scaled_reticle, rect)
    else:
        pygame.mouse.set_visible(True)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LCTRL] or keys[pygame.K_LCTRL]:
             pygame.mouse.set_cursor(game.assets.get('aim_cursor') or pygame.cursors.arrow)
        else:
             pygame.mouse.set_cursor(game.assets.get('custom_cursor') or pygame.cursors.arrow)

    if hasattr(game, 'clock'):
        fps = int(game.clock.get_fps())
        
        # Pull the GAME_VERSION already loaded in config.py
        game_version = getattr(core.data.config, 'GAME_VERSION', 'Unknown')
        
        # Append it to the FPS string
        fps_text = f"FPS: {fps} | Build: {game_version}"
        
        font = game.assets.get('font')
        if font:
            fps_surface = font.render(fps_text, True, (255, 255, 255))
            fps_rect = fps_surface.get_rect(bottomright=(game.game_screen.get_width() - 5, game.game_screen.get_height() - 5))
            game.game_screen.blit(fps_surface, fps_rect)
    
    if hasattr(game, 'virtual_controller') and getattr(game.virtual_controller, 'enabled', False):
        game.virtual_controller.draw(game.game_screen)