import pygame
import uuid
import random
import math

from data.config import *
from core.entities.item import Item, Projectile
from core.entities.corpse import Corpse
from core.update import player_hit_zombie, handle_zombie_death
from core.ui.inventory import get_belt_slot_rect_in_modal, get_inventory_slot_rect, get_backpack_slot_rect
from core.ui.container import get_container_slot_rect

def handle_mouse_down(game, event, mouse_pos):
    if event.button == 1:
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
                        else: 
                            full_height = 300 
                        modal_to_affect['rect'].height = header_height if is_minimized else full_height
                        return

        if game.status_button_rect and game.status_button_rect.collidepoint(mouse_pos):
            from core.events.keyboard import toggle_status_modal
            toggle_status_modal(game)
            return
        if game.inventory_button_rect and game.inventory_button_rect.collidepoint(mouse_pos):
            from core.events.keyboard import toggle_inventory_modal
            toggle_inventory_modal(game)
            return

        for modal in game.modals:
            if modal['type'] == 'inventory':
                backpack_slot_rect = get_backpack_slot_rect(modal['position'])
                if backpack_slot_rect.collidepoint(mouse_pos) and game.player.backpack:
                    modal_exists = any(m['type'] == 'container' and m['item'] == game.player.backpack for m in game.modals)
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

        for modal in game.modals:
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
    for modal in game.modals:
        modal['is_dragging'] = False

    if event.button == 1:
        if game.is_dragging or game.drag_candidate:
            if not game.is_dragging and game.drag_candidate:
                game.dragged_item, game.drag_origin = game.drag_candidate
                game.drag_candidate = None
                try:
                    i_temp, type_temp, *container_temp = game.drag_origin
                except Exception:
                    i_temp = None; type_temp = None; container_temp = []
                if type_temp == 'inventory' and i_temp is not None:
                    if 0 <= i_temp < len(game.player.inventory):
                        game.player.inventory.pop(i_temp)
                elif type_temp == 'belt' and i_temp is not None:
                    if 0 <= i_temp < len(game.player.belt):
                        if game.player.active_weapon == game.player.belt[i_temp]:
                            game.player.active_weapon = None
                        game.player.belt[i_temp] = None
                elif type_temp == 'backpack':
                    game.player.backpack = None
                elif type_temp == 'container' and container_temp:
                    cont_obj = container_temp[0]
                    if 0 <= i_temp < len(cont_obj.inventory):
                        cont_obj.inventory.pop(i_temp)

            if game.drag_origin is None and game.dragged_item:
                inferred = resolve_drag_origin_from_item(game.dragged_item, game.player, game.modals)
                if inferred:
                    if len(inferred) == 2:
                        game.drag_origin = (inferred[0], inferred[1])
                    else:
                        game.drag_origin = (inferred[0], inferred[1], inferred[2])
                else:
                    game.drag_origin = (0, 'inventory')

            i_orig, type_orig, *container_info = game.drag_origin
            container_obj = container_info[0] if type_orig == 'container' and container_info else None

            dropped_successfully = False

            for i_target in range(len(game.player.belt)):
                if any(modal['type'] == 'inventory' and get_belt_slot_rect_in_modal(i_target, modal['position']).collidepoint(mouse_pos) for modal in game.modals):
                    if getattr(game.dragged_item, 'item_type', None) == 'backpack':
                        print("Cannot place backpacks on the belt.")
                        dropped_successfully = False
                        break
                    if game.player.belt[i_target] is None:
                        game.player.belt[i_target] = game.dragged_item
                    else:
                        item_to_swap = game.player.belt[i_target]
                        if type_orig == 'inventory' and 0 <= i_orig <= len(game.player.inventory):
                            game.player.inventory.insert(i_orig, item_to_swap)
                        elif type_orig == 'belt' and 0 <= i_orig < len(game.player.belt):
                            game.player.belt[i_orig] = item_to_swap
                        elif type_orig == 'container' and container_obj is not None and 0 <= i_orig <= len(container_obj.inventory):
                            container_obj.inventory.insert(i_orig, item_to_swap)
                        else:
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(item_to_swap)
                            else:
                                item_to_swap.rect.center = game.player.rect.center
                                game.items_on_ground.append(item_to_swap)
                        game.player.belt[i_target] = game.dragged_item
                    dropped_successfully = True
                    break

            if not dropped_successfully:
                for modal in game.modals:
                    if modal['type'] == 'inventory':
                        backpack_slot_rect = get_backpack_slot_rect(modal['position'])
                        if backpack_slot_rect.collidepoint(mouse_pos):
                            is_backpack_like = (getattr(game.dragged_item, 'item_type', None) in ('backpack', 'container')) or hasattr(game.dragged_item, 'inventory')
                            if not is_backpack_like:
                                break

                            try:
                                if game.dragged_item in game.player.inventory:
                                    game.player.inventory.remove(game.dragged_item)
                                if game.dragged_item in game.player.belt:
                                    for bi, it in enumerate(game.player.belt):
                                        if it is game.dragged_item:
                                            game.player.belt[bi] = None
                                if game.dragged_item in game.items_on_ground:
                                    game.items_on_ground.remove(game.dragged_item)
                            except Exception:
                                pass

                            old_backpack = game.player.backpack
                            game.player.backpack = game.dragged_item
                            print(f"Equipped {game.dragged_item.name} as backpack via drag.")

                            if old_backpack:
                                returned = False
                                if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    game.player.inventory.append(old_backpack)
                                    returned = True
                                else:
                                    for bi in range(len(game.player.belt)):
                                        if game.player.belt[bi] is None:
                                            game.player.belt[bi] = old_backpack
                                            returned = True
                                            break
                                if not returned:
                                    old_backpack.rect.center = game.player.rect.center
                                    game.items_on_ground.append(old_backpack)
                                    print(f"No space to return old backpack; dropped {old_backpack.name} on ground.")

                            dropped_successfully = True
                            break

            if not dropped_successfully:
                for modal in reversed(game.modals):
                    if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
                        target_index = -1
                        for i in range(5):
                            if get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                                target_index = i
                                break
                        
                        if len(game.player.inventory) < game.player.get_total_inventory_slots():
                            if target_index == -1:
                                target_index = len(game.player.inventory)
                            game.player.inventory.insert(target_index, game.dragged_item)
                            dropped_successfully = True
                        else:
                            print("Inventory is full.")
                        break

            if not dropped_successfully:
                for modal in reversed(game.modals):
                    if modal['type'] == 'container' and modal['rect'].collidepoint(mouse_pos):
                        container = modal['item']
                        if game.dragged_item is container:
                            print("Cannot place a container inside itself.")
                            continue

                        if game.dragged_item is game.player.backpack and container is game.player.backpack:
                            print("Cannot move the equipped backpack into its own contents.")
                            continue

                        if len(container.inventory) < (container.capacity or 0):
                            container.inventory.append(game.dragged_item)
                            print(f"Moved {game.dragged_item.name} to {container.name}")
                            dropped_successfully = True
                            break
                        else:
                            print(f"{container.name} is full.")

            if not dropped_successfully:
                game_world_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
                if game_world_rect.collidepoint(mouse_pos):
                    game.dragged_item.rect.x = game.player.rect.centerx
                    game.dragged_item.rect.y = game.player.rect.centery + TILE_SIZE
                    game.items_on_ground.append(game.dragged_item)
                    print(f"Dropped {game.dragged_item.name} by dragging.")
                else:
                    if type_orig == 'inventory' and 0 <= i_orig <= len(game.player.inventory):
                        game.player.inventory.insert(i_orig, game.dragged_item)
                    elif type_orig == 'belt' and 0 <= i_orig < len(game.player.belt):
                        game.player.belt[i_orig] = game.dragged_item
                    elif type_orig == 'backpack':
                        game.player.backpack = game.dragged_item
                    elif type_orig == 'container' and container_obj is not None:
                        container_obj.inventory.insert(i_orig, game.dragged_item)

            game.player.inventory = [item for item in game.player.inventory if item is not None]

        game.is_dragging = False
        game.dragged_item = None
        game.drag_origin = None
        game.drag_candidate = None

