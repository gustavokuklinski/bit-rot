import pygame
import uuid
import random
import math

from data.config import *
from core.entities.item.item import Item, Projectile
from core.entities.zombie.corpse import Corpse
from core.update import player_hit_zombie, handle_zombie_death
# Import the new gear slot rect getter
from core.ui.inventory import get_belt_slot_rect_in_modal, get_inventory_slot_rect, get_backpack_slot_rect, get_invcontainer_slot_rect, get_gear_slot_rects
from core.ui.container import get_container_slot_rect
from core.messages import display_message
from core.events.keyboard import toggle_messages_modal, toggle_status_modal, toggle_inventory_modal, toggle_nearby_modal

def handle_mouse_down(game, event, mouse_pos):
    if event.button == 1:
        # Check for tab clicks (This part is correct)
        for modal in reversed(game.modals):
            if modal['type'] in ['nearby', 'status', 'inventory'] and 'tab_rects' in modal and 'tabs_data' in modal:
                tab_rects = modal.get('tab_rects', [])
                tabs_data = modal.get('tabs_data', [])
                clicked_tab = False
                for i, tab_rect in enumerate(tab_rects):
                    if tab_rect.collidepoint(mouse_pos):
                        if i < len(tabs_data):
                            modal['active_tab'] = tabs_data[i]['label']
                            clicked_tab = True
                            break 
                if clicked_tab:
                    return 

        # (Existing code for modal buttons: close, minimize)
        for button in getattr(game, 'modal_buttons', []):
            if button['rect'].collidepoint(mouse_pos):
                modal_to_affect = next((m for m in game.modals if m['id'] == button['id']), None)
                if modal_to_affect:
                    if button['type'] == 'close':
                        game.modals.remove(modal_to_affect)
                        return
                    elif button['type'] == 'minimize':
                        is_minimized = not modal_to_affect.get('minimized', False)
                        modal_to_affect['minimized'] = is_minimized
                        header_height = 35
                        if modal_to_affect['type'] == 'inventory':
                            full_height = INVENTORY_MODAL_HEIGHT
                        elif modal_to_affect['type'] == 'status':
                            full_height = STATUS_MODAL_HEIGHT
                        elif modal_to_affect['type'] == 'messages':
                            full_height = MESSAGES_MODAL_HEIGHT
                        else: 
                            full_height = 300 
                        modal_to_affect['rect'].height = header_height if is_minimized else full_height
                        return

        # (Existing code for UI buttons: status, inventory, etc.)
        if game.status_button_rect and game.status_button_rect.collidepoint(mouse_pos):
            toggle_status_modal(game)
            return
        if game.inventory_button_rect and game.inventory_button_rect.collidepoint(mouse_pos):
            toggle_inventory_modal(game)
            return
        if game.nearby_button_rect and game.nearby_button_rect.collidepoint(mouse_pos):
            toggle_nearby_modal(game)
            return
        if game.messages_button_rect and game.messages_button_rect.collidepoint(mouse_pos):
            toggle_messages_modal(game)
            return

        # (Existing code for opening backpack from inventory)
        for modal in reversed(game.modals):
            if modal['type'] == 'inventory':
                if modal.get('active_tab', 'Inventory') == 'Inventory':
                    backpack_slot_rect = get_backpack_slot_rect(modal['position'])
                    if backpack_slot_rect.collidepoint(mouse_pos) and game.player.backpack:
                        modal_exists = any(m for m in game.modals if m['type'] == 'container' and m['item'] == game.player.backpack)
                        if not modal_exists:
                            new_container_modal = {
                                'id': uuid.uuid4(),
                                'type': 'container',
                                'item': game.player.backpack,
                                'position': game.last_modal_positions['container'],
                                'is_dragging': False, 'drag_offset': (0, 0),
                                'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], 300, 300),
                                'minimized': False
                            }
                            game.modals.append(new_container_modal)
                        return

        # (Existing code for modal dragging)
        for modal in reversed(game.modals):
            modal_header_rect = pygame.Rect(modal['position'][0], modal['position'][1], modal['rect'].width, 35)
            if modal_header_rect.collidepoint(mouse_pos):
                modal['is_dragging'] = True
                modal['drag_offset'] = (mouse_pos[0] - modal['position'][0], mouse_pos[1] - modal['position'][1])
                game.modals.remove(modal)
                game.modals.append(modal)
                return

        if game.context_menu['active']:
            handle_context_menu_click(game, mouse_pos)
            return

        # This function now checks the active tab
        handle_left_click_drag_candidate(game, mouse_pos)

        if (pygame.key.get_pressed()[pygame.K_LSHIFT] or pygame.key.get_pressed()[pygame.K_RSHIFT]):
            handle_attack(game, mouse_pos)

    elif event.button == 3:
        if game.context_menu['active']:
            game.context_menu['active'] = False
            return

        handle_right_click(game, mouse_pos)
        return

