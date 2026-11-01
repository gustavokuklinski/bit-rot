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

def draw_map_tab(surface, game, modal, assets, full_map=False, target_chunk=None, target_layer=None, is_view_only=False):
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
        content_height = modal['rect'].height - 60

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

    pygame.draw.rect(surface, (20, 20, 20), map_area_rect)
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

def draw_big_map_modal(surface, game, modal, assets):
    item = modal['item']
    base_modal = BaseModal(surface, modal, assets, f"{item.name}")
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    map_info = parse_map_item_info(item)
    draw_map_tab(
        surface, game, modal, assets,
        full_map=map_info['full_map'],
        target_chunk=map_info['target_chunk'],
        target_layer=map_info['layer'],
        is_view_only=True
    )
    return [close_button]