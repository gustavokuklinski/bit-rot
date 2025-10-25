import pygame
from data.config import *

def draw_context_menu(surface, menu_state, mouse_pos):
    if not menu_state['active']:
        return
    options = menu_state['options']
    if not options:
        menu_state['active'] = False
        return
    item_height = 25
    padding = 5
    max_width = max(font.size(opt)[0] for opt in options) + (padding * 2)
    menu_height = len(options) * item_height
    menu_x, menu_y = menu_state['position']
    if menu_x + max_width > VIRTUAL_SCREEN_WIDTH:
        menu_x -= max_width
    if menu_y + menu_height > VIRTUAL_GAME_HEIGHT:
        menu_y -= menu_height
    menu_rect = pygame.Rect(menu_x, menu_y, max_width, menu_height)
    s = pygame.Surface((max_width, menu_height), pygame.SRCALPHA)
    s.fill((20, 20, 20, 220))
    surface.blit(s, menu_rect.topleft)
    pygame.draw.rect(surface, WHITE, menu_rect, 1)
    menu_state['rects'] = []
    for i, option in enumerate(options):
        option_rect = pygame.Rect(menu_x, menu_y + i * item_height, max_width, item_height)
        menu_state['rects'].append(option_rect)
        text_color = WHITE
        if option_rect.collidepoint(mouse_pos):
            pygame.draw.rect(surface, GRAY_80, option_rect)
            text_color = YELLOW
        text_surf = font.render(option, True, text_color)
        surface.blit(text_surf, (option_rect.x + padding, option_rect.y + (item_height - text_surf.get_height()) // 2))