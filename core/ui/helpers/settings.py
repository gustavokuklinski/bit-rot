# core/ui/helpers/settings.py
import pygame
import core.data.config
from core.data.config import *
from core.ui.helpers.trait_config_loader import save_config_xml, load_config_data
from core.data.localization import tr, load_language

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
    col_start_x = 170 
    col_width = 350
    header_height = 30
    border_radius = 4
    padding = 10
    
    BTN_GREEN = (50, 205, 50)  
    BTN_BLUE = (23, 162, 184)  
    
    clickable_rects = {
        "config_inputs": [], 
        "config_bools": [],
        "config_cycles": [],
        "apply_settings": None
    }

    # Control Panel
    control_rect = pygame.Rect(col_start_x, 30, col_width - 100, 100)
    control_header = pygame.Rect(control_rect.x, control_rect.y, control_rect.width, header_height)
    control_body = pygame.Rect(control_rect.x, control_rect.y + header_height, control_rect.width, control_rect.height - header_height)

    pygame.draw.rect(game.game_screen, (30, 30, 30), control_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, control_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, control_rect, 1, border_radius=border_radius)
    
    game.game_screen.blit(font.render(tr('ui', "Settings Control"), True, WHITE), (control_header.x + 10, control_header.y + 7))

    btn_w = 120
    apply_rect = pygame.Rect(0, 0, btn_w, 35)
    apply_rect.center = control_body.center
    
    pygame.draw.rect(game.game_screen, BTN_BLUE, apply_rect, border_radius=4)
    apply_txt = font.render(tr('ui', "Apply"), True, WHITE)
    game.game_screen.blit(apply_txt, (apply_rect.centerx - apply_txt.get_width()//2, apply_rect.centery - apply_txt.get_height()//2))
    clickable_rects['apply_settings'] = apply_rect

    # Settings List
    settings_area_x = col_start_x + col_width
    settings_area_w = 830
    settings_rect = pygame.Rect(settings_area_x - 87, 30, settings_area_w, 660)
    
    settings_header = pygame.Rect(settings_rect.x, settings_rect.y, settings_rect.width, header_height)
    settings_body = pygame.Rect(settings_rect.x, settings_rect.y + header_height, settings_rect.width, settings_rect.height - header_height)

    pygame.draw.rect(game.game_screen, (30, 30, 30), settings_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, settings_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, settings_rect, 1, border_radius=border_radius)
    
    game.game_screen.blit(font.render(tr('ui', "Configuration Values"), True, WHITE), (settings_header.x + 10, settings_header.y + 7))
    
    content_rect = settings_body.inflate(-20, -20)
    line_h = 40
    
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
                # --- NEW: Translate the Header String ('ui', 'game', etc) ---
                header_name = tr('ui', item[1].capitalize())
                text = font.render(header_name.upper(), True, YELLOW)
                sub.blit(text, (0, y_off + 10))
            else:
                block, key, val_data = item[1], item[2], item[3]
                
                raw_label = val_data.get('name', key) if isinstance(val_data, dict) else key
                
                # Try to translate the key. If there is no translation (like in en_US), 
                # it will fall back to 'raw_label' instead of the underscore key.
                display_label = tr('ui', key)

                val = val_data.get('value') if isinstance(val_data, dict) else val_data
                
                input_w = 200
                input_rect = pygame.Rect(content_rect.width - input_w - 5, y_off + 5, input_w, 30)
                abs_rect = pygame.Rect(content_rect.x + input_rect.x, content_rect.y + input_rect.y, input_rect.width, input_rect.height)
                
                str_val = str(val).lower()
                is_bool = str_val in ('true', 'false')
                
                is_percentage_cycle = ('chance' in key) or (block == 'item_spawning' and 'multiplier' in key) or (key in ['water_threshold', 'food_water_multiplier_decay']) or ('volume' in key)
                is_time_cycle = key in ['time_daylength', 'time_sunrise_hr', 'time_sunset_hr', 'time_start_hr', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']
                is_language_cycle = (key == 'language')
                is_cycle_setting = is_percentage_cycle or is_time_cycle or is_language_cycle

                lbl = font_small.render(display_label + ":", True, WHITE)
                sub.blit(lbl, (0, y_off + 12)) 
                
                friendly_text = _get_friendly_value_display(key, val)
                if friendly_text and not is_bool and not is_cycle_setting:
                    info_surf = font_small.render(friendly_text, True, GRAY)
                    info_pos_x = input_rect.x - info_surf.get_width() - 15
                    sub.blit(info_surf, (info_pos_x, y_off + 12))

                if is_bool:
                    hovered = abs_rect.collidepoint(mouse_pos)
                    bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                    pygame.draw.rect(sub, bg_color, input_rect, border_radius=3)
                    pygame.draw.rect(sub, WHITE, input_rect, 1, border_radius=3)
                    
                    val_text = tr('ui', "True") if str_val == "true" else tr('ui', "False")
                    txt_surf = font_small.render(val_text, True, WHITE)
                    text_x = input_rect.x + (input_rect.width - txt_surf.get_width()) // 2
                    text_y = input_rect.y + (input_rect.height - txt_surf.get_height()) // 2
                    sub.blit(txt_surf, (text_x, text_y))
                    
                    pygame.draw.polygon(sub, WHITE, [(input_rect.right - 8, input_rect.centery), (input_rect.right - 14, input_rect.centery - 4), (input_rect.right - 14, input_rect.centery + 4)])
                    pygame.draw.polygon(sub, WHITE, [(input_rect.x + 8, input_rect.centery), (input_rect.x + 14, input_rect.centery - 4), (input_rect.x + 14, input_rect.centery + 4)])
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_bools'].append((block, key, abs_rect))
                        
                elif is_cycle_setting:
                    hovered = abs_rect.collidepoint(mouse_pos)
                    bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                    pygame.draw.rect(sub, bg_color, input_rect, border_radius=3)
                    pygame.draw.rect(sub, WHITE, input_rect, 1, border_radius=3)
                    
                    if is_language_cycle:
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

                            # New 0% label specifically for Volume
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
                    
                    txt_surf = font_small.render(label, True, WHITE)
                    text_x = input_rect.x + (input_rect.width - txt_surf.get_width()) // 2
                    text_y = input_rect.y + (input_rect.height - txt_surf.get_height()) // 2
                    sub.blit(txt_surf, (text_x, text_y))
                    
                    pygame.draw.polygon(sub, WHITE, [(input_rect.right - 8, input_rect.centery), (input_rect.right - 14, input_rect.centery - 4), (input_rect.right - 14, input_rect.centery + 4)])
                    pygame.draw.polygon(sub, WHITE, [(input_rect.x + 8, input_rect.centery), (input_rect.x + 14, input_rect.centery - 4), (input_rect.x + 14, input_rect.centery + 4)])
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_cycles'].append((block, key, abs_rect))
                else:
                    is_active = (state.get('active_setting') == (block, key))
                    col = WHITE if is_active else GRAY
                    pygame.draw.rect(sub, (50, 50, 50), input_rect)
                    pygame.draw.rect(sub, col, input_rect, 1)
                    
                    txt_surf = font_small.render(str(val), True, WHITE)
                    sub.blit(txt_surf, (input_rect.x + 5, input_rect.y + 7))
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_inputs'].append((block, key, abs_rect))
                
            y_off += line_h

    if max_scroll > 0:
        bar_area = pygame.Rect(settings_body.right - 14, settings_body.y + 5, 10, settings_body.height - 10)
        handle_h = max(20, (content_rect.height / total_h) * bar_area.height)
        scroll_pct = scroll_y / max_scroll if max_scroll > 0 else 0
        handle_y = bar_area.y + (scroll_pct * (bar_area.height - handle_h))
        
        state['settings_scroll_handle'] = pygame.Rect(bar_area.x, handle_y, 10, handle_h)
        state['settings_scrollbar_track'] = bar_area
        pygame.draw.rect(game.game_screen, GRAY, state['settings_scroll_handle'], border_radius=2)
    else:
        state['settings_scroll_handle'] = None
    
    state['settings_content_rect'] = content_rect

    return clickable_rects


def handle_settings_events(game, state, event, mouse_pos, clickable_rects):
    if event.type == pygame.MOUSEWHEEL:
        rect = state.get('settings_content_rect')
        if rect and rect.collidepoint(mouse_pos):
            state['settings_scroll_y'] = max(0, min(state['settings_scroll_y'] - (event.y * 30), state.get('settings_max_scroll', 0)))
    
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

        if clickable_rects.get('apply_settings') and clickable_rects['apply_settings'].collidepoint(mouse_pos):
            preset_name = state.get('selected_config_preset', 'config')
            save_config_xml(state['settings_data'], f"./game/save/config/{preset_name}.xml")
            core.data.config.load_settings(preset_name)

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

                        # --- LIVE SAVE: Writes directly to config.xml ---
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
                            
                            # Write new config to disk immediately so you don't have to press apply
                            preset_name = state.get('selected_config_preset', 'config')
                            core.data.config.save_language_to_config(new_val, preset_name)
                            
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
                            
                            # Allow volume to reach 0.0
                            if not 'volume' in key and comp_val <= 0.0: comp_val = 0.01
                            
                            comp_val = round(comp_val, 2)
                            
                            if comp_val < 0.25: new_val = 0.25
                            elif comp_val < 0.50: new_val = 0.50
                            elif comp_val < 0.75: new_val = 0.75
                            elif comp_val < 1.0: new_val = 1.0
                            else: 
                                new_val = 0.0 if 'volume' in key else 0.01 # Volume cycles to 0

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

    elif event.type == pygame.MOUSEBUTTONUP:
        state['is_dragging_settings_scrollbar'] = False
        
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