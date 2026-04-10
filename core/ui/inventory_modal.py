import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs 
from core.ui.container_modal import _draw_slots
from core.data.localization import tr
# --- NEW: Belt HUD Functions ---

def draw_text_shadow(surface, font, text, color, pos, align='topleft', shadow_color=BLACK, offset=(1, 1)):
    """Draws text with a drop shadow for better readability."""
    shadow_surf = font.render(text, True, shadow_color)
    text_surf = font.render(text, True, color)
    
    # Calculate rect based on alignment
    if align == 'bottomright':
        text_rect = text_surf.get_rect(bottomright=pos)
        shadow_rect = shadow_surf.get_rect(bottomright=(pos[0] + offset[0], pos[1] + offset[1]))
    elif align == 'center':
        text_rect = text_surf.get_rect(center=pos)
        shadow_rect = shadow_surf.get_rect(center=(pos[0] + offset[0], pos[1] + offset[1]))
    else: # topleft
        text_rect = text_surf.get_rect(topleft=pos)
        shadow_rect = shadow_surf.get_rect(topleft=(pos[0] + offset[0], pos[1] + offset[1]))

    surface.blit(shadow_surf, shadow_rect)
    surface.blit(text_surf, text_rect)

# --- Belt HUD Functions ---

def get_belt_hud_slot_rect(i):
    slot_size = 40 # Reduced from 48
    gap = 6        # Reduced from 8
    total_width = (slot_size * 5) + (gap * 4)
    start_x = (GAME_WIDTH - total_width) // 2
    start_y = GAME_HEIGHT - slot_size - 15 
    x = start_x + i * (slot_size + gap)
    return pygame.Rect(x, start_y, slot_size, slot_size)


# --- Inventory Tab Helper ---


def _draw_inventory_tab(surface, game, player, modal, assets, mouse_pos, base_modal):
    # [CHANGED] Set slot count to 10
    INVENTORY_SLOTS = 10 

    # 1. Draw Inventory Slots (Pockets)
    for i in range(INVENTORY_SLOTS):
        slot_rect = get_inventory_slot_rect(i, modal['position'])
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

        # Default colors
        bg_color = GRAY_40
        border_color = GRAY
        border_width = 1
        
        # --- NEW: Dynamic Drag & Hover Highlighting ---
        hovered = slot_rect.collidepoint(mouse_pos)
        if hovered:
            bg_color = GRAY_60
            if game and game.dragged_item:
                # Assuming valid placement (expand this if you have specific restrictions)
                border_color = GREEN 
                border_width = 2
            else:
                border_color = WHITE
                
        pygame.draw.rect(surface, bg_color, slot_rect, 0, 3)
        pygame.draw.rect(surface, border_color, slot_rect, border_width, 3)
        # ----------------------------------------------

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

            # Durability
            if item.durability is not None and item.max_durability > 0:
                max_dur = item.max_durability
                cur_dur = max(0, item.durability)
                pct = cur_dur / max_dur
                bar_w, bar_h = slot_rect.width - 10, 3
                bar_x, bar_y = slot_rect.x + 5, slot_rect.bottom - 6
                col = (0, 255, 0) if pct > 0.5 else (255, 255, 0) if pct > 0.2 else (255, 0, 0)
                pygame.draw.rect(surface, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h))
                if pct > 0: pygame.draw.rect(surface, col, (bar_x, bar_y, int(bar_w * pct), bar_h))
            
            # Stack Count (With Shadow)
            show_count = False
            if hasattr(item, 'is_stackable') and item.is_stackable() and item.load is not None and item.load > 1:
                show_count = True
            elif item.item_type in ['weapon', 'weapon_ranged'] and item.load is not None:
                show_count = True

            if show_count:
                draw_text_shadow(
                    surface, 
                    font_14, 
                    str(int(item.load)), 
                    WHITE, 
                    (slot_rect.right - 3, slot_rect.bottom - 1), 
                    align='bottomright'
                )

    
    # 4. Draw Belt Slots (in Modal) - UPDATED TO MATCH HUD
    belt_y_start = modal['position'][1] + 185

    # Optional: Add label 'Belt' if desired, or leave blank as requested
    
    for i in range(5):
        item = player.belt[i]
        slot_rect = get_belt_slot_rect_in_modal(i, modal['position'])
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        
        if item and player.active_weapon and item.id == player.active_weapon.id:
            pygame.draw.rect(surface, YELLOW, slot_rect, 2, 3)
        else:
            pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

        # --- MATCH HUD STYLE: Number inside slot ---
        num_text = font_14.render(str(i + 1), True, GRAY)
        surface.blit(num_text, (slot_rect.x + 3, slot_rect.y + 1))

        if item:
            if item.image:
                img_h = slot_rect.height - 8
                img_w = int(item.image.get_width() * (img_h / item.image.get_height()))
                scaled_sprite = pygame.transform.scale(item.image, (img_w, img_h))
                sprite_rect = scaled_sprite.get_rect(center=slot_rect.center)
                surface.blit(scaled_sprite, sprite_rect)
            else:
                pygame.draw.rect(surface, item.color, slot_rect.inflate(-8, -8))
            
            # Durability Bar
            if item.durability is not None and item.max_durability > 0:
                max_dur = item.max_durability
                cur_dur = max(0, item.durability)
                pct = cur_dur / max_dur
                bar_w, bar_h = slot_rect.width - 10, 3
                bar_x, bar_y = slot_rect.x + 5, slot_rect.bottom - 6
                col = (0, 255, 0) if pct > 0.5 else (255, 255, 0) if pct > 0.2 else (255, 0, 0)
                pygame.draw.rect(surface, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h))
                if pct > 0: pygame.draw.rect(surface, col, (bar_x, bar_y, int(bar_w * pct), bar_h))

            # Stack/Ammo (With Shadow)
            show_count = False
            if hasattr(item, 'is_stackable') and item.is_stackable() and item.load is not None and item.load > 1:
                show_count = True
            elif item.item_type in ['weapon', 'weapon_ranged'] and item.load is not None:
                show_count = True

            if show_count:
                draw_text_shadow(
                    surface, 
                    font_14, 
                    str(int(item.load)), 
                    WHITE, 
                    (slot_rect.right - 3, slot_rect.bottom - 1), 
                    align='bottomright'
                )

    # 5. Draw Active Weapon Status
    # Adjusted start_y to be relative to the shifted belt position
    start_x = base_modal.modal_x + 10
    start_y = belt_y_start + 80
    

