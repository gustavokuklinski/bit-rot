# core/entities/player/player_movement.py

import math
import re
import random
import pygame
import core.data.config
from core.data.config import *
from core.messages import display_message
from core.placement import find_free_tile
from core.entities.npc.npc import NPC
from core.data.localization import tr

class PlayerMovement:
    def enter_vehicle(self, vehicle, game):
        seat_idx = -1
        for i, occupant in enumerate(vehicle.seats):
            if occupant is None:
                seat_idx = i
                break
        
        if seat_idx == -1:
            display_message(tr('msg', "Vehicle is full! No free seats."))
            return

        self.vehicle = vehicle
        self.x = vehicle.x 
        self.y = vehicle.y
        self.rect.topleft = (self.x, self.y)
        
        vehicle.seats[seat_idx] = self
        self.vehicle_seat_index = seat_idx

        if vehicle.rect in game.obstacles:
            game.obstacles.remove(vehicle.rect)
        
        seat_name = "Driver's Seat" if seat_idx == 0 else f"Seat {seat_idx+1}"
        display_message(f"{tr('msg', 'Entered')} {vehicle.name} ({tr('msg', seat_name)})")

    def exit_vehicle(self, game):
        if self.vehicle:
            if hasattr(self, 'vehicle_seat_index') and self.vehicle_seat_index is not None:
                if 0 <= self.vehicle_seat_index < len(self.vehicle.seats):
                    if self.vehicle.seats[self.vehicle_seat_index] == self:
                        self.vehicle.seats[self.vehicle_seat_index] = None

            if self.vehicle.rect not in game.obstacles:
                game.obstacles.append(self.vehicle.rect)
            
            # --- Dynamic Pixel-Perfect Exit Logic ---
            exit_points = [
                (self.vehicle.rect.right + 2, self.vehicle.rect.centery - (self.rect.height / 2)),
                (self.vehicle.rect.left - self.rect.width - 2, self.vehicle.rect.centery - (self.rect.height / 2)),
                (self.vehicle.rect.centerx - (self.rect.width / 2), self.vehicle.rect.bottom + 2),
                (self.vehicle.rect.centerx - (self.rect.width / 2), self.vehicle.rect.top - self.rect.height - 2)
            ]
            
            placed = False
            for px, py in exit_points:
                self.rect.topleft = (int(px), int(py))
                collision = False
                for ob in game.obstacles:
                    if self.rect.colliderect(ob):
                        collision = True
                        break
                        
                if not collision:
                    self.x, self.y = px, py
                    placed = True
                    break
            
            if not placed:
                self.x = self.vehicle.rect.centerx - (self.rect.width / 2)
                self.y = self.vehicle.rect.centery - (self.rect.height / 2)
                self.rect.topleft = (int(self.x), int(self.y))
                
                free_pos = find_free_tile(self.rect, game.obstacles, max_radius=2, initial_pos=(self.x, self.y))
                if free_pos:
                    self.x, self.y = free_pos
                    self.rect.topleft = (int(self.x), int(self.y))
            
            self.vehicle = None
            self.vehicle_seat_index = None
            display_message(tr('msg', "Exited vehicle"))

    def update_position(self, obstacles, zombies, game):
        if self.vehicle:
            if not self.vehicle.is_driveable():
                return

            current_max_speed = self.vehicle.max_speed
            input_x = 0
            input_y = 0
            
            if self.vehicle.active and (self.vx != 0 or self.vy != 0):
                input_magnitude = math.sqrt(self.vx**2 + self.vy**2)
                if input_magnitude > 0:
                    input_x = (self.vx / input_magnitude)
                    input_y = (self.vy / input_magnitude)

            if input_x != 0 or input_y != 0:
                self.vehicle.velocity[0] += input_x * self.vehicle.acceleration * game.dt_mult
                self.vehicle.velocity[1] += input_y * self.vehicle.acceleration * game.dt_mult
            else:
                speed = self.vehicle.current_speed_val
                if speed > 0:
                    friction_loss = min(speed, self.vehicle.friction * game.dt_mult)
                    scale = (speed - friction_loss) / speed
                    self.vehicle.velocity[0] *= scale
                    self.vehicle.velocity[1] *= scale

            speed = self.vehicle.current_speed_val
            if speed > current_max_speed:
                scale = current_max_speed / speed
                self.vehicle.velocity[0] *= scale
                self.vehicle.velocity[1] *= scale
            
            move_x = self.vehicle.velocity[0]
            move_y = self.vehicle.velocity[1]

            if self.vehicle.active and speed > 0.1:
                fuel_item = self.vehicle.equipment.get('fuel')
                if fuel_item:
                    fuel_item.load = max(0, fuel_item.load - 0.005 * game.dt_mult) 
                
                self.vehicle.battery = min(1.0, self.vehicle.battery + 0.0005 * game.dt_mult)

            # Move vehicle
            self.vehicle.move(move_x, move_y, obstacles, game=game)
            vehicle_rect = self.vehicle.rect
            
            # --- ZOMBIE ROADKILL LOGIC ---
            for zombie in zombies[:]:
                if vehicle_rect.colliderect(zombie.rect):
                    self.vehicle.damage_motor(1.5)
                    damage_to_zombie = 2

                    if zombie.take_damage(damage_to_zombie, game):
                        zombie.die(game)
                        display_message(tr('msg', "Roadkill! Zombie splattered."))

                        if hasattr(game, 'zombies_killed'):
                            game.zombies_killed += 1

                    self.vehicle.velocity[0] *= 0.5
                    self.vehicle.velocity[1] *= 0.5

            # --- ANIMAL ROADKILL LOGIC ---
            animals_to_check = getattr(game, 'active_animals', [])
            for animal in list(animals_to_check):
                if vehicle_rect.colliderect(animal.rect):
                    self.vehicle.damage_motor(1.5)
                    damage_to_animal = 2

                    if animal.take_damage(damage_to_animal, game):
                        animal.die(game)
                        if animal in game.items_on_ground:
                            game.items_on_ground.remove(animal)
                        if animal in game.active_animals:
                            game.active_animals.remove(animal)
                        display_message(tr('msg', "Roadkill! Animal splattered."))

                    self.vehicle.velocity[0] *= 0.5
                    self.vehicle.velocity[1] *= 0.5

            # --- NPC ROADKILL LOGIC ---
            if hasattr(game, 'npcs'):
                npcs_to_check = game.npcs.sprites() if hasattr(game.npcs, 'sprites') else game.npcs
                
                for npc in list(npcs_to_check):
                    if not npc.is_dead and vehicle_rect.colliderect(npc.rect):
                        self.vehicle.damage_motor(1.5)
                        damage_to_npc = 2
                        is_dead = npc.take_damage(damage_to_npc, game, attacker=self)
                        
                        self.vehicle.velocity[0] *= 0.5
                        self.vehicle.velocity[1] *= 0.5
                        
                        if is_dead:
                            npc.die(game)
                            display_message(f"{tr('msg', 'You ran over')} {npc.name}!")

            # Sync player position to vehicle
            self.x = self.vehicle.x
            self.y = self.vehicle.y
            self.rect.topleft = (int(self.x), int(self.y))
            
        else:
            # Standard Walking Movement
            def check_collision(rect_check):
                indices = rect_check.collidelistall(obstacles)
                for idx in indices:
                    obstacle = obstacles[idx]
                    gx = obstacle.x // TILE_SIZE
                    gy = obstacle.y // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    if tile_def and 'mask' in tile_def and getattr(self, 'mask', None):
                        offset = (obstacle.x - rect_check.x, obstacle.y - rect_check.y)
                        if self.mask.overlap(tile_def['mask'], offset):
                            return 'tile'
                    else:
                        return 'tile'
                return None

            speed_mult = 1.0

            # 1. Check entities push/slowdown
            entities = zombies + (list(game.npcs) if hasattr(game, 'npcs') and hasattr(game.npcs, '__iter__') else []) + getattr(game, 'active_animals', [])
            for entity in entities:
                if not getattr(entity, 'is_dead', False) and self.rect.colliderect(entity.rect):
                    if hasattr(self, 'mask') and hasattr(entity, 'mask') and self.mask and entity.mask:
                        offset = (entity.rect.x - self.rect.x, entity.rect.y - self.rect.y)
                        if not self.mask.overlap(entity.mask, offset):
                            continue

                    speed_mult = min(speed_mult, 0.20) 
                    
                    dx = entity.rect.centerx - self.rect.centerx
                    dy = entity.rect.centery - self.rect.centery
                    dist = math.hypot(dx, dy)
                    
                    push_power = 0.5 
                    if not hasattr(entity, 'knockback_velocity') or isinstance(entity.knockback_velocity, tuple):
                        entity.knockback_velocity = [0.0, 0.0]
                        
                    if dist > 0:
                        entity.knockback_velocity[0] += (dx / dist) * push_power
                        entity.knockback_velocity[1] += (dy / dist) * push_power
                    else:
                        entity.knockback_velocity[0] += random.choice([-1.0, 1.0]) * push_power
                        entity.knockback_velocity[1] += random.choice([-1.0, 1.0]) * push_power
                        
                    entity.knockback_timer = max(getattr(entity, 'knockback_timer', 0), 100)
                    
            # 2. Window slow down
            gx = self.rect.centerx // TILE_SIZE
            gy = self.rect.centery // TILE_SIZE
            if hasattr(game, 'map_manager'):
                tile_def = game.map_manager.get_tile_at(gx, gy)
                if tile_def:
                    name = tile_def.get('name', '').lower()
                    if 'window' in name or tile_def.get('is_window'):
                        speed_mult = min(speed_mult, 0.35)

            move_x = self.vx * speed_mult * game.dt_mult
            move_y = self.vy * speed_mult * game.dt_mult

            # Sub-stepping with slide resolution
            total_dist = max(abs(move_x), abs(move_y))
            steps = max(1, int(math.ceil(total_dist)))
            step_x = move_x / steps
            step_y = move_y / steps
            max_slide = 4 

            for _ in range(steps):
                # Move X
                self.x += step_x
                self.rect.x = round(self.x)
                if check_collision(self.rect) == 'tile':
                    resolved = False
                    for offset in range(1, max_slide + 1):
                        self.rect.y -= offset
                        if check_collision(self.rect) != 'tile':
                            self.y -= offset
                            resolved = True
                            break
                        self.rect.y += offset

                        self.rect.y += offset
                        if check_collision(self.rect) != 'tile':
                            self.y += offset
                            resolved = True
                            break
                        self.rect.y -= offset

                    if not resolved:
                        self.x -= step_x
                        self.rect.x = round(self.x)

                # Move Y
                self.y += step_y
                self.rect.y = round(self.y)
                if check_collision(self.rect) == 'tile':
                    resolved = False
                    for offset in range(1, max_slide + 1):
                        self.rect.x -= offset
                        if check_collision(self.rect) != 'tile':
                            self.x -= offset
                            resolved = True
                            break
                        self.rect.x += offset

                        self.rect.x += offset
                        if check_collision(self.rect) != 'tile':
                            self.x += offset
                            resolved = True
                            break
                        self.rect.x -= offset

                    if not resolved:
                        self.y -= step_y
                        self.rect.y = round(self.y)

        # --- CHUNK TRANSITION LOGIC ---
        if not getattr(game, 'is_giant_map', False):
            chunk_width_px = getattr(game, 'map_width_pixels', game.CHUNK_SIZE * TILE_SIZE)
            chunk_height_px = getattr(game, 'map_height_pixels', game.CHUNK_SIZE * TILE_SIZE)

            current_map = game.map_manager.current_map_filename
            match = re.match(r'map_L(\d+)_(\d+)_(\d+)_map\.csv', current_map)
            
            if match:
                layer = int(match.group(1))
                gx = int(match.group(2))
                gy = int(match.group(3))
                
                new_gx, new_gy = gx, gy
                transition = False
                
                target = self.vehicle if self.vehicle else self
                
                if target.rect.centerx < 0:
                    new_gx -= 1
                    transition = True
                elif target.rect.centerx >= chunk_width_px:
                    new_gx += 1
                    transition = True
                    
                if target.rect.centery < 0:
                    new_gy -= 1
                    transition = True
                elif target.rect.centery >= chunk_height_px:
                    new_gy += 1
                    transition = True
                    
                if transition:
                    new_map = f"map_L{layer}_{new_gx}_{new_gy}_map.csv"

                    # --- ON-DEMAND GENERATION: Generate chunk as player enters it ---
                    if new_map not in game.map_manager.map_files:
                        if hasattr(game, 'generator') and game.generator:
                            if 0 <= new_gx < game.generator.grid_w and 0 <= new_gy < game.generator.grid_h:
                                game.generator.generate_chunk_on_demand(new_gx, new_gy)
                                game.map_manager.refresh_maps()

                    # Check if the map file exists in the manager now
                    if new_map in game.map_manager.map_files:
                        print(f"Transitioning to chunk: {new_map}")
                        
                        # --- CACHE DEPARTING CHUNK STATE ---
                        game.map_states.setdefault(current_map, {})
                        
                        chasing_zombies = [z for z in game.zombies if getattr(z, 'state', '') == 'chasing']
                        game.map_states[current_map]['zombies'] = [z for z in game.zombies if z not in chasing_zombies]
                        
                        chasing_animals = []
                        if hasattr(game, 'active_animals'):
                            chasing_animals = [a for a in game.active_animals if getattr(a, 'state', '') == 'chasing']
                            game.map_states[current_map]['active_animals'] = [a for a in game.active_animals if a not in chasing_animals]
                        
                        game.map_states[current_map]['items_on_ground'] = [i for i in game.items_on_ground if i not in chasing_animals]
                            
                        followers = []
                        chunk_npcs = []
                        if hasattr(game, 'npcs'):
                            for npc in game.npcs:
                                if getattr(npc, 'is_following', False):
                                    followers.append(npc)
                                else:
                                    chunk_npcs.append(npc)
                            game.map_states[current_map]['npcs'] = chunk_npcs
                            
                        clean_containers = [c for c in game.containers if c != self.vehicle]
                        game.map_states[current_map]['containers'] = clean_containers
                        
                        if hasattr(game.map_manager, 'vehicles'):
                            clean_vehicles = [v for v in game.map_manager.vehicles if v != self.vehicle]
                            game.map_states[current_map]['vehicles'] = clean_vehicles
                        
                        entities_to_teleport = [target] + followers + chasing_zombies + chasing_animals
                        
                        old_width = chunk_width_px
                        old_height = chunk_height_px
                        
                        game.load_map(new_map)
                        
                        new_width = getattr(game, 'map_width_pixels', game.CHUNK_SIZE * TILE_SIZE)
                        new_height = getattr(game, 'map_height_pixels', game.CHUNK_SIZE * TILE_SIZE)
                        
                        for ent in entities_to_teleport:
                            if new_gx < gx: ent.x += new_width
                            elif new_gx > gx: ent.x -= old_width
                            
                            if new_gy < gy: ent.y += new_height
                            elif new_gy > gy: ent.y -= old_height
                            
                            ent.rect.topleft = (int(ent.x), int(ent.y))
                            
                        if self.vehicle:
                            self.x = self.vehicle.x
                            self.y = self.vehicle.y
                            self.rect.topleft = (int(self.x), int(self.y))
                        
                        # --- RESTORE NEW CHUNK STATE ---
                        if new_map in game.map_states:
                            game.items_on_ground = game.map_states[new_map].get('items_on_ground', [])
                            game.zombies = game.map_states[new_map].get('zombies', [])
                            if hasattr(game, 'active_animals'):
                                game.active_animals = game.map_states[new_map].get('active_animals', [])
                                
                            if hasattr(game, 'npcs'):
                                game.npcs.empty()
                                for npc in game.map_states[new_map].get('npcs', []):
                                    game.npcs.add(npc)
                                    
                            if 'containers' in game.map_states[new_map]:
                                default_container_rects = [c.rect for c in game.containers]
                                obstacle_container_rects = [rect for rect in default_container_rects if rect in game.obstacles]
                                game.obstacles = [obs for obs in game.obstacles if obs not in default_container_rects]
                                game.containers = game.map_states[new_map]['containers']
                                for c in game.containers:
                                    if c.rect in obstacle_container_rects and c.rect not in game.obstacles:
                                        game.obstacles.append(c.rect)
                                        
                            if 'vehicles' in game.map_states[new_map] and hasattr(game.map_manager, 'vehicles'):
                                default_veh_rects = [v.rect for v in game.map_manager.vehicles]
                                game.obstacles = [obs for obs in game.obstacles if obs not in default_veh_rects]
                                game.map_manager.vehicles = game.map_states[new_map]['vehicles']
                                for v in game.map_manager.vehicles:
                                    if v.rect not in game.obstacles:
                                        game.obstacles.append(v.rect)
                        else:
                            # First time visiting chunk
                            # First time visiting chunk
                            game.items_on_ground = []
                            game.zombies = []
                            if hasattr(game, 'active_animals'):
                                game.active_animals = []
                            if hasattr(game, 'npcs'):
                                game.npcs.empty()
                                
                            max_z_chunk = getattr(core.data.config, 'ZOMBIE_MAX_CHUNK', 6)
                            z_per_spawn = getattr(core.data.config, 'ZOMBIES_PER_SPAWN', 3)
                            max_z_global = getattr(core.data.config, 'MAX_ZOMBIES_GLOBAL', 500)

                            if hasattr(game, 'current_zombie_spawns') and game.current_zombie_spawns and max_z_chunk > 0 and max_z_global > 0 and z_per_spawn > 0:
                                from core.entities.zombie.zombie import Zombie
                                for szx, szy in game.current_zombie_spawns:
                                    if len(game.zombies) >= max_z_chunk or len(game.zombies) >= max_z_global:
                                        break
                                    for _ in range(z_per_spawn):
                                        z = Zombie.create_random(szx, szy)
                                        if z:
                                            free_pos = find_free_tile(z.rect, game.obstacles, max_radius=15, initial_pos=(szx, szy))
                                            if free_pos:
                                                z.rect.topleft = free_pos
                                                z.x, z.y = free_pos
                                                game.zombies.append(z)
                                        
                            max_npc_chunk = getattr(core.data.config, 'NPC_MAX_CHUNK', 6)
                            max_npc_global = getattr(core.data.config, 'MAX_NPCS_GLOBAL', 1500)
                            can_spawn_npcs = max_npc_chunk > 0 and max_npc_global > 0 and getattr(core.data.config, 'NPC_SPAWN_CHANCE', 1.0) > 0.0

                            if hasattr(game, 'npc_spawn_points') and game.npc_spawn_points and can_spawn_npcs:
                                for spawn_data in game.npc_spawn_points:
                                    if len(game.npcs) >= max_npc_chunk:
                                        break
                                    nx, ny = spawn_data[0], spawn_data[1]
                                    npc_type = spawn_data[2] if len(spawn_data) == 3 else 'NPC'
                                    is_static = (npc_type == 'SNPC')
                                    npc = NPC(nx, ny, game, is_static=is_static)
                                    npc.is_friendly = is_static
                                    free_pos = find_free_tile(npc.rect, game.obstacles, max_radius=15, initial_pos=(nx, ny))
                                    if free_pos:
                                        npc.rect.topleft = free_pos
                                        npc.x, npc.y = free_pos
                                        game.npcs.add(npc)
                                    
                            max_anim = getattr(core.data.config, 'ANIMAL_MAX_CHUNK', 6)
                            anim_per_spawn = getattr(core.data.config, 'ANIMALS_PER_SPAWN', 3)
                            if hasattr(game, 'active_animals') and max_anim > 0 and anim_per_spawn > 0:
                                from core.entities.animal.animal import Animal
                                from core.entities.animal.animal_loader import AnimalLoader
                                AnimalLoader.load_animals()
                                curr_layer = getattr(game, 'current_layer_index', 1)
                                valid_animal_types = []
                                valid_weights = []
                                for a_name, a_def in AnimalLoader.definitions.items():
                                    allowed = a_def.get('spawn_layers', [1, 2])
                                    if curr_layer in allowed:
                                        valid_animal_types.append(a_name)
                                        valid_weights.append(max(1, int(a_def.get('spawn_weight', 10))))

                                if valid_animal_types:
                                    num_to_spawn = min(anim_per_spawn, max_anim)
                                    for _ in range(num_to_spawn):
                                        ax = random.randint(100, max(101, getattr(game, 'map_width_pixels', chunk_width_px) - 100))
                                        ay = random.randint(100, max(101, getattr(game, 'map_height_pixels', chunk_height_px) - 100))
                                        animal_type = random.choices(valid_animal_types, weights=valid_weights, k=1)[0]
                                        animal_obj = Animal(ax, ay, animal_type, game=game, layer=curr_layer)
                                        free_pos = find_free_tile(animal_obj.rect, game.obstacles, max_radius=15, initial_pos=(ax, ay))
                                        if free_pos:
                                            animal_obj.rect.topleft = free_pos
                                            animal_obj.x, animal_obj.y = free_pos
                                            game.active_animals.append(animal_obj)
                                            game.items_on_ground.append(animal_obj)
                                    
                        if hasattr(game, 'npcs'):
                            for f_npc in followers:
                                game.npcs.add(f_npc)

                        game.zombies.extend(chasing_zombies)
                        if hasattr(game, 'active_animals'):
                            game.active_animals.extend(chasing_animals)
                            game.items_on_ground.extend(chasing_animals)

                        if self.vehicle:
                            if self.vehicle not in game.containers:
                                game.containers.append(self.vehicle)
                            if hasattr(game.map_manager, 'vehicles') and self.vehicle not in game.map_manager.vehicles:
                                game.map_manager.vehicles.append(self.vehicle)
                            if self.vehicle.rect in game.obstacles:
                                game.obstacles.remove(self.vehicle.rect)

                        # Prevent physics explosions due to the chunk load time spike
                        if hasattr(game, 'last_time'):
                            game.last_time = pygame.time.get_ticks()
                        if hasattr(game, 'dt_ms'):
                            game.dt_ms = 16.0
                            game.dt_mult = 1.0

                        # --- TRIGGER CHUNK LOADING SCREEN ---
                        game.game_state = 'CHUNK_LOADING'
                        return
                    else:
                        # Revert movement if walking into map bounds where no chunk exists or blocked
                        if target.rect.centerx < 0: target.x = 0
                        elif target.rect.centerx >= chunk_width_px: target.x = chunk_width_px - target.rect.width
                        if target.rect.centery < 0: target.y = 0
                        elif target.rect.centery >= chunk_height_px: target.y = chunk_height_px - target.rect.height
                        
                        target.rect.topleft = (int(target.x), int(target.y))
                        if self.vehicle:
                            self.vehicle.velocity = [0, 0]
                            self.x = self.vehicle.x
                            self.y = self.vehicle.y
                            self.rect.topleft = (int(self.x), int(self.y))