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
                elif source == 'player_self' or source == 'map_tile' or source == 'ground_context':
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
            
            if option == 'Rest':
                print("You take a rest...")
                game.player.is_resting = True
            
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
            elif option == 'Reload':
                if getattr(item, 'item_type', None) in ['utility', 'mobile']:
                    game.player.reload_utility_item(item, source, index, container_item)
                else:
                    game.player.reload_active_weapon(game=game)

            elif option == 'Get bullets': game.player.unload_weapon(game, item)
            elif option == 'Turn on' or option == 'Turn off': game.player.toggle_utility_item(item, source, index, container_item)
            
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
                    print(f"Equipped {item.name} as backpack.")

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
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
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
                                if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    game.player.inventory.append(old_item)
                                else:
                                    old_item.rect.center = game.player.rect.center
                                    game.items_on_ground.append(old_item)
                else: 
                    if source == 'ground':
                        placed = False
                        for bi, slot in enumerate(game.player.belt):
                            if slot is None and getattr(item, 'item_type', None) in ('weapon', 'tool'):
                                game.player.belt[bi] = item
                                if 0 <= index < len(game.items_on_ground):
                                    game.items_on_ground.pop(index)
                                print(f"Picked up and equipped {item.name} to belt slot {bi+1}.")
                                placed = True
                                break
                        if not placed:
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(item)
                                if 0 <= index < len(game.items_on_ground):
                                    game.items_on_ground.pop(index)
                                print(f"Picked up {item.name} into inventory.")
                            else:
                                print("No space to equip or pick up the item.")
                        if getattr(item, 'item_type', None) == 'weapon':
                            game.player.active_weapon = item
                    else:
                        game.player.equip_item_to_belt(item, source, index, container_item)

            elif option == 'Drop one':
                game.player.drop_item_stack(game, source, index, container_item, 1)
                
            elif option == 'Drop all':
                game.player.drop_item_stack(game, source, index, container_item, 'all')
                
            elif option == 'Send all to Backpack':
                game.player.transfer_item_stack(source, index, container_item, game.player.backpack)
            
            elif option == 'Send all to Inventory':
                game.player.transfer_item_stack(source, index, container_item, game.player) 
            elif option == 'Drop':
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
                    if len(game.player.inventory) < game.player.get_total_inventory_slots():
                        game.player.inventory.append(item)
                    else:
                        item.rect.center = game.player.rect.center
                        game.items_on_ground.append(item)
                elif source == 'backpack':
                    item_to_unequip = game.player.backpack
                    if item_to_unequip and item_to_unequip == item:
                        game.player.backpack = None
                        if len(game.player.inventory) < game.player.get_total_inventory_slots():
                            game.player.inventory.append(item_to_unequip)
                        else:
                            item_to_unequip.rect.center = game.player.rect.center
                            game.items_on_ground.append(item_to_unequip)
                elif source == 'gear':
                    slot_name = index 
                    item_to_unequip = game.player.clothes.get(slot_name)
                    if item_to_unequip and item_to_unequip == item:
                        game.player.clothes[slot_name] = None
                        if len(game.player.inventory) < game.player.get_total_inventory_slots():
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
                        if source == 'ground' and item in game.items_on_ground:
                            game.items_on_ground.remove(item)
                            grabbed = True
                        elif source == 'nearby' and container_item and item in container_item.inventory:
                            container_item.inventory.remove(item)
                            if getattr(container_item, 'item_type', '') == 'ground' and item in game.items_on_ground:
                                game.items_on_ground.remove(item)
                            grabbed = True
                        
                        if grabbed:
                            target_inventory.append(item)
                            game.player.stack_item_in_inventory(item)

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
                        if len(game.player.backpack.inventory) < (game.player.backpack.capacity or 0):
                            game.player.backpack.inventory.append(ground_item)
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
        
        for i, ground_item in enumerate(game.items_on_ground):
            if ground_item.rect.collidepoint(world_pos):
                dist = math.hypot(game.player.rect.centerx - ground_item.rect.centerx, game.player.rect.centery - ground_item.rect.centery)
                if dist < TILE_SIZE * 2:
                    clicked_item = ground_item
                    click_source = 'ground'
                    click_index = i
                    click_container_item = None
                    break
                else:
                    display_message("Item is too far away to interact with.")
        
        if not clicked_item:
            for i, container in enumerate(game.containers):
                if container.rect.collidepoint(world_pos):
                    dist = math.hypot(game.player.rect.centerx - container.rect.centerx, game.player.rect.centery - container.rect.centery)
                    if dist < TILE_SIZE * 2:
                        clicked_item = container
                        click_source = 'container_map'
                        click_index = i
                        click_container_item = None
                        break
                    else:
                        display_message("Item is too far away to interact with.")

        if not clicked_item:
            if game.player.rect.collidepoint(world_pos):
                clicked_item = game.player
                click_source = 'player_self'
                click_index = 0
                click_container_item = None

        if not clicked_item:
            sorted_npcs = sorted(game.npcs, key=lambda n: n.rect.bottom, reverse=True)
            for npc in sorted_npcs:
                if npc.rect.collidepoint(world_pos):
                    clicked_item = npc
                    click_source = 'npc'
                    break

        if not clicked_item:
            world_pos = game.screen_to_world(mouse_pos)
            grid_x = int(world_pos[0] // TILE_SIZE)
            grid_y = int(world_pos[1] // TILE_SIZE)
            tile = game.map_manager.get_tile_at(grid_x, grid_y)
            dist = math.hypot(game.player.rect.centerx - world_pos[0], game.player.rect.centery - world_pos[1])

            if tile and tile.get('type') == "maptile_car":
                if dist <= TILE_SIZE * 2:
                    vehicle = game.map_manager.get_vehicle_at(grid_x, grid_y)
                    if vehicle:
                        clicked_item = vehicle
                        click_source = 'container_map'
                        click_index = 0
            else:
                display_message(game, "Too far away to interact.")

            if tile and tile.get('sleep') and dist < TILE_SIZE * 2:
                clicked_item = {'name': 'Bed', 'type': 'map_tile'} 
                click_source = 'map_tile'

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
            if npc.rect.collidepoint(world_pos):
                clicked_item = npc
                click_source = 'npc'
                click_index = 0
                break

    if not clicked_item and not is_over_any_modal:
        clicked_item = {'name': 'Ground', 'type': 'ground'}
        click_source = 'ground_context'
        click_index = 0

    if clicked_item:
        game.context_menu['active'] = True
        game.context_menu['item'] = clicked_item
        game.context_menu['source'] = click_source
        game.context_menu['index'] = click_index
        game.context_menu['container_item'] = click_container_item
        game.context_menu['position'] = mouse_pos

        options = ['']

        if click_source == 'npc':
            dist = math.hypot(game.player.rect.centerx - clicked_item.rect.centerx, 
                              game.player.rect.centery - clicked_item.rect.centery)
            max_dist_px = TILE_SIZE * 3  
            print(f"DEBUG: NPC Interact - Name: {clicked_item.name}, Friendly: {clicked_item.is_friendly}, Dist: {dist:.1f}/{max_dist_px}")

            if dist <= max_dist_px:
                options.append('Talk')
                if hasattr(clicked_item, 'stop_moving'):
                    clicked_item.stop_moving()
            else:
                display_message(game, "Too far to talk to them.")

        elif click_source == 'map_tile':
            options = ['Sleep']
        elif click_source == 'light_source':
            options = ['Toggle Light']
        elif click_source == 'player_self':
            options = ['Status', 'Inventory', 'Gear']
        elif click_source == 'ground_context':
            options = ['Rest']
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
                if 'Grab' not in options: options.insert(0, 'Grab') 

            if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None and not isinstance(clicked_item, Corpse):
                if can_grab:
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
                options = ['Inspect']
        elif click_source == 'nearby':
            if 'Drop' in options: options.remove('Drop')
            if 'Drop one' in options: options.remove('Drop one') 
            if 'Drop all' in options: options.remove('Drop all') 
            if not isinstance(clicked_item, Corpse):
                if 'Grab' not in options: options.insert(0, 'Grab')

        if getattr(clicked_item, 'capacity', 0) and clicked_item.capacity > 0:
            if getattr(clicked_item, 'item_type', '') in ['container', 'backpack', 'cloth']:
                if 'Open' not in options:
                    options.append('Open')

        game.context_menu['options'] = options
        game.context_menu['rects'] = []
        return