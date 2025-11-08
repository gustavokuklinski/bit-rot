# core/ui/map_tab.py

import pygame
from data.config import *

# Define colors for the minimap
MINIMAP_COLORS = {
    ' ': (30, 30, 30),     # Empty/Background
    'G': (30, 30, 30),    # Grass
    'W': (30, 30, 30),    # Water
    'R': (80, 80, 80),     # Road
    'F': (30, 30, 30),     # Forest
    'default': (80, 80, 80) # Default for walls/obstacles
}
MINIMAP_PLAYER_COLOR = (0, 255, 255) # Bright cyan for player

def draw_map_tab(surface, game, modal, assets):
    # --- 1. Get/Initialize Map State ---
    # We store map-specific state in the modal dict
    if 'map_zoom' not in modal:
        modal['map_zoom'] = 6 # Size of each tile in pixels (default zoom)
    if 'map_offset' not in modal:
        modal['map_offset'] = (0, 0) # Camera offset (for future panning)

    map_zoom = modal['map_zoom']
    
    # --- 2. Define Draw Areas ---
    content_y_start = modal['rect'].y + 80 # Below header and tabs
    content_x_start = modal['rect'].x + 10
    content_height = modal['rect'].height - 90 # 80 for header/tab, 10 for bottom padding
    content_width = modal['rect'].width - 20
    
    # This is the main area where the map will be drawn
    # Leave 40px at the bottom for buttons
    map_area_rect = pygame.Rect(content_x_start, content_y_start, content_width, content_height - 40) 
    modal['map_area_rect'] = map_area_rect # Store for scroll detection in input.py

    # --- 3. Draw Map Background ---
    pygame.draw.rect(surface, (20, 20, 20), map_area_rect) # Dark background

    # --- 4. Get Map Data and Player Position ---
    map_data = getattr(game, 'map_data', [])
    if not map_data or not game.player:
        text_surf = font.render("Map data not available.", True, GRAY)
        text_rect = text_surf.get_rect(center=map_area_rect.center)
        surface.blit(text_surf, text_rect)
        return # Can't draw anything else

    player_grid_x = game.player.rect.centerx // TILE_SIZE
    player_grid_y = game.player.rect.centery // TILE_SIZE

    map_height = len(map_data)
    map_width = len(map_data[0]) if map_height > 0 else 0

    # --- 5. Draw the Map (Clipped) ---
    # Create a subsurface for clipping
    try:
        map_surface = surface.subsurface(map_area_rect)
    except ValueError:
        # This can happen if the modal is resized to be tiny
        return # Can't draw

    # Center the view on the player
    offset_x = (map_area_rect.width / 2) - (player_grid_x * map_zoom)
    offset_y = (map_area_rect.height / 2) - (player_grid_y * map_zoom)
    
    modal['map_offset'] = (offset_x, offset_y)
    
    for y in range(map_height):
        for x in range(map_width):
            tile_char = map_data[y][x]
            
            # Simple char matching for color
            base_char = tile_char[0].upper() if tile_char else ' '
            color = MINIMAP_COLORS.get(base_char, MINIMAP_COLORS['default'])

            # Calculate draw position *within the subsurface*
            draw_x = offset_x + (x * map_zoom)
            draw_y = offset_y + (y * map_zoom)

            # Cull tiles outside the viewport
            if draw_x + map_zoom < 0 or draw_x > map_area_rect.width or \
               draw_y + map_zoom < 0 or draw_y > map_area_rect.height:
                continue
                
            tile_rect = pygame.Rect(draw_x, draw_y, map_zoom, map_zoom)
            pygame.draw.rect(map_surface, color, tile_rect)

    # --- 6. Draw Player Icon (on top) ---
    player_draw_x = offset_x + (player_grid_x * map_zoom)
    player_draw_y = offset_y + (player_grid_y * map_zoom)
    player_rect = pygame.Rect(player_draw_x, player_draw_y, map_zoom, map_zoom)
    
    # Draw a filled rect if zoom is tiny, otherwise a border
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
    
    # --- 8. Store button rects in the modal for handle_mouse_down ---
    modal['map_zoom_in_rect'] = zoom_in_rect
    modal['map_zoom_out_rect'] = zoom_out_rect

    return {
        'id': modal['id'], 'type': 'map_zoom_in', 'rect': zoom_in_rect
    }, {
        'id': modal['id'], 'type': 'map_zoom_out', 'rect': zoom_out_rect
    }