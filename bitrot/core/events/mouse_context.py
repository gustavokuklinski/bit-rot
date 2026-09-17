import pygame
import uuid
import math
import random
from core.data.config import *
from core.data.recipe_manager import RecipeManager
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.ui.inventory_modal import get_belt_hud_slot_rect, get_inventory_slot_rect, get_belt_slot_rect_in_modal
from core.ui.container_modal import get_container_slot_rect
from core.messages import display_message
from core.events.keyboard import toggle_status_modal, toggle_inventory_modal, toggle_nearby_modal, toggle_gear_modal
from core.data.localization import tr
from core.placement import find_free_tile
from core.entities.item.item_helpers import does_allow_liquid, is_infinite_liquid_source, find_item_recursive, has_app
from core.ui.crafting_common import is_recipe_unlocked, has_recipe_ingredients, execute_recipe_craft, get_recipe_status_details, is_recipe_relevant_to_item

def _is_barricade_item(it):
    """Safely checks if an item is a valid barricade, guarding against NoneType values."""
    if not it:
        return False
    b_health = getattr(it, 'barricade_health', None)
    if b_health is not None and b_health > 0:
        return True
    return 'barricade' in getattr(it, 'name', '').lower()

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
                elif source == 'player_self' or source == 'map_tile' or source == 'vehicle_equipment' or source == 'vehicle_slot':
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
            
            if option == 'Place barricade':
                if source == 'map_tile' and isinstance(item, dict):
                    gx = item['grid_x']
                    gy = item['grid_y']

                    # Search player inventory or belt for the barricade
                    found_barricade = None
                    barricade_source = None
                    barricade_idx = -1

                    for idx_it, it in enumerate(game.player.inventory):
                        if _is_barricade_item(it):
                            found_barricade = it
                            barricade_source = 'inventory'
                            barricade_idx = idx_it
                            break

                    if not found_barricade:
                        for idx_it, it in enumerate(game.player.belt):
                            if _is_barricade_item(it):
                                found_barricade = it
                                barricade_source = 'belt'
                                barricade_idx = idx_it
                                break

                    if found_barricade:
                        # Check required tools & materials from <place>
                        all_player_items = [it for it in (game.player.inventory + game.player.belt) if it and it != found_barricade]
                        missing_reqs = []

                        for req in getattr(found_barricade, 'place_items', []):
                            needed = req.get('amount', 1)
                            candidates = req.get('items', [])
                            have = 0
                            for it in all_player_items:
                                if it and any(cand.lower() == it.name.lower() or cand.lower() in it.name.lower() for cand in candidates):
                                    have += it.load if (hasattr(it, 'is_stackable') and it.is_stackable() and it.load is not None) else 1
                            if have < needed:
                                cands_str = ", ".join(candidates)
                                missing_reqs.append(f"{cands_str} ({have}/{needed})")

                        if missing_reqs:
                            display_message(f"{tr('msg', 'Need:')} {', '.join(missing_reqs)}")
                            clicked_on_menu = True
                            return

                        def do_place_barricade():
                            # Consume required materials that have destroy="true"
                            for req in getattr(found_barricade, 'place_items', []):
                                if not req.get('destroy', False):
                                    continue
                                to_remove = req.get('amount', 1)
                                candidates = req.get('items', [])
                                for it_list in [game.player.belt, game.player.inventory]:
                                    for idx_c in range(len(it_list)):
                                        it = it_list[idx_c]
                                        if it and it != found_barricade and any(cand.lower() == it.name.lower() or cand.lower() in it.name.lower() for cand in candidates):
                                            if hasattr(it, 'is_stackable') and it.is_stackable() and it.load is not None:
                                                take = min(to_remove, it.load)
                                                it.load -= take
                                                to_remove -= take
                                                if it.load <= 0:
                                                    it_list[idx_c] = None
                                            else:
                                                it_list[idx_c] = None
                                                to_remove -= 1
                                            if to_remove <= 0:
                                                break
                                    if to_remove <= 0:
                                        break

                            # Consume the barricade item itself
                            if barricade_source == 'inventory':
                                if barricade_idx < len(game.player.inventory) and game.player.inventory[barricade_idx] == found_barricade:
                                    game.player.inventory.pop(barricade_idx)
                                elif found_barricade in game.player.inventory:
                                    game.player.inventory.remove(found_barricade)
                            elif barricade_source == 'belt':
                                game.player.belt[barricade_idx] = None

                            game.player.inventory = [it for it in game.player.inventory if it is not None]

                            game.map_manager.add_barricade(gx, gy, found_barricade)
                            display_message(tr('msg', "Barricade placed successfully."))

                        place_time = getattr(found_barricade, 'place_time', 1.5)
                        game.player.start_action("Placing Barricade", place_time, do_place_barricade, xp_reward=5)
                    else:
                        display_message(tr('msg', "Barricade must be in inventory."))
                clicked_on_menu = True

            elif option == 'Remove barricade':
                if source == 'map_tile' and isinstance(item, dict):
                    gx = item['grid_x']
                    gy = item['grid_y']
                    barricade = game.map_manager.get_barricade(gx, gy)

                    if barricade:
                        req_tools = barricade.get('remove_items', ['Crowbar'])
                        remove_time = barricade.get('remove_time', 1.5)

                        has_tool = False
                        for it in game.player.inventory + game.player.belt:
                            if it and any(tool.lower() in it.name.lower() for tool in req_tools):
                                has_tool = True
                                break

                        if has_tool:
                            def do_remove_barricade():
                                removed = game.map_manager.remove_barricade(gx, gy)
                                if removed:
                                    b_item = Item.create_from_name(removed['item_name'])
                                    if b_item:
                                        if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                            game.player.inventory.append(b_item)
                                        else:
                                            b_item.rect.center = game.player.rect.center
                                            b_item.x, b_item.y = b_item.rect.topleft
                                            game.items_on_ground.append(b_item)
                                    display_message(tr('msg', "Barricade removed."))

                            game.player.start_action("Removing Barricade", remove_time, do_remove_barricade, xp_reward=5)
                        else:
                            display_message(f"{tr('msg', 'Need:')} {', '.join(req_tools)}")
                clicked_on_menu = True

            elif option == 'Repair Door/Window':
                if source == 'map_tile' and isinstance(item, dict):
                    gx = item['grid_x']
                    gy = item['grid_y']
                    char = item.get('char', '')
                    t_def = game.map_manager.get_tile_at(gx, gy)

                    if t_def and t_def.get('repair_info'):
                        r_info = t_def['repair_info']
                        req_mag = r_info.get('magazine')

                        if req_mag and req_mag not in getattr(game.player, 'known_recipes', []):
                            display_message(f"{tr('msg', 'Requires magazine:')} {req_mag}")
                            game.context_menu['active'] = False
                            return

                        all_player_items = [it for it in (game.player.inventory + game.player.belt) if it]
                        has_all = True
                        missing = []

                        for req_name, req_qty in r_info['items'].items():
                            avail = sum(it.load if (hasattr(it, 'is_stackable') and it.is_stackable() and it.load) else 1
                                        for it in all_player_items if req_name.lower() in it.name.lower())
                            if avail < req_qty:
                                has_all = False
                                missing.append(f"{req_name} ({avail}/{req_qty})")

                        if not has_all:
                            display_message(f"{tr('msg', 'Missing:')} {', '.join(missing)}")
                            game.context_menu['active'] = False
                            return

                        def do_repair_door():
                            for req_name, req_qty in r_info['items'].items():
                                left = req_qty
                                for it_list in [game.player.belt, game.player.inventory]:
                                    for i in range(len(it_list)):
                                        it = it_list[i]
                                        if it and req_name.lower() in it.name.lower():
                                            if hasattr(it, 'is_stackable') and it.is_stackable() and it.load:
                                                take = min(left, it.load)
                                                it.load -= take
                                                left -= take
                                                if it.load <= 0:
                                                    it_list[i] = None
                                            else:
                                                it_list[i] = None
                                                left -= 1
                                            if left <= 0:
                                                break
                                    if left <= 0:
                                        break

                            game.player.inventory = [it for it in game.player.inventory if it is not None]

                            for skill, amt in r_info.get('gain_xp', {}).items():
                                game.player.progression.add_xp(game.player, skill, amt)

                            base_name = char.replace('_open', '').replace('_close', '').replace('_broke', '')
                            close_char = f"{base_name}_close"
                            if close_char not in game.tile_manager.definitions:
                                close_char = f"{base_name}_open"

                            if close_char in game.tile_manager.definitions:
                                game.map_manager._replace_tile(gx, gy, char, close_char)

                            map_name = game.map_manager.current_map_filename
                            if map_name in game.map_states and 'tile_health' in game.map_states[map_name]:
                                game.map_states[map_name]['tile_health'][(gx, gy)] = t_def.get('health_max', 100)

                            display_message(tr('msg', "Door/Window repaired successfully."))

                        game.player.start_action("Repairing", r_info.get('time', 1.5), do_repair_door, xp_reward=0)
                clicked_on_menu = True

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

            elif option == 'Remove fuel to':
                target_container_name = target_sub_slot
                veh = container_item
                slot_name = index
                
                target_container = None
                all_containers = [item for item in game.player.belt if item] + \
                                 [item for item in game.player.inventory if item] + \
                                 [item for item in game.player.clothes.values() if item]
                
                for c_item in all_containers:
                    if getattr(c_item, 'item_type', '') in ['container', 'cloth']:
                        if hasattr(c_item, 'id') and str(c_item.id) == target_container_name:
                            target_container = c_item
                            break
                        if not target_container and c_item.name == target_container_name:
                            target_container = c_item
                            
                if target_container:
                    fuel_item = veh.equipment.get(slot_name)
                    if fuel_item:
                        transfer_time = max(0.1, fuel_item.get_total_weight() * 0.2)
                        
                        def do_remove_fuel():
                            removed_item = veh.remove_equipment(slot_name)
                            if removed_item:
                                qty_to_send = getattr(removed_item, 'load', 1)
                                if qty_to_send is None: qty_to_send = 1
                                
                                unit_weight = removed_item.get_total_weight() / max(1, qty_to_send)
                                avail_weight = float('inf')
                                
                                cont_weight = getattr(target_container, 'weight', 0)
                                if cont_weight is not None and cont_weight > 0:
                                    max_w = cont_weight * 5.0
                                    cur_w = sum(i.get_total_weight() for i in getattr(target_container, 'inventory', []))
                                    avail_weight = max_w - cur_w
                                    
                                max_qty_by_weight = int(avail_weight // unit_weight) if unit_weight > 0 else qty_to_send
                                
                                actual_transfer = min(qty_to_send, max_qty_by_weight)
                                
                                if actual_transfer <= 0:
                                    veh.add_equipment(removed_item, slot_name)
                                    display_message(tr('msg', "Container is full by weight."))
                                    game.context_menu['active'] = False
                                    return
                                    
                                original_load = qty_to_send
                                amount_transferred = 0
                                
                                if hasattr(removed_item, 'is_stackable') and removed_item.is_stackable():
                                    for inv_item in target_container.inventory:
                                        if inv_item.can_stack_with(removed_item):
                                            i_cap = getattr(target_container, 'max_liquid', None) or getattr(inv_item, 'capacity', 1) or 1
                                            i_load = getattr(inv_item, 'load', 1) or 1
                                            
                                            avail = i_cap - i_load
                                            trans = min(avail, actual_transfer)
                                            if trans > 0:
                                                inv_item.load = i_load + trans
                                                actual_transfer -= trans
                                                amount_transferred += trans
                                            if actual_transfer <= 0:
                                                break
                                                
                                c_cap = getattr(target_container, 'capacity', 0)
                                if c_cap is None: c_cap = 0
                                
                                if actual_transfer > 0 and len(target_container.inventory) < c_cap:
                                    new_item = Item.create_from_name(removed_item.name)
                                    if new_item:
                                        new_item.load = actual_transfer
                                        if hasattr(removed_item, 'durability'): new_item.durability = removed_item.durability
                                        target_container.inventory.append(new_item)
                                        amount_transferred += actual_transfer
                                        actual_transfer = 0
                                        
                                remaining_load = original_load - amount_transferred
                                
                                if remaining_load > 0:
                                    removed_item.load = remaining_load
                                    veh.add_equipment(removed_item, slot_name)
                                    
                                if amount_transferred > 0:
                                    display_message(f"{tr('msg', 'Removed fuel to')} {tr('item', target_container.name)}.")
                                else:
                                    display_message(tr('msg', "Container is full."))
                                    
                        game.player.start_action(f"Transferring {tr('item', fuel_item.name)}", transfer_time, do_remove_fuel, xp_reward=1)
                clicked_on_menu = True

            elif option == 'Send to':
                target_container_name = target_sub_slot
                
                def remove_item_from_src(target_item, is_clone=False):
                    if is_clone: return True
                    
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

                    def do_send_inv():
                        is_inf = source in ['nearby', 'container_map', 'container'] and container_item and is_infinite_liquid_source(container_item)
                        
                        if is_inf and getattr(item, 'liquid', False):
                            clone = Item.create_from_name(item.name)
                            if clone:
                                clone.load = getattr(item, 'capacity', 100)
                                clone.durability = item.durability
                                clone.is_placed = False
                                game.player.inventory.append(clone)
                                game.player.stack_item_in_inventory(clone)
                        else:
                            if remove_item_from_src(item):
                                item.is_placed = False
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
                            if hasattr(c_item, 'id') and str(c_item.id) == target_container_name:
                                target_container = c_item
                                break
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
                                        i_cap = getattr(target_container, 'max_liquid', None) or getattr(inv_item, 'capacity', 1) or 1
                                        i_load = getattr(inv_item, 'load', 1) or 1
                                        r_load = getattr(removed_item, 'load', 1) or 1
                                        
                                        avail = i_cap - i_load
                                        trans = min(avail, qty_to_send, r_load)
                                        if trans > 0:
                                            inv_item.load = i_load + trans
                                            inv_item.capacity = i_cap
                                            removed_item.load = r_load - trans
                                            qty_to_send -= trans
                                            stacked = True
                                        if qty_to_send <= 0 or removed_item.load <= 0:
                                            break
                            
                            c_cap = getattr(target_container, 'capacity', 0)
                            if c_cap is None: c_cap = 0
                            
                            if qty_to_send > 0 and len(target_container.inventory) < c_cap:
                                r_load = getattr(removed_item, 'load', 1) or 1
                                target_max_liq = getattr(target_container, 'max_liquid', None)
                                trans_qty = min(qty_to_send, target_max_liq) if target_max_liq is not None else qty_to_send

                                if trans_qty > 0:
                                    if trans_qty < r_load:
                                        new_item = Item.create_from_name(removed_item.name)
                                        if new_item:
                                            new_item.load = trans_qty
                                            if target_max_liq is not None:
                                                new_item.capacity = target_max_liq
                                            if hasattr(removed_item, 'durability'): new_item.durability = removed_item.durability
                                            removed_item.load = r_load - trans_qty
                                            target_container.inventory.append(new_item)
                                    else:
                                        if remove_item_from_src(item, is_clone=is_clone):
                                            if target_max_liq is not None:
                                                removed_item.capacity = target_max_liq
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

            # --- CLICK HANDLER FOR CRAFTS & FAST CRAFTING ---
            elif option == 'Crafts':
                if target_sub_slot and target_sub_slot.startswith('header_'):
                    return

                if target_sub_slot == 'open_craft' or not target_sub_slot:
                    translated_name = tr('item', item.name)
                    tab_name = tr('tab', "Known Recipes")
                    
                    game.modals = [m for m in game.modals if m['type'] != 'crafting']
                    default_pos = (GAME_WIDTH // 2 - CRAFTING_MODAL_WIDTH // 2, GAME_HEIGHT // 2 - CRAFTING_MODAL_HEIGHT // 2)
                    pos = game.last_modal_positions.get('crafting', default_pos) if hasattr(game, 'last_modal_positions') else default_pos

                    new_modal = {
                        'id': uuid.uuid4(),
                        'type': 'crafting',
                        'position': pos,
                        'rect': pygame.Rect(pos[0], pos[1], CRAFTING_MODAL_WIDTH, CRAFTING_MODAL_HEIGHT),
                        'is_dragging': False,
                        'drag_offset': (0, 0),
                        'active_tab': tab_name,
                        'search_text': translated_name,
                        'search_active': False
                    }
                    game.modals.append(new_modal)
                else:
                    recipe = game.context_menu.get('craft_recipes', {}).get(target_sub_slot)
                    if recipe:
                        execute_recipe_craft(game, recipe)
                clicked_on_menu = True

            elif option == 'Remove' and source == 'vehicle_equipment':
                veh = container_item
                slot_name = index
                item_to_remove = veh.equipment.get(slot_name)
                
                if item_to_remove:
                    transfer_time = max(0.1, item_to_remove.get_total_weight() * 0.2)
                    
                    def do_remove():
                        removed_item = veh.remove_equipment(slot_name)
                        if removed_item:
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(removed_item)
                                if hasattr(game.player, 'stack_item_in_inventory'):
                                    game.player.stack_item_in_inventory(removed_item)
                            else:
                                removed_item.rect.center = game.player.rect.center
                                game.items_on_ground.append(removed_item)
                            display_message(f"{tr('msg', 'Removed')} {tr('item', removed_item.name)}.")
                            
                    game.player.start_action(f"Removing {tr('item', item_to_remove.name)}", transfer_time, do_remove, xp_reward=1)
                clicked_on_menu = True

            elif option.startswith('Insert '):
                if isinstance(item, dict) and item.get('type') == 'virtual_slot':
                    veh = item['vehicle']
                    slot_name = item['slot']

                    found_item, src_list, idx, _ = find_item_recursive(
                        game.player.belt, lambda it: veh.can_equip(it, slot_name)
                    )
                    if not found_item:
                        found_item, src_list, idx, _ = find_item_recursive(
                            game.player.inventory, lambda it: veh.can_equip(it, slot_name)
                        )
                    if not found_item:
                        for k, v in game.player.clothes.items():
                            if not v: continue
                            if veh.can_equip(v, slot_name):
                                found_item, src_list, idx = v, game.player.clothes, k
                                break
                            if hasattr(v, 'inventory') and v.inventory:
                                found_item, src_list, idx, _ = find_item_recursive(
                                    v.inventory, lambda it: veh.can_equip(it, slot_name)
                                )
                                if found_item: break
                                
                    if found_item:
                        transfer_time = max(0.1, found_item.get_total_weight() * 0.2)
                        
                        def do_insert():
                            if src_list == game.player.belt:
                                game.player.belt[idx] = None
                            elif src_list == game.player.clothes:
                                game.player.clothes[idx] = None
                            else:
                                src_list.pop(idx)
                                
                            old_item = veh.add_equipment(found_item, slot_name)
                            if old_item:
                                if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    game.player.inventory.append(old_item)
                                    if hasattr(game.player, 'stack_item_in_inventory'):
                                        game.player.stack_item_in_inventory(old_item)
                                else:
                                    old_item.rect.center = game.player.rect.center
                                    game.items_on_ground.append(old_item)
                            display_message(f"{tr('msg', 'Inserted')} {tr('item', found_item.name)}.")
                            
                        game.player.start_action(f"Inserting {tr('item', found_item.name)}", transfer_time, do_insert, xp_reward=1)
                    else:
                        display_message(f"{tr('msg', 'You do not have a suitable item for this slot.')}")
                        
                clicked_on_menu = True

            elif option in ['Add key', 'Add fuel', 'Add motor', 'Add battery', 'Add tire to']:
                veh = getattr(game.player, 'vehicle', None)
                if not veh:
                    for m in game.modals:
                        if m['type'] == 'vehicle':
                            veh = m['vehicle']
                            break
                            
                if veh:
                    slot = None
                    if option == 'Add key': slot = 'key'
                    elif option == 'Add fuel': slot = 'fuel'
                    elif option == 'Add motor': slot = 'motor'
                    elif option == 'Add battery': slot = 'battery'
                    elif option == 'Add tire to': slot = target_sub_slot

                    if slot and veh.can_equip(item, slot):
                        transfer_time = max(0.1, item.get_total_weight() * 0.2)
                        
                        def do_add():
                            if source == 'inventory':
                                game.player.inventory.pop(index)
                            elif source == 'belt':
                                game.player.belt[index] = None
                            elif source == 'gear':
                                game.player.clothes[index] = None
                            elif source == 'container' and container_item:
                                container_item.inventory.pop(index)

                            old_item = veh.add_equipment(item, slot)
                            if old_item:
                                if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    game.player.inventory.append(old_item)
                                    if hasattr(game.player, 'stack_item_in_inventory'):
                                        game.player.stack_item_in_inventory(old_item)
                                else:
                                    old_item.rect.center = game.player.rect.center
                                    game.items_on_ground.append(old_item)
                            display_message(f"{tr('msg', 'Installed')} {tr('item', item.name)} {tr('msg', 'in vehicle')}.")
                            
                        game.player.start_action(f"Installing {tr('item', item.name)}", transfer_time, do_add, xp_reward=1)
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
                                item_t = getattr(item, 'item_type', '') or ''
                                if slot is None and (item_t.startswith('weapon') or item_t == 'tool'):
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
                                
                        if str(getattr(item, 'item_type', '')).startswith('weapon'):
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
            
            elif option == 'Place':
                game.item_to_place = {
                    'item': item,
                    'source': source,
                    'index': index,
                    'container': container_item
                }
                display_message(tr('msg', "Select a location to place the item."))
                clicked_on_menu = True

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
                    
                    default_pos = (GAME_WIDTH / 2 - CRAFTING_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - CRAFTING_MODAL_HEIGHT / 2)
                    
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
                    is_closed_maptile = getattr(item, 'item_type', '') == 'maptile_container' and not getattr(item, 'is_opened', False)

                    def open_and_show_modal():
                        # Open and generate loot if unopened
                        if hasattr(item, 'open'):
                            item.open(game)
                        else:
                            item.is_opened = True

                        modal_exists = any(m['type'] == 'container' and m['item'] == item for m in game.modals)
                        if not modal_exists:
                            new_container_modal = {
                                'id': uuid.uuid4(), 'type': 'container', 'item': item,
                                'position': game.last_modal_positions.get('container', (MESSAGES_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT)),
                                'is_dragging': False, 'drag_offset': (0, 0),
                                'rect': pygame.Rect(game.last_modal_positions.get('container', (MESSAGES_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT))[0], 
                                                    game.last_modal_positions.get('container', (MESSAGES_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT))[1],
                                                    CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT)
                            }
                            game.modals.append(new_container_modal)

                    if is_closed_maptile:
                        if has_app(game, 'open_container_instant'):
                            open_and_show_modal()
                        else:
                            agility = game.player.progression.get_level('agility')
                            open_time = max(0.2, 1.8 - (agility * 0.2))
                            game.player.start_action(tr('ui', "Opening"), open_time, open_and_show_modal, xp_reward=1.5)
                    else:
                        open_and_show_modal()
                        
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

                    def do_grab():
                        grabbed = False
                        item_to_grab = item
                        
                        if item_to_grab.name in ["Campfire on", "Lantern on"]:
                            from core.entities.item.item import Item
                            new_item = Item.create_from_name(item_to_grab.name.replace(" on", " off"))
                            if new_item:
                                new_item.durability = item_to_grab.durability
                                new_item.load = item_to_grab.load
                                new_item.rect.center = item_to_grab.rect.center
                                new_item.x = item_to_grab.x
                                new_item.y = item_to_grab.y
                                item_to_grab = new_item
                                print(f"{item_to_grab.name.split(' ')[0]} extinguished when picked up.")
                                display_message(tr('msg', f"{item_to_grab.name.split(' ')[0]} extinguished when picked up."))

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
                            item_to_grab.is_placed = False
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
        if item and get_belt_hud_slot_rect(i, game=game).collidepoint(mouse_pos):
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
        
        elif modal['type'] == 'vehicle':
            if modal.get('active_tab') == 'Mechanics' and 'equipment_rects' in modal:
                for slot_name, slot_rect in modal['equipment_rects'].items():
                    if slot_rect.collidepoint(mouse_pos):
                        veh = modal['vehicle']
                        existing_item = veh.equipment.get(slot_name)
                        
                        if existing_item:
                            clicked_item = existing_item
                            click_source = 'vehicle_equipment'
                            click_index = slot_name
                            click_container_item = veh
                            break
                        else:
                            game.context_menu['active'] = True
                            game.context_menu['item'] = {'type': 'virtual_slot', 'slot': slot_name, 'vehicle': veh}
                            game.context_menu['source'] = 'vehicle_slot'
                            game.context_menu['index'] = -1
                            game.context_menu['container_item'] = veh
                            game.context_menu['position'] = mouse_pos
                            
                            display_name = slot_name.replace('_', ' ').title()
                            if display_name == 'Tire Fl': display_name = 'Front Left Tire'
                            elif display_name == 'Tire Fr': display_name = 'Front Right Tire'
                            elif display_name == 'Tire Bl': display_name = 'Back Left Tire'
                            elif display_name == 'Tire Br': display_name = 'Back Right Tire'
                            
                            game.context_menu['options'] = [f"Insert {display_name}"]
                            game.context_menu['rects'] = []
                            game.context_menu['action_map'] = []
                            return

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
        adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
        world_pos = game.screen_to_world(adjusted_mouse_pos)

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
            adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
            world_pos = game.screen_to_world(adjusted_mouse_pos)
            for npc in game.npcs:
                if npc.rect.collidepoint(world_pos) and npc.is_friendly and npc.aggro_timer <= 0:
                    clicked_item = npc
                    click_source = 'npc'
                    click_index = 0
                    break

        if not clicked_item:
            adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
            world_pos = game.screen_to_world(adjusted_mouse_pos)
            grid_x = int(world_pos[0] // TILE_SIZE)
            grid_y = int(world_pos[1] // TILE_SIZE)
            tile = game.map_manager.get_tile_at(grid_x, grid_y)
            dx = game.player.rect.centerx - world_pos[0]
            dy = game.player.rect.centery - world_pos[1]
            dist_sq = dx*dx + dy*dy
            max_dist_sq = (TILE_SIZE * 2) ** 2

            if tile:
                if dist_sq <= max_dist_sq:
                    char = ""
                    try: char = game.map_data[grid_y][grid_x]
                    except: pass
                    
                    if tile.get('type') == "maptile_car":
                        vehicle = game.map_manager.get_vehicle_at(grid_x, grid_y)
                        if vehicle:
                            clicked_item = vehicle
                            click_source = 'container_map'
                            click_index = 0
                    elif tile.get('is_statable') or ('door' in char.lower() or 'window' in char.lower()):
                        clicked_item = {
                            'name': tile.get('name', 'Object'), 
                            'type': 'map_tile', 
                            'grid_x': grid_x, 
                            'grid_y': grid_y, 
                            'state': tile.get('state'),
                            'char': char
                        }
                        click_source = 'map_tile'
                    
                else:
                    if tile.get('type') == "maptile_car" or tile.get('is_statable'):
                        display_message(game, tr('msg', "Too far away to interact."))

    if not clicked_item:
        adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
        world_pos = game.screen_to_world(adjusted_mouse_pos)
        for light in game.map_lights:
            if light['rect'].collidepoint(world_pos):
                clicked_item = light
                click_source = 'light_source'
                click_index = 0
                break

    if not clicked_item:
        adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
        world_pos = game.screen_to_world(adjusted_mouse_pos)
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
        
        if 'tooltips' not in game.context_menu:
            game.context_menu['tooltips'] = {}

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
            gx = clicked_item['grid_x']
            gy = clicked_item['grid_y']
            char = clicked_item.get('char', '')
            t_def = game.map_manager.get_tile_at(gx, gy)

            barricade = game.map_manager.get_barricade(gx, gy)

            # 1. Door Open / Close
            if not barricade and 'state' in clicked_item:
                if clicked_item['state'] == 'close':
                    options.append('Open door/window')
                elif clicked_item['state'] == 'open':
                    options.append('Close door/window')

            # 2. Place Barricade / Remove Barricade
            is_door_or_window = ('door' in char.lower() or 'window' in char.lower() or
                                 (t_def and (t_def.get('is_statable') or 'door' in t_def.get('name', '').lower() or 'window' in t_def.get('name', '').lower())))

            if is_door_or_window:
                if barricade:
                    options.append('Remove barricade')
                    req_tools = barricade.get('remove_items', ['Crowbar', 'Hammer', 'Metal Hammer', 'Primitive Hammer', 'Picaxe'])
                    tt_lines = [tr('ui', "To remove barricade need:")]
                    tt_lines.append(f"- {', '.join(req_tools)}")
                    game.context_menu['tooltips']['Remove barricade'] = "\n".join(tt_lines)
                else:
                    options.append('Place barricade')

                    # Find barricade in player inventory/belt or fallback to template
                    barricade_ref = None
                    for it in game.player.inventory + game.player.belt:
                        if _is_barricade_item(it):
                            barricade_ref = it
                            break

                    if not barricade_ref:
                        from core.entities.item.item_data import ITEM_TEMPLATES
                        tmpl = ITEM_TEMPLATES.get('Wood Barricade', {})
                        if tmpl:
                            barricade_ref = Item.create_from_name('Wood Barricade')

                    if barricade_ref and getattr(barricade_ref, 'place_items', None):
                        tt_lines = [tr('ui', "Place barricade need:")]
                        for req in barricade_ref.place_items:
                            cands_str = ", ".join(req.get('items', []))
                            amt = req.get('amount', 1)
                            if amt > 1:
                                tt_lines.append(f"- {cands_str} ({amt}x)")
                            else:
                                tt_lines.append(f"- {cands_str}")
                        game.context_menu['tooltips']['Place barricade'] = "\n".join(tt_lines)
                    else:
                        game.context_menu['tooltips']['Place barricade'] = tr('ui', "Barricade must be in inventory")

            # 3. Repair Door / Window
            if t_def and t_def.get('repair_info'):
                r_info = t_def['repair_info']
                is_broken = '_broke' in char
                map_name = game.map_manager.current_map_filename
                tile_health_map = game.map_states.get(map_name, {}).get('tile_health', {})
                max_h = t_def.get('health_max', 100)
                is_damaged = (gx, gy) in tile_health_map and tile_health_map[(gx, gy)] < max_h

                if is_broken or is_damaged:
                    options.append('Repair Door/Window')
                    tt_lines = [tr('ui', "Required Materials:")]
                    for req_item, req_qty in r_info['items'].items():
                        tt_lines.append(f"- {tr('item', req_item)}: x{req_qty}")
                    if r_info.get('magazine'):
                        tt_lines.append(f"{tr('ui', 'Requires:')} {r_info['magazine']}")
                    game.context_menu['tooltips']['Repair Door/Window'] = "\n".join(tt_lines)
                        
        elif click_source == 'light_source':
            options = ['Toggle Light']
        elif click_source == 'player_self':
            options = ['Status', 'Inventory', 'Gear']
        elif click_source == 'vehicle_equipment':
            if click_index == 'fuel':
                options = ['Remove fuel to']
            else:
                options = ['Remove']
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
        if click_source in ['inventory', 'belt', 'gear']:
            if 'Place' not in options: options.append('Place')
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
                if click_source != 'vehicle_equipment':
                    options.append('Send to')

        veh = getattr(game.player, 'vehicle', None)
        if not veh:
            for m in game.modals:
                if m['type'] == 'vehicle':
                    veh = m['vehicle']
                    break

        if veh and click_source in ['inventory', 'belt', 'gear', 'container']:
            if veh.can_equip(clicked_item, 'key'):
                if 'Add key' not in options: options.append('Add key')
            if veh.can_equip(clicked_item, 'fuel'):
                if 'Add fuel' not in options: options.append('Add fuel')
            if veh.can_equip(clicked_item, 'motor'):
                if 'Add motor' not in options: options.append('Add motor')
            if veh.can_equip(clicked_item, 'battery'):
                if 'Add battery' not in options: options.append('Add battery')
            if veh.can_equip(clicked_item, 'tire_fl'):
                if 'Add tire to' not in options: options.append('Add tire to')

        if item_type not in ['map_tile', 'maptile', 'maptile_container', 'vehicle'] and not isinstance(clicked_item, Corpse) and not is_maptile:
            item_name_to_check = getattr(clicked_item, 'name', '')
            if item_name_to_check:
                if not RecipeManager.RECIPES:
                    RecipeManager.load_recipes()

                has_crafts = any(is_recipe_relevant_to_item(r, item_name_to_check) for r in RecipeManager.RECIPES)
                if has_crafts and 'Crafts' not in options:
                    options.append('Crafts')


        # --- SUBMENU GENERATION LOGIC ---
        new_options = []
        for opt in options:
            if opt.startswith('Add to '): 
                continue 

            if opt == 'Add tire to':
                sub_opts = ['tire_fl', 'tire_fr', 'tire_bl', 'tire_br']
                display_map = {
                    'tire_fl': 'Front Left', 
                    'tire_fr': 'Front Right', 
                    'tire_bl': 'Back Left', 
                    'tire_br': 'Back Right'
                }
                new_options.append({'label': 'Add tire to', 'sub': sub_opts, 'display_names': display_map})
                continue

            if opt == 'Remove fuel to':
                sub_opts = []
                display_map = {}
                tooltip_map = {}
                
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
                    if not getattr(c, 'allow_liquid', False): continue
                    
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
                        
                        if getattr(c, 'allow_liquid', False):
                            for inside_item in getattr(c, 'inventory', []):
                                if getattr(inside_item, 'liquid', False):
                                    liquid_qty += getattr(inside_item, 'load', 1) or 1
                                    liquid_name = inside_item.name
                        
                        max_liq_str = f"/{c.max_liquid}" if getattr(c, 'max_liquid', None) is not None else ""
                        if liquid_qty > 0:
                            display_str = f"{c.name} ({int(liquid_qty)}{max_liq_str} {liquid_name} {tr('ui', 'units')})"
                        elif getattr(c, 'allow_liquid', False):
                            display_str = f"{c.name} (0{max_liq_str} {tr('ui', 'Empty')})"
                        else:
                            display_str = c.name
                            
                        if c_id not in sub_opts:
                            sub_opts.append(c_id)
                            display_map[c_id] = display_str
                            tooltip_map[c_id] = f"{tr('ui', 'Location:')} {loc_str}"
                            
                new_options.append({'label': 'Remove fuel to', 'sub': sub_opts, 'display_names': display_map, 'tooltips': tooltip_map})
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
                        
                elif item_type in ('weapon', 'weapon_melee', 'weapon_ranged', 'weapon_throw', 'tool', 'consumable_medical', 'utility', 'mobile', 'text', 'map', 'consumable_food'):
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
                    if click_container_item and c is click_container_item: continue # Fix: Exclude sending it back instantly to its current physical container
                    
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
                        max_liq_str = f"/{c.max_liquid}" if getattr(c, 'max_liquid', None) is not None else ""
                        if liquid_qty > 0:
                            display_str = f"{c.name} ({int(liquid_qty)}{max_liq_str} {liquid_name} {tr('ui', 'units')})"
                        elif getattr(c, 'allow_liquid', False):
                            display_str = f"{c.name} (0{max_liq_str} {tr('ui', 'Empty')})"
                        else:
                            display_str = c.name
                            
                        # Package for the dropdown architect
                        if c_id not in sub_opts:
                            sub_opts.append(c_id)
                            display_map[c_id] = display_str
                            tooltip_map[c_id] = f"{tr('ui', 'Location:')} {loc_str}"
                            
                new_options.append({'label': 'Send to', 'sub': sub_opts, 'display_names': display_map, 'tooltips': tooltip_map})
                continue

            elif opt == 'Crafts':
                if not RecipeManager.RECIPES:
                    RecipeManager.load_recipes()

                sub_opts = ['open_craft']
                display_map = {'open_craft': tr('ui', 'Open Craft')}
                tooltip_map = {'open_craft': f"{tr('tooltip', 'Open crafting menu')}\n\n{tr('msg', 'The item must be in inventory or nearby to craft')}"}
                color_map = {'open_craft': WHITE}

                item_name = getattr(clicked_item, 'name', '')
                game.context_menu['craft_recipes'] = {}

                # 1. Bucket recipes by craft type using the strict relevance filter
                craft_buckets = {
                    'Craft': [],
                    'Repair': [],
                    'Dismantle': []
                }

                for r in RecipeManager.RECIPES:
                    # Filter out recipes that do not use this item as an ingredient (or repair/dismantle target)
                    if not is_recipe_relevant_to_item(r, item_name):
                        continue

                    raw_type = getattr(r, 'craft_type', 'create').lower()
                    if raw_type == 'repair':
                        cat_key = 'Repair'
                    elif raw_type == 'dismantle':
                        cat_key = 'Dismantle'
                    else:
                        cat_key = 'Craft'

                    can_craft, is_unlocked, missing_ings, missing_mag, missing_skills = get_recipe_status_details(game.player, game, r)
                    craft_buckets[cat_key].append({
                        'recipe': r,
                        'can_craft': can_craft,
                        'is_unlocked': is_unlocked,
                        'missing_ings': missing_ings,
                        'missing_mag': missing_mag,
                        'missing_skills': missing_skills
                    })

                # 2. Append each category in order: Craft -> Repair -> Dismantle
                global_idx = 0
                max_total_recipes = 12

                for cat_name in ['Craft', 'Repair', 'Dismantle']:
                    bucket = craft_buckets[cat_name]
                    if not bucket:
                        continue

                    # Sort: Available crafts (can_craft=True) first
                    bucket.sort(key=lambda d: (not d['can_craft'], d['recipe'].output_name))

                    # Add category header
                    hdr_id = f"header_{cat_name.lower()}"
                    sub_opts.append(hdr_id)
                    display_map[hdr_id] = tr('tab', cat_name)
                    color_map[hdr_id] = (255, 215, 0)

                    for data in bucket:
                        if global_idx >= max_total_recipes:
                            break

                        r = data['recipe']
                        sub_key = f"recipe_{global_idx}"
                        global_idx += 1

                        sub_opts.append(sub_key)
                        game.context_menu['craft_recipes'][sub_key] = r

                        out_name = tr('item', r.output_name)
                        if r.output_amount > 1:
                            out_name = f"{out_name} x{r.output_amount}"

                        display_map[sub_key] = f"- {out_name}"
                        color_map[sub_key] = WHITE if data['can_craft'] else GRAY

                        # Build tooltip
                        tt_lines = [
                            out_name,
                            f"{tr('ui', 'Type')}: {tr('tab', cat_name)}",
                            ""
                        ]

                        if data['can_craft']:
                            tt_lines.append(f"{tr('ui', 'Ready to craft')} ({r.time_required}s)")
                        else:
                            if data['missing_ings']:
                                tt_lines.append(f"{tr('ui', 'Ingredients')}:")
                                for m in data['missing_ings']:
                                    tt_lines.append(f"- {tr('item', m['name'])} ({m['have']}/{m['needed']})")

                            if data['missing_skills'] or data['missing_mag']:
                                if data['missing_ings']:
                                    tt_lines.append("")
                                tt_lines.append(f"{tr('ui', 'Missing skill')}:")
                                for s in data['missing_skills']:
                                    skill_name = tr('ui', s[0].capitalize())
                                    tt_lines.append(f"- {skill_name} (Lv {s[2]})")
                                if data['missing_mag']:
                                    tt_lines.append(f"- {tr('item', data['missing_mag'])}")

                        tt_lines.append("")
                        tt_lines.append(tr('msg', "The item must be in inventory or nearby to craft"))
                        tooltip_map[sub_key] = "\n".join(tt_lines)

                new_options.append({
                    'label': 'Crafts', 
                    'sub': sub_opts, 
                    'display_names': display_map, 
                    'tooltips': tooltip_map,
                    'colors': color_map
                })
                continue

            else:
                new_options.append(opt)
                
        game.context_menu['options'] = new_options

        if game.game_state == 'PAUSED':
            forbidden_opts = ['Read', 'Drink', 'Use', 'Eat', 'Turn on', 'Turn off', 'Toggle Light', 'Crafts', 'Open door/window', 'Close door/window', 'Barricate', 'Unbarricade']
            filtered_options = []
            for o in new_options:
                label = o if isinstance(o, str) else o.get('label')
                if label not in forbidden_opts:
                    filtered_options.append(o)
            game.context_menu['options'] = filtered_options
        else:
            game.context_menu['options'] = new_options

        game.context_menu['rects'] = []
        game.context_menu['action_map'] = []
        return