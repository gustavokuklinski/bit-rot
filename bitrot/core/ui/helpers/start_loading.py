# core/ui/helpers/start_loading.py

import os
import pygame
from core.data.config import GAME_WIDTH, GAME_HEIGHT, WHITE, SPRITE_PATH, BASE_DIR, UI_SCALE, font_16
from core.data.localization import tr

_LOADING_BG_CACHE = None

def _get_loading_bg():
    """Loads, scales, and caches chunk_load.jpg as the loading screen background."""
    global _LOADING_BG_CACHE
    if _LOADING_BG_CACHE is not None:
        return _LOADING_BG_CACHE

    fname = 'chunk_load.jpg'
    candidates = [
        os.path.join(SPRITE_PATH, 'ui', fname),
        os.path.join(BASE_DIR, 'data.rot', 'lib', 'sprites', 'ui', fname),
        os.path.abspath(os.path.join('data.rot', 'lib', 'sprites', 'ui', fname))
    ]

    for path in candidates:
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert()
                _LOADING_BG_CACHE = pygame.transform.scale(img, (GAME_WIDTH, GAME_HEIGHT))
                return _LOADING_BG_CACHE
            except Exception as e:
                print(f"[Loading] Error loading background {path}: {e}")

    _LOADING_BG_CACHE = None
    return None

def draw_loading_screen(surface, is_done, mouse_pos, events=None, is_main_menu_help=False, game=None):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_x = GAME_WIDTH // 2
    bottom_y = GAME_HEIGHT - S(60)
    current_time = pygame.time.get_ticks()

    # 1. Background image (chunk_load.jpg) with bottom vignette
    bg = _get_loading_bg()
    if bg:
        surface.blit(bg, (0, 0))
        vignette = pygame.Surface((GAME_WIDTH, S(140)), pygame.SRCALPHA)
        vignette.fill((0, 0, 0, 160))
        surface.blit(vignette, (0, GAME_HEIGHT - S(140)))
    else:
        surface.fill((20, 20, 20))

    # 2. Loading Dots or "Click to start" Button
    if not is_done:
        dots = "." * ((current_time // 350) % 4)
        loading_text = f"{tr('ui', 'Loading')}{dots}"
        text_surf = font_16.render(loading_text, False, WHITE)

        pill_rect = text_surf.get_rect(center=(center_x, bottom_y)).inflate(S(40), S(16))
        pill_surf = pygame.Surface((pill_rect.width, pill_rect.height), pygame.SRCALPHA)
        pill_surf.fill((0, 0, 0, 180))
        surface.blit(pill_surf, pill_rect.topleft)
        pygame.draw.rect(surface, (80, 80, 80), pill_rect, 1, border_radius=6)

        surface.blit(text_surf, text_surf.get_rect(center=pill_rect.center))
        return None
    else:
        btn_w, btn_h = S(340), S(48)
        btn_rect = pygame.Rect(0, 0, btn_w, btn_h)
        btn_rect.center = (center_x, bottom_y)

        is_hovered = btn_rect.collidepoint(mouse_pos)
        if is_hovered and not getattr(game, '_start_btn_hovered', False):
            if game and hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
            if game:
                game._start_btn_hovered = True
        elif not is_hovered and game:
            game._start_btn_hovered = False

        bg_color = (0, 150, 0) if is_hovered else (0, 100, 0)
        border_color = (120, 255, 120) if is_hovered else WHITE

        pygame.draw.rect(surface, bg_color, btn_rect, border_radius=6)
        pygame.draw.rect(surface, border_color, btn_rect, 1, border_radius=6)

        btn_txt = font_16.render(tr('ui', "Click to start"), False, WHITE)
        surface.blit(btn_txt, btn_txt.get_rect(center=btn_rect.center))
        return btn_rect