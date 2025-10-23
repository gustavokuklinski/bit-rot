import time
import pygame
import os

from config import *
from core.items import Item

# Note: player references UI helpers for slot rectangles for mouse detection.
# We import functions from ui (which remain in the root ui.py)
from modals import get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect

class Player:
    def __init__(self, player_data=None):
        self.x = GAME_WIDTH // 2
        self.y = GAME_HEIGHT // 2
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.color = BLUE

        data = player_data or {}
        # Stats
        self.max_health = data.get('max_health', 100.0)
        self.health = data.get('health', self.max_health)
        self.water = data.get('water', 100.0)
        self.food = data.get('food', 100.0)
        self.infection = data.get('infection', 0.0)
        self.max_stamina = data.get('max_stamina', 100.0)
        self.stamina = data.get('stamina', self.max_stamina)
        self.skill_strength = data.get('skill_strength', 3)
        self.skill_melee = data.get('skill_melee', 3)
        self.skill_ranged = data.get('skill_ranged', 3)

        self.inventory = []
        self.backpack = None
        self.active_weapon = None
        self.belt = [None] * 5
        self.last_decay_time = time.time()
        self.level = data.get('level', 1)
        self.experience = data.get('experience', 0)
        self.base_inventory_slots = 5

        # animation / action timers
        self.melee_swing_timer = 0
        self.gun_flash_timer = 0
        self.melee_swing_angle = 0
        self.drop_cooldown = 0

        self.is_reloading = False
        self.reload_timer = 0
        self.reload_duration = 120

        self.image = self._load_sprite(data.get('visuals', {}).get('sprite'))

    def _load_sprite(self, sprite_path):
        if not sprite_path: return None
        try:
            return pygame.image.load(sprite_path).convert_alpha()
        except pygame.error as e:
            print(f"Warning: Could not load player sprite '{sprite_path}': {e}")
            return None

    def update_position(self, dx, dy, obstacles, zombies):
        new_x = self.x + dx
        new_y = self.y + dy
        temp_rect = self.rect.copy()
        temp_rect.x = new_x
        collided_with_wall_x = any(temp_rect.colliderect(ob) for ob in obstacles)
        if not collided_with_wall_x:
            self.x = new_x
        temp_rect.y = new_y
        collided_with_wall_y = any(temp_rect.colliderect(ob) for ob in obstacles)
        if not collided_with_wall_y:
            self.y = new_y
        self.x = max(0, min(self.x, GAME_WIDTH - TILE_SIZE))
        self.y = max(0, min(self.y, GAME_HEIGHT - TILE_SIZE))
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, surface):
        draw_rect = self.rect.move(GAME_OFFSET_X, 0)
        if self.image:
            surface.blit(self.image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)
        # melee arc
        if self.melee_swing_timer > 0:
            swing_radius = TILE_SIZE * 1.5
            swing_color = YELLOW
            swing_thickness = 3
            center_x = self.x + TILE_SIZE // 2 + GAME_OFFSET_X
            center_y = self.y + TILE_SIZE // 2
            start_angle = self.melee_swing_angle - (3.1415/4)
            end_angle = self.melee_swing_angle + (3.1415/4)
            pygame.draw.arc(surface, swing_color,
                            (center_x - swing_radius, center_y - swing_radius, swing_radius * 2, swing_radius * 2),
                            start_angle, end_angle, swing_thickness)
            self.melee_swing_timer -= 1
        if self.is_reloading:
            progress = 1.0 - (self.reload_timer / self.reload_duration)
            bar_width = int(TILE_SIZE * 2 * progress)
            bar_rect = pygame.Rect(draw_rect.left - TILE_SIZE // 2, draw_rect.top - 10, bar_width, 5)
            bg_bar_rect = pygame.Rect(draw_rect.left - TILE_SIZE // 2, draw_rect.top - 10, TILE_SIZE * 2, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)
            pygame.draw.rect(surface, YELLOW, bar_rect)

    def update_stats(self):
        current_time = time.time()
        keys = pygame.key.get_pressed()
        is_moving = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]
        if is_moving and self.stamina > 0:
            self.stamina = max(0, self.stamina - 0.2)
        elif not is_moving and self.stamina < self.max_stamina:
            self.stamina = min(self.max_stamina, self.stamina + 0.3)
        if current_time - self.last_decay_time >= DECAY_RATE_SECONDS:
            self.water = max(0, self.water - WATER_DECAY_AMOUNT)
            self.food = max(0, self.food - FOOD_DECAY_AMOUNT)
            self.last_decay_time = current_time
            if self.water <= 0 or self.food <= 0:
                self.health -= 5.0 * (1 if self.water <= 0 else 0) + 5.0 * (1 if self.food <= 0 else 0)
                self.health = max(0, self.health)
            if self.infection > 0:
                self.infection += 0.1
                if self.infection > 100:
                    self.health = 0
        if self.is_reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self._finish_reload()
        if self.health <= 0:
            print("GAME OVER: Health depleted!")
            return True
        if self.drop_cooldown > 0:
            self.drop_cooldown -= 1
        return False

    def get_total_inventory_slots(self):
        if self.backpack:
            return self.base_inventory_slots + (self.backpack.capacity or 0)
        return self.base_inventory_slots

    def find_consumable_at_mouse(self, mouse_pos):
        for i, item in enumerate(self.inventory):
            if item and item.item_type == 'consumable':
                slot_rect = get_inventory_slot_rect(i)
                if slot_rect.collidepoint(mouse_pos):
                    return item, i
        return None, None

    def find_item_at_mouse(self, mouse_pos):
        for i, item in enumerate(self.inventory):
            if item:
                slot_rect = get_inventory_slot_rect(i)
                if slot_rect.collidepoint(mouse_pos):
                    return item, 'inventory', i
        for i, item in enumerate(self.belt):
            if item:
                slot_rect = get_belt_slot_rect_in_modal(i)
                if slot_rect.collidepoint(mouse_pos):
                    return item, 'belt', i
        if self.backpack:
            slot_rect = get_backpack_slot_rect()
            if slot_rect.collidepoint(mouse_pos):
                return self.backpack, 'backpack', 0
        return None, None, None

    def find_matching_ammo(self, weapon):
        if not weapon or not weapon.ammo_type:
            return None, None, None
        ammo_type_needed = weapon.ammo_type
        search_list = [(item, 'belt', i) for i, item in enumerate(self.belt) if item and item.item_type == 'consumable']
        search_list.extend([(item, 'inventory', i) for i, item in enumerate(self.inventory) if item and item.item_type == 'consumable'])
        for item, source_type, index in search_list:
            if item.load is not None and item.name == ammo_type_needed and item.load > 0:
                return item, source_type, index
        return None, None, None

    def reload_active_weapon(self):
        if self.is_reloading:
            print("Already reloading.")
            return
        weapon = self.active_weapon
        if not weapon or not weapon.ammo_type:
            print("Cannot reload: No gun equipped.")
            return
        if weapon.load >= weapon.capacity:
            print(f"{weapon.name} is already full ({weapon.load:.0f}/{weapon.capacity:.0f}).")
            return
        ammo_item, _, _ = self.find_matching_ammo(weapon)
        if not ammo_item:
            print(f"No {weapon.ammo_type} found.")
            return
        self.is_reloading = True
        self.reload_timer = self.reload_duration
        print(f"Reloading {weapon.name}...")

    def _finish_reload(self):
        self.is_reloading = False
        weapon = self.active_weapon
        if not weapon: return
        ammo_item, source_type, index = self.find_matching_ammo(weapon)
        if not ammo_item: return
        needed = int(weapon.capacity - weapon.load)
        available = int(ammo_item.load)
        transfer_amount = min(needed, available)
        if transfer_amount > 0:
            weapon.load += transfer_amount
            ammo_item.load -= transfer_amount
            print(f"Finished reloading. Load: {weapon.load:.0f}/{weapon.capacity:.0f}.")
            if ammo_item.load <= 0:
                if source_type == 'inventory':
                    try:
                        self.inventory.remove(ammo_item)
                    except ValueError:
                        pass
                elif source_type == 'belt':
                    self.belt[index] = None

    def get_item_context_options(self, item):
        options = []
        if item.item_type == 'consumable':
            if 'Ammo' in item.name or 'Shells' in item.name:
                options.append('Reload')
            else:
                options.append('Use')
            options.append('Equip')
        elif item.item_type == 'backpack':
            options.append('Open')
            if not self.backpack:
                options.append('Equip')
        elif item.item_type in ['weapon', 'tool']:
            options.append('Equip')
        options.append('Drop')
        return options

    def _get_source_inventory(self, source_type, container_item=None):
        if source_type == 'inventory':
            return self.inventory
        elif source_type == 'belt':
            return self.belt
        elif source_type == 'container' and container_item:
            return container_item.inventory
        return None

    def equip_item_to_belt(self, item, source_type, item_index, container_item=None):
        if not any(slot is None for slot in self.belt):
            print("Belt is full.")
            return False
        source_inventory = self._get_source_inventory(source_type, container_item)
        if source_inventory is None or item not in source_inventory:
            return False
        for i, slot in enumerate(self.belt):
            if slot is None:
                self.belt[i] = item
                source_inventory.pop(item_index)
                print(f"Equipped {item.name} to belt.")
                return True
        return False

    def consume_item(self, item, source_type, item_index, container_item=None):
        source_inventory = self._get_source_inventory(source_type, container_item)
        if item.item_type == 'consumable':
            if 'Water' in item.name:
                amount_needed = 100 - self.water
                amount_to_consume = min(amount_needed, item.load)
                self.water = min(100, self.water + amount_to_consume)
                self.stamina = min(self.max_stamina, self.stamina + (amount_to_consume / (item.capacity or 1)) * 25)
                item.load -= amount_to_consume
                print(f"Consumed {amount_to_consume:.0f}% Water. Water: {self.water:.0f}%")
            elif 'Food' in item.name:
                amount_needed = 100 - self.food
                amount_to_consume = min(amount_needed, item.load)
                self.food = min(100, self.food + amount_to_consume)
                item.load -= amount_to_consume
                print(f"Consumed {amount_to_consume:.0f}% Food. Food: {self.food:.0f}%")
            elif 'Vaccine' in item.name:
                amount_needed = self.infection
                amount_to_consume = min(amount_needed, item.load)
                self.infection = max(0, self.infection - amount_to_consume)
                item.load -= amount_to_consume
                print(f"Used {amount_to_consume:.0f}% Vaccine. New Infection: {self.infection:.0f}%")
            elif 'Ammo' in item.name or 'Shells' in item.name:
                self.reload_active_weapon()
                return True
            if item.load <= 0:
                if source_type == 'belt':
                    self.belt[item_index] = None
                elif source_type == 'inventory':
                    if item_index < len(self.inventory) and self.inventory[item_index] == item:
                        self.inventory.pop(item_index)
            return True
        return False

    def drop_item(self, source, index, container_item=None):
        if self.drop_cooldown > 0:
            print("Cannot drop items so quickly.")
            return None
        item_to_drop = None
        if source == 'inventory' and index < len(self.inventory):
            item_to_drop = self.inventory.pop(index)
        elif source == 'belt' and index < len(self.belt):
            item_to_drop = self.belt[index]
            self.belt[index] = None
            if self.active_weapon == item_to_drop:
                self.active_weapon = None
        elif source == 'backpack':
            item_to_drop = self.backpack
            self.backpack = None
        elif source == 'container' and container_item and index < len(container_item.inventory):
            item_to_drop = container_item.inventory.pop(index)
        return item_to_drop