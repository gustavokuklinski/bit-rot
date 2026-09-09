import pygame
from core.ui.helpers.game_over import draw_game_over
from core.ui.helpers.load_game_screen import delete_save

def run_game_over(game):
    if hasattr(game, 'world_time') and game.world_time:
        game.world_time.stop_all_sounds()
    
    if getattr(game, 'current_save_folder_name', None):
        try:
            delete_save(game.current_save_folder_name)
            game.logger.info(f"Permadeath: Deleted save folder '{game.current_save_folder_name}' due to player death.")
        except Exception as e:
            game.logger.info(f"Permadeath deletion failed: {e}")
        
        game.current_save_folder_name = None
        
    pygame.mouse.set_visible(True)
    pygame.mouse.set_cursor(game.assets.get('custom_cursor') or pygame.cursors.arrow)
    mouse_pos = game._get_scaled_mouse_pos()
    
    days_survived = game.world_time.day_count if hasattr(game, 'world_time') and game.world_time else 0
    
    menu_button = draw_game_over(game.game_screen, game.zombies_killed, days_survived, mouse_pos)

    for event in game.get_events():
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            game.running = False
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = game._get_scaled_mouse_pos()
            
            if menu_button.collidepoint(mouse_pos):
                game.game_state = 'MENU'
                return
    game._update_screen()