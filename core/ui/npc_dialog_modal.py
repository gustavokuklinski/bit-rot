import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.data.localization import tr
from core.ui.tabs import Tabs
from core.ui.npc_special_dialogs_tab import draw_special_dialogs_tab

COL_1_WIDTH = 180  
PADDING = 20

def get_wrapped_lines(text, font, max_width):
    words = str(text).split(' ')
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_surf = font.render(' '.join(current_line), True, WHITE)
        if test_surf.get_width() > max_width:
            if len(current_line) > 1: 
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
                
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def get_npc_dialog_option_rect(modal_pos, index, dialogs):
    x, y = modal_pos
    start_x = x + COL_1_WIDTH + PADDING
    start_y = y + 80  # [CHANGED] Shifted downwards to accommodate Tabs
    option_width = NPC_DIALOG_MODAL_WIDTH - COL_1_WIDTH - PADDING - 20
    
    extra_y = 0
    last_node = None
    if dialogs:
        for j in range(index + 1):
            node_id = dialogs[j].get('node_id')
            if node_id != last_node:
                extra_y += 25  
                last_node = node_id
            
            if j < index:
                q_text = f"- {dialogs[j]['q']}"
                lines = get_wrapped_lines(q_text, font, option_width - 20)
                extra_y += max(30, len(lines) * 20 + 10)
                
    current_q_text = f"- {dialogs[index]['q']}"
    current_lines = get_wrapped_lines(current_q_text, font, option_width - 20)
    current_height = max(30, len(current_lines) * 20 + 10)
                
    return pygame.Rect(start_x, start_y + extra_y, option_width, current_height)

def draw_tabs(surface, font, x, y, tabs, active_index, total_width):
    """A standalone tab drawing function for custom column layouts."""
    tab_rects = []
    tab_width = total_width // len(tabs)
    tab_height = 30
    
    for i, tab_name in enumerate(tabs):
        rect = pygame.Rect(x + (i * tab_width), y, tab_width, tab_height)
        
        # Determine tab color
        color = GRAY_60 if i == active_index else DARK_GRAY
        
        # Draw background and border
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        
        # Draw text centered in the tab
        text_surf = font.render(tab_name, True, WHITE)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)
        
        tab_rects.append(rect)
        
    return tab_rects

def draw_npc_dialog_modal(surface, modal, game):
    title_str = f"{tr('modal', 'Talking to:')} {modal['npc'].name}"
    base = BaseModal(surface, modal, game.assets, title_str)
    base.draw_base()
    
    close_button, minimize_button = base.get_buttons()
    if base.minimized: return close_button, minimize_button

    x, y = modal['position']
    width, height = modal['rect'].size
    npc = modal['npc']
    
    # Left Column (Stats/Portrait)
    scale_factor = 10
    if hasattr(npc, 'image') and npc.image:
        portrait_size = (npc.image.get_width() * scale_factor, npc.image.get_height() * scale_factor)
        portrait_surf = pygame.Surface(npc.image.get_size(), pygame.SRCALPHA)
        portrait_surf.blit(npc.image, (0, 0))
        
        if hasattr(npc, 'clothes') and npc.clothes:
            clothes_iter = npc.clothes.values() if isinstance(npc.clothes, dict) else npc.clothes
            for item in clothes_iter:
                if item and hasattr(item, 'image') and item.image:
                    portrait_surf.blit(item.image, (0, 0))
        
        scaled_portrait = pygame.transform.scale(portrait_surf, portrait_size)
        portrait_x = x + (COL_1_WIDTH - portrait_size[0])  
        portrait_y = y + 50
        surface.blit(scaled_portrait, (portrait_x, portrait_y))
        pygame.draw.rect(surface, WHITE, (portrait_x, portrait_y, portrait_size[0], portrait_size[1]), 1)
    
    stats_start_y = y + (23 * scale_factor)
    line_height = 20
    stats_x = x + 20
    
    stats = [
        f"{tr('dialog', 'Name:')} {npc.name}",
        f"{tr('dialog', 'HP:')} {npc.health}/{npc.max_health}",
    ]
    
    for i, stat in enumerate(stats):
        stat_surf = font.render(stat, True, WHITE)
        surface.blit(stat_surf, (stats_x, stats_start_y + (i * line_height)))

    # Right Column (Tabs & Content)
    col2_x = x + COL_1_WIDTH + PADDING
    text_area_width = width - COL_1_WIDTH - PADDING - 20
    
    # --- [NEW] Draw Tabs ---
    active_tab = modal.get('active_tab_index', 0)
    tabs = [tr('dialog', 'Current Dialog'), tr('dialog', 'Special Dialogs')]
    tab_rects = draw_tabs(surface, font, col2_x, y + 40, tabs, active_tab, text_area_width)
    modal['tab_rects'] = tab_rects
    
    content_y = tab_rects[0].bottom + 15
    dialogs = modal.get('dialogs', [])

    if active_tab == 0:
        active_index = modal.get('active_dialog_index', -1)
        
        # [FIX 2] Prevent crash if a new NPC has fewer dialogs than the previous one
        if active_index >= len(dialogs):
            active_index = -1
            modal['active_dialog_index'] = -1
            
        if active_index == -1:
            mouse_pos = pygame.mouse.get_pos()
            last_node = None
            for i, option in enumerate(dialogs):
                rect = get_npc_dialog_option_rect((x, y), i, dialogs)
                node_id = option.get('node_id')
                
                if node_id != last_node:
                    title_map = {
                        'greeting': 'Greeting', 'tips': 'Tips',
                        'lore_branch': 'Lore', 'quest_branch': 'Quest'
                    }
                    raw_title = title_map.get(node_id, node_id.replace('_', ' ').title())
                    title_surf = font.render(tr('dialog', raw_title), True, (170, 170, 170)) 
                    surface.blit(title_surf, (col2_x, rect.y - 22))
                    last_node = node_id
                    
                is_hovered = rect.collidepoint(mouse_pos)
                color = YELLOW if is_hovered else WHITE
                q_text_str = f"- {option['q']}"
                lines = get_wrapped_lines(q_text_str, font, rect.width - 20)
                
                for line_idx, line in enumerate(lines):
                    q_line_surf = font.render(line, True, color)
                    surface.blit(q_line_surf, (rect.x + 10, rect.y + 5 + (line_idx * 20)))
                
        else:
            selected_opt = dialogs[active_index]
            q_text_str = f"{tr('dialog', 'You:')} {selected_opt['q']}"
            q_lines = get_wrapped_lines(q_text_str, font, text_area_width)
            
            for i, line in enumerate(q_lines):
                line_surf = font.render(line, True, GRAY)
                surface.blit(line_surf, (col2_x, content_y + (i * 20)))
            
            a_text_str = f"{npc.name}: {selected_opt['a']}"
            a_lines = get_wrapped_lines(a_text_str, font, text_area_width)
            
            start_text_y = content_y + (len(q_lines) * 20) + 10
            for i, line in enumerate(a_lines):
                line_surf = font.render(line, True, WHITE)
                surface.blit(line_surf, (col2_x, start_text_y + (i * 20)))
                
            back_hint = font.render(tr('dialog', "[Click anywhere to go back]"), True, YELLOW)
            hint_y = max(start_text_y + (len(a_lines) * 20) + 20, y + height - 30)
            surface.blit(back_hint, (col2_x, hint_y))

    elif active_tab == 1:
        draw_special_dialogs_tab(surface, modal, game, col2_x, content_y, text_area_width, height - (content_y - y) - PADDING)

    return close_button, minimize_button