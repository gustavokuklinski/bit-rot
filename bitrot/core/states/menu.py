# In core/states/menu.py

import os
import glob
import pygame
import core.data.config
import core.data.localization
from core.data.config import get_writable_dir
from core.ui.helpers.main_menu import draw_menu
from core.ui.helpers.keybinds import keybinds_ui
from core.ui.helpers.preferences import preferences_ui
from core.ui.helpers.help_menu import help_ui  # <-- Import the new Help UI

def run_menu(game):
    if hasattr(game, 'discord_rpc'):
        game.discord_rpc.update_presence(state="Main Menu", details="Browsing menus")
        
    events = game.get_events()
    mouse_pos = game._get_scaled_mouse_pos()
    save_dir = os.path.join(get_writable_dir(), "data.rot", "save", "game")
    saves = sorted(glob.glob(os.path.join(save_dir, "save_*"))) if os.path.exists(save_dir) else []
    has_save = len(saves) > 0

    start_btn, load_btn, settings_btn, quit_btn, flag_rects, help_rect, controls_rect = draw_menu(game.game_screen, mouse_pos, has_save)

    is_sub_menu_open = (
        getattr(keybinds_ui, 'active', False) or 
        getattr(preferences_ui, 'active', False) or 
        getattr(help_ui, 'active', False)
    )

    if not is_sub_menu_open:
        menu_buttons = [b for b in [start_btn, load_btn if has_save else None, settings_btn, quit_btn, help_rect, controls_rect] if b is not None]
        for flag in flag_rects:
            menu_buttons.append(flag['rect'])

        hovered_idx = None
        for idx, b_rect in enumerate(menu_buttons):
            if b_rect.collidepoint(mouse_pos):
                hovered_idx = idx
                break

        if hovered_idx is not None and hovered_idx != getattr(game, '_menu_hovered_btn_idx', None):
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
        game._menu_hovered_btn_idx = hovered_idx
    else:
        game._menu_hovered_btn_idx = None

    if getattr(keybinds_ui, 'active', False):
        keybinds_ui.handle_events(events)
        keybinds_ui.draw(game.game_screen, mouse_pos, game=game)
        game._update_screen()
        return

    if getattr(preferences_ui, 'active', False):
        preferences_ui.handle_events(game, events)
        preferences_ui.draw(game.game_screen, mouse_pos, game=game)
        game._update_screen()
        return

    # Draw Help UI when active
    if getattr(help_ui, 'active', False):
        help_ui.handle_events(game, events)
        help_ui.draw(game.game_screen, mouse_pos, game=game)
        game._update_screen()
        return

    for event in events:
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            game.running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()

        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
            mouse_pos = game._get_scaled_mouse_pos()
            
            # Toggle Help Menu
            if help_rect and help_rect.collidepoint(mouse_pos):
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                help_ui.toggle()
                continue

            if controls_rect and controls_rect.collidepoint(mouse_pos):
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                keybinds_ui.toggle()
                continue

            flag_clicked = False
            for flag_info in flag_rects:
                if flag_info['rect'].collidepoint(mouse_pos):
                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_ui_hover()
                    lang_code = flag_info['name']
                    core.data.config.save_language_to_config(lang_code)
                    core.data.localization.load_language(lang_code)
                    flag_clicked = True
                    break
            
            if flag_clicked: continue
            
            if start_btn.collidepoint(mouse_pos):
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                game.player_setup_state = {}
                game.world_setup_state = {}
                game.game_state = 'PLAYER_SETUP'
                game.player_setup_state['current_tab'] = 'SelectWorld'
                
            elif has_save and load_btn.collidepoint(mouse_pos):
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                game.game_state = 'LOAD_GAME_MENU'
                if 'save_list' in game.load_game_state:
                     del game.load_game_state['save_list']
                     
            elif settings_btn.collidepoint(mouse_pos):
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                preferences_ui.toggle() 
                
            elif quit_btn.collidepoint(mouse_pos):
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                game.running = False
                return
                
    game._update_screen()