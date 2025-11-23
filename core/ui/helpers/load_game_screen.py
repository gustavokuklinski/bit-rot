import pygame
import os
import shutil
from datetime import datetime
from core.data.config import *

def get_save_files():
    """Scans the save directory and returns a sorted list of save folders (newest first)."""
    save_dir = os.path.join("game", "save", "game")
    if not os.path.exists(save_dir):
        return []
    
    saves = []
    try:
        for name in os.listdir(save_dir):
            if name.startswith("save_") and os.path.isdir(os.path.join(save_dir, name)):
                # Parse timestamp for display: save_YYYYMMDD_HHMMSS
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
        
        # Sort by modification time, descending
        saves.sort(key=lambda x: x['time'], reverse=True)
    except Exception as e:
        print(f"Error scanning saves: {e}")
        
    return saves

def delete_save(filename):
    """Deletes a specific save folder."""
    path = os.path.join("game", "save", "game", filename)
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
            return True
    except Exception as e:
        print(f"Error deleting save {path}: {e}")
    return False

def draw_load_game_screen(game, state, mouse_pos):
    """Draws the centered Load Game window."""
    
    # Initialize state if needed
    if 'save_list' not in state:
        state['save_list'] = get_save_files()
        state['scroll_y'] = 0
        state['selected_save_index'] = None
    
    game.virtual_screen.fill(DARK_GRAY)
    
    # Layout Constants
    panel_w = 600
    panel_h = 500
    panel_x = (VIRTUAL_SCREEN_WIDTH - panel_w) // 2
    panel_y = (VIRTUAL_GAME_HEIGHT - panel_h) // 2
    header_height = 40
    border_radius = 4
    padding = 10

    clickable_rects = {
        'save_items': [], # List of (index, filename, rect)
        'load_button': None,
        'delete_button': None,
        'back_button': None
    }

    # --- Draw Main Panel ---
    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    header_rect = pygame.Rect(panel_x, panel_y, panel_w, header_height)
    body_rect = pygame.Rect(panel_x, panel_y + header_height, panel_w, panel_h - header_height)

    # Body Background
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    # Header Background
    pygame.draw.rect(game.virtual_screen, GRAY_60, header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    # Border Outline
    pygame.draw.rect(game.virtual_screen, WHITE, panel_rect, 1, border_radius=border_radius)

    # Header Text
    title_surf = font.render("Load Game", True, WHITE)
    game.virtual_screen.blit(title_surf, (header_rect.x + 15, header_rect.y + 10))

    # --- Save List Area ---
    list_rect = pygame.Rect(body_rect.x + padding, body_rect.y + padding, body_rect.width - (padding * 2), body_rect.height - 70)
    pygame.draw.rect(game.virtual_screen, (20, 20, 20), list_rect)
    pygame.draw.rect(game.virtual_screen, GRAY, list_rect, 1)

    # Calculate Scroll
    item_height = 35
    total_content_height = len(state['save_list']) * item_height
    max_scroll = max(0, total_content_height - list_rect.height)
    state['max_scroll'] = max_scroll
    
    # Clamp Scroll
    state['scroll_y'] = max(0, min(state['scroll_y'], max_scroll))
    
    # Clipping Area
    clip_rect = game.virtual_screen.get_rect().clip(list_rect)
    if clip_rect.width > 0 and clip_rect.height > 0:
        sub = game.virtual_screen.subsurface(clip_rect)
        sub.fill((20, 20, 20))
        
        y_offset = -state['scroll_y']
        for i, save in enumerate(state['save_list']):
            # Relative rect for drawing
            row_rect_rel = pygame.Rect(0, y_offset, list_rect.width, item_height)
            # Absolute rect for clicking
            row_rect_abs = pygame.Rect(list_rect.x, list_rect.y + y_offset, list_rect.width, item_height)
            
            # Check visibility
            if row_rect_abs.bottom > list_rect.top and row_rect_abs.top < list_rect.bottom:
                
                # Hover/Select Highlight
                is_selected = (state['selected_save_index'] == i)
                is_hovered = row_rect_abs.collidepoint(mouse_pos)
                
                bg_color = (20, 20, 20)
                if is_selected:
                    bg_color = (60, 80, 100) # Blue-ish for selected
                elif is_hovered:
                    bg_color = (40, 40, 40) # Dark gray for hover
                
                pygame.draw.rect(sub, bg_color, row_rect_rel)
                
                # Text
                text_color = WHITE if is_selected else GRAY
                name_surf = font.render(save['display_name'], True, text_color)
                sub.blit(name_surf, (10, y_offset + 8))
                
                # Add to clickable
                clickable_rects['save_items'].append((i, save['filename'], row_rect_abs))
            
            y_offset += item_height

    if max_scroll > 0:
        scrollbar_bg = pygame.Rect(list_rect.right - 10, list_rect.top, 10, list_rect.height)
        pygame.draw.rect(game.virtual_screen, (40, 40, 40), scrollbar_bg)
        
        clickable_rects['scrollbar_track'] = scrollbar_bg # Store track

        handle_h = max(20, (list_rect.height / total_content_height) * list_rect.height)
        scroll_pct = state['scroll_y'] / max_scroll
        handle_y = list_rect.y + (scroll_pct * (list_rect.height - handle_h))
        
        handle_rect = pygame.Rect(list_rect.right - 10, handle_y, 10, handle_h)
        pygame.draw.rect(game.virtual_screen, GRAY, handle_rect)
        
        clickable_rects['scrollbar_handle'] = handle_rect # Store handle for clicking

    # Buttons
    button_area_y = list_rect.bottom + 10
    btn_width = 120
    btn_height = 35
    
    load_btn_rect = pygame.Rect(panel_rect.centerx - btn_width // 2, button_area_y, btn_width, btn_height)
    load_color = GREEN if state['selected_save_index'] is not None else GRAY_60
    pygame.draw.rect(game.virtual_screen, load_color, load_btn_rect, border_radius=4)
    load_txt = large_font.render("LOAD GAME", True, WHITE)
    game.virtual_screen.blit(load_txt, load_txt.get_rect(center=load_btn_rect.center))
    if state['selected_save_index'] is not None:
        clickable_rects['load_button'] = load_btn_rect

    del_btn_rect = pygame.Rect(panel_rect.x + padding, button_area_y, btn_width - 20, btn_height)
    if state['selected_save_index'] is not None:
        pygame.draw.rect(game.virtual_screen, RED, del_btn_rect, border_radius=4)
        del_txt = font.render("Delete", True, WHITE)
        game.virtual_screen.blit(del_txt, del_txt.get_rect(center=del_btn_rect.center))
        clickable_rects['delete_button'] = del_btn_rect
    
    back_btn_rect = pygame.Rect(panel_rect.right - padding - (btn_width - 20), button_area_y, btn_width - 20, btn_height)
    pygame.draw.rect(game.virtual_screen, GRAY_80, back_btn_rect, border_radius=4)
    back_txt = font.render("Back", True, WHITE)
    game.virtual_screen.blit(back_txt, back_txt.get_rect(center=back_btn_rect.center))
    clickable_rects['back_button'] = back_btn_rect

    return clickable_rects