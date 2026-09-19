import pygame
from core.ui.helpers.game_over import draw_game_over
from core.systems.load_manager import handle_player_death

def run_game_over(game):
    if hasattr(game, 'world_time') and game.world_time:
        game.world_time.stop_all_sounds()
    
    # Preserve world state and create corpse of dead player if not done yet
    handle_player_death(game)
        
    pygame.mouse.set_visible(True)
    pygame.mouse.set_cursor(game.assets.get('custom_cursor') or pygame.cursors.arrow)
    mouse_pos = game._get_scaled_mouse_pos()
    
    days_survived = game.world_time.day_count if hasattr(game, 'world_time') and game.world_time else 0
    
    respawn_btn, menu_btn = draw_game_over(game.game_screen, game.zombies_killed, days_survived, mouse_pos)

    for event in game.get_events():
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            game.running = False
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                save_folder = game.current_save_folder_name
                game.player_setup_state = {}
                game.player_setup_state['current_tab'] = 'Player'
                game.player_setup_state['respawn_save_folder'] = save_folder
                game.game_state = 'PLAYER_SETUP'
                return
            elif event.key == pygame.K_ESCAPE:
                game.current_save_folder_name = None
                game.game_state = 'MENU'
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = game._get_scaled_mouse_pos()
            
            if respawn_btn.collidepoint(mouse_pos):
                save_folder = game.current_save_folder_name
                game.player_setup_state = {}
                game.player_setup_state['current_tab'] = 'Player'
                game.player_setup_state['respawn_save_folder'] = save_folder
                game.game_state = 'PLAYER_SETUP'
                return
            elif menu_btn.collidepoint(mouse_pos):
                game.current_save_folder_name = None
                game.game_state = 'MENU'
                return

    game._update_screen()