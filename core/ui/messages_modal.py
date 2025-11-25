# core/ui/messages_modal.py
import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs

def draw_messages_modal(surface, game, modal, assets):
    base_modal = BaseModal(surface, modal, assets, "Messages")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    # --- Tabs ---
    tabs_data = [
        {'label': 'All'},
        {'label': 'Chat'},
        {'label': 'Player'},
        {'label': 'Zombie'}
    ]
    modal['tabs_data'] = tabs_data

    # Ensure active_tab is set
    if 'active_tab' not in modal or modal['active_tab'] not in {t['label'] for t in tabs_data}:
        modal['active_tab'] = 'All'

    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw()

    # Get active log
    active_log = game.message_logs.get(modal['active_tab'], [])

    # --- Layout Constants ---
    padding = 5
    input_height = 30
    send_btn_width = 50
    
    # Input Area Position
    input_area_y = modal['rect'].bottom - input_height - padding
    
    input_rect = pygame.Rect(
        base_modal.modal_x + padding,
        input_area_y,
        modal['rect'].width - (padding * 2) - send_btn_width - 5,
        input_height
    )
    
    send_btn_rect = pygame.Rect(
        input_rect.right + 5,
        input_area_y,
        send_btn_width,
        input_height
    )

    # Content Area Position
    content_y_start = base_modal.modal_y + base_modal.header_h + 35 # +35 for tabs
    content_height = input_area_y - content_y_start - padding
    content_width = modal['rect'].width - (padding * 2)
    content_rect = pygame.Rect(base_modal.modal_x + padding, content_y_start, content_width, content_height)
    
    modal['content_rect'] = content_rect 

    # --- Draw Messages (Bottom-Up Alignment) ---
    line_height = font_notification.get_height() + 4
    total_text_height = len(active_log) * line_height
    
    # Calculate max scroll (how much we CAN scroll)
    max_scroll = max(0, total_text_height - content_height)
    
    # [NEW] Auto-scroll Logic
    # Create a unique key for the last known length of this specific tab
    log_len_key = f"last_len_{modal['active_tab']}"
    current_len = len(active_log)
    last_len = modal.get(log_len_key, 0)
    
    # If new messages arrived since last frame (or tab switch), snap to bottom
    if current_len > last_len:
        modal['scroll_offset_y'] = max_scroll
        modal[log_len_key] = current_len
    elif log_len_key not in modal:
        # Initialize for new tabs
        modal[log_len_key] = current_len
        # Optional: Snap to bottom on first load? Yes, usually better.
        if 'scroll_offset_y' not in modal:
            modal['scroll_offset_y'] = max_scroll

    # Save current length for next frame
    modal[log_len_key] = current_len

    # Initialize scroll if missing
    if 'scroll_offset_y' not in modal:
        modal['scroll_offset_y'] = max_scroll
    
    # Clamp scroll to valid range
    modal['scroll_offset_y'] = max(0, min(modal['scroll_offset_y'], max_scroll))
    
    try:
        content_surface = surface.subsurface(content_rect)
        content_surface.fill((20, 20, 20)) 

        # Calculate Y start position
        if total_text_height < content_height:
            # If text fits, align to bottom
            y_pos = content_height - total_text_height
        else:
            # If text is longer, use scroll offset
            y_pos = -modal['scroll_offset_y']

        for msg in active_log:
            txt_surf = font_notification.render(msg, True, WHITE)
            content_surface.blit(txt_surf, (5, y_pos))
            y_pos += line_height

    except Exception:
        pass 

    # --- Draw Scrollbar ---
    if total_text_height > content_height:
        scrollbar_area_rect = pygame.Rect(content_rect.right - 6, content_rect.top, 6, content_rect.height)
        handle_height_ratio = content_height / total_text_height
        handle_height = max(10, content_rect.height * handle_height_ratio)
        
        if max_scroll > 0:
            scroll_pct = modal['scroll_offset_y'] / max_scroll
        else:
            scroll_pct = 0
            
        handle_y = scrollbar_area_rect.y + (scroll_pct * (scrollbar_area_rect.height - handle_height))
        scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.x, handle_y, 6, handle_height)
        
        pygame.draw.rect(surface, GRAY, scrollbar_handle_rect, border_radius=3)
        modal['scrollbar_handle_rect'] = scrollbar_handle_rect
        modal['max_scroll_offset'] = max_scroll 
    else:
        modal['scrollbar_handle_rect'] = None
        modal['max_scroll_offset'] = 0

    # --- Draw Input Box ---
    border_col = YELLOW if game.chat_active else GRAY
    pygame.draw.rect(surface, (0, 0, 0), input_rect)
    pygame.draw.rect(surface, border_col, input_rect, 1)
    
    input_surf = font_small.render(game.chat_input_text, True, WHITE)
    area_width = input_rect.width - 10
    if input_surf.get_width() > area_width:
        crop_area = pygame.Rect(input_surf.get_width() - area_width, 0, area_width, input_surf.get_height())
        surface.blit(input_surf, (input_rect.x + 5, input_rect.y + 5), crop_area)
    else:
        surface.blit(input_surf, (input_rect.x + 5, input_rect.y + 5))

    # Cursor
    if game.chat_active and (pygame.time.get_ticks() // 500) % 2 == 0:
        cursor_x = input_rect.x + 5 + min(input_surf.get_width(), area_width)
        pygame.draw.line(surface, WHITE, (cursor_x, input_rect.y + 5), (cursor_x, input_rect.bottom - 5))

    # --- Draw Send Button ---
    is_hovered = send_btn_rect.collidepoint(pygame.mouse.get_pos())
    btn_col = GRAY_80 if is_hovered else GRAY_60
    pygame.draw.rect(surface, btn_col, send_btn_rect, border_radius=4)
    pygame.draw.rect(surface, WHITE, send_btn_rect, 1, border_radius=4)
    
    send_txt = font_small.render("Send", True, WHITE)
    txt_rect = send_txt.get_rect(center=send_btn_rect.center)
    surface.blit(send_txt, txt_rect)

    send_button = {'id': modal['id'], 'type': 'send_msg', 'rect': send_btn_rect}
    input_button = {'id': modal['id'], 'type': 'chat_input', 'rect': input_rect}

    return None, close_button, minimize_button, send_button, input_button