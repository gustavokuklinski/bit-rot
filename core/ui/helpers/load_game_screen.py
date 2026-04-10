import pygame
import os
import shutil
from datetime import datetime
from core.data.config import *
from core.data.localization import tr
from core.ui.modals import draw_scrollbar

def get_save_files():
    save_dir = os.path.join(get_writable_dir(), "game", "save", "game")
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
    path = os.path.join(get_writable_dir(), "game", "save", "game", filename)
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
            return True
    except Exception as e:
        print(f"Error deleting save {path}: {e}")
    return False

def draw_load_game_screen(game, state, mouse_pos):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_offset_x = (GAME_WIDTH - S(1280)) // 2
    center_offset_y = (GAME_HEIGHT - S(720)) // 2
    
    if 'save_list' not in state:
        state['save_list'] = get_save_files()
        state['scroll_y'] = 0
        state['selected_save_index'] = None
    
    game.game_screen.fill(DARK_GRAY)
    
    panel_w = S(600)
    panel_h = S(500)
    panel_x = (GAME_WIDTH - panel_w) // 2
    panel_y = (GAME_HEIGHT - panel_h) // 2
    header_height = S(40)
    border_radius = S(4)
    padding = S(10)

    clickable_rects = {
        'save_items': [], 
        'load_button': None,
        'delete_button': None,
        'back_button': None
    }

    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    header_rect = pygame.Rect(panel_x, panel_y, panel_w, header_height)
    body_rect = pygame.Rect(panel_x, panel_y + header_height, panel_w, panel_h - header_height)

    pygame.draw.rect(game.game_screen, (30, 30, 30), body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, panel_rect, 1, border_radius=border_radius)

    title_surf = font.render(tr('ui', "Load Game"), True, WHITE)
    game.game_screen.blit(title_surf, (header_rect.x + S(15), header_rect.y + S(10)))

    list_rect = pygame.Rect(body_rect.x + padding, body_rect.y + padding, body_rect.width - (padding * 2), body_rect.height - S(70))
    pygame.draw.rect(game.game_screen, (20, 20, 20), list_rect)
    pygame.draw.rect(game.game_screen, GRAY, list_rect, 1)

    item_height = S(35)
    total_content_height = len(state['save_list']) * item_height
    max_scroll = max(0, total_content_height - list_rect.height)
    state['max_scroll'] = max_scroll
    
    state['scroll_y'] = max(0, min(state['scroll_y'], max_scroll))
    
    clip_rect = game.game_screen.get_rect().clip(list_rect)
    if clip_rect.width > 0 and clip_rect.height > 0:
        sub = game.game_screen.subsurface(clip_rect)
        sub.fill((20, 20, 20))
        
        y_offset = -state['scroll_y']
        for i, save in enumerate(state['save_list']):
            row_rect_rel = pygame.Rect(0, y_offset, list_rect.width, item_height)
            row_rect_abs = pygame.Rect(list_rect.x, list_rect.y + y_offset, list_rect.width, item_height)
            
            if row_rect_abs.bottom > list_rect.top and row_rect_abs.top < list_rect.bottom:
                
                is_selected = (state['selected_save_index'] == i)
                is_hovered = row_rect_abs.collidepoint(mouse_pos)
                
                bg_color = (20, 20, 20)
                if is_selected:
                    bg_color = (60, 80, 100) 
                elif is_hovered:
                    bg_color = (40, 40, 40) 
                
                pygame.draw.rect(sub, bg_color, row_rect_rel)
                
                text_color = WHITE if is_selected else GRAY
                name_surf = font.render(save['display_name'], True, text_color)
                sub.blit(name_surf, (S(10), y_offset + S(8)))
                
                clickable_rects['save_items'].append((i, save['filename'], row_rect_abs))
            
            y_offset += item_height

    if max_scroll > 0:
        bar_rect = pygame.Rect(list_rect.right - S(10), list_rect.top, 8, list_rect.height)
        draw_scrollbar(game.game_screen, state, bar_rect, list_rect.height, total_content_height, state['scroll_y'])
        
        clickable_rects['scrollbar_track'] = bar_rect
        clickable_rects['scrollbar_handle'] = state['scrollbar_handle_rect']

    button_area_y = list_rect.bottom + S(10)
    btn_width = S(120)
    btn_height = S(35)
    
    load_btn_rect = pygame.Rect(panel_rect.centerx - btn_width // 2, button_area_y, btn_width, btn_height)
    load_color = GREEN if state['selected_save_index'] is not None else GRAY_60
    pygame.draw.rect(game.game_screen, load_color, load_btn_rect, border_radius=4)
    load_txt = font_14.render(tr('ui', "LOAD GAME"), True, WHITE)
    game.game_screen.blit(load_txt, load_txt.get_rect(center=load_btn_rect.center))
    if state['selected_save_index'] is not None:
        clickable_rects['load_button'] = load_btn_rect

    del_btn_rect = pygame.Rect(panel_rect.x + padding, button_area_y, btn_width - S(20), btn_height)
    if state['selected_save_index'] is not None:
        pygame.draw.rect(game.game_screen, RED, del_btn_rect, border_radius=4)
        del_txt = font.render(tr('ui', "Delete"), True, WHITE)
        game.game_screen.blit(del_txt, del_txt.get_rect(center=del_btn_rect.center))
        clickable_rects['delete_button'] = del_btn_rect
    
    back_btn_rect = pygame.Rect(panel_rect.right - padding - (btn_width - S(20)), button_area_y, btn_width - S(20), btn_height)
    pygame.draw.rect(game.game_screen, GRAY_80, back_btn_rect, border_radius=4)
    back_txt = font.render(tr('ui', "Back"), True, WHITE)
    game.game_screen.blit(back_txt, back_txt.get_rect(center=back_btn_rect.center))
    clickable_rects['back_button'] = back_btn_rect

    return clickable_rects