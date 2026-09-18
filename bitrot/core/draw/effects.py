# core/draw/effects.py

import pygame
import math
import random
from core.data.config import TILE_SIZE, GAME_WIDTH, GAME_HEIGHT, GAME_OFFSET_X, WHITE, BLACK, SPRITE_PATH, font_12

_ease_filter_cache = {}

def get_radial_ease_mask(radius, center_alpha=10, edge_alpha=255):
    """
    Creates a cached radial mask with an S-curve cosine ease falloff.
    - center_alpha: high visibility around the player (clears fog/rain).
    - edge_alpha: full weather intensity at and beyond the view radius.
    """
    q_radius = max(32, int(round(radius / 4.0) * 4))
    cache_key = (q_radius, center_alpha, edge_alpha)
    
    if cache_key in _ease_filter_cache:
        return _ease_filter_cache[cache_key]

    size = q_radius * 2
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    mask.fill((255, 255, 255, edge_alpha))

    step = 3
    for r in range(q_radius, 0, -step):
        t = r / float(q_radius)
        # Cosine ease curve: 0 at center, 1 at edge
        ease = 0.5 * (1.0 - math.cos(math.pi * t))
        alpha = int(center_alpha + (edge_alpha - center_alpha) * ease)
        pygame.draw.circle(mask, (255, 255, 255, alpha), (q_radius, q_radius), r)

    if len(_ease_filter_cache) > 64:
        _ease_filter_cache.clear()

    _ease_filter_cache[cache_key] = mask
    return mask


