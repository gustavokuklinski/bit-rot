import os
import random
import xml.etree.ElementTree as ET
import pygame
import uuid

from data.config import *

ITEM_TEMPLATES = {}  # loaded templates

class Item:
    """Base class for all in-game items."""
    def __init__(self, name, item_type, durability=None, load=None, capacity=None, color=WHITE, ammo_type=None, pellets=1, spread_angle=0, sprite_file=None, min_damage=None, max_damage=None, min_cure=None, max_cure=None, hp=None, slot=None, defence=None, speed=None, state=None, min_light=None, max_light=None, fuel_type=None, text=None):
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
        if self.item_type in ['backpack', 'container']:
            self.inventory = []
        self.color = color
        self.min_damage = min_damage
        self.max_damage = max_damage
        self.min_cure = min_cure
        self.max_cure = max_cure
        self.hp = hp

        self.slot = slot       # e.g., "head", "torso"
        self.defence = defence # e.g., 0.0
        self.speed = speed     # e.g., 0.0

        self.state = state          # e.g., "on", "off"
        self.min_light = min_light  # e.g., 0
        self.max_light = max_light  # e.g., 15 (in tiles)
        self.fuel_type = fuel_type  # e.g., "Matches"

        self.text = text

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
                multiplier = DURABILITY_MULTIPLIER
                if template['type'] == 'weapon':
                    multiplier *= WEAPON_DURABILITY_MULTIPLIER
                elif template['type'] == 'tool':
                    multiplier *= TOOL_DURABILITY_MULTIPLIER
                elif template['type'] == 'cloth':
                    multiplier *= DURABILITY_MULTIPLIER
                
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
                self.durability is None and self.item_type in ['consumable', 'utility'])

    def can_stack_with(self, other_item):
        """Checks if this item can be stacked with another."""
        if not self.is_stackable or not other_item.is_stackable:
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
        try:
            if sprite_file.startswith("game/"):
                path = sprite_file
            else:
                #path = SPRITE_PATH + "items/" + sprite_file
                if self.item_type == 'cloth':
                    path = SPRITE_PATH + "clothes/" + sprite_file
                else:
                    path = SPRITE_PATH + "items/" + sprite_file
            image = pygame.image.load(path).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
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

            # template = {'type': ttype, 'properties': {}}
            
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
                    

            spawn_node = root.find('spawn')

            if spawn_node is not None:
                template['spawn_chance'] = float(spawn_node.attrib.get('chance', '0'))
            
            loot_node = root.find('loot')
            if loot_node is not None:
                template['loot'] = []
                for loot_item_node in loot_node.findall('item'):
                    loot_item_name = loot_item_node.attrib.get('name')
                    loot_item_chance = float(loot_item_node.attrib.get('chance', '1.0'))
                    template['loot'].append({'name': loot_item_name, 'chance': loot_item_chance})

            ITEM_TEMPLATES[name] = template
        # silent on count to avoid spam
        # print(f"Loaded {len(ITEM_TEMPLATES)} item templates.")

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
        chances = [d['spawn_chance'] * ITEM_SPAWN_CHANCE_MULTIPLIER for d in spawnable.values()]
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

        # if template['type'] == 'weapon':
        if template['type'] in ['weapon', 'utility', 'cloth']:
            randomize_durability = True
            
        props = template['properties']

        durability = None
        min_dur = 0.0
        max_dur = 0.0
        needs_durability = False

        if 'durability' in props and 'max' in props['durability']:
            # Item has durability defined in its XML (weapons, tools)
            min_dur = float(props['durability'].get('min', 0))
            max_dur = float(props['durability']['max'])
            needs_durability = True
        elif template['type'] == 'cloth':
            # Item is cloth, give it default durability even if not in XML
            min_dur = 50.0 # Default min
            max_dur = 100.0 # Default max
            needs_durability = True
        
        if needs_durability:
            # Apply multipliers
            multiplier = DURABILITY_MULTIPLIER
            if template['type'] == 'weapon':
                multiplier *= WEAPON_DURABILITY_MULTIPLIER
            elif template['type'] == 'tool':
                multiplier *= TOOL_DURABILITY_MULTIPLIER
            
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
        capacity = int(props['capacity']['value']) if 'capacity' in props else None
        color_prop = props.get('color', {'r':'255','g':'255','b':'255'})
        color = (int(color_prop['r']), int(color_prop['g']), int(color_prop['b']))
        ammo_type = props.get('ammo', {}).get('type') if 'ammo' in props else None
        pellets = int(props.get('firing', {}).get('pellets', 1)) if 'firing' in props else 1
        spread_angle = float(props.get('firing', {}).get('spread_angle', 0)) if 'firing' in props else 0
        sprite_file = props.get('sprite', {}).get('file') if 'sprite' in props else None
        min_damage = int(props['damage']['min']) if 'damage' in props and 'min' in props['damage'] else None
        max_damage = int(props['damage']['max']) if 'damage' in props and 'max' in props['damage'] else None
        min_cure = int(props['cure']['min']) if 'cure' in props and 'min' in props['cure'] else None
        max_cure = int(props['cure']['max']) if 'cure' in props and 'max' in props['cure'] else None
        hp = random.randint(int(props['hp']['min']), int(props['hp']['max'])) if 'hp' in props and 'min' in props['hp'] and 'max' in props['hp'] else None
        
        slot = props.get('slot', {}).get('value')
        defence = float(props.get('defence', {}).get('value', 0))
        speed = float(props.get('speed', {}).get('value', 0))

        state = template.get('state') # Get root state attribute
        if not state: # Check in properties if not on root
             state = props.get('state', {}).get('value')
             
        min_light = int(props['light']['min']) if 'light' in props and 'min' in props['light'] else None
        max_light = int(props['light']['max']) if 'light' in props and 'max' in props['light'] else None
        fuel_type = props.get('fuel', {}).get('type')
        text = template.get('text')
        new_item = cls(item_name, template['type'], durability=durability, load=load, capacity=capacity, color=color, ammo_type=ammo_type, pellets=pellets, spread_angle=spread_angle, sprite_file=sprite_file, min_damage=min_damage, max_damage=max_damage, min_cure=min_cure, max_cure=max_cure, hp=hp, slot=slot, defence=defence, speed=speed, state=state, min_light=min_light, max_light=max_light, fuel_type=fuel_type, text=text)

        if 'loot' in template and hasattr(new_item, 'inventory'):
            for loot_info in template['loot']:
                if random.random() < loot_info['chance']:
                    loot_item = cls.create_from_name(loot_info['name'])
                    if loot_item:
                        if len(new_item.inventory) < (new_item.capacity or 0):
                            new_item.inventory.append(loot_item)
        
        return new_item

class Container(Item):
    def __init__(self, name, items=None, capacity=0):
        super().__init__(name, item_type='container', capacity=capacity)
        self.inventory = items if items is not None else []

class Projectile:
    """Represents a bullet fired by the player."""
    def __init__(self, start_x, start_y, target_x, target_y, speed=8, color=YELLOW):
        self.x = start_x
        self.y = start_y
        self.rect = pygame.Rect(start_x, start_y, 5, 5)
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

    def update(self, game_width=None, game_height=None, game_offset_x=0):
  
        if game_width is None or game_height is None:
            print("Error: Projectile.update() called without game_width/game_height. Projectile will be removed.")
            return True # Remove projectile if bounds are unknown

        self.x += self.vx
        self.y += self.vy
        self.rect.topleft = (int(self.x), int(self.y))
        if self.x < 0 or self.x > game_width or self.y < 0 or self.y > game_height:
            return True
        return False

    def draw(self, surface, offset_x=0, offset_y=0):
        draw_center = (int(self.x) + offset_x, int(self.y) + offset_y)
        pygame.draw.circle(surface, self.color, draw_center, 5)