def handle_mouse_motion(game, event, mouse_pos):
    if game.context_menu['active']:
        pass

    if game.drag_candidate and not game.is_dragging:
        dist = math.hypot(mouse_pos[0] - game.drag_start_pos[0], mouse_pos[1] - game.drag_start_pos[1])
        if dist > game.DRAG_THRESHOLD:
            game.is_dragging = True
            game.dragged_item, game.drag_origin = game.drag_candidate
            game.drag_candidate = None

            i_orig, type_orig, *container_info = game.drag_origin
            if type_orig == 'inventory':
                game.player.inventory.pop(i_orig)
            elif type_orig == 'belt':
                if game.player.active_weapon == game.player.belt[i_orig]:
                    game.player.active_weapon = None
                game.player.belt[i_orig] = None
            elif type_orig == 'backpack':
                game.player.backpack = None
            elif type_orig == 'container':
                container_obj = container_info[0]
                container_obj.inventory.pop(i_orig)

    for modal in game.modals:
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
    if item is None:
        return None
    try:
        if item in player.inventory:
            return (player.inventory.index(item), 'inventory')
        if item in player.belt:
            return (player.belt.index(item), 'belt')
        if player.backpack is item:
            return (0, 'backpack')
        for modal in modals:
            if modal.get('type') == 'container' and modal.get('item') and hasattr(modal['item'], 'inventory'):
                cont = modal['item']
                if item in cont.inventory:
                    return (cont.inventory.index(item), 'container', cont)
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
                game.player.reload_active_weapon()

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
                
                else:
                    print("Unequip is only available for belt or backpack items.")

            elif source == 'ground' and option == 'Grab':
                ground_idx = index
                if 0 <= ground_idx < len(game.items_on_ground):
                    ground_item = game.items_on_ground[ground_idx]
                    target_inventory = game.player.inventory
                    target_capacity = game.player.base_inventory_slots
                    if game.player.backpack and any(m['type'] == 'container' and m['item'] == game.player.backpack for m in game.modals):
                        target_inventory = game.player.backpack.inventory
                        target_capacity = game.player.backpack.capacity or 0
                    if len(target_inventory) < target_capacity:
                        target_inventory.append(ground_item)
                        game.items_on_ground.pop(ground_idx)
                        print(f"Grabbed {ground_item.name}.")
                    elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                        game.player.inventory.append(ground_item)
                        game.items_on_ground.pop(ground_idx)
                        print(f"Grabbed {ground_item.name} into inventory.")
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
        
        elif modal['type'] == 'container':
            container = modal['item']
            for i, item in enumerate(container.inventory):
                if item and get_container_slot_rect(modal['position'], i).collidepoint(mouse_pos):
                    clicked_item, click_source, click_index, click_container_item = item, 'container', i, container; break
        
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
                    print("Item is too far away to interact with.")

    if clicked_item:
        game.context_menu['active'] = True
        game.context_menu['item'] = clicked_item
        game.context_menu['source'] = click_source
        game.context_menu['index'] = click_index
        game.context_menu['container_item'] = click_container_item
        game.context_menu['position'] = mouse_pos
        options = game.player.get_item_context_options(clicked_item) if click_source != 'ground' else []
        
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

        elif click_source == 'ground':
            options = []
            if not isinstance(clicked_item, Corpse):
                options.append('Grab')
            if getattr(clicked_item, 'item_type', None) in ('weapon', 'tool'):
                options.append('Equip')
            if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None and not isinstance(clicked_item, Corpse):
                options.append('Place on Backpack')
            if getattr(clicked_item, 'inventory', None) is not None:
                options.append('Open')
        
        game.context_menu['options'] = options
        game.context_menu['rects'] = []
        return

