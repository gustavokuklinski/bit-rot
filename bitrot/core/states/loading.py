import pygame
import asyncio
from core.ui.helpers.start_loading import draw_loading_screen

async def _async_start_new_game(game, data):
    await asyncio.sleep(0) # Yield to browser to draw the loading screen
    game.start_new_game(data)

async def _async_load_game(game, folder):
    await asyncio.sleep(0) # Yield to browser to draw the loading screen
    game.load_game(folder)

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
        if getattr(game, '_loading_task', None) is None:
            if game.loading_data:
                game._loading_task = asyncio.create_task(_async_start_new_game(game, game.loading_data))
            elif game.loading_saved_game_folder:
                game._loading_task = asyncio.create_task(_async_load_game(game, game.loading_saved_game_folder))
        else:
            if game._loading_task.done():
                game.loading_done = True
                game._loading_task = None 
                game.loading_data = None 
                game.loading_saved_game_folder = None
    else:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_btn and start_btn.collidepoint(mouse_pos):
                    game.game_state = 'PLAYING'