def handle_mouse_up(game, event, mouse_pos):
    for modal in reversed(game.modals):
        modal['is_dragging'] = False

    if event.button == 1:
        dropped_successfully = False
        if game.is_dragging or game.drag_candidate:
            if not game.is_dragging and game.drag_candidate:
                pass 

            if game.dragged_item:
                i_orig, type_orig, *container_info = game.drag_origin
                container_obj = container_info[0] if type_orig in ('container', 'nearby', 'inventory_stack_split', 'belt_stack_split', 'container_stack_split', 'nearby_stack_split', 'gear_stack_split') and container_info else None # Added gear_stack_split
                
               
                # --- 1. Check for Drop on BELT ---
                for i_target in range(len(game.player.belt)):
                    if any(modal['type'] == 'inventory' and get_belt_slot_rect_in_modal(i_target, modal['position']).collidepoint(mouse_pos) for modal in reversed(game.modals)):
                        if getattr(game.dragged_item, 'item_type', None) == 'backpack':
                            print("Cannot place backpacks on the belt.")
                            break 
                        
                        item_in_slot = game.player.belt[i_target]
                        
                        if item_in_slot is None:
                            game.player.belt[i_target] = game.dragged_item
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
                            game.dragged_item = item_to_swap 
                            dropped_successfully = False
                        
                        if dropped_successfully: break
                if dropped_successfully:
                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                    return

                # --- 2. Check for Drop on INVENTORY, BACKPACK, INVCONTAINER, or GEAR ---
                for modal in reversed(game.modals):
                    if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
                        
                        # --- START TAB-BASED LOGIC ---
                        if modal.get('active_tab', 'Inventory') == 'Inventory':
                            # --- 2a. Check for Drop on BACKPACK slot ---
                            backpack_slot_rect = get_backpack_slot_rect(modal['position'])
                            if backpack_slot_rect.collidepoint(mouse_pos):
                                if getattr(game.dragged_item, 'item_type', None) == 'backpack':
                                    old_backpack = game.player.backpack
                                    game.player.backpack = game.dragged_item
                                    game.dragged_item = old_backpack 
                                    dropped_successfully = False 
                                    if game.dragged_item is None: 
                                        dropped_successfully = True
                                else:
                                    print("Only backpacks can go in this slot.")
                                if dropped_successfully: break

                            # --- 2b. Check for Drop on INVCONTAINER slot ---
                            invcontainer_slot_rect = get_invcontainer_slot_rect(modal['position'])
                            if not dropped_successfully and invcontainer_slot_rect.collidepoint(mouse_pos):
                                if (game.player.invcontainer and 
                                    hasattr(game.player.invcontainer, 'inventory') and
                                    game.dragged_item is not game.player.invcontainer): 
                                    
                                    container = game.player.invcontainer
                                    stacked = False
                                    for item_in_slot in container.inventory:
                                        if item_in_slot.can_stack_with(game.dragged_item):
                                            available_space = item_in_slot.capacity - item_in_slot.load
                                            transfer = min(available_space, game.dragged_item.load)
                                            item_in_slot.load += transfer
                                            game.dragged_item.load -= transfer
                                            if game.dragged_item.load <= 0:
                                                dropped_successfully = True
                                            stacked = True
                                            break
                                    
                                    if not stacked and len(container.inventory) < (container.capacity or 0):
                                        container.inventory.append(game.dragged_item)
                                        dropped_successfully = True
                                    
                                    if dropped_successfully:
                                        break 

                                if not dropped_successfully:
                                    dragged_type = getattr(game.dragged_item, 'item_type', None)
                                    dragged_ammo_type = getattr(game.dragged_item, 'ammo_type', None)
                                    is_allowed_type = (
                                        dragged_type == 'container' or
                                        dragged_type == 'utility' or
                                        (dragged_type == 'consumable' and dragged_ammo_type is not None)
                                    )
                                    if is_allowed_type:
                                        old_invcontainer = game.player.invcontainer
                                        game.player.invcontainer = game.dragged_item
                                        game.dragged_item = old_invcontainer
                                        dropped_successfully = False 
                                        if game.dragged_item is None:
                                            dropped_successfully = True
                                    else:
                                        print("Only containers (non-backpack), utilities, or ammo can go in this slot.")
                                if dropped_successfully: break

                            # --- 2c. Check for Drop on INVENTORY ---
                            if not dropped_successfully:
                                target_index = -1
                                for i in range(5): # Main 5 slots
                                    if get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                                        target_index = i
                                        break
                                
                                if target_index != -1: # Clicked on one of the 5 slots
                                    if target_index < len(game.player.inventory):
                                        item_in_slot = game.player.inventory[target_index]
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
                                        game.player.inventory.insert(target_index, game.dragged_item)
                                        dropped_successfully = True
                                    else:
                                        print("Inventory is full.")
                                
                                elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    # Dropped on empty space, not a specific slot
                                    game.player.inventory.append(game.dragged_item)
                                    dropped_successfully = True
                                else:
                                    print("Inventory is full.")
                                
                                if dropped_successfully: break
                        
                        elif modal.get('active_tab') == 'Gear':
                            # --- 2d. Check for Drop on GEAR slots ---
                            if 'gear_slot_rects' in modal:
                                for slot_name, slot_rect in modal['gear_slot_rects'].items():
                                    if slot_rect.collidepoint(mouse_pos):
                                        dragged_item = game.dragged_item
                                        item_slot = getattr(dragged_item, 'slot', None)
                                        if item_slot == 'hand': 
                                            item_slot = 'hands' 
                                            
                                        if item_slot == slot_name:
                                            item_in_slot = game.player.clothes.get(slot_name)
                                            game.player.clothes[slot_name] = dragged_item
                                            game.dragged_item = item_in_slot 
                                            dropped_successfully = (item_in_slot is None)
                                        else:
                                            print(f"Cannot place {dragged_item.name} in {slot_name} slot.")
                                            dropped_successfully = False 
                                        
                                        break # Slot was found, stop checking
                            if dropped_successfully: break
                        # --- END TAB-BASED LOGIC ---

                if dropped_successfully:
                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                    return
                # --- END OF INVENTORY MODAL CHECKS ---


                # --- 3. Check for Drop on CONTAINER/NEARBY ---
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
                        if game.dragged_item is container: continue
                        if game.dragged_item is game.player.backpack and container is game.player.backpack: continue

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
                                available_space = item_in_slot.capacity - item_in_slot.load
                                transfer = min(available_space, game.dragged_item.load)
                                item_in_slot.load += transfer
                                game.dragged_item.load -= transfer
                                if game.dragged_item.load <= 0:
                                    dropped_successfully = True
                            else:
                                item_to_swap = container.inventory.pop(target_index)
                                container.inventory.insert(target_index, game.dragged_item)
                                game.dragged_item = item_to_swap
                                dropped_successfully = False 
                        elif len(container.inventory) < (container.capacity or 0):
                            container.inventory.append(game.dragged_item)
                            dropped_successfully = True
                        else:
                            print(f"{container.name} is full.")
                        
                        if dropped_successfully: break
                if dropped_successfully:
                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                    return

            # --- 4. Bounce back or Drop on Ground ---
            if not dropped_successfully:
                game_world_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
                if game.dragged_item:
                    if game_world_rect.collidepoint(mouse_pos):
                        dropped_on_stack = False
                        for ground_item in game.items_on_ground:
                            if ground_item.rect.collidepoint(game.screen_to_world(mouse_pos)) and ground_item.can_stack_with(game.dragged_item):
                                available_space = ground_item.capacity - ground_item.load
                                transfer = min(available_space, game.dragged_item.load)
                                ground_item.load += transfer
                                game.dragged_item.load -= transfer
                                if game.dragged_item.load <= 0:
                                    dropped_successfully = True
                                dropped_on_stack = True
                                break
                        
                        if not dropped_on_stack:
                            game.dragged_item.rect.center = game.screen_to_world(mouse_pos)
                            game.items_on_ground.append(game.dragged_item)
                            dropped_successfully = True
                    
                    if not dropped_successfully and game.dragged_item:
                        # BOUNCE BACK
                        if type_orig == 'inventory' and 0 <= i_orig <= len(game.player.inventory):
                            game.player.inventory.insert(i_orig, game.dragged_item)
                        elif type_orig == 'belt' and 0 <= i_orig < len(game.player.belt):
                            game.player.belt[i_orig] = game.dragged_item
                        elif type_orig == 'backpack':
                            game.player.backpack = game.dragged_item
                        elif type_orig == 'invcontainer':
                            game.player.invcontainer = game.dragged_item
                        elif type_orig == 'gear':
                            slot_name = i_orig 
                            game.player.clothes[slot_name] = game.dragged_item
                        elif type_orig == 'container' and container_obj is not None:
                            container_obj.inventory.insert(i_orig, game.dragged_item)
                        elif type_orig == 'nearby' and container_obj is not None:
                            container_obj.inventory.insert(i_orig, game.dragged_item)
                        elif 'stack_split' in type_orig:
                            try:
                                if type_orig == 'inventory_stack_split':
                                    game.player.inventory[i_orig].load += game.dragged_item.load
                                elif type_orig == 'belt_stack_split':
                                    game.player.belt[i_orig].load += game.dragged_item.load
                                # --- NEW GEAR LOGIC (BOUNCE BACK STACK) ---
                                elif type_orig == 'gear_stack_split':
                                    game.player.clothes[i_orig].load += game.dragged_item.load
                                # --- END NEW GEAR LOGIC ---
                                elif type_orig == 'container_stack_split':
                                    container_obj.inventory[i_orig].load += game.dragged_item.load
                                elif type_orig == 'nearby_stack_split':
                                    container_obj.inventory[i_orig].load += game.dragged_item.load
                            except Exception as e:
                                print(f"Stack bounce back failed: {e}")
                        else:
                            game.player.inventory.append(game.dragged_item) # Failsafe
                

        game.is_dragging = False
        game.dragged_item = None
        game.drag_origin = None
        game.drag_candidate = None

