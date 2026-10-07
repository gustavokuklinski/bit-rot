# core/events/mouse_context.py

import os
import pygame
import uuid
import math
import random
import re
import core.data.config
from core.data.config import *
from core.entities.item.item import Item
from core.data.recipe_manager import RecipeManager
from core.entities.zombie.corpse import Corpse
from core.ui.inventory_modal import get_belt_hud_slot_rect, get_inventory_slot_rect
from core.ui.container_modal import get_container_slot_rect
from core.messages import display_message
from core.data.localization import tr
from core.entities.item.item_data import ITEM_TEMPLATES
from core.ui.crafting_common import is_recipe_relevant_to_item
from core.entities.item.item_helpers import (
    is_infinite_liquid_source, is_container_on_player, is_valid_send_to_container, item_allows_belt, is_container_closed_or_locked
)
from core.events.mouse_context_helpers import (
    get_fuel_icon, is_fuel_item, get_player_fuel_units,
    consume_player_fuel_units, calculate_boat_fuel_cost,
    is_barricade_item, teleport_player_to_chunk
)
from core.events.mouse_context_submenus import (
    build_equip_submenu, build_send_to_submenu,
    build_remove_fuel_submenu, build_crafts_submenu
)
from core.events.mouse_context_actions import (
    handle_context_menu_click, remove_from_source
)

