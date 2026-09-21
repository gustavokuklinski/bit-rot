# core/ui/helpers/load_game_screen.py

import pygame
import os
import shutil
from datetime import datetime
import core.data.config as config
from core.data.config import *
from core.data.localization import tr
from core.ui.modals import draw_scrollbar

def get_save_files():
    save_dir = os.path.join(get_writable_dir(), "data.rot", "save", "game")
    if not os.path.exists(save_dir):
        return []
    
    saves = []
    try:
        for name in os.listdir(save_dir):
            if name.startswith("save_") and os.path.isdir(os.path.join(save_dir, name)):
                player_path = os.path.join(save_dir, name, "host.rot")
                world_path = os.path.join(save_dir, name, "world.rot")

                if not os.path.exists(player_path) or not os.path.exists(world_path):
                    continue

                try:
                    timestamp_str = name.replace("save_", "")
                    dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    display_name = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    display_name = name

                saves.append({
                    'filename': name,
                    'display_name': display_name,
                    'path': os.path.join(save_dir, name),
                    'time': os.path.getmtime(os.path.join(save_dir, name))
                })
        
        saves.sort(key=lambda x: x['time'], reverse=True)
    except Exception as e:
        print(f"Error scanning saves: {e}")
        
    return saves

def delete_save(filename):
    path = os.path.join(get_writable_dir(), "data.rot", "save", "game", filename)
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
            return True
    except Exception as e:
        print(f"Error deleting save {path}: {e}")
    return False

def _draw_btn(surface, rect, text, mouse_pos, enabled=True, base_color=(80, 80, 80)):
    is_hovered = rect.collidepoint(mouse_pos)
    
    if not enabled:
        bg_color = (40, 40, 40)
        text_color = (100, 100, 100)
    else:
        bg_color = (min(255, base_color[0] + 30), min(255, base_color[1] + 30), min(255, base_color[2] + 30)) if is_hovered else base_color
        text_color = WHITE

    pygame.draw.rect(surface, bg_color, rect, border_radius=4)
    txt_surf = font_16.render(tr('ui', text), False, text_color)
    txt_rect = txt_surf.get_rect(center=rect.center)
    surface.blit(txt_surf, txt_rect)

