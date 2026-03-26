import os
import re
import pygame
import core.data.config as config_module
from core.data.config import *
from core.data.localization import tr
from core.ui.text_modal import wrap_text

# Global cache to prevent re-parsing the MD every frame and maintain scroll state
HELP_CACHE = {
    'layout': [],
    'total_h': 0,
    'lang': None,
    'box_w': 0,
    'scroll_y': 0.0,
    'is_dragging': False,
    'drag_start_y': 0,
    'drag_start_scroll': 0
}

def draw_loading_screen(surface, is_done, mouse_pos, events=None):
    """
    Draws the loading screen with a manually scrollable Help/Tutorial layout 
    and a progress bar or Start button.
    """
    global HELP_CACHE
    
    surface.fill(DARK_GRAY)
    w, h = surface.get_size()
    center_x, center_y = w // 2, h // 2
    current_time = pygame.time.get_ticks()

    # --- 1. TUTORIAL / HELP BOX DIMENSIONS ---
    box_w = 900
    box_h = int(h * 0.65)
    box_rect = pygame.Rect(0, 0, box_w, box_h)
    box_rect.center = (center_x, center_y - 40)

    # Visual padding so text doesn't touch the top/bottom edges
    padding_y = 20 

    current_lang = getattr(config_module, 'GAME_LANGUAGE', 'en_US')

    # --- 2. MARKDOWN PARSING ENGINE (Cached) ---
    if HELP_CACHE['lang'] != current_lang or HELP_CACHE['box_w'] != box_w:
        layout_elements = [] 
        
        # Point to the new .md files instead of .html
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
            curr_y = 15
            
            for line in md_lines:
                line = line.strip()
                if not line:
                    curr_y += 10
                    continue

                # Rule A: Main Title (# Title) -> Large Font
                if line.startswith("# "):
                    title_txt = line[2:].strip().replace("**", "")
                    title_surf = font_14.render(title_txt, True, WHITE)
                    layout_elements.append({
                        'type': 'text', 
                        'surf': title_surf, 
                        'pos': ((box_w//2) - (title_surf.get_width()//2), curr_y)
                    })
                    curr_y += title_surf.get_height() + 25

                # Rule B: Section Headers (### Header) -> Small Font (Bold)
                elif line.startswith("### "):
                    h3_txt = line[4:].strip().replace("**", "")
                    
                    font_14.set_bold(True)
                    h3_surf = font_14.render(h3_txt, True, WHITE)
                    font_14.set_bold(False)
                    
                    layout_elements.append({'type': 'text', 'surf': h3_surf, 'pos': (15, curr_y)})
                    curr_y += h3_surf.get_height() + 12

                # Rule C: Lists (* or -) -> Handles Bold Keys
                elif line.startswith("* ") or line.startswith("- "):
                    bold_match = re.search(r'^[\*\-]\s+\*\*(.*?)\*\*(.*)', line)
                    if bold_match:
                        # Extract the bolded key and standard description
                        key_txt = "• " + bold_match.group(1).strip()
                        desc_txt = bold_match.group(2).strip()
                        if desc_txt.startswith(":"):
                            desc_txt = desc_txt[1:].strip()
                            
                        # Render bold part natively
                        font_14.set_bold(True)
                        key_surf = font_14.render(key_txt, True, WHITE)
                        font_14.set_bold(False)
                        
                        layout_elements.append({'type': 'text', 'surf': key_surf, 'pos': (30, curr_y)})
                        
                        desc_x = 30 + key_surf.get_width() + 5
                        wrapped = wrap_text(desc_txt, usable_w - desc_x - 15, font_14)
                        
                        temp_y = curr_y
                        for w_line in wrapped:
                            l_surf = font_14.render(w_line, True, WHITE)
                            layout_elements.append({'type': 'text', 'surf': l_surf, 'pos': (desc_x, temp_y)})
                            temp_y += font_14.get_height() + 4
                            
                        curr_y = max(curr_y + font_14.get_height() + 4, temp_y) + 6
                        
                    else:
                        i_txt = "• " + line[2:].strip().replace("**", "")
                        wrapped = wrap_text(i_txt, usable_w - 30, font_14)
                        for w_line in wrapped:
                            l_surf = font_14.render(w_line, True, WHITE)
                            layout_elements.append({'type': 'text', 'surf': l_surf, 'pos': (30, curr_y)})
                            curr_y += font_14.get_height() + 4
                        curr_y += 6

                # Rule E: Images (![alt](path))
                elif line.startswith("![") and "](" in line and line.endswith(")"):
                    # Extract the path from between the parentheses
                    img_path = re.search(r'\((.*?)\)', line)
                    if img_path:
                        clean_path = img_path.group(1).strip()
                        if os.path.exists(clean_path):
                            try:
                                loaded_img = pygame.image.load(clean_path).convert_alpha()
                                
                                # Scale image to be full-width (usable_w) while maintaining aspect ratio
                                img_w, img_h = loaded_img.get_size()
                                scale_factor = usable_w / img_w
                                new_h = int(img_h * scale_factor)
                                scaled_img = pygame.transform.smoothscale(loaded_img, (usable_w, new_h))
                                
                                layout_elements.append({
                                    'type': 'image', 
                                    'surf': scaled_img, 
                                    'pos': (15, curr_y) # 15px padding on the left
                                })
                                curr_y += new_h + 15 # Add margin below image
                            except Exception as e:
                                print(f"[Loading Screen] Error loading image {clean_path}: {e}")
                        else:
                            print(f"[Loading Screen] Image path not found: {clean_path}")

                # Rule D: Normal Paragraph Text
                else:
                    p_txt = line.replace("**", "")
                    wrapped = wrap_text(p_txt, usable_w - 30, font_14)
                    for w_line in wrapped:
                        l_surf = font_14.render(w_line, True, WHITE)
                        layout_elements.append({'type': 'text', 'surf': l_surf, 'pos': (15, curr_y)})
                        curr_y += font_14.get_height() + 4
                    curr_y += 6

            HELP_CACHE['layout'] = layout_elements
            HELP_CACHE['total_h'] = curr_y
            HELP_CACHE['lang'] = current_lang
            HELP_CACHE['box_w'] = box_w
            HELP_CACHE['scroll_y'] = 0.0 
            HELP_CACHE['is_dragging'] = False
            
        except Exception as e:
            print(f"[Loading Screen] Error loading {target_path}: {e}")
            HELP_CACHE['lang'] = current_lang

    # --- 3. DRAW BACKGROUND FOR CONTENT ---
    pygame.draw.rect(surface, (30, 30, 30), box_rect, border_radius=10)
    pygame.draw.rect(surface, (100, 100, 100), box_rect, width=2, border_radius=10)

    # --- 4. MANUAL SCROLL LOGIC ---
    clip_h = box_h - (padding_y * 2)
    max_scroll = max(0, HELP_CACHE['total_h'] - clip_h)
    
    mouse_buttons = pygame.mouse.get_pressed()
    mouse_y = mouse_pos[1]
    
    if events is not None:
        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                HELP_CACHE['scroll_y'] = max(0.0, min(HELP_CACHE['scroll_y'] - (event.y * 35), max_scroll))
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    HELP_CACHE['scroll_y'] = max(0.0, min(HELP_CACHE['scroll_y'] - 35, max_scroll))
                elif event.button == 5:
                    HELP_CACHE['scroll_y'] = max(0.0, min(HELP_CACHE['scroll_y'] + 35, max_scroll))

    track_h = box_h - (padding_y * 2)
    scrollbar_area_rect = pygame.Rect(box_rect.right - 20, box_rect.top + padding_y, 10, track_h)
    
    if max_scroll > 0:
        handle_height = max(40.0, track_h * (track_h / max(1.0, float(HELP_CACHE['total_h']))))
        
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
                elif scrollbar_area_rect.collidepoint(mouse_pos):
                    jump_ratio = (mouse_y - scrollbar_area_rect.top - handle_height/2) / max(1.0, (track_h - handle_height))
                    HELP_CACHE['scroll_y'] = max(0.0, min(jump_ratio * max_scroll, max_scroll))
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

    actual_scroll = int(HELP_CACHE['scroll_y'])

    # --- 5. RENDER CONTENT VIA PADDED SUBSURFACE ---
    clip_rect = pygame.Rect(box_rect.left, box_rect.top + padding_y, box_rect.width, clip_h)
    
    try:
        content_surface = surface.subsurface(clip_rect)
        y_offset = -actual_scroll
        
        for element in HELP_CACHE.get('layout', []):
            if element['type'] in ['text', 'image']:  # <--- CRUCIAL FIX: Allow images to render!
                pos_x, pos_y = element['pos']
                draw_y = pos_y + y_offset
                
                # Render if element is within vertical bounds
                if draw_y + element['surf'].get_height() > 0 and draw_y < clip_h:
                    content_surface.blit(element['surf'], (pos_x, draw_y))
    except ValueError:
        pass 

    # --- 6. BOTTOM SECTION (Progress Bar / Start Button) ---
    if not is_done:
        bar_w = 600
        bar_h = 25
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
        
        if (current_time // 500) % 2 == 0:
            text_color = GREEN
        else:
            text_color = WHITE
            
        pygame.draw.rect(surface, bg_color, btn_rect, border_radius=6)
        
        btn_text = font_14.render(tr('ui', "Click to start"), True, text_color)
        text_rect = btn_text.get_rect(center=btn_rect.center)
        surface.blit(btn_text, text_rect)
        
        return btn_rect