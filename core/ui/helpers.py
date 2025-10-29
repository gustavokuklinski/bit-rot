import pygame
from data.config import *
from data.professions_xml_parser import parse_professions_data

# Keep rect helper functions here as lightweight UI helpers used by Player logic.
# Modal drawing is moved to modals.py to separate rendering responsibilities.

# cached logo image
_logo_img = None

# Buttons and status modal
_inventory_img = None
_status_img = None
def draw_inventory_button(surface):
    global _inventory_img
    if _inventory_img is None:
        try:
            _inventory_img = pygame.image.load(SPRITE_PATH + 'ui/inventory.png').convert_alpha()
            _inventory_img = pygame.transform.scale(_inventory_img, (40, 40))
        except pygame.error:
            _inventory_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _inventory_img.fill(GRAY)
    button_inventory_rect = pygame.Rect(10, 50, 60, 60)
    surface.blit(_inventory_img, button_inventory_rect)
    return button_inventory_rect

def draw_status_button(surface):
    global _status_img
    if _status_img is None:
        try:
            _status_img = pygame.image.load(SPRITE_PATH + 'ui/status.png').convert_alpha()
            _status_img = pygame.transform.scale(_status_img, (40, 40))
        except pygame.error:
            _status_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _status_img.fill(GRAY)
    button_rect = pygame.Rect(10, 10, 40, 40)
    surface.blit(_status_img, button_rect)
    return button_rect

_nearby_img = None
def draw_nearby_button(surface):
    global _nearby_img
    if _nearby_img is None:
        try:
            _nearby_img = pygame.image.load(SPRITE_PATH + 'ui/nearby.png').convert_alpha()
            _nearby_img = pygame.transform.scale(_nearby_img, (40, 40))
        except pygame.error:
            _nearby_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _nearby_img.fill(GRAY)
    button_nearby_rect = pygame.Rect(10, 110, 60, 60)
    surface.blit(_nearby_img, button_nearby_rect)
    return button_nearby_rect


def draw_menu(screen):
    global _logo_img
    screen.fill(DARK_GRAY)

    # try to load and draw logo image instead of text title
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load(SPRITE_PATH + 'ui/logo_v2.png').convert_alpha()
            logo_w = 300
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

    start_text = large_font.render("START", True, WHITE)
    start_rect = start_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2))
    quit_text = large_font.render("QUIT", True, WHITE)
    quit_rect = quit_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 + 60))
    mouse_pos = pygame.mouse.get_pos()
    scale_x = VIRTUAL_SCREEN_WIDTH / screen.get_width()
    scale_y = VIRTUAL_GAME_HEIGHT / screen.get_height()
    scaled_mouse_pos = (mouse_pos[0] * scale_x, mouse_pos[1] * scale_y)
    if start_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, start_rect.inflate(20, 10))
    if quit_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, quit_rect.inflate(20, 10))
    screen.blit(start_text, start_rect)
    screen.blit(quit_text, quit_rect)
    return start_rect, quit_rect

def draw_game_over(screen, zombies_killed):
    screen.fill(DARK_GRAY)
    # draw same logo at top for game over screen (fallback to text if missing)
    global _logo_img
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load(SPRITE_PATH + 'ui/logo_v2.png').convert_alpha()
            logo_w = 300
            logo_h = int(_logo_img.get_height() * (logo_w / _logo_img.get_width()))
            _logo_img = pygame.transform.scale(_logo_img, (logo_w, logo_h))
    except Exception:
        _logo_img = None

    if _logo_img:
        title_rect = _logo_img.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
        screen.blit(_logo_img, title_rect)
    else:
        title_text = title_font.render("YOU DIED", True, RED)
        title_rect = title_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
        screen.blit(title_text, title_rect)

    score_text = large_font.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
    score_rect = score_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 - 60))
    screen.blit(score_text, score_rect)
    restart_text = large_font.render("Restart", True, WHITE)
    restart_rect = restart_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 + 20))
    quit_text = large_font.render("Quit", True, WHITE)
    quit_rect = quit_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 + 80))
    mouse_pos = pygame.mouse.get_pos()
    scale_x = VIRTUAL_SCREEN_WIDTH / screen.get_width()
    scale_y = VIRTUAL_GAME_HEIGHT / screen.get_height()
    scaled_mouse_pos = (mouse_pos[0] * scale_x, mouse_pos[1] * scale_y)
    if restart_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, restart_rect.inflate(20, 10))
    if quit_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, quit_rect.inflate(20, 10))
    screen.blit(restart_text, restart_rect)
    screen.blit(quit_text, quit_rect)
    return restart_rect, quit_rect

def run_player_setup(game):
    professions = parse_professions_data()
    game.virtual_screen.fill(DARK_GRAY)
    title_text = font.render("Choose your Profession", True, WHITE)
    title_rect = title_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, 100))
    game.virtual_screen.blit(title_text, title_rect)

    y_pos = 148
    rectName = pygame.Rect(VIRTUAL_SCREEN_WIDTH // 2 - 200, y_pos, 400, 50)
    spriteName = pygame.image.load(SPRITE_PATH + 'ui/player.png').convert_alpha()
    spriteName = pygame.transform.scale(spriteName, (42, 42))
    game.virtual_screen.blit(spriteName, (rectName.left - 60, rectName.y))

    name_input_rect = pygame.Rect(VIRTUAL_SCREEN_WIDTH // 2 - 200, 150, 400, 40)
    pygame.draw.rect(game.virtual_screen, GRAY, name_input_rect, 2)
    name_text = large_font.render(game.player_name, True, WHITE)
    game.virtual_screen.blit(name_text, (name_input_rect.x + 5, name_input_rect.y + 5))

    profession_rects = []
    for i, prof in enumerate(professions):
        y_pos = 210 + i * 70
        rect = pygame.Rect(VIRTUAL_SCREEN_WIDTH // 2 - 200, y_pos, 400, 50)
        profession_rects.append((rect, prof['name']))
        pygame.draw.rect(game.virtual_screen, GRAY, rect, 2)
        prof_text = large_font.render(prof['name'], True, WHITE)
        game.virtual_screen.blit(prof_text, (rect.x + 10, rect.y + 10))
        desc_text = font_small.render(prof['description'], True, WHITE)
        game.virtual_screen.blit(desc_text, (rect.x + 10, rect.y + 30))

        sprite_path = prof['visuals']['sprite']
        try:
            sprite = pygame.image.load(sprite_path).convert_alpha()
            sprite = pygame.transform.scale(sprite, (42, 42))
            game.virtual_screen.blit(sprite, (rect.left - 60, rect.y))
        except pygame.error as e:
            print(f"Error loading profession sprite: {e}")

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            game.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = game._get_scaled_mouse_pos()
            if name_input_rect.collidepoint(mouse_pos):
                game.name_input_active = True
            else:
                game.name_input_active = False

            for rect, name in profession_rects:
                if rect.collidepoint(mouse_pos):
                    game.start_new_game(name)
                    game.game_state = 'PLAYING'
                    return
        if event.type == pygame.KEYDOWN and game.name_input_active:
            if event.key == pygame.K_BACKSPACE:
                game.player_name = game.player_name[:-1]
            else:
                game.player_name += event.unicode

    game._update_screen()