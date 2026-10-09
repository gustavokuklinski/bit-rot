# core/states/chunk_loading.py

import os
import pygame
from core.data.config import GAME_WIDTH, GAME_HEIGHT, WHITE, BLACK, SPRITE_PATH, BASE_DIR, font_16
from core.data.localization import tr

_CHUNK_BG_CACHE = {}

def _get_chunk_bg(bg_type):
    """Loads, scales, and caches the transition background image."""
    if not bg_type:
        return None

    if bg_type in _CHUNK_BG_CACHE:
        return _CHUNK_BG_CACHE[bg_type]

    filenames = {
        'boat': 'chunk_boat.jpg',
        'layer': 'chunk_layer.jpg',
        'island': 'chunk_island.jpg',
    }
    fname = filenames.get(bg_type)
    if not fname:
        return None

    candidates = [
        os.path.join(SPRITE_PATH, 'ui', fname),
        os.path.join(BASE_DIR, 'data.rot', 'lib', 'sprites', 'ui', fname),
    ]

    for path in candidates:
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert()
                scaled = pygame.transform.scale(img, (GAME_WIDTH, GAME_HEIGHT))
                _CHUNK_BG_CACHE[bg_type] = scaled
                return scaled
            except Exception as e:
                print(f"[ChunkLoading] Error loading background {path}: {e}")

    _CHUNK_BG_CACHE[bg_type] = None
    return None

def _finalize_chunk_loading(game):
    """Resets physics, timers, and returns state to PLAYING cleanly."""
    game._chunk_load_timer = None
    game._chunk_loading_title = None
    game._chunk_loading_bg_type = None
    game._chunk_btn_hovered = False
    game.game_state = 'PLAYING'
    game.dt_ms = 16
    game.dt_mult = 1.0
    game.clock.tick(60)

    current_ticks = pygame.time.get_ticks()
    if hasattr(game, 'world_time') and game.world_time:
        game.world_time.last_update_time = current_ticks

    if getattr(game, 'player', None):
        import time
        game.player.last_decay_time = time.time()
        game.player.vx = 0
        game.player.vy = 0
        game.player.is_moving = False

def run_chunk_loading(game):
    current_time = pygame.time.get_ticks()
    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    events = game.get_events()

    # 1. Initialize timer on first frame
    if not hasattr(game, '_chunk_load_timer') or game._chunk_load_timer is None:
        game._chunk_load_timer = current_time

    MIN_LOADING_DURATION_MS = 1000
    elapsed = current_time - game._chunk_load_timer
    is_ready = elapsed >= MIN_LOADING_DURATION_MS

    # 2. Render Background (Dynamic Image or Dark Fallback)
    bg_type = getattr(game, '_chunk_loading_bg_type', None)
    bg_surface = _get_chunk_bg(bg_type)

    if bg_surface:
        game.game_screen.blit(bg_surface, (0, 0))
        # Subtle vignette overlay to keep bottom controls readable
        vignette = pygame.Surface((GAME_WIDTH, 140), pygame.SRCALPHA)
        vignette.fill((0, 0, 0, 160))
        game.game_screen.blit(vignette, (0, GAME_HEIGHT - 140))
    else:
        game.game_screen.fill((20, 20, 20))

    center_x = GAME_WIDTH // 2
    bottom_y = GAME_HEIGHT - 60  # Aligned center-bottom

    loading_title = getattr(game, '_chunk_loading_title', None) or tr('ui', 'Loading Chunk')
    btn_rect = None

    if not is_ready:
        # 3. Loading Dots at Center-Bottom
        dots = "." * ((current_time // 350) % 4)
        loading_text = f"{loading_title}{dots}"
        
        # Pill backing
        text_surf = font_16.render(loading_text, False, WHITE)
        pill_rect = text_surf.get_rect(center=(center_x, bottom_y)).inflate(40, 16)
        pill_surf = pygame.Surface((pill_rect.width, pill_rect.height), pygame.SRCALPHA)
        pill_surf.fill((0, 0, 0, 180))
        game.game_screen.blit(pill_surf, pill_rect.topleft)
        pygame.draw.rect(game.game_screen, (80, 80, 80), pill_rect, 1, border_radius=6)

        game.game_screen.blit(text_surf, text_surf.get_rect(center=pill_rect.center))
    else:
        # 4. Ready State: "Click to go" Button Aligned at Center-Bottom
        btn_w, btn_h = 340, 48
        btn_rect = pygame.Rect(0, 0, btn_w, btn_h)
        btn_rect.center = (center_x, bottom_y)

        is_hovered = btn_rect.collidepoint(mouse_pos)

        # Hover audio feedback
        if is_hovered and not getattr(game, '_chunk_btn_hovered', False):
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
            game._chunk_btn_hovered = True
        elif not is_hovered:
            game._chunk_btn_hovered = False

        bg_color = (0, 150, 0) if is_hovered else (0, 110, 0)
        border_color = (120, 255, 120) if is_hovered else WHITE

        pygame.draw.rect(game.game_screen, bg_color, btn_rect, border_radius=6)
        pygame.draw.rect(game.game_screen, border_color, btn_rect, 1, border_radius=6)

        btn_txt = font_16.render(tr('ui', "Click to go"), False, WHITE)
        game.game_screen.blit(btn_txt, btn_txt.get_rect(center=btn_rect.center))

    # 5. Event Handling
    for event in events:
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            game.running = False
            return

        if is_ready:
            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
                if btn_rect and btn_rect.collidepoint(mouse_pos):
                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_ui_hover()
                    _finalize_chunk_loading(game)
                    return

            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                _finalize_chunk_loading(game)
                return

            elif event.type == pygame.JOYBUTTONDOWN and getattr(event, 'button', -1) == 0:
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                _finalize_chunk_loading(game)
                return

    game._update_screen()