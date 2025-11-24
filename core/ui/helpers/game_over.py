import pygame
from core.data.config import *
from datetime import datetime

_logo_img = None

def draw_btn(surface, rect, text, mouse_pos, enabled=True):
    """Helper to draw a standardized menu button (Shared style)."""
    is_hovered = rect.collidepoint(mouse_pos)
    
    # Colors matching Main Menu
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

def draw_game_over(screen, zombies_killed, mouse_pos):
    screen.fill(DARK_GRAY)
    
    # --- 1. Logo ---
    global _logo_img
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load('./game/icons/logo.png').convert_alpha()
            logo_w = 500
            logo_h = int(_logo_img.get_height() * (logo_w / _logo_img.get_width()))
            _logo_img = pygame.transform.scale(_logo_img, (logo_w, logo_h))
    except Exception:
        _logo_img = None

    if _logo_img:
        title_rect = _logo_img.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT * 0.25))
        screen.blit(_logo_img, title_rect)
    else:
        title_text = title_font.render("YOU DIED", True, RED)
        title_rect = title_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT * 0.25))
        screen.blit(title_text, title_rect)

    # --- 2. Stats ---
    score_text = large_font.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
    score_rect = score_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT * 0.45))
    screen.blit(score_text, score_rect)

    # --- 3. Buttons ---
    btn_width = 400
    btn_height = 50
    spacing = 20
    center_x = VIRTUAL_SCREEN_WIDTH // 2
    start_y = VIRTUAL_GAME_HEIGHT * 0.55

    # Restart Button
    restart_rect = pygame.Rect(center_x - btn_width // 2, start_y, btn_width, btn_height)
    draw_btn(screen, restart_rect, "Restart", mouse_pos)

    # Back to Menu Button (Replaces Quit)
    menu_rect = pygame.Rect(center_x - btn_width // 2, restart_rect.bottom + spacing, btn_width, btn_height)
    draw_btn(screen, menu_rect, "Back to Menu", mouse_pos)

    # --- 4. Footer ---
    current_year = datetime.now().year
    footer_str = f"Developed by: Gustavo Kuklinski - All Rights Reserved - 2025 - {current_year} | version: {GAME_VERSION}"
    footer_text = font_notification.render(footer_str, True, (100, 100, 100))
    footer_rect = footer_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT - 20))
    screen.blit(footer_text, footer_rect)

    return restart_rect, menu_rect