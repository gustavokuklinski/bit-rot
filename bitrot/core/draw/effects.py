import pygame
import math
import random
from core.data.config import TILE_SIZE, GAME_WIDTH, GAME_HEIGHT, GAME_OFFSET_X, WHITE, BLACK, SPRITE_PATH

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
    # Get current dynamic dimensions from camera.py
    dyn_w = getattr(game, 'dynamic_w', GAME_WIDTH)
    dyn_h = getattr(game, 'dynamic_h', GAME_HEIGHT)
    v_left = getattr(game, 'viewport_left_offset', 0)

    # Define the actual game viewport area to prevent effects from leaking into UI/Modals
    game_viewport_rect = pygame.Rect(v_left, 0, dyn_w, dyn_h)

    if getattr(game.world_time, 'weather', 'CLEAR') == 'RAIN':
        is_under_roof = False
        if getattr(game, 'roof_data', None) and game.player:
            px, py = int(game.player.rect.centerx // TILE_SIZE), int(game.player.rect.centery // TILE_SIZE)
            if 0 <= py < len(game.roof_data) and 0 <= px < len(game.roof_data[py]):
                r_key = game.roof_data[py][px]
                if r_key and r_key != ' ': is_under_roof = True
        
        if not is_under_roof and getattr(game, 'current_layer_index', 1) != 2:
            try:
                if not hasattr(game, 'rain_texture') or game.rain_texture.get_width() != dyn_w:
                    game.rain_texture = pygame.transform.scale(game.assets.get('rain_texture'), (dyn_w, dyn_h)).convert_alpha()
            except Exception: 
                game.rain_texture = None

            if game.rain_texture:
                # --- FIX: CLIP THE RAIN ---
                # Only allow drawing within the game viewport rectangle
                game.game_screen.set_clip(game_viewport_rect)
                
                if not hasattr(game, 'rain_offset'): game.rain_offset = 0
                game.rain_offset = (game.rain_offset + 15 * getattr(game, 'dt_mult', 1.0)) % dyn_h
                
                game.game_screen.blit(game.rain_texture, (v_left, game.rain_offset))
                game.game_screen.blit(game.rain_texture, (v_left, game.rain_offset - dyn_h))
                
                # IMPORTANT: Reset clip to None so other UI elements can draw normally
                game.game_screen.set_clip(None)

    anxiety_level = getattr(game.player, 'anxiety', 0)
    if anxiety_level > 10:
        try:
            if not hasattr(game, 'crt_texture') or game.crt_texture.get_width() != dyn_w + 20:
                game.crt_texture = pygame.transform.scale(game.assets.get('crt_texture'), (dyn_w + 20, dyn_h + 20)).convert_alpha()
        except Exception: 
            game.crt_texture = None
            
        if game.crt_texture:
            # I recommend clipping the CRT too, so shaking doesn't leak into modals
            game.game_screen.set_clip(game_viewport_rect)
            shake = int((anxiety_level / 100) * 5)
            game.game_screen.blit(game.crt_texture, (v_left + random.randint(-shake, shake) - 10, random.randint(-shake, shake) - 10))
            game.game_screen.set_clip(None)

     # --- FIXED GUN FLASH BLOCK ---
    if game.player.gun_flash_timer > 0:
        # 1. Check if the current weapon is one that SHOULD NOT have a flash
        show_flash = True
        if hasattr(game.player, 'weapon') and game.player.weapon:
            weapon_name = getattr(game.player.weapon, 'name', '')
            if weapon_name in ["Slingshot", "Bow"]:
                show_flash = False

        # 2. Only draw if the weapon is not a Slingshot or Bow
        if show_flash:
            screen_x = ((game.player.rect.centerx + offset_x) * zoom) + GAME_OFFSET_X + game.viewport_left_offset
            screen_y = ((game.player.rect.centery + offset_y) * zoom)
            flash_dist = (TILE_SIZE * 1.4) * zoom 
            flash_x = screen_x + math.cos(game.player.aim_angle) * flash_dist
            flash_y = screen_y - math.sin(game.player.aim_angle) * flash_dist
            
            light_tex = game.assets.get('light_texture')
            if light_tex:
                # STRETCH
                base_size = max(8, int(8 * zoom))
                width = int(base_size * 0.8)
                height = int(base_size * 0.8)
                
                small_flash = pygame.transform.smoothscale(light_tex, (width, height))
                
                # COLOR (Yellowish-Orange)
                color_surf = pygame.Surface((width, height))
                color_surf.fill((255, 180, 50)) 
                color_surf.blit(small_flash, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                small_flash = color_surf
                
                # OPACITY (~60% and fade)
                opacity = min(153, int(game.player.gun_flash_timer * 50))
                small_flash.set_alpha(opacity)
                
                # ROTATE to match aim angle
                rotated_flash = pygame.transform.rotate(small_flash, -math.degrees(game.player.aim_angle))
                flash_rect = rotated_flash.get_rect(center=(int(flash_x), int(flash_y)))
                
                # BLEND additive to remove black borders
                game.game_screen.blit(rotated_flash, flash_rect, special_flags=pygame.BLEND_RGB_ADD)
            else:
                pygame.draw.circle(game.game_screen, WHITE, (int(flash_x), int(flash_y)), 1)
            
        # Always decrement the timer so it doesn't get stuck at > 0 for these weapons
        game.player.gun_flash_timer -= getattr(game, 'dt_mult', 1.0)
    # -----------------------------

    if game.player and game.player.chat_text and game.player.chat_timer > 0:
        screen_x = ((game.player.rect.centerx + offset_x) * zoom) + GAME_OFFSET_X
        screen_y = ((game.player.rect.centery + offset_y) * zoom)
        font_bubble = game.assets.get('font')
        text_surf = font_bubble.render(game.player.chat_text, True, BLACK)
        bubble_rect = pygame.Rect(screen_x - ((text_surf.get_width() + 20) / 2) + (TILE_SIZE * zoom / 2) + game.viewport_left_offset, screen_y - text_surf.get_height() - 25, text_surf.get_width() + 20, text_surf.get_height() + 10)
        pygame.draw.rect(game.game_screen, WHITE, bubble_rect, border_radius=8)
        pygame.draw.polygon(game.game_screen, WHITE, [(screen_x + (TILE_SIZE * zoom / 2) - 6, bubble_rect.bottom), (screen_x + (TILE_SIZE * zoom / 2) + 6, bubble_rect.bottom), (screen_x + (TILE_SIZE * zoom / 2), bubble_rect.bottom + 8)])
        game.game_screen.blit(text_surf, text_surf.get_rect(center=bubble_rect.center))