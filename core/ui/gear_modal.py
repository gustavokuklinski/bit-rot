import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.container_modal import _draw_slots
from core.ui.tabs import Tabs
from core.data.localization import tr

def draw_gear_modal(surface, game, player, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, "Gear (G)")
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return close_button, minimize_button
    
    # --- Tabs Logic ---
    # 1. Start with default Gear tab
    tabs_data = [{'label': 'Gear', 'icon': None}] 
    container_mapping = {}

    # 2. Add tabs for clothes with capacity (e.g. Vests, Cargo Pants)
    if hasattr(player, 'clothes'):
        for slot, item in player.clothes.items():
            # Check if item exists and acts as a container
            if item and hasattr(item, 'capacity') and item.capacity and item.capacity > 0:
                 if hasattr(item, 'inventory'):
                     default_name = tr('item', item.name)
                     # Handle duplicates (e.g. two items with same name)
                     count = sum(1 for label in container_mapping if label.startswith(default_name))
                     label = f"{default_name} #{count + 1}" if count > 0 else default_name
                     
                     tabs_data.append({
                        'label': label,
                        'icon': item.image if item.image else None
                     })
                     container_mapping[label] = item

    modal['tabs_data'] = tabs_data
    modal['container_mapping'] = container_mapping

    # Ensure active tab is valid (reset to Gear if previous tab disappeared)
    if 'active_tab' not in modal or modal['active_tab'] not in {t['label'] for t in tabs_data}:
        modal['active_tab'] = 'Gear'

    # 3. Draw Tabs
    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw(game, mouse_pos)

    # 4. Draw Content based on active tab
    active_label = modal['active_tab']
    
    # [FIX] Clear gear slots to prevent ghost highlights when on other tabs
    modal['gear_slot_rects'] = {} 

    if active_label == 'Gear':
        _draw_gear_tab(surface, player, modal, assets, mouse_pos)
    elif active_label in container_mapping:
        _draw_container_tab(surface, game, player, modal, mouse_pos, container_mapping[active_label])
    
    return close_button, minimize_button

def _draw_container_tab(surface, game, player, modal, mouse_pos, container_obj):
    """Draws the inventory slots for a specific clothing container."""
    if not container_obj: return
    
    padding = 10
    start_x = modal['rect'].x + padding
    # Offset Y by 80 (Header 35 + Tabs 30 + Padding 15)
    start_y = modal['rect'].y + 80 
    
    _draw_slots(
        surface, 
        game, 
        container_obj, 
        start_x, 
        start_y, 
        modal['rect'].height, 
        80, # Header offset for scrolling/mouse calculation
        mouse_pos
    )

# Helper function to get rects for the 'Gear' tab
def get_gear_slot_rects(modal_position, modal_width=GEAR_MODAL_WIDTH):
    modal_x, modal_y = modal_position
    slot_size = 48
    gap = 8
    
    # FIX: Use the passed modal_width (or GEAR_MODAL_WIDTH default) to calculate center
    modal_center_x = modal_x + (modal_width / 2)

    # [MODIFIED] Content Y start is 80 (Header 35 + Tabs 30 + Padding 15)
    # Was 40, shifted down to accommodate tabs
    y1 = modal_y + 85
    y2 = y1 + slot_size + gap + 20
    y3 = y2 + slot_size + gap + 20

    rects = {
        # [HEAD]
        'head': pygame.Rect(modal_center_x - (slot_size / 2) - gap - slot_size - 5, y1, slot_size, slot_size),
        'hair': pygame.Rect(modal_center_x - (slot_size / 2), y1, slot_size, slot_size),
        'facial': pygame.Rect(modal_center_x + (slot_size / 2) + gap + 5, y1, slot_size, slot_size),
        # [HANDS][body][arms]
        # Adjust X positions relative to the calculated center
        'hands': pygame.Rect(modal_center_x - (slot_size / 2) - gap - slot_size - 5, y2, slot_size, slot_size),
        'body': pygame.Rect(modal_center_x - (slot_size / 2), y2, slot_size, slot_size),
        'arms': pygame.Rect(modal_center_x + (slot_size / 2) + gap + 5, y2, slot_size, slot_size),
        
        # [LEGS][FEET] (PANTS maps to LEGS)
        # These are overwritten below for better centering, but initialized here
        'legs': pygame.Rect(modal_center_x - (slot_size / 2) - gap - slot_size - 5, y3, slot_size, slot_size),
        'feet': pygame.Rect(modal_center_x - (slot_size / 2), y3, slot_size, slot_size),
        'util': pygame.Rect(modal_center_x + (slot_size / 2) + gap + 5, y3, slot_size, slot_size),
    }
    
    # Correcting legs/feet logic to be perfectly centered
    # Total width of 2 slots = 48*2 + 8 = 104
    # Start X = center_x - 104/2 = center_x - 52
    #rects['legs'] = pygame.Rect(modal_center_x - 52, y3, slot_size, slot_size)
    #rects['feet'] = pygame.Rect(modal_center_x + 4, y3, slot_size, slot_size) # -52 + 48 + 8 = +4


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
                print(f"Error drawing gear item {tr('item', item.name)}: {e}")