def find_item_at_pos(game, mouse_pos):
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
                if game.player.backpack and get_backpack_slot_rect(modal['position']).collidepoint(mouse_pos):
                    return game.player.backpack
                if game.player.invcontainer and get_invcontainer_slot_rect(modal['position']).collidepoint(mouse_pos):
                    return game.player.invcontainer
            
            elif modal.get('active_tab') == 'Gear':
                # Use the rects stored in the modal (calculated by _draw_gear_tab)
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            return game.player.clothes.get(slot_name)
        
        elif modal['type'] == 'container':
            container = modal['item']
            for i, item in enumerate(container.inventory):
                if item and get_container_slot_rect(modal['position'], i).collidepoint(mouse_pos):
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

def handle_mouse_motion(game, event, mouse_pos):
    game.hovered_item = find_item_at_pos(game, mouse_pos)

    game.hovered_container = None
    world_pos = game.screen_to_world(mouse_pos)
    for container in game.containers:
        if container.rect.collidepoint(world_pos):
            game.hovered_container = container
            break

    if game.context_menu['active']:
        pass

    if game.drag_candidate and not game.is_dragging:
        dist = math.hypot(mouse_pos[0] - game.drag_start_pos[0], mouse_pos[1] - game.drag_start_pos[1])
        if dist > game.DRAG_THRESHOLD:
            game.is_dragging = True
            item_to_drag, origin_tuple = game.drag_candidate
            i_orig, type_orig, *container_info = origin_tuple
            
            if hasattr(item_to_drag, 'is_stackable') and item_to_drag.is_stackable() and item_to_drag.load > 1:
                item_to_drag.load -= 1
                new_item = Item.create_from_name(item_to_drag.name)
                new_item.load = 1
                new_item.durability = item_to_drag.durability
                game.dragged_item = new_item
                # --- NEW GEAR LOGIC: Add gear_stack_split type ---
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
                elif type_orig == 'backpack':
                    game.player.backpack = None
                elif type_orig == 'invcontainer':
                    game.player.invcontainer = None
                elif type_orig == 'gear':
                    slot_name = i_orig 
                    game.player.clothes[slot_name] = None 
                elif type_orig == 'container':
                    container_obj = container_info[0]
                    container_obj.inventory.pop(i_orig)
                elif type_orig == 'nearby':
                    container_obj = container_info[0]
                    container_obj.inventory.pop(i_orig)
            
            game.drag_candidate = None 

    for modal in reversed(game.modals):
        if modal['is_dragging']:
            new_x = mouse_pos[0] - modal['drag_offset'][0]
            new_y = mouse_pos[1] - modal['drag_offset'][1]
            is_minimized = modal.get('minimized', False)
            header_height = 35
            modal_width = modal['rect'].width
            modal_height = header_height if is_minimized else modal['rect'].height
            clamped_x = max(0, min(new_x, VIRTUAL_SCREEN_WIDTH - modal_width))
            clamped_y = max(0, min(new_y, VIRTUAL_GAME_HEIGHT - modal_height))
            modal['position'] = (clamped_x, clamped_y)
            modal['rect'].topleft = modal['position']

