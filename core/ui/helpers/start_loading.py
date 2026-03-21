import pygame
import math
from core.data.config import *
from core.data.localization import tr

# Global variable to cache the image so we don't reload it every frame
LOADING_IMG = None

def draw_loading_screen(surface, is_done, mouse_pos):
    """
    Draws the loading screen with an animated image and blinking start text.
    """
    global LOADING_IMG
    
    # 1. Load Image (Cached)
    if LOADING_IMG is None:
        try:
            LOADING_IMG = pygame.image.load('game/icons/loading.png').convert_alpha()
        except Exception:
            # Fallback surface if image is missing
            LOADING_IMG = pygame.Surface((100, 100))
            LOADING_IMG.fill((50, 50, 50))

    surface.fill(DARK_GRAY)
    
    w, h = surface.get_size()
    center_x, center_y = w // 2, h // 2

    # Get rect centered on screen
    img_rect = LOADING_IMG.get_rect(center=(center_x, center_y))

    if not is_done:
        # 2. Fade/Pulse Animation
        # Oscillate alpha between 50 and 255 based on time
        alpha = int(abs(math.sin(pygame.time.get_ticks() * 0.005)) * 200 + 55)
        LOADING_IMG.set_alpha(alpha)
        
        surface.blit(LOADING_IMG, img_rect)
        return None
        
    else:
        # Loading Complete
        
        # Reset alpha to fully visible
        LOADING_IMG.set_alpha(255)
        surface.blit(LOADING_IMG, img_rect)
        
       
        # 4. 'Click to start' Button (Centered at Bottom)
        btn_w, btn_h = 300, 60
        btn_rect = pygame.Rect(0, 0, btn_w, btn_h)
        btn_rect.center = (center_x, h - 100) # 100px from bottom
        
        # Blinking Color Logic (Switch every 500ms)
        current_time = pygame.time.get_ticks()
        if (current_time // 500) % 2 == 0:
            text_color = GREEN
        else:
            text_color = WHITE
            
        # Draw Text (Using large_font for bold effect)
        btn_text = large_font.render(tr('ui', "Click to start"), True, text_color)
        text_rect = btn_text.get_rect(center=btn_rect.center)
        
        # Draw invisible hit box (or subtle bg if needed)
        # pygame.draw.rect(surface, (30,30,30), btn_rect, border_radius=8) 
        surface.blit(btn_text, text_rect)
        
        return btn_rect