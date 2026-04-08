# core/events/mouse_drag.py
import pygame
import math
import random
from core.data.config import *
from core.entities.item.item import Item
from core.ui.inventory_modal import get_belt_slot_rect_in_modal, get_inventory_slot_rect, get_belt_hud_slot_rect
from core.ui.container_modal import get_container_slot_rect
from core.messages import display_message
from core.data.localization import tr

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
    """Checks if adding the incoming item exceeds the container's max weight limit (weight * 5.0)."""
    if not hasattr(container, 'weight') or container.weight <= 0.0: 
        return True
        
    # If the item is already inside this container, its weight is already counted!
    if hasattr(container, 'inventory') and incoming_item in container.inventory:
        return True
    
    current_weight = sum(i.get_total_weight() for i in container.inventory)
    if item_to_remove and item_to_remove in container.inventory:
        current_weight -= item_to_remove.get_total_weight()
    
    max_weight = container.weight * 5.0
    
    return (current_weight + incoming_item.get_total_weight()) <= max_weight

def handle_mouse_up(game, event, mouse_pos):
    if hasattr(event, 'pos'):
        mouse_pos = event.pos
        
    for modal in reversed(game.modals):
        modal['is_dragging'] = False
        modal['is_dragging_scrollbar'] = False
        modal['is_dragging_map'] = False

    if event.button == 1:
        if game.drag_origin:
            _, type_orig, *container_info = game.drag_origin
            if type_orig in ('container', 'nearby') and container_info:
                container_info[0]._drag_locked = False

        dropped_successfully = False
        if game.is_dragging or game.drag_candidate:
            if not game.is_dragging and game.drag_candidate:
                pass

            if game.dragged_item:
                i_orig, type_orig, *container_info = game.drag_origin
                container_obj = container_info[0] if type_orig in ('container', 'nearby', 'inventory_stack_split', 'belt_stack_split', 'container_stack_split', 'nearby_stack_split', 'gear_stack_split') and container_info else None 
                
                def is_container_on_player(cont, player):
                    if not cont: return False
                    def check_list(items):
                        for item in items:
                            if not item: continue
                            if item is cont: return True
                            if hasattr(item, 'inventory') and item.inventory:
                                if check_list(item.inventory): return True
                        return False
                    
                    if check_list(player.belt): return True
                    if check_list(player.inventory): return True
                    if hasattr(player, 'clothes') and check_list(player.clothes.values()): return True
                    return False

                # Nearby and vehicle items are always external
                is_raw_external = type_orig in ['nearby', 'nearby_stack_split', 'vehicle_equipment']
                
                # If dragging from a 'container' tab, verify it's not actually the player's clothes/backpack
                if type_orig in ['container', 'container_stack_split']:
                    if not is_container_on_player(container_obj, game.player):
                        is_raw_external = True
                
                is_external_source = is_raw_external

                # --- Vehicle Equipment Logic ---
                for modal in reversed(game.modals):
                    if modal['type'] == 'vehicle' and modal.get('active_tab') == 'Mechanics':
                        if 'equipment_rects' in modal:
                            for slot_name, slot_rect in modal['equipment_rects'].items():
                                if slot_rect.collidepoint(mouse_pos):
                                    vehicle = modal['vehicle']
                                    valid_drop = vehicle.can_equip(game.dragged_item, slot_name)
                                    if valid_drop:
                                        item_ref = game.dragged_item
                                        
                                        # --- FIX 2: VOID DROP PROTECTION ---
                                        item_ref.rect.center = game.player.rect.center
                                        if item_ref not in game.items_on_ground:
                                            game.items_on_ground.append(item_ref)
                                        
                                        def do_equip_vehicle():
                                            # Clean it up from the floor once the action finishes successfully
                                            if item_ref in game.items_on_ground:
                                                game.items_on_ground.remove(item_ref)
                                                
                                            old_item = vehicle.add_equipment(item_ref, slot_name)
                                            if old_item:
                                                if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                                    game.player.inventory.append(old_item)
                                                else:
                                                    game.items_on_ground.append(old_item)
                                                    old_item.rect.center = game.player.rect.center
                                        
                                        
                                        action_name = tr('msg', "Equipping") if not is_external_source else tr('msg', "Transferring")
                                        transfer_time = max(0.1, item_ref.get_total_weight() * 0.2) if is_external_source else 1.0
                                        game.player.start_action(action_name, transfer_time, do_equip_vehicle, xp_reward=0.5)
                                        
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return
                                    else:
                                        print(f"Cannot place {game.dragged_item.name} in {slot_name} slot.")
                                        display_message(tr('msg', f"Cannot place {game.dragged_item.name} in {slot_name} slot."))
                                    break
                        if dropped_successfully or (not dropped_successfully and game.dragged_item):
                            break
                
                if dropped_successfully:
                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                    return 

                def check_player_weight(incoming_item):
                    if game.player.current_weight + incoming_item.get_total_weight() > game.player.max_carry_weight:
                        display_message(tr('msg', "Cannot carry anymore weight"))
                        return False
                    return True
               
                # --- Drop on BELT ---
                for i_target in range(len(game.player.belt)):
                    is_modal_slot = any(modal['type'] == 'inventory' and get_belt_slot_rect_in_modal(i_target, modal['position']).collidepoint(mouse_pos) for modal in reversed(game.modals))
                    is_hud_slot = get_belt_hud_slot_rect(i_target).collidepoint(mouse_pos)

                    if is_modal_slot or is_hud_slot:
                        
                        # --- NEW RESTRICTION ---
                        if not getattr(game.dragged_item, 'allow_belt', False):
                            print(f"Cannot place {game.dragged_item.name} on the belt. It is a container-only item.")
                            display_message(tr('msg', f"Cannot place {game.dragged_item.name} on the belt."))
                            dropped_successfully = False
                            break
                        
                        item_in_slot = game.player.belt[i_target]
                        
                        if item_in_slot and check_recursive_containment(game.dragged_item, item_in_slot):
                            print("Cannot drop a container into itself.")
                            display_message(tr('msg', "Cannot drop a container into itself."))
                            dropped_successfully = False
                            break
                        
                        if getattr(game.dragged_item, 'liquid', False):
                            print(f"The {game.dragged_item.name} spills and is lost (belt cannot hold liquid).")
                            dropped_successfully = True 
                            break

                        if is_external_source:
                            if not check_player_weight(game.dragged_item):
                                dropped_successfully = False
                                break
                            if item_in_slot is None or item_in_slot.can_stack_with(game.dragged_item):
                                item_ref = game.dragged_item
                                # Convert "Campfire on" to "Campfire off" when looting
                                if item_ref.name == "Campfire on":
                                    new_item = Item.create_from_name("Campfire off")
                                    if new_item:
                                        new_item.durability = item_ref.durability
                                        new_item.load = item_ref.load
                                        item_ref = new_item
                                        print("Campfire extinguished when picked up.")
                                        display_message(tr('msg', "Campfire extinguished when picked up."))
                                        
                                item_ref.rect.center = game.player.rect.center
                                if item_ref not in game.items_on_ground:
                                    game.items_on_ground.append(item_ref)

                                def do_belt_loot():
                                    if item_ref in game.items_on_ground:
                                        game.items_on_ground.remove(item_ref)
                                        
                                    if game.player.belt[i_target] is None:
                                        game.player.belt[i_target] = item_ref
                                        item_ref.in_belt = True
                                    elif game.player.belt[i_target].can_stack_with(item_ref):
                                        avail = game.player.belt[i_target].capacity - game.player.belt[i_target].load
                                        trans = min(avail, item_ref.load)
                                        game.player.belt[i_target].load += trans
                                        item_ref.load -= trans

                                transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                game.player.start_action(tr('msg', "Looting"), transfer_time, do_belt_loot, xp_reward=0.5)
                                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                return
                            else:
                                print("Cannot swap items while looting.")
                                dropped_successfully = False
                                break

                        if item_in_slot is None:
                            game.player.belt[i_target] = game.dragged_item
                            game.dragged_item.in_belt = True
                            dropped_successfully = True
                        elif item_in_slot.can_stack_with(game.dragged_item):
                            available_space = item_in_slot.capacity - item_in_slot.load
                            transfer = min(available_space, game.dragged_item.load)
                            item_in_slot.load += transfer
                            game.dragged_item.load -= transfer
                            if game.dragged_item.load <= 0:
                                dropped_successfully = True
                        else:
                            item_to_swap = item_in_slot
                            game.player.belt[i_target] = game.dragged_item
                            game.dragged_item.in_belt = True
                            game.dragged_item = item_to_swap 
                            game.dragged_item.in_belt = False
                            dropped_successfully = False
                        
                        if dropped_successfully: break
                if dropped_successfully:
                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                    return

                # --- Drop on INVENTORY/MODALS ---
                for modal in reversed(game.modals):
                    tab_drop_handled = False
                    if 'tab_rects' in modal and modal['tab_rects']:
                        for i, tab_rect in enumerate(modal['tab_rects']):
                            if tab_rect.collidepoint(mouse_pos):
                                # Identified a drop on a tab
                                target_container = None
                                target_list = None
                                label = modal['tabs_data'][i]['label']
                                
                                # Resolve Target
                                if modal['type'] == 'inventory':
                                    if label == 'Inventory':
                                        target_list = game.player.inventory
                                    elif label in modal.get('container_mapping', {}):
                                        target_container = modal['container_mapping'][label]
                                
                                elif modal['type'] == 'nearby':
                                    if i < len(modal['tabs_data']):
                                        target_container = modal['tabs_data'][i]['container']
                                        
                                elif modal['type'] == 'gear':
                                    if label == 'Gear':
                                        # Special Case: Try to equip to slot
                                        pass # Handled below in specific logic or just treat as switch
                                    elif label in modal.get('container_mapping', {}):
                                        target_container = modal['container_mapping'][label]

                                # Switch tab visual
                                modal['active_tab'] = label
                                
                                # Perform Logic
                                if target_container:
                                    if is_external_source and is_container_on_player(target_container, game.player) and not check_player_weight(game.dragged_item):
                                        dropped_successfully = False
                                        tab_drop_handled = True
                                        break
                                        
                                    # Prevent Recursion
                                    if check_recursive_containment(game.dragged_item, target_container):
                                        print("Recursion detected.")
                                        dropped_successfully = False
                                    elif getattr(target_container, 'allow_liquid', False) and not getattr(game.dragged_item, 'liquid', False):
                                        print("Container only accepts liquids.")
                                        dropped_successfully = False
                                    elif getattr(game.dragged_item, 'liquid', False) and not getattr(target_container, 'allow_liquid', False):
                                        print("Liquid spills.")
                                        dropped_successfully = True
                                    elif len(target_container.inventory) < (target_container.capacity or 0):
                                        if not check_container_weight_limit(target_container, game.dragged_item):
                                            print(f"{target_container.name} cannot carry that much weight.")
                                            display_message(f"{target_container.name} {tr('msg', 'cannot carry that much weight.')}")
                                            dropped_successfully = False
                                        elif is_external_source:
                                            item_ref = game.dragged_item
                                            # Convert "Campfire on" to "Campfire off" when looting
                                            if item_ref.name == "Campfire on":
                                                new_item = Item.create_from_name("Campfire off")
                                                if new_item:
                                                    new_item.durability = item_ref.durability
                                                    new_item.load = item_ref.load
                                                    item_ref = new_item
                                                    print("Campfire extinguished when picked up.")
                                                    display_message(tr('msg', "Campfire extinguished when picked up."))
                                                     
                                            item_ref.rect.center = game.player.rect.center
                                            if item_ref not in game.items_on_ground:
                                                game.items_on_ground.append(item_ref)

                                            def do_tab_loot():
                                                if item_ref in game.items_on_ground:
                                                    game.items_on_ground.remove(item_ref)
                                                     
                                                target_container.inventory.append(item_ref)
                                        
                                            transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                            game.player.start_action(tr('msg', "Looting"), transfer_time, do_tab_loot, xp_reward=0.5)
                                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                            return
                                        else:
                                            target_container.inventory.append(game.dragged_item)
                                            dropped_successfully = True
                                    else:
                                        print(f"{target_container.name} is full.")
                                        dropped_successfully = False
                                        
                                elif target_list is not None: # e.g. Main Inventory
                                    if is_external_source and not check_player_weight(game.dragged_item):
                                        dropped_successfully = False
                                        tab_drop_handled = True
                                        break
                                        
                                    if getattr(game.dragged_item, 'liquid', False):
                                        print(f"The {game.dragged_item.name} spills and is lost (pockets cannot hold liquid).")
                                        dropped_successfully = True
                                        
                                    if len(target_list) < game.player.get_total_inventory_slots():
                                        if is_external_source:
                                            item_ref = game.dragged_item
                                            # Convert "Campfire on" to "Campfire off" when looting
                                            if item_ref.name == "Campfire on":
                                                new_item = Item.create_from_name("Campfire off")
                                                if new_item:
                                                    new_item.durability = item_ref.durability
                                                    new_item.load = item_ref.load
                                                    item_ref = new_item
                                                    print("Campfire extinguished when picked up.")
                                                    display_message(tr('msg', "Campfire extinguished when picked up."))
                                            item_ref.rect.center = game.player.rect.center
                                            if item_ref not in game.items_on_ground:
                                                game.items_on_ground.append(item_ref)

                                            def do_tab_inv_loot():
                                                if item_ref in game.items_on_ground:
                                                    game.items_on_ground.remove(item_ref)
                                                     
                                                target_list.append(item_ref)
                             
                                            transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                            game.player.start_action(tr('msg', "Looting"), transfer_time, do_tab_inv_loot, xp_reward=0.5)
                                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                            return
                                        else:
                                             target_list.append(game.dragged_item)
                                             dropped_successfully = True
                                    else:
                                        print("Inventory is full.")
                                        display_message(tr('msg', "Inventory is full."))
                                        dropped_successfully = False
                                
                                tab_drop_handled = True
                                break
                    
                    if tab_drop_handled:
                         if dropped_successfully:
                            break # Break modal loop
                         else:
                            # If drop failed but we hit a tab, we probably shouldn't check the body of the modal 
                            # (unless we want to allow 'missed tab' drops, but that's confusing)
                            pass
                            
                    if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
                        
                        if modal.get('active_tab', 'Inventory') == 'Inventory':
                            # Main Inventory Grid
                            if not dropped_successfully:
                                target_index = -1
                                for i in range(10): 
                                    if get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                                        target_index = i
                                        break
                                
                                if target_index != -1 and getattr(game.dragged_item, 'liquid', False):
                                    print(f"The {game.dragged_item.name} spills and is lost (pockets cannot hold liquid).")
                                    dropped_successfully = True
                                
                                elif target_index != -1: 
                                    if target_index < len(game.player.inventory):
                                        item_in_slot = game.player.inventory[target_index]
                                        
                                        if check_recursive_containment(game.dragged_item, item_in_slot):
                                            print("Cannot drop container into itself.")
                                            dropped_successfully = False
                                            break
                                        
                                        if is_external_source:
                                            if not check_player_weight(game.dragged_item):
                                                dropped_successfully = False
                                                break
                                            if item_in_slot.can_stack_with(game.dragged_item):
                                                item_ref = game.dragged_item

                                                item_ref.rect.center = game.player.rect.center
                                                if item_ref not in game.items_on_ground:
                                                    game.items_on_ground.append(item_ref)

                                                def do_inv_stack():
                                                    if item_ref in game.items_on_ground:
                                                        game.items_on_ground.remove(item_ref)
                                                        
                                                    avail = item_in_slot.capacity - item_in_slot.load
                                                    trans = min(avail, item_ref.load)
                                                    item_in_slot.load += trans
                                                    item_ref.load -= trans

                                                transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                                game.player.start_action(tr('msg', "Looting"), transfer_time, do_inv_stack, xp_reward=0.5)
                                                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                                return
                                            else:
                                                print("Cannot swap while looting.")
                                                dropped_successfully = False
                                                break

                                        if item_in_slot.can_stack_with(game.dragged_item):
                                            available_space = item_in_slot.capacity - item_in_slot.load
                                            transfer = min(available_space, game.dragged_item.load)
                                            item_in_slot.load += transfer
                                            game.dragged_item.load -= transfer
                                            if game.dragged_item.load <= 0:
                                                dropped_successfully = True
                                        else:
                                            item_to_swap = game.player.inventory.pop(target_index)
                                            game.player.inventory.insert(target_index, game.dragged_item)
                                            game.dragged_item = item_to_swap
                                            dropped_successfully = False 
                                    elif len(game.player.inventory) < game.player.get_total_inventory_slots():

                                        if is_external_source:
                                            if not check_player_weight(game.dragged_item):
                                                dropped_successfully = False
                                                break
                                            item_ref = game.dragged_item

                                            item_ref.rect.center = game.player.rect.center
                                            if item_ref not in game.items_on_ground:
                                                game.items_on_ground.append(item_ref)

                                            def do_inv_loot():
                                                if item_ref in game.items_on_ground:
                                                    game.items_on_ground.remove(item_ref)
                                                    
                                                game.player.inventory.insert(target_index, item_ref)
                                            
                                            transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                            game.player.start_action(tr('msg', "Looting"), transfer_time, do_inv_loot, xp_reward=0.5)
                                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                            return

                                        game.player.inventory.insert(target_index, game.dragged_item)
                                        dropped_successfully = True
                                
                                elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    
                                    if getattr(game.dragged_item, 'liquid', False):
                                        print(f"The {game.dragged_item.name} spills and is lost.")
                                        dropped_successfully = True
                                    else:
                                        if is_external_source:
                                            if not check_player_weight(game.dragged_item):
                                                dropped_successfully = False
                                                break
                                            item_ref = game.dragged_item

                                            item_ref.rect.center = game.player.rect.center
                                            if item_ref not in game.items_on_ground:
                                                game.items_on_ground.append(item_ref)

                                            def do_inv_append():
                                                if item_ref in game.items_on_ground:
                                                    game.items_on_ground.remove(item_ref)
                                                    
                                                game.player.inventory.append(item_ref)
                              
                                            transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                            game.player.start_action(tr('msg', "Looting"), transfer_time, do_inv_append, xp_reward=0.5)
                                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                            return

                                        game.player.inventory.append(game.dragged_item)
                                        dropped_successfully = True
                                
                                if dropped_successfully: break
                        
                        elif modal.get('active_tab') in modal.get('container_mapping', {}):
                            container = modal['container_mapping'][modal['active_tab']]
                            
                            if container:
                                if check_recursive_containment(game.dragged_item, container):
                                    print("Recursion detected: Cannot put the container inside itself.")
                                    dropped_successfully = False
                                    break
                                
                                if getattr(container, 'allow_liquid', False):
                                    if not getattr(game.dragged_item, 'liquid', False):
                                        print(f"This {container.name} only accepts liquids.")
                                        dropped_successfully = False 
                                        break
                                elif getattr(game.dragged_item, 'liquid', False):
                                    print(f"The {game.dragged_item.name} spills and is lost.")
                                    dropped_successfully = True 
                                    break

                                target_index = -1
                                pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                                for i in range(container.capacity or 0):
                                    if get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                                        target_index = i
                                        break
                                
                                if is_external_source:
                                    if is_container_on_player(container, game.player) and not check_player_weight(game.dragged_item):
                                        dropped_successfully = False
                                        break
                                    can_loot = False
                                    is_stack = False
                                    if target_index != -1 and target_index < len(container.inventory):
                                        item_in_slot = container.inventory[target_index]
                                        if item_in_slot.can_stack_with(game.dragged_item):
                                            can_loot = True; is_stack = True
                                        else:
                                            print("Cannot swap while looting.")
                                            dropped_successfully = False
                                            break
                                    elif len(container.inventory) < (container.capacity or 0):
                                        if not check_container_weight_limit(container, game.dragged_item):
                                            print(f"{container.name} cannot carry that much weight.")
                                            display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                            dropped_successfully = False
                                        else:
                                            can_loot = True
                                    
                                    if can_loot:
                                        item_ref = game.dragged_item
                                        # Convert "Campfire on" to "Campfire off" when looting
                                        if item_ref.name == "Campfire on":
                                            new_item = Item.create_from_name("Campfire off")
                                            if new_item:
                                                new_item.durability = item_ref.durability
                                                new_item.load = item_ref.load
                                                item_ref = new_item
                                                print("Campfire extinguished when picked up.")
                                                display_message(tr('msg', "Campfire extinguished when picked up."))
                                        item_ref.rect.center = game.player.rect.center
                                        if item_ref not in game.items_on_ground:
                                            game.items_on_ground.append(item_ref)

                                        def do_container_loot():
                                            if item_ref in game.items_on_ground:
                                                game.items_on_ground.remove(item_ref)
                                                
                                            if is_stack:
                                                item_in_dst = container.inventory[target_index]
                                                avail = item_in_dst.capacity - item_in_dst.load
                                                trans = min(avail, item_ref.load)
                                                item_in_dst.load += trans
                                                item_ref.load -= trans
                                            else:
                                                if target_index != -1 and target_index <= len(container.inventory):
                                                    container.inventory.insert(target_index, item_ref)
                                                else:
                                                    container.inventory.append(item_ref)
                                        
                                      
                                        transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                        game.player.start_action(tr('msg', "Looting"), transfer_time, do_container_loot, xp_reward=0.5)
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return

                                if target_index != -1:
                                    if target_index < len(container.inventory):
                                        item_in_slot = container.inventory[target_index]
                                        if item_in_slot.can_stack_with(game.dragged_item):
                                            available = item_in_slot.capacity - item_in_slot.load
                                            transfer = min(available, game.dragged_item.load)
                                            item_in_slot.load += transfer
                                            game.dragged_item.load -= transfer
                                            if game.dragged_item.load <= 0: dropped_successfully = True
                                        else:
                                            if not check_container_weight_limit(container, game.dragged_item, item_in_slot):
                                                print(f"{container.name} cannot carry that much weight.")
                                                display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                                dropped_successfully = False
                                            else:
                                                item_to_swap = container.inventory.pop(target_index)
                                                container.inventory.insert(target_index, game.dragged_item)
                                                game.dragged_item = item_to_swap
                                                dropped_successfully = False
                                    else:
                                        if not check_container_weight_limit(container, game.dragged_item):
                                            print(f"{container.name} cannot carry that much weight.")
                                            display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                            dropped_successfully = False
                                        else:
                                            container.inventory.insert(target_index, game.dragged_item)
                                            dropped_successfully = True
                                
                                elif len(container.inventory) < (container.capacity or 0):
                                    if not check_container_weight_limit(container, game.dragged_item):
                                        print(f"{container.name} cannot carry that much weight.")
                                        display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                        dropped_successfully = False
                                    else:
                                        container.inventory.append(game.dragged_item)
                                        dropped_successfully = True
                                
                                if dropped_successfully: break
                    
                    elif modal['type'] == 'slots':
                        for slot_data in modal.get('slot_rects', []):
                            if slot_data['rect'].collidepoint(mouse_pos):
                                target_container = slot_data['container']
                                target_index = slot_data['index']
                                
                                if check_recursive_containment(game.dragged_item, target_container):
                                    display_message(tr('msg', "Cannot put the container inside itself."))
                                    dropped_successfully = False
                                    break
                                
                                if getattr(target_container, 'allow_liquid', False) and not getattr(game.dragged_item, 'liquid', False):
                                    display_message(tr('msg', "Container only accepts liquids."))
                                    dropped_successfully = False
                                    break
                                elif getattr(game.dragged_item, 'liquid', False) and not getattr(target_container, 'allow_liquid', False):
                                    display_message(tr('msg', "Liquid spills."))
                                    dropped_successfully = True
                                    break

                                # Handle Looting from Ground/External
                                if is_external_source:
                                    if is_container_on_player(target_container, game.player) and not check_player_weight(game.dragged_item):
                                        dropped_successfully = False
                                        break
                                    
                                    can_loot = False
                                    is_stack = False
                                    if target_index < len(target_container.inventory):
                                        item_in_slot = target_container.inventory[target_index]
                                        if item_in_slot.can_stack_with(game.dragged_item):
                                            can_loot = True; is_stack = True
                                        else:
                                            display_message(tr('msg', "Cannot swap while looting."))
                                            dropped_successfully = False
                                            break
                                    elif len(target_container.inventory) < (target_container.capacity or 0):
                                        if not check_container_weight_limit(target_container, game.dragged_item):
                                            display_message(f"{target_container.name} {tr('msg', 'cannot carry that much weight.')}")
                                            dropped_successfully = False
                                        else:
                                            can_loot = True

                                    if can_loot:
                                        item_ref = game.dragged_item
                                        item_ref.rect.center = game.player.rect.center
                                        if item_ref not in game.items_on_ground:
                                            game.items_on_ground.append(item_ref)

                                        def do_slots_container_loot():
                                            if item_ref in game.items_on_ground:
                                                game.items_on_ground.remove(item_ref)
                                            if is_stack:
                                                item_in_dst = target_container.inventory[target_index]
                                                avail = item_in_dst.capacity - item_in_dst.load
                                                trans = min(avail, item_ref.load)
                                                item_in_dst.load += trans
                                                item_ref.load -= trans
                                            else:
                                                if target_index <= len(target_container.inventory):
                                                    target_container.inventory.insert(target_index, item_ref)
                                                else:
                                                    target_container.inventory.append(item_ref)
                                        
                                        transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                        game.player.start_action(tr('msg', "Looting"), transfer_time, do_slots_container_loot, xp_reward=0.5)
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return
                                
                                # Internal Drag Drop (Immediate)
                                if target_index < len(target_container.inventory):
                                    item_in_slot = target_container.inventory[target_index]
                                    if item_in_slot.can_stack_with(game.dragged_item):
                                        available = item_in_slot.capacity - item_in_slot.load
                                        transfer = min(available, game.dragged_item.load)
                                        item_in_slot.load += transfer
                                        game.dragged_item.load -= transfer
                                        if game.dragged_item.load <= 0: dropped_successfully = True
                                    else:
                                        if not check_container_weight_limit(target_container, game.dragged_item, item_in_slot):
                                            display_message(f"{target_container.name} {tr('msg', 'cannot carry that much weight.')}")
                                            dropped_successfully = False
                                        else:
                                            item_to_swap = target_container.inventory.pop(target_index)
                                            target_container.inventory.insert(target_index, game.dragged_item)
                                            game.dragged_item = item_to_swap
                                            dropped_successfully = False
                                else:
                                    if not check_container_weight_limit(target_container, game.dragged_item):
                                        display_message(f"{target_container.name} {tr('msg', 'cannot carry that much weight.')}")
                                        dropped_successfully = False
                                    else:
                                        target_container.inventory.insert(target_index, game.dragged_item)
                                        dropped_successfully = True
                                
                                break

                    elif modal['type'] == 'gear' and modal['rect'].collidepoint(mouse_pos):
                        if not dropped_successfully and 'tab_rects' in modal:
                            for i, tab_rect in enumerate(modal.get('tab_rects', [])):
                                if tab_rect.collidepoint(mouse_pos):
                                    tabs_data = modal.get('tabs_data', [])
                                    if i < len(tabs_data):
                                        target_label = tabs_data[i]['label']
                                        
                                        modal['active_tab'] = target_label
                                        
                                        target_container = modal.get('container_mapping', {}).get(target_label)
                                        if target_container:
                                            if is_external_source and is_container_on_player(target_container, game.player) and not check_player_weight(game.dragged_item):
                                                dropped_successfully = False
                                                break
                                            if check_recursive_containment(game.dragged_item, target_container):
                                                print("Recursion detected.")
                                                dropped_successfully = False
                                                break
                                            
                                            if getattr(target_container, 'allow_liquid', False):
                                                if not getattr(game.dragged_item, 'liquid', False):
                                                    print(f"This {target_container.name} only accepts liquids.")
                                                    display_message(f"This {target_container.name} only accepts liquids.")
                                                    dropped_successfully = False
                                                    break
                                            elif getattr(game.dragged_item, 'liquid', False):
                                                print("Liquid spills.")
                                                display_message(tr('msg', "Liquid spills."))
                                                dropped_successfully = True
                                                break

                                            if len(target_container.inventory) < (target_container.capacity or 0):
                                                 if not check_container_weight_limit(target_container, game.dragged_item):
                                                     print(f"{target_container.name} cannot carry that much weight.")
                                                     display_message(f"{target_container.name} {tr('msg', 'cannot carry that much weight.')}")
                                                     dropped_successfully = False
                                                     break

                                                 if is_external_source:
                                                     item_ref = game.dragged_item
                                                     
                                                     # --- FIX 2: VOID DROP PROTECTION ---
                                                     item_ref.rect.center = game.player.rect.center
                                                     if item_ref not in game.items_on_ground:
                                                         game.items_on_ground.append(item_ref)

                                                     def do_tab_loot():
                                                         if item_ref in game.items_on_ground:
                                                             game.items_on_ground.remove(item_ref)
                                                             
                                                         target_container.inventory.append(item_ref)
                                  
                                                     transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                                     game.player.start_action(tr('msg', "Looting"), transfer_time, do_tab_loot, xp_reward=0.5)
                                                     game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                                     return
                                                 else:
                                                     target_container.inventory.append(game.dragged_item)
                                                     dropped_successfully = True
                                            else:
                                                print(f"{target_container.name} is full.")
                                                display_message(f"{target_container.name} is full.")
                                                dropped_successfully = False
                                        
                                        break 
                            
                            if dropped_successfully:
                                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                return

                        active_tab = modal.get('active_tab', 'Gear')
                        
                        if active_tab == 'Gear':
                            if 'gear_slot_rects' in modal:
                                for slot_name, slot_rect in modal['gear_slot_rects'].items():
                                    if slot_rect.collidepoint(mouse_pos):
                                        dragged_item = game.dragged_item
                                        item_slot = getattr(dragged_item, 'slot', None)
                                        if item_slot == 'hand': item_slot = 'hands'
                                        
                                        # [CHANGED] Allow container and util items to bypass the strict slot name check for util slots
                                        is_util_slot = slot_name in ['util', 'util2', 'util3']
                                        is_container = getattr(dragged_item, 'item_type', '') == 'container'
                                        is_util_item = item_slot == 'util'

                                        if item_slot == slot_name or (is_util_slot and (is_container or is_util_item)):
                                            
                                            if getattr(dragged_item, 'liquid', False):
                                                print(f"The {dragged_item.name} spills and is lost.")
                                                display_message(f"{tr('msg', 'The')} {game.dragged_item.name} {tr('msg', 'spills and is lost.')}")
                                                dropped_successfully = True; break

                                            if is_external_source:
                                                if not check_player_weight(game.dragged_item):
                                                    dropped_successfully = False
                                                    break
                                                item_in_slot = game.player.clothes.get(slot_name)
                                                if item_in_slot:
                                                    print("Cannot swap items while equipping from external source.")
                                                    display_message(tr('msg', "Cannot swap items while equipping from external source."))
                                                    dropped_successfully = False
                                                    break

                                                item_ref = dragged_item
                                                # Convert "Campfire on" to "Campfire off" when looting
                                                if item_ref.name == "Campfire on":
                                                    new_item = Item.create_from_name("Campfire off")
                                                    if new_item:
                                                        new_item.durability = item_ref.durability
                                                        new_item.load = item_ref.load
                                                        item_ref = new_item
                                                        print("Campfire extinguished when picked up.")
                                                        display_message(tr('msg', "Campfire extinguished when picked up."))

                                                item_ref.rect.center = game.player.rect.center
                                                if item_ref not in game.items_on_ground:
                                                    game.items_on_ground.append(item_ref)

                                                def do_gear_equip():
                                                    if item_ref in game.items_on_ground:
                                                        game.items_on_ground.remove(item_ref)
                                                        
                                                    game.player.clothes[slot_name] = item_ref

                                                transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                                game.player.start_action("Equipping", transfer_time, do_gear_equip, xp_reward=0.5)
                                                
                                                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                                return

                                            item_in_slot = game.player.clothes.get(slot_name)
                                            game.player.clothes[slot_name] = dragged_item
                                            
                                            if item_in_slot:
                                                if type_orig == 'inventory' and 0 <= i_orig <= len(game.player.inventory):
                                                    game.player.inventory.insert(i_orig, item_in_slot)
                                                elif type_orig == 'belt' and 0 <= i_orig < len(game.player.belt):
                                                    game.player.belt[i_orig] = item_in_slot
                                                    item_in_slot.in_belt = True
                                                
                                                
                                                elif type_orig == 'gear':
                                                    game.player.clothes[i_orig] = item_in_slot
                                                elif (type_orig == 'container' or type_orig == 'nearby') and container_obj:
                                                     container_obj.inventory.insert(i_orig, item_in_slot)
                                                else:
                                                    game.player.inventory.append(item_in_slot)
                                            
                                            dropped_successfully = True
                                        else:
                                            dropped_successfully = False 
                                        break
                        elif active_tab in modal.get('container_mapping', {}):
                            container = modal['container_mapping'][active_tab]
                            if container:
                                if check_recursive_containment(game.dragged_item, container):
                                    print("Recursion detected: Cannot put the container inside itself.")
                                    display_message(tr('msg', "Cannot put the container inside itself."))
                                    dropped_successfully = False
                                    break
                                
                                if getattr(container, 'allow_liquid', False):
                                    if not getattr(game.dragged_item, 'liquid', False):
                                        print(f"This {container.name} only accepts liquids.")
                                        display_message(f"{tr('msg', 'This')} {container.name} {tr('msg', 'only accepts liquids.')}")
                                        dropped_successfully = False 
                                        break
                                elif getattr(game.dragged_item, 'liquid', False):
                                    print(f"The {game.dragged_item.name} spills and is lost.")
                                    display_message(f"{tr('msg', 'The')} {game.dragged_item.name} {tr('msg', 'spills and is lost.')}")
                                    dropped_successfully = True 
                                    break
                                
                                pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                                target_index = -1
                                for i in range(container.capacity or 0):
                                    if get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                                        target_index = i
                                        break
                                
                                if is_external_source:
                                    if is_container_on_player(container, game.player) and not check_player_weight(game.dragged_item):
                                        dropped_successfully = False
                                        break
                                    can_loot = False
                                    is_stack = False
                                    if target_index != -1 and target_index < len(container.inventory):
                                        item_in_slot = container.inventory[target_index]
                                        if item_in_slot.can_stack_with(game.dragged_item):
                                            can_loot = True; is_stack = True
                                        else:
                                            print("Cannot swap while looting.")
                                            display_message("Cannot swap while looting.")
                                            dropped_successfully = False
                                            break
                                    elif len(container.inventory) < (container.capacity or 0):
                                        if not check_container_weight_limit(container, game.dragged_item):
                                            print(f"{container.name} cannot carry that much weight.")
                                            display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                            dropped_successfully = False
                                        else:
                                            can_loot = True
                                    
                                    if can_loot:
                                        item_ref = game.dragged_item
                                        # --- FIX 2: VOID DROP PROTECTION ---
                                        item_ref.rect.center = game.player.rect.center
                                        if item_ref not in game.items_on_ground:
                                            game.items_on_ground.append(item_ref)

                                        def do_gear_container_loot():
                                            if item_ref in game.items_on_ground:
                                                game.items_on_ground.remove(item_ref)
                                                
                                            if is_stack:
                                                item_in_dst = container.inventory[target_index]
                                                avail = item_in_dst.capacity - item_in_dst.load
                                                trans = min(avail, item_ref.load)
                                                item_in_dst.load += trans
                                                item_ref.load -= trans
                                            else:
                                                if target_index != -1 and target_index <= len(container.inventory):
                                                    container.inventory.insert(target_index, item_ref)
                                                else:
                                                    container.inventory.append(item_ref)
                                        
                         
                                        transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                        game.player.start_action(tr('msg', "Looting"), transfer_time, do_gear_container_loot, xp_reward=0.5)
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return
                                
                                if target_index != -1:
                                    if target_index < len(container.inventory):
                                        item_in_slot = container.inventory[target_index]
                                        if item_in_slot.can_stack_with(game.dragged_item):
                                            available = item_in_slot.capacity - item_in_slot.load
                                            transfer = min(available, game.dragged_item.load)
                                            item_in_slot.load += transfer
                                            game.dragged_item.load -= transfer
                                            if game.dragged_item.load <= 0: dropped_successfully = True
                                        else:
                                            if not check_container_weight_limit(container, game.dragged_item, item_in_slot):
                                                print(f"{container.name} cannot carry that much weight.")
                                                display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                                dropped_successfully = False
                                            else:
                                                item_to_swap = container.inventory.pop(target_index)
                                                container.inventory.insert(target_index, game.dragged_item)
                                                game.dragged_item = item_to_swap
                                                dropped_successfully = False
                                    else:
                                        if not check_container_weight_limit(container, game.dragged_item):
                                            print(f"{container.name} cannot carry that much weight.")
                                            display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                            dropped_successfully = False
                                        else:
                                            container.inventory.insert(target_index, game.dragged_item)
                                            dropped_successfully = True
                                elif len(container.inventory) < (container.capacity or 0):
                                    if not check_container_weight_limit(container, game.dragged_item):
                                        print(f"{container.name} cannot carry that much weight.")
                                        display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                        dropped_successfully = False
                                    else:
                                        container.inventory.append(game.dragged_item)
                                        dropped_successfully = True
                        
                        if dropped_successfully: break
                    

                if dropped_successfully:
                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                    return

                # --- Drop on CONTAINER/NEARBY ---
                for modal in reversed(game.modals):
                    if modal['type'] in ['container', 'nearby'] and modal['rect'].collidepoint(mouse_pos):
                        container = None
                        if modal['type'] == 'container':
                            container = modal['item']
                        elif modal['type'] == 'nearby':
                            active_tab_label = modal.get('active_tab')
                            for tab_data in modal.get('tabs_data', []):
                                if tab_data['label'] == active_tab_label:
                                    container = tab_data['container']; break
                        
                        if not container: break
                        
                        if check_recursive_containment(game.dragged_item, container):
                            print("Recursion detected: Cannot put container into itself.")
                            display_message("Recursion detected: Cannot put container into itself.")
                            dropped_successfully = False
                            break

                        if getattr(container, 'allow_liquid', False):
                            if not getattr(game.dragged_item, 'liquid', False):
                                print(f"This {container.name} only accepts liquids.")
                                display_message(f"{tr('msg', 'This')} {container.name} {tr('msg', 'only accepts liquids.')}")
                                dropped_successfully = False 
                                break
                        elif getattr(game.dragged_item, 'liquid', False):
                            print(f"The {game.dragged_item.name} spills and is lost (container does not allow liquid).")
                            
                            display_message(f"{tr('msg', 'The')} {game.dragged_item.name} {tr('msg', 'spills and is lost.')}")
                            dropped_successfully = True 
                            break
                        
                        is_ground = getattr(container, 'item_type', '') == 'ground'
                        if not is_ground and modal['type'] == 'nearby' and modal.get('active_tab') == 'Ground':
                            is_ground = True

                        if is_ground:
                            target_index = -1
                            pos = modal['position']
                            if modal['type'] == 'nearby': pos = modal['content_rect'].topleft
                            
                            for i in range(container.capacity or 0):
                                if get_container_slot_rect(pos, i).collidepoint(mouse_pos):
                                    target_index = i
                                    break
                            
                            if target_index != -1 and target_index < len(container.inventory):
                                item_in_slot = container.inventory[target_index]
                                
                                if item_in_slot.can_stack_with(game.dragged_item):
                                    avail = item_in_slot.capacity - item_in_slot.load
                                    trans = min(avail, game.dragged_item.load)
                                    item_in_slot.load += trans
                                    game.dragged_item.load -= trans
                                    if game.dragged_item.load <= 0:
                                        dropped_successfully = True
                                else:
                                    if item_in_slot in game.items_on_ground:
                                        game.items_on_ground.remove(item_in_slot)
                                    
                                    game.dragged_item.rect.center = item_in_slot.rect.center
                                    game.dragged_item.x = game.dragged_item.rect.x
                                    game.dragged_item.y = game.dragged_item.rect.y
                                    game.items_on_ground.append(game.dragged_item)
                                    
                                    if type_orig == 'nearby' or type_orig == 'ground':
                                        game.items_on_ground.append(item_in_slot)
                                        dropped_successfully = True 
                                    else:
                                        game.dragged_item = item_in_slot
                                        dropped_successfully = False 
                            
                            else:
                                game.items_on_ground.append(game.dragged_item)

                                dx = game.dragged_item.rect.centerx - game.player.rect.centerx
                                dy = game.dragged_item.rect.centery - game.player.rect.centery
                                dist_chk_sq = dx*dx + dy*dy
                                if dist_chk_sq > (TILE_SIZE * 5) ** 2:
                                    off_x = random.randint(-16, 16)
                                    off_y = random.randint(-16, 16)
                                    game.dragged_item.rect.center = (game.player.rect.centerx + off_x, game.player.rect.centery + off_y)
                                    game.dragged_item.x = game.dragged_item.rect.x
                                    game.dragged_item.y = game.dragged_item.rect.y

                                dropped_successfully = True
                            
                            if dropped_successfully: break 
                            break

                        target_index = -1
                        pos = modal['position']
                        if modal['type'] == 'nearby': pos = modal['content_rect'].topleft
                        
                        for i in range(container.capacity or 0):
                            if get_container_slot_rect(pos, i).collidepoint(mouse_pos):
                                target_index = i
                                break
                        
                        use_loader = False
                        action_name = tr('msg', "Storing")
                        
                        if not is_external_source:
                            use_loader = True
                            action_name = tr('msg', "Storing")

                        if use_loader:
                            can_action = False
                            is_stack = False

                            if target_index != -1 and target_index < len(container.inventory):
                                item_in_slot = container.inventory[target_index]
                                if item_in_slot.can_stack_with(game.dragged_item):
                                    can_action = True; is_stack = True
                                else:
                                    print(f"Cannot swap items while {action_name.lower()}.")
                                    display_message(f"{tr('msg', 'Cannot swap items while')} {tr('msg', action_name.lower())}.")
                                    dropped_successfully = False
                                    break
                            elif len(container.inventory) < (container.capacity or 0):
                                if not check_container_weight_limit(container, game.dragged_item):
                                    print(f"{container.name} cannot carry that much weight.")
                                    display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                    dropped_successfully = False
                                    break
                                else:
                                    can_action = True
                            else:
                                print(f"{container.name} is full.")
                                dropped_successfully = False
                                break

                            if can_action:
                                item_ref = game.dragged_item
                                
                                # --- FIX 2: VOID DROP PROTECTION ---
                                item_ref.rect.center = game.player.rect.center
                                if item_ref not in game.items_on_ground:
                                    game.items_on_ground.append(item_ref)

                                def do_timed_action():
                                    if item_ref in game.items_on_ground:
                                        game.items_on_ground.remove(item_ref)
                                        
                                    if is_stack and target_index < len(container.inventory):
                                        item_in_dst = container.inventory[target_index]
                                        avail = item_in_dst.capacity - item_in_dst.load
                                        trans = min(avail, item_ref.load)
                                        item_in_dst.load += trans
                                        item_ref.load -= trans
                                        if item_ref.load > 0:
                                            pass
                                    else:
                                        if target_index != -1 and target_index <= len(container.inventory):
                                            container.inventory.insert(target_index, item_ref)
                                        else:
                                            container.inventory.append(item_ref)
                                
                                transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                game.player.start_action(action_name, transfer_time, do_timed_action, xp_reward=0.5)
                                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                return

                        if target_index != -1 and target_index < len(container.inventory):
                            item_in_slot = container.inventory[target_index]
                            if item_in_slot.can_stack_with(game.dragged_item):
                                available_space = item_in_slot.capacity - item_in_slot.load
                                transfer = min(available_space, game.dragged_item.load)
                                item_in_slot.load += transfer
                                game.dragged_item.load -= transfer
                                if game.dragged_item.load <= 0:
                                    dropped_successfully = True
                            else:
                                if not check_container_weight_limit(container, game.dragged_item, item_in_slot):
                                    print(f"{container.name} cannot carry that much weight.")
                                    display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                    dropped_successfully = False
                                else:
                                    item_to_swap = container.inventory.pop(target_index)
                                    container.inventory.insert(target_index, game.dragged_item)
                                    game.dragged_item = item_to_swap
                                    dropped_successfully = False 
                        elif len(container.inventory) < (container.capacity or 0):
                            if not check_container_weight_limit(container, game.dragged_item):
                                print(f"{container.name} cannot carry that much weight.")
                                display_message(f"{container.name} {tr('msg', 'cannot carry that much weight.')}")
                                dropped_successfully = False
                            else:
                                container.inventory.append(game.dragged_item)
                                dropped_successfully = True
                        else:
                            print(f"{container.name} is full.")
                            display_message(f"{container.name} {tr('msg', 'is full.')}")
                        
                        if dropped_successfully: break
                if dropped_successfully:
                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                    return

            # --- Bounce back or Drop on Ground ---
            if not dropped_successfully:
                is_over_modal = False
                for modal in game.modals:
                    if not modal.get('minimized', False) and modal['rect'].collidepoint(mouse_pos):
                        is_over_modal = True
                        break

                game_world_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
                if game.dragged_item:
                    if game_world_rect.collidepoint(mouse_pos) and not is_over_modal:
                        
                        is_safe_ground = False
                        if getattr(game.dragged_item, 'liquid', False):
                            grid_x = int(mouse_pos[0] // TILE_SIZE)
                            grid_y = int(mouse_pos[1] // TILE_SIZE)
                            tile_def = game.map_manager.get_tile_at(grid_x, grid_y)
                            if tile_def and tile_def.get('allow_liquid', False):
                                is_safe_ground = True
                                print(f"Placed {game.dragged_item.name} on {tile_def.get('name')}.")
                                display_message(f"{tr('msg', 'Placed')} {game.dragged_item.name} {tr('msg', 'on')} {tr('msg', tile_def.get('name', ''))}.")
                            else:
                                print(f"The {game.dragged_item.name} spills on the ground.")
                                display_message(f"{tr('msg', 'The')} {game.dragged_item.name} {tr('msg', 'spills on the ground.')}")
                                dropped_successfully = True 
                        
                        if (not getattr(game.dragged_item, 'liquid', False)) or is_safe_ground:
                            offset_x = random.randint(-8, 8)
                            offset_y = random.randint(-8, 8)
                            
                            game.dragged_item.rect.center = (
                                game.player.rect.centerx + offset_x, 
                                game.player.rect.centery + offset_y
                            )
                            game.dragged_item.x = game.dragged_item.rect.x
                            game.dragged_item.y = game.dragged_item.rect.y
                            
                            game.items_on_ground.append(game.dragged_item)
                            dropped_successfully = True
                    
                    if not dropped_successfully and game.dragged_item:
                        # BOUNCE BACK
                        if type_orig == 'inventory' and 0 <= i_orig <= len(game.player.inventory):
                            game.player.inventory.insert(i_orig, game.dragged_item)
                        elif type_orig == 'belt' and 0 <= i_orig < len(game.player.belt):
                            game.player.belt[i_orig] = game.dragged_item
                            game.dragged_item.in_belt = True
                        
                        
                        elif type_orig == 'gear':
                            slot_name = i_orig 
                            game.player.clothes[slot_name] = game.dragged_item
                        elif type_orig == 'container' and container_obj is not None:
                            container_obj.inventory.insert(i_orig, game.dragged_item)
                        elif type_orig == 'nearby' and container_obj is not None:
                            container_obj.inventory.insert(i_orig, game.dragged_item)
                            if getattr(container_obj, 'item_type', '') == 'ground':
                                game.items_on_ground.append(game.dragged_item)
                        elif 'stack_split' in type_orig:
                            try:
                                if type_orig == 'inventory_stack_split':
                                    game.player.inventory[i_orig].load += game.dragged_item.load
                                elif type_orig == 'belt_stack_split':
                                    game.player.belt[i_orig].load += game.dragged_item.load
                                elif type_orig == 'gear_stack_split':
                                    game.player.clothes[i_orig].load += game.dragged_item.load
                                elif type_orig == 'container_stack_split':
                                    container_obj.inventory[i_orig].load += game.dragged_item.load
                                elif type_orig == 'nearby_stack_split':
                                    container_obj.inventory[i_orig].load += game.dragged_item.load
                            except Exception as e:
                                print(f"Stack bounce back failed: {e}")
                        elif type_orig == 'vehicle_equipment':
                            vehicle = container_info[0]
                            slot_name = i_orig
                            vehicle.equipment[slot_name] = game.dragged_item
                            vehicle.update_stats_from_equipment()
                        

                        else:
                            game.player.inventory.append(game.dragged_item) 

        game.is_dragging = False
        game.dragged_item = None
        game.drag_origin = None
        game.drag_candidate = None


def find_item_at_pos(game, mouse_pos):
    for i, item in enumerate(game.player.belt):
        if item and get_belt_hud_slot_rect(i).collidepoint(mouse_pos):
            return item

    for modal in reversed(game.modals):
        if not modal['rect'].collidepoint(mouse_pos):
            continue

        if modal['type'] == 'inventory':
            if modal.get('active_tab', 'Inventory') == 'Inventory':
                for i, item in enumerate(game.player.inventory):
                    if item and get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                        return item
                for i, item in enumerate(game.player.belt):
                    if item and get_belt_slot_rect_in_modal(i, modal['position']).collidepoint(mouse_pos):
                        return item
                
                
            
            elif modal.get('active_tab') in modal.get('container_mapping', {}):
                container = modal['container_mapping'][modal['active_tab']]
                if container:
                    pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                    for i, item in enumerate(container.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            return item
            
        elif modal['type'] == 'container':
            container = modal['item']
            for i, item in enumerate(container.inventory):
                if item and get_container_slot_rect(modal['position'], i).collidepoint(mouse_pos):
                    return item

        elif modal['type'] == 'gear':
            active_tab = modal.get('active_tab', 'Gear')
            if active_tab == 'Gear':
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            return game.player.clothes.get(slot_name)
            elif active_tab in modal.get('container_mapping', {}):
                container = modal['container_mapping'][active_tab]
                if container:
                    # Offset Y+80
                    pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                    for i, item in enumerate(container.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            return item

        elif modal['type'] == 'nearby':
            active_tab_label = modal.get('active_tab')
            active_container = None
            tabs_data = modal.get('tabs_data', [])
            for tab_data in tabs_data:
                if tab_data['label'] == active_tab_label:
                    active_container = tab_data['container']
                    break
            
            content_rect = modal.get('content_rect')
            if active_container and hasattr(active_container, 'inventory') and content_rect:
                pos = content_rect.topleft
                for i, item in enumerate(active_container.inventory):
                    if item and get_container_slot_rect(pos, i).collidepoint(mouse_pos):
                        return item
        
        return None

    return None

def handle_mouse_motion(game, event, mouse_pos):
    if hasattr(event, 'pos'):
        mouse_pos = event.pos

    if game.player:
        player_screen_x = GAME_OFFSET_X + GAME_WIDTH / 2
        player_screen_y = GAME_HEIGHT / 2
        dx = mouse_pos[0] - player_screen_x
        dy = mouse_pos[1] - player_screen_y
        game.player.aim_angle = math.atan2(-dy, dx) 


    if getattr(game, 'context_menu', {}).get('active', False):
        game.hovered_item = None
    else:
        game.hovered_item = find_item_at_pos(game, mouse_pos)

    game.hovered_container = None

    world_pos = game.screen_to_world(mouse_pos)
    

    for container in game.containers:
        if container.rect.collidepoint(world_pos):
            game.hovered_container = container
            break

    for modal in reversed(game.modals):
        if modal.get('is_dragging_scrollbar') and modal['type'] == 'crafting':
             track = modal.get('crafting_track_rect')
             handle = modal.get('crafting_handle_rect')
             
             if track and handle:
                 track_y = track.y
                 track_h = track.height
                 handle_h = handle.height
                 
                 click_offset = modal.get('scrollbar_click_offset_y', 0)
                 target_handle_y = mouse_pos[1] - click_offset
                 
                 available_space = track_h - handle_h
                 if available_space > 0:
                     relative_y = target_handle_y - track_y
                     pct = relative_y / available_space
                     pct = max(0.0, min(1.0, pct))
                     
                     total = modal.get('crafting_total_items', 0)
                     visible = modal.get('crafting_visible_items', 14)
                     max_scroll = max(0, total - visible)
                     
                     modal['crafting_scroll_offset'] = int(pct * max_scroll)
             return


    for modal in reversed(game.modals):
        if modal.get('is_dragging_scrollbar'):
            mouse_delta_y = mouse_pos[1] - modal['scrollbar_drag_last_y']
            modal['scrollbar_drag_last_y'] = mouse_pos[1]
            
            content_rect = modal.get('content_rect')
            max_scroll = modal.get('max_scroll_offset', 0)
            handle_rect = modal.get('scrollbar_handle_rect')
            
            if content_rect and max_scroll > 0 and handle_rect:
                content_height = content_rect.height
                track_height = content_height - handle_rect.height 
                
                if track_height > 0:
                    scroll_per_pixel = max_scroll / track_height
                    current_offset = modal.get('scroll_offset_y', 0)
                    new_offset = current_offset + (mouse_delta_y * scroll_per_pixel)
                    modal['scroll_offset_y'] = max(0, min(new_offset, max_scroll))
            return

    if game.drag_candidate and not game.is_dragging:
        dist = math.hypot(mouse_pos[0] - game.drag_start_pos[0], mouse_pos[1] - game.drag_start_pos[1])
        if dist > game.DRAG_THRESHOLD:
            game.is_dragging = True
            item_to_drag, origin_tuple = game.drag_candidate
            i_orig, type_orig, *container_info = origin_tuple
            
            keys = pygame.key.get_pressed()
            is_splitting = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])

            if hasattr(item_to_drag, 'is_stackable') and item_to_drag.is_stackable() and item_to_drag.load > 1 and is_splitting:
                item_to_drag.load -= 1
                new_item = Item.create_from_name(item_to_drag.name)

                if not new_item:
                    item_to_drag.load += 1
                    game.drag_candidate = None
                    return

                new_item.load = 1
                new_item.durability = item_to_drag.durability
                game.dragged_item = new_item

                if type_orig == 'gear':
                    game.drag_origin = (i_orig, "gear_stack_split", *container_info)
                else:
                    game.drag_origin = (i_orig, f"{type_orig}_stack_split", *container_info)
            
            else:
                game.dragged_item, game.drag_origin = game.drag_candidate
                if type_orig == 'inventory':
                    game.player.inventory.pop(i_orig)
                elif type_orig == 'belt':
                    if game.player.active_weapon == game.player.belt[i_orig]:
                        game.player.active_weapon = None
                    game.player.belt[i_orig] = None
                    game.dragged_item.in_belt = False

                
                elif type_orig == 'gear':
                    slot_name = i_orig 
                    game.player.clothes[slot_name] = None 
                elif type_orig == 'container':
                    container_obj = container_info[0]
                    container_obj.inventory.pop(i_orig)
                    container_obj._drag_locked = True
                elif type_orig == 'nearby':
                    container_obj = container_info[0]
                    container_obj.inventory.pop(i_orig)
                    container_obj._drag_locked = True
                    if getattr(container_obj, 'item_type', '') == 'ground':
                        if item_to_drag in game.items_on_ground:
                            game.items_on_ground.remove(item_to_drag)
                        # Convert "Campfire on" to "Campfire off" when dragging from ground
                        if item_to_drag.name == "Campfire on":
                            new_item = Item.create_from_name("Campfire off")
                            if new_item:
                                new_item.durability = item_to_drag.durability
                                new_item.load = item_to_drag.load
                                new_item.rect.center = item_to_drag.rect.center
                                new_item.x = item_to_drag.x
                                new_item.y = item_to_drag.y
                                game.dragged_item = new_item
                                print("Campfire extinguished when picked up (drag).")
                                display_message(tr('msg', "Campfire extinguished when picked up."))
                                
                elif type_orig == 'vehicle_equipment':
                    vehicle = container_info[0]
                    slot_name = i_orig
                    vehicle.equipment[slot_name] = None
                    vehicle.update_stats_from_equipment()


            game.drag_candidate = None 

    for modal in reversed(game.modals):
        if modal['is_dragging']:
            new_x = mouse_pos[0] - modal['drag_offset'][0]
            new_y = mouse_pos[1] - modal['drag_offset'][1]
            is_minimized = modal.get('minimized', False)
            header_height = 35
            modal_width = modal['rect'].width
            modal_height = header_height if is_minimized else modal['rect'].height
            clamped_x = max(0, min(new_x, GAME_WIDTH - modal_width))
            clamped_y = max(0, min(new_y, GAME_HEIGHT - modal_height))
            modal['position'] = (clamped_x, clamped_y)
            modal['rect'].topleft = modal['position']

            if hasattr(game, 'last_modal_positions'):
                game.last_modal_positions[modal['type']] = modal['position']

def handle_left_click_drag_candidate(game, mouse_pos):
    if game.player.action_timer > 0:
        return
    topmost_modal = None
    for modal in reversed(game.modals):
        if modal['rect'].collidepoint(mouse_pos):
            topmost_modal = modal
            break
    
    if not topmost_modal:
        return 

    modal = topmost_modal

    header_drag_area = pygame.Rect(modal['rect'].x, modal['rect'].y, max(1, modal['rect'].width - 60), 35)
    
    if header_drag_area.collidepoint(mouse_pos):
        modal['is_dragging'] = True
        modal['drag_offset'] = (mouse_pos[0] - modal['rect'].x, mouse_pos[1] - modal['rect'].y)
        return

    if modal['type'] == 'vehicle' and modal.get('active_tab') == 'Mechanics':
        if 'equipment_rects' in modal:
            for slot_name, slot_rect in modal['equipment_rects'].items():
                if slot_rect.collidepoint(mouse_pos):
                    vehicle = modal['vehicle']
                    item = vehicle.equipment.get(slot_name)
                    if item:
                        game.drag_candidate = (item, (slot_name, 'vehicle_equipment', vehicle))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                        return

    if modal['type'] == 'nearby':
        active_tab_label = modal.get('active_tab')
        active_container = None
        for tab_data in modal.get('tabs_data', []):
            if tab_data['label'] == active_tab_label:
                active_container = tab_data['container']
                break
        
        if active_container and hasattr(active_container, 'inventory'):
            content_rect = modal.get('content_rect')
            if content_rect and content_rect.collidepoint(mouse_pos):
                pos = content_rect.topleft
                for i, item in enumerate(active_container.inventory):
                    if item: 
                        slot_rect = get_container_slot_rect(pos, i)
                        if slot_rect.collidepoint(mouse_pos):
                            game.drag_candidate = (item, (i, 'nearby', active_container, modal['id']))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            return

    elif modal['type'] == 'container':
        container_item = modal['item']
        for i, item in enumerate(container_item.inventory):
            if item:
                slot_rect = get_container_slot_rect(modal['position'], i)
                if slot_rect.collidepoint(mouse_pos):
                    game.drag_candidate = (item, (i, 'container', container_item, modal['id']))
                    game.drag_start_pos = mouse_pos
                    game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                    return 

    elif modal['type'] == 'inventory':
        if modal.get('active_tab', 'Inventory') == 'Inventory':
            for i, item in enumerate(game.player.inventory):
                if item:
                    slot_rect = get_inventory_slot_rect(i, modal['position'])
                    if slot_rect.collidepoint(mouse_pos):
                        game.drag_candidate = (item, (i, 'inventory'))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                        return 

            for i, item in enumerate(game.player.belt):
                if item:
                    slot_rect = get_belt_slot_rect_in_modal(i, modal['position'])
                    if slot_rect.collidepoint(mouse_pos):
                        game.drag_candidate = (item, (i, 'belt'))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                        return 


        
        elif modal.get('active_tab') in modal.get('container_mapping', {}):
            container = modal['container_mapping'][modal['active_tab']]
            if container:
                pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                for i, item in enumerate(container.inventory):
                    if item:
                        slot_rect = get_container_slot_rect(pos_for_calc, i)
                        if slot_rect.collidepoint(mouse_pos):
                            game.drag_candidate = (item, (i, 'container', container, modal['id']))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            return

        elif modal.get('active_tab') == 'Gear':
            if 'gear_slot_rects' in modal:
                for slot_name, slot_rect in modal['gear_slot_rects'].items():
                    if slot_rect.collidepoint(mouse_pos):
                        item = game.player.clothes.get(slot_name)
                        if item:
                            game.drag_candidate = (item, (slot_name, 'gear'))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            return 

    elif modal['type'] == 'slots':
        for slot_data in modal.get('slot_rects', []):
            if slot_data['rect'].collidepoint(mouse_pos):
                c = slot_data['container']
                i = slot_data['index']
                if i < len(c.inventory):
                    item = c.inventory[i]
                    game.drag_candidate = (item, (i, 'container', c))
                    game.drag_start_pos = mouse_pos
                    game.drag_offset = (mouse_pos[0] - slot_data['rect'].x, mouse_pos[1] - slot_data['rect'].y)
                    return

    elif modal['type'] == 'gear':
        active_tab = modal.get('active_tab', 'Gear')
        if active_tab == 'Gear':
            if 'gear_slot_rects' in modal:
                for slot_name, slot_rect in modal['gear_slot_rects'].items():
                    if slot_rect.collidepoint(mouse_pos):
                        item = game.player.clothes.get(slot_name)
                        if item:
                            game.drag_candidate = (item, (slot_name, 'gear'))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            return
        elif active_tab in modal.get('container_mapping', {}):
            container = modal['container_mapping'][active_tab]
            if container:
                # Offset Y+80
                pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                for i, item in enumerate(container.inventory):
                    if item:
                        slot_rect = get_container_slot_rect(pos_for_calc, i)
                        if slot_rect.collidepoint(mouse_pos):
                            game.drag_candidate = (item, (i, 'container', container, modal['id']))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            return