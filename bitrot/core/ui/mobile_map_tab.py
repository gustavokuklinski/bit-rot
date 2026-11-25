# core/ui/mobile_map_tab.py

import pygame
import math
import os
import re
from core.data.config import *
from core.ui.modals import BaseModal
from core.map.map_loader import load_map_from_file
from core.data.localization import tr

MINIMAP_COLORS = {
    'void_l1': (30, 144, 255),    # Ocean Water
    'void_caves': (25, 25, 25),   # Underground Rock/Void
    'water': (30, 144, 255),      # Water / Petrol
    'sand': (238, 214, 175),      # Beach & Sand
    'dirty': (139, 69, 19),       # Dirt & Trails
    'road': (80, 80, 80),         # Asphalt & Roads
    'grass': (34, 139, 34),       # Grassland
    'cave': (60, 50, 40),         # Cave Floors
    'floor': (100, 100, 100),     # Indoor Floors
    'wall': (150, 150, 150),      # Walls & Border Obstacles
    'tree': (20, 80, 20),         # Forest Trees
    'object': (120, 120, 120),    # Props & Objects
    'roof': (70, 70, 70),         # Roofs
    'default': (100, 100, 100)
}
MINIMAP_PLAYER_COLOR = (0, 255, 255)

def get_map_pixel_color(g_char, b_char, r_char, tile_defs=None, layer_idx=1):
    """Calculates the exact RGB color matching the JPG export logic."""
    color = MINIMAP_COLORS['void_l1'] if layer_idx == 1 else MINIMAP_COLORS['void_caves']

    if g_char and g_char != ' ':
        g_def = tile_defs.get(g_char) if tile_defs else None
        g_low = (g_def.get('name', '') if g_def else g_char).lower()
        if 'water' in g_low or 'petrol' in g_low or g_char.startswith('water_') or g_char.startswith('petrol_'):
            color = MINIMAP_COLORS['water']
        elif 'sand' in g_low:
            color = MINIMAP_COLORS['sand']
        elif 'dirty' in g_low:
            color = MINIMAP_COLORS['dirty']
        elif any(k in g_low for k in ['asphalt', 'road', 'street', 'path']):
            color = MINIMAP_COLORS['road']
        elif 'grass' in g_low:
            color = MINIMAP_COLORS['grass']
        elif 'cave' in g_low:
            color = MINIMAP_COLORS['cave']
        else:
            color = MINIMAP_COLORS['floor']

    if b_char and b_char != ' ':
        b_def = tile_defs.get(b_char) if tile_defs else None
        b_low = (b_def.get('name', '') if b_def else b_char).lower()
        if b_char in ('@', '#') or 'wall' in b_low:
            color = MINIMAP_COLORS['wall']
        elif 'tree' in b_low or b_char.startswith('garden_tree'):
            color = MINIMAP_COLORS['tree']
        elif b_def and (b_def.get('is_obstacle', False) or b_def.get('is_statable', False)):
            color = MINIMAP_COLORS['wall']
        else:
            color = MINIMAP_COLORS['object']

    if r_char and r_char != ' ':
        color = MINIMAP_COLORS['roof']

    return color

def parse_map_item_info(item_or_name):
    """
    Parses any map item or item name into layer, chunk, and full_map parameters.
    """
    name = item_or_name.name if hasattr(item_or_name, 'name') else str(item_or_name)
    name = name.strip()

    # 1. Cartography Sector {gx}_{gy} -> L1 single chunk
    m = re.match(r'Cartography Sector\s+(\d+)_(\d+)', name, re.IGNORECASE)
    if m:
        return {
            'is_map': True,
            'layer': 1,
            'full_map': False,
            'target_chunk': (int(m.group(1)), int(m.group(2))),
            'display_name': name
        }

    # 2. Dungeon Sector {layer} {gx}_{gy} -> L2 or L3 single chunk
    m = re.match(r'Dungeon Sector\s+(\d+)\s+(\d+)_(\d+)', name, re.IGNORECASE)
    if m:
        return {
            'is_map': True,
            'layer': int(m.group(1)),
            'full_map': False,
            'target_chunk': (int(m.group(2)), int(m.group(3))),
            'display_name': name
        }

    # 3. Dungeon Map {layer} -> L2 or L3 full map
    m = re.match(r'Dungeon Map\s+(\d+)', name, re.IGNORECASE)
    if m:
        return {
            'is_map': True,
            'layer': int(m.group(1)),
            'full_map': True,
            'target_chunk': None,
            'display_name': name
        }

    # 4. Island Map -> L1 full map
    if name.lower() == 'island map':
        return {
            'is_map': True,
            'layer': 1,
            'full_map': True,
            'target_chunk': None,
            'display_name': name
        }

    # Fallback
    return {
        'is_map': True,
        'layer': 1,
        'full_map': True,
        'target_chunk': None,
        'display_name': name
    }

def get_player_held_maps(player):
    """Gathers all map items held in player inventory, belt, and clothes/gear."""
    maps = []
    if not player:
        return maps
    seen_ids = set()

    def scan(items):
        item_iterable = items.values() if isinstance(items, dict) else items
        for it in item_iterable:
            if not it:
                continue
            if getattr(it, 'item_type', '') == 'map' or getattr(it, 'type', '') == 'map':
                it_id = getattr(it, 'id', None) or it.name
                if it_id not in seen_ids:
                    seen_ids.add(it_id)
                    maps.append(it)
            if hasattr(it, 'inventory') and it.inventory:
                scan(it.inventory)

    scan(getattr(player, 'inventory', []))
    scan(getattr(player, 'belt', []))
    if hasattr(player, 'clothes'):
        scan(player.clothes)

    return maps

