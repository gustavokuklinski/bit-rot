import os
import re
import pygame
import core.data.config as config_module  # <-- Explicit module reference
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.text_modal import wrap_text
from core.data.localization import tr

def draw_help_modal(surface, game, modal, assets):
    base_modal = BaseModal(surface, modal, assets, tr('ui', "Help and Tutorial (?)"))
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    # --- Scroll & UI Constants ---
    padding = 15
    content_y_start = base_modal.modal_y + base_modal.header_h + padding
    content_width = modal['rect'].width - (padding * 2) - 15 
    content_height = modal['rect'].height - base_modal.header_h - (padding * 2)
    content_rect = pygame.Rect(base_modal.modal_x + padding, content_y_start, content_width, content_height)
    modal['content_rect'] = content_rect 

    # --- Miniature RAW Markdown Engine ---
    current_lang = getattr(config_module, 'GAME_LANGUAGE', 'en_US')
    
    if 'help_layout' not in modal or modal.get('loaded_help_lang') != current_lang:
        layout_elements = [] 
        
        # 1. Target the .md files
        if current_lang == "en_US":
            target_path = "./game/lib/data/help/en_US_help.md"
        else:
            target_path = f"./game/lib/lang/{current_lang}_help.md"
            
        if not os.path.exists(target_path):
            print(f"[Help Modal] Warning: {target_path} not found. Falling back to default EN.")
            target_path = "./game/lib/data/help/en_US_help.md"

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                md_lines = f.readlines()
                
            usable_w = content_width
            curr_y = 0

            # 2. Parse Markdown Line-by-Line
            for line in md_lines:
                line = line.strip()
                if not line:
                    curr_y += 10
                    continue

                # Rule A: Main Title (# Title)
                if line.startswith("# "):
                    title_txt = line[2:].strip().replace("**", "")
                    
                    font_small.set_bold(True)
                    title_surf = font_small.render(title_txt, True, WHITE)
                    font_small.set_bold(False)
                    
                    layout_elements.append({
                        'type': 'text', 
                        'surf': title_surf, 
                        'pos': ((usable_w//2) - (title_surf.get_width()//2), curr_y),
                        'bottom_y': curr_y + title_surf.get_height()
                    })
                    curr_y += title_surf.get_height() + 25

                # Rule B: Section Headers (### Header)
                elif line.startswith("### "):
                    h3_txt = line[4:].strip().replace("**", "")
                    
                    font_small.set_bold(True)
                    h3_surf = font_small.render(h3_txt, True, WHITE)
                    font_small.set_bold(False)
                    
                    layout_elements.append({
                        'type': 'text', 
                        'surf': h3_surf, 
                        'pos': (15, curr_y),
                        'bottom_y': curr_y + h3_surf.get_height()
                    })
                    curr_y += h3_surf.get_height() + 12

                # Rule C: Lists (* or -)
                elif line.startswith("* ") or line.startswith("- "):
                    bold_match = re.search(r'^[\*\-]\s+\*\*(.*?)\*\*(.*)', line)
                    if bold_match:
                        key_txt = "• " + bold_match.group(1).strip()
                        desc_txt = bold_match.group(2).strip()
                        if desc_txt.startswith(":"):
                            desc_txt = desc_txt[1:].strip()
                            
                        font_small.set_bold(True)
                        key_surf = font_small.render(key_txt, True, WHITE)
                        font_small.set_bold(False)
                        
                        layout_elements.append({
                            'type': 'text', 
                            'surf': key_surf, 
                            'pos': (15, curr_y),
                            'bottom_y': curr_y + key_surf.get_height()
                        })
                        
                        desc_x = 15 + key_surf.get_width() + 5
                        wrapped = wrap_text(desc_txt, usable_w - desc_x - 15, font_small)
                        
                        temp_y = curr_y
                        for w_line in wrapped:
                            l_surf = font_small.render(w_line, True, WHITE)
                            layout_elements.append({
                                'type': 'text', 'surf': l_surf, 'pos': (desc_x, temp_y),
                                'bottom_y': temp_y + l_surf.get_height()
                            })
                            temp_y += font_small.get_height() + 4
                            
                        curr_y = max(curr_y + font_small.get_height() + 4, temp_y) + 6
                        
                    else:
                        i_txt = "• " + line[2:].strip().replace("**", "")
                        wrapped = wrap_text(i_txt, usable_w - 30, font_small)
                        for w_line in wrapped:
                            l_surf = font_small.render(w_line, True, WHITE)
                            layout_elements.append({
                                'type': 'text', 'surf': l_surf, 'pos': (15, curr_y),
                                'bottom_y': curr_y + l_surf.get_height()
                            })
                            curr_y += font_small.get_height() + 4
                            
                    curr_y += 6

                # Rule D: Normal Paragraph Text
                else:
                    p_txt = line.replace("**", "")
                    wrapped = wrap_text(p_txt, usable_w - 30, font_small)
                    for w_line in wrapped:
                        l_surf = font_small.render(w_line, True, WHITE)
                        layout_elements.append({
                            'type': 'text', 'surf': l_surf, 'pos': (15, curr_y),
                            'bottom_y': curr_y + l_surf.get_height()
                        })
                        curr_y += font_small.get_height() + 4
                    curr_y += 6

            modal['help_layout'] = layout_elements
            modal['help_total_h'] = curr_y
            modal['loaded_help_lang'] = current_lang
                
        except Exception as e:
            print(f"[Help Modal] Error loading {target_path}: {e}")
            modal['help_layout'] = []
            modal['help_total_h'] = 0
            modal['loaded_help_lang'] = current_lang

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
            if element['type'] == 'text':
                pos_x, pos_y = element['pos']
                draw_y = pos_y + y_offset
                
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