def get_inventory_slot_rect(i, modal_position=(GAME_WIDTH, 0)):
    modal_x, modal_y = modal_position
    slot_w = 40 # Reduced from 48
    slot_h = 40
    gap = 6     # Reduced from 8
    start_x = modal_x + 10
    
    row = i // 5
    col = i % 5
    
    start_y = modal_y + 80 
    
    x = start_x + col * (slot_w + gap)
    y = start_y + row * (slot_h + gap)
    return pygame.Rect(x, y, slot_w, slot_h)

def get_belt_slot_rect_in_modal(i, modal_position):
    modal_x, modal_y = modal_position
    slot_w = 40 # Reduced from 48
    slot_h = 40
    gap = 6     # Reduced from 8
    start_x = modal_x + 10
    
    # Recalculated spacing: Inventory takes up to ~170, plus 15px margin
    start_y = modal_y + 185 
    
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)


def draw_inventory_modal(surface, game, player, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, "Inventory (I)")
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()
    

    # --- 1. DYNAMIC TAB GENERATION ---
    tabs_data = [{'label': 'Inventory', 'icon_path': SPRITE_PATH + 'ui/inventory_tab.png'}]
    container_mapping = {}

    def register_container(item, default_name):
        # [CHANGE] Added check: ensure item has 'inventory' attribute before creating a tab
        valid_container_types = ['container']
        
        if item and hasattr(item, 'inventory') and item.item_type in valid_container_types:
            # Create a unique label to handle multiple containers of the same type
            count = sum(1 for label in container_mapping if label.startswith(default_name))
            label = f"{default_name} #{count + 1}" if count > 0 else default_name
            
            tabs_data.append({
                'label': label,
                'icon': item.image if item.image else None
            })
            container_mapping[label] = item

    # Scan all possible player slots for items that are containers
    

    # 3. Check Belt Slots
    for item in player.belt:
        if item:
            register_container(item, tr('item', item.name))

    # 4. Check Main Inventory Slots for nested containers
    for item in player.inventory:
        if item:
            register_container(item, tr('item', item.name))

    modal['tabs_data'] = tabs_data
    modal['container_mapping'] = container_mapping
    # Ensure the active tab remains valid after potential inventory changes
    if 'active_tab' not in modal or modal['active_tab'] not in {t['label'] for t in tabs_data}:
        modal['active_tab'] = 'Inventory'

    # --- 2. RENDER TABS ---
    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw(game, mouse_pos)

    # --- 3. RENDER CONTENT ---
    active_label = modal['active_tab']
    if active_label == 'Inventory':
        _draw_inventory_tab(surface, game, player, modal, assets, mouse_pos, base_modal)
    elif active_label in container_mapping:
        # Use the generic container drawer for any detected container
        _draw_container_tab(surface, game, player, modal, mouse_pos, container_mapping[active_label])
    
    return None, close_button

def _draw_container_tab(surface, game, player, modal, mouse_pos, container_obj):
    """Generic drawer that reuses slot logic for any container object."""
    if not container_obj or not hasattr(container_obj, 'inventory'):
        return

    padding = 10
    start_x = modal['rect'].x + padding
    start_y = modal['rect'].y + 80 
    
    _draw_slots(
        surface, 
        game, 
        container_obj, 
        start_x, 
        start_y, 
        modal['rect'].height, 
        80, 
        mouse_pos
    )