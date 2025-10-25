import pygame
from data.config import *
from core.ui.modals import BaseModal

def get_inventory_slot_rect(i, modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 50
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_belt_slot_rect_in_modal(i, modal_position):
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 190
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_backpack_slot_rect(modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    slot_w = 272
    slot_h = 48
    x = modal_x + 10
    y = modal_y + 110
    return pygame.Rect(x, y, slot_w, slot_h)

def draw_inventory_modal(surface, player, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, "Inventory")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    INVENTORY_SLOTS = 5

    tooltip_info = None

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

        try:
            if slot_rect.collidepoint(mouse_pos) and item:
                tip_w = 220
                tip_h = 60
                tip_x = min(mouse_pos[0] + 16, VIRTUAL_SCREEN_WIDTH - tip_w - 10)
                tip_y = min(mouse_pos[1] + 16, VIRTUAL_GAME_HEIGHT - tip_h - 10)
                if getattr(item, 'load', None) is not None and getattr(item, 'capacity', None):
                    frac = float(item.load) / max(1.0, float(item.capacity))
                    bar_color = GREEN
                elif getattr(item, 'durability', None) is not None:
                    frac = float(item.durability) / 100.0
                    bar_color = YELLOW
                else:
                    frac = 0.0
                    bar_color = GRAY

                tooltip_info = {
                    'rect': pygame.Rect(tip_x, tip_y, tip_w, tip_h),
                    'item': item,
                    'frac': max(0.0, min(1.0, frac)),
                    'bar_color': bar_color
                }
        except Exception:
            pass

    backpack_slot_rect = get_backpack_slot_rect(modal['position'])
    pygame.draw.rect(surface, GRAY_40, backpack_slot_rect, 0, 3)
    surface.blit(font.render("Backpack", True, WHITE), (backpack_slot_rect.x + 1, backpack_slot_rect.y - 10))
    if (backpack := player.backpack):
        pygame.draw.rect(surface, backpack.color, backpack_slot_rect, 2, 3)
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

    belt_y_start = backpack_slot_rect.bottom + 5
    surface.blit(font.render("", True, WHITE), (base_modal.modal_x + 10, belt_y_start))
    for i in range(5):
        item = player.belt[i]
        slot_rect = get_belt_slot_rect_in_modal(i, modal['position'])
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)
        num_text = font.render(str(i + 1), True, WHITE)
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

    active_weapon_text = "None (Hands)"
    if player.active_weapon:
        active_weapon_text = f"Equipped: {player.active_weapon.name.split('(')[0]}"
        if player.active_weapon.durability is not None:
            active_weapon_text += f" | Dur: {player.active_weapon.durability:.0f}%"
        if player.active_weapon.item_type == 'weapon' and player.active_weapon.load is not None:
            active_weapon_text += f" | Ammo: {player.active_weapon.load:.0f}/{player.active_weapon.capacity:.0f}"
    status_text = font.render(active_weapon_text, True, YELLOW)
    surface.blit(status_text, (base_modal.modal_x + 10, belt_y_start + 80))
    
    return tooltip_info, close_button, minimize_button