def resolve_drag_origin_from_item(item, player, modals):
    """Finds where an item is located (inventory, belt, gear, etc.)."""
    if item is None:
        return None
    try:
        if item in player.inventory:
            return (player.inventory.index(item), 'inventory')
        if item in player.belt:
            return (player.belt.index(item), 'belt')
        if player.backpack is item:
            return (0, 'backpack')
        if player.invcontainer is item:
            return (0, 'invcontainer')
        
        if item in player.clothes.values():
            for slot_name, cloth_item in player.clothes.items():
                if cloth_item == item:
                    return (slot_name, 'gear') 
        
        for modal in reversed(modals):
            if modal.get('type') == 'container' and modal.get('item') and hasattr(modal['item'], 'inventory'):
                cont = modal['item']
                if item in cont.inventory:
                    return (cont.inventory.index(item), 'container', cont)
            elif modal.get('type') == 'nearby':
                active_tab_label = modal.get('active_tab')
                tabs_data = modal.get('tabs_data', []) # Use tabs_data, not instance
                active_container = None
                for tab_data in tabs_data:
                    if tab_data['label'] == active_tab_label:
                        active_container = tab_data['container']
                        break
                if active_container and hasattr(active_container, 'inventory') and item in active_container.inventory:
                    return (active_container.inventory.index(item), 'nearby', active_container)

    except Exception:
        pass
    return None


