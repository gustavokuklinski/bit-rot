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

CLOTHING_COLORS = [
    (255, 255, 255), (50, 50, 50), (220, 50, 50), (50, 200, 50), 
    (50, 50, 220), (220, 220, 50), (255, 105, 180), (255, 165, 0), 
    (139, 69, 19), (128, 128, 128)
]

class Zombie(ZombieData, ZombieGraphics, ZombieAI, ZombieCombat, pygame.sprite.Sprite):
    def __init__(self, x, y, template):
        super().__init__()
        
        self.x = x
        self.y = y
        self.id = str(uuid.uuid4())

        sex_val = template.get('sex', 'Male')
        if sex_val.upper() == 'RANDOM':
            self.sex = random.choice(['Male', 'Female'])
        else:
            self.sex = sex_val

        name_val = template.get('name', 'Zombie')
        if name_val.upper() == 'RANDOM':
            if self.sex == 'Male':
                self.name = fake.name_male()
            else:
                self.name = fake.name_female()
        else:
            self.name = name_val 

        self.max_health = template.get('health')
        self.health = self.max_health
        self.speed = template.get('speed', core.data.config.ZOMBIE_SPEED)
        
        # --- FIX: Prevent default XML loot tables from dropping duplicate white clothes ---
        self.loot_table = template.get('loot', [])
        self.loot_table = [loot for loot in self.loot_table if loot.get('item') not in ["Pants", "Jacket", "Tshirt", "TShirt", "Sneakers"]]

        self.xp_value = random.uniform(template.get('min_xp'), template.get('max_xp'))

        self.images = {} 
        self.sprites_data = template.get('sprites', {}) 
        
        if self.sprites_data:
            for sprite_id, sprite_file in self.sprites_data.items():
                img = self.load_sprite(sprite_file)
                if img:
                    self.images[sprite_id] = img
        else:
            old_sprite_file = template.get('sprite')
            if old_sprite_file:
                self.sprites_data = {'center': old_sprite_file, 'left': old_sprite_file, 'right': old_sprite_file}
            fallback_image = self.load_sprite(old_sprite_file)
            if fallback_image:
                self.images['center'] = fallback_image
                self.images['left'] = fallback_image
                self.images['right'] = fallback_image

        self.image = self.images.get('center')
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
        self.hit_sound_cooldown = 300 
        self.last_wander_sound_time = 0
        self.wander_sound_cooldown = random.randint(4000, 12000)

        self.is_ambiently_noisy = random.random() < 0.4 

        sounds = template.get('sounds', {})
        self.sound_hit = sounds.get('hit', None)
        self.sound_wander = sounds.get('wander', None)
        self.sound_dead = sounds.get('dead', None)
        self.sound_attack = sounds.get('attack', None)
        self.sound_steps = sounds.get('steps', None)
        self.last_step_sound_time = 0

        self.vx = 0 
        self.vy = 0 

        self.state = 'wandering' 
        self.is_dead = False
        self.wander_target = None 
        self.last_wander_change = 0 

        self.stuck_timer = 0
        self.stuck_angle = 0

        self.knockback_velocity = [0, 0]
        self.knockback_timer = 0

        self.aggro_timer = 0

        self.last_los_check_time = 0
        self.los_check_interval = 2000  
        self.cached_los_result = True
        self.last_trigger_check_time = 0
        self.trigger_check_interval = 1000  
        self.cached_trigger_result = False

        self.inventory = []
        try:
            id_name = f"ID: {self.name}"
            id_item = Item.create_from_name(id_name)
            if id_item:
                info_text = f"Name: {self.name}\nSex: {self.sex}\n"
                id_item.text = info_text
                self.inventory.append(id_item)
        except Exception as e:
            print(f"Warning: Could not generate ID for zombie: {e}")

    def update(self, game):
        if self.knockback_timer > 0:
            obstacles = game.obstacles
            multiplier = 1.0

            kb_x, kb_y = self.knockback_velocity

            self.x += kb_x
            self.rect.x = int(self.x)
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    self.x -= kb_x
                    self.rect.x = int(self.x)
                    break

            self.y += kb_y
            self.rect.y = int(self.y)
            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    self.y -= kb_y
                    self.rect.y = int(self.y)
                    break

            dt = game.dt_ms * multiplier
            self.knockback_timer -= dt

            decay_factor = math.pow(0.9, game.dt_mult * multiplier)
            self.knockback_velocity[0] *= decay_factor
            self.knockback_velocity[1] *= decay_factor
            return

        super().update(game)

    @staticmethod
    def create_random(x, y):
        if not ZombieData.ZOMBIE_TEMPLATES:
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
            }
            return Zombie(x, y, default_template)

        #type_weights = {
        #    'common': 55,
        #    'worker': 20,
        #    'doctor': 10,
        #    'military': 20,
        #    'special_force': 5
        #}
        template_weights = [t.get('spawn_weight', 10) for t in ZombieData.ZOMBIE_TEMPLATES]
        
        template = random.choices(ZombieData.ZOMBIE_TEMPLATES, weights=template_weights, k=1)[0]
        
        zombie = Zombie(x, y, template)
        
        # FIX: Filter standard loot table assignment to prevent white clothes duplicates
        base_loot = list(template.get('loot', []))
        
        zombie.loot_table = [loot for loot in base_loot if loot.get('item') not in ["Pants", "Jacket", "Tshirt", "TShirt", "Sneakers", "Bald", "Mowalk", "Cut", "Crew", "Long"]]

        num_random_items = random.randint(0, 2)
        if ZombieData.ALL_ITEM_TEMPLATES: 
            for _ in range(num_random_items):
                item_name = random.choice(ZombieData.ALL_ITEM_TEMPLATES)
                # Don't add default clothes randomly either
                if item_name not in ["Pants", "Tshirt", "TShirt", "Jacket", "Sneakers"] and not item_name.endswith(' on'):
                    zombie.loot_table.append({
                        'item': item_name,
                        'chance': random.uniform(25.0, 75.0) 
                    })

        zombie.clothes = {} 
        total_defense = 0

        # Enforce predefined clothes on Zombies and Pre-Tint them randomly
        # Enforce predefined clothes on Zombies and Pre-Tint them randomly
        hair_options = ['Bald', 'Mowalk', 'Cut', 'Crew', 'Long']
        predefined_clothes = template.get('predefined_clothes', {})
        selected_hair = predefined_clothes.get('hair', random.choice(hair_options))
        
        # Base fallback logic combined with XML predefined rules
        clothes_to_equip = {
            "feet": predefined_clothes.get("feet", "Sneakers" if random.random() < 0.8 else None), # 80% chance of Sneakers
            "legs": predefined_clothes.get("legs", "Pants" if random.random() < 0.9 else None),    # 90% chance of Pants
            "body": predefined_clothes.get("body", "Tshirt" if random.random() < 0.8 else None),   # 80% chance of Tshirt
            "arms": predefined_clothes.get("arms", "Jacket" if random.random() < 0.2 else None),   # 30% chance of Jacket
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

                # Only apply random tint to fallback/randomized clothing
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

                if actual_slot not in zombie.clothes:
                    zombie.clothes[actual_slot] = item
                    total_defense += getattr(item, 'defence', 0)
                    # --- FIX: Removed redundant zombie.loot_table.append(...) here ---
        
        defense_multiplier = 1 + (total_defense / 100.0)
        zombie.max_health = random.randint(template['min_health'], template['max_health']) * defense_multiplier
        zombie.health = zombie.max_health
        zombie.speed = random.uniform(template['min_speed'], template['max_speed'])

        return zombie

if not ZombieData.ZOMBIE_TEMPLATES:
    ZombieData.load_templates()