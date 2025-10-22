import pygame
import random
import time
import math

import os
import xml.etree.ElementTree as ET

from config import *
from ui import get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect

ITEM_TEMPLATES = {} # Changed to a dictionary for faster lookups
ZOMBIE_TEMPLATES = []
# --- GAME CLASSES ---

class Item:
    """Base class for all in-game items."""
    def __init__(self, name, item_type, durability=None, load=None, capacity=None, weight=0.0, color=WHITE, ammo_type=None, pellets=1, spread_angle=0, sprite_file=None):
        self.name = name
        self.item_type = item_type # 'consumable', 'weapon', 'tool'
        self.durability = durability
        self.load = load # e.g., ammo count for guns or healing amount for consumables
        self.weight = weight # Weight of the item
        self.capacity = capacity # Max load for weapons or max stack size for consumables
        self.ammo_type = ammo_type # Name of the ammo item this weapon uses
        self.pellets = pellets # For weapons
        self.spread_angle = spread_angle # For weapons
        self.image = self.load_sprite(sprite_file)
        self.rect = pygame.Rect(0, 0, 16, 16)
        # If the item is a container (like a backpack), it has its own inventory
        if self.item_type == 'backpack':
            self.inventory = []
        self.color = color 

    def __repr__(self):
        desc = f"({self.name}"
        if self.durability is not None:
            desc += f", Dur: {self.durability:.0f}"
        if self.load is not None:
            desc += f", Load: {self.load:.0f}"
        if self.capacity is not None:
            desc += f", Cap: {self.capacity:.0f}"
        desc += ")"
        return desc

    def load_sprite(self, sprite_file):
        if not sprite_file:
            return None
        try:
            path = os.path.join('game', 'items', 'sprites', sprite_file)
            image = pygame.image.load(path).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE)) # Scale to TILE_SIZE
            return image
        except pygame.error as e:
            print(f"Warning: Could not load sprite '{sprite_file}': {e}")
            return None

    @staticmethod
    def load_item_templates():
        """Loads item templates from XML files in the /game/items/ directory."""
        global ITEM_TEMPLATES
        if ITEM_TEMPLATES:  # Already loaded
            return

        items_dir = 'game/items'
        if not os.path.isdir(items_dir):
            print(f"Warning: Item templates directory not found at '{items_dir}'")
            return

        for filename in os.listdir(items_dir):
            if filename.endswith('.xml'):
                tree = ET.parse(os.path.join(items_dir, filename))
                root = tree.getroot()
                item_name = root.attrib['name']
                template = {
                    'type': root.attrib['type'],
                    'properties': {},
                }
                for prop in root.find('properties'):
                    template['properties'][prop.tag] = {k: v for k, v in prop.attrib.items()}
                
                spawn_node = root.find('spawn')
                if spawn_node is not None:
                    template['spawn_chance'] = float(spawn_node.attrib['chance'])
                
                ITEM_TEMPLATES[item_name] = template
        print(f"Loaded {len(ITEM_TEMPLATES)} item templates.")

    @staticmethod
    def generate_random():
        """Generates a random item based on game requirements."""
        if not ITEM_TEMPLATES:
            Item.load_item_templates()

        # Filter for items that can be spawned randomly
        spawnable_items = {name: data for name, data in ITEM_TEMPLATES.items() if 'spawn_chance' in data}
        names = list(spawnable_items.keys())
        chances = [item['spawn_chance'] for item in spawnable_items.values()]
        
        chosen_name = random.choices(names, weights=chances, k=1)[0]
        props = spawnable_items[chosen_name]['properties']
        durability = random.uniform(float(props['durability']['min']), float(props['durability']['max'])) if 'durability' in props else None
        
        if 'load' in props and 'min' in props['load']:
            load = random.randint(int(props['load']['min']), int(props['load']['max']))
        else:
            load = float(props['load']['value']) if 'load' in props else None

        capacity = int(props['capacity']['value']) if 'capacity' in props else None
        weight = float(props['weight']['value']) if 'weight' in props else 0.0
        color_prop = props['color']
        color = (int(color_prop['r']), int(color_prop['g']), int(color_prop['b']))
        
        ammo_type = props['ammo']['type'] if 'ammo' in props else None
        
        pellets = 1
        spread_angle = 0
        if 'firing' in props:
            pellets = int(props['firing']['pellets'])
            spread_angle = float(props['firing']['spread_angle'])
        
        sprite_file = props['sprite']['file'] if 'sprite' in props else None

        return Item(chosen_name, spawnable_items[chosen_name]['type'], durability=durability, load=load, capacity=capacity, weight=weight, color=color, ammo_type=ammo_type, pellets=pellets, spread_angle=spread_angle, sprite_file=sprite_file)

    @classmethod
    def create_from_name(cls, item_name):
        """Creates a specific item by its name from the loaded templates."""
        if not ITEM_TEMPLATES:
            cls.load_item_templates()

        if item_name not in ITEM_TEMPLATES:
            print(f"Error: No template found for item '{item_name}'")
            return None

        template = ITEM_TEMPLATES[item_name]
        props = template['properties']

        # For dropped items, we'll use the 'value' or 'max' for properties, not a random range
        durability = float(props['durability']['max']) if 'durability' in props and 'max' in props['durability'] else None
        load = float(props['load']['value']) if 'load' in props and 'value' in props['load'] else None
        capacity = int(props['capacity']['value']) if 'capacity' in props else None
        weight = float(props['weight']['value']) if 'weight' in props else 0.0
        # Use provided weights for specific items
        if item_name == 'Axe': weight = 1.0
        elif item_name == 'Knife': weight = 0.3
        elif 'Ammo' in item_name or 'Shells' in item_name:
            # This is a bit tricky. Let's assume the XML weight is per-box,
            # and we can derive per-bullet weight if needed. For now, let's use a flat value.
            # A better implementation would be weight per bullet * load.
            # For simplicity, let's say the weight in XML is for the full box.
            pass # Keep XML weight
        elif item_name == 'Canned Food': weight = 0.2
        elif item_name == 'Pistol': weight = 0.5
        elif item_name == 'Shotgun': weight = 1.2
        elif item_name == 'Vaccine': weight = 0.1

        color_prop = props.get('color', {'r': '255', 'g': '255', 'b': '255'})
        color = (int(color_prop['r']), int(color_prop['g']), int(color_prop['b']))
        ammo_type = props['ammo']['type'] if 'ammo' in props else None
        pellets = 1
        spread_angle = 0
        if 'firing' in props:
            pellets = int(props['firing']['pellets'])
            spread_angle = float(props['firing']['spread_angle'])
        
        sprite_file = props['sprite']['file'] if 'sprite' in props else None

        return cls(item_name, template['type'], durability=durability, load=load, capacity=capacity, weight=weight, color=color, ammo_type=ammo_type, pellets=pellets, spread_angle=spread_angle, sprite_file=sprite_file)


