import os
import re
import pygame
import core.data.config as config_module
from core.data.config import *
from core.data.localization import tr
from core.ui.text_modal import wrap_text

# Global cache to prevent re-parsing the MD every frame and maintain scroll state
HELP_CACHE = {
    'tabs': [],          # <-- NEW: Replaces 'layout' with a list of Tabs
    'active_tab': 0,     # <-- NEW: Tracks the currently viewed Tab
    'lang': None,
    'box_w': 0,
    'scroll_y': 0.0,
    'is_dragging': False,
    'drag_start_y': 0,
    'drag_start_scroll': 0
}

def draw_loading_screen(surface, is_done, mouse_pos, events=None):
    global HELP_CACHE
    
    surface.fill(DARK_GRAY)
    w, h = surface.get_size()
    center_x, center_y = w // 2, h // 2
    current_time = pygame.time.get_ticks()

    box_w = 900
    box_h = int(h * 0.65)
    box_rect = pygame.Rect(0, 0, box_w, box_h)
    box_rect.center = (center_x, center_y - 40)
    padding_y = 20 

    current_lang = getattr(config_module, 'GAME_LANGUAGE', 'en_US')

    # --- 1. DYNAMIC TAB PARSING ENGINE ---
    if HELP_CACHE['lang'] != current_lang or HELP_CACHE['box_w'] != box_w:
        tabs = []
        
        # Start with a default "Guide" tab in case there is text/images before the first ###
        current_tab = {'title': 'Home', 'layout': [], 'curr_y': 10, 'total_h': 0}
        tabs.append(current_tab)
        
        if current_lang == "en_US":
            target_path = "./game/lib/data/help/en_US_help.md"
        else:
            target_path = f"./game/lib/lang/{current_lang}_help.md"
            
        if not os.path.exists(target_path):
            target_path = "./game/lib/data/help/en_US_help.md"

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                md_lines = f.readlines()
                
            usable_w = box_w - 40
            
            for line in md_lines:
                line = line.strip()
                if not line:
                    current_tab['curr_y'] += 10
                    continue

                # --- NEW: TAB SEPARATOR (### Header) ---
                if line.startswith("### "):
                    # Clean up the title format (e.g. "### [ COMMANDS ]" -> "COMMANDS")
                    tab_title = line[4:].strip().replace("**", "").replace("[", "").replace("]", "").strip()
                    
                    # If our default 'Guide' tab is empty, just rename it. Otherwise, create a new Tab.
                    if current_tab['curr_y'] <= 15 and not current_tab['layout']:
                        current_tab['title'] = tab_title
                    else:
                        current_tab['total_h'] = current_tab['curr_y'] # Seal the previous tab
                        current_tab = {'title': tab_title, 'layout': [], 'curr_y': 15, 'total_h': 0}
                        tabs.append(current_tab)

                # Rule A: Main Title
                elif line.startswith("# "):
                    title_txt = line[2:].strip().replace("**", "")
                    title_surf = font_14.render(title_txt, True, WHITE)
                    current_tab['layout'].append({
                        'type': 'text', 
                        'surf': title_surf, 
                        'pos': ((box_w//2) - (title_surf.get_width()//2), current_tab['curr_y'])
                    })
                    current_tab['curr_y'] += title_surf.get_height() + 25

                # Rule C: Lists (* or -) 
                elif line.startswith("* ") or line.startswith("- "):
                    bold_match = re.search(r'^[\*\-]\s+\*\*(.*?)\*\*(.*)', line)
                    if bold_match:
                        key_txt = "• " + bold_match.group(1).strip()
                        desc_txt = bold_match.group(2).strip()
                        if desc_txt.startswith(":"): desc_txt = desc_txt[1:].strip()
                            
                        font_14.set_bold(True)
                        key_surf = font_14.render(key_txt, True, WHITE)
                        font_14.set_bold(False)
                        
                        current_tab['layout'].append({'type': 'text', 'surf': key_surf, 'pos': (30, current_tab['curr_y'])})
                        desc_x = 30 + key_surf.get_width() + 5
                        wrapped = wrap_text(desc_txt, usable_w - desc_x - 15, font_14)
                        
                        temp_y = current_tab['curr_y']
                        for w_line in wrapped:
                            l_surf = font_14.render(w_line, True, WHITE)
                            current_tab['layout'].append({'type': 'text', 'surf': l_surf, 'pos': (desc_x, temp_y)})
                            temp_y += font_14.get_height() + 4
                            
                        current_tab['curr_y'] = max(current_tab['curr_y'] + font_14.get_height() + 4, temp_y) + 6
                    else:
                        i_txt = "• " + line[2:].strip().replace("**", "")
                        wrapped = wrap_text(i_txt, usable_w - 30, font_14)
                        for w_line in wrapped:
                            l_surf = font_14.render(w_line, True, WHITE)
                            current_tab['layout'].append({'type': 'text', 'surf': l_surf, 'pos': (30, current_tab['curr_y'])})
                            current_tab['curr_y'] += font_14.get_height() + 4
                        current_tab['curr_y'] += 6

                # Rule E: Images (![alt](path))
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
                                
                                current_tab['layout'].append({'type': 'image', 'surf': scaled_img, 'pos': (15, current_tab['curr_y'])})
                                current_tab['curr_y'] += new_h + 15 
                            except Exception as e:
                                print(f"[Loading Screen] Error loading image {clean_path}: {e}")

                # Rule D: Normal Paragraph Text
                else:
                    p_txt = line.replace("**", "")
                    wrapped = wrap_text(p_txt, usable_w - 30, font_14)
                    for w_line in wrapped:
                        l_surf = font_14.render(w_line, True, WHITE)
                        current_tab['layout'].append({'type': 'text', 'surf': l_surf, 'pos': (15, current_tab['curr_y'])})
                        current_tab['curr_y'] += font_14.get_height() + 4
                    current_tab['curr_y'] += 6

            current_tab['total_h'] = current_tab['curr_y'] # Seal the final tab
            
            HELP_CACHE['tabs'] = tabs
            HELP_CACHE['lang'] = current_lang
            HELP_CACHE['box_w'] = box_w
            HELP_CACHE['scroll_y'] = 0.0 
            HELP_CACHE['is_dragging'] = False
            HELP_CACHE['active_tab'] = 0
            
        except Exception as e:
            print(f"[Loading Screen] Error loading {target_path}: {e}")
            HELP_CACHE['lang'] = current_lang

    # --- 2. DRAW BACKGROUND ---
    pygame.draw.rect(surface, (30, 30, 30), box_rect, border_radius=10)
    pygame.draw.rect(surface, (100, 100, 100), box_rect, width=2, border_radius=10)

    # --- 3. DRAW TABS BUTTONS ---
    tab_h = 35
    tab_y = box_rect.top + padding_y
    mouse_buttons = pygame.mouse.get_pressed()
    
    # Grab the current Tab data
    active_tab_idx = HELP_CACHE.get('active_tab', 0)
    tabs = HELP_CACHE.get('tabs', [])
    active_tab = tabs[active_tab_idx] if tabs else {'layout': [], 'total_h': 0}

    total_tabs = len(tabs)
    if total_tabs > 0:
        current_x = box_rect.left + padding_y
        total_w = box_rect.width - (padding_y * 2)
        tab_rects = []

        # 1. Calculate Rects First
        for i in range(total_tabs):
            tab_width = total_w // total_tabs
            if i < total_w % total_tabs:
                tab_width += 1
                
            tab_rect = pygame.Rect(current_x, tab_y, tab_width, tab_h)
            tab_rects.append(tab_rect)
            current_x += tab_width

        # 2. Draw Inactive Tabs
        for i, tab in enumerate(tabs):
            if i != active_tab_idx:
                tab_rect = tab_rects[i]
                is_hovered = tab_rect.collidepoint(mouse_pos)
                
                if is_hovered and mouse_buttons[0]:
                    HELP_CACHE['active_tab'] = i
                    HELP_CACHE['scroll_y'] = 0.0 # Reset scroll on tab swap!
                    HELP_CACHE['is_dragging'] = False
                    
                pygame.draw.rect(surface, DARK_GRAY, tab_rect)
                pygame.draw.rect(surface, WHITE, tab_rect, 1)
                
                tab_text = font_14.render(tab['title'], True, WHITE)
                text_rect = tab_text.get_rect(center=tab_rect.center)
                surface.blit(tab_text, text_rect)

        # 3. Draw Active Tab (On Top)
        if active_tab_idx < total_tabs:
            tab_rect = tab_rects[active_tab_idx]
            pygame.draw.rect(surface, GRAY_60, tab_rect)
            pygame.draw.rect(surface, WHITE, tab_rect, 1)
            
            tab_text = font_14.render(tabs[active_tab_idx]['title'], True, WHITE)
            text_rect = tab_text.get_rect(center=tab_rect.center)
            surface.blit(tab_text, text_rect)

    # --- 4. SCROLL LOGIC (Only maps to Active Tab Height) ---
    content_y_start = tab_y + tab_h + 10
    clip_h = box_rect.bottom - content_y_start - padding_y
    max_scroll = max(0, active_tab['total_h'] - clip_h)
    
    mouse_y = mouse_pos[1]
    
    if events is not None:
        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                HELP_CACHE['scroll_y'] = max(0.0, min(HELP_CACHE['scroll_y'] - (event.y * 35), max_scroll))

    track_h = clip_h
    scrollbar_area_rect = pygame.Rect(box_rect.right - 20, content_y_start, 10, track_h)
    
    if max_scroll > 0:
        handle_height = max(40.0, track_h * (track_h / max(1.0, float(active_tab['total_h']))))
        
        if mouse_buttons[0]:
            if not HELP_CACHE['is_dragging']:
                handle_pos_ratio = HELP_CACHE['scroll_y'] / max_scroll if max_scroll > 0 else 0
                handle_y = scrollbar_area_rect.top + (track_h - handle_height) * handle_pos_ratio
                scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
                
                hitbox = scrollbar_handle_rect.inflate(20, 0)
                
                if hitbox.collidepoint(mouse_pos):
                    HELP_CACHE['is_dragging'] = True
                    HELP_CACHE['drag_start_y'] = mouse_y
                    HELP_CACHE['drag_start_scroll'] = HELP_CACHE['scroll_y']
        else:
            HELP_CACHE['is_dragging'] = False
            
        if HELP_CACHE['is_dragging']:
            delta_y = mouse_y - HELP_CACHE['drag_start_y']
            track_travel = (track_h - handle_height)
            if track_travel > 0:
                scroll_delta = (delta_y / track_travel) * max_scroll
                HELP_CACHE['scroll_y'] = max(0.0, min(HELP_CACHE['drag_start_scroll'] + scroll_delta, max_scroll))
                
        pygame.draw.rect(surface, (50, 50, 50), scrollbar_area_rect, border_radius=5)
        
        handle_pos_ratio = HELP_CACHE['scroll_y'] / max_scroll if max_scroll > 0 else 0
        handle_y = scrollbar_area_rect.top + (track_h - handle_height) * handle_pos_ratio
        scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        
        handle_color = (180, 180, 180) if HELP_CACHE['is_dragging'] else (120, 120, 120)
        pygame.draw.rect(surface, handle_color, scrollbar_handle_rect, border_radius=5)
    else:
        HELP_CACHE['scroll_y'] = 0.0

    # --- 5. RENDER TAB CONTENT ---
    actual_scroll = int(HELP_CACHE['scroll_y'])
    clip_rect = pygame.Rect(box_rect.left, content_y_start, box_rect.width, clip_h)
    
    try:
        content_surface = surface.subsurface(clip_rect)
        y_offset = -actual_scroll
        
        for element in active_tab.get('layout', []):
            if element['type'] in ['text', 'image']:
                pos_x, pos_y = element['pos']
                draw_y = pos_y + y_offset
                
                if draw_y + element['surf'].get_height() > 0 and draw_y < clip_h:
                    content_surface.blit(element['surf'], (pos_x, draw_y))
    except ValueError:
        pass 

    # --- 6. BOTTOM SECTION (Progress Bar / Start Button) ---
    if not is_done:
        bar_w, bar_h = 600, 25
        bar_bg_rect = pygame.Rect(0, 0, bar_w, bar_h)
        bar_bg_rect.center = (center_x, h - 80)
               
        loading_text = font_14.render(tr('ui', "Loading..."), True, WHITE)
        loading_rect = loading_text.get_rect(center=bar_bg_rect.center)
        surface.blit(loading_text, loading_rect)
        return None
        
    else:
        btn_w, btn_h = 400, 50
        btn_rect = pygame.Rect(0, 0, btn_w, btn_h)
        btn_rect.center = (center_x, h - 80)
        
        is_hovered = btn_rect.collidepoint(mouse_pos)
        bg_color = (80, 80, 80) if is_hovered else (60, 60, 60)
        text_color = WHITE
            
        pygame.draw.rect(surface, bg_color, btn_rect, border_radius=6)
        
        btn_text = font_14.render(tr('ui', "Click to start"), True, text_color)
        text_rect = btn_text.get_rect(center=btn_rect.center)
        surface.blit(btn_text, text_rect)
        
        return btn_rect