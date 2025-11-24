import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.container_modal import _draw_slots

def draw_gear_modal(surface, game, player, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, "Clothes")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return close_button, minimize_button
    
    # Reuse the drawing logic
    _draw_gear_tab(surface, player, modal, assets, mouse_pos)
    
    return close_button, minimize_button

# Helper function to get rects for the 'Gear' tab
def get_gear_slot_rects(modal_position, modal_width=GEAR_MODAL_WIDTH):
    modal_x, modal_y = modal_position
    slot_size = 48
    gap = 8
    
    # FIX: Use the passed modal_width (or GEAR_MODAL_WIDTH default) to calculate center
    modal_center_x = modal_x + (modal_width / 2) 

    # Content Y start is 40 (Header 35 + Padding 5)
    y1 = modal_y + 40
    y2 = y1 + slot_size + gap + 20
    y3 = y2 + slot_size + gap + 20

    rects = {
        # [HEAD]
        'head': pygame.Rect(modal_center_x - (slot_size / 2), y1, slot_size, slot_size),
        
        # [HANDS][TORSO][BODY]
        # Adjust X positions relative to the calculated center
        'hands': pygame.Rect(modal_center_x - (slot_size / 2) - gap - slot_size - 5, y2, slot_size, slot_size),
        'torso': pygame.Rect(modal_center_x - (slot_size / 2), y2, slot_size, slot_size),
        'body': pygame.Rect(modal_center_x + (slot_size / 2) + gap + 5, y2, slot_size, slot_size),
        
        # [LEGS][FEET] (PANTS maps to LEGS)
        # These are overwritten below for better centering, but initialized here
        'legs': pygame.Rect(0, 0, slot_size, slot_size),
        'feet': pygame.Rect(0, 0, slot_size, slot_size)
    }
    
    # Correcting legs/feet logic to be perfectly centered
    # Total width of 2 slots = 48*2 + 8 = 104
    # Start X = center_x - 104/2 = center_x - 52
    rects['legs'] = pygame.Rect(modal_center_x - 52, y3, slot_size, slot_size)
    rects['feet'] = pygame.Rect(modal_center_x + 4, y3, slot_size, slot_size) # -52 + 48 + 8 = +4

    return rects

# Helper function to draw the content of the 'Gear' tab
def _draw_gear_tab(surface, player, modal, assets, mouse_pos):
    # Pass the actual modal width so calculations are correct
    modal['gear_slot_rects'] = get_gear_slot_rects(modal['position'], modal['rect'].width)
    
    if not hasattr(player, 'clothes'):
         player.clothes = {} # Safeguard

    for slot_name, slot_rect in modal['gear_slot_rects'].items():
        # Draw empty slot
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

        # Draw label
        label_text = font_notification.render(slot_name.capitalize(), True, GRAY)
        label_rect = label_text.get_rect(centerx=slot_rect.centerx, y=slot_rect.bottom - 42)
        surface.blit(label_text, label_rect)

        # Get item from player's clothes
        item = player.clothes.get(slot_name) 

        if item:
            try:
                if item.image:
                    thumb = pygame.transform.scale(item.image, (slot_rect.width - 8, slot_rect.height - 8))
                    thumb_rect = thumb.get_rect(center=slot_rect.center)
                    surface.blit(thumb, thumb_rect)
                else:
                    pygame.draw.rect(surface, item.color, slot_rect.inflate(-8, -8))
            except Exception as e:
                print(f"Error drawing gear item {item.name}: {e}")