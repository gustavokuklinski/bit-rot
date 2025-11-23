import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs 
from core.ui.container_modal import _draw_slots

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
    slot_size = 48
    gap = 8
    total_width = (slot_size * 5) + (gap * 4)
    start_x = (VIRTUAL_SCREEN_WIDTH - total_width) // 2
    start_y = VIRTUAL_GAME_HEIGHT - slot_size - 15 
    x = start_x + i * (slot_size + gap)
    return pygame.Rect(x, start_y, slot_size, slot_size)

def draw_belt_hud(surface, game, player, mouse_pos):
    """Draws the always-visible belt HUD at the bottom of the screen."""
    for i in range(5):
        slot_rect = get_belt_hud_slot_rect(i)
        
        pygame.draw.rect(surface, (30, 30, 30), slot_rect, 0, 3)
        
        item = player.belt[i]
        if item and player.active_weapon and item.id == player.active_weapon.id:
            pygame.draw.rect(surface, YELLOW, slot_rect, 2, 3)
        else:
            pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

        # Draw Hotkey Number (Inside, Gray)
        num_text = font_small.render(str(i + 1), True, GRAY)
        surface.blit(num_text, (slot_rect.x + 3, slot_rect.y + 1))

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

            # Stack/Ammo Count (With Shadow)
            show_count = False
            if hasattr(item, 'is_stackable') and item.is_stackable() and item.load is not None and item.load > 1:
                show_count = True
            elif item.item_type in ['weapon', 'weapon_ranged'] and item.load is not None:
                show_count = True

            if show_count:
                draw_text_shadow(
                    surface, 
                    font_small, 
                    str(int(item.load)), 
                    WHITE, 
                    (slot_rect.right - 3, slot_rect.bottom - 1), 
                    align='bottomright'
                )

# --- Inventory Tab Helper ---


def _draw_inventory_tab(surface, player, modal, assets, mouse_pos, base_modal):
    INVENTORY_SLOTS = 5

    # 1. Draw Inventory Slots (Pockets)
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
                    font_small, 
                    str(int(item.load)), 
                    WHITE, 
                    (slot_rect.right - 3, slot_rect.bottom - 1), 
                    align='bottomright'
                )

    # 2. Draw Backpack Slot
    backpack_slot_rect = get_backpack_slot_rect(modal['position'])
    pygame.draw.rect(surface, GRAY_40, backpack_slot_rect, 0, 3)
    
    # "Backpack" Label with Shadow
    backpack_label = font_small.render("Backpack", True, GRAY)
    surface.blit(backpack_label, (backpack_slot_rect.x + 3, backpack_slot_rect.y + 1))

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
        
        # Backpack Text with Shadow
        draw_text_shadow(surface, font, f"{backpack.name}", backpack.color, (text_x_offset, backpack_slot_rect.top + 5))
        
        # Slots Info with Shadow
        draw_text_shadow(surface, font, f"Slots: {backpack.capacity or 0}", WHITE, (text_x_offset, backpack_slot_rect.top + 25))
    else:
        pygame.draw.rect(surface, GRAY, backpack_slot_rect, 1, 3)
    
    # 3. Draw Utility Slot
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
    else:
        pygame.draw.rect(surface, GRAY, invcontainer_slot_rect, 1, 3)

    # 4. Draw Belt Slots (in Modal) - UPDATED TO MATCH HUD
    belt_y_start = backpack_slot_rect.bottom + 15

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
        num_text = font_small.render(str(i + 1), True, GRAY)
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
                    font_small, 
                    str(int(item.load)), 
                    WHITE, 
                    (slot_rect.right - 3, slot_rect.bottom - 1), 
                    align='bottomright'
                )

    # 5. Draw Active Weapon Status
    start_x = base_modal.modal_x + 10
    start_y = belt_y_start + 80
    
    if player.active_weapon:
        name_str = f"{player.active_weapon.name.split('(')[0]}"
        draw_text_shadow(surface, font_notification, name_str, YELLOW, (start_x, start_y))
        
        # Calculate width of name for positioning bar
        name_w = font_notification.size(name_str)[0]
        current_x = start_x + name_w + 10
        
        if player.active_weapon.durability is not None:
             max_dur = player.active_weapon.max_durability
             if max_dur > 0:
                 cur_dur = max(0, player.active_weapon.durability)
                 pct = cur_dur / max_dur
                 bar_w, bar_h = 100, 10
                 bar_y_offset = 3
                 col = (0, 255, 0) if pct > 0.5 else (255, 255, 0) if pct > 0.2 else (255, 0, 0)
                 pygame.draw.rect(surface, (60, 60, 60), (current_x, start_y + bar_y_offset, bar_w, bar_h))
                 fill_w = int(bar_w * pct)
                 if fill_w > 0: pygame.draw.rect(surface, col, (current_x, start_y + bar_y_offset, fill_w, bar_h))
                 pygame.draw.rect(surface, (150, 150, 150), (current_x, start_y + bar_y_offset, bar_w, bar_h), 1)
                 current_x += bar_w + 10
        
        if player.active_weapon.item_type in ['weapon', 'weapon_ranged'] and player.active_weapon.load is not None:
             ammo_str = f"| Ammo: {int(player.active_weapon.load)}/{int(player.active_weapon.capacity)}"
             draw_text_shadow(surface, font_notification, ammo_str, YELLOW, (current_x, start_y))
             
    else:
        draw_text_shadow(surface, font_notification, "None (Hands)", YELLOW, (start_x, start_y))

def _draw_backpack_tab(surface, game, player, modal, mouse_pos):
    if not player.backpack:
        return

    # Define content area (aligns with where tabs start)
    padding = 10
    start_x = modal['rect'].x + padding
    start_y = modal['rect'].y + 80 # Header(35) + Tabs(30) + Padding(15)
    
    # Reuse the container drawing logic from core.ui.container
    _draw_slots(
        surface, 
        game, 
        player.backpack, 
        start_x, 
        start_y, 
        modal['rect'].height, 
        80, # Header offset for calculation
        mouse_pos
    )

def get_inventory_slot_rect(i, modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 80 
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_belt_slot_rect_in_modal(i, modal_position):
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 230
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_backpack_slot_rect(modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    slot_w = 218
    slot_h = 48
    x = modal_x + 10
    y = modal_y + 155
    return pygame.Rect(x, y, slot_w, slot_h)

def get_invcontainer_slot_rect(modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    x = modal_x + 235
    y = modal_y + 155 
    return pygame.Rect(x, y, slot_w, slot_h)

def draw_inventory_modal(surface, game, player, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, "Inventory")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    # --- Tabs ---
    tabs_data = [
        {'label': 'Inventory', 'icon_path': SPRITE_PATH + 'ui/inventory_tab.png'}
    ]

    if player.backpack:
        bag_tab = {
            'label': 'Bag',
            'icon': player.backpack.image if player.backpack.image else None 
        }
        tabs_data.append(bag_tab)

    modal['tabs_data'] = tabs_data

    if 'active_tab' not in modal or modal['active_tab'] not in {t['label'] for t in tabs_data}:
        modal['active_tab'] = 'Inventory'

    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw()

    if modal['active_tab'] == 'Inventory':
        _draw_inventory_tab(surface, player, modal, assets, mouse_pos, base_modal)
    elif modal['active_tab'] == 'Bag':
        _draw_backpack_tab(surface, game, player, modal, mouse_pos)
    
    return None, close_button, minimize_button