# core/entities/item/item_helpers.py
import pygame
import math
import core.data.config
from core.entities.item.item import Item


ALLOWED_POCKET_SLOTS = {'arms', 'legs', 'util', 'util1', 'util2', 'util3'}

def item_allows_belt(item):
    """Safely checks if an item allows going to belt (defaults to False if allow_belt='false')."""
    if not item:
        return False
    val = getattr(item, 'allow_belt', None)
    if val is not None:
        if isinstance(val, str):
            return val.lower().strip() in ('true', '1')
        return bool(val)
    if hasattr(item, 'properties') and isinstance(item.properties, dict):
        val = item.properties.get('allow_belt')
        if val is not None:
            if isinstance(val, str):
                return val.lower().strip() in ('true', '1')
            return bool(val)
    return False


def is_item_liquid(item):
    """Checks if an item is a liquid (including type='car_fuel' and 'Fuel Unit')."""
    if not item:
        return False
    if getattr(item, 'liquid', False):
        return True
    itype = getattr(item, 'item_type', '') or getattr(item, 'type', '') or ''
    if itype in ('liquid', 'car_fuel'):
        return True
    return getattr(item, 'name', '') == 'Fuel Unit'

def get_container_liquid_capacity_units(container, liquid_item, target_item=None):
    """
    Calculates how many units of liquid_item can fit inside container:
    1. Checks available volume (max_liquid - current_liquid).
    2. Calculates remaining weight capacity and converts it to liquid units.
    3. Always floors down to the nearest integer (e.g. 1.5 -> 1, 1.9 -> 1).
    4. Safely handles float('inf') without raising OverflowError.
    """
    if not container or not liquid_item:
        return 0

    if not does_allow_liquid(container):
        return 0

    # 1. Volume Capacity (max_liquid)
    avail_vol = get_container_available_liquid(container, target_item=target_item)
    if avail_vol <= 0 or (isinstance(avail_vol, float) and math.isnan(avail_vol)):
        return 0

    # 2. Weight Capacity
    unit_weight = getattr(liquid_item, 'weight', 0.0) or 0.0

    if hasattr(container, 'max_weight'):
        max_w = float(getattr(container, 'max_weight', 0.0) or 0.0)
    elif hasattr(container, 'weight') and container.weight > 0.0:
        max_w = float(container.weight * 5.0)
    else:
        max_w = float('inf')

    if max_w != float('inf') and unit_weight > 0:
        cur_w = sum(i.get_total_weight() for i in getattr(container, 'inventory', []) if i is not target_item)
        rem_w = max(0.0, max_w - cur_w)
        avail_weight_units = rem_w / unit_weight
    else:
        avail_weight_units = float('inf')

    # Float comparison handles float('inf') correctly before integer conversion
    units = min(avail_vol, avail_weight_units)

    if math.isinf(units):
        return 999999
    if math.isnan(units) or units <= 0:
        return 0

    # Always floor down to integer (1.5 -> 1, 1.9 -> 1)
    return int(math.floor(units))


def is_valid_send_to_container(obj):
    """
    Checks if an object is a valid destination container for 'Send to':
    - Items with type/item_type == 'container'
    - Clothes with id/slot in 'arms', 'legs', 'util' having capacity > 0 (pockets)
    - World containers (maptile_container, Corpse)
    - Vehicles (trunk)
    Excludes weapons, tools, ammo, items without capacity, and non-pocket clothing.
    """
    if not obj:
        return False

    itype = getattr(obj, 'item_type', '') or getattr(obj, 'type', '') or ''

    # Weapons and non-container items are strictly prohibited
    if itype.startswith('weapon') or itype in ('tool', 'resource', 'currency', 'recipe', 'text', 'map', 'liquid'):
        return False

    cap = getattr(obj, 'capacity', 0) or 0
    if cap <= 0:
        return False

    # Standard containers, corpses, vehicles, and maptile containers
    if itype in ('container', 'maptile_container', 'vehicle') or type(obj).__name__ in ('Container', 'Corpse', 'Vehicle'):
        return True

    # Clothes with pockets: id/slot must be 'arms', 'legs', or 'util'
    if itype == 'cloth' or type(obj).__name__ == 'Item':
        slot = getattr(obj, 'slot', None)
        if not slot and hasattr(obj, 'properties') and isinstance(obj.properties, dict):
            slot = obj.properties.get('slot', {}).get('value')
        slot_str = str(slot).lower().strip() if slot else ''
        if slot_str in ALLOWED_POCKET_SLOTS:
            return True

    return False