def handle_context_menu_click(game, mouse_pos):
    clicked_on_menu = False
    for i, rect in enumerate(game.context_menu['rects']):
        if rect.collidepoint(mouse_pos):
            option = game.context_menu['options'][i]
            item = game.context_menu['item']
            source = game.context_menu['source']
            index = game.context_menu['index']
            container_item = game.context_menu.get('container_item')

            print(f"Clicked '{option}' on '{getattr(item,'name',str(item))}' (source={source})")

            if option == 'Use':
                game.player.consume_item(item, source, index, container_item)
            elif option == 'Reload':
                if getattr(item, 'item_type', None) == 'utility':
                    game.player.reload_utility_item(item, source, index, container_item)
                else:
                    game.player.reload_active_weapon() 
            elif option == 'Turn on' or option == 'Turn off':
                game.player.toggle_utility_item(item, source, index, container_item)
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
                    if item_slot == 'hand': 
                        item_slot = 'hands'
                    
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
                            print(f"Error equipping cloth: item not found at source {source}.")
                
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
                dropped = game.player.drop_item_stack(source, index, container_item, 1)
                if dropped:
                    game.items_on_ground.append(dropped)
            elif option == 'Drop all':
                dropped = game.player.drop_item_stack(source, index, container_item, 'all')
                if dropped:
                    game.items_on_ground.append(dropped)
            elif option == 'Send all to Backpack':
                game.player.transfer_item_stack(source, index, container_item, game.player.backpack)
            elif option == 'Send all to Utility':
                game.player.transfer_item_stack(source, index, container_item, game.player.invcontainer)
            elif option == 'Send all to Inventory':
                game.player.transfer_item_stack(source, index, container_item, game.player) 
            elif option == 'Drop':
                dropped_item = None
                if source == 'backpack':
                    item_to_drop = game.player.backpack
                    if item_to_drop and item_to_drop == item:
                        game.player.backpack = None
                        item_to_drop.rect.center = game.player.rect.center
                        game.items_on_ground.append(item_to_drop)
                        print(f"Dropped {item_to_drop.name} from backpack slot.")
                        dropped_item = item_to_drop
                    else:
                        print("Backpack drop error: item mismatch.")
                
                elif source == 'gear':
                    slot_name = index 
                    item_to_drop = game.player.clothes.get(slot_name)
                    if item_to_drop and item_to_drop == item:
                        game.player.clothes[slot_name] = None
                        item_to_drop.rect.center = game.player.rect.center
                        game.items_on_ground.append(item_to_drop)
                        print(f"Dropped {item_to_drop.name} from {slot_name} slot.")
                        dropped_item = item_to_drop
                
                elif source == 'invcontainer':
                    slot_name = index 
                    item_to_unequip = game.player.clothes.get(slot_name)
                    if item_to_unequip and item_to_unequip == item:
                        game.player.clothes[slot_name] = None
                        if len(game.player.inventory) < game.player.get_total_inventory_slots():
                            game.player.inventory.append(item_to_unequip)
                            print(f"Unequipped {item_to_unequip.name} -> Inventory")
                        else:
                            item_to_unequip.rect.center = game.player.rect.center
                            game.items_on_ground.append(item_to_unequip)
                
                else:
                    dropped_item = game.player.drop_item(source, index, container_item)
                    if dropped_item:
                        dropped_item.rect.center = game.player.rect.center
                        game.items_on_ground.append(dropped_item)

            elif option == 'Open':
                modal_exists = any(m['type'] == 'container' and m['item'] == item for m in game.modals)
                if not modal_exists:
                    new_container_modal = {
                        'id': uuid.uuid4(),
                        'type': 'container',
                        'item': item,
                        'position': game.last_modal_positions['container'],
                        'is_dragging': False, 'drag_offset': (0, 0),
                        'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], 300, 300),
                        'minimized': False
                    }
                    game.modals.append(new_container_modal)
            elif option == 'Inspect':
                modal_exists = any(m['type'] == 'container' and m['item'] == item for m in game.modals)
                if not modal_exists:
                    new_container_modal = {
                        'id': uuid.uuid4(),
                        'type': 'container',
                        'item': item,
                        'position': game.last_modal_positions['container'],
                        'is_dragging': False, 'drag_offset': (0, 0),
                        'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], 300, 300),
                        'minimized': False
                    }
                    game.modals.append(new_container_modal)

            elif option == 'Unequip':
                if source == 'belt':
                    if 0 <= index < len(game.player.belt) and game.player.belt[index] == item:
                        game.player.belt[index] = None
                    if game.player.active_weapon == item:
                        game.player.active_weapon = None
                    if len(game.player.inventory) < game.player.get_total_inventory_slots():
                        game.player.inventory.append(item)
                        print(f"Unequipped {item.name} -> Inventory")
                    else:
                        item.rect.center = game.player.rect.center
                        game.items_on_ground.append(item)
                        print(f"Unequipped {item.name} -> Dropped on ground (inventory full)")
                elif source == 'backpack':
                    item_to_unequip = game.player.backpack
                    if item_to_unequip and item_to_unequip == item:
                        game.player.backpack = None
                        if len(game.player.inventory) < game.player.get_total_inventory_slots():
                            game.player.inventory.append(item_to_unequip)
                            print(f"Unequipped {item_to_unequip.name} -> Inventory")
                        else:
                            item_to_unequip.rect.center = game.player.rect.center
                            game.items_on_ground.append(item_to_unequip)
                            print(f"Unequipped {item_to_unequip.name} -> Dropped on ground (inventory full)")
                    else:
                         print("Backpack unequip error: item mismatch.")
                
                elif source == 'gear':
                    slot_name = index 
                    item_to_unequip = game.player.clothes.get(slot_name)
                    if item_to_unequip and item_to_unequip == item:
                        game.player.clothes[slot_name] = None
                        if len(game.player.inventory) < game.player.get_total_inventory_slots():
                            game.player.inventory.append(item_to_unequip)
                            print(f"Unequipped {item_to_unequip.name} -> Inventory")
                        else:
                            item_to_unequip.rect.center = game.player.rect.center
                            game.items_on_ground.append(item_to_unequip)
                            print(f"Unequipped {item_to_unequip.name} -> Dropped on ground (inventory full)")
                
                else:
                    print("Unequip is only available for belt or backpack items.")

            elif (source == 'ground' or source == 'nearby') and option == 'Grab':
                target_inventory = game.player.inventory
                target_capacity = game.player.get_total_inventory_slots()
                
                if len(target_inventory) < target_capacity:
                    grabbed_item = None
                    if source == 'ground' and 0 <= index < len(game.items_on_ground):
                        grabbed_item = game.items_on_ground.pop(index)
                    elif source == 'nearby' and container_item and 0 <= index < len(container_item.inventory):
                        grabbed_item = container_item.inventory.pop(index)
                    
                    if grabbed_item:
                        target_inventory.append(grabbed_item)
                        print(f"Grabbed {grabbed_item.name} into inventory.")
                        game.player.stack_item_in_inventory(grabbed_item) 
                else:
                    print("No space to grab the item.")

            elif source == 'ground' and option == 'Place on Backpack':
                if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None:
                    ground_idx = index
                    if 0 <= ground_idx < len(game.items_on_ground):
                        ground_item = game.items_on_ground[ground_idx]
                        if len(game.player.backpack.inventory) < (game.player.backpack.capacity or 0):
                            game.player.backpack.inventory.append(ground_item)
                            game.items_on_ground.pop(ground_idx)
                            print(f"Placed {ground_item.name} into backpack.")
                        else:
                            print("Backpack is full.")
                else:
                    print("No backpack equipped.")

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
                if not clicked_item:
                    if game.player.invcontainer and get_invcontainer_slot_rect(modal['position']).collidepoint(mouse_pos):
                        clicked_item, click_source, click_index = game.player.invcontainer, 'invcontainer', 0
            
            elif modal.get('active_tab') == 'Gear':
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            item = game.player.clothes.get(slot_name)
                            if item:
                                clicked_item, click_source, click_index = item, 'gear', slot_name; break
        
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

    if not clicked_item:
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
                    display_message(game, "Item is too far away to interact with.")
                    print("Item is too far away to interact with.")
        
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
                        display_message(game, "Item is too far away to interact with.")
                        print("Container is too far away to interact with.")

    if clicked_item:
        game.context_menu['active'] = True
        game.context_menu['item'] = clicked_item
        game.context_menu['source'] = click_source
        game.context_menu['index'] = click_index
        game.context_menu['container_item'] = click_container_item
        game.context_menu['position'] = mouse_pos

        options = game.player.get_item_context_options(clicked_item, click_source, click_container_item)

        if click_source == 'belt':
            if 'Unequip' not in options:
                options.append('Unequip')
            options = [o for o in options if o != 'Equip']
        
        elif click_source == 'backpack':
            if 'Unequip' not in options:
                options.append('Unequip')
            if 'Drop' not in options:
                options.append('Drop')
            options = [o for o in options if o != 'Equip']

        elif click_source == 'gear':
            if 'Unequip' not in options:
                options.append('Unequip')
            if 'Drop' not in options:
                options.append('Drop')
            options = [o for o in options if o != 'Equip']
        
        elif click_source == 'invcontainer':
            if 'Unequip' not in options:
                options.append('Unequip')
            if 'Drop' not in options:
                options.append('Drop')
            options = [o for o in options if o != 'Equip']

        elif click_source == 'ground':
            if 'Drop' in options:
                options.remove('Drop')
            if not isinstance(clicked_item, Corpse):
                if 'Grab' not in options:
                    options.insert(0, 'Grab') 
            if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None and not isinstance(clicked_item, Corpse):
                if 'Place on Backpack' not in options:
                    options.append('Place on Backpack')
            if getattr(clicked_item, 'inventory', None) is not None:
                if 'Open' not in options:
                    options.append('Open')
        
        elif click_source == 'container_map':
            options = ['Inspect']

        elif click_source == 'nearby':
            if 'Drop' in options:
                options.remove('Drop')
            if 'Drop one' in options:
                 options.remove('Drop one') 
            if 'Drop all' in options:
                 options.remove('Drop all') 
            if not isinstance(clicked_item, Corpse):
                if 'Grab' not in options:
                    options.insert(0, 'Grab')
            if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None and not isinstance(clicked_item, Corpse):
                if 'Place on Backpack' not in options:
                    options.append('Place on Backpack')


        game.context_menu['options'] = options
        game.context_menu['rects'] = []
        return

