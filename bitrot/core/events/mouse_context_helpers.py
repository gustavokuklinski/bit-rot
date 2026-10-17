# core/events/mouse_context_helpers.py

import os
import re
import pygame
from core.data.config import SPRITE_PATH, GREEN, RED
from core.systems.utils import teleport_player_to_chunk as sys_teleport
from core.data.localization import tr

_fuel_icon_cache = None

def get_fuel_icon():
    global _fuel_icon_cache
    if _fuel_icon_cache is not None:
        return _fuel_icon_cache
    icon_path = os.path.join(SPRITE_PATH, 'items', 'car_fuel_unit.png')
    if not os.path.exists(icon_path):
        icon_path = os.path.join(SPRITE_PATH, 'car_fuel_unit.png')
    if os.path.exists(icon_path):
        try:
            img = pygame.image.load(icon_path).convert_alpha()
            _fuel_icon_cache = pygame.transform.scale(img, (16, 16))
            return _fuel_icon_cache
        except Exception:
            pass
    return None

def is_fuel_item(item):
    if not item:
        return False
    return (
        item.name.lower() == "fuel unit" or 
        getattr(item, 'status_effect', None) == 'fuel' or 
        getattr(item, 'item_type', '') == 'car_fuel'
    )

def get_player_fuel_units(player):
    """Calculates total Fuel Units available across inventory, belt, and worn containers."""
    if not player:
        return 0
    total = 0
    def scan(items):
        nonlocal total
        if not items:
            return
        item_iterable = items.values() if isinstance(items, dict) else items
        for it in item_iterable:
            if not it:
                continue
            if is_fuel_item(it):
                total += int(getattr(it, 'load', 1) or 1)
            if hasattr(it, 'inventory') and it.inventory:
                scan(it.inventory)

    scan(getattr(player, 'inventory', []))
    scan(getattr(player, 'belt', []))
    if hasattr(player, 'clothes'):
        scan(player.clothes)
    return total

def consume_player_fuel_units(player, amount_needed):
    """Consumes the specified amount of Fuel Units from player inventory/belt."""
    if not player or amount_needed <= 0:
        return True

    remaining = amount_needed
    items_to_modify = []

    def scan(items, ctype):
        if not items:
            return
        if ctype == 'dict':
            for k in list(items.keys()):
                it = items[k]
                if not it:
                    continue
                if is_fuel_item(it):
                    items_to_modify.append((items, k, it, 'dict'))
                if hasattr(it, 'inventory') and it.inventory:
                    scan(it.inventory, 'list')
        else:
            for idx in range(len(items) - 1, -1, -1):
                it = items[idx]
                if not it:
                    continue
                if is_fuel_item(it):
                    items_to_modify.append((items, idx, it, 'list'))
                if hasattr(it, 'inventory') and it.inventory:
                    scan(it.inventory, 'list')

    scan(getattr(player, 'inventory', []), 'list')
    scan(getattr(player, 'belt', []), 'list')
    if hasattr(player, 'clothes'):
        scan(player.clothes, 'dict')

    for container, key, it, ctype in items_to_modify:
        if remaining <= 0:
            break
        current_load = int(getattr(it, 'load', 1) or 1)
        take = min(remaining, current_load)
        remaining -= take

        if hasattr(it, 'load') and it.load is not None and it.is_stackable():
            it.load -= take
            if it.load <= 0:
                if container is getattr(player, 'belt', None):
                    container[key] = None
                    it.in_belt = False
                elif ctype == 'list':
                    if it in container:
                        container.remove(it)
                    elif isinstance(key, int) and key < len(container):
                        container.pop(key)
                elif ctype == 'dict':
                    container[key] = None
        else:
            if container is getattr(player, 'belt', None):
                container[key] = None
                it.in_belt = False
            elif ctype == 'list':
                if it in container:
                    container.remove(it)
                elif isinstance(key, int) and key < len(container):
                    container.pop(key)
            elif ctype == 'dict':
                container[key] = None

    return remaining <= 0

def calculate_boat_fuel_cost(game, dest_gx, dest_gy):
    gen = getattr(game, 'generator', None)
    lobby_chunk = getattr(gen, 'lobby_chunk', None) if gen else None

    if lobby_chunk and (dest_gx, dest_gy) == lobby_chunk:
        cur_map = getattr(game.map_manager, 'current_map_filename', '')
        match = re.match(r'map_L\d+_(\d+)_(\d+)_map\.csv', cur_map)
        if match:
            cur_gx, cur_gy = int(match.group(1)), int(match.group(2))
            return max(5, (abs(cur_gx) + abs(cur_gy)) * 5)
        return 5

    return max(5, (abs(dest_gx) + abs(dest_gy)) * 5)

def is_barricade_item(it):
    if not it:
        return False
    b_health = getattr(it, 'barricade_health', None)
    if b_health is not None and b_health > 0:
        return True
    return 'barricade' in getattr(it, 'name', '').lower()

def teleport_player_to_chunk(game, dest_gx, dest_gy, dest_layer=1):
    sys_teleport(game, dest_gx, dest_gy, dest_layer)