import pygame
import core.data.config
from core.data.config import *
from core.ui.helpers.trait_config_loader import save_config_xml, load_config_data

def _get_friendly_value_display(key, value):
    """Returns a formatted string (unit/conversion) based on the setting key."""
    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return ""

    # Milliseconds -> Minutes/Seconds (Day length, timers)
    if key in ['time_daylength', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']: 
        seconds = val_float / 1000.0
        if seconds >= 60:
            return f"({seconds/60:.1f} min)"
        return f"({seconds:.0f} sec)"
    
    # Seconds explicit: Convert to minutes if >= 60
    if 'seconds' in key or '_sec' in key: 
        if val_float >= 60:
             return f"({val_float/60:.1f} min)"
        return "(sec)"
        
    # Hours: Convert decimal (5.5) to Clock (05:30)
    if '_hr' in key: 
        hours = int(val_float)
        minutes = int((val_float - hours) * 60)
        return f"({hours:02d}:{minutes:02d})"
        
    # Multipliers / Chances
    if 'multiplier' in key or 'chance' in key:
        return f"({val_float*100:.0f}%)"
        
    if key == 'map_chunks':
        size = int(val_float)
        return f"({size}x{size} World)"

    return ""

def _draw_settings_screen(game, state, mouse_pos):
    """Draws the Settings configuration screen."""
    
    # Layout Constants
    col_start_x = 170 
    col_width = 350
    header_height = 30
    border_radius = 4
    padding = 10
    
    # Custom Colors for UI match
    BTN_GREEN = (50, 205, 50)  # LimeGreen-ish
    BTN_BLUE = (23, 162, 184)  # Bootstrap Info/Teal
    
    clickable_rects = {
        "config_inputs": [], 
        "config_bools": [],
        "config_cycles": [],
        "apply_settings": None
    }

    # ==========================================================
    # 1. Control Panel (Left Side)
    # ==========================================================
    # Simplified to just hold the Apply button
    control_rect = pygame.Rect(col_start_x, 30, col_width - 100, 100)
    control_header = pygame.Rect(control_rect.x, control_rect.y, control_rect.width, header_height)
    control_body = pygame.Rect(control_rect.x, control_rect.y + header_height, control_rect.width, control_rect.height - header_height)

    # Backgrounds
    pygame.draw.rect(game.game_screen, (30, 30, 30), control_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, control_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, control_rect, 1, border_radius=border_radius)
    game.game_screen.blit(font.render("Settings Control", True, WHITE), (control_header.x + 10, control_header.y + 7))

    # --- Apply Button ---
    btn_w = 120
    apply_rect = pygame.Rect(0, 0, btn_w, 35)
    apply_rect.center = control_body.center
    
    pygame.draw.rect(game.game_screen, BTN_BLUE, apply_rect, border_radius=4)
    apply_txt = font.render("Apply", True, WHITE)
    game.game_screen.blit(apply_txt, (apply_rect.centerx - apply_txt.get_width()//2, apply_rect.centery - apply_txt.get_height()//2))
    clickable_rects['apply_settings'] = apply_rect


    # ==========================================================
    # 2. Settings List (Right Side)
    # ==========================================================
    settings_area_x = col_start_x + col_width
    settings_area_w = 830
    settings_rect = pygame.Rect(settings_area_x - 87, 30, settings_area_w, 660)
    
    settings_header = pygame.Rect(settings_rect.x, settings_rect.y, settings_rect.width, header_height)
    settings_body = pygame.Rect(settings_rect.x, settings_rect.y + header_height, settings_rect.width, settings_rect.height - header_height)

    pygame.draw.rect(game.game_screen, (30, 30, 30), settings_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, settings_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, settings_rect, 1, border_radius=border_radius)
    
    game.game_screen.blit(font.render("Configuration Values", True, WHITE), (settings_header.x + 10, settings_header.y + 7))
    
    content_rect = settings_body.inflate(-20, -20)
    line_h = 40
    
    # Flatten data for drawing
    draw_items = []
    config_data = state.get('settings_data', {})
    
    block_order = ['ui','game', 'map', 'player','durability', 'vehicle', 'item_spawning','animal', 'zombie', 'npc']
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
                text = font.render(item[1].upper(), True, YELLOW)
                sub.blit(text, (0, y_off + 10))
            else:
                block, key, val_data = item[1], item[2], item[3]
                
                if isinstance(val_data, dict):
                    display_label = val_data.get('name', key)
                    val = val_data.get('value')
                else:
                    display_label = key
                    val = val_data
                
                input_w = 200
                input_rect = pygame.Rect(content_rect.width - input_w - 5, y_off + 5, input_w, 30)
                abs_rect = pygame.Rect(content_rect.x + input_rect.x, content_rect.y + input_rect.y, input_rect.width, input_rect.height)
                
                str_val = str(val).lower()
                is_bool = str_val in ('true', 'false')
                is_spawning_multiplier = (block == 'item_spawning' and 'multiplier' in key)

                lbl = font_small.render(display_label + ":", True, WHITE)
                sub.blit(lbl, (0, y_off + 12)) 
                
                friendly_text = _get_friendly_value_display(key, val)
                if friendly_text and not is_bool and not is_spawning_multiplier:
                    info_surf = font_small.render(friendly_text, True, GRAY)
                    info_pos_x = input_rect.x - info_surf.get_width() - 15
                    sub.blit(info_surf, (info_pos_x, y_off + 12))

                if is_bool:
                    hovered = abs_rect.collidepoint(mouse_pos)
                    bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                    
                    pygame.draw.rect(sub, bg_color, input_rect, border_radius=3)
                    pygame.draw.rect(sub, WHITE, input_rect, 1, border_radius=3)
                    
                    val_text = "True" if str_val == "true" else "False"
                    txt_surf = font_small.render(val_text, True, WHITE)
                    text_x = input_rect.x + (input_rect.width - txt_surf.get_width()) // 2
                    text_y = input_rect.y + (input_rect.height - txt_surf.get_height()) // 2
                    sub.blit(txt_surf, (text_x, text_y))
                    
                    # Draw cycle arrows on sides
                    pygame.draw.polygon(sub, WHITE, [(input_rect.right - 8, input_rect.centery), (input_rect.right - 14, input_rect.centery - 4), (input_rect.right - 14, input_rect.centery + 4)])
                    pygame.draw.polygon(sub, WHITE, [(input_rect.x + 8, input_rect.centery), (input_rect.x + 14, input_rect.centery - 4), (input_rect.x + 14, input_rect.centery + 4)])
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_bools'].append((block, key, abs_rect))
                        
                elif is_spawning_multiplier:
                    hovered = abs_rect.collidepoint(mouse_pos)
                    bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                    
                    pygame.draw.rect(sub, bg_color, input_rect, border_radius=3)
                    pygame.draw.rect(sub, WHITE, input_rect, 1, border_radius=3)
                    
                    try:
                        current_val_float = float(val)
                    except ValueError:
                        current_val_float = 1.0
                        
                    if abs(current_val_float - 0.01) < 0.001: label = "Extreme Low (1%)"
                    elif abs(current_val_float - 0.25) < 0.001: label = "Low (25%)"
                    elif abs(current_val_float - 0.50) < 0.001: label = "Balanced (50%)"
                    elif abs(current_val_float - 0.75) < 0.001: label = "High (75%)"
                    elif abs(current_val_float - 1.0) < 0.001: label = "Extreme High (100%)"
                    else: label = f"Custom ({current_val_float*100:.0f}%)"
                    
                    txt_surf = font_small.render(label, True, WHITE)
                    text_x = input_rect.x + (input_rect.width - txt_surf.get_width()) // 2
                    text_y = input_rect.y + (input_rect.height - txt_surf.get_height()) // 2
                    sub.blit(txt_surf, (text_x, text_y))
                    
                    # Draw cycle arrows on sides
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

    # Scrollbar
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
        if state.get('config_name_active'):
            if event.key == pygame.K_BACKSPACE: state['config_name'] = state['config_name'][:-1]
            elif event.key == pygame.K_RETURN: state['config_name_active'] = False
            else: state['config_name'] += event.unicode
        elif state.get('active_setting'):
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
        state['config_name_active'] = False
        state['active_setting'] = None
        
        if state.get('settings_scroll_handle') and state['settings_scroll_handle'].collidepoint(mouse_pos):
            state['is_dragging_settings_scrollbar'] = True
            state['settings_scroll_drag_last_y'] = mouse_pos[1]
            return

        if clickable_rects.get('apply_settings') and clickable_rects['apply_settings'].collidepoint(mouse_pos):
            preset_name = state.get('selected_config_preset', 'config')
            save_config_xml(state['settings_data'], f"./game/save/config/{preset_name}.xml")
            core.data.config.load_settings(preset_name)
            
            if core.data.config.UI_BACKGROUND_MUSIC:
                if not pygame.mixer.music.get_busy():
                    game.sound_manager.play_music('game/lib/sfx/ui/music.ogg', volume=0.2)
            else:
                pygame.mixer.music.stop()

            state['current_tab'] = 'Player'
            print("Settings applied. Returning to Player Builder.")
            return

        elif clickable_rects.get('load_config_dd') and clickable_rects['load_config_dd'].collidepoint(mouse_pos):
            state['config_dd_active'] = not state.get('config_dd_active')
            return
        
        elif state.get('config_dd_active'):
            dropdown_handled = False
            for opt, r in clickable_rects.get('load_config_options', []):
                if r.collidepoint(mouse_pos):
                    state['selected_config_preset'] = opt
                    state['config_name'] = opt if opt != 'default' else ""
                    new_data = load_config_data(f"./game/save/config/{opt}.xml")
                    if new_data:
                        state['settings_data'] = new_data
                    
                    state['config_dd_active'] = False
                    dropdown_handled = True
                    break
            
            if not dropdown_handled:
                state['config_dd_active'] = False
            return

        else:
            clicked_input = False
            for block, key, rect in clickable_rects.get('config_inputs', []):
                if rect.collidepoint(mouse_pos):
                    state['active_setting'] = (block, key)
                    state['seed_input_active'] = False
                    state['config_name_active'] = False
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

                        try:
                            current_val = float(setting_obj['value'])
                        except ValueError:
                            current_val = 1.0
                            
                        if current_val < 0.25: new_val = 0.25
                        elif current_val < 0.50: new_val = 0.50
                        elif current_val < 0.75: new_val = 0.75
                        elif current_val < 1.0: new_val = 1.0
                        else: new_val = 0.01
                        
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