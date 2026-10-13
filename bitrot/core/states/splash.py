# core/states/splash.py

import os
import math
import pygame
import core.data.config
from core.data.config import GAME_WIDTH, GAME_HEIGHT, BASE_DIR, SOUND_PATH, DARK_GRAY

def _resolve_asset_path(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def finish_splash(game):
    """Stops the splash audio, starts background music, and enters MENU."""
    # Stop the splash sound channel if still playing
    if hasattr(game, '_splash_channel') and game._splash_channel:
        try:
            game._splash_channel.stop()
        except Exception:
            pass
        game._splash_channel = None

    # Start the main menu music cleanly
    if core.data.config.UI_BACKGROUND_MUSIC and not pygame.mixer.music.get_busy():
        music_path = os.path.join(BASE_DIR, "data.rot", "lib", "sfx", "ui", "music.ogg")
        game.sound_manager.play_music(music_path, volume=core.data.config.VOLUME_MUSIC)

    # Clean up temporary splash attributes
    for attr in ('_splash_start_time', '_splash_logo_surf', '_splash_logo_rect', '_splash_sound_played'):
        if hasattr(game, attr):
            delattr(game, attr)

    game.game_state = 'MENU'

def run_splash(game):
    current_time = pygame.time.get_ticks()

    # 1. Initialize state on the first frame
    if not hasattr(game, '_splash_start_time'):
        game._splash_start_time = current_time

        # Locate publisher logo
        logo_candidates = [
            os.path.join(BASE_DIR, "data.rot", "lib", "kukaroach", "kukaroach.png"),
            os.path.abspath("data.rot/lib/kukaroach/kukaroach.png"),
            os.path.join(core.data.config.SPRITE_PATH, "ui", "kukaroach.png")
        ]
        logo_path = _resolve_asset_path(logo_candidates)

        logo_surf = None
        if logo_path:
            try:
                raw_img = pygame.image.load(logo_path).convert_alpha()
                lw, lh = raw_img.get_size()

                # Adjust this percentage to control the size:
                # 0.25 = small (~180px tall), 0.30 = medium-small, 0.35 = medium
                TARGET_SCREEN_PERCENT = 0.20  

                max_w = int(GAME_WIDTH * TARGET_SCREEN_PERCENT)
                max_h = int(GAME_HEIGHT * TARGET_SCREEN_PERCENT)

                # Always scale proportionally to fit within max bounds
                scale = min(max_w / lw, max_h / lh)
                target_w = max(1, int(lw * scale))
                target_h = max(1, int(lh * scale))

                logo_surf = pygame.transform.smoothscale(raw_img, (target_w, target_h))
            except Exception as e:
                print(f"[Splash] Error loading logo: {e}")

        game._splash_logo_surf = logo_surf
        if logo_surf:
            game._splash_logo_rect = logo_surf.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2))
        else:
            game._splash_logo_rect = None

        # Locate and play publisher sound
        sound_candidates = [
            os.path.join(BASE_DIR, "data.rot", "lib", "kukaroach", "kukaroach.ogg"),

            os.path.abspath("data.rot/lib/kukaroach/kukaroach.ogg")
        ]
        sound_path = _resolve_asset_path(sound_candidates)

        if sound_path and pygame.mixer.get_init():
            try:
                splash_sound = pygame.mixer.Sound(sound_path)
                splash_sound.set_volume(getattr(core.data.config, 'VOLUME_ITEMS', 0.8))
                game._splash_channel = splash_sound.play()
            except Exception as e:
                print(f"[Splash] Error playing sound: {e}")
                game._splash_channel = None

    # 2. Timing and Smooth Cosine Fade Calculation
    FADE_IN_MS = 1000   # 1.0s fade in
    HOLD_MS = 1500      # 1.5s visible hold
    FADE_OUT_MS = 1000  # 1.0s fade out
    TOTAL_DURATION_MS = FADE_IN_MS + HOLD_MS + FADE_OUT_MS

    elapsed = current_time - game._splash_start_time

    if elapsed >= TOTAL_DURATION_MS:
        finish_splash(game)
        return

    if elapsed < FADE_IN_MS:
        progress = elapsed / float(FADE_IN_MS)
        ease = 0.5 * (1.0 - math.cos(math.pi * progress))
        alpha = int(255 * ease)
    elif elapsed < (FADE_IN_MS + HOLD_MS):
        alpha = 255
    else:
        fade_out_elapsed = elapsed - (FADE_IN_MS + HOLD_MS)
        progress = 1.0 - (fade_out_elapsed / float(FADE_OUT_MS))
        ease = 0.5 * (1.0 - math.cos(math.pi * progress))
        alpha = int(255 * ease)

    alpha = max(0, min(255, alpha))

    # 3. Render
    game.game_screen.fill(DARK_GRAY)

    if game._splash_logo_surf and alpha > 0:
        faded_logo = game._splash_logo_surf.copy()
        faded_logo.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        game.game_screen.blit(faded_logo, game._splash_logo_rect)

    # 4. Handle Skip Input (Any key, mouse click, or joystick button)
    for event in game.get_events():
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            game.running = False
            return

        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
            finish_splash(game)
            return

    game._update_screen()