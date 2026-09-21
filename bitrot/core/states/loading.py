# core/states/loading.py

import pygame
import threading
import traceback
from core.ui.helpers.start_loading import draw_loading_screen

def run_loading(game):
    events = pygame.event.get()
    mouse_pos = game._get_scaled_mouse_pos()
    
    for event in events:
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)
        if event.type == pygame.QUIT:
            game.running = False
            return

    # --- 1. Launch loading task in a background daemon thread ---
    if not game.loading_done and not getattr(game, '_loading_thread_running', False):
        game._loading_thread_running = True

        def _worker():
            try:
                if game.loading_data:
                    respawn_save = game.loading_data.get('respawn_save_folder')
                    if respawn_save:
                        game.respawn_player_in_world(game.loading_data, respawn_save)
                    else:
                        game.start_new_game(game.loading_data)
                    game.loading_data = None
                elif game.loading_saved_game_folder:
                    game.load_game(game.loading_saved_game_folder)
                    game.loading_saved_game_folder = None
            except Exception as e:
                traceback.print_exc()
                if hasattr(game, 'logger') and game.logger:
                    game.logger.crash("Critical error during background loading", e)
            finally:
                game.loading_done = True
                game._loading_thread_running = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    # --- 2. Keep the UI alive, interactive, and responsive at 60 FPS ---
    start_btn = draw_loading_screen(game.game_screen, game.loading_done, mouse_pos, events)
    game._update_screen()

    # --- 3. Handle "Click to start" once loading has finished ---
    if game.loading_done:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_btn and start_btn.collidepoint(mouse_pos):
                    game._loading_thread_running = False
                    game.game_state = 'PLAYING'
                    game.dt_ms = 16
                    game.dt_mult = 1.0
                    game.clock.tick(60)
                    return
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                game._loading_thread_running = False
                game.game_state = 'PLAYING'
                game.dt_ms = 16
                game.dt_mult = 1.0
                game.clock.tick(60)
                return