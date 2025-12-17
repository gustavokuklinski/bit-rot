import pygame
import math
import random
from core.data.config import TILE_SIZE
from core.entities.item.item import Item

class Vehicle:
    def __init__(self, name, x, y, width, height, image, stats, capacity=20, items=None):

        self.item_type = 'vehicle'
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.image = image
        self.rect = pygame.Rect(x, y, width, height)
        self.color = (0, 0, 255)
        
        self.capacity = capacity

        self.inventory = items if items is not None else []
       
        self.max_speed = float(stats.get('max_speed', 10))
        
        # Initial stats (will be overwritten by equipment items if they spawn)
        self.fuel = float(stats.get('fuel', 0.0))
        self.battery = float(stats.get('battery', 0.0))
        self.motor = float(stats.get('motor', 0.0))

        
        self.lights = stats.get('lights', 'off')
        if self.lights == '1.0': self.lights = 'off' 
        
        self.light_radius = float(stats.get('lights_radius', 4.0))
        
        self.car_state = "Off" 
        
        key_val = stats.get('key', 'false').strip()
        
        if key_val.lower() in ['false', 'none', '0', '']:
            self.required_key_id = None 
        else:
            self.required_key_id = key_val
        
        self.equipment = {
            'motor': None,
            'key': None,
            'fuel': None,
            'battery': None 
        }
        
        self.velocity = [0, 0]

        self.acceleration = 0.4
        self.friction = 0.4

        self.active = False 

        self.seat_count = int(stats.get('seats', 4))

        self.seats = [None] * self.seat_count

        self._spawn_random_equipment()
        
        self.generate_trunk_loot()
        
        self.update_stats_from_equipment()

    # ... [Keep existing current_speed_val and brake methods] ...
    @property
    def current_speed_val(self):
        return math.hypot(self.velocity[0], self.velocity[1])

    def brake(self, brake_force=0.9): 
        if not self.active: return
        self.velocity[0] *= (1 - brake_force)
        self.velocity[1] *= (1 - brake_force)
        if self.current_speed_val < 0.1:
            self.velocity = [0, 0]

    def _spawn_random_equipment(self):
        # 1. Spawn Key (30% chance, only if vehicle requires a key)
        if self.required_key_id and random.random() < 0.3:
            key_item = Item.create_from_name(self.required_key_id)
            if key_item:
                self.equipment['key'] = key_item
                # print(f"Spawned {self.name} with key: {key_item.name}")

        # 2. Spawn Fuel (50% chance)
        if random.random() < 0.5:
            fuel_item = Item.create_from_name("Car Fuel") 
            if fuel_item:
                if hasattr(fuel_item, 'capacity') and fuel_item.capacity:
                    fuel_item.load = random.uniform(1.0, float(fuel_item.capacity))
                self.equipment['fuel'] = fuel_item
        
        motor_item = Item.create_from_name("Car Engine")
        if motor_item:
            if hasattr(motor_item, 'durability'):
                 motor_item.durability = float(motor_item.durability)
            self.equipment['motor'] = motor_item

        # 3. Spawn Battery (50% chance)
        if random.random() < 0.5:
            batt_item = Item.create_from_name("Powerbank")
            if batt_item:
                if hasattr(batt_item, 'capacity') and batt_item.capacity:
                     if hasattr(batt_item, 'load'): 
                        batt_item.load = random.uniform(1.0, float(batt_item.capacity))
                     elif hasattr(batt_item, 'durability'): 
                        batt_item.durability = random.uniform(1.0, float(batt_item.max_durability))
                self.equipment['battery'] = batt_item

    def generate_trunk_loot(self):
        """Populates the trunk with random items based on a simple loot table logic."""
        # Simple loot table for cars
        possible_loot = []
        
        # Try to spawn 0 to 4 items
        num_items = random.randint(0, 4)
        
        for _ in range(num_items):
            if len(self.inventory) >= self.capacity:
                break
            
            for name, chance in possible_loot:
                if random.random() < chance:
                    item = Item.create_from_name(name)
                    if item:
                        self.inventory.append(item)
                    if len(self.inventory) >= self.capacity:
                        break
    
    @property
    def health(self):
        motor_pct = max(0.0, min(1.0, self.motor))
        batt_item = self.equipment.get('battery')
        max_batt = 100.0
        if batt_item:
            if hasattr(batt_item, 'max_durability') and batt_item.max_durability > 0:
                max_batt = float(batt_item.max_durability)
            elif hasattr(batt_item, 'capacity') and batt_item.capacity:
                max_batt = float(batt_item.capacity)
        
        battery_pct = max(0.0, min(1.0, self.battery / max_batt)) if max_batt > 0 else 0.0

        fuel_item = self.equipment.get('fuel')
        max_fuel = 25.0
        if fuel_item and hasattr(fuel_item, 'capacity') and fuel_item.capacity:
            max_fuel = float(fuel_item.capacity)
            
        fuel_pct = max(0.0, min(1.0, self.fuel / max_fuel)) if max_fuel > 0 else 0.0

        weighted_health = (motor_pct * 60) + (battery_pct * 30) + (fuel_pct * 10)
        return weighted_health

    def is_driveable(self):
        if self.motor <= 0: return False

        required_key = self.required_key_id
        if required_key and required_key.lower() != 'true':
            key_item = self.equipment.get('key')
            if not key_item or key_item.name != required_key:
                 return False
        
        fuel_item = self.equipment.get('fuel')
        if not fuel_item or (hasattr(fuel_item, 'load') and fuel_item.load <= 0):
            return False
            
        battery_item = self.equipment.get('battery')
        has_power = False
        if battery_item:
            if battery_item.durability is not None and battery_item.durability > 0:
                has_power = True
            elif hasattr(battery_item, 'load') and battery_item.load is not None and battery_item.load > 0:
                has_power = True
        
        if not has_power: return False
        return True

    def damage_motor(self, amount):
        motor_item = self.equipment.get('motor')
        if not motor_item:
            return 

        if hasattr(motor_item, 'load') and motor_item.load is not None:
             motor_item.load = max(0, motor_item.load - amount)
             print(f"Motor hit! Damage: {amount}. Remaining Status: {motor_item.load}/{motor_item.capacity}")
             
        elif hasattr(motor_item, 'durability') and motor_item.durability is not None:
             motor_item.durability = max(0, motor_item.durability - amount)
        
        self.update_stats_from_equipment()
        
        if self.motor <= 0:
            self.active = False
            self.car_state = "Off"
            print("Motor failed! Engine stopped.")

    def move(self, dx, dy, obstacles):
        if not self.active: return

        self.x += dx
        self.rect.x = int(self.x)
        collision_x = False
        for obstacle in obstacles:
            if obstacle is not self.rect and self.rect.colliderect(obstacle):
                if dx > 0: self.rect.right = obstacle.left
                elif dx < 0: self.rect.left = obstacle.right
                self.x = self.rect.x
                collision_x = True

        self.y += dy
        self.rect.y = int(self.y)
        collision_y = False
        for obstacle in obstacles:
            if obstacle is not self.rect and self.rect.colliderect(obstacle):
                if dy > 0: self.rect.bottom = obstacle.top
                elif dy < 0: self.rect.top = obstacle.bottom
                self.y = self.rect.y
                collision_y = True
        
        if collision_x or collision_y:
            current_speed = self.current_speed_val
            if current_speed > 2.0:
                damage = current_speed * 2.0 
                print(f"CRASH! Speed: {current_speed:.1f} | Damage: {damage:.1f}")
                self.damage_motor(damage)
                self.velocity = [0, 0]

    @property
    def current_light_radius(self):
        if self.lights != 'on': return 0
        if self.battery <= 0: return 0
        return self.light_radius * TILE_SIZE

    def toggle_lights(self):
        if self.lights == 'on':
            self.lights = 'off'
            # print(f"{self.name} lights turned OFF.")
        else:
            battery_item = self.equipment.get('battery')
            has_power = False
            if battery_item:
                if battery_item.durability is not None and battery_item.durability > 0:
                    has_power = True
                elif hasattr(battery_item, 'load') and battery_item.load is not None and battery_item.load > 0:
                    has_power = True
            
            if has_power:
                self.lights = 'on'
                # print(f"{self.name} lights turned ON.")
            else:
                print("Cannot turn on lights: No Battery Power.")

    def toggle_engine(self):
        driver_seat = self.seats[0]
        if not driver_seat or type(driver_seat).__name__ != 'Player':
            print("Cannot start engine: No driver in the driver's seat.")
            return

        if self.active:
            self.active = False
            self.car_state = "Off"
            print(f"{self.name} engine turned OFF.")
        else:
            has_key = self.equipment.get('key') is not None
            battery_item = self.equipment.get('battery')
            has_power = False
            if battery_item:
                if battery_item.durability is not None and battery_item.durability > 0:
                    has_power = True
                elif hasattr(battery_item, 'load') and battery_item.load is not None and battery_item.load > 0:
                    has_power = True

            fuel_item = self.equipment.get('fuel')
            has_fuel = fuel_item and (not hasattr(fuel_item, 'load') or fuel_item.load > 0)
            
            if has_key and has_power and has_fuel:
                self.active = True
                self.car_state = "On"
                print(f"{self.name} engine turned ON.")
            else:
                missing = []
                if not has_key: missing.append("Key")
                if not has_power: missing.append("Battery Power")
                if not has_fuel: missing.append("Fuel")
                print(f"Cannot start. Missing/Empty: {', '.join(missing)}")

    # ... [Keep existing can_equip, add_equipment, remove_equipment, update_stats_from_equipment, update, current_weight, max_weight, draw] ...
    def can_equip(self, item, slot):
        if slot not in self.equipment: return False

        if slot == 'key':
            if self.required_key_id:
                is_key_type = getattr(item, 'item_type', None) == 'car_key' or getattr(item, 'type', None) == 'car_key'
                if item.name == self.required_key_id and is_key_type: return True
                return False
            return False
            
        elif slot == 'fuel': return getattr(item, 'status_effect', None) == 'fuel'
            
        elif slot == 'battery':
            item_type = getattr(item, 'item_type', None)
            return item_type in ['battery', 'tool', 'utility'] and (hasattr(item, 'durability') or hasattr(item, 'load'))
        
        elif slot == 'motor':
            is_motor = getattr(item, 'item_type', None) == 'car_motor' or getattr(item, 'type', None) == 'car_motor'
            return is_motor or getattr(item, 'status', None) == 'motor'
            
        return False

    def add_equipment(self, item, slot):
        if not self.can_equip(item, slot):
            print(f"Cannot equip {item.name} in {slot} slot.")
            return False

        old_item = self.equipment.pop(slot, None)
        self.equipment[slot] = item
        self.update_stats_from_equipment()
        return old_item

    def remove_equipment(self, slot):
        if slot in self.equipment:
            item = self.equipment.pop(slot)
            self.update_stats_from_equipment()
            return item
        return None

    def update_stats_from_equipment(self):
        battery_item = self.equipment.get('battery')
        if battery_item:
            if hasattr(battery_item, 'durability') and battery_item.durability is not None:
                 self.battery = float(battery_item.durability)
            elif hasattr(battery_item, 'load') and battery_item.load is not None:
                 self.battery = float(battery_item.load)
            else:
                 self.battery = 0.0 
        else:
            self.battery = 0 
        
        fuel_item = self.equipment.get('fuel')
        if fuel_item:
            if hasattr(fuel_item, 'load') and fuel_item.load is not None:
                self.fuel = float(fuel_item.load)
            else:
                self.fuel = 0.0 
        else:
            self.fuel = 0
        
        motor_item = self.equipment.get('motor')
        if motor_item:
            current = 0.0
            maximum = 100.0
            if hasattr(motor_item, 'load') and motor_item.load is not None:
                current = float(motor_item.load)
                maximum = float(motor_item.capacity) if hasattr(motor_item, 'capacity') and motor_item.capacity else 100.0
            elif hasattr(motor_item, 'durability') and motor_item.durability is not None:
                current = float(motor_item.durability)
                maximum = float(motor_item.max_durability) if hasattr(motor_item, 'max_durability') else 100.0
            
            if maximum > 0:
                self.motor = max(0.0, min(1.0, current / maximum))
            else:
                self.motor = 0.0
        else:
            self.motor = 0.0

    def update(self, game_map=None):
        # Sync items again just in case (e.g. if damaged externally)
        self.update_stats_from_equipment()
        battery_item = self.equipment.get('battery')
        fuel_item = self.equipment.get('fuel')

        if self.active:
             fuel_drain = 0.0001 
             if self.fuel > 0:
                 self.fuel -= fuel_drain
                 if fuel_item and hasattr(fuel_item, 'load') and fuel_item.load is not None:
                     fuel_item.load = max(0, fuel_item.load - fuel_drain)
             else:
                 self.active = False
                 self.car_state = "Off"
                 print("Engine died (No Fuel).")

        if self.lights == 'on':
            drain_amount = 0.0005
            if self.battery > 0:
                self.battery -= drain_amount
                if battery_item:
                    if battery_item.durability is not None:
                        battery_item.durability = max(0, battery_item.durability - drain_amount)
                    elif hasattr(battery_item, 'load') and battery_item.load is not None:
                        battery_item.load = max(0, battery_item.load - drain_amount)
            else:
                self.battery = 0
                self.lights = 'off'
                if self.active:
                    self.active = False
                    self.car_state = "Off"
                    print("Engine died (No Battery).")

        has_key = self.equipment.get('key') is not None
        if not has_key and self.active:
             self.active = False
             self.car_state = "Off"
             print("Engine stopped (Key removed).")
             
        if not battery_item and self.active:
             self.active = False
             self.car_state = "Off"
             print("Engine stopped (Battery removed).")

    @property
    def current_weight(self):
        return sum(getattr(item, 'load', 1) for item in self.inventory)

    @property
    def max_weight(self):
        return self.capacity * 10
        
    def draw(self, surface, offset_x, offset_y):
        if self.image:
            surface.blit(self.image, (self.rect.x + offset_x, self.rect.y + offset_y))
        else:
            draw_rect = self.rect.move(offset_x, offset_y)
            pygame.draw.rect(surface, self.color, draw_rect)