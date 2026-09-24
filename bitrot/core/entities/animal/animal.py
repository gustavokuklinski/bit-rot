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
from core.data.config import TILE_SIZE
from core.systems.utils import create_smooth_entity_mask

class Animal(Zombie):

    def __init__(self, x, y, animal_type=None, game=None, layer=None):
        if not AnimalLoader.definitions:
            AnimalLoader.load_animals()

        # 1. Resolve target layer into a local variable before initializing Sprite
        if layer is not None:
            target_layer = layer
        elif game:
            target_layer = getattr(game, 'current_layer_index', 1)
        else:
            target_layer = 1

        # 2. Get definition matching the resolved layer
        template = AnimalLoader.get_definition(animal_type, layer=target_layer)

        if not template:
            template = {
                'name': 'Rat',
                'stats': {
                    'health': {'min': 10, 'max': 20},
                    'speed': {'min': 0.5, 'max': 0.8},
                    'attack': {'min': 1, 'max': 5},
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

        # 3. Call super().__init__ which initializes pygame.sprite.Sprite
        super().__init__(x, y, zombie_template)

        # 4. Now safe to set self.layer on the initialized Sprite
        
        self.mask = create_smooth_entity_mask(TILE_SIZE, TILE_SIZE, inset_x=2, inset_y=2)
        self.layer = target_layer
        self.attack_player = template.get('attack_player', False)
        self.spawn_zombies_max = template.get('spawn_zombies', 0)

        sounds = template.get('sounds', {})
        self.sound_hit = sounds.get('hit')
        self.sound_dead = sounds.get('dead')
        self.sound_attack = sounds.get('attack')
        self.sound_steps = sounds.get('steps')
        self.sound_wander = sounds.get('wander')

        self.inventory = []
        self.type = "animal"
        
        min_hp = int(template['stats']['health']['min'])
        max_hp = int(template['stats']['health']['max'])
        self.max_health = random.randint(min_hp, max(min_hp, max_hp))
        self.health = self.max_health
        
        min_spd = float(template['stats']['speed']['min'])
        max_spd = float(template['stats']['speed']['max'])
        self.speed = random.uniform(min_spd, max(min_spd, max_spd))

    def attack(self, target_entity, game):
        # Prevent non-hostile animals from ever damaging players
        if not self.attack_player and (target_entity == getattr(game, 'player', None) or type(target_entity).__name__ == 'RemotePlayer'):
            return
        super().attack(target_entity, game)

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

        # Predator animals that are flagged to attack players
        if self.attack_player:
            super().update_ai(player_rect, obstacles, other_zombies, game)
            return

        # Non-hostile animals: flee from threats or wander peacefully
        threat_radius = 150 if self.name.lower() != "cow" else 250
        threat_detected = False
        flee_x, flee_y = 0, 0
        
        threats = []
        if game.player and not game.player.is_dead:
            threats.append(game.player)
        for rp in getattr(game, 'remote_players', {}).values():
            if not getattr(rp, 'is_dead', False):
                threats.append(rp)

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
            if entity is self or getattr(entity, 'is_dead', False): 
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
            self.aggro_timer = 3000
            flee_dist = math.hypot(flee_x, flee_y)
            if flee_dist > 0:
                flee_x += random.uniform(-20, 20)
                flee_y += random.uniform(-20, 20)
                target_x = self.rect.centerx + flee_x
                target_y = self.rect.centery + flee_y
                self.move_towards((target_x, target_y), obstacles, other_zombies, game, can_see_target=False, allow_break_obstacles=False)
        else:
            if getattr(self, 'aggro_timer', 0) > 0:
                self.aggro_timer -= getattr(game, 'dt_ms', 16)

            self.state = 'wandering'
            current_time = pygame.time.get_ticks()

            if getattr(self, 'sound_wander', None):
                if current_time - getattr(self, 'last_wander_sound_time', 0) > getattr(self, 'wander_sound_cooldown', 8000):
                    game.sound_manager.play_sound(
                        self.sound_wander,
                        subdir='animals',
                        game=game,
                        source_pos=self.rect.center,
                        base_volume=0.3,
                        pitch_variance=0.15
                    )
                    self.last_wander_sound_time = current_time
                    self.wander_sound_cooldown = random.randint(6000, 14000)

            target_reached = self.wander_target and math.hypot(self.wander_target[0] - self.rect.centerx, self.wander_target[1] - self.rect.centery) < TILE_SIZE
            wander_interval = getattr(core.data.config, 'ZOMBIE_WANDER_CHANGE_INTERVAL', 2500)

            if (current_time - getattr(self, 'last_wander_change', 0) > wander_interval) or (self.wander_target is None) or target_reached:
                for _ in range(10):
                    wander_radius = 5 * TILE_SIZE
                    new_target_x = self.rect.centerx + random.randint(-wander_radius, wander_radius)
                    new_target_y = self.rect.centery + random.randint(-wander_radius, wander_radius)

                    grid_x = int(new_target_x // TILE_SIZE)
                    grid_y = int(new_target_y // TILE_SIZE)

                    if hasattr(game, 'map_data') and 0 <= grid_y < len(game.map_data) and 0 <= grid_x < len(game.map_data[0]):
                        tile = game.map_manager.get_tile_at(grid_x, grid_y) if hasattr(game, 'map_manager') else None
                        if not tile or not tile.get('is_obstacle', False):
                            g_layer = game.all_ground_layers.get(getattr(self, 'layer', 1), [[]])
                            g_tile = g_layer[grid_y][grid_x] if 0 <= grid_y < len(g_layer) and 0 <= grid_x < len(g_layer[0]) else ''
                            if 'water' not in g_tile.lower():
                                self.wander_target = (new_target_x, new_target_y)
                                break

                self.last_wander_change = current_time

            if self.wander_target:
                self.move_towards(self.wander_target, obstacles, other_zombies, game, can_see_target=False, allow_break_obstacles=False)

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
            self.aggro_timer = 4000
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

        # --- SPAWN ZOMBIES ON PLAYER RADIUS (Based on XML spawn_zombies flag) ---
        max_zombies_to_spawn = int(getattr(self, 'spawn_zombies_max', 0))
        if max_zombies_to_spawn > 0 and getattr(game, 'player', None):
            from core.entities.zombie.zombie import Zombie
            from core.placement import find_free_tile
            
            max_z_global = getattr(core.data.config, 'MAX_ZOMBIES_GLOBAL', 500)
            num_z_to_spawn = random.randint(1, max_zombies_to_spawn) if max_zombies_to_spawn > 1 else max_zombies_to_spawn
            p_center = game.player.rect.center
            view_radius = getattr(game, 'player_view_radius', 10 * TILE_SIZE)

            for _ in range(num_z_to_spawn):
                if len(game.zombies) >= max_z_global:
                    break
                angle = random.uniform(0, math.pi * 2)
                dist = random.uniform(TILE_SIZE * 3, max(TILE_SIZE * 5, view_radius))
                zx = int(p_center[0] + math.cos(angle) * dist)
                zy = int(p_center[1] + math.sin(angle) * dist)
                
                z = Zombie.create_random(zx, zy)
                if z:
                    z.layer = self.layer
                    free_pos = find_free_tile(z.rect, game.obstacles, initial_pos=(zx, zy), max_radius=8)
                    if free_pos:
                        z.rect.topleft = free_pos
                        z.x, z.y = free_pos
                        game.zombies.append(z)

        # --- DIVERSIFIED RESPAWN (Strictly on self.layer) ---
        from core.map.spawn_manager import get_out_of_sight_spawn_pos

        max_anim = getattr(core.data.config, 'ANIMAL_MAX_CHUNK', 6)
        if getattr(core.data.config, 'ANIMAL_RESPAWN', True) and max_anim > 0:
            animals_per_spawn = int(getattr(core.data.config, 'ANIMALS_PER_SPAWN', 1))
            if animals_per_spawn > 0:
                for _ in range(animals_per_spawn):
                    spawn_pos = get_out_of_sight_spawn_pos(game)
                    if spawn_pos:
                        diverse_type = AnimalLoader.get_random_animal_type(layer=self.layer)
                        if diverse_type:
                            new_animal = Animal(spawn_pos[0], spawn_pos[1], diverse_type, game=game, layer=self.layer)
                            game.items_on_ground.append(new_animal)
                            if hasattr(game, 'active_animals'):
                                game.active_animals.append(new_animal)

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