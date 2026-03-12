import math
import pygame
import random
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.messages import display_message
from core.data.config import TILE_SIZE

class NPCCombat:
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
            if check_rect.colliderect(obstacle):
                    # [NEW] Check if this obstacle tile allows visibility
                    gx = obstacle.centerx // TILE_SIZE
                    gy = obstacle.centery // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    if tile_def and tile_def.get('is_visible'):
                        continue # It's transparent, keep checking further!
                        
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

    def take_damage(self, damage, game, attacker=None):
        if self.is_dead: return True
        self.health -= damage
        self.health_bar_timer = 180
        
       
        # Track who attacked this NPC
        if attacker:
            self.current_attacker = attacker
            self.aggro_timer = 10000  # 10 seconds aggro
        
        # If attacked by player, become hostile
        if attacker is not None and attacker == game.player:
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
        
        if hasattr(game, 'sound_manager') and hasattr(self, 'sound_hit') and self.sound_hit:
            current_time = pygame.time.get_ticks()
            if current_time - getattr(self, 'last_hit_sound_time', 0) > getattr(self, 'hit_sound_cooldown', 300):
                game.sound_manager.play_sound(self.sound_hit, subdir='npc', game=game, source_pos=self.rect.center, base_volume=random.uniform(0.2, 0.7),pitch_variance=0.15)
                self.last_hit_sound_time = current_time

        if self.health <= 0:
            self.die(game)
            return True
        return False

    def die(self, game):
        if self.is_dead: return
        self.is_dead = True 

        if hasattr(game, 'sound_manager') and hasattr(self, 'sound_dead') and self.sound_dead:
            game.sound_manager.play_sound(self.sound_dead, subdir='npc', game=game, source_pos=self.rect.center, base_volume=random.uniform(0.2, 0.7), pitch_variance=0.15)

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

        # [FIX] Force immediate item grid rebuild so corpse displays instantly
        if hasattr(game, 'rebuild_item_grid'):
            game.rebuild_item_grid(force=True)

        if self in game.npcs:
            game.npcs.remove(self)
        if self in game.active_npcs:
            game.active_npcs.remove(self)