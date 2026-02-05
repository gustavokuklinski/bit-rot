import math
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

            self.vehicle.move(move_x, move_y, obstacles)
            
            vehicle_rect = self.vehicle.rect
            for zombie in zombies[:]: 
                if vehicle_rect.colliderect(zombie.rect):
                    damage_to_zombie = 1000
                    zombie.take_damage(damage_to_zombie, game)
                    self.vehicle.velocity[0] *= 0.5
                    self.vehicle.velocity[1] *= 0.5

            self.x = self.vehicle.x
            self.y = self.vehicle.y
            self.rect.topleft = (int(self.x), int(self.y))
            
        else:
            self.x += self.vx
            self.rect.x = round(self.x)

            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    if self.vx > 0: self.rect.right = obstacle.left
                    elif self.vx < 0: self.rect.left = obstacle.right
                    self.x = self.rect.x

            self.y += self.vy
            self.rect.y = round(self.y)

            for obstacle in obstacles:
                if self.rect.colliderect(obstacle):
                    if self.vy > 0: self.rect.bottom = obstacle.top
                    elif self.vy < 0: self.rect.top = obstacle.bottom
                    self.y = self.rect.y