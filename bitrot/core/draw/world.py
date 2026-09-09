import pygame
import time
import random
import core.data.config
from core.data.config import TILE_SIZE

def draw_world(game, surface, offset_x, offset_y, view_w, view_h):
    chunk_size = core.data.config.CHUNK_SIZE
    tile_size = TILE_SIZE
    
    min_world_x, min_world_y = -offset_x, -offset_y
    max_world_x, max_world_y = -offset_x + view_w, -offset_y + view_h
    
    min_chunk_x = int(min_world_x // (chunk_size * tile_size))
    min_chunk_y = int(min_world_y // (chunk_size * tile_size))
    max_chunk_x = int(max_world_x // (chunk_size * tile_size)) + 1
    max_chunk_y = int(max_world_y // (chunk_size * tile_size)) + 1

    map_h = len(game.map_data) if hasattr(game, 'map_data') and game.map_data else 0
    map_w = len(game.map_data[0]) if map_h > 0 else 0
    map_chunk_w = (map_w // chunk_size) + 1
    map_chunk_h = (map_h // chunk_size) + 1

    min_chunk_x = max(0, min_chunk_x)
    min_chunk_y = max(0, min_chunk_y)
    max_chunk_x = min(map_chunk_w, max_chunk_x + 1)
    max_chunk_y = min(map_chunk_h, max_chunk_y + 1)
    
    tm = game.tile_manager
    shaking_tiles = game.map_manager.shaking_tiles
    current_time = time.time()
    tiles_to_remove = []

    visible_chunks = [(cx, cy) for cy in range(min_chunk_y, max_chunk_y) for cx in range(min_chunk_x, max_chunk_x)]
    center_cx = (min_chunk_x + max_chunk_x) / 2
    center_cy = (min_chunk_y + max_chunk_y) / 2
    visible_chunks.sort(key=lambda p: (p[0] - center_cx)**2 + (p[1] - center_cy)**2)

    for cx, cy in visible_chunks:
        chunk_surf = game.map_manager.get_chunk_surface(cx, cy, game.current_layer_index, 'world')
        if chunk_surf:
            dest_x = cx * chunk_size * tile_size + offset_x
            dest_y = cy * chunk_size * tile_size + offset_y
            chunk_rect = pygame.Rect(dest_x, dest_y, chunk_surf.get_width(), chunk_surf.get_height())
            screen_rect_clip = pygame.Rect(0, 0, view_w, view_h)
            clip_rect = chunk_rect.clip(screen_rect_clip)
            
            if clip_rect.width > 0 and clip_rect.height > 0:
                area_rect = pygame.Rect(clip_rect.x - dest_x, clip_rect.y - dest_y, clip_rect.width, clip_rect.height)
                surface.blit(chunk_surf, clip_rect.topleft, area=area_rect)

    for pos, start_t in shaking_tiles.items():
        gx, gy = pos
        screen_px = int(gx * tile_size + offset_x)
        screen_py = int(gy * tile_size + offset_y)
        
        if -tile_size < screen_px < view_w and -tile_size < screen_py < view_h:
            b_key = game.map_data[gy][gx]
            if b_key and b_key != ' ':
                b_def = tm.definitions.get(b_key)
                if b_def:
                    draw_x, draw_y = screen_px, screen_py
                    if current_time - start_t > 0.2: tiles_to_remove.append(pos)
                    else:
                        draw_x += random.randint(-2, 2)
                        draw_y += random.randint(-2, 2)
                    surface.blit(b_def['image'], (draw_x, draw_y))
    
    for k in tiles_to_remove:
        if k in game.map_manager.shaking_tiles:
            del game.map_manager.shaking_tiles[k]

    if hasattr(game, 'blood_stains'):
        min_view_x, max_view_x = -offset_x - 100, -offset_x + view_w + 100
        min_view_y, max_view_y = -offset_y - 100, -offset_y + view_h + 100
        for stain in game.blood_stains:
            stain_wx, stain_wy = stain['pos']
            if not (min_view_x < stain_wx < max_view_x and min_view_y < stain_wy < max_view_y): continue
            pygame.draw.circle(surface, stain.get('color', (139, 0, 0)), (int(stain_wx + offset_x), int(stain_wy + offset_y)), stain['size'] // 2)