import random
import math
import pygame
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Item
from core.data.config import ZOMBIE_INFECTION_CHANCE
import core.data.config

class ZombieCombat:
    def take_damage(self, amount, game, attacker=None): 
        self.health -= amount
        # [FIX] Ensure health does not stay stuck at 1 or above if damage is sufficient
        if self.health <= 0:
            self.health = 0
            
        self.show_health_bar_timer = 120 

        current_time = pygame.time.get_ticks()
        if current_time - getattr(self, 'last_hit_sound_time', 0) > getattr(self, 'hit_sound_cooldown', 300):
            if hasattr(self, 'sound_hit') and self.sound_hit:
                snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
                game.sound_manager.play_sound(self.sound_hit, subdir=snd_dir, game=game, source_pos=self.rect.center, base_volume=random.uniform(0.2, 0.7), pitch_variance=0.15)
            self.last_hit_sound_time = current_time

        # [FIX] Return True if the entity should be dead
        if self.health <= 0:
            return True
        return False

    def attack(self, target_entity, game):
        self.melee_swing_timer = 10
        dx = target_entity.rect.centerx - self.rect.centerx
        dy = target_entity.rect.centery - self.rect.centery
        self.melee_swing_angle = math.atan2(-dy, dx)
        damage = random.randint(self.min_attack, self.max_attack)

        # 1. Target is the Player
        if target_entity == game.player:
            infection = 0
            if random.random() < ZOMBIE_INFECTION_CHANCE:
                infection = random.uniform(self.min_infection, self.max_infection)
            
            # The player's take_damage handles defense modifiers internally now
            final_dmg, final_inf = target_entity.take_damage(game, damage, infection)
            
            if final_inf > 0:
                print(f"**HIT!** Zombie hit you for {final_dmg:.1f} damage and {final_inf:.1f} infection!")
            else:
                print(f"**HIT!** Zombie hit you for {final_dmg:.1f} damage.")

        # 2. Target is an NPC, Animal, or other Zombie
        else:
            is_dead = target_entity.take_damage(damage, game, attacker=self)
            if is_dead and hasattr(game, 'npcs') and target_entity in game.npcs:
                # Target entity die() is usually called inside its own take_damage, 
                # but we print the message here.
                print("A survivor has been killed by a zombie.")

        # Play attack sound
        if getattr(self, 'sound_attack', None):
            snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
            game.sound_manager.play_sound(
                self.sound_attack, 
                subdir=snd_dir, 
                game=game, 
                source_pos=self.rect.center, 
                base_volume=random.uniform(0.2, 0.7), 
                pitch_variance=0.15
            )

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