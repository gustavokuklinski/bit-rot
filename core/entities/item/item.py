import os
import random
import xml.etree.ElementTree as ET
import pygame
import uuid

from core.data.config import *
import core.data.config

ITEM_TEMPLATES = {}  # loaded templates
SPRITE_CACHE = {}    # [NEW] Optimization: Cache loaded images to reduce disk I/O

class Item:
    """Base class for all in-game items."""
    def __init__(self, name, item_type, durability=None, load=None, capacity=None, color=WHITE, ammo_type=None, pellets=1, spread_angle=0, sprite_file=None, min_damage=None, max_damage=None, min_restore=None, max_restore=None, slot=None, defence=None, speed=None, state=None, min_light=None, max_light=None, fuel_type=None, text=None, attribute_modifiers=None, min_reduce=None, max_reduce=None, sounds=None, status_effect=None, effects=None, repair_list=None, knockback=None, machine_gun=False, firing_second=0.0, allow_sleep=False):

        self.name = name
        self.item_type = item_type  # 'consumable', 'weapon', 'tool', 'backpack', ...
        self.id = str(uuid.uuid4())
        self.durability = durability
        self.load = load
        self.capacity = capacity
        self.ammo_type = ammo_type
        self.pellets = pellets
        self.spread_angle = spread_angle
        self.image = self.load_sprite(sprite_file)
        self.rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        
        self.x = 0
        self.y = 0

        # if self.item_type in ['backpack', 'container']:
        self.inventory = []

        self.color = color
        self.min_damage = min_damage
        self.max_damage = max_damage
        self.min_restore = min_restore
        self.max_restore = max_restore

        self.min_reduce = min_reduce
        self.max_reduce = max_reduce

        self.slot = slot       # e.g., "head", "torso"
        self.defence = defence # e.g., 0.0
        self.speed = speed     # e.g., 0.0

        self.state = state          # e.g., "on", "off"
        self.min_light = min_light  # e.g., 0
        self.max_light = max_light  # e.g., 15 (in tiles)
        self.fuel_type = fuel_type  # e.g., "Matches"

        self.text = text
        self.attribute_modifiers = attribute_modifiers if attribute_modifiers is not None else {} 
        self.sounds = sounds if sounds is not None else {}

        self.status_effect = status_effect
        self.effects = effects if effects is not None else []
        self.repair_list = repair_list if repair_list is not None else []
        self.knockback = knockback
        self.machine_gun = machine_gun
        self.firing_second = firing_second

        self.allow_sleep = allow_sleep


    def to_dict(self):
        """Serializes the item's dynamic state to a dictionary."""
        data = {
            'name': self.name,
            'durability': self.durability,
            'load': self.load,
            'state': self.state,
            # Recursively save inventory items (e.g. for backpacks)
            'inventory': [i.to_dict() for i in self.inventory] if self.inventory else []
        }
        return data

    @staticmethod
    def from_dict(data):
        """Creates an item from a dictionary, restoring its state."""
        if not data or 'name' not in data: return None
        
        # 1. Create a fresh instance from the template to get static stats (damage, sprite, etc.)
        item = Item.create_from_name(data['name'])
        if not item: return None
        
        # 2. Overwrite dynamic properties with saved data
        if 'durability' in data: item.durability = data['durability']
        if 'load' in data: item.load = data['load']
        if 'state' in data: item.state = data['state']
        
        # 3. Recursively restore inventory
        if 'inventory' in data and data['inventory']:
            item.inventory = [Item.from_dict(i_data) for i_data in data['inventory'] if i_data]
            
        return item


    @property
    def damage(self):
        if self.min_damage is not None and self.max_damage is not None:
            base_damage = random.randint(self.min_damage, self.max_damage)
            if self.durability is not None:
                template = ITEM_TEMPLATES.get(self.name)
                if template:
                    props = template.get('properties', {})
                    if 'durability' in props and 'max' in props['durability']:
                        max_durability = float(props['durability']['max'])
                        if max_durability > 0:
                            durability_percentage = self.durability / max_durability
                            return int(base_damage * durability_percentage)
            return base_damage
        return 0

    @property
    def max_durability(self):
        """Gets the max durability from the item's template."""
        template = ITEM_TEMPLATES.get(self.name)
        if template:
            props = template.get('properties', {})
            if 'durability' in props and 'max' in props['durability']:
                # Apply multipliers just like in create_from_name
                max_dur = float(props['durability']['max'])
                multiplier = core.data.config.DURABILITY_MULTIPLIER
                if template['type'] == 'weapon_melee':
                    multiplier *= core.data.config.WEAPON_MELEE_DURABILITY_MULTIPLIER
                elif template['type'] == 'weapon_ranged':
                    multiplier *= core.data.config.WEAPON_RANGED_DURABILITY_MULTIPLIER
                elif template['type'] == 'tool':
                    multiplier *= core.data.config.TOOL_DURABILITY_MULTIPLIER
                elif template['type'] == 'cloth':
                    multiplier *= core.data.config.CLOTH_DURABILITY_MULTIPLIER
                
                return max_dur * multiplier
                
        return self.durability or 100 # Fallback
        
    @property
    def current_light_radius(self):
        """Calculates the current light radius based on durability."""
        if self.state != 'on' or self.min_light is None or self.max_light is None:
            return 0
        
        max_dur = self.max_durability
        if max_dur <= 0 or self.durability is None:
            return self.min_light
            
        # Light scales with durability
        dur_percent = max(0, min(1, self.durability / max_dur))
        
        # Lerp
        light_range = self.max_light - self.min_light
        return (self.min_light + (light_range * dur_percent)) * TILE_SIZE

    def is_stackable(self):
        """Returns True if the item uses 'load' as a quantity."""
        # Items are stackable if they have a 'capacity' defined for stacking
        return (self.capacity is not None and self.capacity > 1 and 
                self.durability is None and self.item_type in ['consumable','currency','car_fuel','consumable_repair','consumable_medication','consumable_drink','consumable_ammo','consumable_food', 'utility'])

    def can_stack_with(self, other_item):
        """Checks if this item can be stacked with another."""
        if not self.is_stackable() or not other_item.is_stackable():
            return False
        # Stacking requires same name and (for safety) same item type
        # We also check that durability is None, as stackable items shouldn't have it
        return (self.name == other_item.name and 
                self.item_type == other_item.item_type and
                self.durability is None)

    @property
    def current_damage_range(self):
        if self.min_damage is not None and self.max_damage is not None:
            if self.durability is not None:
                template = ITEM_TEMPLATES.get(self.name)
                if template:
                    props = template.get('properties', {})
                    if 'durability' in props and 'max' in props['durability']:
                        max_durability = float(props['durability']['max'])
                        if max_durability > 0:
                            durability_percentage = self.durability / max_durability
                            min_damage = int(self.min_damage * durability_percentage)
                            max_damage = int(self.max_damage * durability_percentage)
                            return (min_damage, max_damage)
            return (self.min_damage, self.max_damage)
        return (0, 0)

    def __repr__(self):
        parts = [self.name]
        if self.durability is not None:
            parts.append(f"Dur:{self.durability:.0f}")
        if self.load is not None:
            parts.append(f"Load:{self.load:.0f}")
        return "(" + ", ".join(parts) + ")"

    def load_sprite(self, sprite_file):
        if not sprite_file:
            return None
        
        # Check Cache First
        if sprite_file in SPRITE_CACHE:
            return SPRITE_CACHE[sprite_file]

        try:
            if sprite_file.startswith("./game/"):
                path = sprite_file
            else:
                #path = SPRITE_PATH + "items/" + sprite_file
                if self.item_type == 'cloth':
                    path = SPRITE_PATH + "clothes/" + sprite_file
                else:
                    path = SPRITE_PATH + "items/" + sprite_file
            
            image = pygame.image.load(path).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
            
            # [NEW] Store in Cache
            SPRITE_CACHE[sprite_file] = image
            return image
        except pygame.error as e:
            print(f"Warning: Could not load sprite '{sprite_file}': {e}")
            return None

    @staticmethod
    def load_item_templates(items_dir=DATA_PATH + 'items/'):
        """Loads item templates from XML files in the game/data/items directory."""
        global ITEM_TEMPLATES
        if ITEM_TEMPLATES:
            return
        if not os.path.isdir(items_dir):
            print(f"Warning: Item templates directory not found at '{items_dir}'")
            return
        for filename in os.listdir(items_dir):
            if not filename.endswith('.xml'):
                continue
            tree = ET.parse(f"{items_dir}/{filename}")
            root = tree.getroot()
            name = root.attrib.get('name')
            ttype = root.attrib.get('type')

            state = root.attrib.get('state')
            template = {'type': ttype, 'properties': {}, 'state': state}

            props_node = root.find('properties')
            if props_node is not None:
                for prop in props_node:
                    template['properties'][prop.tag] = {k: v for k, v in prop.attrib.items()}
                
                text_node = props_node.find('text')
                if text_node is not None:
                    # Clean up indentation from XML text
                    template['text'] = "\n".join(line.strip() for line in text_node.text.strip().split('\n'))
                else:
                    template['text'] = None

                template['effects'] = []

                # Helper to parse "[a, b]" string into list
                def parse_status_list(s):
                    if not s: return []
                    return [t.strip() for t in s.replace('[', '').replace(']', '').split(',')]

                # Capture global status for backward compatibility
                global_status = None
                status_node = props_node.find('status')
                if status_node is not None:
                    global_status = status_node.get('value')
                    template['properties']['status'] = {'value': global_status}

                # Parse Restore effects
                for node in props_node.findall('restore'):
                    status_str = node.get('status')
                    targets = parse_status_list(status_str) if status_str else ([global_status] if global_status else [])
                    
                    if targets:
                        template['effects'].append({
                            'type': 'restore',
                            'targets': targets,
                            'min': int(node.get('min', '0')),
                            'max': int(node.get('max', '0'))
                        })
                    
                    # Keep legacy props for safety
                    if not status_str and global_status:
                         template['properties']['restore'] = {
                            'min': node.get('min', '0'),
                            'max': node.get('max', '0')
                        }

                # Parse Reduce effects
                for node in props_node.findall('reduce'):
                    status_str = node.get('status')
                    targets = parse_status_list(status_str) if status_str else ([global_status] if global_status else [])
                    
                    if targets:
                        template['effects'].append({
                            'type': 'reduce',
                            'targets': targets,
                            'min': int(node.get('min', '0')),
                            'max': int(node.get('max', '0'))
                        })
                    
                    # Keep legacy props for safety
                    if not status_str and global_status:
                         template['properties']['reduce'] = {
                            'min': node.get('min', '0'),
                            'max': node.get('max', '0')
                        }
                    
            spawn_node = root.find('spawn')

            if spawn_node is not None:
                template['spawn_chance'] = float(spawn_node.attrib.get('chance', '0'))
            

            repair_node = root.find('repair')
            if repair_node is not None:
                template['repair_list'] = []
                for repair_item in repair_node.findall('item'):
                    template['repair_list'].append(repair_item.get('name'))


            template['stats'] = None
            if ttype == 'charm':
                template['attribute_modifiers'] = {}
                attr_node = root.find('attributes')
                if attr_node is not None:
                    for attr in attr_node:
                        # attr.tag will be "lucky", "strength", etc.
                        # attr.get('value') will be "0.5", "1.0", etc.
                        template['attribute_modifiers'][attr.tag] = float(attr.get('value', 0))


            loot_node = root.find('loot')
            if loot_node is not None:
                template['loot'] = []
                for loot_item_node in loot_node.findall('item'):
                    loot_item_name = loot_item_node.attrib.get('name')
                    loot_item_chance = float(loot_item_node.attrib.get('chance', '1.0'))
                    template['loot'].append({'name': loot_item_name, 'chance': loot_item_chance})
            
            template['sounds'] = {}
            sound_node = root.find('sound')
            if sound_node is not None:
                # Weapons sound
                shoot_node = sound_node.find('shoot')
                if shoot_node is not None:
                    template['sounds']['shoot'] = shoot_node.get('src')
                
                reload_node = sound_node.find('reload')
                if reload_node is not None:
                    template['sounds']['reload'] = reload_node.get('src')
                
                noammo_node = sound_node.find('noammo')
                if noammo_node is not None:
                    template['sounds']['noammo'] = noammo_node.get('src')
                
                # Melee Weapon Sound
                swing_node = sound_node.find('swing') # For melee
                if swing_node is not None:
                    template['sounds']['swing'] = swing_node.get('src')


            ITEM_TEMPLATES[name] = template

        clothes_dir = DATA_PATH + 'clothes/'
        print(f"Loading clothes templates from: {clothes_dir}")
        if not os.path.isdir(clothes_dir):
            print(f"Warning: Clothes templates directory not found at '{clothes_dir}'")
        else:
            for filename in os.listdir(clothes_dir):
                if not filename.endswith('.xml'):
                    continue
                try:
                    tree = ET.parse(f"{clothes_dir}/{filename}")
                    root = tree.getroot()
                    if root.tag != 'cloth': continue # Skip if not <cloth>
                    
                    name = root.attrib.get('name')
                    if not name: continue
                    
                    # Create a template that *mimics* an item template
                    template = {
                        'type': root.attrib.get('type'), # "cloth"
                        'properties': {}
                    }
                    
                    builder_str = root.attrib.get('builder', 'false')
                    template['builder'] = (builder_str.lower() == 'true')

                    # Store the slot ID (e.g., "head")
                    template['properties']['slot'] = {'value': root.attrib.get('id')}
                    
                    props_node = root.find('properties')
                    if props_node is not None:
                        # Map <defence> to item template format
                        def_node = props_node.find('defence')
                        if def_node is not None:
                            template['properties']['defence'] = {'value': def_node.attrib.get('value', '0')}

                        # Map <speed> (if you add it) to item template format
                        spd_node = props_node.find('speed')
                        if spd_node is not None:
                            template['properties']['speed'] = {'value': spd_node.attrib.get('value', '0')}

                        # Map <capacity> to item template format
                        cap_node = props_node.find('capacity')
                        if cap_node is not None:
                            template['properties']['capacity'] = {'value': cap_node.attrib.get('value', '0')}

                        # Map <sprite> to item template format
                        spr_node = props_node.find('sprite')
                        if spr_node is not None:
                            template['properties']['sprite'] = {'file': spr_node.attrib.get('file')}
                    
                    # Add this new "cloth-item" to the main template list
                    if name in ITEM_TEMPLATES:
                        print(f"Warning: Duplicate item/cloth name '{name}'")
                    ITEM_TEMPLATES[name] = template

                except Exception as e:
                    print(f"Error parsing cloth {filename}: {e}")
        
        print(f"Loaded {len(ITEM_TEMPLATES)} total item/cloth templates.")


    @staticmethod
    def generate_random():
        """Generates a random item based on spawn chances in templates."""
        if not ITEM_TEMPLATES:
            Item.load_item_templates()
        spawnable = {n:d for n,d in ITEM_TEMPLATES.items() if 'spawn_chance' in d}
        if not spawnable:
            return None
        names = list(spawnable.keys())

        chances = []
        for d in spawnable.values():
            base_chance = d['spawn_chance']
            # Apply Global Multiplier
            multiplier = core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER
            
            # Apply Type Specific Multipliers
            t_type = d.get('type')
            
            if t_type == 'weapon_melee':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_MELEE
            elif t_type == 'weapon_ranged':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_RANGED
            elif t_type == 'mobile':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_MOBILE
            elif t_type == 'container':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONTAINER
            elif t_type == 'backpack':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_BACKPACK
            elif t_type == 'currency':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CURRENCY
            elif t_type == 'text':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_TEXT
            
            # Consumables hierarchy
            elif t_type and t_type.startswith('consumable'):
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE
                
                if t_type == 'consumable_food':
                    multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_FOOD
                elif t_type == 'consumable_drink':
                    multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_DRINK
                elif t_type == 'consumable_medication':
                    multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_MEDICATION
                elif t_type == 'consumable_ammo':
                    multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_AMMO
            
            chances.append(base_chance * multiplier)


        chosen_name = random.choices(names, weights=chances, k=1)[0]
        return Item.create_from_name(chosen_name, randomize_durability=True)

    @classmethod
    def create_from_name(cls, item_name, randomize_durability=False):
        if not ITEM_TEMPLATES:
            cls.load_item_templates()
        if item_name not in ITEM_TEMPLATES:
            print(f"Error: No template for '{item_name}'")
            return None
        template = ITEM_TEMPLATES[item_name]

        if template['type'] in ['weapon_melee', 'weapon_ranged', 'utility', 'cloth']:
            randomize_durability = True
            
        props = template['properties']

        # [NEW] SAFETY HELPER
        def get_prop_val(prop_dict, key, subkey='value', default=None):
            """Safely extracts a value from the properties dictionary."""
            if key not in prop_dict: return default
            return prop_dict[key].get(subkey, default)

        durability = None
        min_dur = 0.0
        max_dur = 0.0
        needs_durability = False

        if 'durability' in props and 'max' in props['durability']:
            # Item has durability defined in its XML (weapons, tools)
            min_dur = float(props['durability'].get('min', 0))
            max_dur = float(props['durability']['max'])
            needs_durability = True
        
        if needs_durability:
            # Apply multipliers
            multiplier = core.data.config.DURABILITY_MULTIPLIER
            if template['type'] == 'weapon_melee':
                    multiplier *= core.data.config.WEAPON_MELEE_DURABILITY_MULTIPLIER
            elif template['type'] == 'weapon_ranged':
                multiplier *= core.data.config.WEAPON_RANGED_DURABILITY_MULTIPLIER
            elif template['type'] == 'tool':
                multiplier *= core.data.config.TOOL_DURABILITY_MULTIPLIER
            elif template['type'] == 'cloth':
                multiplier *= core.data.config.CLOTH_DURABILITY_MULTIPLIER
            
            min_dur *= multiplier
            max_dur *= multiplier

            # Always randomize durability for items that have it
            durability = random.uniform(min_dur, max_dur)

        load = None
        if 'load' in props:
            if 'min' in props['load']:
                load = random.randint(int(props['load']['min']), int(props['load']['max']))
            else:
                load = float(props['load'].get('value', 0))
        
        # [MODIFIED] Use Safety Helper
        capacity_str = get_prop_val(props, 'capacity', 'value', None)
        capacity = int(capacity_str) if capacity_str else None

        color_prop = props.get('color', {'r':'255','g':'255','b':'255'})
        color = (int(color_prop.get('r', 255)), int(color_prop.get('g', 255)), int(color_prop.get('b', 255)))
        
        ammo_type = get_prop_val(props, 'ammo', 'type', None)
        
        pellets_str = get_prop_val(props, 'firing', 'pellets', '1')
        pellets = int(pellets_str)
        
        spread_angle_str = get_prop_val(props, 'firing', 'spread_angle', '0')
        spread_angle = float(spread_angle_str)
        
        sprite_file = get_prop_val(props, 'sprite', 'file', None)

        min_damage = int(get_prop_val(props, 'damage', 'min', 0)) if 'damage' in props else None
        max_damage = int(get_prop_val(props, 'damage', 'max', 0)) if 'damage' in props else None

        min_restore = int(get_prop_val(props, 'restore', 'min', 0)) if 'restore' in props else None
        max_restore = int(get_prop_val(props, 'restore', 'max', 0)) if 'restore' in props else None      

        min_reduce = int(get_prop_val(props, 'reduce', 'min', 0)) if 'reduce' in props else None
        max_reduce = int(get_prop_val(props, 'reduce', 'max', 0)) if 'reduce' in props else None 

        slot = get_prop_val(props, 'slot', 'value', None)
        defence = float(get_prop_val(props, 'defence', 'value', 0))
        speed = float(get_prop_val(props, 'speed', 'value', 0))

        state = template.get('state') # Get root state attribute
        if not state: # Check in properties if not on root
             state = get_prop_val(props, 'state', 'value', None)
             
        min_light = int(get_prop_val(props, 'light', 'min', 0)) if 'light' in props else None
        max_light = int(get_prop_val(props, 'light', 'max', 0)) if 'light' in props else None
        
        fuel_type = get_prop_val(props, 'fuel', 'type', None)
        
        text = template.get('text')

        attribute_modifiers = template.get('attribute_modifiers', {})
        status_effect = get_prop_val(props, 'status', 'value', None)
        
        sounds = template.get('sounds', {})

        effects = list(template.get('effects', []))

        repair_list = list(template.get('repair_list', []))

        knockback_str = get_prop_val(props, 'knockback', 'value', None)
        knockback = float(knockback_str) if knockback_str else None

        allow_sleep_str = get_prop_val(props, 'allow_sleep', 'value', 'false')
        allow_sleep = (allow_sleep_str.lower() == 'true')

        machine_gun_str = get_prop_val(props, 'firing', 'machine_gun', 'false')
        machine_gun = (machine_gun_str.lower() == 'true')

        firing_second_str = get_prop_val(props, 'firing', 'firing_second', '0.0')
        firing_second = float(firing_second_str)

        new_item = cls(item_name, template['type'], durability=durability, load=load, capacity=capacity, color=color, ammo_type=ammo_type, pellets=pellets, spread_angle=spread_angle, sprite_file=sprite_file, min_damage=min_damage, max_damage=max_damage, min_restore=min_restore, max_restore=max_restore, slot=slot, defence=defence, speed=speed, state=state, min_light=min_light, max_light=max_light, fuel_type=fuel_type, text=text, min_reduce=min_reduce, max_reduce=max_reduce, sounds=sounds, attribute_modifiers=attribute_modifiers, status_effect=status_effect, effects=effects, repair_list=repair_list, knockback=knockback, machine_gun=machine_gun, firing_second=firing_second, allow_sleep=allow_sleep)


        if 'loot' in template and hasattr(new_item, 'inventory'):
            for loot_info in template['loot']:
                if random.random() < loot_info['chance']:
                    loot_item = cls.create_from_name(loot_info['name'])
                    if loot_item:
                        if len(new_item.inventory) < (new_item.capacity or 0):
                            new_item.inventory.append(loot_item)
        
        return new_item

    def draw(self, surface, offset_x, offset_y, opacity=0):
        draw_rect = self.rect.move(offset_x, offset_y)
        
        if self.image:
            temp_image = self.image.copy()
            if opacity < 0:
                temp_image.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(temp_image, draw_rect)
        else:
            # Fallback for items with no sprite
            temp_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            temp_surface.fill((*self.color, opacity))
            surface.blit(temp_surface, draw_rect)