def handle_right_click(game, mouse_pos):
    game.context_menu['active'] = False
    game.context_menu['options'] = []
    game.context_menu['rects'] = []
    game.context_menu['action_map'] = []
    game.context_menu['tooltips'] = {}
    game.context_menu['last_hovered_sub'] = -1
    game.context_menu.pop('craft_recipes', None)

    clicked_item = None
    click_source = None
    click_index = -1
    click_container_item = None
    click_modal_type = None

    # Find the single topmost modal under mouse_pos based on z-order
    top_modal = None
    for modal in reversed(game.modals):
        if modal.get('rect') and modal['rect'].collidepoint(mouse_pos):
            top_modal = modal
            break

    # Unconditionally define is_over_any_modal so it is available on all code paths
    is_over_any_modal = (top_modal is not None)

    # If right-clicking on a modal, bring it to the front (focused)
    if top_modal:
        if game.modals[-1] != top_modal:
            game.modals.remove(top_modal)
            game.modals.append(top_modal)


        modal = top_modal
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
                            # Empty slot clicked: only allow insert key if locked
                            if slot_name != 'key' and veh.equipment.get('key') is None:
                                display_message(tr('msg', "Vehicle requires key inserted in the Key slot."))
                                return

                            
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
                # Disallow right-click inspection if container is closed or vehicle trunk is locked
                is_closed = is_container_closed_or_locked(active_container, game.player)
                if not is_closed:
                    pos = content_rect.topleft
                    for i, item in enumerate(active_container.inventory):
                        if item and get_container_slot_rect(pos, i).collidepoint(mouse_pos):
                            clicked_item, click_source, click_index, click_container_item = item, 'nearby', i, active_container
                            click_modal_type = 'nearby'
                            break

        if not clicked_item:
            return

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
                        if is_barricade_item(it):
                            barricade_ref = it
                            break

                    if not barricade_ref:
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
            veh = click_container_item
            has_vehicle_key = (veh.equipment.get('key') is not None) if (veh and hasattr(veh, 'equipment')) else False

            # Require key inserted in the Key slot to remove or send any parts
            if not has_vehicle_key:
                display_message(tr('msg', "Vehicle requires key inserted in the Key slot."))
                return

            # Keep ONLY 'Send to' (Remove is deleted)
            options = []
            if click_index == 'fuel':
                # Fuel slot only permits siphoning into containers
                options.append('Remove fuel to')
            else:
                options.append('Send to')

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

        if click_source in ('map_tile', 'light_source', 'player_self', 'vehicle_equipment', 'vehicle_slot'):
            pass

        elif getattr(clicked_item, 'item_type', '') == 'vehicle':
            # Vehicle must have key physically in equipment['key']
            if clicked_item.required_key_id and clicked_item.equipment.get('key') is None:
                display_message(tr('msg', "Need a vehicle key to interact."))
                if 'fail' in getattr(clicked_item, 'sounds', {}):
                    game.sound_manager.play_sound(
                        clicked_item.sounds['fail'],
                        subdir='vehicles',
                        game=game,
                        source_pos=clicked_item.rect.center,
                        base_volume=0.5,
                        is_critical=True
                    )
                game.context_menu['active'] = False
                return
            options = ['Vehicle options', 'Trunk']

        elif is_nearby:
            options = []
            if not isinstance(clicked_item, Corpse) and getattr(clicked_item, 'type', None) not in ('animal', 'zombie'):
                if not getattr(clicked_item, 'liquid', False) or is_fuel_item(clicked_item):
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
                if not getattr(clicked_item, 'liquid', False) or is_fuel_item(clicked_item):
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

                # TARGET ONLY THE OPENED VEHICLE MODAL HIGHLIGHTED BY THE PLAYER
                veh = None
                veh_modal = next((m for m in reversed(game.modals) if m.get('type') == 'vehicle'), None)
                if veh_modal and veh_modal.get('vehicle'):
                    veh = veh_modal.get('vehicle')
                elif getattr(game.player, 'vehicle', None):
                    veh = game.player.vehicle
                else:
                    for v in getattr(game, 'vehicles', []) + [c for c in game.containers if getattr(c, 'item_type', '') == 'vehicle']:
                        if math.hypot(game.player.rect.centerx - v.rect.centerx, game.player.rect.centery - v.rect.centery) <= TILE_SIZE * 2.5:
                            veh = v
                            break

                if veh:
                    has_veh_key = (not veh.required_key_id) or (veh.equipment.get('key') is not None)
                    is_key = veh.can_equip(clicked_item, 'key')
                    can_install = False

                    # Only show install option if it's the key or the vehicle already has its key inserted
                    if is_key or has_veh_key:
                        for slot in list(veh.equipment.keys()) + getattr(veh, 'required_tires', []):
                            if slot != 'key' and not has_veh_key:
                                continue
                            if veh.can_equip(clicked_item, slot):
                                can_install = True
                                break

                    if can_install and 'Install on Vehicle' not in options:
                        options.append('Install on Vehicle')

            elif click_source == 'container':
                options = []
                if not getattr(clicked_item, 'liquid', False) or is_fuel_item(clicked_item):
                    if hasattr(clicked_item, 'is_stackable') and clicked_item.is_stackable() and getattr(clicked_item, 'load', 1) > 1:
                        options.extend(['Grab One', 'Grab Half', 'Grab All'])
                    else:
                        options.append('Grab')
                options.append('Send to')

        new_options = []
        for opt in options:
            if isinstance(opt, dict):
                new_options.append(opt)
                continue

            if not isinstance(opt, str):
                continue

            if opt.startswith('Add to '): 
                continue 

            if opt == 'Install on Vehicle':
                from core.events.mouse_context_submenus import build_install_vehicle_submenu
                install_sub = build_install_vehicle_submenu(clicked_item, game)
                if install_sub:
                    new_options.append(install_sub)
                continue

            if opt == 'Equip':
                equip_sub = build_equip_submenu(clicked_item, click_source, game)
                if equip_sub:
                    new_options.append(equip_sub)
                continue

            elif opt == 'Send to':
                send_sub = build_send_to_submenu(clicked_item, click_source, click_container_item, game)
                if send_sub:
                    new_options.append(send_sub)
                continue

            elif opt == 'Remove fuel to':
                new_options.append(build_remove_fuel_submenu(game))
                continue

            elif opt == 'Crafts':
                new_options.append(build_crafts_submenu(clicked_item, game))
                continue

            else:
                new_options.append(opt)
                
        game.context_menu['options'] = new_options

        if game.game_state == 'PAUSED':
            forbidden_opts = [
                'Read', 'Drink', 'Use', 'Eat', 'Turn on', 'Turn off', 
                'Toggle Light', 'Crafts', 'Travel to', 'Open door/window', 
                'Close door/window', 'Barricate', 'Unbarricade'
            ]
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