def generate_minimap_cache(game, full_map=False, target_chunk=None, target_layer=None):
    if target_layer is None:
        target_layer = getattr(game, 'current_layer_index', 1)
    current_layer = target_layer

    tile_defs = game.tile_manager.definitions
    chunk_size = getattr(game, 'CHUNK_SIZE', 128)
    bg_fill = MINIMAP_COLORS['void_l1'] if current_layer == 1 else MINIMAP_COLORS['void_caves']

    if target_chunk:
        cache_surf = pygame.Surface((chunk_size, chunk_size))
        cache_surf.fill(bg_fill)
        pixels = pygame.PixelArray(cache_surf)

        gx, gy = target_chunk
        map_folder = game.map_manager.map_folder
        prefix = f"map_L{current_layer}_{gx}_{gy}"
        b_file = os.path.join(map_folder, f"{prefix}_map.csv")
        g_file = os.path.join(map_folder, f"{prefix}_ground.csv")
        r_file = os.path.join(map_folder, f"{prefix}_roof.csv")

        b_data = load_map_from_file(b_file) if os.path.exists(b_file) else []
        g_data = load_map_from_file(g_file) if os.path.exists(g_file) else []
        r_data = load_map_from_file(r_file) if os.path.exists(r_file) else []

        for y in range(chunk_size):
            for x in range(chunk_size):
                g_char = g_data[y][x] if y < len(g_data) and x < len(g_data[y]) else ' '
                b_char = b_data[y][x] if y < len(b_data) and x < len(b_data[y]) else ' '
                r_char = r_data[y][x] if y < len(r_data) and x < len(r_data[y]) else ' '

                col = get_map_pixel_color(g_char, b_char, r_char, tile_defs, layer_idx=current_layer)
                try:
                    pixels[x, y] = col
                except IndexError:
                    pass

        pixels.close()
        return cache_surf

    elif full_map and not getattr(game, 'is_giant_map', False):
        map_files = game.map_manager.map_files
        max_gx = 0
        max_gy = 0
        pattern = re.compile(rf'map_L{current_layer}_(\d+)_(\d+)_map\.csv')

        for filename in map_files:
            match = pattern.match(filename)
            if match:
                max_gx = max(max_gx, int(match.group(1)))
                max_gy = max(max_gy, int(match.group(2)))

        if hasattr(game, 'generator'):
            max_gx = max(max_gx, getattr(game.generator, 'grid_w', 1) - 1)
            max_gy = max(max_gy, getattr(game.generator, 'grid_h', 1) - 1)

        map_width = (max_gx + 1) * chunk_size
        map_height = (max_gy + 1) * chunk_size

        cache_surf = pygame.Surface((map_width, map_height))
        cache_surf.fill(bg_fill)
        pixels = pygame.PixelArray(cache_surf)

        map_folder = game.map_manager.map_folder
        active_chunks = getattr(game, 'generator', None).active_chunks if (hasattr(game, 'generator') and hasattr(game.generator, 'active_chunks')) else None

        for gy in range(max_gy + 1):
            for gx in range(max_gx + 1):
                if active_chunks is not None and (gx, gy) not in active_chunks:
                    continue

                prefix = f"map_L{current_layer}_{gx}_{gy}"
                b_file = os.path.join(map_folder, f"{prefix}_map.csv")
                g_file = os.path.join(map_folder, f"{prefix}_ground.csv")
                r_file = os.path.join(map_folder, f"{prefix}_roof.csv")

                b_data = load_map_from_file(b_file) if os.path.exists(b_file) else []
                g_data = load_map_from_file(g_file) if os.path.exists(g_file) else []
                r_data = load_map_from_file(r_file) if os.path.exists(r_file) else []

                offset_x = gx * chunk_size
                offset_y = gy * chunk_size

                for y in range(chunk_size):
                    for x in range(chunk_size):
                        g_char = g_data[y][x] if y < len(g_data) and x < len(g_data[y]) else ' '
                        b_char = b_data[y][x] if y < len(b_data) and x < len(b_data[y]) else ' '
                        r_char = r_data[y][x] if y < len(r_data) and x < len(r_data[y]) else ' '

                        col = get_map_pixel_color(g_char, b_char, r_char, tile_defs, layer_idx=current_layer)
                        try:
                            pixels[offset_x + x, offset_y + y] = col
                        except IndexError:
                            pass

        pixels.close()
        return cache_surf

    else:
        # Single chunk map of player's current layer (Used by live GPS)
        base_layer = game.all_map_layers.get(current_layer, getattr(game, 'map_data', []))
        if not base_layer:
            return None

        map_height = len(base_layer)
        map_width = len(base_layer[0]) if map_height > 0 else 0

        cache_surf = pygame.Surface((map_width, map_height))
        cache_surf.fill(bg_fill)
        pixels = pygame.PixelArray(cache_surf)

        ground_layer = game.all_ground_layers.get(current_layer, [])
        roof_layer = game.all_roof_layers.get(current_layer, [])

        for y in range(map_height):
            for x in range(map_width):
                g_char = ground_layer[y][x] if y < len(ground_layer) and x < len(ground_layer[y]) else ' '
                b_char = base_layer[y][x] if y < len(base_layer) and x < len(base_layer[y]) else ' '
                r_char = roof_layer[y][x] if y < len(roof_layer) and x < len(roof_layer[y]) else ' '

                col = get_map_pixel_color(g_char, b_char, r_char, tile_defs, layer_idx=current_layer)
                try:
                    pixels[x, y] = col
                except IndexError:
                    pass

        pixels.close()
        return cache_surf

def get_fogged_minimap_surface(game, base_cache_surf, current_layer, current_map_file):
    """Returns a black Fog-of-War masked minimap surface showing only explored tiles."""
    if not base_cache_surf:
        return None

    map_w, map_h = base_cache_surf.get_size()
    expected_size = map_w * map_h
    gps_explored = getattr(game, 'gps_explored_tiles', None)

    if (not isinstance(gps_explored, (bytearray, bytes)) or
        len(gps_explored) != expected_size or
        getattr(game, 'gps_explored_map_name', '') != current_map_file):

        if not hasattr(game, 'gps_explored_dict'):
            game.gps_explored_dict = {}
        cached_exp = game.gps_explored_dict.get(current_map_file)
        if isinstance(cached_exp, (bytearray, bytes)) and len(cached_exp) == expected_size:
            game.gps_explored_tiles = cached_exp
        else:
            game.gps_explored_tiles = bytearray(expected_size)
            game.gps_explored_dict[current_map_file] = game.gps_explored_tiles
        game.gps_explored_map_name = current_map_file
        gps_explored = game.gps_explored_tiles
        game._gps_fog_surface = None

    fog_surf = getattr(game, '_gps_fog_surface', None)
    if (fog_surf is None or
        fog_surf.get_size() != (map_w, map_h) or
        getattr(game, '_gps_fog_layer', None) != current_layer or
        getattr(game, '_gps_fog_map_file', None) != current_map_file):

        fog_surf = base_cache_surf.copy()
        mask_surf = pygame.Surface((map_w, map_h))
        mask_surf.fill((0, 0, 0))

        for ty in range(map_h):
            row_off = ty * map_w
            in_run = False
            run_start = 0
            for tx in range(map_w):
                if gps_explored[row_off + tx]:
                    if not in_run:
                        in_run = True
                        run_start = tx
                else:
                    if in_run:
                        pygame.draw.rect(mask_surf, (255, 255, 255), (run_start, ty, tx - run_start, 1))
                        in_run = False
            if in_run:
                pygame.draw.rect(mask_surf, (255, 255, 255), (run_start, ty, map_w - run_start, 1))

        fog_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        game._gps_fog_surface = fog_surf
        game._gps_fog_layer = current_layer
        game._gps_fog_map_file = current_map_file
        if hasattr(game, '_gps_pending_reveals'):
            game._gps_pending_reveals.clear()
        return fog_surf

    pending = getattr(game, '_gps_pending_reveals', None)
    if pending:
        for tx, ty in list(pending):
            if 0 <= tx < map_w and 0 <= ty < map_h:
                fog_surf.set_at((tx, ty), base_cache_surf.get_at((tx, ty)))
        pending.clear()

    return fog_surf

