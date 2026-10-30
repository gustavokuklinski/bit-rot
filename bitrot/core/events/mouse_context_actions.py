import uuid
import math
import pygame
import core.data.config
from core.data.config import *
from core.entities.item.item import Item
from core.messages import display_message
from core.data.localization import tr
from core.events.keyboard import (
    toggle_status_modal, toggle_inventory_modal, toggle_gear_modal, toggle_crafting_modal
)
from core.entities.item.item_helpers import (
    get_container_available_liquid, is_container_on_player,
    item_allows_belt, is_valid_send_to_container, does_allow_liquid,
    is_item_liquid, get_container_liquid_capacity_units, is_infinite_liquid_source,
    get_transfer_time, has_app
)
from core.events.mouse_drag_utils import check_container_weight_limit
from core.events.mouse_context_helpers import (
    calculate_boat_fuel_cost, get_player_fuel_units,
    consume_player_fuel_units, teleport_player_to_chunk, is_barricade_item, is_fuel_item
)
from core.ui.crafting_common import (
    execute_recipe_craft, get_recipe_status_details,
    get_crafting_item_locations, prioritize_locations_for_craft
)

def remove_from_source(game, target_item, source, index, container_item=None):
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
    elif source == 'vehicle_equipment' and container_item:
        if hasattr(container_item, 'remove_equipment'):
            return container_item.remove_equipment(index)
        elif hasattr(container_item, 'equipment') and index in container_item.equipment:
            removed = container_item.equipment[index]
            container_item.equipment[index] = None
            if hasattr(container_item, 'update_stats_from_equipment'):
                container_item.update_stats_from_equipment()
            return removed

    return None

def _get_player_charm(player):
    """Finds a charm in player inventory, belt, or clothes. Returns (item, container, index, ctype)."""
    for idx, it in enumerate(player.inventory):
        if it and getattr(it, 'item_type', '') == 'charm':
            return it, player.inventory, idx, 'list'
    for idx, it in enumerate(player.belt):
        if it and getattr(it, 'item_type', '') == 'charm':
            return it, player.belt, idx, 'belt'
    for slot, it in player.clothes.items():
        if it and getattr(it, 'item_type', '') == 'charm':
            return it, player.clothes, slot, 'dict'
    return None, None, None, None

def _consume_player_charm(player):
    it, cont, idx, ctype = _get_player_charm(player)
    if not it:
        return False
    if ctype == 'list':
        cont.pop(idx)
    elif ctype == 'belt':
        cont[idx] = None
        it.in_belt = False
    elif ctype == 'dict':
        cont[idx] = None
    return True

def _set_npc_layer(game, npc, new_layer):
    """Safely updates NPC layer avoiding pygame.sprite.LayeredUpdates setter restriction."""
    if hasattr(npc, 'groups') and npc.groups():
        for g in list(npc.groups()):
            if hasattr(g, 'change_layer'):
                try:
                    g.change_layer(npc, new_layer)
                except Exception:
                    pass
    try:
        npc.layer = new_layer
    except AttributeError:
        npc._layer = new_layer

def _teleport_npc_to_lobby(game, npc):
    gen = getattr(game, 'generator', None)
    lobby_gx, lobby_gy = getattr(gen, 'lobby_chunk', (0, 0)) if gen else (0, 0)
    lobby_map = f"map_L1_{lobby_gx}_{lobby_gy}_map.csv"
    cur_map = getattr(game.map_manager, 'current_map_filename', '')

    if cur_map == lobby_map:
        _set_npc_layer(game, npc, 1)
        npc.map_filename = lobby_map
        npc.is_static = True
        npc.is_friendly = True
        npc.is_at_port = False
        npc.is_at_lobby = True
        npc.render_opacity = 255.0
        npc.cached_los_draw_result = True
        npc.last_los_draw_check = pygame.time.get_ticks()

        spawn_pos = _find_lobby_safe_pos(game, lobby_gx, lobby_gy, lobby_map, npc_to_exclude=npc)
        npc.rect.topleft = spawn_pos
        npc.x, npc.y = float(spawn_pos[0]), float(spawn_pos[1])
        if npc not in game.npcs:
            game.npcs.add(npc)
    else:
        if npc in game.npcs:
            game.npcs.remove(npc)
        if hasattr(game, 'active_npcs') and npc in game.active_npcs:
            try:
                game.active_npcs.remove(npc)
            except ValueError:
                pass
        npc.kill()

        _set_npc_layer(game, npc, 1)
        npc.map_filename = lobby_map
        npc.is_static = True
        npc.is_friendly = True
        npc.is_at_port = False
        npc.is_at_lobby = True
        npc.render_opacity = 255.0
        npc.cached_los_draw_result = True
        npc.last_los_draw_check = pygame.time.get_ticks()

        lobby_npcs = _get_or_create_lobby_npcs(game, lobby_gx, lobby_gy, lobby_map)
        spawn_pos = _find_lobby_safe_pos(game, lobby_gx, lobby_gy, lobby_map, npc_to_exclude=npc, existing_lobby_npcs=lobby_npcs)
        npc.rect.topleft = spawn_pos
        npc.x, npc.y = float(spawn_pos[0]), float(spawn_pos[1])
        lobby_npcs.append(npc)
        game.map_states[lobby_map]['npcs'] = lobby_npcs

    if hasattr(game, 'sound_manager'):
        game.sound_manager.play_sound("notification.ogg", subdir="ui", game=game, base_volume=0.8, is_critical=True)

