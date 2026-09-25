# core/states/loading.py

import pygame
import threading
import traceback
import time
from core.ui.helpers.start_loading import draw_loading_screen

def run_loading(game):
    events = game.get_events()
    mouse_pos = game._get_scaled_mouse_pos()
    
    for event in events:
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)
        if event.type == pygame.QUIT:
            game.running = False
            return

    # --- 1. Launch loading task in a background daemon thread ---
    if not getattr(game, 'loading_done', False) and not getattr(game, '_loading_thread_running', False):
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
                elif getattr(game, 'loading_saved_game_folder', None):
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
    start_btn = draw_loading_screen(game.game_screen, getattr(game, 'loading_done', False), mouse_pos, events)
    game._update_screen()

    # --- 3. Handle "Click to start" once loading has finished ---
    if getattr(game, 'loading_done', False):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
                if start_btn and start_btn.collidepoint(mouse_pos):
                    _finalize_loading(game)
                    return
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                _finalize_loading(game)
                return

def _finalize_loading(game):
    """Resets internal clocks to prevent massive time-delta spikes that corrupt physics/vitals."""
    game._loading_thread_running = False
    game.game_state = 'PLAYING'
    game.dt_ms = 16
    game.dt_mult = 1.0
    game.clock.tick(60)

    # Prevent massive skip in time if the user sat on the loading screen for a while
    current_ticks = pygame.time.get_ticks()
    if hasattr(game, 'game_start_time'):
        game.game_start_time = current_ticks
    if hasattr(game, 'world_time'):
        game.world_time.last_update_time = current_ticks
    
    # Reset player metabolism timers so they don't instantly starve/dehydrate
    if getattr(game, 'player', None):
        game.player.last_decay_time = time.time()

