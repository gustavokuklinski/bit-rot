import time
import pygame
import os
import random
import math

from data.config import *
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.entities.player.player_progression import PlayerProgression
from core.ui.inventory import get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect, get_invcontainer_slot_rect
from core.messages import display_message
from core.placement import find_free_tile

class Player:
    def __init__(self, player_data=None):
        self.x = GAME_WIDTH // 2
        self.y = GAME_HEIGHT // 2
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.vx = 0
        self.vy = 0
        self.is_running = False
        self.color = BLUE

        data = player_data or {}
        stats = data.get('stats', {})
        self.progression = PlayerProgression(data)

        # Stats
        self.name = data.get('name', "Player")
        self.profession = data.get('profession', "Survivor")
        self.max_health = stats.get('health', 100.0)
        self.health = stats.get('health', self.max_health)
        self.water = stats.get('water', 100.0)
        self.food = stats.get('food', 100.0)
        self.infection = stats.get('infection', 0.0)
        self.max_stamina = stats.get('stamina', 100.0)
        self.stamina = stats.get('stamina', self.max_stamina)
        self.anxiety = stats.get('anxiety', 0.0)
        self.tireness = stats.get('tireness', 0.0)

        self.sex = data.get('sex', 'Male')
        self.traits = data.get('traits', [])

        self.inventory = []
        self.backpack = None
        self.invcontainer = None
        self.active_weapon = None
        self.belt = [None] * 5
        self.last_decay_time = time.time()
        self.base_inventory_slots = 5

        self.clothes_slots =  ['head','legs', 'feet',  'torso' ,'body', 'hands']
        self.clothes = {slot: None for slot in self.clothes_slots}
        
        # Load clothes from player_data
        chosen_clothes_dict = data.get('clothes', {})
        for slot, item_name in chosen_clothes_dict.items():
            if item_name and item_name != "None" and slot in self.clothes_slots:
                # Create the item instance for the chosen clothing
                self.clothes[slot] = Item.create_from_name(item_name)

        # animation / action timers
        self.melee_swing_timer = 0
        self.gun_flash_timer = 0
        self.melee_swing_angle = 0
        self.drop_cooldown = 0

        self.is_reloading = False
        self.reload_timer = 0
        self.reload_duration = 120

        self.image = self._load_sprite(data.get('visuals', {}).get('sprite'))

        self.layer_switch_cooldown = 0
        self.aim_angle = 0
        self.facing_direction = (0, 1)

    def _load_sprite(self, sprite_path):
        if not sprite_path: return None
        try:
            image = pygame.image.load(SPRITE_PATH + sprite_path).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
            return image
        except pygame.error as e:
            print(f"Warning: Could not load player sprite '{sprite_path}': {e}")
            return None

    def get_total_defence(self):
        """Calculates the total defence value from all equipped clothes."""
        total_defence = 0
        for item in self.clothes.values():
            if item and hasattr(item, 'defence') and item.defence is not None:
                # Only add defence if the item is not broken
                if hasattr(item, 'durability') and item.durability is not None and item.durability > 0:
                    total_defence += item.defence
                # Also count items that don't have durability
                elif not hasattr(item, 'durability') or item.durability is None:
                     total_defence += item.defence
        return total_defence

    def take_durability_damage(self, raw_damage, game):
        """Applies durability damage to a random piece of equipped gear."""
        # Find all clothes that have durability
        worn_clothes = [item for item in self.clothes.values() if item and hasattr(item, 'durability') and item.durability is not None and item.durability > 0]
        
        if not worn_clothes:
            return # No clothes to damage

        # Pick one random piece to take the hit
        item_hit = random.choice(worn_clothes)
        
        # Calculate durability damage (e.g., 25% of raw attack damage)
        # This can be tuned for balance
        dur_damage = raw_damage * 0.25 
        
        if dur_damage > 0:
            item_hit.durability = max(0, item_hit.durability - dur_damage)

            if item_hit.durability <= 0:
                # Find the slot this item was in and remove it
                slot_to_clear = None
                for slot, item in self.clothes.items():
                    if item == item_hit:
                        slot_to_clear = slot
                        break
                
                if slot_to_clear:
                    self.clothes[slot_to_clear] = None
                    display_message(game, f"Your {item_hit.name} broke!")


    def process_kill(self, weapon, zombie):
        self.progression.process_kill(self, weapon, zombie)

    def update_position(self, obstacles, zombies):
        # Move on X axis first
        self.x += self.vx
        self.rect.x = round(self.x)

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
        self.rect.y = round(self.y)

        # Check for Y-axis collisions with obstacles
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if self.vy > 0:  # Moving down
                    self.rect.bottom = obstacle.top
                elif self.vy < 0:  # Moving up
                    self.rect.top = obstacle.bottom
                self.y = self.rect.y

    def draw(self, surface, offset_x, offset_y, is_aiming=False):
        draw_rect = self.rect.move(offset_x, offset_y)
        
        if self.image:
            surface.blit(self.image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)

        for slot in self.clothes_slots: # Draw in order
            item = self.clothes.get(slot)
            if item and item.image:
                surface.blit(item.image, draw_rect)


        if is_aiming and self.active_weapon and self.active_weapon.image and \
           self.active_weapon.item_type == 'weapon_ranged':
            # 1. Get the original weapon image
            original_image = self.active_weapon.image
            
            # 2. Rotate the image
            angle_degrees = math.degrees(self.aim_angle)
            rotated_image = pygame.transform.rotate(original_image, angle_degrees)
            
            # 3. Get the rect of the rotated image, centered at the player's draw center
            rotated_rect = rotated_image.get_rect(center=draw_rect.center)
            
            # 4. Offset the rect so it looks "held"
            # We use the angle to push it outwards from the center
            offset_radius = TILE_SIZE * 0.8 # How far from the center
            offset_x_weapon = math.cos(self.aim_angle) * offset_radius
            offset_y_weapon = -math.sin(self.aim_angle) * offset_radius # -sin because pygame Y is inverted
            
            rotated_rect.centerx += offset_x_weapon
            rotated_rect.centery += offset_y_weapon

            # 5. Blit it
            surface.blit(rotated_image, rotated_rect)


        # Melee arc
        if self.melee_swing_timer > 0:
            if self.active_weapon and self.active_weapon.image and \
               self.active_weapon.item_type in ['weapon_melee', 'tool']:
            # [END MODIFICATION]
                
                # 1. Get the original weapon image
                original_image = self.active_weapon.image
                
                # 2. Rotate the image (use melee_swing_angle, negate for pygame)
                angle_degrees = math.degrees(self.melee_swing_angle)
                rotated_image = pygame.transform.rotate(original_image, angle_degrees) # Negate angle
                
                # 3. Get the rect, centered at the player's draw center
                rotated_rect = rotated_image.get_rect(center=draw_rect.center)
                
                # 4. Offset the rect
                offset_radius = TILE_SIZE * 0.8 
                offset_x_weapon = math.cos(self.melee_swing_angle) * offset_radius
                offset_y_weapon = -math.sin(self.melee_swing_angle) * offset_radius
                
                rotated_rect.centerx += offset_x_weapon
                rotated_rect.centery += offset_y_weapon
                
                # 5. Blit it
                surface.blit(rotated_image, rotated_rect)

            swing_radius = TILE_SIZE * 0.7
            center_x, center_y = draw_rect.center
            start_angle = self.melee_swing_angle - (3.1415 / 4)
            end_angle = self.melee_swing_angle + (3.1415 / 4)
            arc_bounds = pygame.Rect(center_x - swing_radius, center_y - swing_radius, swing_radius * 2, swing_radius * 2)
            pygame.draw.arc(surface, YELLOW, arc_bounds, start_angle, end_angle, 1)
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

    def update_stats(self, game):
        

        current_time = time.time()
        keys = pygame.key.get_pressed()
        is_moving = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]

        self.progression.update(self, is_moving, game)

        if current_time - self.last_decay_time >= DECAY_RATE_SECONDS:
            self.water = max(0, self.water - WATER_DECAY_AMOUNT)
            self.food = max(0, self.food - FOOD_DECAY_AMOUNT)
            self.last_decay_time = current_time
            if self.water <= 0 or self.food <= 0:
                self.health -= 5.0 * (1 if self.water <= 0 else 0) + 5.0 * (1 if self.food <= 0 else 0)
                self.health = max(0, self.health)

            if AUTO_DRINK and self.water <= AUTO_DRINK_THRESHOLD:
                print(f"Water level {self.water} <= threshold {AUTO_DRINK_THRESHOLD}. Attempting auto-drink.") # Debug print
                water_item, source, index, container = self.find_water_to_auto_drink()
                if water_item:
                    print(f"Auto-consuming {water_item.name} from {source} index {index}") # Debug print
                    self.consume_item(water_item, source, index, container)
        
        all_inventories = [self.belt, self.inventory]
        if self.backpack:
            all_inventories.append(self.backpack.inventory)
            
        if self.invcontainer and hasattr(self.invcontainer, 'inventory'):
             all_inventories.append(self.invcontainer.inventory)

        for inv in all_inventories:
            for item in inv:
                # Use getattr for safety
                if getattr(item, 'state', 'off') == 'on':
                    if item.durability is not None:
                        item.durability -= 0.05 # Adjust this value for consumption rate
                        if item.durability <= 0:
                            item.durability = 0
                            # Item is out of fuel/broken, turn it off
                            self.toggle_utility_item(item, None, None, None) # Pass None source to just toggle

        if self.is_reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self._finish_reload()


        for item in self.inventory:
            if item and item.item_type == 'skill' and item.skill_stats:
                for stat_name, value in item.skill_stats.items():
                    # Set the player's stat directly
                    # This will overwrite current values with the buff
                    # e.g., self.anxiety = 0.0, self.health = 100.0
                    setattr(self, stat_name, value)


        if self.health <= 1:
            print("GAME OVER: Health depleted!")
            return True
        if self.infection >= 100:
            print("GAME OVER: Zombified!")
            return True

        if self.drop_cooldown > 0:
            self.drop_cooldown -= 1
        
        if self.layer_switch_cooldown > 0:
            self.layer_switch_cooldown -= 1

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
        if self.invcontainer:
            slot_rect = get_invcontainer_slot_rect()
            if slot_rect.collidepoint(mouse_pos):
                return self.invcontainer, 'invcontainer', 0

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

    def find_fuel(self, fuel_name):
        """Searches all inventories for a fuel item (like 'Matches')."""
        if not fuel_name:
            return None, None, None, None
            
        # 1. Search Belt
        for i, item in enumerate(self.belt):
            if item and item.name == fuel_name and getattr(item, 'load', 0) > 0:
                return item, 'belt', i, None

        # 2. Search Inventory
        for i, item in enumerate(self.inventory):
            if item and item.name == fuel_name and getattr(item, 'load', 0) > 0:
                return item, 'inventory', i, None
        
        # 3. Search Backpack (if exists)
        if self.backpack and hasattr(self.backpack, 'inventory'):
            for i, item in enumerate(self.backpack.inventory):
                if item and item.name == fuel_name and getattr(item, 'load', 0) > 0:
                    return item, 'container', i, self.backpack
                    
        # 4. Search attached container
        if self.invcontainer and hasattr(self.invcontainer, 'inventory'):
            for i, item in enumerate(self.invcontainer.inventory):
                 if item and item.name == fuel_name and getattr(item, 'load', 0) > 0:
                    return item, 'container', i, self.invcontainer

        return None, None, None, None


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

    def get_item_context_options(self, item, source, container_item=None):
        options = []
        if isinstance(item, Corpse):
            options.append('Open')
            return options

        if item.item_type == 'text':
            options.append('Read')
            if hasattr(item, 'is_stackable') and item.is_stackable():
                 # This logic probably won't apply to text items, but good to keep
                options.append('Drop one')
                if item.load > 1:
                    options.append('Drop all')
            else:
                options.append('Drop')
            return options # Return immediately

        #if item.item_type == 'consumable':
        #    if 'Ammo' in item.name or 'Shells' in item.name:
        #        options.append('Reload')
        #    else:
        #        options.append('Use')
        #    options.append('Equip')

        if item.item_type == 'consumable':
            if 'Ammo' in item.name or 'Shells' in item.name:
                options.append('Reload') # This is for guns
            else:
                options.append('Use')
            options.append('Equip')
        elif item.item_type in ['utility', 'mobile']:
            if item.state == 'on':
                options.append('Turn off')
            elif item.state == 'off':
                options.append('Turn on')
            if item.fuel_type:
                options.append('Reload') # This is for lanterns
            if item.item_type == 'mobile': # Check for mobile
                options.append('Open')
            options.append('Equip')

        elif item.item_type == 'backpack':
            options.append('Open')
            if not self.backpack:
                options.append('Equip')
        elif item.item_type in ['weapon_melee', 'weapon_ranged', 'tool']:
            options.append('Equip')
        elif item.item_type == 'container':
            options.append('Open')

        if hasattr(item, 'is_stackable') and item.is_stackable() and item.load is not None:
            options.append('Drop one')
            if item.load > 1:
                options.append('Drop all')
            
            # 1. Check if item is NOT in Backpack, and we have one
            if self.backpack and container_item is not self.backpack:
                options.append('Send all to Backpack')
            
            # 2. Check if item is NOT in Utility, and we have one
            if self.invcontainer and container_item is not self.invcontainer and source != 'invcontainer':
                 options.append('Send all to Utility')

            # 3. Check if item is NOT in main inventory
            if source != 'inventory':
                options.append('Send all to Inventory')

        else:
            # Not stackable, add normal 'Drop'
            options.append('Drop')
        return options

    def _get_source_inventory(self, source_type, container_item=None):
        if source_type == 'inventory':
            return self.inventory
        elif source_type == 'belt':
            return self.belt
        elif source_type == 'invcontainer':
            return [self.invcontainer] if self.invcontainer else []
        elif (source_type == 'container' or source_type == 'nearby') and container_item:
            return container_item.inventory
        return None

    def equip_item_to_belt(self, item, source_type, item_index, container_item=None):
        if not any(slot is None for slot in self.belt):
            print("Belt is full.")
            return False
        source_inventory = self._get_source_inventory(source_type, container_item)
        if source_inventory is None:
             print(f"Error: Could not find source inventory for {source_type}")
             return False

        if item not in source_inventory:
             # Handle special case where item is 'invcontainer' itself
            if source_type == 'invcontainer' and item == self.invcontainer:
                 for i, slot in enumerate(self.belt):
                    if slot is None:
                        self.belt[i] = item
                        self.invcontainer = None # Unequip from slot
                        print(f"Equipped {item.name} to belt.")
                        return True
            print(f"Error: Item {item.name} not found in source {source_type}")
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
        if not item.item_type == 'consumable':
            return False

        if item.load <= 0:
            print(f"Cannot use {item.name}, it is empty.")
            return False

        status_effect = getattr(item, 'status_effect', None)
        ammo_type = getattr(item, 'ammo_type', None) # Keep this for reload logic
        consumed = False

        if status_effect == 'ammo' or ammo_type is not None:
            # Item is ammo, trigger a reload
            self.reload_active_weapon()
            return True # Return early, reload handles its own logic

        elif status_effect == 'infection':
            # Item is a cure (Vaccine)
            if item.min_cure is not None:
                cure_chance = random.uniform(item.min_cure, item.max_cure)
                if random.random() < (cure_chance / 100.0): # Assuming 1-100
                    self.infection = 0
                    print("The vaccine worked! Infection cured.")
                else:
                    print("The vaccine had no effect.")
                consumed = True
        
        elif status_effect is not None and hasattr(self, status_effect):
            stat_name = status_effect
            current_val = getattr(self, stat_name)

            # Check for RESTORE (increase stat)
            # This assumes your Item class has min_restore and max_restore
            if hasattr(item, 'min_restore') and hasattr(item, 'max_restore') and item.min_restore is not None:
                amount = random.randint(item.min_restore, item.max_restore)
                
                max_val = 100.0
                if stat_name == 'health':
                    max_val = self.max_health
                
                new_val = min(max_val, current_val + amount) # Add to stat
                setattr(self, stat_name, new_val)
                
                print(f"Used {item.name}. Restored {amount} {stat_name.capitalize()}.")
                consumed = True

            # Check for REDUCE (decrease stat)
            # This assumes your Item class can also have min_reduce and max_reduce
            elif hasattr(item, 'min_reduce') and hasattr(item, 'max_reduce') and item.min_reduce is not None:
                amount = random.randint(item.min_reduce, item.max_reduce)
                
                min_val = 0.0 # Stats shouldn't go below zero
                
                new_val = max(min_val, current_val - amount) # Subtract from stat
                setattr(self, stat_name, new_val)
                
                print(f"Used {item.name}. Reduced {stat_name.capitalize()} by {amount}.")
                consumed = True
            
            else:
                # Item has a status but neither restore nor reduce properties
                print(f"Cannot consume {item.name}: misconfigured item (status='{status_effect}' has no restore/reduce properties).")
                return False
        
        else:
            print(f"Cannot consume {item.name}: unknown or misconfigured item (status='{status_effect}').")
            return False

        # If consumed, decrement load and handle empty stack
        if consumed:
            item.load -= 1
            if item.load <= 0:
                if source_type == 'belt':
                    self.belt[item_index] = None
                elif source_type == 'inventory':
                    if item_index < len(self.inventory) and self.inventory[item_index] == item:
                        self.inventory.pop(item_index)
                elif (source_type == 'container' or source_type == 'nearby') and container_item:
                    if item_index < len(container_item.inventory) and container_item.inventory[item_index] == item:
                        container_item.inventory.pop(item_index)
            return True
        
        return False


    def toggle_utility_item(self, item, source, index, container_item):
        """Toggles a utility item's state (e.g., Lantern On/Off)."""
        if not hasattr(item, 'state'):
            return

        new_name = ""
        if item.state == "on":
            new_name = item.name.replace(" on", " off")
        elif item.state == "off":
            if item.durability is not None and item.durability <= 0:
                print(f"Cannot turn on {item.name}, it's out of power.")
                return
            
            # Check for fuel type (e.g., "Matches" for lantern)
            if item.fuel_type == "Matches":
                matches, m_source, m_index, m_container = self.find_fuel("Matches")
                if not matches:
                    print("No matches to light the lantern.")
                    return
                
                # Consume one match
                matches.load -= 1
                if matches.load <= 0:
                    m_inv = self._get_source_inventory(m_source, m_container)
                    if m_inv and m_index < len(m_inv) and m_inv[m_index] == matches:
                        m_inv.pop(m_index)
            
            # If fuel_type is "Powerbank", we don't need to consume anything to *turn on*,
            # just check durability (which we did).
            # If fuel_type is None, it also just turns on.
            
            new_name = item.name.replace(" off", " on")
        
        if not new_name:
            return

        # Create the new item
        new_item = Item.create_from_name(new_name)
        if not new_item:
            print(f"Error: Could not find item template for '{new_name}'")
            return

        # Preserve durability and load (fuel)
        new_item.durability = item.durability
        new_item.load = item.load

        # Replace the item in its original location
        # If source is None, it means it was an update_stats call
        if source and index is not None:
            source_inventory = self._get_source_inventory(source, container_item)
            if source_inventory and index < len(source_inventory) and source_inventory[index] == item:
                source_inventory[index] = new_item
            else:
                # Failsafe: if we can't find it, we can't replace it
                print(f"Error: Could not find item {item.name} in {source} to toggle.")
        elif item in self.belt:
             self.belt[self.belt.index(item)] = new_item
        elif item in self.inventory:
             self.inventory[self.inventory.index(item)] = new_item
        # Add backpack/container checks if needed
        
    def reload_utility_item(self, item, source, index, container_item):
        """Reloads a utility item (Lantern) with fuel (Matches). Resets Durability."""
        if not item.fuel_type:
            print(f"{item.name} does not use fuel.")
            return

        fuel_item, f_source, f_index, f_container = self.find_fuel(item.fuel_type)
        if not fuel_item:
            print(f"No {item.fuel_type} found to reload.")
            return
            
        # Check if durability is already full
        max_dur = item.max_durability
        dur_needed = max_dur - (item.durability or 0)
        
        if dur_needed <= 0:
            print(f"{item.name} durability is already full.")
            return

        # Check if there are any matches left
        if fuel_item.load <= 0:
            print(f"No {item.fuel_type} left to use.")
            return

        # Consume only 1 match
        fuel_item.load -= 1
        
        # As requested: "Reload" resets durability to full
        item.durability = max_dur
        
        print(f"Used 1 {item.fuel_type} to reload {item.name}. Durability set to: {item.durability:.0f}")

        if fuel_item.load <= 0:
            # Remove empty fuel item
            f_inv = self._get_source_inventory(f_source, f_container)
            if f_inv and f_index < len(f_inv) and f_inv[f_index] == fuel_item:
                f_inv.pop(f_index)
    
    def find_item_and_stack(self, source, index, container_item):
        """Helper to find an item and its containing inventory list."""
        source_inventory = self._get_source_inventory(source, container_item)
        if source_inventory and 0 <= index < len(source_inventory):
            item = source_inventory[index]
            return item, source_inventory
        
        # Handle special cases like 'backpack' or 'invcontainer' which aren't in lists
        if source == 'backpack' and self.backpack:
            return self.backpack, [self] # Use [self] as a dummy list
        if source == 'invcontainer' and self.invcontainer:
            return self.invcontainer, [self]
            
        return None, None

    def drop_item_stack(self, game, source, index, container_item, quantity):
        """Drops one, all, or a specific quantity of a stackable item."""
        item, source_inventory = self.find_item_and_stack(source, index, container_item)
        if not item:
            print("Error: Could not find item to drop.")
            return

        item_to_drop = None
        if quantity == 'all' or quantity >= item.load:
            # Drop the entire stack
            item_to_drop = self.drop_item(game, source, index, container_item)
        elif quantity > 0 and item.load > 0:
            # Drop a partial stack
            item_to_drop = Item.create_from_name(item.name)
            if not item_to_drop: return

            transfer_amount = min(item.load, quantity)
            item_to_drop.load = transfer_amount
            item_to_drop.durability = item.durability # Preserve stats
            
            item.load -= transfer_amount
            if item.load <= 0:
                # The original stack is now empty, remove it
                self.drop_item(game, source, index, container_item) # Use original drop to handle pop
        
        if item_to_drop:
            if find_free_tile(item_to_drop.rect, game.obstacles, game.items_on_ground, initial_pos=self.rect.center, max_radius=1):
                return item_to_drop # Success, return item to be added to ground
            else:
                # No space, put the created stack back into inventory
                print("No free space to drop the item.")
                self.inventory.append(item_to_drop) # Failsafe: add to inventory
                self.stack_item_in_inventory(item_to_drop) # Try to stack it
                return None
        return None

    def transfer_item_stack(self, source, index, container_item, target_container):
        """Transfers an entire stack to another container, merging if possible."""
        

        # Get the item and its actual source list
        item = None
        source_inventory = self._get_source_inventory(source, container_item) # Get the real inventory list
        
        if source == 'backpack':
            item = self.backpack
        elif source == 'invcontainer':
            item = self.invcontainer
        elif source_inventory and 0 <= index < len(source_inventory):
            item = source_inventory[index] # Get the item from the list

        target_inv = None
        target_cap = 0
        target_name = "Unknown"

        if target_container is self: # Check if target is the player object
            target_inv = self.inventory
            target_cap = self.get_total_inventory_slots()
            target_name = "Inventory"
        elif target_container and hasattr(target_container, 'inventory'):
            target_inv = target_container.inventory
            target_cap = target_container.capacity or 0
            target_name = target_container.name
        else:
            print("Error: Invalid source or target container.")
            return

        if not item:
            print("Error: Invalid source item.")
            return
        
        # 1. Try to merge with existing stacks
        remaining_load = item.load
        for target_item in target_inv:
            if target_item.can_stack_with(item):
                available_space = target_item.capacity - target_item.load
                transfer = min(available_space, remaining_load)
                
                target_item.load += transfer
                remaining_load -= transfer
                item.load = remaining_load # This updates the item in the source
                
                if remaining_load <= 0:
                    break 
        
        # 2. If stack is now empty, remove it from source
        if item.load <= 0:
            # self.drop_item(game, source, index, container_item) # [OLD BUGGY LINE]
            
            if source == 'backpack':
                self.backpack = None
            elif source == 'invcontainer':
                self.invcontainer = None
            elif source_inventory and 0 <= index < len(source_inventory) and source_inventory[index] == item:
                source_inventory.pop(index) # Use pop(index) to be precise
            
            print(f"Merged all of {item.name} into {target_name}.")
            return
            
        # 3. If load remains, try to add as a new stack
        if remaining_load > 0:
            if len(target_inv) < target_cap:
                # We need to create a new item, as we can't just move 'item' (it might be a partial stack)
                new_stack = Item.create_from_name(item.name)
                new_stack.load = remaining_load
                new_stack.durability = item.durability # Copy stats just in case
                
                target_inv.append(new_stack)
                
                # self.drop_item(game, source, index, container_item) # [OLD BUGGY LINE]

                # The original item is now empty, remove it from its source.
                if source == 'backpack':
                    self.backpack = None
                elif source == 'invcontainer':
                    self.invcontainer = None
                elif source_inventory and 0 <= index < len(source_inventory) and source_inventory[index] == item:
                     source_inventory.pop(index) # Use pop(index)

                print(f"Sent {remaining_load} {item.name} to {target_name}.")
            else:
                print(f"{target_name} is full. Could not transfer remaining {remaining_load}.")


    def drop_item(self, game, source, index, container_item=None):
        if self.drop_cooldown > 0:
            print("Cannot drop items so quickly.")
            return None

        item_to_drop = None
        source_inventory = None # To know where to return it
        source_index = -1

        if source == 'inventory' and index < len(self.inventory):
            item_to_drop = self.inventory.pop(index)
            source_inventory = self.inventory
            source_index = index
        elif source == 'belt' and index < len(self.belt):
            item_to_drop = self.belt[index]
            self.belt[index] = None
            if self.active_weapon == item_to_drop:
                self.active_weapon = None
            source_inventory = self.belt
            source_index = index
        elif source == 'backpack':
            item_to_drop = self.backpack
            self.backpack = None
            source_inventory = [self] # Use dummy list
            source_index = 0 # Dummy index
        elif source == 'invcontainer':
            item_to_drop = self.invcontainer
            self.invcontainer = None
            source_inventory = [self] # Use dummy list
            source_index = 1 # Dummy index
        elif source == 'gear':
            item_to_drop = self.clothes.get(index) # index is slot_name
            self.clothes[index] = None
            source_inventory = [self] # Use dummy list
            source_index = 2 # Dummy index
        elif (source == 'container' or source == 'nearby') and container_item and index < len(container_item.inventory):
            item_to_drop = container_item.inventory.pop(index)
            source_inventory = container_item.inventory
            source_index = index

        if item_to_drop:
            # --- MODIFIED: Check for valid drop location ---
            if find_free_tile(item_to_drop.rect, game.obstacles, game.items_on_ground, initial_pos=self.rect.center, max_radius=1):
                return item_to_drop # Success
            else:
                # No space, put it back
                print("No free space to drop the item.")
                if source == 'inventory':
                    source_inventory.insert(source_index, item_to_drop)
                elif source == 'belt':
                    source_inventory[source_index] = item_to_drop
                elif source == 'backpack':
                    self.backpack = item_to_drop
                elif source == 'invcontainer':
                    self.invcontainer = item_to_drop
                elif source == 'gear':
                    self.clothes[index] = item_to_drop # index is slot_name
                elif source == 'container' or source == 'nearby':
                    source_inventory.insert(source_index, item_to_drop)
                return None # Failed to drop

        return None

    def stack_item_in_inventory(self, item_to_stack):
        """Tries to merge an item with existing stacks in inventory, then belt."""
        if not item_to_stack.is_stackable():
            return # Not stackable, do nothing

        # 1. Try to merge with inventory
        for item in self.inventory:
            if item.can_stack_with(item_to_stack):
                available_space = item.capacity - item.load
                transfer = min(available_space, item_to_stack.load)
                item.load += transfer
                item_to_stack.load -= transfer
                if item_to_stack.load <= 0:
                    return # Fully stacked
        
        # 2. Try to merge with belt
        for item in self.belt:
            if item and item.can_stack_with(item_to_stack):
                available_space = item.capacity - item.load
                transfer = min(available_space, item_to_stack.load)
                item.load += transfer
                item_to_stack.load -= transfer
                if item_to_stack.load <= 0:
                    return # Fully stacked

    def destroy_broken_weapon(self, broken_weapon):
        if self.active_weapon == broken_weapon:
            self.active_weapon = None

        # Check belt
        for i, item in enumerate(self.belt):
            if item == broken_weapon:
                self.belt[i] = None
                print(f"{broken_weapon.name} broke and was removed from your belt.")
                return

        # Check inventory
        try:
            self.inventory.remove(broken_weapon)
            print(f"{broken_weapon.name} broke and was removed from your inventory.")
        except ValueError:
            pass

    def find_water_to_auto_drink(self):
        """Searches belt, inventory, then backpack for a usable water item."""
        # 1. Search Belt
        for i, item in enumerate(self.belt):
            if item and 'Water' in item.name and item.load > 0:
                print(f"Found water in belt slot {i}") # Optional debug
                return item, 'belt', i, None # No container item needed for belt

        # 2. Search Inventory
        for i, item in enumerate(self.inventory):
            if item and 'Water' in item.name and item.load > 0:
                print(f"Found water in inventory slot {i}") # Optional debug
                return item, 'inventory', i, None # No container item needed for inventory

        for i, container_item in enumerate(self.inventory):
            if container_item and hasattr(container_item, 'inventory') and container_item.inventory:
                print(f"Checking inside container '{container_item.name}' in inventory slot {i}") # Debug
                for sub_index, sub_item in enumerate(container_item.inventory):
                    if sub_item and 'Water' in sub_item.name and sub_item.load > 0:
                        print(f"Found water inside '{container_item.name}' at sub-index {sub_index}")
                        # Source: 'container', Index: sub_index (within container), Container: container_item
                        return sub_item, 'container', sub_index, container_item

        # 3. Search Backpack (if exists and has inventory)
        if self.backpack and hasattr(self.backpack, 'inventory'):
            for i, item in enumerate(self.backpack.inventory):
                if item and 'Water' in item.name and item.load > 0:
                    print(f"Found water in backpack slot {i}") # Optional debug
                    # For backpack items, the source is 'container' and we need the backpack itself
                    return item, 'container', i, self.backpack

        # 4. Not found
        print("No water found for auto-drink.") # Optional debug
        return None, None, None, None