def _teleport_npc_to_port(game, npc):
    h = len(game.map_data) if game.map_data else 0
    w = len(game.map_data[0]) if h > 0 else 0

    boat_pos = None
    for y in range(h):
        for x in range(w):
            b_char = game.map_data[y][x] if y < len(game.map_data) and x < len(game.map_data[y]) else ''
            g_char = game.ground_data[y][x] if (getattr(game, 'ground_data', None) and y < len(game.ground_data) and x < len(game.ground_data[y])) else ''
            s_char = game.spawn_data[y][x] if (getattr(game, 'spawn_data', None) and y < len(game.spawn_data) and x < len(game.spawn_data[y])) else ''
            t_def = game.map_manager.get_tile_at(x, y)

            if (
                b_char in ('tp_boat', 'teleport_boat') or
                g_char in ('tp_boat', 'teleport_boat') or
                s_char in ('tp_boat', 'teleport_boat') or
                (t_def and (t_def.get('type') == 'maptile_teleport' or 'boat' in str(t_def.get('name', '')).lower()))
            ):
                boat_pos = (x * TILE_SIZE, y * TILE_SIZE)
                break
        if boat_pos:
            break

    target_pos = boat_pos if boat_pos else (game.player.rect.centerx, game.player.rect.centery)
    blocked = list(game.obstacles) + [n.rect for n in game.npcs if n != npc]

    # Find walkable non-water non-obstacle tile near the boat
    start_gx = target_pos[0] // TILE_SIZE
    start_gy = target_pos[1] // TILE_SIZE
    found_spot = None
    g_data = getattr(game, 'ground_data', None)
    b_data = getattr(game, 'map_data', None)
    defs = getattr(game.tile_manager, 'definitions', {}) if hasattr(game, 'tile_manager') else {}

    for r in range(1, 15):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if abs(dx) < r and abs(dy) < r: continue
                gx = start_gx + dx
                gy = start_gy + dy
                if b_data and (0 <= gy < len(b_data) and 0 <= gx < len(b_data[0])):
                    if g_data and 0 <= gy < len(g_data) and 0 <= gx < len(g_data[0]):
                        gt = str(g_data[gy][gx]).lower().strip()
                        if not gt or 'water' in gt or 'petrol' in gt or gt == ' ':
                            continue
                    bt = str(b_data[gy][gx]).strip()
                    if bt in ('@', '#') or 'door' in bt.lower() or 'window' in bt.lower():
                        continue
                    if bt in defs and defs[bt].get('is_obstacle', False):
                        continue
                    test_rect = pygame.Rect(gx * TILE_SIZE, gy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if any(test_rect.colliderect(b) for b in blocked):
                        continue
                    found_spot = (gx * TILE_SIZE, gy * TILE_SIZE)
                    break
            if found_spot: break
        if found_spot: break

    if found_spot:
        npc.rect.topleft = found_spot
        npc.x, npc.y = float(found_spot[0]), float(found_spot[1])

    npc.is_static = True
    npc.is_friendly = True
    npc.is_at_port = True
    npc.render_opacity = 255.0
    npc.cached_los_draw_result = True
    npc.last_los_draw_check = pygame.time.get_ticks()

    if hasattr(game, 'sound_manager'):
        game.sound_manager.play_sound("notification.ogg", subdir="ui", game=game, base_volume=0.8, is_critical=True)

def _get_or_create_lobby_npcs(game, lobby_gx, lobby_gy, lobby_map):
    """Ensures existing Lobby NPCs are registered so rescued survivors can anchor to them."""
    from core.map.map_loader import load_map_from_file
    from core.entities.npc.npc import NPC

    game.map_states.setdefault(lobby_map, {})
    if 'npcs' in game.map_states[lobby_map] and game.map_states[lobby_map]['npcs']:
        return game.map_states[lobby_map]['npcs']

    initial_npcs = []
    map_folder = game.map_manager.map_folder
    s_file = os.path.join(map_folder, f"map_L1_{lobby_gx}_{lobby_gy}_spawn.csv")

    if os.path.exists(s_file):
        s_data = load_map_from_file(s_file)
        occupied = set()
        for y, row in enumerate(s_data):
            for x, char in enumerate(row):
                if char.strip() == 'FNPC' and len(initial_npcs) < 3:
                    px, py = x * TILE_SIZE, y * TILE_SIZE
                    if (px, py) not in occupied:
                        occupied.add((px, py))
                        npc = NPC(px, py, game, is_static=True, layer=1)
                        npc.is_friendly = True
                        npc.map_filename = lobby_map
                        initial_npcs.append(npc)

    game.map_states[lobby_map]['npcs'] = initial_npcs
    return initial_npcs

def _find_lobby_safe_pos(game, lobby_gx, lobby_gy, lobby_map, npc_to_exclude=None, existing_lobby_npcs=None):
    """Finds an open, walkable floor tile directly next to the current Lobby NPCs, avoiding water and obstacles."""
    from core.map.map_loader import load_map_from_file

    cur_map = getattr(game.map_manager, 'current_map_filename', '')
    is_in_lobby = (cur_map == lobby_map)

    if is_in_lobby:
        b_data = getattr(game, 'map_data', [])
        g_data = getattr(game, 'ground_data', [])
        existing_npcs = [n for n in getattr(game, 'npcs', []) if n != npc_to_exclude]
        obstacles = list(getattr(game, 'obstacles', []))
    else:
        map_folder = game.map_manager.map_folder
        prefix = f"map_L1_{lobby_gx}_{lobby_gy}"
        b_file = os.path.join(map_folder, f"{prefix}_map.csv")
        g_file = os.path.join(map_folder, f"{prefix}_ground.csv")
        b_data = load_map_from_file(b_file) if os.path.exists(b_file) else []
        g_data = load_map_from_file(g_file) if os.path.exists(g_file) else []
        existing_npcs = [n for n in (existing_lobby_npcs or []) if n != npc_to_exclude]
        obstacles = []
        if b_data and hasattr(game, 'tile_manager'):
            defs = game.tile_manager.definitions
            for y, row in enumerate(b_data):
                for x, char in enumerate(row):
                    if char in ('@', '#') or (char in defs and defs[char].get('is_obstacle', False)):
                        obstacles.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    blocked = list(obstacles) + [n.rect for n in existing_npcs]

    # Find the anchor NPC position in the Lobby
    anchor_gx, anchor_gy = None, None
    if existing_npcs:
        anchor_gx = existing_npcs[0].rect.centerx // TILE_SIZE
        anchor_gy = existing_npcs[0].rect.centery // TILE_SIZE
    elif not is_in_lobby:
        map_folder = game.map_manager.map_folder
        s_file = os.path.join(map_folder, f"map_L1_{lobby_gx}_{lobby_gy}_spawn.csv")
        if os.path.exists(s_file):
            s_data = load_map_from_file(s_file)
            for y, row in enumerate(s_data):
                for x, char in enumerate(row):
                    if char.strip() == 'FNPC':
                        anchor_gx, anchor_gy = x, y
                        break
                if anchor_gx is not None:
                    break

    if anchor_gx is None or anchor_gy is None:
        anchor_gx, anchor_gy = 60, 60

    # Search expanding rings around the anchor NPC
    h = len(b_data)
    w = len(b_data[0]) if h > 0 else 0
    defs = getattr(game.tile_manager, 'definitions', {}) if hasattr(game, 'tile_manager') else {}

    for r in range(1, 20):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if abs(dx) < r and abs(dy) < r:
                    continue
                gx = anchor_gx + dx
                gy = anchor_gy + dy

                if not (0 <= gy < h and 0 <= gx < w):
                    continue

                # 1. Strictly avoid water and petrol tiles
                if g_data and gy < len(g_data) and gx < len(g_data[gy]):
                    gt = str(g_data[gy][gx]).lower().strip()
                    if not gt or gt == ' ' or 'water' in gt or 'petrol' in gt:
                        continue

                # 2. Strictly avoid walls, doors, windows, and obstacles
                bt = str(b_data[gy][gx]).strip()
                if bt in ('@', '#') or 'door' in bt.lower() or 'window' in bt.lower():
                    continue
                if bt in defs:
                    t_def = defs[bt]
                    if t_def.get('is_obstacle', False) or t_def.get('is_statable', False) or t_def.get('is_window', False):
                        continue

                # 3. Strictly avoid colliding with obstacles or existing NPCs
                test_rect = pygame.Rect(gx * TILE_SIZE, gy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if any(test_rect.colliderect(b) for b in blocked):
                    continue

                return (gx * TILE_SIZE, gy * TILE_SIZE)

    return (anchor_gx * TILE_SIZE, anchor_gy * TILE_SIZE)


def _teleport_npc_to_port(game, npc):
    from core.placement import find_free_tile
    h = len(game.map_data) if game.map_data else 0
    w = len(game.map_data[0]) if h > 0 else 0

    boat_pos = None
    for y in range(h):
        for x in range(w):
            b_char = game.map_data[y][x] if y < len(game.map_data) and x < len(game.map_data[y]) else ''
            g_char = game.ground_data[y][x] if (getattr(game, 'ground_data', None) and y < len(game.ground_data) and x < len(game.ground_data[y])) else ''
            s_char = game.spawn_data[y][x] if (getattr(game, 'spawn_data', None) and y < len(game.spawn_data) and x < len(game.spawn_data[y])) else ''
            t_def = game.map_manager.get_tile_at(x, y)

            if (
                b_char in ('tp_boat', 'teleport_boat') or
                g_char in ('tp_boat', 'teleport_boat') or
                s_char in ('tp_boat', 'teleport_boat') or
                (t_def and (t_def.get('type') == 'maptile_teleport' or 'boat' in str(t_def.get('name', '')).lower()))
            ):
                boat_pos = (x * TILE_SIZE, y * TILE_SIZE)
                break
        if boat_pos:
            break

    target_pos = boat_pos if boat_pos else (game.player.rect.centerx, game.player.rect.centery)
    blocked = list(game.obstacles) + [n.rect for n in game.npcs if n != npc]
    free_spot = find_free_tile(npc.rect, blocked, initial_pos=target_pos, max_radius=8)
    if free_spot:
        npc.rect.topleft = free_spot
        npc.x, npc.y = float(free_spot[0]), float(free_spot[1])

    npc.is_static = True
    npc.is_friendly = True
    npc.is_at_port = True
    npc.render_opacity = 255.0
    npc.cached_los_draw_result = True
    npc.last_los_draw_check = pygame.time.get_ticks()

    if hasattr(game, 'sound_manager'):
        game.sound_manager.play_sound("notification.ogg", subdir="ui", game=game, base_volume=0.8, is_critical=True)

def handle_npc_save(game, npc):
    if not getattr(npc, 'is_static', False):
        display_message(tr('msg', "Only static survivors can be rescued!"))
        return

    player = game.player
    from core.events.mouse_context_helpers import (
        get_player_fuel_units, consume_player_fuel_units, calculate_boat_fuel_cost
    )

    player_fuel = get_player_fuel_units(player)
    has_charm = (_get_player_charm(player)[0] is not None)

    gen = getattr(game, 'generator', None)
    has_lobby = getattr(core.data.config, 'SPAWN_LOBBY_CHUNK', True) and gen and getattr(gen, 'lobby_chunk', None) is not None
    lobby_chunk = getattr(gen, 'lobby_chunk', (0, 0)) if gen and gen.lobby_chunk else None
    lobby_map = f"map_L1_{lobby_chunk[0]}_{lobby_chunk[1]}_map.csv" if lobby_chunk else ""
    cur_map = getattr(game.map_manager, 'current_map_filename', '')

    is_already_at_lobby = has_lobby and (getattr(npc, 'is_at_lobby', False) or (cur_map == lobby_map))
    if is_already_at_lobby:
        display_message(tr('msg', f"{npc.name} is already safe in the Lobby!"))
        return

    is_at_port = getattr(npc, 'is_at_port', False)

    # If there is no Lobby in the world, survivors can only be evacuated to Port
    if not has_lobby:
        if is_at_port:
            display_message(tr('msg', f"{npc.name} is already safe at the Port!"))
        elif has_charm or player_fuel > 0:
            if has_charm:
                _consume_player_charm(player)
            elif player_fuel > 0:
                consume_player_fuel_units(player, player_fuel)
                game.boat_fuel_discount = 0.5
            _teleport_npc_to_port(game, npc)
            display_message(f"{tr('msg', 'Evacuated')} {npc.name} {tr('msg', 'to the Port!')}")
        else:
            display_message(tr('msg', "Rescue requires Fuel or Charm!"))
        return

    # Normal Lobby rescue logic when Lobby exists
    if is_at_port:
        if has_charm and player_fuel > 0:
            _consume_player_charm(player)
            fuel_cost = calculate_boat_fuel_cost(game, lobby_chunk[0], lobby_chunk[1])
            fuel_taken = min(player_fuel, fuel_cost)
            consume_player_fuel_units(player, fuel_taken)
            _teleport_npc_to_lobby(game, npc)
            display_message(f"{tr('msg', 'Rescued')} {npc.name} {tr('msg', 'to Lobby! (1 Charm and')} {fuel_taken} {tr('msg', 'Fuel used)')}")
        elif player_fuel > 0 and not has_charm:
            display_message(tr('msg', f"{npc.name} is at the Port! Need a Charm and Fuel to rescue to the Lobby."))
        else:
            display_message(tr('msg', "Need a Charm and Fuel to rescue survivor from Port to Lobby!"))
        return

    elif has_charm and player_fuel <= 0:
        _consume_player_charm(player)
        _teleport_npc_to_port(game, npc)
        display_message(f"{tr('msg', 'Evacuated')} {npc.name} {tr('msg', 'to the Port with a Charm!')}")

    elif player_fuel > 0 and not has_charm:
        fuel_taken = player_fuel
        consume_player_fuel_units(player, fuel_taken)
        game.boat_fuel_discount = 0.5
        _teleport_npc_to_port(game, npc)
        display_message(f"{tr('msg', 'Evacuated')} {npc.name} {tr('msg', 'to the Port! (Used all')} {fuel_taken} {tr('msg', 'Fuel. Boat travel is now 50% cheaper!)')}")

    elif player_fuel > 0 and has_charm:
        fuel_taken = min(player_fuel, calculate_boat_fuel_cost(game, lobby_chunk[0], lobby_chunk[1]))
        consume_player_fuel_units(player, fuel_taken)
        _consume_player_charm(player)
        _teleport_npc_to_lobby(game, npc)
        display_message(f"{tr('msg', 'Rescued')} {npc.name} {tr('msg', 'to Lobby! (1 Charm and')} {fuel_taken} {tr('msg', 'Fuel used)')}")

    else:
        display_message(tr('msg', "Rescue requires Fuel (to Port) or Fuel + Charm (to Lobby)!"))

    



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

            # Check that the player hasn't walked away from the map tile before clicking the option
            if source == 'map_tile' and isinstance(item, dict) and 'grid_x' in item and 'grid_y' in item:
                p_gx = int(game.player.rect.centerx // TILE_SIZE)
                p_gy = int(game.player.rect.centery // TILE_SIZE)
                if abs(item['grid_x'] - p_gx) > 1 or abs(item['grid_y'] - p_gy) > 1:
                    display_message(tr('msg', "Too far away to interact."))
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

                elif option == 'Save':
                    handle_npc_save(game, item)
                    clicked_on_menu = True

            elif option == 'Equip':
                target_slot = target_sub_slot

                # Helper to normalize all slot alias variants to player.clothes keys
                def normalize_slot(s):
                    if not s: return None
                    s_low = str(s).lower().strip()
                    if s_low in ('hand', 'hands', 'glove', 'gloves'): return 'hands'
                    if s_low in ('foot', 'feet', 'shoe', 'shoes', 'boot', 'boots', 'sneakers'): return 'feet'
                    if s_low in ('body', 'torso', 'chest', 'tshirt', 'shirt'): return 'body'
                    if s_low in ('head', 'hat', 'helmet', 'cap'): return 'head'
                    if s_low in ('leg', 'legs', 'pant', 'pants', 'jeans'): return 'legs'
                    if s_low in ('arm', 'arms', 'jacket'): return 'arms'
                    if s_low in ('face', 'facial', 'mask'): return 'facial'
                    return s_low

                # 1. Equip to Belt Slot
                if target_slot and target_slot.startswith('belt_'):
                    if not item_allows_belt(item):
                        display_message(tr('msg', "This item cannot be equipped to belt."))
                        game.context_menu['active'] = False
                        return
                    try:
                        bi = int(target_slot.split('_')[1])
                        item_from_src = remove_from_source(game, item, source, index, container_item)
                        if item_from_src:
                            old_item = game.player.belt[bi] if bi < len(game.player.belt) else None
                            if bi < len(game.player.belt):
                                game.player.belt[bi] = item_from_src
                            else:
                                game.player.belt.append(item_from_src)

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

                # 2. Equip to Specific Gear Slot from Submenu
                elif target_slot:
                    slot_name = normalize_slot(target_slot)

                    # Validate slot against player's valid equipment slots
                    if slot_name not in game.player.clothes:
                        display_message(tr('msg', "Invalid gear slot."))
                        game.context_menu['active'] = False
                        return

                    is_util_slot = slot_name in ['util', 'util2', 'util3']
                    item_slot = normalize_slot(getattr(item, 'slot', None))
                    is_util_item = item_slot in ['util', 'util1', 'util2', 'util3']

                    if is_util_slot and not is_util_item:
                        display_message(tr('msg', "Only utility items can be equipped in Util slots."))
                        game.context_menu['active'] = False
                        return
                    if is_util_item and not is_util_slot:
                        display_message(tr('msg', "Utility items can only be equipped in Util slots."))
                        game.context_menu['active'] = False
                        return

                    item_from_src = remove_from_source(game, item, source, index, container_item)
                    if item_from_src:
                        old_item = game.player.clothes.get(slot_name)
                        game.player.clothes[slot_name] = item_from_src

                        if hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound('equip_gear.ogg', subdir='items', game=game, source_pos=game.player.rect.center, is_critical=True)

                        # Return previously equipped item to inventory safely
                        if old_item:
                            if getattr(old_item, 'liquid', False):
                                old_item.rect.center = game.player.rect.center
                                game.items_on_ground.append(old_item)
                            elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(old_item)
                                if hasattr(game.player, 'stack_item_in_inventory'):
                                    game.player.stack_item_in_inventory(old_item)
                            else:
                                old_item.rect.center = game.player.rect.center
                                game.items_on_ground.append(old_item)

                        # Sync belt slots immediately if this was a utility item with hotbar="true"
                        if hasattr(game.player, 'sync_belt_slots'):
                            game.player.sync_belt_slots(game)

                        display_message(f"{tr('msg', 'Equipped')} {tr('item', item_from_src.name)} {tr('msg', 'to')} {tr('ui', slot_name.capitalize())}.")

                # 3. Direct Click Fallback on "Equip" (Auto-detects appropriate slot)
                else:
                    item_type = getattr(item, 'item_type', '') or ''
                    item_slot = normalize_slot(getattr(item, 'slot', None))
                    
                    target_s = None
                    if item_slot in ('util', 'util1', 'util2', 'util3'):
                        target_s = next((s for s in ['util', 'util2', 'util3'] if game.player.clothes.get(s) is None), 'util')
                    elif item_slot and item_slot in game.player.clothes:
                        target_s = item_slot
                    elif item_allows_belt(item):
                        # If it's a weapon or tool without clothing slot, send to first empty belt slot
                        game.player.equip_item_to_belt(item, source, index, container_item)
                        clicked_on_menu = True
                        game.context_menu['active'] = False
                        return

                    if not target_s:
                        display_message(tr('msg', "Cannot equip this item."))
                        game.context_menu['active'] = False
                        return

                    item_from_src = remove_from_source(game, item, source, index, container_item)
                    if item_from_src:
                        old_item = game.player.clothes.get(target_s)
                        game.player.clothes[target_s] = item_from_src

                        if hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound('equip_gear.ogg', subdir='items', game=game, source_pos=game.player.rect.center, is_critical=True)

                        if old_item:
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(old_item)
                                if hasattr(game.player, 'stack_item_in_inventory'):
                                    game.player.stack_item_in_inventory(old_item)
                            else:
                                old_item.rect.center = game.player.rect.center
                                game.items_on_ground.append(old_item)

                        if hasattr(game.player, 'sync_belt_slots'):
                            game.player.sync_belt_slots(game)

                        display_message(f"{tr('msg', 'Equipped')} {tr('item', item_from_src.name)} {tr('msg', 'to')} {tr('ui', target_s.capitalize())}.")

                clicked_on_menu = True

            elif option == 'Send to':
                target_dest = target_sub_slot

                # Verify key requirement if sending from vehicle equipment
                if source == 'vehicle_equipment' and container_item:
                    if container_item.equipment.get('key') is None:
                        display_message(tr('msg', "Vehicle requires key inserted in the Key slot."))
                        game.context_menu['active'] = False
                        return

                # An action is external (requires looting timer) if from world, vehicle, nearby, or external container
                is_external = (
                    source in ['nearby', 'ground', 'container_map', 'vehicle_equipment'] 
                    or (source == 'container' and (not container_item or not is_container_on_player(container_item, game.player)))
                )

                if target_dest == 'Inventory':
                    if source == 'inventory':
                        game.context_menu['active'] = False
                        return

                    if source == 'vehicle_equipment' and index == 'fuel':
                        display_message(tr('msg', "Use 'Remove fuel to' to transfer fuel into a container."))
                        game.context_menu['active'] = False
                        return

                    if getattr(item, 'liquid', False):
                        removed = remove_from_source(game, item, source, index, container_item)
                        display_message(tr('msg', f"The {item.name} spills on the ground and is lost."))
                        if hasattr(game, 'splashes'):
                            game.splashes.append({
                                'pos': (game.player.rect.centerx, game.player.rect.bottom),
                                'time': pygame.time.get_ticks(),
                                'duration': 350,
                                'radius': 4,
                                'type': 'hit_puff'
                            })
                        game.context_menu['active'] = False
                        return

                    def do_send_inv():
                        removed = remove_from_source(game, item, source, index, container_item)
                        if removed:
                            removed.is_placed = False
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(removed)
                                if hasattr(game.player, 'stack_item_in_inventory'):
                                    game.player.stack_item_in_inventory(removed)
                            else:
                                removed.rect.center = game.player.rect.center
                                removed.x, removed.y = removed.rect.topleft
                                game.items_on_ground.append(removed)
                                display_message(tr('msg', "Inventory full. Item dropped on ground."))

                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
                            display_message(f"{tr('msg', 'Sent')} {tr('item', removed.name)} {tr('msg', 'to inventory.')}")

                    transfer_time = get_transfer_time(game.player)
                    if is_external:
                        action_label = f"{tr('ui', 'Removing')} {tr('item', item.name)}" if source == 'vehicle_equipment' else tr('msg', "Looting")
                        game.player.start_action(action_label, transfer_time, do_send_inv, xp_reward=0.5)
                    else:
                        do_send_inv()

                elif target_dest == 'Ground':
                    if source == 'vehicle_equipment':
                        display_message(tr('msg', "Vehicle parts must be sent to inventory first."))
                        game.context_menu['active'] = False
                        return

                    if getattr(item, 'liquid', False):
                        remove_from_source(game, item, source, index, container_item)
                        display_message(tr('msg', f"The {item.name} spills on the ground."))
                        if hasattr(game, 'splashes'):
                            game.splashes.append({
                                'pos': (game.player.rect.centerx, game.player.rect.bottom),
                                'time': pygame.time.get_ticks(),
                                'duration': 350,
                                'radius': 4,
                                'type': 'hit_puff'
                            })
                        game.context_menu['active'] = False
                        return

                    def do_send_ground():
                        removed = remove_from_source(game, item, source, index, container_item)
                        if removed:
                            removed.rect.center = game.player.rect.center
                            removed.x, removed.y = removed.rect.topleft
                            removed.is_placed = False
                            removed.layer = getattr(game, 'current_layer_index', 1)
                            removed.map_filename = getattr(game.map_manager, 'current_map_filename', '')
                            game.items_on_ground.append(removed)
                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('drop.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
                            display_message(f"{tr('msg', 'Dropped')} {tr('item', removed.name)} {tr('msg', 'on ground.')}")

                    transfer_time = get_transfer_time(game.player)
                    action_label = f"{tr('ui', 'Removing')} {tr('item', item.name)}"
                    game.player.start_action(action_label, transfer_time, do_send_ground, xp_reward=0.5)

                elif target_dest == 'Belt':
                    if source == 'belt':
                        game.context_menu['active'] = False
                        return

                    if not item_allows_belt(item):
                        display_message(tr('msg', "This item cannot be placed on the belt."))
                        game.context_menu['active'] = False
                        return

                    empty_idx = next((bi for bi, b in enumerate(game.player.belt) if b is None), None)
                    if empty_idx is not None:
                        def do_send_belt():
                            removed = remove_from_source(game, item, source, index, container_item)
                            if removed:
                                removed.in_belt = True
                                game.player.belt[empty_idx] = removed
                                if hasattr(game, 'sound_manager'):
                                    game.sound_manager.play_sound('equip_belt.ogg', subdir='items', game=game, source_pos=game.player.rect.center, is_critical=True)
                                display_message(f"{tr('msg', 'Sent')} {tr('item', removed.name)} {tr('msg', 'to belt slot')} {empty_idx+1}.")

                        transfer_time = get_transfer_time(game.player)
                        if is_external:
                            game.player.start_action(tr('msg', "Looting"), transfer_time, do_send_belt, xp_reward=0.5)
                        else:
                            do_send_belt()
                    else:
                        display_message(tr('msg', "Belt is full."))

                else:
                    target_container = None
                    search_pools = [
                        [b for b in game.player.belt if b and is_valid_send_to_container(b) and hasattr(b, 'inventory')],
                        [it for it in game.player.inventory if it and is_valid_send_to_container(it) and hasattr(it, 'inventory')],
                        [c for c in game.player.clothes.values() if c and is_valid_send_to_container(c) and hasattr(c, 'inventory')],
                        [m.get('item') for m in game.modals if m.get('type') == 'container' and m.get('item') and is_valid_send_to_container(m.get('item'))],
                        [m.get('vehicle') for m in game.modals if m.get('type') == 'vehicle' and m.get('vehicle')],
                        [c for c in game.find_nearby_containers() if is_valid_send_to_container(c)]
                    ]
                    for pool in search_pools:
                        for c in pool:
                            if c and (str(getattr(c, 'id', '')) == target_dest or getattr(c, 'name', '') == target_dest):
                                target_container = c
                                break
                        if target_container:
                            break

                    if target_container and hasattr(target_container, 'inventory'):
                        if not is_valid_send_to_container(target_container):
                            display_message(tr('msg', "Invalid destination container."))
                            game.context_menu['active'] = False
                            return

                        if getattr(target_container, 'item_type', '') == 'maptile_container' and not getattr(target_container, 'is_opened', False):
                            display_message(tr('msg', "Cannot send items into a closed container."))
                            game.context_menu['active'] = False
                            return

                        c_cap = getattr(target_container, 'capacity', 0)
                        if (c_cap is None or c_cap <= 0) and not does_allow_liquid(target_container):
                            display_message(tr('msg', "Target has no inventory capacity."))
                            game.context_menu['active'] = False
                            return

                        # Enforce container capacity (Liquid vs Solid)
                        if is_item_liquid(item) and does_allow_liquid(target_container):
                            avail_units = get_container_liquid_capacity_units(target_container, item)
                            if avail_units <= 0:
                                display_message(tr('msg', "Container is full of liquid."))
                                game.context_menu['active'] = False
                                return

                        def do_send_cont():
                            is_liquid = is_item_liquid(item)
                            total_load = getattr(item, 'load', 1)
                            if total_load is None: total_load = 1
                            target_cap = getattr(target_container, 'capacity', 0) or 0

                            if is_liquid:
                                # First calculate weight, then volume to determine exact fillable units
                                avail_units = get_container_liquid_capacity_units(target_container, item)
                                if avail_units <= 0:
                                    if get_container_available_liquid(target_container) <= 0:
                                        display_message(tr('msg', "Container is full of liquid."))
                                    else:
                                        display_message(f"{tr('item', target_container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                    return

                                # Floor units down to the integer below
                                transfer_units = float(int(math.floor(min(total_load, float(avail_units)))))
                                if transfer_units <= 0:
                                    return

                                max_l_val = getattr(target_container, 'max_liquid', None)
                                if max_l_val is not None and not math.isinf(float(max_l_val)):
                                    target_max_l = int(math.floor(float(max_l_val)))
                                else:
                                    target_max_l = int(getattr(item, 'capacity', 100) or 100)

                                stacked = False
                                for inv_it in target_container.inventory:
                                    is_inv_liq = getattr(inv_it, 'liquid', False) or getattr(inv_it, 'item_type', '') in ('liquid', 'car_fuel') or getattr(inv_it, 'name', '') == 'Fuel Unit'
                                    if is_inv_liq and inv_it.name == item.name:
                                        inv_it.load = (getattr(inv_it, 'load', 0) or 0) + transfer_units
                                        inv_it.capacity = target_max_l
                                        stacked = True
                                        break

                                if not stacked:
                                    target_cap = max(1, getattr(target_container, 'capacity', 0) or 1)
                                    if len(target_container.inventory) >= target_cap:
                                        display_message(tr('msg', "Container is full."))
                                        return
                                    
                                    # Only create a new item if no stack exists
                                    new_liq = Item.create_from_name(item.name)
                                    if new_liq:
                                        new_liq.load = transfer_units
                                        new_liq.capacity = target_max_l
                                        target_container.inventory.append(new_liq)

                                # If transferring from an infinite liquid maptile container, preserve its stock
                                if container_item and is_infinite_liquid_source(container_item):
                                    item.load = getattr(item, 'capacity', 100)
                                else:
                                    if transfer_units >= total_load:
                                        remove_from_source(game, item, source, index, container_item)
                                    else:
                                        item.load -= transfer_units

                                

                                if hasattr(game, 'sound_manager'):
                                    game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
                                display_message(f"{tr('msg', 'Transferred')} {int(transfer_units)} {tr('item', item.name)} {tr('msg', 'into')} {target_container.name}.")
                                return

                            if not check_container_weight_limit(target_container, item):
                                display_message(f"{tr('item', target_container.name)} {tr('msg', 'cannot carry that much weight.')}")
                                return

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

                            if qty_to_send > 0:
                                if len(target_container.inventory) < target_cap:
                                    if qty_to_send < total_load:
                                        new_it = Item.create_from_name(item.name)
                                        if new_it:
                                            new_it.load = qty_to_send
                                            target_container.inventory.append(new_it)
                                            item.load -= qty_to_send
                                    else:
                                        removed = remove_from_source(game, item, source, index, container_item)
                                        if removed:
                                            target_container.inventory.append(removed)
                                else:
                                    if not stacked:
                                        display_message(tr('msg', "Container is full."))
                                        return
                                    else:
                                        item.load = qty_to_send

                            elif stacked:
                                remove_from_source(game, item, source, index, container_item)

                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
                            display_message(f"{tr('msg', 'Sent to')} {target_container.name}.")

                        transfer_time = get_transfer_time(game.player)
                        if is_external:
                            game.player.start_action(f"Transferring to {target_container.name}", transfer_time, do_send_cont, xp_reward=0.5)
                        else:
                            do_send_cont()

                clicked_on_menu = True
            
            elif option == 'Remove fuel to':
                veh = container_item if getattr(container_item, 'item_type', '') == 'vehicle' else getattr(game.player, 'vehicle', None)
                if not veh:
                    for m in game.modals:
                        if m.get('type') == 'vehicle':
                            veh = m.get('vehicle')
                            break

                if not veh:
                    display_message(tr('msg', "No vehicle found."))
                    game.context_menu['active'] = False
                    return

                if veh.required_key_id and veh.equipment.get('key') is None:
                    display_message(tr('msg', "Vehicle requires key inserted in the Key slot."))
                    game.context_menu['active'] = False
                    return

                fuel_amount = veh.fuel
                if fuel_amount <= 0:
                    display_message(tr('msg', "No fuel to remove."))
                    game.context_menu['active'] = False
                    return

                # Find target container
                target_container = None
                for c_list in [game.player.belt, game.player.inventory, list(game.player.clothes.values())]:
                    for c in c_list:
                        if not c: continue
                        if str(getattr(c, 'id', c.name)) == target_sub_slot:
                            target_container = c
                            break
                        if hasattr(c, 'inventory') and c.inventory:
                            for sub_c in c.inventory:
                                if str(getattr(sub_c, 'id', sub_c.name)) == target_sub_slot:
                                    target_container = sub_c
                                    break
                    if target_container: break

                if not target_container:
                    display_message(tr('msg', "Target container not found."))
                    game.context_menu['active'] = False
                    return

                avail_liquid = get_container_available_liquid(target_container)
                if avail_liquid <= 0:
                    display_message(f"{target_container.name} {tr('msg', 'is full of liquid.')}")
                    game.context_menu['active'] = False
                    return

                transfer_units = min(fuel_amount, avail_liquid)

                def do_siphon_fuel():
                    if not hasattr(target_container, 'inventory'):
                        target_container.inventory = []

                    # Find existing fuel or create new item in the target container
                    existing_fuel = next((it for it in target_container.inventory if it and it.name == "Fuel Unit"), None)
                    max_liq_cap = int(getattr(target_container, 'max_liquid', 100) or 100)

                    if existing_fuel:
                        existing_fuel.load = (getattr(existing_fuel, 'load', 0) or 0) + transfer_units
                        existing_fuel.capacity = max_liq_cap
                    else:
                        new_fuel = Item.create_from_name("Fuel Unit")
                        if new_fuel:
                            new_fuel.load = transfer_units
                            new_fuel.capacity = max_liq_cap
                            target_container.inventory.append(new_fuel)

                    # Deduct from vehicle tank
                    veh.fuel = max(0.0, veh.fuel - transfer_units)
                    fuel_eq = veh.equipment.get('fuel')
                    if fuel_eq and hasattr(fuel_eq, 'load'):
                        fuel_eq.load = max(0.0, float(fuel_eq.load) - transfer_units)
                    veh.update_stats_from_equipment()

                    

                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_sound('grab.ogg', subdir='items', game=game, source_pos=game.player.rect.center)
                    display_message(f"{tr('msg', 'Transferred')} {int(transfer_units)} {tr('item', 'Fuel Unit')} {tr('msg', 'to')} {target_container.name}.")

                siphon_time = max(0.4, transfer_units * 0.05)
                game.player.start_action(tr('ui', "Siphoning Fuel"), siphon_time, do_siphon_fuel, xp_reward=0.5)
                clicked_on_menu = True

            elif option == 'Install on Vehicle':
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

                if not veh:
                    display_message(tr('msg', "No vehicle nearby."))
                    game.context_menu['active'] = False
                    return

                target_slot = target_sub_slot
                if not target_slot:
                    if veh.can_equip(item, 'key'): target_slot = 'key'
                    elif veh.can_equip(item, 'fuel') or getattr(item, 'name', '') == 'Fuel Unit': target_slot = 'fuel'
                    elif veh.can_equip(item, 'motor'): target_slot = 'motor'
                    elif veh.can_equip(item, 'battery'): target_slot = 'battery'
                    else:
                        for t_s in getattr(veh, 'required_tires', []):
                            if veh.can_equip(item, t_s):
                                target_slot = t_s
                                break

                if not target_slot:
                    display_message(tr('msg', "Item cannot be installed on this vehicle."))
                    game.context_menu['active'] = False
                    return

                # Non-key parts strictly require the key to be in the key slot
                if target_slot != 'key' and veh.required_key_id and veh.equipment.get('key') is None:
                    display_message(tr('msg', "Vehicle requires key inserted in the Key slot."))
                    game.context_menu['active'] = False
                    return

                if target_slot == 'fuel':
                    def do_refuel_action():
                        trans, err = veh.refuel(item)
                        if err:
                            display_message(tr('msg', err))
                        else:
                            # FIX: Distinguish between a container (canister) and a loose fuel item
                            is_container = hasattr(item, 'inventory')
                            is_loose_fuel = (getattr(item, 'name', '') == "Fuel Unit")
                            
                            # Only remove from source if it's a loose fuel unit and it's now empty
                            if is_loose_fuel and hasattr(item, 'load') and item.load <= 0:
                                remove_from_source(game, item, source, index, container_item)
                            
                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('repair.ogg', subdir='craft', game=game, source_pos=game.player.rect.center)
                            display_message(f"{tr('msg', 'Added')} {int(trans)} {tr('msg', 'fuel units to vehicle.')}")

                    transfer_time = max(0.4, float(getattr(item, 'load', 1) or 1) * 0.05)
                    game.player.start_action(tr('ui', "Refueling"), transfer_time, do_refuel_action, xp_reward=0.5)

                else:
                    def do_install_action():
                        removed = remove_from_source(game, item, source, index, container_item)
                        if removed:
                            old_item = veh.add_equipment(removed, target_slot)
                            if old_item:
                                if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    game.player.inventory.append(old_item)
                                else:
                                    old_item.rect.center = game.player.rect.center
                                    game.items_on_ground.append(old_item)
                            veh.update_stats_from_equipment()
                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_sound('repair.ogg', subdir='craft', game=game, source_pos=game.player.rect.center)
                            display_message(f"{tr('msg', 'Installed')} {tr('item', removed.name)} {tr('msg', 'into vehicle.')}")

                    install_time = 0.5
                    game.player.start_action(f"{tr('ui', 'Installing')} {tr('item', item.name)}", install_time, do_install_action, xp_reward=0.5)

                clicked_on_menu = True

            elif option in ['Add key', 'Add fuel', 'Add motor', 'Add battery', 'Add tire to']:
                veh_modal = next((m for m in reversed(game.modals) if m.get('type') == 'vehicle'), None)
                veh = veh_modal.get('vehicle') if veh_modal else None

                if not veh:
                    display_message(tr('msg', "No vehicle modal open."))
                    game.context_menu['active'] = False
                    return

                target_slot = 'key' if option == 'Add key' else ('fuel' if option == 'Add fuel' else ('motor' if option == 'Add motor' else ('battery' if option == 'Add battery' else target_sub_slot)))

                if target_slot != 'key' and veh.equipment.get('key') is None:
                    display_message(tr('msg', "Vehicle requires key inserted in the Key slot."))
                    game.context_menu['active'] = False
                    return

                def do_install_part():
                    # Re-check key status
                    if target_slot != 'key' and veh.equipment.get('key') is None:
                        display_message(tr('msg', "Vehicle requires key inserted in the Key slot."))
                        return

                    removed = remove_from_source(game, item, source, index, container_item)
                    if removed:
                        old_item = veh.add_equipment(removed, target_slot)
                        if old_item:
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(old_item)
                            else:
                                old_item.rect.center = game.player.rect.center
                                old_item.x, old_item.y = old_item.rect.topleft
                                game.items_on_ground.append(old_item)

                        veh.update_stats_from_equipment()
                        if hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound('repair.ogg', subdir='craft', game=game, source_pos=game.player.rect.center)
                        display_message(f"{tr('msg', 'Installed')} {tr('item', removed.name)} {tr('msg', 'into vehicle.')}")

                install_time = 0.5
                action_name = f"{tr('ui', 'Installing')} {tr('item', item.name)}"
                game.player.start_action(action_name, install_time, do_install_part, xp_reward=0.5)
                clicked_on_menu = True

            elif option == 'Place barricade':
                if source == 'map_tile' and isinstance(item, dict):
                    gx = item['grid_x']
                    gy = item['grid_y']

                    found_barricade = None
                    barricade_source = None
                    barricade_idx = -1

                    for idx_it, it in enumerate(game.player.inventory):
                        if is_barricade_item(it):
                            found_barricade = it
                            barricade_source = 'inventory'
                            barricade_idx = idx_it
                            break

                    if not found_barricade:
                        for idx_it, it in enumerate(game.player.belt):
                            if is_barricade_item(it):
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

            elif option == 'Discover Island':
                fuel_cost = 25
                player_fuel = get_player_fuel_units(game.player)
                fuel_name = tr('item', "Fuel Unit")

                if player_fuel < fuel_cost:
                    display_message(f"{tr('msg', 'Not enough fuel! Need')} {fuel_cost}x {fuel_name} {tr('msg', 'to discover an island.')}")
                elif not getattr(game, 'generator', None):
                    display_message(tr('msg', "Generator is not available in this world."))
                else:
                    consume_player_fuel_units(game.player, fuel_cost)
                    new_gx, new_gy = game.generator.discover_new_isolated_island()
                    game.map_manager.refresh_maps()

                    # Create and give the cartography map to the player
                    map_item_name = f"Cartography Sector {new_gx}_{new_gy}"
                    map_item = Item.create_from_name(map_item_name)
                    if not map_item:
                        # Fallback to generic map item with custom text and name
                        map_item = Item.create_from_name("Cartography Sector [MAP_POS]")
                        if map_item:
                            map_item.name = map_item_name

                    if map_item:
                        if len(game.player.inventory) < game.player.get_total_inventory_slots():
                            game.player.inventory.append(map_item)
                            if hasattr(game.player, 'stack_item_in_inventory'):
                                game.player.stack_item_in_inventory(map_item)
                        else:
                            map_item.rect.center = game.player.rect.center
                            map_item.x, map_item.y = map_item.rect.topleft
                            game.items_on_ground.append(map_item)
                            display_message(tr('msg', "Inventory full. Map dropped on ground."))

                    display_message(f"{tr('msg', 'Used')} {fuel_cost}x {fuel_name}. {tr('msg', 'Discovered Island')} ({new_gx}, {new_gy})!")
                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_sound("notification.ogg", subdir="ui", game=game, base_volume=0.8, is_critical=True)

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

            elif option == 'Use' or option.startswith('Use '):
                use_target = item
                use_source = source
                use_index = index
                use_container = container_item

                # If clicked directly on a container maptile on the map
                if source == 'container_map' and hasattr(item, 'inventory'):
                    found_it = None
                    if option.startswith('Use '):
                        req_name = option[4:].strip().lower()
                        found_it = next((it for it in item.inventory if it and getattr(it, 'allow_use', False) and (tr('item', it.name).lower() == req_name or it.name.lower() == req_name)), None)
                    if not found_it:
                        found_it = next((it for it in item.inventory if it and getattr(it, 'allow_use', False)), None)
                    if found_it:
                        use_target = found_it
                        use_container = item
                        use_index = item.inventory.index(found_it)

                game.player.consume_item(use_target, use_source, use_index, use_container, game=game)
                clicked_on_menu = True

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
                    else:
                        for idx_g, g_it in enumerate(game.items_on_ground):
                            if g_it is item or getattr(g_it, 'id', None) == getattr(item, 'id', None):
                                game.items_on_ground[idx_g] = result
                                break
                    if hasattr(game, 'spatial_manager'):
                        game.spatial_manager.rebuild_item_grid(force=True)
                elif source == 'nearby' and container_item and result and hasattr(result, 'name'):
                    if getattr(container_item, 'item_type', '') == 'ground':
                        for i_idx, ground_item in enumerate(game.items_on_ground):
                            if ground_item is item or getattr(ground_item, 'id', None) == getattr(item, 'id', None):
                                game.items_on_ground[i_idx] = result
                                break
                    if index is not None and 0 <= index < len(container_item.inventory):
                        container_item.inventory[index] = result
                    if hasattr(game, 'spatial_manager'):
                        game.spatial_manager.rebuild_item_grid(force=True)

            elif option == 'Drop one':
                if getattr(item, 'liquid', False):
                    has_load = hasattr(item, 'load') and item.load is not None
                    if has_load and item.load > 1:
                        item.load -= 1
                        display_message(f"{tr('msg', 'A portion of')} {tr('item', item.name)} {tr('msg', 'spills.')}")
                    else:
                        remove_from_source(game, item, source, index, container_item)
                        display_message(f"{tr('item', item.name)} {tr('msg', 'spills on the ground.')}")
                    
                    if hasattr(game, 'splashes'):
                        game.splashes.append({
                            'pos': (game.player.rect.centerx, game.player.rect.bottom),
                            'time': pygame.time.get_ticks(),
                            'duration': 350,
                            'radius': 3,
                            'type': 'hit_puff'
                        })
                    
                else:
                    game.player.drop_item_stack(game, source, index, container_item, 1)
                clicked_on_menu = True

            elif option == 'Drop all':
                if getattr(item, 'liquid', False):
                    remove_from_source(game, item, source, index, container_item)
                    display_message(f"{tr('msg', 'All of the')} {tr('item', item.name)} {tr('msg', 'spills on the ground.')}")
                    if hasattr(game, 'splashes'):
                        game.splashes.append({
                            'pos': (game.player.rect.centerx, game.player.rect.bottom),
                            'time': pygame.time.get_ticks(),
                            'duration': 350,
                            'radius': 5,
                            'type': 'hit_puff'
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
                    remove_from_source(game, item, source, index, container_item)
                    display_message(f"{tr('item', item.name)} {tr('msg', 'spills on the ground.')}")
                    if hasattr(game, 'splashes'):
                        game.splashes.append({
                            'pos': (game.player.rect.centerx, game.player.rect.bottom),
                            'time': pygame.time.get_ticks(),
                            'duration': 350,
                            'radius': 4,
                            'type': 'hit_puff'
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

            elif option == 'Use':
                game.player.consume_item(item, source, index, container_item, game=game)
                clicked_on_menu = True

            elif option in ('Open', 'Inspect'):
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
                    # Prevent multiple opens if already in progress or player is busy
                    if getattr(item, 'is_opening', False):
                        display_message(tr('msg', "Someone is already opening this container."))
                        game.context_menu['active'] = False
                        return

                    if game.player.action_timer > 0:
                        display_message(tr('msg', "Busy..."))
                        game.context_menu['active'] = False
                        return

                    def open_and_show_modal():
                        item.is_opening = False
                        if hasattr(item, 'open'):
                            item.open(game)
                        else:
                            item.is_opened = True

                        # Play opening sound consistently for all containers (maptiles, corpses, containers)
                        if game and hasattr(game, 'sound_manager'):
                            sound_pos = item.rect.center if hasattr(item, 'rect') else game.player.rect.center
                            game.sound_manager.play_sound(
                                'open_maptile.ogg',
                                subdir='map',
                                game=game,
                                source_pos=sound_pos,
                                base_volume=0.5,
                                is_critical=True
                            )

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
                                has_default_ui = any(m['type'] in ('inventory', 'nearby', 'slots') for m in game.modals)
                                if has_default_ui:
                                    slots_modal = next((m for m in game.modals if m.get('type') == 'slots'), None)
                                    if slots_modal and 'rect' in slots_modal:
                                        slots_pos = (slots_modal['rect'].x, slots_modal['rect'].y)
                                    else:
                                        slots_pos = getattr(game, 'last_modal_positions', {}).get(
                                            'slots', (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT)
                                        )
                                    target_pos = (slots_pos[0], max(0, slots_pos[1] - CONTAINER_MODAL_HEIGHT))
                                    game.last_modal_positions['container'] = target_pos
                                else:
                                    # Modals are hidden -> open centered without border snapping
                                    target_pos = (
                                        GAME_WIDTH - CONTAINER_MODAL_WIDTH - 5,
                                        GAME_HEIGHT - CONTAINER_MODAL_HEIGHT - 5
                                    )

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

                    # Containers in the world / ground and closed maptiles perform the loader
                    is_on_player = is_container_on_player(item, game.player)
                    is_closed_maptile = getattr(item, 'item_type', '') == 'maptile_container' and not getattr(item, 'is_opened', False)
                    needs_loader = (not is_on_player) or is_closed_maptile

                    instant = getattr(core.data.config, 'ALL_VISIBLE', False) or has_app(game, 'open_container_instant')

                    if needs_loader and not instant:
                        agility = game.player.progression.get_level('agility')
                        open_time = max(0.2, 1.8 - (agility * 0.2))

                        item.is_opening = True

                        def cancel_open():
                            item.is_opening = False

                        game.player.start_action(
                            f"{game.player.name} {tr('ui', 'Opening')}", 
                            open_time, 
                            open_and_show_modal, 
                            xp_reward=1.5, 
                            cancel_on_move=True, 
                            on_cancel=cancel_open
                        )
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

            elif option == 'Crafts':
                if target_sub_slot == 'open_craft':
                    crafting_modal = next((m for m in game.modals if m.get('type') == 'crafting'), None)
                    if not crafting_modal:
                        toggle_crafting_modal(game)
                        crafting_modal = next((m for m in game.modals if m.get('type') == 'crafting'), None)
                    else:
                        game.modals.remove(crafting_modal)
                        game.modals.append(crafting_modal)

                    if crafting_modal:
                        item_name = getattr(item, 'name', '')
                        crafting_modal['search_text'] = item_name
                        crafting_modal['active_tab'] = tr('tab', "Known Recipes")
                        if 'instance' in crafting_modal and crafting_modal['instance']:
                            crafting_modal['instance'].search_text = item_name
                            crafting_modal['instance'].modal['search_text'] = item_name
                            crafting_modal['instance'].modal['crafting_scroll_offset'] = 0

                    clicked_on_menu = True

                elif target_sub_slot and target_sub_slot.startswith('recipe_'):
                    if game.player.action_timer > 0:
                        display_message(tr('msg', "Busy..."))
                        game.context_menu['active'] = False
                        return

                    craft_recipes = game.context_menu.get('craft_recipes', {})
                    recipe = craft_recipes.get(target_sub_slot)
                    if recipe:
                        can_craft, is_unlocked, missing_ings, missing_mag, missing_skills = get_recipe_status_details(game.player, game, recipe)
                        if not is_unlocked:
                            if missing_mag:
                                display_message(f"{tr('msg', 'Requires magazine:')} {tr('item', missing_mag)}")
                            elif missing_skills:
                                s_str = ", ".join([f"{tr('ui', s[0].capitalize())} (Lv {s[2]})" for s in missing_skills])
                                display_message(f"{tr('msg', 'Missing skill:')} {s_str}")
                            else:
                                display_message(tr('msg', "You haven't unlocked this recipe yet."))
                        elif not can_craft:
                            if missing_ings:
                                m_str = ", ".join([f"{tr('item', m['name'])} ({m['have']}/{m['needed']})" for m in missing_ings])
                                display_message(f"{tr('msg', 'Missing ingredients:')} {m_str}")
                            else:
                                display_message(tr('msg', "At least one required item must be in your inventory."))
                        else:
                            c_type = getattr(recipe, 'craft_type', 'create').lower()
                            if c_type == 'repair':
                                locs = get_crafting_item_locations(game.player, game, include_nearby=True)
                                locs = prioritize_locations_for_craft(locs, preferred_id=getattr(item, 'id', None))
                                has_damaged = any(
                                    it.name.lower() == recipe.output_name.lower() and it.durability is not None and it.durability < it.max_durability
                                    for _, _, it, _, _ in locs
                                )
                                if not has_damaged:
                                    display_message(f"{tr('msg', 'No damaged')} {tr('item', recipe.output_name)} {tr('msg', 'found to repair.')}")
                                    game.context_menu['active'] = False
                                    return

                            execute_recipe_craft(game, recipe, player=game.player, count=1, preferred_item_id=getattr(item, 'id', None))
                    clicked_on_menu = True

            elif source in ['ground', 'nearby', 'container'] and option in ['Grab', 'Grab One', 'Grab Half', 'Grab All']:
                if getattr(item, 'type', None) in ('animal', 'zombie'):
                    game.context_menu['active'] = False
                    return

                target_inventory = game.player.inventory
                target_capacity = game.player.get_total_inventory_slots()

                if len(target_inventory) < target_capacity:
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

                    # Check if the container is external (requires looting timer)
                    is_external_grab = (
                        source in ('nearby', 'ground') 
                        or (source == 'container' and (not container_item or not is_container_on_player(container_item, game.player)))
                    )

                    if is_external_grab:
                        grab_time = get_transfer_time(game.player)
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