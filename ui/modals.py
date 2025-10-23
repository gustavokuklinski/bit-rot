import pygame
import os
from data.config import *
from core.entities.item import Item
from core.entities.zombie import Zombie

class BaseModal:
    def __init__(self, surface, modal, assets, title):
        self.surface = surface
        self.modal = modal
        self.assets = assets
        self.title = title
        self.modal_w, self.modal_h = self.get_modal_dimensions()
        self.modal_x, self.modal_y = modal['position']
        self.header_h = 35
        self.minimized = modal.get('minimized', False)
        self.modal_rect = pygame.Rect(self.modal_x, self.modal_y, self.modal_w, self.header_h if self.minimized else self.modal_h)
        self.close_button_rect = self.assets['close_button'].get_rect(topright=(self.modal_x + self.modal_w - 10, self.modal_y + 10))
        self.minimize_button_rect = self.assets['minimize_button'].get_rect(topright=(self.close_button_rect.left - 10, self.modal_y + 10))

    def get_modal_dimensions(self):
        if self.modal['type'] == 'inventory':
            return INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT
        elif self.modal['type'] == 'status':
            return STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT
        elif self.modal['type'] == 'container':
            return 300, 300
        return 300, 300

    def draw_header(self):
        header_rect = pygame.Rect(self.modal_x, self.modal_y, self.modal_w, self.header_h)
        pygame.draw.rect(self.surface, (60, 60, 60), header_rect, 0, border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.rect(self.surface, WHITE, header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)
        title_text = font.render(self.title, True, WHITE)
        self.surface.blit(title_text, (self.modal_x + 10, self.modal_y + 10))
        self.surface.blit(self.assets['close_button'], self.close_button_rect)
        self.surface.blit(self.assets['minimize_button'], self.minimize_button_rect)

    def draw_base(self):
        height = self.header_h if self.minimized else self.modal_h
        s = pygame.Surface((self.modal_w, height), pygame.SRCALPHA)
        s.fill((20, 20, 20, 200))
        self.surface.blit(s, (self.modal_x, self.modal_y))
        pygame.draw.rect(self.surface, WHITE, self.modal_rect, 1, 4)
        self.draw_header()

    def get_buttons(self):
        return {'id': self.modal['id'], 'type': 'close', 'rect': self.close_button_rect}, \
               {'id': self.modal['id'], 'type': 'minimize', 'rect': self.minimize_button_rect}

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
    slot_h = 48
    gap = 8
    start_x = modal_x + 10
    start_y = modal_y + 190
    x = start_x + i * (slot_w + gap)
    return pygame.Rect(x, start_y, slot_w, slot_h)

def get_backpack_slot_rect(modal_position=(VIRTUAL_SCREEN_WIDTH, 0)):
    modal_x, modal_y = modal_position
    # Backpack occupies a wide slot under the inventory row
    slot_w = 272
    slot_h = 48
    x = modal_x + 10
    y = modal_y + 110
    return pygame.Rect(x, y, slot_w, slot_h)

def get_container_slot_rect(container_pos, i):
    rows, cols = 4, 5
    slot_size = 48
    padding = 10
    start_x = container_pos[0] + padding
    start_y = container_pos[1] + 40
    row = i // cols
    col = i % cols
    return pygame.Rect(start_x + col * (slot_size + padding), start_y + row * (slot_size + padding), slot_size, slot_size)

# --- Modal Drawers (inventory/status/container/context) ---
def draw_inventory_modal(surface, player, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, "Inventory")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    # FIX: inventory UI must show exactly 5 inventory slots (single horizontal row)
    INVENTORY_SLOTS = 5

    tooltip_info = None  # collect tooltip data to draw later (on top)

    for i in range(INVENTORY_SLOTS):
        slot_rect = get_inventory_slot_rect(i, modal['position'])
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
    backpack_slot_rect = get_backpack_slot_rect(modal['position'])
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
    surface.blit(font.render("Belt", True, WHITE), (base_modal.modal_x + 10, belt_y_start))
    for i in range(5):
        item = player.belt[i]
        slot_rect = get_belt_slot_rect_in_modal(i, modal['position'])
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
    surface.blit(status_text, (base_modal.modal_x + 10, belt_y_start + 60))
    

    # Return tooltip info so caller can draw it on top of everything
    return tooltip_info, close_button, minimize_button

def draw_container_view(surface, container_item, modal, assets):
    if not container_item or not hasattr(container_item, 'inventory'):
        return
    
    base_modal = BaseModal(surface, modal, assets, f"{container_item.name} Contents")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return close_button, minimize_button

    rows, cols = 4, 5
    slot_size = 48
    padding = 10
    start_x = base_modal.modal_x + padding
    start_y = base_modal.modal_y + 40
    max_visible_rows = int((base_modal.modal_h - base_modal.header_h - padding) / (slot_size + padding))
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
    return close_button, minimize_button

def draw_status_modal(surface, player, modal, assets, zombies_killed):
    base_modal = BaseModal(surface, modal, assets, "Player Status")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return close_button, minimize_button

    y_offset = base_modal.modal_y + base_modal.header_h + 10
    x_offset = base_modal.modal_x + 10

    level_text = font.render(f"Level: {player.level}", True, WHITE)
    surface.blit(level_text, (x_offset, y_offset))
    y_offset += 20

    # Load stat icons (lazy, per-frame safe)
    stat_icons = {}
    icon_files = {
        "HP": "game/ui/hp.png",
        "Stamina": "game/ui/stamina.png",
        "Water": "game/ui/water.png",
        "Food": "game/ui/food.png",
        "Infection": "game/ui/infection.png",
        "XP": "game/ui/xp.png"
    }
    for k, path in icon_files.items():
        try:
            img = pygame.image.load(path).convert_alpha()
            stat_icons[k] = pygame.transform.scale(img, (24, 24))
        except Exception:
            stat_icons[k] = None

    stats = [
        ("HP", player.health, player.max_health, RED),
        ("Stamina", player.stamina, player.max_stamina, GRAY),
        ("Water", player.water, 100, BLUE),
        ("Food", player.food, 100, GREEN),
        ("Infection", player.infection, 100, YELLOW),
        ("XP", player.experience, player.xp_to_next_level, YELLOW)
    ]
    for i, (name, value, max_value, color) in enumerate(stats):
        y_pos = y_offset + i * 28
        icon = stat_icons.get(name)
        if icon:
            surface.blit(icon, (x_offset, y_pos))
            label_x = x_offset + 28
        else:
            # fallback to text label if icon missing
            text = font.render(f"{name}:", True, WHITE)
            surface.blit(text, (x_offset, y_pos))
            label_x = x_offset + 110

        # draw the bar (positioned after icon/text)
        bar_x = label_x + 12
        bar_width = int(100 * (value / max_value))
        bar_rect = pygame.Rect(bar_x, y_pos + 5, bar_width, 10)
        pygame.draw.rect(surface, color, bar_rect)
        pygame.draw.rect(surface, WHITE, (bar_x, y_pos + 5, 100, 10), 1)

    try:
        if '_kills_img' not in globals() or _kills_img is None:
            _kills_img = pygame.image.load('game/zombies/sprites/dead.png').convert_alpha()
            _kills_img = pygame.transform.scale(_kills_img, (24, 24))
    except Exception:
        _kills_img = None

    if _kills_img:
        surface.blit(_kills_img, (x_offset, y_pos + 35))
        num_text = font.render(f"{str(zombies_killed)} Killed", True, WHITE)
        surface.blit(num_text, (x_offset + _kills_img.get_width() + 16, y_pos + 35 + 6))
    else:
        zombies_killed_text = font.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
        surface.blit(zombies_killed_text, (x_offset, y_pos))
    
    return close_button, minimize_button

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