def handle_left_click_drag_candidate(game, mouse_pos):
    # Check container/nearby first
    for modal in reversed(game.modals):
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
                        slot_rect = get_container_slot_rect(pos, i)
                        if slot_rect.collidepoint(mouse_pos):
                            game.drag_candidate = (item, (i, 'nearby', active_container, modal['id']))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            break
            if game.drag_candidate: break

        if modal['type'] == 'container':
            container_item = modal['item']
            for i, item in enumerate(container_item.inventory):
                slot_rect = get_container_slot_rect(modal['position'], i)
                if slot_rect.collidepoint(mouse_pos):
                    game.drag_candidate = (item, (i, 'container', container_item, modal['id']))
                    game.drag_start_pos = mouse_pos
                    game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                    break
            if game.drag_candidate: break
    if game.drag_candidate: return

    # Check inventory modal (inventory, belt, gear, etc.)
    for modal in reversed(game.modals):
        if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
            
            # --- MODIFIED: Check active tab FIRST ---
            if modal.get('active_tab', 'Inventory') == 'Inventory':
                # Check inventory slots
                for i, item in enumerate(game.player.inventory):
                    if item:
                        slot_rect = get_inventory_slot_rect(i, modal['position'])
                        if slot_rect.collidepoint(mouse_pos):
                            game.drag_candidate = (item, (i, 'inventory'))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            break
                if game.drag_candidate: break

                # Check belt slots
                for i, item in enumerate(game.player.belt):
                    if item:
                        slot_rect = get_belt_slot_rect_in_modal(i, modal['position'])
                        if slot_rect.collidepoint(mouse_pos):
                            game.drag_candidate = (item, (i, 'belt'))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            break
                if game.drag_candidate: break

                # Check invcontainer slot
                if game.player.invcontainer:
                    slot_rect = get_invcontainer_slot_rect(modal['position'])
                    if slot_rect.collidepoint(mouse_pos):
                        game.drag_candidate = (game.player.invcontainer, (0, 'invcontainer'))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                        break # Found candidate
            
            elif modal.get('active_tab') == 'Gear':
                # Check gear slots
                # Use the stored rects from the modal, which draw_inventory_modal should add
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            item = game.player.clothes.get(slot_name)
                            if item:
                                game.drag_candidate = (item, (slot_name, 'gear')) # (slot_name, 'gear')
                                game.drag_start_pos = mouse_pos
                                game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                                break # Found item to drag
            # --- END MODIFIED BLOCK ---

            if game.drag_candidate: break
    
    if game.drag_candidate:
        return

