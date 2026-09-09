import pygame
import math
from core.data.config import TILE_SIZE

def draw_lighting(game, surface, offset_x, offset_y, view_w, view_h):
    if not hasattr(game, 'light_mask_cache'): game.light_mask_cache = {}
    if len(game.light_mask_cache) > 256:
        keys = list(game.light_mask_cache.keys())
        for key in keys[:-256]: del game.light_mask_cache[key]

    divisor = 2
    low_res_w = max(1, view_w // divisor)
    low_res_h = max(1, view_h // divisor)

    if not hasattr(game, 'light_mask_low_cache') or game.light_mask_low_cache.get_size() != (low_res_w, low_res_h):
        game.light_mask_low_cache = pygame.Surface((low_res_w, low_res_h)).convert()
        
    map_h = len(game.map_data) if hasattr(game, 'map_data') and game.map_data else 0
    map_w = len(game.map_data[0]) if map_h > 0 else 0
    exp_w = max(1, (map_w * TILE_SIZE) // divisor)
    exp_h = max(1, (map_h * TILE_SIZE) // divisor)
    curr_map = getattr(game.map_manager, 'current_map_filename', 'unknown')
    
    if not hasattr(game, 'world_explored_mask') or game.world_explored_mask.get_size() != (exp_w, exp_h) or getattr(game, 'explored_map_name', '') != curr_map:
        game.world_explored_mask = pygame.Surface((exp_w, exp_h)).convert()
        game.world_explored_mask.fill((0, 0, 0))
        game.explored_map_name = curr_map

    ambient = int(game.world_time.current_ambient_light)
    light_mask_low = game.light_mask_low_cache
    light_mask_low.fill((0, 0, 0))

    light_texture = game.assets.get('light_texture')
    light_sources = []

    if light_texture:
        try:
            radius_world_pixels = game.player_view_radius
            radius_view_pixels = int(radius_world_pixels)

            if radius_view_pixels > 0:
                radius_low = max(16, round((radius_view_pixels // 2) / 16) * 16)
                p_screen_x = (game.player.rect.centerx + offset_x) / 2
                p_screen_y = (game.player.rect.centery + offset_y) / 2

                day_glow_brightness = max(50, ambient // 2) 
                day_glow_surf = pygame.transform.scale(light_texture, (radius_low * 2, radius_low * 2))
                day_glow_surf.fill((day_glow_brightness, day_glow_brightness, day_glow_brightness), special_flags=pygame.BLEND_RGBA_MULT)
                day_glow_rect = day_glow_surf.get_rect(center=(p_screen_x, p_screen_y))
                light_mask_low.blit(day_glow_surf, day_glow_rect, special_flags=pygame.BLEND_RGB_ADD)

                view_brightness = max(50, ambient)
                cache_key_cone = ('soft_cone_tex', radius_low, view_brightness)
                if cache_key_cone not in game.light_mask_cache:
                    cone_img = game.assets.get('cone_texture', light_texture)
                    scaled_cone = pygame.transform.smoothscale(cone_img, (radius_low * 2, radius_low * 2))
                    scaled_cone.fill((view_brightness, view_brightness, view_brightness), special_flags=pygame.BLEND_RGBA_MULT)
                    game.light_mask_cache[cache_key_cone] = scaled_cone

                base_cone_tex = game.light_mask_cache[cache_key_cone]
                aim_angle_degrees = math.degrees(getattr(game.player, 'aim_angle', 0))
                rotated_cone = pygame.transform.rotate(base_cone_tex, aim_angle_degrees)
                light_mask_low.blit(rotated_cone, rotated_cone.get_rect(center=(p_screen_x, p_screen_y)), special_flags=pygame.BLEND_RGB_ADD)

                shadow_mask = pygame.Surface((low_res_w, low_res_h))
                shadow_mask.fill((255, 255, 255))
                p_pos_low = (p_screen_x, p_screen_y)
                
                for ob in getattr(game, 'screen_obstacles', []):
                    gx = ob.x // TILE_SIZE
                    gy = ob.y // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    if tile_def and tile_def.get('is_visible'): continue

                    ob_low_x, ob_low_y = (ob.x + offset_x) / 2, (ob.y + offset_y) / 2
                    ob_w_low, ob_h_low = ob.width / 2, ob.height / 2
                    corners = [(ob_low_x, ob_low_y), (ob_low_x + ob_w_low, ob_low_y), (ob_low_x + ob_w_low, ob_low_y + ob_h_low), (ob_low_x, ob_low_y + ob_h_low)]
                    
                    for i in range(4):
                        p1, p2 = corners[i], corners[(i + 1) % 4]
                        mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                        edge_vec_x, edge_vec_y = mid_x - p_pos_low[0], mid_y - p_pos_low[1]
                        edge_dx, edge_dy = p2[0] - p1[0], p2[1] - p1[1]
                        normal = (-edge_dy, edge_dx)
                        
                        if (normal[0] * edge_vec_x + normal[1] * edge_vec_y) < 0:
                            shadow_dist = radius_low * 1.5 
                            v1_x, v1_y = p1[0] - p_pos_low[0], p1[1] - p_pos_low[1]
                            v2_x, v2_y = p2[0] - p_pos_low[0], p2[1] - p_pos_low[1]
                            mag1, mag2 = math.hypot(v1_x, v1_y) or 1, math.hypot(v2_x, v2_y) or 1
                            proj1 = (p1[0] + (v1_x / mag1) * shadow_dist, p1[1] + (v1_y / mag1) * shadow_dist)
                            proj2 = (p2[0] + (v2_x / mag2) * shadow_dist, p2[1] + (v2_y / mag2) * shadow_dist)
                            pygame.draw.polygon(shadow_mask, (0, 0, 0), [p1, p2, proj2, proj1])
                
                shrunk = pygame.transform.smoothscale(shadow_mask, (max(1, low_res_w // 4), max(1, low_res_h // 4)))
                blurred_shadows = pygame.transform.smoothscale(shrunk, (low_res_w, low_res_h))
                light_mask_low.blit(blurred_shadows, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

                current_vision = light_mask_low.copy()
                current_vision.fill((40, 40, 40), special_flags=pygame.BLEND_RGB_MIN)
                game.world_explored_mask.blit(current_vision, (int(-offset_x // divisor), int(-offset_y // divisor)), special_flags=pygame.BLEND_RGB_MAX)
                light_mask_low.blit(game.world_explored_mask, (int(offset_x // divisor), int(offset_y // divisor)), special_flags=pygame.BLEND_RGB_MAX)

        except Exception as e: print(f"Error drawing player vision: {e}")

    for inv in [game.player.belt, game.player.inventory]:
        for item in inv:
            if getattr(item, 'state', 'off') == 'on': light_sources.append({'item': item, 'owner': 'player'})

    for item in game.visible_items:
         if getattr(item, 'state', 'off') == 'on': light_sources.append({'item': item, 'owner': 'ground'})
    
    if hasattr(game, 'vehicles'):
        for vehicle in game.vehicles:
            if getattr(vehicle, 'lights', 'off') == 'on' and vehicle.battery > 0: light_sources.append({'item': vehicle, 'owner': 'vehicle'})

    for container in game.visible_containers:
        if getattr(container, 'item_type', '') == 'vehicle' and not any(ls['item'] == container for ls in light_sources):
             if getattr(container, 'lights', 'off') == 'on' and container.battery > 0: light_sources.append({'item': container, 'owner': 'vehicle'})

    if light_texture:
        screen_rect = pygame.Rect(-offset_x, -offset_y, view_w, view_h)
        for light_info in light_sources:
            light = light_info['item']
            radius_world = getattr(light, 'current_light_radius', 0)
            if radius_world <= 0: continue
            lx, ly = (game.player.rect.centerx, game.player.rect.centery) if light_info['owner'] == 'player' else (light.rect.centerx, light.rect.centery)
            if not screen_rect.inflate(radius_world*2, radius_world*2).collidepoint(lx, ly): continue

            radius_low = max(16, round((int(radius_world / 2)) / 16) * 16)
            try:
                cache_key = ('light', radius_low)
                if cache_key not in game.light_mask_cache:
                    game.light_mask_cache[cache_key] = pygame.transform.scale(light_texture, (radius_low * 2, radius_low * 2))
                scaled_light_tex = game.light_mask_cache[cache_key]
                light_rect = scaled_light_tex.get_rect()

                if light_info['owner'] == 'player':
                    zoom = getattr(game, 'zoom_level', 1.0)
                    offset_lx = (game.player.facing_direction[0] * TILE_SIZE / zoom) * 0.375
                    offset_ly = (game.player.facing_direction[1] * TILE_SIZE / zoom) * 0.375
                    light_rect.center = ((game.player.rect.centerx + offset_x) / 2 + offset_lx, (game.player.rect.centery + offset_y) / 2 + offset_ly)
                else:
                    light_rect.center = ((light.rect.centerx + offset_x) / 2, (light.rect.centery + offset_y) / 2)
                light_mask_low.blit(scaled_light_tex, light_rect, special_flags=pygame.BLEND_RGBA_ADD)
            except Exception: pass

        if getattr(game.world_time, 'state', 'DAY') != 'DAY':
            for light in game.map_lights:
                if not light.get('active', True) or ('rect' in light and not screen_rect.colliderect(light['rect'])): continue
                try:
                    cache_key = ('map_light_darkened', 32)
                    if cache_key not in game.light_mask_cache:
                        base_scaled = pygame.transform.scale(light_texture, (64, 64))
                        base_scaled.fill((80, 80, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)
                        game.light_mask_cache[cache_key] = base_scaled
                    
                    light_rect = game.light_mask_cache[cache_key].get_rect(center=((light['rect'].centerx + offset_x) / 2, (light['rect'].centery + offset_y) / 2))
                    light_mask_low.blit(game.light_mask_cache[cache_key], light_rect, special_flags=pygame.BLEND_RGBA_ADD)
                except Exception: pass

    if not hasattr(game, 'light_upscaled_cache') or game.light_upscaled_cache.get_size() != (view_w, view_h):
        game.light_upscaled_cache = pygame.Surface((view_w, view_h)).convert()
    pygame.transform.scale(light_mask_low, (view_w, view_h), game.light_upscaled_cache)
    surface.blit(game.light_upscaled_cache, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)