class Projectile:
    """Represents a bullet fired by the player."""
    def __init__(self, start_x, start_y, target_x, target_y):
        # Coordinates are relative to the central game box (0 to GAME_WIDTH)
        self.x = start_x
        self.y = start_y
        self.rect = pygame.Rect(start_x, start_y, 5, 5)
        self.color = YELLOW
        self.speed = 8 

        # Calculate velocity vector
        dx = target_x - start_x
        dy = target_y - start_y # Corrected from target_y - start_y
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist > 0:
            self.vx = (dx / dist) * self.speed
            self.vy = (dy / dist) * self.speed
        else:
            self.vx = 0
            self.vy = 0

    def update(self):
        """Moves the projectile and returns True if it should be removed."""
        self.x += self.vx
        self.y += self.vy # Corrected from self.y += self.vy
        self.rect.topleft = (int(self.x), int(self.y))
        
        # Check if out of game box bounds
        if self.x < 0 or self.x > GAME_WIDTH or self.y < 0 or self.y > GAME_HEIGHT:
             return True
        return False

    def draw(self, surface):
        """Draws the projectile with the game offset applied."""
        draw_center = (int(self.x) + GAME_OFFSET_X, int(self.y))
        # Draw a sharp yellow square/circle for bullet visualization
        pygame.draw.circle(surface, self.color, draw_center, 5) 
        
