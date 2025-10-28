import pygame
import sys
import math
from data.config import *
from core.events.keyboard import handle_keyboard_events
from core.events.mouse import handle_mouse_down, handle_mouse_up, handle_mouse_motion

def handle_movement(game):
    keys = pygame.key.get_pressed()
    current_speed = PLAYER_SPEED

    is_walking = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
    game.player.is_walking = is_walking

    if is_walking:
        current_speed = PLAYER_SPEED / 2

    if game.player.stamina <= 0:
        current_speed = PLAYER_SPEED / 3

    dx, dy = 0, 0
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        dy -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        dy += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        dx -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        dx += 1

    if dx != 0 and dy != 0:
        # Normalize for diagonal movement
        dx /= math.sqrt(2)
        dy /= math.sqrt(2)

    game.player.vx = dx * current_speed
    game.player.vy = dy * current_speed
    

def handle_input(game):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                game.zoom_level += 0.1
            elif event.y < 0:
                game.zoom_level -= 0.1
            game.zoom_level = max(FAR_ZOOM, min(game.zoom_level, NEAR_ZOOM))

        if event.type == pygame.VIDEORESIZE:
            game.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

        mouse_pos = game._get_scaled_mouse_pos()

        if game.game_state == 'PLAYING':
            handle_movement(game)
            handle_keyboard_events(game, event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                handle_mouse_down(game, event, mouse_pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                handle_mouse_up(game, event, mouse_pos)
            elif event.type == pygame.MOUSEMOTION:
                handle_mouse_motion(game, event, mouse_pos)
        elif game.game_state == 'PAUSED':
            handle_keyboard_events(game, event)