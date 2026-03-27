import time
import pygame
import random
import math

import core.data.config
from core.data.config import GAME_WIDTH, GAME_HEIGHT, TILE_SIZE, BLUE, AUTO_DRINK
from core.entities.item.item import Item
from core.entities.player.player_progression import PlayerProgression
from core.messages import display_message
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

from core.data.localization import tr

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
        
        
        self.attributes = data.get('attributes', {
            'strength': 0.0, 'fitness': 0.0, 'melee': 0.0, 
            'ranged': 0.0, 'lucky': 0.0, 'agility': 0.0, 'intelligence': 0.0
        })

        self.max_health = stats.get('health', 100.0)
        self.health = self.max_health
        
        self.max_tireness = stats.get('tireness', 100.0)
        self.tireness = stats.get('tireness', self.max_tireness)
        self.max_stamina = stats.get('stamina', 100.0)
        self.stamina = stats.get('stamina', self.max_stamina)
        self.water = stats.get('water', 100.0)
        self.food = stats.get('food', 100.0)
        self.infection = stats.get('infection', 0.0)
        self.anxiety = stats.get('anxiety', 0.0)
        self.intelligence = stats.get('intelligence', 0.0)

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
        self.active_weapon = None
        self.belt = [None] * 5
        self.last_decay_time = time.time()
        # [CHANGED] Increased base inventory slots from 5 to 10
        self.base_inventory_slots = 10
        
        self.clothes_slots =  ['hair', 'head','legs', 'feet', 'body','util','arms', 'hands', 'facial']
        self.clothes = {slot: None for slot in self.clothes_slots}
        
        chosen_clothes_dict = data.get('clothes', {})
        self.clothes = {slot: None for slot in self.clothes_slots}
        
        chosen_clothes_dict = data.get('clothes', {})
        clothes_colors_dict = data.get('clothes_colors', {}) # Fetch colors from setup data
        
        for slot, item_data in chosen_clothes_dict.items():
            if item_data and item_data != "None" and slot in self.clothes_slots:
                if isinstance(item_data, dict):
                    # It's loading from a save file, from_dict handles the color now!
                    self.clothes[slot] = Item.from_dict(item_data)
                else:
                    # It's a fresh spawn from Player Builder
                    setup_color = clothes_colors_dict.get(slot, (255, 255, 255))
                    self.clothes[slot] = Item.create_from_name(item_data, force_color=setup_color)
                    
                # Apply the specific color to the player's instantiated item
                if self.clothes[slot]:
                    # Determine color: prioritize the loaded item's color, fallback to setup data
                    assigned_color = getattr(self.clothes[slot], 'color', None)
                    if not assigned_color or assigned_color == (255,255,255):
                         assigned_color = clothes_colors_dict.get(slot, (255, 255, 255))
                         
                    self.clothes[slot].color = assigned_color
                    
                    # Pre-tint the item's ground/inventory image right now!
                    if self.clothes[slot].image and assigned_color != (255, 255, 255):
                        tinted = self.clothes[slot].image.copy()
                        tinted.fill((*assigned_color, 255)[:4], special_flags=pygame.BLEND_RGBA_MULT)
                        self.clothes[slot].image = tinted

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
        for item in self.clothes.values():
             if item: total += item.get_total_weight()
        
        return total

    @property
    def max_carry_weight(self):
        # Base 10 + scaling with strength
        _, flat_bonus = self.progression.get_derived_bonus('carry_weight')
        return 5.0 + flat_bonus

    def update_stats(self, game):
        current_time = time.time()

        if self.action_timer > 0:
            # Apply fast forward to action timer
            multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
            self.action_timer -= multiplier * game.dt_mult
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
            self.chat_timer -= game.dt_mult
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
        
        tile_name = tile.get('name', '').lower() if tile else ""
        is_recovery_tile = "bed" in tile_name or "bench" in tile_name
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

        # Get dynamic stats from your progression.xml
        tireness_drain = abs(PROGRESSION_CONFIG.get_stat('tireness', 'night_decay', -0.002))
        stamina_regen = PROGRESSION_CONFIG.get_stat('stamina', 'regen_base', 0.02)
        tireness_recovery = PROGRESSION_CONFIG.get_stat('tireness', 'day_recovery', 0.001)

        if not self.is_sleeping and not is_active_resting:
            # Apply stamina penalty to tireness if stamina is depleted
            stamina_penalty = abs(PROGRESSION_CONFIG.get_stat('tireness', 'stamina_penalty', -0.005)) if self.stamina <= 0 else 0
            total_drain = (tireness_drain + stamina_penalty) * game.dt_mult
            self.tireness = max(0.0, self.tireness - total_drain)

        if not self.is_sleeping and is_active_resting:
            # [CHANGED] Fetch multipliers from XML dynamically
            stam_mult = PROGRESSION_CONFIG.get_stat('stamina', 'bed_recovery_mult', 2.0) if is_recovery_tile else 1.0
            tire_mult = PROGRESSION_CONFIG.get_stat('tireness', 'bed_recovery_mult', 2.0) if is_recovery_tile else 1.0
            
            if self.stamina < self.max_stamina:
                self.stamina = min(self.max_stamina, self.stamina + (stamina_regen * stam_mult * game.dt_mult))
            if self.tireness < self.max_tireness:
                self.tireness = min(self.max_tireness, self.tireness + (tireness_recovery * tire_mult * game.dt_mult))

        if self.is_sleeping:
            game.is_fast_forwarding = True
            
            # [CHANGED] Fetch sleep multipliers and health regen from XML
            sleep_restore = 0.5 * game.dt_mult
            
            if is_recovery_tile:
                sleep_mult = PROGRESSION_CONFIG.get_stat('tireness', 'bed_sleep_mult', 1.5)
                sleep_restore *= sleep_mult
                
                # Recover health while sleeping on beds/benches
                base_health_regen = PROGRESSION_CONFIG.get_stat('health', 'bed_sleep_regen', 0.01)
                self.health = min(self.max_health, self.health + (base_health_regen * game.dt_mult))

            self.tireness = min(self.max_tireness, self.tireness + sleep_restore)
            self.stamina = min(self.max_stamina, self.stamina + sleep_restore)

            if self.tireness >= self.max_tireness:
                self.tireness = self.max_tireness
                self.is_sleeping = False
                game.is_fast_forwarding = False
                display_message(tr('msg', "You wake up refreshed."))

        mouse_buttons = pygame.mouse.get_pressed()
        is_aiming = keys[pygame.K_LCTRL] or keys[pygame.K_LCTRL]
        is_firing = mouse_buttons[0]

        if not self.is_sleeping and is_aiming and is_firing:
             if self.active_weapon and getattr(self.active_weapon, 'machine_gun', False):
                  from core.events.mouse import handle_attack
                  handle_attack(game, pygame.mouse.get_pos())

        if is_moving:
            anim_speed = 25 if self.is_running else 15
            self.walk_anim_angle = math.sin(current_time * anim_speed) * 2
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
                    base_volume=random.uniform(0.2, 0.4),
                    pitch_variance=0.15)
                
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
            self.infection = min(100.0, self.infection + (passive_inf_gain * multiplier * game.dt_mult))
            
        is_starving = self.food <= 20.0
        is_dehydrated = self.water <= 20.0
        is_infected = self.infection > 0
        
        damage_this_frame = 0.0
        if is_starving:
            damage_this_frame += 0.005 * multiplier * game.dt_mult
        if is_dehydrated:
            damage_this_frame += 0.003 * multiplier * game.dt_mult
        if is_infected:
            damage_this_frame += 0.005 * (self.infection / 100.0) * multiplier * game.dt_mult
            
        if damage_this_frame > 0:
            self.health = max(0.0, self.health - damage_this_frame)

        if getattr(game, 'is_fast_forwarding', False):
             dt = 1.0 / 60.0
             decay_boost = dt * (game.fast_forward_speed - 1.0)
             self.last_decay_time -= decay_boost

        decay_rate = PROGRESSION_CONFIG.get_stat('metabolism', 'decay_rate_seconds', 5.0)
        
        # FIXED TYPO: Removed the extra "- current_time" so the math evaluates correctly in seconds
        if current_time - self.last_decay_time >= decay_rate:
            water_mod = 1.0 + (self.progression.get_water_bonus(self) / 100.0)
            food_mod = 1.0 + (self.progression.get_food_bonus(self) / 100.0)
            
            base_water_decay = PROGRESSION_CONFIG.get_stat('water', 'decay_amount', 0.2)
            base_food_decay = PROGRESSION_CONFIG.get_stat('food', 'decay_amount', 0.1)
            
            water_decay = max(0, base_water_decay * water_mod)
            food_decay = max(0, base_food_decay * food_mod)
            
            self.water = max(0, self.water - water_decay)
            self.food = max(0, self.food - food_decay)

            self.last_decay_time = current_time
            

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
             self.health = max(0.0, self.health - loss)
             
             if self.is_running and is_moving:
                  self.progression.add_xp(self, 'strength', 0.001)

        all_inventories = [self.belt, self.inventory]
            
        for inv in all_inventories:
            for item in inv:
                if getattr(item, 'state', 'off') == 'on':
                    if item.durability is not None:
                        item.durability -= 0.005 * game.dt_mult
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
            base_rain_infection = PROGRESSION_CONFIG.get_stat('infection', 'passive_gain_on_rain', 0.002)
            actual_rain_infection = base_rain_infection * (1.0 - total_weather_protection)
            
            if actual_rain_infection > 0:
                self.infection = min(100.0, self.infection + actual_rain_infection)

        


        def msg(text):
            display_message(text)

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
                    display_message(f"{tr('msg', 'Discarded empty')} {tr('item', item.name)}.")

        if self.is_reloading:
            self.reload_timer -= game.dt_mult
            if self.reload_timer <= 0:
                self._finish_reload()

        if self.health <= 1:
            print("GAME OVER: Health depleted!")
            return True
        if self.infection >= 100:
            print("GAME OVER: Zombified!")
            return True

        if self.drop_cooldown > 0:
            self.drop_cooldown -= game.dt_mult

        if self.layer_switch_cooldown > 0:
            self.layer_switch_cooldown -= game.dt_mult

        return False

    def has_line_of_sight(self, target_rect, obstacles, game=None):
        """Checks if there is an uninterrupted line between player and target."""
        start_pos = self.rect.center
        end_pos = target_rect.center

        for obs in obstacles:
            if obs.clipline(start_pos, end_pos):
                # [NEW] Check if this obstacle tile allows visibility
                if game and hasattr(game, 'map_manager'):
                    gx = obs.centerx // TILE_SIZE
                    gy = obs.centery // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    if tile_def and tile_def.get('is_visible'):
                        continue # It's transparent, keep checking further!
                
                return False

        return True