import time
import pygame
import random
import math

import core.data.config
from core.data.config import GAME_WIDTH, GAME_HEIGHT, TILE_SIZE, BLUE, AUTO_DRINK
from core.entities.item.item import Item
from core.entities.player.player_progression import PlayerProgression
from core.messages import display_message_player
from core.data.recipe_manager import RecipeManager
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS
from core.data.progression_loader import PROGRESSION_CONFIG

# Import Mixins
from core.entities.player.player_stats import PlayerStats
from core.entities.player.player_movement import PlayerMovement
from core.entities.player.player_graphics import PlayerGraphics
from core.entities.player.player_inventory import PlayerInventory
from core.entities.player.player_actions import PlayerActions
from core.entities.player.player_combat import PlayerCombat

class Player(PlayerStats, PlayerMovement, PlayerGraphics, 
             PlayerInventory, PlayerActions, PlayerCombat):
             
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
            'ranged': 0.0, 'lucky': 0.0, 'agility': 0.0
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
        self.dialog_history = data.get('dialog_history', [])

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
        # [CHANGED] Increased base inventory slots from 5 to 10
        self.base_inventory_slots = 10
        
        self.clothes_slots =  ['hair', 'head','legs', 'feet', 'body','util','arms', 'hands', 'facial']
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
        # [NEW] Create collision mask from the player's image
        if self.image:
            self.mask = pygame.mask.from_surface(self.image)
        else:
            self.mask = None

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
        self.action_xp_attr = 'agility'
        self.saved_detection_radius = None

    @property
    def current_weight(self):
        total = 0.0
        # Belt
        for item in self.belt:
             if item: total += item.get_total_weight()
        # Inventory
        for item in self.inventory:
             total += item.get_total_weight() 
        # Clothes
        for item in self.clothes.values():
             if item: total += item.get_total_weight()
        # Backpack
        if self.backpack:
             total += self.backpack.get_total_weight()
        
        return total

    @property
    def max_carry_weight(self):
        # Base 10 + scaling with strength
        strength = self.progression.get_strength(self)
        return 5.0 + (strength * 1.5)

    def update_stats(self, game):
        current_time = time.time()

        if self.action_timer > 0:
            # Apply fast forward to action timer
            multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
            self.action_timer -= multiplier
            self.vx = 0
            self.vy = 0
            self.is_running = False

            if self.action_timer <= 0:
                if self.action_callback:
                    self.action_callback()
                    self.action_callback = None
                    if self.action_xp_reward > 0:
                        self.progression.add_xp(self, self.action_xp_attr, self.action_xp_reward)
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

        is_sleeping_or_resting = self.is_sleeping or is_active_resting
        
        # Entering sleep state
        if is_sleeping_or_resting and self.saved_detection_radius is None:
            self.saved_detection_radius = core.data.config.ZOMBIE_DETECTION_RADIUS
            core.data.config.ZOMBIE_DETECTION_RADIUS = core.data.config.ZOMBIE_DETECTION_RADIUS * core.data.config.ZOMBIE_MULTIPLIER
            print(f"Stealth Mode: Radius set to {core.data.config.ZOMBIE_DETECTION_RADIUS}")

        # Exiting sleep state
        elif not is_sleeping_or_resting and self.saved_detection_radius is not None:
            core.data.config.ZOMBIE_DETECTION_RADIUS = self.saved_detection_radius
            self.saved_detection_radius = None
            print(f"Stealth Mode Over: Radius restored to {core.data.config.ZOMBIE_DETECTION_RADIUS}")

        if not self.is_sleeping and not is_active_resting:
            self.tireness = min(self.max_tireness, self.tireness - 0.002)

        if not self.is_sleeping and is_active_resting:
            if self.stamina < self.max_stamina:
                self.stamina = min(self.max_stamina, self.stamina + 0.5)
            if self.tireness < self.max_tireness:
                self.tireness = min(self.max_tireness, self.tireness + 0.03)

        if self.is_sleeping:
            game.is_fast_forwarding = True
            restore_amount = 0.5
            self.tireness = max(0.0, self.tireness + restore_amount)

            if self.tireness >= self.max_tireness:
                self.tireness = self.max_tireness
                self.is_sleeping = False
                game.is_fast_forwarding = False
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
        
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
        
        # Increase infection over time if infected
        if self.infection > 0:
            passive_inf_gain = PROGRESSION_CONFIG.get_stat('infection', 'passive_gain', 0.002)
            self.infection = min(100.0, self.infection + (passive_inf_gain * multiplier))
            
        is_starving = self.food <= 0
        is_dehydrated = self.water <= 0
        is_infected = self.infection > 0
        
        # Do not regenerate body damage if starving, dehydrated, or infected!
        # can_regen = not (is_starving or is_dehydrated or is_infected)
        
        #if can_regen:
        #    healed_any = False
        #    for part, data in self.body_parts.items():
        #        if data['value'] < 100.0:
        #            rate = PROGRESSION_CONFIG.healing_rates.get(part, 0.005) * multiplier
        #            data['value'] = min(100.0, data['value'] + rate)
        #            healed_any = True
        #    if healed_any:
        #        self.update_global_health()

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
            
            # --- Health Decay from Negative States ---
            damage_to_take = 0.0
            if self.water <= 0:
                damage_to_take += 5.0
            if self.food <= 0:
                damage_to_take += 5.0
            if self.infection > 0:
                damage_to_take += 5.0 * (self.infection / 100.0)  # Infection damage scales with severity
                
            if damage_to_take > 0:
                # Apply damage to ALL body parts. This accurately mimics a systemic failure
                # and forces global health (which is an average) to decay by exactly 'damage_to_take'%.
                for p in self.body_parts.keys():
                    self.body_parts[p]['value'] = max(0.0, self.body_parts[p]['value'] - damage_to_take)
                self.update_global_health()

            if AUTO_DRINK and self.water <= core.data.config.AUTO_DRINK_THRESHOLD:
                water_item, source, index, container = self.find_water_to_auto_drink()
                if water_item:
                    self.consume_item(water_item, source, index, container, is_auto_drink=True, game=game)
        
        # --- Overweight Logic ---
        overweight_ratio = 0
        if self.max_carry_weight > 0:
             overweight_ratio = self.current_weight / self.max_carry_weight
        
        if overweight_ratio > 1.0:
             loss = 0.01 * (overweight_ratio - 1.0) 
             for part in self.body_parts.values():
                 part['value'] = max(0.0, part['value'] - loss)
             
             self.update_global_health()
             
             if self.is_running and is_moving:
                  self.progression.add_xp(self, 'strength', 0.001)

        all_inventories = [self.belt, self.inventory]
        if self.backpack:
            all_inventories.append(self.backpack.inventory)
            
        for inv in all_inventories:
            for item in inv:
                if getattr(item, 'state', 'off') == 'on':
                    if item.durability is not None:
                        item.durability -= 0.005 
                        if item.durability <= 0:
                            item.durability = 0
                            self.toggle_utility_item(item, None, None, None) 

        # --- NEW: Weather & Barefoot Mechanics ---
        # 1. Determine if under a roof
        is_under_roof = False
        if getattr(game, 'roof_data', None) and getattr(game, 'current_layer_index', 1) != 2:
            px = int(self.rect.centerx // TILE_SIZE)
            py = int(self.rect.centery // TILE_SIZE)
            if 0 <= py < len(game.roof_data) and 0 <= px < len(game.roof_data[py]):
                r_key = game.roof_data[py][px]
                if r_key and r_key != ' ':
                    is_under_roof = True

        is_outside = getattr(game, 'current_layer_index', 1) != 2 and not is_under_roof
        
        # [CHANGED] 2. Rain Sickness Infection (Uses Defense instead of weather_protection)
        if is_outside and getattr(game.world_time, 'weather', 'CLEAR') == 'RAIN' and self.vehicle is None:
            # Uses the same calculation for damage, 5.0 defense = 100% protection against elements
            total_defence = self.get_total_defence()
            total_weather_protection = min(1.0, total_defence / 5.0)
            
            # Base infection increase per tick while standing in rain
            base_rain_infection = 0.005 
            actual_rain_infection = base_rain_infection * (1.0 - total_weather_protection)
            
            if actual_rain_infection > 0:
                self.infection = min(100.0, self.infection + actual_rain_infection)

        # 3. Barefoot Damage
        if is_moving and self.vehicle is None:
            # Check if player is not wearing anything on feet
            if not self.clothes.get('feet'):
                foot_dmg = 0.02 if self.is_running else 0.005
                self.take_damage_to_part('feet', foot_dmg)
                
                # Show message rarely
                if random.random() < 0.002:
                    display_message_player("Your bare feet are bleeding!")


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

    def has_line_of_sight(self, target_rect, obstacles):
        """Checks if there is an uninterrupted line between player and target."""
        start_pos = self.rect.center
        end_pos = target_rect.center

        for obs in obstacles:
            if obs.clipline(start_pos, end_pos):
                return False

        return True