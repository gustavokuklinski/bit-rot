# core/entities/animal/animal.py
import pygame
import random
import os
from core.entities.zombie.zombie import Zombie
from core.entities.animal.animal_loader import AnimalLoader

class Animal(Zombie):
    SPRITE_PATH = "game/lib/sprites/animals"

    def __init__(self, x, y, animal_type):
        if not AnimalLoader.definitions:
            AnimalLoader.load_animals()
            
        template = AnimalLoader.definitions.get(animal_type)
        if not template:
            print(f"Warning: Animal type '{animal_type}' not found. Spawning generic Rat.")
            template = AnimalLoader.definitions.get('Rat')

        # Convert Animal XML structure to Zombie template structure
        zombie_template = {
            'name': template['name'],
            'health': template['stats']['health']['max'], 
            'speed': template['stats']['speed']['max'],
            'min_attack': template['stats']['attack']['min'],
            'max_attack': template['stats']['attack']['max'],
            'min_infection': template['stats']['infection']['min'],
            'max_infection': template['stats']['infection']['max'],
            'loot': template['loot'],
            'min_xp': 1, 
            'max_xp': 3,
            'sex': 'Animal', 
            'vaccine': 'False',
            'sprites': {'center': template['sprite']} 
        }

        super().__init__(x, y, zombie_template)
        
        # [FIX] Clear inventory to prevent ID Cards or default Zombie items from appearing
        self.inventory = []
        
        self.type = "animal"
        
        # Apply specific stat randomization
        min_hp = template['stats']['health']['min']
        max_hp = template['stats']['health']['max']
        self.max_health = random.randint(min_hp, max_hp)
        self.health = self.max_health
        
        min_spd = template['stats']['speed']['min']
        max_spd = template['stats']['speed']['max']
        self.speed = random.uniform(min_spd, max_spd)

    def load_sprite(self, filename):
        """Overrides Zombie.load_sprite to use the specific animal sprite path."""
        full_path = os.path.join(self.SPRITE_PATH, filename)
        try:
            # We assume a global pygame display is initialized
            image = pygame.image.load(full_path).convert_alpha()
            return image
        except Exception as e:
            print(f"Error loading animal sprite {filename} at {full_path}: {e}")
            return None