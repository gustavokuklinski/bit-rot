import random
import math
import pygame
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Item
from core.data.config import ZOMBIE_INFECTION_CHANCE
import core.data.config
from core.ui.notifications import check_milestone_progress

class ZombieCombat:
    def take_damage(self, amount, game, attacker=None):
        if getattr(self, 'is_dead', False) or getattr(self, 'health', 0) <= 0:
            return False

        if getattr(game, 'is_client', False):
            from core.server.network import NetMsg, send_msg
            send_msg(game.client.socket, {
                'type': NetMsg.ENTITY_DAMAGE,
                'entity_type': 'zombie',
                'id': getattr(self, 'id', None),
                'damage': amount
            })
            self.health -= amount
            self.show_health_bar_timer = 120
            if self.health <= 0: return True
            return False

        # Prevent multiple kill triggers on an already dead zombie
        was_dead = getattr(self, 'is_dead', False) or self.health <= 0
        
        player = getattr(game, 'player', None)
        
        # --- TRIGGER HIT STATIC NPC MILESTONE ---
        if (attacker == player or attacker is None) and type(self).__name__ == 'NPC' and getattr(self, 'is_static', False):
            check_milestone_progress(game, 'hit', 'static_npc')
        # ---------------------------------------------

        self.health -= amount

        # [FIX] Ensure health does not stay stuck at 1 or above
        if self.health <= 0:
            self.health = 0

            # --- TRIGGER KILL MILESTONES (Only if it just died from this hit) ---
            if not was_dead:
                # Treat 'None' as the player to catch default weapon/projectile hits
                if attacker == player or attacker is None:
                    if type(self).__name__ == 'NPC':
                        if not getattr(self, 'is_friendly', True):
                            check_milestone_progress(game, 'kill', 'hostile_npc')
                    else:
                        check_milestone_progress(game, 'kill', 'zombie')
            # --------------------------------------------------------------------

        self.show_health_bar_timer = 120 

        current_time = pygame.time.get_ticks()
        if current_time - getattr(self, 'last_hit_sound_time', 0) > getattr(self, 'hit_sound_cooldown', 300):
            if hasattr(self, 'sound_hit') and self.sound_hit:
                snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
                game.sound_manager.play_sound(
                    self.sound_hit, 
                    subdir=snd_dir, 
                    game=game, 
                    source_pos=self.rect.center, 
                    base_volume=0.6, 
                    pitch_variance=0.15
                )
            self.last_hit_sound_time = current_time

        if self.health <= 0:
            return True
        return False

    def attack(self, target_entity, game):
        if getattr(self, 'is_dead', False) or getattr(self, 'health', 0) <= 0:
            return

        if getattr(target_entity, 'is_dead', False) or getattr(target_entity, 'health', 1) <= 0:
            return
            
        if getattr(target_entity, 'type', '') == 'animal' or target_entity.__class__.__name__ == 'Animal':
            return

        # If player is driving a vehicle, attack damages the vehicle motor instead of biting the player
        if target_entity == getattr(game, 'player', None) and getattr(game.player, 'vehicle', None):
            veh = game.player.vehicle
            veh.damage_motor(random.uniform(0.5, 1.5))
            self.melee_swing_timer = 10
            return

        self.melee_swing_timer = 10
        dx = target_entity.rect.centerx - self.rect.centerx
        dy = target_entity.rect.centery - self.rect.centery
        self.melee_swing_angle = math.atan2(-dy, dx)
        damage = random.randint(self.min_attack, self.max_attack)

        # 1. Target is the Player or a RemotePlayer
        if target_entity == game.player or type(target_entity).__name__ == 'RemotePlayer':
            infection = 0
            if random.random() < ZOMBIE_INFECTION_CHANCE:
                infection = random.uniform(self.min_infection, self.max_infection)
            
            if target_entity == game.player:
                final_dmg, final_inf = target_entity.take_damage(game, damage, infection, attacker=self)
                if final_inf > 0:
                    print(f"**HIT!** Zombie hit you for {final_dmg:.1f} damage and {final_inf:.1f} infection!")
                else:
                    print(f"**HIT!** Zombie hit you for {final_dmg:.1f} damage.")
            else:
                target_entity.take_damage(damage, game, infection=infection)
                
        # 2. Target is an NPC, Animal, or other Zombie
        else:
            if getattr(target_entity, 'type', '') == 'animal' or target_entity.__class__.__name__ == 'Animal':
                return
            is_dead = target_entity.take_damage(damage, game, attacker=self)
            if is_dead and hasattr(game, 'npcs') and target_entity in game.npcs:
                print("A survivor has been killed by a zombie.")

        # Play attack sound only when actually biting/hitting an unshielded entity
        if getattr(self, 'sound_attack', None):
            snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
            game.sound_manager.play_sound(
                self.sound_attack, 
                subdir=snd_dir, 
                game=game, 
                source_pos=self.rect.center, 
                base_volume=0.6, 
                pitch_variance=0.15
            )

    def die(self, game):
        """Handles zombie death: plays sound, creates corpse, generates loot, and respawns reinforcements."""
        if getattr(self, 'is_dead', False): return

        self.is_dead = True
        self.health = 0
        self.state = 'dead'
        self.vx = 0
        self.vy = 0
        self.aggro_timer = 0
        self.noise_target = None
        self.path = []

        if not hasattr(self, 'inventory') or self.inventory is None:
            self.inventory = []

        if hasattr(self, 'clothes'):
            for slot, cloth_item in self.clothes.items():
                if cloth_item:
                    self.inventory.append(cloth_item)
            self.clothes = {}

        # 1. Play sound
        if getattr(self, 'sound_dead', None) and hasattr(game, 'sound_manager'):
            snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
            game.sound_manager.play_sound(
                self.sound_dead, 
                subdir=snd_dir, 
                game=game, 
                source_pos=self.rect.center, 
                base_volume=0.3, 
                pitch_variance=0.15
            )
             
        # 2. Create Corpse at death position
        corpse = Corpse(
            name=f"Corpse of {self.name}",
            capacity=20, 
            image_path="zombie/dead.png",
            pos=self.rect.center,
            decay_ms=60000
        )

        for item in self.inventory:
            corpse.inventory.append(item)

        if getattr(self, 'loot_table', None):
            for loot_entry in self.loot_table:
                chance_val = float(loot_entry.get('chance', 0))
                if chance_val > 1.0:
                    chance_val /= 100.0
                if random.random() <= chance_val:
                    item_name = loot_entry.get('item')
                    new_item = Item.create_from_name(item_name)
                    if new_item:
                        corpse.inventory.append(new_item)

        game.items_on_ground.append(corpse)

        # Remove from active lists
        if self in game.zombies:
            try: game.zombies.remove(self)
            except ValueError: pass
        if hasattr(game, 'active_zombies') and self in game.active_zombies:
            try: game.active_zombies.remove(self)
            except ValueError: pass

        # Move dead zombie's hitbox completely out of world bounds
        self.rect.x = -9999
        self.rect.y = -9999
        self.x = -9999
        self.y = -9999
        try:
            self.kill()
        except Exception:
            pass

        # 3. Dynamic Instant Circular Zombie Respawn (10 tiles from view radius)
        if getattr(core.data.config, 'ZOMBIE_RESPAWN', True) and getattr(self, 'type', 'zombie') != 'animal':
            from core.map.spawn_manager import get_out_of_sight_spawn_pos
            from core.entities.zombie.zombie import Zombie
            
            max_spawn = getattr(core.data.config, 'ZOMBIES_PER_SPAWN', 1)
            num_to_spawn = max(1, int(max_spawn))
            
            for _ in range(num_to_spawn):
                if len(game.zombies) >= core.data.config.MAX_ZOMBIES_GLOBAL:
                    break
                spawn_pos = get_out_of_sight_spawn_pos(game)
                if spawn_pos:
                    new_zombie = Zombie.create_random(spawn_pos[0], spawn_pos[1])
                    game.zombies.append(new_zombie)

        if hasattr(game, 'spatial_manager'):
            game.spatial_manager.rebuild_zombie_grid(force=True)