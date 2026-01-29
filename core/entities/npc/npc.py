import pygame
import random
import os
import math
import time
from core.entities.item.item import Item, Projectile, ITEM_TEMPLATES
from core.entities.zombie.corpse import Corpse
from core.messages import display_message
import xml.etree.ElementTree as ET
from core.entities.zombie.zombie import Zombie, ZOMBIE_CLOTHES_POOL
from core.data.config import *

class NPC(Zombie):
    _base_cache = {} 
    NPC_TEMPLATES = [] 
    NPC_DIALOGS = None

    def __init__(self, x, y, game, is_static=False):
        if not NPC.NPC_TEMPLATES:
            NPC.load_templates()

        if NPC.NPC_TEMPLATES:
            template = random.choice(NPC.NPC_TEMPLATES)
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

        super().__init__(x, y, template)
        
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

        self.idle_timer = 0
        
        self.stuck_timer = 0
        self.stuck_angle = 0
        
        self.dialog_flags = set()

        self.knockback_velocity = [0, 0]
        self.knockback_timer = 0

        self.inventory = []
        id_card = Item.create_from_name("ID")
        self.inventory.append(id_card)

        if not self.inventory:
             random_item = Item.generate_random()
             if random_item:
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
        self.dead_image = self.load_sprite('zombie/dead.png')
        
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

    def load_sprite(self, sprite_file):
        if not sprite_file: return None
        candidates = [
            os.path.join(SPRITE_PATH, "player", sprite_file),
            os.path.join(SPRITE_PATH, sprite_file),
            os.path.join(SPRITE_PATH, "zombie", sprite_file)
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                except Exception as e:
                    print(f"Error loading NPC sprite at {path}: {e}")
        return None

    @staticmethod
    def load_templates():
        npc_folder = os.path.join(DATA_PATH, 'npc')
        NPC.NPC_TEMPLATES = []
        if not os.path.exists(npc_folder):
            print(f"NPC Warning: Folder not found at {npc_folder}")
            return
        for filename in os.listdir(npc_folder):
            if filename.endswith('.xml'):
                filepath = os.path.join(npc_folder, filename)
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    if root.tag == 'zombie':
                        template = {}
                        name_node = root.find('name')
                        template['name'] = name_node.get('value') if name_node is not None else 'Survivor'
                        stats_node = root.find('stats')
                        if stats_node is not None:
                            health_node = stats_node.find('health')
                            template['min_health'] = int(health_node.get('min', 100))
                            template['max_health'] = int(health_node.get('max', 100))
                            template['health'] = template['max_health'] 
                            speed_node = stats_node.find('speed')
                            template['min_speed'] = float(speed_node.get('min', 1.0))
                            template['max_speed'] = float(speed_node.get('max', 1.0))
                            template['speed'] = template['max_speed']
                            attack_node = stats_node.find('attack')
                            template['min_attack'] = int(attack_node.get('min', 5))
                            template['max_attack'] = int(attack_node.get('max', 10))
                            infection_node = stats_node.find('infection')
                            template['min_infection'] = int(infection_node.get('min', 0))
                            template['max_infection'] = int(infection_node.get('max', 0))
                        xp_node = root.find('xp')
                        if xp_node is not None:
                            template['min_xp'] = float(xp_node.get('min', 10))
                            template['max_xp'] = float(xp_node.get('max', 20))
                        else:
                            template['min_xp'], template['max_xp'] = 10, 20
                        visuals_node = root.find('visuals')
                        template['sprites'] = {}
                        if visuals_node is not None:
                            for sprite_node in visuals_node.findall('sprite'):
                                s_id = sprite_node.get('id')
                                s_file = sprite_node.get('file')
                                if s_id and s_file:
                                    template['sprites'][s_id] = s_file
                        clothes_node = root.find('clothes')
                        template['clothes_slots'] = []
                        if clothes_node is not None:
                            for slot_node in clothes_node:
                                template['clothes_slots'].append(slot_node.tag)
                        sound_node = root.find('sound')
                        template['sounds'] = {}
                        if sound_node is not None:
                            for sound_type in ['hit', 'wander', 'dead', 'attack', 'steps']:
                                node = sound_node.find(sound_type)
                                if node is not None:
                                    template['sounds'][sound_type] = node.get('src')
                        template['sex'] = root.find('sex').get('value') if root.find('sex') is not None else 'Random'
                        template['profession'] = root.find('profession').get('value') if root.find('profession') is not None else 'Survivor'
                        template['loot'] = [] 
                        NPC.NPC_TEMPLATES.append(template)
                except Exception as e:
                    print(f"NPC Error: Could not load {filename}: {e}")

    def _load_base_sprite(self):
        candidates = ["player/base.png", "player/player.png", "player/idle.png", "zombie/zombie.png"]
        found_img = None
        for filename in candidates:
            if filename in NPC._base_cache:
                found_img = NPC._base_cache[filename]; break
            full_path_A = os.path.join(SPRITE_PATH, *filename.split('/'))
            full_path_B = os.path.join(SPRITE_PATH, filename)
            if os.path.exists(full_path_A):
                try:
                    img = pygame.image.load(full_path_A).convert_alpha()
                    found_img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                    NPC._base_cache[filename] = found_img
                    break
                except: pass
            elif os.path.exists(full_path_B):
                 try:
                    img = pygame.image.load(full_path_B).convert_alpha()
                    found_img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                    NPC._base_cache[filename] = found_img
                    break
                 except: pass
        if found_img:
            self.images['center'] = found_img
            self.images['left'] = found_img
            self.images['right'] = found_img
            self.image = found_img
        else:
             print("NPC Error: No valid sprite found! Rendering as Red Square.")

    def _assign_random_clothes(self):
        self.clothes = {}
        slots = ['legs', 'body', 'head']
        for slot in slots:
            if slot == 'head' and random.random() < 0.3: continue 
            available = ZOMBIE_CLOTHES_POOL.get(slot, [])
            if available:
                choice = random.choice(available)
                if isinstance(choice, str):
                    self.clothes[slot] = Item.create_from_name(choice)
                elif isinstance(choice, dict) and 'name' in choice:
                    self.clothes[slot] = Item.create_from_name(choice['name'])

    def check_line_of_sight(self, target, game):
        x1, y1 = self.rect.center
        x2, y2 = target.rect.center
        distance = math.hypot(x2 - x1, y2 - y1)
        if distance == 0: return True
        step_size = TILE_SIZE / 2
        steps = int(distance / step_size)
        if steps < 1: return True
        dx = (x2 - x1) / steps
        dy = (y2 - y1) / steps
        check_rect = pygame.Rect(0, 0, 4, 4) 
        for i in range(1, steps): 
            check_x = x1 + dx * i
            check_y = y1 + dy * i
            check_rect.center = (int(check_x), int(check_y))
            for obstacle in game.obstacles:
                if check_rect.colliderect(obstacle):
                    return False
        return True

    def _switch_weapon(self, game):
        best_candidate = None
        for item in self.inventory:
            if item.item_type == 'weapon_melee':
                best_candidate = item; break 
            elif item.item_type == 'weapon_ranged' and item.load > 0:
                best_candidate = item; break 
        if best_candidate:
            if self.equipped_weapon:
                self.inventory.append(self.equipped_weapon)
            self.inventory.remove(best_candidate)
            self.equipped_weapon = best_candidate
            display_message(game, f"{self.name} switched to {best_candidate.name}!")
            return True
        return False

    def _try_reload(self, weapon, game):
        if not weapon.ammo_type: return False
        for item in self.inventory:
            if item.name == weapon.ammo_type and item.load > 0:
                needed = weapon.capacity - weapon.load
                amount = min(needed, item.load)
                weapon.load += amount
                item.load -= amount
                if item.load <= 0: self.inventory.remove(item)
                display_message(game, f"{self.name} reloaded!")
                return True
        return False

    def update(self, game):
        obstacles = game.obstacles
        if self.is_dead: return 


        current_time = pygame.time.get_ticks()
        
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
            dt = 16 
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
            self.idle_timer -= 1
            self.state = 'idle'
            self.dx = 0
            self.dy = 0
            # Skip normal movement logic
        else:
            if target_entity:
                dx = target_entity.rect.centerx - self.rect.centerx
                dy = target_entity.rect.centery - self.rect.centery
                dist = math.hypot(dx, dy)
                
                is_avoiding = False
                if self.stuck_timer > 0:
                    self.stuck_timer -= 1
                    is_avoiding = True

                attack_cooldown = self.attack_cooldown
                effective_attack_range = self.attack_range
                
                if is_ranged_weapon:
                    effective_attack_range = TILE_SIZE * 8 
                    attack_cooldown = 500 
                elif weapon and weapon.item_type in ['weapon_melee', 'tool']:
                    effective_attack_range = TILE_SIZE * 1.2
                    attack_cooldown = 1000

                if self.state == 'chasing':
                    move_threshold = effective_attack_range * 0.8 if is_ranged_weapon else TILE_SIZE * 0.8
                elif self.state == 'following':
                    move_threshold = TILE_SIZE * 2
                else:
                    move_threshold = 0
                
                if dist > move_threshold and not is_avoiding:
                    self.angle = math.degrees(math.atan2(-dy, dx))

                    if not self.is_static:
                        scale = self.speed / dist
                        self.dx = dx * scale
                        self.dy = dy * scale
                    else:
                        self.dx, self.dy = 0, 0

                elif is_avoiding:
                    if not self.is_static:
                        self.angle = self.stuck_angle
                        rad = math.radians(self.angle)
                        self.dx = math.cos(rad) * self.speed * 1.0 
                        self.dy = -math.sin(rad) * self.speed * 1.0
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
                                 self.last_attack_time = current_time + 1000
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
                                     
                                    # Calculate defence and reduction (replicating Player.take_damage logic)
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
                self.state = 'wandering'
                if not self.is_static:
                    if random.random() < 0.02:
                        self.angle += random.randint(-45, 45)
                    rad = math.radians(self.angle)
                    self.dx = math.cos(rad) * self.speed * 0.5
                    self.dy = -math.sin(rad) * self.speed * 0.5
                else:
                    self.dx, self.dy = 0, 0

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

        self.x += self.dx
        self.rect.x = int(self.x)
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if self.dx > 0: self.rect.right = obstacle.left
                elif self.dx < 0: self.rect.left = obstacle.right
                self.x = self.rect.x
                self.stuck_timer = 30 
                self.stuck_angle = random.randint(0, 360)
                self.dx = 0
                break

        for entity in entities_to_check:
            if self.rect.colliderect(entity.rect):
                if self.dx > 0: self.rect.right = entity.rect.left
                elif self.dx < 0: self.rect.left = entity.rect.right
                self.x = self.rect.x
                self.dx = 0
                break

        self.y += self.dy
        self.rect.y = int(self.y)
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if self.dy > 0: self.rect.bottom = obstacle.top
                elif self.dy < 0: self.rect.top = obstacle.bottom
                self.y = self.rect.y
                self.stuck_timer = 30 
                self.stuck_angle = random.randint(0, 360)
                self.dy = 0
                break

        for entity in entities_to_check:
            if self.rect.colliderect(entity.rect):
                if self.dy > 0: self.rect.bottom = entity.rect.top
                elif self.dy < 0: self.rect.top = entity.rect.bottom
                self.y = self.rect.y
                self.dy = 0
                break

        self.rect.topleft = (int(self.x), int(self.y))

    def stop_moving(self):
        """Forces the NPC to stop moving and enter idle state."""
        self.state = 'idle'
        self.path = []      
        self.target = None
        self.velocity = pygame.math.Vector2(0, 0)
        # [FIX 2] Set timer for 300 frames (approx 5 seconds at 60 FPS)
        self.idle_timer = 500 

    def die(self, game):
        if self.is_dead: return
        self.is_dead = True 

        corpse = Corpse(
            name=f"Corpse of {self.name}",
            capacity=20,
            pos=self.rect.center, 
            image_path="zombie/dead.png",
            decay_ms=3600000
        )
        
        for item in self.inventory:
            corpse.inventory.append(item)
            
        if self.equipped_weapon:
            corpse.inventory.append(self.equipped_weapon)
            
        if hasattr(self, 'clothes') and self.clothes:
            for cloth_data in self.clothes.values():
                if isinstance(cloth_data, Item):
                    corpse.inventory.append(cloth_data)
                elif isinstance(cloth_data, dict):
                    name = cloth_data.get('name')
                    if name: corpse.inventory.append(Item.create_from_name(name))
                elif isinstance(cloth_data, str):
                     corpse.inventory.append(Item.create_from_name(cloth_data))

        game.items_on_ground.append(corpse)
        
        if self in game.npcs:
            game.npcs.remove(self)


    @staticmethod
    def load_dialogs():
        """Parses the new Node-based XML structure."""
        if NPC.NPC_DIALOGS is not None: return
        
        NPC.NPC_DIALOGS = {} 
        path = os.path.join(DATA_PATH, 'npc', 'dialogs.xml')
        
        if not os.path.exists(path):
            print(f"NPC Warning: Dialog file not found at {path}")
            return

        try:
            tree = ET.parse(path)
            root = tree.getroot()
            
            # [CHANGED] Iterate through <node> elements instead of flat <options>
            for node in root.findall('node'):
                node_id = node.get('id')
                if not node_id: continue
                
                NPC.NPC_DIALOGS[node_id] = []
                
                for opt in node.findall('options'):
                    question = opt.get('player_question')
                    answer = opt.get('npc_answer')
                    
                    # Read priority (default 100) and unlock_flag
                    try:
                        priority = int(opt.get('priority', '100'))
                    except ValueError:
                        priority = 100
                        
                    unlock_flag = opt.get('unlock_flag') # Can be None
                    npc_state_friendly = opt.get('npc_state_friendly') # Returns string "true"/"false" or None
                    npc_state_static = opt.get('npc_state_static')     # Returns string "true"/"false" or None
                    award_item = opt.get('award_item')

                    if question and answer:
                        NPC.NPC_DIALOGS[node_id].append({
                            'q': question, 
                            'a': answer,
                            'priority': priority,
                            'unlock_flag': unlock_flag,
                            'npc_state_friendly': npc_state_friendly, # Store raw string
                            'npc_state_static': npc_state_static,     # Store raw string
                            'award_item': award_item
                        })
                    
        except Exception as e:
            print(f"NPC Error: Could not load dialogs: {e}")


    def get_dialog_options(self):
        """Generates options based on mandatory nodes + unlocked flags."""
        if NPC.NPC_DIALOGS is None:
            NPC.load_dialogs()
        
        options = []
        
        # 1. Define Mandatory Nodes
        mandatory_nodes = {"greeting", "tips", "lore_branch"}
        
        # 2. Determine Active Nodes (Mandatory + Unlocked)
        active_nodes = mandatory_nodes.union(self.dialog_flags)
        
        # [CHANGED] Sort the nodes. 
        # Since we now refresh the menu dynamically, using a Set (unordered) 
        # would cause questions to jump around randomly every time we go back.
        sorted_nodes = sorted(list(active_nodes))
        
        # 3. Generate one option per active node
        for node_id in sorted_nodes:
            node_options = NPC.NPC_DIALOGS.get(node_id)
            if not node_options:
                continue
                
            # Weighted Random Selection
            total_priority = sum(opt['priority'] for opt in node_options)
            if total_priority <= 0: continue
            
            pick = random.randint(1, total_priority)
            current = 0
            selected_opt = None
            
            for opt in node_options:
                current += opt['priority']
                if pick <= current:
                    selected_opt = opt.copy() 
                    break
            
            if selected_opt:
                options.append(selected_opt)
            
        # 4. Format Text (Replacements)
        inv_str = ", ".join([i.name for i in self.inventory]) if self.inventory else "nothing"
        cloth_str = ", ".join([i.name for i in self.clothes.values()]) if self.clothes else "ragged clothes"
        
        for opt in options:
            if opt['a']:
                opt['a'] = opt['a'].replace('[inventory_list]', inv_str)
                opt['a'] = opt['a'].replace('[clothes_list]', cloth_str)
                
        return options


    def unlock_node(self, node_id):
        """Unlocks a new dialog node for this NPC."""
        if node_id:
            self.dialog_flags.add(node_id)
            print(f"NPC Dialog unlocked: {node_id}")


    def draw(self, surface, offset_x, offset_y, opacity=255):
        if self.is_dead and self.dead_image:
            draw_rect = self.rect.move(offset_x, offset_y)
            surface.blit(self.dead_image, draw_rect)
            return
        
        super().draw(surface, offset_x, offset_y, opacity)
        
        max_h = self.template.get('max_health', 100) if hasattr(self, 'template') else 100
        
        if self.health < max_h and self.health_bar_timer > 0:
            bar_width = TILE_SIZE
            bar_height = 4
            
            bar_x = self.rect.x + offset_x
            bar_y = self.rect.y + offset_y - 8 
            
            pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))
            
            health_ratio = max(0, self.health / max_h)
            current_width = int(bar_width * health_ratio)
            pygame.draw.rect(surface, (0, 255, 0), (bar_x, bar_y, current_width, bar_height))

        weapon = self.equipped_weapon
        if weapon and weapon.image:
            angle_rad = math.radians(self.angle)
            angle_deg = -self.angle

            if weapon.item_type == 'weapon_melee' and self.melee_swing_timer > 0:
                SWING_DURATION = 15
                swing_progress = (SWING_DURATION - self.melee_swing_timer) / SWING_DURATION
                base_angle_rad = self.melee_swing_angle
                SWING_ARC_RADIANS = math.pi / 2
                swing_offset = (swing_progress * SWING_ARC_RADIANS) - (SWING_ARC_RADIANS / 2) 
                current_weapon_angle_rad = base_angle_rad + swing_offset 
                weapon_distance_from_center = TILE_SIZE * 0.7 
                weapon_center_x = self.rect.centerx + math.cos(current_weapon_angle_rad) * weapon_distance_from_center
                weapon_center_y = self.rect.centery - math.sin(current_weapon_angle_rad) * weapon_distance_from_center
                angle_deg = -math.degrees(current_weapon_angle_rad)
            else:
                hand_offset_dist = TILE_SIZE * 0.4
                angle_rad = math.radians(self.angle)
                weapon_center_x = self.rect.centerx + math.cos(angle_rad) * hand_offset_dist
                weapon_center_y = self.rect.centery - math.sin(angle_rad) * hand_offset_dist
                angle_deg = -self.angle

            rotated_image = pygame.transform.rotate(weapon.image, angle_deg)
            new_rect = rotated_image.get_rect(center=(weapon_center_x + offset_x, weapon_center_y + offset_y))
            surface.blit(rotated_image, new_rect.topleft)

    def take_damage(self, damage, game, attacker=None):
        if self.is_dead: return True
        self.health -= damage
        self.health_bar_timer = 180
        if attacker == game.player:
            self.is_friendly = False
            self.state = 'chasing'
        if hasattr(game, 'blood_stains') and damage > 0:
             count = random.randint(1, 2)
             for _ in range(count):
                 game.blood_stains.append({
                    'pos': (self.rect.centerx + random.randint(-8, 8), self.rect.centery + random.randint(-8, 8)),
                    'size': random.randint(5, 12),
                    'color': (139, 0, 0),
                    'time': pygame.time.get_ticks(),
                    'duration': random.randint(30000, 60000)
                 })
        if hasattr(game, 'splashes') and damage > 0:
             game.splashes.append({
                'pos': self.rect.center,
                'time': pygame.time.get_ticks(),
                'duration': 350,
                'radius': 3,
                'type': 'hit_puff' 
             })
        if self.health <= 0:
            self.die(game)
            return True
        return False