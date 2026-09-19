# core/draw/world.py

import pygame
import time
import random
import core.data.config
from core.data.config import TILE_SIZE, DARK_GRAY

def _is_transparent_overlay(char):
    if not char:
        return False
    return (
        (char.startswith('dirty_') and char != 'dirty_01') or
        (char.startswith('sand_') and char != 'sand_01') or
        (char.startswith('beach_sand_') and char != 'beach_sand_01') or
        (char.startswith('asphalt_') and char != 'asphalt_01')
    )

def draw_world(game, surface, offset_x, offset_y, view_w, view_h):
    tile_size = TILE_SIZE
    
    # 1. Retrieve active layer data
    base_data = getattr(game, 'map_data', None)
    if not base_data:
        return

    map_h = len(base_data)
    map_w = len(base_data[0]) if map_h > 0 else 0
    if map_w == 0 or map_h == 0:
        return

    ground_data = getattr(game, 'ground_data', None)
    if not ground_data and hasattr(game, 'all_ground_layers'):
        ground_data = game.all_ground_layers.get(game.current_layer_index, [])

    light_data = getattr(game, 'light_data', None)
    if not light_data and hasattr(game, 'all_light_layers'):
        light_data = game.all_light_layers.get(game.current_layer_index, [])

    tm_defs = game.tile_manager.definitions
    shaking_tiles = game.map_manager.shaking_tiles
    current_time = time.time()
    tiles_to_remove = []

    # 2. Viewport Culling: Compute exact visible grid boundaries
    # 1 tile margin prevents visual popping at camera edges
    start_x = max(0, int(-offset_x // tile_size) - 1)
    end_x = min(map_w, int((-offset_x + view_w) // tile_size) + 2)
    start_y = max(0, int(-offset_y // tile_size) - 1)
    end_y = min(map_h, int((-offset_y + view_h) // tile_size) + 2)

    map_mgr = game.map_manager

    # 3. Direct On-Screen Blitting (Zero chunk surface memory allocation)
    for y in range(start_y, end_y):
        row_ground = ground_data[y] if ground_data and y < len(ground_data) else None
        row_base = base_data[y]
        row_light = light_data[y] if light_data and y < len(light_data) else None

        screen_py = int(y * tile_size + offset_y)

        for x in range(start_x, end_x):
            screen_px = int(x * tile_size + offset_x)

            # --- A. Ground Layer ---
            if row_ground and x < len(row_ground):
                g_char = row_ground[x]
                if g_char and g_char != ' ':
                    # Draw solid background underlay for rounded transparent path edges
                    if _is_transparent_overlay(g_char):
                        bg_tile = map_mgr._get_adjacent_bg(ground_data, x, y)
                        if bg_tile in tm_defs:
                            surface.blit(tm_defs[bg_tile]['image'], (screen_px, screen_py))
                    
                    defn = tm_defs.get(g_char)
                    if defn:
                        surface.blit(defn['image'], (screen_px, screen_py))

            # --- B. Base Layer (Walls, Objects) ---
            # If the tile is shaking, skip here so the dedicated shaking section draws it below
            if (x, y) not in shaking_tiles and x < len(row_base):
                b_char = row_base[x]
                if b_char and b_char != ' ':
                    defn = tm_defs.get(b_char)
                    if defn:
                        surface.blit(defn['image'], (screen_px, screen_py))

            # --- C. Light Layer ---
            if row_light and x < len(row_light):
                l_char = row_light[x]
                if l_char and l_char != ' ':
                    defn = tm_defs.get(l_char)
                    if defn:
                        surface.blit(defn['image'], (screen_px, screen_py))

    # --- 4. Draw Placed Barricades over Doors and Windows ---
    map_name = game.map_manager.current_map_filename
    if map_name in game.map_states and 'barricades' in game.map_states[map_name]:
        for (gx, gy), b_data in list(game.map_states[map_name]['barricades'].items()):
            if (gx, gy) in shaking_tiles:
                continue
            screen_px = int(gx * tile_size + offset_x)
            screen_py = int(gy * tile_size + offset_y)
            if -tile_size < screen_px < view_w and -tile_size < screen_py < view_h:
                b_sprite = b_data.get('sprite')
                if not b_sprite and b_data.get('item_name'):
                    from core.entities.item.item import Item
                    item_def = Item.create_from_name(b_data['item_name'])
                    if item_def and item_def.image:
                        b_data['sprite'] = item_def.image
                        b_sprite = item_def.image
                if b_sprite:
                    surface.blit(b_sprite, (screen_px, screen_py))

    # --- 5. Draw Shaking Tiles (Doors, Windows, and Barricades) ---
    for pos, start_t in shaking_tiles.items():
        gx, gy = pos
        screen_px = int(gx * tile_size + offset_x)
        screen_py = int(gy * tile_size + offset_y)
        
        if -tile_size < screen_px < view_w and -tile_size < screen_py < view_h:
            b_key = game.map_data[gy][gx]
            if b_key and b_key != ' ':
                b_def = tm_defs.get(b_key)
                if b_def:
                    draw_x, draw_y = screen_px, screen_py
                    if current_time - start_t > 0.2:
                        tiles_to_remove.append(pos)
                    else:
                        draw_x += random.randint(-2, 2)
                        draw_y += random.randint(-2, 2)

                    # Blit ground underneath to prevent ghost visual artifacts
                    try:
                        g_char = game.all_ground_layers[game.current_layer_index][gy][gx]
                        g_def = tm_defs.get(g_char)
                        if g_def:
                            surface.blit(g_def['image'], (screen_px, screen_py))
                    except Exception:
                        pass

                    surface.blit(b_def['image'], (draw_x, draw_y))

                    # If this tile is barricaded, draw the shaking barricade sprite on top
                    barricade = game.map_manager.get_barricade(gx, gy)
                    if barricade:
                        b_sprite = barricade.get('sprite')
                        if not b_sprite and barricade.get('item_name'):
                            from core.entities.item.item import Item
                            item_def = Item.create_from_name(barricade['item_name'])
                            if item_def and item_def.image:
                                barricade['sprite'] = item_def.image
                                b_sprite = item_def.image
                        if b_sprite:
                            surface.blit(b_sprite, (draw_x, draw_y))
    
    for k in tiles_to_remove:
        if k in game.map_manager.shaking_tiles:
            del game.map_manager.shaking_tiles[k]

    # --- 6. Draw Blood Stains ---
    if hasattr(game, 'blood_stains'):
        min_view_x, max_view_x = -offset_x - 100, -offset_x + view_w + 100
        min_view_y, max_view_y = -offset_y - 100, -offset_y + view_h + 100
        for stain in game.blood_stains:
            stain_wx, stain_wy = stain['pos']
            if not (min_view_x < stain_wx < max_view_x and min_view_y < stain_wy < max_view_y): 
                continue
            pygame.draw.circle(
                surface, 
                stain.get('color', (139, 0, 0)), 
                (int(stain_wx + offset_x), int(stain_wy + offset_y)), 
                stain['size'] // 2
            )