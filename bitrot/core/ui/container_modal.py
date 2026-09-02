import pygame
from core.data.config import *
from core.ui.modals import BaseModal

def get_container_slot_rect(container_pos, i):
    rows, cols = 4, 5
    slot_size = 40
    gap = 6        
    start_x = container_pos[0] + 10
    start_y = container_pos[1] + 40
    row = i // cols
    col = i % cols
    return pygame.Rect(start_x + col * (slot_size + gap), start_y + row * (slot_size + gap), slot_size, slot_size)

def _draw_slots(surface, game, container_item, start_x, start_y, modal_h, header_h, mouse_pos, modal=None):
    rows, cols = 4, 5
    slot_size = 40
    gap = 6
    padding = 10
    
    # Dynamically verify if this specific modal is at the top layer over the mouse cursor
    is_top_hovered = True
    if modal:
        for m in reversed(game.modals):
            if m['rect'].collidepoint(mouse_pos):
                if m.get('id') != modal.get('id'):
                    is_top_hovered = False
                break
                
    # Calculate visible rows dynamically utilizing the new gap calculation
    max_visible_rows = int((modal_h - header_h - padding) / (slot_size + gap))
    max_visible_slots = max_visible_rows * cols

    for i in range(min(container_item.capacity or 0, max_visible_slots)):
        row = i // cols
        col = i % cols
        slot_rect = pygame.Rect(start_x + col * (slot_size + gap), start_y + row * (slot_size + gap), slot_size, slot_size)
        
        # Fill background with GRAY_40 to match inventory slots
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        
        # Default border is GRAY, changes to WHITE when highlighted ONLY if it is the Top Modal
        border_color = GRAY
        if getattr(game, 'is_dragging', False) and slot_rect.collidepoint(mouse_pos) and is_top_hovered:
            border_color = WHITE # Highlight color

        pygame.draw.rect(surface, border_color, slot_rect, 1, 3)

        if i < len(container_item.inventory):
            item = container_item.inventory[i]
            if getattr(item, 'image', None):
                surface.blit(pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8)), slot_rect.move(4, 4))
            elif hasattr(item, 'color'):
                pygame.draw.rect(surface, item.color, slot_rect.inflate(-8, -8))
            
            # --- STRICT DURABILITY BAR LOGIC ---
            if hasattr(item, 'durability') and item.durability is not None and getattr(item, 'max_durability', None) is not None and float(item.max_durability) > 0:
                pct = max(0.0, min(1.0, float(item.durability) / float(item.max_durability)))
                bar_w, bar_h = slot_rect.width - 10, 3
                bar_x, bar_y = slot_rect.x + 5, slot_rect.bottom - 6
                
                col_color = (0, 255, 0) if pct > 0.5 else (255, 255, 0) if pct > 0.2 else (255, 0, 0)
                
                pygame.draw.rect(surface, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h))
                if pct > 0: 
                    pygame.draw.rect(surface, col_color, (bar_x, bar_y, int(bar_w * pct), bar_h))
            # -----------------------------------
            
            # --- Text Overlay Logic (For Ammo & Stacks) ---
            show_count = False
            if hasattr(item, 'is_stackable') and getattr(item, 'is_stackable', lambda: False)() and item.load is not None and item.load > 1:
                show_count = True
            elif getattr(item, 'item_type', '') in ['weapon', 'weapon_ranged'] and getattr(item, 'load', None) is not None:
                show_count = True
            elif hasattr(item, 'load') and item.load is not None and item.load > 1:
                show_count = True
            
            if show_count:
                try:
                    from core.ui.inventory_modal import draw_text_shadow, font_12
                    draw_text_shadow(surface, font_12, str(int(item.load)), WHITE, 
                                   (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')
                except ImportError:
                    from core.data.config import font_12
                    stack_text = font_12.render(str(int(item.load)), False, WHITE)
                    text_rect = stack_text.get_rect(bottomright=(slot_rect.right - 5, slot_rect.bottom - 2))
                    surface.blit(stack_text, text_rect)

def draw_container_content(surface, game, container_item, modal, assets, mouse_pos):
    if not container_item or not hasattr(container_item, 'inventory'):
        return

    padding = 10
    start_x = modal['rect'].x + padding
    start_y = modal['rect'].y + 40
    # Pass 'modal' variable explicitly down the chain
    _draw_slots(surface, game, container_item, start_x, start_y, modal['rect'].height, 40, mouse_pos, modal)

def draw_container_view(surface, game, container_item, modal, assets, mouse_pos):
    if not container_item or not hasattr(container_item, 'inventory'):
        return ()
    
    base_modal = BaseModal(surface, modal, assets, f"{container_item.name} Contents")
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    padding = 10
    start_x = base_modal.modal_x + padding
    start_y = base_modal.modal_y + 40
    
    # Pass 'modal' variable explicitly down the chain
    _draw_slots(surface, game, container_item, start_x, start_y, base_modal.modal_h, base_modal.header_h, mouse_pos, modal)
    
    return close_button