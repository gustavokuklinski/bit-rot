import os
import random
import math
import pygame
import time
import xml.etree.ElementTree as ET
import uuid
from faker import Faker
from core.data.config import *
import core.data.config
from core.messages import display_message
import random
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse # Ensure Corpse is imported

fake = Faker()
ZOMBIE_TEMPLATES = []
ZOMBIE_CLOTHES_POOL = {}
ALL_ITEM_TEMPLATES = []

# 1. Inherit from pygame.sprite.Sprite
class Zombie(pygame.sprite.Sprite):
    def __init__(self, x, y, template):
        # 2. Initialize the parent Sprite class
        super().__init__()
        
        self.x = x
        self.y = y
        self.id = str(uuid.uuid4())

        # 1. Generate Sex (must be first, as Name depends on it)
        sex_val = template.get('sex', 'Male') # Get value from XML
        if sex_val.upper() == 'RANDOM':
            self.sex = random.choice(['Male', 'Female'])
        else:
            self.sex = sex_val

        # 2. Generate Name
        name_val = template.get('name', 'Zombie') # Get value from XML
        if name_val.upper() == 'RANDOM':
            # Use Faker to get a name matching the generated sex
            if self.sex == 'Male':
                self.name = fake.name_male()
            else:
                self.name = fake.name_female()
        else:
            self.name = name_val # Use the hard-coded name (e.g., "John Doe")

        # 3. Generate Profession
        prof_val = template.get('profession', 'Civilian') # Get value from XML
        if prof_val.upper() == 'RANDOM':
            self.profession = fake.job()
        else:
            self.profession = prof_val

        # 4. Generate Vaccine Status
        vacc_val = template.get('vaccine', 'False') # Get value from XML
        if vacc_val.upper() == 'RANDOM':
            self.vaccine = random.choice([True, False])
        else:
            # Convert the string "True" or "False" to a real boolean
            self.vaccine = vacc_val.lower() == 'true'


        self.max_health = template.get('health')
        self.health = self.max_health
        self.speed = template.get('speed', core.data.config.ZOMBIE_SPEED)
        self.loot_table = template.get('loot', [])
        self.xp_value = random.uniform(template.get('min_xp'), template.get('max_xp'))

        self.images = {} # Use a dict to store multiple sprites
        sprites_data = template.get('sprites', {}) # e.g., {'center': 'zombie.png', ...}
        
        if sprites_data:
            # Load all sprites defined in the new XML structure
            for sprite_id, sprite_file in sprites_data.items():
                img = self.load_sprite(sprite_file)
                if img:
                    self.images[sprite_id] = img
        else:
            # Fallback for old templates that might still use the single 'sprite' key
            old_sprite_file = template.get('sprite')
            fallback_image = self.load_sprite(old_sprite_file)
            if fallback_image:
                self.images['center'] = fallback_image
                self.images['left'] = fallback_image
                self.images['right'] = fallback_image

        # Set a default image (self.image is no longer the main one, but good to have)
        self.image = self.images.get('center')

        self.clothes = template.get('clothes', {})
        self.color = RED
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.show_health_bar_timer = 0
        self.last_attack_time = 0
        self.attack_range = TILE_SIZE * 1
        self.min_attack = template.get('min_attack')
        self.max_attack = template.get('max_attack')
        self.min_infection = template.get('min_infection')
        self.max_infection = template.get('max_infection')
        self.melee_swing_timer = 0
        self.melee_swing_angle = 0

        self.walk_anim_angle = 0

        self.last_hit_sound_time = 0
        self.hit_sound_cooldown = 300 # 300ms cooldown for hit sound
        self.last_wander_sound_time = 0
        self.wander_sound_cooldown = random.randint(4000, 12000) # 4-12 sec
        
        self.is_ambiently_noisy = random.random() < 0.4 # 60% of zombies noisy

        # Load sound filenames from template
        sounds = template.get('sounds', {})
        self.sound_hit = sounds.get('hit', None)
        self.sound_wander = sounds.get('wander', None)
        self.sound_dead = sounds.get('dead', None)
        self.sound_attack = sounds.get('attack', None)
        self.sound_steps = sounds.get('steps', None) 
        self.last_step_sound_time = 0

        self.vx = 0 # Track velocity for drawing
        self.vy = 0 # Track velocity for drawing

        self.state = 'wandering'  # Can be 'wandering' or 'chasing'
        self.wander_target = None # (x, y) coordinate
        self.last_wander_change = 0 # Timestamp for changing wander direction

        # [NEW] Pathfinding stuck logic
        self.stuck_timer = 0
        self.stuck_angle = 0

        self.inventory = []
        try:
            # Attempt to create the ID item (assumes an item with name="ID" exists in XML)
            id_item = Item.create_from_name("ID")
            if id_item:
                # Customize the ID card
                id_item.name = f"ID: {self.name}"
                
                # Build the description text
                info_text = f"Name: {self.name}\nSex: {self.sex}\nProfession: {self.profession}"
                if self.vaccine:
                    info_text += "\nVaccinated: Yes"
                else:
                    info_text += "\nVaccinated: No"
                
                id_item.text = info_text
                
                # Add to zombie's direct inventory
                self.inventory.append(id_item)
        except Exception as e:
            print(f"Warning: Could not generate ID for zombie: {e}")
            

    def load_sprite(self, sprite_file):
        """Robustly loads a sprite, checking multiple paths."""
        if not sprite_file: return None
        
        # Paths to check: 1. zombie/folder, 2. root sprite folder, 3. player folder (common for NPCs)
        candidates = [
            os.path.join(SPRITE_PATH, "zombie", sprite_file),
            os.path.join(SPRITE_PATH, sprite_file),
            os.path.join(SPRITE_PATH, "player", sprite_file)
        ]

        for path in candidates:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                except Exception as e:
                    print(f"Error loading sprite at {path}: {e}")
        
        print(f"Warning: Could not find sprite '{sprite_file}' in common paths.")
        return None

    def take_damage(self, amount, game, attacker=None): 
        self.health -= amount
        self.health = max(0, self.health)
        self.show_health_bar_timer = 120 # Show health bar for 2 seconds (60fps)

        current_time = pygame.time.get_ticks()
        if current_time - self.last_hit_sound_time > self.hit_sound_cooldown:
            if self.sound_hit: # Check if a sound is defined
                game.sound_manager.play_sound(self.sound_hit, subdir='zombie', game=game, source_pos=self.rect.center)
            self.last_hit_sound_time = current_time

        return self.health <= 0 # Return True if dead
    
    # [NEW] Standardized Die Method for Loot Generation
    def die(self, game):
        """Handles zombie death: plays sound, creates corpse, generates loot."""
        # 1. Play sound
        if self.sound_dead:
             game.sound_manager.play_sound(self.sound_dead, subdir='zombie', game=game, source_pos=self.rect.center)
        
        # 2. Create Corpse
        corpse = Corpse(
            name=f"Corpse of {self.name}",
            capacity=20, 
            image_path="zombie/dead.png", # Corpse class handles default if None
            pos=self.rect.center,
            decay_ms=300000 # 5 minutes decay
        )

        # 3. Add Fixed Inventory (like ID card)
        for item in self.inventory:
            corpse.inventory.append(item)

        # 4. Add Random Loot Table Items
        if self.loot_table:
            for loot_entry in self.loot_table:
                if random.random() * 100 < float(loot_entry.get('chance', 0)):
                    item_name = loot_entry.get('item')
                    new_item = Item.create_from_name(item_name)
                    if new_item:
                         corpse.inventory.append(new_item)

        # 5. Add Clothes
        #for slot, clothe in self.clothes.items():
        #    if clothe:
        #         item_name = clothe.get('name')
        #         if item_name and not item_name.startswith("Empty"):
        #             # Simple check to try and create the item version of the cloth
        #             cloth_item = Item.create_from_name(item_name)
        #             if cloth_item:
        #                 corpse.inventory.append(cloth_item)

        game.items_on_ground.append(corpse)
        
        # Remove self from game
        if self in game.zombies:
            game.zombies.remove(self)


    def draw(self, surface, offset_x, offset_y, opacity=255):
        # This draw method is for the pixelated zoom approach
        draw_rect = self.rect.move(offset_x, offset_y)

        current_image = None
        if self.vx < -0.1: # Moving left (using a small threshold)
            current_image = self.images.get('left')
        elif self.vx > 0.1: # Moving right
            current_image = self.images.get('right')
        
        # Default to 'center' if moving vertically or standing still
        if current_image is None:
            current_image = self.images.get('center')

        if current_image:
            temp_image = current_image.copy()
            temp_image.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
            if self.walk_anim_angle != 0:
                rotated_img = pygame.transform.rotate(temp_image, self.walk_anim_angle)
                rot_rect = rotated_img.get_rect(center=draw_rect.center)
                surface.blit(rotated_img, rot_rect)
            else:
                surface.blit(temp_image, draw_rect)

            # Draw clothes
            for slot, clothe in self.clothes.items():
                if clothe:
                    clothe_sprite = self.load_clothe_sprite(clothe.get('sprite'))
                    if clothe_sprite:
                        clothe_sprite.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
                        if self.walk_anim_angle != 0:
                            rotated_cloth = pygame.transform.rotate(clothe_sprite, self.walk_anim_angle)
                            rot_cloth_rect = rotated_cloth.get_rect(center=draw_rect.center)
                            surface.blit(rotated_cloth, rot_cloth_rect)
                        else:
                            surface.blit(clothe_sprite, draw_rect)
        else:
            # Fallback for zombies without an image
            temp_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            temp_surface.fill((self.color[0], self.color[1], self.color[2], opacity))

            if self.walk_anim_angle != 0:
                rotated_surf = pygame.transform.rotate(temp_surface, self.walk_anim_angle)
                rot_rect = rotated_surf.get_rect(center=draw_rect.center)
                surface.blit(rotated_surf, rot_rect)
            else:
                surface.blit(temp_surface, draw_rect)

        if self.show_health_bar_timer > 0:
            bar_y = draw_rect.top - 7
            bg_bar_rect = pygame.Rect(draw_rect.left, bar_y, TILE_SIZE, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)

            health_percentage = max(0, self.health / self.max_health)
            health_bar_width = int(health_percentage * TILE_SIZE)
            health_bar_rect = pygame.Rect(draw_rect.left, bar_y, health_bar_width, 5)
            pygame.draw.rect(surface, GREEN, health_bar_rect)

            self.show_health_bar_timer -= 1

        if self.melee_swing_timer > 0:
            swing_radius = TILE_SIZE * 0.9
            center_x, center_y = draw_rect.center
            start_angle = self.melee_swing_angle - (3.1415 / 4)
            end_angle = self.melee_swing_angle + (3.1415 / 4)
            arc_bounds = pygame.Rect(center_x - swing_radius, center_y - swing_radius, swing_radius * 2, swing_radius * 2)
            pygame.draw.arc(surface, RED, arc_bounds, start_angle, end_angle, 1)
            self.melee_swing_timer -= 1

    def load_clothe_sprite(self, sprite_file):
        if not sprite_file: return None
        try:
            path = SPRITE_PATH + "clothes/" + sprite_file
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
        except Exception as e:
            print(f"Error loading clothe sprite {sprite_file}: {e}")
            return None

    def has_line_of_sight(self, target_rect, obstacles):
        """Checks if there is an uninterrupted line between zombie and target."""
        if not core.data.config.ZOMBIE_LINE_OF_SIGHT_CHECK:
            return True # Skip check if disabled in config

        start_pos = self.rect.center
        end_pos = target_rect.center

        # Simple line segment-rectangle intersection check using pygame's clipline
        # clipline returns the clipped points if it intersects, or empty tuple if not
        for obs in obstacles:
            if obs.clipline(start_pos, end_pos):
                return False # Line of sight is blocked

        return True # Line of sight is clear

    def update_ai(self, player_rect, obstacles, other_zombies, game):
        """Main AI logic: decide state (wander/chase) and target."""
        current_time = pygame.time.get_ticks()

        target_rect = player_rect
        target_entity = game.player  # Default target
        
        dist_to_player = math.hypot(player_rect.centerx - self.rect.centerx,
                                    player_rect.centery - self.rect.centery)

        nearest_npc = None
        min_npc_dist = 9999
        
        # Access NPCs from game instance
        if hasattr(game, 'npcs'):
            for npc in game.npcs:
                # [FIX] Skip targeting NPCs that are already dead (issue #1)
                if npc.is_dead:
                    continue

                d = math.hypot(npc.rect.centerx - self.rect.centerx, npc.rect.centery - self.rect.centery)
                if d < min_npc_dist:
                    min_npc_dist = d
                    nearest_npc = npc
        
        # Switch target to NPC if it is closer than player
        if nearest_npc and (min_npc_dist < dist_to_player):
            target_rect = nearest_npc.rect
            target_entity = nearest_npc # Set specific entity target
            dist_to_target = min_npc_dist
        else:
            dist_to_target = dist_to_player

        can_see_target = self.has_line_of_sight(target_rect, obstacles)
        target_pos = None

        # Decide state: Chasing or Wandering
        if dist_to_target < core.data.config.ZOMBIE_DETECTION_RADIUS and can_see_target:
            self.state = 'chasing'
            target_pos = target_rect.center 
            
            # Check attack range
            if dist_to_target < self.attack_range:
                if current_time - self.last_attack_time > 1000: # 1 sec attack speed
                    self.attack(target_entity, game) # Attack the specific entity
                    self.last_attack_time = current_time

        else:
            self.state = 'wandering'
            
            if self.is_ambiently_noisy and core.data.config.ZOMBIE_WANDER_ENABLED and self.sound_wander:
                if current_time - self.last_wander_sound_time > self.wander_sound_cooldown:
                    game.sound_manager.play_sound(
                        self.sound_wander, 
                        subdir='zombie', 
                        game=game, 
                        source_pos=self.rect.center, 
                        base_volume=random.uniform(0.05, 0.08)
                    )
                    self.last_wander_sound_time = current_time
                    self.wander_sound_cooldown = random.randint(4000, 12000)

            if core.data.config.ZOMBIE_WANDER_ENABLED:
                target_reached = self.wander_target and math.hypot(self.wander_target[0] - self.rect.centerx, self.wander_target[1] - self.rect.centery) < TILE_SIZE
                if (current_time - self.last_wander_change > core.data.config.ZOMBIE_WANDER_CHANGE_INTERVAL) or \
                   (self.wander_target is None) or target_reached:

                    wander_radius = 5 * TILE_SIZE
                    new_target_x = self.rect.centerx + random.randint(-wander_radius, wander_radius)
                    new_target_y = self.rect.centery + random.randint(-wander_radius, wander_radius)

                    self.wander_target = (new_target_x, new_target_y)
                    self.last_wander_change = current_time

                target_pos = self.wander_target 
            else:
                target_pos = None

        if target_pos:
            self.move_towards(target_pos, obstacles, other_zombies, game)

    def move_towards(self, target_pos, obstacles, other_zombies, game):
        """Calculates movement vector towards a target_pos and handles collisions."""
        # [NEW] Check stuck timer
        if self.stuck_timer > 0:
            self.stuck_timer -= 1
            # Move in random stuck angle
            rad = math.radians(self.stuck_angle)
            move_x = math.cos(rad) * self.speed
            move_y = -math.sin(rad) * self.speed
        else:
            # Normal movement
            dx = target_pos[0] - self.rect.centerx
            dy = target_pos[1] - self.rect.centery
            dist = math.hypot(dx, dy)

            stop_distance = TILE_SIZE / 2 
            if self.state == 'chasing':
                stop_distance = self.attack_range * 1

            if dist > stop_distance:
                move_x = (dx / dist) * self.speed
                move_y = (dy / dist) * self.speed
            else:
                move_x, move_y = 0, 0
        
        self.vx = move_x 
        self.vy = move_y 
        
        is_moving = move_x != 0 or move_y != 0

        if is_moving:
            self.walk_anim_angle = math.sin(time.time() * 15) * 2
        else:
            self.walk_anim_angle = 0

        if is_moving and self.is_ambiently_noisy and self.sound_steps:
            current_time = pygame.time.get_ticks()
            if current_time > self.last_step_sound_time:
                game.sound_manager.play_sound(
                    self.sound_steps,
                    subdir='zombie', 
                    game=game,
                    source_pos=self.rect.center,
                    base_volume=random.uniform(0.02, 0.06)
                )

                if self.state == 'chasing':
                    next_delay = random.randint(280, 380)
                else:
                    next_delay = random.randint(420, 520)
                
                self.last_step_sound_time = current_time + next_delay

        # Collision Handling (separated X and Y checks)
        old_x, old_y = self.x, self.y

        # Move X
        self.x += move_x
        self.rect.x = int(self.x)
        collided_x = False
        for obs in obstacles:
            if self.rect.colliderect(obs): collided_x = True; break
        if not collided_x:
            for z in other_zombies:
                if z is not self and self.rect.colliderect(z.rect): collided_x = True; break

        if collided_x:
            self.x = old_x
            self.rect.x = int(self.x)
            # [NEW] Trigger Stuck Logic
            if self.state == 'chasing':
                self.stuck_timer = 20 # 20 frames of avoidance
                self.stuck_angle = random.randint(0, 360)

        # Move Y
        self.y += move_y
        self.rect.y = int(self.y)
        collided_y = False
        for obs in obstacles:
            if self.rect.colliderect(obs): collided_y = True; break
        if not collided_y:
            for z in other_zombies:
                 if z is not self and self.rect.colliderect(z.rect): collided_y = True; break

        if collided_y:
            self.y = old_y
            self.rect.y = int(self.y)
            # [NEW] Trigger Stuck Logic
            if self.state == 'chasing':
                self.stuck_timer = 20
                self.stuck_angle = random.randint(0, 360)

        self.rect.topleft = (int(self.x), int(self.y))

    def attack(self, target_entity, game):
        self.melee_swing_timer = 10
        dx = target_entity.rect.centerx - self.rect.centerx
        dy = target_entity.rect.centery - self.rect.centery
        self.melee_swing_angle = math.atan2(-dy, dx)
        damage = random.randint(self.min_attack, self.max_attack)

        if hasattr(target_entity, 'take_durability_damage'):
            # It's a Player
            target_entity.take_durability_damage(damage, game)
            
            total_defence = target_entity.get_total_defence()
            damage_reduction = 1.0 - (total_defence / 100.0)
            
            infection = 0
            if random.random() < core.data.config.ZOMBIE_INFECTION_CHANCE:
                infection = random.randint(self.min_infection, self.max_infection)
            
            infection_reduction = 1.0 - ((total_defence / 2.0) / 100.0)
            final_damage = max(0, damage * damage_reduction)
            final_infection = max(0, infection * infection_reduction)

            final_damage_taken, final_infection_taken = target_entity.take_damage(game, final_damage, final_infection)
            
            if final_infection_taken > 0:
                 display_message(f"**HIT!** Player takes {final_damage_taken:.1f} damage and {final_infection_taken:.1f}% infection.")
            else:
                 display_message(f"**HIT!** Player takes {final_damage_taken:.1f} damage.")

        # Handle NPC specific damage logic (NPC inherits Zombie)
        else:
            # It's an NPC (Zombie class logic)
            is_dead = target_entity.take_damage(damage, game) 
            if is_dead and target_entity in game.npcs:
                # [MODIFIED] Use the new die method instead of just removing
                target_entity.die(game)
                display_message("A survivor has been killed by a zombie.")

        if self.sound_attack:
            game.sound_manager.play_sound(self.sound_attack, subdir='zombie', game=game, source_pos=self.rect.center)


        

    @staticmethod
    def load_templates(folder=DATA_PATH + 'zombie/'):
        """Loads all zombie templates from XML files in a folder."""
        global ZOMBIE_TEMPLATES, ZOMBIE_CLOTHES_POOL, ALL_ITEM_TEMPLATES
        ZOMBIE_TEMPLATES = []
        ZOMBIE_CLOTHES_POOL.clear()
        ALL_ITEM_TEMPLATES.clear()

        try:
            # Load clothes data first
            clothes_data = {}
            clothes_folder = DATA_PATH + 'clothes/'
            for filename in os.listdir(clothes_folder):
                if filename.endswith('.xml'):
                    filepath = os.path.join(clothes_folder, filename)
                    try:
                        tree = ET.parse(filepath)
                        root = tree.getroot()
                        if root.tag == 'cloth':

                            clothe_type = root.get('id') # e.g., "head", "torso", "legs"
                            if not clothe_type:
                                print(f"Warning: Clothe {filename} has no 'type' attribute, skipping.")
                                continue

                            if clothe_type not in ZOMBIE_CLOTHES_POOL:
                                ZOMBIE_CLOTHES_POOL[clothe_type] = [] # e.g., ZOMBIE_CLOTHES_POOL['head'] = []

                            properties = root.find('properties')
                            if properties is None: continue

                            # Build a dictionary of this clothe's properties
                            clothe_props = {
                                'name': root.get('name'),
                                'type': clothe_type,
                                'defence': 0.0, # Default
                                'speed': 0.0, # Default
                                'sprite': None # Default
                            }
                            
                            def_node = properties.find('defence')
                            if def_node is not None:
                                clothe_props['defence'] = float(def_node.get('value', 0))
                                
                            spd_node = properties.find('speed')
                            if spd_node is not None:
                                clothe_props['speed'] = float(spd_node.get('value', 0))
                                
                            spr_node = properties.find('sprite')
                            if spr_node is not None:
                                clothe_props['sprite'] = spr_node.get('file')

                            # Add this item to the global pool, sorted by its type
                            ZOMBIE_CLOTHES_POOL[clothe_type].append(clothe_props)
                    except Exception as e:
                        print(f"Error loading clothe from {filename}: {e}")

            items_folder = DATA_PATH + 'items/'
            if os.path.exists(items_folder):
                for filename in os.listdir(items_folder):
                    if filename.endswith('.xml'):
                        try:
                            item_path = os.path.join(items_folder, filename)
                            tree = ET.parse(item_path)
                            root = tree.getroot()
                            if root.tag == 'item':
                                item_name = root.get('name')
                                if item_name:
                                    ALL_ITEM_TEMPLATES.append(item_name)
                        except Exception as e:
                            print(f"Error parsing item XML {filename}: {e}")
                print(f"Loaded {len(ALL_ITEM_TEMPLATES)} item names for random loot.")
            else:
                print(f"Warning: Item folder not found at {items_folder}")
            
            
            
            for filename in os.listdir(folder):
                if filename.endswith('.xml'):
                    filepath = os.path.join(folder, filename)
                    try:
                        tree = ET.parse(filepath)
                        root = tree.getroot()
                        if root.tag == 'zombie':
                            template = {}
                            name_node = root.find('name')
                            stats_node = root.find('stats')
                            visuals_node = root.find('visuals')
                            xp_node = root.find('xp')
                            loot_node = root.find('loot')
                            clothes_node = root.find('clothes')
                            sound_node = root.find('sound')
                            template['name'] = name_node.get('value') if name_node is not None else 'Unknown Zombie'

                            health_node = stats_node.find('health')
                            template['min_health'] = int(health_node.get('min'))
                            template['max_health'] = int(health_node.get('max'))

                            speed_node = stats_node.find('speed')
                            template['min_speed'] = int(speed_node.get('min'))
                            template['max_speed'] = int(speed_node.get('max'))

                            attack_node = stats_node.find('attack')
                            template['min_attack'] = int(attack_node.get('min'))
                            template['max_attack'] = int(attack_node.get('max'))

                            infection_node = stats_node.find('infection')
                            template['min_infection'] = int(infection_node.get('min'))
                            template['max_infection'] = int(infection_node.get('max'))

                            template['sprites'] = {} # Use a dict to store multiple sprites
                            if visuals_node is not None:
                                # Find all <sprite> tags
                                for sprite_node in visuals_node.findall('sprite'):
                                    sprite_id = sprite_node.get('id') # e.g., "center", "left"
                                    sprite_file = sprite_node.get('file') # e.g., "zombie.png"
                                    if sprite_id and sprite_file:
                                        template['sprites'][sprite_id] = sprite_file

                            template['min_xp'] = float(xp_node.get('min'))
                            template['max_xp'] = float(xp_node.get('max'))

                            template['loot'] = []
                            if loot_node is not None:
                                for item_node in loot_node.findall('item'):
                                    template['loot'].append({
                                        'item': item_node.get('name'),
                                        'chance': float(item_node.get('chance'))
                                    })

                            # Instead of loading item lists, just get the tag names
                            template['clothes_slots'] = []
                            if clothes_node is not None:
                                for slot_node in clothes_node:
                                    # slot_node.tag will be "head", "torso", etc.
                                    template['clothes_slots'].append(slot_node.tag)


                            template['sounds'] = {}
                            if sound_node is not None:
                                hit_node = sound_node.find('hit')
                                if hit_node is not None:
                                    template['sounds']['hit'] = hit_node.get('src')
                                
                                wander_node = sound_node.find('wander')
                                if wander_node is not None:
                                    template['sounds']['wander'] = wander_node.get('src')
                                    
                                dead_node = sound_node.find('dead')
                                if dead_node is not None:
                                    template['sounds']['dead'] = dead_node.get('src')
                                    
                                attack_node = sound_node.find('attack')
                                if attack_node is not None:
                                    template['sounds']['attack'] = attack_node.get('src')

                                steps_node = sound_node.find('steps') # Find the <steps> tag
                                if steps_node is not None:
                                    template['sounds']['steps'] = steps_node.get('src')


                            ZOMBIE_TEMPLATES.append(template)
                            print(f"Loaded zombie template: {template['name']}")
                    except Exception as e:
                        print(f"Error loading zombie template from {filename}: {e}")
        except FileNotFoundError:
            print(f"Error: Zombie template folder not found: {folder}")


    @staticmethod
    def create_random(x, y):
        """Creates a zombie instance from a random template."""
        if not ZOMBIE_TEMPLATES:
            # Fallback if loading failed or no templates exist
            print("Error: No zombie templates loaded. Creating default zombie.")
            default_template = {
                'name':'Jogn Doe',
                'health':10,
                'speed':core.data.config.ZOMBIE_SPEED, 
                'loot':[], 
                'min_xp':1,
                'max_xp':5, 
                'min_attack':1, 
                'max_attack':3, 
                'min_infection':0, 
                'max_infection':1,
                'sex': 'Male', 
                'profession': 'Civilian', 
                'vaccine': 'False'
            }
            return Zombie(x, y, default_template)

        template = random.choice(ZOMBIE_TEMPLATES)
        zombie = Zombie(x, y, template)
        zombie.loot_table = list(template.get('loot', []))

        num_random_items = random.randint(0, 2) # Add 0, 1, or 2 extra items
        if ALL_ITEM_TEMPLATES: # Make sure the list isn't empty
            for _ in range(num_random_items):
                item_name = random.choice(ALL_ITEM_TEMPLATES)
                # Add to the zombie's loot table with a random chance
                zombie.loot_table.append({
                    'item': item_name,
                    'chance': random.uniform(25.0, 75.0) # e.g., 25% to 75% chance
                })


        # Randomly assign clothes and calculate defense bonus
        total_defense = 0
        zombie.clothes = {} # Start with an empty clothes dict for this instance

        # Check if the template has the 'clothes_slots' list (from <head></head>, etc.)
        if 'clothes_slots' in template:
            
            # Iterate through each slot defined in the XML (e.g., 'head', 'torso', ...)
            for slot_name in template['clothes_slots']:
                
                # Find the list of available clothes for this specific slot
                # e.g., ZOMBIE_CLOTHES_POOL['head']
                available_clothes_for_slot = ZOMBIE_CLOTHES_POOL.get(slot_name)
                
                # Check if we have any clothes for that slot
                if available_clothes_for_slot:
                    # Pick one random piece of clothing from the list
                    chosen_clothe = random.choice(available_clothes_for_slot)
                    
                    # Assign it to the zombie instance
                    zombie.clothes[slot_name] = chosen_clothe
                    
                    # Add its defense value
                    total_defense += chosen_clothe.get('defence', 0)
            
        for slot_name, clothe_dict in zombie.clothes.items():
            if clothe_dict:
                item_name = clothe_dict.get('name')
                if item_name and not item_name.startswith("Empty"):
                    # Add the *specific* item this zombie is wearing to loot
                    zombie.loot_table.append({
                        'item': item_name,
                        'chance': 100.0 # Always drops the clothes it's wearing
                    })
        
        # Apply defense multiplier to health
        defense_multiplier = 1 + (total_defense / 100.0)
        zombie.max_health = random.randint(template['min_health'], template['max_health']) * defense_multiplier
        zombie.health = zombie.max_health

        # Set other stats
        zombie.speed = random.randint(template['min_speed'], template['max_speed'])

        return zombie

# Load templates when the module is imported (ensure it only happens once)
if not ZOMBIE_TEMPLATES:
    Zombie.load_templates()