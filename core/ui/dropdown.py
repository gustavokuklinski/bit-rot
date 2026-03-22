import pygame
from core.data.config import *
from core.data.localization import tr

def draw_context_menu(surface, menu_state, mouse_pos):
    if not menu_state['active']:
        return
    options = menu_state['options']
    if not options:
        menu_state['active'] = False
        return
        
    # Translate options for display using the 'context' category
    translated_options = [tr('context', opt) for opt in options]

    item_height = 25
    padding = 5
    # Calculate width based on the translated text
    max_width = max(font.size(opt)[0] for opt in translated_options) + (padding * 2)
    menu_height = len(options) * item_height
    menu_x, menu_y = menu_state['position']
    
    if menu_x + max_width > GAME_WIDTH:
        menu_x -= max_width
    if menu_y + menu_height > GAME_HEIGHT:
        menu_y -= menu_height
        
    menu_rect = pygame.Rect(menu_x, menu_y, max_width, menu_height)
    s = pygame.Surface((max_width, menu_height), pygame.SRCALPHA)
    s.fill((20, 20, 20, 220))
    surface.blit(s, menu_rect.topleft)
    pygame.draw.rect(surface, WHITE, menu_rect, 1)
    
    menu_state['rects'] = []
    for i, translated_option in enumerate(translated_options):
        option_rect = pygame.Rect(menu_x, menu_y + i * item_height, max_width, item_height)
        menu_state['rects'].append(option_rect)
        
        text_color = WHITE
        if option_rect.collidepoint(mouse_pos):
            pygame.draw.rect(surface, GRAY_80, option_rect)
            text_color = YELLOW
            
        # Draw using the translated string
        text_surf = font.render(translated_option, True, text_color)
        surface.blit(text_surf, (option_rect.x + padding, option_rect.y + (item_height - text_surf.get_height()) // 2))