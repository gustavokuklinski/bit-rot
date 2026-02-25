import pygame
import uuid
import random
import math
import time
from core.data.config import *
from core.entities.item.item import Item
from core.ui.inventory_modal import get_belt_hud_slot_rect, get_backpack_slot_rect
from core.ui.npc_dialog_modal import get_npc_dialog_option_rect
from core.messages import display_message
from core.events.keyboard import toggle_messages_modal, toggle_status_modal, toggle_inventory_modal, toggle_nearby_modal, toggle_gear_modal, toggle_crafting_modal, toggle_pause

# Imports from split files
from core.events.mouse_context import handle_context_menu_click, handle_right_click
from core.events.mouse_drag import handle_mouse_up, handle_mouse_motion, handle_left_click_drag_candidate
from core.events.mouse_combat import handle_attack

def handle_mouse_down(game, event, mouse_pos):
    if event.button == 1:
        if game.context_menu['active']:
            menu_clicked = False
            for rect in game.context_menu.get('rects', []):
                if rect.collidepoint(mouse_pos):
                    handle_context_menu_click(game, mouse_pos)
                    return 
            game.context_menu['active'] = False

        topmost_modal = None
        for modal in reversed(game.modals):
            if modal['rect'].collidepoint(mouse_pos):
                topmost_modal = modal
                break
        
        if topmost_modal:

            if topmost_modal['type'] == 'npc_dialog':
                clicked_header_button = False
                for button in getattr(game, 'modal_buttons', []):
                    if button['id'] == topmost_modal['id'] and button['rect'].collidepoint(mouse_pos):
                        clicked_header_button = True
                        break
                
                if not clicked_header_button:
                    active_index = topmost_modal.get('active_dialog_index', -1)
                    
                    if active_index == -1:
                        # Logic: Clicking a question
                        dialogs = topmost_modal.get('dialogs', [])
                        for i in range(len(dialogs)):
                            rect = get_npc_dialog_option_rect(topmost_modal['position'], i)
                            if rect.collidepoint(mouse_pos):
                                topmost_modal['active_dialog_index'] = i
                                
                                selected_opt = dialogs[i]
                                
                                # 1. Handle Unlock Flag
                                unlock_flag = selected_opt.get('unlock_flag')
                                if unlock_flag:
                                    topmost_modal['npc'].unlock_node(unlock_flag)

                                gain_raw = selected_opt.get('gain_xp')
                                if gain_raw and "[lucky:" in gain_raw:
                                    try:
                                        # Parse "[lucky:30]" -> 30
                                        val_str = gain_raw.split(':')[1].replace(']', '')
                                        xp_amount = int(val_str)
                                        # Add XP (can be negative)
                                        game.player.progression.add_xp(game.player, 'lucky', xp_amount)
                                    except Exception as e:
                                        print(f"Error applying dialog XP: {e}")

                                # [NEW] 1.2 Handle 'Once' Dialog History
                                if selected_opt.get('dialog_type') == 'once':
                                    node_id = selected_opt.get('node_id')
                                    q_text = selected_opt.get('q')
                                    if node_id and q_text:
                                        dialog_key = f"{node_id}_{q_text}"
                                        if dialog_key not in game.player.dialog_history:
                                            game.player.dialog_history.append(dialog_key)

                                # [CHANGED] 2. Handle State Changes
                                npc_ref = topmost_modal['npc']

                                # Handle Friendly/Hostile Change
                                friendly_flag = selected_opt.get('npc_state_friendly')
                                if friendly_flag is not None:
                                    # Convert string "true"/"false" to boolean
                                    is_friendly = str(friendly_flag).lower() == 'true'
                                    npc_ref.is_friendly = is_friendly
                                    print(f"NPC {npc_ref.name} friendly state set to: {is_friendly}")
                                    
                                    # If turning hostile, ensure they start looking for targets immediately
                                    if not is_friendly:
                                        npc_ref.state = 'chasing'

                                # Handle Static/Moving Change
                                static_flag = selected_opt.get('npc_state_static')
                                if static_flag is not None:
                                    is_static = str(static_flag).lower() == 'true'
                                    npc_ref.is_static = is_static
                                    print(f"NPC {npc_ref.name} static state set to: {is_static}")
                                    
                                    # If we tell them to move, reset idle timers so they don't wait
                                    if not is_static:
                                        npc_ref.idle_timer = 0

                                award_raw = selected_opt.get('award_item')
                                if award_raw:
                                    # Remove brackets if present
                                    cleaned_raw = award_raw.replace('[', '').replace(']', '')
                                    
                                    # Split by comma and strip whitespace to get list of options
                                    possible_items = [name.strip() for name in cleaned_raw.split(',')]
                                    
                                    if possible_items:
                                        # Randomly select one item from the list
                                        item_name = random.choice(possible_items)
                                        
                                        # Create Item
                                        new_item = Item.create_from_name(item_name)
                                        if new_item:
                                            # Check Inventory Space
                                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                                game.player.inventory.append(new_item)
                                                display_message(game, f"Received {new_item.name}!")
                                            else:
                                                # Drop on ground if full
                                                new_item.rect.center = game.player.rect.center
                                                game.items_on_ground.append(new_item)
                                                display_message(game, f"Inventory full. {new_item.name} dropped on ground.")
                                        else:
                                            print(f"Error: Could not create award item '{item_name}'")

                                
                                return
                    else:
                        # Logic: Clicking anywhere inside (except buttons) while viewing answer goes back
                        topmost_modal['active_dialog_index'] = -1
                        topmost_modal['dialogs'] = topmost_modal['npc'].get_dialog_options()
                        return

            if game.modals[-1] != topmost_modal:
                game.modals.remove(topmost_modal)
                game.modals.append(topmost_modal)
            
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
                        elif topmost_modal['type'] == 'crafting': full_h = CRAFTING_MODAL_HEIGHT
                        elif topmost_modal['type'] == 'npc_dialog': full_h = CRAFTING_MODAL_HEIGHT
                        else: full_h = CONTAINER_MODAL_WIDTH
                        topmost_modal['rect'].height = header_height if is_minimized else full_h
                        return
                    elif button['type'] in ['map_zoom_in', 'map_zoom_out']:
                        current_zoom = float(topmost_modal.get('map_zoom', 4))
                        is_image_mode = topmost_modal.get('full_map_image') is not None
                        
                        if is_image_mode:
                            step = max(0.2, current_zoom * 0.2)
                            if button['type'] == 'map_zoom_in':
                                topmost_modal['map_zoom'] = min(50.0, current_zoom + step)
                            else:
                                topmost_modal['map_zoom'] = max(0.2, current_zoom - step)
                        else:
                            current_zoom = int(current_zoom)
                            if button['type'] == 'map_zoom_in':
                                topmost_modal['map_zoom'] = min(32, current_zoom + 1)
                            else:
                                topmost_modal['map_zoom'] = max(2, current_zoom - 1)
                        return
            
            if topmost_modal.get('minimized', False):
                 modal_header_rect = pygame.Rect(topmost_modal['position'][0], topmost_modal['position'][1], topmost_modal['rect'].width, 35)
                 if modal_header_rect.collidepoint(mouse_pos):
                    topmost_modal['is_dragging'] = True
                    topmost_modal['drag_offset'] = (mouse_pos[0] - topmost_modal['position'][0], mouse_pos[1] - topmost_modal['position'][1])
                    return
            else:
                modal_header_rect = pygame.Rect(topmost_modal['position'][0], topmost_modal['position'][1], topmost_modal['rect'].width, 35)
                if modal_header_rect.collidepoint(mouse_pos):
                    topmost_modal['is_dragging'] = True
                    topmost_modal['drag_offset'] = (mouse_pos[0] - topmost_modal['position'][0], mouse_pos[1] - topmost_modal['position'][1])
                    return

                scrollbar_rect = topmost_modal.get('scrollbar_handle_rect') 
                if scrollbar_rect and scrollbar_rect.collidepoint(mouse_pos):
                    topmost_modal['is_dragging_scrollbar'] = True
                    topmost_modal['scrollbar_drag_last_y'] = mouse_pos[1] 
                    return

                if topmost_modal['type'] == 'crafting':
                    handle_rect = topmost_modal.get('crafting_handle_rect')
                    if handle_rect and handle_rect.collidepoint(mouse_pos):
                        topmost_modal['is_dragging_scrollbar'] = True
                        topmost_modal['scrollbar_click_offset_y'] = mouse_pos[1] - handle_rect.y
                        return
                
                if 'instance' in topmost_modal and hasattr(topmost_modal['instance'], 'handle_event'):
                    if topmost_modal['instance'].handle_event(event): 
                        return
                
                if topmost_modal['type'] in ['nearby', 'status', 'inventory', 'mobile', 'messages','vehicle', 'gear'] and 'tab_rects' in topmost_modal:
                    for i, tab_rect in enumerate(topmost_modal.get('tab_rects', [])):
                        if tab_rect.collidepoint(mouse_pos):
                             tabs_data = topmost_modal.get('tabs_data', [])
                             if i < len(tabs_data):
                                 topmost_modal['active_tab'] = tabs_data[i]['label']
                                 return

                if hasattr(topmost_modal, 'handle_event'):
                    if topmost_modal.handle_event(event): return

                if topmost_modal['type'] == 'vehicle' and topmost_modal.get('active_tab') == 'Info':
                    rects = topmost_modal.get('rects', {})
                    veh = topmost_modal['vehicle']
                    if 'lights_on' in rects and rects['lights_on'].collidepoint(mouse_pos):
                        veh.toggle_lights(); return
                    if 'lights_off' in rects and rects['lights_off'].collidepoint(mouse_pos):
                        veh.toggle_lights(); return

                if topmost_modal['type'] == 'inventory' and topmost_modal.get('active_tab', 'Inventory') == 'Inventory':
                     backpack_slot_rect = get_backpack_slot_rect(topmost_modal['position'])
                     if backpack_slot_rect.collidepoint(mouse_pos) and game.player.backpack:
                         modal_exists = any(m for m in game.modals if m['type'] == 'container' and m['item'] == game.player.backpack)
                         if not modal_exists:
                            new_container_modal = {
                                'id': uuid.uuid4(),
                                'type': 'container',
                                'item': game.player.backpack,
                                'position': game.last_modal_positions['container'],
                                'is_dragging': False, 'drag_offset': (0, 0),
                                'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT),
                                'minimized': False
                            }
                            game.modals.append(new_container_modal)
                         return
                
                if topmost_modal['type'] == 'big_map' and not topmost_modal.get('minimized', False):
                    map_rect = topmost_modal.get('map_area_rect')
                    if map_rect and map_rect.collidepoint(mouse_pos):
                        topmost_modal['is_dragging_map'] = True
                        topmost_modal['drag_map_start'] = mouse_pos
                        return

                handle_left_click_drag_candidate(game, mouse_pos)
                return

        for button in getattr(game, 'modal_buttons', []):
             if not button.get('id'): 
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

        if game.pause_button_rect and game.pause_button_rect.collidepoint(mouse_pos):
            toggle_pause(game); return
        if game.forward_button_rect and game.forward_button_rect.collidepoint(mouse_pos):
            game.is_fast_forwarding = not game.is_fast_forwarding
            return
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
        if game.crafting_button_rect and game.crafting_button_rect.collidepoint(mouse_pos):
            toggle_crafting_modal(game); return

        for i, item in enumerate(game.player.belt):
            slot_rect = get_belt_hud_slot_rect(i)
            if slot_rect.collidepoint(mouse_pos):
                if item:
                    if game.player.action_timer > 0:
                        return
                    game.drag_candidate = (item, (i, 'belt'))
                    game.drag_start_pos = mouse_pos
                    game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                    return
            
        if (pygame.key.get_pressed()[pygame.K_LALT] or pygame.key.get_pressed()[pygame.K_LALT]):
            handle_attack(game, mouse_pos)
            return

    elif event.button in (4, 5):
        topmost_modal = None
        for modal in reversed(game.modals):
            if modal['rect'].collidepoint(mouse_pos):
                topmost_modal = modal
                break
        
        if topmost_modal and topmost_modal['type'] == 'crafting':
            offset = topmost_modal.get('crafting_scroll_offset', 0)
            total = topmost_modal.get('crafting_total_items', 0)
            visible = topmost_modal.get('crafting_visible_items', 14)
            max_scroll = max(0, total - visible)
            
            if event.button == 4: # Scroll Up
                topmost_modal['crafting_scroll_offset'] = max(0, offset - 1)
            elif event.button == 5: # Scroll Down
                topmost_modal['crafting_scroll_offset'] = min(max_scroll, offset + 1)
            return

    elif event.button == 3:
        if game.context_menu['active']:
            game.context_menu['active'] = False
            return

        handle_right_click(game, mouse_pos)
        return