def draw_map_tab(surface, game, modal, assets, full_map=False, target_chunk=None, target_layer=None, is_view_only=False, bottom_pad=0):
    if 'map_zoom' not in modal:
        modal['map_zoom'] = 6
    if 'map_offset' not in modal:
        modal['map_offset'] = (0, 0)

    is_mobile_modal = (modal.get('type') == 'mobile')
    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    mouse_just_pressed = mouse_pressed and not modal.get('_last_map_click', False)
    modal['_last_map_click'] = mouse_pressed

    # --- MOBILE MODAL DROPDOWN HANDLING ---
    active_held_map_name = None
    if is_mobile_modal:
        held_maps = get_player_held_maps(game.player)
        held_map_names = [m.name for m in held_maps]

        if 'selected_map_name' not in modal or (modal['selected_map_name'] != 'GPS (Live)' and modal['selected_map_name'] not in held_map_names):
            modal['selected_map_name'] = 'GPS (Live)'

        # If a held map is selected, override display parameters
        if modal['selected_map_name'] != 'GPS (Live)':
            active_held_map_name = modal['selected_map_name']
            parsed_info = parse_map_item_info(active_held_map_name)
            full_map = parsed_info['full_map']
            target_chunk = parsed_info['target_chunk']
            target_layer = parsed_info['layer']
            is_view_only = True
        else:
            # GPS (Live) mode
            full_map = False
            target_chunk = None
            target_layer = getattr(game, 'current_layer_index', 1)
            is_view_only = False

        # Dropdown button dimensions
        dd_btn_h = 22
        dd_rect = pygame.Rect(modal['rect'].x + 10, modal['rect'].y + 68, modal['rect'].width - 20, dd_btn_h)
        modal['map_dropdown_rect'] = dd_rect

        content_y_start = dd_rect.bottom + 4
        content_height = modal['rect'].bottom - content_y_start - 8
    else:
        content_y_start = modal['rect'].y + 50
        content_height = modal['rect'].height - 60 - bottom_pad

    content_x_start = modal['rect'].x + 10
    content_width = modal['rect'].width - 20

    map_area_rect = pygame.Rect(content_x_start, content_y_start, content_width, content_height)
    modal['map_area_rect'] = map_area_rect

    # Map dragging logic
    if 'is_dragging_map' not in modal:
        modal['is_dragging_map'] = False
    if 'last_drag_pos' not in modal:
        modal['last_drag_pos'] = (0, 0)

    dd_open = modal.get('mobile_map_dd_open', False)

    if mouse_pressed and not dd_open:
        if modal.get('is_dragging_map', False):
            dx = mouse_pos[0] - modal['last_drag_pos'][0]
            dy = mouse_pos[1] - modal['last_drag_pos'][1]
            zoom = float(modal.get('map_zoom', 6))
            if zoom <= 0: zoom = 1.0
            modal['map_offset'] = (
                modal['map_offset'][0] + (dx / zoom),
                modal['map_offset'][1] + (dy / zoom)
            )
            modal['last_drag_pos'] = mouse_pos
    else:
        modal['is_dragging_map'] = False

    pygame.draw.rect(surface, (0, 0, 0) if not is_view_only else (20, 20, 20), map_area_rect)
    if not game.player:
        return

    # Cache key per layer, full_map, and chunk
    current_layer = target_layer if target_layer is not None else getattr(game, 'current_layer_index', 1)
    current_map_file = getattr(game.map_manager, 'current_map_filename', '')
    cache_key = f'cached_minimap_L{current_layer}_F{full_map}_C{target_chunk}'

    needs_update = False
    if cache_key not in modal:
        needs_update = True
    elif modal.get(f'{cache_key}_layer') != current_layer:
        needs_update = True
    elif not full_map and not target_chunk and modal.get(f'{cache_key}_file') != current_map_file:
        needs_update = True

    if needs_update:
        modal[cache_key] = generate_minimap_cache(game, full_map=full_map, target_chunk=target_chunk, target_layer=current_layer)
        modal[f'{cache_key}_layer'] = current_layer
        modal[f'{cache_key}_file'] = current_map_file

    cached_surf = modal.get(cache_key)

    if cached_surf and not is_view_only:
        cached_surf = get_fogged_minimap_surface(game, cached_surf, current_layer, current_map_file)

    if cached_surf:
        map_zoom = float(modal.get('map_zoom', 6))
        chunk_size = getattr(game, 'CHUNK_SIZE', 128)
        map_w, map_h = cached_surf.get_size()

        gx_offset, gy_offset = 0, 0
        if target_chunk:
            focus_x = chunk_size // 2
            focus_y = chunk_size // 2
        elif full_map:
            if is_view_only:
                focus_x = map_w // 2
                focus_y = map_h // 2
            else:
                match = re.search(r'map_L\d+_(\d+)_(\d+)_map\.csv', current_map_file)
                gx_offset = int(match.group(1)) * chunk_size if match else 0
                gy_offset = int(match.group(2)) * chunk_size if match else 0
                focus_x = (game.player.rect.centerx // TILE_SIZE) + gx_offset
                focus_y = (game.player.rect.centery // TILE_SIZE) + gy_offset
        else:
            focus_x = game.player.rect.centerx // TILE_SIZE
            focus_y = game.player.rect.centery // TILE_SIZE

        off_x, off_y = modal.get('map_offset', (0, 0))
        tiles_in_view_w = map_area_rect.width / map_zoom
        tiles_in_view_h = map_area_rect.height / map_zoom

        max_off_x = focus_x - (tiles_in_view_w / 2)
        min_off_x = focus_x + (tiles_in_view_w / 2) - map_w
        max_off_y = focus_y - (tiles_in_view_h / 2)
        min_off_y = focus_y + (tiles_in_view_h / 2) - map_h

        clamped_x = focus_x - map_w / 2 if tiles_in_view_w > map_w else max(min_off_x, min(off_x, max_off_x))
        clamped_y = focus_y - map_h / 2 if tiles_in_view_h > map_h else max(min_off_y, min(off_y, max_off_y))

        modal['map_offset'] = (clamped_x, clamped_y)
        off_x, off_y = clamped_x, clamped_y

        src_x = (focus_x - (tiles_in_view_w / 2)) - off_x
        src_y = (focus_y - (tiles_in_view_h / 2)) - off_y

        src_x_int = int(math.floor(src_x))
        src_y_int = int(math.floor(src_y))
        src_w_int = int(math.ceil(tiles_in_view_w)) + 1
        src_h_int = int(math.ceil(tiles_in_view_h)) + 1

        src_rect = pygame.Rect(src_x_int, src_y_int, src_w_int, src_h_int)
        map_rect = cached_surf.get_rect()
        clipped_src = src_rect.clip(map_rect)

        if clipped_src.width > 0 and clipped_src.height > 0:
            sub_surf = cached_surf.subsurface(clipped_src)
            dest_w = int(clipped_src.width * map_zoom)
            dest_h = int(clipped_src.height * map_zoom)

            if dest_w > 0 and dest_h > 0:
                scaled_surf = pygame.transform.scale(sub_surf, (dest_w, dest_h))
                draw_offset_x = (clipped_src.x - src_x) * map_zoom
                draw_offset_y = (clipped_src.y - src_y) * map_zoom
                
                # Clip strictly to map_area_rect
                old_clip = surface.get_clip()
                surface.set_clip(map_area_rect)
                surface.blit(scaled_surf, (map_area_rect.x + draw_offset_x, map_area_rect.y + draw_offset_y))
                surface.set_clip(old_clip)

        # Render Location Marker & Radar Dots ONLY on Live GPS (never on view-only maps)
        if not is_view_only:
            screen_player_x = map_area_rect.x + (focus_x - src_x) * map_zoom
            screen_player_y = map_area_rect.y + (focus_y - src_y) * map_zoom
            marker_size = max(8, int(map_zoom * 1.5))
            player_rect = pygame.Rect(0, 0, marker_size, marker_size)
            player_rect.center = (screen_player_x + (map_zoom / 2), screen_player_y + (map_zoom / 2))

            if map_area_rect.collidepoint(player_rect.center):
                pygame.draw.rect(surface, MINIMAP_PLAYER_COLOR, player_rect, 0)
                pygame.draw.rect(surface, (0, 0, 0), player_rect, 1)

            # Active SD Card Radar Modules
            active_caps = set()
            for card in getattr(game, 'app_state', {}).get('slots', []):
                if not card: continue
                map_val = getattr(card, 'map_value', None)
                if not map_val and hasattr(card, 'properties') and isinstance(card.properties, dict):
                    map_val = card.properties.get('map', {}).get('value')
                if not map_val and hasattr(card, 'name') and card.name in ITEM_TEMPLATES:
                    map_val = ITEM_TEMPLATES[card.name].get('properties', {}).get('map', {}).get('value')
                if map_val: active_caps.add(map_val.strip().lower())

            if 'show_zombies' in active_caps:
                for z in getattr(game, 'zombies', []):
                    if getattr(z, 'is_dead', False): continue
                    zx = (z.rect.centerx // TILE_SIZE) + gx_offset
                    zy = (z.rect.centery // TILE_SIZE) + gy_offset
                    sx = map_area_rect.x + (zx - src_x) * map_zoom + (map_zoom / 2)
                    sy = map_area_rect.y + (zy - src_y) * map_zoom + (map_zoom / 2)
                    if map_area_rect.collidepoint(sx, sy):
                        pygame.draw.circle(surface, (220, 40, 40), (int(sx), int(sy)), 3)

            if 'show_animals' in active_caps:
                animal_list = getattr(game, 'active_animals', [])
                if not animal_list:
                    animal_list = [i for i in getattr(game, 'items_on_ground', []) if getattr(i, 'type', '') == 'animal']
                for a in animal_list:
                    if getattr(a, 'is_dead', False): continue
                    ax = (a.rect.centerx // TILE_SIZE) + gx_offset
                    ay = (a.rect.centery // TILE_SIZE) + gy_offset
                    sx = map_area_rect.x + (ax - src_x) * map_zoom + (map_zoom / 2)
                    sy = map_area_rect.y + (ay - src_y) * map_zoom + (map_zoom / 2)
                    if map_area_rect.collidepoint(sx, sy):
                        pygame.draw.circle(surface, (240, 220, 50), (int(sx), int(sy)), 3)

            if 'show_vehicles' in active_caps:
                veh_list = getattr(game, 'vehicles', [])
                if not veh_list and hasattr(game, 'map_manager'):
                    veh_list = getattr(game.map_manager, 'vehicles', [])
                for v in veh_list:
                    vx = (v.rect.centerx // TILE_SIZE) + gx_offset
                    vy = (v.rect.centery // TILE_SIZE) + gy_offset
                    sx = map_area_rect.x + (vx - src_x) * map_zoom + (map_zoom / 2)
                    sy = map_area_rect.y + (vy - src_y) * map_zoom + (map_zoom / 2)
                    if map_area_rect.collidepoint(sx, sy):
                        pygame.draw.circle(surface, (40, 140, 255), (int(sx), int(sy)), 3)

            if 'show_friendly_npc' in active_caps or 'show_static_npc' in active_caps:
                for npc in getattr(game, 'npcs', []):
                    if getattr(npc, 'is_dead', False): continue
                    if not getattr(npc, 'is_friendly', True): continue
                    nx = (npc.rect.centerx // TILE_SIZE) + gx_offset
                    ny = (npc.rect.centery // TILE_SIZE) + gy_offset
                    sx = map_area_rect.x + (nx - src_x) * map_zoom + (map_zoom / 2)
                    sy = map_area_rect.y + (ny - src_y) * map_zoom + (map_zoom / 2)
                    if map_area_rect.collidepoint(sx, sy):
                        pygame.draw.circle(surface, (255, 140, 0), (int(sx), int(sy)), 3)

            if 'show_hostile_npc' in active_caps:
                for npc in getattr(game, 'npcs', []):
                    if getattr(npc, 'is_dead', False): continue
                    if getattr(npc, 'is_friendly', True): continue
                    nx = (npc.rect.centerx // TILE_SIZE) + gx_offset
                    ny = (npc.rect.centery // TILE_SIZE) + gy_offset
                    sx = map_area_rect.x + (nx - src_x) * map_zoom + (map_zoom / 2)
                    sy = map_area_rect.y + (ny - src_y) * map_zoom + (map_zoom / 2)
                    if map_area_rect.collidepoint(sx, sy):
                        pygame.draw.circle(surface, (255, 50, 50), (int(sx), int(sy)), 3)

    modal['_map_transform'] = (map_area_rect, src_x, src_y, map_zoom)

    # Render saved / pending ink strokes & written notes on map items
    map_item_ref = modal.get('item')
    if is_mobile_modal and active_held_map_name:
        held_obj = next((m for m in get_player_held_maps(game.player) if m.name == active_held_map_name), None)
        if held_obj:
            map_item_ref = held_obj

    old_clip = surface.get_clip()
    surface.set_clip(map_area_rect)

    if map_item_ref:
        strokes_to_draw = modal.get('pending_strokes') if modal.get('type') == 'big_map' else getattr(map_item_ref, 'map_strokes', [])
        if strokes_to_draw:
            pen_size_scales = (0.25, 0.60, 1.15)
            for stroke in strokes_to_draw:
                pts = stroke.get('points', [])
                col = tuple(stroke.get('color', (220, 50, 50)))
                s_idx = int(stroke.get('size', 0))
                s_idx = max(0, min(2, s_idx))
                stroke_w = max(1, int(round(map_zoom * pen_size_scales[s_idx])))
                if len(pts) >= 2:
                    screen_pts = [
                        (int(map_area_rect.x + (px - src_x) * map_zoom), int(map_area_rect.y + (py - src_y) * map_zoom))
                        for px, py in pts
                    ]
                    pygame.draw.lines(surface, col, False, screen_pts, stroke_w)
                elif len(pts) == 1:
                    px, py = pts[0]
                    sx = int(map_area_rect.x + (px - src_x) * map_zoom)
                    sy = int(map_area_rect.y + (py - src_y) * map_zoom)
                    pygame.draw.circle(surface, col, (sx, sy), max(1, stroke_w // 2))

            texts_to_draw = modal.get('pending_texts') if modal.get('type') == 'big_map' else getattr(map_item_ref, 'map_texts', [])
            if texts_to_draw:
                text_fonts = (font_14, font_12, font_16)
                for t_entry in texts_to_draw:
                    txt_val = str(t_entry.get('text', '')).strip()
                    if not txt_val:
                        continue
                    tx, ty = t_entry.get('x', 0), t_entry.get('y', 0)
                    sx = int(map_area_rect.x + (tx - src_x) * map_zoom)
                    sy = int(map_area_rect.y + (ty - src_y) * map_zoom)
                    col = tuple(t_entry.get('color', (245, 245, 245)))
                    s_idx = max(0, min(2, int(t_entry.get('size', 1))))
                    t_font = text_fonts[s_idx]
                    outline_col = (220, 220, 220) if (col[0] + col[1] + col[2]) < 90 else (0, 0, 0)
                    txt_surf = t_font.render(txt_val, False, col)
                    sh_surf = t_font.render(txt_val, False, outline_col)
                    draw_rect = txt_surf.get_rect(center=(sx, sy))
                    t_entry['_screen_rect'] = draw_rect
                    if map_area_rect.colliderect(draw_rect):
                        surface.blit(sh_surf, (draw_rect.x + 1, draw_rect.y + 1))
                        surface.blit(txt_surf, draw_rect.topleft)

    # Per-chunk coordinate tags in top-right of each chunk on full maps
    if full_map and (chunk_size * map_zoom) >= 26:
        chunks_w_cnt = max(1, map_w // chunk_size)
        chunks_h_cnt = max(1, map_h // chunk_size)
        active_c = getattr(getattr(game, 'generator', None), 'active_chunks', None)
        for cgx in range(chunks_w_cnt):
            for cgy in range(chunks_h_cnt):
                if active_c is not None and (cgx, cgy) not in active_c:
                    continue
                c_right_x = int(map_area_rect.x + ((cgx + 1) * chunk_size - src_x) * map_zoom)
                c_top_y = int(map_area_rect.y + (cgy * chunk_size - src_y) * map_zoom)
                if c_right_x < map_area_rect.left or c_top_y > map_area_rect.bottom:
                    continue
                c_lbl = f"{cgx}_{cgy}"
                c_surf = font_14.render(c_lbl, False, WHITE)
                c_sh = font_14.render(c_lbl, False, BLACK)
                tx_p = c_right_x - c_surf.get_width() - 3
                ty_p = c_top_y + 3
                if map_area_rect.collidepoint(tx_p, ty_p):
                    surface.blit(c_sh, (tx_p + 1, ty_p + 1))
                    surface.blit(c_surf, (tx_p, ty_p))

    # Display written text note overlay at bottom-left of big_map if present
    if modal.get('type') == 'big_map' and map_item_ref and getattr(map_item_ref, 'text', None) and str(map_item_ref.text).strip():
        note_lines = [ln for ln in str(map_item_ref.text).strip().split('\n') if ln.strip()][:3]
        if note_lines:
            line_h = font_14.get_height() + 3
            max_nw = min(map_area_rect.width - 16, max(font_14.size(ln)[0] for ln in note_lines) + 12)
            nh = len(note_lines) * line_h + 8
            note_box = pygame.Rect(map_area_rect.x + 6, map_area_rect.bottom - nh - 6, max_nw, nh)
            note_bg = pygame.Surface((note_box.width, note_box.height), pygame.SRCALPHA)
            note_bg.fill((15, 15, 15, 200))
            surface.blit(note_bg, note_box.topleft)
            pygame.draw.rect(surface, (120, 120, 120), note_box, 1, border_radius=3)
            ny = note_box.y + 4
            for ln in note_lines:
                ns = font_14.render(ln, False, (230, 230, 200))
                surface.blit(ns, (note_box.x + 6, ny))
                ny += line_h

    # Top-Right Map Coordinates in small font (font_14)
    coord_text = f"L{current_layer}"
    if target_chunk:
        coord_text = f"L{current_layer} {target_chunk[0]}_{target_chunk[1]}"
    elif full_map:
        if map_area_rect.collidepoint(mouse_pos) and map_zoom > 0:
            h_tx = src_x + (mouse_pos[0] - map_area_rect.x) / map_zoom
            h_ty = src_y + (mouse_pos[1] - map_area_rect.y) / map_zoom
            h_gx = max(0, int(h_tx // chunk_size))
            h_gy = max(0, int(h_ty // chunk_size))
            coord_text = f"L{current_layer} {h_gx}_{h_gy}"
        else:
            cw_n = max(1, map_w // chunk_size)
            ch_n = max(1, map_h // chunk_size)
            coord_text = f"L{current_layer} ({cw_n}x{ch_n})"
    else:
        m_cur = re.search(r'map_L\d+_(\d+)_(\d+)_map\.csv', current_map_file)
        if m_cur:
            coord_text = f"L{current_layer} {m_cur.group(1)}_{m_cur.group(2)}"

    c_txt_surf = font_14.render(coord_text, False, YELLOW)
    pill_w = c_txt_surf.get_width() + 8
    pill_h = c_txt_surf.get_height() + 6
    pill_rect = pygame.Rect(map_area_rect.right - pill_w - 4, map_area_rect.y + 4, pill_w, pill_h)
    pill_bg = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
    pill_bg.fill((15, 15, 15, 200))
    surface.blit(pill_bg, pill_rect.topleft)
    pygame.draw.rect(surface, (80, 80, 80), pill_rect, 1, border_radius=2)
    surface.blit(c_txt_surf, (pill_rect.x + 4, pill_rect.y + 3))

    surface.set_clip(old_clip)

    # --- RENDER DROPDOWN CONTROLS (MOBILE PHONE ONLY) ---
    if is_mobile_modal:
        dd_rect = modal.get('map_dropdown_rect')
        current_map_label = modal.get('selected_map_name', 'GPS (Live)')
        if current_map_label == 'GPS (Live)':
            disp_label = f"GPS (L{getattr(game, 'current_layer_index', 1)})"
        else:
            disp_label = tr('item', current_map_label)
            if len(disp_label) > 22:
                disp_label = disp_label[:20] + ".."

        # Dropdown Button Bar
        is_dd_hovered = dd_rect.collidepoint(mouse_pos)
        pygame.draw.rect(surface, (40, 40, 40) if is_dd_hovered else (28, 28, 28), dd_rect, border_radius=3)
        pygame.draw.rect(surface, YELLOW if is_dd_hovered else GRAY_60, dd_rect, 1, border_radius=3)

        label_surf = font_12.render(disp_label, False, YELLOW if modal.get('selected_map_name') == 'GPS (Live)' else WHITE)
        surface.blit(label_surf, (dd_rect.x + 8, dd_rect.centery - label_surf.get_height() // 2))

        arrow_char = "^" if modal.get('mobile_map_dd_open') else "v"
        arrow_surf = font_12.render(arrow_char, False, WHITE)
        surface.blit(arrow_surf, (dd_rect.right - 16, dd_rect.centery - arrow_surf.get_height() // 2))

        # Handle opening dropdown on button click
        if mouse_just_pressed and is_dd_hovered:
            modal['mobile_map_dd_open'] = not modal.get('mobile_map_dd_open', False)

        # Draw Open Dropdown Popup Menu on top
        if modal.get('mobile_map_dd_open'):
            options = ['GPS (Live)'] + [m.name for m in get_player_held_maps(game.player)]
            opt_h = 20
            max_visible = 4
            total_items = len(options)
            total_h = total_items * opt_h

            visible_count = min(total_items, max_visible)
            popup_h = visible_count * opt_h
            popup_rect = pygame.Rect(dd_rect.x, dd_rect.bottom + 1, dd_rect.width, popup_h)
            modal['map_dropdown_popup_rect'] = popup_rect

            max_scroll = max(0, total_h - popup_h)
            modal['mobile_map_dd_max_scroll'] = max_scroll

            if 'mobile_map_dd_scroll_y' not in modal:
                modal['mobile_map_dd_scroll_y'] = 0.0

            needs_scrollbar = total_items > max_visible
            bar_w = 6 if needs_scrollbar else 0
            bar_rect = pygame.Rect(popup_rect.right - bar_w - 2, popup_rect.y + 2, bar_w, popup_h - 4) if needs_scrollbar else None
            opt_w = popup_rect.width - (bar_w + 4) if needs_scrollbar else popup_rect.width

            # --- Scrollbar Handle Dragging ---
            if needs_scrollbar and bar_rect:
                handle_h = max(14, int((popup_h / max(1, total_h)) * bar_rect.height))
                track_avail = max(1, bar_rect.height - handle_h)
                scroll_pct = modal['mobile_map_dd_scroll_y'] / max(1, max_scroll)
                handle_y = bar_rect.y + int(scroll_pct * track_avail)
                handle_rect = pygame.Rect(bar_rect.x, handle_y, bar_rect.width, handle_h)

                if mouse_just_pressed:
                    if handle_rect.collidepoint(mouse_pos):
                        modal['map_dd_dragging'] = True
                        modal['map_dd_drag_offset'] = mouse_pos[1] - handle_y
                    elif bar_rect.collidepoint(mouse_pos):
                        modal['map_dd_dragging'] = True
                        modal['map_dd_drag_offset'] = handle_h // 2
                        rel_y = mouse_pos[1] - bar_rect.y - (handle_h // 2)
                        pct = max(0.0, min(1.0, rel_y / track_avail))
                        modal['mobile_map_dd_scroll_y'] = pct * max_scroll

                if mouse_pressed and modal.get('map_dd_dragging'):
                    rel_y = mouse_pos[1] - bar_rect.y - modal.get('map_dd_drag_offset', handle_h // 2)
                    pct = max(0.0, min(1.0, rel_y / track_avail))
                    modal['mobile_map_dd_scroll_y'] = pct * max_scroll
            else:
                modal['map_dd_dragging'] = False

            if not mouse_pressed:
                modal['map_dd_dragging'] = False

            scroll_y = max(0.0, min(modal['mobile_map_dd_scroll_y'], float(max_scroll)))
            modal['mobile_map_dd_scroll_y'] = scroll_y

            # Popup Base
            pygame.draw.rect(surface, (20, 20, 20), popup_rect, border_radius=3)
            pygame.draw.rect(surface, WHITE, popup_rect, 1, border_radius=3)

            # Render Clipped Options List
            old_clip = surface.get_clip()
            clip_rect = pygame.Rect(popup_rect.x, popup_rect.y, opt_w, popup_h)
            surface.set_clip(clip_rect)

            clicked_opt = None
            is_over_bar = bar_rect.collidepoint(mouse_pos) if (needs_scrollbar and bar_rect) else False

            for idx, opt_name in enumerate(options):
                row_y = popup_rect.y + (idx * opt_h) - int(scroll_y)
                row_rect = pygame.Rect(popup_rect.x, row_y, opt_w, opt_h)

                if row_rect.bottom > popup_rect.top and row_rect.top < popup_rect.bottom:
                    row_hover = row_rect.collidepoint(mouse_pos) and clip_rect.collidepoint(mouse_pos) and not is_over_bar
                    if row_hover:
                        pygame.draw.rect(surface, (50, 50, 50), row_rect)
                        if mouse_just_pressed and not modal.get('map_dd_dragging'):
                            clicked_opt = opt_name

                    if opt_name == 'GPS (Live)':
                        row_txt = f"GPS (L{getattr(game, 'current_layer_index', 1)})"
                        row_color = YELLOW
                    else:
                        row_txt = tr('item', opt_name)
                        row_color = WHITE

                    # Truncate text cleanly to prevent overflowing into scrollbar
                    max_text_w = opt_w - 12
                    while font_12.size(row_txt)[0] > max_text_w and len(row_txt) > 4:
                        row_txt = row_txt[:-1]
                    if row_txt != tr('item', opt_name) and opt_name != 'GPS (Live)':
                        row_txt += ".."

                    r_surf = font_12.render(row_txt, False, row_color)
                    surface.blit(r_surf, (row_rect.x + 6, row_rect.centery - r_surf.get_height() // 2))

            surface.set_clip(old_clip)

            # Draw Scrollbar
            if needs_scrollbar and bar_rect:
                pygame.draw.rect(surface, DARK_GRAY, bar_rect, border_radius=2)
                handle_h = max(14, int((popup_h / max(1, total_h)) * bar_rect.height))
                track_avail = max(1, bar_rect.height - handle_h)
                scroll_pct = scroll_y / max(1, max_scroll)
                handle_y = bar_rect.y + int(scroll_pct * track_avail)
                handle_rect = pygame.Rect(bar_rect.x, handle_y, bar_rect.width, handle_h)
                pygame.draw.rect(surface, GRAY, handle_rect, border_radius=2)

            # Handle Selection / Close
            if mouse_just_pressed and not modal.get('map_dd_dragging'):
                if clicked_opt:
                    modal['selected_map_name'] = clicked_opt
                    modal['map_offset'] = (0, 0)
                    modal['mobile_map_dd_open'] = False
                elif not is_dd_hovered and not popup_rect.collidepoint(mouse_pos):
                    modal['mobile_map_dd_open'] = False
        else:
            modal['map_dropdown_popup_rect'] = None
            modal['map_dd_dragging'] = False

MAP_PEN_COLORS = [
    ('Red', [220, 50, 50]),
    ('White', [245, 245, 245]),
    ('Black', [15, 15, 15]),
    ('Marine Blue', [0, 55, 140]),
]
MAP_PEN_SIZE_SCALES = (0.25, 0.60, 1.15)
MAP_ERASER_RADII = (0.8, 2.0, 4.0)


def _erase_map_region(modal, ex, ey, r_tiles, screen_pos, map_zoom):
    """Erases only the parts of strokes and placed textboxes touched by the eraser radius."""
    r_sq = r_tiles * r_tiles
    step_max = max(0.25, r_tiles * 0.35)
    new_strokes = []

    for stroke in modal.get('pending_strokes', []):
        pts = stroke.get('points', [])
        if not pts:
            continue
        col = stroke.get('color', [220, 50, 50])
        sz = stroke.get('size', 0)

        # Subdivide long segments so erasing cuts through straight lines cleanly
        dense_pts = [pts[0]]
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            seg_len = math.hypot(bx - ax, by - ay)
            if seg_len > step_max:
                n_sub = int(math.ceil(seg_len / step_max))
                for s_i in range(1, n_sub + 1):
                    t = s_i / float(n_sub)
                    dense_pts.append([ax + (bx - ax) * t, ay + (by - ay) * t])
            else:
                dense_pts.append([bx, by])

        cur_run = []
        for pt in dense_pts:
            if (pt[0] - ex) ** 2 + (pt[1] - ey) ** 2 > r_sq:
                cur_run.append(pt)
            else:
                if cur_run:
                    new_strokes.append({'color': list(col), 'size': sz, 'points': cur_run})
                    cur_run = []
        if cur_run:
            new_strokes.append({'color': list(col), 'size': sz, 'points': cur_run})

    modal['pending_strokes'] = new_strokes

    # Erase any placed textbox overlapping the eraser circle
    erase_px_r = max(4, int(r_tiles * map_zoom))
    remaining_texts = []
    for t_entry in modal.get('pending_texts', []):
        s_rect = t_entry.get('_screen_rect')
        if s_rect and s_rect.inflate(erase_px_r * 2, erase_px_r * 2).collidepoint(screen_pos):
            continue
        tx, ty = t_entry.get('x', 0), t_entry.get('y', 0)
        if (tx - ex) ** 2 + (ty - ey) ** 2 <= r_sq:
            continue
        remaining_texts.append(t_entry)
    modal['pending_texts'] = remaining_texts


def draw_big_map_modal(surface, game, modal, assets):
    item = modal['item']
    base_modal = BaseModal(surface, modal, assets, f"{item.name}")
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    if 'pending_strokes' not in modal:
        modal['pending_strokes'] = [
            {'color': list(s.get('color', [220, 50, 50])), 'size': int(s.get('size', 0)), 'points': [list(p) for p in s.get('points', [])]}
            for s in (getattr(item, 'map_strokes', []) or [])
        ]
    if 'pending_texts' not in modal:
        modal['pending_texts'] = [
            dict(t) for t in (getattr(item, 'map_texts', []) or [])
        ]

    modal.setdefault('map_tool', 'pan')
    modal.setdefault('map_pen_color', [220, 50, 50])  # Default Red
    modal.setdefault('map_pen_size', 1)               # 0=S, 1=M, 2=L
    modal.setdefault('map_eraser_size', 1)            # 0=S, 1=M, 2=L
    modal.setdefault('map_text_input', '')
    modal.setdefault('map_text_active', False)

    from core.entities.item.item_helpers import player_has_any_item
    from core.messages import display_message

    has_pen = player_has_any_item(game.player, ('Pen',)) if getattr(game, 'player', None) else False
    has_pencil = player_has_any_item(game.player, ('Pencil',)) if getattr(game, 'player', None) else False
    has_writer = has_pen or has_pencil
    has_eraser = player_has_any_item(game.player, ('Eraser',)) if getattr(game, 'player', None) else False

    if not has_writer and modal.get('map_tool') in ('draw', 'text'):
        modal['map_tool'] = 'pan'
        modal['map_text_active'] = False
    if not has_eraser and modal.get('map_tool') == 'erase':
        modal['map_tool'] = 'pan'

    modal['map_draw_mode'] = (modal.get('map_tool') == 'draw')

    map_info = parse_map_item_info(item)
    draw_map_tab(
        surface, game, modal, assets,
        full_map=map_info['full_map'],
        target_chunk=map_info['target_chunk'],
        target_layer=map_info['layer'],
        is_view_only=True,
        bottom_pad=72
    )

    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    prev_pressed = modal.get('_big_map_prev_click', False)
    mouse_just_pressed = mouse_pressed and not prev_pressed
    modal['_big_map_prev_click'] = mouse_pressed

    active_tool = modal.get('map_tool', 'pan')
    pen_color = list(modal.get('map_pen_color', [220, 50, 50]))
    pen_size = int(modal.get('map_pen_size', 1))
    eraser_size = int(modal.get('map_eraser_size', 1))

    # --- Canvas Tool Interaction & Cursor Previews ---
    transform = modal.get('_map_transform')
    if transform:
        map_area_rect, src_x, src_y, map_zoom = transform
        in_map = map_area_rect.collidepoint(mouse_pos) and map_zoom > 0

        if in_map:
            tx = src_x + (mouse_pos[0] - map_area_rect.x) / map_zoom
            ty = src_y + (mouse_pos[1] - map_area_rect.y) / map_zoom

            if active_tool == 'draw' and has_writer:
                prev_c = surface.get_clip()
                surface.set_clip(map_area_rect)
                brush_r = max(2, int(round(MAP_PEN_SIZE_SCALES[pen_size] * map_zoom * 0.5)))
                pygame.draw.circle(surface, tuple(pen_color), (int(mouse_pos[0]), int(mouse_pos[1])), brush_r)
                pygame.draw.circle(surface, WHITE, (int(mouse_pos[0]), int(mouse_pos[1])), brush_r + 1, 1)
                surface.set_clip(prev_c)

                if mouse_pressed:
                    if mouse_just_pressed or not modal.get('_is_drawing_stroke', False):
                        modal['pending_strokes'].append({'color': pen_color, 'size': pen_size, 'points': [[tx, ty]]})
                        modal['_is_drawing_stroke'] = True
                    else:
                        cur_pts = modal['pending_strokes'][-1]['points']
                        last_x, last_y = cur_pts[-1]
                        if math.hypot(tx - last_x, ty - last_y) >= max(0.12, 1.5 / map_zoom):
                            cur_pts.append([tx, ty])
                else:
                    modal['_is_drawing_stroke'] = False

            elif active_tool == 'erase' and has_eraser:
                r_tiles = MAP_ERASER_RADII[eraser_size]
                erase_px_r = max(4, int(round(r_tiles * map_zoom)))
                prev_c = surface.get_clip()
                surface.set_clip(map_area_rect)
                pygame.draw.circle(surface, (255, 80, 80), (int(mouse_pos[0]), int(mouse_pos[1])), erase_px_r, 1)
                surface.set_clip(prev_c)

                if mouse_pressed:
                    prev_e = modal.get('_last_erase_tile')
                    if mouse_just_pressed or not prev_e:
                        _erase_map_region(modal, tx, ty, r_tiles, mouse_pos, map_zoom)
                    else:
                        px0, py0 = prev_e
                        dist_e = math.hypot(tx - px0, ty - py0)
                        steps = max(1, int(math.ceil(dist_e / max(0.25, r_tiles * 0.5))))
                        for step_i in range(1, steps + 1):
                            t = step_i / float(steps)
                            ix = px0 + (tx - px0) * t
                            iy = py0 + (ty - py0) * t
                            _erase_map_region(modal, ix, iy, r_tiles, mouse_pos, map_zoom)
                    modal['_last_erase_tile'] = (tx, ty)
                    if mouse_just_pressed and hasattr(game, 'sound_manager'):
                        game.sound_manager.play_sound('eraser.ogg', subdir='ui', game=game, source_pos=None, base_volume=0.35, is_critical=True)
                else:
                    modal['_last_erase_tile'] = None

            elif active_tool == 'text' and has_writer:
                pending_txt = modal.get('map_text_input', '').strip()
                if pending_txt:
                    text_fonts = (font_14, font_12, font_16)
                    p_font = text_fonts[pen_size]
                    p_surf = p_font.render(pending_txt, False, tuple(pen_color))
                    prev_c = surface.get_clip()
                    surface.set_clip(map_area_rect)
                    surface.blit(p_surf, p_surf.get_rect(center=(int(mouse_pos[0]), int(mouse_pos[1]))))
                    surface.set_clip(prev_c)

                    if mouse_just_pressed:
                        modal['pending_texts'].append({
                            'x': tx,
                            'y': ty,
                            'text': pending_txt,
                            'color': pen_color,
                            'size': pen_size
                        })
                        modal['map_text_input'] = ''
                        modal['map_text_active'] = False
                        pygame.key.set_repeat()
                        if hasattr(game, 'sound_manager'):
                            game.sound_manager.play_sound('write.ogg', subdir='ui', game=game, source_pos=None, base_volume=0.4, is_critical=True)
        else:
            modal['_is_drawing_stroke'] = False
            modal['_last_erase_tile'] = None
    else:
        modal['_is_drawing_stroke'] = False
        modal['_last_erase_tile'] = None

    # --- Two-Row Bottom Toolbar ---
    tb_row1_y = modal['rect'].bottom - 68
    tb_row2_y = modal['rect'].bottom - 34
    tb_x = modal['rect'].x + 10
    tb_h = 26

    def _draw_tb_btn(rect, label, active=False, enabled=True, active_col=(40, 95, 140)):
        hov = enabled and rect.collidepoint(mouse_pos)
        if not enabled:
            bg, bd, tc = (32, 32, 32), (55, 55, 55), (100, 100, 100)
        elif active:
            bg, bd, tc = active_col, YELLOW, YELLOW
        elif hov:
            bg, bd, tc = (65, 65, 65), WHITE, YELLOW
        else:
            bg, bd, tc = (42, 42, 42), GRAY_60, WHITE
        pygame.draw.rect(surface, bg, rect, border_radius=4)
        pygame.draw.rect(surface, bd, rect, 1, border_radius=4)
        ts = font_12.render(label, False, tc)
        surface.blit(ts, ts.get_rect(center=rect.center))
        return hov

    # Row 1: Modes, Colors, Sizes, Save
    btn_pan = pygame.Rect(tb_x, tb_row1_y, 50, tb_h)
    btn_draw = pygame.Rect(btn_pan.right + 4, tb_row1_y, 56, tb_h)
    btn_text = pygame.Rect(btn_draw.right + 4, tb_row1_y, 54, tb_h)
    btn_erase = pygame.Rect(btn_text.right + 4, tb_row1_y, 62, tb_h)

    hov_pan = _draw_tb_btn(btn_pan, tr('ui', "Pan"), active=(active_tool == 'pan'))
    hov_draw = _draw_tb_btn(btn_draw, tr('ui', "Draw"), active=(active_tool == 'draw'), enabled=has_writer)
    hov_text = _draw_tb_btn(btn_text, tr('ui', "Text"), active=(active_tool == 'text'), enabled=has_writer)
    hov_erase = _draw_tb_btn(btn_erase, tr('ui', "Erase"), active=(active_tool == 'erase'), enabled=has_eraser, active_col=(130, 45, 45))

    # Color Swatches (Red, White, Black, Marine Blue)
    cur_x = btn_erase.right + 12
    col_lbl = font_12.render(f"{tr('ui', 'Color')}:", False, (190, 190, 190))
    surface.blit(col_lbl, (cur_x, tb_row1_y + 6))
    cur_x += col_lbl.get_width() + 6

    swatch_rects = []
    for c_name, c_rgb in MAP_PEN_COLORS:
        s_rect = pygame.Rect(cur_x, tb_row1_y + 2, 22, 22)
        is_sel = (list(pen_color) == list(c_rgb))
        is_hov_s = has_writer and s_rect.collidepoint(mouse_pos)
        pygame.draw.rect(surface, tuple(c_rgb), s_rect, border_radius=3)
        pygame.draw.rect(surface, YELLOW if is_sel else (WHITE if is_hov_s else GRAY_60), s_rect, 2 if is_sel else 1, border_radius=3)
        swatch_rects.append((s_rect, c_rgb, is_hov_s))
        cur_x += 26

    # Size Selector (controls Eraser size in erase mode, or Pen/Text size otherwise)
    cur_x += 8
    size_lbl = font_12.render(f"{tr('ui', 'Size')}:", False, (190, 190, 190))
    surface.blit(size_lbl, (cur_x, tb_row1_y + 6))
    cur_x += size_lbl.get_width() + 6

    active_size_idx = eraser_size if active_tool == 'erase' else pen_size
    size_enabled = has_eraser if active_tool == 'erase' else has_writer
    size_rects = []
    for idx_s, s_label in enumerate(('S', 'M', 'L')):
        sz_r = pygame.Rect(cur_x, tb_row1_y + 1, 24, 24)
        hov_sz = _draw_tb_btn(sz_r, s_label, active=(active_size_idx == idx_s), enabled=size_enabled)
        size_rects.append((idx_s, hov_sz))
        cur_x += 28

    # Save Button
    can_save = has_writer or has_eraser
    btn_save = pygame.Rect(modal['rect'].right - 10 - 80, tb_row1_y, 80, tb_h)
    hov_save = _draw_tb_btn(btn_save, tr('ui', "Save"), active=can_save, enabled=can_save, active_col=(35, 100, 45))

    # Row 2: Text Input Box for writing textboxes directly onto the map
    txt_lbl = font_12.render(f"{tr('ui', 'Text')}:", False, (190, 190, 190))
    surface.blit(txt_lbl, (tb_x, tb_row2_y + 6))

    input_x = tb_x + txt_lbl.get_width() + 8
    input_w = max(180, modal['rect'].right - 10 - input_x - 165)
    input_rect = pygame.Rect(input_x, tb_row2_y, input_w, tb_h)
    modal['map_text_input_rect'] = input_rect

    is_txt_active = bool(modal.get('map_text_active', False)) and has_writer
    is_txt_hover = has_writer and input_rect.collidepoint(mouse_pos)
    pygame.draw.rect(surface, (15, 15, 15) if is_txt_active else (26, 26, 26), input_rect, border_radius=3)
    pygame.draw.rect(surface, YELLOW if is_txt_active else (WHITE if is_txt_hover else GRAY_60), input_rect, 1, border_radius=3)

    cur_txt = modal.get('map_text_input', '')
    old_c = surface.get_clip()
    surface.set_clip(input_rect.inflate(-8, -4))
    if not has_writer:
        ph_s = font_12.render(tr('msg', "Must have a: Pen, Pencil"), False, (110, 110, 110))
        surface.blit(ph_s, (input_rect.x + 6, input_rect.y + 6))
    elif not cur_txt and not is_txt_active:
        ph_s = font_12.render(tr('ui', "Type text to place on map..."), False, (110, 110, 110))
        surface.blit(ph_s, (input_rect.x + 6, input_rect.y + 6))
    else:
        t_s = font_12.render(cur_txt, False, WHITE)
        surface.blit(t_s, (input_rect.x + 6, input_rect.y + 6))
        if is_txt_active and (pygame.time.get_ticks() // 500) % 2 == 0:
            cx_cur = min(input_rect.right - 6, input_rect.x + 6 + t_s.get_width() + 1)
            pygame.draw.line(surface, WHITE, (cx_cur, input_rect.y + 5), (cx_cur, input_rect.bottom - 5), 1)
    surface.set_clip(old_c)

    # Hint on right side of Row 2
    if active_tool == 'text' and has_writer:
        hint_msg = tr('ui', "Click map to place")
        hint_col = YELLOW
    elif active_tool == 'erase' and has_eraser:
        hint_msg = tr('ui', "Drag to erase")
        hint_col = (255, 130, 130)
    elif active_tool == 'draw' and has_writer:
        hint_msg = tr('ui', "Drag to draw")
        hint_col = (130, 200, 255)
    else:
        hint_msg = tr('ui', "Drag to move map")
        hint_col = (140, 140, 140)
    hint_s = font_12.render(hint_msg, False, hint_col)
    surface.blit(hint_s, (input_rect.right + 10, tb_row2_y + 6))

    # --- Toolbar Click Handling ---
    if mouse_just_pressed:
        if is_txt_hover and has_writer:
            modal['map_text_active'] = True
            modal['map_tool'] = 'text'
            pygame.key.set_repeat(400, 40)
        elif not (transform and transform[0].collidepoint(mouse_pos)):
            if modal.get('map_text_active', False):
                modal['map_text_active'] = False
                pygame.key.set_repeat()

        if hov_pan:
            modal['map_tool'] = 'pan'
            modal['map_text_active'] = False
            pygame.key.set_repeat()
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
        elif hov_draw:
            modal['map_tool'] = 'pan' if active_tool == 'draw' else 'draw'
            modal['map_text_active'] = False
            pygame.key.set_repeat()
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
        elif hov_text:
            modal['map_tool'] = 'text'
            modal['map_text_active'] = True
            pygame.key.set_repeat(400, 40)
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
        elif hov_erase:
            modal['map_tool'] = 'pan' if active_tool == 'erase' else 'erase'
            modal['map_text_active'] = False
            pygame.key.set_repeat()
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
        elif hov_save:
            item.map_strokes = [
                {'color': list(s.get('color', [220, 50, 50])), 'size': int(s.get('size', 0)), 'points': [list(p) for p in s.get('points', [])]}
                for s in modal.get('pending_strokes', [])
            ]
            item.map_texts = [
                {
                    'x': t.get('x', 0),
                    'y': t.get('y', 0),
                    'text': t.get('text', ''),
                    'color': list(t.get('color', [245, 245, 245])),
                    'size': int(t.get('size', 1))
                }
                for t in modal.get('pending_texts', [])
            ]
            item.is_written = bool(item.map_strokes or item.map_texts or (getattr(item, 'text', '') and str(item.text).strip()))
            modal['map_tool'] = 'pan'
            modal['map_text_active'] = False
            pygame.key.set_repeat()
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_sound('write.ogg', subdir='ui', game=game, source_pos=None, base_volume=0.5, is_critical=True)
            display_message(game, tr('msg', "Map saved."))
        else:
            for _, c_rgb, is_hov_s in swatch_rects:
                if is_hov_s:
                    modal['map_pen_color'] = list(c_rgb)
                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_ui_hover()
                    break
            for idx_s, hov_sz in size_rects:
                if hov_sz:
                    if active_tool == 'erase':
                        modal['map_eraser_size'] = idx_s
                    else:
                        modal['map_pen_size'] = idx_s
                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_ui_hover()
                    break

    return [close_button]