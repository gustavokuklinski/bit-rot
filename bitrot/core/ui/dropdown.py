# core/ui/dropdown.py
import pygame
from core.data.config import *
from core.data.localization import tr

def draw_context_menu(surface, menu_state, mouse_pos):
    if not menu_state['active']:
        return
    options = menu_state['options']
    if not options:
        menu_state['active'] = False
        return

    item_height = 30
    padding = 5
    
    # Pre-calculate main menu metrics
    main_labels = []
    has_sub = []
    for opt in options:
        if isinstance(opt, dict):
            main_labels.append(tr('context', opt['label']))
            has_sub.append(True)
        else:
            main_labels.append(tr('context', opt))
            has_sub.append(False)

    max_width = max((font_12.size(label)[0] for label in main_labels), default=0) + (padding * 4) + 10 # Extra space for arrows
    menu_height = len(options) * item_height
    menu_x, menu_y = menu_state['position']
    
    if menu_x + max_width > GAME_WIDTH:
        menu_x -= max_width
    if menu_y + menu_height > GAME_HEIGHT:
        menu_y -= menu_height
        
    menu_rect = pygame.Rect(menu_x, menu_y, max_width, menu_height)
    
    # Draw main menu background
    s = pygame.Surface((max_width, menu_height), pygame.SRCALPHA)
    s.fill((20, 20, 20, 220))
    surface.blit(s, menu_rect.topleft)
    pygame.draw.rect(surface, WHITE, menu_rect, 1)
    
    menu_state['rects'] = []
    menu_state['action_map'] = [] # Maps drawn rect index to the actual string action
    
    hovered_main_index = -1
    active_tooltip = None  # [NEW] Global tooltip tracker
    
    # Draw main items
    for i, label in enumerate(main_labels):
        option_rect = pygame.Rect(menu_x, menu_y + i * item_height, max_width, item_height)
        
        is_hovered = option_rect.collidepoint(mouse_pos)
        
        # If hovering a submenu parent or its child, keep it highlighted
        if is_hovered:
            hovered_main_index = i
            
            # [NEW] Check for main menu tooltips (like "Barricate")
            if not has_sub[i] and isinstance(options[i], str):
                main_tooltip = menu_state.get('tooltips', {}).get(options[i])
                if main_tooltip:
                    active_tooltip = (tr('msg', main_tooltip), mouse_pos)
            
        text_color = WHITE
        if is_hovered:
            pygame.draw.rect(surface, GRAY_80, option_rect)
            text_color = YELLOW
            
        text_surf = font_12.render(label, False, text_color)
        surface.blit(text_surf, (option_rect.x + padding, option_rect.y + (item_height - text_surf.get_height()) // 2))
        
        if has_sub[i]:
            arrow_surf = font_12.render(">", False, text_color)
            surface.blit(arrow_surf, (option_rect.right - padding - arrow_surf.get_width(), option_rect.y + (item_height - arrow_surf.get_height()) // 2))
            
        if not has_sub[i]:
            menu_state['rects'].append(option_rect)
            menu_state['action_map'].append(options[i])
            
    # Handle Submenu drawing
    active_sub_idx = -1
    
    if 'last_hovered_sub' not in menu_state:
        menu_state['last_hovered_sub'] = -1

    if menu_state['last_hovered_sub'] >= len(has_sub):
        menu_state['last_hovered_sub'] = -1

    if hovered_main_index != -1 and has_sub[hovered_main_index]:
        active_sub_idx = hovered_main_index
        menu_state['last_hovered_sub'] = active_sub_idx
    elif menu_state['last_hovered_sub'] != -1 and has_sub[menu_state['last_hovered_sub']]:
        active_sub_idx = menu_state['last_hovered_sub']

    if active_sub_idx != -1:
        parent_rect = pygame.Rect(menu_x, menu_y + active_sub_idx * item_height, max_width, item_height)
        sub_options = options[active_sub_idx]['sub']
        
        # Extract custom display names if provided, otherwise fallback to the raw ID
        sub_labels = []
        for sub in sub_options:
            disp_name = options[active_sub_idx].get('display_names', {}).get(sub, sub)
            sub_labels.append(tr('context', disp_name))
            
        sub_max_width = max((font_12.size(label)[0] for label in sub_labels), default=0) + (padding * 2) + 15 # Extra space for *
        sub_height = len(sub_options) * item_height
        
        sub_x = menu_x + max_width
        sub_y = menu_y + active_sub_idx * item_height
        
        if sub_x + sub_max_width > GAME_WIDTH:
            sub_x = menu_x - sub_max_width
            
        if sub_y + sub_height > GAME_HEIGHT:
            sub_y = GAME_HEIGHT - sub_height
            
        sub_rect = pygame.Rect(sub_x, sub_y, sub_max_width, sub_height)
        
        # Check if mouse is in submenu or parent
        in_sub = sub_rect.collidepoint(mouse_pos)
        in_parent = parent_rect.collidepoint(mouse_pos)
        
        if not (in_sub or in_parent):
            menu_state['last_hovered_sub'] = -1
        else:
            # Highlight parent if we are in the submenu
            if in_sub:
                pygame.draw.rect(surface, GRAY_80, parent_rect)
                text_surf = font_12.render(main_labels[active_sub_idx], False, YELLOW)
                surface.blit(text_surf, (parent_rect.x + padding, parent_rect.y + (item_height - text_surf.get_height()) // 2))
                arrow_surf = font_12.render(">", False, YELLOW)
                surface.blit(arrow_surf, (parent_rect.right - padding - arrow_surf.get_width(), parent_rect.y + (item_height - arrow_surf.get_height()) // 2))

            # Draw submenu
            sub_s = pygame.Surface((sub_max_width, sub_height), pygame.SRCALPHA)
            sub_s.fill((20, 20, 20, 220))
            surface.blit(sub_s, sub_rect.topleft)
            pygame.draw.rect(surface, WHITE, sub_rect, 1)

            for i, sub_label in enumerate(sub_labels):
                sub_opt_rect = pygame.Rect(sub_x, sub_y + i * item_height, sub_max_width, item_height)
                raw_sub_id = sub_options[i]
                is_header = raw_sub_id.startswith('header_')

                if is_header:
                    hdr_color = options[active_sub_idx].get('colors', {}).get(raw_sub_id, (255, 215, 0))
                    text_surf = font_12.render(sub_label, False, hdr_color)
                    surface.blit(text_surf, (sub_opt_rect.x + padding + 4, sub_opt_rect.y + (item_height - text_surf.get_height()) // 2))
                    continue

                # Regular clickable item (Open Craft and Recipes)
                replace_name = options[active_sub_idx].get('replacing', {}).get(raw_sub_id)
                sub_tooltip = options[active_sub_idx].get('tooltips', {}).get(raw_sub_id) 

                menu_state['rects'].append(sub_opt_rect)
                action_string = f"{options[active_sub_idx]['label']}::{raw_sub_id}"
                menu_state['action_map'].append(action_string)
                
                base_color = options[active_sub_idx].get('colors', {}).get(raw_sub_id, WHITE)
                text_color = base_color

                if sub_opt_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(surface, GRAY_80, sub_opt_rect)
                    text_color = YELLOW if base_color == WHITE else (220, 220, 160)

                    if replace_name:
                        active_tooltip = (f"{tr('msg', 'This item will replace')} {tr('item', replace_name)}", sub_opt_rect, sub_rect)
                    elif sub_tooltip:
                        active_tooltip = (sub_tooltip, sub_opt_rect, sub_rect)
                    
                text_surf = font_12.render(sub_label, False, text_color)
                surface.blit(text_surf, (sub_opt_rect.x + padding + 6, sub_opt_rect.y + (item_height - text_surf.get_height()) // 2))
                
                if replace_name:
                    ast_surf = font_12.render("*", False, (255, 100, 100))
                    surface.blit(ast_surf, (sub_opt_rect.right - padding - ast_surf.get_width(), sub_opt_rect.y + (item_height - ast_surf.get_height()) // 2))

    # --- Tooltip Rendering Anchored to the Side of the Submenu ---
    if active_tooltip:
        if len(active_tooltip) == 3:
            t_text, opt_rect, parent_rect = active_tooltip
            t_pos = None
        else:
            t_text, t_pos = active_tooltip
            opt_rect, parent_rect = None, None

        lines = t_text.split('\n')
        line_height = font_12.get_height() + 4
        tt_padding = 8

        max_w = max((font_12.size(line)[0] for line in lines), default=0)
        tt_w = max_w + (tt_padding * 2)
        tt_h = (len(lines) * line_height) + (tt_padding * 2)

        if parent_rect and opt_rect:
            # Place to the right of the submenu
            tt_x = parent_rect.right + 5
            if tt_x + tt_w > GAME_WIDTH:
                # Flip to the left of the submenu if offscreen
                tt_x = parent_rect.left - tt_w - 5
            tt_x = max(5, min(tt_x, GAME_WIDTH - tt_w - 5))

            # Align vertically with the hovered option
            tt_y = opt_rect.top
            if tt_y + tt_h > GAME_HEIGHT:
                tt_y = max(5, GAME_HEIGHT - tt_h - 5)
            tt_y = max(5, tt_y)
        else:
            tt_x = max(5, min(t_pos[0] + 15, GAME_WIDTH - tt_w - 5))
            tt_y = max(5, min(t_pos[1] + 15, GAME_HEIGHT - tt_h - 5))

        tt_rect = pygame.Rect(tt_x, tt_y, tt_w, tt_h)
        s_tooltip = pygame.Surface((tt_w, tt_h), pygame.SRCALPHA)
        s_tooltip.fill((20, 20, 20, 245))
        surface.blit(s_tooltip, tt_rect.topleft)
        pygame.draw.rect(surface, WHITE, tt_rect, 1)

        for line_idx, line in enumerate(lines):
            if not line:
                continue

            line_color = WHITE
            if "Type:" in line:
                line_color = (180, 180, 180)       # Sub-header style (soft gray)
            elif "Missing" in line or "Ingredients:" in line or "Requires" in line:
                line_color = (255, 130, 130)       # Section headers (soft red)
            elif line.startswith("- "):
                line_color = (220, 220, 220)       # List items (light gray)
            elif "Ready" in line:
                line_color = (130, 255, 130)       # Success status (soft green)
            elif "inventory or nearby" in line:
                line_color = (255, 215, 0)         # Crafting reminder note (gold)

            line_surf = font_12.render(line, False, line_color)
            surface.blit(line_surf, (tt_x + tt_padding, tt_y + tt_padding + (line_idx * line_height)))
    