import pygame
import os
from config import *
from core.items import Item
from core.zombies import Zombie

# This module contains modal/window rendering functions previously in ui.py

def get_inventory_slot_rect(i, modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    # Inventory is a single row of 5 columns inside the inventory modal
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 50
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_belt_slot_rect_in_modal(i, modal_position):
    # Belt slots arranged horizontally below backpack slot
    modal_x, modal_y = modal_position
    slot_w = 48
    slot_h = 40
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 190
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_backpack_slot_rect(modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    # Backpack occupies a wide slot under the inventory row
    slot_w = 280
    slot_h = 60
    x = modal_x + 10
    y = modal_y + 110
    return pygame.Rect(x, y, slot_w, slot_h)

def get_container_slot_rect(container_pos, i):
    rows, cols = 4, 4
    slot_size = 60
    padding = 10
    start_x = container_pos[0] + padding
    start_y = container_pos[1] + 40
    row = i // cols
    col = i % cols
    return pygame.Rect(start_x + col * (slot_size + padding), start_y + row * (slot_size + padding), slot_size, slot_size)

# --- Modal Drawers (inventory/status/container/context) ---
def draw_inventory_modal(surface, player, position, mouse_pos):
    modal_w, modal_h = 300, 300
    modal_x, modal_y = position
    modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
    s = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
    s.fill((20, 20, 20, 200))
    surface.blit(s, (modal_x, modal_y))
    pygame.draw.rect(surface, WHITE, modal_rect, 1, 4)

    header_h = 35
    header_rect = pygame.Rect(modal_x, modal_y, modal_w, header_h)
    pygame.draw.rect(surface, (60, 60, 60), header_rect, 0, border_top_left_radius=4, border_top_right_radius=4)
    pygame.draw.rect(surface, WHITE, header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)
    title_text = font.render("Inventory", True, WHITE)
    surface.blit(title_text, (modal_x + 10, modal_y + 10))
    close_text = font.render("ESC to close", True, GRAY)
    surface.blit(close_text, (modal_x + modal_w - close_text.get_width() - 10, modal_y + 10))

    # FIX: inventory UI must show exactly 5 inventory slots (single horizontal row)
    INVENTORY_SLOTS = 5

    tooltip_info = None  # collect tooltip data to draw later (on top)

    for i in range(INVENTORY_SLOTS):
        slot_rect = get_inventory_slot_rect(i, position)
        pygame.draw.rect(surface, (40, 40, 40), slot_rect, 0, 3)
        pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

        item = player.inventory[i] if i < len(player.inventory) else None

        # If item present draw its thumbnail centered in slot
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

        # Hover detection — store tooltip data (do not draw here)
        try:
            if slot_rect.collidepoint(mouse_pos) and item:
                tip_w = 220
                tip_h = 60
                tip_x = min(mouse_pos[0] + 16, VIRTUAL_SCREEN_WIDTH - tip_w - 10)
                tip_y = min(mouse_pos[1] + 16, VIRTUAL_GAME_HEIGHT - tip_h - 10)
                # determine fraction and color for bar
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

    # Backpack slot rendering unchanged (keeps current visuals)
    backpack_slot_rect = get_backpack_slot_rect(position)
    pygame.draw.rect(surface, (40, 40, 40), backpack_slot_rect, 0, 3)
    surface.blit(font.render("Backpack", True, WHITE), (backpack_slot_rect.x + 5, backpack_slot_rect.y - 20))
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
        info_text = font.render(f"Slots: +{backpack.capacity or 0}", True, WHITE)
        surface.blit(info_text, (text_x_offset, backpack_slot_rect.top + 25))
    else:
        pygame.draw.rect(surface, GRAY, backpack_slot_rect, 1, 3)

    # Belt
    belt_y_start = backpack_slot_rect.bottom + 10
    surface.blit(font.render("Belt", True, WHITE), (modal_x + 10, belt_y_start))
    for i in range(5):
        item = player.belt[i]
        slot_rect = get_belt_slot_rect_in_modal(i, position)
        pygame.draw.rect(surface, (40, 40, 40), slot_rect, 0, 3)
        pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)
        num_text = font.render(str(i + 1), True, WHITE)
        surface.blit(num_text, (slot_rect.centerx - num_text.get_width() // 2, slot_rect.top - 20))
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
    surface.blit(status_text, (modal_x + 10, belt_y_start + 60))
    

    # Return tooltip info so caller can draw it on top of everything
    return tooltip_info

def draw_container_view(surface, container_item, position):
    if not container_item or not hasattr(container_item, 'inventory'):
        return
    modal_w, modal_h = 300, 300
    modal_x, modal_y = position
    modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
    s = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
    s.fill((20, 20, 20, 200))
    surface.blit(s, (modal_x, modal_y))
    pygame.draw.rect(surface, WHITE, modal_rect, 1, 4)
    header_h = 35
    header_rect = pygame.Rect(modal_x, modal_y, modal_w, header_h)
    pygame.draw.rect(surface, (60, 60, 60), header_rect, 0, border_top_left_radius=4, border_top_right_radius=4)
    pygame.draw.rect(surface, WHITE, header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)
    title_text = font.render(f"{container_item.name} Contents", True, WHITE)
    surface.blit(title_text, (modal_x + 10, modal_y + 10))
    close_text = font.render("ESC to close", True, GRAY)
    surface.blit(close_text, (modal_x + modal_w - close_text.get_width() - 10, modal_y + 10))
    rows, cols = 4, 4
    slot_size = 60
    padding = 10
    start_x = modal_x + padding
    start_y = modal_y + 40
    max_visible_rows = int((modal_h - header_h - padding) / (slot_size + padding))
    max_visible_slots = max_visible_rows * cols
    for i in range(min(container_item.capacity, max_visible_slots)):
        row = i // cols
        col = i % cols
        slot_rect = pygame.Rect(start_x + col * (slot_size + padding), start_y + row * (slot_size + padding), slot_size, slot_size)
        pygame.draw.rect(surface, (40, 40, 40), slot_rect, 1, 3)
        if i < len(container_item.inventory):
            item = container_item.inventory[i]
            if item.image:
                surface.blit(pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8)), slot_rect.move(4, 4))
            else:
                pygame.draw.rect(surface, item.color, slot_rect.inflate(-8, -8))
    if container_item.capacity > max_visible_slots:
        more_text = font.render(f"... {container_item.capacity - max_visible_slots} more items ...", True, GRAY)
        surface.blit(more_text, (modal_x + padding, modal_y + modal_h - padding - more_text.get_height()))

# Buttons and status modal
_inventory_img = None
_status_img = None
def draw_inventory_button(surface):
    global _inventory_img
    if _inventory_img is None:
        try:
            _inventory_img = pygame.image.load('game/ui/inventory.png').convert_alpha()
            _inventory_img = pygame.transform.scale(_inventory_img, (40, 40))
        except pygame.error:
            _inventory_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _inventory_img.fill(GRAY)
    button_inventory_rect = pygame.Rect(10, 50, 60, 60)
    surface.blit(_inventory_img, button_inventory_rect)
    return button_inventory_rect

def draw_status_button(surface):
    global _status_img
    if _status_img is None:
        try:
            _status_img = pygame.image.load('game/ui/status.png').convert_alpha()
            _status_img = pygame.transform.scale(_status_img, (40, 40))
        except pygame.error:
            _status_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _status_img.fill(GRAY)
    button_rect = pygame.Rect(10, 10, 40, 40)
    surface.blit(_status_img, button_rect)
    return button_rect

def draw_status_modal(surface, player, position, zombies_killed):
    modal_w, modal_h = 300, 400
    modal_x, modal_y = position
    modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
    s = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
    s.fill((20, 20, 20, 200))
    surface.blit(s, (modal_x, modal_y))
    pygame.draw.rect(surface, WHITE, modal_rect, 1, 4)
    header_h = 35
    header_rect = pygame.Rect(modal_x, modal_y, modal_w, header_h)
    pygame.draw.rect(surface, (60, 60, 60), header_rect, 0, border_top_left_radius=4, border_top_right_radius=4)
    pygame.draw.rect(surface, WHITE, header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)
    title_text = font.render("Player Status", True, WHITE)
    surface.blit(title_text, (modal_x + 10, modal_y + 10))
    close_text = font.render("ESC to close", True, GRAY)
    surface.blit(close_text, (modal_x + modal_w - close_text.get_width() - 10, modal_y + 10))

    y_offset = modal_y + header_h + 10
    x_offset = modal_x + 10
    stats = [
        ("HP", player.health, RED),
        ("Stamina", player.stamina, GRAY),
        ("Water", player.water, BLUE),
        ("Food", player.food, GREEN),
        ("Infection", player.infection, YELLOW),
        ("XP", player.experience, YELLOW)
    ]
    for i, (name, value, color) in enumerate(stats):
        y_pos = y_offset + i * 28
        text = font.render(f"{name}:", True, WHITE)
        surface.blit(text, (x_offset, y_pos))
        bar_width = int(100 * (value / 100))
        bar_rect = pygame.Rect(x_offset + 110, y_pos + 5, bar_width, 10)
        pygame.draw.rect(surface, color, bar_rect)
        pygame.draw.rect(surface, WHITE, (x_offset + 110, y_pos + 5, 100, 10), 1)
    skill_y = y_pos + 35
    surface.blit(font.render(f"Ranged Skill: {player.skill_ranged}/10", True, WHITE), (x_offset, skill_y))
    surface.blit(font.render(f"Melee Skill: {player.skill_melee}/10", True, WHITE), (x_offset, skill_y + 20))
    weight_text = font.render(f"Weight: {player.get_inventory_weight():.1f}/{player.max_carry_weight:.1f}", True, WHITE)
    surface.blit(weight_text, (x_offset, skill_y + 50))
    zombies_killed_text = font.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
    surface.blit(zombies_killed_text, (x_offset, skill_y + 80))
    
   

def draw_context_menu(surface, menu_state, mouse_pos):
    if not menu_state['active']:
        return
    options = menu_state['options']
    if not options:
        menu_state['active'] = False
        return
    item_height = 25
    padding = 5
    max_width = max(font.size(opt)[0] for opt in options) + (padding * 2)
    menu_height = len(options) * item_height
    menu_x, menu_y = menu_state['position']
    if menu_x + max_width > VIRTUAL_SCREEN_WIDTH:
        menu_x -= max_width
    if menu_y + menu_height > VIRTUAL_GAME_HEIGHT:
        menu_y -= menu_height
    menu_rect = pygame.Rect(menu_x, menu_y, max_width, menu_height)
    s = pygame.Surface((max_width, menu_height), pygame.SRCALPHA)
    s.fill((20, 20, 20, 220))
    surface.blit(s, menu_rect.topleft)
    pygame.draw.rect(surface, WHITE, menu_rect, 1)
    menu_state['rects'] = []
    for i, option in enumerate(options):
        option_rect = pygame.Rect(menu_x, menu_y + i * item_height, max_width, item_height)
        menu_state['rects'].append(option_rect)
        text_color = WHITE
        if option_rect.collidepoint(mouse_pos):
            pygame.draw.rect(surface, (80, 80, 80), option_rect)
            text_color = YELLOW
        text_surf = font.render(option, True, text_color)
        surface.blit(text_surf, (option_rect.x + padding, option_rect.y + (item_height - text_surf.get_height()) // 2))