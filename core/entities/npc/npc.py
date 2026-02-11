import pygame
import random
import math
import time
from core.entities.item.item import Item, Projectile, ITEM_TEMPLATES
from core.entities.zombie.zombie import Zombie
from core.messages import display_message
from core.data.config import *

# Mixins
from core.entities.npc.npc_data import NPCData
from core.entities.npc.npc_graphics import NPCGraphics
from core.entities.npc.npc_dialog import NPCDialog
from core.entities.npc.npc_combat import NPCCombat

class NPC(NPCData, NPCGraphics, NPCDialog, NPCCombat, Zombie):
    def __init__(self, x, y, game, is_static=False):
        if not NPCData.NPC_TEMPLATES:
            NPCData.load_templates()

        if NPCData.NPC_TEMPLATES:
            template = random.choice(NPCData.NPC_TEMPLATES)
        else:
            template = {
                'name': "Survivor", 
                'sex': random.choice(['Male', 'Female']),
                'health': 100,
                'speed': 1.0,
                'min_xp': 10,
                'max_xp': 20,
                'min_attack': 1,
                'max_attack': 5,
                'loot': [],
                'sprites': {},
                'clothes': {} 
            }

        # Initialize Zombie (sets up rect, base health, etc.)
        Zombie.__init__(self, x, y, template)
        
        self.game = game

        self.max_health = int(self.max_health * NPC_HEALTH_MULTIPLIER)
        self.health = int(self.health * NPC_HEALTH_MULTIPLIER)
        self.min_attack = int(self.min_attack * NPC_DAMAGE_MULTIPLIER)
        self.max_attack = int(self.max_attack * NPC_DAMAGE_MULTIPLIER)
        
        if not hasattr(self, 'speed') or self.speed == 0:
            self.speed = 1.1 
        self.speed = self.speed * NPC_SPEED_MULTIPLIER

        self.base_search_range = NPC_DETECTION_RADIUS
        
        if self.name == "Zombie" or self.name == "RANDOM":
             self.name = f"Survivor {random.randint(100, 999)}"

        self.is_static = is_static
        self.is_friendly = random.random() > NPC_HOSTILE_SPAWN
        self.is_following = False
        self.state = 'wandering' if not is_static else 'idle'

        self.start_x = x
        self.start_y = y
        self.patrol_target = None
        self.patrol_wait = 0
        self.shelter_target = None

        self.idle_timer = 0
        
        self.stuck_timer = 0
        self.stuck_angle = 0
        
        self.dialog_flags = set()

        self.knockback_velocity = [0, 0]
        self.knockback_timer = 0

        self.inventory = []
        id_card = Item.create_from_name("ID")
        self.inventory.append(id_card)
        
        # [ADDED] Spawn with Mobile (Off)
        mobile = Item.create_from_name("Mobile off")
        if mobile:
            mobile.state = "off"
            self.inventory.append(mobile)

        if not self.inventory:
             random_item = Item.generate_random()
             # [CHANGED] Check if the item is liquid (e.g. water/fuel unit) and exclude it
             if random_item and not random_item.liquid:
                 self.inventory.append(random_item)

        possible_weapons = [name for name, data in ITEM_TEMPLATES.items() 
                            if data.get('type') in ['weapon_melee', 'weapon_ranged']]
        
        if possible_weapons:
            weapon_name = random.choice(possible_weapons)
            self.equipped_weapon = Item.create_from_name(weapon_name, randomize_durability=True)
        else:
            self.equipped_weapon = Item.create_from_name("Knife", randomize_durability=True)
            
        if not self.equipped_weapon:
             self.equipped_weapon = Item.generate_random()

        if self.equipped_weapon and self.equipped_weapon.item_type == 'weapon_ranged':
            ammo_type = self.equipped_weapon.ammo_type
            if ammo_type:
                ammo_item = Item.create_from_name(ammo_type)
                if ammo_item:
                    ammo_item.load = 50 
                    self.inventory.append(ammo_item)

        self.melee_swing_timer = 0
        self.melee_swing_angle = 0

        self.is_dead = False
        #self.dead_image = self._load_sprite(self.visuals.get('dead_sprite', 'dead.png'))
        
        if not hasattr(self, 'angle'): self.angle = 0
        if not hasattr(self, 'dx'): self.dx = 0
        if not hasattr(self, 'dy'): self.dy = 0
            
        self.attack_range = TILE_SIZE * 1
        self.last_attack_time = 0
        self.attack_cooldown = 1000
        
        self.health_bar_timer = 0

        if not self.images or not self.images.get('center'):
            self._load_base_sprite()
            
        if not self.clothes:
             self._assign_random_clothes()

        clean_clothes = {}
        for slot, item_data in self.clothes.items():
            if not item_data: continue
            
            if isinstance(item_data, Item):
                clean_clothes[slot] = item_data
            elif isinstance(item_data, str):
                clean_clothes[slot] = Item.create_from_name(item_data)
            elif isinstance(item_data, dict) and 'name' in item_data:
                clean_clothes[slot] = Item.create_from_name(item_data['name'])
        
        self.clothes = clean_clothes

    def update(self, game):
        obstacles = game.obstacles
        if self.is_dead: return 

        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
        effective_speed = self.speed * multiplier

        current_time = pygame.time.get_ticks()
        
        is_raining = getattr(game, 'is_raining', False)
        if hasattr(game, 'weather'):
            is_raining = is_raining or getattr(game.weather, 'is_raining', False)
        if hasattr(game, 'world_time') and hasattr(game.world_time, 'state'):
            is_raining = is_raining or ('RAIN' in getattr(game.world_time, 'state', ''))

        if self.knockback_timer > 0:
            kb_x, kb_y = self.knockback_velocity
            self.x += kb_x
            self.rect.x = int(self.x)
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    self.x -= kb_x; self.rect.x = int(self.x); break
            self.y += kb_y
            self.rect.y = int(self.y)
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    self.y -= kb_y; self.rect.y = int(self.y); break
            self.rect.topleft = (int(self.x), int(self.y))
            dt = 16 * multiplier 
            self.knockback_timer -= dt
            self.knockback_velocity[0] *= 0.9
            self.knockback_velocity[1] *= 0.9
            return

        entities_to_check = [e for e in game.npcs if e != self and not e.is_dead]
        if game.player and not game.player.is_dead:
            entities_to_check.append(game.player)

        target_entity = None
        FOLLOW_PRIORITY_RANGE = TILE_SIZE * 20 
        player_is_far_and_following = False
        if game.player:
            player_dist = math.hypot(game.player.rect.centerx - self.rect.centerx, game.player.rect.centery - self.rect.centery)
            if self.is_following and player_dist > FOLLOW_PRIORITY_RANGE:
                player_is_far_and_following = True

        weapon = getattr(self, 'equipped_weapon', None)
        search_range = self.base_search_range 
        is_ranged_weapon = weapon and weapon.item_type == 'weapon_ranged'
        if is_ranged_weapon: search_range = self.base_search_range * 2 

        potential_targets = []
        potential_targets.extend(game.zombies)
        
        if not self.is_friendly:
            if game.player and not game.player.is_dead:
                potential_targets.append(game.player)
            for npc in game.npcs:
                if npc != self and not npc.is_dead and npc.is_friendly:
                    potential_targets.append(npc)

        min_dist_to_target = float('inf')
        
        if not player_is_far_and_following:
            for entity in potential_targets:
                dist = math.hypot(entity.rect.centerx - self.rect.centerx, entity.rect.centery - self.rect.centery)
                if dist < search_range and dist < min_dist_to_target:
                    min_dist_to_target = dist
                    target_entity = entity
                    self.state = 'chasing'

        if not target_entity and self.is_following and game.player or player_is_far_and_following:
            if player_dist > TILE_SIZE * 2 or player_is_far_and_following:
                target_entity = game.player
                self.state = 'following'

        # Check idle timer unless we have a target (combat priority)
        if self.idle_timer > 0 and not target_entity:
            self.idle_timer -= 1 * multiplier
            self.state = 'idle'
            self.dx = 0
            self.dy = 0
        else:
            if target_entity:
                dx = target_entity.rect.centerx - self.rect.centerx
                dy = target_entity.rect.centery - self.rect.centery
                dist = math.hypot(dx, dy)
                
                is_avoiding = False
                if self.stuck_timer > 0:
                    self.stuck_timer -= 1
                    is_avoiding = True

                attack_cooldown = self.attack_cooldown / multiplier 
                effective_attack_range = self.attack_range
                
                if is_ranged_weapon:
                    effective_attack_range = TILE_SIZE * 8 
                    attack_cooldown = 500 / multiplier 
                elif weapon and weapon.item_type in ['weapon_melee', 'tool']:
                    effective_attack_range = TILE_SIZE * 1.2
                    attack_cooldown = 1000 / multiplier 

                if self.state == 'chasing':
                    move_threshold = effective_attack_range * 0.8 if is_ranged_weapon else TILE_SIZE * 0.8
                elif self.state == 'following':
                    move_threshold = TILE_SIZE * 2
                else:
                    move_threshold = 0
                
                if dist > move_threshold and not is_avoiding:
                    self.angle = math.degrees(math.atan2(-dy, dx))

                    if not self.is_static:
                        scale = effective_speed / dist 
                        self.dx = dx * scale
                        self.dy = dy * scale
                    else:
                        self.dx, self.dy = 0, 0

                elif is_avoiding:
                    if not self.is_static:
                        self.angle = self.stuck_angle
                        rad = math.radians(self.angle)
                        self.dx = math.cos(rad) * effective_speed * 1.0 
                        self.dy = -math.sin(rad) * effective_speed * 1.0
                    else:
                        self.dx, self.dy = 0, 0
                else:
                    self.dx, self.dy = 0, 0
                    if self.state == 'following':
                        self.state = 'idle'
                    
                if self.state == 'chasing':
                    if dist <= effective_attack_range and (current_time - self.last_attack_time > attack_cooldown):
                        weapon_is_ready = True
                        if weapon and weapon.durability is not None and weapon.durability <= 0:
                            self.equipped_weapon = None 
                            weapon_is_ready = False
                            weapon = None 
                            
                        if weapon and weapon.item_type == 'weapon_ranged' and weapon.load is not None and weapon.load <= 0:
                             weapon_is_ready = False
                             if not self._try_reload(weapon, game):
                                 if weapon.sounds and 'noammo' in weapon.sounds:
                                    game.sound_manager.play_sound(weapon.sounds['noammo'], subdir='items', game=game, source_pos=self.rect.center)
                                 if not self._switch_weapon(game):
                                     self.inventory.append(self.equipped_weapon) 
                                     self.equipped_weapon = None 
                                     weapon = None 
                             else:
                                 self.last_attack_time = current_time + (1000 / multiplier) 
                                 weapon_is_ready = True
                        
                        has_los = True
                        if is_ranged_weapon and weapon:
                            has_los = self.check_line_of_sight(target_entity, game)

                        if weapon_is_ready and has_los:
                            self.last_attack_time = current_time
                            attack_angle = math.atan2(-dy, dx)
                            
                            damage_to_deal = random.randint(self.min_attack, self.max_attack)
                            if weapon:
                                 damage_range = weapon.current_damage_range 
                                 if damage_range[1] > 0: 
                                     damage_to_deal = random.randint(damage_range[0], damage_range[1])
                            
                            is_dead = False
                            
                            if weapon and weapon.durability is not None:
                                 weapon.durability -= 1 

                            if is_ranged_weapon and weapon: 
                                if hasattr(game, 'projectiles') and weapon.load is not None and weapon.load > 0:
                                    weapon.load -= 1
                                    if weapon.sounds and 'shoot' in weapon.sounds:
                                        game.sound_manager.play_sound(weapon.sounds['shoot'], subdir='items', game=game, source_pos=self.rect.center)

                                    pellets = getattr(weapon, 'pellets', 1)
                                    spread = getattr(weapon, 'spread_angle', 0.0)
                                    aim_angle = math.atan2(target_entity.rect.centery - self.rect.centery, 
                                                           target_entity.rect.centerx - self.rect.centerx)

                                    for _ in range(pellets):
                                        current_spread = math.radians(random.uniform(-spread, spread))
                                        final_angle = aim_angle + current_spread
                                        proj_dist = 1000
                                        target_x = self.rect.centerx + math.cos(final_angle) * proj_dist
                                        target_y = self.rect.centery + math.sin(final_angle) * proj_dist

                                        projectile = Projectile(self.rect.centerx, self.rect.centery, target_x, target_y, speed=20)
                                        projectile.damage = damage_to_deal
                                        projectile.owner = self
                                        projectile.hostile = True
                                        game.projectiles.append(projectile)
                                
                            else: 
                                self.melee_swing_timer = 15
                                self.melee_swing_angle = attack_angle
                                if weapon and weapon.sounds and 'swing' in weapon.sounds:
                                    game.sound_manager.play_sound(weapon.sounds['swing'], subdir='items', game=game, source_pos=self.rect.center)
                                
                                if target_entity == game.player:
                                    if hasattr(target_entity, 'take_durability_damage'):
                                        target_entity.take_durability_damage(damage_to_deal, game)
                                    target_part = target_entity.get_vulnerable_part()
                                     
                                    total_defence = target_entity.get_total_defence()
                                    health_bonus_perc = target_entity.progression.get_health_bonus(target_entity)
                                     
                                    total_reduction_perc = health_bonus_perc + total_defence
                                    damage_modifier = 1.0 - (total_reduction_perc / 100.0)
                                    damage_modifier = max(0.0, damage_modifier)
                                     
                                    final_damage = max(0, damage_to_deal * damage_modifier)
                                     
                                    target_entity.take_damage_to_part(target_part, final_damage)
                                    display_message(game, f"{self.name} attacked your {target_part}!")
                                else:
                                     is_dead = target_entity.take_damage(damage_to_deal, game, attacker=self)
                            
                            if is_dead and target_entity != game.player:
                                if hasattr(target_entity, 'die'):
                                    target_entity.die(game)
            
                         
            else:
                is_avoiding = False
                if self.stuck_timer > 0:
                    self.stuck_timer -= 1
                    is_avoiding = True

                if is_avoiding:
                    self.angle = self.stuck_angle
                    rad = math.radians(self.angle)
                    self.dx = math.cos(rad) * effective_speed * 0.8
                    self.dy = -math.sin(rad) * effective_speed * 0.8
                else:
                    if self.is_static:
                        if is_raining:
                            # 1. Seek Shelter during Rain
                            current_grid_x = int(self.rect.centerx // TILE_SIZE)
                            current_grid_y = int(self.rect.centery // TILE_SIZE)
                            current_tile = game.map_manager.get_tile_at(current_grid_x, current_grid_y)
                            
                            is_indoor = current_tile and (current_tile.get('is_indoor', False) or current_tile.get('has_roof', False))
                            if is_indoor:
                                self.dx, self.dy = 0, 0
                                self.state = 'idle'
                                self.shelter_target = None 
                            else:
                                if not self.shelter_target:
                                    found = False
                                    for r in range(1, 20):
                                        for d_x in range(-r, r+1):
                                            for d_y in range(-r, r+1):
                                                tx, ty = current_grid_x + d_x, current_grid_y + d_y
                                                t_def = game.map_manager.get_tile_at(tx, ty)
                                                if t_def and (t_def.get('is_indoor', False) or t_def.get('has_roof', False)):
                                                    self.shelter_target = (tx * TILE_SIZE + TILE_SIZE//2, ty * TILE_SIZE + TILE_SIZE//2)
                                                    found = True
                                                    break
                                            if found: break
                                        if found: break
                                    
                                    if not found:
                                        self.shelter_target = (self.start_x, self.start_y)
                                
                                if self.shelter_target:
                                    self.state = 'seeking_shelter'
                                    dx_s = self.shelter_target[0] - self.rect.centerx
                                    dy_s = self.shelter_target[1] - self.rect.centery
                                    dist_s = math.hypot(dx_s, dy_s)
                                    if dist_s > TILE_SIZE / 2:
                                        self.angle = math.degrees(math.atan2(-dy_s, dx_s))
                                        scale = effective_speed / max(1, dist_s)
                                        self.dx = dx_s * scale
                                        self.dy = dy_s * scale
                                    else:
                                        self.dx, self.dy = 0, 0
                                        self.state = 'idle'
                        else:
                            # 2. Patrol Logic (10 tiles around start position)
                            self.shelter_target = None
                            
                            if self.patrol_wait > 0:
                                self.patrol_wait -= 1 * multiplier
                                self.dx, self.dy = 0, 0
                                self.state = 'idle'
                            else:
                                if not self.patrol_target:
                                    angle_p = math.radians(random.uniform(0, 360))
                                    dist_p = random.uniform(0, TILE_SIZE * 10) # 10 Tiles radius
                                    self.patrol_target = (self.start_x + math.cos(angle_p) * dist_p, self.start_y + math.sin(angle_p) * dist_p)
                                    self.state = 'wandering'
                                
                                if self.patrol_target:
                                    dx_p = self.patrol_target[0] - self.rect.centerx
                                    dy_p = self.patrol_target[1] - self.rect.centery
                                    dist_p = math.hypot(dx_p, dy_p)
                                    if dist_p > TILE_SIZE / 2:
                                        self.angle = math.degrees(math.atan2(-dy_p, dx_p))
                                        scale = (effective_speed * 0.5) / max(1, dist_p) 
                                        self.dx = dx_p * scale
                                        self.dy = dy_p * scale
                                    else:
                                        self.patrol_target = None
                                        self.patrol_wait = random.randint(100, 300)
                                        self.dx, self.dy = 0, 0
                                        self.state = 'idle'
                    else:
                        # 3. Non-Static Wandering
                        self.state = 'wandering'
                        if random.random() < 0.02:
                            self.angle += random.randint(-45, 45)
                        rad = math.radians(self.angle)
                        self.dx = math.cos(rad) * effective_speed * 0.5 
                        self.dy = -math.sin(rad) * effective_speed * 0.5

        is_moving = self.dx != 0 or self.dy != 0

        if is_moving:
            self.walk_anim_angle = math.sin(time.time() * 15) * 2
            self.vx = self.dx
        else:
            self.walk_anim_angle = 0
            self.vx = 0
            
        if self.melee_swing_timer > 0:
            self.melee_swing_timer -= 1

        if self.health_bar_timer > 0:
            self.health_bar_timer -= 1

        if not is_moving: return

        # Physics Sub-Stepping Loop for NPCs
        total_dist_x = abs(self.dx)
        total_dist_y = abs(self.dy)
        
        step_size_limit = TILE_SIZE * 0.45
        steps = int(math.ceil(max(total_dist_x, total_dist_y) / step_size_limit))
        steps = max(1, steps)
        
        step_dx = self.dx / steps
        step_dy = self.dy / steps
        
        for _ in range(steps):
            # Move X
            self.x += step_dx
            self.rect.x = int(self.x)
            collided_x = False
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    # --- DOOR LOGIC X ---
                    obs_grid_x = obstacle.x // TILE_SIZE
                    obs_grid_y = obstacle.y // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(obs_grid_x, obs_grid_y)
                    if tile_def and tile_def.get('is_statable'):
                        char = game.map_data[obs_grid_y][obs_grid_x]
                        if 'close' in char or tile_def.get('state') == 'close':
                            game.map_manager.toggle_door_state(obs_grid_x, obs_grid_y)
                    # --------------------
                    if self.dx > 0: self.rect.right = obstacle.left
                    elif self.dx < 0: self.rect.left = obstacle.right
                    self.x = self.rect.x
                    self.stuck_timer = 30 
                    self.stuck_angle = random.randint(0, 360)
                    self.dx = 0
                    collided_x = True
                    break
            if not collided_x:
                for entity in entities_to_check:
                    if self.rect.colliderect(entity.rect):
                        self.x -= step_dx
                        self.rect.x = int(self.x)
                        self.dx = 0
                        collided_x = True
                        break

            # Move Y
            self.y += step_dy
            self.rect.y = int(self.y)
            collided_y = False
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    # --- DOOR LOGIC Y ---
                    obs_grid_x = obstacle.x // TILE_SIZE
                    obs_grid_y = obstacle.y // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(obs_grid_x, obs_grid_y)
                    if tile_def and tile_def.get('is_statable'):
                        char = game.map_data[obs_grid_y][obs_grid_x]
                        if 'close' in char or tile_def.get('state') == 'close':
                            game.map_manager.toggle_door_state(obs_grid_x, obs_grid_y)
                    # --------------------
                    if self.dy > 0: self.rect.bottom = obstacle.top
                    elif self.dy < 0: self.rect.top = obstacle.bottom
                    self.y = self.rect.y
                    self.stuck_timer = 30 
                    self.stuck_angle = random.randint(0, 360)
                    self.dy = 0
                    collided_y = True
                    break
            
            if not collided_y:
                for entity in entities_to_check:
                    if self.rect.colliderect(entity.rect):
                        self.y -= step_dy
                        self.rect.y = int(self.y)
                        self.dy = 0
                        collided_y = True
                        break

        self.rect.topleft = (int(self.x), int(self.y))

    def stop_moving(self):
        """Forces the NPC to stop moving and enter idle state."""
        self.state = 'idle'
        self.path = []      
        self.target = None
        self.velocity = pygame.math.Vector2(0, 0)
        self.idle_timer = 500
    
    def die(self, game):
        """
        Overrides Zombie.die to ensure NPC inventory and weapons 
        are dropped on the ground before the corpse is created.
        """
        # 1. Drop Inventory (ID Cards, Ammo, Meds)
        if hasattr(self, 'inventory'):
            for item in self.inventory:
                if item:
                    item.rect.center = self.rect.center
                    # Scatter slightly so they don't stack perfectly
                    item.rect.x += random.randint(-10, 10)
                    item.rect.y += random.randint(-10, 10)
                    game.items_on_ground.append(item)
            self.inventory = [] # Clear list

        # 2. Drop Equipped Weapon
        if hasattr(self, 'equipped_weapon') and self.equipped_weapon:
            self.equipped_weapon.rect.center = self.rect.center
            game.items_on_ground.append(self.equipped_weapon)
            self.equipped_weapon = None

        # 3. Call Parent Die (Handles Corpse creation, XP, and standard loot_table if any)
        super().die(game)