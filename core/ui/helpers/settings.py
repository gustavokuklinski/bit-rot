# core/ui/helpers/settings.py
import pygame
import sys
import os
import subprocess
import core.data.config
from core.data.config import *
from core.ui.helpers.trait_config_loader import save_config_xml, load_config_data
from core.data.localization import tr, load_language
from core.ui.modals import draw_scrollbar

def _get_friendly_value_display(key, value):
    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return ""

    if key in ['time_daylength', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']: 
        seconds = val_float / 1000.0
        if seconds >= 60:
            return f"({seconds/60:.1f} {tr('ui', 'min')})"
        return f"({seconds:.0f} {tr('ui', 'sec')})"
    
    if 'seconds' in key or '_sec' in key: 
        if val_float >= 60:
             return f"({val_float/60:.1f} {tr('ui', 'min')})"
        return f"({tr('ui', 'sec')})"
        
    if '_hr' in key: 
        hours = int(val_float)
        minutes = int((val_float - hours) * 60)
        return f"({hours:02d}:{minutes:02d})"
        
    if 'multiplier' in key or 'chance' in key or 'volume' in key:
        return f"({val_float*100:.0f}%)"
        
    if key == 'map_chunks':
        size = int(val_float)
        return f"({size}x{size} {tr('ui', 'World')})"

    return ""


def _draw_settings_screen(game, state, mouse_pos):
    if not state.get('settings_data'):
        preset_name = state.get('selected_config_preset', 'config')
        correct_path = core.data.config.get_active_config_path(preset_name)
        state['settings_data'] = load_config_data(correct_path)

    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_offset_x = (GAME_WIDTH - S(1280)) // 2
    center_offset_y = (GAME_HEIGHT - S(720)) // 2
    
    col_start_x = S(170) + center_offset_x
    base_y = S(30) + center_offset_y
    
    col_width = S(350)
    header_height = S(30)
    border_radius = S(4)
    padding = S(10)
    
    BTN_GREEN = (50, 205, 50)  
    BTN_BLUE = (23, 162, 184)  
    
    clickable_rects = {
        "config_inputs": [], 
        "config_bools": [],
        "config_cycles": [],
        "apply_settings": None
    }

    control_rect = pygame.Rect(col_start_x, base_y, col_width - S(100), S(180))
    control_header = pygame.Rect(control_rect.x, control_rect.y, control_rect.width, header_height)
    control_body = pygame.Rect(control_rect.x, control_rect.y + header_height, control_rect.width, control_rect.height - header_height)

    pygame.draw.rect(game.game_screen, (30, 30, 30), control_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, control_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, control_rect, 1, border_radius=border_radius)
    
    game.game_screen.blit(font.render(tr('ui', "Settings Control"), True, WHITE), (control_header.x + S(10), control_header.y + S(7)))

    btn_w = S(130)
    apply_rect = pygame.Rect(0, 0, btn_w, S(35))
    
    # Move Apply to the left
    apply_rect.centerx = control_body.centerx - S(70)
    apply_rect.centery = control_body.centery - S(8)
    
    pygame.draw.rect(game.game_screen, BTN_BLUE, apply_rect, border_radius=4)
    apply_txt = font.render(tr('ui', "Apply"), True, WHITE)
    game.game_screen.blit(apply_txt, (apply_rect.centerx - apply_txt.get_width()//2, apply_rect.centery - apply_txt.get_height()//2))
    clickable_rects['apply_settings'] = apply_rect

    # Add Reset Default to the right
    BTN_RED = (200, 50, 50)
    reset_rect = pygame.Rect(0, 0, btn_w, S(35))
    reset_rect.centerx = control_body.centerx + S(70)
    reset_rect.centery = control_body.centery - S(8)
    
    pygame.draw.rect(game.game_screen, BTN_RED, reset_rect, border_radius=4)
    reset_txt = font.render(tr('ui', "Reset Default"), True, WHITE)
    game.game_screen.blit(reset_txt, (reset_rect.centerx - reset_txt.get_width()//2, reset_rect.centery - reset_txt.get_height()//2))
    clickable_rects['reset_default'] = reset_rect

    warning_text = font_14.render(tr('ui', "Requires a restart to apply."), True, GRAY)
    warning_x = control_body.centerx - (warning_text.get_width() // 2)
    warning_y = apply_rect.bottom + S(5)
    game.game_screen.blit(warning_text, (warning_x, warning_y + S(20)))

    settings_area_x = col_start_x + col_width
    settings_area_w = S(830)
    settings_rect = pygame.Rect(settings_area_x - S(87), base_y, settings_area_w, S(660))
    
    settings_header = pygame.Rect(settings_rect.x, settings_rect.y, settings_rect.width, header_height)
    settings_body = pygame.Rect(settings_rect.x, settings_rect.y + header_height, settings_rect.width, settings_rect.height - header_height)

    pygame.draw.rect(game.game_screen, (30, 30, 30), settings_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, settings_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, settings_rect, 1, border_radius=border_radius)
    
    game.game_screen.blit(font.render(tr('ui', "Configuration Values"), True, WHITE), (settings_header.x + S(10), settings_header.y + S(7)))
    
    content_rect = settings_body.inflate(-S(20), -S(20))
    line_h = S(40)
    
    draw_items = []
    config_data = state.get('settings_data', {})
    
    if 'ui' in config_data and 'language' not in config_data['ui']:
        config_data['ui']['language'] = {'value': 'en_US', 'name': 'Language'}

    block_order = ['ui', 'audio', 'game', 'map', 'player','durability', 'vehicle', 'item_spawning','animal', 'zombie', 'npc']
    for k in config_data:
        if k not in block_order: block_order.append(k)

    for block in block_order:
        if block not in config_data: continue
        draw_items.append(('header', block))
        for key, val_data in config_data[block].items():
            draw_items.append(('item', block, key, val_data))

    total_h = len(draw_items) * line_h
    max_scroll = max(0, total_h - content_rect.height)
    state['settings_max_scroll'] = max_scroll
    scroll_y = state.get('settings_scroll_y', 0)
    
    clip_rect = game.game_screen.get_rect().clip(content_rect)
    if clip_rect.width > 0 and clip_rect.height > 0:
        sub = game.game_screen.subsurface(clip_rect)
        sub.fill((30, 30, 30))
        
        y_off = -scroll_y
        for item in draw_items:
            if item[0] == 'header':
                header_name = tr('ui', item[1].capitalize())
                text = font.render(header_name.upper(), True, YELLOW)
                sub.blit(text, (0, y_off + S(10)))
            else:
                block, key, val_data = item[1], item[2], item[3]
                
                raw_label = val_data.get('name', key) if isinstance(val_data, dict) else key
                
                display_label = tr('ui', key)
                if display_label == key:
                    display_label = tr('ui', raw_label)
                    if display_label == raw_label:
                        display_label = raw_label

                val = val_data.get('value') if isinstance(val_data, dict) else val_data
                
                input_w = S(200)
                input_rect = pygame.Rect(content_rect.width - input_w - S(5), y_off + S(5), input_w, S(30))
                abs_rect = pygame.Rect(content_rect.x + input_rect.x, content_rect.y + input_rect.y, input_rect.width, input_rect.height)
                
                str_val = str(val).lower()
                is_bool = str_val in ('true', 'false')
                
                is_percentage_cycle = ('chance' in key) or (block == 'item_spawning' and 'multiplier' in key) or (key in ['water_threshold', 'food_water_multiplier_decay']) or ('volume' in key)
                is_time_cycle = key in ['time_daylength', 'time_sunrise_hr', 'time_sunset_hr', 'time_start_hr', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']
                is_language_cycle = (key == 'language')
                is_display_cycle = (key in ['resolution', 'window_mode']) 
                is_cycle_setting = is_percentage_cycle or is_time_cycle or is_language_cycle or is_display_cycle

                lbl = font_14.render(display_label + ":", True, WHITE)
                sub.blit(lbl, (0, y_off + S(12))) 
                
                friendly_text = _get_friendly_value_display(key, val)
                if friendly_text and not is_bool and not is_cycle_setting:
                    info_surf = font_14.render(friendly_text, True, GRAY)
                    info_pos_x = input_rect.x - info_surf.get_width() - S(15)
                    sub.blit(info_surf, (info_pos_x, y_off + S(12)))

                if is_bool:
                    hovered = abs_rect.collidepoint(mouse_pos)
                    bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                    pygame.draw.rect(sub, bg_color, input_rect, border_radius=3)
                    pygame.draw.rect(sub, WHITE, input_rect, 1, border_radius=3)
                    
                    val_text = tr('ui', "True") if str_val == "true" else tr('ui', "False")
                    txt_surf = font_14.render(val_text, True, WHITE)
                    text_x = input_rect.x + (input_rect.width - txt_surf.get_width()) // 2
                    text_y = input_rect.y + (input_rect.height - txt_surf.get_height()) // 2
                    sub.blit(txt_surf, (text_x, text_y))
                    
                    pygame.draw.polygon(sub, WHITE, [(input_rect.right - S(8), input_rect.centery), (input_rect.right - S(14), input_rect.centery - S(4)), (input_rect.right - S(14), input_rect.centery + S(4))])
                    pygame.draw.polygon(sub, WHITE, [(input_rect.x + S(8), input_rect.centery), (input_rect.x + S(14), input_rect.centery - S(4)), (input_rect.x + S(14), input_rect.centery + S(4))])
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_bools'].append((block, key, abs_rect))
                        
                elif is_cycle_setting:
                    hovered = abs_rect.collidepoint(mouse_pos)
                    bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                    pygame.draw.rect(sub, bg_color, input_rect, border_radius=3)
                    pygame.draw.rect(sub, WHITE, input_rect, 1, border_radius=3)
                    
                    if is_language_cycle:
                        label = str(val)
                    elif is_display_cycle: 
                        if key == 'resolution' and str(val).lower() == 'max':
                            label = tr('ui', "Native (Max)")
                        elif key == 'window_mode':
                            label = tr('ui', str(val).capitalize())
                        else:
                            label = str(val)
                    else:
                        try:
                            current_val_float = float(val)
                        except ValueError:
                            current_val_float = 1.0
                            
                        if is_percentage_cycle:
                            comp_val = current_val_float
                            if key == 'water_threshold': comp_val /= 100.0
                            if not 'volume' in key and comp_val <= 0.0: comp_val = 0.01
                            comp_val = round(comp_val, 2)

                            if 'volume' in key and abs(comp_val - 0.0) < 0.001: label = tr('ui', "Muted (0%)")
                            elif abs(comp_val - 0.01) < 0.001: label = tr('ui', "Extreme Low (1%)")
                            elif abs(comp_val - 0.25) < 0.001: label = tr('ui', "Low (25%)")
                            elif abs(comp_val - 0.50) < 0.001: label = tr('ui', "Balanced (50%)")
                            elif abs(comp_val - 0.75) < 0.001: label = tr('ui', "High (75%)")
                            elif abs(comp_val - 1.0) < 0.001: label = tr('ui', "Extreme High (100%)")
                            else: label = f"{tr('ui', 'Custom')} ({comp_val*100:.0f}%)"
                        elif key in ['time_daylength', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']:
                            mins = int(current_val_float / 60000)
                            if mins == 0: mins = 15
                            label = f"{mins} {tr('ui', 'min')}"
                        elif key in ['time_sunrise_hr', 'time_sunset_hr', 'time_start_hr']:
                            hours = int(current_val_float)
                            minutes = int((current_val_float - hours) * 60)
                            label = f"{hours:02d}:{minutes:02d}"
                        else:
                            label = str(current_val_float)
                    
                    txt_surf = font_14.render(label, True, WHITE)
                    text_x = input_rect.x + (input_rect.width - txt_surf.get_width()) // 2
                    text_y = input_rect.y + (input_rect.height - txt_surf.get_height()) // 2
                    sub.blit(txt_surf, (text_x, text_y))
                    
                    pygame.draw.polygon(sub, WHITE, [(input_rect.right - S(8), input_rect.centery), (input_rect.right - S(14), input_rect.centery - S(4)), (input_rect.right - S(14), input_rect.centery + S(4))])
                    pygame.draw.polygon(sub, WHITE, [(input_rect.x + S(8), input_rect.centery), (input_rect.x + S(14), input_rect.centery - S(4)), (input_rect.x + S(14), input_rect.centery + S(4))])
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_cycles'].append((block, key, abs_rect))
                else:
                    is_active = (state.get('active_setting') == (block, key))
                    col = WHITE if is_active else GRAY
                    pygame.draw.rect(sub, (50, 50, 50), input_rect)
                    pygame.draw.rect(sub, col, input_rect, 1)
                    
                    txt_surf = font_14.render(str(val), True, WHITE)
                    sub.blit(txt_surf, (input_rect.x + S(5), input_rect.y + S(7)))
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_inputs'].append((block, key, abs_rect))
                
            y_off += line_h

    if max_scroll > 0:
        bar_area = pygame.Rect(settings_body.right - S(14), settings_body.y + S(5), 8, settings_body.height - S(10))
        draw_scrollbar(game.game_screen, state, bar_area, content_rect.height, total_h, scroll_y)
        
        # Route the global handle rect to the specific key your drag math expects
        state['settings_scroll_handle'] = state['scrollbar_handle_rect']
        state['settings_scrollbar_track'] = bar_area
    else:
        state['settings_scroll_handle'] = None
    
    state['settings_content_rect'] = content_rect

    return clickable_rects

def handle_settings_events(game, state, event, mouse_pos, clickable_rects):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    if event.type == pygame.MOUSEWHEEL:
        rect = state.get('settings_content_rect')
        if rect and rect.collidepoint(mouse_pos):
            state['settings_scroll_y'] = max(0, min(state['settings_scroll_y'] - (event.y * S(30)), state.get('settings_max_scroll', 0)))
    
    elif event.type == pygame.KEYDOWN:
        if state.get('active_setting'):
            block, key = state['active_setting']
            setting_obj = state['settings_data'][block][key]
            
            if not isinstance(setting_obj, dict):
                 setting_obj = {'value': setting_obj, 'name': key}
                 state['settings_data'][block][key] = setting_obj
            
            current_val = str(setting_obj['value'])
            if event.key == pygame.K_BACKSPACE:
                setting_obj['value'] = current_val[:-1]
            elif event.key == pygame.K_RETURN: 
                state['active_setting'] = None
            else: 
                setting_obj['value'] = current_val + event.unicode
                
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        state['active_setting'] = None
        
        if state.get('settings_scroll_handle') and state['settings_scroll_handle'].collidepoint(mouse_pos):
            state['is_dragging_settings_scrollbar'] = True
            state['settings_scroll_drag_last_y'] = mouse_pos[1]
            return

        if clickable_rects.get('reset_default') and clickable_rects['reset_default'].collidepoint(mouse_pos):
            if 'settings_data' in state:
                for block, settings in state['settings_data'].items():
                    for key, setting_obj in settings.items():
                        # If the setting is a dictionary and has the 'default' attribute from your XML
                        if isinstance(setting_obj, dict) and 'default' in setting_obj:
                            setting_obj['value'] = setting_obj['default']
            return
        
        

        if clickable_rects.get('apply_settings') and clickable_rects['apply_settings'].collidepoint(mouse_pos):
            preset_name = state.get('selected_config_preset', 'config')
            
            # 1. Get the safe, persistent directory (where the .exe is)
            writable_root = core.data.config.get_writable_dir()
            save_dir = os.path.join(writable_root, "game", "save", "config")
            
            # 2. Safely create the nested folders if they don't exist yet
            os.makedirs(save_dir, exist_ok=True)
            
            # 3. Save the XML
            save_path = os.path.join(save_dir, f"{preset_name}.xml")
            save_config_xml(state['settings_data'], save_path)
            
            core.data.config.load_settings(preset_name)
            pygame.quit()
        
            if sys.argv[0].endswith('.py'):
                # Running from source code (IDE/Terminal)
                subprocess.Popen([sys.executable] + sys.argv)
            else:
                # Running from compiled Nuitka executable
                executable_path = os.path.abspath(sys.argv[0])
                subprocess.Popen([executable_path] + sys.argv[1:])
            
            # 5. Exit immediately to trigger Nuitka's /tmp folder cleanup
            sys.exit(0)
                
            # Note: os.execv completely replaces the current process. 
            # Any code below this line will never execute!
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume(0.5 * core.data.config.VOLUME_MUSIC)

            state['current_tab'] = 'Player'
            return

        else:
            clicked_input = False
            for block, key, rect in clickable_rects.get('config_inputs', []):
                if rect.collidepoint(mouse_pos):
                    state['active_setting'] = (block, key)
                    clicked_input = True
                    break
            
            if not clicked_input:
                for block, key, rect in clickable_rects.get('config_bools', []):
                    if rect.collidepoint(mouse_pos):
                        setting_obj = state['settings_data'][block][key]
                        if not isinstance(setting_obj, dict):
                             setting_obj = {'value': setting_obj, 'name': key}
                             state['settings_data'][block][key] = setting_obj

                        current_val = setting_obj['value']
                        new_val = "false" if str(current_val).lower() == "true" else "true"
                        state['settings_data'][block][key]['value'] = new_val
                        clicked_input = True
                        break
                        
            if not clicked_input:
                for block, key, rect in clickable_rects.get('config_cycles', []):
                    if rect.collidepoint(mouse_pos):
                        setting_obj = state['settings_data'][block][key]
                        if not isinstance(setting_obj, dict):
                             setting_obj = {'value': setting_obj, 'name': key}
                             state['settings_data'][block][key] = setting_obj

                        if key == 'language':
                            langs = ['en_US', 'pt_BR']
                            current_val = str(setting_obj['value'])
                            try:
                                idx = langs.index(current_val)
                            except ValueError:
                                idx = 0
                            new_val = langs[(idx + 1) % len(langs)]
                            
                            state['settings_data'][block][key]['value'] = new_val
                            load_language(new_val)
                            
                            preset_name = state.get('selected_config_preset', 'config')
                            core.data.config.save_language_to_config(new_val, preset_name)
                            
                            clicked_input = True
                            break

                        elif key == 'resolution':
                            modes = pygame.display.list_modes()
                            
                            if modes == -1 or not modes:
                                res_list = ['1280x720', '1920x1080', 'max']
                            else:
                                res_list = [f"{w}x{h}" for w, h in reversed(modes) if w >= 1280 and h >= 720]
                                res_list = list(dict.fromkeys(res_list))
                                res_list.append('max')

                            current_val = str(setting_obj['value']).lower()
                            idx = res_list.index(current_val) if current_val in res_list else 0
                            new_val = res_list[(idx + 1) % len(res_list)]
                            
                            state['settings_data'][block][key]['value'] = new_val
                            clicked_input = True
                            break
                            
                        elif key == 'window_mode':
                            modes = ['windowed', 'fullscreen']
                            current_val = str(setting_obj['value']).lower()
                            idx = modes.index(current_val) if current_val in modes else 0
                            new_val = modes[(idx + 1) % len(modes)]
                            
                            state['settings_data'][block][key]['value'] = new_val
                            clicked_input = True
                            break

                        try:
                            current_val = float(setting_obj['value'])
                        except ValueError:
                            current_val = 0.0
                            
                        is_percentage_cycle = ('chance' in key) or (block == 'item_spawning' and 'multiplier' in key) or (key in ['water_threshold', 'food_water_multiplier_decay']) or ('volume' in key)

                        if is_percentage_cycle:
                            comp_val = current_val
                            if key == 'water_threshold': comp_val /= 100.0
                            
                            if not 'volume' in key and comp_val <= 0.0: comp_val = 0.01
                            
                            comp_val = round(comp_val, 2)
                            
                            if comp_val < 0.25: new_val = 0.25
                            elif comp_val < 0.50: new_val = 0.50
                            elif comp_val < 0.75: new_val = 0.75
                            elif comp_val < 1.0: new_val = 1.0
                            else: 
                                new_val = 0.0 if 'volume' in key else 0.01 

                        elif key in ['time_daylength', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']:
                            if current_val < 1800000: new_val = 1800000.0
                            elif current_val < 2700000: new_val = 2700000.0
                            elif current_val < 3600000: new_val = 3600000.0
                            else: new_val = 900000.0
                        elif key == 'time_sunrise_hr':
                            if current_val < 5.5: new_val = 5.5
                            elif current_val < 6.0: new_val = 6.0
                            elif current_val < 6.5: new_val = 6.5
                            elif current_val < 7.0: new_val = 7.0
                            else: new_val = 5.0
                        elif key == 'time_sunset_hr':
                            if current_val < 17.5: new_val = 17.5
                            elif current_val < 18.0: new_val = 18.0
                            elif current_val < 18.5: new_val = 18.5
                            elif current_val < 19.0: new_val = 19.0
                            else: new_val = 17.0
                        elif key == 'time_start_hr':
                            new_val = current_val + 1.0
                            if new_val > 23.0: new_val = 0.0
                        else:
                            new_val = current_val
                        
                        if key in ['time_daylength', 'water_threshold', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']:
                            state['settings_data'][block][key]['value'] = str(int(new_val))
                        else:
                            state['settings_data'][block][key]['value'] = str(new_val)
                        clicked_input = True
                        break
            if not clicked_input and state.get('settings_content_rect') and state['settings_content_rect'].collidepoint(mouse_pos):
                state['is_dragging_settings_content'] = True
                state['settings_content_drag_last_y'] = mouse_pos[1]

    elif event.type == pygame.MOUSEBUTTONUP:
        state['is_dragging_settings_scrollbar'] = False
        state['is_dragging_settings_content'] = False
        
    elif event.type == pygame.MOUSEMOTION:
        if state.get('is_dragging_settings_scrollbar'):
            mouse_delta_y = mouse_pos[1] - state['settings_scroll_drag_last_y']
            state['settings_scroll_drag_last_y'] = mouse_pos[1]
            
            track_rect = state.get('settings_scrollbar_track')
            handle_rect = state.get('settings_scroll_handle')
            max_scroll = state.get('settings_max_scroll', 0)

            if track_rect and handle_rect and max_scroll > 0:
                track_height = track_rect.height - handle_rect.height
                if track_height > 0:
                    scroll_amount = mouse_delta_y * (max_scroll / track_height)
                    state['settings_scroll_y'] = max(0, min(state['settings_scroll_y'] + scroll_amount, max_scroll))
            
        elif state.get('is_dragging_settings_content'):
            mouse_delta_y = mouse_pos[1] - state['settings_content_drag_last_y']
            state['settings_content_drag_last_y'] = mouse_pos[1]
            max_scroll = state.get('settings_max_scroll', 0)
            
            if max_scroll > 0:
                # Moving the mouse down moves the content down (decreases scroll_y)
                current_scroll = state.get('settings_scroll_y', 0)
                state['settings_scroll_y'] = max(0, min(current_scroll - mouse_delta_y, max_scroll))