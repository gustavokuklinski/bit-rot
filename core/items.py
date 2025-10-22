import os
import random
import xml.etree.ElementTree as ET
import pygame

from config import TILE_SIZE, WHITE

ITEM_TEMPLATES = {}  # loaded templates

class Item:
    """Base class for all in-game items."""
    def __init__(self, name, item_type, durability=None, load=None, capacity=None, weight=0.0, color=WHITE, ammo_type=None, pellets=1, spread_angle=0, sprite_file=None):
        self.name = name
        self.item_type = item_type  # 'consumable', 'weapon', 'tool', 'backpack', ...
        self.durability = durability
        self.load = load
        self.capacity = capacity
        self.weight = weight
        self.ammo_type = ammo_type
        self.pellets = pellets
        self.spread_angle = spread_angle
        self.image = self.load_sprite(sprite_file)
        self.rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        if self.item_type == 'backpack':
            self.inventory = []
        self.color = color

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
            path = os.path.join('game', 'items', 'sprites', sprite_file)
            image = pygame.image.load(path).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
            return image
        except pygame.error as e:
            print(f"Warning: Could not load sprite '{sprite_file}': {e}")
            return None

    @staticmethod
    def load_item_templates(items_dir='game/items'):
        """Loads item templates from XML files in the game/items directory."""
        global ITEM_TEMPLATES
        if ITEM_TEMPLATES:
            return
        if not os.path.isdir(items_dir):
            print(f"Warning: Item templates directory not found at '{items_dir}'")
            return
        for filename in os.listdir(items_dir):
            if not filename.endswith('.xml'):
                continue
            tree = ET.parse(os.path.join(items_dir, filename))
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
            ITEM_TEMPLATES[name] = template
        # silent on count to avoid spam
        # print(f"Loaded {len(ITEM_TEMPLATES)} item templates.")

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
        chosen = random.choices(names, weights=chances, k=1)[0]
        props = spawnable[chosen]['properties']
        durability = None
        if 'durability' in props and 'min' in props['durability']:
            durability = random.uniform(float(props['durability']['min']), float(props['durability']['max']))
        load = None
        if 'load' in props:
            if 'min' in props['load']:
                load = random.randint(int(props['load']['min']), int(props['load']['max']))
            else:
                load = float(props['load'].get('value', 0))
        capacity = int(props['capacity']['value']) if 'capacity' in props else None
        weight = float(props['weight']['value']) if 'weight' in props else 0.0
        color_prop = props.get('color', {'r':'255','g':'255','b':'255'})
        color = (int(color_prop['r']), int(color_prop['g']), int(color_prop['b']))
        ammo_type = props.get('ammo', {}).get('type') if 'ammo' in props else None
        pellets = int(props.get('firing', {}).get('pellets', 1)) if 'firing' in props else 1
        spread_angle = float(props.get('firing', {}).get('spread_angle', 0)) if 'firing' in props else 0
        sprite_file = props.get('sprite', {}).get('file') if 'sprite' in props else None
        return Item(chosen, spawnable[chosen]['type'], durability=durability, load=load, capacity=capacity, weight=weight, color=color, ammo_type=ammo_type, pellets=pellets, spread_angle=spread_angle, sprite_file=sprite_file)

    @classmethod
    def create_from_name(cls, item_name):
        if not ITEM_TEMPLATES:
            cls.load_item_templates()
        if item_name not in ITEM_TEMPLATES:
            print(f"Error: No template for '{item_name}'")
            return None
        template = ITEM_TEMPLATES[item_name]
        props = template['properties']
        durability = float(props['durability']['max']) if 'durability' in props and 'max' in props['durability'] else None
        load = float(props['load']['value']) if 'load' in props and 'value' in props['load'] else None
        capacity = int(props['capacity']['value']) if 'capacity' in props else None
        weight = float(props['weight']['value']) if 'weight' in props else 0.0
        color_prop = props.get('color', {'r':'255','g':'255','b':'255'})
        color = (int(color_prop['r']), int(color_prop['g']), int(color_prop['b']))
        ammo_type = props.get('ammo', {}).get('type') if 'ammo' in props else None
        pellets = int(props.get('firing', {}).get('pellets', 1)) if 'firing' in props else 1
        spread_angle = float(props.get('firing', {}).get('spread_angle', 0)) if 'firing' in props else 0
        sprite_file = props.get('sprite', {}).get('file') if 'sprite' in props else None
        return cls(item_name, template['type'], durability=durability, load=load, capacity=capacity, weight=weight, color=color, ammo_type=ammo_type, pellets=pellets, spread_angle=spread_angle, sprite_file=sprite_file)

class Projectile:
    """Represents a bullet fired by the player."""
    def __init__(self, start_x, start_y, target_x, target_y, speed=8, color=(255,255,0)):
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
        from config import GAME_WIDTH, GAME_HEIGHT
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

    def draw(self, surface, game_offset_x=0):
        draw_center = (int(self.x) + game_offset_x, int(self.y))
        pygame.draw.circle(surface, self.color, draw_center, 5)