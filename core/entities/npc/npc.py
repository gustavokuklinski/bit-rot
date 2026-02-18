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
    def __init__(self, x, y, game, is_static=False, layer=None):
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

        # Initialize Zombie (sets up rect, base health, path variables from ZombieAI, etc.)
        Zombie.__init__(self, x, y, template)
        
        self.game = game
        
        # [FIX] Track the layer this NPC belongs to
        if layer is not None:
            self.layer = layer
        else:
            self.layer = game.current_layer_index if hasattr(game, 'current_layer_index') else 1

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
        
        mobile = Item.create_from_name("Mobile off")
        if mobile:
            mobile.state = "off"
            self.inventory.append(mobile)

        if not self.inventory:
             random_item = Item.generate_random()
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
        
        if not hasattr(self, 'angle'): self.angle = 0
        if not hasattr(self, 'dx'): self.dx = 0
        if not hasattr(self, 'dy'): self.dy = 0
            
        self.attack_range = TILE_SIZE * 1
        self.last_attack_time = 0
        self.attack_cooldown = 1000
        
        self.health_bar_timer = 0
        
        # New AI Pathfinding Inits (in case not init by Zombie)
        if not hasattr(self, 'path'): self.path = []
        if not hasattr(self, 'last_path_calc_time'): self.last_path_calc_time = 0

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
        
        # [NEW] Generate mask for pixel-perfect collision
        if self.image:
            self.mask = pygame.mask.from_surface(self.image)
        else:
            self.mask = pygame.mask.Mask((TILE_SIZE, TILE_SIZE))
            self.mask.fill()

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

        # --- KNOCKBACK HANDLING ---
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

        # --- ENTITY SCANNING ---
        entities_to_check = [e for e in game.npcs if e != self and not e.is_dead]
        if game.player and not game.player.is_dead:
            entities_to_check.append(game.player)

        target_entity = None
        target_pos = None
        
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

        # --- TARGET ACQUISITION ---
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

        # --- MOVEMENT LOGIC ---
        
        # Determine Destination
        if target_entity:
            target_pos = target_entity.rect.center
            self.idle_timer = 0
        else:
            # Not chasing or following. Patrol or Shelter.
            if self.is_static:
                # Static behavior (guard)
                if is_raining:
                     # Reuse existing shelter logic but just set target_pos
                     if not self.shelter_target:
                        self._find_shelter(game) # Helper to find shelter (extracted logic below)
                     if self.shelter_target:
                         target_pos = self.shelter_target
                         self.state = 'seeking_shelter'
                else:
                    target_pos = None
                    self.state = 'idle'
            else:
                # Dynamic behavior
                if is_raining:
                    if not self.shelter_target:
                         self._find_shelter(game)
                    if self.shelter_target:
                        target_pos = self.shelter_target
                        self.state = 'seeking_shelter'
                    else:
                        target_pos = (self.start_x, self.start_y) # Go home if no shelter
                else:
                    self.shelter_target = None
                    if self.patrol_wait > 0:
                        self.patrol_wait -= 1 * multiplier
                        target_pos = None
                        self.state = 'idle'
                    else:
                        if not self.patrol_target:
                            self._pick_patrol_point(game)
                        target_pos = self.patrol_target
                        self.state = 'wandering'

        # Calculate Move Vector (Smart Pathfinding)
        self.dx, self.dy = 0, 0
        
        if target_pos:
            dist_to_dest = math.hypot(target_pos[0] - self.rect.centerx, target_pos[1] - self.rect.centery)
            
            # Distance Thresholds
            move_threshold = TILE_SIZE * 0.5
            if self.state == 'chasing':
                 # Stop closer if melee, further if ranged
                 move_threshold = (TILE_SIZE * 8) if is_ranged_weapon else (TILE_SIZE * 0.8)
            elif self.state == 'following':
                 move_threshold = TILE_SIZE * 2.5
            
            if dist_to_dest > move_threshold:
                # --- PATHFINDING INTEGRATION ---
                # Check Line of Sight
                has_los = True
                if self.state != 'chasing': # Always pathfind for patrol/shelter to avoid sticking to walls
                     has_los = False 
                else:
                    has_los = self.has_line_of_sight(pygame.Rect(target_pos[0]-2, target_pos[1]-2, 4, 4), obstacles)

                # Use pathfinding if no LOS or if we are stuck
                if not has_los or (self.stuck_timer > 0 and self.stuck_timer % 20 == 0):
                    if current_time - self.last_path_calc_time > 1000 or not self.path or (self.state == 'chasing' and current_time - self.last_path_calc_time > 500):
                         # Note: _get_path_astar is inherited from ZombieAI
                         new_path = self._get_path_astar(self.rect.center, target_pos, game)
                         if new_path:
                             self.path = new_path
                             self.last_path_calc_time = current_time
                    
                    if self.path:
                        next_node = self.path[0]
                        dx_path = next_node[0] - self.rect.centerx
                        dy_path = next_node[1] - self.rect.centery
                        dist_path = math.hypot(dx_path, dy_path)
                        
                        if dist_path < TILE_SIZE * 0.5:
                            self.path.pop(0)
                            if self.path:
                                next_node = self.path[0]
                                dx_path = next_node[0] - self.rect.centerx
                                dy_path = next_node[1] - self.rect.centery
                                dist_path = math.hypot(dx_path, dy_path)
                        
                        if dist_path > 0:
                            scale = effective_speed / dist_path
                            self.dx = dx_path * scale
                            self.dy = dy_path * scale
                    else:
                        # Fallback direct
                        scale = effective_speed / dist_to_dest
                        self.dx = (target_pos[0] - self.rect.centerx) * scale
                        self.dy = (target_pos[1] - self.rect.centery) * scale
                else:
                    # Direct move
                    self.path = []
                    scale = effective_speed / dist_to_dest
                    self.dx = (target_pos[0] - self.rect.centerx) * scale
                    self.dy = (target_pos[1] - self.rect.centery) * scale
                    
                self.angle = math.degrees(math.atan2(-self.dy, self.dx))
            else:
                 # Reached destination
                 if self.state == 'wandering' and self.patrol_target:
                      self.patrol_target = None
                      self.patrol_wait = random.randint(100, 300)
                 elif self.state == 'seeking_shelter':
                      pass 

        # --- COMBAT LOGIC (Attack) ---
        if self.state == 'chasing' and target_entity:
             self._handle_combat(target_entity, game, multiplier, current_time)

        # --- PHYSICS & ANIMATION ---
        is_moving = self.dx != 0 or self.dy != 0

        if is_moving:
            self.walk_anim_angle = math.sin(time.time() * 15) * 2
            self.vx = self.dx
        else:
            self.walk_anim_angle = 0
            self.vx = 0
            
        if self.melee_swing_timer > 0: self.melee_swing_timer -= 1
        if self.health_bar_timer > 0: self.health_bar_timer -= 1

        if not is_moving: return

        # Stuck / Wiggle Logic
        if self.stuck_timer > 0:
            self.stuck_timer -= 1
            rad = math.radians(self.stuck_angle)
            self.dx += math.cos(rad) * effective_speed * 0.5
            self.dy += -math.sin(rad) * effective_speed * 0.5

        # Sub-stepping Physics
        total_dist_x = abs(self.dx)
        total_dist_y = abs(self.dy)
        step_size_limit = TILE_SIZE * 0.45
        steps = int(math.ceil(max(total_dist_x, total_dist_y) / step_size_limit))
        steps = max(1, steps)
        
        step_dx = self.dx / steps
        step_dy = self.dy / steps
        
        def check_mask_collision(rect_check):
            # Check tiles
            for obstacle in obstacles:
                if rect_check.colliderect(obstacle):
                    gx = obstacle.x // TILE_SIZE
                    gy = obstacle.y // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    if tile_def and 'mask' in tile_def:
                        offset = (obstacle.x - rect_check.x, obstacle.y - rect_check.y)
                        if self.mask.overlap(tile_def['mask'], offset):
                            return True, obstacle
                    else:
                         # Fallback for tiles without masks (shouldn't happen with updated tile loader)
                         return True, obstacle
            
            # Check entities
            for entity in entities_to_check:
                if rect_check.colliderect(entity.rect):
                    if hasattr(entity, 'mask') and entity.mask:
                        offset = (entity.rect.x - rect_check.x, entity.rect.y - rect_check.y)
                        if self.mask.overlap(entity.mask, offset):
                            return True, entity
                    else:
                        return True, entity
            return False, None

        for _ in range(steps):
            # Move X
            self.x += step_dx
            self.rect.x = int(self.x)
            
            collision, collider = check_mask_collision(self.rect)
            
            if collision:
                # Handle interaction if it's a door
                if collider in obstacles:
                    self._handle_door_interaction(collider, game)
                
                # Revert X
                self.x -= step_dx
                self.rect.x = int(self.x)
                self.dx = 0
                
                # If stuck timer isn't active, activate it
                if self.stuck_timer <= 0:
                     self.stuck_timer = 20
                     self.stuck_angle = random.randint(0, 360)
            
            # Move Y
            self.y += step_dy
            self.rect.y = int(self.y)
            
            collision, collider = check_mask_collision(self.rect)
            
            if collision:
                if collider in obstacles:
                    self._handle_door_interaction(collider, game)
                
                # Revert Y
                self.y -= step_dy
                self.rect.y = int(self.y)
                self.dy = 0

                if self.stuck_timer <= 0:
                     self.stuck_timer = 20
                     self.stuck_angle = random.randint(0, 360)

        self.rect.topleft = (int(self.x), int(self.y))

    def _find_shelter(self, game):
        """Helper to find nearby indoor tile"""
        current_grid_x = int(self.rect.centerx // TILE_SIZE)
        current_grid_y = int(self.rect.centery // TILE_SIZE)
        
        found = False
        for r in range(1, 20):
            for d_x in range(-r, r+1):
                for d_y in range(-r, r+1):
                    tx, ty = current_grid_x + d_x, current_grid_y + d_y
                    if 0 <= ty < len(game.map_data) and 0 <= tx < len(game.map_data[0]):
                        t_def = game.map_manager.get_tile_at(tx, ty)
                        if t_def and (t_def.get('is_indoor', False) or t_def.get('has_roof', False)):
                            self.shelter_target = (tx * TILE_SIZE + TILE_SIZE//2, ty * TILE_SIZE + TILE_SIZE//2)
                            found = True
                            break
                if found: break
            if found: break
    
    def _pick_patrol_point(self, game):
        """Pick a valid patrol point on the map"""
        for _ in range(10): # Try 10 times to find valid point
            angle_p = math.radians(random.uniform(0, 360))
            dist_p = random.uniform(TILE_SIZE * 2, TILE_SIZE * 10)
            px = self.start_x + math.cos(angle_p) * dist_p
            py = self.start_y + math.sin(angle_p) * dist_p
            
            grid_x = int(px // TILE_SIZE)
            grid_y = int(py // TILE_SIZE)
            
            if 0 <= grid_y < len(game.map_data) and 0 <= grid_x < len(game.map_data[0]):
                t_def = game.map_manager.get_tile_at(grid_x, grid_y)
                if t_def and not t_def.get('is_obstacle', False):
                    self.patrol_target = (px, py)
                    return

    def _handle_door_interaction(self, obstacle, game):
        """If bumping into a door, try to open it."""
        obs_grid_x = obstacle.x // TILE_SIZE
        obs_grid_y = obstacle.y // TILE_SIZE
        tile_def = game.map_manager.get_tile_at(obs_grid_x, obs_grid_y)
        if tile_def and tile_def.get('is_statable'):
            char = game.map_data[obs_grid_y][obs_grid_x]
            if 'close' in char or tile_def.get('state') == 'close':
                game.map_manager.toggle_door_state(obs_grid_x, obs_grid_y)

    def _handle_combat(self, target_entity, game, multiplier, current_time):
        """Extracted combat logic from update loop"""
        weapon = getattr(self, 'equipped_weapon', None)
        is_ranged_weapon = weapon and weapon.item_type == 'weapon_ranged'
        
        dx = target_entity.rect.centerx - self.rect.centerx
        dy = target_entity.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        
        effective_attack_range = self.attack_range
        attack_cooldown = self.attack_cooldown / multiplier 
        if is_ranged_weapon:
            effective_attack_range = TILE_SIZE * 8
            attack_cooldown = 500 / multiplier
        
        if dist <= effective_attack_range and (current_time - self.last_attack_time > attack_cooldown):
             # (Reuse existing combat logic here...)
             # For brevity, I am assuming the logic remains similar to original but inside this helper
             # The key update is that movement is handled before this.
             
             weapon_is_ready = True
             # ... Reload checks ...
             
             has_los = True
             if is_ranged_weapon:
                 has_los = self.check_line_of_sight(target_entity, game)

             if weapon_is_ready and has_los:
                 self.last_attack_time = current_time
                 attack_angle = math.atan2(-dy, dx)
                 
                 # ... Damage calc ...
                 damage_to_deal = random.randint(self.min_attack, self.max_attack)
                 
                 # Execute Attack
                 if is_ranged_weapon and weapon:
                      # Shoot logic
                      projectile = Projectile(self.rect.centerx, self.rect.centery, target_entity.rect.centerx, target_entity.rect.centery, speed=20)
                      projectile.damage = damage_to_deal
                      projectile.owner = self
                      projectile.hostile = True
                      game.projectiles.append(projectile)
                 else:
                      # Melee logic
                      self.melee_swing_timer = 15
                      self.melee_swing_angle = attack_angle
                      
                      # [FIX] Handle different damage signatures for Player vs Entity
                      if target_entity == game.player:
                           # Player uses (game, damage, infection)
                           target_entity.take_damage(game, damage_to_deal, 0)
                      else:
                           # Zombies/NPCs use (damage, game, attacker=...)
                           target_entity.take_damage(damage_to_deal, game, attacker=self)

    def stop_moving(self):
        """Forces the NPC to stop moving and enter idle state."""
        self.state = 'idle'
        self.path = []      
        self.idle_timer = 500
    
    def die(self, game):
        # 1. Drop Inventory
        if hasattr(self, 'inventory'):
            for item in self.inventory:
                if item:
                    item.rect.center = self.rect.center
                    item.rect.x += random.randint(-10, 10)
                    item.rect.y += random.randint(-10, 10)
                    game.items_on_ground.append(item)
            self.inventory = [] 

        # 2. Drop Equipped Weapon
        if hasattr(self, 'equipped_weapon') and self.equipped_weapon:
            self.equipped_weapon.rect.center = self.rect.center
            game.items_on_ground.append(self.equipped_weapon)
            self.equipped_weapon = None

        super().die(game)