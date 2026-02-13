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
    BTN_BLUE = (23, 162, 184)  # Bootstrap Info/Teal
    
    clickable_rects = {
        "config_inputs": [], 
        "config_bools": [],
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
        pygame.draw.rect(game.game_screen, GRAY, state['settings_scroll_handle'], border_radius=2)
    else:
        state['settings_scroll_handle'] = None
    
    state['settings_content_rect'] = content_rect

    return clickable_rects