class Player:
    def __init__(self, player_data=None):
        # Coordinates are relative to the central game box
        self.x = GAME_WIDTH // 2
        self.y = GAME_HEIGHT // 2
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.color = BLUE

        # --- Stats & Skills ---
        # Use provided data or set defaults
        data = player_data or {}
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

        # --- Experience & Leveling ---
        self.level = data.get('level', 1)
        self.experience = data.get('experience', 0)
        self.base_inventory_slots = 5 # The player has 5 base inventory slots
        
        # Animation Timers (frames remaining)
        self.melee_swing_timer = 0
        self.gun_flash_timer = 0
        self.melee_swing_angle = 0 # Angle for the melee swing animation

        self.drop_cooldown = 0

        # Reloading state
        self.is_reloading = False
        self.reload_timer = 0
        self.reload_duration = 120 # 2 seconds at 60 FPS
        self.max_carry_weight = self.get_max_carry_weight() # Initialize max carry weight

        self.image = self._load_sprite(data.get('visuals', {}).get('sprite'))

    def _load_sprite(self, sprite_path):
        if not sprite_path: return None
        try:
            return pygame.image.load(sprite_path).convert_alpha()
        except pygame.error as e:
            print(f"Warning: Could not load player sprite '{sprite_path}': {e}")
            return None

    def update_position(self, dx, dy, obstacles, zombies):
        """Move player and keep within game box bounds."""
        # Store original dx, dy
        original_dx, original_dy = dx, dy

        # Now apply movement and check for hard obstacles (walls)
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Create a temporary rect for collision checking
        temp_rect = self.rect.copy()

        # Move in X direction and check for collisions with walls
        temp_rect.x = new_x
        collided_with_wall_x = any(temp_rect.colliderect(ob) for ob in obstacles)

        if not collided_with_wall_x:
            self.x = new_x
        
        # Move in Y direction and check for collisions with walls
        temp_rect.y = new_y
        collided_with_wall_y = any(temp_rect.colliderect(ob) for ob in obstacles)

        if not collided_with_wall_y:
            self.y = new_y

        # Ensure player stays within game bounds
        self.x = max(0, min(self.x, GAME_WIDTH - TILE_SIZE))
        self.y = max(0, min(self.y, GAME_HEIGHT - TILE_SIZE))
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, surface):
        """Draws the player and the melee swing animation."""
        
        # 1. Draw Player
        draw_rect = self.rect.move(GAME_OFFSET_X, 0)
        if self.image:
            surface.blit(self.image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)

        # 2. Draw Melee Swing Animation
        if self.melee_swing_timer > 0:
            swing_radius = TILE_SIZE * 1.5
            swing_color = YELLOW
            swing_thickness = 3
            
            # Center for the swing arc (at player's center)
            center_x = self.x + TILE_SIZE // 2 + GAME_OFFSET_X
            center_y = self.y + TILE_SIZE // 2
            
            # Define the arc of the swing (e.g., 90 degrees wide)
            start_angle = self.melee_swing_angle - math.radians(45)
            end_angle = self.melee_swing_angle + math.radians(45)
            
            pygame.draw.arc(surface, swing_color, 
                            (center_x - swing_radius, center_y - swing_radius, swing_radius * 2, swing_radius * 2), 
                            start_angle, end_angle, swing_thickness)
            
            self.melee_swing_timer -= 1

        # 3. Draw Reloading Bar
        if self.is_reloading:
            progress = 1.0 - (self.reload_timer / self.reload_duration)
            bar_width = int(TILE_SIZE * 2 * progress)
            bar_rect = pygame.Rect(draw_rect.left - TILE_SIZE // 2, draw_rect.top - 10, bar_width, 5)
            bg_bar_rect = pygame.Rect(draw_rect.left - TILE_SIZE // 2, draw_rect.top - 10, TILE_SIZE * 2, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)
            pygame.draw.rect(surface, YELLOW, bar_rect)

    def update_stats(self):
        """Handle resource decay and health checks."""
        current_time = time.time()
        is_moving = pygame.key.get_pressed()[pygame.K_w] or \
                    pygame.key.get_pressed()[pygame.K_s] or \
                    pygame.key.get_pressed()[pygame.K_a] or \
                    pygame.key.get_pressed()[pygame.K_d]

        # Stamina logic
        if is_moving and self.stamina > 0:
            self.stamina = max(0, self.stamina - 0.2) # Stamina drain from running
        elif not is_moving and self.stamina < self.max_stamina:
            self.stamina = min(self.max_stamina, self.stamina + 0.3) # Stamina regen when still

        if current_time - self.last_decay_time >= DECAY_RATE_SECONDS:
            # Resource Decay
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

        # Reloading timer
        if self.is_reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self._finish_reload()

        if self.health <= 0:
            print("GAME OVER: Health depleted!")
            return True 

        if self.drop_cooldown > 0: self.drop_cooldown -= 1

        if self.health <= 0:
            print("GAME OVER: Health depleted!")
            return True 
        return False

    def get_total_inventory_slots(self):
        """Calculates total inventory slots based on base slots and equipped backpack."""
        if self.backpack:
            return self.base_inventory_slots + self.backpack.capacity
        return self.base_inventory_slots

    def get_inventory_weight(self):
        """Calculates the total weight of all items in the inventory and belt."""
        total_weight = 0
        for item in self.inventory + self.belt:
            if item:
                total_weight += getattr(item, 'weight', 0)
        if self.backpack:
            total_weight += getattr(self.backpack, 'weight', 0)
            # Add weight of items inside the backpack
            for item in self.backpack.inventory:
                total_weight += getattr(item, 'weight', 0)
        return total_weight

    def get_max_carry_weight(self):
        """Calculates the maximum weight the player can carry."""
        # Base carry weight + bonus from strength
        base_carry = 15
        strength_bonus = self.skill_strength * 2
        return base_carry + strength_bonus

    def find_consumable_at_mouse(self, mouse_pos):
        """Checks if the mouse is over a consumable item in the inventory."""
        for i, item in enumerate(self.inventory):
            if item and item.item_type == 'consumable':
                # We need to get the rect for the inventory slot to check for collision
                slot_rect = get_inventory_slot_rect(i)
                if slot_rect.collidepoint(mouse_pos):
                    return item, i
        return None, None

    def find_item_at_mouse(self, mouse_pos):
        """Checks if the mouse is over an item in the inventory or belt."""
        # Check inventory first
        for i, item in enumerate(self.inventory):
            if item:
                slot_rect = get_inventory_slot_rect(i)
                if slot_rect.collidepoint(mouse_pos):
                    return item, 'inventory', i
        # Then check belt
        for i, item in enumerate(self.belt):
            if item:
                slot_rect = get_belt_slot_rect_in_modal(i)
                if slot_rect.collidepoint(mouse_pos):
                    return item, 'belt', i
        # Then check backpack slot
        if self.backpack:
            slot_rect = get_backpack_slot_rect()
            if slot_rect.collidepoint(mouse_pos):
                return self.backpack, 'backpack', 0
        return None, None, None

    def find_matching_ammo(self, weapon):
        """Searches inventory and belt for the required ammo type."""
        if not weapon or not weapon.ammo_type:
            return None, None, None
        
        ammo_type_needed = weapon.ammo_type
        
        # Combine items from belt and inventory for easy search
        search_list = [(item, 'belt', i) for i, item in enumerate(self.belt) if item and item.item_type == 'consumable']
        search_list.extend([(item, 'inventory', i) for i, item in enumerate(self.inventory) if item and item.item_type == 'consumable'])
        
        for item, source_type, index in search_list:
            if item.load is not None and item.name == ammo_type_needed and item.load > 0:
                return item, source_type, index
        
        return None, None, None


    def reload_active_weapon(self):
        """Handles reloading the active gun with matching ammo from inventory/belt (triggered by 'R' or belt use)."""
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
        
        # Start the reload timer
        self.is_reloading = True
        self.reload_timer = self.reload_duration
        print(f"Reloading {weapon.name}...")

    def _finish_reload(self):
        """Called when the reload timer finishes. Transfers the ammo."""
        self.is_reloading = False
        weapon = self.active_weapon
        if not weapon: return

        ammo_item, source_type, index = self.find_matching_ammo(weapon)
        if not ammo_item: return # Ammo might have been dropped during reload

        needed = weapon.capacity - weapon.load
        # Since ammo_item.load is guaranteed to be not None by find_matching_ammo, we can use it directly
        available = ammo_item.load

        transfer_amount = min(needed, available)

        if transfer_amount > 0:
            weapon.load += transfer_amount
            ammo_item.load -= transfer_amount
            print(f"Finished reloading. Load: {weapon.load:.0f}/{weapon.capacity:.0f}.")
            
            # Clean up empty ammo stack/box
            if ammo_item.load <= 0:
                print(f"Used up all {ammo_item.name}!")
                if source_type == 'inventory':
                    # Need to check if item is still in the inventory (it might have been swapped or moved during the check)
                    try:
                        self.inventory.remove(ammo_item)
                    except ValueError:
                        pass # Already removed or moved
                elif source_type == 'belt':
                    self.belt[index] = None
    
    def get_item_context_options(self, item):
        """Returns a list of context menu options for a given item."""
        options = []
        if item.item_type == 'consumable':
            if 'Ammo' in item.name or 'Shells' in item.name:
                options.append('Reload')
            else:
                options.append('Use')
            options.append('Equip')
        elif item.item_type == 'backpack':
            options.append('Open')
            if not self.backpack: # Can only equip if slot is empty
                options.append('Equip')
        elif item.item_type in ['weapon', 'tool']:
            options.append('Equip')
        
        options.append('Drop')
        return options

    def _get_source_inventory(self, source_type, container_item=None):
        """Helper to get the correct inventory list based on source."""
        if source_type == 'inventory':
            return self.inventory
        elif source_type == 'belt':
            return self.belt
        elif source_type == 'container' and container_item:
            return container_item.inventory
        return None

    def equip_item_to_belt(self, item, source_type, item_index, container_item=None):
        """Moves an item from inventory or a container to an empty belt slot."""
        if not any(slot is None for slot in self.belt):
            print("Belt is full.")
            return False

        source_inventory = self._get_source_inventory(source_type, container_item)
        if source_inventory is None or item not in source_inventory:
            return False # Item not found

        # Find first empty slot and place it
        for i, slot in enumerate(self.belt):
            if slot is None:
                self.belt[i] = item
                source_inventory.pop(item_index)
                print(f"Equipped {item.name} to belt.")
                return True
        return False

    def consume_item(self, item, source_type, item_index, container_item=None):
        """Uses a consumable item from the inventory or belt."""
        source_inventory = self._get_source_inventory(source_type, container_item)
        if item.item_type == 'consumable':
            amount_consumed = 0
            if 'Water' in item.name:
                amount_needed = 100 - self.water
                amount_to_consume = min(amount_needed, item.load)
                self.water = min(100, self.water + amount_to_consume)
                self.stamina = min(self.max_stamina, self.stamina + (amount_to_consume / item.capacity) * 25) # Scale stamina regen
                item.load -= amount_to_consume
                amount_consumed = amount_to_consume
                print(f"Consumed {amount_consumed:.0f}% Water. Water: {self.water:.0f}%")
            elif 'Food' in item.name:
                amount_needed = 100 - self.food
                amount_to_consume = min(amount_needed, item.load)
                self.food = min(100, self.food + amount_to_consume)
                item.load -= amount_to_consume
                amount_consumed = amount_to_consume
                print(f"Consumed {amount_consumed:.0f}% Food. Food: {self.food:.0f}%")
            elif 'Vaccine' in item.name:
                amount_needed = self.infection # Amount of infection to cure
                amount_to_consume = min(amount_needed, item.load) # Use up to item's load
                self.infection = max(0, self.infection - amount_to_consume)
                item.load -= amount_to_consume
                amount_consumed = amount_to_consume
                print(f"Used {amount_consumed:.0f}% Vaccine. New Infection: {self.infection:.0f}%")
            elif 'Ammo' in item.name or 'Shells' in item.name:
                # If ammo is used from the belt, it attempts to reload the active weapon
                self.reload_active_weapon()
                return True # Don't remove the item, reload handles it
            
            # Only remove the item if its load is completely depleted
            if item.load <= 0:
                if source_type == 'belt':
                    self.belt[item_index] = None
                elif source_type == 'inventory':
                    if item_index < len(self.inventory) and self.inventory[item_index] == item:
                        self.inventory.pop(item_index)
            
            return True
        return False
    
    def drop_item(self, source, index, container_item=None):
        """Removes an item from inventory/belt and returns it."""
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

class Zombie:
    def __init__(self, x, y, template):
        # Coordinates are relative to the central game box
        self.x = x
        self.y = y
        
        # Load stats from template
        self.name = template['name']
        self.max_health = template['health']
        self.health = template['health']
        self.speed = template['speed'] 
        self.loot_table = template['loot']
        self.xp_value = template.get('xp', 10) # Default to 10 if not in template
        
        self.image = self.load_sprite(template['sprite'])
        self.color = RED # Fallback color if no sprite

        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.show_health_bar_timer = 0
        self.last_attack_time = 0 # Initialize for attack cooldown
        self.attack_range = TILE_SIZE * 1.5 # Increased attack range
        self.attack_range = TILE_SIZE * 1.5 # Increased attack range

    @staticmethod
    def load_zombie_templates():
        """Loads zombie templates from XML files in the /game/zombies/ directory."""
        global ZOMBIE_TEMPLATES
        if ZOMBIE_TEMPLATES: # Already loaded
            return

        zombies_dir = 'game/zombies'
        if not os.path.exists(zombies_dir):
            print(f"Warning: Zombie templates directory not found at '{zombies_dir}'")
            return

        for filename in os.listdir(zombies_dir):
            if filename.endswith('.xml'):
                tree = ET.parse(os.path.join(zombies_dir, filename))
                root = tree.getroot()
                template = {
                    'name': root.attrib['name'],
                    'health': float(root.find('stats/health').attrib['value']),
                    'speed': float(root.find('stats/speed').attrib['value']) * ZOMBIE_SPEED,
                    'sprite': root.find('visuals/sprite').attrib['file'],
                    'loot': [],
                    'xp': int(root.find('stats/xp').attrib['value']) if root.find('stats/xp') is not None else 10
                }
                for drop in root.findall('loot/drop'):
                    template['loot'].append({
                        'item': drop.attrib['item'],
                        'chance': float(drop.attrib['chance']) * ZOMBIE_DROP
                    })
                ZOMBIE_TEMPLATES.append(template)
        print(f"Loaded {len(ZOMBIE_TEMPLATES)} zombie templates.")

    @staticmethod
    def create_random(x, y):
        """Creates a random type of zombie at the given coordinates."""
        if not ZOMBIE_TEMPLATES:
            Zombie.load_zombie_templates()
        
        if not ZOMBIE_TEMPLATES:
            raise Exception("No zombie templates loaded! Cannot create zombies.")

        chosen_template = random.choice(ZOMBIE_TEMPLATES)
        return Zombie(x, y, chosen_template)

    def load_sprite(self, sprite_file):
        if not sprite_file: return None
        try:
            path = os.path.join('game', 'zombies', 'sprites', sprite_file)
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            print(f"Warning: Could not load zombie sprite '{sprite_file}': {e}")
            return None

    def draw(self, surface):
        """Draws the zombie with the game offset applied."""
        draw_rect = self.rect.move(GAME_OFFSET_X, 0) # This is a rect on the virtual screen
        if self.image:
            surface.blit(self.image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)

        # Draw health bar if recently hit
        if self.show_health_bar_timer > 0:
            # Background of the health bar (the empty part)
            bg_bar_rect = pygame.Rect(draw_rect.left, draw_rect.top - 10, TILE_SIZE, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)

            # Current health
            health_percentage = self.health / self.max_health
            health_bar_width = int(health_percentage * TILE_SIZE)
            health_bar_rect = pygame.Rect(draw_rect.left, draw_rect.top - 10, health_bar_width, 5)
            pygame.draw.rect(surface, GREEN, health_bar_rect)

            self.show_health_bar_timer -= 1

    def move_towards(self, target_rect, obstacles, other_zombies):
        """Simple movement toward the player, avoiding obstacles and other zombies."""
        dx = target_rect.x - self.x
        dy = target_rect.y - self.y
        dist = math.sqrt(dx**2 + dy**2)

        if dist > 0:
            # If already overlapping player, try to push out
            if self.rect.colliderect(target_rect):
                overlap_x = min(self.rect.right, target_rect.right) - max(self.rect.left, target_rect.left)
                overlap_y = min(self.rect.bottom, target_rect.bottom) - max(self.rect.top, target_rect.top)

                if overlap_x > 0 and overlap_y > 0: # Only push if there's actual overlap
                    if overlap_x < overlap_y: # Overlap is smaller in X, push in X
                        if self.rect.centerx < target_rect.centerx: # Zombie is to the left of player
                            self.x -= overlap_x
                        else:
                            self.x += overlap_x
                    else: # Overlap is smaller in Y, push in Y
                        if self.rect.centery < target_rect.centery: # Zombie is above player
                            self.y -= overlap_y
                        else:
                            self.y += overlap_y
                    self.rect.topleft = (int(self.x), int(self.y))

            move_x = (dx / dist) * self.speed
            move_y = (dy / dist) * self.speed
            
            separation_x, separation_y = 0, 0
            SEPARATION_RADIUS = TILE_SIZE # Zombies try to keep this distance
            SEPARATION_FORCE = 0.5 # How strongly they repel

            # Separate from other zombies
            for other_z in other_zombies:
                if other_z is self: continue
                dist_sq = (self.x - other_z.x)**2 + (self.y - other_z.y)**2
                if dist_sq < SEPARATION_RADIUS**2 and dist_sq > 0:
                    dist_val = math.sqrt(dist_sq)
                    # Vector pointing from other_z to self
                    repel_x = (self.x - other_z.x) / dist_val
                    repel_y = (self.y - other_z.y) / dist_val
                    separation_x += repel_x * (SEPARATION_RADIUS - dist_val) * SEPARATION_FORCE
                    separation_y += repel_y * (SEPARATION_RADIUS - dist_val) * SEPARATION_FORCE

            # Separate from player
            dist_sq_player = (self.x - target_rect.x)**2 + (self.y - target_rect.y)**2
            if dist_sq_player < SEPARATION_RADIUS**2 and dist_sq_player > 0:
                dist_player = math.sqrt(dist_sq_player)
                repel_x_player = (self.x - target_rect.x) / dist_player
                repel_y_player = (self.y - target_rect.y) / dist_player
                separation_x += repel_x_player * (SEPARATION_RADIUS - dist_player) * SEPARATION_FORCE
                separation_y += repel_y_player * (SEPARATION_RADIUS - dist_player) * SEPARATION_FORCE

            # Apply separation to movement
            move_x += separation_x
            move_y += separation_y
            
            # Store current position
            old_x, old_y = self.x, self.y
            # Attempt X movement
            self.x += move_x
            self.rect.x = int(self.x) # Update rect for collision check

            # Check for collisions after X movement
            collided_x = any(self.rect.colliderect(ob) for ob in obstacles) or \
                         any(self.rect.colliderect(z.rect) for z in other_zombies if z is not self) or \
                         self.rect.colliderect(target_rect) # target_rect is player

            if collided_x:
                self.x = old_x # Revert X movement if collision
                self.rect.x = int(self.x)

            # Attempt Y movement
            self.y += move_y
            self.rect.y = int(self.y) # Update rect for collision check

            # Check for collisions after Y movement
            collided_y = any(self.rect.colliderect(ob) for ob in obstacles) or \
                         any(self.rect.colliderect(z.rect) for z in other_zombies if z is not self) or \
                         self.rect.colliderect(target_rect) # target_rect is player

            if collided_y:
                self.y = old_y # Revert Y movement if collision
                self.rect.y = int(self.y)

            self.rect.topleft = (int(self.x), int(self.y))

    def attack(self, player):
        """Zombie attacks the player, potentially infecting them."""
        # ... (Attack logic remains the same)
        body_parts = {"Head": (0.50, 0.20), "Body": (0.35, 0.25), "Arms": (0.30, 0.25), "Legs": (0.20, 0.15), "Feet": (0.10, 0.15)}
        part_names = list(body_parts.keys())
        weights = [p[0] for p in body_parts.values()]
        
        hit_part = random.choices(part_names, weights, k=1)[0]
        inf_chance, dmg_mult = body_parts[hit_part]
        
        damage = 5 * dmg_mult 
        player.health -= damage
        player.health = max(0, player.health)
        
        if random.random() < inf_chance:
            infection_amount = 15 # Increased infection amount
            player.infection = min(100, player.infection + infection_amount)
            print(f"**HIT!** Player hit on {hit_part}. Took {damage:.1f} damage and gained {infection_amount}% infection!")
        else:
            print(f"Player hit on {hit_part}. Took {damage:.1f} damage (no infection).")

    def take_damage(self, damage):
        self.health -= damage
        self.show_health_bar_timer = 120 # Show health bar for 2 seconds (120 frames)
        if self.health <= 0:
            print("Zombie eliminated.")
            return True
        return False