import pygame
from data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs # Import the Tabs class

# Helper function to draw the content of the 'Inventory' tab
def _draw_inventory_tab(surface, player, modal, assets, mouse_pos, base_modal):
    INVENTORY_SLOTS = 5

    for i in range(INVENTORY_SLOTS):
        slot_rect = get_inventory_slot_rect(i, modal['position'])
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

        item = player.inventory[i] if i < len(player.inventory) else None

        if item:
            try:
                if item.image:
                    thumb = pygame.transform.scale(item.image, (slot_rect.width - 8, slot_rect.height - 8))
                    thumb_rect = thumb.get_rect(center=slot_rect.center)
                    surface.blit(thumb, thumb_rect)
                else:
                    pygame.draw.rect(surface, item.color, slot_rect.inflate(-8, -8))
            except Exception:
                pass
            
            if item.is_stackable and item.load is not None and item.load > 1:
                stack_text = font_small.render(str(int(item.load)), True, WHITE)
                text_rect = stack_text.get_rect(bottomright=(slot_rect.right - 5, slot_rect.bottom - 2))
                surface.blit(stack_text, text_rect)

    backpack_slot_rect = get_backpack_slot_rect(modal['position'])
    pygame.draw.rect(surface, GRAY_40, backpack_slot_rect, 0, 3)
    surface.blit(font_small.render("Backpack", True, WHITE), (backpack_slot_rect.x + 1, backpack_slot_rect.y - 15))
    if (backpack := player.backpack):
        pygame.draw.rect(surface, backpack.color, backpack_slot_rect, 2, 5)
        if backpack.image:
            img_h = backpack_slot_rect.height - 10
            img_w = int(backpack.image.get_width() * (img_h / backpack.image.get_height()))
            scaled_sprite = pygame.transform.scale(backpack.image, (img_w, img_h))
            sprite_rect = scaled_sprite.get_rect(centery=backpack_slot_rect.centery, left=backpack_slot_rect.left + 5)
            surface.blit(scaled_sprite, sprite_rect)
            text_x_offset = sprite_rect.right + 10
        else:
            text_x_offset = backpack_slot_rect.left + 10
        item_name_text = font.render(f"{backpack.name}", True, backpack.color)
        surface.blit(item_name_text, (text_x_offset, backpack_slot_rect.top + 5))
        info_text = font.render(f"Slots: {backpack.capacity or 0}", True, WHITE)
        surface.blit(info_text, (text_x_offset, backpack_slot_rect.top + 25))
    else:
        pygame.draw.rect(surface, GRAY, backpack_slot_rect, 1, 3)
    
    invcontainer_slot_rect = get_invcontainer_slot_rect(modal['position'])
    pygame.draw.rect(surface, GRAY_40, invcontainer_slot_rect, 0, 3)

    surface.blit(font_small.render("", True, WHITE), (invcontainer_slot_rect.x + 1, invcontainer_slot_rect.y - 15))
    if (invcontainer := player.invcontainer):
        pygame.draw.rect(surface, invcontainer.color, invcontainer_slot_rect, 2, 5)
        if invcontainer.image:
            img_h = invcontainer_slot_rect.height - 10
            img_w = int(invcontainer.image.get_width() * (img_h / invcontainer.image.get_height()))
            scaled_sprite = pygame.transform.scale(invcontainer.image, (img_w, img_h))
            sprite_rect = scaled_sprite.get_rect(centery=invcontainer_slot_rect.centery, left=invcontainer_slot_rect.left + 5)
            surface.blit(scaled_sprite, sprite_rect)
            text_x_offset = sprite_rect.right + 10
        else:
            text_x_offset = invcontainer_slot_rect.left + 10

    else:
        pygame.draw.rect(surface, GRAY, invcontainer_slot_rect, 1, 3)

    belt_y_start = backpack_slot_rect.bottom + 15
    # This line caused the error. It now has access to base_modal.
    surface.blit(font.render("", True, WHITE), (base_modal.modal_x + 10, belt_y_start))
    for i in range(5):
        item = player.belt[i]
        slot_rect = get_belt_slot_rect_in_modal(i, modal['position'])
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        
        # Highlight active weapon
        if item and player.active_weapon and item.id == player.active_weapon.id:
            pygame.draw.rect(surface, YELLOW, slot_rect, 2, 3)
        else:
            pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

        num_text = font_small.render(f"[{str(i + 1)}]", True, WHITE)
        surface.blit(num_text, (slot_rect.centerx - num_text.get_width() // 2, slot_rect.top - 15))
        if item:
            if item.image:
                img_h = slot_rect.height - 8
                img_w = int(item.image.get_width() * (img_h / item.image.get_height()))
                scaled_sprite = pygame.transform.scale(item.image, (img_w, img_h))
                sprite_rect = scaled_sprite.get_rect(center=slot_rect.center)
                surface.blit(scaled_sprite, sprite_rect)
            else:
                pygame.draw.rect(surface, item.color, slot_rect.inflate(-8, -8))
            
            if item.is_stackable and item.load is not None and item.load > 1:
                stack_text = font_small.render(str(int(item.load)), True, WHITE)
                text_rect = stack_text.get_rect(bottomright=(slot_rect.right - 5, slot_rect.bottom - 2))
                surface.blit(stack_text, text_rect)

    active_weapon_text = "None (Hands)"
    if player.active_weapon:
        active_weapon_text = f"Equipped: {player.active_weapon.name.split('(')[0]}"
        if player.active_weapon.durability is not None:
            active_weapon_text += f" | Dur: {player.active_weapon.durability:.0f}%"
        if player.active_weapon.item_type == 'weapon' and player.active_weapon.load is not None:
            active_weapon_text += f" | Ammo: {player.active_weapon.load:.0f}/{player.active_weapon.capacity:.0f}"
    status_text = font_small.render(active_weapon_text, True, YELLOW)
    surface.blit(status_text, (base_modal.modal_x + 10, belt_y_start + 80))

# Helper function to get rects for the 'Gear' tab
def get_gear_slot_rects(modal_position):
    modal_x, modal_y = modal_position
    slot_size = 48
    gap = 8
    # Use INVENTORY_MODAL_WIDTH from config or modals.py, hardcoding 300 as a fallback
    modal_center_x = modal_x + (INVENTORY_MODAL_WIDTH / 2) 

    # Content Y start is 80 (Header 35 + Tab 30 + Padding 15)
    y1 = modal_y + 80 
    y2 = y1 + slot_size + gap
    y3 = y2 + slot_size + gap

    rects = {
        # [HEAD]
        'head': pygame.Rect(modal_center_x - (slot_size / 2), y1, slot_size, slot_size),
        
        # [HANDS][TORSO][BODY]
        'hands': pygame.Rect(modal_center_x - (slot_size / 2) - gap - slot_size, y2, slot_size, slot_size),
        'torso': pygame.Rect(modal_center_x - (slot_size / 2), y2, slot_size, slot_size),
        'body': pygame.Rect(modal_center_x + (slot_size / 2) + gap, y2, slot_size, slot_size),
        
        # [LEGS][FEET] (PANTS maps to LEGS)
        'legs': pygame.Rect(modal_center_x - (slot_size / 2) - (gap/2) - (slot_size/2), y3, slot_size, slot_size),
        'feet': pygame.Rect(modal_center_x + (gap/2) + (slot_size/2) - (slot_size/2), y3, slot_size, slot_size)
    }
    
    # Correcting legs/feet logic to be perfectly centered
    # Total width of 2 slots = 48*2 + 8 = 104
    # Start X = center_x - 104/2 = center_x - 52
    rects['legs'] = pygame.Rect(modal_center_x - 52, y3, slot_size, slot_size)
    rects['feet'] = pygame.Rect(modal_center_x + 4, y3, slot_size, slot_size) # -52 + 48 + 8 = +4

    return rects

# Helper function to draw the content of the 'Gear' tab
def _draw_gear_tab(surface, player, modal, assets, mouse_pos):
    modal['gear_slot_rects'] = get_gear_slot_rects(modal['position'])
    
    if not hasattr(player, 'clothes'):
         player.clothes = {} # Safeguard

    for slot_name, slot_rect in modal['gear_slot_rects'].items():
        # Draw empty slot
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

        # Draw label
        label_text = font_small.render(slot_name.upper(), True, GRAY)
        label_rect = label_text.get_rect(centerx=slot_rect.centerx, y=slot_rect.bottom + 5)
        surface.blit(label_text, label_rect)

        # Get item from player's clothes
        # Assumes player.clothes stores Item objects, similar to player.inventory
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

# --- Slot Position Getters (Modified for Tab Bar) ---
# Content now starts ~30px lower to accommodate the tab bar

def get_inventory_slot_rect(i, modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 80 # Was 50, moved down 30 for tabs
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_belt_slot_rect_in_modal(i, modal_position):
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 230 # Was 200, moved down 30 for tabs
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_backpack_slot_rect(modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    slot_w = 218
    slot_h = 48
    x = modal_x + 10
    y = modal_y + 155 # Was 125, moved down 30 for tabs
    return pygame.Rect(x, y, slot_w, slot_h)

def get_invcontainer_slot_rect(modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    x = modal_x + 235
    y = modal_y + 155 # Was 125, moved down 30 for tabs
    return pygame.Rect(x, y, slot_w, slot_h)

# --- Main Modal Function (Refactored for Tabs) ---

def draw_inventory_modal(surface, player, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, "Inventory")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    # --- Tabs ---
    tabs_data = [
        {'label': 'Inventory', 'icon_path': SPRITE_PATH + 'ui/inventory.png'},
        {'label': 'Gear', 'icon_path': SPRITE_PATH + 'ui/status.png'} # Using status icon for gear
    ]
    modal['tabs_data'] = tabs_data

    # Ensure active_tab is set correctly
    if 'active_tab' not in modal or modal['active_tab'] not in {t['label'] for t in tabs_data}:
        modal['active_tab'] = 'Inventory' # Default to Inventory

    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw() # Draws tabs below the header

    # --- Draw Tab Content ---
    if modal['active_tab'] == 'Inventory':
        # Draw the original inventory/belt/backpack content
        # *** FIX: Pass base_modal to the helper function ***
        _draw_inventory_tab(surface, player, modal, assets, mouse_pos, base_modal)
    elif modal['active_tab'] == 'Gear':
        # Draw the new 6-slot gear layout
        _draw_gear_tab(surface, player, modal, assets, mouse_pos)

    
    return None, close_button, minimize_button