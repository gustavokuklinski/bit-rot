# core/events/mouse_drag_utils.py

from core.data.localization import tr
from core.entities.item.item_helpers import (
    is_infinite_liquid_source, is_container_on_player
)

def check_recursive_containment(dragged_item, target_container):
    if dragged_item is target_container:
        return True
    
    if not hasattr(dragged_item, 'inventory') or not dragged_item.inventory:
        return False
        
    for item in dragged_item.inventory:
        if item is target_container:
            return True
        if check_recursive_containment(item, target_container):
            return True
            
    return False

def check_container_weight_limit(container, incoming_item, item_to_remove=None):
    """Checks if adding incoming item exceeds the container's max weight limit."""
    if not container or not incoming_item:
        return True

    # If the item is already inside this container, its weight is already counted
    if hasattr(container, 'inventory') and incoming_item in container.inventory:
        return True

    incoming_weight = incoming_item.get_total_weight() if hasattr(incoming_item, 'get_total_weight') else getattr(incoming_item, 'weight', 0.0)

    # 1. Vehicle max_weight check
    if hasattr(container, 'max_weight'):
        try:
            cur_weight = float(getattr(container, 'current_weight', 0.0) or 0.0)
        except Exception:
            cur_weight = 0.0
        return (cur_weight + incoming_weight) <= container.max_weight

    # 2. Container and clothes pocket check (weight * 5.0)
    if hasattr(container, 'weight') and container.weight > 0.0:
        current_weight = sum(i.get_total_weight() for i in getattr(container, 'inventory', []))
        if item_to_remove and item_to_remove in container.inventory:
            current_weight -= item_to_remove.get_total_weight()
        max_weight = container.weight * 5.0
        return (current_weight + incoming_weight) <= max_weight

    return True

def check_player_weight(incoming_item):
    return True

def _sync_container_to_server(game, container_obj):
    if getattr(game, 'is_client', False) and getattr(game, 'client', None):
        if container_obj and hasattr(container_obj, 'inventory'):
            from core.server.network import NetMsg, send_msg
            send_msg(game.client.socket, {
                'type': NetMsg.WORLD_ACTION, 'action': 'container_sync',
                'x': container_obj.rect.x, 'y': container_obj.rect.y,
                'is_opened': getattr(container_obj, 'is_opened', True),
                'inventory': [i.to_dict() if hasattr(i, 'to_dict') else i for i in container_obj.inventory]
            })

def _remove_from_ground_and_sync(game, item, type_orig=None, container_obj=None):
    if type_orig in ('container', 'nearby', 'container_stack_split', 'nearby_stack_split') and container_obj:
        _sync_container_to_server(game, container_obj)
        
    if item in game.items_on_ground:
        game.items_on_ground.remove(item)
        if getattr(game, 'is_client', False) and getattr(game, 'client', None):
            from core.server.network import NetMsg, send_msg
            send_msg(game.client.socket, {
                'type': NetMsg.WORLD_ACTION, 'action': 'pickup', 'id': getattr(item, 'id', None)
            })

def _sync_source_container(game, container_obj):
    if container_obj and hasattr(container_obj, 'inventory'):
        if getattr(game, 'is_client', False) and getattr(game, 'client', None):
            from core.server.network import NetMsg, send_msg
            send_msg(game.client.socket, {
                'type': NetMsg.WORLD_ACTION, 'action': 'container_sync',
                'x': container_obj.rect.x, 'y': container_obj.rect.y,
                'is_opened': getattr(container_obj, 'is_opened', True),
                'inventory': [i.to_dict() for i in container_obj.inventory]
            })

def return_remainder_to_origin(game, item, type_orig, i_orig, container_obj):
    """Safely returns the remaining portion of an item back to its original container/slot."""
    if not item or getattr(item, 'load', 0) <= 0:
        if item in game.items_on_ground:
            game.items_on_ground.remove(item)
        return

    # 1. Clean up void-protection so it never remains on the floor
    if item in game.items_on_ground:
        game.items_on_ground.remove(item)

    # 2. If it was a clone from an infinite liquid source (e.g. sink), discard remainder
    if container_obj and is_infinite_liquid_source(container_obj) and getattr(item, 'liquid', False):
        return

    # 3. Return to Main Inventory
    if type_orig == 'inventory':
        if 0 <= i_orig <= len(game.player.inventory):
            game.player.inventory.insert(i_orig, item)
        else:
            game.player.inventory.append(item)
        if hasattr(game.player, 'stack_item_in_inventory'):
            game.player.stack_item_in_inventory(item)

    # 4. Return to Belt
    elif type_orig == 'belt':
        if 0 <= i_orig < len(game.player.belt) and game.player.belt[i_orig] is None:
            game.player.belt[i_orig] = item
            item.in_belt = True
        else:
            game.player.inventory.append(item)

    # 5. Return to Gear Slot
    elif type_orig == 'gear':
        slot_name = i_orig
        if hasattr(game.player, 'clothes') and game.player.clothes.get(slot_name) is None:
            game.player.clothes[slot_name] = item
        else:
            game.player.inventory.append(item)

    # 6. Return to Source Container
    elif type_orig == 'container' and container_obj is not None:
        if hasattr(container_obj, 'inventory'):
            if 0 <= i_orig <= len(container_obj.inventory):
                container_obj.inventory.insert(i_orig, item)
            else:
                container_obj.inventory.append(item)
            _sync_container_to_server(game, container_obj)

    # 7. Return to Nearby Container or Ground
    elif type_orig == 'nearby' and container_obj is not None:
        if getattr(container_obj, 'item_type', '') == 'ground':
            if item not in game.items_on_ground:
                game.items_on_ground.append(item)
        elif hasattr(container_obj, 'inventory'):
            if 0 <= i_orig <= len(container_obj.inventory):
                container_obj.inventory.insert(i_orig, item)
            else:
                container_obj.inventory.append(item)
            _sync_container_to_server(game, container_obj)

    # 8. Stack split origins
    elif 'stack_split' in str(type_orig):
        try:
            if type_orig == 'inventory_stack_split':
                game.player.inventory[i_orig].load += item.load
            elif type_orig == 'belt_stack_split':
                game.player.belt[i_orig].load += item.load
            elif type_orig == 'gear_stack_split':
                game.player.clothes[i_orig].load += item.load
            elif type_orig == 'container_stack_split' and container_obj:
                container_obj.inventory[i_orig].load += item.load
            elif type_orig == 'nearby_stack_split' and container_obj:
                container_obj.inventory[i_orig].load += item.load
        except Exception:
            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                game.player.inventory.append(item)
            else:
                if item not in game.items_on_ground:
                    game.items_on_ground.append(item)

    # 9. Fallback
    else:
        if len(game.player.inventory) < game.player.get_total_inventory_slots():
            game.player.inventory.append(item)
        else:
            if item not in game.items_on_ground:
                game.items_on_ground.append(item)