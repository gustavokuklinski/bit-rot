# core/entities/item/item.py
import pygame
import uuid
import random
import core.data.config
from core.data.config import *
from core.entities.item.projectile import Projectile
from core.entities.item.item_data import ITEM_TEMPLATES, load_item_templates_data
from core.entities.item.item_factory import create_item_from_name, generate_random_item

SPRITE_CACHE = {}

class Item:
    """Base class for all in-game items."""
    def __init__(self, name, item_type, durability=None, load=None, capacity=None, color=WHITE, ammo_type=None, pellets=1, spread_angle=0, sprite_file=None, min_damage=None, max_damage=None, min_restore=None, max_restore=None, slot=None, defence=None, speed=None, state=None, min_light=None, max_light=None, fuel_type=None, text=None, attribute_modifiers=None, min_reduce=None, max_reduce=None, sounds=None, status_effect=None, effects=None, repair_list=None, knockback=None, machine_gun=False, firing_second=0.0, allow_sleep=False, key_id=None, firing_distance=None, disposable=False, liquid=False, allow_liquid=False, require=None, weight=0.0, weight_reduction=0.0, allow_belt=False):
        self.name = name
        self.item_type = item_type
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

        self.inventory = []

        self.color = color
        self.min_damage = min_damage
        self.max_damage = max_damage
        self.min_restore = min_restore
        self.max_restore = max_restore

        self.min_reduce = min_reduce
        self.max_reduce = max_reduce

        self.slot = slot
        self.defence = defence
        self.speed = speed

        self.state = state
        self.min_light = min_light
        self.max_light = max_light
        self.fuel_type = fuel_type

        self.text = text
        self.attribute_modifiers = attribute_modifiers if attribute_modifiers is not None else {} 
        self.sounds = sounds if sounds is not None else {}

        self.status_effect = status_effect
        self.effects = effects if effects is not None else []
        self.repair_list = repair_list if repair_list is not None else []
        self.knockback = knockback
        self.machine_gun = machine_gun
        self.firing_second = firing_second
        self.key_id = key_id
        self.allow_sleep = allow_sleep
        self.firing_distance = firing_distance 
        self.disposable = disposable
        
        self.liquid = liquid
        self.allow_liquid = allow_liquid

        self.require = require
        # Weight System
        self.weight = weight
        self.weight_reduction = weight_reduction
        
        self.allow_belt = allow_belt
        self.in_belt = False

    def get_total_weight(self):
        """Calculates total weight including contents and reductions."""
        # Start with the base weight of the item itself
        total = self.weight
        
        # If item is stackable (like resources/ammo), weight is per unit * quantity (load)
        if self.is_stackable() and self.load is not None:
            total = self.weight * self.load

        # Add weight of contents if it's a container (recursive)
        if self.inventory:
            contents_weight = sum(item.get_total_weight() for item in self.inventory)
            # Apply reduction (e.g., backpack reduces content weight by %)
            total += contents_weight * (1.0 - self.weight_reduction)
            
        if getattr(self, 'in_belt', False):
            total *= 0.90
            
        return total

    def to_dict(self):
        """Serializes the item's dynamic state to a dictionary."""
        data = {
            'name': self.name,
            'durability': self.durability,
            'load': self.load,
            'state': self.state,
            'inventory': [i.to_dict() for i in self.inventory] if self.inventory else []
        }

        if getattr(self, 'in_belt', False):
            data['in_belt'] = self.in_belt

        if self.text is not None:
            data['text'] = self.text

        if hasattr(self, 'color') and self.color != (255, 255, 255):
            data['color'] = self.color

        return data

    @staticmethod
    def from_dict(data):
        if not data or 'name' not in data: return None
        saved_color = tuple(data['color']) if 'color' in data else None
        item = Item.create_from_name(data['name'], force_color=saved_color)
        if not item: return None
        
        if 'durability' in data: item.durability = data['durability']
        if 'load' in data: item.load = data['load']
        if 'state' in data: item.state = data['state']
        if 'in_belt' in data: item.in_belt = data['in_belt']

        if 'text' in data: item.text = data['text']
        
        if 'color' in data: 
            item.color = tuple(data['color'])
            if item.image and item.color != (255, 255, 255):
                tinted = item.image.copy()
                tinted.fill((*item.color, 255)[:4], special_flags=pygame.BLEND_RGBA_MULT)
                item.image = tinted

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
        template = ITEM_TEMPLATES.get(self.name)
        if template:
            props = template.get('properties', {})
            if 'durability' in props and 'max' in props['durability']:
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
                
        return self.durability or 100 
        
    @property
    def current_light_radius(self):
        if self.state != 'on' or self.min_light is None or self.max_light is None:
            return 0
        
        max_dur = self.max_durability
        if max_dur <= 0 or self.durability is None:
            return self.min_light
            
        dur_percent = max(0, min(1, self.durability / max_dur))
        light_range = self.max_light - self.min_light
        return (self.min_light + (light_range * dur_percent)) * TILE_SIZE

    def is_stackable(self):
        return (self.capacity is not None and self.capacity > 1 and 
                self.durability is None and self.item_type in ['consumable','currency','resource','reciple','car_fuel','consumable_medication','consumable_drugs','consumable_drink','consumable_ammo','consumable_food', 'utility'])

    def can_stack_with(self, other_item):
        if not self.is_stackable() or not other_item.is_stackable():
            return False
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
        
        if sprite_file in SPRITE_CACHE:
            return SPRITE_CACHE[sprite_file]

        try:
            if sprite_file.startswith("./game/"):
                path = sprite_file
            else:
                if self.item_type == 'cloth':
                    path = SPRITE_PATH + "clothes/" + sprite_file
                else:
                    path = SPRITE_PATH + "items/" + sprite_file
            
            image = pygame.image.load(path).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
            
            SPRITE_CACHE[sprite_file] = image
            return image
        except pygame.error as e:
            print(f"Warning: Could not load sprite '{sprite_file}': {e}")
            return None

    @staticmethod
    def load_item_templates(items_dir=DATA_PATH + 'items/'):
        load_item_templates_data(items_dir)

    @staticmethod
    def generate_random():
        return generate_random_item(Item)

    @classmethod
    def create_from_name(cls, item_name, randomize_durability=False, force_color=None):
        return create_item_from_name(cls, item_name, randomize_durability, force_color)

    @staticmethod
    def cleanup_disposables(item_list, modals=None, message_func=None):
        """
        Recursively removes empty disposable containers from a list of items.
        """
        if item_list is None: return

        # Iterate over a copy to safely modify the original list
        for item in list(item_list):
            if not item: continue

            # 1. Recursion: Clean inside this item first
            if hasattr(item, 'inventory') and item.inventory:
                Item.cleanup_disposables(item.inventory, modals, message_func)

            # 2. Check if this item itself should be destroyed
            if getattr(item, 'disposable', False) and hasattr(item, 'inventory') and len(item.inventory) == 0:
                # Close associated modal if it's open
                if modals:
                    for m in list(modals):
                        if m.get('item') == item:
                            modals.remove(m)
                
                # Notify
                if message_func:
                    message_func(f"Discarded empty {item.name}.")
                
                # Remove the item from the list
                if item in item_list:
                    item_list.remove(item)

    def draw(self, surface, offset_x, offset_y, opacity=0):
        draw_rect = self.rect.move(offset_x, offset_y)
        
        if self.image:
            temp_image = self.image.copy()
            if opacity < 0:
                temp_image.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(temp_image, draw_rect)
        else:
            temp_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            temp_surface.fill((*self.color, opacity))
            surface.blit(temp_surface, draw_rect)

class Container(Item):
    def __init__(self, name, items=None, capacity=0):
        super().__init__(name, item_type='container', capacity=capacity)
        self.inventory = items if items is not None else []