class Container(Item):
    def __init__(self, name, items=None, capacity=0):
        super().__init__(name, item_type='container', capacity=capacity)
        self.inventory = items if items is not None else []

class Projectile:
    """Represents a bullet fired by the player."""
    def __init__(self, start_x, start_y, target_x, target_y, speed=10, color=WHITE):
        self.x = start_x
        self.y = start_y
        self.rect = pygame.Rect(start_x, start_y, 1, 2)
        self.color = color
        self.speed = speed
        dx = target_x - start_x
        dy = target_y - start_y
        dist = (dx*dx + dy*dy) ** 0.5
        if dist > 0:
            self.vx = (dx / dist) * self.speed
            self.vy = (dy / dist) * self.speed
        else:
            self.vx = self.vy = 0

    def update(self, world_min_x=0, world_min_y=0, world_max_x=None, world_max_y=None):
    # def update(self, game_width=None, game_height=None, game_offset_x=0):

        if world_max_x is None or world_max_y is None:
        #if game_width is None or game_height is None:
            print("Error: Projectile.update() called without game_width/game_height. Projectile will be removed.")
            return True # Remove projectile if bounds are unknown

        self.x += self.vx
        self.y += self.vy
        self.rect.topleft = (int(self.x), int(self.y))

        if self.x < world_min_x or self.x > world_max_x or self.y < world_min_y or self.y > world_max_y:
            return True
        return False

    def draw(self, surface, offset_x=0, offset_y=0):
        draw_center = (int(self.x) + offset_x, int(self.y) + offset_y)
        pygame.draw.circle(surface, self.color, draw_center, 1)