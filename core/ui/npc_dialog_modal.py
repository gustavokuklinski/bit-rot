import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.data.localization import tr

COL_1_WIDTH = 180  
PADDING = 20

# --- [NEW] Reusable Line Wrapper ---
def get_wrapped_lines(text, font, max_width):
    """Breaks a string into multiple lines to fit within a specific pixel width."""
    words = str(text).split(' ')
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_surf = font.render(' '.join(current_line), True, WHITE)
        if test_surf.get_width() > max_width:
            if len(current_line) > 1: # Avoid infinite loop on giant single words
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
                
    if current_line:
        lines.append(' '.join(current_line))
    return lines


def get_npc_dialog_option_rect(modal_pos, index, dialogs):
    x, y = modal_pos
    start_x = x + COL_1_WIDTH + PADDING
    start_y = y + 45 
    option_width = NPC_DIALOG_MODAL_WIDTH - COL_1_WIDTH - PADDING - 20
    
    extra_y = 0
    last_node = None
    if dialogs:
        for j in range(index + 1):
            node_id = dialogs[j].get('node_id')
            if node_id != last_node:
                extra_y += 25  # Add 25px space for every new title header
                last_node = node_id
            
            # [NEW] Dynamically add height based on how many lines the PREVIOUS items used
            if j < index:
                q_text = f"- {dialogs[j]['q']}"
                lines = get_wrapped_lines(q_text, font, option_width - 20)
                extra_y += max(30, len(lines) * 20 + 10)
                
    # [NEW] Calculate CURRENT item's dynamic height
    current_q_text = f"- {dialogs[index]['q']}"
    current_lines = get_wrapped_lines(current_q_text, font, option_width - 20)
    current_height = max(30, len(current_lines) * 20 + 10)
                
    return pygame.Rect(start_x, start_y + extra_y, option_width, current_height)


def draw_npc_dialog_modal(surface, modal, game):
    title_str = f"{tr('modal', 'Talking to:')} {modal['npc'].name}"
    base = BaseModal(surface, modal, game.assets, title_str)
    base.draw_base()
    
    close_button, minimize_button = base.get_buttons()

    if base.minimized:
        return close_button, minimize_button

    x, y = modal['position']
    width, height = modal['rect'].size
    npc = modal['npc']
    
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

    col2_x = x + COL_1_WIDTH + PADDING
    active_index = modal.get('active_dialog_index', -1)
    dialogs = modal.get('dialogs', [])
    text_area_width = width - COL_1_WIDTH - PADDING - 20

    if active_index == -1:
        instruction = font.render("", True, GRAY_80)
        surface.blit(instruction, (col2_x, y + 50))
        
        mouse_pos = pygame.mouse.get_pos()
        last_node = None
        
        for i, option in enumerate(dialogs):
            rect = get_npc_dialog_option_rect((x, y), i, dialogs)
            node_id = option.get('node_id')
            
            if node_id != last_node:
                title_map = {
                    'greeting': 'Greeting',
                    'tips': 'Tips',
                    'lore_branch': 'Lore',
                    'quest_branch': 'Quest'
                }
                raw_title = title_map.get(node_id, node_id.replace('_', ' ').title())
                title_str = tr('dialog', raw_title)
                
                title_surf = font.render(title_str, True, (170, 170, 170)) 
                surface.blit(title_surf, (col2_x, rect.y - 22))
                last_node = node_id
                
            is_hovered = rect.collidepoint(mouse_pos)
            color = YELLOW if is_hovered else WHITE
            
            # --- [NEW] Draw wrapped text for the clickable options ---
            q_text_str = f"- {option['q']}"
            lines = get_wrapped_lines(q_text_str, font, rect.width - 20)
            
            for line_idx, line in enumerate(lines):
                q_line_surf = font.render(line, True, color)
                surface.blit(q_line_surf, (rect.x + 10, rect.y + 5 + (line_idx * 20)))
            
    else:
        selected_opt = dialogs[active_index]
        
        # --- [NEW] Wrap the player's question in the active view ---
        q_text_str = f"{tr('dialog', 'You:')} {selected_opt['q']}"
        q_lines = get_wrapped_lines(q_text_str, font, text_area_width)
        
        q_start_y = y + 50
        for i, line in enumerate(q_lines):
            line_surf = font.render(line, True, GRAY)
            surface.blit(line_surf, (col2_x, q_start_y + (i * 20)))
        
        # --- [CHANGED] Dynamically push the answer text down ---
        a_text_str = f"{npc.name}: {selected_opt['a']}"
        a_lines = get_wrapped_lines(a_text_str, font, text_area_width)
        
        start_text_y = q_start_y + (len(q_lines) * 20) + 10
        for i, line in enumerate(a_lines):
            line_surf = font.render(line, True, WHITE)
            surface.blit(line_surf, (col2_x, start_text_y + (i * 20)))
            
        back_hint = font.render(tr('dialog', "[Click anywhere to go back]"), True, YELLOW)
        hint_y = max(start_text_y + (len(a_lines) * 20) + 20, y + height - 30)
        surface.blit(back_hint, (col2_x, hint_y))

    return close_button, minimize_button