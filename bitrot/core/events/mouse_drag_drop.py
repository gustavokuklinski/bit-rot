# core/events/mouse_drag_drop.py

import pygame
import random
from core.data.config import *
from core.entities.item.item import Item
from core.entities.item.item_data import ITEM_TEMPLATES
from core.ui.inventory_modal import get_inventory_slot_rect, get_belt_hud_slot_rect
from core.ui.container_modal import get_container_slot_rect
from core.messages import display_message
from core.data.localization import tr
from core.entities.item.item_helpers import (
    does_allow_liquid, is_infinite_liquid_source,
    get_container_max_liquid, get_container_available_liquid,
    add_item_to_container_inventory, is_container_on_player
)
from core.events.mouse_drag_utils import (
    check_recursive_containment, check_container_weight_limit,
    check_player_weight, _remove_from_ground_and_sync,
    _sync_source_container, _sync_container_to_server,
    return_remainder_to_origin
)

def handle_mouse_up(game, event, mouse_pos):
    for modal in reversed(game.modals):
        modal['is_dragging'] = False
        modal['is_dragging_scrollbar'] = False
        modal['is_dragging_map'] = False
        modal['is_scrolling_content'] = False

    from core.draw.camera import update_messages_modal_elastic_width
    update_messages_modal_elastic_width(game)

    if event.button != 1:
        return

    if game.drag_origin:
        _, type_orig, *container_info = game.drag_origin
        if type_orig in ('container', 'nearby') and container_info:
            container_info[0]._drag_locked = False

    dropped_successfully = False

    if game.is_dragging or game.drag_candidate:
        if game.dragged_item:
            i_orig, type_orig, *container_info = game.drag_origin
            container_obj = container_info[0] if type_orig in (
                'container', 'nearby', 'inventory_stack_split', 'belt_stack_split',
                'container_stack_split', 'nearby_stack_split', 'gear_stack_split'
            ) and container_info else None 

            is_raw_external = type_orig in ['nearby', 'nearby_stack_split', 'vehicle_equipment']
            if type_orig in ['container', 'container_stack_split']:
                if not is_container_on_player(container_obj, game.player):
                    is_raw_external = True
            is_external_source = is_raw_external

            # --- Target 1: Vehicle Equipment Slots ---
            for modal in reversed(game.modals):
                if modal['type'] == 'vehicle' and modal.get('active_tab') == 'Mechanics':
                    if 'equipment_rects' in modal:
                        for slot_name, slot_rect in modal['equipment_rects'].items():
                            if slot_rect.collidepoint(mouse_pos):
                                vehicle = modal['vehicle']
                                valid_drop = vehicle.can_equip(game.dragged_item, slot_name)
                                if valid_drop:
                                    item_ref = game.dragged_item
                                    existing_item = vehicle.equipment.get(slot_name)
                                    if existing_item and existing_item.can_stack_with(item_ref):
                                        item_ref.rect.center = game.player.rect.center
                                        if item_ref not in game.items_on_ground:
                                            game.items_on_ground.append(item_ref)
                                            
                                        def do_stack_vehicle():
                                            _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                            available = existing_item.capacity - existing_item.load
                                            transfer = min(available, item_ref.load)
                                            existing_item.load += transfer
                                            item_ref.load -= transfer
                                            vehicle.update_stats_from_equipment()
                                            
                                            if item_ref.load > 0:
                                                if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                                    game.player.inventory.append(item_ref)
                                                else:
                                                    game.items_on_ground.append(item_ref)
                                                    item_ref.rect.center = game.player.rect.center
                                        
                                        action_name = tr('msg', "Refueling") if slot_name == 'fuel' else tr('msg', "Transferring")
                                        transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                        game.player.start_action(action_name, transfer_time, do_stack_vehicle, xp_reward=0.5)
                                        
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return

                                    item_ref.rect.center = game.player.rect.center
                                    if item_ref not in game.items_on_ground:
                                        game.items_on_ground.append(item_ref)
                                    
                                    def do_equip_vehicle():
                                        _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                        old_item = vehicle.add_equipment(item_ref, slot_name)
                                        if old_item:
                                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                                game.player.inventory.append(old_item)
                                            else:
                                                game.items_on_ground.append(old_item)
                                                old_item.rect.center = game.player.rect.center
                                    
                                    action_name = tr('msg', "Equipping") if not is_external_source else tr('msg', "Transferring")
                                    transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                    game.player.start_action(action_name, transfer_time, do_equip_vehicle, xp_reward=0.5)
                                    
                                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                    return
                                else:
                                    display_message(f"{tr('msg', 'Cannot place')} {game.dragged_item.name} {tr('msg', 'in')} {slot_name} {tr('msg', 'slot.')}")
                                break
                    if dropped_successfully or (not dropped_successfully and game.dragged_item):
                        break
            
            if dropped_successfully:
                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                return 

            # --- Target 2: Belt HUD Slots ---
            is_over_modal = any(modal.get('rect') and modal['rect'].collidepoint(mouse_pos) for modal in game.modals)
            for i_target in range(len(game.player.belt)):
                is_hud_slot = (not is_over_modal) and get_belt_hud_slot_rect(i_target, game=game).collidepoint(mouse_pos)

                if is_hud_slot:
                    if not getattr(game.dragged_item, 'allow_belt', False):
                        display_message(f"{tr('msg', 'Cannot place')} {game.dragged_item.name} {tr('msg', 'to belt.')}")
                        dropped_successfully = False
                        break
                    
                    item_in_slot = game.player.belt[i_target]
                    if item_in_slot and check_recursive_containment(game.dragged_item, item_in_slot):
                        display_message(tr('msg', "Cannot drop a container into itself."))
                        dropped_successfully = False
                        break
                    
                    if getattr(game.dragged_item, 'liquid', False):
                        display_message(tr('msg', f"The {game.dragged_item.name} spills and is lost."))
                        dropped_successfully = True 
                        break

                    if is_external_source:
                        if not check_player_weight(game.dragged_item):
                            dropped_successfully = False
                            break
                        if item_in_slot is None or item_in_slot.can_stack_with(game.dragged_item):
                            item_ref = game.dragged_item
                            if item_ref.name in ["Campfire on", "Lantern on"]:
                                new_item = Item.create_from_name(item_ref.name.replace(" on", " off"))
                                if new_item:
                                    new_item.durability = item_ref.durability
                                    new_item.load = item_ref.load
                                    item_ref = new_item
                                    display_message(tr('msg', f"{item_ref.name.split(' ')[0]} extinguished when picked up."))
                                    
                            item_ref.rect.center = game.player.rect.center
                            if item_ref not in game.items_on_ground:
                                game.items_on_ground.append(item_ref)

                            def do_belt_loot():
                                _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                _sync_source_container(game, container_obj)

                                if game.player.belt[i_target] is None:
                                    game.player.belt[i_target] = item_ref
                                    item_ref.in_belt = True
                                elif game.player.belt[i_target].can_stack_with(item_ref):
                                    avail = game.player.belt[i_target].capacity - game.player.belt[i_target].load
                                    trans = min(avail, item_ref.load)
                                    game.player.belt[i_target].load += trans
                                    item_ref.load -= trans
                                
                                if game and hasattr(game, 'sound_manager'):
                                    game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)

                            transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                            game.player.start_action(tr('msg', "Looting"), transfer_time, do_belt_loot, xp_reward=0.5)
                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                            return
                        else:
                            dropped_successfully = False
                            break

                    if item_in_slot is None:
                        game.player.belt[i_target] = game.dragged_item
                        game.dragged_item.in_belt = True
                        dropped_successfully = True
                        if game and hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound('equip_belt.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)

                    elif item_in_slot.can_stack_with(game.dragged_item):
                        available_space = item_in_slot.capacity - item_in_slot.load
                        transfer = min(available_space, game.dragged_item.load)
                        item_in_slot.load += transfer
                        game.dragged_item.load -= transfer
                        if game.dragged_item.load <= 0:
                            dropped_successfully = True

                        if game and hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound('equip_belt.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)

                    else:
                        item_to_swap = item_in_slot
                        game.player.belt[i_target] = game.dragged_item
                        game.dragged_item.in_belt = True
                        game.dragged_item = item_to_swap 
                        game.dragged_item.in_belt = False
                        dropped_successfully = False

                        if game and hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound('equip_belt.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)

                    if dropped_successfully: break
            if dropped_successfully:
                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                return

            # --- Target 3: Modals (Inventory, Gear, Slots, Nearby, Containers, etc.) ---
            for modal in reversed(game.modals):
                if modal.get('type') == 'npc_dialog' and modal.get('active_tab_index') == 2:
                    drop_zone = modal.get('trade_drop_zone_rect')
                    if drop_zone and drop_zone.collidepoint(mouse_pos):
                        modal['trade_offered_item'] = game.dragged_item
                        modal['trade_message'] = ""
                        
                        if type_orig == 'inventory':
                            game.player.inventory.insert(i_orig, game.dragged_item)
                        elif type_orig == 'belt':
                            game.player.belt[i_orig] = game.dragged_item
                            game.dragged_item.in_belt = True
                        elif type_orig == 'gear':
                            game.player.clothes[i_orig] = game.dragged_item
                        else:
                            game.player.inventory.append(game.dragged_item)
                            
                        dropped_successfully = True
                        break

                tab_drop_handled = False
                if 'tab_rects' in modal and modal['tab_rects']:
                    for i, tab_rect in enumerate(modal['tab_rects']):
                        if tab_rect.collidepoint(mouse_pos):
                            target_container = None
                            target_list = None
                            label = modal['tabs_data'][i]['label']
                            
                            if modal['type'] == 'inventory':
                                if label == 'Inventory':
                                    target_list = game.player.inventory
                                elif label in modal.get('container_mapping', {}):
                                    target_container = modal['container_mapping'][label]
                            
                            elif modal['type'] == 'nearby':
                                if i < len(modal['tabs_data']):
                                    target_container = modal['tabs_data'][i]['container']
                                    
                            elif modal['type'] == 'gear':
                                if label != 'Gear' and label in modal.get('container_mapping', {}):
                                    target_container = modal['container_mapping'][label]

                            modal['active_tab'] = label
                            
                            if target_container:
                                if is_external_source and is_container_on_player(target_container, game.player) and not check_player_weight(game.dragged_item):
                                    dropped_successfully = False
                                    tab_drop_handled = True
                                    break
                                    
                                if check_recursive_containment(game.dragged_item, target_container):
                                    dropped_successfully = False
                                    tab_drop_handled = True
                                    break
                                    
                                elif does_allow_liquid(target_container) and not getattr(game.dragged_item, 'liquid', False):
                                    display_message(tr('msg', "Container only accepts liquids."))
                                    dropped_successfully = False
                                    tab_drop_handled = True
                                    break
                                    
                                elif getattr(game.dragged_item, 'liquid', False) and not does_allow_liquid(target_container):
                                    display_message(tr('msg', "Liquid spills."))
                                    dropped_successfully = True
                                    tab_drop_handled = True
                                    break

                                is_drag_liq = getattr(game.dragged_item, 'liquid', False)
                                target_max_liq = get_container_max_liquid(target_container) if is_drag_liq else None
                                
                                stack_it = None
                                if hasattr(target_container, 'inventory'):
                                    for it in target_container.inventory:
                                        if it and it.can_stack_with(game.dragged_item):
                                            stack_it = it
                                            break

                                if is_drag_liq and target_max_liq is not None:
                                    avail_liq = get_container_available_liquid(target_container, target_item=stack_it)
                                    if avail_liq <= 0:
                                        display_message(tr('msg', "Container is full."))
                                        dropped_successfully = False
                                        tab_drop_handled = True
                                        break

                                can_fit_in_container = (stack_it is not None) or (len(target_container.inventory) < (target_container.capacity or 0))

                                if can_fit_in_container:
                                    if not check_container_weight_limit(target_container, game.dragged_item):
                                        display_message(f"{tr('item', target_container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                        dropped_successfully = False
                                        tab_drop_handled = True
                                        break

                                    if is_external_source:
                                        item_ref = game.dragged_item
                                        if item_ref.name in ["Campfire on", "Lantern on"]:
                                            new_item = Item.create_from_name(item_ref.name.replace(" on", " off"))
                                            if new_item:
                                                new_item.durability = item_ref.durability
                                                new_item.load = item_ref.load
                                                item_ref = new_item
                                                display_message(tr('msg', f"{item_ref.name.split(' ')[0]} extinguished when picked up."))
                                                 
                                        item_ref.rect.center = game.player.rect.center
                                        if item_ref not in game.items_on_ground:
                                            game.items_on_ground.append(item_ref)

                                        def do_tab_loot():
                                            trans, rem, ok = add_item_to_container_inventory(
                                                target_container, item_ref, target_index=-1, is_stack=(stack_it is not None)
                                            )
                                            if ok:
                                                _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                                if rem > 0 and not is_infinite_liquid_source(container_obj):
                                                    return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                                                _sync_source_container(game, container_obj)
                                            else:
                                                return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                                    
                                        transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                        game.player.start_action(tr('msg', "Looting"), transfer_time, do_tab_loot, xp_reward=0.5)
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return
                                    else:
                                        trans, rem, ok = add_item_to_container_inventory(
                                            target_container, game.dragged_item, target_index=-1, is_stack=(stack_it is not None)
                                        )
                                        if ok:
                                            if rem > 0 and not is_infinite_liquid_source(container_obj):
                                                return_remainder_to_origin(game, game.dragged_item, type_orig, i_orig, container_obj)
                                            game.dragged_item = None
                                            dropped_successfully = True
                                        else:
                                            dropped_successfully = False
                                else:
                                    display_message(f"{tr('item', target_container.name)} {tr('msg', 'is full.')}")
                                    dropped_successfully = False
                                    
                            elif target_list is not None:
                                if is_external_source and not check_player_weight(game.dragged_item):
                                    dropped_successfully = False
                                    tab_drop_handled = True
                                    break
                                    
                                if getattr(game.dragged_item, 'liquid', False):
                                    display_message(tr('msg', "Liquid spills."))
                                    dropped_successfully = True
                                    
                                elif len(target_list) < game.player.get_total_inventory_slots():
                                    if is_external_source:
                                        item_ref = game.dragged_item
                                        if item_ref.name in ["Campfire on", "Lantern on"]:
                                            new_item = Item.create_from_name(item_ref.name.replace(" on", " off"))
                                            if new_item:
                                                new_item.durability = item_ref.durability
                                                new_item.load = item_ref.load
                                                item_ref = new_item
                                                display_message(tr('msg', f"{item_ref.name.split(' ')[0]} extinguished when picked up."))
                                        item_ref.rect.center = game.player.rect.center
                                        if item_ref not in game.items_on_ground:
                                            game.items_on_ground.append(item_ref)

                                        def do_tab_inv_loot():
                                            _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                            target_list.append(item_ref)
                                        
                                        if game and hasattr(game, 'sound_manager'):
                                            game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)
                         
                                        transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                        game.player.start_action(tr('msg', "Looting"), transfer_time, do_tab_inv_loot, xp_reward=0.5)
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return
                                    else:
                                        target_list.append(game.dragged_item)
                                        dropped_successfully = True
                                        if game and hasattr(game, 'sound_manager'):
                                            game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)
                                else:
                                    display_message(tr('msg', "Inventory is full."))
                                    dropped_successfully = False
                            
                            tab_drop_handled = True
                            break
                
                if tab_drop_handled:
                    if dropped_successfully:
                        break 
                        
                if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
                    if modal.get('active_tab', 'Inventory') == 'Inventory':
                        if not dropped_successfully:
                            target_index = -1
                            for i in range(15): 
                                if get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                                    target_index = i
                                    break
                            
                            if target_index != -1 and getattr(game.dragged_item, 'liquid', False):
                                display_message(tr('msg', "Liquid spills."))
                                dropped_successfully = True
                            
                            elif target_index != -1: 
                                if target_index < len(game.player.inventory):
                                    item_in_slot = game.player.inventory[target_index]
                                    
                                    if check_recursive_containment(game.dragged_item, item_in_slot):
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
                                                _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                                avail = item_in_slot.capacity - item_in_slot.load
                                                trans = min(avail, item_ref.load)
                                                item_in_slot.load += trans
                                                item_ref.load -= trans
                                                if game and hasattr(game, 'sound_manager'):
                                                    game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)

                                            transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                            game.player.start_action(tr('msg', "Looting"), transfer_time, do_inv_stack, xp_reward=0.5)
                                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                            return
                                        else:
                                            dropped_successfully = False
                                            break

                                    if item_in_slot.can_stack_with(game.dragged_item):
                                        available_space = item_in_slot.capacity - item_in_slot.load
                                        transfer = min(available_space, game.dragged_item.load)
                                        item_in_slot.load += transfer
                                        game.dragged_item.load -= transfer
                                        if game.dragged_item.load <= 0:
                                            dropped_successfully = True
                                        if game and hasattr(game, 'sound_manager'):
                                            game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)

                                    else:
                                        item_to_swap = game.player.inventory.pop(target_index)
                                        game.player.inventory.insert(target_index, game.dragged_item)
                                        game.dragged_item = item_to_swap
                                        dropped_successfully = False 
                                        if game and hasattr(game, 'sound_manager'):
                                            game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)

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
                                            _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                            _sync_source_container(game, container_obj)
                                            game.player.inventory.insert(target_index, item_ref)
                                            if game and hasattr(game, 'sound_manager'):
                                                game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)
                                        
                                        transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                        game.player.start_action(tr('msg', "Looting"), transfer_time, do_inv_loot, xp_reward=0.5)
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return

                                    game.player.inventory.insert(target_index, game.dragged_item)
                                    dropped_successfully = True
                                    if game and hasattr(game, 'sound_manager'):
                                        game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)
                            
                            elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                                if getattr(game.dragged_item, 'liquid', False):
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
                                            _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                            game.player.inventory.append(item_ref)
                                            if game and hasattr(game, 'sound_manager'):
                                                game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)

                                        transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                        game.player.start_action(tr('msg', "Looting"), transfer_time, do_inv_append, xp_reward=0.5)
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return

                                    game.player.inventory.append(game.dragged_item)
                                    dropped_successfully = True
                                    if game and hasattr(game, 'sound_manager'):
                                        game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)
                            
                            if dropped_successfully: break
                    
                    elif modal.get('active_tab') in modal.get('container_mapping', {}):
                        container = modal['container_mapping'][modal['active_tab']]
                        if container:
                            if check_recursive_containment(game.dragged_item, container):
                                dropped_successfully = False
                                break
                            
                            if does_allow_liquid(container) and not getattr(game.dragged_item, 'liquid', False):
                                display_message(tr('msg', "Container only accepts liquids."))
                                dropped_successfully = False 
                                break
                            elif getattr(game.dragged_item, 'liquid', False) and not does_allow_liquid(container):
                                display_message(tr('msg', "Liquid spills."))
                                dropped_successfully = True 
                                break

                            target_index = -1
                            pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                            for i in range(container.capacity or 0):
                                if get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                                    target_index = i
                                    break
                            
                            is_drag_liq = getattr(game.dragged_item, 'liquid', False)
                            cont_max_liq = get_container_max_liquid(container) if is_drag_liq else None
                            
                            item_in_slot = container.inventory[target_index] if (target_index != -1 and target_index < len(container.inventory)) else None
                            is_stack = (item_in_slot is not None and item_in_slot.can_stack_with(game.dragged_item))

                            if is_drag_liq and cont_max_liq is not None:
                                avail_liq = get_container_available_liquid(container, target_item=item_in_slot if is_stack else None)
                                if avail_liq <= 0:
                                    display_message(tr('msg', "Container is full."))
                                    dropped_successfully = False
                                    break

                            if is_external_source:
                                if is_container_on_player(container, game.player) and not check_player_weight(game.dragged_item):
                                    dropped_successfully = False
                                    break
                                can_loot = False
                                if is_stack:
                                    can_loot = True
                                elif len(container.inventory) < (container.capacity or 0):
                                    if not check_container_weight_limit(container, game.dragged_item):
                                        display_message(f"{tr('item', container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                        dropped_successfully = False
                                    else:
                                        can_loot = True
                                else:
                                    display_message(f"{tr('item', container.name)} {tr('msg', 'is full.')}")
                                    dropped_successfully = False
                                    break
                                
                                if can_loot:
                                    item_ref = game.dragged_item
                                    if item_ref.name in ["Campfire on", "Lantern on"]:
                                        new_item = Item.create_from_name(item_ref.name.replace(" on", " off"))
                                        if new_item:
                                            new_item.durability = item_ref.durability
                                            new_item.load = item_ref.load
                                            item_ref = new_item
                                            display_message(tr('msg', f"{item_ref.name.split(' ')[0]} extinguished when picked up."))
                                    item_ref.rect.center = game.player.rect.center
                                    if item_ref not in game.items_on_ground:
                                        game.items_on_ground.append(item_ref)

                                    def do_container_loot():
                                        trans, rem, ok = add_item_to_container_inventory(
                                            container, item_ref, target_index=target_index, is_stack=is_stack
                                        )
                                        if ok:
                                            _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                            if rem > 0 and not is_infinite_liquid_source(container_obj):
                                                return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                                            _sync_source_container(game, container_obj)
                                        else:
                                            return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                                    
                                    transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                    game.player.start_action(tr('msg', "Looting"), transfer_time, do_container_loot, xp_reward=0.5)
                                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                    return

                            if is_stack:
                                trans, rem, ok = add_item_to_container_inventory(
                                    container, game.dragged_item, target_index=target_index, is_stack=True
                                )
                                if ok:
                                    if rem > 0 and not is_infinite_liquid_source(container_obj):
                                        return_remainder_to_origin(game, game.dragged_item, type_orig, i_orig, container_obj)
                                    game.dragged_item = None
                                    dropped_successfully = True
                                else:
                                    dropped_successfully = False
                            elif target_index != -1 and target_index < len(container.inventory):
                                if not check_container_weight_limit(container, game.dragged_item, item_in_slot):
                                    display_message(f"{tr('item', container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                    dropped_successfully = False
                                else:
                                    item_to_swap = container.inventory.pop(target_index)
                                    container.inventory.insert(target_index, game.dragged_item)
                                    game.dragged_item = item_to_swap
                                    dropped_successfully = False
                            elif len(container.inventory) < (container.capacity or 0):
                                if not check_container_weight_limit(container, game.dragged_item):
                                    display_message(f"{tr('item', container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                    dropped_successfully = False
                                else:
                                    trans, rem, ok = add_item_to_container_inventory(
                                        container, game.dragged_item, target_index=target_index, is_stack=False
                                    )
                                    if ok:
                                        if rem > 0 and not is_infinite_liquid_source(container_obj):
                                            return_remainder_to_origin(game, game.dragged_item, type_orig, i_orig, container_obj)
                                        game.dragged_item = None
                                        dropped_successfully = True
                                    else:
                                        dropped_successfully = False
                            else:
                                display_message(f"{tr('item', container.name)} {tr('msg', 'is full.')}")
                                dropped_successfully = False
                            
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
                            
                            if does_allow_liquid(target_container) and not getattr(game.dragged_item, 'liquid', False):
                                display_message(tr('msg', "Container only accepts liquids."))
                                dropped_successfully = False
                                break
                            elif getattr(game.dragged_item, 'liquid', False) and not does_allow_liquid(target_container):
                                display_message(tr('msg', "Liquid spills."))
                                dropped_successfully = True
                                break

                            is_drag_liq = getattr(game.dragged_item, 'liquid', False)
                            cont_max_liq = get_container_max_liquid(target_container) if is_drag_liq else None
                            
                            item_in_slot = target_container.inventory[target_index] if target_index < len(target_container.inventory) else None
                            is_stack = (item_in_slot is not None and item_in_slot.can_stack_with(game.dragged_item))

                            if is_drag_liq and cont_max_liq is not None:
                                avail_liq = get_container_available_liquid(target_container, target_item=item_in_slot if is_stack else None)
                                if avail_liq <= 0:
                                    display_message(tr('msg', "Container is full."))
                                    dropped_successfully = False
                                    break

                            if is_external_source:
                                if is_container_on_player(target_container, game.player) and not check_player_weight(game.dragged_item):
                                    dropped_successfully = False
                                    break
                                
                                can_loot = False
                                if is_stack:
                                    can_loot = True
                                elif len(target_container.inventory) < (target_container.capacity or 0):
                                    if not check_container_weight_limit(target_container, game.dragged_item):
                                        display_message(f"{tr('item', target_container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                        dropped_successfully = False
                                    else:
                                        can_loot = True
                                else:
                                    display_message(f"{tr('item', target_container.name)} {tr('msg', 'is full.')}")
                                    dropped_successfully = False
                                    break

                                if can_loot:
                                    item_ref = game.dragged_item
                                    item_ref.rect.center = game.player.rect.center
                                    if item_ref not in game.items_on_ground:
                                        game.items_on_ground.append(item_ref)

                                    def do_slots_container_loot():
                                        trans, rem, ok = add_item_to_container_inventory(
                                            target_container, item_ref, target_index=target_index, is_stack=is_stack
                                        )
                                        if ok:
                                            _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                            if rem > 0 and not is_infinite_liquid_source(container_obj):
                                                return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                                            _sync_source_container(game, container_obj)
                                        else:
                                            return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                                    
                                    transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                    game.player.start_action(tr('msg', "Looting"), transfer_time, do_slots_container_loot, xp_reward=0.5)
                                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                    return
                            
                            if is_stack:
                                trans, rem, ok = add_item_to_container_inventory(
                                    target_container, game.dragged_item, target_index=target_index, is_stack=True
                                )
                                if ok:
                                    if rem > 0 and not is_infinite_liquid_source(container_obj):
                                        return_remainder_to_origin(game, game.dragged_item, type_orig, i_orig, container_obj)
                                    game.dragged_item = None
                                    dropped_successfully = True
                                else:
                                    dropped_successfully = False
                            elif target_index < len(target_container.inventory):
                                if not check_container_weight_limit(target_container, game.dragged_item, item_in_slot):
                                    display_message(f"{tr('item', target_container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                    dropped_successfully = False
                                else:
                                    item_to_swap = target_container.inventory.pop(target_index)
                                    target_container.inventory.insert(target_index, game.dragged_item)
                                    game.dragged_item = item_to_swap
                                    dropped_successfully = False
                            else:
                                if not check_container_weight_limit(target_container, game.dragged_item):
                                    display_message(f"{tr('item', target_container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                    dropped_successfully = False
                                else:
                                    trans, rem, ok = add_item_to_container_inventory(
                                        target_container, game.dragged_item, target_index=target_index, is_stack=False
                                    )
                                    if ok:
                                        if rem > 0 and not is_infinite_liquid_source(container_obj):
                                            return_remainder_to_origin(game, game.dragged_item, type_orig, i_orig, container_obj)
                                        game.dragged_item = None
                                        dropped_successfully = True
                                    else:
                                        dropped_successfully = False
                            
                            break

                elif modal['type'] == 'gear' and modal['rect'].collidepoint(mouse_pos):
                    active_tab = modal.get('active_tab', 'Gear')
                    
                    if active_tab == 'Gear':
                        if 'gear_slot_rects' in modal:
                            for slot_name, slot_rect in modal['gear_slot_rects'].items():
                                if slot_rect.collidepoint(mouse_pos):
                                    dragged_item = game.dragged_item
                                    item_slot = getattr(dragged_item, 'slot', None)
                                    if item_slot == 'hand': item_slot = 'hands'
                                    
                                    is_util_slot = slot_name in ['util', 'util2', 'util3']
                                    is_container = getattr(dragged_item, 'item_type', '') == 'container'
                                    is_util_item = item_slot == 'util'

                                    if item_slot == slot_name or (is_util_slot and (is_container or is_util_item)):
                                        if getattr(dragged_item, 'liquid', False):
                                            display_message(tr('msg', "Liquid spills."))
                                            dropped_successfully = True; break

                                        if is_external_source:
                                            if not check_player_weight(game.dragged_item):
                                                dropped_successfully = False
                                                break
                                            item_in_slot = game.player.clothes.get(slot_name)
                                            if item_in_slot:
                                                display_message(tr('msg', "Cannot swap items while equipping from external source."))
                                                dropped_successfully = False
                                                break

                                            item_ref = dragged_item
                                            if item_ref.name == "Campfire on":
                                                new_item = Item.create_from_name("Campfire off")
                                                if new_item:
                                                    new_item.durability = item_ref.durability
                                                    new_item.load = item_ref.load
                                                    item_ref = new_item
                                                    display_message(tr('msg', "Campfire extinguished when picked up."))

                                            item_ref.rect.center = game.player.rect.center
                                            if item_ref not in game.items_on_ground:
                                                game.items_on_ground.append(item_ref)

                                            def do_gear_equip():
                                                _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                                game.player.clothes[slot_name] = item_ref

                                                if game and hasattr(game, 'sound_manager'):
                                                    game.sound_manager.play_sound('equip_gear.ogg', subdir='items', game=game, source_pos=game.player.rect.center, base_volume=0.5, pitch_variance=0.1, is_critical=True)

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

                                        if game and hasattr(game, 'sound_manager'):
                                            game.sound_manager.play_sound(
                                                'equip_gear.ogg',
                                                subdir='items',
                                                game=game,
                                                source_pos=game.player.rect.center,
                                                base_volume=0.5,
                                                pitch_variance=0.1,
                                                is_critical=True
                                            )
                                    else:
                                        dropped_successfully = False 
                                    break

                    elif active_tab in modal.get('container_mapping', {}):
                        container = modal['container_mapping'][active_tab]
                        if container:
                            if check_recursive_containment(game.dragged_item, container):
                                display_message(tr('msg', "Cannot put the container inside itself."))
                                dropped_successfully = False
                                break
                            
                            if does_allow_liquid(container) and not getattr(game.dragged_item, 'liquid', False):
                                display_message(tr('msg', "Container only accepts liquids."))
                                dropped_successfully = False 
                                break
                            elif getattr(game.dragged_item, 'liquid', False) and not does_allow_liquid(container):
                                display_message(tr('msg', "Liquid spills."))
                                dropped_successfully = True 
                                break
                            
                            pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                            target_index = -1
                            for i in range(container.capacity or 0):
                                if get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                                    target_index = i
                                    break
                            
                            is_drag_liq = getattr(game.dragged_item, 'liquid', False)
                            cont_max_liq = get_container_max_liquid(container) if is_drag_liq else None
                            
                            item_in_slot = container.inventory[target_index] if (target_index != -1 and target_index < len(container.inventory)) else None
                            is_stack = (item_in_slot is not None and item_in_slot.can_stack_with(game.dragged_item))

                            if is_drag_liq and cont_max_liq is not None:
                                avail_liq = get_container_available_liquid(container, target_item=item_in_slot if is_stack else None)
                                if avail_liq <= 0:
                                    display_message(tr('msg', "Container is full."))
                                    dropped_successfully = False
                                    break

                            if is_external_source:
                                if is_container_on_player(container, game.player) and not check_player_weight(game.dragged_item):
                                    dropped_successfully = False
                                    break
                                can_loot = False
                                if is_stack:
                                    can_loot = True
                                elif len(container.inventory) < (container.capacity or 0):
                                    if not check_container_weight_limit(container, game.dragged_item):
                                        display_message(f"{tr('item', container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                        dropped_successfully = False
                                    else:
                                        can_loot = True
                                else:
                                    display_message(f"{tr('item', container.name)} {tr('msg', 'is full.')}")
                                    dropped_successfully = False
                                    break
                                
                                if can_loot:
                                    item_ref = game.dragged_item
                                    if item_ref.name in ["Campfire on", "Lantern on"]:
                                        new_item = Item.create_from_name(item_ref.name.replace(" on", " off"))
                                        if new_item:
                                            new_item.durability = item_ref.durability
                                            new_item.load = item_ref.load
                                            item_ref = new_item
                                            display_message(tr('msg', f"{item_ref.name.split(' ')[0]} extinguished when picked up."))
                                    item_ref.rect.center = game.player.rect.center
                                    if item_ref not in game.items_on_ground:
                                        game.items_on_ground.append(item_ref)

                                    def do_gear_container_loot():
                                        trans, rem, ok = add_item_to_container_inventory(
                                            container, item_ref, target_index=target_index, is_stack=is_stack
                                        )
                                        if ok:
                                            _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                            if rem > 0 and not is_infinite_liquid_source(container_obj):
                                                return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                                            _sync_source_container(game, container_obj)
                                        else:
                                            return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                                    
                                    transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                                    game.player.start_action(tr('msg', "Looting"), transfer_time, do_gear_container_loot, xp_reward=0.5)
                                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                    return
                            
                            if is_stack:
                                trans, rem, ok = add_item_to_container_inventory(
                                    container, game.dragged_item, target_index=target_index, is_stack=True
                                )
                                if ok:
                                    if rem > 0 and not is_infinite_liquid_source(container_obj):
                                        return_remainder_to_origin(game, game.dragged_item, type_orig, i_orig, container_obj)
                                    game.dragged_item = None
                                    dropped_successfully = True
                                else:
                                    dropped_successfully = False
                            elif target_index != -1 and target_index < len(container.inventory):
                                if not check_container_weight_limit(container, game.dragged_item, item_in_slot):
                                    display_message(f"{tr('item', container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                    dropped_successfully = False
                                else:
                                    item_to_swap = container.inventory.pop(target_index)
                                    container.inventory.insert(target_index, game.dragged_item)
                                    game.dragged_item = item_to_swap
                                    dropped_successfully = False
                            elif len(container.inventory) < (container.capacity or 0):
                                if not check_container_weight_limit(container, game.dragged_item):
                                    display_message(f"{tr('item', container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                    dropped_successfully = False
                                else:
                                    trans, rem, ok = add_item_to_container_inventory(
                                        container, game.dragged_item, target_index=target_index, is_stack=False
                                    )
                                    if ok:
                                        if rem > 0 and not is_infinite_liquid_source(container_obj):
                                            return_remainder_to_origin(game, game.dragged_item, type_orig, i_orig, container_obj)
                                        game.dragged_item = None
                                        dropped_successfully = True
                                    else:
                                        dropped_successfully = False
                            else:
                                display_message(f"{tr('item', container.name)} {tr('msg', 'is full.')}")
                                dropped_successfully = False
                    if dropped_successfully: break

                elif modal['type'] == 'mobile' and modal.get('active_tab') == 'Apps' and modal['rect'].collidepoint(mouse_pos):
                    for slot_data in modal.get('app_slot_rects', []):
                        if slot_data['rect'].collidepoint(mouse_pos):
                            i = slot_data['index']
                            dragged = game.dragged_item
                            item_type = getattr(dragged, 'type', None) or getattr(dragged, 'item_type', None)
                            if not item_type:
                                tmpl = ITEM_TEMPLATES.get(getattr(dragged, 'name', ''))
                                if tmpl:
                                    item_type = tmpl.get('type')
                            
                            if item_type == 'sd_card':
                                slots = getattr(game, 'app_state', {}).get('slots', [])
                                old_item = slots[i]
                                slots[i] = dragged
                                
                                if old_item:
                                    game.dragged_item = old_item
                                    dropped_successfully = False
                                else:
                                    dropped_successfully = True
                            else:
                                display_message(tr('msg', "Only SD cards can be inserted here."))
                                dropped_successfully = False
                            break
                    if dropped_successfully: break

            if dropped_successfully:
                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                return

            # --- Target 4: Container and Nearby Modals ---
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
                    if getattr(container, 'item_type', '') == 'maptile_container' and not getattr(container, 'is_opened', False):
                        break
                    
                    if check_recursive_containment(game.dragged_item, container):
                        display_message("Recursion detected: Cannot put container into itself.")
                        dropped_successfully = False
                        break

                    if does_allow_liquid(container) and not getattr(game.dragged_item, 'liquid', False):
                        display_message(tr('msg', "Container only accepts liquids."))
                        dropped_successfully = False 
                        break
                    elif getattr(game.dragged_item, 'liquid', False) and not does_allow_liquid(container):
                        display_message(tr('msg', "Liquid spills."))
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
                                game.dragged_item.is_placed = False
                                game.items_on_ground.append(game.dragged_item)
                                
                                if type_orig == 'nearby' or type_orig == 'ground':
                                    game.items_on_ground.append(item_in_slot)
                                    dropped_successfully = True 
                                else:
                                    game.dragged_item = item_in_slot
                                    dropped_successfully = False 
                        
                        else:
                            game.dragged_item.is_placed = False
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

                        if dropped_successfully and game and hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound(
                                'drop.ogg',
                                subdir='items',
                                game=game,
                                source_pos=game.player.rect.center,
                                base_volume=0.5,
                                pitch_variance=0.1,
                                is_critical=True
                            )
                        if dropped_successfully: break 
                        break

                    target_index = -1
                    pos = modal['position']
                    if modal['type'] == 'nearby': pos = modal['content_rect'].topleft
                    
                    for i in range(container.capacity or 0):
                        if get_container_slot_rect(pos, i).collidepoint(mouse_pos):
                            target_index = i
                            break

                    is_drag_liq = getattr(game.dragged_item, 'liquid', False)
                    cont_max_liq = get_container_max_liquid(container) if is_drag_liq else None

                    item_in_slot = container.inventory[target_index] if (target_index != -1 and target_index < len(container.inventory)) else None
                    is_stack = (item_in_slot is not None and item_in_slot.can_stack_with(game.dragged_item))

                    if is_drag_liq and cont_max_liq is not None:
                        avail_liq = get_container_available_liquid(container, target_item=item_in_slot if is_stack else None)
                        if avail_liq <= 0:
                            display_message(tr('msg', "Container is full."))
                            dropped_successfully = False
                            break

                    use_loader = not is_external_source
                    action_name = tr('msg', "Storing")

                    if use_loader:
                        can_action = False
                        if is_stack:
                            can_action = True
                        elif target_index != -1 and target_index < len(container.inventory):
                            display_message(f"{tr('msg', 'Cannot swap items while')} {tr('msg', action_name.lower())}.")
                            dropped_successfully = False
                            break
                        elif len(container.inventory) < (container.capacity or 0):
                            if not check_container_weight_limit(container, game.dragged_item):
                                display_message(f"{tr('item', container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                dropped_successfully = False
                                break
                            else:
                                can_action = True
                        else:
                            display_message(tr('msg', "Container is full."))
                            dropped_successfully = False
                            break

                        if can_action:
                            item_ref = game.dragged_item
                            item_ref.rect.center = game.player.rect.center
                            if item_ref not in game.items_on_ground:
                                game.items_on_ground.append(item_ref)

                            def do_timed_action():
                                trans, rem, ok = add_item_to_container_inventory(
                                    container, item_ref, target_index=target_index, is_stack=is_stack
                                )
                                if ok:
                                    if item_ref in game.items_on_ground:
                                        game.items_on_ground.remove(item_ref)
                                    _remove_from_ground_and_sync(game, item_ref, type_orig, container_obj)
                                    if rem > 0 and not is_infinite_liquid_source(container_obj):
                                        return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                                    _sync_source_container(game, container_obj)
                                else:
                                    return_remainder_to_origin(game, item_ref, type_orig, i_orig, container_obj)
                            
                            transfer_time = max(0.1, item_ref.get_total_weight() * 0.2)
                            game.player.start_action(action_name, transfer_time, do_timed_action, xp_reward=0.5)
                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                            return

                    if is_stack:
                        trans, rem, ok = add_item_to_container_inventory(
                            container, game.dragged_item, target_index=target_index, is_stack=True
                        )
                        if ok:
                            if rem > 0 and not is_infinite_liquid_source(container_obj):
                                return_remainder_to_origin(game, game.dragged_item, type_orig, i_orig, container_obj)
                            game.dragged_item = None
                            dropped_successfully = True
                        else:
                            dropped_successfully = False
                    elif target_index != -1 and target_index < len(container.inventory):
                        if not check_container_weight_limit(container, game.dragged_item, item_in_slot):
                            display_message(f"{tr('item', container.name)} {tr('msg', 'cannot carry that much weight.')}")
                            dropped_successfully = False
                        else:
                            item_to_swap = container.inventory.pop(target_index)
                            container.inventory.insert(target_index, game.dragged_item)
                            game.dragged_item = item_to_swap
                            dropped_successfully = False 
                    elif len(container.inventory) < (container.capacity or 0):
                        if not check_container_weight_limit(container, game.dragged_item):
                            display_message(f"{tr('item', container.name)} {tr('msg', 'cannot carry that much weight.')}")
                            dropped_successfully = False
                        else:
                            trans, rem, ok = add_item_to_container_inventory(
                                container, game.dragged_item, target_index=target_index, is_stack=False
                            )
                            if ok:
                                if rem > 0 and not is_infinite_liquid_source(container_obj):
                                    return_remainder_to_origin(game, game.dragged_item, type_orig, i_orig, container_obj)
                                game.dragged_item = None
                                dropped_successfully = True
                            else:
                                dropped_successfully = False
                    else:
                        display_message(f"{tr('item', container.name)} {tr('msg', 'is full.')}")
                    
                    if dropped_successfully: break

            if dropped_successfully:
                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                if type_orig in ('container', 'nearby', 'container_stack_split', 'nearby_stack_split') and container_obj:
                    _sync_container_to_server(game, container_obj)
                return

        # --- Target 5: Drop on Open Ground / World or Bounce Back ---
        if not dropped_successfully:
            is_over_modal = False
            for modal in game.modals:
                if modal['rect'].collidepoint(mouse_pos):
                    is_over_modal = True
                    break

            game_world_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
            if game.dragged_item:
                if game_world_rect.collidepoint(mouse_pos) and not is_over_modal:
                    poured_in_map = False
                    if getattr(game.dragged_item, 'liquid', False):
                        grid_x = int(mouse_pos[0] // TILE_SIZE)
                        grid_y = int(mouse_pos[1] // TILE_SIZE)
                        tile_def = game.map_manager.get_tile_at(grid_x, grid_y)
                        
                        tile_allow_liquid = tile_def.get('allow_liquid', False) if tile_def else False
                        if str(tile_allow_liquid).lower() in ['true', '1'] or tile_allow_liquid is True:
                            poured_in_map = True
                            display_message(f"{tr('msg', 'Poured')} {tr('item', game.dragged_item.name)} {tr('msg', 'into')} {tr('msg', tile_def.get('name', ''))}.")
                            game.dragged_item.load = 0
                            dropped_successfully = True
                            
                            if game and hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound(
                                    'drop.ogg',
                                    subdir='items',
                                    game=game,
                                    source_pos=game.dragged_item.rect.center,
                                    base_volume=0.5,
                                    pitch_variance=0.1,
                                    is_critical=True
                                )
                            dropped_successfully = True
                        else:
                            display_message(f"{tr('msg', 'The')} {tr('item', game.dragged_item.name)} {tr('msg', 'spills on the ground.')}")
                            dropped_successfully = True 
                    
                    if not poured_in_map and not getattr(game.dragged_item, 'liquid', False):
                        offset_x = random.randint(-8, 8)
                        offset_y = random.randint(-8, 8)
                        
                        game.dragged_item.rect.center = (
                            game.player.rect.centerx + offset_x, 
                            game.player.rect.centery + offset_y
                        )
                        game.dragged_item.x = game.dragged_item.rect.x
                        game.dragged_item.y = game.dragged_item.rect.y
                        game.dragged_item.is_placed = False
                        game.dragged_item.layer = getattr(game, 'current_layer_index', 1)
                        game.dragged_item.map_filename = getattr(game.map_manager, 'current_map_filename', '')
                        
                        if getattr(game, 'is_client', False) and getattr(game, 'client', None):
                            from core.server.network import NetMsg, send_msg
                            send_msg(game.client.socket, {
                                'type': NetMsg.WORLD_ACTION, 'action': 'drop',
                                'item_data': game.dragged_item.to_dict(),
                                'x': game.dragged_item.x, 'y': game.dragged_item.y,
                                'layer': game.dragged_item.layer,
                                'is_placed': False
                            })
                        
                        if game.dragged_item not in game.items_on_ground:
                            game.items_on_ground.append(game.dragged_item)
                        dropped_successfully = True

                        if game and hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound(
                                'drop.ogg',
                                subdir='items',
                                game=game,
                                source_pos=game.dragged_item.rect.center,
                                base_volume=0.5,
                                pitch_variance=0.1,
                                is_critical=True
                            )

                        if type_orig in ('container', 'nearby', 'container_stack_split', 'nearby_stack_split') and container_obj:
                            _sync_container_to_server(game, container_obj)

                if not dropped_successfully and game.dragged_item:
                    # BOUNCE BACK SAFELY
                    if type_orig == 'inventory' and 0 <= i_orig <= len(game.player.inventory):
                        game.player.inventory.insert(i_orig, game.dragged_item)
                    elif type_orig == 'belt' and 0 <= i_orig < len(game.player.belt):
                        game.player.belt[i_orig] = game.dragged_item
                        game.dragged_item.in_belt = True
                    elif type_orig == 'app':
                        game.app_state['slots'][i_orig] = game.dragged_item
                    elif type_orig == 'gear':
                        slot_name = i_orig 
                        game.player.clothes[slot_name] = game.dragged_item
                    elif type_orig == 'container' and container_obj is not None:
                        if is_infinite_liquid_source(container_obj) and getattr(game.dragged_item, 'liquid', False):
                            pass
                        else:
                            container_obj.inventory.insert(i_orig, game.dragged_item)
                            _sync_container_to_server(game, container_obj)
                    elif type_orig == 'nearby' and container_obj is not None:
                        if is_infinite_liquid_source(container_obj) and getattr(game.dragged_item, 'liquid', False):
                            pass
                        else:
                            container_obj.inventory.insert(i_orig, game.dragged_item)
                            _sync_container_to_server(game, container_obj)
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