import pygame
from data.config import *
from core.ui.modals import BaseModal

_message_icon = None

def draw_messages_modal(surface, game, modal, assets):
    base_modal = BaseModal(surface, modal, assets, "Messages")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    # Draw messages
    y_offset = base_modal.modal_y + base_modal.header_h + 5
    for msg_text in reversed(game.message_log): # Display newest messages at the top
        text_surface = font_small.render(msg_text, True, WHITE)
        surface.blit(text_surface, (base_modal.modal_x + 5, y_offset))
        y_offset += text_surface.get_height() + 2
        if y_offset > base_modal.modal_y + modal['rect'].height - 5: # Don't draw outside modal
            break

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