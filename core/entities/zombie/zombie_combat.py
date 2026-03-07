import random
import math
import pygame
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Item
from core.messages import display_message
from core.data.config import ZOMBIE_INFECTION_CHANCE
import core.data.config

class ZombieCombat:
    def take_damage(self, amount, game, attacker=None): 
        self.health -= amount
        self.health = max(0, self.health)
        self.show_health_bar_timer = 120 # Show health bar for 2 seconds (60fps)

        current_time = pygame.time.get_ticks()
        if current_time - self.last_hit_sound_time > self.hit_sound_cooldown:
            if self.sound_hit: # Check if a sound is defined
                snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
                game.sound_manager.play_sound(self.sound_hit, subdir=snd_dir, game=game, source_pos=self.rect.center, base_volume=random.uniform(0.2, 0.7), pitch_variance=0.15)
            self.last_hit_sound_time = current_time

        return self.health <= 0 # Return True if dead

    def attack(self, target_entity, game):
        self.melee_swing_timer = 10
        dx = target_entity.rect.centerx - self.rect.centerx
        dy = target_entity.rect.centery - self.rect.centery
        self.melee_swing_angle = math.atan2(-dy, dx)
        damage = random.randint(self.min_attack, self.max_attack)

        if hasattr(target_entity, 'take_damage_to_part'):
            # It's a Player or Entity with complex health
            target_entity.take_durability_damage(damage, game)
            
            parts = ['head', 'feet', 'arms', 'body','hand','legs']
            # Optional: You can use weighted choice if you want legs to be hit less/more often
            # target_part = random.choices(parts, weights=[10, 30, 30, 30], k=1)[0]
            target_part = random.choice(parts)
            
            total_defence = target_entity.get_total_defence() # Or part-specific defence if calculated inside player
            damage_reduction = 1.0 - (total_defence / 100.0)
            
            infection = 0
            if random.random() < ZOMBIE_INFECTION_CHANCE:
                infection = random.uniform(self.min_infection, self.max_infection)
            
            infection_reduction = 1.0 - ((total_defence / 2.0) / 100.0)
            final_damage = max(0, damage * damage_reduction)
            final_infection = max(0, infection * infection_reduction)

            # Apply damage to the specific part
            target_entity.take_damage_to_part(target_part, final_damage)
            
            # Apply infection globally
            if final_infection > 0:
                target_entity.infection = min(100, target_entity.infection + final_infection)
            
            if final_infection > 0:
                 display_message(f"**HIT!** Zombie hit {target_part} for {final_damage:.1f} damage and infection!")
            else:
                 display_message(f"**HIT!** Zombie hit {target_part} for {final_damage:.1f} damage.")

        # Handle NPC specific damage logic (NPC inherits Zombie)
        else:
            is_dead = target_entity.take_damage(damage, game, attacker=self)
            if is_dead and target_entity in game.npcs:
                target_entity.die(game)
                display_message("A survivor has been killed by a zombie.")

        if self.sound_attack:
            snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
            game.sound_manager.play_sound(self.sound_attack, subdir=snd_dir, game=game, source_pos=self.rect.center, base_volume=random.uniform(0.2, 0.7), pitch_variance=0.15)

    def die(self, game):
        """Handles zombie death: plays sound, creates corpse, generates loot."""
        if self.is_dead: return

        if not hasattr(self, 'inventory') or self.inventory is None:
            self.inventory = []

        if hasattr(self, 'clothes'):
            for slot, cloth_item in self.clothes.items():
                if cloth_item:
                    self.inventory.append(cloth_item)
            self.clothes = {} # Clear it out

        self.is_dead = True
        
        # 1. Play sound
        if self.sound_dead:
             snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
             game.sound_manager.play_sound(self.sound_dead, subdir=snd_dir, game=game, source_pos=self.rect.center, base_volume=random.uniform(0.2, 0.7), pitch_variance=0.15)
             
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
                chance_val = float(loot_entry.get('chance', 0))
                
                # Normalize chance: if the code occasionally passes whole numbers (like 50.0 for 50%),
                # convert it to the 0.0 - 1.0 scale. Since you use 1.0 as 100%, this covers both bases.
                if chance_val > 1.0:
                    chance_val /= 100.0
                    
                if random.random() <= chance_val:
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

        # [FIX] Force immediate item grid rebuild so corpse displays instantly
        if hasattr(game, 'rebuild_item_grid'):
            game.rebuild_item_grid(force=True)

        # Remove self from game
        if self in game.zombies:
            game.zombies.remove(self)
        if self in game.active_zombies:
            game.active_zombies.remove(self)
        if self in game.active_animals:
            game.active_animals.remove(self)