def does_allow_liquid(obj):
    """Safely checks if an object allows liquid, accounting for string-parsed XML booleans."""
    if not obj:
        return False
    val = getattr(obj, 'allow_liquid', None)
    if val is not None:
        return str(val).lower() in ('true', '1') or val is True
    if hasattr(obj, 'properties') and isinstance(obj.properties, dict):
        if 'allow_liquid' in obj.properties:
            val = obj.properties['allow_liquid']
            return str(val).lower() in ('true', '1') or val is True
    if isinstance(obj, dict):
        if 'allow_liquid' in obj:
            val = obj['allow_liquid']
            return str(val).lower() in ('true', '1') or val is True
    return False

def is_infinite_liquid_source(obj):
    """Checks if the object is an infinite map tile source/sink."""
    if not getattr(core.data.config, 'INFINITE_LIQUID', True):
        return False
    if not does_allow_liquid(obj):
        return False
    item_type = getattr(obj, 'item_type', '')
    obj_type = getattr(obj, 'type', '')
    if isinstance(obj, dict):
        item_type = obj.get('item_type', item_type)
        obj_type = obj.get('type', obj_type)
    return item_type == 'maptile_container' or obj_type == 'maptile_container' or getattr(obj, 'is_maptile', False)

def deserialize_item(data):
    """Unified deserializer handling dict-serialized items or plain string item names."""
    if not data:
        return None
    if isinstance(data, dict):
        return Item.from_dict(data)
    return Item.create_from_name(data)

def serialize_item(item):
    """Unified serializer returning a dict if available, otherwise returning the item."""
    if not item:
        return None
    return item.to_dict() if hasattr(item, 'to_dict') else item

def find_item_recursive(containers, predicate):
    """Recursively searches a list of items/containers for an item matching predicate(item).
    Returns (item, source_list, index, parent_container) or (None, None, -1, None).
    """
    for idx, it in enumerate(containers):
        if not it:
            continue
        if predicate(it):
            return it, containers, idx, None
        if hasattr(it, 'inventory') and it.inventory:
            found, src_list, nested_idx, _ = find_item_recursive(it.inventory, predicate)
            if found:
                return found, src_list, nested_idx, it
    return None, None, -1, None

def player_has_mobile(player):
    """Recursively checks if the player has a Mobile phone."""
    if not player:
        return False

    def search_inv(inventory):
        if not inventory: return False
        for item in inventory:
            if item:
                if 'Mobile' in getattr(item, 'name', ''):
                    return True
                if hasattr(item, 'inventory') and search_inv(item.inventory):
                    return True
        return False

    if search_inv(player.inventory): return True
    if search_inv(player.belt): return True
    if hasattr(player, 'clothes') and search_inv(list(player.clothes.values())): return True
    return False

def get_active_sd_cards(player_or_game):
    """Returns all SD Card items currently active in Mobile Apps."""
    if not player_or_game:
        return []

    game = None
    if hasattr(player_or_game, 'app_state'):
        game = player_or_game
    elif hasattr(player_or_game, 'game') and getattr(player_or_game, 'game'):
        game = player_or_game.game

    if not game:
        import core.messages
        game = getattr(core.messages, '_game_instance', None)

    if not game:
        return []

    player = getattr(game, 'player', None)
    if not player and hasattr(player_or_game, 'progression'):
        player = player_or_game

    if not player or not player_has_mobile(player):
        return []

    active_cards = []
    for slot in getattr(game, 'app_state', {}).get('slots', []):
        if slot and getattr(slot, 'item_type', '') == 'sd_card':
            active_cards.append(slot)
    return active_cards