def draw_world_effects(game, surface, offset_x, offset_y, view_w, view_h):
    player_tile_x = int(game.player.rect.centerx // TILE_SIZE)
    player_tile_y = int(game.player.rect.centery // TILE_SIZE)
    
    is_under_roof = False
    if getattr(game, 'roof_data', None):
        if 0 <= player_tile_y < len(game.roof_data) and 0 <= player_tile_x < len(game.roof_data[player_tile_y]):
            r_key = game.roof_data[player_tile_y][player_tile_x]
            if r_key and r_key != ' ': is_under_roof = True

    roof_hide_radius = 4 if is_under_roof else 1

    if getattr(game, 'roof_data', None):
        chunk_size = getattr(game, 'CHUNK_SIZE', 128)
        map_h = len(game.map_data) if hasattr(game, 'map_data') and game.map_data else 0
        map_w = len(game.map_data[0]) if map_h > 0 else 0

        min_chunk_x = max(0, int(-offset_x // (chunk_size * TILE_SIZE)))
        min_chunk_y = max(0, int(-offset_y // (chunk_size * TILE_SIZE)))
        max_chunk_x = min((map_w // chunk_size) + 1, int((-offset_x + view_w) // (chunk_size * TILE_SIZE)) + 1)
        max_chunk_y = min((map_h // chunk_size) + 1, int((-offset_y + view_h) // (chunk_size * TILE_SIZE)) + 1)

        min_grid_x = max(0, min_chunk_x * chunk_size)
        min_grid_y = max(0, min_chunk_y * chunk_size)
        max_grid_x = min(map_w, max_chunk_x * chunk_size)
        max_grid_y = min(map_h, max_chunk_y * chunk_size)

        hide_min_tx, hide_max_tx = player_tile_x - roof_hide_radius, player_tile_x + roof_hide_radius
        hide_min_ty, hide_max_ty = player_tile_y - roof_hide_radius, player_tile_y + roof_hide_radius

        tm = game.tile_manager
        for gy in range(min_grid_y, max_grid_y):
            for gx in range(min_grid_x, max_grid_x):
                r_key = game.roof_data[gy][gx]
                if r_key and r_key != ' ' and not (hide_min_tx <= gx <= hide_max_tx and hide_min_ty <= gy <= hide_max_ty):
                    r_def = tm.definitions.get(r_key)
                    if r_def: surface.blit(r_def['image'], (int(gx * TILE_SIZE + offset_x), int(gy * TILE_SIZE + offset_y)))

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

        if splash.get('type') == 'explosion':
            if not hasattr(game, 'explosion_img'):
                try: game.explosion_img = pygame.image.load(SPRITE_PATH + 'items/weapon_throw_explosion.png').convert_alpha()
                except: game.explosion_img = None
                    
            if game.explosion_img:
                img = game.explosion_img.copy()
                img.fill((255, 255, 255, base_opacity), special_flags=pygame.BLEND_RGBA_MULT)
                start_x, start_y = int(impact_x - splash['radius']), int(impact_y - splash['radius'])
                end_x, end_y = int(impact_x + splash['radius']), int(impact_y + splash['radius'])
                
                for ty in range(start_y, end_y, TILE_SIZE):
                    for tx in range(start_x, end_x, TILE_SIZE):
                        if math.hypot((tx + TILE_SIZE/2) - impact_x, (ty + TILE_SIZE/2) - impact_y) <= splash['radius']:
                            surface.blit(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)), (tx, ty))
            else: pygame.draw.circle(surface, (255, 100, 0, base_opacity), (int(impact_x), int(impact_y)), int(splash['radius']))
            continue

        for i in range(4):
            offset_dist = (1.0 - fade_factor) * (TILE_SIZE / 3) * random.uniform(0.7, 1.3)
            angle = math.radians(i * 90 + random.randint(-45, 45))
            draw_x, draw_y = impact_x + (math.cos(angle) * offset_dist), impact_y + (math.sin(angle) * offset_dist)
            p_radius = int(splash['radius'] * random.uniform(1.0, 1.5) * (fade_factor * 0.5 + 0.5))
            if p_radius <= 0: continue
            scratch_rect = pygame.Rect(0, 0, p_radius*2, p_radius*2)
            scratch.fill((0,0,0,0), scratch_rect)
            pygame.draw.circle(scratch, (int(SPLASH_COLOR[0] * fade_factor), int(SPLASH_COLOR[1] * fade_factor), int(SPLASH_COLOR[2] * fade_factor), base_opacity), (p_radius, p_radius), p_radius)
            surface.blit(scratch, (int(draw_x - p_radius), int(draw_y - p_radius)), scratch_rect)


def draw_screen_effects(game, offset_x, offset_y, zoom):
    dyn_w = getattr(game, 'dynamic_w', GAME_WIDTH)
    dyn_h = getattr(game, 'dynamic_h', GAME_HEIGHT)
    v_left = getattr(game, 'viewport_left_offset', 0)

    game_viewport_rect = pygame.Rect(v_left, 0, dyn_w, dyn_h)
    dt = getattr(game, 'dt_mult', 1.0)

    # --- ALCOHOL BLUR EFFECT ---
    alcohol = getattr(game.player, 'alcohol_level', 0.0) if game.player else 0.0
    if alcohol >= 5.0 and dyn_w > 0 and dyn_h > 0:
        if not hasattr(game, 'blur_cache_surf') or game.blur_cache_surf.get_size() != (dyn_w, dyn_h):
            game.blur_cache_surf = pygame.Surface((dyn_w, dyn_h))

        game.blur_cache_surf.blit(game.game_screen, (0, 0), game_viewport_rect)

        factor = max(5, min(10, int(5 + (alcohol - 5.0) * 0.8)))
        small_w = max(1, dyn_w // factor)
        small_h = max(1, dyn_h // factor)

        downsampled = pygame.transform.smoothscale(game.blur_cache_surf, (small_w, small_h))
        blurred = pygame.transform.smoothscale(downsampled, (dyn_w, dyn_h))

        sway_time = pygame.time.get_ticks() * 0.0025
        sway_x = int(math.sin(sway_time) * 4)
        sway_y = int(math.cos(sway_time * 0.7) * 3)

        blur_alpha = min(230, int(180 + (alcohol - 5.0) * 10))
        blurred.set_alpha(blur_alpha)

        game.game_screen.set_clip(game_viewport_rect)
        game.game_screen.blit(blurred, (v_left + sway_x, sway_y))
        game.game_screen.set_clip(None)

    # --- WEATHER: FOG, RAIN, RAINING WITH FOG (SMOOTH FADE IN / FADE OUT) ---
    current_weather = getattr(game.world_time, 'weather', 'CLEAR')
    is_cave = getattr(game, 'current_layer_index', 1) == 2

    # Check roof occlusion
    is_under_roof = False
    if getattr(game, 'roof_data', None) and game.player:
        px = int(game.player.rect.centerx // TILE_SIZE)
        py = int(game.player.rect.centery // TILE_SIZE)
        if 0 <= py < len(game.roof_data) and 0 <= px < len(game.roof_data[py]):
            r_key = game.roof_data[py][px]
            if r_key and r_key != ' ':
                is_under_roof = True

    # 1. Target weather opacities
    target_fog = 0.0
    target_rain = 0.0

    if not is_cave:
        if current_weather in ['FOG', 'RAIN_FOG']:
            target_fog = 0.25 if is_under_roof else 1.0  # Faint indoor mist if inside
        if current_weather in ['RAIN', 'RAIN_FOG'] and not is_under_roof:
            target_rain = 1.0

    # 2. Smooth Interpolation (Fade in & Fade out over ~3 seconds)
    if not hasattr(game, 'weather_fog_alpha'): game.weather_fog_alpha = 0.0
    if not hasattr(game, 'weather_rain_alpha'): game.weather_rain_alpha = 0.0

    fade_speed = 0.006 * dt
    if game.weather_fog_alpha < target_fog:
        game.weather_fog_alpha = min(target_fog, game.weather_fog_alpha + fade_speed)
    elif game.weather_fog_alpha > target_fog:
        game.weather_fog_alpha = max(target_fog, game.weather_fog_alpha - fade_speed)

    if game.weather_rain_alpha < target_rain:
        game.weather_rain_alpha = min(target_rain, game.weather_rain_alpha + fade_speed)
    elif game.weather_rain_alpha > target_rain:
        game.weather_rain_alpha = max(target_rain, game.weather_rain_alpha - fade_speed)

    # 3. Render weather if either fog or rain has visible opacity
    if game.weather_fog_alpha > 0.005 or game.weather_rain_alpha > 0.005:
        if not hasattr(game, 'weather_surf') or game.weather_surf.get_size() != (dyn_w, dyn_h):
            game.weather_surf = pygame.Surface((dyn_w, dyn_h), pygame.SRCALPHA)

        weather_surf = game.weather_surf
        weather_surf.fill((0, 0, 0, 0))

        # --- A. FOG LAYER (Atmospheric Muted Gray Cloud Filter) ---
        if game.weather_fog_alpha > 0.005:
            # Subtle, translucent slate-gray ambient base (not washed-out white!)
            base_gray_alpha = int(55 * game.weather_fog_alpha)
            weather_surf.fill((65, 70, 78, base_gray_alpha))

            # Drifting cloudy texture
            try:
                if not hasattr(game, 'fog_texture') or game.fog_texture.get_size() != (dyn_w, dyn_h):
                    raw_fog = game.assets.get('fog_texture')
                    if raw_fog:
                        game.fog_texture = pygame.transform.scale(raw_fog, (dyn_w, dyn_h)).convert_alpha()
                    else:
                        game.fog_texture = None
            except Exception:
                game.fog_texture = None

            if game.fog_texture:
                if not hasattr(game, 'fog_offset_x'): game.fog_offset_x = 0.0
                if not hasattr(game, 'fog_offset_y'): game.fog_offset_y = 0.0

                game.fog_offset_x = (game.fog_offset_x + 0.35 * dt) % dyn_w
                game.fog_offset_y = (game.fog_offset_y + 0.15 * dt) % dyn_h

                fx = int(game.fog_offset_x)
                fy = int(game.fog_offset_y)

                # Soft, visible cloud puffs (modulated alpha, no blinding additive burn)
                cloud_surf = game.fog_texture.copy()
                cloud_alpha = int(105 * game.weather_fog_alpha)
                cloud_surf.fill((160, 170, 180, cloud_alpha), special_flags=pygame.BLEND_RGBA_MULT)

                # 4-quadrant seamless toroidal wrap
                weather_surf.blit(cloud_surf, (fx, fy))
                weather_surf.blit(cloud_surf, (fx - dyn_w, fy))
                weather_surf.blit(cloud_surf, (fx, fy - dyn_h))
                weather_surf.blit(cloud_surf, (fx - dyn_w, fy - dyn_h))

        # --- B. RAIN LAYER (Falling Streaks) ---
        if game.weather_rain_alpha > 0.005:
            try:
                if not hasattr(game, 'rain_texture') or game.rain_texture.get_size() != (dyn_w, dyn_h):
                    raw_rain = game.assets.get('rain_texture')
                    if raw_rain:
                        game.rain_texture = pygame.transform.scale(raw_rain, (dyn_w, dyn_h)).convert_alpha()
                    else:
                        game.rain_texture = None
            except Exception:
                game.rain_texture = None

            if game.rain_texture:
                if not hasattr(game, 'rain_offset'): game.rain_offset = 0.0
                game.rain_offset = (game.rain_offset + 16.0 * dt) % dyn_h

                ro = int(game.rain_offset)
                rain_surf = game.rain_texture.copy()
                rain_alpha = int(170 * game.weather_rain_alpha)
                rain_surf.fill((255, 255, 255, rain_alpha), special_flags=pygame.BLEND_RGBA_MULT)

                weather_surf.blit(rain_surf, (0, ro))
                weather_surf.blit(rain_surf, (0, ro - dyn_h))

        # --- C. PLAYER VIEW RADIUS RADIAL EASE FILTER ---
        if game.player:
            p_vx = int(((game.player.rect.centerx + offset_x) * zoom) + GAME_OFFSET_X)
            p_vy = int((game.player.rect.centery + offset_y) * zoom)
            view_r = int(getattr(game, 'player_view_radius', 12 * TILE_SIZE) * zoom)

            # Center visibility: clear near the player (alpha 10), easing out to 255 at edge
            center_alpha = 10 if game.weather_fog_alpha > 0 else 60
            ease_mask = get_radial_ease_mask(view_r, center_alpha=center_alpha, edge_alpha=255)

            mask_x = p_vx - (ease_mask.get_width() // 2)
            mask_y = p_vy - (ease_mask.get_height() // 2)
            
            # Smoothly cuts out visibility around the player
            weather_surf.blit(ease_mask, (mask_x, mask_y), special_flags=pygame.BLEND_RGBA_MULT)

        # 4. Composite final weather layer to screen
        game.game_screen.set_clip(game_viewport_rect)
        game.game_screen.blit(weather_surf, (v_left, 0))
        game.game_screen.set_clip(None)

    # --- CRT ANXIETY EFFECT ---
    anxiety_level = getattr(game.player, 'anxiety', 0)
    if anxiety_level > 10:
        try:
            if not hasattr(game, 'crt_texture') or game.crt_texture.get_width() != dyn_w + 20:
                game.crt_texture = pygame.transform.scale(game.assets.get('crt_texture'), (dyn_w + 20, dyn_h + 20)).convert_alpha()
        except Exception: 
            game.crt_texture = None
            
        if game.crt_texture:
            game.game_screen.set_clip(game_viewport_rect)
            shake = int((anxiety_level / 100) * 5)
            game.game_screen.blit(game.crt_texture, (v_left + random.randint(-shake, shake) - 10, random.randint(-shake, shake) - 10))
            game.game_screen.set_clip(None)

    # --- GUN FLASH ---
    if game.player.gun_flash_timer > 0:
        show_flash = True
        if hasattr(game.player, 'weapon') and game.player.weapon:
            weapon_name = getattr(game.player.weapon, 'name', '')
            if weapon_name in ["Slingshot", "Bow"]:
                show_flash = False

        if show_flash:
            screen_x = ((game.player.rect.centerx + offset_x) * zoom) + GAME_OFFSET_X + game.viewport_left_offset
            screen_y = ((game.player.rect.centery + offset_y) * zoom)
            flash_dist = (TILE_SIZE * 1.4) * zoom 
            flash_x = screen_x + math.cos(game.player.aim_angle) * flash_dist
            flash_y = screen_y - math.sin(game.player.aim_angle) * flash_dist
            
            light_tex = game.assets.get('light_texture')
            if light_tex:
                base_size = max(8, int(8 * zoom))
                width = int(base_size * 0.8)
                height = int(base_size * 0.8)
                
                small_flash = pygame.transform.smoothscale(light_tex, (width, height))
                
                color_surf = pygame.Surface((width, height))
                color_surf.fill((255, 180, 50)) 
                color_surf.blit(small_flash, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                small_flash = color_surf
                
                opacity = min(153, int(game.player.gun_flash_timer * 50))
                small_flash.set_alpha(opacity)
                
                rotated_flash = pygame.transform.rotate(small_flash, -math.degrees(game.player.aim_angle))
                flash_rect = rotated_flash.get_rect(center=(int(flash_x), int(flash_y)))
                
                game.game_screen.blit(rotated_flash, flash_rect, special_flags=pygame.BLEND_RGB_ADD)
            else:
                pygame.draw.circle(game.game_screen, WHITE, (int(flash_x), int(flash_y)), 1)
            
        game.player.gun_flash_timer -= getattr(game, 'dt_mult', 1.0)