import pygame
import uuid
import math
import random
from core.data.config import *
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.ui.inventory_modal import get_belt_hud_slot_rect, get_inventory_slot_rect, get_belt_slot_rect_in_modal
from core.ui.container_modal import get_container_slot_rect
from core.messages import display_message
from core.events.keyboard import toggle_status_modal, toggle_inventory_modal, toggle_nearby_modal, toggle_gear_modal
from core.data.localization import tr


def does_allow_liquid(obj):
    """Safely checks if an object allows liquid, accounting for string-parsed XML booleans."""
    if not obj: return False
    val = getattr(obj, 'allow_liquid', None)
    if val is not None: return str(val).lower() in ['true', '1'] or val is True
    if hasattr(obj, 'properties') and isinstance(obj.properties, dict):
        if 'allow_liquid' in obj.properties:
            val = obj.properties['allow_liquid']
            return str(val).lower() in ['true', '1'] or val is True
    if isinstance(obj, dict):
        if 'allow_liquid' in obj:
            val = obj['allow_liquid']
            return str(val).lower() in ['true', '1'] or val is True
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

def handle_context_menu_click(game, mouse_pos):
    clicked_on_menu = False

    if 'rects' not in game.context_menu or 'action_map' not in game.context_menu:
        game.context_menu['active'] = False
        return

    for i, rect in enumerate(game.context_menu['rects']):
        if rect.collidepoint(mouse_pos):
            raw_option = game.context_menu['action_map'][i]
            
            target_sub_slot = None
            if "::" in raw_option:
                parts = raw_option.split("::")
                option = parts[0]
                target_sub_slot = parts[1]
            else:
                option = raw_option

            item = game.context_menu['item']
            source = game.context_menu['source']
            index = game.context_menu['index']
            container_item = game.context_menu.get('container_item')

            try:
                verified_item = None
                if source == 'inventory' and 0 <= index < len(game.player.inventory):
                    verified_item = game.player.inventory[index]
                elif source == 'belt' and 0 <= index < len(game.player.belt):
                    verified_item = game.player.belt[index]
                elif source == 'gear':
                    verified_item = game.player.clothes.get(index)
                elif source == 'ground' and 0 <= index < len(game.items_on_ground):
                    verified_item = game.items_on_ground[index]
                elif source == 'container' and container_item and 0 <= index < len(container_item.inventory):
                    verified_item = container_item.inventory[index]
                elif source == 'nearby' and container_item and 0 <= index < len(container_item.inventory):
                    verified_item = container_item.inventory[index]
                elif source == 'npc':
                    if item in game.npcs:
                        verified_item = item
                    else:
                        verified_item = None
                elif source == 'container_map': 
                    if getattr(item, 'item_type', '') == 'vehicle':
                        verified_item = item 
                    elif container_item: 
                        verified_item = container_item.inventory[index] if 0 <= index < len(container_item.inventory) else None
                    else:
                        verified_item = item
                elif source == 'player_self' or source == 'map_tile':
                    verified_item = item
                
                if verified_item is not item and not isinstance(item, dict):
                    print("Error: UI Index Mismatch. The item changed or moved.")
                    game.context_menu['active'] = False
                    return

            except Exception as e:
                print(f"Validation Error in Context Menu: {e}")
                game.context_menu['active'] = False
                return

            if source == 'npc':
                if option == 'Talk':
                    dialogs = item.get_dialog_options()
                    pos_x = (GAME_WIDTH // 2) - (NPC_DIALOG_MODAL_WIDTH // 2)
                    pos_y = (GAME_HEIGHT // 2) - (NPC_DIALOG_MODAL_HEIGHT // 2)
                    
                    new_modal = {
                        'id': uuid.uuid4(),
                        'type': 'npc_dialog',
                        'npc': item,
                        'dialogs': dialogs,
                        'position': (pos_x, pos_y),
                        'rect': pygame.Rect(pos_x, pos_y, NPC_DIALOG_MODAL_WIDTH, NPC_DIALOG_MODAL_HEIGHT),
                        'is_dragging': False,
                        'drag_offset': (0, 0),
                        'active_dialog_index': -1 
                    }
                    game.modals.append(new_modal)
                    clicked_on_menu = True

            if clicked_on_menu: 
                print(f"Clicked '{option}' on '{getattr(item,'name',str(item))}' (source={source})")
                
            if option == 'Vehicle options' and getattr(item, 'item_type', '') == 'vehicle':
                grid_x = int(item.x // TILE_SIZE)
                grid_y = int(item.y // TILE_SIZE)
                if hasattr(game.map_manager, 'remove_vehicle_tile'):
                     game.map_manager.remove_vehicle_tile(grid_x, grid_y)

                game.modals = [m for m in game.modals if m['type'] != 'vehicle']
                default_pos = (GAME_WIDTH // 2 - 200, GAME_HEIGHT // 2 - 200)
                pos = game.last_modal_positions.get('vehicle', default_pos) if hasattr(game, 'last_modal_positions') else default_pos

                new_modal = {
                    'id': uuid.uuid4(),
                    'type': 'vehicle', 'vehicle': item,
                    'position': pos,
                    'rect': pygame.Rect(pos[0], pos[1], VEHICLE_MODAL_WIDTH, VEHICLE_MODAL_HEIGHT),
                    'is_dragging': False, 
                    'drag_offset': (0, 0), 
                    'active_tab': 'Info'
                }
                new_modal['rect'].topleft = new_modal['position']
                game.modals.append(new_modal)
                clicked_on_menu = True
                return 

            elif option == 'Trunk':
                 if getattr(item, 'item_type', '') == 'vehicle':
                     grid_x = int(item.x // TILE_SIZE)
                     grid_y = int(item.y // TILE_SIZE)
                     if hasattr(game.map_manager, 'remove_vehicle_tile'):
                        game.map_manager.remove_vehicle_tile(grid_x, grid_y)

                 modal_exists = any(m['type'] == 'container' and m['item'] == item for m in game.modals)
                 if not modal_exists:
                    new_container_modal = {
                        'id': uuid.uuid4(), 'type': 'container', 'item': item,
                        'position': game.last_modal_positions['container'],
                        'is_dragging': False, 'drag_offset': (0, 0),
                        'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT)
                    }
                    game.modals.append(new_container_modal)
                 clicked_on_menu = True

            
            if option == 'Status': toggle_status_modal(game)
            elif option == 'Inventory': toggle_inventory_modal(game)
            elif option == 'Gear': toggle_gear_modal(game)

            if option == 'Sleep':
                # Prevent micro-sleeping or accidental sleep when fully rested (above 95%)
                if game.player.tireness >= game.player.max_tireness * 0.95:
                    display_message(tr('msg', "You are not tired enough to sleep."))
                else:
                    print("You go to sleep...")
                    game.player.is_sleeping = True
            if option in ['Open door/window', 'Close door/window']:
                if source == 'map_tile' and isinstance(item, dict) and 'grid_x' in item and 'grid_y' in item:
                    game.map_manager.toggle_door_state(item['grid_x'], item['grid_y'])
                clicked_on_menu = True
            if option == 'Toggle Light':
                if source == 'light_source':
                    item['active'] = not item['active']
                    print(f"Light turned {'ON' if item['active'] else 'OFF'}")
                clicked_on_menu = True

            if option == 'Use': game.player.consume_item(item, source, index, container_item)
            elif option.startswith('Bandage '):
                part = option.split(' ')[1].lower()
                game.player.consume_item(item, source, index, container_item, target_part=part)
                clicked_on_menu = True

            elif option == 'Send to':
                target_container_name = target_sub_slot
                
                def remove_item_from_src(target_item, is_clone=False):
                    if is_clone: return True  # Do not pop clones representing infinite sources
                    
                    if source == 'inventory':
                        for idx_val, v in enumerate(game.player.inventory):
                            if v is target_item: game.player.inventory.pop(idx_val); return True
                    elif source == 'belt':
                        for idx_val, v in enumerate(game.player.belt):
                            if v is target_item: game.player.belt[idx_val] = None; return True
                    elif source == 'container' and container_item:
                        for idx_val, v in enumerate(container_item.inventory):
                            if v is target_item: container_item.inventory.pop(idx_val); return True
                    elif source == 'nearby' and container_item:
                        for idx_val, v in enumerate(container_item.inventory):
                            if v is target_item: 
                                container_item.inventory.pop(idx_val)
                                if getattr(container_item, 'item_type', '') == 'ground':
                                    for g_idx, g_v in enumerate(game.items_on_ground):
                                        if g_v is target_item: game.items_on_ground.pop(g_idx); break
                                return True
                    elif source == 'ground':
                        for idx_val, v in enumerate(game.items_on_ground):
                            if v is target_item: game.items_on_ground.pop(idx_val); return True
                    elif source == 'gear':
                        for k, v in game.player.clothes.items():
                            if v is target_item: game.player.clothes[k] = None; return True
                    return False

                if target_container_name == 'Inventory':
                    if source == 'inventory':
                        game.context_menu['active'] = False
                        return
                    
                    if getattr(item, 'liquid', False):
                        display_message(tr('msg', "Liquid spills. It needs a container."))
                        game.context_menu['active'] = False
                        return

                    if game.player.current_weight + item.get_total_weight() > game.player.max_carry_weight:
                        display_message(tr('msg', "Cannot carry anymore weight"))
                        game.context_menu['active'] = False
                        return
                        
                    def do_send_inv():
                        # Clone if it's an infinite liquid source
                        is_inf = source in ['nearby', 'container_map', 'container'] and container_item and is_infinite_liquid_source(container_item)
                        
                        if is_inf and getattr(item, 'liquid', False):
                            clone = Item.create_from_name(item.name)
                            if clone:
                                clone.load = getattr(item, 'capacity', 100)
                                clone.durability = item.durability
                                game.player.inventory.append(clone)
                                game.player.stack_item_in_inventory(clone)
                        else:
                            if remove_item_from_src(item):
                                game.player.inventory.append(item)
                                game.player.stack_item_in_inventory(item)
                        
                    transfer_time = max(0.1, item.get_total_weight() * 0.2)
                    if source in ['nearby', 'ground', 'container', 'container_map']:
                        game.player.start_action(tr('msg', "Looting"), transfer_time, do_send_inv, xp_reward=0.5)
                    else:
                        do_send_inv()
                        
                else:
                    target_container = None
                    all_containers = [item for item in game.player.belt if item] + \
                                     [item for item in game.player.inventory if item] + \
                                     [item for item in game.player.clothes.values() if item]
                    
                    for c_item in all_containers:
                        if getattr(c_item, 'item_type', '') in ['container', 'cloth']:
                            # Safe ID matching fixes issues with duplicate container names
                            if hasattr(c_item, 'id') and str(c_item.id) == target_container_name:
                                target_container = c_item
                                break
                            # Fallback to name just in case
                            if not target_container and c_item.name == target_container_name:
                                target_container = c_item
                            
                    if target_container:
                        item_load = getattr(item, 'load', 1)
                        if item_load is None: item_load = 1
                        
                        unit_weight = item.get_total_weight() / max(1, item_load)
                        avail_weight = float('inf')
                        
                        cont_weight = getattr(target_container, 'weight', 0)
                        if cont_weight is not None and cont_weight > 0:
                            max_w = cont_weight * 5.0
                            cur_w = sum(i.get_total_weight() for i in getattr(target_container, 'inventory', []))
                            avail_weight = max_w - cur_w
                            
                        max_qty_by_weight = int(avail_weight // unit_weight) if unit_weight > 0 else item_load
                        
                        if max_qty_by_weight <= 0:
                            display_message(tr('msg', "Container is full by weight."))
                            game.context_menu['active'] = False
                            return
                            
                        def do_send_container():
                            removed_item = item
                            is_clone = False
                            
                            is_inf = source in ['nearby', 'container_map', 'container'] and container_item and is_infinite_liquid_source(container_item)
                            
                            # Handle infinite liquid sources: safely clone the item
                            if is_inf and getattr(removed_item, 'liquid', False):
                                clone = Item.create_from_name(removed_item.name)
                                if clone:
                                    clone.load = getattr(removed_item, 'capacity', 100)
                                    clone.durability = removed_item.durability
                                    removed_item = clone
                                    is_clone = True
                                    
                            qty_to_send = getattr(removed_item, 'load', 1)
                            if qty_to_send is None: qty_to_send = 1
                            
                            if qty_to_send > max_qty_by_weight:
                                qty_to_send = max_qty_by_weight
                                
                            stacked = False
                            if hasattr(removed_item, 'is_stackable') and removed_item.is_stackable():
                                for inv_item in target_container.inventory:
                                    if inv_item.can_stack_with(removed_item):
                                        i_cap = getattr(inv_item, 'capacity', 1)
                                        if i_cap is None: i_cap = 1
                                        i_load = getattr(inv_item, 'load', 1)
                                        if i_load is None: i_load = 1
                                        r_load = getattr(removed_item, 'load', 1)
                                        if r_load is None: r_load = 1
                                        
                                        avail = i_cap - i_load
                                        trans = min(avail, qty_to_send, r_load)
                                        if trans > 0:
                                            inv_item.load = i_load + trans
                                            removed_item.load = r_load - trans
                                            qty_to_send -= trans
                                            stacked = True
                                        if qty_to_send <= 0 or removed_item.load <= 0:
                                            break
                            
                            c_cap = getattr(target_container, 'capacity', 0)
                            if c_cap is None: c_cap = 0
                            
                            if qty_to_send > 0 and len(target_container.inventory) < c_cap:
                                r_load = getattr(removed_item, 'load', 1)
                                if r_load is None: r_load = 1
                                
                                if qty_to_send < r_load:
                                    new_item = Item.create_from_name(removed_item.name)
                                    if new_item:
                                        new_item.load = qty_to_send
                                        if hasattr(removed_item, 'durability'): new_item.durability = removed_item.durability
                                        removed_item.load = r_load - qty_to_send
                                        target_container.inventory.append(new_item)
                                else:
                                    # Use original item reference here to pop correctly, pass is_clone for infinite bypassing
                                    if remove_item_from_src(item, is_clone=is_clone):
                                        target_container.inventory.append(removed_item)
                            elif qty_to_send > 0 and not stacked:
                                display_message(tr('msg', "Container is full."))
                                
                            if hasattr(removed_item, 'load') and removed_item.load is not None and removed_item.load <= 0:
                                remove_item_from_src(item, is_clone=is_clone)
                                
                        transfer_time = max(0.1, item.get_total_weight() * 0.2)
                        if source in ['nearby', 'ground', 'container', 'container_map']:
                            game.player.start_action(f"Transferring to {target_container.name}", transfer_time, do_send_container, xp_reward=0.5)
                        else:
                            do_send_container()
                            
                clicked_on_menu = True

            elif option == 'Reload':
                if getattr(item, 'item_type', None) in ['utility', 'mobile']:
                    game.player.reload_utility_item(item, source, index, container_item)
                else:
                    game.player.reload_active_weapon(game=game)

            elif option == 'Get bullets': game.player.unload_weapon(game, item)
            elif option == 'Turn on' or option == 'Turn off':
                result = game.player.toggle_utility_item(item, source, index, container_item)
                if source == 'ground' and result and hasattr(result, 'name'):
                    if index is not None and 0 <= index < len(game.items_on_ground):
                        game.items_on_ground[index] = result
                elif source == 'nearby' and container_item and result and hasattr(result, 'name'):
                    if getattr(container_item, 'item_type', '') == 'ground':
                        for i, ground_item in enumerate(game.items_on_ground):
                            if ground_item is item:
                                game.items_on_ground[i] = result
                                break
            
            elif option == 'Equip':
                item_type = getattr(item, 'item_type', None)
                if item_type in ('cloth', 'container'):
                    
                    if target_sub_slot:
                        item_slot = target_sub_slot
                    else:
                        item_slot = getattr(item, 'slot', None)
                        if item_slot == 'hand': item_slot = 'hands'
                        
                        if item_type == 'container':
                            slots_to_try = [item_slot] if item_slot and item_slot not in ['util'] else ['util', 'util2', 'util3']
                            if item_slot == 'util' or not item_slot:
                                slots_to_try = ['util', 'util2', 'util3']
                                
                            found_empty_slot = False
                            for slot in slots_to_try:
                                if game.player.clothes.get(slot) is None:
                                    item_slot = slot
                                    found_empty_slot = True
                                    break
                        else:
                            if item_slot == 'util':
                                if game.player.clothes.get('util') is not None:
                                    if game.player.clothes.get('util2') is None:
                                        item_slot = 'util2'
                                    elif game.player.clothes.get('util3') is None:
                                        item_slot = 'util3'

                    source_is_external = source in ['ground', 'nearby']
                    if source_is_external:
                        if game.player.current_weight + item.get_total_weight() > game.player.max_carry_weight:
                            display_message(tr('msg', "Cannot carry anymore weight"))
                            game.context_menu['active'] = False
                            return

                    if item_slot in game.player.clothes_slots or item_slot in ['util', 'util2', 'util3']:
                        item_from_source = None
                        if source == 'inventory' and 0 <= index < len(game.player.inventory):
                            item_from_source = game.player.inventory.pop(index)
                        elif source == 'container' and container_item and 0 <= index < len(container_item.inventory):
                            item_from_source = container_item.inventory.pop(index)
                        elif source == 'ground' and 0 <= index < len(game.items_on_ground):
                            item_from_source = game.items_on_ground.pop(index)
                        elif source == 'nearby' and container_item and 0 <= index < len(container_item.inventory):
                            item_from_source = container_item.inventory.pop(index)
                            if getattr(container_item, 'item_type', '') == 'ground' and item_from_source in game.items_on_ground:
                                game.items_on_ground.remove(item_from_source)

                        if item_from_source:
                            old_item = game.player.clothes.get(item_slot)
                            game.player.clothes[item_slot] = item_from_source
                            print(f"Equipped {item_from_source.name} to {item_slot}.")
                            
                            if old_item:
                                if getattr(old_item, 'liquid', False):
                                    old_item.rect.center = game.player.rect.center
                                    game.items_on_ground.append(old_item)
                                elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    game.player.inventory.append(old_item)
                                else:
                                    old_item.rect.center = game.player.rect.center
                                    game.items_on_ground.append(old_item)
                else: 
                    if source == 'ground':
                        if getattr(item, 'liquid', False):
                            print("Cannot pick up liquid directly to inventory.")
                            game.context_menu['active'] = False
                            return

                        if game.player.current_weight + item.get_total_weight() > game.player.max_carry_weight:
                            display_message(tr('msg', "Cannot carry anymore weight"))
                            game.context_menu['active'] = False
                            return

                        placed = False
                        if target_sub_slot and target_sub_slot.startswith('belt_'):
                            try:
                                bi = int(target_sub_slot.split('_')[1])
                                old_belt_item = game.player.belt[bi]
                                game.player.belt[bi] = item
                                if 0 <= index < len(game.items_on_ground):
                                    game.items_on_ground.pop(index)
                                print(f"Picked up and equipped {tr('item', item.name)} to belt slot {bi+1}.")
                                placed = True
                                
                                if old_belt_item:
                                    if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                        game.player.inventory.append(old_belt_item)
                                    else:
                                        old_belt_item.rect.center = game.player.rect.center
                                        game.items_on_ground.append(old_belt_item)
                            except ValueError: pass
                        else:
                            for bi, slot in enumerate(game.player.belt):
                                if slot is None and getattr(item, 'item_type', None) in ('weapon', 'tool'):
                                    game.player.belt[bi] = item
                                    if 0 <= index < len(game.items_on_ground):
                                        game.items_on_ground.pop(index)
                                    print(f"Picked up and equipped {tr('item', item.name)} to belt slot {bi+1}.")
                                    placed = True
                                    break
                                    
                        if not placed:
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(item)
                                if 0 <= index < len(game.items_on_ground):
                                    game.items_on_ground.pop(index)
                                print(f"Picked up {tr('item', item.name)} into inventory.")
                            else:
                                print("No space to equip or pick up the item.")
                                
                        if getattr(item, 'item_type', None) == 'weapon':
                            game.player.active_weapon = item
                    else:
                        if target_sub_slot and target_sub_slot.startswith('belt_'):
                             try:
                                 bi = int(target_sub_slot.split('_')[1])
                                 item_from_source = None
                                 if source == 'inventory' and 0 <= index < len(game.player.inventory):
                                     item_from_source = game.player.inventory.pop(index)
                                 elif source == 'container' and container_item and 0 <= index < len(container_item.inventory):
                                     item_from_source = container_item.inventory.pop(index)
                                 elif source == 'nearby' and container_item and 0 <= index < len(container_item.inventory):
                                     item_from_source = container_item.inventory.pop(index)
                                     if getattr(container_item, 'item_type', '') == 'ground' and item_from_source in game.items_on_ground:
                                         game.items_on_ground.remove(item_from_source)
                                         
                                 if item_from_source:
                                     old_belt_item = game.player.belt[bi]
                                     game.player.belt[bi] = item_from_source
                                     print(f"Equipped {tr('item', item_from_source.name)} to belt slot {bi+1}.")
                                     if old_belt_item:
                                         if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                             game.player.inventory.append(old_belt_item)
                                         else:
                                             old_belt_item.rect.center = game.player.rect.center
                                             game.items_on_ground.append(old_belt_item)
                             except ValueError: pass
                        else:
                             game.player.equip_item_to_belt(item, source, index, container_item)

            elif option == 'Drop one':
                if getattr(item, 'liquid', False):
                    if hasattr(item, 'load') and item.load is not None and item.load > 1:
                        item.load -= 1
                        print(f"A portion of {tr('item', item.name)} spills.")
                    else:
                        print(f"The {tr('item', item.name)} spills.")
                        if source == 'inventory' and 0 <= index < len(game.player.inventory):
                            game.player.inventory.pop(index)
                        elif source == 'belt' and 0 <= index < len(game.player.belt):
                            game.player.belt[index] = None
                        elif source == 'container' and container_item and 0 <= index < len(container_item.inventory):
                            container_item.inventory.pop(index)
                else:
                    game.player.drop_item_stack(game, source, index, container_item, 1)
                
            elif option == 'Drop all':
                if getattr(item, 'liquid', False):
                    print(f"All of the {tr('item', item.name)} spills.")
                    if source == 'inventory' and 0 <= index < len(game.player.inventory):
                        game.player.inventory.pop(index)
                    elif source == 'belt' and 0 <= index < len(game.player.belt):
                        game.player.belt[index] = None
                    elif source == 'container' and container_item and 0 <= index < len(container_item.inventory):
                        container_item.inventory.pop(index)
                else:
                    game.player.drop_item_stack(game, source, index, container_item, 'all')
            
            elif option == 'Drop':
                if getattr(item, 'liquid', False):
                    print(f"The {tr('item', item.name)} spills.")
                    if source == 'gear':
                        game.player.clothes[index] = None
                    elif source == 'inventory' and 0 <= index < len(game.player.inventory):
                        game.player.inventory.pop(index)
                    elif source == 'belt' and 0 <= index < len(game.player.belt):
                        game.player.belt[index] = None
                    elif source == 'container' and container_item and 0 <= index < len(container_item.inventory):
                        container_item.inventory.pop(index)
                else:
                    dropped_item = None
                    if source == 'gear':
                        slot_name = index 
                        item_to_drop = game.player.clothes.get(slot_name)
                        if item_to_drop and item_to_drop == item:
                            dropped_item = game.player.drop_item(game, source, index, container_item)
                            if dropped_item:
                                print(f"Dropped {dropped_item.name} from {slot_name} slot.")
                    else:
                        game.player.drop_item(game, source, index, container_item)

            elif option == 'Read':
                if getattr(item, 'item_type', None) == 'text':
                    modal_exists = any(m['type'] == 'text' and m['item'] == item for m in game.modals)
                    if not modal_exists:
                        new_text_modal = {
                            'id': uuid.uuid4(), 'type': 'text', 'item': item,
                            'position': game.last_modal_positions['text'], 
                            'is_dragging': False, 'drag_offset': (0, 0),
                            'rect': pygame.Rect(game.last_modal_positions['text'][0], game.last_modal_positions['text'][1], TEXT_MODAL_WIDTH, TEXT_MODAL_HEIGHT),
                            'scroll_offset_y': 0
                        }
                        game.modals.append(new_text_modal)
                else:
                    game.player.read_recipe_book(item)
                clicked_on_menu = True

            elif option == 'Open' or option == 'Inspect':
                if getattr(item, 'item_type', None) == 'map':
                    game.modals = [m for m in game.modals if m['type'] != 'big_map']
                    
                    default_pos = (GAME_WIDTH // 2 - 450, GAME_HEIGHT // 2 - 350)
                    
                    new_map_modal = {
                        'id': uuid.uuid4(), 
                        'type': 'big_map', 
                        'item': item,
                        'position': default_pos,
                        'rect': pygame.Rect(default_pos, (MAP_MODAL_WIDTH, MAP_MODAL_HEIGHT)),
                        'is_dragging': False, 
                        'drag_offset': (0, 0),
                        'map_zoom': 6,
                        'map_offset': (0, 0),
                        'is_dragging_map': False
                    }
                    game.modals.append(new_map_modal)
                    clicked_on_menu = True
                    
                elif getattr(item, 'item_type', None) == 'mobile':
                    modal_exists = any(m['type'] == 'mobile' and m['item'] == item for m in game.modals)
                    if not modal_exists:
                        new_mobile_modal = {
                            'id': uuid.uuid4(), 'type': 'mobile', 'item': item,
                            'position': game.last_modal_positions['mobile'],
                            'is_dragging': False, 'drag_offset': (0, 0),
                            'rect': pygame.Rect(game.last_modal_positions['mobile'][0], game.last_modal_positions['mobile'][1], MOBILE_MODAL_WIDTH, MOBILE_MODAL_HEIGHT), 
                            'active_tab': 'Clock'
                        }
                        game.modals.append(new_mobile_modal)
                    clicked_on_menu = True
                elif getattr(item, 'item_type', None) == 'text':
                    modal_exists = any(m['type'] == 'text' and m['item'] == item for m in game.modals)
                    if not modal_exists:
                        new_text_modal = {
                            'id': uuid.uuid4(), 'type': 'text', 'item': item,
                            'position': game.last_modal_positions['text'], 
                            'is_dragging': False, 'drag_offset': (0, 0),
                            'rect': pygame.Rect(game.last_modal_positions['text'][0], game.last_modal_positions['text'][1], TEXT_MODAL_WIDTH, TEXT_MODAL_HEIGHT),
                            'scroll_offset_y': 0
                        }
                        game.modals.append(new_text_modal)
                    clicked_on_menu = True
                elif getattr(item, 'inventory', None) is not None:
                    modal_exists = any(m['type'] == 'container' and m['item'] == item for m in game.modals)
                    if not modal_exists:
                        new_container_modal = {
                            'id': uuid.uuid4(), 'type': 'container', 'item': item,
                            'position': game.last_modal_positions['container'],
                            'is_dragging': False, 'drag_offset': (0, 0),
                            'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1],CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT)
                        }
                        game.modals.append(new_container_modal)
                    clicked_on_menu = True

            elif option == 'Unequip':
                if source == 'belt':
                    if 0 <= index < len(game.player.belt) and game.player.belt[index] == item:
                        game.player.belt[index] = None
                    if game.player.active_weapon == item:
                        game.player.active_weapon = None
                    if getattr(item, 'liquid', False):
                        item.rect.center = game.player.rect.center
                        game.items_on_ground.append(item)
                    elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                        game.player.inventory.append(item)
                    else:
                        item.rect.center = game.player.rect.center
                        game.items_on_ground.append(item)
                elif source == 'gear':
                    slot_name = index 
                    item_to_unequip = game.player.clothes.get(slot_name)
                    if item_to_unequip and item_to_unequip == item:
                        game.player.clothes[slot_name] = None
                        if getattr(item_to_unequip, 'liquid', False):
                            item_to_unequip.rect.center = game.player.rect.center
                            game.items_on_ground.append(item_to_unequip)
                        elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                            game.player.inventory.append(item_to_unequip)
                        else:
                            item_to_unequip.rect.center = game.player.rect.center
                            game.items_on_ground.append(item_to_unequip)
                

            elif source in ['ground', 'nearby', 'container'] and option in ['Grab', 'Grab One', 'Grab Half', 'Grab All']:
                
                if getattr(item, 'type', None) in ('animal', 'zombie'):
                    game.context_menu['active'] = False
                    return

                target_inventory = game.player.inventory
                target_capacity = game.player.get_total_inventory_slots()

                if len(target_inventory) < target_capacity:
                    
                    weight_multiplier = 1.0
                    if hasattr(item, 'load') and item.load and item.load > 0:
                        if option == 'Grab One':
                            weight_multiplier = 1.0 / item.load
                        elif option == 'Grab Half':
                            weight_multiplier = max(1, item.load // 2) / item.load

                    item_weight = item.get_total_weight() if hasattr(item, 'get_total_weight') else getattr(item, 'weight', 0)

                    if game.player.current_weight + (item_weight * weight_multiplier) > game.player.max_carry_weight:
                        display_message(tr('msg', "Cannot carry anymore weight"))
                        game.context_menu['active'] = False
                        return

                    def do_grab():
                        grabbed = False
                        item_to_grab = item
                        
                        if item.name == "Campfire on":
                            from core.entities.item.item import Item
                            new_item = Item.create_from_name("Campfire off")
                            if new_item:
                                new_item.durability = item.durability
                                new_item.load = item.load
                                new_item.rect.center = item.rect.center
                                new_item.x = item.x
                                new_item.y = item.y
                                item_to_grab = new_item
                                print("Campfire extinguished when picked up.")
                                display_message(tr('msg', "Campfire extinguished when picked up."))

                        is_partial = False
                        amount = item_to_grab.load if hasattr(item_to_grab, 'load') and item_to_grab.load else 1
                        
                        if hasattr(item_to_grab, 'is_stackable') and item_to_grab.is_stackable() and hasattr(item_to_grab, 'load') and item_to_grab.load > 1:
                            if option == 'Grab One':
                                amount = 1
                                is_partial = True
                            elif option == 'Grab Half':
                                amount = max(1, item_to_grab.load // 2)
                                is_partial = True
                            elif option == 'Grab All':
                                amount = item_to_grab.load
                                
                        if is_partial and amount < item_to_grab.load:
                            from core.entities.item.item import Item
                            new_item = Item.create_from_name(item_to_grab.name)
                            if new_item:
                                new_item.load = amount
                                if hasattr(item_to_grab, 'durability'):
                                    new_item.durability = item_to_grab.durability
                                item_to_grab.load -= amount
                                target_inventory.append(new_item)
                                game.player.stack_item_in_inventory(new_item)
                            return

                        if source == 'ground' and item in game.items_on_ground:
                            game.items_on_ground.remove(item)
                            grabbed = True
                        elif source == 'nearby' and container_item and item in container_item.inventory:
                            container_item.inventory.remove(item)
                            if getattr(container_item, 'item_type', '') == 'ground' and item in game.items_on_ground:
                                game.items_on_ground.remove(item)
                            grabbed = True
                        elif source == 'container' and container_item and item in container_item.inventory:
                            container_item.inventory.remove(item)
                            grabbed = True

                        if grabbed:
                            target_inventory.append(item_to_grab)
                            game.player.stack_item_in_inventory(item_to_grab)

                    if source == 'nearby':
                        grab_weight = item.get_total_weight() * weight_multiplier
                        grab_time = max(0.1, grab_weight * 0.2)
                        game.player.start_action(tr('msg', "Looting"), grab_time, do_grab, xp_reward=0.5)
                    else:
                        do_grab()
                else:
                    print("Inventory full.")
                    display_message(tr('msg', "Inventory is full."))

            clicked_on_menu = True
            break

    game.context_menu['active'] = False
    if clicked_on_menu:
        return


def handle_right_click(game, mouse_pos):
    clicked_item = None
    click_source = None
    click_index = -1
    click_container_item = None

    for i, item in enumerate(game.player.belt):
        if item and get_belt_hud_slot_rect(i).collidepoint(mouse_pos):
            clicked_item = item
            click_source = 'belt'
            click_index = i
            break

    for modal in reversed(game.modals):
        if not modal['rect'].collidepoint(mouse_pos): continue

        if modal['type'] == 'inventory':
            if modal.get('active_tab', 'Inventory') == 'Inventory':
                for i, item in enumerate(game.player.inventory):
                    if item and get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                        clicked_item, click_source, click_index = item, 'inventory', i; break
                if not clicked_item:
                    for i, item in enumerate(game.player.belt):
                        if item and get_belt_slot_rect_in_modal(i, modal['position']).collidepoint(mouse_pos):
                            clicked_item, click_source, click_index = item, 'belt', i; break
                
                
            
            elif modal.get('active_tab') in modal.get('container_mapping', {}):
                container = modal['container_mapping'][modal['active_tab']]
                if container:
                    pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                    for i, item in enumerate(container.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            clicked_item, click_source, click_index = item, 'container', i
                            click_container_item = container
                            break
                            
            elif modal.get('active_tab') == 'Gear':
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            item = game.player.clothes.get(slot_name)
                            if item:
                                clicked_item, click_source, click_index = item, 'gear', slot_name; break


        elif modal['type'] == 'gear':
            active_tab = modal.get('active_tab', 'Gear')
            if active_tab == 'Gear':
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            item = game.player.clothes.get(slot_name)
                            if item:
                                clicked_item, click_source, click_index = item, 'gear', slot_name
                                break
            elif active_tab in modal.get('container_mapping', {}):
                container = modal['container_mapping'][active_tab]
                if container:
                    pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                    for i, item in enumerate(container.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            clicked_item, click_source, click_index, click_container_item = item, 'container', i, container
                            break

        elif modal['type'] == 'container':
            container = modal['item']
            for i, item in enumerate(container.inventory):
                if item and get_container_slot_rect(modal['position'], i).collidepoint(mouse_pos):
                    clicked_item, click_source, click_index, click_container_item = item, 'container', i, container; break
        
        elif modal['type'] == 'slots':
            for slot_data in modal.get('slot_rects', []):
                if slot_data['rect'].collidepoint(mouse_pos):
                    c = slot_data['container']
                    i = slot_data['index']
                    if i < len(c.inventory):
                        clicked_item, click_source, click_index, click_container_item = c.inventory[i], 'container', i, c
                        break

        elif modal['type'] == 'nearby':
            active_tab_label = modal.get('active_tab')
            active_container = None
            for tab_data in modal.get('tabs_data', []):
                if tab_data['label'] == active_tab_label:
                    active_container = tab_data['container']
                    break
            
            content_rect = modal.get('content_rect')
            if active_container and hasattr(active_container, 'inventory') and content_rect:
                pos = content_rect.topleft
                for i, item in enumerate(active_container.inventory):
                    if item and get_container_slot_rect(pos, i).collidepoint(mouse_pos):
                        clicked_item, click_source, click_index, click_container_item = item, 'nearby', i, active_container; break
        
        if clicked_item: break

    is_over_any_modal = any(modal['rect'].collidepoint(mouse_pos) for modal in game.modals)

    if not clicked_item and not is_over_any_modal:
        world_pos = game.screen_to_world(mouse_pos)

        max_interact_dist_sq = (TILE_SIZE * 2) ** 2
        for i, ground_item in enumerate(game.items_on_ground):
            if ground_item.rect.collidepoint(world_pos):
                dx = game.player.rect.centerx - ground_item.rect.centerx
                dy = game.player.rect.centery - ground_item.rect.centery
                dist_sq = dx*dx + dy*dy
                if dist_sq < max_interact_dist_sq:
                    clicked_item = ground_item
                    click_source = 'ground'
                    click_index = i
                    click_container_item = None
                    break
                else:
                    display_message(tr('msg', "Item is too far away to interact with."))

        if not clicked_item:
            for i, container in enumerate(game.containers):
                if container.rect.collidepoint(world_pos):
                    dx = game.player.rect.centerx - container.rect.centerx
                    dy = game.player.rect.centery - container.rect.centery
                    dist_sq = dx*dx + dy*dy
                    if dist_sq < max_interact_dist_sq:
                        clicked_item = container
                        click_source = 'container_map'
                        click_index = i
                        click_container_item = None
                        break
                    else:
                        display_message(tr('msg', "Item is too far away to interact with."))

        if not clicked_item:
            if game.player.rect.collidepoint(world_pos):
                clicked_item = game.player
                click_source = 'player_self'
                click_index = 0
                click_container_item = None

        if not clicked_item:
            world_pos = game.screen_to_world(mouse_pos)
            for npc in game.npcs:
                if npc.rect.collidepoint(world_pos) and npc.is_friendly and npc.aggro_timer <= 0:
                    clicked_item = npc
                    click_source = 'npc'
                    click_index = 0
                    break

        if not clicked_item:
            world_pos = game.screen_to_world(mouse_pos)
            grid_x = int(world_pos[0] // TILE_SIZE)
            grid_y = int(world_pos[1] // TILE_SIZE)
            tile = game.map_manager.get_tile_at(grid_x, grid_y)
            dx = game.player.rect.centerx - world_pos[0]
            dy = game.player.rect.centery - world_pos[1]
            dist_sq = dx*dx + dy*dy
            max_dist_sq = (TILE_SIZE * 2) ** 2

            if tile:
                if dist_sq <= max_dist_sq:
                    if tile.get('type') == "maptile_car":
                        vehicle = game.map_manager.get_vehicle_at(grid_x, grid_y)
                        if vehicle:
                            clicked_item = vehicle
                            click_source = 'container_map'
                            click_index = 0
                    elif tile.get('is_statable'):
                        clicked_item = {
                            'name': tile.get('name', 'Object'), 
                            'type': 'map_tile', 
                            'grid_x': grid_x, 
                            'grid_y': grid_y, 
                            'state': tile.get('state')
                        }
                        click_source = 'map_tile'
                    elif tile.get('sleep'):
                        clicked_item = {'name': 'Bed', 'type': 'map_tile'}
                        click_source = 'map_tile'
                else:
                    if tile.get('type') == "maptile_car" or tile.get('is_statable') or tile.get('sleep'):
                        display_message(game, tr('msg', "Too far away to interact."))

    if not clicked_item:
        world_pos = game.screen_to_world(mouse_pos)
        for light in game.map_lights:
            if light['rect'].collidepoint(world_pos):
                clicked_item = light
                click_source = 'light_source'
                click_index = 0
                break

    if not clicked_item:
        world_pos = game.screen_to_world(mouse_pos)
        for npc in game.npcs:
            if npc.rect.collidepoint(world_pos) and npc.is_friendly:
                clicked_item = npc
                click_source = 'npc'
                click_index = 0
                break

    if clicked_item:
        game.context_menu['active'] = True
        game.context_menu['item'] = clicked_item
        game.context_menu['source'] = click_source
        game.context_menu['index'] = click_index
        game.context_menu['container_item'] = click_container_item
        game.context_menu['position'] = mouse_pos

        options = ['']

        if click_source == 'npc':
            dx = game.player.rect.centerx - clicked_item.rect.centerx
            dy = game.player.rect.centery - clicked_item.rect.centery
            dist_sq = dx*dx + dy*dy
            max_dist_px = TILE_SIZE * 3
            max_dist_px_sq = max_dist_px ** 2
            dist = dist_sq ** 0.5
            print(f"DEBUG: NPC Interact - Name: {clicked_item.name}, Friendly: {clicked_item.is_friendly}, Dist: {dist:.1f}/{max_dist_px}")

            if dist_sq <= max_dist_px_sq:
                if clicked_item.is_friendly and clicked_item.aggro_timer <= 0:
                    options.append('Talk')
                    if hasattr(clicked_item, 'stop_moving'):
                        clicked_item.stop_moving()
            else:
                display_message(game, tr('msg', "Too far to talk to them."))

        elif click_source == 'map_tile':
            options = []
            if clicked_item.get('name') == 'Bed':
                options.append('Sleep')
            elif 'state' in clicked_item:
                if clicked_item['state'] == 'close':
                    options.append('Open door/window')
                elif clicked_item['state'] == 'open':
                    options.append('Close door/window')
        elif click_source == 'light_source':
            options = ['Toggle Light']
        elif click_source == 'player_self':
            options = ['Status', 'Inventory', 'Gear']
        else:
            options = game.player.get_item_context_options(clicked_item, click_source, click_container_item)
            if getattr(clicked_item, 'item_type', None) == 'consumable_repair' and 'Use' in options:
                options.remove('Use')

        if 'Send all to Inventory' in options:
            options.remove('Send all to Inventory')

        if click_source == 'belt':
            if 'Unequip' not in options: options.append('Unequip')
            options = [o for o in options if o != 'Equip']
        elif click_source == 'gear':
            if 'Unequip' not in options: options.append('Unequip')
            if 'Drop' not in options: options.append('Drop')
            options = [o for o in options if o != 'Equip']

        elif click_source == 'ground':
            if 'Drop' in options: options.remove('Drop')

            is_camp = getattr(clicked_item, 'item_type', None) == 'camp'
            can_grab = True
            
            if isinstance(clicked_item, Corpse):
                can_grab = False
            elif getattr(clicked_item, 'type', None) in ('animal', 'zombie'):
                can_grab = False
            elif is_camp and clicked_item.inventory:
                can_grab = False
            
            if can_grab:
                if not getattr(clicked_item, 'liquid', False):
                    if hasattr(clicked_item, 'is_stackable') and clicked_item.is_stackable() and getattr(clicked_item, 'load', 1) > 1:
                        if 'Grab' in options: options.remove('Grab')
                        options = ['Grab One', 'Grab Half', 'Grab All'] + options
                    else:
                        if 'Grab' not in options: options.insert(0, 'Grab') 

            if is_camp and getattr(clicked_item, 'allow_sleep', False):
                options.append('Sleep')

            if getattr(clicked_item, 'inventory', None) is not None:
                is_valid_type = getattr(clicked_item, 'item_type', '') in ['container', 'cloth']
                if isinstance(clicked_item, Corpse) or is_valid_type:
                    if 'Open' not in options: options.append('Open')
                
        elif click_source == 'container_map':
            if getattr(clicked_item, 'item_type', '') == 'vehicle':
                options = ['Vehicle options', 'Trunk']
            else:
                options = ['Open']
        elif click_source in ['nearby', 'container']:
            if 'Drop' in options: options.remove('Drop')
            if 'Drop one' in options: options.remove('Drop one') 
            if 'Drop all' in options: options.remove('Drop all') 
            if not isinstance(clicked_item, Corpse) and getattr(clicked_item, 'type', None) not in ('animal', 'zombie'):
                if not getattr(clicked_item, 'liquid', False):
                    if hasattr(clicked_item, 'is_stackable') and clicked_item.is_stackable() and getattr(clicked_item, 'load', 1) > 1:
                        if 'Grab' in options: options.remove('Grab')
                        options = ['Grab One', 'Grab Half', 'Grab All'] + options
                    else:
                        if 'Grab' not in options: options.insert(0, 'Grab')

        if getattr(clicked_item, 'capacity', 0) and clicked_item.capacity > 0:
            if getattr(clicked_item, 'item_type', '') in ['container', 'cloth']:
                if 'Open' not in options:
                    options.append('Open')

        # Detect if it's a map tile/map container
        is_maptile = False
        if isinstance(clicked_item, dict):
            if clicked_item.get('type') in ['maptile', 'maptile_container', 'map_tile']:
                is_maptile = True
        else:
            if getattr(clicked_item, 'type', None) in ['maptile', 'maptile_container', 'map_tile']:
                is_maptile = True
            if getattr(clicked_item, 'item_type', None) in ['maptile', 'maptile_container', 'map_tile']:
                is_maptile = True
                
        if click_source in ['container_map', 'map_tile']:
            is_maptile = True

        # Allow "Send to" for ANY valid item, but exclude map objects, corpses, vehicles, camps, etc.
        item_type = getattr(clicked_item, 'item_type', None)
        invalid_types = [None, 'vehicle', 'map_tile', 'maptile', 'maptile_container']
        
        if item_type not in invalid_types and not isinstance(clicked_item, Corpse) and not is_maptile:
            if 'Send to' not in options:
                options.append('Send to')

        # --- SUBMENU GENERATION LOGIC ---
        new_options = []
        for opt in options:
            if opt.startswith('Add to '): 
                continue 
                
            if opt == 'Equip':
                sub_opts = []
                replace_map = {}
                item_type = getattr(clicked_item, 'item_type', None)
                
                if item_type == 'container':
                    base_slot = getattr(clicked_item, 'slot', None)
                    if base_slot and base_slot != 'util':
                        slots_to_check = [base_slot]
                    else:
                        slots_to_check = ['util', 'util2', 'util3']
                        
                    for s in slots_to_check:
                        sub_opts.append(s)
                        existing = game.player.clothes.get(s)
                        if existing:
                            replace_map[s] = existing.name
                            
                elif item_type == 'cloth':
                    slot = getattr(clicked_item, 'slot', None)
                    if slot == 'hand': slot = 'hands'
                    
                    slots_to_check = []
                    if slot == 'util':
                        slots_to_check = ['util', 'util2', 'util3']
                    elif slot:
                        slots_to_check = [slot]
                        
                    for s in slots_to_check:
                        sub_opts.append(s)
                        existing = game.player.clothes.get(s)
                        if existing:
                            replace_map[s] = existing.name
                        
                elif item_type in ('weapon', 'tool', 'consumable_medical', 'utility', 'mobile', 'text', 'map', 'consumable_food'):
                    if getattr(clicked_item, 'allow_belt', True):
                         for b_idx in range(len(game.player.belt)):
                             slot_str = f"belt_{b_idx}"
                             sub_opts.append(slot_str)
                             existing = game.player.belt[b_idx]
                             if existing:
                                 replace_map[slot_str] = existing.name
                
                if sub_opts:
                    new_options.append({'label': 'Equip', 'sub': sub_opts, 'replacing': replace_map})
                else:
                    new_options.append('Equip')
                    
            elif opt == 'Send to':
                sub_opts = []
                display_map = {}
                tooltip_map = {}
                
                is_liquid = getattr(clicked_item, 'liquid', False)
                
                # Never display plain 'Inventory' for liquid items
                if not is_liquid:
                    sub_opts.append('Inventory')
                    display_map['Inventory'] = 'Inventory'
                
                # Fetch all valid player containers alongside their UI locations
                containers_with_loc = []
                for i, b_item in enumerate(game.player.belt):
                    if b_item and getattr(b_item, 'item_type', '') in ['container', 'cloth'] and getattr(b_item, 'inventory', None) is not None:
                        containers_with_loc.append((b_item, f"Belt > Slot {i+1}"))
                for i_item in game.player.inventory:
                    if i_item and getattr(i_item, 'item_type', '') in ['container', 'cloth'] and getattr(i_item, 'inventory', None) is not None:
                        containers_with_loc.append((i_item, "Inventory"))
                for slot, c_item in game.player.clothes.items():
                    if c_item and getattr(c_item, 'item_type', '') in ['container', 'cloth'] and getattr(c_item, 'inventory', None) is not None:
                        containers_with_loc.append((c_item, f"Gear > {str(slot).capitalize()}"))
                        
                for c, loc_str in containers_with_loc:
                    if c is clicked_item: continue
                    
                    # Core constraints: Filter based on liquid allowance
                    if is_liquid and not getattr(c, 'allow_liquid', False): continue
                    if getattr(c, 'allow_liquid', False) and not is_liquid: continue
                    
                    c_item_load = getattr(clicked_item, 'load', 1)
                    if c_item_load is None: c_item_load = 1
                    
                    unit_weight = clicked_item.get_total_weight() / max(1, c_item_load)
                    avail_weight = float('inf')
                    
                    cont_weight = getattr(c, 'weight', 0)
                    if cont_weight is not None and cont_weight > 0:
                        max_w = cont_weight * 5.0
                        cur_w = sum(i.get_total_weight() for i in getattr(c, 'inventory', []))
                        avail_weight = max_w - cur_w
                        
                    if avail_weight < unit_weight:
                        continue 
                        
                    can_fit = False
                    c_cap = getattr(c, 'capacity', 0)
                    if c_cap is None: c_cap = 0
                    
                    if len(c.inventory) < c_cap:
                        can_fit = True
                    else:
                        for i in c.inventory:
                            i_cap = getattr(i, 'capacity', 1)
                            if i_cap is None: i_cap = 1
                            i_load = getattr(i, 'load', 1)
                            if i_load is None: i_load = 1
                            
                            if hasattr(i, 'can_stack_with') and i.can_stack_with(clicked_item) and i_load < i_cap:
                                can_fit = True
                                break
                                
                    if can_fit:
                        c_id = str(getattr(c, 'id', c.name))
                        
                        liquid_qty = 0
                        liquid_name = ""
                        
                        # Inspect the container to see if there are any liquids inside
                        if getattr(c, 'allow_liquid', False):
                            for inside_item in getattr(c, 'inventory', []):
                                if getattr(inside_item, 'liquid', False):
                                    liquid_qty += getattr(inside_item, 'load', 1) or 1
                                    liquid_name = inside_item.name
                        
                        # Generate the dynamic label string 
                        if liquid_qty > 0:
                            display_str = f"{c.name} ({int(liquid_qty)} {liquid_name} units)"
                        elif getattr(c, 'allow_liquid', False):
                            display_str = f"{c.name} (Empty)"
                        else:
                            display_str = c.name
                            
                        # Package for the dropdown architect
                        if c_id not in sub_opts:
                            sub_opts.append(c_id)
                            display_map[c_id] = display_str
                            tooltip_map[c_id] = f"Location: {loc_str}"
                            
                new_options.append({'label': 'Send to', 'sub': sub_opts, 'display_names': display_map, 'tooltips': tooltip_map})
                
            else:
                new_options.append(opt)
                
        game.context_menu['options'] = new_options

        game.context_menu['rects'] = []
        game.context_menu['action_map'] = []
        return