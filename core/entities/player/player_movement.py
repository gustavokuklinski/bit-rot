# core/entities/player/player_movement.py

import math
import re
import random
import pygame
from core.data.config import TILE_SIZE
from core.messages import display_message
from core.placement import find_free_tile

class PlayerMovement:
    def enter_vehicle(self, vehicle, game):
        seat_idx = -1
        for i, occupant in enumerate(vehicle.seats):
            if occupant is None:
                seat_idx = i
                break
        
        if seat_idx == -1:
            display_message("Vehicle is full! No free seats.")
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
        display_message(f"Entered {vehicle.name} ({seat_name})")

    def exit_vehicle(self, game):
        if self.vehicle:
            if hasattr(self, 'vehicle_seat_index') and self.vehicle_seat_index is not None:
                if 0 <= self.vehicle_seat_index < len(self.vehicle.seats):
                    if self.vehicle.seats[self.vehicle_seat_index] == self:
                        self.vehicle.seats[self.vehicle_seat_index] = None

            if self.vehicle.rect not in game.obstacles:
                game.obstacles.append(self.vehicle.rect)
            
            self.x += TILE_SIZE 
            self.rect.topleft = (self.x, self.y)
            self.vehicle = None
            self.vehicle_seat_index = None
            
            display_message("Exited vehicle")

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

            # Move the vehicle (handles wall collisions)
            self.vehicle.move(move_x, move_y, obstacles, game=game)
            
            vehicle_rect = self.vehicle.rect
            
            # --- ZOMBIE ROADKILL LOGIC ---
            for zombie in zombies[:]:
                if vehicle_rect.colliderect(zombie.rect):
                    self.vehicle.damage_motor(1.5)
                    damage_to_zombie = 2

                    if zombie.take_damage(damage_to_zombie, game):
                        zombie.die(game)
                        display_message(f"Roadkill! Zombie splattered.")

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
                        display_message(f"Roadkill! Animal splattered.")

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
                            display_message(f"You ran over {npc.name}!")

            # Sync player position to vehicle
            self.x = self.vehicle.x
            self.y = self.vehicle.y
            self.rect.topleft = (int(self.x), int(self.y))
            
        else:
            # Standard Player Walking Movement (when not in vehicle)
            def check_collision(rect_check):
                # Optimize by using collidelistall to only evaluate AABBs we are already touching
                indices = rect_check.collidelistall(obstacles)
                for idx in indices:
                    obstacle = obstacles[idx]
                    gx = obstacle.x // TILE_SIZE
                    gy = obstacle.y // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    if tile_def and 'mask' in tile_def:
                        offset = (obstacle.x - rect_check.x, obstacle.y - rect_check.y)
                        if self.mask.overlap(tile_def['mask'], offset):
                            return 'tile'
                    else:
                        return 'tile'
                return None

            # [FIX] Calculate terrain/entity speed multiplier
            speed_mult = 1.0

            # 1. Check if over entities (Zombies, NPCs, Animals)
            entities = zombies + (list(game.npcs) if hasattr(game, 'npcs') and hasattr(game.npcs, '__iter__') else []) + getattr(game, 'active_animals', [])
            for entity in entities:
                if not getattr(entity, 'is_dead', False) and self.rect.colliderect(entity.rect):
                    speed_mult = min(speed_mult, 0.35) # Slow down heavily when walking over entities
                    break
                    
            # 2. Check if over open window
            gx = self.rect.centerx // TILE_SIZE
            gy = self.rect.centery // TILE_SIZE
            if hasattr(game, 'map_manager'):
                tile_def = game.map_manager.get_tile_at(gx, gy)
                if tile_def:
                    name = tile_def.get('name', '').lower()
                    if 'window' in name or tile_def.get('is_window'):
                        speed_mult = min(speed_mult, 0.35) # Slow down through windows

            move_x = self.vx * speed_mult * game.dt_mult
            move_y = self.vy * speed_mult * game.dt_mult

            # --- SUB-STEPPING WITH SLIDE/SNAG RESOLUTION ---
            total_dist = max(abs(move_x), abs(move_y))
            steps = max(1, int(math.ceil(total_dist)))
            step_x = move_x / steps
            step_y = move_y / steps

            # Increased slide tolerance to easily slip past jagged/diagonal masks
            max_slide = 4 

            for _ in range(steps):
                # Move X
                self.x += step_x
                self.rect.x = round(self.x)
                if check_collision(self.rect) == 'tile':
                    resolved = False
                    for offset in range(1, max_slide + 1):
                        # Try sliding vertically UP
                        self.rect.y -= offset
                        if check_collision(self.rect) != 'tile':
                            self.y -= offset
                            resolved = True
                            break
                        self.rect.y += offset  # Revert UP attempt

                        # Try sliding vertically DOWN
                        self.rect.y += offset
                        if check_collision(self.rect) != 'tile':
                            self.y += offset
                            resolved = True
                            break
                        self.rect.y -= offset  # Revert DOWN attempt

                    if not resolved:
                        self.x -= step_x
                        self.rect.x = round(self.x)

                # Move Y
                self.y += step_y
                self.rect.y = round(self.y)
                if check_collision(self.rect) == 'tile':
                    resolved = False
                    for offset in range(1, max_slide + 1):
                        # Try sliding horizontally LEFT
                        self.rect.x -= offset
                        if check_collision(self.rect) != 'tile':
                            self.x -= offset
                            resolved = True
                            break
                        self.rect.x += offset  # Revert LEFT attempt

                        # Try sliding horizontally RIGHT
                        self.rect.x += offset
                        if check_collision(self.rect) != 'tile':
                            self.x += offset
                            resolved = True
                            break
                        self.rect.x -= offset  # Revert RIGHT attempt

                    if not resolved:
                        self.y -= step_y
                        self.rect.y = round(self.y)

        # --- CHUNK TRANSITION LOGIC ---
        if not getattr(game, 'is_giant_map', False):
            #chunk_width_px = game.CHUNK_SIZE * TILE_SIZE
            #chunk_height_px = game.CHUNK_SIZE * TILE_SIZE
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
                
                # We check the center of the player/vehicle to see if they crossed the boundary
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
                    # Check if the map file exists in the manager
                    if new_map in game.map_manager.map_files:
                        print(f"Transitioning to chunk: {new_map}")
                        
                        # --- CACHE DEPARTING CHUNK STATE ---
                        game.map_states.setdefault(current_map, {})
                        
                        # [FIX] Filter out chasing entities so they travel with the player
                        chasing_zombies = [z for z in game.zombies if getattr(z, 'state', '') == 'chasing']
                        game.map_states[current_map]['zombies'] = [z for z in game.zombies if z not in chasing_zombies]
                        
                        chasing_animals = []
                        if hasattr(game, 'active_animals'):
                            chasing_animals = [a for a in game.active_animals if getattr(a, 'state', '') == 'chasing']
                            game.map_states[current_map]['active_animals'] = [a for a in game.active_animals if a not in chasing_animals]
                        
                        # Animals are also kept in items_on_ground for rendering purposes, remove chasing ones from cache
                        game.map_states[current_map]['items_on_ground'] = [i for i in game.items_on_ground if i not in chasing_animals]
                            
                        # Keep followers with the player so they don't get cached away
                        followers = []
                        chunk_npcs = []
                        if hasattr(game, 'npcs'):
                            for npc in game.npcs:
                                if getattr(npc, 'is_following', False):
                                    followers.append(npc)
                                else:
                                    chunk_npcs.append(npc)
                            game.map_states[current_map]['npcs'] = chunk_npcs
                            
                        # Cache vehicles & containers (excluding the one the player is currently driving to prevent clones)
                        clean_containers = [c for c in game.containers if c != self.vehicle]
                        game.map_states[current_map]['containers'] = clean_containers
                        
                        if hasattr(game.map_manager, 'vehicles'):
                            clean_vehicles = [v for v in game.map_manager.vehicles if v != self.vehicle]
                            game.map_states[current_map]['vehicles'] = clean_vehicles
                        
                        # Adjust coordinates for wrap-around
                        entities_to_teleport = [target] + followers + chasing_zombies + chasing_animals
                        
                        old_width = chunk_width_px
                        old_height = chunk_height_px
                        
                        # Load the new chunk FIRST so its true dynamic dimensions exist in memory!
                        game.load_map(new_map)
                        
                        new_width = getattr(game, 'map_width_pixels', game.CHUNK_SIZE * TILE_SIZE)
                        new_height = getattr(game, 'map_height_pixels', game.CHUNK_SIZE * TILE_SIZE)
                        
                        # Adjust coordinates dynamically depending on which edge was crossed
                        for ent in entities_to_teleport:
                            if new_gx < gx: ent.x += new_width     # Walked left -> appear at right edge of NEW map
                            elif new_gx > gx: ent.x -= old_width   # Walked right -> appear at left edge (subtracted old map width)
                            
                            if new_gy < gy: ent.y += new_height    # Walked up -> appear at bottom edge of NEW map
                            elif new_gy > gy: ent.y -= old_height  # Walked down -> appear at top edge
                            
                            ent.rect.topleft = (int(ent.x), int(ent.y))
                            
                        if self.vehicle:
                            self.x = self.vehicle.x
                            self.y = self.vehicle.y
                            self.rect.topleft = (int(self.x), int(self.y))
                        
                        # --- RESTORE NEW CHUNK STATE ---
                        if new_map in game.map_states:
                            # Re-populate from Memory
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
                                # Identify which of the default containers were actually parsed as obstacles
                                obstacle_container_rects = [rect for rect in default_container_rects if rect in game.obstacles]
                                
                                game.obstacles = [obs for obs in game.obstacles if obs not in default_container_rects]
                                
                                game.containers = game.map_states[new_map]['containers']
                                for c in game.containers:
                                    # Only add back to obstacles if it was originally an obstacle
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
                            # First time ever visiting this chunk! Convert the raw map points into dynamic entities.
                            game.items_on_ground = []
                            game.zombies = []
                            if hasattr(game, 'active_animals'):
                                game.active_animals = []
                            if hasattr(game, 'npcs'):
                                game.npcs.empty()
                                
                            if hasattr(game, 'current_zombie_spawns') and game.current_zombie_spawns:
                                from core.entities.zombie.zombie import Zombie
                                for szx, szy in game.current_zombie_spawns:
                                    for _ in range(random.randint(1, 2)):
                                        z = Zombie.create_random(szx, szy)
                                        if z:
                                            # [FIX] Robust Spatial Spawn - Automatically shifts entity until it's not inside a wall
                                            free_pos = find_free_tile(z.rect, game.obstacles, max_radius=15, initial_pos=(szx, szy))
                                            if free_pos:
                                                z.rect.topleft = free_pos
                                                z.x, z.y = free_pos
                                                game.zombies.append(z)
                                        
                            if hasattr(game, 'npc_spawn_points') and game.npc_spawn_points:
                                from core.entities.npc.npc import NPC
                                for nx, ny in game.npc_spawn_points:
                                    npc = NPC(nx, ny, game, is_static=False)
                                    # [FIX] Robust Spatial Spawn 
                                    free_pos = find_free_tile(npc.rect, game.obstacles, max_radius=15, initial_pos=(nx, ny))
                                    if free_pos:
                                        npc.rect.topleft = free_pos
                                        npc.x, npc.y = free_pos
                                        game.npcs.add(npc)
                                    
                            if hasattr(game, 'active_animals'):
                                from core.entities.animal.animal import Animal
                                num_to_spawn = random.randint(2, 6)
                                for _ in range(num_to_spawn):
                                    ax = random.randint(100, max(101, getattr(game, 'map_width_pixels', chunk_width_px) - 100))
                                    ay = random.randint(100, max(101, getattr(game, 'map_height_pixels', chunk_height_px) - 100))
                                    animal_type = random.choice(['Rat', 'Pig', 'Dog', 'Chicken'])
                                    animal_obj = Animal(ax, ay, animal_type)
                                    
                                    # [FIX] Robust Spatial Spawn
                                    free_pos = find_free_tile(animal_obj.rect, game.obstacles, max_radius=15, initial_pos=(ax, ay))
                                    if free_pos:
                                        animal_obj.rect.topleft = free_pos
                                        animal_obj.x, animal_obj.y = free_pos
                                        game.active_animals.append(animal_obj)
                                        game.items_on_ground.append(animal_obj)
                                    
                        # Make sure followers aren't lost
                        if hasattr(game, 'npcs'):
                            for f_npc in followers:
                                game.npcs.add(f_npc)

                        # [FIX] Re-attach chasing entities to the new active chunk
                        game.zombies.extend(chasing_zombies)
                        if hasattr(game, 'active_animals'):
                            game.active_animals.extend(chasing_animals)
                            # Re-add animals to ground rendering list
                            game.items_on_ground.extend(chasing_animals)

                        # Re-attach driving vehicle to the new chunk
                        if self.vehicle:
                            if self.vehicle not in game.containers:
                                game.containers.append(self.vehicle)
                            if hasattr(game.map_manager, 'vehicles') and self.vehicle not in game.map_manager.vehicles:
                                game.map_manager.vehicles.append(self.vehicle)
                                
                            # Ensure the driven vehicle is NOT in obstacles so it doesn't collide with itself
                            if self.vehicle.rect in game.obstacles:
                                game.obstacles.remove(self.vehicle.rect)
                                
                        # Prevent physics explosions due to the chunk load time spike
                        if hasattr(game, 'last_time'):
                            game.last_time = pygame.time.get_ticks()
                        if hasattr(game, 'dt_ms'):
                            game.dt_ms = 16.0
                            game.dt_mult = 1.0
                                
                        return
                    else:
                        # Revert movement if walking into map bounds where no chunk exists
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