import pygame
from core.data.config import GAME_WIDTH, GAME_HEIGHT, WHITE, GRAY, font_12
from core.draw import draw_game
from core.events.mouse import handle_mouse_down, handle_right_click
from core.events.mouse_drag import handle_mouse_up, handle_mouse_motion
from core.data.localization import tr

def run_paused(game):
    if not getattr(game, 'is_mixer_paused', False):
        pygame.mixer.pause()
        pygame.mixer.music.pause()
        game.is_mixer_paused = True

    allowed_modals = ['status', 'messages', 'nearby', 'inventory', 'gear', 'container', 'belt', 'slots']
    game.modals = [m for m in game.modals if m.get('type') in allowed_modals]

    draw_game(game)

    overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
    game.game_screen.blit(overlay, (0, 0))

    banner_rect = pygame.Rect(0, 0, GAME_WIDTH, 28)
    pygame.draw.rect(game.game_screen, (20, 20, 20, 240), banner_rect)
    pygame.draw.line(game.game_screen, (100, 100, 100), (0, 28), (GAME_WIDTH, 28), 1)

    pause_text = font_12.render(tr('ui', "PAUSED"), False, (220, 70, 70))
    game.game_screen.blit(pause_text, (10, 8))
    
    start_x = 10 + pause_text.get_width() + 10
    sep = font_12.render("-", False, GRAY)
    game.game_screen.blit(sep, (start_x, 8))
    start_x += sep.get_width() + 10

    mouse_pos = game._get_scaled_mouse_pos()
    events = game.get_events()

    btn_continue = pygame.Rect(start_x, 4, 70, 20)
    start_x += 80
    btn_save = pygame.Rect(start_x, 4, 50, 20)
    start_x += 60
    btn_exit = pygame.Rect(start_x, 4, 50, 20)

    def draw_banner_btn(rect, text):
        is_hovered = rect.collidepoint(mouse_pos)
        color = WHITE if is_hovered else (150, 150, 150)
        txt_surf = font_12.render(text, False, color)
        game.game_screen.blit(txt_surf, (rect.x + (rect.width - txt_surf.get_width())//2, rect.y + (rect.height - txt_surf.get_height())//2))
        return is_hovered

    hover_cont = draw_banner_btn(btn_continue, tr('ui', "Continue"))
    hover_save = draw_banner_btn(btn_save, tr('ui', "Save"))
    hover_exit = draw_banner_btn(btn_exit, tr('ui', "Exit"))

    for event in events:
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            game.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
            pygame.mixer.unpause()
            pygame.mixer.music.unpause()
            game.is_mixer_paused = False
            game.game_state = 'PLAYING'
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if btn_continue.collidepoint(mouse_pos):
                    pygame.mixer.unpause()
                    pygame.mixer.music.unpause()
                    game.is_mixer_paused = False
                    game.game_state = 'PLAYING'
                elif btn_save.collidepoint(mouse_pos):
                    game.save_game()
                elif btn_exit.collidepoint(mouse_pos):
                    pygame.mixer.unpause()
                    pygame.mixer.music.unpause()
                    game.is_mixer_paused = False
                    if hasattr(game, 'world_time') and game.world_time:
                        game.world_time.stop_all_sounds()
                    game.game_state = 'MENU'
                else:
                    handle_mouse_down(game, event, mouse_pos)
            elif event.button in [4, 5]:
                handle_mouse_down(game, event, mouse_pos)
            elif event.button == 3:
                handle_right_click(game, mouse_pos)
                
        elif event.type == pygame.MOUSEBUTTONUP:
            handle_mouse_up(game, event, mouse_pos)
        elif event.type == pygame.MOUSEMOTION:
            handle_mouse_motion(game, event, mouse_pos)

    game._update_screen()