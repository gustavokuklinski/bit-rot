import pygame
from core.ui.helpers.load_game_screen import draw_load_game_screen, get_save_files, delete_save

def run_load_game_menu(game):
    mouse_pos = game._get_scaled_mouse_pos()
    clickable_rects = draw_load_game_screen(game, game.load_game_state, mouse_pos)
    
    if 'is_dragging_scrollbar' not in game.load_game_state:
        game.load_game_state['is_dragging_scrollbar'] = False
        game.load_game_state['scroll_drag_start_y'] = 0

    for event in game.get_events():
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            game.running = False
            return
        
        if event.type == pygame.MOUSEWHEEL:
             scroll_amount = event.y * 35 
             current_scroll = game.load_game_state.get('scroll_y', 0)
             max_scroll = game.load_game_state.get('max_scroll', 0)
             game.load_game_state['scroll_y'] = max(0, min(current_scroll - scroll_amount, max_scroll))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = game._get_scaled_mouse_pos()
            
            if clickable_rects.get('scrollbar_handle') and clickable_rects['scrollbar_handle'].collidepoint(mouse_pos):
                game.load_game_state['is_dragging_scrollbar'] = True
                game.load_game_state['scroll_drag_start_y'] = mouse_pos[1]
                continue 

            for index, filename, rect in clickable_rects['save_items']:
                if rect.collidepoint(mouse_pos):
                    game.load_game_state['selected_save_index'] = index
                    break
            
            if clickable_rects['load_button'] and clickable_rects['load_button'].collidepoint(mouse_pos):
                idx = game.load_game_state.get('selected_save_index')
                if idx is not None and idx < len(game.load_game_state['save_list']):
                    save_folder = game.load_game_state['save_list'][idx]['filename']
                    game.load_game(save_folder)

                    game.loading_saved_game_folder = save_folder
                    game.loading_done = False
                    game.game_state = 'LOADING'
            
            elif clickable_rects['delete_button'] and clickable_rects['delete_button'].collidepoint(mouse_pos):
                idx = game.load_game_state.get('selected_save_index')
                if idx is not None and idx < len(game.load_game_state['save_list']):
                    filename = game.load_game_state['save_list'][idx]['filename']
                    if delete_save(filename):
                        game.load_game_state['save_list'] = get_save_files()
                        game.load_game_state['selected_save_index'] = None
            
            elif clickable_rects['back_button'] and clickable_rects['back_button'].collidepoint(mouse_pos):
                game.game_state = 'MENU'

        if event.type == pygame.MOUSEBUTTONUP:
            game.load_game_state['is_dragging_scrollbar'] = False

        if event.type == pygame.MOUSEMOTION:
            if game.load_game_state.get('is_dragging_scrollbar'):
                mouse_delta_y = mouse_pos[1] - game.load_game_state['scroll_drag_start_y']
                game.load_game_state['scroll_drag_start_y'] = mouse_pos[1]
                
                track_rect = clickable_rects.get('scrollbar_track')
                handle_rect = clickable_rects.get('scrollbar_handle')
                max_scroll = game.load_game_state.get('max_scroll', 0)

                if track_rect and handle_rect and max_scroll > 0:
                    track_height = track_rect.height - handle_rect.height
                    if track_height > 0:
                        scroll_amount = mouse_delta_y * (max_scroll / track_height)
                        game.load_game_state['scroll_y'] = max(0, min(game.load_game_state['scroll_y'] + scroll_amount, max_scroll))

    game._update_screen()