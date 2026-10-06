# core/events/mouse_context.py

import os
import pygame
import uuid
import math
import random
import re
import core.data.config
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
from core.entities.item.item_helpers import (
    does_allow_liquid, is_infinite_liquid_source, find_item_recursive, 
    has_app, get_container_available_liquid, is_container_on_player
)
from core.ui.crafting_common import (
    is_recipe_unlocked, has_recipe_ingredients, execute_recipe_craft, 
    get_recipe_status_details, is_recipe_relevant_to_item
)
from core.systems.utils import teleport_player_to_chunk as sys_teleport


_fuel_icon_cache = None

def get_fuel_icon():
    global _fuel_icon_cache
    if _fuel_icon_cache is not None:
        return _fuel_icon_cache
    icon_path = os.path.join(SPRITE_PATH, 'items', 'car_fuel_unit.png')
    if not os.path.exists(icon_path):
        icon_path = os.path.join(SPRITE_PATH, 'car_fuel_unit.png')
    if os.path.exists(icon_path):
        try:
            img = pygame.image.load(icon_path).convert_alpha()
            _fuel_icon_cache = pygame.transform.scale(img, (16, 16))
            return _fuel_icon_cache
        except Exception:
            pass
    return None

def is_fuel_item(item):
    if not item:
        return False
    return (
        item.name.lower() == "fuel unit" or 
        getattr(item, 'status_effect', None) == 'fuel' or 
        getattr(item, 'item_type', '') == 'car_fuel'
    )

def get_player_fuel_units(player):
    """Calculates total Fuel Units available in player inventory, belt, and worn containers."""
    if not player:
        return 0
    total = 0
    def scan(items):
        nonlocal total
        if not items:
            return
        item_iterable = items.values() if isinstance(items, dict) else items
        for it in item_iterable:
            if not it:
                continue
            if is_fuel_item(it):
                total += int(getattr(it, 'load', 1) or 1)
            if hasattr(it, 'inventory') and it.inventory:
                scan(it.inventory)

    scan(getattr(player, 'inventory', []))
    scan(getattr(player, 'belt', []))
    if hasattr(player, 'clothes'):
        scan(player.clothes)
    return total

def consume_player_fuel_units(player, amount_needed):
    """Consumes the specified amount of Fuel Units from player inventory/belt."""
    if not player or amount_needed <= 0:
        return True

    remaining = amount_needed
    items_to_modify = []

    def scan(items, ctype):
        if not items:
            return
        if ctype == 'dict':
            for k in list(items.keys()):
                it = items[k]
                if not it:
                    continue
                if is_fuel_item(it):
                    items_to_modify.append((items, k, it, 'dict'))
                if hasattr(it, 'inventory') and it.inventory:
                    scan(it.inventory, 'list')
        else:
            for idx in range(len(items) - 1, -1, -1):
                it = items[idx]
                if not it:
                    continue
                if is_fuel_item(it):
                    items_to_modify.append((items, idx, it, 'list'))
                if hasattr(it, 'inventory') and it.inventory:
                    scan(it.inventory, 'list')

    scan(getattr(player, 'inventory', []), 'list')
    scan(getattr(player, 'belt', []), 'list')
    if hasattr(player, 'clothes'):
        scan(player.clothes, 'dict')

    for container, key, it, ctype in items_to_modify:
        if remaining <= 0:
            break
        current_load = int(getattr(it, 'load', 1) or 1)
        take = min(remaining, current_load)
        remaining -= take

        if hasattr(it, 'load') and it.load is not None and it.is_stackable():
            it.load -= take
            if it.load <= 0:
                if container is getattr(player, 'belt', None):
                    container[key] = None
                    it.in_belt = False
                elif ctype == 'list':
                    if it in container:
                        container.remove(it)
                    elif isinstance(key, int) and key < len(container):
                        container.pop(key)
                elif ctype == 'dict':
                    container[key] = None
        else:
            if container is getattr(player, 'belt', None):
                container[key] = None
                it.in_belt = False
            elif ctype == 'list':
                if it in container:
                    container.remove(it)
                elif isinstance(key, int) and key < len(container):
                    container.pop(key)
            elif ctype == 'dict':
                container[key] = None

    return remaining <= 0

def calculate_boat_fuel_cost(game, dest_gx, dest_gy):
    gen = getattr(game, 'generator', None)
    lobby_chunk = getattr(gen, 'lobby_chunk', None) if gen else None

    if lobby_chunk and (dest_gx, dest_gy) == lobby_chunk:
        cur_map = getattr(game.map_manager, 'current_map_filename', '')
        match = re.match(r'map_L\d+_(\d+)_(\d+)_map\.csv', cur_map)
        if match:
            cur_gx, cur_gy = int(match.group(1)), int(match.group(2))
            return max(5, (abs(cur_gx) + abs(cur_gy)) * 5)
        return 5

    return max(5, (abs(dest_gx) + abs(dest_gy)) * 5)

def _is_barricade_item(it):
    if not it:
        return False
    b_health = getattr(it, 'barricade_health', None)
    if b_health is not None and b_health > 0:
        return True
    return 'barricade' in getattr(it, 'name', '').lower()

