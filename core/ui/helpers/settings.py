import pygame
from core.data.config import *

def _get_friendly_value_display(key, value):
    """Returns a formatted string (unit/conversion) based on the setting key."""
    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return ""

    # Milliseconds -> Minutes/Seconds (Day length, timers)
    if key in ['time_daylength', 'respawn_timer', 'zombie_respawn_timer_ms']: 
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
    BTN_RED = (220, 53, 69)    # Bootstrap Danger
    BTN_BLUE = (23, 162, 184)  # Bootstrap Info/Teal
    
    clickable_rects = {
        "config_inputs": [], 
        "config_bools": [],
        "save_config": None,
        "delete_config": None,
        "load_config_dd": None,
        "apply_settings": None,
        "load_config_options": [],
        "config_name_input": None
    }

    # Sync Dropdown Selection with Input Box logic
    curr_preset = state.get('selected_config_preset', 'default')
    last_preset = state.get('_internal_last_preset')

    if curr_preset != last_preset:
        state['config_name'] = curr_preset
        state['_internal_last_preset'] = curr_preset

    # ==========================================================
    # 1. Preset Management Panel (Top Left)
    # ==========================================================
    preset_rect = pygame.Rect(col_start_x, 50, col_width, 270)
    preset_header = pygame.Rect(preset_rect.x, preset_rect.y, preset_rect.width, header_height)
    preset_body = pygame.Rect(preset_rect.x, preset_rect.y + header_height, preset_rect.width, preset_rect.height - header_height)

    # Backgrounds
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), preset_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, preset_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, preset_rect, 1, border_radius=border_radius)
    game.virtual_screen.blit(font.render("Config Preset", True, WHITE), (preset_header.x + 10, preset_header.y + 7))

    # --- Element 1: "New Config Name" Label & Input ---
    current_y = preset_body.y + 10
    game.virtual_screen.blit(font.render("New Config Name:", True, WHITE), (preset_body.x + padding, current_y))
    
    current_y += 25
    name_input_rect = pygame.Rect(preset_body.x + padding, current_y, preset_body.width - padding*2, 30)
    pygame.draw.rect(game.virtual_screen, (50, 50, 50), name_input_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, name_input_rect, 1)
    
    conf_name = state.get('config_name', "")
    text_surf = font.render(conf_name, True, WHITE)
    game.virtual_screen.blit(text_surf, (name_input_rect.x + 5, name_input_rect.y + 5))
    
    # Cursor
    if state.get('config_name_active') and int(pygame.time.get_ticks() / 500) % 2 == 0:
        cx = name_input_rect.x + 5 + text_surf.get_width()
        pygame.draw.line(game.virtual_screen, WHITE, (cx, name_input_rect.y+5), (cx, name_input_rect.bottom-5), 2)
    
    clickable_rects['config_name_input'] = name_input_rect

    # --- Element 2: BUTTONS SECTION (Moved UP to avoid dropdown overlap) ---
    current_y = name_input_rect.bottom + 10
    btn_w = 100
    
    # Save Button
    save_rect = pygame.Rect(preset_body.x + padding, current_y, btn_w, 30)
    pygame.draw.rect(game.virtual_screen, BTN_GREEN, save_rect, border_radius=4)
    save_txt = font.render("New/Save", True, WHITE)
    game.virtual_screen.blit(save_txt, (save_rect.centerx - save_txt.get_width()//2, save_rect.centery - save_txt.get_height()//2))
    clickable_rects['save_config'] = save_rect

    # Apply Button (Next to Save)
    apply_rect = pygame.Rect(save_rect.right + 10, current_y, btn_w, 30)
    pygame.draw.rect(game.virtual_screen, BTN_BLUE, apply_rect, border_radius=4)
    apply_txt = font.render("Apply", True, WHITE)
    game.virtual_screen.blit(apply_txt, (apply_rect.centerx - apply_txt.get_width()//2, apply_rect.centery - apply_txt.get_height()//2))
    clickable_rects['apply_settings'] = apply_rect
    
    # Delete Button (Row below, or next to Apply if space permits? Let's put below for safety)
    # Actually, let's put Delete to the right of Apply if it fits, or below.
    # col_width is 350. padding 10. 330 usable. 100*3 + 20 gap = 320. It fits!
    del_rect = pygame.Rect(apply_rect.right + 10, current_y, btn_w, 30)
    pygame.draw.rect(game.virtual_screen, BTN_RED, del_rect, border_radius=4)
    del_txt = font.render("Delete", True, WHITE) # Shortened to fit comfortably
    game.virtual_screen.blit(del_txt, (del_rect.centerx - del_txt.get_width()//2, del_rect.centery - del_txt.get_height()//2))
    clickable_rects['delete_config'] = del_rect

    # --- Element 3: DROPDOWN SECTION (Moved DOWN) ---
    # This ensures that when the list expands, it covers empty space, not buttons.
    current_y = save_rect.bottom + 20
    
    # Label
    game.virtual_screen.blit(font.render("Select config to load:", True, WHITE), (preset_body.x + padding, current_y))

    # Dropdown Box
    current_y += 25
    load_rect = pygame.Rect(preset_body.x + padding, current_y, preset_body.width - padding*2, 30)
    clickable_rects['load_config_dd'] = load_rect
    pygame.draw.rect(game.virtual_screen, (50, 50, 50), load_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, load_rect, 1)
    game.virtual_screen.blit(font.render(curr_preset, True, WHITE), (load_rect.x + 5, load_rect.y + 5))
    
    # Dropdown Arrow
    pygame.draw.polygon(game.virtual_screen, WHITE, [(load_rect.right - 15, load_rect.y + 10), (load_rect.right - 5, load_rect.y + 10), (load_rect.right - 10, load_rect.y + 15)])


    # ==========================================================
    # 2. Settings List (Right Side)
    # ==========================================================
    settings_area_x = col_start_x + col_width + 20
    settings_area_w = 600
    settings_rect = pygame.Rect(settings_area_x, 50, settings_area_w, 640)
    
    settings_header = pygame.Rect(settings_rect.x, settings_rect.y, settings_rect.width, header_height)
    settings_body = pygame.Rect(settings_rect.x, settings_rect.y + header_height, settings_rect.width, settings_rect.height - header_height)

    pygame.draw.rect(game.virtual_screen, (30, 30, 30), settings_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, settings_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, settings_rect, 1, border_radius=border_radius)
    
    game.virtual_screen.blit(font.render("Configuration Values", True, WHITE), (settings_header.x + 10, settings_header.y + 7))
    
    content_rect = settings_body.inflate(-20, -20)
    line_h = 40
    
    # Flatten data for drawing
    draw_items = []
    config_data = state.get('settings_data', {})
    
    block_order = ['game', 'map', 'player', 'vehicle', 'item_spawning', 'zombie', 'npc']
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
    
    clip_rect = game.virtual_screen.get_rect().clip(content_rect)
    if clip_rect.width > 0 and clip_rect.height > 0:
        sub = game.virtual_screen.subsurface(clip_rect)
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

                lbl = font_small.render(display_label + ":", True, WHITE)
                sub.blit(lbl, (0, y_off + 12)) 
                
                friendly_text = _get_friendly_value_display(key, val)
                if friendly_text and not is_bool:
                    info_surf = font_small.render(friendly_text, True, GRAY)
                    info_pos_x = input_rect.x - info_surf.get_width() - 15
                    sub.blit(info_surf, (info_pos_x, y_off + 12))

                if is_bool:
                    pygame.draw.rect(sub, (50, 50, 50), input_rect)
                    pygame.draw.rect(sub, WHITE, input_rect, 1)
                    val_text = "True" if str_val == "true" else "False"
                    sub.blit(font_small.render(val_text, True, WHITE), (input_rect.x + 5, input_rect.y + 7))
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_bools'].append((block, key, abs_rect))
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
        pygame.draw.rect(game.virtual_screen, GRAY, state['settings_scroll_handle'], border_radius=2)
    else:
        state['settings_scroll_handle'] = None
    
    state['settings_content_rect'] = content_rect

    # Dropdown Options Overlay
    if state.get('config_dd_active'):
        opts = state.get('config_preset_list', [])
        dd_h = len(opts) * 25
        # Ensure dropdown draws over everything else (Z-Index is high because it's drawn last)
        dd_rect = pygame.Rect(load_rect.x, load_rect.bottom, load_rect.width, dd_h)
        pygame.draw.rect(game.virtual_screen, (40,40,40), dd_rect)
        pygame.draw.rect(game.virtual_screen, WHITE, dd_rect, 1)
        
        dy = dd_rect.y
        for opt in opts:
            opt_r = pygame.Rect(dd_rect.x, dy, dd_rect.width, 25)
            if opt_r.collidepoint(mouse_pos):
                pygame.draw.rect(game.virtual_screen, GRAY, opt_r)
            game.virtual_screen.blit(font.render(opt, True, WHITE), (opt_r.x + 5, opt_r.y + 2))
            clickable_rects['load_config_options'].append((opt, opt_r))
            dy += 25

    return clickable_rects