def has_app(game, app_value):
    target = app_value.strip().lower()
    for card in get_active_sd_cards(game):
        val = getattr(card, 'map_value', None)
        if not val and hasattr(card, 'properties') and isinstance(card.properties, dict):
            val = card.properties.get('map', {}).get('value')
        if not val and hasattr(card, 'name'):
            from core.entities.item.item_data import ITEM_TEMPLATES
            if card.name in ITEM_TEMPLATES:
                val = ITEM_TEMPLATES[card.name].get('properties', {}).get('map', {}).get('value')
        if val and val.strip().lower() == target:
            return True
    return False

def _get_card_property_dict(card, prop_name):
    props = getattr(card, 'properties', {})
    if not props:
        from core.entities.item.item_data import ITEM_TEMPLATES
        card_name = getattr(card, 'name', '')
        props = ITEM_TEMPLATES.get(card_name, {}).get('properties', {})
    return props.get(prop_name, {})

def get_sd_card_attr_info(player, attr_id):
    """
    Returns live bonus info for an attribute:
    {'level_boost': int, 'xp_boost': float, 'passive_amount': int, 'passive_interval': int}
    """
    attr_key = attr_id.lower().strip()
    info = {'level_boost': 0, 'xp_boost': 0.0, 'passive_amount': 0, 'passive_interval': 5}

    for card in get_active_sd_cards(player):
        # Level boost
        level_data = _get_card_property_dict(card, 'level') or _get_card_property_dict(card, 'attribute_levels')
        if attr_key in level_data:
            try: info['level_boost'] += int(float(level_data[attr_key]))
            except: pass

        # XP % boost
        xp_data = _get_card_property_dict(card, 'xp_boost') or _get_card_property_dict(card, 'xp')
        if attr_key in xp_data:
            try: info['xp_boost'] += float(xp_data[attr_key])
            except: pass

        # Passive live tick
        passive_data = _get_card_property_dict(card, 'passive_xp')
        if attr_key in passive_data:
            try:
                info['passive_amount'] += int(float(passive_data[attr_key]))
                info['passive_interval'] = int(float(passive_data.get('interval', 5.0)))
            except: pass

    return info

