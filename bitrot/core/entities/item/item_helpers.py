# core/entities/item/item_helpers.py
import pygame
from core.entities.item.item import Item

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