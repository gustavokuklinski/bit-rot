import os
import glob
import pygame
import core.data.config
import core.data.localization
from core.data.config import get_writable_dir
from core.ui.helpers.main_menu import draw_menu
from core.ui.helpers.keybinds import keybinds_ui
from core.ui.helpers.start_loading import draw_loading_screen

def run_menu(game):
    events = game.get_events()
    mouse_pos = game._get_scaled_mouse_pos()
    save_dir = os.path.join(get_writable_dir(), "data.rot", "save", "game")
    saves = sorted(glob.glob(os.path.join(save_dir, "save_*"))) if os.path.exists(save_dir) else []
    has_save = len(saves) > 0

    start_btn, load_btn, settings_btn, quit_btn, flag_rects, help_rect, controls_rect = draw_menu(game.game_screen, mouse_pos, has_save)

    if getattr(keybinds_ui, 'active', False):
        keybinds_ui.handle_events(events)
        keybinds_ui.draw(game.game_screen, mouse_pos)
        game._update_screen()
        return

    back_btn = None
    if getattr(game, 'show_main_menu_help', False):
        back_btn = draw_loading_screen(game.game_screen, True, mouse_pos, events, is_main_menu_help=True)

    for event in events:
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            game.running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()

        if getattr(game, 'show_main_menu_help', False):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = game._get_scaled_mouse_pos()
                if back_btn and back_btn.collidepoint(mouse_pos):
                    game.show_main_menu_help = False
                    continue
            continue 

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = game._get_scaled_mouse_pos()
            
            if help_rect and help_rect.collidepoint(mouse_pos):
                game.show_main_menu_help = True
                continue

            if controls_rect and controls_rect.collidepoint(mouse_pos):
                keybinds_ui.toggle()
                continue

            flag_clicked = False
            for flag_info in flag_rects:
                if flag_info['rect'].collidepoint(mouse_pos):
                    lang_code = flag_info['name']
                    core.data.config.save_language_to_config(lang_code)
                    core.data.localization.load_language(lang_code)
                    flag_clicked = True
                    break
            
            if flag_clicked: continue
            
            if start_btn.collidepoint(mouse_pos):
                game.player_setup_state = {} 
                game.game_state = 'PLAYER_SETUP'
                game.player_setup_state['current_tab'] = 'Player' 
                
            elif has_save and load_btn.collidepoint(mouse_pos):
                game.game_state = 'LOAD_GAME_MENU'
                if 'save_list' in game.load_game_state:
                     del game.load_game_state['save_list']
                     
            elif settings_btn.collidepoint(mouse_pos):
                game.game_state = 'PLAYER_SETUP'
                game.player_setup_state['current_tab'] = 'Settings'
                
            elif quit_btn.collidepoint(mouse_pos):
                game.running = False
                return
                
    game._update_screen()