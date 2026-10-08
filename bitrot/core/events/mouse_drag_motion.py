# core/events/mouse_drag_motion.py

import pygame
import math
from core.data.config import *
from core.entities.item.item import Item
from core.entities.item.item_data import ITEM_TEMPLATES
from core.ui.inventory_modal import get_inventory_slot_rect, get_belt_hud_slot_rect
from core.ui.container_modal import get_container_slot_rect
from core.messages import display_message
from core.data.localization import tr
from core.entities.item.item_helpers import is_infinite_liquid_source, is_container_closed_or_locked

def find_item_at_pos(game, mouse_pos):
    # 1. Identify the single topmost modal under the mouse cursor based on z-order
    top_modal = None
    for modal in reversed(game.modals):
        if modal.get('rect') and modal['rect'].collidepoint(mouse_pos):
            top_modal = modal
            break

    # 2. If the mouse is over any modal, ONLY look inside that topmost modal!
    if top_modal:
        m_type = top_modal.get('type')

        if m_type == 'inventory':
            if top_modal.get('active_tab', 'Inventory') == 'Inventory':
                for i, item in enumerate(game.player.inventory):
                    if item and get_inventory_slot_rect(i, top_modal['position']).collidepoint(mouse_pos):
                        return item
            elif top_modal.get('active_tab') in top_modal.get('container_mapping', {}):
                container = top_modal['container_mapping'][top_modal['active_tab']]
                if container and hasattr(container, 'inventory'):
                    pos_for_calc = (top_modal['rect'].x, top_modal['rect'].y + 40)
                    for i, item in enumerate(container.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            return item

        elif m_type == 'container':
            container = top_modal.get('item')
            if container and hasattr(container, 'inventory'):
                if is_infinite_liquid_source(container):
                    for item in container.inventory:
                        if getattr(item, 'liquid', False) or getattr(item, 'item_type', '') in ('liquid', 'car_fuel') or getattr(item, 'name', '') == 'Fuel Unit':
                            item.load = getattr(item, 'capacity', 100)
                for i, item in enumerate(container.inventory):
                    if item and get_container_slot_rect(top_modal['position'], i).collidepoint(mouse_pos):
                        return item

        elif m_type == 'gear':
            active_tab = top_modal.get('active_tab', 'Gear')
            if active_tab == 'Gear':
                if 'gear_slot_rects' in top_modal:
                    for slot_name, slot_rect in top_modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            return game.player.clothes.get(slot_name)
            elif active_tab in top_modal.get('container_mapping', {}):
                container = top_modal['container_mapping'][active_tab]
                if container and hasattr(container, 'inventory'):
                    pos_for_calc = (top_modal['rect'].x, top_modal['rect'].y + 40)
                    for i, item in enumerate(container.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            return item

        elif m_type == 'slots':
            for slot_data in top_modal.get('slot_rects', []):
                if slot_data['rect'].collidepoint(mouse_pos):
                    c = slot_data['container']
                    i = slot_data['index']
                    if hasattr(c, 'inventory') and i < len(c.inventory):
                        return c.inventory[i]

        elif m_type == 'vehicle':
            if top_modal.get('active_tab') == 'Mechanics' and 'equipment_rects' in top_modal:
                veh = top_modal.get('vehicle')
                if veh and hasattr(veh, 'equipment'):
                    for slot_name, slot_rect in top_modal['equipment_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            return veh.equipment.get(slot_name)

        elif m_type == 'npc_dialog':
            if top_modal.get('active_tab_index') == 2:
                for slot_data in top_modal.get('trade_slot_rects', []):
                    if slot_data['rect'].collidepoint(mouse_pos):
                        return slot_data['item']
                drop_zone = top_modal.get('trade_drop_zone_rect')
                if drop_zone and drop_zone.collidepoint(mouse_pos):
                    return top_modal.get('trade_offered_item')

        elif m_type == 'nearby':
            active_tab_label = top_modal.get('active_tab')
            active_container = None
            for tab_data in top_modal.get('tabs_data', []):
                if tab_data['label'] == active_tab_label:
                    active_container = tab_data['container']
                    break

            content_rect = top_modal.get('content_rect')
            if active_container and hasattr(active_container, 'inventory') and content_rect:
                is_closed = is_container_closed_or_locked(active_container, game.player)
                if not is_closed:
                    if is_infinite_liquid_source(active_container):
                        for item in active_container.inventory:
                            if getattr(item, 'liquid', False):
                                item.load = getattr(item, 'capacity', 100)
                    pos = content_rect.topleft
                    for i, item in enumerate(active_container.inventory):
                        if item and get_container_slot_rect(pos, i).collidepoint(mouse_pos):
                            return item

        # Cursor is over the topmost modal -> NEVER fall through to modals beneath it!
        return None

    # Not over any modal -> check Belt HUD
    for i, item in enumerate(game.player.belt):
        if item and get_belt_hud_slot_rect(i, game=game).collidepoint(mouse_pos):
            return item

    return None

def handle_left_click_drag_candidate(game, mouse_pos):
    if game.player.action_timer > 0:
        return
    topmost_modal = None
    for modal in reversed(game.modals):
        if modal['rect'].collidepoint(mouse_pos):
            topmost_modal = modal
            break
    
    if not topmost_modal:
        return 

    modal = topmost_modal
    if modal['type'] == 'vehicle' and modal.get('active_tab') == 'Mechanics':
        if 'equipment_rects' in modal:
            for slot_name, slot_rect in modal['equipment_rects'].items():
                if slot_rect.collidepoint(mouse_pos):
                    vehicle = modal['vehicle']
                    item = vehicle.equipment.get(slot_name)
                    if item:
                        # Cannot drag parts out without key inserted in the Key slot
                        if vehicle.equipment.get('key') is None:
                            display_message(tr('msg', "Vehicle requires key inserted in the Key slot."))
                            return
                        
                        # Prevent dragging the fuel tank out
                        if slot_name == 'fuel':
                            display_message(tr('msg', "Cannot remove the fuel tank. Right-click to siphon."))
                            return

                        game.drag_candidate = (item, (slot_name, 'vehicle_equipment', vehicle))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                        return
                        
    elif modal['type'] == 'mobile' and modal.get('active_tab') == 'Apps':
        for slot_data in modal.get('app_slot_rects', []):
            if slot_data['rect'].collidepoint(mouse_pos):
                i = slot_data['index']
                slots = getattr(game, 'app_state', {}).get('slots', [])
                item = slots[i]
                if item:
                    game.drag_candidate = (item, (i, 'app'))
                    game.drag_start_pos = mouse_pos
                    game.drag_offset = (mouse_pos[0] - slot_data['rect'].x, mouse_pos[1] - slot_data['rect'].y)
                    return

    if modal['type'] == 'nearby':
        active_tab_label = modal.get('active_tab')
        active_container = None
        for tab_data in modal.get('tabs_data', []):
            if tab_data['label'] == active_tab_label:
                active_container = tab_data['container']
                break
        
        if active_container and hasattr(active_container, 'inventory'):
            is_closed = is_container_closed_or_locked(active_container, game.player)
            if not is_closed:
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

        elif modal.get('active_tab') in modal.get('container_mapping', {}):
            container = modal['container_mapping'][modal['active_tab']]
            if container:
                pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                for i, item in enumerate(container.inventory):
                    if item:
                        slot_rect = get_container_slot_rect(pos_for_calc, i)
                        if slot_rect.collidepoint(mouse_pos):
                            game.drag_candidate = (item, (i, 'container', container, modal['id']))
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

    elif modal['type'] == 'slots':
        for slot_data in modal.get('slot_rects', []):
            if slot_data['rect'].collidepoint(mouse_pos):
                c = slot_data['container']
                i = slot_data['index']
                if i < len(c.inventory):
                    item = c.inventory[i]
                    game.drag_candidate = (item, (i, 'container', c))
                    game.drag_start_pos = mouse_pos
                    game.drag_offset = (mouse_pos[0] - slot_data['rect'].x, mouse_pos[1] - slot_data['rect'].y)
                    return

    elif modal['type'] == 'gear':
        active_tab = modal.get('active_tab', 'Gear')
        if active_tab == 'Gear':
            if 'gear_slot_rects' in modal:
                for slot_name, slot_rect in modal['gear_slot_rects'].items():
                    if slot_rect.collidepoint(mouse_pos):
                        item = game.player.clothes.get(slot_name)
                        if item:
                            game.drag_candidate = (item, (slot_name, 'gear'))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            return
        elif active_tab in modal.get('container_mapping', {}):
            container = modal['container_mapping'][active_tab]
            if container:
                pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                for i, item in enumerate(container.inventory):
                    if item:
                        slot_rect = get_container_slot_rect(pos_for_calc, i)
                        if slot_rect.collidepoint(mouse_pos):
                            game.drag_candidate = (item, (i, 'container', container, modal['id']))
                            game.drag_start_pos = mouse_pos
                            game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                            return

def handle_mouse_motion(game, event, mouse_pos):
    if game.player:
        player_screen_x = GAME_OFFSET_X + GAME_WIDTH / 2
        player_screen_y = GAME_HEIGHT / 2
        dx = mouse_pos[0] - player_screen_x
        dy = mouse_pos[1] - player_screen_y
        game.player.aim_angle = math.atan2(-dy, dx) 

    if getattr(game, 'context_menu', {}).get('active', False):
        game.hovered_item = None
    else:
        game.hovered_item = find_item_at_pos(game, mouse_pos)

    game.hovered_container = None

    adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
    world_pos = game.screen_to_world(adjusted_mouse_pos)

    for container in game.containers:
        if container.rect.collidepoint(world_pos):
            game.hovered_container = container
            break

    for modal in reversed(game.modals):
        if modal.get('is_dragging_scrollbar') and modal['type'] == 'crafting':
            track = modal.get('crafting_track_rect')
            handle = modal.get('crafting_handle_rect')
            
            if track and handle:
                track_y = track.y
                track_h = track.height
                handle_h = handle.height
                
                click_offset = modal.get('scrollbar_click_offset_y', 0)
                target_handle_y = mouse_pos[1] - click_offset
                
                available_space = track_h - handle_h
                if available_space > 0:
                    relative_y = target_handle_y - track_y
                    pct = relative_y / available_space
                    pct = max(0.0, min(1.0, pct))
                    
                    total = modal.get('crafting_total_items', 0)
                    visible = modal.get('crafting_visible_items', 14)
                    max_scroll = max(0, total - visible)
                    
                    modal['crafting_scroll_offset'] = int(pct * max_scroll)
            return

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

        if modal.get('is_scrolling_content'):
            if getattr(game, 'is_dragging', False) or getattr(game, 'drag_candidate', None):
                modal['is_scrolling_content'] = False
                continue
                
            mouse_delta_y = mouse_pos[1] - modal['content_drag_last_y']
            modal['content_drag_last_y'] = mouse_pos[1]
            
            if modal.get('type') == 'crafting':
                sensitivity = 20
                modal['content_drag_accum_y'] = modal.get('content_drag_accum_y', 0) + mouse_delta_y
                
                if abs(modal['content_drag_accum_y']) >= sensitivity:
                    steps = int(modal['content_drag_accum_y'] / sensitivity)
                    modal['content_drag_accum_y'] -= steps * sensitivity
                    
                    offset = modal.get('crafting_scroll_offset', 0)
                    total = modal.get('crafting_total_items', 0)
                    visible = modal.get('crafting_visible_items', 14)
                    max_scroll = max(0, total - visible)
                    modal['crafting_scroll_offset'] = max(0, min(max_scroll, offset - steps))
            else:
                max_scroll = modal.get('max_scroll_offset', 0)
                if max_scroll > 0:
                    current_offset = modal.get('scroll_offset_y', 0)
                    new_offset = current_offset - mouse_delta_y
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

                if is_infinite_liquid_source(container_info[0] if container_info else None) and getattr(item_to_drag, 'liquid', False):
                    item_to_drag.load = getattr(item_to_drag, 'capacity', 100)

                new_item = Item.create_from_name(item_to_drag.name)

                if not new_item:
                    item_to_drag.load += 1
                    game.drag_candidate = None
                    return

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
                    game.dragged_item.in_belt = False

                elif type_orig == 'gear':
                    slot_name = i_orig 
                    game.player.clothes[slot_name] = None 
                elif type_orig == 'container':
                    container_obj = container_info[0]
                    if is_infinite_liquid_source(container_obj) and getattr(game.dragged_item, 'liquid', False):
                        clone = Item.create_from_name(game.dragged_item.name)
                        if clone:
                            clone.load = getattr(clone, 'capacity', 100)
                            clone.durability = game.dragged_item.durability
                            game.dragged_item = clone
                        item_to_drag.load = getattr(item_to_drag, 'capacity', 100)
                    else:
                        container_obj.inventory.pop(i_orig)
                    container_obj._drag_locked = True
                elif type_orig == 'nearby':
                    container_obj = container_info[0]
                    if is_infinite_liquid_source(container_obj) and getattr(game.dragged_item, 'liquid', False):
                        clone = Item.create_from_name(game.dragged_item.name)
                        if clone:
                            clone.load = getattr(clone, 'capacity', 100)
                            clone.durability = game.dragged_item.durability
                            game.dragged_item = clone
                        item_to_drag.load = getattr(item_to_drag, 'capacity', 100)
                    else:
                        container_obj.inventory.pop(i_orig)
                        container_obj._drag_locked = True

                    if getattr(container_obj, 'item_type', '') == 'ground':
                        if item_to_drag in game.items_on_ground:
                            game.items_on_ground.remove(item_to_drag)
                        if item_to_drag.name in ["Campfire on", "Lantern on"]:
                            new_item = Item.create_from_name(item_to_drag.name.replace(" on", " off"))
                            if new_item:
                                new_item.durability = item_to_drag.durability
                                new_item.load = item_to_drag.load
                                new_item.rect.center = item_to_drag.rect.center
                                new_item.x = item_to_drag.x
                                new_item.y = item_to_drag.y
                                game.dragged_item = new_item
                                display_message(tr('msg', f"{item_to_drag.name.split(' ')[0]} extinguished when picked up."))
                elif type_orig == 'app':
                    game.app_state['slots'][i_orig] = None
                       
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
            modal_width = modal['rect'].width
            modal_height = modal['rect'].height
            clamped_x = max(0, min(new_x, GAME_WIDTH - modal_width))
            clamped_y = max(0, min(new_y, GAME_HEIGHT - modal_height))
            modal['position'] = (clamped_x, clamped_y)
            modal['rect'].topleft = modal['position']

            if hasattr(game, 'last_modal_positions'):
                game.last_modal_positions[modal['type']] = modal['position']