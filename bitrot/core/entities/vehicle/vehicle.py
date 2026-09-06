import pygame
import math
import random
from core.data.config import *
from core.entities.item.item import Item
from core.entities.item.item_data import ITEM_TEMPLATES, load_item_templates_data
from core.entities.zombie.zombie import Zombie
from core.entities.npc.npc import NPC
from core.entities.vehicle.vehicle_data import VehicleData
from core.messages import display_message
from core.data.localization import tr

class Vehicle:
    def __init__(self, name, x, y, width, height, image, stats, capacity=20, items=None, loot_table=None, facing='right'):

        self.item_type = 'vehicle'
        self.name = name

        # Fetch stats directly from the definition if they are missing or empty (e.g., during load from save state)
        if not stats or 'seats' not in stats:
            if not VehicleData.VEHICLE_TEMPLATES: VehicleData.load_templates() # Auto-load safely
            definition = VehicleData.get_definition_by_name(name)
            if definition and 'stats' in definition:
                merged_stats = definition['stats'].copy()
                if stats:
                    merged_stats.update(stats)
                stats = merged_stats

        # [NEW] Dynamically map required tires from the XML stats
        self.required_tires = [k for k in stats.keys() if k.startswith('tire_')]
        if not self.required_tires:
            # Fallback for older saves without tire data
            self.required_tires = ['tire_front_left', 'tire_front_right', 'tire_back_left', 'tire_back_right']

        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        self.images = {}
        self.facing = facing # Default direction
        
        if isinstance(image, dict):
            self.images = image
        elif image:
            self.images['right'] = image
        
        self.rect = pygame.Rect(x, y, width, height)
        self.color = (0, 0, 255)
        
        self.capacity = capacity
        self.inventory = items if items is not None else []
        self.max_speed = float(stats.get('max_speed', 10))
        
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
        
        # [NEW] Initialize equipment with dynamic tires
        self.equipment = {
            'motor': None,
            'key': None,
            'fuel': None,
            'battery': None
        }
        for t_slot in self.required_tires:
            self.equipment[t_slot] = None
        
        self.velocity = [0, 0]
        self.acceleration = 0.4
        self.friction = 0.4
        self.active = False 

        try:
            self.seat_count = int(stats.get('seats', 4))
        except (ValueError, TypeError):
            self.seat_count = 4
            
        self.seats = [None] * self.seat_count

        self.hit_entities = []

        self._spawn_random_equipment()
        self.generate_trunk_loot(loot_table)
        self.update_stats_from_equipment()
        
        if self.image:
             self.mask = pygame.mask.from_surface(self.image)
        else:
             self.mask = pygame.mask.Mask((width, height))
             self.mask.fill()
        
        self.engine_channel = None
        self.sounds = {}
        
        # Load sound paths from definition
        if not VehicleData.VEHICLE_TEMPLATES: VehicleData.load_templates()
        definition = VehicleData.get_definition_by_name(name)
        if definition and 'sounds' in definition:
            self.sounds = definition['sounds']

    @property
    def image(self):
        if not self.images:
            if not VehicleData.VEHICLE_TEMPLATES: VehicleData.load_templates()
            definition = VehicleData.get_definition_by_name(self.name)
            if definition and definition.get('images'):
                self.images = definition['images']
        
        img = self.images.get(self.facing)
        if not img and self.images:
            img = next(iter(self.images.values()))
            
        if img:
            if self.width != img.get_width() or self.height != img.get_height():
                 self.width = img.get_width()
                 self.height = img.get_height()
                 self.rect.size = (self.width, self.height)
                 self.mask = pygame.mask.from_surface(img)
            return img
            
        return None

    @image.setter
    def image(self, value):
        if isinstance(value, dict):
            self.images = value
        else:
            self.images = {'right': value}
            self.facing = 'right'
            if value:
                self.mask = pygame.mask.from_surface(value)

    @property
    def current_speed_val(self):
        return math.hypot(self.velocity[0], self.velocity[1])

    def brake(self, brake_force=0.9, game=None): 
        if not self.active: return
        multiplier = game.dt_mult if game else 1.0
        scale = math.pow(brake_force, multiplier)
        
        self.velocity[0] *= scale
        self.velocity[1] *= scale
        
        if self.current_speed_val < 0.1:
            self.velocity = [0, 0]

    def _spawn_random_equipment(self):
        if self.required_key_id and random.random() < VEH_HAS_KEY:
            key_item = Item.create_from_name(self.required_key_id)
            if key_item:
                self.equipment['key'] = key_item

        if random.random() < VEH_HAS_FUEL:
            fuel_item = Item.create_from_name("Fuel Unit") 
            if fuel_item:
                if hasattr(fuel_item, 'capacity') and fuel_item.capacity:
                    fuel_item.load = random.uniform(1.0, float(fuel_item.capacity))
                self.equipment['fuel'] = fuel_item
        
        motor_item = Item.create_from_name("Car Engine")
        if motor_item:
            if hasattr(motor_item, 'durability'):
                 motor_item.durability = float(motor_item.durability)
            self.equipment['motor'] = motor_item

        if random.random() < VEH_HAS_BATTERY:
            batt_item = Item.create_from_name("Car Battery")
            if batt_item:
                if hasattr(batt_item, 'durability') and hasattr(batt_item, 'max_durability'):
                    batt_item.durability = random.uniform(1.0, float(batt_item.max_durability))
                elif hasattr(batt_item, 'capacity') and batt_item.capacity:
                     if hasattr(batt_item, 'load'): 
                        batt_item.load = random.uniform(1.0, float(batt_item.capacity))
                self.equipment['battery'] = batt_item

        # [NEW] Dynamic tire spawning
        for tire_slot in self.required_tires:
            if random.random() < VEH_HAS_TIRES:
                tire_item = Item.create_from_name("Car Tire")
                if tire_item:
                    if hasattr(tire_item, 'durability') and hasattr(tire_item, 'max_durability'):
                        tire_item.durability = random.uniform(20.0, float(tire_item.max_durability))
                    self.equipment[tire_slot] = tire_item

    def generate_trunk_loot(self, loot_table=None):
        if not loot_table: return
        if not ITEM_TEMPLATES: load_item_templates_data()
            
        for entry in loot_table:
            if len(self.inventory) >= self.capacity: break
            chance = entry.get('chance', 0)
            try: chance = float(chance)
            except (ValueError, TypeError): chance = 0.0
            
            if random.random() < chance:
                if 'type' in entry:
                    min_qty = entry.get('min', 1)
                    max_qty = entry.get('max', 1)
                    qty = random.randint(min_qty, max_qty)
                    matching_items = [n for n, d in ITEM_TEMPLATES.items() if d.get('type') == entry['type']]
                    if matching_items:
                        for _ in range(qty):
                            if len(self.inventory) >= self.capacity: break
                            chosen_name = random.choice(matching_items)
                            new_item = Item.create_from_name(chosen_name)
                            if new_item: self.inventory.append(new_item)
                elif 'item' in entry:
                    item_name = entry.get('item')
                    item = Item.create_from_name(item_name)
                    if item: self.inventory.append(item)

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
        
        # [NEW] Check if driveable based on having all required tires
        for t_slot in self.required_tires:
            tire = self.equipment.get(t_slot)
            if not tire or getattr(tire, 'durability', 0) <= 0:
                return False
                
        return True

    def damage_motor(self, amount):
        motor_item = self.equipment.get('motor')
        if not motor_item: return 

        if hasattr(motor_item, 'load') and motor_item.load is not None:
             motor_item.load = max(0, motor_item.load - amount)
             if motor_item.load <= 0:
                 print(f"Motor hit! Damage: {amount}. Remaining Status: {motor_item.load}/{motor_item.capacity}")
             
        elif hasattr(motor_item, 'durability') and motor_item.durability is not None:
             motor_item.durability = max(0, motor_item.durability - amount)
        
        self.update_stats_from_equipment()
        
        if self.motor <= 0:
            self.active = False
            self.car_state = "Off"
            print("Motor failed! Engine stopped.")

    def move(self, dx, dy, obstacles, game=None):
        if not self.active: return

        if abs(dx) > abs(dy):
            if dx > 0: self.facing = 'right'
            elif dx < 0: self.facing = 'left'
        elif abs(dy) > abs(dx):
            if dy > 0: self.facing = 'down'
            elif dy < 0: self.facing = 'top'

        dist = math.hypot(dx, dy)
        if dist > 0:
            tire_degradation = dist * 0.0005 
            broken_tire = False
            # [NEW] Degrade dynamic tires
            for tire_slot in self.required_tires:
                tire = self.equipment.get(tire_slot)
                if tire and hasattr(tire, 'durability'):
                    tire.durability -= tire_degradation
                    if tire.durability <= 0:
                        tire.durability = 0
                        broken_tire = True
            
            if broken_tire:
                display_message(tr('msg', "A tire has broken!"))
                self.velocity = [0, 0]
                self.active = False
                self.car_state = "Off"
                return 
        
        def check_collision(rect_check):
            for obstacle in obstacles:
                if rect_check.colliderect(obstacle):
                    if game:
                        gx = obstacle.x // TILE_SIZE
                        gy = obstacle.y // TILE_SIZE
                        tile_def = game.map_manager.get_tile_at(gx, gy)
                        if tile_def and 'mask' in tile_def:
                            offset = (obstacle.x - rect_check.x, obstacle.y - rect_check.y)
                            if self.mask.overlap(tile_def['mask'], offset):
                                return True, obstacle
                        else:
                            return True, obstacle
                    else:
                        return True, obstacle

            if game:
                entities = game.zombies + (list(game.npcs) if hasattr(game.npcs, '__iter__') else []) + [game.player]
                for entity in entities:
                    if entity == self: continue 
                    if entity in self.seats: continue 
                    
                    if rect_check.colliderect(entity.rect):
                        if hasattr(entity, 'mask') and entity.mask:
                             offset = (entity.rect.x - rect_check.x, entity.rect.y - rect_check.y)
                             if self.mask.overlap(entity.mask, offset):
                                 return True, entity
                        else:
                             return True, entity
            return False, None

        self.x += dx
        self.rect.x = int(self.x)
        collision, collider = check_collision(self.rect)
        
        if collision:
            is_entity = False
            if hasattr(collider, 'take_damage') or hasattr(collider, 'health') or type(collider).__name__ in ['Zombie', 'NPC', 'Player']:
                is_entity = True
            
            if is_entity:
                self.damage_motor(1.0)
                if collider not in self.hit_entities:
                    self.hit_entities.append(collider)
            else:
                if dx > 0: self.rect.right = collider.left
                elif dx < 0: self.rect.left = collider.right
                self.x = self.rect.x

        self.y += dy
        self.rect.y = int(self.y)
        collision, collider = check_collision(self.rect)
        
        if collision:
            is_entity = False
            if hasattr(collider, 'take_damage') or hasattr(collider, 'health') or type(collider).__name__ in ['Zombie', 'NPC', 'Player']:
                is_entity = True

            if is_entity:
                self.damage_motor(1.0)
                if collider not in self.hit_entities:
                     if collider not in self.hit_entities: 
                        self.hit_entities.append(collider)
            else:
                if dy > 0: self.rect.bottom = collider.top
                elif dy < 0: self.rect.top = collider.bottom
                self.y = self.rect.y
        
        if collision and not is_entity:
             current_speed = self.current_speed_val
             if current_speed > 2.0:
                 damage = current_speed * 0.5
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
            else:
                display_message(tr('msg', "Cannot turn on lights: No Battery Power."))

    def toggle_engine(self, game=None):
        driver_seat = self.seats[0]
        if not driver_seat or type(driver_seat).__name__ != 'Player':
            display_message("Cannot start engine: No driver in the driver's seat.")
            return

        if game is None and hasattr(driver_seat, 'game'):
            game = driver_seat.game

        if self.active:
            self.active = False
            self.car_state = "Off"

            if self.engine_channel:
                self.engine_channel.stop()
                self.engine_channel = None

            display_message(f"{self.name} {tr('msg', 'engine turned OFF.')}")
            
            if getattr(self, '_auto_key_inserted', False) and self.equipment.get('key'):
                key_item = self.equipment.get('key')
                target_list = getattr(self, '_auto_key_container', driver_seat.inventory)
                self.remove_equipment('key')
                self._auto_key_inserted = False
                self._auto_key_container = None
                
                returned = False
                if isinstance(target_list, list):
                    if target_list is driver_seat.belt:
                        for i in range(len(driver_seat.belt)):
                            if driver_seat.belt[i] is None:
                                driver_seat.belt[i] = key_item
                                returned = True
                                break
                    elif target_list is driver_seat.inventory:
                        if len(driver_seat.inventory) < driver_seat.get_total_inventory_slots():
                            driver_seat.inventory.append(key_item)
                            if hasattr(driver_seat, 'stack_item_in_inventory'):
                                driver_seat.stack_item_in_inventory(key_item)
                            returned = True
                    else:
                        target_list.append(key_item) 
                        returned = True
                        
                if not returned:
                    if len(driver_seat.inventory) < driver_seat.get_total_inventory_slots():
                        driver_seat.inventory.append(key_item)
                        if hasattr(driver_seat, 'stack_item_in_inventory'):
                            driver_seat.stack_item_in_inventory(key_item)
                    else:
                        key_item.rect.center = driver_seat.rect.center
                        if hasattr(driver_seat, 'game') and hasattr(driver_seat.game, 'items_on_ground'):
                            driver_seat.game.items_on_ground.append(key_item)
        else:
            has_key = self.equipment.get('key') is not None
            
            if not has_key:
                def recursive_search_key(item_list):
                    for i, it in enumerate(item_list):
                        if not it: continue
                        if self.can_equip(it, 'key'):
                            return it, item_list, i
                        if hasattr(it, 'inventory') and it.inventory:
                            found, src_list, idx = recursive_search_key(it.inventory)
                            if found: return found, src_list, idx
                    return None, None, -1
                    
                found_key = None
                src_list = None
                idx = -1
                
                found_key, src_list, idx = recursive_search_key(driver_seat.belt)
                if not found_key:
                    found_key, src_list, idx = recursive_search_key(driver_seat.inventory)
                if not found_key:
                    for k, v in driver_seat.clothes.items():
                        if not v: continue
                        if self.can_equip(v, 'key'):
                            found_key, src_list, idx = v, driver_seat.clothes, k
                            break
                        if hasattr(v, 'inventory') and v.inventory:
                            found_key, src_list, idx = recursive_search_key(v.inventory)
                            if found_key: break
                            
                if found_key:
                    if src_list == driver_seat.belt:
                        driver_seat.belt[idx] = None
                    elif src_list == driver_seat.clothes:
                        driver_seat.clothes[idx] = None
                    else:
                        src_list.pop(idx)
                        
                    self.equipment['key'] = found_key
                    self.update_stats_from_equipment()
                    self._auto_key_inserted = True
                    self._auto_key_container = src_list
                    has_key = True

            battery_item = self.equipment.get('battery')
            has_power = False
            if battery_item:
                if battery_item.durability is not None and battery_item.durability > 0:
                    has_power = True
                elif hasattr(battery_item, 'load') and battery_item.load is not None and battery_item.load > 0:
                    has_power = True

            fuel_item = self.equipment.get('fuel')
            has_fuel = fuel_item and (not hasattr(fuel_item, 'load') or fuel_item.load > 0)
            
            # [NEW] Check required tires explicitly to block engine ignition
            missing_tires = []
            for t_slot in self.required_tires:
                tire = self.equipment.get(t_slot)
                if not tire or getattr(tire, 'durability', 0) <= 0:
                    missing_tires.append(t_slot)
            has_all_tires = len(missing_tires) == 0

            if has_key and has_power and has_fuel and has_all_tires:
                self.active = True
                self.car_state = "On"

                if game and 'on' in self.sounds:
                    game.sound_manager.play_sound(
                        self.sounds['on'], 
                        subdir='vehicles', 
                        game=game, 
                        source_pos=self.rect.center, # <--- Spatial
                        base_volume=0.5,             # <--- Lowered
                        is_critical=True
                    )

                print(f"{self.name} engine turned ON.")
            else:
                if game and 'fail' in self.sounds:
                    game.sound_manager.play_sound(
                        self.sounds['fail'], 
                        subdir='vehicles', 
                        game=game, 
                        source_pos=self.rect.center, # <--- Spatial
                        base_volume=0.5,             # <--- Lowered
                        is_critical=True
                    )

                missing = []
                if not has_key: missing.append("Key")
                if not has_power: missing.append("Battery Power")
                if not has_fuel: missing.append("Fuel")
                if not has_all_tires: missing.append("Tires")
                display_message(f"{tr('msg', 'Cannot start. Missing/Empty:')} {', '.join(missing)}")

    def can_equip(self, item, slot):
        if slot not in self.equipment: return False

        if slot == 'key':
            if not self.required_key_id:
                item_key_id = getattr(item, 'key_id', getattr(item, 'key', None))
                if item_key_id and str(item_key_id).strip().lower() == self.name.lower():
                    self.required_key_id = str(item_key_id).strip()
                else:
                    return False

            item_type = getattr(item, 'item_type', getattr(item, 'type', None))
            if item_type != 'car_key': return False

            required_val = str(self.required_key_id).strip().lower()
            item_name = getattr(item, 'name', '').strip().lower()
            item_key_id = getattr(item, 'key_id', '')
            if item_key_id: item_key_id = str(item_key_id).strip().lower()

            return (item_name == required_val) or (item_key_id and item_key_id == required_val)
            
        elif slot == 'fuel': 
            return getattr(item, 'status_effect', None) == 'fuel' or getattr(item, 'name', '') == 'Fuel Unit'
            
        elif slot == 'battery':
            item_type = getattr(item, 'item_type', getattr(item, 'type', None))
            return item_type == 'car_battery' or getattr(item, 'name', '') == 'Car Battery'
        
        elif slot == 'motor':
            item_type = getattr(item, 'item_type', getattr(item, 'type', None))
            return item_type == 'car_motor' or getattr(item, 'name', '') == 'Car Engine' or getattr(item, 'status', None) == 'motor'
        
        # [NEW] Dynamic tire checks
        elif slot in self.required_tires:
            item_type = getattr(item, 'item_type', getattr(item, 'type', None))
            return item_type == 'car_tire' or getattr(item, 'name', '') == 'Car Tire'

        return False

    def add_equipment(self, item, slot):
        if not self.can_equip(item, slot):
            display_message(f"{tr('msg', 'Cannot equip')} {tr('item', item.name)} {tr('msg', 'in')} {slot} {tr('msg', 'slot.')}")
            return False

        old_item = self.equipment.get(slot)
        self.equipment[slot] = item
        self.update_stats_from_equipment()
        return old_item

    def remove_equipment(self, slot):
        if slot in self.equipment:
            item = self.equipment[slot]
            self.equipment[slot] = None 
            self.update_stats_from_equipment()
            return item
        return None

    def update_stats_from_equipment(self):
        # --- Battery Check ---
        battery_item = self.equipment.get('battery')
        if battery_item:
            # Prioritize durability as per your XML
            if hasattr(battery_item, 'durability') and battery_item.durability is not None:
                 self.battery = float(battery_item.durability)
            elif hasattr(battery_item, 'load') and battery_item.load is not None:
                 self.battery = float(battery_item.load)
            else: self.battery = 0.0 
        else: self.battery = 0 
        
        # --- Fuel Check ---
        fuel_item = self.equipment.get('fuel')
        if fuel_item:
            if hasattr(fuel_item, 'load') and fuel_item.load is not None: self.fuel = float(fuel_item.load)
            else: self.fuel = 0.0 
        else: self.fuel = 0
        
        # --- Motor Check ---
        motor_item = self.equipment.get('motor')
        if motor_item:
            current = 0.0
            maximum = 100.0
            # Check durability first as per your XML
            if hasattr(motor_item, 'durability') and motor_item.durability is not None:
                current = float(motor_item.durability)
                maximum = float(getattr(motor_item, 'max_durability', 100.0))
            elif hasattr(motor_item, 'load') and motor_item.load is not None:
                current = float(motor_item.load)
                maximum = float(getattr(motor_item, 'capacity', 100.0))
            
            if maximum > 0: self.motor = max(0.0, min(1.0, current / maximum))
            else: self.motor = 0.0
        else: self.motor = 0.0

    def update(self, game=None, game_map=None, dt_mult=1.0):
        self.update_stats_from_equipment()
        battery_item = self.equipment.get('battery')
        fuel_item = self.equipment.get('fuel')

        if self.active:
            # 1. Fuel Drain
            fuel_drain = 0.0001 * dt_mult
            if self.fuel > 0:
                self.fuel -= fuel_drain
                if fuel_item and hasattr(fuel_item, 'load') and fuel_item.load is not None:
                    fuel_item.load = max(0, fuel_item.load - fuel_drain)
            else:
                self.active = False
                self.car_state = "Off"
                display_message(tr('msg', "Engine died (No Fuel)."))
                return # Exit early if engine stopped

            # 2. STRICT BATTERY CHECK
            # If the battery is removed or durability hits 0, the electrical system fails
            if self.battery <= 0:
                self.active = False
                self.car_state = "Off"
                display_message(tr('msg', "Engine stopped (Battery Dead/Missing)."))
                return

            # 3. STRICT ENGINE (MOTOR) CHECK
            # If the motor durability is 0 or it's removed, the car stops
            if self.motor <= 0:
                self.active = False
                self.car_state = "Off"
                display_message(tr('msg', "Engine failed (Motor Destroyed/Missing)."))
                return

            # 4. STRICT TIRE CHECK
            # Ensure all required tires are present and have durability > 0
            for t_slot in self.required_tires:
                tire = self.equipment.get(t_slot)
                if not tire or getattr(tire, 'durability', 0) <= 0:
                    self.active = False
                    self.car_state = "Off"
                    display_message(tr('msg', f"Engine stopped ({t_slot.replace('_', ' ')} Broken/Missing)."))
                    return

             # --- FIXED ENGINE SOUND LOGIC ---
            if game:
                current_speed = self.current_speed_val
                VEHICLE_BASE_VOL = 0.4 # <--- Global lower volume for engine loops
                
                if current_speed < 0.5:
                    # IDLE SOUND
                    if 'idle' in self.sounds:
                        if not self.engine_channel or not self.engine_channel.get_busy():
                            self.engine_channel = game.sound_manager.play_sound(
                                self.sounds['idle'], 
                                subdir='vehicles', 
                                game=game, 
                                source_pos=self.rect.center,
                                base_volume=VEHICLE_BASE_VOL, 
                                loops=-1
                            )
                else:
                    # MOVING SOUND
                    if 'moving' in self.sounds:
                        pitch_factor = 1.0 + (min(current_speed / self.max_speed, 1.0) * 0.5)
                        pitch_factor = round(pitch_factor * 20) / 20.0
                        
                        base_sound_key = f"vehicles/{self.sounds['moving']}"
                        if base_sound_key not in game.sound_manager.sounds:
                            game.sound_manager.load_sound(base_sound_key, os.path.join('vehicles', self.sounds['moving']))

                        base_sound = game.sound_manager.sounds.get(base_sound_key)
                        pitched_sound = game.sound_manager.get_pitched_sound(base_sound_key, base_sound, pitch_factor)

                        if not self.engine_channel or self.engine_channel.get_sound() != pitched_sound:
                            if self.engine_channel:
                                self.engine_channel.stop()
                            
                            self.engine_channel = game.sound_manager.play_sound(
                                self.sounds['moving'], 
                                subdir='vehicles', 
                                game=game, 
                                source_pos=self.rect.center,
                                base_volume=VEHICLE_BASE_VOL, 
                                loops=-1
                            )
                            if self.engine_channel:
                                self.engine_channel.play(pitched_sound, loops=-1)

                # --- CRITICAL: Update volume/panning every frame as vehicle moves ---
                if self.engine_channel:
                    game.sound_manager.update_spatial_volume(
                        self.engine_channel, 
                        self.rect.center, 
                        game, 
                        base_volume=VEHICLE_BASE_VOL, 
                        subdir='vehicles'
                    )

        # If engine dies, stop the sound
        if not self.active and self.engine_channel:
            self.engine_channel.stop()
            self.engine_channel = None

            fuel_drain = 0.0001 * dt_mult
            if self.fuel > 0:
                self.fuel -= fuel_drain
                if fuel_item and hasattr(fuel_item, 'load') and fuel_item.load is not None:
                    fuel_item.load = max(0, fuel_item.load - fuel_drain)
            else:
                self.active = False
                self.car_state = "Off"
                display_message(tr('msg', "Engine died (No Fuel)."))

            # [NEW] Turn off engine immediately if a tire goes missing or breaks while active
            for t_slot in self.required_tires:
                tire = self.equipment.get(t_slot)
                if not tire or getattr(tire, 'durability', 0) <= 0:
                    self.active = False
                    self.car_state = "Off"
                    display_message(tr('msg', "Engine stopped (Missing Tire)."))
                    break

        if self.lights == 'on':
            drain_amount = 0.0005 * dt_mult
            if self.battery > 0:
                self.battery -= drain_amount
                if battery_item:
                    if hasattr(battery_item, 'durability') and battery_item.durability is not None:
                        battery_item.durability = max(0, battery_item.durability - drain_amount)
                    elif hasattr(battery_item, 'load') and battery_item.load is not None:
                        battery_item.load = max(0, battery_item.load - drain_amount)
            else:
                self.battery = 0
                self.lights = 'off'
                if self.active:
                    self.active = False
                    self.car_state = "Off"
                    display_message(tr('msg', "Engine died (No Battery)."))

        has_key = self.equipment.get('key') is not None
        if not has_key and self.active:
             self.active = False
             self.car_state = "Off"
             display_message(tr('msg', "Engine stopped (Key removed)."))
             
        if not battery_item and self.active:
             self.active = False
             self.car_state = "Off"
             display_message(tr('msg', "Engine stopped (Battery removed)."))

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