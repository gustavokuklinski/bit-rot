# core/entities/player/player.py

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
        self.is_moving = False # Safety initialization
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
        
        self.max_stamina = stats.get('stamina', 100.0)
        self.stamina = stats.get('stamina', self.max_stamina)
        self.water = stats.get('water', 100.0)
        self.food = stats.get('food', 100.0)
        self.infection = stats.get('infection', 0.0)
        self.anxiety = stats.get('anxiety', 0.0)
        self.intelligence = stats.get('intelligence', 0.0)

        self.sex = data.get('sex', 'Male')
        self.traits = data.get('traits', [])
        self.quests = data.get('quests', [])
        self.completed_quests = data.get('completed_quests', [])
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
        self.base_inventory_slots = 10
        
        self.clothes_slots =  ['hair', 'head','legs', 'feet', 'body','util','arms', 'hands', 'facial', 'util2', 'util3']
        self.clothes = {slot: None for slot in self.clothes_slots}
        
        chosen_clothes_dict = data.get('clothes', {})
        self.clothes = {slot: None for slot in self.clothes_slots}
        
        chosen_clothes_dict = data.get('clothes', {})
        clothes_colors_dict = data.get('clothes_colors', {}) 
        
        for slot, item_data in chosen_clothes_dict.items():
            if item_data and item_data != "None" and slot in self.clothes_slots:
                if isinstance(item_data, dict):
                    self.clothes[slot] = Item.from_dict(item_data)
                else:
                    setup_color = clothes_colors_dict.get(slot, (255, 255, 255))
                    self.clothes[slot] = Item.create_from_name(item_data, force_color=setup_color)
                    
                if self.clothes[slot]:
                    assigned_color = getattr(self.clothes[slot], 'color', None)
                    if not assigned_color or assigned_color == (255,255,255):
                         assigned_color = clothes_colors_dict.get(slot, (255, 255, 255))
                         
                    self.clothes[slot].color = assigned_color
                    
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
        if self.image:
            self.mask = pygame.mask.from_surface(self.image)
        else:
            self.mask = None

        self.layer_switch_cooldown = 0
        self.aim_angle = 0
        self.facing_direction = (0, 1)

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

        self.action_xp_attr = 'agility'
        self.saved_detection_radius = None

    @property
    def current_weight(self):
        total = 0.0
        for item in self.belt:
             if item: # FIX: Check if item exists before calling method
                total += item.get_total_weight()* 0.85
        for item in self.inventory:
             if item: # FIX: Check if item exists before calling method
                total += item.get_total_weight() 
        for item in self.clothes.values():
             if item: total += item.get_total_weight()* 0.85
        return total

    @property
    def max_carry_weight(self):
        _, flat_bonus = self.progression.get_derived_bonus('carry_weight')
        return 5.0 + flat_bonus

    def update_stats(self, game):
        current_time = time.time()

        if self.action_timer > 0:
            multiplier = 1.0
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

        if self.chat_timer > 0:
            self.chat_timer -= game.dt_mult
            if self.chat_timer <= 0:
                self.chat_text = None

        keys = pygame.key.get_pressed()
        is_moving = getattr(self, 'is_moving', False) and (self.vehicle is None)

            
        grid_x = int(self.rect.centerx // TILE_SIZE)
        grid_y = int(self.rect.centery // TILE_SIZE)
        tile = game.map_manager.get_tile_at(grid_x, grid_y)
        
        tile_name = tile.get('name', '').lower() if tile else ""
        is_recovery_tile = "bed" in tile_name or "bench" in tile_name
        
        # Stealth bonus if hiding on a bed/bench
        if is_recovery_tile and self.saved_detection_radius is None:
            self.saved_detection_radius = core.data.config.ZOMBIE_DETECTION_RADIUS
            core.data.config.ZOMBIE_DETECTION_RADIUS = core.data.config.ZOMBIE_DETECTION_RADIUS * core.data.config.ZOMBIE_MULTIPLIER
            print(f"Stealth Mode: Radius set to {core.data.config.ZOMBIE_DETECTION_RADIUS}")

        elif not is_recovery_tile and self.saved_detection_radius is not None:
            core.data.config.ZOMBIE_DETECTION_RADIUS = self.saved_detection_radius
            self.saved_detection_radius = None
            print(f"Stealth Mode Over: Radius restored to {core.data.config.ZOMBIE_DETECTION_RADIUS}")

        stamina_regen = self.progression.get_stamina_regeneration(self)

        if is_recovery_tile:
            stam_mult = PROGRESSION_CONFIG.get_stat('stamina', 'bed_recovery_mult', 3.0) 
            if self.stamina < self.max_stamina:
                self.stamina = min(self.max_stamina, self.stamina + (stamina_regen * stam_mult * game.dt_mult))
        else:
            if is_moving and self.is_running:
                # CHANGE THIS:
                # stamina_drain = PROGRESSION_CONFIG.get_stat('stamina', 'run_drain', 0.15)
                # TO THIS:
                stamina_drain = self.progression.get_stamina_consumption(True, self)
                
                self.stamina = max(0.0, self.stamina - (stamina_drain * game.dt_mult))
            else:
                if self.stamina < self.max_stamina:
                    self.stamina = min(self.max_stamina, self.stamina + (stamina_regen * game.dt_mult))

        mouse_buttons = pygame.mouse.get_pressed()

        is_aiming = getattr(self, 'is_aiming', False) 
        is_firing = mouse_buttons[0]

        if is_aiming and is_firing:
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
                step_vol = random.uniform(0.35, 0.38) if self.is_running else random.uniform(0.22, 0.25)
                
                game.sound_manager.play_sound(
                    self.sound_steps,
                    subdir='player',
                    game=game,
                    source_pos=self.rect.center,
                    base_volume=step_vol,
                    pitch_variance=0.06, # Reduced from 0.15 for a more seamless, consistent material sound
                    is_critical=True
                )
                
                if self.is_running:
                    next_delay = random.uniform(0.25, 0.35) 
                else:
                    next_delay = random.uniform(0.35, 0.5)
                self.last_step_sound_time = current_time + next_delay

        self.progression.update(self, is_moving, game)
        
        multiplier = 1.0
        
        if self.infection > 0:
            passive_inf_gain = PROGRESSION_CONFIG.get_stat('infection', 'passive_gain', 0.002)
            self.infection = min(100.0, self.infection + (passive_inf_gain * multiplier * game.dt_mult))
            
        is_starving = self.food <= 20.0
        is_dehydrated = self.water <= 20.0
        is_infected = self.infection > 0
        is_exhausted = self.stamina <= 0.0
        
        damage_this_frame = 0.0
        if is_starving:
            damage_this_frame += 0.005 * multiplier * game.dt_mult
        if is_dehydrated:
            damage_this_frame += 0.003 * multiplier * game.dt_mult
        if is_infected:
            damage_this_frame += 0.005 * (self.infection / 100.0) * multiplier * game.dt_mult
            
        # CREATIVE ADDITION: anxiety, and mechanical interruptions instead of passing out
        if is_exhausted:
            damage_this_frame += 0.001 * multiplier * game.dt_mult
            self.anxiety = min(100.0, getattr(self, 'anxiety', 0.0) + (0.005 * multiplier * game.dt_mult))

            # Mechanic: Trembling hands. Breaks focus occasionally while aiming
            if getattr(self, 'is_aiming', False) and random.random() < 0.05:
                self.current_aim_factor = max(0.1, getattr(self, 'current_aim_factor', 1.0) - 0.1)
            
        if damage_this_frame > 0:
            self.health = max(0.0, self.health - damage_this_frame)


        decay_rate = PROGRESSION_CONFIG.get_stat('metabolism', 'decay_rate_seconds', 5.0)
        
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

            def _update_items_text(items):
                for item in items:
                    if item:
                        if hasattr(item, 'update_dynamic_text'):
                            item.update_dynamic_text(self)
                        if hasattr(item, 'inventory') and item.inventory:
                            _update_items_text(item.inventory)
                            
            _update_items_text(self.inventory + self.belt + list(self.clothes.values()))

        # --- Overweight Logic ---
        overweight_amount = self.current_weight - self.max_carry_weight
        
        if overweight_amount > 0:
            health_pen_rate = PROGRESSION_CONFIG.get_stat('weight', 'overweight_health_penalty', 0.05)
            stamina_pen_rate = PROGRESSION_CONFIG.get_stat('weight', 'overweight_stamina_penalty', 0.025)

            health_reduction = health_pen_rate * overweight_amount
            stamina_reduction = stamina_pen_rate * overweight_amount

            current_max_health = self.max_health * max(0.1, 1.0 - health_reduction)
            current_max_stamina = self.max_stamina * max(0.1, 1.0 - stamina_reduction)

            if self.health > current_max_health:
                self.health -= 0.05 * game.dt_mult
                self.health = max(current_max_health, self.health)

            if self.stamina > current_max_stamina:
                self.stamina = current_max_stamina
                
            if self.is_running and is_moving:
                self.progression.add_xp(self, 'fitness', 0.001)
        else:
            overweight_ratio = 0
            if self.max_carry_weight > 0:
                overweight_ratio = self.current_weight / self.max_carry_weight
                
            t1 = PROGRESSION_CONFIG.get_stat('weight', 'penalty_threshold_1', 0.75)
            stamina_cap_mult = 1.0
            if overweight_ratio >= t1:
                stamina_cap_mult = PROGRESSION_CONFIG.get_stat('weight', 'penalty_value_1', 0.75)
                
            current_max_stamina = self.max_stamina * stamina_cap_mult
            if self.stamina > current_max_stamina:
                self.stamina = current_max_stamina

        all_inventories = [self.belt, self.inventory]
            
        for inv in all_inventories:
            for item in inv:
                if getattr(item, 'state', 'off') == 'on':
                    if item.durability is not None:
                        item.durability -= 0.005 * game.dt_mult
                        if item.durability <= 0:
                            item.durability = 0
                            self.toggle_utility_item(item, None, None, None) 

        # --- Weather & Barefoot Mechanics ---
        is_under_roof = False
        if getattr(game, 'roof_data', None) and getattr(game, 'current_layer_index', 1) != 2:
            px = int(self.rect.centerx // TILE_SIZE)
            py = int(self.rect.centery // TILE_SIZE)
            if 0 <= py < len(game.roof_data) and 0 <= px < len(game.roof_data[py]):
                r_key = game.roof_data[py][px]
                if r_key and r_key != ' ':
                    is_under_roof = True

        is_outside = getattr(game, 'current_layer_index', 1) != 2 and not is_under_roof
        
        if is_outside and getattr(game.world_time, 'weather', 'CLEAR') == 'RAIN' and self.vehicle is None:
            total_defence = self.get_total_defence()
            total_weather_protection = min(1.0, total_defence / 5.0)
            
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
                
                if getattr(item, 'disposable', False) and not getattr(item, '_drag_locked', False) and hasattr(item, 'inventory') and len(item.inventory) == 0:
                    close_modal(item)
                    self.belt[i] = None
                    display_message(f"{tr('msg', 'Discarded empty')} {tr('item', item.name)}.")

        for slot, item in self.clothes.items():
            if item:
                if hasattr(item, 'inventory') and item.inventory:
                     Item.cleanup_disposables(item.inventory, game.modals, msg)
                
                if getattr(item, 'disposable', False) and not getattr(item, '_drag_locked', False) and hasattr(item, 'inventory') and len(item.inventory) == 0:
                    close_modal(item)
                    self.clothes[slot] = None
                    display_message(f"{tr('msg', 'Discarded empty')} {tr('item', item.name)}.")

        if self.is_reloading:
            self.reload_timer -= game.dt_mult
            if self.reload_timer <= 0:
                self._finish_reload()

        # --- DEATH HOOK --- 
        if self.health <= 1:
            print("GAME OVER: Health depleted!")
            pygame.mixer.music.stop() # Silence music
            if hasattr(game, 'mp3_state'):
                 game.mp3_state['status'] = 'stopped'
            return True
            
        if self.infection >= 100:
            print("GAME OVER: Zombified!")
            pygame.mixer.music.stop() # Silence music
            if hasattr(game, 'mp3_state'):
                 game.mp3_state['status'] = 'stopped'
            return True

        if self.drop_cooldown > 0:
            self.drop_cooldown -= game.dt_mult

        if self.layer_switch_cooldown > 0:
            self.layer_switch_cooldown -= game.dt_mult

        return False

    def has_line_of_sight(self, target_rect, obstacles, game=None):
        start_pos = self.rect.center
        end_pos = target_rect.center

        for obs in obstacles:
            if obs.clipline(start_pos, end_pos):
                if game and hasattr(game, 'map_manager'):
                    gx = obs.centerx // TILE_SIZE
                    gy = obs.centery // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    if tile_def and tile_def.get('is_visible'):
                        continue 
                return False

        return True