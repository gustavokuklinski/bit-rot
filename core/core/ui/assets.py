import pygame
from core.data.config import *


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
        assets['aim_reticle'] = aim_cursor_image

    except pygame.error as e:
        print(f"Error loading aim cursor: {e}")
        assets['aim_cursor'] = None
        assets['aim_reticle'] = None
    try:
        assets['day_icon'] = pygame.image.load(SPRITE_PATH + 'ui/day.png').convert_alpha()
        assets['night_icon'] = pygame.image.load(SPRITE_PATH + 'ui/night.png').convert_alpha()

    except pygame.error as e:
        print(f"Error loading day/night icons: {e}")
        assets['day_icon'] = None
        assets['night_icon'] = None


    try:
        assets['close_button'] = pygame.image.load(SPRITE_PATH + 'ui/close.png').convert_alpha()
    except pygame.error as e:
        print(f"Error loading modal buttons: {e}")
        assets['close_button'] = None

    try:
        assets['gear_icon'] = pygame.image.load(SPRITE_PATH + 'ui/gear_icon.png').convert_alpha()
    except pygame.error as e:
        print(f"Error loading gear icon: {e}")
        assets['gear_icon'] = None

    try:
        assets['vehicle_icon'] = pygame.image.load(SPRITE_PATH + 'ui/vehicle.png').convert_alpha()
    except pygame.error as e:
        print(f"Error loading vehicle icon: {e}")
        assets['vehicle_icon'] = None

    try:
        assets['mechanics_icon'] = pygame.image.load(SPRITE_PATH + 'ui/mechanics.png').convert_alpha()
    except pygame.error as e:
        print(f"Error loading mechanics icon: {e}")
        assets['mechanics_icon'] = None
    
    try:
        assets['seats_icon'] = pygame.image.load(SPRITE_PATH + 'ui/seats.png').convert_alpha()
    except pygame.error as e:
        print(f"Error loading seats icon: {e}")
        assets['seats_icon'] = None
        
    try:
        # This image should be a white circle fading to transparent
        assets['light_texture'] = pygame.image.load(SPRITE_PATH + 'ui/light.png').convert_alpha()
    except pygame.error as e:
        print(f"Error loading light texture: {e}")
        assets['light_texture'] = None

    assets['font'] = font_14

    return assets