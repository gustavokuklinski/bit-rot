import os
import re
import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.text_modal import wrap_text
from core.data.localization import tr

def draw_help_modal(surface, game, modal, assets):
    base_modal = BaseModal(surface, modal, assets, tr('ui', "Help and Tutorial (?)")) # <--- UPDATE THIS
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    # --- Scroll & UI Constants ---
    padding = 15
    content_y_start = base_modal.modal_y + base_modal.header_h + padding
    content_width = modal['rect'].width - (padding * 2) - 15 # -15 for scrollbar
    content_height = modal['rect'].height - base_modal.header_h - (padding * 2)
    content_rect = pygame.Rect(base_modal.modal_x + padding, content_y_start, content_width, content_height)
    modal['content_rect'] = content_rect 

    # --- Miniature Layout Engine (Parses HTML & Builds Grid) ---
    if 'help_layout' not in modal:
        layout_elements = [] # Stores all our pre-calculated rectangles and text surfaces
        total_height = 0
        
        try:
            with open("game/lib/data/help/index.html", "r", encoding="utf-8") as f:
                html = f.read()
                
            usable_w = content_width
            half_w = (usable_w - 20) // 2 # 20 is the gap between the two columns
            curr_y = 0
            
            # 1. Main Title (<h1>)
            title_match = re.search(r'<h1>(.*?)</h1>', html, re.IGNORECASE)
            if title_match:
                title_txt = title_match.group(1).strip()
                title_surf = font_small.render(title_txt, True, WHITE)
                # Center the title
                layout_elements.append({'type': 'text', 'surf': title_surf, 'pos': ((usable_w//2) - (title_surf.get_width()//2), curr_y)})
                curr_y += title_surf.get_height() + 25
                
            # 2. Extract and Process Blocks
            block_matches = re.finditer(r'<div class="block(.*?)">(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
            
            col_index = 0
            row_start_y = curr_y
            max_row_height = 0
            
            for match in block_matches:
                is_full_width = 'full-width' in match.group(1)
                content = match.group(2)
                
                # If we hit a full-width block but we are currently on the right column, push to next row
                if is_full_width and col_index == 1:
                    row_start_y += max_row_height + 20
                    col_index = 0
                    max_row_height = 0
                
                # Calculate Block Dimensions
                block_x = 0 if col_index == 0 or is_full_width else half_w + 20
                block_w = usable_w if is_full_width else half_w
                block_y = row_start_y
                
                inner_y = block_y + 15 # Top padding inside block
                
                # Render Block Title (<h3>)
                h3_match = re.search(r'<h3>(.*?)</h3>', content, re.IGNORECASE)
                if h3_match:
                    h3_txt = h3_match.group(1).strip()
                    # #ffcc00 yellowish color
                    h3_surf = font_small.render(h3_txt, True, (255, 204, 0)) 
                    layout_elements.append({'type': 'text', 'surf': h3_surf, 'pos': (block_x + 15, inner_y)})
                    inner_y += h3_surf.get_height() + 12
                    
                # Render List Items (<li>)
                items = re.finditer(r'<li>(.*?)</li>', content, re.DOTALL | re.IGNORECASE)
                for item in items:
                    raw_text = item.group(1).strip()
                    
                    # Look for <strong> tags to apply our green color
                    strong_match = re.search(r'<strong>(.*?)</strong>(.*)', raw_text, re.IGNORECASE | re.DOTALL)
                    
                    if strong_match:
                        # Extract the key and description separately
                        key_txt = "• " + strong_match.group(1).strip()
                        desc_txt = re.sub(r'<[^>]+>', '', strong_match.group(2)).strip()
                        
                        # Render the bold part in green (#26bd01 -> RGB: 38, 189, 1)
                        key_surf = font_small.render(key_txt, True, (38, 189, 1))
                        layout_elements.append({'type': 'text', 'surf': key_surf, 'pos': (block_x + 15, inner_y)})
                        
                        # Calculate the X position to start the description (right after the green text)
                        desc_x = block_x + 15 + key_surf.get_width() + 5
                        
                        # Wrap the description text so it doesn't overflow the block
                        wrapped = wrap_text(desc_txt, block_w - (desc_x - block_x) - 15, font_small)
                        
                        temp_y = inner_y
                        for line in wrapped:
                            l_surf = font_small.render(line, True, WHITE)
                            layout_elements.append({'type': 'text', 'surf': l_surf, 'pos': (desc_x, temp_y)})
                            temp_y += font_small.get_height() + 4
                            
                        # Advance Y by whichever part was taller
                        inner_y = max(inner_y + font_small.get_height() + 4, temp_y)
                        
                    else:
                        # Fallback for normal list items without <strong>
                        i_txt = "• " + re.sub(r'<[^>]+>', '', raw_text).strip()
                        wrapped = wrap_text(i_txt, block_w - 30, font_small)
                        for line in wrapped:
                            l_surf = font_small.render(line, True, WHITE)
                            layout_elements.append({'type': 'text', 'surf': l_surf, 'pos': (block_x + 15, inner_y)})
                            inner_y += font_small.get_height() + 4
                            
                    inner_y += 6
                    
                # Store the Block Background Rect (rendered before the text)
                block_h = inner_y - block_y + 10
                block_rect = pygame.Rect(block_x, block_y, block_w, block_h)
                
                # We insert the rect at the START of the list so it draws behind the text
                layout_elements.insert(0, {
                    'type': 'rect', 
                    'rect': block_rect, 
                    'bg_color': (42, 42, 42),      # #2a2a2a background
                    'border_color': (68, 68, 68)   # #444 border
                })
                
                # Update Grid Positions
                if is_full_width:
                    row_start_y = block_y + block_h + 20
                    curr_y = row_start_y
                else:
                    max_row_height = max(max_row_height, block_h)
                    col_index += 1
                    if col_index > 1: # Row is full, reset to next row
                        col_index = 0
                        row_start_y += max_row_height + 20
                        curr_y = row_start_y
                        max_row_height = 0
                        
            # Final height calculation for scrollbar
            if col_index == 1: 
                curr_y = row_start_y + max_row_height + 20
                
            modal['help_layout'] = layout_elements
            modal['help_total_h'] = curr_y
                
        except FileNotFoundError:
            # Safe fallback if file is missing
            modal['help_layout'] = []
            modal['help_total_h'] = 0

    # --- Scrolling Math ---
    scroll_offset_y = modal.get('scroll_offset_y', 0)
    max_scroll_offset = max(0, modal.get('help_total_h', 0) - content_height)
    modal['max_scroll_offset'] = max_scroll_offset 
    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll_offset))
    modal['scroll_offset_y'] = scroll_offset_y

    # --- Fast Draw Loop ---
    try:
        content_surface = surface.subsurface(content_rect)
        y_offset = -scroll_offset_y
        
        for element in modal.get('help_layout', []):
            if element['type'] == 'rect':
                r = element['rect']
                # Create a shifted rect for scrolling
                draw_rect = pygame.Rect(r.x, r.y + y_offset, r.width, r.height)
                
                # Only draw if it's visible on screen (performance boost)
                if draw_rect.bottom > 0 and draw_rect.top < content_height:
                    pygame.draw.rect(content_surface, element['bg_color'], draw_rect, border_radius=6)
                    pygame.draw.rect(content_surface, element['border_color'], draw_rect, width=1, border_radius=6)
                    
            elif element['type'] == 'text':
                pos_x, pos_y = element['pos']
                draw_y = pos_y + y_offset
                
                # Only draw text if visible
                if draw_y + element['surf'].get_height() > 0 and draw_y < content_height:
                    content_surface.blit(element['surf'], (pos_x, draw_y))
                    
    except ValueError:
        pass 

    # --- Draw Scrollbar ---
    if max_scroll_offset > 0:
        scrollbar_area_rect = pygame.Rect(content_rect.right + 5, content_rect.top, 8, content_height)
        handle_height = max(20, content_height * (content_height / modal['help_total_h']))
        handle_pos_ratio = scroll_offset_y / max_scroll_offset if max_scroll_offset > 0 else 0
        handle_y = scrollbar_area_rect.top + (content_height - handle_height) * handle_pos_ratio
        
        scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        pygame.draw.rect(surface, GRAY, scrollbar_handle_rect, 0, 4)
        modal['scrollbar_handle_rect'] = scrollbar_handle_rect
    else:
        modal['scrollbar_handle_rect'] = None

    return None, close_button, minimize_button