def handle_attack(game, mouse_pos):
    if any(modal['is_dragging'] for modal in game.modals):
        return

    click_in_modal = False
    for modal in reversed(game.modals):
        modal_rect = modal['rect']
        if modal_rect.collidepoint(mouse_pos):
            click_in_modal = True
            break
    if click_in_modal:
        return

    if GAME_OFFSET_X <= mouse_pos[0] < GAME_OFFSET_X + GAME_WIDTH:
        weapon = game.player.active_weapon
        if game.player.is_reloading:
            print("Cannot shoot while reloading.")
            return

        if weapon and weapon.item_type == 'weapon' and weapon.ammo_type:
            if weapon.load > 0 and weapon.durability > 0:
                target_world_x, target_world_y = game.screen_to_world(mouse_pos)
                
                dx = target_world_x - game.player.rect.centerx
                dy = target_world_y - game.player.rect.centery
                base_angle = math.atan2(dy, dx)

                for _ in range(weapon.pellets):
                    spread = math.radians(random.uniform(-weapon.spread_angle / 2, weapon.spread_angle / 2))
                    angle = base_angle + spread
                    
                    target_x = game.player.rect.centerx + math.cos(angle) * 1000
                    target_y = game.player.rect.centery + math.sin(angle) * 1000

                    game.projectiles.append(Projectile(game.player.rect.centerx, game.player.rect.centery, target_x, target_y))

                weapon.load -= 1
                weapon.durability = max(0, weapon.durability - 0.5)
                game.player.gun_flash_timer = 5
                if weapon.durability <= 0:
                    print(f"{weapon.name} broke!")
                    game.player.destroy_broken_weapon(weapon)
            elif weapon.load <= 0: print(f"**CLICK!** {weapon.name} is out of ammo.")
            else: print(f"**CLUNK!** {weapon.name} is broken.")
        else:
            if game.player.progression.handle_melee_attack(game.player):
                game.player.melee_swing_timer = 10
                player_screen_x = GAME_OFFSET_X + GAME_WIDTH / 2
                player_screen_y = GAME_HEIGHT / 2
                
                dx_swing = mouse_pos[0] - player_screen_x
                dy_swing = mouse_pos[1] - player_screen_y
                game.player.melee_swing_angle = math.atan2(-dy_swing, dx_swing)
                hit_a_zombie = False
                for zombie in game.zombies:
                    if game.player.rect.colliderect(zombie.rect.inflate(20, 20)):
                        if player_hit_zombie(game.player, zombie):
                            handle_zombie_death(game, zombie, game.items_on_ground, game.obstacles, weapon)
                            game.zombies.remove(zombie)
                            game.zombies_killed += 1
                        hit_a_zombie = True
                        break

                if not hit_a_zombie: print("Swung and missed!")