def handle_left_click_drag_candidate(game, mouse_pos):
    for modal in reversed(game.modals):
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

    for modal in reversed(game.modals):
        if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
            
            for i, item in enumerate(game.player.inventory):
                if item:
                    slot_rect = get_inventory_slot_rect(i, modal['position'])
                    if slot_rect.collidepoint(mouse_pos):
                        game.drag_candidate = (item, (i, 'inventory'))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                        break
            if game.drag_candidate: break

            for i, item in enumerate(game.player.belt):
                if item:
                    slot_rect = get_belt_slot_rect_in_modal(i, modal['position'])
                    if slot_rect.collidepoint(mouse_pos):
                        game.drag_candidate = (item, (i, 'belt'))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                        break
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
                    for i, item in enumerate(game.player.belt):
                        if item == weapon: game.player.belt[i] = None; break
                    game.player.active_weapon = None
            elif weapon.load <= 0: print(f"**CLICK!** {weapon.name} is out of ammo.")
            else: print(f"**CLUNK!** {weapon.name} is broken.")
        else:
            if game.player.stamina >= 10:
                game.player.stamina -= 10
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
                            handle_zombie_death(game, zombie, game.items_on_ground, game.obstacles)
                            game.zombies.remove(zombie)
                            game.zombies_killed += 1
                        hit_a_zombie = True
                        break

                if not hit_a_zombie: print("Swung and missed!")
            else: print("Too tired to swing!")