def draw_load_game_screen(game, state, mouse_pos):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_x = GAME_WIDTH // 2
    center_y = GAME_HEIGHT // 2

    if 'save_list' not in state:
        state['save_list'] = get_save_files()
        state['scroll_y'] = 0
        state['selected_save_index'] = None

        state['is_scrolling_content'] = False
        state['content_drag_last_y'] = 0
        state['is_dragging_scrollbar'] = False
        state['scrollbar_drag_last_y'] = 0
    
    # 1. Fill Background
    game.game_screen.fill(DARK_GRAY)

    # 2. Main Panel Dimensions matching Preferences & Keybinds
    w = S(900)
    h = S(480)
    bg_rect = pygame.Rect(center_x - w // 2, center_y - h // 2, w, h)
    
    pygame.draw.rect(game.game_screen, (35, 35, 35), bg_rect, border_radius=10)
    pygame.draw.rect(game.game_screen, GRAY_80, bg_rect, width=2, border_radius=10)

    # Header Bar
    header_h = S(50)
    header_rect = pygame.Rect(bg_rect.x, bg_rect.y, bg_rect.width, header_h)
    pygame.draw.rect(game.game_screen, (45, 45, 45), header_rect, border_top_left_radius=10, border_top_right_radius=10)
    pygame.draw.line(game.game_screen, GRAY_80, header_rect.bottomleft, header_rect.bottomright, 2)

    title_surf = font_16.render(tr('ui', "Load Game"), False, WHITE)
    game.game_screen.blit(title_surf, (header_rect.x + S(20), header_rect.centery - title_surf.get_height() // 2))

    # 3. Content List & Scrollbar Area
    padding = S(20)
    scrollbar_w = S(12)
    list_y = header_rect.bottom + padding
    list_h = bg_rect.bottom - list_y - padding

    list_rect = pygame.Rect(bg_rect.x + padding, list_y, bg_rect.width - (padding * 2) - scrollbar_w - S(10), list_h)
    bar_rect = pygame.Rect(list_rect.right + S(10), list_y, scrollbar_w, list_h)

    item_height = S(45)
    total_content_height = len(state['save_list']) * item_height
    max_scroll = max(0, total_content_height - list_rect.height)
    state['max_scroll'] = max_scroll
    state['scroll_y'] = max(0, min(state['scroll_y'], max_scroll))

    clickable_rects = {
        'save_items': [],
        'load_button': None,
        'delete_button': None,
        'back_button': None,
        'list_area': list_rect,
        'scrollbar_track': bar_rect,
        'scrollbar_handle': None
    }

    # Draw Save Entries
    old_clip = game.game_screen.get_clip()
    game.game_screen.set_clip(list_rect)

    y_offset = list_rect.y - state['scroll_y']
    for i, save in enumerate(state['save_list']):
        row_rect = pygame.Rect(list_rect.x, y_offset, list_rect.width, item_height)
        
        if row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
            is_selected = (state['selected_save_index'] == i)
            is_hovered = row_rect.collidepoint(mouse_pos)

            if is_selected:
                row_bg = (55, 75, 95)
            elif is_hovered:
                row_bg = (45, 45, 45)
            else:
                row_bg = (30, 30, 30)

            pygame.draw.rect(game.game_screen, row_bg, row_rect, border_radius=4)
            pygame.draw.line(game.game_screen, (55, 55, 55), (row_rect.left, row_rect.bottom - 1), (row_rect.right, row_rect.bottom - 1), 1)

            text_color = YELLOW if is_selected else (WHITE if is_hovered else (200, 200, 200))
            name_surf = font_16.render(save['display_name'], False, text_color)
            game.game_screen.blit(name_surf, (row_rect.x + S(15), row_rect.centery - name_surf.get_height() // 2))

            clickable_rects['save_items'].append((i, save['filename'], row_rect))

        y_offset += item_height

    game.game_screen.set_clip(old_clip)

    # Draw Scrollbar
    draw_scrollbar(game.game_screen, state, bar_rect, list_rect.height, total_content_height, state['scroll_y'])
    clickable_rects['scrollbar_handle'] = state.get('scrollbar_handle_rect')

    # 4. Standard Bottom Buttons matching Preferences & Keybinds
    btn_w = S(200)
    btn_h = S(45)
    spacing = S(20)

    total_btns_w = (btn_w * 3) + (spacing * 2)
    start_btn_x = center_x - (total_btns_w // 2)
    btn_y = bg_rect.bottom + S(20)

    has_selection = state['selected_save_index'] is not None

    load_btn_rect = pygame.Rect(start_btn_x, btn_y, btn_w, btn_h)
    delete_btn_rect = pygame.Rect(load_btn_rect.right + spacing, btn_y, btn_w, btn_h)
    back_btn_rect = pygame.Rect(delete_btn_rect.right + spacing, btn_y, btn_w, btn_h)

    # Draw Load Button (Teal / Cyan theme like Apply in preferences)
    _draw_btn(game.game_screen, load_btn_rect, "Load", mouse_pos, enabled=has_selection, base_color=(23, 162, 184))
    if has_selection:
        clickable_rects['load_button'] = load_btn_rect

    # Draw Delete Button (Red theme like Reset in preferences/keybinds)
    _draw_btn(game.game_screen, delete_btn_rect, "Delete", mouse_pos, enabled=has_selection, base_color=(200, 50, 50))
    if has_selection:
        clickable_rects['delete_button'] = delete_btn_rect

    # Draw Back Button (Neutral Gray)
    _draw_btn(game.game_screen, back_btn_rect, "Back", mouse_pos, enabled=True, base_color=(80, 80, 80))
    clickable_rects['back_button'] = back_btn_rect

    return clickable_rects