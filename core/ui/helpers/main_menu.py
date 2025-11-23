import pygame
from core.data.config import *
from datetime import datetime
_logo_img = None

def draw_menu(screen, mouse_pos, has_save=False):
    global _logo_img
    screen.fill(DARK_GRAY)

    # try to load and draw logo image instead of text title
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load('./game/icons/logo.png').convert_alpha()
            logo_w = 400
            logo_h = int(_logo_img.get_height() * (logo_w / _logo_img.get_width()))
            _logo_img = pygame.transform.scale(_logo_img, (logo_w, logo_h))
    except Exception:
        _logo_img = None

    if _logo_img:
        title_rect = _logo_img.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
        screen.blit(_logo_img, title_rect)
    else:
        title_text = title_font.render("Bit Rot", True, RED)
        title_rect = title_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
        screen.blit(title_text, title_rect)

    # [CHANGE START] Adjust button layout
    center_x = VIRTUAL_SCREEN_WIDTH // 2
    center_y = VIRTUAL_GAME_HEIGHT // 2
    
    # Start Button
    start_text = large_font.render("NEW GAME", True, WHITE)
    start_rect = start_text.get_rect(center=(center_x, center_y))
    
    # Load Button (Optional)
    load_rect = None
    if has_save:
        # Shift Start down if Load exists
        start_rect.y += 40 
        
        load_text = large_font.render("LOAD GAME", True, WHITE)
        load_rect = load_text.get_rect(center=(center_x, center_y - 20))
        
        if load_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, GRAY, load_rect.inflate(20, 10))
        screen.blit(load_text, load_rect)

    # Quit Button
    quit_text = large_font.render("QUIT", True, WHITE)
    quit_rect = quit_text.get_rect(center=(center_x, start_rect.y + 60))
    
    # Draw hover effects
    if start_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, GRAY, start_rect.inflate(20, 10))
    if quit_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, GRAY, quit_rect.inflate(20, 10))

    screen.blit(start_text, start_rect)
    screen.blit(quit_text, quit_rect)

    current_year = datetime.now().year
    footer_str = f"Developed by: Gustavo Kuklinski - All Rights Reserved - 2025 - {current_year} | version: {GAME_VERSION}"
    footer_text = font_notification.render(footer_str, True, GRAY)
    footer_rect = footer_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT - 20))
    screen.blit(footer_text, footer_rect)

    return start_rect, load_rect, quit_rect
