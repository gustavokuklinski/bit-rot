import pygame
import os
from core.data.config import *
from datetime import datetime
from core.data.localization import tr
from core.data.config import BASE_DIR

_logo_img = None

def draw_btn(surface, rect, text, mouse_pos, enabled=True):
    """Helper to draw a standardized menu button (Shared style)."""
    is_hovered = rect.collidepoint(mouse_pos)
    
    if not enabled:
        bg_color = (40, 40, 40)
        text_color = (100, 100, 100)
    else:
        bg_color = (80, 80, 80) if is_hovered else (60, 60, 60)
        text_color = WHITE

    pygame.draw.rect(surface, bg_color, rect, border_radius=6)
    
    txt_surf = font_14.render(text, True, text_color)
    txt_rect = txt_surf.get_rect(center=rect.center)
    surface.blit(txt_surf, txt_rect)

# --- CHANGED: Added days_survived parameter ---
def draw_game_over(screen, zombies_killed, days_survived, mouse_pos):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_offset_x = (GAME_WIDTH - S(1280)) // 2
    center_offset_y = (GAME_HEIGHT - S(720)) // 2

    screen.fill(DARK_GRAY)
    
    global _logo_img
    try:
        if _logo_img is None:
            logo_path = os.path.join(BASE_DIR, 'game', 'icons', 'logo.png')
            _logo_img = pygame.image.load(logo_path).convert_alpha()
            logo_w = S(500)
            logo_h = int(_logo_img.get_height() * (logo_w / _logo_img.get_width()))
            _logo_img = pygame.transform.scale(_logo_img, (logo_w, logo_h))
    except Exception:
        _logo_img = None

    center_x = GAME_WIDTH // 2

    if _logo_img:
        title_rect = _logo_img.get_rect(center=(center_x, center_offset_y + S(180)))
        screen.blit(_logo_img, title_rect)
    else:
        # --- CHANGED: Changed the title text ---
        title_text = font_14.render(tr('ui', "YOU ROTTED"), True, RED)
        title_rect = title_text.get_rect(center=(center_x, center_offset_y + S(180)))
        screen.blit(title_text, title_rect)

    score_text = font_14.render(f"{tr('ui', 'Rotters Dead:')} {zombies_killed}", True, WHITE)
    score_rect = score_text.get_rect(center=(center_x, center_offset_y + S(324)))
    screen.blit(score_text, score_rect)
    
    # --- CHANGED: Render the days survived below the kills ---
    days_text = font_14.render(f"{tr('ui', 'Days Survived:')} {days_survived}", True, WHITE)
    days_rect = days_text.get_rect(center=(center_x, center_offset_y + S(350)))
    screen.blit(days_text, days_rect)

    btn_width = S(400)
    btn_height = S(50)
    start_y = center_offset_y + S(396)

    menu_rect = pygame.Rect(center_x - btn_width // 2, start_y, btn_width, btn_height)
    draw_btn(screen, menu_rect, tr('ui', "Back to Menu"), mouse_pos)

    current_year = datetime.now().year
    footer_str = f"Bit Rot - All Rights Reserved - 2025 - {current_year} | version: {GAME_VERSION}"
    footer_text = font_14.render(footer_str, True, (100, 100, 100))
    footer_rect = footer_text.get_rect(center=(center_x, center_offset_y + S(700)))
    screen.blit(footer_text, footer_rect)

    return menu_rect