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

    item_height = 35 
    padding = 10
    
    main_labels = []
    has_sub = []
    for opt in options:
        if isinstance(opt, dict):
            main_labels.append(tr('context', opt['label']))
            has_sub.append(True)
        else:
            main_labels.append(tr('context', opt))
            has_sub.append(False)

    max_width = max((font.size(label)[0] for label in main_labels), default=0) + (padding * 4) + 15 
    menu_height = len(options) * item_height
    menu_x, menu_y = menu_state['position']
    
    if menu_x + max_width > GAME_WIDTH:
        menu_x -= max_width
    if menu_y + menu_height > GAME_HEIGHT:
        menu_y -= menu_height
        
    menu_rect = pygame.Rect(menu_x, menu_y, max_width, menu_height)
    
    s = pygame.Surface((max_width, menu_height), pygame.SRCALPHA)
    s.fill((20, 20, 20, 240))
    surface.blit(s, menu_rect.topleft)
    pygame.draw.rect(surface, WHITE, menu_rect, 1)
    
    menu_state['rects'] = []
    menu_state['action_map'] = [] 
    
    # --- NEW: Retrieve the latest virtual navigation overrides ---
    use_nav = menu_state.get('use_nav', False)
    nav_main = menu_state.get('nav_main_idx', 0)
    nav_sub = menu_state.get('nav_sub_idx', -1)
    
    hovered_main_index = -1
    
    for i, label in enumerate(main_labels):
        option_rect = pygame.Rect(menu_x, menu_y + i * item_height, max_width, item_height)
        
        # Determine highlighting mechanism dynamically 
        is_hovered = False
        if use_nav:
            if nav_main == i:
                is_hovered = True
                if nav_sub == -1:
                    menu_state['nav_target_rect'] = option_rect # Stored target rect for the FIRE button
        else:
            is_hovered = option_rect.collidepoint(mouse_pos)
        
        if is_hovered:
            hovered_main_index = i
            
        text_color = WHITE
        if is_hovered:
            pygame.draw.rect(surface, GRAY_80, option_rect)
            text_color = YELLOW
            
        text_surf = font.render(label, True, text_color)
        surface.blit(text_surf, (option_rect.x + padding, option_rect.y + (item_height - text_surf.get_height()) // 2))
        
        if has_sub[i]:
            arrow_surf = font.render(">", True, text_color)
            surface.blit(arrow_surf, (option_rect.right - padding - arrow_surf.get_width(), option_rect.y + (item_height - arrow_surf.get_height()) // 2))
            
        if not has_sub[i]:
            menu_state['rects'].append(option_rect)
            menu_state['action_map'].append(options[i])
            
    active_sub_idx = -1
    
    if 'last_hovered_sub' not in menu_state:
        menu_state['last_hovered_sub'] = -1

    if menu_state['last_hovered_sub'] >= len(has_sub):
        menu_state['last_hovered_sub'] = -1

    if use_nav:
        if nav_sub != -1 and has_sub[nav_main]:
            active_sub_idx = nav_main
    else:
        if hovered_main_index != -1 and has_sub[hovered_main_index]:
            active_sub_idx = hovered_main_index
            menu_state['last_hovered_sub'] = active_sub_idx
        elif menu_state['last_hovered_sub'] != -1 and has_sub[menu_state['last_hovered_sub']]:
            active_sub_idx = menu_state['last_hovered_sub']

    if active_sub_idx != -1:
        parent_rect = pygame.Rect(menu_x, menu_y + active_sub_idx * item_height, max_width, item_height)
        sub_options = options[active_sub_idx]['sub']
        
        sub_labels = [tr('context', sub) for sub in sub_options]
        sub_max_width = max((font.size(label)[0] for label in sub_labels), default=0) + (padding * 2) + 15 
        sub_height = len(sub_options) * item_height
        
        sub_x = menu_x + max_width
        sub_y = menu_y + active_sub_idx * item_height
        
        if sub_x + sub_max_width > GAME_WIDTH:
            sub_x = menu_x - sub_max_width
            
        if sub_y + sub_height > GAME_HEIGHT:
            sub_y = GAME_HEIGHT - sub_height
            
        sub_rect = pygame.Rect(sub_x, sub_y, sub_max_width, sub_height)
        
        in_sub = False
        in_parent = False
        
        if not use_nav:
            in_sub = sub_rect.collidepoint(mouse_pos)
            in_parent = parent_rect.collidepoint(mouse_pos)
            if not (in_sub or in_parent):
                menu_state['last_hovered_sub'] = -1
        
        if use_nav or in_sub or in_parent:
            if in_sub or (use_nav and nav_sub != -1):
                pygame.draw.rect(surface, GRAY_80, parent_rect)
                text_surf = font.render(main_labels[active_sub_idx], True, YELLOW)
                surface.blit(text_surf, (parent_rect.x + padding, parent_rect.y + (item_height - text_surf.get_height()) // 2))
                arrow_surf = font.render(">", True, YELLOW)
                surface.blit(arrow_surf, (parent_rect.right - padding - arrow_surf.get_width(), parent_rect.y + (item_height - arrow_surf.get_height()) // 2))

            sub_s = pygame.Surface((sub_max_width, sub_height), pygame.SRCALPHA)
            sub_s.fill((20, 20, 20, 240))
            surface.blit(sub_s, sub_rect.topleft)
            pygame.draw.rect(surface, WHITE, sub_rect, 1)
            
            tooltip_info = None

            for i, sub_label in enumerate(sub_labels):
                sub_opt_rect = pygame.Rect(sub_x, sub_y + i * item_height, sub_max_width, item_height)
                
                raw_sub_id = sub_options[i]
                replace_name = options[active_sub_idx].get('replacing', {}).get(raw_sub_id)

                menu_state['rects'].append(sub_opt_rect)
                action_string = f"{options[active_sub_idx]['label']}::{sub_options[i]}"
                menu_state['action_map'].append(action_string)
                
                text_color = WHITE
                is_sub_hovered = False
                
                if use_nav:
                    if nav_main == active_sub_idx and nav_sub == i:
                        is_sub_hovered = True
                        menu_state['nav_target_rect'] = sub_opt_rect
                else:
                    is_sub_hovered = sub_opt_rect.collidepoint(mouse_pos)
                    
                if is_sub_hovered:
                    pygame.draw.rect(surface, GRAY_80, sub_opt_rect)
                    text_color = YELLOW
                    if replace_name:
                        t_pos = sub_opt_rect.center if use_nav else mouse_pos
                        tooltip_info = (f"{tr('msg', 'This item will replace')} {tr('item', replace_name)}", t_pos)
                    
                text_surf = font.render(sub_label, True, text_color)
                surface.blit(text_surf, (sub_opt_rect.x + padding, sub_opt_rect.y + (item_height - text_surf.get_height()) // 2))
                
                if replace_name:
                    ast_surf = font.render("*", True, (255, 100, 100)) 
                    surface.blit(ast_surf, (sub_opt_rect.right - padding - ast_surf.get_width(), sub_opt_rect.y + (item_height - ast_surf.get_height()) // 2))

            if tooltip_info:
                t_text, t_pos = tooltip_info
                t_surf = font.render(t_text, True, WHITE)
                t_rect = t_surf.get_rect()
                t_rect.topleft = (t_pos[0] + 15, t_pos[1] + 15) 
                
                if t_rect.right > GAME_WIDTH:
                    t_rect.right = t_pos[0] - 5
                if t_rect.bottom > GAME_HEIGHT:
                    t_rect.bottom = t_pos[1] - 5
                    
                bg_rect = t_rect.inflate(10, 10)
                
                s_tooltip = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                s_tooltip.fill((20, 20, 20, 240))
                surface.blit(s_tooltip, bg_rect.topleft)
                pygame.draw.rect(surface, WHITE, bg_rect, 1)
                surface.blit(t_surf, t_rect)