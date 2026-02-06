import random
import core.data.config
from core.entities.item.item_data import ITEM_TEMPLATES, load_item_templates_data

def generate_random_item(cls):
    if not ITEM_TEMPLATES:
        load_item_templates_data()
    spawnable = {n:d for n,d in ITEM_TEMPLATES.items() if 'spawn_chance' in d}
    if not spawnable:
        return None
    names = list(spawnable.keys())

    chances = []
    for d in spawnable.values():
        base_chance = d['spawn_chance']
        multiplier = core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER
        
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
        elif t_type == 'map':
            multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_MAP
        elif t_type == 'resource':
            multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_RESOURCE
        elif t_type == 'recipe':
            multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_RECIPE
        elif t_type == 'utility':
            multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_UTILITY
        
        elif t_type and t_type.startswith('consumable'):
            multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE
            
            if t_type == 'consumable_food':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_FOOD
            elif t_type == 'consumable_drink':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_DRINK
            elif t_type == 'consumable_medication':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_MEDICATION
            elif t_type == 'consumable_drugs':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_DRUGS
            elif t_type == 'consumable_ammo':
                multiplier *= core.data.config.ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_AMMO
        
        chances.append(base_chance * multiplier)


    chosen_name = random.choices(names, weights=chances, k=1)[0]
    return cls.create_from_name(chosen_name, randomize_durability=True)

def create_item_from_name(cls, item_name, randomize_durability=False):
    if not ITEM_TEMPLATES:
        load_item_templates_data()
    if item_name not in ITEM_TEMPLATES:
        print(f"Error: No template for '{item_name}'")
        return None
    template = ITEM_TEMPLATES[item_name]

    if template['type'] in ['weapon_melee', 'weapon_ranged', 'utility', 'cloth']:
        randomize_durability = True
        
    props = template['properties']

    def get_prop_val(prop_dict, key, subkey='value', default=None):
        if key not in prop_dict: return default
        return prop_dict[key].get(subkey, default)

    durability = None
    min_dur = 0.0
    max_dur = 0.0
    needs_durability = False

    if 'durability' in props and 'max' in props['durability']:
        min_dur = float(props['durability'].get('min', 0))
        max_dur = float(props['durability']['max'])
        needs_durability = True
    
    if needs_durability:
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

        durability = random.uniform(min_dur, max_dur)

    load = None
    if 'load' in props:
        if 'min' in props['load']:
            load = random.randint(int(props['load']['min']), int(props['load']['max']))
        else:
            load = float(props['load'].get('value', 0))
    
    capacity_str = get_prop_val(props, 'capacity', 'value', None)
    capacity = int(capacity_str) if capacity_str else None

    color_prop = props.get('color', {'r':'255','g':'255','b':'255'})
    color = (int(color_prop.get('r', 255)), int(color_prop.get('g', 255)), int(color_prop.get('b', 255)))
    
    ammo_type = get_prop_val(props, 'ammo', 'type', None)
    
    pellets_str = get_prop_val(props, 'firing', 'pellets', '1')
    pellets = int(pellets_str)
    
    spread_angle_str = get_prop_val(props, 'firing', 'spread_angle', '0')
    spread_angle = float(spread_angle_str)

    firing_distance_str = get_prop_val(props, 'firing', 'distance', None)
    firing_distance = float(firing_distance_str) if firing_distance_str else None
    
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

    state = template.get('state')
    if not state:
            state = get_prop_val(props, 'state', 'value', None)
            
    min_light = int(get_prop_val(props, 'light', 'min', 0)) if 'light' in props else None
    max_light = int(get_prop_val(props, 'light', 'max', 0)) if 'light' in props else None
    
    fuel_type = get_prop_val(props, 'fuel', 'type', None)

    if fuel_type and fuel_type.startswith('[') and fuel_type.endswith(']'):
        fuel_type = [t.strip() for t in fuel_type[1:-1].split(',')]
    
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
    
    key_id = get_prop_val(props, 'key', 'value', None)
    
    disposable = template.get('disposable', False)
    
    liquid = template.get('liquid', False)
    allow_liquid = template.get('allow_liquid', False)

    require = get_prop_val(props, 'require', 'type', None)
    if require and require.startswith('[') and require.endswith(']'):
        require = [t.strip() for t in require[1:-1].split(',')]
    
    # Weight & Reduction
    weight = float(get_prop_val(props, 'weight', 'weight', '0.0'))
    reduction_str = get_prop_val(props, 'weight', 'reduction', '0%').replace('%', '')
    weight_reduction = float(reduction_str) / 100.0

    new_item = cls(item_name, template['type'], durability=durability, load=load, capacity=capacity, color=color, ammo_type=ammo_type, pellets=pellets, spread_angle=spread_angle, sprite_file=sprite_file, min_damage=min_damage, max_damage=max_damage, min_restore=min_restore, max_restore=max_restore, slot=slot, defence=defence, speed=speed, state=state, min_light=min_light, max_light=max_light, fuel_type=fuel_type, text=text, min_reduce=min_reduce, max_reduce=max_reduce, sounds=sounds, attribute_modifiers=attribute_modifiers, status_effect=status_effect, effects=effects, repair_list=repair_list, knockback=knockback, machine_gun=machine_gun, firing_second=firing_second, allow_sleep=allow_sleep, key_id=key_id, firing_distance=firing_distance, disposable=disposable, liquid=liquid, allow_liquid=allow_liquid, require=require, weight=weight, weight_reduction=weight_reduction)

    if 'loot' in template and hasattr(new_item, 'inventory'):
        for loot_info in template['loot']:
            if random.random() < loot_info['chance']:
                loot_item = cls.create_from_name(loot_info['name'])
                if loot_item:
                    # Check 1: Slot Capacity (Standard check)
                    fits = True
                    max_cap = new_item.capacity or 0
                    
                    if len(new_item.inventory) >= max_cap:
                        fits = False
                    
                    # Check 2: Weight Capacity (For containers/backpacks)
                    # We treat 'capacity' as the Max Weight limit as well.
                    if fits and new_item.item_type in ['container', 'backpack']:
                         current_weight = sum(i.get_total_weight() for i in new_item.inventory)
                         item_weight = loot_item.get_total_weight()
                         
                         if current_weight + item_weight > max_cap:
                             fits = False

                    if fits:
                        new_item.inventory.append(loot_item)
    
    return new_item