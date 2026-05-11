import pygame
from core.data.config import *
from core.data.localization import tr
from core.ui.modals import draw_scrollbar


def draw_special_dialogs_tab(surface, modal, game, start_x, start_y, width, height):
    from core.ui.npc_dialog_modal import get_wrapped_lines
    
    special_dialogs = getattr(game.player, 'special_dialogs', [])
    
    if not special_dialogs:
        empty_text = tr('dialog', "No special memories recorded.")
        empty_surf = font.render(empty_text, True, GRAY)
        surface.blit(empty_surf, (start_x, start_y))
        return
        
    # [CHANGED] Use standard scrolling keys for universal mouse hooks
    scroll_y = modal.get('scroll_offset_y', 0)
    
    current_y = 0
    player_name = getattr(game.player, 'name', 'Player')

    drawn_items = []
    # Reverse order to display NEWEST to OLDEST
    for dialog in reversed(special_dialogs):
        stored_npc_name = dialog.get('npc_name', modal['npc'].name)
        
        q_text = f"{player_name}: {dialog['q']}"
        a_text = f"{stored_npc_name}: {dialog['a']}"
        
        q_lines = get_wrapped_lines(q_text, font, width - 20)
        a_lines = get_wrapped_lines(a_text, font, width - 20)
        
        drawn_items.append({
            'q_lines': q_lines,
            'a_lines': a_lines,
            'y': current_y
        })
        current_y += (len(q_lines) * 20) + (len(a_lines) * 20) + 15
        
    total_height = current_y
    max_scroll = max(0, total_height - height)
    
    # Clamp scroll ranges
    if scroll_y > max_scroll: scroll_y = max_scroll
    if scroll_y < 0: scroll_y = 0
    modal['scroll_offset_y'] = scroll_y
    modal['max_scroll_offset'] = max_scroll
    
    # Set content rect required for standard drag calculation
    modal['content_rect'] = pygame.Rect(start_x, start_y, width, height)
    
    # Draw to a dynamic sub-surface
    content_surf = pygame.Surface((width, max(total_height, height)), pygame.SRCALPHA)
    
    for item in drawn_items:
        item_y = item['y']
        for line in item['q_lines']:
            line_surf = font.render(line, True, YELLOW)
            content_surf.blit(line_surf, (0, item_y))
            item_y += 20
            
        for line in item['a_lines']:
            line_surf = font.render(line, True, WHITE)
            content_surf.blit(line_surf, (0, item_y))
            item_y += 20
            
    # Blit the actively visible scrolling window
    surface.blit(content_surf, (start_x, start_y), (0, scroll_y, width, height))
    
    # Draw Scrollbar
    bar_rect = pygame.Rect(start_x + width - 10, start_y, 8, height)
    draw_scrollbar(surface, modal, bar_rect, height, total_height, scroll_y)