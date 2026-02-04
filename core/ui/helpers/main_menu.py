import pygame
from core.data.config import *
from datetime import datetime
_logo_img = None

def draw_btn(surface, rect, text, mouse_pos, enabled=True):
    """Helper to draw a standardized menu button."""
    is_hovered = rect.collidepoint(mouse_pos)
    
    # Colors
    if not enabled:
        bg_color = (40, 40, 40)
        text_color = (100, 100, 100)

    else:
        bg_color = (80, 80, 80) if is_hovered else (60, 60, 60)
        text_color = WHITE

    # Draw Button Body
    pygame.draw.rect(surface, bg_color, rect, border_radius=6)

    
    # Draw Text
    txt_surf = large_font.render(text, True, text_color)
    txt_rect = txt_surf.get_rect(center=rect.center)
    surface.blit(txt_surf, txt_rect)

def draw_menu(screen, mouse_pos, has_save=False):
    global _logo_img
    screen.fill(DARK_GRAY)

    # --- 1. Draw Logo ---
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load('./game/icons/logo.png').convert_alpha()
            # Scale logo preserving aspect ratio
            target_w = 500
            scale_factor = target_w / _logo_img.get_width()
            target_h = int(_logo_img.get_height() * scale_factor)
            _logo_img = pygame.transform.scale(_logo_img, (target_w, target_h))
    except Exception:
        _logo_img = None

    if _logo_img:
        # Position logo in upper 3rd
        logo_rect = _logo_img.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT * 0.3))
        screen.blit(_logo_img, logo_rect)
    else:
        # Fallback text
        title_text = title_font.render("Bit Rot", True, RED)
        title_rect = title_text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT * 0.25))
        screen.blit(title_text, title_rect)


    # --- 2. Button Layout ---
    # Layout configuration
    btn_width = 400
    btn_height = 50
    spacing = 20
    
    center_x = GAME_WIDTH // 2
    start_y = GAME_HEIGHT * 0.55 # Start slightly below middle

    # 1. Load Game Button (Top)
    load_rect = pygame.Rect(center_x - btn_width // 2, start_y, btn_width, btn_height)
    draw_btn(screen, load_rect, "Load Game", mouse_pos, enabled=has_save)

    # 2. New Game Button (Middle)
    start_rect = pygame.Rect(center_x - btn_width // 2, load_rect.bottom + spacing, btn_width, btn_height)
    draw_btn(screen, start_rect, "New Game", mouse_pos)

    # 3. Settings & Quit Buttons (Bottom, split)
    split_width = (btn_width - spacing) // 2
    settings_rect = pygame.Rect(center_x - btn_width // 2, start_rect.bottom + spacing, split_width, btn_height)
    quit_rect = pygame.Rect(settings_rect.right + spacing, start_rect.bottom + spacing, split_width, btn_height)

    draw_btn(screen, settings_rect, "Settings", mouse_pos)
    draw_btn(screen, quit_rect, "Quit", mouse_pos)

    # --- 3. Footer ---
    current_year = datetime.now().year
    footer_str = f"Developed by: Gustavo Kuklinski - All Rights Reserved - 2025 - {current_year} | version: {GAME_VERSION}"
    footer_text = font_notification.render(footer_str, True, (100, 100, 100))
    footer_rect = footer_text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT - 20))
    screen.blit(footer_text, footer_rect)

    # Return rects for click handling
    # Note: We return load_rect even if disabled so the main loop can decide to ignore it
    return start_rect, load_rect, settings_rect, quit_rect