def update_sd_card_progression(player, game):
    """
    Called every frame. Ticks live points on interval.
    If an SD card is removed, immediately reverts all boosts, levels, and gained points, restarting back at baseline.
    """
    if not player or not hasattr(player, 'progression'):
        return

    active_cards = get_active_sd_cards(player)
    current_card_ids = set(getattr(c, 'id', c.name) for c in active_cards)

    if not hasattr(player, '_sd_active_card_ids'):
        player._sd_active_card_ids = set()
    if not hasattr(player, '_sd_baselines'):
        player._sd_baselines = {}
    if not hasattr(player, '_sd_timers'):
        player._sd_timers = {}

    # --- 1. DETECT CARD REMOVAL -> REVERT ALL BOOSTS AND RESTART ---
    if player._sd_active_card_ids and player._sd_active_card_ids != current_card_ids:
        # Revert all modified attributes back to clean permanent baseline
        for attr_id, base_data in list(player._sd_baselines.items()):
            if attr_id in player.progression.attributes:
                attr = player.progression.attributes[attr_id]
                attr['level'] = base_data['level']
                attr['xp'] = base_data['xp']
                attr['xp_to_next_level'] = player.progression._calc_xp_req(attr_id, attr['level'], player=player)

        player._sd_baselines.clear()
        player._sd_timers.clear()
        player._sd_active_card_ids = set(current_card_ids)

    # --- 2. DETECT NEW CARD ATTACHMENT -> SAVE BASELINE & APPLY INSTANT LEVEL BOOST ---
    if current_card_ids and not player._sd_active_card_ids:
        player._sd_active_card_ids = set(current_card_ids)

        for card in active_cards:
            level_data = _get_card_property_dict(card, 'level') or _get_card_property_dict(card, 'attribute_levels')
            for attr_name, boost_str in level_data.items():
                attr_key = attr_name.strip().lower()
                if attr_key in player.progression.attributes:
                    attr = player.progression.attributes[attr_key]
                    if attr_key not in player._sd_baselines:
                        player._sd_baselines[attr_key] = {'level': attr['level'], 'xp': attr['xp']}
                    try:
                        boost_val = int(float(boost_str))
                        attr['level'] = min(10, attr['level'] + boost_val)
                        attr['xp_to_next_level'] = player.progression._calc_xp_req(attr_key, attr['level'], player=player)
                    except: pass

    # --- 3. LIVE POINTS COUNTER (TICKS ON INTERVAL) ---
    if not active_cards:
        return

    dt_sec = getattr(game, 'dt_ms', 16) / 1000.0

    for card in active_cards:
        passive_data = _get_card_property_dict(card, 'passive_xp')
        if not passive_data:
            continue

        try: interval = float(passive_data.get('interval', 5.0))
        except: interval = 5.0

        card_key = getattr(card, 'id', card.name)
        player._sd_timers[card_key] = player._sd_timers.get(card_key, 0.0) + dt_sec

        if player._sd_timers[card_key] >= interval:
            player._sd_timers[card_key] = 0.0

            for attr_name, val_str in passive_data.items():
                if attr_name == 'interval': continue
                attr_key = attr_name.strip().lower()
                if attr_key in player.progression.attributes:
                    attr = player.progression.attributes[attr_key]
                    if attr_key not in player._sd_baselines:
                        player._sd_baselines[attr_key] = {'level': attr['level'], 'xp': attr['xp']}

                    if attr['level'] < 10:
                        try:
                            xp_amount = float(val_str)
                            attr['xp'] += xp_amount
                            # Live Level Up check
                            if attr['xp'] >= attr['xp_to_next_level']:
                                player.progression._level_up(player, attr)
                        except: pass

def get_container_max_liquid(container):
    """Returns max_liquid of container if defined, else None."""
    if not container:
        return None
    val = getattr(container, 'max_liquid', None)
    if val is not None:
        try:
            return float(val)
        except (ValueError, TypeError):
            pass
    if hasattr(container, 'properties') and isinstance(container.properties, dict):
        if 'max_liquid' in container.properties:
            m = container.properties['max_liquid']
            v = m.get('value') if isinstance(m, dict) else m
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return None

def get_container_liquid_load(container, exclude_item=None):
    """Calculates total liquid units currently stored in container."""
    if not container or not hasattr(container, 'inventory') or not container.inventory:
        return 0.0
    total = 0.0
    for it in container.inventory:
        if it and it is not exclude_item and is_item_liquid(it):
            total += float(getattr(it, 'load', 0) or 0)
    return total

def get_container_available_liquid(container, target_item=None):
    """
    Returns how many units of liquid can be added to container.
    Returns float('inf') if container does not restrict max_liquid.
    """
    max_liq = get_container_max_liquid(container)
    if max_liq is None:
        return float('inf')
    current_liq = get_container_liquid_load(container, exclude_item=target_item)
    return max(0.0, max_liq - current_liq)

