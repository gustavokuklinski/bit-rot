# core/data/player_xml_parser.py

import json
import os
import random
from core.data.config import DATA_PATH, SPRITE_PATH

PLAYER_JSON_PATH = os.path.join(DATA_PATH, 'player', 'player.json')

def parse_player_data(filepath=None):
    """
    Parses player JSON and returns a dictionary of base player data
    and a list of initial trait names.
    """
    target_path = filepath or PLAYER_JSON_PATH
    if not os.path.exists(target_path):
        print(f"FATAL: Player JSON not found at {target_path}")
        return {}, []

    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        p_node = raw.get('player', raw.get('preset', raw))
    except Exception as e:
        print(f"FATAL: Error reading {target_path}: {e}")
        return {}, []

    data = {
        'name': p_node.get('name', 'Player'),
        'sex': p_node.get('sex', 'Male'),
        'stats': {},
        'attributes': {},
        'body_parts': {},
        'initial_loot': [],
        'visuals': {},
        'clothes': p_node.get('clothes', {}),
        'clothes_colors': {
            slot: tuple(int(c) for c in col[:3])
            for slot, col in p_node.get('clothes_colors', {}).items()
            if isinstance(col, (list, tuple)) and len(col) >= 3
        },
        'known_recipes': list(p_node.get('recipes', p_node.get('known_recipes', [])))
    }

    # Stats
    for stat_name, val in p_node.get('stats', {}).items():
        try:
            data['stats'][stat_name] = float(val)
        except (ValueError, TypeError):
            data['stats'][stat_name] = 0.0

    # Attributes
    for attr_name, val in p_node.get('attributes', {}).items():
        try:
            data['attributes'][attr_name] = max(0.0, float(val))
        except (ValueError, TypeError):
            data['attributes'][attr_name] = 0.0

    # Initial Loot with roll chance
    for item_entry in p_node.get('initial_loot', []):
        if isinstance(item_entry, dict):
            iname = item_entry.get('name')
            chance = float(item_entry.get('chance', 1.0))
        else:
            iname = str(item_entry)
            chance = 1.0

        if iname and random.random() < chance:
            data['initial_loot'].append(iname)

    # Visuals
    visuals = p_node.get('visuals', {})
    center_sprite = visuals.get('center', 'player.png')
    data['visuals']['sprite'] = 'player/' + center_sprite.replace('player/', '')
    data['visuals']['center'] = center_sprite
    data['visuals']['left'] = visuals.get('left', 'player_left.png')
    data['visuals']['right'] = visuals.get('right', 'player_right.png')

    trait_names = list(p_node.get('traits', []))

    return data, trait_names