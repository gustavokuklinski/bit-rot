import pygame
import uuid
import random
import math

from core.data.config import *
from core.entities.item.item import Item, Projectile
from core.entities.zombie.corpse import Corpse
from core.update import player_hit_zombie, handle_zombie_death
from core.ui.inventory_modal import get_belt_slot_rect_in_modal, get_inventory_slot_rect, get_backpack_slot_rect, get_invcontainer_slot_rect, get_belt_hud_slot_rect
from core.ui.container_modal import get_container_slot_rect
from core.messages import display_message
from core.events.keyboard import toggle_messages_modal, toggle_status_modal, toggle_inventory_modal, toggle_nearby_modal, toggle_gear_modal
from core.placement import find_free_tile

# Recursive Logic Check (Prevents Bag-in-Bag crashes)
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

def handle_mouse_down(game, event, mouse_pos):
    if event.button == 1:
        # [FIX] 0. Context Menu Priority - Check this FIRST
        # If the menu is active, it floats above everything else.
        if game.context_menu['active']:
            menu_clicked = False
            # Check if we clicked on an option
            for rect in game.context_menu.get('rects', []):
                if rect.collidepoint(mouse_pos):
                    handle_context_menu_click(game, mouse_pos)
                    return # Stop processing (Action taken)
            
            # If we clicked outside the menu, close it
            game.context_menu['active'] = False
            # We allow the code to "fall through" here so the click 
            # registers on whatever was underneath the menu (e.g. closing it by clicking a modal)

        # [OPTIMIZATION] 1. Check Topmost Modal Logic First
        topmost_modal = None
        for modal in reversed(game.modals):
            if modal['rect'].collidepoint(mouse_pos):
                topmost_modal = modal
                break
        
        # [OPTIMIZATION] Handle Topmost Modal Specifics
        if topmost_modal:
            # Bring to front
            if game.modals[-1] != topmost_modal:
                game.modals.remove(topmost_modal)
                game.modals.append(topmost_modal)
            
            # Check Modal Buttons (Close/Minimize) attached to this modal
            for button in getattr(game, 'modal_buttons', []):
                if button['id'] == topmost_modal['id'] and button['rect'].collidepoint(mouse_pos):
                    if button['type'] == 'close':
                        if topmost_modal['type'] == 'messages':
                            game.chat_active = False
                        game.modals.remove(topmost_modal)
                        return
                    elif button['type'] == 'minimize':
                        is_minimized = not topmost_modal.get('minimized', False)
                        topmost_modal['minimized'] = is_minimized
                        header_height = 35
                        if topmost_modal['type'] == 'inventory': full_h = INVENTORY_MODAL_HEIGHT
                        elif topmost_modal['type'] == 'gear': full_h = GEAR_MODAL_HEIGHT
                        elif topmost_modal['type'] == 'status': full_h = STATUS_MODAL_HEIGHT
                        elif topmost_modal['type'] == 'messages': full_h = MESSAGES_MODAL_HEIGHT
                        else: full_h = 300
                        topmost_modal['rect'].height = header_height if is_minimized else full_h
                        return
                    elif button['type'] in ['map_zoom_in', 'map_zoom_out']:
                        current_zoom = topmost_modal.get('map_zoom', 4)
                        if button['type'] == 'map_zoom_in':
                             topmost_modal['map_zoom'] = min(16, current_zoom + 1)
                        else:
                             topmost_modal['map_zoom'] = max(2, current_zoom - 1)
                        return
            
            # If minimized, we only care about header dragging
            if topmost_modal.get('minimized', False):
                 modal_header_rect = pygame.Rect(topmost_modal['position'][0], topmost_modal['position'][1], topmost_modal['rect'].width, 35)
                 if modal_header_rect.collidepoint(mouse_pos):
                    topmost_modal['is_dragging'] = True
                    topmost_modal['drag_offset'] = (mouse_pos[0] - topmost_modal['position'][0], mouse_pos[1] - topmost_modal['position'][1])
                    return
            else:
                # Not minimized: Check Tabs, Scrollbars, Content
                
                # Header Drag
                modal_header_rect = pygame.Rect(topmost_modal['position'][0], topmost_modal['position'][1], topmost_modal['rect'].width, 35)
                if modal_header_rect.collidepoint(mouse_pos):
                    topmost_modal['is_dragging'] = True
                    topmost_modal['drag_offset'] = (mouse_pos[0] - topmost_modal['position'][0], mouse_pos[1] - topmost_modal['position'][1])
                    return

                # Scrollbar Drag
                scrollbar_rect = topmost_modal.get('scrollbar_handle_rect') 
                if scrollbar_rect and scrollbar_rect.collidepoint(mouse_pos):
                    topmost_modal['is_dragging_scrollbar'] = True
                    topmost_modal['scrollbar_drag_last_y'] = mouse_pos[1] 
                    return

                # Tabs
                if topmost_modal['type'] in ['nearby', 'status', 'inventory', 'mobile', 'messages','vehicle'] and 'tab_rects' in topmost_modal:
                    for i, tab_rect in enumerate(topmost_modal.get('tab_rects', [])):
                        if tab_rect.collidepoint(mouse_pos):
                             tabs_data = topmost_modal.get('tabs_data', [])
                             if i < len(tabs_data):
                                 topmost_modal['active_tab'] = tabs_data[i]['label']
                                 return

                # Specific Modal Logic
                if hasattr(topmost_modal, 'handle_event'):
                    if topmost_modal.handle_event(event): return

                if topmost_modal['type'] == 'vehicle' and topmost_modal.get('active_tab') == 'Info':
                    rects = topmost_modal.get('rects', {})
                    veh = topmost_modal['vehicle']
                    if 'lights_on' in rects and rects['lights_on'].collidepoint(mouse_pos):
                        veh.toggle_lights(); return
                    if 'lights_off' in rects and rects['lights_off'].collidepoint(mouse_pos):
                        veh.toggle_lights(); return

                # Specific Inventory Logic (Opening Backpack)
                if topmost_modal['type'] == 'inventory' and topmost_modal.get('active_tab', 'Inventory') == 'Inventory':
                     backpack_slot_rect = get_backpack_slot_rect(topmost_modal['position'])
                     if backpack_slot_rect.collidepoint(mouse_pos) and game.player.backpack:
                         # Open backpack container if not already open
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

                # If we clicked inside the topmost modal but didn't hit a button/tab, 
                # check for drag candidate (items) within that modal
                handle_left_click_drag_candidate(game, mouse_pos)
                return

        # [END OPTIMIZATION] - If we reach here, we clicked OUTSIDE any modal

        # 2. Global UI Buttons (HUD)
        for button in getattr(game, 'modal_buttons', []):
             if not button.get('id'): # Global buttons?
                 if button['rect'].collidepoint(mouse_pos):
                      if button['type'] == 'send_msg':
                           if game.chat_input_text.strip():
                               game.player.chat_text = game.chat_input_text
                               game.player.chat_timer = game.player.chat_duration
                               from core.messages import display_message_player
                               display_message_player(game, f"You: {game.chat_input_text}")
                               game.chat_input_text = ""
                               game.chat_active = True 
                           return
                      elif button['type'] == 'chat_input':
                           game.chat_active = True
                           return

        if game.chat_active:
            game.chat_active = False

        # HUD Icons
        if game.status_button_rect and game.status_button_rect.collidepoint(mouse_pos):
            toggle_status_modal(game); return
        if game.inventory_button_rect and game.inventory_button_rect.collidepoint(mouse_pos):
            toggle_inventory_modal(game); return
        if game.nearby_button_rect and game.nearby_button_rect.collidepoint(mouse_pos):
            toggle_nearby_modal(game); return
        if game.gear_button_rect and game.gear_button_rect.collidepoint(mouse_pos):
            toggle_gear_modal(game); return
        if game.messages_button_rect and game.messages_button_rect.collidepoint(mouse_pos):
            toggle_messages_modal(game); return

        # Belt HUD
        for i, item in enumerate(game.player.belt):
            slot_rect = get_belt_hud_slot_rect(i)
            if slot_rect.collidepoint(mouse_pos):
                if item:
                    game.drag_candidate = (item, (i, 'belt'))
                    game.drag_start_pos = mouse_pos
                    game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                    return
            
        # Attack / World Interaction
        if (pygame.key.get_pressed()[pygame.K_LCTRL] or pygame.key.get_pressed()[pygame.K_RCTRL] or pygame.mouse.get_pressed()[2]):
            handle_attack(game, mouse_pos)
            return

    elif event.button == 3:
        if game.context_menu['active']:
            game.context_menu['active'] = False
            return

        handle_right_click(game, mouse_pos)
        return

