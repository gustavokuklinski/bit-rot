# core/events/mouse.py
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
from core.ui.notifications import add_notification
from core.placement import find_free_tile

def handle_mouse_down(game, event, mouse_pos):
    if event.button == 1:
        if getattr(game, 'item_to_place', None):
            adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
            world_pos = game.screen_to_world(adjusted_mouse_pos)
            
            mouse_tx = int(world_pos[0]) // TILE_SIZE
            mouse_ty = int(world_pos[1]) // TILE_SIZE
            
            p_tx = int(game.player.rect.centerx // TILE_SIZE)
            p_ty = int(game.player.rect.centery // TILE_SIZE)
            
            # [FIX] STRICT SNAP: Force the click position to the top-left of the tile
            snap_x = mouse_tx * TILE_SIZE
            snap_y = mouse_ty * TILE_SIZE
            
            in_range = abs(mouse_tx - p_tx) <= 1 and abs(mouse_ty - p_ty) <= 1
            
            if in_range:
                test_rect = pygame.Rect(snap_x, snap_y, TILE_SIZE, TILE_SIZE)
                is_free = not any(ob.colliderect(test_rect) for ob in getattr(game, 'obstacles', []))
                
                if not is_free:
                    display_message(tr('msg', "Cannot place item here, blocked by obstacle!"))
                else:
                    item_data = game.item_to_place
                    item = item_data['item']
                    source = item_data['source']
                    index = item_data['index']
                    container_item = item_data['container']
                    
                    if getattr(item, 'liquid', False):
                        display_message(tr('msg', "Cannot place liquid directly."))
                    else:
                        dropped_item = None
                        if source == 'gear':
                            item_to_drop = game.player.clothes.get(index)
                            if item_to_drop and item_to_drop == item:
                                dropped_item = game.player.drop_item(game, source, index, container_item)
                        else:
                            dropped_item = game.player.drop_item(game, source, index, container_item)
                            
                        if not dropped_item and game.items_on_ground:
                            if game.items_on_ground[-1].name == item.name:
                                dropped_item = game.items_on_ground[-1]
                                
                        if dropped_item:
                            dropped_item.rect.topleft = (snap_x, snap_y)
                            dropped_item.x, dropped_item.y = snap_x, snap_y
                            dropped_item.is_placed = True
                            dropped_item.layer = getattr(game, 'current_layer_index', 1)
                            dropped_item.map_filename = getattr(game.map_manager, 'current_map_filename', '')
                            
                            if getattr(game, 'is_client', False) and getattr(game, 'client', None):
                                from core.server.network import NetMsg, send_msg
                                send_msg(game.client.socket, {
                                    'type': NetMsg.WORLD_ACTION, 
                                    'action': 'drop', 
                                    'item_data': dropped_item.to_dict(), 
                                    'x': dropped_item.x, 
                                    'y': dropped_item.y, 
                                    'layer': dropped_item.layer,
                                    'is_placed': True
                                })
                            
                            if game and hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound(
                                    'place.ogg',
                                    subdir='items',
                                    game=game,
                                    source_pos=dropped_item.rect.center,
                                    base_volume=0.5,
                                    pitch_variance=0.1,
                                    is_critical=True
                                )
            else:
                display_message(tr('msg', "Too far to place item!"))
                
            game.item_to_place = None
            return

        if game.context_menu['active']:
            menu_clicked = False
            for rect in game.context_menu.get('rects', []):
                if rect.collidepoint(mouse_pos):
                    handle_context_menu_click(game, mouse_pos)
                    return 
            game.context_menu['active'] = False

        if getattr(game, 'notifications', None):
            clicked_notif = False
            for notif in game.notifications:
                if notif.get('rect') and notif['rect'].collidepoint(mouse_pos):
                    # Ensure status modal is open
                    status_modal = next((m for m in game.modals if m['type'] == 'status'), None)
                    target_tab = notif.get('target_tab', 'Quests')
                    if status_modal:
                        status_modal['active_tab'] = target_tab
                        # Bring modal to front
                        game.modals.remove(status_modal)
                        game.modals.append(status_modal)
                    else:
                        toggle_status_modal(game)
                        # The newly created modal is always placed at the end of the list
                        game.modals[-1]['active_tab'] = target_tab
                        
                    # Remove the clicked notification
                    game.notifications.remove(notif)
                    clicked_notif = True
                    break
                    
            # If a notification was clicked, stop processing other UI underneath it
            if clicked_notif:
                return

        topmost_modal = None
        for modal in reversed(game.modals):
            if modal['rect'].collidepoint(mouse_pos):
                topmost_modal = modal
                break
        
        if topmost_modal:
            # 1. Direct close button click
            if topmost_modal.get('close_button_rect') and topmost_modal['close_button_rect'].collidepoint(mouse_pos):
                if topmost_modal.get('type') == 'messages':
                    game.chat_active = False
                game.modals.remove(topmost_modal)
                return

            # 2. Immediately bring clicked modal to the very top (focus it)
            if game.modals[-1] != topmost_modal:
                game.modals.remove(topmost_modal)
                game.modals.append(topmost_modal)

            flat_buttons = []
            def _flatten_buttons(items):
                if isinstance(items, dict):
                    flat_buttons.append(items)
                elif isinstance(items, (list, tuple)):
                    for i in items:
                        _flatten_buttons(i)
            
            _flatten_buttons(getattr(game, 'modal_buttons', []))

            # 3. Check specific topmost modal buttons
            for button in flat_buttons:
                if 'id' not in button or 'rect' not in button:
                    continue

                if button.get('id') == topmost_modal.get('id') and button['rect'].collidepoint(mouse_pos):
                    if button.get('type') == 'close':
                        if topmost_modal.get('type') == 'messages':
                            game.chat_active = False
                        game.modals.remove(topmost_modal)
                        return
                    elif button.get('type') in ['map_zoom_in', 'map_zoom_out']:
                        current_zoom = float(topmost_modal.get('map_zoom', 4))
                        is_image_mode = topmost_modal.get('full_map_image') is not None
                        if is_image_mode:
                            step = max(0.2, current_zoom * 0.2)
                            if button.get('type') == 'map_zoom_in':
                                topmost_modal['map_zoom'] = min(50.0, current_zoom + step)
                            else:
                                topmost_modal['map_zoom'] = max(0.2, current_zoom - step)
                        else:
                            current_zoom = int(current_zoom)
                            if button.get('type') == 'map_zoom_in':
                                topmost_modal['map_zoom'] = min(32, current_zoom + 1)
                            else:
                                topmost_modal['map_zoom'] = max(2, current_zoom - 1)
                        return
                    elif button.get('type') == 'send_msg':
                        if game.chat_input_text.strip():
                            game.player.chat_text = game.chat_input_text
                            game.player.chat_timer = game.player.chat_duration
                            display_message(game, f"[{tr('msg', 'You')}]: {game.chat_input_text}")
                            game.chat_input_text = ""
                            game.chat_active = True 
                        return
                    elif button.get('type') == 'chat_input':
                        game.chat_active = True
                        return

            if 'instance' in topmost_modal and hasattr(topmost_modal['instance'], 'close_button_rect'):
                if topmost_modal['instance'].close_button_rect.collidepoint(mouse_pos):
                    if topmost_modal.get('type') == 'messages':
                        game.chat_active = False
                    game.modals.remove(topmost_modal)
                    return

            # 4. Dragging and modal controls
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

            if topmost_modal.get('type') == 'crafting':
                handle_rect = topmost_modal.get('crafting_handle_rect')
                if handle_rect and handle_rect.collidepoint(mouse_pos):
                    topmost_modal['is_dragging_scrollbar'] = True
                    topmost_modal['scrollbar_click_offset_y'] = mouse_pos[1] - handle_rect.y
                    return

            max_scroll = topmost_modal.get('max_scroll_offset', 0)
            if topmost_modal.get('type') == 'crafting':
                total = topmost_modal.get('crafting_total_items', 0)
                visible = topmost_modal.get('crafting_visible_items', 14)
                max_scroll = max(0, total - visible)
            
            if max_scroll > 0:
                topmost_modal['is_scrolling_content'] = True
                topmost_modal['content_drag_last_y'] = mouse_pos[1]
                
            if 'instance' in topmost_modal and hasattr(topmost_modal['instance'], 'handle_event'):
                if topmost_modal['instance'].handle_event(event): 
                    return
            
            if topmost_modal.get('type') in ['nearby', 'status', 'inventory', 'mobile', 'messages','vehicle', 'gear'] and 'tab_rects' in topmost_modal:
                for i, tab_rect in enumerate(topmost_modal.get('tab_rects', [])):
                    if tab_rect.collidepoint(mouse_pos):
                        tabs_data = topmost_modal.get('tabs_data', [])
                        if not tabs_data and topmost_modal.get('type') == 'vehicle':
                            tabs_data = [{'label': 'Vehicle'}, {'label': 'Mechanics'}]
                             
                        if i < len(tabs_data):
                            topmost_modal['active_tab'] = tabs_data[i]['label']
                            return

            # --- [FIX] NPC DIALOG MODAL TABS & DIALOGUE CLICK HANDLER ---
            if topmost_modal.get('type') == 'npc_dialog':
                # 1. Tab Clicks (Current Dialog, Special Dialogs, Trade)
                if 'tab_rects' in topmost_modal:
                    for i, tab_rect in enumerate(topmost_modal['tab_rects']):
                        if tab_rect.collidepoint(mouse_pos):
                            topmost_modal['active_tab_index'] = i
                            topmost_modal['scroll_offset_y'] = 0
                            topmost_modal['active_dialog_index'] = -1
                            npc = topmost_modal.get('npc')
                            if npc and i == 0:
                                topmost_modal['dialogs'] = npc.get_dialog_options()
                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_ui_hover()
                            return

                # 2. Dialogue Lines & Answers (Tab 0: Current Dialog)
                if topmost_modal.get('active_tab_index', 0) == 0:
                    active_idx = topmost_modal.get('active_dialog_index', -1)
                    if active_idx == -1:
                        for opt_data in topmost_modal.get('dialog_option_rects', []):
                            if opt_data['rect'].collidepoint(mouse_pos):
                                clicked_idx = opt_data['index']
                                opt = opt_data['option']
                                npc = topmost_modal.get('npc')

                                topmost_modal['active_dialog_index'] = clicked_idx
                                topmost_modal['scroll_offset_y'] = 0

                                # 1. Gain XP reward if specified
                                gain_xp = opt.get('gain_xp')
                                if gain_xp:
                                    clean_xp = gain_xp.replace('[', '').replace(']', '').strip()
                                    for part in clean_xp.split(','):
                                        if ':' in part:
                                            skill, amt = part.split(':', 1)
                                            try:
                                                if hasattr(game.player, 'progression'):
                                                    amt_val = float(amt.strip())
                                                    game.player.progression.add_xp(game.player, skill.strip().lower(), amt_val)
                                                    display_message(game, f"+{int(amt_val)} XP {skill.strip().capitalize()}")
                                            except ValueError:
                                                pass

                                # 2. Deduct requested items from player
                                rqst = opt.get('rqst_item')
                                if rqst:
                                    clean_rqst = rqst.replace('[', '').replace(']', '').strip()
                                    for iname in [x.strip() for x in clean_rqst.split(',') if x.strip()]:
                                        target_lower = iname.lower()
                                        deducted = False
                                        for inv_list in [game.player.inventory, game.player.belt]:
                                            for slot_i, it in enumerate(inv_list):
                                                if it and (it.name.lower() == target_lower or target_lower in it.name.lower()):
                                                    if hasattr(it, 'load') and it.load is not None and it.load > 1:
                                                        it.load -= 1
                                                    else:
                                                        if inv_list is game.player.belt:
                                                            game.player.belt[slot_i] = None
                                                        else:
                                                            inv_list.pop(slot_i)
                                                    deducted = True
                                                    display_message(game, f"{tr('msg', 'Gave:')} {tr('item', it.name)}")
                                                    break
                                            if deducted: break
                                        if not deducted and hasattr(game.player, 'clothes'):
                                            for slot_k, it in game.player.clothes.items():
                                                if it and (it.name.lower() == target_lower or target_lower in it.name.lower()):
                                                    game.player.clothes[slot_k] = None
                                                    display_message(game, f"{tr('msg', 'Gave:')} {tr('item', it.name)}")
                                                    break

                                # 3. Award items to player with fallback aliases
                                award = opt.get('award_item')
                                if award:
                                    clean_award = award.replace('[', '').replace(']', '').strip()
                                    for iname in [x.strip() for x in clean_award.split(',') if x.strip()]:
                                        new_it = Item.create_from_name(iname)
                                        if not new_it:
                                            for cand in [f"{iname} on", f"{iname} off", iname.replace(" phone", "")]:
                                                new_it = Item.create_from_name(cand)
                                                if new_it: break

                                        if new_it:
                                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                                game.player.inventory.append(new_it)
                                                if hasattr(game.player, 'stack_item_in_inventory'):
                                                    game.player.stack_item_in_inventory(new_it)
                                            else:
                                                new_it.rect.center = game.player.rect.center
                                                new_it.x, new_it.y = new_it.rect.topleft
                                                game.items_on_ground.append(new_it)
                                            display_message(game, f"{tr('msg', 'Received:')} {tr('item', new_it.name)}")

                                # 4. Unlock narrative flags or new quests
                                unlock = opt.get('unlock_flag')
                                if unlock and npc:
                                    npc.unlock_node(unlock)
                                    if str(unlock).startswith("Quest:"):
                                        from core.ui.notifications import add_notification
                                        add_notification(game, tr('ui', 'New Quest!'), str(unlock)[6:].strip(), target_tab='Quests')
                                        display_message(game, f"{tr('msg', 'New Quest:')} {str(unlock)[6:].strip()}")

                                # 5. Complete quests
                                complete = opt.get('complete_flag')
                                if complete:
                                    if complete not in game.player.completed_quests:
                                        game.player.completed_quests.append(complete)
                                    if hasattr(game.player, 'quests') and complete in game.player.quests:
                                        game.player.quests.remove(complete)
                                    from core.ui.notifications import add_notification
                                    add_notification(game, tr('ui', 'Quest Completed!'), complete, target_tab='Quests')
                                    display_message(game, f"{tr('msg', 'Quest Completed:')} {complete}")

                                # 6. FIX: ONLY add to dialog_history if dialog_type is "once"
                                d_type = opt.get('dialog_type', '')
                                if d_type == 'once':
                                    dialog_key = f"{opt.get('node_id')}_{opt['q']}"
                                    if hasattr(game.player, 'dialog_history'):
                                        if dialog_key not in game.player.dialog_history:
                                            game.player.dialog_history.append(dialog_key)

                                if d_type in ('once', 'special'):
                                    if not hasattr(game.player, 'special_dialogs'):
                                        game.player.special_dialogs = []
                                    game.player.special_dialogs.append({
                                        'q': opt['q'],
                                        'a': opt['a'],
                                        'npc_name': npc.name if npc else 'Survivor'
                                    })

                                # 7. Attitude adjustments
                                if opt.get('npc_state_friendly') is not None and npc:
                                    npc.is_friendly = str(opt['npc_state_friendly']).lower() == 'true'
                                if opt.get('npc_state_static') is not None and npc:
                                    npc.is_static = str(opt['npc_state_static']).lower() == 'true'

                                if hasattr(game, 'sound_manager'):
                                    game.sound_manager.play_ui_hover()
                                return
                    else:
                        # FIX: In answer view, clicking ANYWHERE inside the modal returns to the dialogue list
                        if topmost_modal.get('rect') and topmost_modal['rect'].collidepoint(mouse_pos):
                            topmost_modal['active_dialog_index'] = -1
                            topmost_modal['scroll_offset_y'] = 0
                            npc = topmost_modal.get('npc')
                            if npc:
                                topmost_modal['dialogs'] = npc.get_dialog_options()
                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_ui_hover()
                            return
            # -------------------------------------------------------------

            if hasattr(topmost_modal, 'handle_event'):
                if topmost_modal.handle_event(event): return

            if topmost_modal.get('type') == 'vehicle' and topmost_modal.get('active_tab') == 'Vehicle':
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

            if topmost_modal.get('type') in ['big_map', 'mobile']:
                if topmost_modal.get('type') == 'mobile' and topmost_modal.get('active_tab', '') != 'Map':
                    pass
                else:
                    map_rect = topmost_modal.get('map_area_rect')
                    if map_rect and map_rect.collidepoint(mouse_pos):
                        topmost_modal['is_dragging_map'] = True
                        topmost_modal['last_drag_pos'] = mouse_pos
                        return

            handle_left_click_drag_candidate(game, mouse_pos)
            return

        if game.chat_active:
            game.chat_active = False

        if game.pause_button_rect and game.pause_button_rect.collidepoint(mouse_pos):
            toggle_pause(game); return
        
        if getattr(game, 'menu_hud_button_rect', None) and game.menu_hud_button_rect.collidepoint(mouse_pos):
            game.show_hud_menus = not getattr(game, 'show_hud_menus', False)
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
            if game.game_state != 'PAUSED': toggle_crafting_modal(game)
            return
        if game.help_button_rect and game.help_button_rect.collidepoint(mouse_pos):
            if game.game_state != 'PAUSED': toggle_help_modal(game)
            return
            
        if getattr(game.player, 'is_aiming', False):
            if getattr(game, 'game_state', None) == 'PLAYING':
                handle_attack(game, mouse_pos)
            return

    elif event.button in (4, 5):
        # [Unchanged Logic...]
        topmost_modal = None
        for modal in reversed(game.modals):
            if modal['rect'].collidepoint(mouse_pos):
                topmost_modal = modal
                break
        if topmost_modal:
            topmost_modal['scroll_dy'] = 1 if event.button == 4 else -1
        if topmost_modal and topmost_modal['type'] == 'crafting':
            offset = topmost_modal.get('crafting_scroll_offset', 0)
            total = topmost_modal.get('crafting_total_items', 0)
            visible = topmost_modal.get('crafting_visible_items', 14)
            max_scroll = max(0, total - visible)
            
            if event.button == 4:
                topmost_modal['crafting_scroll_offset'] = max(0, offset - 1)
            elif event.button == 5:
                topmost_modal['crafting_scroll_offset'] = min(max_scroll, offset + 1)
            return

        if topmost_modal and topmost_modal['type'] in ['text', 'help', 'slots', 'npc_dialog']:
            offset = topmost_modal.get('scroll_offset_y', 0)
            max_scroll = topmost_modal.get('max_scroll_offset', 0)
            
            if event.button == 4:
                topmost_modal['scroll_offset_y'] = max(0, offset - 30)
            elif event.button == 5:
                topmost_modal['scroll_offset_y'] = min(max_scroll, offset + 30)
            return

    elif event.button == 3:
        if getattr(game, 'item_to_place', None):
            game.item_to_place = None
            return
            
        if game.context_menu['active']:
            game.context_menu['active'] = False
            return

        handle_right_click(game, mouse_pos)
        return
    
    is_over_any_modal = any(modal.get('rect') and modal['rect'].collidepoint(mouse_pos) for modal in game.modals)
    if hasattr(game, 'dynamic_h') and not is_over_any_modal:
        for i in range(5):
            slot_rect = get_belt_hud_slot_rect(i, game=game, dynamic_h=game.dynamic_h)
            
            if slot_rect.collidepoint(mouse_pos):
                if game.player.belt[i] is not None:
                    game.drag_candidate = (game.player.belt[i], ('belt', i)) 
                    game.drag_start_pos = mouse_pos
                    game.drag_origin = ('belt', i)
                    return