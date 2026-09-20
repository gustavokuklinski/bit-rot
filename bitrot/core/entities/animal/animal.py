# core/entities/animal/animal.py

import pygame
import random
import os
import math
import core.data.config
from core.entities.zombie.zombie import Zombie
from core.entities.animal.animal_loader import AnimalLoader
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Item
from core.ui.notifications import check_milestone_progress

class Animal(Zombie):

    def __init__(self, x, y, animal_type=None, game=None, layer=None):
        if not AnimalLoader.definitions:
            AnimalLoader.load_animals()

        # Retrieve definition dynamically with case-insensitivity and random fallback
        template = AnimalLoader.get_definition(animal_type)

        if not template:
            # Absolute failsafe if no XMLs exist
            template = {
                'name': 'Rat',
                'stats': {
                    'health': {'min': 5, 'max': 10},
                    'speed': {'min': 1.0, 'max': 1.5},
                    'attack': {'min': 1, 'max': 2},
                    'infection': {'min': 0, 'max': 0}
                },
                'loot': [],
                'sounds': {},
                'sprite': 'rat.png',
                'attack_player': False,
                'spawn_zombies': 0
            }

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
        self.spawn_zombies_max = template.get('spawn_zombies', 0)

        sounds = template.get('sounds', {})
        self.sound_hit = sounds.get('hit')
        self.sound_dead = sounds.get('dead')
        self.sound_attack = sounds.get('attack')
        self.sound_steps = sounds.get('steps')

        if layer is not None:
            self.layer = layer
        elif game:
            self.layer = getattr(game, 'current_layer_index', 1)
        else:
            self.layer = 1

        self.inventory = []
        self.type = "animal"
        
        min_hp = int(template['stats']['health']['min'])
        max_hp = int(template['stats']['health']['max'])
        self.max_health = random.randint(min_hp, max(min_hp, max_hp))
        self.health = self.max_health
        
        min_spd = float(template['stats']['speed']['min'])
        max_spd = float(template['stats']['speed']['max'])
        self.speed = random.uniform(min_spd, max(min_spd, max_spd))

    def update(self, game):
        super().update(game)
        if self.is_dead:
            return

        is_moving = hasattr(self, 'dx') and hasattr(self, 'dy') and (self.dx != 0 or self.dy != 0)
        if is_moving and getattr(self, 'sound_steps', None):
            current_time = pygame.time.get_ticks()
            if not hasattr(self, 'last_step_sound_time'):
                self.last_step_sound_time = current_time + random.randint(0, 400)
                self.current_step_delay = random.randint(350, 450)
                
            delay = getattr(self, 'current_step_delay', 400)
            if current_time - getattr(self, 'last_step_sound_time', 0) > delay:
                game.sound_manager.play_sound(
                    self.sound_steps, 
                    subdir='animals',  
                    game=game, 
                    source_pos=self.rect.center, 
                    base_volume=0.3,
                    pitch_variance=0.2
                )
                self.last_step_sound_time = current_time
                self.current_step_delay = random.randint(350, 500)

    def update_ai(self, player_rect, obstacles, other_zombies, game):
        if self.is_dead:
            return

        if self.attack_player:
            super().update_ai(player_rect, obstacles, other_zombies, game)
            return

        threat_radius = 150 if self.name.lower() != "cow" else 250
        threat_detected = False
        flee_x, flee_y = 0, 0
        
        threats = []
        if game.player and not game.player.is_dead: threats.append(game.player)
        for rp in getattr(game, 'remote_players', {}).values():
            if not getattr(rp, 'is_dead', False): threats.append(rp)

        for t in threats:
            dx = t.rect.centerx - self.rect.centerx
            dy = t.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            
            if getattr(t, 'gun_flash_timer', 0) > 0 and dist < threat_radius * 2:
                flee_x -= dx
                flee_y -= dy
                threat_detected = True
            elif dist < threat_radius and (getattr(t, 'is_running', False) or getattr(self, 'aggro_timer', 0) > 0):
                flee_x -= dx
                flee_y -= dy
                threat_detected = True

        for entity in other_zombies + list(getattr(game, 'npcs', [])):
            if entity is self or entity.is_dead: 
                continue
            dx = entity.rect.centerx - self.rect.centerx
            dy = entity.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist < threat_radius:
                flee_x -= dx
                flee_y -= dy
                threat_detected = True

        if threat_detected:
            self.state = 'fleeing'
            self.aggro_timer = 2000
            flee_dist = math.hypot(flee_x, flee_y)
            if flee_dist > 0:
                flee_x += random.uniform(-50, 50)
                flee_y += random.uniform(-50, 50)
                target_x = self.rect.centerx + flee_x
                target_y = self.rect.centery + flee_y
                self.move_towards((target_x, target_y), obstacles, other_zombies, game, can_see_target=True)
        else:
            if getattr(self, 'aggro_timer', 0) > 0:
                self.aggro_timer -= game.dt_ms
            else:
                super().update_ai(player_rect, obstacles, other_zombies, game)

    def take_damage(self, amount, game, attacker=None):
        if getattr(game, 'is_client', False):
            from core.server.network import NetMsg, send_msg
            send_msg(game.client.socket, {
                'type': NetMsg.ENTITY_DAMAGE,
                'entity_type': 'animal',
                'id': getattr(self, 'id', None),
                'damage': amount
            })
            self.health -= amount
            if self.health <= 0: return True
            return False
            
        if getattr(self, 'is_dead', False):
            return False

        self.health -= amount
        self.show_health_bar_timer = 120

        current_time = pygame.time.get_ticks()
        if hasattr(self, 'sound_hit') and self.sound_hit and game and hasattr(game, 'sound_manager'):
            if current_time - getattr(self, 'last_hit_sound_time', 0) > getattr(self, 'hit_sound_cooldown', 300):
                game.sound_manager.play_sound(
                    self.sound_hit, 
                    subdir='animals', 
                    game=game, 
                    source_pos=self.rect.center, 
                    base_volume=0.3, 
                    pitch_variance=0.15
                ) 
                self.last_hit_sound_time = current_time

        if self.health <= 0:
            self.health = 0
            self.state = 'dead'
            player = getattr(game, 'player', None)
            if attacker == player or attacker is None:
                check_milestone_progress(game, 'kill', 'animal')
            self.die(game)
            return True

        if self.attack_player:
            self.aggro_timer = 10000
            self.state = 'chasing'
        else:
            self.aggro_timer = 2000
            self.state = 'fleeing'

        return False

    def die(self, game):
        if self.is_dead: return
        self.is_dead = True
        self.state = 'dead'

        if getattr(self, 'sound_dead', None) and hasattr(game, 'sound_manager'):
            game.sound_manager.play_sound(
                self.sound_dead, 
                subdir='animals', 
                game=game, 
                source_pos=self.rect.center, 
                base_volume=0.3, 
                pitch_variance=0.15
            )

        corpse = Corpse(
            name=f"Dead {self.name}",
            capacity=10, 
            image_path="../animals/dead.png",  
            pos=self.rect.center,
            decay_ms=60000
        )

        if hasattr(self, 'loot_table') and self.loot_table:
            for loot_entry in self.loot_table:
                chance_val = float(loot_entry.get('chance', 0))
                if chance_val > 1.0: chance_val /= 100.0
                if random.random() <= chance_val:
                    item_name = loot_entry.get('item')
                    new_item = Item.create_from_name(item_name)
                    if new_item: corpse.inventory.append(new_item)

        game.items_on_ground.append(corpse)

        if self in game.items_on_ground:
            try: game.items_on_ground.remove(self)
            except ValueError: pass
        if hasattr(game, 'active_animals') and self in game.active_animals:
            try: game.active_animals.remove(self)
            except ValueError: pass

        # --- DIVERSIFIED INSTANT RESPAWN ---
        from core.map.spawn_manager import get_out_of_sight_spawn_pos

        if getattr(core.data.config, 'ANIMAL_RESPAWN', True):
            animals_per_spawn = getattr(core.data.config, 'ANIMALS_PER_SPAWN', 1)
            num_animals = max(1, int(animals_per_spawn))

            for _ in range(num_animals):
                spawn_pos = get_out_of_sight_spawn_pos(game)
                if spawn_pos:
                    # Pick a diverse animal species based on XML definitions for this layer
                    diverse_type = AnimalLoader.get_random_animal_type(layer=self.layer)
                    new_animal = Animal(spawn_pos[0], spawn_pos[1], diverse_type, game=game, layer=self.layer)
                    game.items_on_ground.append(new_animal)

        if getattr(core.data.config, 'ZOMBIE_RESPAWN', True):
            from core.entities.zombie.zombie import Zombie
            max_zombie_spawns = getattr(core.data.config, 'ZOMBIES_PER_SPAWN', 1)
            num_zombies = max(1, int(max_zombie_spawns))

            for _ in range(num_zombies):
                if len(game.zombies) >= getattr(core.data.config, 'MAX_ZOMBIES_GLOBAL', 10000):
                    break
                spawn_pos = get_out_of_sight_spawn_pos(game)
                if spawn_pos:
                    zombie = Zombie.create_random(spawn_pos[0], spawn_pos[1])
                    game.zombies.append(zombie)

        if hasattr(game, 'splashes'):
            game.splashes.append({
                'pos': (self.rect.centerx, self.rect.bottom), 
                'time': pygame.time.get_ticks(),
                'duration': 250, 
                'radius': 5,    
                'type': 'death_burst'
            })

        if hasattr(game, 'spatial_manager'):
            game.spatial_manager.rebuild_zombie_grid()
            game.spatial_manager.rebuild_item_grid(force=True)

        try: self.kill()
        except Exception: pass

        self.rect.x = -9999
        self.rect.y = -9999