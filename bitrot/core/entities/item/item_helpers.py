# core/entities/item/item_helpers.py
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