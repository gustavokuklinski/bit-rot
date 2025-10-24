import time
import pygame
import os
import random

from data.config import *
from core.entities.item import Item
from core.entities.corpse import Corpse

# Note: player references UI helpers for slot rectangles for mouse detection.
# We import functions from ui (which remain in the root ui.py)
from ui.modals import get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect

class Player:
    def __init__(self, player_data=None):
        self.x = GAME_WIDTH // 2
        self.y = GAME_HEIGHT // 2
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.vx = 0
        self.vy = 0
        self.color = BLUE

        data = player_data or {}
        stats = data.get('stats', {})
        skills = data.get('skills', {})

        # Stats
        self.max_health = stats.get('health', 100.0)
        self.health = stats.get('health', self.max_health)
        self.water = stats.get('water', 100.0)
        self.food = stats.get('food', 100.0)
        self.infection = stats.get('infection', 0.0)
        self.max_stamina = stats.get('stamina', 100.0)
        self.stamina = stats.get('stamina', self.max_stamina)
        self.skill_strength = skills.get('strength', 3)
        self.skill_melee = skills.get('melee', 3)
        self.skill_ranged = skills.get('ranged', 3)

        self.inventory = []
        self.backpack = None
        self.active_weapon = None
        self.belt = [None] * 5
        self.last_decay_time = time.time()
        self.level = stats.get('level', 1)
        self.experience = stats.get('experience', 0)
        self.xp_to_next_level = 100 * self.level
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

    def add_xp(self, amount):
        self.experience += amount
        print(f"Gained {amount} XP.")
        if self.experience >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.experience = 0
        self.xp_to_next_level = 100 * self.level
        self.max_health += 10
        self.health = self.max_health
        print(f"Leveled up to level {self.level}!")

    def update_position(self, obstacles, zombies):
        # Move on X axis first
        self.x += self.vx
        self.rect.x = int(self.x)

        # Check for X-axis collisions with obstacles
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if self.vx > 0:  # Moving right
                    self.rect.right = obstacle.left
                elif self.vx < 0:  # Moving left
                    self.rect.left = obstacle.right
                self.x = self.rect.x

        # Move on Y axis separately
        self.y += self.vy
        self.rect.y = int(self.y)

        # Check for Y-axis collisions with obstacles
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if self.vy > 0:  # Moving down
                    self.rect.bottom = obstacle.top
                elif self.vy < 0:  # Moving up
                    self.rect.top = obstacle.bottom
                self.y = self.rect.y
        
        # --- ADD THIS BLOCK BACK ---
        # Clamp player to screen boundaries (for edge transitions)
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > GAME_WIDTH:
            self.rect.right = GAME_WIDTH
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > GAME_HEIGHT:
            self.rect.bottom = GAME_HEIGHT
            
        self.x = self.rect.x
        self.y = self.rect.y
        # --- END OF ADDED BLOCK ---

    def draw(self, surface, offset_x, offset_y):
        draw_rect = self.rect.move(offset_x, offset_y)
        
        if self.image:
            surface.blit(self.image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)

        # Melee arc
        if self.melee_swing_timer > 0:
            swing_radius = TILE_SIZE * 1.5
            center_x, center_y = draw_rect.center
            start_angle = self.melee_swing_angle - (3.1415 / 4)
            end_angle = self.melee_swing_angle + (3.1415 / 4)
            arc_bounds = pygame.Rect(center_x - swing_radius, center_y - swing_radius, swing_radius * 2, swing_radius * 2)
            pygame.draw.arc(surface, YELLOW, arc_bounds, start_angle, end_angle, 3)
            self.melee_swing_timer -= 1

        # Reloading bar
        if self.is_reloading:
            progress = 1.0 - (self.reload_timer / self.reload_duration)
            bar_total_width = TILE_SIZE * 2
            bar_x = draw_rect.centerx - (bar_total_width / 2)
            bar_y = draw_rect.top - 10
            
            bg_bar_rect = pygame.Rect(bar_x, bar_y, bar_total_width, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)
            
            bar_progress_width = int(bar_total_width * progress)
            bar_rect = pygame.Rect(bar_x, bar_y, bar_progress_width, 5)
            pygame.draw.rect(surface, YELLOW, bar_rect)

    def update_stats(self):
        current_time = time.time()
        keys = pygame.key.get_pressed()
        is_moving = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]
        stamina_cap = self.max_stamina * (1 - self.infection / 100)
        if is_moving and self.stamina > 0:
            self.stamina = max(0, self.stamina - 0.2)
        elif not is_moving and self.stamina < stamina_cap:
            self.stamina = min(stamina_cap, self.stamina + 0.3)



        if current_time - self.last_decay_time >= DECAY_RATE_SECONDS:
            self.water = max(0, self.water - WATER_DECAY_AMOUNT)
            self.food = max(0, self.food - FOOD_DECAY_AMOUNT)
            self.last_decay_time = current_time
            if self.water <= 0 or self.food <= 0:
                self.health -= 5.0 * (1 if self.water <= 0 else 0) + 5.0 * (1 if self.food <= 0 else 0)
                self.health = max(0, self.health)
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
        if isinstance(item, Corpse):
            options.append('Open')
            return options
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
                item.load -= amount_to_consume
                print(f"Consumed {amount_to_consume:.0f}% Water. Water: {self.water:.0f}%")
            elif 'Food' in item.name:
                amount_needed = 100 - self.food
                amount_to_consume = min(amount_needed, item.load)
                self.food = min(100, self.food + amount_to_consume)
                item.load -= amount_to_consume
                print(f"Consumed {amount_to_consume:.0f}% Food. Food: {self.food:.0f}%")
            elif item.hp is not None:
                self.health = min(self.max_health, self.health + item.hp)
                print(f"Used {item.name} and restored {item.hp} HP.")
                item.load -= 1
            elif 'Vaccine' in item.name:
                cure_chance = random.uniform(item.min_cure, item.max_cure)
                if random.random() < cure_chance:
                    self.infection = 0
                    print("The vaccine worked! Infection cured.")
                else:
                    print("The vaccine had no effect.")
                item.load -= 1
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
