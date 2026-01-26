# In core/ui/npc_dialog_modal.py

import pygame
from core.data.config import *
from core.ui.modals import BaseModal

def get_npc_dialog_option_rect(modal_pos, index):
    """Calculates the clickable area for a dialog option."""
    x, y = modal_pos
    start_y = y + 45 
    item_height = 30
    return pygame.Rect(x + 20, start_y + (index * item_height), NPC_DIALOG_MODAL_WIDTH - 40, item_height)

def draw_npc_dialog_modal(surface, modal, game):
    # 1. Draw Base (Header, Background, Title)
    base = BaseModal(surface, modal, game.assets, f"Talking to: {modal['npc'].name}")
    base.draw_base()
    
    # [FIX] Capture buttons to return them
    close_btn, minimize_btn = base.get_buttons()
    buttons = [close_btn, minimize_btn]
    
    if modal.get('minimized', False):
        return buttons

    x, y = modal['position']
    width, height = modal['rect'].size
    npc = modal['npc']
    
    # 2. Draw Content
    active_index = modal.get('active_dialog_index', -1)
    dialogs = modal.get('dialogs', [])

    if active_index == -1:
        # State: Showing Questions
        instruction = font.render("Select a topic:", True, GRAY_80)
        surface.blit(instruction, (x + 20, y + 45))
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, option in enumerate(dialogs):
            rect = get_npc_dialog_option_rect((x, y), i)
            
            # Hover effect
            is_hovered = rect.collidepoint(mouse_pos)
            color = YELLOW if is_hovered else WHITE
            
            # Draw Question
            q_text = font.render(f"- {option['q']}", True, color)
            surface.blit(q_text, (rect.x, rect.y + 5))
            
    else:
        # State: Showing Answer
        selected_opt = dialogs[active_index]
        
        # Draw Question (Dimmed)
        q_text = font.render(f"You: {selected_opt['q']}", True, GRAY)
        surface.blit(q_text, (x + 20, y + 50))
        
        # Draw Answer
        a_text_str = f"{npc.name}: {selected_opt['a']}"
        
        words = a_text_str.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_surf = font.render(' '.join(current_line), True, WHITE)
            if test_surf.get_width() > width - 40:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        
        start_text_y = y + 80
        for i, line in enumerate(lines):
            line_surf = font.render(line, True, WHITE)
            surface.blit(line_surf, (x + 20, start_text_y + (i * 20)))
            
        # Draw "Back" hint
        back_hint = font.render("[Click anywhere to go back]", True, YELLOW)
        surface.blit(back_hint, (x + 20, y + height - 30))

    return buttons