import os
import random
import xml.etree.ElementTree as ET
import pygame
import uuid

from data.config import *

ITEM_TEMPLATES = {}  # loaded templates

class Item:
    """Base class for all in-game items."""
    def __init__(self, name, item_type, durability=None, load=None, capacity=None, color=WHITE, ammo_type=None, pellets=1, spread_angle=0, sprite_file=None, min_damage=None, max_damage=None, min_cure=None, max_cure=None, hp=None, slot=None, defence=None, speed=None):
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

    @property
    def damage(self):
        if self.min_damage is not None and self.max_damage is not None:
            return random.randint(self.min_damage, self.max_damage)
        return 0

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
            template = {'type': ttype, 'properties': {}}
            props_node = root.find('properties')
            if props_node is not None:
                for prop in props_node:
                    template['properties'][prop.tag] = {k: v for k, v in prop.attrib.items()}
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
        chances = [d['spawn_chance'] for d in spawnable.values()]
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
        props = template['properties']
        durability = None
        if 'durability' in props and 'max' in props['durability']:
            if randomize_durability and 'min' in props['durability']:
                durability = random.uniform(float(props['durability']['min']), float(props['durability']['max']))
            else:
                durability = float(props['durability']['max'])
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


        #new_item = cls(item_name, template['type'], durability=durability, load=load, capacity=capacity, color=color, ammo_type=ammo_type, pellets=pellets, spread_angle=spread_angle, sprite_file=sprite_file, min_damage=min_damage, max_damage=max_damage, min_cure=min_cure, max_cure=max_cure, hp=hp)
        new_item = cls(item_name, template['type'], durability=durability, load=load, capacity=capacity, color=color, ammo_type=ammo_type, pellets=pellets, spread_angle=spread_angle, sprite_file=sprite_file, min_damage=min_damage, max_damage=max_damage, min_cure=min_cure, max_cure=max_cure, hp=hp, slot=slot, defence=defence, speed=speed)

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
        # lazy import to avoid circular imports at module load time
        from data.config import GAME_WIDTH, GAME_HEIGHT
        if game_width is None:
            game_width = GAME_WIDTH
        if game_height is None:
            game_height = GAME_HEIGHT

        self.x += self.vx
        self.y += self.vy
        self.rect.topleft = (int(self.x), int(self.y))
        if self.x < 0 or self.x > game_width or self.y < 0 or self.y > game_height:
            return True
        return False

    def draw(self, surface, offset_x=0, offset_y=0):
        draw_center = (int(self.x) + offset_x, int(self.y) + offset_y)
        pygame.draw.circle(surface, self.color, draw_center, 5)
