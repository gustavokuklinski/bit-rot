import os
import re
import pygame
import core.data.config as config_module
from core.data.config import *
from core.ui.modals import BaseModal, draw_scrollbar
from core.ui.text_modal import wrap_text
from core.data.localization import tr

class HelpModalInstance:
    """Lightweight event handler to catch synthetic joystick clicks for Tabs"""
    def __init__(self, modal, game):
        self.modal = modal
        self.game = game
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
            m_pos = self.game._get_scaled_mouse_pos() if hasattr(self.game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
            tab_rects = self.modal.get('tab_rects', [])
            for i, rect in enumerate(tab_rects):
                if rect.collidepoint(m_pos):
                    self.modal['active_help_tab'] = i
                    self.modal['scroll_offset_y'] = 0
                    return True
        return False

def draw_help_modal(surface, game, modal, assets):
    # Ensure event listener is attached to catch synthetic UI events from joystick or mouse.py
    if 'instance' not in modal:
        modal['instance'] = HelpModalInstance(modal, game)

    base_modal = BaseModal(surface, modal, assets, tr('ui', "Help and Tutorial"))
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    # --- Scroll & UI Constants ---
    padding = 15
    content_y_start = base_modal.modal_y + base_modal.header_h + padding
    content_width = modal['rect'].width - (padding * 2) - 15 
    
    # --- Miniature RAW Markdown Engine w/ TABS ---
    current_lang = getattr(config_module, 'GAME_LANGUAGE', 'en_US')
    
    if 'help_tabs' not in modal or modal.get('loaded_help_lang') != current_lang:
        tabs = []
        current_tab = {'title': 'Home', 'layout': [], 'curr_y': 0, 'total_h': 0}
        tabs.append(current_tab)
        
        if current_lang == "en_US":
            target_path = os.path.join(config_module.BASE_DIR, "game", "lib", "data", "help", "en_US_help.md")
        else:
            target_path = os.path.join(config_module.BASE_DIR, "game", "lib", "lang", f"{current_lang}_help.md")
            
        if not os.path.exists(target_path):
            print(f"[Help Modal] Warning: {target_path} not found. Falling back to default EN.")
            target_path = os.path.join(config_module.BASE_DIR, "game", "lib", "data", "help", "en_US_help.md")

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                md_lines = f.readlines()
                
            usable_w = content_width

            for line in md_lines:
                line = line.strip()
                if not line:
                    current_tab['curr_y'] += 10
                    continue
                    
                if line.startswith("### "):
                    tab_title = line[4:].strip().replace("**", "").replace("[", "").replace("]", "").strip()
                    
                    if current_tab['curr_y'] <= 0 and not current_tab['layout']:
                        current_tab['title'] = tab_title
                    else:
                        current_tab['total_h'] = current_tab['curr_y'] 
                        current_tab = {'title': tab_title, 'layout': [], 'curr_y': 0, 'total_h': 0}
                        tabs.append(current_tab)

                elif line.startswith("# "):
                    title_txt = line[2:].strip().replace("**", "")
                    
                    font_14.set_bold(True)
                    title_surf = font_14.render(title_txt, True, WHITE)
                    font_14.set_bold(False)
                    
                    current_tab['layout'].append({
                        'type': 'text', 
                        'surf': title_surf, 
                        'pos': ((usable_w//2) - (title_surf.get_width()//2), current_tab['curr_y']),
                        'bottom_y': current_tab['curr_y'] + title_surf.get_height()
                    })
                    current_tab['curr_y'] += title_surf.get_height() + 25

                elif line.startswith("* ") or line.startswith("- "):
                    bold_match = re.search(r'^[\*\-]\s+\*\*(.*?)\*\*(.*)', line)
                    if bold_match:
                        key_txt = "• " + bold_match.group(1).strip()
                        desc_txt = bold_match.group(2).strip()
                        if desc_txt.startswith(":"):
                            desc_txt = desc_txt[1:].strip()
                            
                        font_14.set_bold(True)
                        key_surf = font_14.render(key_txt, True, WHITE)
                        font_14.set_bold(False)
                        
                        current_tab['layout'].append({
                            'type': 'text', 'surf': key_surf, 'pos': (15, current_tab['curr_y']),
                            'bottom_y': current_tab['curr_y'] + key_surf.get_height()
                        })
                        
                        ALIGN_X = 240 
                        desc_x = 15 + max(ALIGN_X, key_surf.get_width() + 15)
                        
                        wrapped = wrap_text(desc_txt, usable_w - desc_x - 15, font_14)
                        
                        temp_y = current_tab['curr_y']
                        for w_line in wrapped:
                            l_surf = font_14.render(w_line, True, WHITE)
                            current_tab['layout'].append({
                                'type': 'text', 'surf': l_surf, 'pos': (desc_x, temp_y),
                                'bottom_y': temp_y + l_surf.get_height()
                            })
                            temp_y += font_14.get_height() + 4
                            
                        current_tab['curr_y'] = max(current_tab['curr_y'] + font_14.get_height() + 4, temp_y) + 6
                    else:
                        i_txt = "• " + line[2:].strip().replace("**", "")
                        wrapped = wrap_text(i_txt, usable_w - 30, font_14)
                        for w_line in wrapped:
                            l_surf = font_14.render(w_line, True, WHITE)
                            current_tab['layout'].append({
                                'type': 'text', 'surf': l_surf, 'pos': (15, current_tab['curr_y']),
                                'bottom_y': current_tab['curr_y'] + l_surf.get_height()
                            })
                            current_tab['curr_y'] += font_14.get_height() + 4
                    current_tab['curr_y'] += 6

                elif line.startswith("![") and "](" in line and line.endswith(")"):
                    img_path = re.search(r'\((.*?)\)', line)
                    if img_path:
                        clean_path = img_path.group(1).strip()
                        if os.path.exists(clean_path):
                            try:
                                loaded_img = pygame.image.load(clean_path).convert_alpha()
                                img_w, img_h = loaded_img.get_size()
                                scale_factor = usable_w / img_w
                                new_h = int(img_h * scale_factor)
                                scaled_img = pygame.transform.smoothscale(loaded_img, (usable_w, new_h))
                                
                                current_tab['layout'].append({
                                    'type': 'image', 'surf': scaled_img, 'pos': (0, current_tab['curr_y']),
                                    'bottom_y': current_tab['curr_y'] + new_h
                                })
                                current_tab['curr_y'] += new_h + 15
                            except Exception as e:
                                print(f"[Help Modal] Error loading image {clean_path}: {e}")

                else:
                    p_txt = line.replace("**", "")
                    wrapped = wrap_text(p_txt, usable_w - 30, font_14)
                    for w_line in wrapped:
                        l_surf = font_14.render(w_line, True, WHITE)
                        current_tab['layout'].append({
                            'type': 'text', 'surf': l_surf, 'pos': (15, current_tab['curr_y']),
                            'bottom_y': current_tab['curr_y'] + l_surf.get_height()
                        })
                        current_tab['curr_y'] += font_14.get_height() + 4
                    current_tab['curr_y'] += 6

            current_tab['total_h'] = current_tab['curr_y']
            
            modal['help_tabs'] = tabs
            modal['loaded_help_lang'] = current_lang
            modal['active_help_tab'] = 0
                
        except Exception as e:
            print(f"[Help Modal] Error loading {target_path}: {e}")
            modal['help_tabs'] = []
            modal['loaded_help_lang'] = current_lang
            modal['active_help_tab'] = 0

    # --- Draw Tabs Header ---
    tab_h = 30
    tab_y = content_y_start
    
    # ---> FIX 1: Read dynamically scaled screen coordinates for correct UI hover matching
    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    
    # ---> FIX 2: Safely capture the joystick 'Left Trigger' as a native UI click
    is_clicking = pygame.mouse.get_pressed()[0]
    if getattr(game, 'joystick_handler', None):
        if getattr(game.joystick_handler, 'lt_pressed', False):
            is_clicking = True
    
    active_tab_idx = modal.get('active_help_tab', 0)
    tabs = modal.get('help_tabs', [])
    active_tab = tabs[active_tab_idx] if tabs else {'layout': [], 'total_h': 0}

    total_tabs = len(tabs)
    if total_tabs > 0:
        current_x = base_modal.modal_x + padding
        tab_rects = []

        # 1. Calculate Rects First (Dynamic full-width match to tabs.py)
        for i in range(total_tabs):
            tab_width = content_width // total_tabs
            if i < content_width % total_tabs:
                tab_width += 1
                
            tab_rect = pygame.Rect(current_x, tab_y, tab_width, tab_h)
            tab_rects.append(tab_rect)
            current_x += tab_width
            
        # ---> FIX 3: Push the tab rects so Joystick can magnetically snap to them!
        modal['tab_rects'] = tab_rects

        # 2. Draw Inactive Tabs
        for i, tab in enumerate(tabs):
            if i != active_tab_idx:
                tab_rect = tab_rects[i]
                is_hovered = tab_rect.collidepoint(mouse_pos)
                
                if is_hovered and is_clicking:
                    modal['active_help_tab'] = i
                    modal['scroll_offset_y'] = 0 # Reset scroll
                    
                pygame.draw.rect(surface, DARK_GRAY, tab_rect)
                pygame.draw.rect(surface, WHITE, tab_rect, 1) 
                
                tab_text = font_14.render(tab['title'], True, WHITE)
                text_rect = tab_text.get_rect(center=tab_rect.center)
                surface.blit(tab_text, text_rect)

        # 3. Draw Active Tab (Last, so it stays on top)
        if active_tab_idx < total_tabs:
            tab_rect = tab_rects[active_tab_idx]
            pygame.draw.rect(surface, GRAY_60, tab_rect)
            pygame.draw.rect(surface, WHITE, tab_rect, 1)
            
            tab_text = font_14.render(tabs[active_tab_idx]['title'], True, WHITE)
            text_rect = tab_text.get_rect(center=tab_rect.center)
            surface.blit(tab_text, text_rect)

    # --- Setup Content Rect below Tabs ---
    content_y_start += tab_h + 10
    content_height = modal['rect'].height - base_modal.header_h - tab_h - 10 - (padding * 2)
    content_rect = pygame.Rect(base_modal.modal_x + padding, content_y_start, content_width, content_height)
    modal['content_rect'] = content_rect 

    # --- Scrolling Math ---
    scroll_offset_y = modal.get('scroll_offset_y', 0)
    max_scroll_offset = max(0, active_tab['total_h'] - content_height)
    modal['max_scroll_offset'] = max_scroll_offset 
    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll_offset))
    modal['scroll_offset_y'] = scroll_offset_y

    # --- Fast Draw Loop ---
    try:
        content_surface = surface.subsurface(content_rect)
        y_offset = -scroll_offset_y
        
        for element in active_tab.get('layout', []):
            if element['type'] in ['text', 'image']:
                pos_x, pos_y = element['pos']
                draw_y = pos_y + y_offset
                
                if draw_y + element['surf'].get_height() > 0 and draw_y < content_height:
                    content_surface.blit(element['surf'], (pos_x, draw_y))
                    
    except ValueError:
        pass 

    # --- Draw Scrollbar ---
    bar_rect = pygame.Rect(content_rect.right + 5, content_rect.top, 8, content_height)
    draw_scrollbar(surface, modal, bar_rect, content_height, active_tab['total_h'], scroll_offset_y)

    return None, close_button