import math
import pygame
from core.data.config import TILE_SIZE
from core.messages import display_message_player

class PlayerMovement:
    def enter_vehicle(self, vehicle, game):
        seat_idx = -1
        for i, occupant in enumerate(vehicle.seats):
            if occupant is None:
                seat_idx = i
                break
        
        if seat_idx == -1:
            display_message_player("Vehicle is full! No free seats.")
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
        display_message_player(f"Entered {vehicle.name} ({seat_name})")

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
            
            display_message_player("Exited vehicle")

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
                self.vehicle.velocity[0] += input_x * self.vehicle.acceleration
                self.vehicle.velocity[1] += input_y * self.vehicle.acceleration
            else:
                speed = self.vehicle.current_speed_val
                if speed > 0:
                    friction_loss = min(speed, self.vehicle.friction)
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
                    fuel_item.load = max(0, fuel_item.load - 0.005) 
                
                self.vehicle.battery = min(1.0, self.vehicle.battery + 0.0005)

            # Move the vehicle (handles wall collisions)
            # [UPDATED] Pass game instance for mask checks against tiles
            self.vehicle.move(move_x, move_y, obstacles, game=game)
            
            vehicle_rect = self.vehicle.rect
            
            # --- ZOMBIE ROADKILL LOGIC ---
            # Explicitly check collision with zombies and KILL them if hit
            for zombie in zombies[:]:
                if vehicle_rect.colliderect(zombie.rect):
                    self.vehicle.damage_motor(1.5)
                    # Massive damage to ensure instant kill
                    damage_to_zombie = 2

                    # Apply damage. take_damage returns True if health <= 0
                    if zombie.take_damage(damage_to_zombie, game):
                        # IMPORTANT: Must call die() to spawn corpse and remove from list
                        zombie.die(game)
                        display_message_player(f"Roadkill! Zombie splattered.")

                        # Add kill count if not handled inside die
                        if hasattr(game, 'zombies_killed'):
                            game.zombies_killed += 1

                    # Slow down vehicle on impact
                    self.vehicle.velocity[0] *= 0.5
                    self.vehicle.velocity[1] *= 0.5

            # --- ANIMAL ROADKILL LOGIC ---
            # Check collision with animals and KILL them
            animals_to_check = getattr(game, 'active_animals', [])
            for animal in list(animals_to_check):
                if vehicle_rect.colliderect(animal.rect):
                    self.vehicle.damage_motor(1.5)
                    damage_to_animal = 2

                    # Apply damage. take_damage returns True if health <= 0
                    if animal.take_damage(damage_to_animal, game):
                        # IMPORTANT: Must call die() to spawn corpse and remove from lists
                        animal.die(game)
                        if animal in game.items_on_ground:
                            game.items_on_ground.remove(animal)
                        if animal in game.active_animals:
                            game.active_animals.remove(animal)
                        display_message_player(f"Roadkill! Animal splattered.")

                    # Slow down vehicle on impact
                    self.vehicle.velocity[0] *= 0.5
                    self.vehicle.velocity[1] *= 0.5

            # --- NPC ROADKILL LOGIC ---
            if hasattr(game, 'npcs'):
                # Handle both List and SpriteGroup safely
                npcs_to_check = game.npcs.sprites() if hasattr(game.npcs, 'sprites') else game.npcs
                
                for npc in list(npcs_to_check):
                    if not npc.is_dead and vehicle_rect.colliderect(npc.rect):
                        self.vehicle.damage_motor(1.5)
                        damage_to_npc = 2
                        # Apply damage (attacker=self works because PlayerMovement is a Player mixin)
                        is_dead = npc.take_damage(damage_to_npc, game, attacker=self)
                        
                        # Slow down vehicle
                        self.vehicle.velocity[0] *= 0.5
                        self.vehicle.velocity[1] *= 0.5
                        
                        if is_dead:
                            # IMPORTANT: Must call die() for NPCs too
                            npc.die(game)
                            display_message_player(f"You ran over {npc.name}!")

            # Sync player position to vehicle
            self.x = self.vehicle.x
            self.y = self.vehicle.y
            self.rect.topleft = (int(self.x), int(self.y))
            
        else:
            # Standard Player Walking Movement (when not in vehicle)
            # [NEW] PIXEL PERFECT COLLISION LOGIC with "Push/Slow" mechanic
            
            def check_collision(rect_check):
                # 1. Check Tile Obstacles -> Returns 'tile' on hit
                for obstacle in obstacles:
                    if rect_check.colliderect(obstacle):
                        gx = obstacle.x // TILE_SIZE
                        gy = obstacle.y // TILE_SIZE
                        tile_def = game.map_manager.get_tile_at(gx, gy)
                        if tile_def and 'mask' in tile_def:
                            offset = (obstacle.x - rect_check.x, obstacle.y - rect_check.y)
                            if self.mask.overlap(tile_def['mask'], offset):
                                return 'tile'
                        else:
                            return 'tile'
                
                # 2. Check Zombies and NPCs -> Returns 'entity' on hit
                entities = zombies + (list(game.npcs) if hasattr(game.npcs, '__iter__') else [])
                for entity in entities:
                    if rect_check.colliderect(entity.rect):
                        if hasattr(entity, 'mask') and entity.mask:
                            offset = (entity.rect.x - rect_check.x, entity.rect.y - rect_check.y)
                            if self.mask.overlap(entity.mask, offset):
                                return 'entity'
                        else:
                            return 'entity'
                return None

            # Move X
            self.x += self.vx
            self.rect.x = round(self.x)
            
            col_type = check_collision(self.rect)
            if col_type == 'tile':
                 # Hard block for walls
                 self.x -= self.vx
                 self.rect.x = round(self.x)
            elif col_type == 'entity':
                 # Push/Slow effect: Revert 80% of movement to simulate moving slowly through crowd
                 self.x -= self.vx * 0.8
                 self.rect.x = round(self.x)

            # Move Y
            self.y += self.vy
            self.rect.y = round(self.y)

            col_type = check_collision(self.rect)
            if col_type == 'tile':
                 # Hard block for walls
                 self.y -= self.vy
                 self.rect.y = round(self.y)
            elif col_type == 'entity':
                 # Push/Slow effect: Revert 80% of movement
                 self.y -= self.vy * 0.8
                 self.rect.y = round(self.y)