import pygame
from data.config import *


def load_assets():
    assets = {}
    try:
        cursor_image = pygame.image.load(SPRITE_PATH + 'ui/cursor.png').convert_alpha()
        cursor_hotspot = (0, 0)
        assets['custom_cursor'] = pygame.cursors.Cursor(cursor_hotspot, cursor_image)
    except pygame.error as e:
        print(f"Error loading cursor: {e}")
        assets['custom_cursor'] = None

    try:
        aim_cursor_image = pygame.image.load(SPRITE_PATH + 'ui/aim.png').convert_alpha()
        aim_cursor_hotspot = (aim_cursor_image.get_width() // 2, aim_cursor_image.get_height() // 2)
        assets['aim_cursor'] = pygame.cursors.Cursor(aim_cursor_hotspot, aim_cursor_image)
    except pygame.error as e:
        print(f"Error loading aim cursor: {e}")
        assets['aim_cursor'] = None

    try:
        assets['close_button'] = pygame.image.load(SPRITE_PATH + 'ui/close.png').convert_alpha()
        assets['minimize_button'] = pygame.image.load(SPRITE_PATH + 'ui/minimize.png').convert_alpha()
    except pygame.error as e:
        print(f"Error loading modal buttons: {e}")
        assets['close_button'] = None
        assets['minimize_button'] = None

    try:
        # This image should be a white circle fading to transparent
        assets['light_texture'] = pygame.image.load(SPRITE_PATH + 'ui/light.png').convert_alpha()
    except pygame.error as e:
        print(f"Error loading light texture: {e}")
        assets['light_texture'] = None
    # --- END ADDITION ---

    assets['font'] = font

    return assets