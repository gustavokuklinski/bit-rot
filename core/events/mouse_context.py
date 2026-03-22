import pygame
import uuid
import math
import random
from core.data.config import *
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.ui.inventory_modal import get_belt_hud_slot_rect, get_inventory_slot_rect, get_backpack_slot_rect, get_belt_slot_rect_in_modal
from core.ui.container_modal import get_container_slot_rect
from core.messages import display_message
from core.events.keyboard import toggle_status_modal, toggle_inventory_modal, toggle_nearby_modal, toggle_gear_modal
from core.data.localization import tr

def handle_context_menu_click(game, mouse_pos):
    clicked_on_menu = False
    for i, rect in enumerate(game.context_menu['rects']):
        if rect.collidepoint(mouse_pos):
            option = game.context_menu['options'][i]
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
                elif source == 'backpack' and game.player.backpack:
                    verified_item = game.player.backpack
                
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
                elif source == 'container_map': # Vehicle or object
                    if getattr(item, 'item_type', '') == 'vehicle':
                        verified_item = item # Pass through for vehicles
                    elif container_item: # If it had a container reference
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
                    # Load dialog options
                    dialogs = item.get_dialog_options()
                    
                    # Center the modal
                    pos_x = (GAME_WIDTH // 2) - (NPC_DIALOG_MODAL_WIDTH // 2)
                    pos_y = (GAME_HEIGHT // 2) - (NPC_DIALOG_MODAL_HEIGHT // 2)
                    
                    new_modal = {
                        'id': uuid.uuid4(),
                        'type': 'npc_dialog',
                        'npc': item,
                        'dialogs': dialogs,
                        'position': (pos_x, pos_y),
                        'rect': pygame.Rect(pos_x, pos_y, NPC_DIALOG_MODAL_WIDTH, NPC_DIALOG_MODAL_HEIGHT),
                        'minimized': False,
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
                    'minimized': False,
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
                        'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT),
                        'minimized': False
                    }
                    game.modals.append(new_container_modal)
                 clicked_on_menu = True

            
            if option == 'Status': toggle_status_modal(game)
            elif option == 'Inventory': toggle_inventory_modal(game)
            elif option == 'Gear': toggle_gear_modal(game)

            if option == 'Sleep':
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
            elif option.startswith('Add to '):
                container_name = option[7:]
                
                def can_accept_liquid(container):
                    if not container or not getattr(container, 'allow_liquid', False):
                        return False
                    if len(container.inventory) < (container.capacity or 0):
                        return True
                    for inv_item in container.inventory:
                        if hasattr(inv_item, 'can_stack_with') and inv_item.can_stack_with(item):
                            if getattr(inv_item, 'load', 0) < getattr(inv_item, 'capacity', 1):
                                return True
                    return False

                target_container = None
                for b_item in game.player.belt:
                    if b_item and b_item.name == container_name and can_accept_liquid(b_item):
                        target_container = b_item
                        break
                if not target_container:
                    for i_item in game.player.inventory:
                        if i_item and i_item.name == container_name and can_accept_liquid(i_item):
                            target_container = i_item
                            break
                if not target_container and game.player.backpack and game.player.backpack.name == container_name and can_accept_liquid(game.player.backpack):
                    target_container = game.player.backpack
                if not target_container:
                    for c_item in game.player.clothes.values():
                        if c_item and c_item.name == container_name and can_accept_liquid(c_item):
                            target_container = c_item
                            break
                
                if target_container:
                    def do_add_to_container():
                        removed_item = None
                        if source == 'inventory':
                            if 0 <= index < len(game.player.inventory):
                                removed_item = game.player.inventory.pop(index)
                        elif source == 'belt':
                            if 0 <= index < len(game.player.belt):
                                removed_item = game.player.belt[index]
                                game.player.belt[index] = None
                        elif source == 'container' and container_item:
                            if 0 <= index < len(container_item.inventory):
                                removed_item = container_item.inventory.pop(index)
                        elif source == 'nearby' and container_item:
                            if 0 <= index < len(container_item.inventory):
                                removed_item = container_item.inventory.pop(index)
                                if getattr(container_item, 'item_type', '') == 'ground' and removed_item in game.items_on_ground:
                                    game.items_on_ground.remove(removed_item)
                        elif source == 'ground':
                            if 0 <= index < len(game.items_on_ground):
                                removed_item = game.items_on_ground.pop(index)
                        elif source == 'gear':
                            removed_item = game.player.clothes.get(index)
                            game.player.clothes[index] = None
                        elif source == 'backpack':
                            removed_item = game.player.backpack
                            game.player.backpack = None
                        
                        if removed_item:
                            stacked = False
                            if hasattr(removed_item, 'is_stackable') and removed_item.is_stackable():
                                for inv_item in target_container.inventory:
                                    if inv_item.can_stack_with(removed_item):
                                        avail = inv_item.capacity - inv_item.load
                                        trans = min(avail, removed_item.load)
                                        inv_item.load += trans
                                        removed_item.load -= trans
                                        if removed_item.load <= 0:
                                            stacked = True
                                            break
                            if not stacked:
                                target_container.inventory.append(removed_item)
                            elif removed_item.load > 0:
                                target_container.inventory.append(removed_item)
                    
                    if source in ['nearby', 'ground', 'container', 'container_map']:
                        game.player.start_action(f"Transferring to {target_container.name}", 1.0, do_add_to_container, xp_reward=0.5)
                    else:
                        do_add_to_container()
                
                clicked_on_menu = True

            elif option == 'Reload':
                if getattr(item, 'item_type', None) in ['utility', 'mobile']:
                    game.player.reload_utility_item(item, source, index, container_item)
                else:
                    game.player.reload_active_weapon(game=game)

            elif option == 'Get bullets': game.player.unload_weapon(game, item)
            elif option == 'Turn on' or option == 'Turn off':
                result = game.player.toggle_utility_item(item, source, index, container_item)
                # Handle ground source - replace item in game.items_on_ground
                if source == 'ground' and result and hasattr(result, 'name'):
                    if index is not None and 0 <= index < len(game.items_on_ground):
                        game.items_on_ground[index] = result
                elif source == 'nearby' and container_item and result and hasattr(result, 'name'):
                    # Check if it's a VirtualGroundContainer (ground items in nearby modal)
                    if getattr(container_item, 'item_type', '') == 'ground':
                        # Find and replace the item in game.items_on_ground using identity comparison
                        for i, ground_item in enumerate(game.items_on_ground):
                            if ground_item is item:
                                game.items_on_ground[i] = result
                                break
                    # For other containers, the replacement is already done in toggle_utility_item
            
            elif option == 'Equip':
                if getattr(item, 'item_type', None) == 'backpack':
                    def remove_from_source(src, idx, c_item=None):
                        if src == 'inventory' and 0 <= idx < len(game.player.inventory):
                            return game.player.inventory.pop(idx)
                        if src == 'belt' and 0 <= idx < len(game.player.belt):
                            it = game.player.belt[idx]
                            game.player.belt[idx] = None
                            return it
                        if src == 'container' and c_item and 0 <= idx < len(c_item.inventory):
                            return c_item.inventory.pop(idx)
                        if (src == 'container' or src == 'nearby') and c_item and 0 <= idx < len(c_item.inventory):
                            it = c_item.inventory.pop(idx)
                            if getattr(c_item, 'item_type', '') == 'ground' and it in game.items_on_ground:
                                game.items_on_ground.remove(it)
                            return it
                        if src == 'ground' and 0 <= idx < len(game.items_on_ground):
                            return game.items_on_ground.pop(idx)
                        return None

                    old_backpack = game.player.backpack
                    removed = remove_from_source(source, index, container_item)
                    game.player.backpack = item
                    print(f"Equipped {tr('item', item.name)} as backpack.")

                    if old_backpack:
                        placed = False
                        if source == 'inventory':
                            game.player.inventory.insert(index if 0 <= index <= len(game.player.inventory) else len(game.player.inventory), old_backpack)
                            placed = True
                        elif source == 'belt':
                            if 0 <= index < len(game.player.belt) and game.player.belt[index] is None:
                                game.player.belt[index] = old_backpack
                                placed = True
                            else:
                                for bi in range(len(game.player.belt)):
                                    if game.player.belt[bi] is None:
                                        game.player.belt[bi] = old_backpack
                                        placed = True
                                        break
                        elif source == 'container' and container_item:
                            container_item.inventory.insert(index if 0 <= index <= len(container_item.inventory) else len(container_item.inventory), old_backpack)
                            placed = True
                        if not placed:
                            if getattr(old_backpack, 'liquid', False):
                                old_backpack.rect.center = game.player.rect.center
                                game.items_on_ground.append(old_backpack)
                            elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(old_backpack)
                            else:
                                old_backpack.rect.center = game.player.rect.center
                                game.items_on_ground.append(old_backpack)
                                print(f"No space to return old backpack; dropped {old_backpack.name} on ground.")
                
                elif getattr(item, 'item_type', None) == 'cloth':
                    item_slot = getattr(item, 'slot', None)
                    if item_slot == 'hand': item_slot = 'hands'
                    
                    if item_slot in game.player.clothes_slots:
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
                
            elif option == 'Send all to Backpack':
                game.player.transfer_item_stack(source, index, container_item, game.player.backpack)
            
            elif option == 'Send all to Inventory':
                game.player.transfer_item_stack(source, index, container_item, game.player) 
            
            elif option == 'Drop':
                if getattr(item, 'liquid', False):
                    print(f"The {tr('item', item.name)} spills.")
                    if source == 'backpack':
                        game.player.backpack = None
                    elif source == 'gear':
                        game.player.clothes[index] = None
                    elif source == 'inventory' and 0 <= index < len(game.player.inventory):
                        game.player.inventory.pop(index)
                    elif source == 'belt' and 0 <= index < len(game.player.belt):
                        game.player.belt[index] = None
                    elif source == 'container' and container_item and 0 <= index < len(container_item.inventory):
                        container_item.inventory.pop(index)
                else:
                    dropped_item = None
                    if source == 'backpack':
                        dropped_item = game.player.drop_item(game, source, index, container_item)
                        if dropped_item:
                            print(f"Dropped {dropped_item.name} from backpack slot.")
                    elif source == 'gear':
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
                            'minimized': False, 'scroll_offset_y': 0
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
                        'minimized': False,
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
                            'minimized': False, 'active_tab': 'Clock'
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
                            'minimized': False, 'scroll_offset_y': 0
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
                            'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1],CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT),
                            'minimized': False
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
                elif source == 'backpack':
                    item_to_unequip = game.player.backpack
                    if item_to_unequip and item_to_unequip == item:
                        game.player.backpack = None
                        if getattr(item_to_unequip, 'liquid', False):
                            item_to_unequip.rect.center = game.player.rect.center
                            game.items_on_ground.append(item_to_unequip)
                        elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                            game.player.inventory.append(item_to_unequip)
                        else:
                            item_to_unequip.rect.center = game.player.rect.center
                            game.items_on_ground.append(item_to_unequip)
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
                

            elif (source == 'ground' or source == 'nearby') and option == 'Grab':

                target_inventory = game.player.inventory
                target_capacity = game.player.get_total_inventory_slots()

                if len(target_inventory) < target_capacity:

                    def do_grab():
                        grabbed = False
                        item_to_grab = item
                        
                        # Convert "Campfire on" to "Campfire off" when picking up
                        if tr('item', item.name) == "Campfire on":
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

                        if source == 'ground' and item in game.items_on_ground:
                            game.items_on_ground.remove(item)
                            grabbed = True
                        elif source == 'nearby' and container_item and item in container_item.inventory:
                            container_item.inventory.remove(item)
                            if getattr(container_item, 'item_type', '') == 'ground' and item in game.items_on_ground:
                                game.items_on_ground.remove(item)
                            grabbed = True

                        if grabbed:
                            target_inventory.append(item_to_grab)
                            game.player.stack_item_in_inventory(item_to_grab)

                    if source == 'nearby':
                        game.player.start_action("Looting", 1.0, do_grab, xp_reward=0.5)
                    else:
                        do_grab()
                else:
                    print("Inventory full.")


            elif source == 'ground' and option == 'Place on Backpack':
                if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None:
                    ground_idx = index
                    if 0 <= ground_idx < len(game.items_on_ground):
                        ground_item = game.items_on_ground[ground_idx]
                        item_to_place = ground_item
                        
                        # Convert "Campfire on" to "Campfire off" when placing in backpack
                        if ground_item.name == "Campfire on":
                            from core.entities.item.item import Item
                            new_item = Item.create_from_name("Campfire off")
                            if new_item:
                                new_item.durability = ground_item.durability
                                new_item.load = ground_item.load
                                item_to_place = new_item
                                print("Campfire extinguished when placed in backpack.")
                        
                        if len(game.player.backpack.inventory) < (game.player.backpack.capacity or 0):
                            game.player.backpack.inventory.append(item_to_place)
                            game.items_on_ground.pop(ground_idx)

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
                if not clicked_item:
                    if game.player.backpack and get_backpack_slot_rect(modal['position']).collidepoint(mouse_pos):
                        clicked_item, click_source, click_index = game.player.backpack, 'backpack', 0
                
            
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

            elif modal.get('active_tab') == 'Bag':
                if game.player.backpack:
                    pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                    for i, item in enumerate(game.player.backpack.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            clicked_item = item
                            click_source = 'container'
                            click_index = i
                            click_container_item = game.player.backpack
                            break
        
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
                # [MODIFIED] Fallback check also requires the NPC to be friendly and calm
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
                    # --- NEW: Check if the tile can be opened/closed ---
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
                    # Only show distance warning if they clicked something interactable
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
            # Fallback check also requires the NPC to be friendly
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
            dist = dist_sq ** 0.5  # Only compute sqrt for debug display
            print(f"DEBUG: NPC Interact - Name: {clicked_item.name}, Friendly: {clicked_item.is_friendly}, Dist: {dist:.1f}/{max_dist_px}")

            if dist_sq <= max_dist_px_sq:
                # Final safety check before providing the Talk option
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
            # --- NEW: Provide contextual Open/Close text based on current state ---
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

        if click_source == 'belt':
            if 'Unequip' not in options: options.append('Unequip')
            options = [o for o in options if o != 'Equip']
        elif click_source == 'backpack':
            if 'Unequip' not in options: options.append('Unequip')
            if 'Drop' not in options: options.append('Drop')
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
            elif is_camp and clicked_item.inventory:
                can_grab = False
            
            if can_grab:
                if not getattr(clicked_item, 'liquid', False):
                    if 'Grab' not in options: options.insert(0, 'Grab') 

            if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None and not isinstance(clicked_item, Corpse):
                if can_grab:
                    bp_allow_liquid = getattr(game.player.backpack, 'allow_liquid', False)
                    is_item_liquid = getattr(clicked_item, 'liquid', False)
                    if bp_allow_liquid == is_item_liquid:
                        if 'Place on Backpack' not in options: options.append('Place on Backpack')

            if is_camp and getattr(clicked_item, 'allow_sleep', False):
                options.append('Sleep')

            if getattr(clicked_item, 'inventory', None) is not None:
                is_valid_type = getattr(clicked_item, 'item_type', '') in ['backpack', 'container', 'cloth']
                if isinstance(clicked_item, Corpse) or is_valid_type:
                    if 'Open' not in options: options.append('Open')
                
        elif click_source == 'container_map':
            if getattr(clicked_item, 'item_type', '') == 'vehicle':
                options = ['Vehicle options', 'Trunk']
            else:
                options = ['Open'] # Changed from 'Inspect' to 'Open'
        elif click_source == 'nearby':
            if 'Drop' in options: options.remove('Drop')
            if 'Drop one' in options: options.remove('Drop one') 
            if 'Drop all' in options: options.remove('Drop all') 
            if not isinstance(clicked_item, Corpse):
                if not getattr(clicked_item, 'liquid', False):
                    if 'Grab' not in options: options.insert(0, 'Grab')

        if getattr(clicked_item, 'capacity', 0) and clicked_item.capacity > 0:
            if getattr(clicked_item, 'item_type', '') in ['container', 'backpack', 'cloth']:
                if 'Open' not in options:
                    options.append('Open')

        game.context_menu['options'] = options
        game.context_menu['rects'] = []
        return