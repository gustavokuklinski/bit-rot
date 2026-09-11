# core/entities/npc/npc.py

import pygame
import random
import math
import time
from core.entities.item.item import Item, Projectile, ITEM_TEMPLATES
from core.entities.zombie.zombie import Zombie
from core.entities.zombie.zombie_data import ZombieData  
from core.messages import display_message
from core.data.config import *
from faker import Faker
from core.entities.npc.npc_dialog import NPCDialog

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
            
        if NPCDialog.NPC_DIALOGS is None:
            NPCDialog.load_dialogs(game)

        if NPCData.NPC_TEMPLATES:
            available_templates = []
            template_weights = []
            for t in NPCData.NPC_TEMPLATES:
                t_static = t.get('is_static', False)
                
                if is_static and not t_static:
                    continue
                if not is_static and t_static:
                    continue
                    
                available_templates.append(t)
                template_weights.append(t.get('spawn_weight', 10))
                
            if available_templates:
                template = random.choices(available_templates, weights=template_weights, k=1)[0]
            else:
                template = random.choices(NPCData.NPC_TEMPLATES, weights=[t.get('spawn_weight', 10) for t in NPCData.NPC_TEMPLATES], k=1)[0]
        else:
            template = {
                'type': 'common',
                'name': "RANDOM",
                'sex': random.choice(['Male', 'Female']),
                'health': 100,
                'speed': 1.0,
                'min_xp': 10,
                'max_xp': 20,
                'min_attack': 1,
                'max_attack': 5,
                'loot': [],
                'sprites': {},
                'clothes': {},
                'is_friendly': False,
                'is_static': False,
                'spawn_zombies': 0
            }

        Zombie.__init__(self, x, y, template)
        self.spawn_zombies_max = template.get('spawn_zombies', 0)
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
        
        name_val = template.get('name', 'RANDOM')
        template_static = template.get('is_static', False)

        sex_val = template.get('sex', 'Random').capitalize()
        if sex_val == 'Random':
            sex_val = random.choice(['Male', 'Female'])
        self.sex = sex_val

        if name_val != 'RANDOM' and name_val != 'Zombie':
            self.name = name_val
            self.is_static = True
        else:
            self.is_static = template_static or is_static
            try:
                fake = Faker()
                if self.sex == 'Male':
                    self.name = fake.first_name_male()
                else:
                    self.name = fake.first_name_female()
            except ImportError:
                self.name = f"Survivor {random.randint(100, 999)}"

        if self.is_static:
            self.is_friendly = True
        else:
            self.is_friendly = False
            
        self.state = 'wandering' if not self.is_static else 'idle'
        self.is_following = False

        self.start_x = x
        self.start_y = y

        self.idle_timer = 0
        self.stuck_timer = 0
        self.stuck_angle = 0

        self.dialog_flags = set()
        self.special_dialogs = []

        loaded_data = locals().get('data', locals().get('save_data', None))

        if loaded_data:
            self.health = loaded_data.get('health', self.max_health)
            self.state = loaded_data.get('state', 'idle')
            
            if 'inventory' in loaded_data:
                self.inventory = [item_factory.create_item_from_dict(i_data) for i_data in loaded_data['inventory']]
            if 'belt' in loaded_data:
                self.belt = [item_factory.create_item_from_dict(i_data) if i_data else None for i_data in loaded_data['belt']]
            if 'clothes' in loaded_data:
                self.clothes = {}
                for slot, c_data in loaded_data['clothes'].items():
                    self.clothes[slot] = item_factory.create_item_from_dict(c_data) if c_data else None
                    
            self.dialog_flags = set(loaded_data.get('dialog_flags', []))
            self.special_dialogs = loaded_data.get('special_dialogs', [])

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

        # 1. Categorize all available weapons from templates
        melee_pool = [name for name, data in ITEM_TEMPLATES.items() if data.get('type') == 'weapon_melee']
        ranged_pool = [name for name, data in ITEM_TEMPLATES.items() if data.get('type') == 'weapon_ranged']
        
        template_weapons = []
        if hasattr(self, 'loot_table'):
            for loot_dict in self.loot_table:
                item_name = loot_dict.get('item')
                if item_name in ITEM_TEMPLATES and ITEM_TEMPLATES[item_name].get('type') in ['weapon_melee', 'weapon_ranged']:
                    template_weapons.append(item_name)
        
        weapon_name = None

        # 2. Handle Weapon Assignment
        if template_weapons:
            weapon_name = random.choice(template_weapons)
        elif not self.is_friendly:
            if random.random() < 0.05 and ranged_pool:
                weapon_name = random.choice(ranged_pool)
            elif melee_pool:
                weapon_name = random.choice(melee_pool)
            else:
                weapon_name = "Knife"
        else:
            all_weapons = melee_pool + ranged_pool
            if all_weapons:
                weapon_name = random.choice(all_weapons)
            else:
                weapon_name = "Knife"

        if weapon_name:
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
        clothes_slots = template.get('clothes_slots', []) 
        
        clothes_to_equip = {
            "feet": "Sneakers",
            "legs": "Pants",
            "body": "Tshirt",
            "arms": "Jacket" if random.random() < 0.2 else None,
            "hair": random.choice(hair_options)
        }
        
        for slot_name in clothes_slots:
            cloth_name = predefined_clothes.get(slot_name)
            if cloth_name:
                clothes_to_equip[slot_name] = cloth_name
            else:
                available_pool = ZombieData.ZOMBIE_CLOTHES_POOL.get(slot_name, [])
                if available_pool:
                    choice = random.choice(available_pool)
                    clothes_to_equip[slot_name] = choice['name'] if isinstance(choice, dict) else choice
                else:
                    clothes_to_equip[slot_name] = None
                    
        for slot_name, cloth_name in predefined_clothes.items():
            if slot_name not in clothes_to_equip:
                clothes_to_equip[slot_name] = cloth_name
        
        for slot_name, cloth_name in clothes_to_equip.items():
            if not cloth_name:
                continue
            item = Item.create_from_name(cloth_name)
            if item:
                is_explicitly_defined = (slot_name in predefined_clothes and predefined_clothes.get(slot_name) == cloth_name)

                if not is_explicitly_defined and cloth_name in ("Tshirt", "Pants", "Jacket", "Sneakers"):
                    item.color = random.choice(CLOTHING_COLORS)
                    if item.image:
                        tinted = item.image.copy()
                        tinted.fill((*item.color, 255)[:4], special_flags=pygame.BLEND_RGBA_MULT)
                        item.image = tinted
                
                actual_slot = getattr(item, 'slot', slot_name)
                
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

        self.last_grid_pos = (int(self.rect.centerx // TILE_SIZE), int(self.rect.centery // TILE_SIZE))

    def update(self, game):
        obstacles = game.obstacles
        if self.is_dead: return 

        multiplier = 1.0
        
        speed_mult = 1.0
        gx = self.rect.centerx // TILE_SIZE
        gy = self.rect.centery // TILE_SIZE
        if hasattr(game, 'map_manager'):
            tile_def = game.map_manager.get_tile_at(gx, gy)
            if tile_def:
                name = tile_def.get('name', '').lower()
                if 'window' in name or tile_def.get('is_window'):
                    speed_mult = 0.35 

        effective_speed = self.speed * multiplier * game.dt_mult * speed_mult
        current_time = pygame.time.get_ticks()
        
        current_grid_pos = (int(self.rect.centerx // TILE_SIZE), int(self.rect.centery // TILE_SIZE))
        
        if hasattr(self, 'last_grid_pos') and current_grid_pos != self.last_grid_pos:
            self.last_grid_pos = current_grid_pos

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

        if not self.is_friendly and game.player:
            if getattr(game.player, 'is_aiming', False):
                search_range *= 0.5
            elif getattr(game.player, 'is_running', False):
                search_range *= 1.5

        is_ranged_weapon = weapon and weapon.item_type == 'weapon_ranged'
        if is_ranged_weapon: search_range = self.base_search_range * 2 

        potential_targets = []
        
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
            dx_target = target_pos[0] - self.rect.centerx
            dy_target = target_pos[1] - self.rect.centery
            self.aim_angle = math.degrees(math.atan2(-dy_target, dx_target))
            self.idle_timer = 0
        else:
            self.aim_angle = self.angle
            target_pos = None
            self.state = 'idle'

        self.dx, self.dy = 0, 0
        
        if target_pos:
            dist_to_dest = math.hypot(target_pos[0] - self.rect.centerx, target_pos[1] - self.rect.centery)
            
            move_threshold = TILE_SIZE * 0.5
            if self.state == 'chasing':
                 move_threshold = (TILE_SIZE * 8) if is_ranged_weapon else (TILE_SIZE * 0.8)
            elif self.state == 'following':
                 move_threshold = TILE_SIZE * 2.5
            
            if dist_to_dest > move_threshold:
                has_los = self.has_line_of_sight(pygame.Rect(target_pos[0]-2, target_pos[1]-2, 4, 4), game, current_time)

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
            
            elif self.state == 'chasing':
                shuffle_speed = effective_speed * 0.3
                offset_x = math.sin(current_time * 0.002) * shuffle_speed
                offset_y = math.cos(current_time * 0.002) * shuffle_speed
                self.dx = offset_x
                self.dy = offset_y
                self.angle = math.degrees(math.atan2(-self.dy, self.dx))
                
            else:
                # State is not chasing, just stay idle
                pass

        if self.state == 'chasing' and target_entity:
             self._handle_combat(target_entity, game, multiplier, current_time)

        is_moving = self.dx != 0 or self.dy != 0

        if is_moving:
            self.walk_anim_angle = math.sin(time.time() * 15) * 2
            self.vx = self.dx

            if hasattr(self, 'sound_steps') and self.sound_steps:
                if not hasattr(self, 'last_step_sound_time'):
                    self.last_step_sound_time = current_time + random.randint(0, 400)
                    self.current_step_delay = random.randint(350, 450)
                    
                delay = getattr(self, 'current_step_delay', 400)
                if current_time - getattr(self, 'last_step_sound_time', 0) > delay:
                    game.sound_manager.play_sound(
                        self.sound_steps, 
                        subdir='npc', 
                        game=game, 
                        source_pos=self.rect.center, 
                        base_volume=0.3, 
                        pitch_variance=0.25 
                    )
                    self.last_step_sound_time = current_time
                    self.current_step_delay = random.randint(350, 500) 
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
                hitbox = entity.rect.inflate(-12, -12)
                if rect_check.colliderect(hitbox):
                    return True, entity
            return False, None

        for _ in range(steps):
            self.x += step_dx
            self.rect.x = int(self.x)
            
            collision, collider = check_mask_collision(self.rect)
            
            if collision:
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
                self.y -= step_dy
                self.rect.y = int(self.y)
                self.dy = 0

                if self.stuck_timer <= 0:
                     self.stuck_timer = 200
                     self.stuck_angle = random.randint(0, 360)

        self.rect.topleft = (int(self.x), int(self.y))

    def _handle_combat(self, target_entity, game, multiplier, current_time):
        weapon = getattr(self, 'equipped_weapon', None)
        is_ranged_weapon = weapon and weapon.item_type == 'weapon_ranged'
        
        dx = target_entity.rect.centerx - self.rect.centerx
        dy = target_entity.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        
        angle_to_target = math.degrees(math.atan2(-dy, dx))
        angle_diff = (angle_to_target - self.angle + 180) % 360 - 180
        
        effective_attack_range = self.attack_range
        attack_cooldown = self.attack_cooldown / multiplier 
        if is_ranged_weapon:
            effective_attack_range = TILE_SIZE * 8
            attack_cooldown = 500 / multiplier
        
        is_in_front = abs(angle_diff) < 45 

        if dist <= effective_attack_range and (current_time - self.last_attack_time > attack_cooldown):
            weapon_is_ready = True
             
            has_los = True
            if is_ranged_weapon:
                has_los = self.check_line_of_sight(target_entity, game)

            if not is_ranged_weapon and not is_in_front:
                return 

            if weapon_is_ready and has_los:
                self.last_attack_time = current_time
                attack_angle = math.atan2(-dy, dx)
                 
                base_damage = random.randint(self.min_attack, self.max_attack)
                weapon_dmg = 0
                if weapon:
                    if hasattr(weapon, 'damage'):
                        weapon_dmg = weapon.damage
                    elif hasattr(weapon, 'min_damage') and hasattr(weapon, 'max_damage'):
                        weapon_dmg = random.randint(weapon.min_damage, weapon.max_damage)
                
                damage_to_deal = max(1, base_damage + weapon_dmg)
                 
                if is_ranged_weapon and weapon:
                    weapon_sound = weapon.sounds.get('shoot') if hasattr(weapon, 'sounds') else None
                    
                    if weapon_sound:
                        game.sound_manager.play_sound(
                            weapon_sound, 
                            subdir='items', 
                            game=game, 
                            source_pos=self.rect.center, 
                            base_volume=0.5
                        )

                    projectile = Projectile(self.rect.centerx, self.rect.centery, target_entity.rect.centerx, target_entity.rect.centery, speed=20)
                    projectile.damage = damage_to_deal
                    projectile.owner = self
                    projectile.hostile = True
                    game.projectiles.append(projectile)
                    
                else: 
                    if getattr(self, 'sound_attack', None):
                        game.sound_manager.play_sound(
                            self.sound_attack, subdir='npc', 
                            game=game, 
                            source_pos=self.rect.center, 
                            base_volume=0.3, 
                            pitch_variance=0.15
                        )
                    self.melee_swing_timer = 250
                    self.melee_swing_angle = attack_angle
                    
                    if target_entity == game.player:
                        target_entity.take_damage(game, damage_to_deal, 0)
                    else:
                        is_dead = target_entity.take_damage(damage_to_deal, game, attacker=self)
                        if is_dead:
                            target_entity.die(game)

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
        self.kill()

        if getattr(self, 'spawn_zombies_max', 0) > 0:
            reanimated_zombie = Zombie.create_random(self.rect.centerx, self.rect.centery)
            reanimated_zombie.aggro_timer = 10000
            reanimated_zombie.state = 'chasing'
            game.zombies.append(reanimated_zombie)
            
            if hasattr(game, 'player') and game.player:
                dx = self.rect.centerx - game.player.rect.centerx
                dy = self.rect.centery - game.player.rect.centery
                
                if (dx*dx + dy*dy) <= (getattr(game, 'player_view_radius', TILE_SIZE * 20) * 1.5) ** 2:
                    import core.data.config as game_config
                    num_zombies_to_spawn = int((random.randint(0, game_config.ZOMBIES_PER_SPAWN))) + 1
                    
                    for _ in range(num_zombies_to_spawn):
                        spawn_x, spawn_y = None, None
                        for attempt in range(10):
                            angle = random.uniform(0, math.pi * 2)
                            radius = random.uniform(TILE_SIZE * 10, TILE_SIZE * 15)
                            tx = game.player.rect.centerx + math.cos(angle) * radius
                            ty = game.player.rect.centery + math.sin(angle) * radius
                            
                            gx, gy = int(tx // TILE_SIZE), int(ty // TILE_SIZE)
                            if 0 <= gy < len(game.map_data) and 0 <= gx < len(game.map_data[0]):
                                tile_def = game.map_manager.get_tile_at(gx, gy)
                                if not tile_def or not tile_def.get('is_obstacle', False):
                                    spawn_x, spawn_y = tx, ty
                                    break

                        zombie = Zombie.create_random(spawn_x, spawn_y)
                        zombie.aggro_timer = 10000
                        zombie.state = 'chasing'
                        game.zombies.append(zombie)