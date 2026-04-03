import pygame
import uuid
import random
import math
import time
from core.data.config import *
from core.entities.item.item import Item
from core.ui.inventory_modal import get_belt_hud_slot_rect
from core.ui.npc_dialog_modal import get_npc_dialog_option_rect
from core.messages import display_message
from core.events.keyboard import toggle_messages_modal, toggle_status_modal, toggle_inventory_modal, toggle_nearby_modal, toggle_gear_modal, toggle_crafting_modal, toggle_pause, toggle_help_modal, toggle_slots_modal
# Imports from split files
from core.events.mouse_context import handle_context_menu_click, handle_right_click
from core.events.mouse_drag import handle_mouse_up, handle_mouse_motion, handle_left_click_drag_candidate
from core.events.mouse_combat import handle_attack
from core.data.localization import tr

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
                    # --- [NEW] Check Tab Clicks ---
                    tab_rects = topmost_modal.get('tab_rects', [])
                    clicked_tab = False
                    for t_idx, t_rect in enumerate(tab_rects):
                        if t_rect.collidepoint(mouse_pos):
                            topmost_modal['active_tab_index'] = t_idx
                            clicked_tab = True
                            break
                    if clicked_tab: return
                    
                    active_tab = topmost_modal.get('active_tab_index', 0)
                    
                    if active_tab == 0:
                        active_index = topmost_modal.get('active_dialog_index', -1)
                        if active_index == -1:
                            dialogs = topmost_modal.get('dialogs', [])
                            scroll_offset_y = topmost_modal.get('scroll_offset_y', 0)
                            
                            # [NEW] Ensure click happens within the content viewport, not out of bounds
                            content_y = topmost_modal.get('tab_rects', [pygame.Rect(0,0,0,0)])[0].bottom + 15
                            
                            if mouse_pos[1] >= content_y:
                                for i in range(len(dialogs)):
                                    # [MODIFIED] Pass the scroll offset!
                                    rect = get_npc_dialog_option_rect(topmost_modal['position'], i, dialogs, scroll_offset_y)
                                    if rect.collidepoint(mouse_pos):
                                        topmost_modal['active_dialog_index'] = i
                                        topmost_modal['scroll_offset_y'] = 0 # Reset offset for the next view
                                        
                                        selected_opt = dialogs[i]
                                        npc_ref = topmost_modal['npc']
                                        
                                        # --- [NEW] ANTI-EXPLOIT CHECK ---
                                        is_once = selected_opt.get('dialog_type') == 'once'
                                        node_id = selected_opt.get('node_id')
                                        q_text = selected_opt.get('q')
                                        dialog_key = f"{node_id}_{q_text}"
                                        
                                        if is_once and dialog_key in game.player.dialog_history:
                                            display_message(game, f"[NPC] {npc_ref.name}: You were already awarded")
                                        else:
                                            # [NEW] Handle Memory Saving
                                            if is_once and node_id and q_text:
                                                game.player.dialog_history.append(dialog_key)
                                                    
                                                # Store onto Global Player Journal
                                                if not hasattr(game.player, 'special_dialogs'):
                                                    game.player.special_dialogs = []
                                                
                                                already_saved = any(d['q'] == q_text for d in game.player.special_dialogs)
                                                if not already_saved:
                                                    game.player.special_dialogs.append({
                                                        'q': q_text,
                                                        'a': selected_opt.get('a', ''),
                                                        'npc_name': npc_ref.name  # Save the speaker's name globally!
                                                    })
                                                    
                                            # --- Process Unlocks, Awards, and Consumables ---
                                            
                                            # 1. Unlock future dialog nodes
                                            if selected_opt.get('unlock_flag'):
                                                npc_ref.unlock_node(selected_opt['unlock_flag'])
                                                
                                            # 2. Consume Quest Items (if required)
                                            if selected_opt.get('req_item'):
                                                item_names = [i.strip() for i in selected_opt['req_item'].replace('[', '').replace(']', '').split(',')]
                                                for i_name in item_names:
                                                    # Try removing from inventory
                                                    removed = False
                                                    for idx, slot in enumerate(game.player.inventory):
                                                        if slot and slot.name == i_name:
                                                            item_to_give = game.player.inventory.pop(idx) # Properly remove from list
                                                            npc_ref.inventory.append(item_to_give) # Transfer item to NPC
                                                            removed = True
                                                            break
                                                    # If not in inventory, check the belt
                                                    if not removed:
                                                        for idx, slot in enumerate(game.player.belt):
                                                            if slot and slot.name == i_name:
                                                                item_to_give = game.player.belt[idx]
                                                                game.player.belt[idx] = None
                                                                item_to_give.in_belt = False
                                                                # Unequip if it was in the hands
                                                                if game.player.active_weapon == item_to_give:
                                                                    game.player.active_weapon = None
                                                                npc_ref.inventory.append(item_to_give) # Transfer item to NPC
                                                                break

                                            # 3. Award Item(s) to Player
                                            if selected_opt.get('award_item'):
                                                item_names = [i.strip() for i in selected_opt['award_item'].replace('[', '').replace(']', '').split(',')]
                                                for i_name in item_names:
                                                    new_item = Item.create_from_name(i_name)
                                                    if new_item:
                                                        placed = False
                                                        if len(game.player.inventory) < game.player.base_inventory_slots:
                                                            game.player.inventory.append(new_item)
                                                            placed = True
                                                        if not placed:
                                                            new_item.rect.center = game.player.rect.center
                                                            game.items_on_ground.append(new_item)
                                                        display_message(game, f"{tr('msg', 'Received')}: {i_name}")

                                            # --- 4. Quest Completion ---
                                            if selected_opt.get('complete_flag'):
                                                comp_flag = selected_opt['complete_flag']
                                                if hasattr(game.player, 'quests') and comp_flag in game.player.quests:
                                                    game.player.quests.remove(comp_flag)
                                                    if not hasattr(game.player, 'completed_quests'):
                                                        game.player.completed_quests = []
                                                    game.player.completed_quests.append(comp_flag)
                                                    display_message(game, f"{tr('msg', 'Quest Completed')}: {comp_flag}")

                                            # --- 5. Gain XP ---
                                            if selected_opt.get('gain_xp'):
                                                xp_str = selected_opt['gain_xp'].replace('[', '').replace(']', '')
                                                if ':' in xp_str:
                                                    attr, amt = xp_str.split(':', 1)
                                                    try:
                                                        game.player.progression.add_xp(game.player, attr.strip(), int(amt))
                                                        #display_message(game, f"+{amt} {attr.capitalize()} XP")
                                                    except ValueError:
                                                        pass

                                            # --- 6. NPC State Changes ---
                                            if selected_opt.get('npc_state_friendly') is not None:
                                                npc_ref.is_friendly = str(selected_opt['npc_state_friendly']).lower() == 'true'
                                                if not npc_ref.is_friendly:
                                                    npc_ref.state = 'chasing'
                                                    npc_ref.aggro_timer = 5000
                                                    npc_ref.current_attacker = game.player

                                            if selected_opt.get('npc_state_static') is not None:
                                                npc_ref.is_static = str(selected_opt['npc_state_static']).lower() == 'true'
                                                if not npc_ref.is_static:
                                                    npc_ref.state = 'wandering'
                                        
                                        # Refresh the dialog options list immediately so the used 'once' dialog vanishes 
                                        # topmost_modal['dialogs'] = npc_ref.get_dialog_options()
                                        break
                        else:
                            topmost_modal['active_dialog_index'] = -1
                            
                            # --- [NEW] Refresh dynamic dialog options ---
                            # This recalculates requirements (like new items or unlocked flags)
                            # so newly available dialog options appear immediately!
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
                        elif topmost_modal['type'] == 'help': full_h = HELP_MODAL_HEIGHT
                        elif topmost_modal['type'] == 'big_map': full_h = MAP_MODAL_HEIGHT
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

                    elif button['type'] == 'send_msg':
                        if game.chat_input_text.strip():
                            game.player.chat_text = game.chat_input_text
                            game.player.chat_timer = game.player.chat_duration
                            display_message(game, f"[{tr('msg', 'You')}]: {game.chat_input_text}")
                            game.chat_input_text = ""
                            game.chat_active = True 
                        return
                    elif button['type'] == 'chat_input':
                        game.chat_active = True
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
                             
                             # Fix: Provide fallback tabs for Vehicle modal if 'tabs_data' isn't natively populated on the dictionary
                             if not tabs_data and topmost_modal['type'] == 'vehicle':
                                 tabs_data = [{'label': 'Vehicle'}, {'label': 'Mechanics'}, {'label': 'Seats'}]
                                 
                             if i < len(tabs_data):
                                 topmost_modal['active_tab'] = tabs_data[i]['label']
                                 return

                if hasattr(topmost_modal, 'handle_event'):
                    if topmost_modal.handle_event(event): return

                # Engine and Lights toggles specifically on the Info tab
                if topmost_modal['type'] == 'vehicle' and topmost_modal.get('active_tab') == 'Vehicle':
                    rects = topmost_modal.get('rects', {})
                    veh = topmost_modal['vehicle']
                    
                    if 'engine_on' in rects and rects['engine_on'].collidepoint(mouse_pos):
                        if not veh.active: veh.toggle_engine()
                        return
                    if 'engine_off' in rects and rects['engine_off'].collidepoint(mouse_pos):
                        if veh.active: veh.toggle_engine()
                        return
                    if 'lights_on' in rects and rects['lights_on'].collidepoint(mouse_pos):
                        if veh.lights != 'on': veh.toggle_lights()
                        return
                    if 'lights_off' in rects and rects['lights_off'].collidepoint(mouse_pos):
                        if veh.lights == 'on': veh.toggle_lights()
                        return

                
                
                if topmost_modal['type'] == 'big_map' and not topmost_modal.get('minimized', False):
                    map_rect = topmost_modal.get('map_area_rect')
                    if map_rect and map_rect.collidepoint(mouse_pos):
                        topmost_modal['is_dragging_map'] = True
                        topmost_modal['drag_map_start'] = mouse_pos
                        return

                handle_left_click_drag_candidate(game, mouse_pos)
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
        if game.slots_button_rect and game.slots_button_rect.collidepoint(mouse_pos):
            toggle_slots_modal(game); return
        if game.messages_button_rect and game.messages_button_rect.collidepoint(mouse_pos):
            toggle_messages_modal(game); return
        if game.crafting_button_rect and game.crafting_button_rect.collidepoint(mouse_pos):
            toggle_crafting_modal(game); return
        if game.help_button_rect and game.help_button_rect.collidepoint(mouse_pos): # <--- ADD THIS
            toggle_help_modal(game); return

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
            
        if getattr(game.player, 'is_aiming', False):
            handle_attack(game, mouse_pos)
            return

    elif event.button in (4, 5):
        topmost_modal = None
        for modal in reversed(game.modals):
            if modal['rect'].collidepoint(mouse_pos):
                topmost_modal = modal
                break
        if topmost_modal:
            # Button 4 is scroll UP (positive dy), Button 5 is scroll DOWN (negative dy)
            topmost_modal['scroll_dy'] = 1 if event.button == 4 else -1
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

        if topmost_modal and topmost_modal['type'] in ['text', 'help', 'slots', 'npc_dialog']:
            offset = topmost_modal.get('scroll_offset_y', 0)
            max_scroll = topmost_modal.get('max_scroll_offset', 0)
            
            if event.button == 4: # Scroll Up
                topmost_modal['scroll_offset_y'] = max(0, offset - 30)
            elif event.button == 5: # Scroll Down
                topmost_modal['scroll_offset_y'] = min(max_scroll, offset + 30)
            return

    elif event.button == 3:
        if game.context_menu['active']:
            game.context_menu['active'] = False
            return

        handle_right_click(game, mouse_pos)
        return