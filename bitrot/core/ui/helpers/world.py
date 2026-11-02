# core/ui/helpers/world.py
import pygame
import os
import random
from datetime import datetime
import core.data.config
from core.data.config import *
from core.ui.helpers.trait_config_loader import load_config_data, save_config_json
from core.data.localization import tr
from core.ui.modals import draw_scrollbar

def _get_friendly_value_display(key, value):
    try: val_float = float(value)
    except: return ""

    if key in ['time_daylength', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']: 
        seconds = val_float / 1000.0
        if seconds >= 60: return f"({seconds/60:.1f} {tr('ui', 'min')})"
        return f"({seconds:.0f} {tr('ui', 'sec')})"
        
    if '_hr' in key: 
        hours = int(val_float)
        minutes = int((val_float - hours) * 60)
        return f"({hours:02d}:{minutes:02d})"
        
    if 'multiplier' in key or 'chance' in key or 'percent' in key:
        return f"({val_float*100:.0f}%)"
        
    if key in ['map_chunks', 'chunks']:
        size = int(val_float)
        return f"({size} {tr('ui', 'Chunks')})"

    if key == 'view_radius':
        return f"({int(val_float)} {tr('ui', 'tiles')})"

    if 'threshold' in key:
        return f"({int(val_float)}%)"

    return ""

def _get_world_presets_dir():
    candidates = [
        os.path.join(get_writable_dir(), "data.rot", "save", "world"),
        os.path.join(BASE_DIR, "data.rot", "save", "world"),
        os.path.join(get_writable_dir(), "bitrot", "data.rot", "save", "world"),
        os.path.join(BASE_DIR, "bitrot", "data.rot", "save", "world"),
    ]
    for d in candidates:
        if os.path.exists(d):
            return d
    target = os.path.join(get_writable_dir(), "data.rot", "save", "world")
    os.makedirs(target, exist_ok=True)
    return target

def _load_world_presets(state):
    preset_dir = _get_world_presets_dir()
    presets = ["world"]
    try:
        files = [f for f in os.listdir(preset_dir) if f.endswith('.json')]
        for f in sorted(files):
            name = os.path.splitext(f)[0]
            if name != 'world' and name not in presets:
                presets.append(name)
    except Exception:
        pass
    state['config_preset_list'] = presets

def _clone_to_custom(state):
    state['world_unsaved'] = True

def _save_world_preset(state):
    preset_name = state.get('world_preset_name', '').strip()
    if not preset_name or preset_name == "world":
        preset_name = state.get('selected_config_preset', 'world')
    if not preset_name:
        preset_name = datetime.now().strftime("world_%Y%m%d_%H%M%S")

    # Avoid spaces: convert to underscores
    preset_name = preset_name.replace(' ', '_')
    state['world_preset_name'] = preset_name
    state['selected_config_preset'] = preset_name

    preset_dir = _get_world_presets_dir()
    save_path = os.path.join(preset_dir, f"{preset_name}.json")

    # Sync seed into world_data map block
    if 'map' not in state['world_data']:
        state['world_data']['map'] = {}
    if 'seed' not in state['world_data']['map']:
        state['world_data']['map']['seed'] = {'name': 'World seed', 'default': ''}
    state['world_data']['map']['seed']['value'] = str(state.get('world_seed', ''))

    save_config_json(state['world_data'], save_path)
    state['world_unsaved'] = False
    _load_world_presets(state)

def _delete_world_preset(state):
    preset_name = state.get('selected_config_preset', 'world')
    if preset_name and preset_name != 'world':
        preset_dir = _get_world_presets_dir()
        filepath = os.path.join(preset_dir, f"{preset_name}.json")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Error deleting preset: {e}")

    state['selected_config_preset'] = 'world'
    state['world_preset_name'] = datetime.now().strftime("world_%Y%m%d_%H%M%S")
    path = core.data.config.get_world_config_path('world')
    state['world_data'] = load_config_data(path)
    state['world_unsaved'] = False
    _load_world_presets(state)

def _draw_world_screen(game, state, mouse_pos):
    if not hasattr(game, 'world_setup_state'):
        game.world_setup_state = {}
        
    state = game.world_setup_state

    scale = UI_SCALE
    def S(val): return int(val * scale)

    if not state.get('world_data'):
        preset_name = state.get('selected_config_preset', 'world')
        state['world_preset_name'] = preset_name
        correct_path = core.data.config.get_world_config_path(preset_name)
        state['world_data'] = load_config_data(correct_path)
        state['world_unsaved'] = False
        state['seed_input_active'] = False
        _load_world_presets(state)

    # Always ensure preset name field is pre-filled with a timestamp
    if not state.get('world_preset_name'):
        state['world_preset_name'] = datetime.now().strftime("world_%Y%m%d_%H%M%S")

    # Always ensure a valid seed exists and is synchronized
    if not state.get('world_seed'):
        existing_seed = state.get('world_data', {}).get('map', {}).get('seed', {}).get('value', '')
        if existing_seed and str(existing_seed).strip():
            state['world_seed'] = str(existing_seed).strip()
        else:
            state['world_seed'] = "".join(str(random.randint(0, 9)) for _ in range(12))

    if 'map' in state['world_data'] and 'seed' in state['world_data']['map']:
        state['world_data']['map']['seed']['value'] = str(state['world_seed'])

    center_offset_x = (GAME_WIDTH - S(1280)) // 2
    center_offset_y = (GAME_HEIGHT - S(720)) // 2
    
    col1_x = S(170) + center_offset_x
    base_y = S(30) + center_offset_y
    
    col1_width = S(270)
    col2_x = col1_x + col1_width + S(20)
    col2_width = S(225)
    col3_x = col2_x + col2_width + S(20)
    col3_width = S(225)
    col4_x = col3_x + col3_width + S(20)
    col4_width = S(275)
    
    header_height = S(30)
    border_radius = S(4)
    padding = S(10)
    
    BTN_GREEN = (50, 205, 50)
    
    clickable_rects = {
        "world_inputs": [], 
        "world_bools": [],
        "world_cycles": [],
        "next_tab": None,
        "load_dropdown_button": None,
        "load_dropdown_options": [],
        "save_button": None,
        "delete_button": None,
        "name_input": None,
        "seed_input": None
    }

    settings_area_x = col1_x
    settings_area_w = (col3_x + col3_width) - col1_x
    settings_rect = pygame.Rect(settings_area_x, base_y, settings_area_w, S(640))
    
    settings_header = pygame.Rect(settings_rect.x, settings_rect.y, settings_rect.width, header_height)
    settings_body = pygame.Rect(settings_rect.x, settings_rect.y + header_height, settings_rect.width, settings_rect.height - header_height)

    pygame.draw.rect(game.game_screen, (30, 30, 30), settings_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, settings_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, settings_rect, 1, border_radius=border_radius)
    
    game.game_screen.blit(font_12.render(tr('ui', "World Rules"), False, WHITE), (settings_header.x + S(10), settings_header.y + S(7)))
    
    content_rect = settings_body.inflate(-S(20), -S(20))
    line_h = S(40)
    
    draw_items = []
    config_data = state.get('world_data', {})
    
    block_order = ['game', 'player', 'map', 'item_spawning', 'vehicle', 'zombie', 'npc', 'animal']
    for k in config_data:
        if k not in block_order and k not in ['ui', 'audio', 'durability', 'preferences']: 
            block_order.append(k)

    for block in block_order:
        if block not in config_data: continue
        draw_items.append(('header', block))
        for key, val_data in config_data[block].items():
            if key == 'seed': 
                continue
            if key == 'spawn' and block in ['zombie', 'npc', 'animal']:
                continue
            draw_items.append(('item', block, key, val_data))

    total_h = len(draw_items) * line_h
    max_scroll = max(0, total_h - content_rect.height)
    state['world_max_scroll'] = max_scroll
    scroll_y = state.get('world_scroll_y', 0)
    
    clip_rect = game.game_screen.get_rect().clip(content_rect)
    if clip_rect.width > 0 and clip_rect.height > 0:
        sub = game.game_screen.subsurface(clip_rect)
        sub.fill((30, 30, 30))
        
        y_off = -scroll_y
        for item in draw_items:
            if item[0] == 'header':
                header_name = tr('ui', item[1].capitalize())
                text = font_12.render(header_name.upper(), False, YELLOW)
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
                is_bool = str_val in ('true', 'false') or isinstance(val, bool)
                
                is_time_cycle = key in ['time_sunrise_hr', 'time_sunset_hr', 'time_start_hr']
                is_percent_cycle = ('chance' in key) or (block == 'item_spawning' and 'multiplier' in key) or key in ['static_percent', 'hostile_percent']
                is_view_cycle = key in ['view_radius']
                is_max_ent_cycle = key in ['vehicle_spawn_per_chunk', 'zombie_spawn_per_chunk', 'npc_spawn_per_chunk', 'animal_spawn_per_chunk']
                is_legacy_cycle = key in ['time_daylength', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']
                is_int_percent_cycle = ('threshold' in key)
                
                is_cycle_setting = is_time_cycle or is_percent_cycle or is_view_cycle or is_max_ent_cycle or is_legacy_cycle or is_int_percent_cycle

                lbl = font_12.render(display_label + ":", False, WHITE)
                sub.blit(lbl, (0, y_off + S(12))) 
                
                friendly_text = _get_friendly_value_display(key, val)
                if friendly_text and not is_bool and not is_cycle_setting:
                    info_surf = font_12.render(friendly_text, False, GRAY)
                    info_pos_x = input_rect.x - info_surf.get_width() - S(15)
                    sub.blit(info_surf, (info_pos_x, y_off + S(12)))

                if is_bool:
                    is_disabled = False
                    if key in ('start_at_the_lobby', 'start_lobby', 'no_boat_to_lobby'):
                        lobby_gen_val = config_data.get('game', {}).get('generate_lobby_chunk', {}).get('value', True)
                        if str(lobby_gen_val).lower() not in ('true', '1') and lobby_gen_val is not True:
                            str_val = "false"
                            is_disabled = True

                    hovered = abs_rect.collidepoint(mouse_pos) and not is_disabled
                    
                    if is_disabled:
                        bg_color = (35, 35, 35)
                        border_color = (55, 55, 55)
                        arrow_color = (70, 70, 70)
                        text_color = (90, 90, 90)
                    else:
                        bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                        border_color = WHITE
                        arrow_color = WHITE
                        text_color = WHITE

                    pygame.draw.rect(sub, bg_color, input_rect, border_radius=3)
                    pygame.draw.rect(sub, border_color, input_rect, 1, border_radius=3)

                    val_text = tr('ui', "True") if (val is True or str_val == "true") else tr('ui', "False")
                    txt_surf = font_12.render(val_text, False, text_color)
                    text_x = input_rect.x + (input_rect.width - txt_surf.get_width()) // 2
                    text_y = input_rect.y + (input_rect.height - txt_surf.get_height()) // 2
                    sub.blit(txt_surf, (text_x, text_y))
                    
                    pygame.draw.polygon(sub, arrow_color, [(input_rect.right - S(8), input_rect.centery), (input_rect.right - S(14), input_rect.centery - S(4)), (input_rect.right - S(14), input_rect.centery + S(4))])
                    pygame.draw.polygon(sub, arrow_color, [(input_rect.x + S(8), input_rect.centery), (input_rect.x + S(14), input_rect.centery - S(4)), (input_rect.x + S(14), input_rect.centery + S(4))])
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['world_bools'].append((block, key, abs_rect))
                        
                elif is_cycle_setting:
                    hovered = abs_rect.collidepoint(mouse_pos)
                    bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                    pygame.draw.rect(sub, bg_color, input_rect, border_radius=3)
                    pygame.draw.rect(sub, WHITE, input_rect, 1, border_radius=3)
                    
                    try: current_val_float = float(val)
                    except: current_val_float = 0.0
                        
                    if is_time_cycle:
                        hours = int(current_val_float)
                        minutes = int((current_val_float - hours) * 60)
                        label = f"{hours:02d}:{minutes:02d}"
                    elif is_percent_cycle:
                        label = f"{int(round(current_val_float * 100))}%"
                    elif is_int_percent_cycle:
                        disp_val = current_val_float * 100 if current_val_float <= 1.0 and current_val_float > 0 and "." in str(val) else current_val_float
                        label = f"{int(disp_val)}%"
                    elif is_view_cycle:
                        label = f"{int(current_val_float)} tiles"
                    elif is_max_ent_cycle:
                        label = f"{int(current_val_float)} spawn"
                    elif is_legacy_cycle:
                        mins = int(current_val_float / 60000)
                        if mins == 0: mins = 15
                        label = f"{mins} {tr('ui', 'min')}"
                    else:
                        label = f"{str(current_val_float)}"
                
                    txt_surf = font_12.render(label, False, WHITE)
                    text_x = input_rect.x + (input_rect.width - txt_surf.get_width()) // 2
                    text_y = input_rect.y + (input_rect.height - txt_surf.get_height()) // 2
                    sub.blit(txt_surf, (text_x, text_y))
                    
                    pygame.draw.polygon(sub, WHITE, [(input_rect.right - S(8), input_rect.centery), (input_rect.right - S(14), input_rect.centery - S(4)), (input_rect.right - S(14), input_rect.centery + S(4))])
                    pygame.draw.polygon(sub, WHITE, [(input_rect.x + S(8), input_rect.centery), (input_rect.x + S(14), input_rect.centery - S(4)), (input_rect.x + S(14), input_rect.centery + S(4))])
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['world_cycles'].append((block, key, abs_rect))
                else:
                    is_active = (state.get('active_setting') == (block, key))
                    col = WHITE if is_active else GRAY
                    pygame.draw.rect(sub, (50, 50, 50), input_rect)
                    pygame.draw.rect(sub, col, input_rect, 1)
                    
                    txt_surf = font_12.render(str(val), False, WHITE)
                    sub.blit(txt_surf, (input_rect.x + S(5), input_rect.y + S(7)))
                    
                    if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                        clickable_rects['world_inputs'].append((block, key, abs_rect))
            
            pygame.draw.line(sub, (55, 55, 55), (0, y_off + line_h - 1), (content_rect.width, y_off + line_h - 1), 1)
            y_off += line_h

    if max_scroll > 0:
        bar_area = pygame.Rect(settings_body.right - S(14), settings_body.y + S(5), 8, settings_body.height - S(10))
        draw_scrollbar(game.game_screen, state, bar_area, content_rect.height, total_h, scroll_y)
        state['world_scroll_handle'] = state['scrollbar_handle_rect']
        state['world_scrollbar_track'] = bar_area
    else:
        state['world_scroll_handle'] = None
    
    state['world_content_rect'] = content_rect
    
    # --- RIGHT PANEL (WORLD PRESET, SAVE/DELETE, DROPDOWN, WORLD SEED) ---
    preset_rect = pygame.Rect(col4_x, base_y, col4_width, S(550))
    preset_header = pygame.Rect(preset_rect.x, preset_rect.y, preset_rect.width, header_height)
    preset_body = pygame.Rect(preset_rect.x, preset_rect.y + header_height, preset_rect.width, preset_rect.height - header_height)

    pygame.draw.rect(game.game_screen, (30, 30, 30), preset_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, preset_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, preset_rect, 1, border_radius=border_radius)
    game.game_screen.blit(font_12.render(tr('ui', "World Preset"), False, WHITE), (preset_header.x + S(10), preset_header.y + S(7)))

    # 1. Preset Name Field (Pre-filled with timestamp)
    cur_y = preset_body.y + S(12)
    game.game_screen.blit(font_12.render(tr('ui', "Preset Name:"), False, WHITE), (preset_body.x + padding, cur_y))
    name_input_rect = pygame.Rect(preset_body.x + padding, cur_y + S(20), preset_body.width - padding * 2, S(30))
    
    pygame.draw.rect(game.game_screen, (50, 50, 50), name_input_rect)
    pygame.draw.rect(game.game_screen, WHITE if state.get('name_input_active') else GRAY, name_input_rect, 1)
    
    preset_name_text = state.get('world_preset_name', '')
    p_name_surf = font_12.render(preset_name_text, False, WHITE)
    clickable_rects['name_input'] = name_input_rect
    
    if state.get('name_input_active') and int(pygame.time.get_ticks() / 500) % 2 == 0:
        cursor_x = name_input_rect.x + S(6) + p_name_surf.get_width()
        pygame.draw.line(game.game_screen, WHITE, (cursor_x, name_input_rect.y + S(5)), (cursor_x, name_input_rect.bottom - S(5)), S(2))
        
    game.game_screen.blit(p_name_surf, (name_input_rect.x + S(6), name_input_rect.y + S(7)))

    # 2. Save and Delete Buttons
    cur_y = name_input_rect.bottom + S(12)
    btn_w = (preset_body.width - (padding * 2) - S(10)) // 2
    
    save_btn_rect = pygame.Rect(preset_body.x + padding, cur_y, btn_w, S(30))
    is_save_hover = save_btn_rect.collidepoint(mouse_pos)
    pygame.draw.rect(game.game_screen, (80, 80, 80) if is_save_hover else (60, 60, 60), save_btn_rect, border_radius=4)
    save_txt = font_12.render(tr('ui', "Save"), False, WHITE)
    game.game_screen.blit(save_txt, save_txt.get_rect(center=save_btn_rect.center))
    clickable_rects['save_button'] = save_btn_rect

    delete_btn_rect = pygame.Rect(save_btn_rect.right + S(10), cur_y, btn_w, S(30))
    is_del_hover = delete_btn_rect.collidepoint(mouse_pos)
    pygame.draw.rect(game.game_screen, (80, 80, 80) if is_del_hover else (60, 60, 60), delete_btn_rect, border_radius=4)
    del_txt = font_12.render(tr('ui', "Delete"), False, WHITE)
    game.game_screen.blit(del_txt, del_txt.get_rect(center=delete_btn_rect.center))
    clickable_rects['delete_button'] = delete_btn_rect

    # 3. Presets Dropdown Selector
    cur_y = save_btn_rect.bottom + S(14)
    load_dd_rect = pygame.Rect(preset_body.x + padding, cur_y, preset_body.width - padding * 2, S(30))
    clickable_rects['load_dropdown_button'] = load_dd_rect
    is_dd_hover = load_dd_rect.collidepoint(mouse_pos)
    
    pygame.draw.rect(game.game_screen, (60, 60, 60) if is_dd_hover else (50, 50, 50), load_dd_rect)
    pygame.draw.rect(game.game_screen, YELLOW if is_dd_hover else WHITE, load_dd_rect, 1)
    
    selected_preset = state.get('selected_config_preset', "world")
    game.game_screen.blit(font_12.render(selected_preset, False, WHITE), (load_dd_rect.x + S(6), load_dd_rect.y + S(7)))
    pygame.draw.polygon(game.game_screen, WHITE, [
        (load_dd_rect.right - S(15), load_dd_rect.y + S(11)),
        (load_dd_rect.right - S(5), load_dd_rect.y + S(11)),
        (load_dd_rect.right - S(10), load_dd_rect.y + S(18))
    ])

    # 4. World Seed Input (At the bottom of presets)
    cur_y = load_dd_rect.bottom + S(22)
    game.game_screen.blit(font_12.render(tr('ui', "World Seed (12-digit):"), False, WHITE), (preset_body.x + padding, cur_y))
    seed_input_rect = pygame.Rect(preset_body.x + padding, cur_y + S(20), preset_body.width - padding * 2, S(30))
    
    pygame.draw.rect(game.game_screen, (50, 50, 50), seed_input_rect)
    pygame.draw.rect(game.game_screen, WHITE if state.get('seed_input_active') else GRAY, seed_input_rect, 1)
    
    seed_text = state.get('world_seed', '')
    seed_surf = font_12.render(seed_text, False, WHITE)
    clickable_rects['seed_input'] = seed_input_rect
    
    if state.get('seed_input_active') and int(pygame.time.get_ticks() / 500) % 2 == 0:
        cursor_x = seed_input_rect.x + S(6) + seed_surf.get_width()
        pygame.draw.line(game.game_screen, WHITE, (cursor_x, seed_input_rect.y + S(5)), (cursor_x, seed_input_rect.bottom - S(5)), S(2))
        
    game.game_screen.blit(seed_surf, (seed_input_rect.x + S(6), seed_input_rect.y + S(7)))

    # 5. Dropdown Popup Overlay (Drawn on top)
    if state.get('config_dd_active'):
        options = state.get('config_preset_list', ["world"])
        option_height = S(25)
        max_visible = 6
        visible_count = min(len(options), max_visible)
        list_height = visible_count * option_height
        total_height = len(options) * option_height
        
        list_rect = pygame.Rect(load_dd_rect.x, load_dd_rect.bottom + S(2), load_dd_rect.width, list_height)
        state['config_list_rect'] = list_rect
        
        pygame.draw.rect(game.game_screen, (30, 30, 30), list_rect)
        pygame.draw.rect(game.game_screen, WHITE, list_rect, 1)
        
        max_list_scroll = max(0, total_height - list_height)
        state['config_max_scroll'] = max_list_scroll
        list_scroll_y = max(0, min(state.get('config_scroll_y', 0), max_list_scroll))
        state['config_scroll_y'] = list_scroll_y
        
        drawable_list_rect = game.game_screen.get_rect().clip(list_rect)
        
        if drawable_list_rect.width > 0 and drawable_list_rect.height > 0:
            list_surface = game.game_screen.subsurface(drawable_list_rect)
            y_offset = 0 - list_scroll_y
            for option_name in options:
                row_rect_rel = pygame.Rect(0, y_offset, list_rect.width, option_height)
                row_rect_abs = pygame.Rect(list_rect.x, list_rect.y + y_offset, list_rect.width, option_height)
                
                if row_rect_rel.bottom > 0 and row_rect_rel.top < list_rect.height:
                    is_h = row_rect_abs.collidepoint(mouse_pos)
                    if is_h:
                        pygame.draw.rect(list_surface, (70, 70, 70), row_rect_rel)
                    col_txt = YELLOW if option_name == selected_preset else WHITE
                    list_surface.blit(font_12.render(option_name, False, col_txt), (row_rect_rel.x + S(6), row_rect_rel.y + S(4)))
                    clickable_rects["load_dropdown_options"].append((option_name, row_rect_abs))
                y_offset += option_height

    next_rect = pygame.Rect(col4_x, S(310) + S(20) + S(240) + S(20), col4_width, S(70))
    is_unsaved = state.get('world_unsaved', False)

    clickable_rects['next_tab'] = next_rect

    if is_unsaved:
        pygame.draw.rect(game.game_screen, (200, 130, 20), next_rect, border_radius=border_radius)
        if next_rect.collidepoint(mouse_pos):
            pygame.draw.rect(game.game_screen, (220, 150, 40), next_rect.inflate(-S(4), -S(4)), border_radius=border_radius)
        next_txt = font_16.render(tr('ui', "SAVE AND CONTINUE"), True, WHITE)
    else:
        pygame.draw.rect(game.game_screen, BTN_GREEN, next_rect, border_radius=border_radius)
        if next_rect.collidepoint(mouse_pos):
            pygame.draw.rect(game.game_screen, (0, 150, 0), next_rect.inflate(-S(4), -S(4)), border_radius=border_radius)
        next_txt = font_16.render(tr('ui', "NEXT: PLAYER SETUP"), True, WHITE)

    game.game_screen.blit(next_txt, next_txt.get_rect(center=next_rect.center))
    return clickable_rects

def handle_world_events(game, state, event, mouse_pos, clickable_rects=None):
    if not hasattr(game, 'world_setup_state'):
        game.world_setup_state = {}
    state = game.world_setup_state
    scale = UI_SCALE
    def S(val): return int(val * scale)

    if clickable_rects is None:
        clickable_rects = _draw_world_screen(game, state, mouse_pos)

    if event.type == pygame.MOUSEWHEEL:
        rect = state.get('world_content_rect')
        list_rect = state.get('config_list_rect')
        if state.get('config_dd_active') and list_rect and list_rect.collidepoint(mouse_pos):
            state['config_scroll_y'] = max(0, min(state.get('config_scroll_y', 0) - (event.y * S(30)), state.get('config_max_scroll', 0)))
        elif rect and rect.collidepoint(mouse_pos):
            state['world_scroll_y'] = max(0, min(state.get('world_scroll_y', 0) - (event.y * S(30)), state.get('world_max_scroll', 0)))
    
    elif event.type == pygame.KEYDOWN:
        if state.get('name_input_active'):
            current_val = state.get('world_preset_name', '')
            if event.key == pygame.K_BACKSPACE:
                state['world_preset_name'] = current_val[:-1]
                state['world_unsaved'] = True
            elif event.key == pygame.K_RETURN: 
                state['name_input_active'] = False
            elif event.key == pygame.K_SPACE or event.unicode == ' ':
                # Replace space with underscore
                state['world_preset_name'] = current_val + '_'
                state['world_unsaved'] = True
            else: 
                if len(current_val) < 28 and event.unicode.isprintable():
                    char_to_add = '_' if event.unicode == ' ' else event.unicode
                    state['world_preset_name'] = current_val + char_to_add
                    state['world_unsaved'] = True

        elif state.get('seed_input_active'):
            current_val = state.get('world_seed', '')
            if event.key == pygame.K_BACKSPACE:
                state['world_seed'] = current_val[:-1]
                state['world_unsaved'] = True
            elif event.key == pygame.K_RETURN: 
                state['seed_input_active'] = False
            else: 
                if len(current_val) < 12 and event.unicode.isnumeric():
                    state['world_seed'] = current_val + event.unicode
                    state['world_unsaved'] = True

        elif state.get('active_setting'):
            block, key = state['active_setting']
            setting_obj = state['world_data'][block][key]
            
            if not isinstance(setting_obj, dict):
                 setting_obj = {'value': setting_obj, 'name': key}
                 state['world_data'][block][key] = setting_obj
            
            current_val = str(setting_obj['value'])
            if event.key == pygame.K_BACKSPACE:
                setting_obj['value'] = current_val[:-1]
                _clone_to_custom(state)
                state['world_unsaved'] = True
            elif event.key == pygame.K_RETURN: 
                state['active_setting'] = None
            else: 
                if event.unicode.isnumeric() if key in ['map_chunks', 'chunks'] else event.unicode.isprintable():
                    setting_obj['value'] = current_val + event.unicode
                    _clone_to_custom(state)
                    state['world_unsaved'] = True
                
    elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
        state['active_setting'] = None
        state['name_input_active'] = False
        state['seed_input_active'] = False
        
        if state.get('world_scroll_handle') and state['world_scroll_handle'].collidepoint(mouse_pos):
            state['is_dragging_world_scrollbar'] = True
            state['world_scroll_drag_last_y'] = mouse_pos[1]
            return

        # Save and Continue
        if clickable_rects.get('next_tab') and clickable_rects['next_tab'].collidepoint(mouse_pos):
            # Save the preset
            _save_world_preset(state)

            mode_id = state.get('chosen_mode', 'sandbox')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_name = f"save_{mode_id}_{timestamp}"
            save_path = os.path.join(get_writable_dir(), "data.rot", "save", "game", save_name)
            os.makedirs(save_path, exist_ok=True)

            world_json_path = os.path.join(save_path, "world.json")
            save_config_json(state['world_data'], world_json_path)

            game.current_save_folder_name = save_name
            state['save_folder_name'] = save_name
            state['world_json_path'] = world_json_path

            game.player_setup_state['save_folder_name'] = save_name
            game.player_setup_state['world_json_path'] = world_json_path
            game.player_setup_state['world_data'] = state['world_data']
            game.player_setup_state['world_seed'] = state.get('world_seed', '')
            game.player_setup_state['selected_config_preset'] = state.get('selected_config_preset', 'world')
            game.player_setup_state['world_preset_name'] = state.get('world_preset_name', 'world')
            game.player_setup_state['chosen_mode'] = mode_id
            game.player_setup_state['current_tab'] = 'Player'
            return

        if clickable_rects.get('name_input') and clickable_rects['name_input'].collidepoint(mouse_pos):
            state['name_input_active'] = True
            return

        if clickable_rects.get('seed_input') and clickable_rects['seed_input'].collidepoint(mouse_pos):
            state['seed_input_active'] = True
            return

        if clickable_rects.get('save_button') and clickable_rects['save_button'].collidepoint(mouse_pos):
            _save_world_preset(state)
            return

        if clickable_rects.get('delete_button') and clickable_rects['delete_button'].collidepoint(mouse_pos):
            _delete_world_preset(state)
            return

        if state.get('config_dd_active'):
            if state.get('config_list_rect') and state['config_list_rect'].collidepoint(mouse_pos):
                for option_name, option_rect in clickable_rects.get("load_dropdown_options", []):
                    if option_rect.collidepoint(mouse_pos):
                        state['selected_config_preset'] = option_name
                        state['world_preset_name'] = option_name
                        state['config_dd_active'] = False
                        
                        # Automatically load the selected preset and fulfill fields
                        path = core.data.config.get_world_config_path(option_name)
                        state['world_data'] = load_config_data(path)
                        state['world_unsaved'] = False
                        
                        xml_seed = state['world_data'].get('map', {}).get('seed', {}).get('value', '')
                        if xml_seed and str(xml_seed).strip():
                            state['world_seed'] = str(xml_seed).strip()
                        break
                return 
            elif clickable_rects.get('load_dropdown_button') and clickable_rects['load_dropdown_button'].collidepoint(mouse_pos):
                state['config_dd_active'] = False
                return 
            else:
                state['config_dd_active'] = False
        elif clickable_rects.get('load_dropdown_button') and clickable_rects['load_dropdown_button'].collidepoint(mouse_pos):
            state['config_dd_active'] = True
            return

        clicked_input = False
        for block, key, rect in clickable_rects.get('world_inputs', []):
            if rect.collidepoint(mouse_pos):
                state['active_setting'] = (block, key)
                clicked_input = True
                break
        
        if not clicked_input:
            for block, key, rect in clickable_rects.get('world_bools', []):
                if rect.collidepoint(mouse_pos):
                    setting_obj = state['world_data'][block][key]
                    if not isinstance(setting_obj, dict):
                         setting_obj = {'value': setting_obj, 'name': key}
                         state['world_data'][block][key] = setting_obj

                    current_val = setting_obj['value']

                    if key in ('start_at_the_lobby', 'start_lobby', 'no_boat_to_lobby'):
                        lobby_gen_val = state['world_data'].get('game', {}).get('generate_lobby_chunk', {}).get('value', True)
                        if str(lobby_gen_val).lower() not in ('true', '1') and lobby_gen_val is not True:
                            clicked_input = True
                            break

                    is_true = (current_val is True or str(current_val).lower() == "true")
                    new_val = not is_true

                    if key in ('generate_lobby_chunk', 'spawn_lobby_chunk') and not new_val:
                        if 'game' in state['world_data']:
                            if 'start_at_the_lobby' in state['world_data']['game']:
                                if isinstance(state['world_data']['game']['start_at_the_lobby'], dict):
                                    state['world_data']['game']['start_at_the_lobby']['value'] = False
                            if 'no_boat_to_lobby' in state['world_data']['game']:
                                if isinstance(state['world_data']['game']['no_boat_to_lobby'], dict):
                                    state['world_data']['game']['no_boat_to_lobby']['value'] = False

                    state['world_data'][block][key]['value'] = new_val
                    _clone_to_custom(state)
                    state['world_unsaved'] = True
                    clicked_input = True
                    break
                    
        if not clicked_input:
            for block, key, rect in clickable_rects.get('world_cycles', []):
                if rect.collidepoint(mouse_pos):
                    setting_obj = state['world_data'][block][key]
                    if not isinstance(setting_obj, dict):
                         setting_obj = {'value': setting_obj, 'name': key}
                         state['world_data'][block][key] = setting_obj

                    try: current_val_float = float(setting_obj['value'])
                    except: current_val_float = 0.0

                    is_time_cycle = key in ['time_sunrise_hr', 'time_sunset_hr', 'time_start_hr']
                    is_percent_cycle = ('chance' in key) or (block == 'item_spawning' and 'multiplier' in key) or key in ['static_percent', 'hostile_percent']
                    is_view_cycle = key in ['view_radius']
                    is_max_ent_cycle = key in ['vehicle_spawn_per_chunk', 'zombie_spawn_per_chunk', 'npc_spawn_per_chunk', 'animal_spawn_per_chunk']
                    is_legacy_cycle = key in ['time_daylength', 'respawn_timer', 'zombie_respawn_timer_ms', 'animal_respawn_ms_timer']
                    is_int_percent_cycle = ('threshold' in key)

                    dir_step = -1 if mouse_pos[0] < rect.centerx else 1

                    if is_time_cycle:
                        new_val = current_val_float + (0.5 * dir_step)
                        if new_val < 0: new_val = 23.5
                        elif new_val >= 24.0: new_val = 0.0
                    elif is_percent_cycle:
                        new_val = round(current_val_float + (0.1 * dir_step), 2)
                        if new_val < 0.0: new_val = 1.0
                        elif new_val > 1.0: new_val = 0.0
                    elif is_int_percent_cycle:
                        work_val = current_val_float * 100 if current_val_float <= 1.0 and current_val_float > 0 and "." in str(setting_obj['value']) else current_val_float
                        new_val = work_val + (10 * dir_step)
                        if new_val < 0: new_val = 100
                        elif new_val > 100: new_val = 0
                    elif is_view_cycle:
                        new_val = current_val_float + (3 * dir_step)
                        if new_val < 3: new_val = 30
                        elif new_val > 30: new_val = 3
                    elif is_max_ent_cycle:
                        new_val = current_val_float + (4 * dir_step)
                        if new_val < 0: new_val = 100
                        elif new_val > 100: new_val = 0
                    elif is_legacy_cycle:
                        steps = [900000.0, 1800000.0, 2700000.0, 3600000.0]
                        try: idx = steps.index(current_val_float)
                        except ValueError: idx = 0
                        idx = (idx + dir_step) % len(steps)
                        new_val = steps[idx]
                    else:
                        new_val = current_val_float

                    if is_view_cycle or is_max_ent_cycle or is_legacy_cycle or is_int_percent_cycle:
                        state['world_data'][block][key]['value'] = int(new_val)
                    else:
                        state['world_data'][block][key]['value'] = float(new_val)

                    if is_max_ent_cycle and block in ['zombie', 'npc', 'animal']:
                        spawn_val = max(1, int(new_val) // 2)
                        if 'spawn' not in state['world_data'][block]:
                             state['world_data'][block]['spawn'] = {'value': spawn_val, 'name': 'spawns'}
                        else:
                             if not isinstance(state['world_data'][block]['spawn'], dict):
                                 state['world_data'][block]['spawn'] = {'value': spawn_val, 'name': 'spawns'}
                             state['world_data'][block]['spawn']['value'] = spawn_val

                    if key == 'static_percent':
                        hostile_val = round(1.0 - new_val, 2)
                        if 'hostile_percent' in state['world_data'][block]:
                            if not isinstance(state['world_data'][block]['hostile_percent'], dict):
                                state['world_data'][block]['hostile_percent'] = {'value': hostile_val, 'name': 'Hostile NPC percentage'}
                            state['world_data'][block]['hostile_percent']['value'] = hostile_val
                    elif key == 'hostile_percent':
                        static_val = round(1.0 - new_val, 2)
                        if 'static_percent' in state['world_data'][block]:
                            if not isinstance(state['world_data'][block]['static_percent'], dict):
                                state['world_data'][block]['static_percent'] = {'value': static_val, 'name': 'Static NPC percentage'}
                            state['world_data'][block]['static_percent']['value'] = static_val

                    _clone_to_custom(state)
                    state['world_unsaved'] = True
                    clicked_input = True
                    break
                    
        if not clicked_input and state.get('world_content_rect') and state['world_content_rect'].collidepoint(mouse_pos):
            state['is_dragging_world_content'] = True
            state['world_content_drag_last_y'] = mouse_pos[1]

    elif event.type == pygame.MOUSEBUTTONUP:
        state['is_dragging_world_scrollbar'] = False
        state['is_dragging_world_content'] = False
        
    elif event.type == pygame.MOUSEMOTION:
        if state.get('is_dragging_world_scrollbar'):
            mouse_delta_y = mouse_pos[1] - state['world_scroll_drag_last_y']
            state['world_scroll_drag_last_y'] = mouse_pos[1]
            track_rect = state.get('world_scrollbar_track')
            handle_rect = state.get('world_scroll_handle')
            max_scroll = state.get('world_max_scroll', 0)
            if track_rect and handle_rect and max_scroll > 0:
                track_height = track_rect.height - handle_rect.height
                if track_height > 0:
                    scroll_amount = mouse_delta_y * (max_scroll / track_height)
                    state['world_scroll_y'] = max(0, min(state.get('world_scroll_y',0) + scroll_amount, max_scroll))
            
        elif state.get('is_dragging_world_content'):
            mouse_delta_y = mouse_pos[1] - state['world_content_drag_last_y']
            state['world_content_drag_last_y'] = mouse_pos[1]
            max_scroll = state.get('world_max_scroll', 0)
            if max_scroll > 0:
                current_scroll = state.get('world_scroll_y', 0)
                state['world_scroll_y'] = max(0, min(current_scroll - mouse_delta_y, max_scroll))