def teleport_player_to_chunk(game, dest_gx, dest_gy, dest_layer=1):
    sys_teleport(game, dest_gx, dest_gy, dest_layer)

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

            def remove_from_source(target_item):
                if source == 'inventory':
                    if 0 <= index < len(game.player.inventory) and game.player.inventory[index] == target_item:
                        return game.player.inventory.pop(index)
                    if target_item in game.player.inventory:
                        game.player.inventory.remove(target_item)
                        return target_item
                elif source == 'belt':
                    if 0 <= index < len(game.player.belt) and game.player.belt[index] == target_item:
                        game.player.belt[index] = None
                        target_item.in_belt = False
                        return target_item
                elif source == 'gear':
                    item_found = game.player.clothes.get(index)
                    if item_found == target_item:
                        game.player.clothes[index] = None
                        return target_item
                elif source in ('container', 'nearby') and container_item:
                    if 0 <= index < len(container_item.inventory) and container_item.inventory[index] == target_item:
                        removed = container_item.inventory.pop(index)
                        if getattr(container_item, 'item_type', '') == 'ground' and target_item in game.items_on_ground:
                            try: game.items_on_ground.remove(target_item)
                            except ValueError: pass
                        return removed
                    if target_item in container_item.inventory:
                        container_item.inventory.remove(target_item)
                        return target_item
                elif source == 'ground':
                    if 0 <= index < len(game.items_on_ground) and game.items_on_ground[index] == target_item:
                        return game.items_on_ground.pop(index)
                    if target_item in game.items_on_ground:
                        game.items_on_ground.remove(target_item)
                        return target_item
                return None

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
                elif source in ('container', 'nearby') and container_item and 0 <= index < len(container_item.inventory):
                    verified_item = container_item.inventory[index]
                elif source == 'npc':
                    verified_item = item if item in game.npcs else None
                elif source == 'container_map': 
                    if getattr(item, 'item_type', '') == 'vehicle':
                        verified_item = item 
                    elif container_item: 
                        verified_item = container_item.inventory[index] if 0 <= index < len(container_item.inventory) else None
                    else:
                        verified_item = item
                elif source in ('player_self', 'map_tile', 'vehicle_equipment', 'vehicle_slot', 'light_source'):
                    verified_item = item
                
                is_match = False
                if verified_item is item or isinstance(item, dict):
                    is_match = True
                elif verified_item and hasattr(verified_item, 'id') and hasattr(item, 'id') and verified_item.id == item.id:
                    item = verified_item
                    game.context_menu['item'] = verified_item
                    is_match = True
                elif verified_item and hasattr(verified_item, 'name') and hasattr(item, 'name') and verified_item.name == item.name:
                    item = verified_item
                    game.context_menu['item'] = verified_item
                    is_match = True

                if not is_match:
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

            # ==========================================
            # --- EQUIP OPTION WITH SUBMENU TARGETS ---
            # ==========================================
            elif option == 'Equip':
                target_slot = target_sub_slot

                # Branch A: Equip directly into a chosen Belt slot (belt_0 ... belt_4)
                if target_slot and target_slot.startswith('belt_'):
                    try:
                        bi = int(target_slot.split('_')[1])
                        item_from_src = remove_from_source(item)
                        if item_from_src:
                            old_item = game.player.belt[bi]
                            game.player.belt[bi] = item_from_src
                            item_from_src.in_belt = True

                            if str(getattr(item_from_src, 'item_type', '')).startswith('weapon'):
                                game.player.active_weapon = item_from_src

                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('equip_belt.ogg', subdir='items', game=game, source_pos=game.player.rect.center, is_critical=True)

                            if old_item:
                                old_item.in_belt = False
                                if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    game.player.inventory.append(old_item)
                                    if hasattr(game.player, 'stack_item_in_inventory'):
                                        game.player.stack_item_in_inventory(old_item)
                                else:
                                    old_item.rect.center = game.player.rect.center
                                    game.items_on_ground.append(old_item)

                            display_message(f"{tr('msg', 'Equipped')} {tr('item', item_from_src.name)} {tr('msg', 'to belt slot')} {bi+1}.")
                    except Exception as e:
                        print(f"Error equipping to belt: {e}")

                # Branch B: Equip to a specific Gear / Clothing slot (head, body, util, util2, etc.)
                elif target_slot:
                    slot_name = target_slot
                    if slot_name == 'hand': slot_name = 'hands'
                    item_from_src = remove_from_source(item)
                    if item_from_src:
                        old_item = game.player.clothes.get(slot_name)
                        game.player.clothes[slot_name] = item_from_src

                        if hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound('equip_gear.ogg', subdir='items', game=game, source_pos=game.player.rect.center, is_critical=True)

                        if old_item:
                            if getattr(old_item, 'liquid', False):
                                old_item.rect.center = game.player.rect.center
                                game.items_on_ground.append(old_item)
                            elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(old_item)
                            else:
                                old_item.rect.center = game.player.rect.center
                                game.items_on_ground.append(old_item)

                        display_message(f"{tr('msg', 'Equipped')} {tr('item', item_from_src.name)} {tr('msg', 'to')} {tr('ui', slot_name.capitalize())}.")

                # Branch C: Fallback when clicked without submenu selection
                else:
                    item_type = getattr(item, 'item_type', '') or ''
                    if item_type in ('cloth', 'container'):
                        target_s = getattr(item, 'slot', None)
                        if target_s == 'hand': target_s = 'hands'
                        if target_s == 'util' or not target_s:
                            target_s = next((s for s in ['util', 'util2', 'util3'] if game.player.clothes.get(s) is None), 'util')
                        item_from_src = remove_from_source(item)
                        if item_from_src:
                            old_item = game.player.clothes.get(target_s)
                            game.player.clothes[target_s] = item_from_src
                            if old_item:
                                game.player.inventory.append(old_item)
                    else:
                        game.player.equip_item_to_belt(item, source, index, container_item)

                clicked_on_menu = True

            # ==========================================
            # --- SEND TO OPTION WITH SUBMENU TARGETS ---
            # ==========================================
            elif option == 'Send to':
                target_dest = target_sub_slot
                is_external = (
                    source in ['nearby', 'ground', 'container_map'] 
                    or (source == 'container' and container_item and not is_container_on_player(container_item, game.player))
                )

                # 1. Send to Player Inventory
                if target_dest == 'Inventory':
                    if source == 'inventory':
                        game.context_menu['active'] = False
                        return

                    if getattr(item, 'liquid', False):
                        display_message(tr('msg', "Liquid spills without a proper container."))
                        game.context_menu['active'] = False
                        return

                    def do_send_inv():
                        removed = remove_from_source(item)
                        if removed:
                            removed.is_placed = False
                            game.player.inventory.append(removed)
                            if hasattr(game.player, 'stack_item_in_inventory'):
                                game.player.stack_item_in_inventory(removed)
                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
                            display_message(f"{tr('msg', 'Sent')} {tr('item', removed.name)} {tr('msg', 'to inventory.')}")

                    transfer_time = max(0.1, item.get_total_weight() * 0.2)
                    if is_external:
                        game.player.start_action(tr('msg', "Looting"), transfer_time, do_send_inv, xp_reward=0.5)
                    else:
                        do_send_inv()

                # 2. Send to Belt
                elif target_dest == 'Belt':
                    if source == 'belt':
                        game.context_menu['active'] = False
                        return

                    empty_idx = next((bi for bi, b in enumerate(game.player.belt) if b is None), None)
                    if empty_idx is not None:
                        removed = remove_from_source(item)
                        if removed:
                            removed.in_belt = True
                            game.player.belt[empty_idx] = removed
                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('equip_belt.ogg', subdir='items', game=game, source_pos=game.player.rect.center, is_critical=True)
                            display_message(f"{tr('msg', 'Sent')} {tr('item', removed.name)} {tr('msg', 'to belt slot')} {empty_idx+1}.")
                    else:
                        display_message(tr('msg', "Belt is full."))

                # 3. Send to Container / Vessel / Trunk
                else:
                    target_container = None
                    search_pools = [
                        [b for b in game.player.belt if b and hasattr(b, 'inventory')],
                        [it for it in game.player.inventory if it and hasattr(it, 'inventory')],
                        [c for c in game.player.clothes.values() if c and hasattr(c, 'inventory')],
                        [m.get('item') for m in game.modals if m.get('type') == 'container' and m.get('item')],
                        [m.get('vehicle') for m in game.modals if m.get('type') == 'vehicle' and m.get('vehicle')],
                        game.find_nearby_containers()
                    ]
                    for pool in search_pools:
                        for c in pool:
                            if c and (str(getattr(c, 'id', '')) == target_dest or getattr(c, 'name', '') == target_dest):
                                target_container = c
                                break
                        if target_container:
                            break

                    if target_container and hasattr(target_container, 'inventory'):
                        # Enforce container state checks
                        if getattr(target_container, 'item_type', '') == 'maptile_container' and not getattr(target_container, 'is_opened', False):
                            display_message(tr('msg', "Cannot send items into a closed container."))
                            game.context_menu['active'] = False
                            return

                        c_cap = getattr(target_container, 'capacity', 0)
                        if c_cap is None or c_cap <= 0:
                            display_message(tr('msg', "Target has no inventory capacity."))
                            game.context_menu['active'] = False
                            return

                        def do_send_cont():
                            is_liquid = getattr(item, 'liquid', False)
                            total_load = getattr(item, 'load', 1)
                            if total_load is None: total_load = 1

                            # A. Handle Liquid Transfer with strict max_liquid clamping
                            if is_liquid:
                                avail_liquid = get_container_available_liquid(target_container)
                                if avail_liquid <= 0:
                                    display_message(tr('msg', "Container is full of liquid."))
                                    return

                                transfer_units = min(total_load, avail_liquid)
                                target_max_l = getattr(target_container, 'max_liquid', transfer_units) or transfer_units

                                # Stack into existing liquid unit in target container if present
                                stacked = False
                                for inv_it in target_container.inventory:
                                    if getattr(inv_it, 'liquid', False) and inv_it.name == item.name:
                                        inv_it.load = (getattr(inv_it, 'load', 0) or 0) + transfer_units
                                        inv_it.capacity = target_max_l
                                        stacked = True
                                        break

                                # Or add as new liquid item
                                if not stacked:
                                    if len(target_container.inventory) >= c_cap:
                                        display_message(tr('msg', "Container is full."))
                                        return
                                    new_liq = Item.create_from_name(item.name)
                                    if new_liq:
                                        new_liq.load = transfer_units
                                        new_liq.capacity = target_max_l
                                        target_container.inventory.append(new_liq)

                                # Deduct transferred amount from source
                                if transfer_units >= total_load:
                                    remove_from_source(item)
                                else:
                                    item.load -= transfer_units

                                if hasattr(game, 'sound_manager'):
                                    game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
                                display_message(f"{tr('msg', 'Transferred')} {int(transfer_units)} {tr('item', item.name)} {tr('msg', 'into')} {target_container.name}.")
                                return

                            # B. Handle Regular Stackable / Single Item Transfer
                            qty_to_send = total_load
                            stacked = False

                            if getattr(item, 'is_stackable', lambda: False)():
                                for inv_it in target_container.inventory:
                                    if hasattr(inv_it, 'can_stack_with') and inv_it.can_stack_with(item):
                                        i_cap = getattr(inv_it, 'capacity', 100) or 100
                                        i_load = getattr(inv_it, 'load', 1) or 1
                                        avail = max(0, i_cap - i_load)
                                        trans = min(avail, qty_to_send)
                                        if trans > 0:
                                            inv_it.load = i_load + trans
                                            qty_to_send -= trans
                                            stacked = True
                                        if qty_to_send <= 0:
                                            break

                            # If transferring leftover stack or new item into a slot
                            if qty_to_send > 0:
                                if len(target_container.inventory) < c_cap:
                                    if qty_to_send < total_load:
                                        # Split stack
                                        new_it = Item.create_from_name(item.name)
                                        if new_it:
                                            new_it.load = qty_to_send
                                            target_container.inventory.append(new_it)
                                            item.load -= qty_to_send
                                    else:
                                        # Whole item transferred
                                        removed = remove_from_source(item)
                                        if removed:
                                            target_container.inventory.append(removed)
                                else:
                                    if not stacked:
                                        display_message(tr('msg', "Container is full."))
                                        return
                                    else:
                                        item.load = qty_to_send

                            elif stacked:
                                remove_from_source(item)

                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
                            display_message(f"{tr('msg', 'Sent to')} {target_container.name}.")

                        transfer_time = max(0.1, item.get_total_weight() * 0.2)
                        if is_external:
                            game.player.start_action(f"Transferring to {target_container.name}", transfer_time, do_send_cont, xp_reward=0.5)
                        else:
                            do_send_cont()

                clicked_on_menu = True

            elif option == 'Place barricade':
                if source == 'map_tile' and isinstance(item, dict):
                    gx = item['grid_x']
                    gy = item['grid_y']

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
                                    for i_idx in range(len(it_list)):
                                        it = it_list[i_idx]
                                        if it and req_name.lower() in it.name.lower():
                                            if hasattr(it, 'is_stackable') and it.is_stackable() and it.load:
                                                take = min(left, it.load)
                                                it.load -= take
                                                left -= take
                                                if it.load <= 0:
                                                    it_list[i_idx] = None
                                            else:
                                                it_list[i_idx] = None
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

            elif option == 'Travel to':
                if target_sub_slot:
                    try:
                        dest_gx, dest_gy = map(int, target_sub_slot.split('_'))
                        fuel_cost = calculate_boat_fuel_cost(game, dest_gx, dest_gy)
                        player_fuel = get_player_fuel_units(game.player)

                        if player_fuel < fuel_cost:
                            fuel_name = tr('item', "Fuel Unit")
                            display_message(f"{tr('msg', 'Not enough fuel! Need')} {fuel_cost}x {fuel_name} {tr('msg', 'to travel.')}")
                        else:
                            consume_player_fuel_units(game.player, fuel_cost)
                            fuel_name = tr('item', "Fuel Unit")
                            display_message(f"{tr('msg', 'Used')} {fuel_cost}x {fuel_name}.")
                            teleport_player_to_chunk(game, dest_gx, dest_gy)
                    except Exception as e:
                        print(f"Error traveling: {e}")
                clicked_on_menu = True

            elif option == 'Vehicle options' and getattr(item, 'item_type', '') == 'vehicle':
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
                    if hasattr(item, 'has_key_access') and not item.has_key_access(game.player):
                        display_message(tr('msg', "Vehicle trunk is locked! Requires vehicle key."))
                        if 'fail' in getattr(item, 'sounds', {}):
                            game.sound_manager.play_sound(
                                item.sounds['fail'],
                                subdir='vehicles',
                                game=game,
                                source_pos=item.rect.center,
                                base_volume=0.5,
                                is_critical=True
                            )
                        game.context_menu['active'] = False
                        return

                    grid_x = int(item.x // TILE_SIZE)
                    grid_y = int(item.y // TILE_SIZE)
                    if hasattr(game.map_manager, 'remove_vehicle_tile'):
                        game.map_manager.remove_vehicle_tile(grid_x, grid_y)

                modal_exists = any(m['type'] == 'container' and m['item'] == item for m in game.modals)
                if not modal_exists:
                    new_container_modal = {
                        'id': uuid.uuid4(),
                        'type': 'container',
                        'item': item,
                        'position': game.last_modal_positions['container'],
                        'is_dragging': False,
                        'drag_offset': (0, 0),
                        'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT)
                    }
                    game.modals.append(new_container_modal)
                clicked_on_menu = True

            elif option == 'Status': toggle_status_modal(game)
            elif option == 'Inventory': toggle_inventory_modal(game)
            elif option == 'Gear': toggle_gear_modal(game)
                    
            elif option in ['Open door/window', 'Close door/window']:
                if source == 'map_tile' and isinstance(item, dict) and 'grid_x' in item and 'grid_y' in item:
                    game.map_manager.toggle_door_state(item['grid_x'], item['grid_y'])
                clicked_on_menu = True

            elif option == 'Toggle Light':
                if source == 'light_source':
                    item['active'] = not item['active']
                clicked_on_menu = True

            elif option == 'Use': game.player.consume_item(item, source, index, container_item)

            elif option == 'Reload':
                if getattr(item, 'item_type', None) in ['utility', 'mobile']:
                    game.player.reload_utility_item(item, source, index, container_item)
                else:
                    game.player.reload_active_weapon(game=game)
            
            elif option == 'Get bullets': game.player.unload_weapon(game, item)
            elif option == 'Turn on' or option == 'Turn off':
                is_mobile = (getattr(item, 'item_type', '') == 'mobile' or 'Mobile' in getattr(item, 'name', ''))
                result = game.player.toggle_utility_item(item, source, index, container_item)
                if is_mobile:
                    game.modals = [m for m in game.modals if m.get('type') != 'mobile']
                if source == 'ground' and result and hasattr(result, 'name'):
                    if index is not None and 0 <= index < len(game.items_on_ground):
                        game.items_on_ground[index] = result
                elif source == 'nearby' and container_item and result and hasattr(result, 'name'):
                    if getattr(container_item, 'item_type', '') == 'ground':
                        for i_idx, ground_item in enumerate(game.items_on_ground):
                            if ground_item is item:
                                game.items_on_ground[i_idx] = result
                                break

            elif option == 'Drop one':
                if getattr(item, 'liquid', False):
                    has_load = hasattr(item, 'load') and item.load is not None
                    if has_load and item.load > 1:
                        item.load -= 1
                        display_message(f"{tr('msg', 'A portion of')} {tr('item', item.name)} {tr('msg', 'spills.')}")
                    else:
                        remove_from_source(item)
                        display_message(f"{tr('item', item.name)} {tr('msg', 'spills on the ground.')}")
                    
                    if hasattr(game, 'splashes'):
                        game.splashes.append({
                            'pos': (game.player.rect.centerx, game.player.rect.bottom),
                            'time': pygame.time.get_ticks(),
                            'duration': 350,
                            'radius': 3,
                            'type': 'hit_puff'
                        })
                    if container_item and getattr(game, 'is_client', False) and getattr(game, 'client', None):
                        from core.server.network import NetMsg, send_msg
                        send_msg(game.client.socket, {
                            'type': NetMsg.WORLD_ACTION, 'action': 'container_sync',
                            'x': container_item.rect.x, 'y': container_item.rect.y,
                            'is_opened': getattr(container_item, 'is_opened', True),
                            'inventory': [it.to_dict() for it in container_item.inventory]
                        })
                else:
                    game.player.drop_item_stack(game, source, index, container_item, 1)
                clicked_on_menu = True

            elif option == 'Drop all':
                if getattr(item, 'liquid', False):
                    remove_from_source(item)
                    display_message(f"{tr('msg', 'All of the')} {tr('item', item.name)} {tr('msg', 'spills on the ground.')}")
                    if hasattr(game, 'splashes'):
                        game.splashes.append({
                            'pos': (game.player.rect.centerx, game.player.rect.bottom),
                            'time': pygame.time.get_ticks(),
                            'duration': 350,
                            'radius': 5,
                            'type': 'hit_puff'
                        })
                    if container_item and getattr(game, 'is_client', False) and getattr(game, 'client', None):
                        from core.server.network import NetMsg, send_msg
                        send_msg(game.client.socket, {
                            'type': NetMsg.WORLD_ACTION, 'action': 'container_sync',
                            'x': container_item.rect.x, 'y': container_item.rect.y,
                            'is_opened': getattr(container_item, 'is_opened', True),
                            'inventory': [it.to_dict() for it in container_item.inventory]
                        })
                else:
                    game.player.drop_item_stack(game, source, index, container_item, 'all')
                clicked_on_menu = True
            
            elif option == 'Place':
                if getattr(item, 'liquid', False):
                    display_message(tr('msg', "Cannot place liquid directly."))
                    game.context_menu['active'] = False
                    return
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
                    remove_from_source(item)
                    display_message(f"{tr('item', item.name)} {tr('msg', 'spills on the ground.')}")
                    if hasattr(game, 'splashes'):
                        game.splashes.append({
                            'pos': (game.player.rect.centerx, game.player.rect.bottom),
                            'time': pygame.time.get_ticks(),
                            'duration': 350,
                            'radius': 4,
                            'type': 'hit_puff'
                        })
                    if container_item and getattr(game, 'is_client', False) and getattr(game, 'client', None):
                        from core.server.network import NetMsg, send_msg
                        send_msg(game.client.socket, {
                            'type': NetMsg.WORLD_ACTION, 'action': 'container_sync',
                            'x': container_item.rect.x, 'y': container_item.rect.y,
                            'is_opened': getattr(container_item, 'is_opened', True),
                            'inventory': [it.to_dict() for it in container_item.inventory]
                        })
                else:
                    if source == 'gear':
                        slot_name = index 
                        item_to_drop = game.player.clothes.get(slot_name)
                        if item_to_drop and item_to_drop == item:
                            game.player.drop_item(game, source, index, container_item)
                    else:
                        game.player.drop_item(game, source, index, container_item)
                clicked_on_menu = True

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

                elif getattr(item, 'inventory', None) is not None:
                    is_closed_maptile = getattr(item, 'item_type', '') == 'maptile_container' and not getattr(item, 'is_opened', False)

                    if getattr(item, 'is_opening', False):
                        display_message(tr('msg', "Someone is already opening this container."))
                        game.context_menu['active'] = False
                        return

                    def open_and_show_modal():
                        if hasattr(item, 'open'):
                            item.open(game)
                        else:
                            item.is_opened = True

                        nearby_modal = next((m for m in game.modals if m['type'] == 'nearby'), None)
                        is_nearby_tab = False
                        if source != 'nearby' and nearby_modal and 'tabs_data' in nearby_modal:
                            for tab in nearby_modal['tabs_data']:
                                if tab.get('container') == item:
                                    is_nearby_tab = True
                                    nearby_modal['active_tab'] = tab['label']
                                    game.modals.remove(nearby_modal)
                                    game.modals.append(nearby_modal)
                                    break

                        if not is_nearby_tab:
                            modal_exists = any(m['type'] == 'container' and m.get('item') == item for m in game.modals)
                            if not modal_exists:
                                slots_modal = next((m for m in game.modals if m.get('type') == 'slots'), None)
                                if slots_modal and 'rect' in slots_modal:
                                    slots_pos = (slots_modal['rect'].x, slots_modal['rect'].y)
                                else:
                                    slots_pos = getattr(game, 'last_modal_positions', {}).get(
                                        'slots', (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT)
                                    )
                                target_pos = (slots_pos[0], max(0, slots_pos[1] - CONTAINER_MODAL_HEIGHT))
                                game.last_modal_positions['container'] = target_pos

                                new_container_modal = {
                                    'id': uuid.uuid4(),
                                    'type': 'container',
                                    'item': item,
                                    'position': target_pos,
                                    'is_dragging': False,
                                    'drag_offset': (0, 0),
                                    'rect': pygame.Rect(target_pos[0], target_pos[1], CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT)
                                }
                                game.modals.append(new_container_modal)
                            else:
                                existing = next((m for m in game.modals if m['type'] == 'container' and m.get('item') == item), None)
                                if existing:
                                    game.modals.remove(existing)
                                    game.modals.append(existing)

                    if is_closed_maptile:
                        if getattr(core.data.config, 'ALL_VISIBLE', False) or has_app(game, 'open_container_instant'):
                            open_and_show_modal()
                        else:
                            agility = game.player.progression.get_level('agility')
                            open_time = max(0.2, 1.8 - (agility * 0.2))

                            item.is_opening = True
                            if getattr(game, 'is_client', False):
                                from core.server.network import NetMsg, send_msg
                                send_msg(game.client.socket, {
                                    'type': NetMsg.WORLD_ACTION, 
                                    'action': 'lock_container', 
                                    'x': item.rect.x, 'y': item.rect.y
                                })
                            
                            def cancel_open():
                                item.is_opening = False

                            game.player.start_action(f"{game.player.name} {tr('ui', 'Opening')}", open_time, open_and_show_modal, xp_reward=1.5, cancel_on_move=True, on_cancel=cancel_open)
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
                        if hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
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
                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
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
                            new_item = Item.create_from_name(item_to_grab.name.replace(" on", " off"))
                            if new_item:
                                new_item.durability = item_to_grab.durability
                                new_item.load = item_to_grab.load
                                new_item.rect.center = item_to_grab.rect.center
                                new_item.x = item_to_grab.x
                                new_item.y = item_to_grab.y
                                item_to_grab = new_item
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
                            new_item = Item.create_from_name(item_to_grab.name)
                            if new_item:
                                new_item.load = amount
                                if hasattr(item_to_grab, 'durability'):
                                    new_item.durability = item_to_grab.durability
                                item_to_grab.load -= amount
                                target_inventory.append(new_item)
                                game.player.stack_item_in_inventory(new_item)

                                if hasattr(game, 'sound_manager'):
                                    game.sound_manager.play_sound(
                                        'grab.ogg', subdir='items', game=game,
                                        source_pos=game.player.rect.center, base_volume=0.5, is_critical=True
                                    )
                            return

                        if source == 'ground' and item in game.items_on_ground:
                            game.items_on_ground.remove(item)
                            grabbed = True
                        elif source in ('nearby', 'container') and container_item and item in container_item.inventory:
                            container_item.inventory.remove(item)
                            if getattr(container_item, 'item_type', '') == 'ground' and item in game.items_on_ground:
                                game.items_on_ground.remove(item)
                            grabbed = True

                        if grabbed:
                            item_to_grab.is_placed = False
                            target_inventory.append(item_to_grab)
                            game.player.stack_item_in_inventory(item_to_grab)

                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound(
                                    'grab.ogg', subdir='items', game=game,
                                    source_pos=game.player.rect.center, base_volume=0.5, is_critical=True
                                )

                            if getattr(game, 'is_client', False) and getattr(game, 'client', None):
                                from core.server.network import NetMsg, send_msg
                                if source == 'ground':
                                    send_msg(game.client.socket, {
                                        'type': NetMsg.WORLD_ACTION, 'action': 'pickup', 'id': getattr(item, 'id', None)
                                    })
                                elif container_item:
                                    send_msg(game.client.socket, {
                                        'type': NetMsg.WORLD_ACTION, 'action': 'container_sync',
                                        'x': container_item.rect.x, 'y': container_item.rect.y,
                                        'is_opened': getattr(container_item, 'is_opened', True),
                                        'inventory': [it.to_dict() for it in container_item.inventory]
                                    })

                    if source == 'nearby':
                        grab_weight = item.get_total_weight() * weight_multiplier
                        grab_time = max(0.1, grab_weight * 0.2)
                        game.player.start_action(tr('msg', "Looting"), grab_time, do_grab, xp_reward=0.5)
                    else:
                        do_grab()
                else:
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
    click_modal_type = None

    is_over_any_modal = any(modal.get('rect') and modal['rect'].collidepoint(mouse_pos) for modal in game.modals)

    for modal in reversed(game.modals):
        if not modal['rect'].collidepoint(mouse_pos): continue

        if modal['type'] == 'inventory':
            if modal.get('active_tab', 'Inventory') == 'Inventory':
                for i, item in enumerate(game.player.inventory):
                    if item and get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                        clicked_item, click_source, click_index = item, 'inventory', i
                        click_modal_type = 'inventory'
                        break
            
            elif modal.get('active_tab') in modal.get('container_mapping', {}):
                container = modal['container_mapping'][modal['active_tab']]
                if container:
                    pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                    for i, item in enumerate(container.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            clicked_item, click_source, click_index = item, 'container', i
                            click_container_item = container
                            click_modal_type = 'inventory'
                            break
                            
            elif modal.get('active_tab') == 'Gear':
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            item = game.player.clothes.get(slot_name)
                            if item:
                                clicked_item, click_source, click_index = item, 'gear', slot_name
                                click_modal_type = 'inventory'
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
                                click_modal_type = 'gear'
                                break
            elif active_tab in modal.get('container_mapping', {}):
                container = modal['container_mapping'][active_tab]
                if container:
                    pos_for_calc = (modal['rect'].x, modal['rect'].y + 40)
                    for i, item in enumerate(container.inventory):
                        if item and get_container_slot_rect(pos_for_calc, i).collidepoint(mouse_pos):
                            clicked_item, click_source, click_index, click_container_item = item, 'container', i, container
                            click_modal_type = 'gear'
                            break

        elif modal['type'] == 'container':
            container = modal['item']
            for i, item in enumerate(container.inventory):
                if item and get_container_slot_rect(modal['position'], i).collidepoint(mouse_pos):
                    clicked_item, click_source, click_index, click_container_item = item, 'container', i, container
                    click_modal_type = 'container'
                    break
        
        elif modal['type'] == 'slots':
            for slot_data in modal.get('slot_rects', []):
                if slot_data['rect'].collidepoint(mouse_pos):
                    c = slot_data['container']
                    i = slot_data['index']
                    if i < len(c.inventory):
                        clicked_item, click_source, click_index, click_container_item = c.inventory[i], 'container', i, c
                        click_modal_type = 'slots'
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
                is_closed = (getattr(active_container, 'item_type', '') == 'maptile_container' and not getattr(active_container, 'is_opened', False))
                if not is_closed:
                    pos = content_rect.topleft
                    for i, item in enumerate(active_container.inventory):
                        if item and get_container_slot_rect(pos, i).collidepoint(mouse_pos):
                            clicked_item, click_source, click_index, click_container_item = item, 'nearby', i, active_container
                            click_modal_type = 'nearby'
                            break
        
        if clicked_item: break

    if not clicked_item and not is_over_any_modal:
        for i, item in enumerate(game.player.belt):
            if item and get_belt_hud_slot_rect(i, game=game).collidepoint(mouse_pos):
                clicked_item = item
                click_source = 'belt'
                click_index = i
                click_modal_type = 'belt'
                break

    if not clicked_item and not is_over_any_modal:
        adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
        world_pos = game.screen_to_world(adjusted_mouse_pos)

        max_interact_dist_sq = (TILE_SIZE * 2.5) ** 2
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
                    click_modal_type = 'ground'
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
            for npc in game.npcs:
                if npc.rect.collidepoint(world_pos) and npc.is_friendly and npc.aggro_timer <= 0:
                    clicked_item = npc
                    click_source = 'npc'
                    click_index = 0
                    break

        if not clicked_item:
            grid_x = int(world_pos[0] // TILE_SIZE)
            grid_y = int(world_pos[1] // TILE_SIZE)
            tile = game.map_manager.get_tile_at(grid_x, grid_y)

            tile_cx = (grid_x + 0.5) * TILE_SIZE
            tile_cy = (grid_y + 0.5) * TILE_SIZE
            dx = game.player.rect.centerx - tile_cx
            dy = game.player.rect.centery - tile_cy
            dist_sq = dx*dx + dy*dy

            if tile:
                char = ""
                try: char = game.map_data[grid_y][grid_x]
                except: pass
                
                is_boat = (
                    tile.get('type') == "maptile_teleport" or 
                    tile.get('name') in ("tp_boat", "teleport_boat") or 
                    char in ("tp_boat", "teleport_boat") or
                    'boat' in str(tile.get('name', '')).lower()
                )
                
                is_door_window = (
                    tile.get('is_statable') or 
                    '_open' in char.lower() or 
                    '_close' in char.lower() or 
                    '_broke' in char.lower() or
                    'door' in char.lower() or 
                    'window' in char.lower() or
                    (tile.get('name') and ('door' in tile['name'].lower() or 'window' in tile['name'].lower()))
                )

                max_interact_sq = (TILE_SIZE * 2.8) ** 2

                if is_boat or is_door_window or tile.get('type') == "maptile_car":
                    if dist_sq <= max_interact_sq:
                        if tile.get('type') == "maptile_car":
                            vehicle = game.map_manager.get_vehicle_at(grid_x, grid_y)
                            if vehicle:
                                clicked_item = vehicle
                                click_source = 'container_map'
                                click_index = 0

                        elif is_boat:
                            clicked_item = {
                                'name': tile.get('name', 'Boat'), 
                                'type': 'maptile_teleport', 
                                'grid_x': grid_x, 
                                'grid_y': grid_y, 
                                'char': char
                            }
                            click_source = 'map_tile'

                        elif is_door_window:
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
                        display_message(tr('msg', "Too far away to interact."))

    if not clicked_item:
        adjusted_mouse_pos = (mouse_pos[0] - game.viewport_left_offset, mouse_pos[1])
        world_pos = game.screen_to_world(adjusted_mouse_pos)
        for light in game.map_lights:
            if light['rect'].collidepoint(world_pos):
                clicked_item = light
                click_source = 'light_source'
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

        options = []

        if click_source == 'npc':
            dx = game.player.rect.centerx - clicked_item.rect.centerx
            dy = game.player.rect.centery - clicked_item.rect.centery
            dist_sq = dx*dx + dy*dy
            max_dist_px = TILE_SIZE * 3
            if dist_sq <= max_dist_px ** 2:
                if clicked_item.is_friendly and clicked_item.aggro_timer <= 0:
                    options.append('Talk')
                    if hasattr(clicked_item, 'stop_moving'):
                        clicked_item.stop_moving()
            else:
                display_message(tr('msg', "Too far to talk to them."))

        elif click_source == 'map_tile':
            options = []
            gx = clicked_item['grid_x']
            gy = clicked_item['grid_y']
            char = clicked_item.get('char', '')
            t_def = game.map_manager.get_tile_at(gx, gy)

            if clicked_item.get('type') == 'maptile_teleport':
                cur_map = game.map_manager.current_map_filename
                match = re.match(r'map_L\d+_(\d+)_(\d+)_map\.csv', cur_map)
                cur_gx, cur_gy = (int(match.group(1)), int(match.group(2))) if match else (None, None)

                gen = getattr(game, 'generator', None)
                active_chunks = set()
                lobby_chunk = None
                military_chunk = None
                isolated_islands = set()

                if gen:
                    active_chunks = getattr(gen, 'active_chunks', set())
                    lobby_chunk = getattr(gen, 'lobby_chunk', None)
                    military_chunk = getattr(gen, 'military_chunk', None)
                    isolated_islands = getattr(gen, 'isolated_island_chunks', set())

                owned_maps = set()
                def check_inventory_for_maps(inv):
                    for it in inv:
                        if not it: continue
                        if it.name.startswith("Cartography for "):
                            chunk_str = it.name.replace("Cartography for ", "").strip()
                            owned_maps.add(chunk_str)
                        if hasattr(it, 'inventory') and it.inventory:
                            check_inventory_for_maps(it.inventory)

                if game.player:
                    check_inventory_for_maps(game.player.inventory)
                    check_inventory_for_maps(game.player.belt)
                    check_inventory_for_maps(game.player.clothes.values())

                sub_opts = []
                display_map = {}
                icon_map = {}
                extra_text_map = {}
                extra_color_map = {}
                tooltip_map = {}

                player_fuel = get_player_fuel_units(game.player)
                fuel_icon = get_fuel_icon()

                if lobby_chunk and (cur_gx, cur_gy) != lobby_chunk:
                    sub_key = f"{lobby_chunk[0]}_{lobby_chunk[1]}"
                    sub_opts.append(sub_key)
                    fuel_cost = calculate_boat_fuel_cost(game, lobby_chunk[0], lobby_chunk[1])
                    display_map[sub_key] = f"{tr('ui', 'Lobby (Safe Haven)')} - "
                    if fuel_icon: icon_map[sub_key] = fuel_icon
                    extra_text_map[sub_key] = f"{fuel_cost}"
                    extra_color_map[sub_key] = GREEN if player_fuel >= fuel_cost else RED
                    tooltip_map[sub_key] = (
                        f"{tr('ui', 'Destination:')} {tr('ui', 'Lobby')}\n"
                        f"{tr('ui', 'Fuel needed:')} {fuel_cost}\n"
                        f"{tr('ui', 'Available fuel:')} {player_fuel}"
                    )

                for (cgx, cgy) in sorted(list(active_chunks)):
                    sub_key = f"{cgx}_{cgy}"
                    if (cgx, cgy) == military_chunk: continue
                    if (cgx, cgy) == lobby_chunk: continue
                    if (cgx, cgy) == (cur_gx, cur_gy): continue
                    if sub_key not in owned_maps: continue

                    sub_opts.append(sub_key)
                    fuel_cost = calculate_boat_fuel_cost(game, cgx, cgy)
                    chunk_type_lbl = tr('ui', 'Island') if (cgx, cgy) in isolated_islands else tr('ui', 'Sector')
                    display_map[sub_key] = f"{chunk_type_lbl} ({cgx}, {cgy}) - "
                    if fuel_icon: icon_map[sub_key] = fuel_icon
                    extra_text_map[sub_key] = f"{fuel_cost}"
                    extra_color_map[sub_key] = GREEN if player_fuel >= fuel_cost else RED
                    tooltip_map[sub_key] = (
                        f"{tr('ui', 'Destination:')} {chunk_type_lbl} ({cgx}, {cgy})\n"
                        f"{tr('ui', 'Fuel needed:')} {fuel_cost}\n"
                        f"{tr('ui', 'Available fuel:')} {player_fuel}"
                    )

                if not sub_opts:
                    display_message(tr('msg', "You need Cartography maps to navigate further."))
                    game.context_menu['active'] = False
                    return

                options = [{
                    'label': 'Travel to', 
                    'sub': sub_opts, 
                    'display_names': display_map,
                    'icons': icon_map,
                    'extra_texts': extra_text_map,
                    'extra_colors': extra_color_map,
                    'tooltips': tooltip_map,
                    'extra_text_map': extra_text_map,
                    'extra_color_map': extra_color_map,
                    'tooltip_map': tooltip_map
                }]

            barricade = game.map_manager.get_barricade(gx, gy)

            if not barricade:
                tile_state = clicked_item.get('state')
                if not tile_state and t_def:
                    tile_state = t_def.get('state')
                if not tile_state:
                    if '_open' in char: tile_state = 'open'
                    elif '_close' in char: tile_state = 'close'

                if tile_state == 'close':
                    options.append('Open door/window')
                elif tile_state == 'open':
                    options.append('Close door/window')

            is_door_or_window = (
                'door' in char.lower() or 'window' in char.lower() or
                '_open' in char.lower() or '_close' in char.lower() or '_broke' in char.lower() or
                (t_def and (t_def.get('is_statable') or 'door' in str(t_def.get('name', '')).lower() or 'window' in str(t_def.get('name', '')).lower()))
            )

            if is_door_or_window:
                if barricade:
                    options.append('Remove barricade')
                    req_tools = barricade.get('remove_items', ['Crowbar', 'Hammer', 'Metal Hammer', 'Primitive Hammer', 'Picaxe'])
                    tt_lines = [tr('ui', "To remove barricade need:")]
                    tt_lines.append(f"- {', '.join(req_tools)}")
                    game.context_menu['tooltips']['Remove barricade'] = "\n".join(tt_lines)
                else:
                    options.append('Place barricade')

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

        is_maptile = False
        if isinstance(clicked_item, dict):
            if clicked_item.get('type') in ['maptile', 'maptile_container', 'map_tile', 'maptile_teleport']:
                is_maptile = True
        else:
            if getattr(clicked_item, 'type', None) in ['maptile', 'maptile_container', 'map_tile', 'maptile_teleport']:
                is_maptile = True
            if getattr(clicked_item, 'item_type', None) in ['maptile', 'maptile_container', 'map_tile', 'maptile_teleport']:
                is_maptile = True
                
        if click_source in ['container_map', 'map_tile']:
            is_maptile = True

        is_nearby = (click_modal_type == 'nearby') or (click_source == 'nearby')
        is_in_inv_or_gear_modal = click_modal_type in ('inventory', 'gear', 'belt')
        is_nested_in_player = (
            click_source == 'container' 
            and click_container_item 
            and (is_in_inv_or_gear_modal or click_modal_type == 'slots' or is_container_on_player(click_container_item, game.player))
        )
        is_player_item = is_in_inv_or_gear_modal or is_nested_in_player

        # --- BRANCHING: PRESERVE SPECIAL SOURCES FROM BEING CLEARED ---
        if click_source in ('map_tile', 'light_source', 'player_self', 'vehicle_equipment', 'vehicle_slot'):
            pass

        elif is_nearby:
            options = []
            if not isinstance(clicked_item, Corpse) and getattr(clicked_item, 'type', None) not in ('animal', 'zombie'):
                if not getattr(clicked_item, 'liquid', False):
                    if hasattr(clicked_item, 'is_stackable') and clicked_item.is_stackable() and getattr(clicked_item, 'load', 1) > 1:
                        options.extend(['Grab One', 'Grab Half', 'Grab All'])
                    else:
                        options.append('Grab')

            item_type = getattr(clicked_item, 'item_type', None)
            invalid_types = [None, 'vehicle', 'map_tile', 'maptile', 'maptile_container', 'maptile_teleport']
            if item_type not in invalid_types and not isinstance(clicked_item, Corpse) and not is_maptile:
                options.append('Send to')

        elif click_source == 'ground':
            options = []
            if isinstance(clicked_item, Corpse):
                options.append('Open')
            else:
                if not getattr(clicked_item, 'liquid', False):
                    if hasattr(clicked_item, 'is_stackable') and clicked_item.is_stackable() and getattr(clicked_item, 'load', 1) > 1:
                        options.extend(['Grab One', 'Grab Half', 'Grab All'])
                    else:
                        options.append('Grab')
                options.append('Send to')

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

            if is_player_item:
                if 'Place' not in options: options.append('Place')
                if 'Send to' not in options and click_source != 'vehicle_equipment':
                    options.append('Send to')

                item_type = getattr(clicked_item, 'item_type', None)
                invalid_types = [None, 'vehicle', 'map_tile', 'maptile', 'maptile_container', 'maptile_teleport']
                if item_type not in invalid_types and not isinstance(clicked_item, Corpse) and not is_maptile:
                    item_name_to_check = getattr(clicked_item, 'name', '')
                    if item_name_to_check:
                        if not RecipeManager.RECIPES:
                            RecipeManager.load_recipes()
                        has_crafts = any(is_recipe_relevant_to_item(r, item_name_to_check) for r in RecipeManager.RECIPES)
                        if has_crafts and 'Crafts' not in options:
                            options.append('Crafts')

                veh = getattr(game.player, 'vehicle', None)
                if not veh:
                    for m in game.modals:
                        if m['type'] == 'vehicle':
                            veh = m['vehicle']
                            break
                if veh:
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

            elif click_source == 'container':
                options = []
                if not getattr(clicked_item, 'liquid', False):
                    if hasattr(clicked_item, 'is_stackable') and clicked_item.is_stackable() and getattr(clicked_item, 'load', 1) > 1:
                        options.extend(['Grab One', 'Grab Half', 'Grab All'])
                    else:
                        options.append('Grab')
                options.append('Send to')

        # --- SUBMENU GENERATION LOGIC ---
        new_options = []
        for opt in options:
            if isinstance(opt, dict):
                new_options.append(opt)
                continue

            if not isinstance(opt, str):
                continue

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

            # =========================================================================
            # --- 1. EQUIP AS A DETAILED SUBMENU SHOWING ALL AVAILABLE SLOTS ---
            # =========================================================================
            if opt == 'Equip':
                sub_opts = []
                display_map = {}
                replace_map = {}
                item_type = getattr(clicked_item, 'item_type', '') or ''
                is_liquid = getattr(clicked_item, 'liquid', False)

                # A. Belt Slots (Weapons, Tools, and items flagged with allow_belt=True)
                can_go_belt = not is_liquid and (
                    getattr(clicked_item, 'allow_belt', False) or 
                    item_type in ('weapon', 'weapon_melee', 'weapon_ranged', 'weapon_throw', 'tool', 'utility', 'mobile', 'text', 'map', 'consumable_medical', 'consumable_food')
                )

                if can_go_belt and click_source != 'belt':
                    for b_idx in range(len(game.player.belt)):
                        slot_key = f"belt_{b_idx}"
                        sub_opts.append(slot_key)
                        existing = game.player.belt[b_idx]
                        if existing:
                            display_map[slot_key] = f"{tr('ui', 'Belt')} {b_idx + 1}"
                            replace_map[slot_key] = existing.name
                        else:
                            display_map[slot_key] = f"{tr('ui', 'Belt')} {b_idx + 1} ({tr('ui', 'Empty')})"

                # B. Gear / Clothes Slots (Clothes, Helmets, Armor, Bags, Vests, Containers)
                if item_type in ('cloth', 'container') and not is_liquid:
                    slot = getattr(clicked_item, 'slot', None)
                    if slot == 'hand': slot = 'hands'
                    
                    gear_slots = []
                    if slot in ('util', 'util1', 'util2', 'util3') or (item_type == 'container' and not slot):
                        gear_slots = ['util', 'util2', 'util3']
                    elif slot:
                        gear_slots = [slot]
                        
                    for s in gear_slots:
                        if s in game.player.clothes_slots or s in ('util', 'util2', 'util3'):
                            sub_opts.append(s)
                            existing = game.player.clothes.get(s)
                            
                            s_label = s
                            if s == 'util': s_label = "Util 1"
                            elif s == 'util2': s_label = "Util 2"
                            elif s == 'util3': s_label = "Util 3"
                            else: s_label = s.capitalize()
                            
                            if existing:
                                display_map[s] = tr('ui', s_label)
                                replace_map[s] = existing.name
                            else:
                                display_map[s] = f"{tr('ui', s_label)} ({tr('ui', 'Empty')})"

                if sub_opts:
                    new_options.append({
                        'label': 'Equip',
                        'sub': sub_opts,
                        'display_names': display_map,
                        'replacing': replace_map
                    })
                continue

            # =========================================================================
            # --- 2. SEND TO SUBMENU WITH OPEN CONTAINERS, BELT, AND INVENTORY ---
            # =========================================================================
            elif opt == 'Send to':
                sub_opts = []
                display_map = {}
                tooltip_map = {}
                is_liquid = getattr(clicked_item, 'liquid', False)

                # A. Destination Inventory (Only if not already in inventory and not spilled liquid)
                if click_source != 'inventory' and not is_liquid:
                    sub_opts.append('Inventory')
                    display_map['Inventory'] = tr('ui', 'Inventory')
                    tooltip_map['Inventory'] = f"{tr('ui', 'Send to')} {tr('ui', 'Inventory')}"

                # B. Destination Belt (Only if not in belt, allows belt, and has free space)
                can_go_belt = not is_liquid and (
                    getattr(clicked_item, 'allow_belt', False) or 
                    getattr(clicked_item, 'item_type', '') in ('weapon', 'weapon_melee', 'weapon_ranged', 'weapon_throw', 'tool', 'utility', 'mobile', 'consumable_medical', 'consumable_food')
                )
                if click_source != 'belt' and can_go_belt and any(b is None for b in game.player.belt):
                    sub_opts.append('Belt')
                    display_map['Belt'] = tr('ui', 'Belt')
                    tooltip_map['Belt'] = f"{tr('ui', 'Send to')} {tr('ui', 'Belt')}"

                # C. Gather Potential Target Containers
                candidate_containers = []

                # Active open modals (Chest, Locker, Crate, Vehicle Trunk)
                for m in getattr(game, 'modals', []):
                    if m.get('type') == 'container' and m.get('item'):
                        candidate_containers.append((m['item'], tr('ui', 'Open Container')))
                    elif m.get('type') == 'vehicle' and m.get('vehicle'):
                        candidate_containers.append((m['vehicle'], tr('ui', 'Vehicle Trunk')))

                # Nearby world containers (EXCLUDE closed maptiles and locked vehicles)
                for nearby_obj in game.find_nearby_containers():
                    if hasattr(nearby_obj, 'inventory') and nearby_obj.inventory is not None:
                        is_ground = (getattr(nearby_obj, 'item_type', '') == 'ground')
                        is_closed_maptile = (getattr(nearby_obj, 'item_type', '') == 'maptile_container' and not getattr(nearby_obj, 'is_opened', False))
                        is_locked_veh = (getattr(nearby_obj, 'item_type', '') == 'vehicle' and hasattr(nearby_obj, 'has_key_access') and not nearby_obj.has_key_access(game.player))

                        if not is_ground and not is_closed_maptile and not is_locked_veh:
                            candidate_containers.append((nearby_obj, tr('ui', 'Nearby Container')))

                # Player's carried/worn containers (Bags, Vests, Backpacks)
                for i, b_item in enumerate(game.player.belt):
                    if b_item and getattr(b_item, 'inventory', None) is not None:
                        candidate_containers.append((b_item, f"{tr('ui', 'Belt')} > {tr('ui', 'Slot')} {i+1}"))
                for i_item in game.player.inventory:
                    if i_item and getattr(i_item, 'inventory', None) is not None:
                        candidate_containers.append((i_item, tr('ui', 'Inventory')))
                for slot_k, c_item in game.player.clothes.items():
                    if c_item and getattr(c_item, 'inventory', None) is not None:
                        candidate_containers.append((c_item, f"{tr('ui', 'Gear')} > {str(slot_k).capitalize()}"))

                seen_c_keys = set()
                for c, loc_str in candidate_containers:
                    if c is clicked_item: continue
                    if click_container_item and c is click_container_item: continue

                    c_key = str(getattr(c, 'id', c.name))
                    if c_key in seen_c_keys: continue

                    # 1. Reject closed containers and locked vehicles
                    if getattr(c, 'item_type', '') == 'maptile_container' and not getattr(c, 'is_opened', False):
                        continue
                    if getattr(c, 'item_type', '') == 'vehicle' and hasattr(c, 'has_key_access') and not c.has_key_access(game.player):
                        continue

                    # 2. Strict Capacity Check: Clothes MUST have capacity > 0 (prevents 0-capacity clothes from appearing)
                    c_cap = getattr(c, 'capacity', 0)
                    if c_cap is None or c_cap <= 0:
                        continue

                    # 3. Liquid Constraints
                    c_allows_liquid = does_allow_liquid(c)
                    if is_liquid and not c_allows_liquid: continue
                    if not is_liquid and c_allows_liquid: continue
                    if is_liquid and get_container_available_liquid(c) <= 0: continue

                    # 4. Item Space Availability
                    can_fit = (len(getattr(c, 'inventory', [])) < c_cap)
                    if not can_fit and getattr(clicked_item, 'is_stackable', lambda: False)():
                        for inv_it in getattr(c, 'inventory', []):
                            if hasattr(inv_it, 'can_stack_with') and inv_it.can_stack_with(clicked_item):
                                if (getattr(inv_it, 'load', 0) or 0) < (getattr(inv_it, 'capacity', 1) or 1):
                                    can_fit = True
                                    break

                    if can_fit:
                        seen_c_keys.add(c_key)
                        sub_opts.append(c_key)
                        c_name = getattr(c, 'name', tr('ui', 'Container'))
                        
                        # Extra label detail for liquid vessels
                        if c_allows_liquid:
                            max_l = getattr(c, 'max_liquid', None)
                            cur_l = int(sum(getattr(x, 'load', 1) or 1 for x in getattr(c, 'inventory', []) if getattr(x, 'liquid', False)))
                            display_map[c_key] = f"{c_name} ({cur_l}/{max_l or '?'})"
                        else:
                            display_map[c_key] = f"{c_name}"

                        tooltip_map[c_key] = f"{tr('ui', 'Location:')} {loc_str}"

                if sub_opts:
                    new_options.append({
                        'label': 'Send to',
                        'sub': sub_opts,
                        'display_names': display_map,
                        'tooltips': tooltip_map
                    })
                continue

            elif opt == 'Remove fuel to':
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

            elif opt == 'Crafts':
                if not RecipeManager.RECIPES:
                    RecipeManager.load_recipes()

                sub_opts = ['open_craft']
                display_map = {'open_craft': tr('ui', 'Open Craft')}
                tooltip_map = {'open_craft': f"{tr('tooltip', 'Open crafting menu')}\n\n{tr('msg', 'The item must be in inventory or nearby to craft')}"}
                color_map = {'open_craft': WHITE}

                item_name = getattr(clicked_item, 'name', '')
                game.context_menu['craft_recipes'] = {}

                craft_buckets = {
                    'Craft': [],
                    'Repair': [],
                    'Dismantle': []
                }

                for r in RecipeManager.RECIPES:
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

                global_idx = 0
                max_total_recipes = 12

                for cat_name in ['Craft', 'Repair', 'Dismantle']:
                    bucket = craft_buckets[cat_name]
                    if not bucket:
                        continue

                    bucket.sort(key=lambda d: (not d['can_craft'], d['recipe'].output_name))

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
            forbidden_opts = ['Read', 'Drink', 'Use', 'Eat', 'Turn on', 'Turn off', 'Toggle Light', 'Crafts', 'Travel to', 'Open door/window', 'Close door/window', 'Barricate', 'Unbarricade']
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