def add_item_to_container_inventory(container, item_to_add, target_index=-1, is_stack=False):
    """
    Safely adds or stacks item_to_add into container.inventory, enforcing container volume and weight limits.
    Returns (transferred_amount, remaining_load, success).
    """
    if not container or not hasattr(container, 'inventory'):
        return 0.0, float(getattr(item_to_add, 'load', 1) or 1), False

    is_liquid = is_item_liquid(item_to_add)
    current_load = float(getattr(item_to_add, 'load', 1) or 1)

    if is_liquid:
        avail_units = get_container_liquid_capacity_units(container, item_to_add)
        if avail_units <= 0:
            return 0.0, current_load, False

        # Floor transferred units to the integer below
        trans = float(int(math.floor(min(current_load, float(avail_units)))))
        if trans <= 0:
            return 0.0, current_load, False

        max_l_val = getattr(container, 'max_liquid', None)
        if max_l_val is not None and not math.isinf(float(max_l_val)):
            target_max_l = int(math.floor(float(max_l_val)))
        else:
            target_max_l = int(getattr(item_to_add, 'capacity', 100) or 100)

        # Check existing matching liquid stack
        dst = next((it for it in container.inventory if it and is_item_liquid(it) and it.name == item_to_add.name), None)
        if dst:
            dst.load = (getattr(dst, 'load', 0) or 0) + trans
            dst.capacity = target_max_l
        else:
            new_it = Item.create_from_name(item_to_add.name)
            if not new_it:
                return 0.0, current_load, False
            new_it.load = trans
            new_it.capacity = target_max_l
            if target_index != -1 and target_index <= len(container.inventory):
                container.inventory.insert(target_index, new_it)
            else:
                container.inventory.append(new_it)

        remaining = current_load - trans
        if hasattr(item_to_add, 'load') and item_to_add.load is not None:
            item_to_add.load = remaining
        return trans, remaining, True

    if is_stack:
        dst = None
        if 0 <= target_index < len(container.inventory):
            dst = container.inventory[target_index]
        else:
            dst = next((it for it in container.inventory if it and it.can_stack_with(item_to_add)), None)

        if not dst:
            return 0.0, current_load, False

        avail = (dst.capacity or 100) - dst.load
        trans = min(max(0.0, avail), current_load)
        if trans <= 0:
            return 0.0, current_load, False

        dst.load += trans
        remaining = current_load - trans
        if hasattr(item_to_add, 'load') and item_to_add.load is not None:
            item_to_add.load = remaining
        return trans, remaining, True

    else:
        if not check_container_weight_limit(container, item_to_add):
            return 0.0, current_load, False

        c_cap = getattr(container, 'capacity', 0) or 0
        if len(container.inventory) >= c_cap:
            return 0.0, current_load, False

        if target_index != -1 and target_index <= len(container.inventory):
            container.inventory.insert(target_index, item_to_add)
        else:
            container.inventory.append(item_to_add)
        return current_load, 0.0, True

def is_container_on_player(cont, player):
    """Checks if a container object is equipped, worn, or in the player's inventory/belt."""
    if not cont or not player:
        return False
    if cont is player or cont is getattr(player, 'inventory', None):
        return True

    def check_list(items):
        for item in items:
            if not item: continue
            if item is cont: return True
            if hasattr(item, 'inventory') and item.inventory:
                if check_list(item.inventory): return True
        return False

    if check_list(getattr(player, 'belt', [])): return True
    if check_list(getattr(player, 'inventory', [])): return True
    if hasattr(player, 'clothes') and check_list(player.clothes.values()): return True
    return False

def is_container_type(obj):
    """Checks if an object is a container (item_type='container', maptile container, corpse, or vehicle)."""
    if not obj:
        return False
    itype = getattr(obj, 'item_type', '') or getattr(obj, 'type', '') or ''
    return itype in ('container', 'maptile_container', 'vehicle') or type(obj).__name__ in ('Container', 'Corpse', 'Vehicle')

def is_container_closed_or_locked(container, player=None):
    """Returns True if the container is closed or if it is a vehicle trunk locked without key access."""
    if not container:
        return True
    if getattr(container, 'item_type', '') == 'maptile_container' and not getattr(container, 'is_opened', False):
        return True
    if getattr(container, 'item_type', '') == 'vehicle' and hasattr(container, 'has_key_access'):
        if player and not container.has_key_access(player):
            return True
    return False