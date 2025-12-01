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
        # Assume 1.0 = 100%
        return f"({val_float*100:.0f}%)"
        
    return ""

def _draw_settings_screen(game, state, mouse_pos):
    """Draws the Settings configuration screen."""
    # Reuse styles from player build screen
    col_start_x = 170 # Offset for Sidebar
    col_width = 350
    header_height = 30
    border_radius = 4
    padding = 10
    
    clickable_rects = {
        "config_inputs": [], # list of (block, key, rect)
        "config_bools": [],  # NEW: list of (block, key, rect) for boolean toggles
        "save_config": None,
        "delete_config": None,
        "load_config_dd": None,
        "load_config_options": [],
        "seed_input": None
    }

    # 1. Preset Management Panel (Top Left of content area)
    # Increased height to accommodate Seed input
    preset_rect = pygame.Rect(col_start_x, 50, col_width, 270)
    preset_header = pygame.Rect(preset_rect.x, preset_rect.y, preset_rect.width, header_height)
    preset_body = pygame.Rect(preset_rect.x, preset_rect.y + header_height, preset_rect.width, preset_rect.height - header_height)

    pygame.draw.rect(game.virtual_screen, (30, 30, 30), preset_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, preset_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, preset_rect, 1, border_radius=border_radius)
    game.virtual_screen.blit(font.render("Config Preset", True, WHITE), (preset_header.x + 10, preset_header.y + 7))

    # Config Name Input
    game.virtual_screen.blit(font.render("Config Name:", True, WHITE), (preset_body.x + padding, preset_body.y + 10))
    name_input_rect = pygame.Rect(preset_body.x + padding, preset_body.y + 35, preset_body.width - padding*2, 30)
    pygame.draw.rect(game.virtual_screen, (50, 50, 50), name_input_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, name_input_rect, 1)
    
    conf_name = state.get('config_name', "")
    text_surf = font.render(conf_name, True, WHITE)
    game.virtual_screen.blit(text_surf, (name_input_rect.x + 5, name_input_rect.y + 5))
    
    if state.get('config_name_active') and int(pygame.time.get_ticks() / 500) % 2 == 0:
        cx = name_input_rect.x + 5 + text_surf.get_width()
        pygame.draw.line(game.virtual_screen, WHITE, (cx, name_input_rect.y+5), (cx, name_input_rect.bottom-5), 2)
    
    clickable_rects['config_name_input'] = name_input_rect

    # --- World Seed Input ---
    seed_y = name_input_rect.bottom + 10
    game.virtual_screen.blit(font.render("World Seed:", True, WHITE), (preset_body.x + padding, seed_y))
    
    seed_input_rect = pygame.Rect(preset_body.x + padding, seed_y + 25, preset_body.width - padding*2, 30)
    pygame.draw.rect(game.virtual_screen, (50, 50, 50), seed_input_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, seed_input_rect, 1)
    
    seed_val = state.get('world_seed', "")
    if not seed_val:
         game.virtual_screen.blit(font.render("Random", True, GRAY), (seed_input_rect.x + 5, seed_input_rect.y + 5))
    else:
         game.virtual_screen.blit(font.render(seed_val, True, WHITE), (seed_input_rect.x + 5, seed_input_rect.y + 5))
         
    if state.get('seed_input_active') and int(pygame.time.get_ticks() / 500) % 2 == 0:
        cx = seed_input_rect.x + 5 + font.size(seed_val)[0]
        pygame.draw.line(game.virtual_screen, WHITE, (cx, seed_input_rect.y + 5), (cx, seed_input_rect.bottom - 5), 2)
        
    clickable_rects['seed_input'] = seed_input_rect
    # -----------------------

    # Buttons
    btn_w = 100
    buttons_y = seed_input_rect.bottom + 15
    save_rect = pygame.Rect(preset_body.x + padding, buttons_y, btn_w, 30)
    pygame.draw.rect(game.virtual_screen, GREEN, save_rect, border_radius=4)
    game.virtual_screen.blit(font.render("Save", True, WHITE), (save_rect.x + 30, save_rect.y + 5))
    clickable_rects['save_config'] = save_rect

    del_rect = pygame.Rect(save_rect.right + padding, buttons_y, btn_w, 30)
    pygame.draw.rect(game.virtual_screen, RED, del_rect, border_radius=4)
    game.virtual_screen.blit(font.render("Delete", True, WHITE), (del_rect.x + 25, del_rect.y + 5))
    clickable_rects['delete_config'] = del_rect

    # Load Dropdown
    load_rect = pygame.Rect(preset_body.x + padding, buttons_y + 40, preset_body.width - padding*2, 30)
    clickable_rects['load_config_dd'] = load_rect
    pygame.draw.rect(game.virtual_screen, (50, 50, 50), load_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, load_rect, 1)
    curr_preset = state.get('selected_config_preset', 'default')
    game.virtual_screen.blit(font.render(curr_preset, True, WHITE), (load_rect.x + 5, load_rect.y + 5))
    
    # Dropdown arrow
    pygame.draw.polygon(game.virtual_screen, WHITE, [(load_rect.right - 15, load_rect.y + 10), (load_rect.right - 5, load_rect.y + 10), (load_rect.right - 10, load_rect.y + 15)])

    # 2. Settings List (Scrollable Area)
    settings_area_x = col_start_x + col_width + 20
    settings_area_w = 600
    settings_rect = pygame.Rect(settings_area_x, 50, settings_area_w, 640)
    
    settings_header = pygame.Rect(settings_rect.x, settings_rect.y, settings_rect.width, header_height)
    settings_body = pygame.Rect(settings_rect.x, settings_rect.y + header_height, settings_rect.width, settings_rect.height - header_height)

    # Draw Backgrounds
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), settings_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, settings_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, settings_rect, 1, border_radius=border_radius)
    
    # Draw Title in Header
    game.virtual_screen.blit(font.render("Configuration Values", True, WHITE), (settings_header.x + 10, settings_header.y + 7))
    
    # Content calculation (inside body)
    content_rect = settings_body.inflate(-20, -20)
    line_h = 40
    
    # Flatten data for drawing
    draw_items = []
    config_data = state.get('settings_data', {})
    
    # Order of blocks
    block_order = ['game', 'player', 'item_spawning', 'zombie']
    for k in config_data:
        if k not in block_order: block_order.append(k)

    for block in block_order:
        if block not in config_data: continue
        draw_items.append(('header', block))
        # val_data is now {'value': ..., 'name': ...}
        for key, val_data in config_data[block].items():
            draw_items.append(('item', block, key, val_data))

    total_h = len(draw_items) * line_h
    max_scroll = max(0, total_h - content_rect.height)
    state['settings_max_scroll'] = max_scroll
    scroll_y = state.get('settings_scroll_y', 0)
    
    # Clip surface
    clip_rect = game.virtual_screen.get_rect().clip(content_rect)
    if clip_rect.width > 0 and clip_rect.height > 0:
        sub = game.virtual_screen.subsurface(clip_rect)
        sub.fill((30, 30, 30))
        
        y_off = -scroll_y
        for item in draw_items:
            # Draw Item relative to sub
            if item[0] == 'header':
                pygame.draw.rect(sub, GRAY_60, (0, y_off, content_rect.width, line_h))
                text = font.render(item[1].upper(), True, YELLOW)
                sub.blit(text, (10, y_off + 10))
            else:
                block, key, val_data = item[1], item[2], item[3]
                
                if isinstance(val_data, dict):
                    display_label = val_data.get('name', key)
                    val = val_data.get('value')
                else:
                    display_label = key
                    val = val_data
                
                lbl = font_small.render(display_label + ":", True, WHITE)
                sub.blit(lbl, (20, y_off + 12))
                
                input_w = 200
                input_rect = pygame.Rect(content_rect.width - input_w - 10, y_off + 5, input_w, 30)
                abs_rect = pygame.Rect(content_rect.x + input_rect.x, content_rect.y + input_rect.y, input_rect.width, input_rect.height)
                
                # Check if boolean
                str_val = str(val).lower()
                is_bool = str_val in ('true', 'false')
                
                if is_bool:
                    # Draw as a "Dropdown" / Toggle Button
                    # Background
                    pygame.draw.rect(sub, (50, 50, 50), input_rect)
                    pygame.draw.rect(sub, WHITE, input_rect, 1)
                    
                    # Value
                    val_text = "True" if str_val == "true" else "False"
                    txt_surf = font_small.render(val_text, True, WHITE)
                    sub.blit(txt_surf, (input_rect.x + 5, input_rect.y + 7))
                    
                    # Dropdown Arrow (relative to sub)
                    arrow_x = input_rect.right - 15
                    arrow_y = input_rect.y + 10
                    pygame.draw.polygon(sub, WHITE, [(arrow_x, arrow_y), (arrow_x + 10, arrow_y), (arrow_x + 5, arrow_y + 5)])
                    
                    # Add to bool clickables
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_bools'].append((block, key, abs_rect))
                else:
                    # Draw as Text Input
                    is_active = (state.get('active_setting') == (block, key))
                    col = WHITE if is_active else GRAY
                    
                    pygame.draw.rect(sub, (50, 50, 50), input_rect)
                    pygame.draw.rect(sub, col, input_rect, 1)
                    
                    val_text = str(val)
                    txt_surf = font_small.render(val_text, True, WHITE)
                    
                    # Text clipping inside input box
                    txt_clip = pygame.Rect(input_rect.x + 5, input_rect.y, input_rect.width - 10, input_rect.height)
                    sub.blit(txt_surf, (input_rect.x + 5, input_rect.y + 7))
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['config_inputs'].append((block, key, abs_rect))

                    # --- USER FRIENDLY DISPLAY HELPER ---
                    friendly_text = _get_friendly_value_display(key, val)
                    if friendly_text:
                        info_surf = font_small.render(friendly_text, True, GRAY)
                        # Draw to the left of the input box
                        info_pos_x = input_rect.x - info_surf.get_width() - 10
                        info_pos_y = input_rect.y + 7
                        sub.blit(info_surf, (info_pos_x, info_pos_y))
                    # ------------------------------------
                
            y_off += line_h

    # Scrollbar
    if max_scroll > 0:
        bar_area = pygame.Rect(settings_body.right - 14, settings_body.y + 5, 10, settings_body.height - 10)
        handle_h = max(20, (content_rect.height / total_h) * bar_area.height)
        
        if max_scroll > 0:
            scroll_pct = scroll_y / max_scroll
        else:
            scroll_pct = 0
            
        handle_y = bar_area.y + (scroll_pct * (bar_area.height - handle_h))
        handle_rect = pygame.Rect(bar_area.x, handle_y, 10, handle_h)
        pygame.draw.rect(game.virtual_screen, GRAY, handle_rect, border_radius=2)
        
        state['settings_scroll_handle'] = handle_rect
        state['settings_scrollbar_track'] = bar_area
    else:
        state['settings_scroll_handle'] = None
    
    state['settings_content_rect'] = content_rect

    # Draw dropdown list if active (on top)
    if state.get('config_dd_active'):
        opts = state.get('config_preset_list', [])
        dd_h = len(opts) * 25
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