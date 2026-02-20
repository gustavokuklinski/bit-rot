import os
import random
import math
import pygame
import uuid
from faker import Faker
import core.data.config
from core.data.config import TILE_SIZE, RED
from core.entities.item.item import Item

# Mixins
from core.entities.zombie.zombie_data import ZombieData
from core.entities.zombie.zombie_graphics import ZombieGraphics
from core.entities.zombie.zombie_ai import ZombieAI
from core.entities.zombie.zombie_combat import ZombieCombat

fake = Faker()

# 1. Inherit from pygame.sprite.Sprite and Mixins
class Zombie(ZombieData, ZombieGraphics, ZombieAI, ZombieCombat, pygame.sprite.Sprite):
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
        self.sprites_data = template.get('sprites', {}) # e.g., {'center': 'zombie.png', ...}
        
        if self.sprites_data:
            # Load all sprites defined in the new XML structure
            for sprite_id, sprite_file in self.sprites_data.items():
                img = self.load_sprite(sprite_file)
                if img:
                    self.images[sprite_id] = img
        else:
            # Fallback for old templates that might still use the single 'sprite' key
            old_sprite_file = template.get('sprite')
            if old_sprite_file:
                self.sprites_data = {'center': old_sprite_file, 'left': old_sprite_file, 'right': old_sprite_file}
            fallback_image = self.load_sprite(old_sprite_file)
            if fallback_image:
                self.images['center'] = fallback_image
                self.images['left'] = fallback_image
                self.images['right'] = fallback_image

        # Set a default image (self.image is no longer the main one, but good to have)
        self.image = self.images.get('center')
        # [NEW] Create collision mask from the zombie's image
        if self.image:
            self.mask = pygame.mask.from_surface(self.image)
        else:
            self.mask = None

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
        self.is_dead = False
        self.wander_target = None # (x, y) coordinate
        self.last_wander_change = 0 # Timestamp for changing wander direction

        # [NEW] Pathfinding stuck logic
        self.stuck_timer = 0
        self.stuck_angle = 0
        
        # [NEW] Knockback variables
        self.knockback_velocity = [0, 0]
        self.knockback_timer = 0

        self.inventory = []
        try:
            # Attempt to create the ID item (assumes an item with name="ID" exists in XML)
            id_item = Item.create_from_name("ID")
            if id_item:
                # Customize the ID card
                id_item.name = f"ID: {self.name}"
                
                # Build the description text
                info_text = f"Name: {self.name}\nSex: {self.sex}\n"
                if self.vaccine:
                    info_text += "\nVaccinated: Yes"
                else:
                    info_text += "\nVaccinated: No"
                
                id_item.text = info_text
                
                # Add to zombie's direct inventory
                self.inventory.append(id_item)
        except Exception as e:
            print(f"Warning: Could not generate ID for zombie: {e}")

    def update(self, game):
        """
        Update logic for Zombie. Handles knockback if active, otherwise delegates
        to the standard ZombieAI update loop via super().
        """
        # --- KNOCKBACK HANDLING ---
        if self.knockback_timer > 0:
            obstacles = game.obstacles
            multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
            
            kb_x, kb_y = self.knockback_velocity
            
            # Move X with collision
            self.x += kb_x
            self.rect.x = int(self.x)
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    self.x -= kb_x
                    self.rect.x = int(self.x)
                    break
            
            # Move Y with collision
            self.y += kb_y
            self.rect.y = int(self.y)
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    self.y -= kb_y
                    self.rect.y = int(self.y)
                    break
            
            # Decay
            dt = 16 * multiplier 
            self.knockback_timer -= dt
            self.knockback_velocity[0] *= 0.9
            self.knockback_velocity[1] *= 0.9
            return

        # If not knocked back, perform standard AI/Update
        super().update(game)

    @staticmethod
    def create_random(x, y):
        """Creates a zombie instance from a random template."""
        if not ZombieData.ZOMBIE_TEMPLATES:
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
                'vaccine': 'False'
            }
            return Zombie(x, y, default_template)

        template = random.choice(ZombieData.ZOMBIE_TEMPLATES)
        zombie = Zombie(x, y, template)
        zombie.loot_table = list(template.get('loot', []))

        num_random_items = random.randint(0, 2) # Add 0, 1, or 2 extra items
        if ZombieData.ALL_ITEM_TEMPLATES: # Make sure the list isn't empty
            for _ in range(num_random_items):
                item_name = random.choice(ZombieData.ALL_ITEM_TEMPLATES)
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
                available_clothes_for_slot = ZombieData.ZOMBIE_CLOTHES_POOL.get(slot_name)
                
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
        zombie.speed = random.uniform(template['min_speed'], template['max_speed'])

        return zombie

# Load templates when the module is imported (ensure it only happens once)
if not ZombieData.ZOMBIE_TEMPLATES:
    ZombieData.load_templates()