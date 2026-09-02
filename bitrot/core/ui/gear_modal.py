import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.container_modal import _draw_slots
from core.ui.tabs import Tabs
from core.data.localization import tr

def draw_gear_modal(surface, game, player, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, "Gear")
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()
    
    # --- Tabs Logic ---
    # 1. Start with default Gear tab
    tabs_data = [{'label': 'Gear', 'icon': assets.get('gear_icon')}] 
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
    
    return close_button

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
    slot_size = 40 
    gap = 6        
    large_gap = 28 # Space separating the main slots from the Util column
    
    # Calculate total width of the entire block to center it dynamically
    total_width = (slot_size * 4) + (gap * 2) + large_gap
    start_x = modal_x + (modal_width - total_width) / 2
    
    # Column X coordinates
    c1 = start_x
    c2 = c1 + slot_size + gap
    c3 = c2 + slot_size + gap
    c4 = c3 + slot_size + large_gap

    # Row Y coordinates (Keeping your original vertical spacing logic)
    y1 = modal_y + 85
    y2 = y1 + slot_size + gap + 10
    y3 = y2 + slot_size + gap + 10

    rects = {
        # --- ROW 1 ---
        'head': pygame.Rect(c1, y1, slot_size, slot_size),
        'hair': pygame.Rect(c2, y1, slot_size, slot_size),
        'facial': pygame.Rect(c3, y1, slot_size, slot_size),
        'util': pygame.Rect(c4, y1, slot_size, slot_size),
        
        # --- ROW 2 ---
        'hands': pygame.Rect(c1, y2 - 5, slot_size, slot_size),
        'body': pygame.Rect(c2, y2 - 5, slot_size, slot_size),
        'arms': pygame.Rect(c3, y2 - 5, slot_size, slot_size),
        'util2': pygame.Rect(c4, y2 - 5, slot_size, slot_size),
        
        # --- ROW 3 ---
        'legs': pygame.Rect(c1, y3 - 10, slot_size, slot_size),
        'feet': pygame.Rect(c2, y3 - 10, slot_size, slot_size),
        # Column 3 is left empty here to match the 3x3 layout missing the bottom right
        'util3': pygame.Rect(c4, y3 - 10, slot_size, slot_size),
    }

    return rects

# Helper function to draw the content of the 'Gear' tab
def _draw_gear_tab(surface, player, modal, assets, mouse_pos):
    # Pass the actual modal width so calculations are perfectly centered regardless of modal sizes
    modal['gear_slot_rects'] = get_gear_slot_rects(modal['position'], modal['rect'].width)
    
    if not hasattr(player, 'clothes'):
         player.clothes = {} # Safeguard

    for slot_name, slot_rect in modal['gear_slot_rects'].items():
        # Draw empty slot
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

        # Draw label, shifting slightly up into the smaller square 
        label_text = font_14.render(slot_name.capitalize(), False, GRAY)
        label_rect = label_text.get_rect(centerx=slot_rect.centerx, y=slot_rect.top + 13)
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
                
                # --- NEW: Durability Bar ---
                # Safely get the attributes and ensure they are actually numbers, not None
                durability = getattr(item, 'durability', None)
                max_durability = getattr(item, 'max_durability', None)
                
                if durability is not None and max_durability is not None and max_durability > 0:
                    # Your exact standard durability algorithm
                    max_dur = max_durability
                    cur_dur = max(0, durability)
                    pct = cur_dur / max_dur
                    bar_w, bar_h = slot_rect.width - 10, 3
                    bar_x, bar_y = slot_rect.x + 5, slot_rect.bottom - 6
                    
                    col = (0, 255, 0) if pct > 0.5 else (255, 255, 0) if pct > 0.2 else (255, 0, 0)
                    
                    pygame.draw.rect(surface, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h))
                    if pct > 0: 
                        pygame.draw.rect(surface, col, (bar_x, bar_y, int(bar_w * pct), bar_h))
                # ---------------------------
                # ---------------------------
            except Exception as e:
                print(f"Error drawing gear item {tr('item', item.name)}: {e}")