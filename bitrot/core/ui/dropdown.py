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

    max_width = max((font.size(label)[0] for label in main_labels), default=0) + (padding * 4) + 10 # Extra space for arrows
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
            
        text_surf = font.render(label, False, text_color)
        surface.blit(text_surf, (option_rect.x + padding, option_rect.y + (item_height - text_surf.get_height()) // 2))
        
        if has_sub[i]:
            arrow_surf = font.render(">", False, text_color)
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
            
        sub_max_width = max((font.size(label)[0] for label in sub_labels), default=0) + (padding * 2) + 15 # Extra space for *
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
                text_surf = font.render(main_labels[active_sub_idx], False, YELLOW)
                surface.blit(text_surf, (parent_rect.x + padding, parent_rect.y + (item_height - text_surf.get_height()) // 2))
                arrow_surf = font.render(">", False, YELLOW)
                surface.blit(arrow_surf, (parent_rect.right - padding - arrow_surf.get_width(), parent_rect.y + (item_height - arrow_surf.get_height()) // 2))

            # Draw submenu
            sub_s = pygame.Surface((sub_max_width, sub_height), pygame.SRCALPHA)
            sub_s.fill((20, 20, 20, 220))
            surface.blit(sub_s, sub_rect.topleft)
            pygame.draw.rect(surface, WHITE, sub_rect, 1)

            for i, sub_label in enumerate(sub_labels):
                sub_opt_rect = pygame.Rect(sub_x, sub_y + i * item_height, sub_max_width, item_height)
                
                # Check for replacements
                raw_sub_id = sub_options[i]
                replace_name = options[active_sub_idx].get('replacing', {}).get(raw_sub_id)
                sub_tooltip = options[active_sub_idx].get('tooltips', {}).get(raw_sub_id) 

                menu_state['rects'].append(sub_opt_rect)
                action_string = f"{options[active_sub_idx]['label']}::{sub_options[i]}"
                menu_state['action_map'].append(action_string)
                
                text_color = WHITE
                if sub_opt_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(surface, GRAY_80, sub_opt_rect)
                    text_color = YELLOW
                    # If hovering over an occupied slot, prep the tooltip
                    if replace_name:
                        active_tooltip = (f"{tr('msg', 'This item will replace')} {tr('item', replace_name)}", mouse_pos)
                    # Render location tooltip
                    elif sub_tooltip:
                        active_tooltip = (tr('msg', sub_tooltip), mouse_pos)
                    
                text_surf = font.render(sub_label, False, text_color)
                surface.blit(text_surf, (sub_opt_rect.x + padding, sub_opt_rect.y + (item_height - text_surf.get_height()) // 2))
                
                # Draw the little red *
                if replace_name:
                    ast_surf = font.render("*", False, (255, 100, 100)) # Light Red asterisk
                    surface.blit(ast_surf, (sub_opt_rect.right - padding - ast_surf.get_width(), sub_opt_rect.y + (item_height - ast_surf.get_height()) // 2))

    # [NEW] Draw the tooltip globally on top of everything
    if active_tooltip:
        t_text, t_pos = active_tooltip
        t_surf = font.render(t_text, False, WHITE)
        t_rect = t_surf.get_rect()
        t_rect.topleft = (t_pos[0] + 15, t_pos[1] + 15) # Offset below mouse
        
        # Clamp tooltip to screen
        if t_rect.right > GAME_WIDTH:
            t_rect.right = t_pos[0] - 5
        if t_rect.bottom > GAME_HEIGHT:
            t_rect.bottom = t_pos[1] - 5
            
        bg_rect = t_rect.inflate(10, 10)
        
        # Draw background
        s_tooltip = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        s_tooltip.fill((20, 20, 20, 240))
        surface.blit(s_tooltip, bg_rect.topleft)
        pygame.draw.rect(surface, WHITE, bg_rect, 1)
        surface.blit(t_surf, t_rect)