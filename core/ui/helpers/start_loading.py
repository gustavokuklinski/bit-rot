import pygame
from core.data.config import *

def draw_loading_screen(surface, is_done, mouse_pos):
    """
    Draws the loading screen. 
    If is_done is False, shows 'Loading...'.
    If is_done is True, shows 'Loading Complete' and a 'Click to start' button.
    Returns the button rect if is_done is True, else None.
    """
    surface.fill(DARK_GRAY)
    
    w, h = surface.get_size()
    center_x, center_y = w // 2, h // 2

    if not is_done:
        text_surf = large_font.render("Loading...", True, WHITE)
        rect = text_surf.get_rect(center=(center_x, center_y))
        surface.blit(text_surf, rect)
        return None
    else:
        text_surf = large_font.render("Welcome to Bit Rot...", True, WHITE)
        rect = text_surf.get_rect(center=(center_x, center_y - 50))
        surface.blit(text_surf, rect)
        
        # Start Button
        btn_w, btn_h = 250, 60
        btn_rect = pygame.Rect(0, 0, btn_w, btn_h)
        btn_rect.center = (center_x, center_y + 50)
        
        # Hover effect
        color = DARK_GRAY
        if btn_rect.collidepoint(mouse_pos):
            # Slightly lighter green for hover
            color = (DARK_GRAY) 
        
        pygame.draw.rect(surface, color, btn_rect, border_radius=8)
        pygame.draw.rect(surface, DARK_GRAY, btn_rect, 2, border_radius=8)
        
        btn_text = font_notification.render("Click to start", True, WHITE)
        text_rect = btn_text.get_rect(center=btn_rect.center)
        surface.blit(btn_text, text_rect)
        
        return btn_rect