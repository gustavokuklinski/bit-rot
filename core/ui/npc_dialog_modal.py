# core/ui/npc_dialog_modal.py
import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.data.localization import tr

COL_1_WIDTH = 180  
PADDING = 20

def get_npc_dialog_option_rect(modal_pos, index):
    x, y = modal_pos
    start_x = x + COL_1_WIDTH + PADDING
    start_y = y + 45 
    item_height = 30
    option_width = NPC_DIALOG_MODAL_WIDTH - COL_1_WIDTH - PADDING - 20
    return pygame.Rect(start_x, start_y + (index * item_height), option_width, item_height)

def draw_npc_dialog_modal(surface, modal, game):
    # Added translation for modal title
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
    
    # Translated Stats
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

    if active_index == -1:
        instruction = font.render("", True, GRAY_80)
        surface.blit(instruction, (col2_x, y + 50))
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, option in enumerate(dialogs):
            rect = get_npc_dialog_option_rect((x, y), i)
            is_hovered = rect.collidepoint(mouse_pos)
            color = YELLOW if is_hovered else WHITE
            q_text = font.render(f"- {option['q']}", True, color)
            surface.blit(q_text, (rect.x, rect.y + 5))
            
    else:
        selected_opt = dialogs[active_index]
        
        # Translated Question Label
        q_text = font.render(f"{tr('dialog', 'You:')} {selected_opt['q']}", True, GRAY)
        surface.blit(q_text, (col2_x, y + 50))
        
        a_text_str = f"{npc.name}: {selected_opt['a']}"
        words = a_text_str.split(' ')
        lines = []
        current_line = []
        text_area_width = width - COL_1_WIDTH - PADDING - 20
        
        for word in words:
            current_line.append(word)
            test_surf = font.render(' '.join(current_line), True, WHITE)
            if test_surf.get_width() > text_area_width:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        
        start_text_y = y + 80
        for i, line in enumerate(lines):
            line_surf = font.render(line, True, WHITE)
            surface.blit(line_surf, (col2_x, start_text_y + (i * 20)))
            
        # Translated Back Hint
        back_hint = font.render(tr('dialog', "[Click anywhere to go back]"), True, YELLOW)
        hint_y = max(start_text_y + (len(lines) * 20) + 20, y + height - 30)
        surface.blit(back_hint, (col2_x, hint_y))

    return close_button, minimize_button