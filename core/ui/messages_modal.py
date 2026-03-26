# core/ui/messages_modal.py
import pygame
from core.data.config import *
from core.ui.modals import BaseModal
# Removed unused Tabs import (optional, but cleaner)

def draw_messages_modal(surface, game, modal, assets):
    base_modal = BaseModal(surface, modal, assets, "Messages (M)")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    # --- REMOVED TABS LOGIC ---
    # The tabs_data list and tabs.draw() have been deleted.

    # Get active log (Hardcoded to 'All' since tabs are gone)
    active_log = game.message_logs.get('All', [])

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
    # CHANGED: Removed the +35 padding that was previously making room for the tabs. 
    # Added +5 for a small natural margin under the header.
    content_y_start = base_modal.modal_y + base_modal.header_h + 5 
    content_height = input_area_y - content_y_start - padding
    content_width = modal['rect'].width - (padding * 2)
    content_rect = pygame.Rect(base_modal.modal_x + padding, content_y_start, content_width, content_height)
    
    modal['content_rect'] = content_rect 

    def wrap_text(text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word]) if current_line else word
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []
        if current_line:
            lines.append(' '.join(current_line))
        return lines

    max_text_width = max(50, content_width - 15)
    wrapped_log = []
    for msg in active_log:
        wrapped_log.extend(wrap_text(msg, font_14, max_text_width))

    # --- Draw Messages (Bottom-Up Alignment) ---
    line_height = font_14.get_height() + 4
    total_text_height = len(wrapped_log) * line_height
    
    # Calculate max scroll (how much we CAN scroll)
    max_scroll = max(0, total_text_height - content_height)
    
    # [NEW] Auto-scroll Logic
    # CHANGED: Hardcoded the key to "All" instead of using modal['active_tab']
    log_len_key = "last_len_All"
    current_len = len(active_log)
    last_len = modal.get(log_len_key, 0)
    
    # If new messages arrived since last frame, snap to bottom
    if current_len > last_len:
        modal['scroll_offset_y'] = max_scroll
        modal[log_len_key] = current_len
    elif log_len_key not in modal:
        # Initialize
        modal[log_len_key] = current_len
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

        # [OPTIMIZED] Virtual Scrolling: Only render what is visible
        start_index = 0
        
        # 1. Skip messages above the view
        if y_pos < 0:
            skip_count = int(abs(y_pos) // line_height)
            start_index = skip_count
            y_pos += skip_count * line_height

        # 2. Iterate only from start_index
        for i in range(start_index, len(wrapped_log)):
            msg = wrapped_log[i]
            
            # 3. Stop rendering if we go below the view
            if y_pos > content_height:
                break
                
            txt_surf = font_14.render(msg, True, WHITE)
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
    
    input_surf = font_14.render(game.chat_input_text, True, WHITE)
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
    
    send_txt = font_14.render("Send", True, WHITE)
    txt_rect = send_txt.get_rect(center=send_btn_rect.center)
    surface.blit(send_txt, txt_rect)

    send_button = {'id': modal['id'], 'type': 'send_msg', 'rect': send_btn_rect}
    input_button = {'id': modal['id'], 'type': 'chat_input', 'rect': input_rect}

    return None, close_button, minimize_button, send_button, input_button