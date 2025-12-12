# core/ui/map_tab.py

import pygame
import math # Import math for ceil/floor operations
from core.data.config import *

# Define colors for the minimap
MINIMAP_COLORS = {
    ' ': (30, 30, 30),     # Empty/Background
    'G': (80, 80, 80),    # Grass
    'W': (80, 80, 80),    # Water
    'R': (30, 30, 30),     # Road
    'F': (80, 80, 80),     # Forest
    'default': (80, 80, 80) # Default for walls/obstacles
}
MINIMAP_PLAYER_COLOR = (0, 255, 255) # Bright cyan for player

def draw_map_tab(surface, game, modal, assets):
    # --- 1. Get/Initialize Map State ---
    if 'map_zoom' not in modal:
        modal['map_zoom'] = 6
    if 'map_offset' not in modal:
        modal['map_offset'] = (0, 0)

    # --- [OPTIMIZATION 1] Cache Valid Construction Chars ---
    # We build a set of characters that are obstacles but NOT nature (F/W)
    # This prevents expensive dictionary lookups inside the loop
    if 'construction_cache' not in modal:
        valid_chars = set()
        for char, defn in game.tile_manager.definitions.items():
            # Check if it is an obstacle
            if defn.get('is_obstacle', False):
                # Check if it is NOT nature (Forest/Water)
                base_char = char[0].upper()
                if base_char not in ['F', 'W']:
                    valid_chars.add(char)
        modal['construction_cache'] = valid_chars
    
    valid_construction_chars = modal['construction_cache']

    map_zoom = modal['map_zoom']
    
    # --- 2. Define Draw Areas ---
    content_y_start = modal['rect'].y + 80
    content_x_start = modal['rect'].x + 10
    content_height = modal['rect'].height - 90
    content_width = modal['rect'].width - 20
    
    map_area_rect = pygame.Rect(content_x_start, content_y_start, content_width, content_height - 40) 
    modal['map_area_rect'] = map_area_rect

    # --- 3. Draw Map Background ---
    pygame.draw.rect(surface, (20, 20, 20), map_area_rect)

    # --- 4. Get Map Data and Player Position ---
    map_data = getattr(game, 'map_data', [])
    if not map_data or not game.player:
        text_surf = font.render("Map data not available.", True, GRAY)
        text_rect = text_surf.get_rect(center=map_area_rect.center)
        surface.blit(text_surf, text_rect)
        return

    player_grid_x = game.player.rect.centerx // TILE_SIZE
    player_grid_y = game.player.rect.centery // TILE_SIZE

    map_height = len(map_data)
    map_width = len(map_data[0]) if map_height > 0 else 0

    # --- 5. Draw the Map (Clipped) ---
    try:
        map_surface = surface.subsurface(map_area_rect)
    except ValueError:
        return

    # Center the view on the player
    offset_x = (map_area_rect.width / 2) - (player_grid_x * map_zoom)
    offset_y = (map_area_rect.height / 2) - (player_grid_y * map_zoom)
    
    modal['map_offset'] = (offset_x, offset_y)
    
    # --- [OPTIMIZATION 2] Viewport Calculation (Frustum Culling) ---
    # Only iterate over tiles that are actually visible on screen.
    # We solve for x:  0 <= offset_x + (x * zoom) <= view_width
    
    start_col = max(0, int(-offset_x // map_zoom))
    end_col = min(map_width, int((map_area_rect.width - offset_x) // map_zoom) + 1)
    
    start_row = max(0, int(-offset_y // map_zoom))
    end_row = min(map_height, int((map_area_rect.height - offset_y) // map_zoom) + 1)

    # Iterate only the visible range
    for y in range(start_row, end_row):
        for x in range(start_col, end_col):
            tile_char = map_data[y][x]
            if not tile_char: continue
            
            # Fast check using the cached set
            if tile_char not in valid_construction_chars:
                continue

            # Calculate draw position
            draw_x = offset_x + (x * map_zoom)
            draw_y = offset_y + (y * map_zoom)

            # (No need for extra culling check here, the loop range handles it)
            
            # Determine color
            base_char = tile_char[0].upper()
            color = MINIMAP_COLORS.get(base_char, MINIMAP_COLORS['default'])

            tile_rect = pygame.Rect(draw_x, draw_y, map_zoom, map_zoom)
            pygame.draw.rect(map_surface, color, tile_rect)

    # --- 6. Draw Player Icon (on top) ---
    player_draw_x = offset_x + (player_grid_x * map_zoom)
    player_draw_y = offset_y + (player_grid_y * map_zoom)
    player_rect = pygame.Rect(player_draw_x, player_draw_y, map_zoom, map_zoom)
    
    border_width = 0 if map_zoom < 4 else (2 if map_zoom > 6 else 1)
    pygame.draw.rect(map_surface, MINIMAP_PLAYER_COLOR, player_rect, border_width)

    # --- 7. Draw Zoom Buttons ---
    button_y = map_area_rect.bottom + 10
    zoom_in_rect = pygame.Rect(map_area_rect.centerx - 30 - 5, button_y, 30, 30)
    zoom_out_rect = pygame.Rect(map_area_rect.centerx + 5, button_y, 30, 30)

    # Draw Zoom In (+)
    pygame.draw.rect(surface, GRAY_60, zoom_in_rect, 0, 3)
    pygame.draw.rect(surface, WHITE, zoom_in_rect, 1, 3)
    plus_surf = large_font.render("+", True, WHITE)
    plus_rect = plus_surf.get_rect(center=zoom_in_rect.center)
    surface.blit(plus_surf, plus_rect)

    # Draw Zoom Out (-)
    pygame.draw.rect(surface, GRAY_60, zoom_out_rect, 0, 3)
    pygame.draw.rect(surface, WHITE, zoom_out_rect, 1, 3)
    minus_surf = large_font.render("-", True, WHITE)
    minus_rect = minus_surf.get_rect(center=zoom_out_rect.center)
    surface.blit(minus_surf, minus_rect)
    
    # --- 8. Store button rects ---
    modal['map_zoom_in_rect'] = zoom_in_rect
    modal['map_zoom_out_rect'] = zoom_out_rect

    return {
        'id': modal['id'], 'type': 'map_zoom_in', 'rect': zoom_in_rect
    }, {
        'id': modal['id'], 'type': 'map_zoom_out', 'rect': zoom_out_rect
    }