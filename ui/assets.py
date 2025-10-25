import pygame

def load_assets():
    assets = {}
    try:
        cursor_image = pygame.image.load('game/ui/sprites/cursor.png').convert_alpha()
        cursor_hotspot = (0, 0)
        assets['custom_cursor'] = pygame.cursors.Cursor(cursor_hotspot, cursor_image)
    except pygame.error as e:
        print(f"Error loading cursor: {e}")
        assets['custom_cursor'] = None

    try:
        aim_cursor_image = pygame.image.load('game/ui/sprites/aim.png').convert_alpha()
        aim_cursor_hotspot = (aim_cursor_image.get_width() // 2, aim_cursor_image.get_height() // 2)
        assets['aim_cursor'] = pygame.cursors.Cursor(aim_cursor_hotspot, aim_cursor_image)
    except pygame.error as e:
        print(f"Error loading aim cursor: {e}")
        assets['aim_cursor'] = None

    try:
        assets['close_button'] = pygame.image.load('game/ui/sprites/close.png').convert_alpha()
        assets['minimize_button'] = pygame.image.load('game/ui/sprites/minimize.png').convert_alpha()
    except pygame.error as e:
        print(f"Error loading modal buttons: {e}")
        assets['close_button'] = None
        assets['minimize_button'] = None

    assets['font'] = pygame.font.Font(None, 24)

    return assets