# core/entities/animal/animal.py
import pygame
import random
import os
import math
from core.entities.zombie.zombie import Zombie
from core.entities.animal.animal_loader import AnimalLoader
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Item

class Animal(Zombie):

    def __init__(self, x, y, animal_type, game=None, layer=None):
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
            'sounds': template.get('sounds', {}),
            'min_xp': 1, 
            'max_xp': 3,
            'sex': 'Animal', 
            'vaccine': 'False',
            'sprites': {'center': template['sprite']} 
        }

        super().__init__(x, y, zombie_template)
        self.attack_player = template.get('attack_player', False)

        sounds = template.get('sounds', {})
        self.sound_hit = sounds.get('hit')
        self.sound_dead = sounds.get('dead')
        self.sound_attack = sounds.get('attack')
        self.sound_steps = sounds.get('steps')

        # Track the layer this Animal belongs to
        if layer is not None:
            self.layer = layer
        elif game:
            self.layer = game.current_layer_index if hasattr(game, 'current_layer_index') else 1
        else:
            self.layer = 1

        # Clear inventory to prevent ID Cards or default Zombie items from appearing
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
        
        print(f"[ANIMAL] Created {self.name} at ({self.x}, {self.y}) with sprite: {self.image is not None}")

    def update(self, game):
        # Call the base class update first
        super().update(game)
        
        if self.is_dead:
            return
            
        # Check if the animal is currently moving
        is_moving = hasattr(self, 'dx') and hasattr(self, 'dy') and (self.dx != 0 or self.dy != 0)
        
        if is_moving and hasattr(self, 'sound_steps') and self.sound_steps:
            current_time = pygame.time.get_ticks()
            if not hasattr(self, 'last_step_sound_time'):
                self.last_step_sound_time = current_time + random.randint(0, 400)
            # Step speed (400ms is a good default trot, adjust if needed)
            if current_time - getattr(self, 'last_step_sound_time', 0) > 400:

                game.sound_manager.play_sound(
                    self.sound_steps, 
                    subdir='animals',  
                    game=game, 
                    source_pos=self.rect.center, 
                    base_volume=0.3
                )
                self.last_step_sound_time = current_time

    # [FIX] Explicitly prevent the AI update from running if the animal is dead
    def update_ai(self, player_rect, obstacles, other_zombies, game):
        if self.is_dead:
            return
        
        # --- CHANGED: Use the XML flag instead of hardcoded names ---
        if self.attack_player:
            # Attacks player and wanders normally
            super().update_ai(player_rect, obstacles, other_zombies, game)
            return

        current_time = pygame.time.get_ticks()
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
        
        threat_radius = 150 if self.name != "Cow" else 250 
        
        threat_detected = False
        flee_x, flee_y = 0, 0
        
        # 1. Check for player threat (Player is running or shooting)
        if game.player and not game.player.is_dead and not getattr(game.player, 'godzen_mode', False):
            dx = game.player.rect.centerx - self.rect.centerx
            dy = game.player.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            
            # Flee if player shoots (loud) or gets too close
            if getattr(game.player, 'gun_flash_timer', 0) > 0 and dist < threat_radius * 2:
                flee_x -= dx
                flee_y -= dy
                threat_detected = True
            elif dist < threat_radius and (getattr(game.player, 'is_running', False) or getattr(self, 'aggro_timer', 0) > 0):
                flee_x -= dx
                flee_y -= dy
                threat_detected = True

        # 2. Check for Zombie / Hostile NPC threats
        for entity in other_zombies + list(getattr(game, 'npcs', [])):
            if entity is self or entity.is_dead: continue
            
            # If it's an NPC, only flee if it's hostile. If it's a zombie, always flee.
            # if hasattr(entity, 'is_friendly') and entity.is_friendly: continue

            dx = entity.rect.centerx - self.rect.centerx
            dy = entity.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            
            if dist < threat_radius:
                flee_x -= dx
                flee_y -= dy
                threat_detected = True
                
        # 3. Movement Execution
        if threat_detected:
            self.state = 'fleeing'
            self.aggro_timer = 2000 # Keep running for 2 seconds after threat is gone
            
            # Normalize flee vector
            flee_dist = math.hypot(flee_x, flee_y)
            if flee_dist > 0:
                # Add a bit of randomness so they don't just run in a perfect straight line into a wall
                flee_x += random.uniform(-50, 50)
                flee_y += random.uniform(-50, 50)
                
                target_x = self.rect.centerx + flee_x
                target_y = self.rect.centery + flee_y
                self.move_towards((target_x, target_y), obstacles, other_zombies, game, can_see_target=True)
        else:
            if getattr(self, 'aggro_timer', 0) > 0:
                 self.aggro_timer -= game.dt_ms
            else:
                 # Standard wandering from Zombie base class
                 super().update_ai(player_rect, obstacles, other_zombies, game)

    # [FIX] Override take_damage for instant hit feedback
    def take_damage(self, amount, game, attacker=None):
        if self.is_dead:
            return False
            
        self.health -= amount
        self.show_health_bar_timer = 120
        
        # Play hit sound BEFORE checking death so the final blow feels punchy and instant
        current_time = pygame.time.get_ticks()
        if hasattr(self, 'sound_hit') and self.sound_hit and game and hasattr(game, 'sound_manager'):
            if current_time - getattr(self, 'last_hit_sound_time', 0) > getattr(self, 'hit_sound_cooldown', 300):
                game.sound_manager.play_sound(
                    self.sound_hit, 
                    subdir='animals', 
                    game=game, 
                    source_pos=self.rect.center, 
                    base_volume=1.0, 
                    pitch_variance=0.15
                ) # Natural sound variation!
                self.last_hit_sound_time = current_time
        
        # Instantly register as ready to die so the game calls die() without delay
        if self.health <= 0:
            self.health = 0
            self.state = 'dead' # Extra safety flag
            self.die(game)
            return True
            
        # Make the animal chase the attacker if hit but not killed
        if self.attack_player:
            self.aggro_timer = 10000
            self.state = 'chasing'
        else:
            self.aggro_timer = 2000
            self.state = 'fleeing'
                
        return False

    # [FIX] Custom animal die method without the lag-inducing grid rebuilds
    def die(self, game):
        if self.is_dead: return
        self.is_dead = True
        self.state = 'dead'
        
        # 1. Play animal death sound
        if getattr(self, 'sound_dead', None) and hasattr(game, 'sound_manager'):
            game.sound_manager.play_sound(
                self.sound_dead, 
                subdir='animals', 
                game=game, 
                source_pos=self.rect.center, 
                base_volume=1.0, 
                pitch_variance=0.15
            ) # Natural sound variation!

        # 2. Create Animal Corpse using the updated relative path
        corpse = Corpse(
            name=f"Dead {self.name}",
            capacity=10, 
            image_path="../animals/dead.png",  
            pos=self.rect.center,
            decay_ms=120000 
        )

        # 3. Add animal-specific loot
        if hasattr(self, 'loot_table') and self.loot_table:
            for loot_entry in self.loot_table:
                chance_val = float(loot_entry.get('chance', 0))
                if chance_val > 1.0: chance_val /= 100.0
                if random.random() <= chance_val:
                    item_name = loot_entry.get('item')
                    new_item = Item.create_from_name(item_name)
                    if new_item: corpse.inventory.append(new_item)

        # 4. Add corpse to map INSTANTLY
        game.items_on_ground.append(corpse)
        
        # Add a death burst effect to make the death visually pop and feel responsive
        if hasattr(game, 'splashes'):
            game.splashes.append({
                'pos': (self.rect.centerx, self.rect.bottom), 
                'time': pygame.time.get_ticks(),
                'duration': 250, 
                'radius': 5,    
                'type': 'death_burst'
            })

        # 5. Safely clean up from active memory to prevent ghost artifacts
        try: self.kill() # Instantly removes it from Pygame rendering groups if it exists in one
        except: pass
        
        if self in game.items_on_ground:
            try: game.items_on_ground.remove(self)
            except ValueError: pass
            
        if hasattr(game, 'active_animals') and self in game.active_animals:
            try: game.active_animals.remove(self)
            except ValueError: pass
            
        if self in game.zombies:
            try: game.zombies.remove(self)
            except ValueError: pass
            
        if hasattr(game, 'active_zombies') and self in game.active_zombies:
            try: game.active_zombies.remove(self)
            except ValueError: pass
            
        # Force position offscreen to prevent 1-frame ghost rendering 
        self.rect.x = -9999
        self.rect.y = -9999