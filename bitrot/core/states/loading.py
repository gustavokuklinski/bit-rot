# core/states/loading.py

import pygame
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
    
    start_btn = draw_loading_screen(game.game_screen, game.loading_done, mouse_pos, events)
    game._update_screen()
    
    if not game.loading_done:
        # Step 1: Allow the first frame to render "Loading..." onto the screen
        if not getattr(game, '_loading_frame_drawn', False):
            game._loading_frame_drawn = True
            return

        # Step 2: Synchronously generate or load the game data
        if game.loading_data:
            game.start_new_game(game.loading_data)
            game.loading_data = None
        elif game.loading_saved_game_folder:
            game.load_game(game.loading_saved_game_folder)
            game.loading_saved_game_folder = None
            
        game.loading_done = True
        game._loading_frame_drawn = False

    else:
        # Step 3: Handle "Click to start" button
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_btn and start_btn.collidepoint(mouse_pos):
                    game.game_state = 'PLAYING'