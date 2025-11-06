import os
import random
import math
import pygame
import xml.etree.ElementTree as ET
import uuid
from faker import Faker
from data.config import *
from core.messages import display_message

fake = Faker()
ZOMBIE_TEMPLATES = []
ZOMBIE_CLOTHES_POOL = {}
ALL_ITEM_TEMPLATES = []

class Zombie:
    def __init__(self, x, y, template):
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
        self.speed = template.get('speed', ZOMBIE_SPEED)
        self.loot_table = template.get('loot', [])
        self.xp_value = random.uniform(template.get('min_xp'), template.get('max_xp'))
        self.image = self.load_sprite(template.get('sprite'))
        self.clothes = template.get('clothes', {})
        self.color = RED
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.show_health_bar_timer = 0
        self.last_attack_time = 0
        self.attack_range = TILE_SIZE * 1.5
        self.min_attack = template.get('min_attack')
        self.max_attack = template.get('max_attack')
        self.min_infection = template.get('min_infection')
        self.max_infection = template.get('max_infection')
        self.melee_swing_timer = 0
        self.melee_swing_angle = 0

        self.state = 'wandering'  # Can be 'wandering' or 'chasing'
        self.wander_target = None # (x, y) coordinate
        self.last_wander_change = 0 # Timestamp for changing wander direction

    def load_sprite(self, sprite_file):
        if not sprite_file: return None
        try:
            path = SPRITE_PATH + "zombie/" + sprite_file
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
        except Exception as e:
            print(f"Error loading zombie sprite {sprite_file}: {e}")
            return None

    def take_damage(self, amount):
        self.health -= amount
        self.health = max(0, self.health)
        self.show_health_bar_timer = 120 # Show health bar for 2 seconds (60fps)
        return self.health <= 0 # Return True if dead

    def draw(self, surface, offset_x, offset_y, opacity=255):
        # This draw method is for the pixelated zoom approach
        draw_rect = self.rect.move(offset_x, offset_y)

        if self.image:
            temp_image = self.image.copy()
            temp_image.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(temp_image, draw_rect)

            # Draw clothes
            for slot, clothe in self.clothes.items():
                if clothe:
                    clothe_sprite = self.load_clothe_sprite(clothe.get('sprite'))
                    if clothe_sprite:
                        clothe_sprite.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
                        surface.blit(clothe_sprite, draw_rect)
        else:
            # Fallback for zombies without an image
            temp_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            temp_surface.fill((self.color[0], self.color[1], self.color[2], opacity))
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
            swing_radius = TILE_SIZE * 0.8
            center_x, center_y = draw_rect.center
            start_angle = self.melee_swing_angle - (3.1415 / 4)
            end_angle = self.melee_swing_angle + (3.1415 / 4)
            arc_bounds = pygame.Rect(center_x - swing_radius, center_y - swing_radius, swing_radius * 2, swing_radius * 2)
            pygame.draw.arc(surface, RED, arc_bounds, start_angle, end_angle, 3)
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
        if not ZOMBIE_LINE_OF_SIGHT_CHECK:
            return True # Skip check if disabled in config

        start_pos = self.rect.center
        end_pos = target_rect.center

        # Simple line segment-rectangle intersection check using pygame's clipline
        # clipline returns the clipped points if it intersects, or empty tuple if not
        for obs in obstacles:
            if obs.clipline(start_pos, end_pos):
                return False # Line of sight is blocked

        return True # Line of sight is clear

    def update_ai(self, player_rect, obstacles, other_zombies):
        """Main AI logic: decide state (wander/chase) and target."""
        current_time = pygame.time.get_ticks()
        dist_to_player = math.hypot(player_rect.centerx - self.rect.centerx,
                                    player_rect.centery - self.rect.centery)

        can_see_player = self.has_line_of_sight(player_rect, obstacles)
        target_pos = None # Reset target each frame

        # Decide state: Chasing or Wandering
        if dist_to_player < ZOMBIE_DETECTION_RADIUS and can_see_player:
            self.state = 'chasing'
            target_pos = player_rect.center # Chase the player directly
        else:
            self.state = 'wandering'

            # Update wander target if needed
            if ZOMBIE_WANDER_ENABLED:
                # If interval passed, no target exists, or target was reached
                target_reached = self.wander_target and math.hypot(self.wander_target[0] - self.rect.centerx, self.wander_target[1] - self.rect.centery) < TILE_SIZE
                if (current_time - self.last_wander_change > ZOMBIE_WANDER_CHANGE_INTERVAL) or \
                   (self.wander_target is None) or target_reached:

                    # Pick a new random point within ~5 tiles
                    wander_radius = 5 * TILE_SIZE
                    new_target_x = self.rect.centerx + random.randint(-wander_radius, wander_radius)
                    new_target_y = self.rect.centery + random.randint(-wander_radius, wander_radius)

                    self.wander_target = (new_target_x, new_target_y)
                    self.last_wander_change = current_time

                target_pos = self.wander_target # Wander towards the target point
            else:
                target_pos = None # Wandering disabled, stand still

        # If we have a valid target (player or wander point), move towards it
        if target_pos:
            self.move_towards(target_pos, obstacles, other_zombies)
        else:
            # No target, do nothing (or add idle animation later)
            pass

    def move_towards(self, target_pos, obstacles, other_zombies):
        """Calculates movement vector towards a target_pos and handles collisions."""
        dx = target_pos[0] - self.rect.centerx
        dy = target_pos[1] - self.rect.centery
        dist = math.hypot(dx, dy)

        stop_distance = TILE_SIZE / 2 # Default stop distance for wandering
        if self.state == 'chasing':
            # If chasing, stop when within attack range
            stop_distance = self.attack_range * 0.9 # Use 90% of range to avoid jitter

        if dist > stop_distance: # Don't move if already very close
            # Normalize and scale by speed
            move_x = (dx / dist) * self.speed
            move_y = (dy / dist) * self.speed
        else:
            move_x, move_y = 0, 0

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

        # Update final position based on potential collision adjustments
        self.rect.topleft = (int(self.x), int(self.y))

    def attack(self, player, game):
        self.melee_swing_timer = 10
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        self.melee_swing_angle = math.atan2(-dy, dx)
        damage = random.randint(self.min_attack, self.max_attack)
        infection = random.randint(self.min_infection, self.max_infection)
        player.take_durability_damage(damage, game)

        total_defence = player.get_total_defence() # Get defence from player
        
        final_damage = damage
        final_infection = infection

        if total_defence > 0:
            # Defence reduces damage by its percentage
            damage_reduction = 1.0 - (total_defence / 100.0)
            # Defence reduces infection by half its percentage
            infection_reduction = 1.0 - ((total_defence / 2.0) / 100.0) 

            final_damage = max(0, damage * damage_reduction) # Ensure damage doesn't go negative
            final_infection = max(0, infection * infection_reduction) # Ensure infection doesn't go negative

        player.health -= damage
        player.health = max(0, player.health)
        if infection > 0:
            player.infection = min(100, player.infection + infection)
            display_message(game, f"**HIT!** Player takes {damage} damage and {infection}% infection.")
        else:
            display_message(game, f"**HIT!** Player takes {damage} damage.")


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

                            template['sprite'] = visuals_node.find('sprite').get('file') if visuals_node and visuals_node.find('sprite') is not None else None

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



                            ZOMBIE_TEMPLATES.append(template)
                            print(f"Loaded zombie template: {template['name']}")
                    except Exception as e:
                        print(f"Error loading zombie template from {filename}: {e}")
        except FileNotFoundError:
            print(f"Error: Zombie template folder not found: {folder}")


    @staticmethod
    def create_random(x, y):
        """Creates a zombie instance from a random template."""
        if not ZOMBIE_TEMPLATES or not ALL_ITEM_TEMPLATES: # <-- Check both lists
            Zombie.load_templates()
        if not ZOMBIE_TEMPLATES:
            Zombie.load_templates() # Load templates if not already loaded
        if not ZOMBIE_TEMPLATES:
            # Fallback if loading failed or no templates exist
            print("Error: No zombie templates loaded. Creating default zombie.")
            default_template = {
                'name':'Jogn Doe',
                'health':10,
                'speed':ZOMBIE_SPEED, 
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
        #print(f"Zombie '{zombie.name}' spawned. Loot: {[item['item'] for item in zombie.loot_table]}")
        #print(f"Zombie: '{zombie.name}' spawned with clothes: {list(zombie.clothes.keys())}")
        
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
