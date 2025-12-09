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
from core.data.config import TILE_SIZE, SPRITE_PATH, DATA_PATH

class NPC(Zombie):
    # --- Class-Level Cache ---
    _base_cache = {} 
    NPC_TEMPLATES = [] # Store loaded NPC templates here

    def __init__(self, x, y, game):
        # 1. Load templates if they haven't been loaded yet
        if not NPC.NPC_TEMPLATES:
            NPC.load_templates()

        # 2. Select a template (Fallback to hardcoded if XML fails)
        if NPC.NPC_TEMPLATES:
            template = random.choice(NPC.NPC_TEMPLATES)
        else:
            # Fallback template
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

        # 3. Initialize parent (Zombie) with the chosen template
        super().__init__(x, y, template)
        
        self.game = game
        
        # Override name if template was random/generic
        if self.name == "Zombie" or self.name == "RANDOM":
             self.name = f"Survivor {random.randint(100, 999)}"

        self.is_friendly = True
        self.is_following = False
        self.state = 'wandering'

        # --- Pathing/Stuck Fix Attributes ---
        self.stuck_timer = 0
        self.stuck_angle = 0
        # --- END Pathing/Stuck Fix Attributes ---

        # --- NPC Specific Inventory/Loot Setup (Fix: Loot initialization) ---
        self.inventory = []
        id_card = Item.create_from_name("ID")
        if id_card:
            id_card.name = f"{self.name}'s ID"
        self.inventory.append(id_card)

        # Give the NPC a random item as starting loot if its template didn't provide any
        if not self.inventory:
             random_item = Item.generate_random()
             if random_item:
                 self.inventory.append(random_item)
        # --- END NPC Loot Setup ---

        # --- NPC Weapon Setup (Fix: Equipped Weapon) ---
        possible_weapons = [name for name, data in ITEM_TEMPLATES.items() 
                            if data.get('type') in ['weapon_melee', 'weapon_ranged']]
        
        if possible_weapons:
            weapon_name = random.choice(possible_weapons)
            self.equipped_weapon = Item.create_from_name(weapon_name, randomize_durability=True)
        else:
            # Fallback if no templates found
            self.equipped_weapon = Item.create_from_name("Knife", randomize_durability=True)
            
        # Fallback if creation failed
        if not self.equipped_weapon:
             self.equipped_weapon = Item.generate_random()

        self.melee_swing_timer = 0
        self.melee_swing_angle = 0
        # --- END NPC Weapon Setup ---

        self.is_dead = False
        self.dead_image = self.load_sprite('zombie/dead.png')
        
        # Ensure movement attributes exist
        if not hasattr(self, 'angle'): self.angle = 0
        if not hasattr(self, 'dx'): self.dx = 0
        if not hasattr(self, 'dy'): self.dy = 0
        
        if not hasattr(self, 'speed') or self.speed == 0:
            self.speed = 1.1
            
        self.attack_range = TILE_SIZE * 1
        self.last_attack_time = 0
        self.attack_cooldown = 1000
        
        self.health_bar_timer = 0

        # --- Visual Setup ---
        # Fix: Check if 'center' is missing, not just if the dict is empty
        if not self.images or not self.images.get('center'):
            self._load_base_sprite()
            
        # Only assign random clothes if the XML didn't specify them
        if not self.clothes:
             self._assign_random_clothes()

    def load_sprite(self, sprite_file):
        """Override to prefer player/ folder for NPCs."""
        if not sprite_file: return None
        
        # Paths to check for NPC sprites
        candidates = [
            os.path.join(SPRITE_PATH, "player", sprite_file), # Prefer player/
            os.path.join(SPRITE_PATH, sprite_file),
            os.path.join(SPRITE_PATH, "zombie", sprite_file)  # Fallback
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
        """Loads NPC templates from game/lib/data/npc/."""
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
                        
                        # Add an empty loot list if not found (to match fallback template)
                        template['loot'] = [] 

                        NPC.NPC_TEMPLATES.append(template)

                except Exception as e:
                    print(f"NPC Error: Could not load {filename}: {e}")

    def _load_base_sprite(self):
        """Robustly loads a base sprite (Fallback if XML has no visuals)."""
        candidates = ["player/base.png", "player/player.png", "player/idle.png", "zombie/zombie.png"]
        found_img = None

        for filename in candidates:
            if filename in NPC._base_cache:
                found_img = NPC._base_cache[filename]; break
            
            # Check multiple path styles (exact path vs sprite root)
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
        """Fallback clothes assignment."""
        self.clothes = {}
        slots = ['legs', 'body', 'head']
        for slot in slots:
            if slot == 'head' and random.random() < 0.3: continue 
            available = ZOMBIE_CLOTHES_POOL.get(slot, [])
            if available:
                self.clothes[slot] = random.choice(available)

    def update(self, game):
        """Updates the NPC: AI, Physics, Animation. (Fix: Pathing and Ammo Check)"""
        obstacles = game.obstacles

        if self.is_dead:
            return # Stop updating physics/AI if dead

        current_time = pygame.time.get_ticks()

        entities_to_check = [e for e in game.npcs if e != self and not e.is_dead]
        if game.player and not game.player.is_dead:
            entities_to_check.append(game.player)

        # --- AI: Find and Attack Zombies ---
        target_entity = None

        FOLLOW_PRIORITY_RANGE = TILE_SIZE * 20 # 20 tiles threshold to prioritize following
        
        player_is_far_and_following = False
        if game.player:
            player_dist = math.hypot(game.player.rect.centerx - self.rect.centerx, game.player.rect.centery - self.rect.centery)
            if self.is_following and player_dist > FOLLOW_PRIORITY_RANGE:
                player_is_far_and_following = True

        # Determine effective search range based on weapon
        weapon = getattr(self, 'equipped_weapon', None)
        search_range = TILE_SIZE * 15 # Default search range (15 tiles)
        is_ranged_weapon = weapon and weapon.item_type == 'weapon_ranged'
        if is_ranged_weapon:
            search_range = TILE_SIZE * 30 # Search further for ranged attacks

        # 1. Prioritize Attack nearby Zombie
        min_dist_to_zombie = float('inf')
        
        if not player_is_far_and_following:
            # Check Zombies
            for zombie in game.zombies:
                dist = math.hypot(zombie.rect.centerx - self.rect.centerx, zombie.rect.centery - self.rect.centery)
                if dist < search_range and dist < min_dist_to_zombie: # Use modified search range
                    min_dist_to_zombie = dist
                    target_entity = zombie
                    self.state = 'chasing'
            
            # Check Player (Hostility Check)
            if not self.is_friendly and game.player and not game.player.is_dead:
                 dist_p = math.hypot(game.player.rect.centerx - self.rect.centerx, game.player.rect.centery - self.rect.centery)
                 # If player is within range and closer than the closest zombie (or no zombie found)
                 if dist_p < search_range and dist_p < min_dist_to_zombie:
                     target_entity = game.player
                     self.state = 'chasing'


        # 2. If no immediate zombie threat, check if following the player
        if not target_entity and self.is_following and game.player or player_is_far_and_following:
            # Follow if player is far (e.g., more than 2 tiles away)
            if player_dist > TILE_SIZE * 2 or player_is_far_and_following:
                target_entity = game.player
                self.state = 'following'

        # 3. Move/Act based on the determined target
        if target_entity:
            dx = target_entity.rect.centerx - self.rect.centerx
            dy = target_entity.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            
            # --- Pathing Avoidance Logic ---
            is_avoiding = False
            if self.stuck_timer > 0:
                self.stuck_timer -= 1
                is_avoiding = True

            # Determine weapon-specific attack parameters
            attack_cooldown = self.attack_cooldown
            effective_attack_range = self.attack_range
            
            if is_ranged_weapon:
                effective_attack_range = TILE_SIZE * 8 # Attack range for shooting (8 tiles)
                attack_cooldown = 500 # Faster firing
            elif weapon and weapon.item_type in ['weapon_melee', 'tool']:
                effective_attack_range = TILE_SIZE * 1.2
                attack_cooldown = 1000

            # Determine movement threshold based on state and weapon range
            if self.state == 'chasing':
                # Stop slightly outside melee range, or at ranged effective range
                move_threshold = effective_attack_range * 0.8 if is_ranged_weapon else TILE_SIZE * 0.8
            elif self.state == 'following':
                move_threshold = TILE_SIZE * 2
            else:
                move_threshold = 0
            
            if dist > move_threshold and not is_avoiding:
                # Normal chasing movement
                self.angle = math.degrees(math.atan2(-dy, dx))
                scale = self.speed / dist
                self.dx = dx * scale
                self.dy = dy * scale
            elif is_avoiding:
                # Avoidance movement (uses self.stuck_angle)
                self.angle = self.stuck_angle
                rad = math.radians(self.angle)
                self.dx = math.cos(rad) * self.speed * 1.0 
                self.dy = -math.sin(rad) * self.speed * 1.0
            else:
                # Stopped/Idle movement
                self.dx, self.dy = 0, 0
                if self.state == 'following':
                    self.state = 'idle'
                
            # Attack logic
            if self.state == 'chasing':
                if dist <= effective_attack_range and (current_time - self.last_attack_time > attack_cooldown):
                    
                    # Weapon Break/Load Check before attacking
                    weapon_is_ready = True
                    if weapon and weapon.durability is not None and weapon.durability <= 0:
                        display_message(game, f"{self.name}'s {weapon.name} broke!")
                        self.equipped_weapon = None 
                        weapon_is_ready = False
                        weapon = None 
                        
                    # Stop shooting when ranged weapon is out of ammo
                    if weapon and weapon.item_type == 'weapon_ranged' and weapon.load is not None and weapon.load <= 0:
                         weapon_is_ready = False
                         if weapon.sounds and 'noammo' in weapon.sounds:
                            game.sound_manager.play_sound(weapon.sounds['noammo'], subdir='items', game=game, source_pos=self.rect.center)
                         
                         # Drop the empty ranged weapon and prepare for melee
                         display_message(game, f"{self.name}'s {weapon.name} is out of ammo! Dropping it to switch to melee.")
                         self.inventory.append(self.equipped_weapon) 
                         self.equipped_weapon = None 
                         weapon = None 
                    
                    if weapon_is_ready:
                        self.last_attack_time = current_time
                        attack_angle = math.atan2(-dy, dx)
                        
                        damage_to_deal = random.randint(self.min_attack, self.max_attack)
                        if weapon:
                             damage_range = weapon.current_damage_range 
                             if damage_range[1] > 0: 
                                 damage_to_deal = random.randint(damage_range[0], damage_range[1])
                        
                        is_dead = False
                        
                        # Apply durability reduction after damage is calculated
                        if weapon and weapon.durability is not None:
                             weapon.durability -= 1 # Deduct durability on successful attack attempt

                        if is_ranged_weapon and weapon: # Check weapon exists after ammo check
                            # Ranged Attack
                            if hasattr(game, 'projectiles') and weapon.load is not None and weapon.load > 0:
                                # Use one unit of load as ammo
                                weapon.load -= 1
                                if weapon.sounds and 'shoot' in weapon.sounds:
                                    game.sound_manager.play_sound(weapon.sounds['shoot'], subdir='items', game=game, source_pos=self.rect.center)

                                projectile = Projectile(
                                    self.rect.centerx, 
                                    self.rect.centery, 
                                    target_entity.rect.centerx, 
                                    target_entity.rect.centery, 
                                    speed=20
                                )
                                # [FIX] Add projectile to game list
                                game.projectiles.append(projectile)
                            
                            # Note: Projectile handles damage when it hits, 
                            # but for instant-hit logic (if you aren't using real projectiles for damage):
                            # Since we are using projectiles now, we let the projectile update loop handle damage.
                            pass


                        else: # Melee Attack (or if ranged weapon broke/ran out)
                            self.melee_swing_timer = 15
                            self.melee_swing_angle = attack_angle
                            
                            if weapon and weapon.sounds and 'swing' in weapon.sounds:
                                game.sound_manager.play_sound(weapon.sounds['swing'], subdir='items', game=game, source_pos=self.rect.center)
                            
                            # Deal damage
                            if target_entity == game.player:
                                 if hasattr(target_entity, 'take_durability_damage'):
                                     target_entity.take_durability_damage(damage_to_deal, game)
                                 target_entity.take_damage(game, damage_to_deal, 0)
                                 display_message(game, f"{self.name} attacked you!")
                            else:
                                 is_dead = target_entity.take_damage(damage_to_deal, game, attacker=self)
                        
                        if is_dead and target_entity != game.player:
                            if target_entity in game.zombies:
                                target_entity.die(game)
                        
        else:
            self.state = 'wandering'
            if random.random() < 0.02:
                self.angle += random.randint(-45, 45)
            rad = math.radians(self.angle)
            self.dx = math.cos(rad) * self.speed * 0.5
            self.dy = -math.sin(rad) * self.speed * 0.5

        

        # Optimization & Animation
        is_moving = self.dx != 0 or self.dy != 0

        if is_moving:
            self.walk_anim_angle = math.sin(time.time() * 15) * 2
            self.vx = self.dx
        else:
            self.walk_anim_angle = 0
            self.vx = 0
            
        if self.melee_swing_timer > 0: # Decrement swing timer regardless of movement
            self.melee_swing_timer -= 1

        if self.health_bar_timer > 0:
            self.health_bar_timer -= 1

        if not is_moving: return

        # --- Apply Physics ---
        self.x += self.dx
        self.rect.x = int(self.x)
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if self.dx > 0: self.rect.right = obstacle.left
                elif self.dx < 0: self.rect.left = obstacle.right
                self.x = self.rect.x
                # Pathing Fix: Force avoidance on collision
                self.stuck_timer = 30 # 0.5 seconds of random direction
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
                # Pathing Fix: Force avoidance on collision
                self.stuck_timer = 30 # 0.5 seconds of random direction
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

    def die(self, game):
        """Creates a corpse at the NPC's position and transfers all equipped clothes, weapon, and inventory to it."""
        if self.is_dead: return
        self.is_dead = True # Mark as dead immediately to prevent loop

        # 1. Create Corpse
        corpse = Corpse(
            name=f"Corpse of {self.name}",
            capacity=20,
            pos=self.rect.center, 
            image_path="zombie/dead.png",
            decay_ms=3600000
        )
        
        # 2. Transfer Inventory (includes ID Card)
        for item in self.inventory:
            corpse.inventory.append(item)
            
        # 3. Transfer Equipped Weapon
        if self.equipped_weapon:
            corpse.inventory.append(self.equipped_weapon)
            
        # 4. Drop Current Clothes [FIXED SECTION]
        if hasattr(self, 'clothes') and self.clothes:
            for cloth_data in self.clothes.values():
                # cloth_data is a dict (e.g. {'name': 'Blue Jeans', ...}), so we must convert it
                if cloth_data and isinstance(cloth_data, dict):
                    item_name = cloth_data.get('name')
                    if item_name:
                        # Create a real Item object from the name
                        cloth_item = Item.create_from_name(item_name)
                        if cloth_item:
                            corpse.inventory.append(cloth_item)
                elif isinstance(cloth_data, Item):
                    # Handle case if it somehow is already an Item object
                    corpse.inventory.append(cloth_data)

        # 5. Add to game world and remove NPC
        game.items_on_ground.append(corpse)
        
        if self in game.npcs:
            game.npcs.remove(self)

    def draw(self, surface, offset_x, offset_y, opacity=255):
        if self.is_dead and self.dead_image:
            draw_rect = self.rect.move(offset_x, offset_y)
            surface.blit(self.dead_image, draw_rect)
            return
        
        # Call parent's draw method (inherited from Zombie) for non-dead state
        super().draw(surface, offset_x, offset_y, opacity)
        
        # --- [FIX] Draw Health Bar if Damaged ---
        # NOTE: self.health and self.template['max_health'] must exist.
        # Max health is usually set in template or __init__.
        max_h = self.template.get('max_health', 100) if hasattr(self, 'template') else 100
        
        # [FIX] Only show if health is less than max AND timer is active
        if self.health < max_h and self.health_bar_timer > 0:
            bar_width = TILE_SIZE
            bar_height = 4
            
            # Position above head
            bar_x = self.rect.x + offset_x
            bar_y = self.rect.y + offset_y - 8 
            
            # Background (Red)
            pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))
            
            # Foreground (Green)
            health_ratio = max(0, self.health / max_h)
            current_width = int(bar_width * health_ratio)
            pygame.draw.rect(surface, (0, 255, 0), (bar_x, bar_y, current_width, bar_height))
        # ----------------------------------------

        # Draw equipped weapon 
        weapon = self.equipped_weapon
        if weapon and weapon.image:
            
            # Angle of the NPC's facing direction
            angle_rad = math.radians(self.angle)
            angle_deg = -self.angle # Pygame rotation is CCW

            # 2.1 Weapon is swinging (Melee Arch)
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

            # 2.2 Weapon is held statically (Ranged or Melee Idle/Aiming)
            else:
                # Use facing angle for static hold (which is the aiming direction when chasing)
                hand_offset_dist = TILE_SIZE * 0.4
                angle_rad = math.radians(self.angle)
                
                weapon_center_x = self.rect.centerx + math.cos(angle_rad) * hand_offset_dist
                weapon_center_y = self.rect.centery - math.sin(angle_rad) * hand_offset_dist
                angle_deg = -self.angle


            # Draw the rotated weapon
            rotated_image = pygame.transform.rotate(weapon.image, angle_deg)
            new_rect = rotated_image.get_rect(center=(weapon_center_x + offset_x, weapon_center_y + offset_y))
            surface.blit(rotated_image, new_rect.topleft)

    def take_damage(self, damage, game, attacker=None):
        """
        Apply damage. If attacker is player, become hostile.
        Returns True if dead, False otherwise.
        """
        if self.is_dead: return True
        
        self.health -= damage

        self.health_bar_timer = 180
        
        # Fight back logic
        if attacker == game.player:
            self.is_friendly = False
            self.state = 'chasing'
            # The Zombie AI will automatically target game.player if state is chasing
        
        if self.health <= 0:
            self.die(game)
            return True
            
        return False