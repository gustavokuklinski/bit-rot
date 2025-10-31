import pygame
from data.config import *
from core.ui.modals import BaseModal

def get_container_slot_rect(container_pos, i):
    rows, cols = 4, 5
    slot_size = 48
    padding = 10
    start_x = container_pos[0] + padding
    start_y = container_pos[1] + 40
    row = i // cols
    col = i % cols
    return pygame.Rect(start_x + col * (slot_size + padding), start_y + row * (slot_size + padding), slot_size, slot_size)

def _draw_slots(surface, game, container_item, start_x, start_y, modal_h, header_h):
    rows, cols = 4, 5
    slot_size = 48
    padding = 10
    max_visible_rows = int((modal_h - header_h - padding) / (slot_size + padding))
    max_visible_slots = max_visible_rows * cols
    mouse_pos = pygame.mouse.get_pos()

    for i in range(min(container_item.capacity or 0, max_visible_slots)):
        row = i // cols
        col = i % cols
        slot_rect = pygame.Rect(start_x + col * (slot_size + padding), start_y + row * (slot_size + padding), slot_size, slot_size)
        
        border_color = GRAY_40
        if game.is_dragging and slot_rect.collidepoint(mouse_pos):
            border_color = WHITE # Highlight color

        pygame.draw.rect(surface, border_color, slot_rect, 1, 3)

        if i < len(container_item.inventory):
            item = container_item.inventory[i]
            if item.image:
                surface.blit(pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8)), slot_rect.move(4, 4))
            else:
                pygame.draw.rect(surface, item.color, slot_rect.inflate(-8, -8))
            
            if item.is_stackable and item.load is not None and item.load > 1:
                stack_text = font_small.render(str(int(item.load)), True, WHITE)
                text_rect = stack_text.get_rect(bottomright=(slot_rect.right - 5, slot_rect.bottom - 2))
                surface.blit(stack_text, text_rect)

def draw_container_content(surface, game, container_item, modal, assets):
    if not container_item or not hasattr(container_item, 'inventory'):
        return

    padding = 10
    start_x = modal['rect'].x + padding
    start_y = modal['rect'].y + 40
    _draw_slots(surface, game, container_item, start_x, start_y, modal['rect'].height, 40)

def draw_container_view(surface, game, container_item, modal, assets):
    if not container_item or not hasattr(container_item, 'inventory'):
        return
    
    base_modal = BaseModal(surface, modal, assets, f"{container_item.name} Contents")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return close_button, minimize_button

    padding = 10
    start_x = base_modal.modal_x + padding
    start_y = base_modal.modal_y + 40
    _draw_slots(surface, game, container_item, start_x, start_y, base_modal.modal_h, base_modal.header_h)
    return close_button, minimize_button
