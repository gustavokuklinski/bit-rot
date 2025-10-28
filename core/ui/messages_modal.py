import pygame
from data.config import *
from core.ui.modals import BaseModal

_message_icon = None

def draw_messages_modal(surface, game, modal, assets):
    base_modal = BaseModal(surface, modal, assets, "Messages")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    # --- Scroll Variables ---
    # Ensure scroll_offset_y exists, default to 0
    scroll_offset_y = modal.get('scroll_offset_y', 0)
    line_height = font_small.get_height() + 2 # Height of one message line + padding
    padding = 5

    # Define the content area (below header)
    content_y_start = base_modal.modal_y + base_modal.header_h + padding
    content_height = modal['rect'].height - base_modal.header_h - (padding * 2)
    content_width = modal['rect'].width - (padding * 2)
    content_rect = pygame.Rect(base_modal.modal_x + padding, content_y_start, content_width, content_height)

    # Store content_rect in modal for input handling
    modal['content_rect'] = content_rect

    if base_modal.minimized:
        # Return minimized buttons, content_rect might still be useful if needed later
        return None, close_button, minimize_button

    # Calculate total height needed for all messages
    total_text_height = len(game.message_log) * line_height

    # Calculate max scroll offset (don't scroll past the last message)
    max_scroll_offset = max(0, total_text_height - content_height)
    # Clamp current offset
    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll_offset))
    modal['scroll_offset_y'] = scroll_offset_y # Update modal state

    # --- Draw messages within a clipping area ---
    # Create a subsurface for the content area to clip rendering
    content_surface = surface.subsurface(content_rect)
    content_surface.fill((20, 20, 20)) # Fill background (adjust color if needed)

    # Draw messages adjusted by scroll offset
    y_pos = 0 - scroll_offset_y # Start drawing from the scrolled position
    for msg_text in reversed(game.message_log): # Newest messages first still works
        text_surface = font_small.render(msg_text, True, WHITE)
        # Calculate draw position *within the content_surface*
        draw_pos_in_subsurface = (0, y_pos) # X is always 0 in the subsurface

        # Blit onto the content_surface (it handles clipping)
        content_surface.blit(text_surface, draw_pos_in_subsurface)

        y_pos += line_height

    # --- (Optional) Draw Scrollbar ---
    if total_text_height > content_height:
        scrollbar_area_height = content_height
        scrollbar_area_rect = pygame.Rect(content_rect.right + 1, content_rect.top, 8, scrollbar_area_height)
        # Draw scrollbar background track (optional)
        # pygame.draw.rect(surface, DARK_GRAY, scrollbar_area_rect)

        # Calculate scrollbar handle size and position
        handle_height_ratio = content_height / total_text_height
        handle_height = max(10, scrollbar_area_height * handle_height_ratio) # Min height 10px

        handle_pos_ratio = scroll_offset_y / max_scroll_offset
        handle_y = scrollbar_area_rect.top + (scrollbar_area_height - handle_height) * handle_pos_ratio

        scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        pygame.draw.rect(surface, GRAY, scrollbar_handle_rect, 0, 2) # Draw the handle

    return None, close_button, minimize_button

def draw_messages_button(surface):
    global _message_icon
    if _message_icon is None:
        try:
            _message_icon = pygame.image.load(SPRITE_PATH + 'ui/messages.png').convert_alpha()
            _message_icon = pygame.transform.scale(_message_icon, (40, 40))
        except pygame.error as e:
            print(f"Warning: Could not load message icon: {e}")
            _message_icon = pygame.Surface((40, 40), pygame.SRCALPHA)
            _message_icon.fill(GRAY)
    
    # Position below nearby button
    button_messages_rect = pygame.Rect(10, 170, 60, 60) # Below nearby (110 + 60 = 170)
    surface.blit(_message_icon, button_messages_rect)
    return button_messages_rect