def handle_mouse_up(game, event, mouse_pos):
    for modal in reversed(game.modals):
        modal['is_dragging'] = False
        modal['is_dragging_scrollbar'] = False

    if event.button == 1:
        dropped_successfully = False
        if game.is_dragging or game.drag_candidate:
            if not game.is_dragging and game.drag_candidate:
                pass 

            if game.dragged_item:
                i_orig, type_orig, *container_info = game.drag_origin
                container_obj = container_info[0] if type_orig in ('container', 'nearby', 'inventory_stack_split', 'belt_stack_split', 'container_stack_split', 'nearby_stack_split', 'gear_stack_split') and container_info else None 
                is_external_source = type_orig in ['container', 'nearby', 'container_stack_split', 'nearby_stack_split']

                # --- Vehicle Equipment Logic ---
                for modal in reversed(game.modals):
                    if modal['type'] == 'vehicle' and modal.get('active_tab') == 'Info':
                        if 'equipment_rects' in modal:
                            for slot_name, slot_rect in modal['equipment_rects'].items():
                                if slot_rect.collidepoint(mouse_pos):
                                    vehicle = modal['vehicle']
                                    valid_drop = vehicle.can_equip(game.dragged_item, slot_name)
                                    if valid_drop:
                                        old_item = vehicle.add_equipment(game.dragged_item, slot_name)
                                        if old_item:
                                            game.dragged_item = old_item
                                            dropped_successfully = False 
                                        else:
                                            dropped_successfully = True
                                    else:
                                        print(f"Cannot place {game.dragged_item.name} in {slot_name} slot.")
                                    break
                        if dropped_successfully or (not dropped_successfully and game.dragged_item):
                            break
                
                if dropped_successfully:
                    game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                    return 
               
                # --- Drop on BELT ---
                for i_target in range(len(game.player.belt)):
                    is_modal_slot = any(modal['type'] == 'inventory' and get_belt_slot_rect_in_modal(i_target, modal['position']).collidepoint(mouse_pos) for modal in reversed(game.modals))
                    is_hud_slot = get_belt_hud_slot_rect(i_target).collidepoint(mouse_pos)

                    if is_modal_slot or is_hud_slot:
                        if getattr(game.dragged_item, 'item_type', None) == 'backpack':
                            print("Cannot place backpacks on the belt.")
                            break 
                        
                        item_in_slot = game.player.belt[i_target]
                        
                        if item_in_slot and check_recursive_containment(game.dragged_item, item_in_slot):
                            print("Cannot drop a container into itself.")
                            dropped_successfully = False
                            break

                        if is_external_source:
                            if item_in_slot is None or item_in_slot.can_stack_with(game.dragged_item):
                                item_ref = game.dragged_item
                                def do_belt_loot():
                                    if game.player.belt[i_target] is None:
                                        game.player.belt[i_target] = item_ref
                                    elif game.player.belt[i_target].can_stack_with(item_ref):
                                        avail = game.player.belt[i_target].capacity - game.player.belt[i_target].load
                                        trans = min(avail, item_ref.load)
                                        game.player.belt[i_target].load += trans
                                        item_ref.load -= trans
                                
                                game.player.start_action("Looting", 1.0, do_belt_loot, xp_reward=2)
                                game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                return
                            else:
                                print("Cannot swap items while looting.")
                                dropped_successfully = False
                                break

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

                # --- Drop on INVENTORY/MODALS ---
                for modal in reversed(game.modals):
                    if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
                        
                        if modal.get('active_tab', 'Inventory') == 'Inventory':
                            # Backpack slot
                            backpack_slot_rect = get_backpack_slot_rect(modal['position'])
                            if backpack_slot_rect.collidepoint(mouse_pos):
                                if getattr(game.dragged_item, 'item_type', None) == 'backpack':
                                    if game.player.backpack and check_recursive_containment(game.dragged_item, game.player.backpack):
                                        print("Cannot put a container inside itself."); break
                                    
                                    if is_external_source:
                                        if game.player.backpack is None:
                                            item_ref = game.dragged_item
                                            def do_bp_loot():
                                                game.player.backpack = item_ref
                                            game.player.start_action("Equipping", 1.5, do_bp_loot, xp_reward=2)
                                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                            return
                                        else:
                                            print("Unequip current backpack first.")
                                            dropped_successfully = False
                                            break
                                    

                                    old_backpack = game.player.backpack
                                    game.player.backpack = game.dragged_item
                                    game.dragged_item = old_backpack 
                                    dropped_successfully = False 
                                    if game.dragged_item is None: 
                                        dropped_successfully = True
                                else:
                                    print("Only backpacks can go in this slot.")
                                if dropped_successfully: break

                            # InvContainer slot
                            invcontainer_slot_rect = get_invcontainer_slot_rect(modal['position'])
                            if not dropped_successfully and invcontainer_slot_rect.collidepoint(mouse_pos):
                                if game.player.invcontainer and check_recursive_containment(game.dragged_item, game.player.invcontainer):
                                    print("Cannot put a container inside itself."); break

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
                                    
                                    if dropped_successfully: break 

                                if not dropped_successfully:
                                    dragged_type = getattr(game.dragged_item, 'item_type', None)
                                    dragged_ammo_type = getattr(game.dragged_item, 'ammo_type', None)
                                    is_allowed_type = (
                                        dragged_type == 'container' or
                                        dragged_type == 'utility' or
                                        dragged_type == 'mobile' or
                                        (dragged_type == 'consumable' and dragged_ammo_type is not None)
                                    )
                                    if is_allowed_type:
                                        if is_external_source:
                                        # Only allow if empty or stackable (simple logic)
                                            can_loot = False
                                            is_stack = False
                                        if game.player.invcontainer is None:
                                            can_loot = True
                                        elif game.player.invcontainer.can_stack_with(game.dragged_item):
                                            can_loot = True; is_stack = True
                                        elif (game.player.invcontainer and hasattr(game.player.invcontainer, 'inventory') and 
                                              game.dragged_item is not game.player.invcontainer):
                                              # Logic for dropping INTO the equipped container is handled below (Main Inventory Grid usually doesn't overlap perfectly, but let's be safe)
                                              pass

                                        if can_loot:
                                            item_ref = game.dragged_item
                                            def do_util_loot():
                                                if game.player.invcontainer is None:
                                                    game.player.invcontainer = item_ref
                                                elif is_stack:
                                                    avail = game.player.invcontainer.capacity - game.player.invcontainer.load
                                                    trans = min(avail, item_ref.load)
                                                    game.player.invcontainer.load += trans
                                                    item_ref.load -= trans
                                            game.player.start_action("Equipping", 1.0, do_util_loot, xp_reward=2)
                                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                            return
                                        else:
                                            # If logic is complex (swapping or putting inside), skip timed loot or fail
                                            if not (game.player.invcontainer and hasattr(game.player.invcontainer, 'inventory')):
                                                 print("Slot occupied.")
                                                 dropped_successfully = False
                                                 break
                                    else:
                                        print("Only containers (non-backpack), utilities, or ammo can go in this slot.")
                                if dropped_successfully: break

                            # Main Inventory Grid
                            if not dropped_successfully:
                                target_index = -1
                                for i in range(5): 
                                    if get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                                        target_index = i
                                        break
                                
                                if target_index != -1: 
                                    if target_index < len(game.player.inventory):
                                        item_in_slot = game.player.inventory[target_index]
                                        
                                        if check_recursive_containment(game.dragged_item, item_in_slot):
                                            print("Cannot drop container into itself.")
                                            dropped_successfully = False
                                            break
                                        
                                        if is_external_source:
                                            if item_in_slot.can_stack_with(game.dragged_item):
                                                item_ref = game.dragged_item
                                                def do_inv_stack():
                                                    avail = item_in_slot.capacity - item_in_slot.load
                                                    trans = min(avail, item_ref.load)
                                                    item_in_slot.load += trans
                                                    item_ref.load -= trans
                                                game.player.start_action("Looting", 1.0, do_inv_stack, xp_reward=2)
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
                                            item_ref = game.dragged_item
                                            def do_inv_loot():
                                                game.player.inventory.insert(target_index, item_ref)
                                            game.player.start_action("Looting", 1.0, do_inv_loot, xp_reward=2)
                                            game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                            return

                                        game.player.inventory.insert(target_index, game.dragged_item)
                                        dropped_successfully = True
                                
                                elif len(game.player.inventory) < game.player.get_total_inventory_slots():

                                    if is_external_source:
                                        item_ref = game.dragged_item
                                        def do_inv_append():
                                            game.player.inventory.append(item_ref)
                                        game.player.start_action("Looting", 1.0, do_inv_append, xp_reward=2)
                                        game.is_dragging = False; game.dragged_item = None; game.drag_origin = None; game.drag_candidate = None
                                        return

                                    game.player.inventory.append(game.dragged_item)
                                    dropped_successfully = True
                                
                                if dropped_successfully: break
                        
                        elif modal.get('active_tab') == 'Bag':
                            if game.player.backpack:
                                container = game.player.backpack
                                if check_recursive_containment(game.dragged_item, container):
                                    print("Recursion detected: Cannot put the container inside itself.")
                                    dropped_successfully = False
                                    break

                                target_index = -1
                                pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                                for i in range(container.capacity or 0):
                                    if get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                                        target_index = i
                                        break
                                
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
                                            item_to_swap = container.inventory.pop(target_index)
                                            container.inventory.insert(target_index, game.dragged_item)
                                            game.dragged_item = item_to_swap
                                            dropped_successfully = False
                                    else:
                                        container.inventory.insert(target_index, game.dragged_item)
                                        dropped_successfully = True
                                
                                elif len(container.inventory) < (container.capacity or 0):
                                    container.inventory.append(game.dragged_item)
                                    dropped_successfully = True
                                
                                if dropped_successfully: break
                        
                    elif modal['type'] == 'gear' and modal['rect'].collidepoint(mouse_pos):
                        if 'gear_slot_rects' in modal:
                            for slot_name, slot_rect in modal['gear_slot_rects'].items():
                                if slot_rect.collidepoint(mouse_pos):
                                    dragged_item = game.dragged_item
                                    item_slot = getattr(dragged_item, 'slot', None)
                                    if item_slot == 'hand': item_slot = 'hands'
                                        
                                    if item_slot == slot_name:
                                        item_in_slot = game.player.clothes.get(slot_name)
                                        game.player.clothes[slot_name] = dragged_item
                                        
                                        if item_in_slot:
                                            if type_orig == 'inventory' and 0 <= i_orig <= len(game.player.inventory):
                                                game.player.inventory.insert(i_orig, item_in_slot)
                                            elif type_orig == 'belt' and 0 <= i_orig < len(game.player.belt):
                                                game.player.belt[i_orig] = item_in_slot
                                            elif type_orig == 'backpack':
                                                game.player.backpack = item_in_slot
                                            elif type_orig == 'invcontainer':
                                                game.player.invcontainer = item_in_slot
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
                            dropped_successfully = False
                            break

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
                        if find_free_tile(game.dragged_item.rect, game.obstacles, game.items_on_ground, initial_pos=game.player.rect.center, max_radius=1):
                            game.items_on_ground.append(game.dragged_item)
                            dropped_successfully = True
                        else:
                            dropped_successfully = False
                            print("No free space to drop the item.")
                    
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
                if game.player.backpack and get_backpack_slot_rect(modal['position']).collidepoint(mouse_pos):
                    return game.player.backpack
                if game.player.invcontainer and get_invcontainer_slot_rect(modal['position']).collidepoint(mouse_pos):
                    return game.player.invcontainer
            
            elif modal.get('active_tab') == 'Bag':
                if game.player.backpack:
                    pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                    for i, item in enumerate(game.player.backpack.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            return item
        
        elif modal['type'] == 'container':
            container = modal['item']
            for i, item in enumerate(container.inventory):
                if item and get_container_slot_rect(modal['position'], i).collidepoint(mouse_pos):
                    return item

        elif modal['type'] == 'gear':
            if 'gear_slot_rects' in modal:
                for slot_name, slot_rect in modal['gear_slot_rects'].items():
                    if slot_rect.collidepoint(mouse_pos):
                        return game.player.clothes.get(slot_name)

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

    if game.player:
        player_screen_x = GAME_OFFSET_X + GAME_WIDTH / 2
        player_screen_y = GAME_HEIGHT / 2
        dx = mouse_pos[0] - player_screen_x
        dy = mouse_pos[1] - player_screen_y
        game.player.aim_angle = math.atan2(-dy, dx) 


    game.hovered_item = find_item_at_pos(game, mouse_pos)

    game.hovered_container = None

    world_pos = game.screen_to_world(mouse_pos)
    

    for container in game.containers:
        if container.rect.collidepoint(world_pos):
            game.hovered_container = container
            break

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
            clamped_x = max(0, min(new_x, VIRTUAL_SCREEN_WIDTH - modal_width))
            clamped_y = max(0, min(new_y, VIRTUAL_GAME_HEIGHT - modal_height))
            modal['position'] = (clamped_x, clamped_y)
            modal['rect'].topleft = modal['position']

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
                elif source == 'invcontainer' and game.player.invcontainer:
                    verified_item = game.player.invcontainer
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
                if option == 'Follow':
                    item.is_following = True
                    print(f"{item.name} is now following you.")
                    display_message(game, f"{item.name} is now following you.")
                    clicked_on_menu = True
                elif option == 'Unfollow':
                    item.is_following = False
                    print(f"{item.name} stopped following.")
                    display_message(game, f"{item.name} stopped following.")
                    clicked_on_menu = True


            # print(f"Clicked '{option}' on '{getattr(item,'name',str(item))}' (source={source})")
            if clicked_on_menu: # Only print if we handled it explicitly
                print(f"Clicked '{option}' on '{getattr(item,'name',str(item))}' (source={source})")
                
            if option == 'Vehicle options' and getattr(item, 'item_type', '') == 'vehicle':
                game.modals = [m for m in game.modals if m['type'] != 'vehicle']
                new_modal = {
                    'id': uuid.uuid4(),
                    'type': 'vehicle', 'vehicle': item,
                    'position': (VIRTUAL_SCREEN_WIDTH // 2 - 200, VIRTUAL_GAME_HEIGHT // 2 - 200),
                    'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], 300, 300), 
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
                 modal_exists = any(m['type'] == 'container' and m['item'] == item for m in game.modals)
                 if not modal_exists:
                    new_container_modal = {
                        'id': uuid.uuid4(), 'type': 'container', 'item': item,
                        'position': game.last_modal_positions['container'],
                        'is_dragging': False, 'drag_offset': (0, 0),
                        'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], 300, 300),
                        'minimized': False
                    }
                    game.modals.append(new_container_modal)
                 clicked_on_menu = True

            elif option == 'Open':
                if getattr(item, 'item_type', '') != 'vehicle':
                     if getattr(item, 'inventory', None) is not None:
                        modal_exists = any(m['type'] == 'container' and m['item'] == item for m in game.modals)
                        if not modal_exists:
                            new_container_modal = {
                                'id': uuid.uuid4(), 'type': 'container', 'item': item,
                                'position': game.last_modal_positions['container'],
                                'is_dragging': False, 'drag_offset': (0, 0),
                                'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], 300, 300),
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
            
            if option == 'Toggle Light':
                if source == 'light_source':
                    # Toggle the boolean state
                    item['active'] = not item['active']
                    print(f"Light turned {'ON' if item['active'] else 'OFF'}")
                clicked_on_menu = True

            if option == 'Use': game.player.consume_item(item, source, index, container_item)
            elif option == 'Reload':
                if getattr(item, 'item_type', None) in ['utility', 'mobile']:
                    game.player.reload_utility_item(item, source, index, container_item)
                else:
                    game.player.reload_active_weapon(game=game)
            elif option == 'Repair': game.player.repair_item(game, item)
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
                dropped = game.player.drop_item_stack(game, source, index, container_item, 1)
                if dropped: game.items_on_ground.append(dropped)
            elif option == 'Drop all':
                dropped = game.player.drop_item_stack(game, source, index, container_item, 'all')
                if dropped: game.items_on_ground.append(dropped)
            elif option == 'Send all to Backpack':
                game.player.transfer_item_stack(source, index, container_item, game.player.backpack)
            elif option == 'Send all to Utility':
                game.player.transfer_item_stack(source, index, container_item, game.player.invcontainer)
            elif option == 'Send all to Inventory':
                game.player.transfer_item_stack(source, index, container_item, game.player) 
            elif option == 'Drop':
                dropped_item = None
                if source == 'backpack':
                    dropped_item = game.player.drop_item(game, source, index, container_item)
                    if dropped_item:
                        game.items_on_ground.append(dropped_item)
                        print(f"Dropped {dropped_item.name} from backpack slot.")
                elif source == 'gear':
                    slot_name = index 
                    item_to_drop = game.player.clothes.get(slot_name)
                    if item_to_drop and item_to_drop == item:
                        dropped_item = game.player.drop_item(game, source, index, container_item)
                        if dropped_item:
                            game.items_on_ground.append(dropped_item)
                            print(f"Dropped {dropped_item.name} from {slot_name} slot.")
                elif source == 'invcontainer':
                    item_to_drop = game.player.invcontainer
                    if item_to_drop and item_to_drop == item:
                        dropped_item = game.player.drop_item(game, source, index, container_item)
                        if dropped_item:
                            game.items_on_ground.append(dropped_item)
                            print(f"Dropped {dropped_item.name} from invcontainer slot.")
                else:
                    dropped_item = game.player.drop_item(game, source, index, container_item)
                    if dropped_item:
                        dropped_item.rect.center = game.player.rect.center
                        game.items_on_ground.append(dropped_item)

            elif option == 'Open' or option == 'Read' or option == 'Inspect':
                if getattr(item, 'item_type', None) == 'mobile':
                    modal_exists = any(m['type'] == 'mobile' and m['item'] == item for m in game.modals)
                    if not modal_exists:
                        new_mobile_modal = {
                            'id': uuid.uuid4(), 'type': 'mobile', 'item': item,
                            'position': game.last_modal_positions['mobile'],
                            'is_dragging': False, 'drag_offset': (0, 0),
                            'rect': pygame.Rect(game.last_modal_positions['mobile'][0], game.last_modal_positions['mobile'][1], 250, 400), 
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
                            'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], 300, 300),
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
                elif source == 'invcontainer':
                    item_to_unequip = game.player.invcontainer
                    if item_to_unequip and item_to_unequip == item:
                        game.player.invcontainer = None 
                        if len(game.player.inventory) < game.player.get_total_inventory_slots():
                            game.player.inventory.append(item_to_unequip)
                        else:
                            item_to_unequip.rect.center = game.player.rect.center
                            game.items_on_ground.append(item_to_unequip)

            elif (source == 'ground' or source == 'nearby') and option == 'Grab':
                
                target_inventory = game.player.inventory
                target_capacity = game.player.get_total_inventory_slots()
                
                if len(target_inventory) < target_capacity:
                    grabbed = False
                    # Use 'item' directly (captured from closure) instead of index for safety
                    if source == 'ground' and item in game.items_on_ground:
                        game.items_on_ground.remove(item)
                        grabbed = True
                    elif source == 'nearby' and container_item and item in container_item.inventory:
                        container_item.inventory.remove(item)
                        grabbed = True
                    
                    if grabbed:
                        target_inventory.append(item)
                        game.player.stack_item_in_inventory(item)
                else:
                    print("Inventory full.")

                if len(target_inventory) < target_capacity:
                    grabbed_item = None
                    if source == 'ground' and 0 <= index < len(game.items_on_ground):
                        grabbed_item = game.items_on_ground.pop(index)
                    elif source == 'nearby' and container_item and 0 <= index < len(container_item.inventory):
                        grabbed_item = container_item.inventory.pop(index)
                    if grabbed_item:
                        target_inventory.append(grabbed_item)
                        game.player.stack_item_in_inventory(grabbed_item) 

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
             if 'gear_slot_rects' in modal:
                for slot_name, slot_rect in modal['gear_slot_rects'].items():
                    if slot_rect.collidepoint(mouse_pos):
                        item = game.player.clothes.get(slot_name)
                        if item:
                            clicked_item, click_source, click_index = item, 'gear', slot_name
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

    # [FIX] Check if we are clicking "through" a modal to the ground
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
            world_pos = game.screen_to_world(mouse_pos)
            grid_x = int(world_pos[0] // TILE_SIZE)
            grid_y = int(world_pos[1] // TILE_SIZE)
            tile = game.map_manager.get_tile_at(grid_x, grid_y)

            if tile and tile.get('type') == "maptile_car":
                vehicle = game.map_manager.get_vehicle_by_tile(tile)
                if vehicle:
                    clicked_item = vehicle
                    click_source = 'container_map'
                    click_index = 0
            
            tile_center_x = (grid_x * TILE_SIZE) + (TILE_SIZE / 2)
            tile_center_y = (grid_y * TILE_SIZE) + (TILE_SIZE / 2)
            dist = math.hypot(game.player.rect.centerx - tile_center_x, game.player.rect.centery - tile_center_y)

            if tile and tile.get('sleep') and dist < TILE_SIZE * 2:
                clicked_item = {'name': 'Bed', 'type': 'map_tile'} 
                click_source = 'map_tile'

    if not clicked_item:
        world_pos = game.screen_to_world(mouse_pos)
        for light in game.map_lights:
            # Check if we clicked the specific tile of the light
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


    if clicked_item:
        game.context_menu['active'] = True
        game.context_menu['item'] = clicked_item
        game.context_menu['source'] = click_source
        game.context_menu['index'] = click_index
        game.context_menu['container_item'] = click_container_item
        game.context_menu['position'] = mouse_pos

        options = ['']
        if click_source == 'npc':
            if clicked_item.is_following:
                options.append('Unfollow')
            else:
                options.append('Follow')

        elif click_source == 'map_tile':
            options = ['Sleep']
        elif click_source == 'light_source': # [NEW]
            status = "OFF" if clicked_item['active'] else "ON"
            options = ['Toggle Light']
        elif click_source == 'player_self':
            options = ['Status', 'Inventory', 'Gear']
        else:
            options = game.player.get_item_context_options(clicked_item, click_source, click_container_item)

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
        elif click_source == 'invcontainer':
            if 'Unequip' not in options: options.append('Unequip')
            if 'Drop' not in options: options.append('Drop')
            options = [o for o in options if o != 'Equip']
        elif click_source == 'ground':
            if 'Drop' in options: options.remove('Drop')
            if not isinstance(clicked_item, Corpse):
                if 'Grab' not in options: options.insert(0, 'Grab') 
            if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None and not isinstance(clicked_item, Corpse):
                if 'Place on Backpack' not in options: options.append('Place on Backpack')
            if getattr(clicked_item, 'inventory', None) is not None:
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
            if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None and not isinstance(clicked_item, Corpse):
                if 'Place on Backpack' not in options: options.append('Place on Backpack')

        game.context_menu['options'] = options
        game.context_menu['rects'] = []
        return

def handle_left_click_drag_candidate(game, mouse_pos):
    topmost_modal = None
    for modal in reversed(game.modals):
        if modal['rect'].collidepoint(mouse_pos):
            topmost_modal = modal
            break
    
    if not topmost_modal:
        return 

    modal = topmost_modal
    if modal['type'] == 'vehicle' and modal.get('active_tab') == 'Info':
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

            if game.player.invcontainer:
                slot_rect = get_invcontainer_slot_rect(modal['position'])
                if slot_rect.collidepoint(mouse_pos):
                    game.drag_candidate = (game.player.invcontainer, (0, 'invcontainer'))
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
        
        elif modal.get('active_tab') == 'Bag':
            if game.player.backpack:
                pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                for i, item in enumerate(game.player.backpack.inventory):
                    if item:
                        slot_rect = get_container_slot_rect(pos_for_calc, i)
                        if slot_rect.collidepoint(mouse_pos):
                            game.drag_candidate = (item, (i, 'container', game.player.backpack, modal['id']))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            return

    elif modal['type'] == 'gear':
        if 'gear_slot_rects' in modal:
            for slot_name, slot_rect in modal['gear_slot_rects'].items():
                if slot_rect.collidepoint(mouse_pos):
                    item = game.player.clothes.get(slot_name)
                    if item:
                        game.drag_candidate = (item, (slot_name, 'gear'))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
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
    
    if not click_in_modal:
        for i in range(5):
            if get_belt_hud_slot_rect(i).collidepoint(mouse_pos):
                click_in_modal = True
                break

    if click_in_modal:
        return

    if GAME_OFFSET_X <= mouse_pos[0] < GAME_OFFSET_X + GAME_WIDTH:
        weapon = game.player.active_weapon
        if game.player.is_reloading:
            print("Cannot shoot while reloading.")
            return

        if weapon and weapon.item_type == 'weapon_ranged' and weapon.ammo_type:
            
            if weapon.load > 0 and weapon.durability > 0:
                if 'shoot' in weapon.sounds and weapon.sounds['shoot']:
                    game.sound_manager.play_sound(
                        weapon.sounds['shoot'], 
                        subdir='items',
                        game=game,
                        source_pos=game.player.rect.center
                    )

                target_world_x, target_world_y = game.screen_to_world(mouse_pos)
                
                dx = target_world_x - game.player.rect.centerx
                dy = target_world_y - game.player.rect.centery
                base_angle = math.atan2(dy, dx)

                base_aim_inaccuracy = game.player.current_aim_factor * 25.0
                ranged_level = game.player.progression.get_ranged(game.player)
                skill_modifier = max(0.1, 1.0 - (ranged_level * 0.05))
                final_inaccuracy = base_aim_inaccuracy * skill_modifier
                total_spread_deg = weapon.spread_angle + final_inaccuracy

                for _ in range(weapon.pellets):
                    spread = math.radians(random.uniform(-total_spread_deg / 2, total_spread_deg / 2))
                    angle = base_angle + spread
                    
                    target_x = game.player.rect.centerx + math.cos(angle) * 1000
                    target_y = game.player.rect.centery + math.sin(angle) * 1000

                    game.projectiles.append(Projectile(game.player.rect.centerx, game.player.rect.centery, target_x, target_y))

                weapon.load -= 1

                dur_loss = game.player.progression.get_ranged_durability_loss(game.player)
                weapon.durability = max(0, weapon.durability - dur_loss)

                game.player.gun_flash_timer = 5
                if weapon.durability <= 0:
                    print(f"{weapon.name} broke!")
                    game.player.progression._add_xp(game.player, game.player.progression.maintenance, 'maintenance', 50)
                    game.player.destroy_broken_weapon(weapon)
            elif weapon.load <= 0: 
                if 'noammo' in weapon.sounds and weapon.sounds['noammo']:
                    game.sound_manager.play_sound(weapon.sounds['noammo'], subdir='items', game=game, source_pos=game.player.rect.center)
                print(f"**CLICK!** {weapon.name} is out of ammo.")
            else: print(f"**CLUNK!** {weapon.name} is broken.")

        else:
            # --- MELEE ATTACK LOGIC ---
            if game.player.progression.handle_melee_attack(game.player):
                if weapon and weapon.item_type in ['weapon_melee', 'tool'] and 'swing' in weapon.sounds and weapon.sounds['swing']:
                    game.sound_manager.play_sound(
                        weapon.sounds['swing'], 
                        subdir='items',
                        game=game,
                        source_pos=game.player.rect.center
                    )

                game.player.melee_swing_timer = 10
                player_screen_x = GAME_OFFSET_X + GAME_WIDTH / 2
                player_screen_y = GAME_HEIGHT / 2
                
                dx_swing = mouse_pos[0] - player_screen_x
                dy_swing = mouse_pos[1] - player_screen_y
                game.player.melee_swing_angle = math.atan2(-dy_swing, dx_swing)
          
                hit_something = False
                world_pos = game.screen_to_world(mouse_pos)

                # Check Zombies (Proximity)
                for zombie in game.zombies:
                    if game.player.rect.colliderect(zombie.rect.inflate(20, 20)):
                        if player_hit_zombie(game.player, zombie, game):
                            handle_zombie_death(game, zombie, game.items_on_ground, game.obstacles, weapon)
                            game.zombies_killed += 1
                        hit_something = True
                        break

                # [FIX] Check NPCs (Proximity + Direction OR Direct Click)
                if not hit_something: # Prioritize zombies
                    for npc in game.npcs:
                        if not npc.is_dead:
                            # 1. Check Distance
                            dist = math.hypot(game.player.rect.centerx - npc.rect.centerx, game.player.rect.centery - npc.rect.centery)
                            attack_range = TILE_SIZE * 2
                            
                            if dist <= attack_range:
                                # 2. Check Hit Condition (Click OR Facing)
                                clicked_on_it = npc.rect.collidepoint(world_pos)
                                
                                # Angle check
                                dx = npc.rect.centerx - game.player.rect.centerx
                                dy = game.player.rect.centery - npc.rect.centery # Inverted Y for math
                                npc_angle = math.atan2(dy, dx)
                                swing_angle = game.player.melee_swing_angle
                                angle_diff = abs(swing_angle - npc_angle)
                                if angle_diff > math.pi: angle_diff = 2 * math.pi - angle_diff
                                
                                # 45 degree cone (0.8 rads)
                                if clicked_on_it or angle_diff < 0.8:
                                    damage = game.player.get_attack_damage()
                                    npc.take_damage(damage, game, attacker=game.player)
                                    display_message(game, f"You attacked {npc.name} for {damage} damage!")
                                    hit_something = True
                                    break 

                if not hit_something: print("Swung and missed!")