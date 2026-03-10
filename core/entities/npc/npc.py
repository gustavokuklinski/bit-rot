# core/entities/npc/npc.py

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

CLOTHING_COLORS = [
    (255, 255, 255), (50, 50, 50), (220, 50, 50), (50, 200, 50), 
    (50, 50, 220), (220, 220, 50), (255, 105, 180), (255, 165, 0), 
    (139, 69, 19), (128, 128, 128)
]

class NPC(NPCData, NPCGraphics, NPCDialog, NPCCombat, Zombie):
    def __init__(self, x, y, game, is_static=False, layer=None):
        if not NPCData.NPC_TEMPLATES:
            NPCData.load_templates()

        if NPCData.NPC_TEMPLATES:
            # --- NEW: Weighted Template Selection ---
            type_weights = {
                'common': 55,
                'worker': 20,
                'doctor': 10,
                'military': 20,
                'special_force': 5
            }
            template_weights = [type_weights.get(t.get('type', 'common'), 10) for t in NPCData.NPC_TEMPLATES]
            template = random.choices(NPCData.NPC_TEMPLATES, weights=template_weights, k=1)[0]

        else:
            template = {
                'type': 'common',
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

        Zombie.__init__(self, x, y, template)
        
        # --- FIX: Prevent default XML loot tables from dropping duplicate white clothes ---
        if hasattr(self, 'loot_table'):
            self.loot_table = [loot for loot in self.loot_table if loot.get('item') not in ["Pants", "Jacket", "Tshirt", "TShirt", "Sneakers"]]

        self.game = game
        
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

        self.aggro_timer = 0
        self.current_attacker = None

        self.inventory = []
        id_name = f"ID: {self.name}"
        id_card = Item.create_from_name(id_name)
        if id_card:
            id_card.text = f"Name: {self.name}\nSex: {self.sex}\n"
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
        self.dead_image = False
        
        if not hasattr(self, 'angle'): self.angle = 0
        if not hasattr(self, 'dx'): self.dx = 0
        if not hasattr(self, 'dy'): self.dy = 0
            
        self.attack_range = TILE_SIZE * 1.5
        self.last_attack_time = 0
        self.attack_cooldown = 1000
        
        self.health_bar_timer = 0
        
        if not hasattr(self, 'path'): self.path = []
        if not hasattr(self, 'last_path_calc_time'): self.last_path_calc_time = 0

        if not self.images or not self.images.get('center'):
            self._load_base_sprite()
            
        self.clothes = {}
        hair_options = ['Bald', 'Mowalk', 'Cut', 'Crew', 'Long']
        predefined_clothes = template.get('predefined_clothes', {})
        selected_hair = predefined_clothes.get('hair', random.choice(hair_options))
        
        # Base fallback logic combined with XML predefined rules
        clothes_to_equip = {
            "feet": predefined_clothes.get("feet") or "Sneakers",
            "legs": predefined_clothes.get("legs") or "Pants",
            "body": predefined_clothes.get("body") or "Tshirt",
            "arms": predefined_clothes.get("arms") or ("Jacket" if random.random() < 0.2 else None),
            "hair": selected_hair
        }
        
        # Inject other predefined specific clothing slots (like hand, head, util)
        for slot_name, cloth_name in predefined_clothes.items():
            if slot_name not in clothes_to_equip:
                clothes_to_equip[slot_name] = cloth_name
        
        for slot_name, cloth_name in clothes_to_equip.items():
            if not cloth_name:
                continue
            item = Item.create_from_name(cloth_name)
            if item:
                # Check if this specific item was explicitly defined in the XML for this slot
                is_explicitly_defined = (slot_name in predefined_clothes and predefined_clothes[slot_name] == cloth_name)

                # Only apply random tint to fallback/randomized clothing (Not XML overrides)
                if not is_explicitly_defined:
                    item.color = random.choice(CLOTHING_COLORS)
                    if item.image:
                        tinted = item.image.copy()
                        tinted.fill((*item.color, 255)[:4], special_flags=pygame.BLEND_RGBA_MULT)
                        item.image = tinted
                
                actual_slot = getattr(item, 'slot', slot_name)
                
                # Apply fallback slot overrides just in case item doesn't have it explicitly defined
                if not getattr(item, 'slot', None):
                    if cloth_name == "Pants": actual_slot = "legs"
                    elif cloth_name == "Jacket": actual_slot = "arms"
                    elif cloth_name == "Tshirt": actual_slot = "body"
                    elif cloth_name == "Sneakers": actual_slot = "feet"
                    elif cloth_name in hair_options: actual_slot = "hair"

                if actual_slot not in self.clothes:
                    self.clothes[actual_slot] = item
        
        if self.image:
            self.mask = pygame.mask.from_surface(self.image)
        else:
            self.mask = pygame.mask.Mask((TILE_SIZE, TILE_SIZE))
            self.mask.fill()

    def update(self, game):
        obstacles = game.obstacles
        if self.is_dead: return 

        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
        
        # [NEW] Determine terrain speed multiplier
        speed_mult = 1.0
        gx = self.rect.centerx // TILE_SIZE
        gy = self.rect.centery // TILE_SIZE
        if hasattr(game, 'map_manager'):
            tile_def = game.map_manager.get_tile_at(gx, gy)
            if tile_def:
                name = tile_def.get('name', '').lower()
                if 'window' in name or tile_def.get('is_window'):
                    speed_mult = 0.35 # Slow down on windows

        effective_speed = self.speed * multiplier * game.dt_mult * speed_mult
        current_time = pygame.time.get_ticks()
        
        is_raining = getattr(game, 'is_raining', False)
        if hasattr(game, 'weather'):
            is_raining = is_raining or getattr(game.weather, 'is_raining', False)
        if hasattr(game, 'world_time') and hasattr(game.world_time, 'state'):
            is_raining = is_raining or ('RAIN' in getattr(game.world_time, 'state', ''))

        if self.knockback_timer > 0:
            VELOCITY_MULTIPLIER = 0.25
            kb_x, kb_y = self.knockback_velocity
            self.x += kb_x * VELOCITY_MULTIPLIER
            self.rect.x = int(self.x)
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    self.x -= kb_x * VELOCITY_MULTIPLIER; self.rect.x = int(self.x); break
            self.y += kb_y * VELOCITY_MULTIPLIER
            self.rect.y = int(self.y)
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    self.y -= kb_y * VELOCITY_MULTIPLIER; self.rect.y = int(self.y); break
            self.rect.topleft = (int(self.x), int(self.y))
            dt = game.dt_ms * multiplier
            self.knockback_timer -= dt

            decay_factor = math.pow(0.9, game.dt_mult * multiplier)
            self.knockback_velocity[0] *= decay_factor
            self.knockback_velocity[1] *= decay_factor
            return

        if self.aggro_timer > 0:
            self.aggro_timer -= game.dt_ms
            if self.aggro_timer <= 0:
                self.current_attacker = None

        entities_to_check = [e for e in game.npcs if e != self and not e.is_dead]
        if game.player and not game.player.is_dead and not getattr(game.player, 'godzen_mode', False):
            entities_to_check.append(game.player)

        target_entity = None
        target_pos = None
        
        FOLLOW_PRIORITY_RANGE = TILE_SIZE * 20
        player_is_far_and_following = False
        is_aggroed = self.aggro_timer > 0
        if game.player:
            player_dist = math.hypot(game.player.rect.centerx - self.rect.centerx, game.player.rect.centery - self.rect.centery)
            if self.is_following and player_dist > FOLLOW_PRIORITY_RANGE:
                player_is_far_and_following = True
            if is_aggroed and player_dist > FOLLOW_PRIORITY_RANGE:
                player_is_far_and_following = True

        weapon = getattr(self, 'equipped_weapon', None)
        search_range = self.base_search_range 
        is_ranged_weapon = weapon and weapon.item_type == 'weapon_ranged'
        if is_ranged_weapon: search_range = self.base_search_range * 2 

        potential_targets = []
        
        # [FIX] Do not target zombies that are already dead
        for z in game.zombies:
            if not getattr(z, 'is_dead', False):
                potential_targets.append(z)

        attacker = getattr(self, 'current_attacker', None)

        if self.is_friendly:
            for npc in game.npcs:
                if npc != self and not npc.is_dead and not npc.is_friendly:
                    potential_targets.append(npc)
            if attacker == game.player and game.player and not game.player.is_dead and not getattr(game.player, 'godzen_mode', False):
                potential_targets.append(game.player)
        else:
            if game.player and not game.player.is_dead and not getattr(game.player, 'godzen_mode', False):
                potential_targets.append(game.player)
            for npc in game.npcs:
                if npc != self and not npc.is_dead and npc.is_friendly:
                    potential_targets.append(npc)

        min_dist_to_target = float('inf')

        if not player_is_far_and_following:
            for entity in potential_targets:
                # [FIX] Static NPCs do not aggro based on proximity, they only react if hit
                if self.is_static:
                    continue

                dist = math.hypot(entity.rect.centerx - self.rect.centerx, entity.rect.centery - self.rect.centery)
                if dist < search_range and dist < min_dist_to_target:
                    min_dist_to_target = dist
                    target_entity = entity
                    self.state = 'chasing'

        if is_aggroed:
            if attacker and not attacker.is_dead:
                if attacker == game.player and getattr(game.player, 'godzen_mode', False):
                    self.aggro_timer = 0
                else:
                    target_entity = attacker
                    self.state = 'chasing'
            elif game.player and not game.player.is_dead and not getattr(game.player, 'godzen_mode', False):
                target_entity = game.player
                self.state = 'chasing'

        if not target_entity and self.is_following and game.player or player_is_far_and_following:
            if player_dist > TILE_SIZE * 2 or player_is_far_and_following:
                target_entity = game.player
                self.state = 'following'

        if target_entity:
            target_pos = target_entity.rect.center
            self.idle_timer = 0
        else:
            if self.is_static:
                # [FIX] Static NPCs do not seek shelter or patrol. They strictly stand still unless aggroed.
                target_pos = None
                self.state = 'idle'
            else:
                if is_raining:
                    if not self.shelter_target:
                         self._find_shelter(game)
                    if self.shelter_target:
                        target_pos = self.shelter_target
                        self.state = 'seeking_shelter'
                    else:
                        target_pos = (self.start_x, self.start_y) 
                else:
                    self.shelter_target = None
                    if self.patrol_wait > 0:
                        self.patrol_wait -= game.dt_ms * multiplier
                        target_pos = None
                        self.state = 'idle'
                    else:
                        if not self.patrol_target:
                            self._pick_patrol_point(game)
                        target_pos = self.patrol_target
                        self.state = 'wandering'

        self.dx, self.dy = 0, 0
        
        if target_pos:
            dist_to_dest = math.hypot(target_pos[0] - self.rect.centerx, target_pos[1] - self.rect.centery)
            
            move_threshold = TILE_SIZE * 0.5
            if self.state == 'chasing':
                 move_threshold = (TILE_SIZE * 8) if is_ranged_weapon else (TILE_SIZE * 0.8)
            elif self.state == 'following':
                 move_threshold = TILE_SIZE * 2.5
            
            if dist_to_dest > move_threshold:
                has_los = True
                if self.state != 'chasing': 
                     has_los = False 
                else:
                    has_los = self.has_line_of_sight(pygame.Rect(target_pos[0]-2, target_pos[1]-2, 4, 4), obstacles, current_time)

                if not has_los or self.stuck_timer > 0:
                    if current_time - self.last_path_calc_time > 1000 or not self.path or (self.state == 'chasing' and current_time - self.last_path_calc_time > 500):
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
                        scale = effective_speed / dist_to_dest
                        self.dx = (target_pos[0] - self.rect.centerx) * scale
                        self.dy = (target_pos[1] - self.rect.centery) * scale
                else:
                    self.path = []
                    scale = effective_speed / dist_to_dest
                    self.dx = (target_pos[0] - self.rect.centerx) * scale
                    self.dy = (target_pos[1] - self.rect.centery) * scale
                    
                self.angle = math.degrees(math.atan2(-self.dy, self.dx))
            else:
                 if self.state == 'wandering' and self.patrol_target:
                      self.patrol_target = None
                      self.patrol_wait = random.randint(100, 300)
                 elif self.state == 'seeking_shelter':
                      pass 

        if self.state == 'chasing' and target_entity:
             self._handle_combat(target_entity, game, multiplier, current_time)

        is_moving = self.dx != 0 or self.dy != 0

        if is_moving:
            self.walk_anim_angle = math.sin(time.time() * 15) * 2
            self.vx = self.dx

            if hasattr(self, 'sound_steps') and self.sound_steps:
                if current_time - getattr(self, 'last_step_sound_time', 0) > 400:
                    game.sound_manager.play_sound(self.sound_steps, subdir='npc', game=game, source_pos=self.rect.center, base_volume=random.uniform(0.2, 0.7), pitch_variance=0.15)
                    self.last_step_sound_time = current_time
        else:
            self.walk_anim_angle = 0
            self.vx = 0
            
        if self.melee_swing_timer > 0: self.melee_swing_timer -= game.dt_ms
        if self.health_bar_timer > 0: self.health_bar_timer -= game.dt_ms

        if not is_moving: return

        if self.stuck_timer > 0:
            self.stuck_timer -= game.dt_ms
            rad = math.radians(self.stuck_angle)
            self.dx += math.cos(rad) * effective_speed * 0.5
            self.dy += -math.sin(rad) * effective_speed * 0.5

        total_dist_x = abs(self.dx)
        total_dist_y = abs(self.dy)
        step_size_limit = TILE_SIZE * 0.45
        steps = int(math.ceil(max(total_dist_x, total_dist_y) / step_size_limit))
        steps = max(1, steps)
        
        step_dx = self.dx / steps
        step_dy = self.dy / steps
        
        def check_mask_collision(rect_check):
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
                         return True, obstacle
            
            for entity in entities_to_check:
                # [FIX] Shrink the entity's hitbox slightly so the NPC can step inside a few pixels
                # We also ignore pixel-perfect mask checks here so edges can visually overlap
                hitbox = entity.rect.inflate(-12, -12)
                if rect_check.colliderect(hitbox):
                    return True, entity
            return False, None

        for _ in range(steps):
            self.x += step_dx
            self.rect.x = int(self.x)
            
            collision, collider = check_mask_collision(self.rect)
            
            if collision:
                if collider in obstacles:
                    self._handle_door_interaction(collider, game)
                
                self.x -= step_dx
                self.rect.x = int(self.x)
                self.dx = 0
                
                if self.stuck_timer <= 0:
                     self.stuck_timer = 200
                     self.stuck_angle = random.randint(0, 360)
            
            self.y += step_dy
            self.rect.y = int(self.y)
            
            collision, collider = check_mask_collision(self.rect)
            
            if collision:
                if collider in obstacles:
                    self._handle_door_interaction(collider, game)
                
                self.y -= step_dy
                self.rect.y = int(self.y)
                self.dy = 0

                if self.stuck_timer <= 0:
                     self.stuck_timer = 200
                     self.stuck_angle = random.randint(0, 360)

        self.rect.topleft = (int(self.x), int(self.y))

    def _find_shelter(self, game):
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
        for _ in range(10): 
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
        obs_grid_x = obstacle.x // TILE_SIZE
        obs_grid_y = obstacle.y // TILE_SIZE
        tile_def = game.map_manager.get_tile_at(obs_grid_x, obs_grid_y)
        if tile_def and tile_def.get('is_statable'):
            char = game.map_data[obs_grid_y][obs_grid_x]
            if 'close' in char or tile_def.get('state') == 'close':
                game.map_manager.toggle_door_state(obs_grid_x, obs_grid_y)

    def _handle_combat(self, target_entity, game, multiplier, current_time):
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
            weapon_is_ready = True
             
            has_los = True
            if is_ranged_weapon:
                has_los = self.check_line_of_sight(target_entity, game)

            if weapon_is_ready and has_los:
                self.last_attack_time = current_time
                attack_angle = math.atan2(-dy, dx)
                 
                # [FIX] Properly calculate NPC damage including equipped weapons
                base_damage = random.randint(self.min_attack, self.max_attack)
                weapon_dmg = 0
                if weapon:
                    if hasattr(weapon, 'damage'):
                        weapon_dmg = weapon.damage
                    elif hasattr(weapon, 'min_damage') and hasattr(weapon, 'max_damage'):
                        weapon_dmg = random.randint(weapon.min_damage, weapon.max_damage)
                
                # Ensures that NPCs always do at least 1 damage (never 0 damage locking targets at 1 HP)
                damage_to_deal = max(1, base_damage + weapon_dmg)
                 
                if is_ranged_weapon and weapon:
                    weapon_sound = weapon.sounds.get('shoot') if hasattr(weapon, 'sounds') else None
                    
                    if weapon_sound:
                        game.sound_manager.play_sound(weapon_sound, subdir='items', game=game, source_pos=self.rect.center, base_volume=random.uniform(0.2, 0.7), pitch_variance=0.15)

                    projectile = Projectile(self.rect.centerx, self.rect.centery, target_entity.rect.centerx, target_entity.rect.centery, speed=20)
                    projectile.damage = damage_to_deal
                    projectile.owner = self
                    projectile.hostile = True
                    game.projectiles.append(projectile)
                    
                else: # Melee attack
                    if getattr(self, 'sound_attack', None):
                        game.sound_manager.play_sound(self.sound_attack, subdir='npc', game=game, source_pos=self.rect.center, base_volume=random.uniform(0.2, 0.7), pitch_variance=0.15)
                    self.melee_swing_timer = 250
                    self.melee_swing_angle = attack_angle
                    
                    if target_entity == game.player:
                        target_entity.take_damage(game, damage_to_deal, 0)
                    else:
                        # [FIX] Call die() for any target entity (Zombie, Animal, NPC) if damage is lethal
                        is_dead = target_entity.take_damage(damage_to_deal, game, attacker=self)
                        if is_dead:
                            target_entity.die(game)
                            if target_entity in game.npcs:
                                display_message(game, "A survivor has been killed.")
                            elif getattr(target_entity, 'type', '') == 'animal':
                                pass # Animal death handled in its own die()
                            else:
                                display_message(game, f"A zombie was eliminated by {self.name}.")

    def stop_moving(self):
        self.state = 'idle'
        self.path = []      
        self.idle_timer = 500
    
    def die(self, game):
        if not hasattr(self, 'inventory') or self.inventory is None:
            self.inventory = []

        if hasattr(self, 'equipped_weapon') and self.equipped_weapon:
            self.inventory.append(self.equipped_weapon)
            self.equipped_weapon = None
            
        if hasattr(self, 'clothes'):
            for slot, cloth_item in self.clothes.items():
                if cloth_item:
                    self.inventory.append(cloth_item)
            self.clothes = {}

        super().die(game)
        
        # [FIX] Force removal from sprite rendering groups preventing dead visual entities
        self.kill()