import pygame
from config import *

# Keep rect helper functions here as lightweight UI helpers used by Player logic.
# Modal drawing is moved to modals.py to separate rendering responsibilities.

def get_inventory_slot_rect(i, modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    # Inventory is a single row of 5 columns inside the inventory modal
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 50
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_belt_slot_rect_in_modal(i, modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    # Belt slots arranged horizontally below backpack slot
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 190
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_backpack_slot_rect(modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    # Backpack occupies a wide slot under the inventory row
    slot_w = 272
    slot_h = 48
    x = modal_x + 10
    y = modal_y + 110
    return pygame.Rect(x, y, slot_w, slot_h)

def get_container_slot_rect(container_pos, i):
    rows, cols = 4, 5
    slot_size = 48
    padding = 10
    start_x = container_pos[0] + padding
    start_y = container_pos[1] + 40
    row = i // cols
    col = i % cols
    return pygame.Rect(start_x + col * (slot_size + padding), start_y + row * (slot_size + padding), slot_size, slot_size)

# cached logo image
_logo_img = None

def draw_menu(screen):
    global _logo_img
    screen.fill(DARK_GRAY)

    # try to load and draw logo image instead of text title
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load('game/ui/logo.png').convert_alpha()
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
            _logo_img = pygame.image.load('game/ui/logo.png').convert_alpha()
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