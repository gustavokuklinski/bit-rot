import time
import pygame
import os
import random
import math

from core.data.config import *
import core.data.config
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.entities.player.player_progression import PlayerProgression
from core.ui.inventory_modal import get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect
from core.messages import display_message, display_message_player
from core.placement import find_free_tile
from core.data.recipe_manager import RecipeManager
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS

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
        self.body_parts = data.get('body_parts', {
            'head': {'value': 100.0, 'defence': 0.0},
            'legs': {'value': 100.0, 'defence': 0.0},
            'feet': {'value': 100.0, 'defence': 0.0},
            'body': {'value': 100.0, 'defence': 0.0},
            'hand': {'value': 100.0, 'defence': 0.0},
            'arms': {'value': 100.0, 'defence': 0.0}
        })
        
        self.attributes = data.get('attributes', {
            'strength': 0.0, 'fitness': 0.0, 'melee': 0.0, 
            'ranged': 0.0, 'lucky': 0.0, 'speed': 0.0
        })

        self.max_health = stats.get('health', 100.0)
        self.update_global_health()
        
        self.max_tireness = stats.get('tireness', 100.0)
        self.tireness = stats.get('tireness', self.max_tireness)
        self.max_stamina = stats.get('stamina', 100.0)
        self.stamina = stats.get('stamina', self.max_stamina)
        self.water = stats.get('water', 100.0)
        self.food = stats.get('food', 100.0)
        self.infection = stats.get('infection', 0.0)
        self.anxiety = stats.get('anxiety', 0.0)

        self.sex = data.get('sex', 'Male')
        self.traits = data.get('traits', [])
        
        self.known_recipes = data.get('known_recipes', [])
        
        if self.traits:
            for trait_id in self.traits:
                trait_def = TRAIT_DEFINITIONS.get(trait_id)
                if trait_def and 'recipes' in trait_def:
                    for magazine in trait_def['recipes']:
                        if magazine not in self.known_recipes:
                            self.known_recipes.append(magazine)

        if not RecipeManager.RECIPES:
             RecipeManager.load_recipes()

        self.inventory = []
        self.backpack = None
        self.active_weapon = None
        self.belt = [None] * 5
        self.last_decay_time = time.time()
        self.base_inventory_slots = 5
        
        self.clothes_slots =  ['head','legs', 'feet',  'body' ,'arms', 'hands']
        self.clothes = {slot: None for slot in self.clothes_slots}
        
        chosen_clothes_dict = data.get('clothes', {})
        for slot, item_data in chosen_clothes_dict.items():
            if item_data and item_data != "None" and slot in self.clothes_slots:
                if isinstance(item_data, dict):
                    self.clothes[slot] = Item.from_dict(item_data)
                else:
                    self.clothes[slot] = Item.create_from_name(item_data)

        self.melee_swing_timer = 0
        self.gun_flash_timer = 0
        self.melee_swing_angle = 0
        self.drop_cooldown = 0

        self.is_reloading = False
        self.reloading_weapon = None
        self.reload_timer = 0
        self.reload_duration = 120

        self.action_timer = 0
        self.action_total_time = 0
        self.action_callback = None
        self.action_name = ""
        self.action_xp_reward = 0

        self.images = {}
        visuals_data = data.get('visuals', {})
        self.visuals = visuals_data
        
        if 'center' in visuals_data:
            self.images['center'] = self._load_sprite(visuals_data.get('center'))
            self.images['left'] = self._load_sprite(visuals_data.get('left'))
            self.images['right'] = self._load_sprite(visuals_data.get('right'))
        else:
            old_sprite = self._load_sprite(visuals_data.get('sprite'))
            self.images['center'] = old_sprite
            self.images['left'] = old_sprite
            self.images['right'] = old_sprite

        self.image = self.images.get('center')
        self.layer_switch_cooldown = 0
        self.aim_angle = 0
        self.facing_direction = (0, 1)
        self.is_sleeping = False
        self.sounds_data = data.get('sounds', {})
        if not self.sounds_data or 'steps' not in self.sounds_data:
             self.sounds_data = {'steps': 'steps.ogg'}
        self.sound_steps = self.sounds_data.get('steps')
        self.last_step_sound_time = 0
        self.chat_text = None
        self.chat_timer = 0
        self.chat_duration = 300
        self.current_aim_factor = 1.0 
        self.is_aiming = False
        self.vehicle = None
        self.walk_anim_angle = 0
        self.is_moving_to_tile = False
        self.target_x = 0
        self.target_y = 0
        self.is_dead = False
        self.dead_image = self._load_sprite(self.visuals.get('dead_sprite', 'dead.png'))
        self.last_shot_time = 0
        self.is_resting = False

    def update_global_health(self):
        if not self.body_parts:
            return
        total_value = sum(part['value'] for part in self.body_parts.values())
        max_possible = 100.0 * len(self.body_parts)
        self.health = (total_value / max_possible) * 100.0

    def get_vulnerable_part(self):
        slot_map = {'hand': 'hands'} 
        candidates = []
        lowest_def = float('inf')

        for part, data in self.body_parts.items():
            defence = data.get('defence', 0.0)
            c_slot = slot_map.get(part, part)
            item = self.clothes.get(c_slot)
            if item and hasattr(item, 'defence'):
                defence += item.defence
            
            if defence < lowest_def:
                lowest_def = defence
                candidates = [part]
            elif defence == lowest_def:
                candidates.append(part)
        
        return random.choice(candidates) if candidates else 'body'

    def take_damage_to_part(self, part, amount):
        if part in self.body_parts:
            self.body_parts[part]['value'] = max(0.0, self.body_parts[part]['value'] - amount)
            self.update_global_health()

    def get_most_damaged_part(self):
        candidates = []
        lowest_val = 101.0
        for part, data in self.body_parts.items():
            if data['value'] < lowest_val:
                lowest_val = data['value']
                candidates = [part]
            elif data['value'] == lowest_val:
                candidates.append(part)
        if lowest_val >= 100.0:
            return None
        return random.choice(candidates)

    def _load_sprite(self, sprite_path):
        if not sprite_path: return None
        try:
            path = SPRITE_PATH + "player/" + sprite_path
            image = pygame.image.load(path).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
            return image
        except pygame.error as e:
            print(f"Warning: Could not load player sprite '{sprite_path}': {e}")
            return None
    
    def enter_vehicle(self, vehicle, game):
        seat_idx = -1
        for i, occupant in enumerate(vehicle.seats):
            if occupant is None:
                seat_idx = i
                break
        
        if seat_idx == -1:
            display_message_player("Vehicle is full! No free seats.")
            return

        self.vehicle = vehicle
        self.x = vehicle.x 
        self.y = vehicle.y
        self.rect.topleft = (self.x, self.y)
        
        vehicle.seats[seat_idx] = self
        self.vehicle_seat_index = seat_idx

        if vehicle.rect in game.obstacles:
            game.obstacles.remove(vehicle.rect)
        
        seat_name = "Driver's Seat" if seat_idx == 0 else f"Seat {seat_idx+1}"
        display_message_player(f"Entered {vehicle.name} ({seat_name})")

    def exit_vehicle(self, game):
        if self.vehicle:
            if hasattr(self, 'vehicle_seat_index') and self.vehicle_seat_index is not None:
                if 0 <= self.vehicle_seat_index < len(self.vehicle.seats):
                    if self.vehicle.seats[self.vehicle_seat_index] == self:
                        self.vehicle.seats[self.vehicle_seat_index] = None

            if self.vehicle.rect not in game.obstacles:
                game.obstacles.append(self.vehicle.rect)
            
            self.x += TILE_SIZE 
            self.rect.topleft = (self.x, self.y)
            self.vehicle = None
            self.vehicle_seat_index = None
            
            display_message_player("Exited vehicle")

    def update_aim(self, is_moving):
        if not self.is_aiming:
            self.current_aim_factor = 1.0
            return

        ranged_level = self.progression.get_ranged(self)
        shrink_speed = 0.01 + (ranged_level * 0.002)

        if is_moving:
            self.current_aim_factor = min(1.0, self.current_aim_factor + 0.05)
        else:
            self.current_aim_factor = max(0.0, self.current_aim_factor - shrink_speed)

    def get_total_defence(self):
        total_defence = 0
        for item in self.clothes.values():
            if item and hasattr(item, 'defence') and item.defence is not None:
                if hasattr(item, 'durability') and item.durability is not None:
                    if item.max_durability > 0:
                        defence_factor = item.durability / item.max_durability
                        total_defence += item.defence * defence_factor
                    elif item.durability > 0:
                         total_defence += item.defence
                elif not hasattr(item, 'durability') or item.durability is None:
                     total_defence += item.defence
        return total_defence

    def get_attack_damage(self):
        min_dmg = 1
        max_dmg = 3 
        
        if self.active_weapon:
            min_dmg = getattr(self.active_weapon, 'min_damage', 1)
            max_dmg = getattr(self.active_weapon, 'max_damage', 5)
            
            if hasattr(self.active_weapon, 'current_damage_range'):
                rng = self.active_weapon.current_damage_range
                min_dmg = rng[0]
                max_dmg = rng[1]

        return random.randint(int(min_dmg), int(max_dmg))

    def take_durability_damage(self, raw_damage, game):
        worn_clothes = [item for item in self.clothes.values() if item and hasattr(item, 'durability') and item.durability is not None and item.durability > 0]
        if not worn_clothes: return

        item_hit = random.choice(worn_clothes)
        dur_damage = raw_damage * 0.25 
        
        if dur_damage > 0:
            item_hit.durability = max(0, item_hit.durability - dur_damage)
            if item_hit.durability <= 0:
                slot_to_clear = None
                for slot, item in self.clothes.items():
                    if item == item_hit:
                        slot_to_clear = slot
                        break
                if slot_to_clear:
                    self.clothes[slot_to_clear] = None
                    display_message(f"Your {item_hit.name} broke!")

    def take_damage(self, game, base_damage, base_infection):
        if self.vehicle: return 0, 0
        
        self.take_durability_damage(base_damage, game)

        total_defence = self.get_total_defence()
        health_bonus_perc = self.progression.get_health_bonus(self)
        infection_bonus_perc = self.progression.get_infection_bonus(self)
        
        total_reduction_perc = health_bonus_perc + total_defence
        
        damage_modifier = 1.0 - (total_reduction_perc / 100.0)
        damage_modifier = max(0.0, damage_modifier)

        infection_modifier = 1.0 + (infection_bonus_perc / 100.0)
        
        final_damage_taken = max(0, base_damage * damage_modifier)
        final_infection_taken = max(0, base_infection * infection_modifier)
        
        self.take_damage_to_part('body', final_damage_taken)

        if final_infection_taken > 0:
            self.infection = min(100, self.infection + final_infection_taken)
            
        return final_damage_taken, final_infection_taken

    def process_kill(self, weapon, zombie):
        self.progression.process_kill(self, weapon, zombie)

    def update_position(self, obstacles, zombies, game):
        if self.vehicle:
            if not self.vehicle.is_driveable():
                return

            current_max_speed = self.vehicle.max_speed
            input_x = 0
            input_y = 0
            
            if self.vehicle.active and (self.vx != 0 or self.vy != 0):
                input_magnitude = math.sqrt(self.vx**2 + self.vy**2)
                if input_magnitude > 0:
                    input_x = (self.vx / input_magnitude)
                    input_y = (self.vy / input_magnitude)

            if input_x != 0 or input_y != 0:
                self.vehicle.velocity[0] += input_x * self.vehicle.acceleration
                self.vehicle.velocity[1] += input_y * self.vehicle.acceleration
            else:
                speed = self.vehicle.current_speed_val
                if speed > 0:
                    friction_loss = min(speed, self.vehicle.friction)
                    scale = (speed - friction_loss) / speed
                    self.vehicle.velocity[0] *= scale
                    self.vehicle.velocity[1] *= scale

            speed = self.vehicle.current_speed_val
            if speed > current_max_speed:
                scale = current_max_speed / speed
                self.vehicle.velocity[0] *= scale
                self.vehicle.velocity[1] *= scale
            
            move_x = self.vehicle.velocity[0]
            move_y = self.vehicle.velocity[1]

            if self.vehicle.active and speed > 0.1:
                fuel_item = self.vehicle.equipment.get('fuel')
                if fuel_item:
                    fuel_item.load = max(0, fuel_item.load - 0.005) 
                
                self.vehicle.battery = min(1.0, self.vehicle.battery + 0.0005)

            self.vehicle.move(move_x, move_y, obstacles)
            
            vehicle_rect = self.vehicle.rect
            for zombie in zombies[:]: 
                if vehicle_rect.colliderect(zombie.rect):
                    damage_to_zombie = 1000
                    zombie.take_damage(damage_to_zombie, game)
                    self.vehicle.velocity[0] *= 0.5
                    self.vehicle.velocity[1] *= 0.5

            self.x = self.vehicle.x
            self.y = self.vehicle.y
            self.rect.topleft = (int(self.x), int(self.y))
            
        else:
            self.x += self.vx
            self.rect.x = round(self.x)

            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    if self.vx > 0: self.rect.right = obstacle.left
                    elif self.vx < 0: self.rect.left = obstacle.right
                    self.x = self.rect.x

            self.y += self.vy
            self.rect.y = round(self.y)

            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    if self.vy > 0: self.rect.bottom = obstacle.top
                    elif self.vy < 0: self.rect.top = obstacle.bottom
                    self.y = self.rect.y

    def draw(self, surface, offset_x, offset_y, is_aiming=False):
        if self.vehicle:
            veh_draw_pos = (self.vehicle.x + offset_x, self.vehicle.y + offset_y)
            surface.blit(self.vehicle.image, veh_draw_pos)
            return

        draw_rect = self.rect.move(offset_x, offset_y)

        current_image = None
        if self.facing_direction[0] < 0: 
            current_image = self.images.get('left')
        elif self.facing_direction[0] > 0: 
            current_image = self.images.get('right')
        
        if current_image is None:
            current_image = self.images.get('center')

        if current_image:
            if self.walk_anim_angle != 0:
                rotated_img = pygame.transform.rotate(current_image, self.walk_anim_angle)
                rot_rect = rotated_img.get_rect(center=draw_rect.center)
                surface.blit(rotated_img, rot_rect)
            else:
                surface.blit(current_image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)

        for slot in self.clothes_slots: 
            item = self.clothes.get(slot)
            if item and item.image:
                if self.walk_anim_angle != 0:
                    rotated_cloth = pygame.transform.rotate(item.image, self.walk_anim_angle)
                    rot_cloth_rect = rotated_cloth.get_rect(center=draw_rect.center)
                    surface.blit(rotated_cloth, rot_cloth_rect)
                else:
                    surface.blit(item.image, draw_rect)

        if self.active_weapon and self.active_weapon.image:
            is_swinging = (self.melee_swing_timer > 0)
            is_ranged_aiming = (is_aiming and self.active_weapon.item_type == 'weapon_ranged')
            
            if not is_swinging and not is_ranged_aiming:
                weapon_img = self.active_weapon.image
                angle_degrees = math.degrees(self.aim_angle)
                
                if math.cos(self.aim_angle) < 0:
                    weapon_img = pygame.transform.flip(weapon_img, False, True)
                
                rotated_image = pygame.transform.rotate(weapon_img, angle_degrees)
                offset_dist = TILE_SIZE * 0.4
                offset_x = math.cos(self.aim_angle) * offset_dist
                offset_y = -math.sin(self.aim_angle) * offset_dist
                
                rotated_rect = rotated_image.get_rect(center=draw_rect.center)
                rotated_rect.centerx += offset_x
                rotated_rect.centery += offset_y
                
                surface.blit(rotated_image, rotated_rect)

        if is_aiming and self.active_weapon and self.active_weapon.image and \
           self.active_weapon.item_type == 'weapon_ranged':
            
            weapon_img = self.active_weapon.image
            angle_degrees = math.degrees(self.aim_angle)

            if math.cos(self.aim_angle) < 0:
                weapon_img = pygame.transform.flip(weapon_img, False, True)

            rotated_image = pygame.transform.rotate(weapon_img, angle_degrees)
            offset_dist = TILE_SIZE * 0.8 
            offset_x = math.cos(self.aim_angle) * offset_dist
            offset_y = -math.sin(self.aim_angle) * offset_dist 
            
            rotated_rect = rotated_image.get_rect(center=draw_rect.center)
            rotated_rect.centerx += offset_x
            rotated_rect.centery += offset_y

            surface.blit(rotated_image, rotated_rect)

        if self.is_sleeping:
            if self.max_tireness < 0:
                progress = 1.0 - max(0.0, min(1.0, self.tireness / self.max_tireness))
            else:
                progress = 0.0
            
            bar_total_width = TILE_SIZE * 2
            bar_x = draw_rect.centerx - (bar_total_width / 2)
            bar_y = draw_rect.top - 20 
            
            bg_bar_rect = pygame.Rect(bar_x, bar_y, bar_total_width, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)
            
            bar_progress_width = int(bar_total_width * progress)
            bar_rect = pygame.Rect(bar_x, bar_y, bar_progress_width, 5)
            pygame.draw.rect(surface, (100, 150, 255), bar_rect)

        if self.action_timer > 0 and self.action_total_time > 0:
            progress = 1.0 - (self.action_timer / self.action_total_time)
            
            bar_total_width = TILE_SIZE * 2
            bar_x = draw_rect.centerx - (bar_total_width / 2)
            bar_y = draw_rect.top - 15 
            
            bg_bar_rect = pygame.Rect(bar_x, bar_y, bar_total_width, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)
            
            bar_progress_width = int(bar_total_width * progress)
            bar_rect = pygame.Rect(bar_x, bar_y, bar_progress_width, 5)
            pygame.draw.rect(surface, (50, 200, 50), bar_rect)

        if self.melee_swing_timer > 0:
            if self.active_weapon and self.active_weapon.image and \
               self.active_weapon.item_type in ['weapon_melee', 'tool']:
                
                original_image = self.active_weapon.image
                angle_degrees = math.degrees(self.melee_swing_angle)
                rotated_image = pygame.transform.rotate(original_image, angle_degrees) 
                rotated_rect = rotated_image.get_rect(center=draw_rect.center)
                
                offset_radius = TILE_SIZE * 0.8 
                offset_x_weapon = math.cos(self.melee_swing_angle) * offset_radius
                offset_y_weapon = -math.sin(self.melee_swing_angle) * offset_radius
                
                rotated_rect.centerx += offset_x_weapon
                rotated_rect.centery += offset_y_weapon
                
                surface.blit(rotated_image, rotated_rect)

            swing_radius = TILE_SIZE * 0.7
            center_x, center_y = draw_rect.center
            start_angle = self.melee_swing_angle - (3.1415 / 4)
            end_angle = self.melee_swing_angle + (3.1415 / 4)
            arc_surf = pygame.Surface((swing_radius * 2, swing_radius * 2), pygame.SRCALPHA)
            
            arc_rect = arc_surf.get_rect()
            pygame.draw.arc(arc_surf, (0, 0, 0, 80), arc_rect, start_angle, end_angle, 2)
            surface.blit(arc_surf, (center_x - swing_radius, center_y - swing_radius))
            
            self.melee_swing_timer -= 1

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

        if self.action_timer > 0:
            self.action_timer -= 1
            self.vx = 0
            self.vy = 0
            self.is_running = False

            if self.action_timer <= 0:
                if self.action_callback:
                    self.action_callback()
                    self.action_callback = None
                    if self.action_xp_reward > 0:
                        self.progression.add_speed_xp(self, self.action_xp_reward)
                self.action_name = ""
            return False

        if self.chat_timer > 0:
            self.chat_timer -= 1
            if self.chat_timer <= 0:
                self.chat_text = None

        keys = pygame.key.get_pressed()
        has_input = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]
        is_moving = has_input and (self.vehicle is None)

        if is_moving:
            self.is_resting = False
            
        grid_x = int(self.rect.centerx // TILE_SIZE)
        grid_y = int(self.rect.centery // TILE_SIZE)
        tile = game.map_manager.get_tile_at(grid_x, grid_y)
        
        is_active_resting = (tile and tile.get('rest')) or self.is_resting

        if not self.is_sleeping and not is_active_resting:
            self.tireness = min(self.max_tireness, self.tireness - 0.005)

        if not self.is_sleeping and is_active_resting:
            if self.stamina < self.max_stamina:
                self.stamina = min(self.max_stamina, self.stamina + 0.5)
            if self.tireness < self.max_tireness:
                self.tireness = min(self.max_tireness, self.tireness + 0.03)

        if self.is_sleeping:
            # [CHANGED] Sleep Logic to Simulate World
            
            # 1. Enable Fast Forward (Simulate World)
            game.is_fast_forwarding = True
            
            # 2. Restore Energy slower per frame (because simulated frames are many)
            # 0.05 per frame * 60 FPS * 50x speed = 150 points per real-time second
            # This makes sleeping very fast but actually runs the game loop.
            restore_amount = 0.5 
            
            self.tireness = max(0.0, self.tireness + restore_amount)
            
            if self.tireness >= self.max_tireness:
                self.tireness = self.max_tireness
                self.is_sleeping = False
                game.is_fast_forwarding = False # Disable FF on wake
                display_message_player("You wake up refreshed.")

        mouse_buttons = pygame.mouse.get_pressed()
        is_aiming = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
        is_firing = mouse_buttons[0]

        if not self.is_sleeping and is_aiming and is_firing:
             if self.active_weapon and getattr(self.active_weapon, 'machine_gun', False):
                  from core.events.mouse import handle_attack
                  handle_attack(game, pygame.mouse.get_pos())

        if is_moving:
            self.walk_anim_angle = math.sin(current_time * 15) * 2
        else:
            self.walk_anim_angle = 0
        self.update_aim(is_moving)
        
        if is_moving and self.sound_steps:
            if current_time > self.last_step_sound_time:
                game.sound_manager.play_sound(
                    self.sound_steps,
                    subdir='player',
                    game=game,
                    source_pos=self.rect.center,
                    base_volume=random.uniform(0.2, 0.4)
                )
                if self.is_running:
                    next_delay = random.uniform(0.25, 0.35) 
                else:
                    next_delay = random.uniform(0.35, 0.5)
                self.last_step_sound_time = current_time + next_delay

        self.progression.update(self, is_moving, game)
        
        if getattr(game, 'is_fast_forwarding', False):
             dt = 1.0 / 60.0
             decay_boost = dt * (game.fast_forward_speed - 1.0)
             self.last_decay_time -= decay_boost

        if current_time - self.last_decay_time >= core.data.config.DECAY_RATE_SECONDS:
            water_mod = 1.0 + (self.progression.get_water_bonus(self) / 100.0)
            food_mod = 1.0 + (self.progression.get_food_bonus(self) / 100.0)
            
            water_decay = max(0, core.data.config.WATER_DECAY_AMOUNT * water_mod)
            food_decay = max(0, core.data.config.FOOD_DECAY_AMOUNT * food_mod)
            
            self.water = max(0, self.water - water_decay)
            self.food = max(0, self.food - food_decay)

            self.last_decay_time = current_time
            if self.water <= 0 or self.food <= 0:
                self.health -= 5.0 * (1 if self.water <= 0 else 0) + 5.0 * (1 if self.food <= 0 else 0)
                self.health = max(0, self.health)

            if AUTO_DRINK and self.water <= core.data.config.AUTO_DRINK_THRESHOLD:
                water_item, source, index, container = self.find_water_to_auto_drink()
                if water_item:
                    self.consume_item(water_item, source, index, container, is_auto_drink=True, game=game)
        
        all_inventories = [self.belt, self.inventory]
        if self.backpack:
            all_inventories.append(self.backpack.inventory)
            
        for inv in all_inventories:
            for item in inv:
                if getattr(item, 'state', 'off') == 'on':
                    if item.durability is not None:
                        item.durability -= 0.05 
                        if item.durability <= 0:
                            item.durability = 0
                            self.toggle_utility_item(item, None, None, None) 
        
        def msg(text):
            display_message_player(text)

        def close_modal(target_item):
            for m in list(game.modals):
                if m.get('item') == target_item:
                    game.modals.remove(m)

        Item.cleanup_disposables(self.inventory, game.modals, msg)

        for i, item in enumerate(self.belt):
            if item:
                if hasattr(item, 'inventory') and item.inventory:
                     Item.cleanup_disposables(item.inventory, game.modals, msg)
                
                if getattr(item, 'disposable', False) and hasattr(item, 'inventory') and len(item.inventory) == 0:
                    close_modal(item)
                    self.belt[i] = None
                    msg(f"Discarded empty {item.name}.")

        if self.backpack:
            Item.cleanup_disposables(self.backpack.inventory, game.modals, msg)
            
            if getattr(self.backpack, 'disposable', False) and hasattr(self.backpack, 'inventory') and len(self.backpack.inventory) == 0:
                close_modal(self.backpack)
                self.backpack = None
                msg(f"Discarded empty backpack container.")

        if self.is_reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self._finish_reload()

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

    # ... (rest of the file remains unchanged)
    def start_action(self, action_name, base_duration_mult, callback, xp_reward=5):
        if self.action_timer > 0:
            display_message_player("Busy...")
            return False

        UNIT_TIME = 60
        speed_lvl = self.progression.get_speed(self)
        speed_factor = 1.0 / (1.0 + (speed_lvl * 0.1)) 
        
        total_duration = int(UNIT_TIME * base_duration_mult * speed_factor)
        
        self.action_timer = total_duration
        self.action_total_time = total_duration
        self.action_name = action_name
        self.action_callback = callback
        self.action_xp_reward = xp_reward
        
        display_message_player(f"{action_name}...")
        return True
    
    def get_total_inventory_slots(self):
        if self.backpack:
            return self.base_inventory_slots + (self.backpack.capacity or 0)
        return self.base_inventory_slots

    def find_consumable_at_mouse(self, mouse_pos):
        for i, item in enumerate(self.inventory):
            if item and item.item_type.startswith('consumable'):
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
            return None, None, None, None
        ammo_type_needed = weapon.ammo_type
        
        # 1. Search Belt (Direct and Nested)
        for i, item in enumerate(self.belt):
            if item:
                # Direct check
                if item.item_type.startswith('consumable') and getattr(item, 'load', 0) > 0 and item.name == ammo_type_needed:
                    return item, 'belt', i, None
                # Nested check (if belt item is a container)
                if hasattr(item, 'inventory') and item.inventory:
                     for sub_i, sub_item in enumerate(item.inventory):
                         if sub_item and sub_item.item_type.startswith('consumable') and getattr(sub_item, 'load', 0) > 0 and sub_item.name == ammo_type_needed:
                             return sub_item, 'container', sub_i, item

        # 2. Search Inventory (Direct and Nested)
        for i, item in enumerate(self.inventory):
            if item:
                # Direct check
                if item.item_type.startswith('consumable') and getattr(item, 'load', 0) > 0 and item.name == ammo_type_needed:
                    return item, 'inventory', i, None
                # Nested check (Containers inside inventory)
                if hasattr(item, 'inventory') and item.inventory:
                    for sub_i, sub_item in enumerate(item.inventory):
                        if sub_item and sub_item.item_type.startswith('consumable') and getattr(sub_item, 'load', 0) > 0 and sub_item.name == ammo_type_needed:
                            return sub_item, 'container', sub_i, item
        
        # 3. Search Gear/Clothes (Direct and Nested)
        for slot, item in self.clothes.items():
            if item:
                # Direct check (e.g. if the gear itself is ammo)
                if item.item_type.startswith('consumable') and getattr(item, 'load', 0) > 0 and item.name == ammo_type_needed:
                    return item, 'gear', slot, None
                # Nested check (Items inside Vest/Pants pockets)
                if hasattr(item, 'inventory') and item.inventory:
                     for sub_i, sub_item in enumerate(item.inventory):
                         if sub_item and sub_item.item_type.startswith('consumable') and getattr(sub_item, 'load', 0) > 0 and sub_item.name == ammo_type_needed:
                             return sub_item, 'container', sub_i, item

        # 4. Search Backpack (Direct and Nested)
        if self.backpack and hasattr(self.backpack, 'inventory'):
            for i, item in enumerate(self.backpack.inventory):
                 if item:
                     # Direct check inside backpack
                     if item.item_type.startswith('consumable') and getattr(item, 'load', 0) > 0 and item.name == ammo_type_needed:
                        return item, 'container', i, self.backpack
                     # Nested check (Containers inside backpack)
                     if hasattr(item, 'inventory') and item.inventory:
                        for sub_i, sub_item in enumerate(item.inventory):
                            if sub_item and sub_item.item_type.startswith('consumable') and getattr(sub_item, 'load', 0) > 0 and sub_item.name == ammo_type_needed:
                                return sub_item, 'container', sub_i, item

        return None, None, None, None

    def find_fuel(self, fuel_name):
        if not fuel_name:
            return None, None, None, None
            
        for i, item in enumerate(self.belt):
            if item and item.name == fuel_name and getattr(item, 'load', 0) > 0:
                return item, 'belt', i, None

        for i, item in enumerate(self.inventory):
            if item and item.name == fuel_name and getattr(item, 'load', 0) > 0:
                return item, 'inventory', i, None
        
        if self.backpack and hasattr(self.backpack, 'inventory'):
            for i, item in enumerate(self.backpack.inventory):
                if item and item.name == fuel_name and getattr(item, 'load', 0) > 0:
                    return item, 'container', i, self.backpack
                    
        return None, None, None, None

    def reload_active_weapon(self, weapon=None,game=None):
        if self.is_reloading:
            display_message_player("Already reloading.")
            return
            
        target_weapon = weapon if weapon else self.active_weapon
        
        if not target_weapon or not getattr(target_weapon, 'ammo_type', None):
            display_message_player("Cannot reload: No gun equipped.")
            return
            
        if target_weapon.load >= target_weapon.capacity:
            display_message_player(f"{target_weapon.name} is already full ({target_weapon.load:.0f}/{target_weapon.capacity:.0f}).")
            return
        
        ammo_item, _, _, _ = self.find_matching_ammo(target_weapon)
        
        if not ammo_item:
            display_message_player(f"No {target_weapon.ammo_type} found.")
            return
        
        if game and hasattr(target_weapon, 'sounds') and 'reload' in target_weapon.sounds and target_weapon.sounds['reload']:
            game.sound_manager.play_sound(
                target_weapon.sounds['reload'],
                subdir='items',
                game=game,
                source_pos=self.rect.center
            )
            
        self.is_reloading = True
        self.reloading_weapon = target_weapon 
        self.reload_timer = self.reload_duration
        display_message_player(f"Reloading {target_weapon.name}...")

    def _finish_reload(self):
        self.is_reloading = False
        
        weapon = getattr(self, 'reloading_weapon', self.active_weapon)
        self.reloading_weapon = None 
        
        if not weapon: return
        
        ammo_item, source_type, index, container_obj = self.find_matching_ammo(weapon)
        
        if not ammo_item: return
        needed = int(weapon.capacity - weapon.load)
        available = int(ammo_item.load)
        transfer_amount = min(needed, available)
        
        if transfer_amount > 0:
            weapon.load += transfer_amount
            ammo_item.load -= transfer_amount
            display_message_player(f"Finished reloading {weapon.name}. Load: {weapon.load:.0f}/{weapon.capacity:.0f}.")
            
            if ammo_item.load <= 0:
                if source_type == 'inventory':
                    try:
                        self.inventory.remove(ammo_item)
                    except ValueError: pass
                elif source_type == 'belt':
                    self.belt[index] = None
                elif source_type == 'gear':
                    self.clothes[index] = None
                elif source_type == 'container' and container_obj:
                    try:
                        container_obj.inventory.remove(ammo_item)
                    except ValueError: pass
    
    def find_repair_kit(self, target_item):
        if not target_item: return None, None, None, None

        def is_valid_kit(it):
            return (it and it.item_type == 'consumable_repair' and 
                    hasattr(it, 'repair_list') and 
                    target_item.name in it.repair_list and 
                    it.load > 0)

        for i, item in enumerate(self.belt):
            if is_valid_kit(item): return item, 'belt', i, None
        
        for i, item in enumerate(self.inventory):
            if is_valid_kit(item): return item, 'inventory', i, None

        if self.backpack:
            for i, item in enumerate(self.backpack.inventory):
                if is_valid_kit(item): return item, 'container', i, self.backpack

        return None, None, None, None

    def repair_item(self, game, target_item):
        if self.action_timer > 0:
            display_message_player("Busy...")
            return

        kit, source, index, container = self.find_repair_kit(target_item)
        
        if not kit:
            display_message_player(f"No repair kit found for {target_item.name}.")
            return

        if target_item.durability >= target_item.max_durability:
            display_message_player(f"{target_item.name} is already in perfect condition.")
            return

        def execute_repair():
            restore_amount = random.randint(kit.min_restore, kit.max_restore)
            old_dur = target_item.durability
            target_item.durability = min(target_item.max_durability, target_item.durability + restore_amount)
            restored = target_item.durability - old_dur
            
            display_message_player(f"Repaired {target_item.name} by {restored:.0f} points using {kit.name}.")
            self.progression.add_xp(self, 'maintenance', 20)

            kit.load -= 1
            if kit.load <= 0:
                inv = self._get_source_inventory(source, container)
                if inv:
                    if source == 'belt': self.belt[index] = None
                    else: inv.pop(index)
                display_message_player(f"{kit.name} used up.")

        self.start_action("Repairing", 2.0, execute_repair, xp_reward=10)

    def get_item_context_options(self, item, source, container_item=None):
        options = []

        if getattr(item, 'item_type', '') == 'vehicle':
             options.append("Inspect")
             return options

        if isinstance(item, Corpse):
            options.append('Open')
            return options
        
        if item.item_type == 'text' or item.item_type == 'recipe' or item.item_type == 'map':
            if item.item_type == 'recipe':
                options.append('Use')
            elif item.item_type == 'map':
                options.append('Open')
            else:
                options.append('Read')

            if hasattr(item, 'is_stackable') and item.is_stackable():
                options.append('Drop one')
                if item.load > 1:
                    options.append('Drop all')
            else:
                options.append('Drop')
            return options

        if item.item_type.startswith('consumable'):
            if item.item_type == 'consumable_ammo' or 'Ammo' in item.name or 'Shells' in item.name:
                options.append('Reload') 
            elif item.item_type == 'consumable_medication' or 'Medkit' in item.name or 'Bandage' in item.name:
                options.append('Use')
                for part, data in self.body_parts.items():
                    if data['value'] < 100.0:
                        options.append(f"Bandage {part.capitalize()}")
            else:
                options.append('Use')
            options.append('Equip')
        elif item.item_type in ['utility', 'mobile']:
            if item.state == 'on':
                options.append('Turn off')
            elif item.state == 'off':
                options.append('Turn on')
            if item.fuel_type:
                options.append('Reload') 
            if item.item_type == 'mobile': 
                options.append('Open')
            options.append('Equip')

        elif item.item_type == 'backpack':
            options.append('Open')
            if not self.backpack:
                options.append('Equip')
        
        elif item.item_type == 'cloth':
            options.append('Open')
            options.append('Equip')

        elif item.item_type in ['weapon_melee', 'weapon_ranged', 'tool']:
            options.append('Equip')

            if item.item_type == 'weapon_ranged':
                options.append('Reload')
            
            if item.item_type == 'weapon_ranged' and item.load is not None and item.load > 0:
                options.append('Get bullets')

        elif item.item_type == 'container':
            options.append('Open')

        if hasattr(item, 'is_stackable') and item.is_stackable() and item.load is not None:
            options.append('Drop one')
            if item.load > 1:
                options.append('Drop all')
            
            if self.backpack and container_item is not self.backpack:
                options.append('Send all to Backpack')
            
            

            if source != 'inventory':
                options.append('Send all to Inventory')

        else:
            options.append('Drop')
        return options
    
    def read_recipe_book(self, item):
        recipes_taught = RecipeManager.get_recipes_by_magazine(item.name)
        
        if not recipes_taught:
            display_message_player(f"You read {item.name}, but learn nothing new.")
            return

        new_recipes = [r for r in recipes_taught if r.magazine not in self.known_recipes] 
        
        if not new_recipes and item.name in self.known_recipes:
            display_message_player(f"You already know the recipes in {item.name}.")
            return

        def finish_reading():
            if item.name not in self.known_recipes:
                self.known_recipes.append(item.name)
                for r in recipes_taught:
                    display_message_player(f"Learned how to craft: {r.output_name}")
            else:
                 display_message_player(f"You reviewed {item.name}.")

        self.start_action(f"Reading {item.name}", 3.0, finish_reading)

    def unload_weapon(self, game, weapon):
        if not weapon.ammo_type or weapon.load <= 0:
            return

        ammo = Item.create_from_name(weapon.ammo_type)
        if not ammo:
            print(f"Error creating ammo: {weapon.ammo_type}")
            return

        ammo.load = weapon.load
        weapon.load = 0
        
        display_message_player(f"Unloaded {int(ammo.load)} {ammo.name} from {weapon.name}.")

        self.stack_item_in_inventory(ammo)
        
        if ammo.load <= 0:
            return 

        if len(self.inventory) < self.base_inventory_slots:
             self.inventory.append(ammo)
             return
        
        if self.backpack and len(self.backpack.inventory) < (self.backpack.capacity or 0):
             self.backpack.inventory.append(ammo)
             display_message_player("Moved to backpack.")
             return

        ammo.rect.center = self.rect.center

        if find_free_tile(ammo.rect, game.obstacles, [], initial_pos=self.rect.center, max_radius=1):
            game.items_on_ground.append(ammo)
            display_message_player("Inventory full. Dropped ammo on ground.")
        else:
             weapon.load = ammo.load
             display_message_player("No space to unload ammo!")

    def _get_source_inventory(self, source_type, container_item=None):
        if source_type == 'inventory':
            return self.inventory
        elif source_type == 'belt':
            return self.belt
        
        elif (source_type == 'container' or source_type == 'nearby') and container_item:
            return container_item.inventory
        return None

    def equip_item_to_belt(self, item, source_type, item_index, container_item=None):
        if not any(slot is None for slot in self.belt):
            display_message_player("Belt is full.")
            return False
        source_inventory = self._get_source_inventory(source_type, container_item)
        if source_inventory is None:
             print(f"Error: Could not find source inventory for {source_type}")
             return False

        for i, slot in enumerate(self.belt):
            if slot is None:
                self.belt[i] = item
                source_inventory.pop(item_index)
                display_message_player(f"Equipped {item.name} to belt.")
                return True
        return False

    def consume_item(self, item, source_type, item_index, container_item=None, is_auto_drink=False, game=None, target_part=None):
        if self.action_timer > 0 and not is_auto_drink:
            display_message_player("Busy...")
            return False

        if getattr(item, 'item_type', '').lower() == 'recipe':
            self.read_recipe_book(item)
            return True

        if hasattr(item, 'require') and item.require:
            required_list = item.require if isinstance(item.require, list) else [item.require]
            found_req = False
            
            def has_valid_item(name):
                for it in self.belt:
                    if it and it.name == name:
                        if it.load is not None and it.load <= 0: continue
                        return True
                for it in self.inventory:
                    if it and it.name == name:
                         if it.load is not None and it.load <= 0: continue
                         return True
                if self.backpack:
                    for it in self.backpack.inventory:
                        if it and it.name == name:
                             if it.load is not None and it.load <= 0: continue
                             return True
                return False

            for req_name in required_list:
                if has_valid_item(req_name):
                    found_req = True
                    break
            
            if not found_req:
                req_str = " or ".join(required_list)
                display_message_player(f"Requires {req_str} to use.")
                return False

        source_inventory = self._get_source_inventory(source_type, container_item)
        
        if not item.item_type.startswith('consumable'):
            return False

        if item.load <= 0:
            display_message_player(f"Cannot use {item.name}, it is empty.")
            return False
            
        duration_mult = 1.0
        if item.item_type == 'consumable_medication' or 'Medkit' in item.name:
            duration_mult = 2.0
        elif 'Water' in item.name or item.item_type == 'consumable_drink':
            duration_mult = 1.0
        elif item.item_type == 'consumable_food':
            duration_mult = 1.0
            
        def execute_consume():
            status_effect_legacy = getattr(item, 'status_effect', None)
            ammo_type = getattr(item, 'ammo_type', None) 
            consumed = False

            if item.item_type == 'consumable_ammo' or status_effect_legacy == 'ammo' or ammo_type is not None:
                self.reload_active_weapon(game=game)
                return 

            if hasattr(item, 'effects') and item.effects:
                for effect in item.effects:
                    eff_type = effect['type'] 
                    targets = effect['targets'] 
                    val = random.randint(effect['min'], effect['max'])
                    
                    for target_stat in targets:
                        if eff_type == 'restore' and target_stat == 'health':
                             part = target_part.lower() if target_part else self.get_most_damaged_part()
                             
                             if part and part in self.body_parts:
                                 current_part_val = self.body_parts[part]['value']
                                 if current_part_val >= 100.0:
                                     display_message_player(f"{part.capitalize()} is already healthy.")
                                     consumed = False
                                 else:
                                     new_part_val = min(100.0, current_part_val + val)
                                     self.body_parts[part]['value'] = new_part_val
                                     self.update_global_health()
                                     display_message_player(f"Used {item.name}. Restored {val} on {part.capitalize()}.")
                                     consumed = True
                             elif part:
                                 display_message_player(f"Cannot heal {part}.")
                                 consumed = False
                             else:
                                 display_message_player(f"Health is full.")
                                 consumed = False
                                 
                        elif hasattr(self, target_stat):
                            current_val = getattr(self, target_stat)
                            
                            if eff_type == 'restore':
                                stat_cap = 100.0
                                if target_stat == 'health': stat_cap = self.max_health # Fallback
                                elif target_stat == 'stamina': stat_cap = self.max_stamina
                                elif target_stat == 'tireness': stat_cap = self.max_tireness

                                new_val = min(stat_cap, current_val + val)
                                setattr(self, target_stat, new_val)
                                display_message_player(f"Used {item.name}. Restored {val} {target_stat.capitalize()}.")
                                consumed = True

                            elif eff_type == 'reduce':
                                min_cap = 0.0
                                new_val = max(min_cap, current_val - val)
                                setattr(self, target_stat, new_val)
                                display_message_player(f"Used {item.name}. Reduced {target_stat.capitalize()} by {val}.")
                                consumed = True
            
            elif status_effect_legacy and hasattr(self, status_effect_legacy):
                pass
            
            else:
                if not consumed:
                    display_message_player(f"Cannot consume {item.name}: no valid effects found.")
                    return 

            if consumed:
                item.load -= 1
                if item.load <= 0:
                    if source_type == 'belt':
                        self.belt[item_index] = None
                    elif source_type == 'inventory':
                        if item_index < len(self.inventory) and self.inventory[item_index] == item:
                            self.inventory.pop(item_index)
                    elif source_type == 'gear':
                        self.clothes[item_index] = None
                    elif (source_type == 'container' or source_type == 'nearby') and container_item:
                        if item_index < len(container_item.inventory) and container_item.inventory[item_index] == item:
                            container_item.inventory.pop(item_index)

        if is_auto_drink:
            execute_consume()
            return True
        else:
            return self.start_action(f"Using {item.name}", duration_mult, execute_consume, xp_reward=5)
    
    def toggle_utility_item(self, item, source, index, container_item):
        if not hasattr(item, 'state'):
            return

        new_name = ""
        if item.state == "on":
            new_name = item.name.replace(" on", " off")
        elif item.state == "off":
            if item.durability is not None and item.durability <= 0:
                display_message_player(f"Cannot turn on {item.name}, it's out of power.")
                return
            
            if item.fuel_type == "Matches":
                matches, m_source, m_index, m_container = self.find_fuel("Matches")
                if not matches:
                    display_message_player("No matches to light the lantern.")
                    return
                
                matches.load -= 1
                if matches.load <= 0:
                    m_inv = self._get_source_inventory(m_source, m_container)
                    if m_inv and m_index < len(m_inv) and m_inv[m_index] == matches:
                        m_inv.pop(m_index)
            
            new_name = item.name.replace(" off", " on")
        
        if not new_name:
            return

        new_item = Item.create_from_name(new_name)
        if not new_item:
            print(f"Error: Could not find item template for '{new_name}'")
            return

        new_item.durability = item.durability
        new_item.load = item.load

        if source and index is not None:
            source_inventory = self._get_source_inventory(source, container_item)
            if source_inventory and index < len(source_inventory) and source_inventory[index] == item:
                source_inventory[index] = new_item
            else:
                print(f"Error: Could not find item {item.name} in {source} to toggle.")
        elif item in self.belt:
             self.belt[self.belt.index(item)] = new_item
        elif item in self.inventory:
             self.inventory[self.inventory.index(item)] = new_item
        
    def reload_utility_item(self, item, source, index, container_item):
        if not item.fuel_type:
            display_message_player(f"{item.name} does not use fuel.")
            return

        fuel_item, f_source, f_index, f_container = self.find_fuel(item.fuel_type)
        if not fuel_item:
            display_message_player(f"No {item.fuel_type} found to reload.")
            return
            
        max_dur = item.max_durability
        dur_needed = max_dur - (item.durability or 0)
        
        if dur_needed <= 0:
            display_message_player(f"{item.name} durability is already full.")
            return

        if fuel_item.load <= 0:
            display_message_player(f"No {item.fuel_type} left to use.")
            return

        fuel_item.load -= 1
        
        item.durability = max_dur
        
        display_message_player(f"Used 1 {item.fuel_type} to reload {item.name}. Durability set to: {item.durability:.0f}")

        if fuel_item.load <= 0:
            f_inv = self._get_source_inventory(f_source, f_container)
            if f_inv and f_index < len(f_inv) and f_inv[f_index] == fuel_item:
                f_inv.pop(f_index)
    
    def find_item_and_stack(self, source, index, container_item):
        source_inventory = self._get_source_inventory(source, container_item)
        if source_inventory and 0 <= index < len(source_inventory):
            item = source_inventory[index]
            return item, source_inventory
        
        if source == 'backpack' and self.backpack:
            return self.backpack, [self] 
        
            
        return None, None

    def drop_item_stack(self, game, source, index, container_item, quantity):
        item, source_inventory = self.find_item_and_stack(source, index, container_item)
        if not item:
            print("Error: Could not find item to drop.")
            return

        item_to_drop = None
        if quantity == 'all' or quantity >= item.load:
            item_to_drop = self.drop_item(game, source, index, container_item)
        elif quantity > 0 and item.load > 0:
            item_to_drop = Item.create_from_name(item.name)
            if not item_to_drop: return

            transfer_amount = min(item.load, quantity)
            item_to_drop.load = transfer_amount
            item_to_drop.durability = item.durability 
            
            item.load -= transfer_amount
            if item.load <= 0:
                self.drop_item(game, source, index, container_item) 
        
        if item_to_drop:
            offset_x = random.randint(-8, 8)
            offset_y = random.randint(-8, 8)
            
            item_to_drop.rect.center = (
                self.rect.centerx + offset_x, 
                self.rect.centery + offset_y
            )
            item_to_drop.x = item_to_drop.rect.x
            item_to_drop.y = item_to_drop.rect.y
            
            if item_to_drop not in game.items_on_ground:
                game.items_on_ground.append(item_to_drop)
                
            return item_to_drop
            
        return None


    def transfer_item_stack(self, source, index, container_item, target_container, game=None):
        if self.action_timer > 0:
            display_message_player("Busy...")
            return

        def execute_transfer():
            item = None
            source_inventory = self._get_source_inventory(source, container_item) 
            
            if source == 'backpack':
                item = self.backpack
            elif source_inventory and 0 <= index < len(source_inventory):
                item = source_inventory[index] 

            targets = []
            
            if target_container is self:
                targets.append({
                    'inv': self.inventory, 
                    'cap': self.base_inventory_slots, 
                    'name': "Inventory"
                })
                if self.backpack:
                    targets.append({
                        'inv': self.backpack.inventory, 
                        'cap': self.backpack.capacity or 0, 
                        'name': self.backpack.name
                    })
            elif target_container and hasattr(target_container, 'inventory'):
                targets.append({
                    'inv': target_container.inventory, 
                    'cap': target_container.capacity or 0, 
                    'name': target_container.name
                })
            else:
                print("Error: Invalid source or target container.")
                return

            if not item: return
            
            remaining_load = item.load
            
            for target in targets:
                target_inv = target['inv']
                for target_item in target_inv:
                    if target_item.can_stack_with(item):
                        available_space = target_item.capacity - target_item.load
                        transfer = min(available_space, remaining_load)
                        
                        target_item.load += transfer
                        remaining_load -= transfer
                        item.load = remaining_load 
                        
                        if remaining_load <= 0:
                            break
                if remaining_load <= 0:
                    break
            
            if item.load <= 0:
                if source == 'backpack':
                    self.backpack = None
                elif source_inventory and 0 <= index < len(source_inventory) and source_inventory[index] == item:
                    source_inventory.pop(index)
                    if game and getattr(container_item, 'item_type', '') == 'ground' and item in game.items_on_ground:
                        game.items_on_ground.remove(item)
                
                dest_name = targets[0]['name'] if targets else "Inventory"
                display_message_player(f"Merged all of {item.name} into {dest_name}.")
                return
                
            if remaining_load > 0:
                transferred = False
                for target in targets:
                    target_inv = target['inv']
                    target_cap = target['cap']
                    target_name = target['name']

                    if len(target_inv) < target_cap:
                        new_stack = Item.create_from_name(item.name)
                        new_stack.load = remaining_load
                        new_stack.durability = item.durability 
                        target_inv.append(new_stack)
                        
                        if source == 'backpack':
                            self.backpack = None
                        elif source_inventory and 0 <= index < len(source_inventory) and source_inventory[index] == item:
                            source_inventory.pop(index)
                            if game and getattr(container_item, 'item_type', '') == 'ground' and item in game.items_on_ground:
                                game.items_on_ground.remove(item)

                        display_message_player(f"Sent {remaining_load} {item.name} to {target_name}.")
                        transferred = True
                        break 
                
                if not transferred:
                    display_message_player(f"Inventory full. Could not transfer remaining {remaining_load}.")

        def is_on_player(container):
            if not container: return False
            if container is self: return True 
            if container is self.backpack: return True
            if container in self.belt: return True
            if container in self.clothes.values(): return True
            return False

        source_is_on_player = (
            source in ['inventory', 'belt', 'backpack', 'gear'] or
            (source == 'container' and is_on_player(container_item))
        )

        target_is_on_player = is_on_player(target_container)
        
        needs_timer = not (source_is_on_player and target_is_on_player)
        action_label = "Looting" if not source_is_on_player and target_is_on_player else "Transferring"

        if needs_timer:
            self.start_action(action_label, 1.5, execute_transfer, xp_reward=2)
        else:
            execute_transfer()


    def drop_item(self, game, source, index, container_item=None):
        if self.drop_cooldown > 0:
            display_message_player("Cannot drop items so quickly.")
            return None

        item_to_drop = None
        source_inventory = None 
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
            source_inventory = [self] 
            source_index = 0 
        
        elif source == 'gear':
            item_to_drop = self.clothes.get(index) 
            self.clothes[index] = None
            source_inventory = [self] 
            source_index = 2 
        elif (source == 'container' or source == 'nearby') and container_item and index < len(container_item.inventory):
            item_to_drop = container_item.inventory.pop(index)
            source_inventory = container_item.inventory
            source_index = index

        if item_to_drop:
            offset_x = random.randint(-8, 8)
            offset_y = random.randint(-8, 8)
            
            item_to_drop.rect.center = (
                self.rect.centerx + offset_x, 
                self.rect.centery + offset_y
            )
            
            item_to_drop.x = item_to_drop.rect.x
            item_to_drop.y = item_to_drop.rect.y
            
            game.items_on_ground.append(item_to_drop)
            self.drop_cooldown = 10 
            
            return item_to_drop

        return None

    def stack_item_in_inventory(self, item_to_stack):
        if not item_to_stack.is_stackable():
            return 

        for item in self.inventory:
            if item.can_stack_with(item_to_stack):
                available_space = item.capacity - item.load
                transfer = min(available_space, item_to_stack.load)
                item.load += transfer
                item_to_stack.load -= transfer
                if item_to_stack.load <= 0:
                    return 
        
        for item in self.belt:
            if item and item.can_stack_with(item_to_stack):
                available_space = item.capacity - item.load
                transfer = min(available_space, item_to_stack.load)
                item.load += transfer
                item_to_stack.load -= transfer
                if item_to_stack.load <= 0:
                    return 

    def destroy_broken_weapon(self, broken_weapon):
        if self.active_weapon == broken_weapon:
            self.active_weapon = None

        for i, item in enumerate(self.belt):
            if item == broken_weapon:
                self.belt[i] = None
                display_message_player(f"{broken_weapon.name} broke and was removed from your belt.")
                return

        try:
            self.inventory.remove(broken_weapon)
            display_message_player(f"{broken_weapon.name} broke and was removed from your inventory.")
        except ValueError:
            pass

    def find_water_to_auto_drink(self):
        for i, item in enumerate(self.belt):
            if item and 'Water' in item.name and item.load > 0:
                print(f"Found water in belt slot {i}") 
                return item, 'belt', i, None 

        for i, item in enumerate(self.inventory):
            if item and 'Water' in item.name and item.load > 0:
                print(f"Found water in inventory slot {i}") 
                return item, 'inventory', i, None 

        for slot, item in self.clothes.items():
            if item and 'Water' in item.name and item.load > 0:
                print(f"Found water in gear slot {slot}")
                return item, 'gear', slot, None

        for i, container_item in enumerate(self.inventory):
            if container_item and hasattr(container_item, 'inventory') and container_item.inventory:
                print(f"Checking inside container '{container_item.name}' in inventory slot {i}") 
                for sub_index, sub_item in enumerate(container_item.inventory):
                    if sub_item and 'Water' in sub_item.name and sub_item.load > 0:
                        print(f"Found water inside '{container_item.name}' at sub-index {sub_index}")
                        return sub_item, 'container', sub_index, container_item

        if self.backpack and hasattr(self.backpack, 'inventory'):
            for i, item in enumerate(self.backpack.inventory):
                if item and 'Water' in item.name and item.load > 0:
                    print(f"Found water in backpack slot {i}") 
                    return item, 'container', i, self.backpack

        print("No water found for auto-drink.") 
        return None, None, None, None