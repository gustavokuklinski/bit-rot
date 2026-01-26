import pygame
import math
import os
from core.data.config import *
from core.ui.modals import BaseModal

# Define colors for the minimap
MINIMAP_COLORS = {
    ' ': (30, 30, 30),      # Empty/Background
    'G': (34, 139, 34),     # Forest/Grass - Lush Green
    'W': (30, 144, 255),    # Water - Bright Blue
    'R': (100, 100, 100),   # Road/Street - Asphalt Grey
    'F': (20, 80, 20),      # Deep Forest - Darker Green
    'C': (200, 200, 200),   # Construction - Solid Light Block
    'default': (80, 80, 80) # Default fallback
}
MINIMAP_PLAYER_COLOR = (0, 255, 255) # Bright cyan for player

def generate_minimap_cache(game):
    """
    Generates a 1:1 pixel representation of the current map layer.
    This is run ONCE when the tab opens or layer changes.
    """
    base_layer = getattr(game, 'map_data', [])
    if not base_layer:
        return None

    map_height = len(base_layer)
    map_width = len(base_layer[0]) if map_height > 0 else 0
    
    # Create a surface where 1 pixel = 1 tile
    cache_surf = pygame.Surface((map_width, map_height))
    cache_surf.fill(MINIMAP_COLORS[' '])
    
    # Use PixelArray for fast direct pixel access
    pixels = pygame.PixelArray(cache_surf)
    
    ground_layer = game.all_ground_layers.get(game.current_layer_index, [])
    roof_layer = game.all_roof_layers.get(game.current_layer_index, [])
    tile_defs = game.tile_manager.definitions

    # Iterate over the entire map once
    for y in range(map_height):
        for x in range(map_width):
            final_char = ' '
            
            # --- 1. Ground Layer (Grass, Water) ---
            if y < len(ground_layer) and x < len(ground_layer[y]):
                g_tile = ground_layer[y][x]
                if g_tile and g_tile != ' ':
                    g_def = tile_defs.get(g_tile)
                    g_name = g_def.get('name', '').lower() if g_def else ''
                    
                    if 'water' in g_name or g_tile.upper().startswith('W'):
                        final_char = 'W'
                    elif 'grass' in g_name or g_tile.upper().startswith('G'):
                        final_char = 'G'
                    elif 'forest' in g_name:
                        final_char = 'F'
            
            # --- 2. Base Layer (Roads, Walls, Indoor Floors) ---
            if y < len(base_layer) and x < len(base_layer[y]):
                b_tile = base_layer[y][x]
                if b_tile and b_tile != ' ':
                    b_def = tile_defs.get(b_tile)
                    if b_def:
                        b_name = b_def.get('name', '').lower()
                        # Road Detection
                        if any(k in b_name for k in ['road', 'street', 'asphalt', 'path']):
                            final_char = 'R'
                        # Construction Detection (Walls OR Indoor Floors)
                        elif b_def.get('is_obstacle') or 'wall' in b_name or ('floor' in b_name and 'grass' not in b_name):
                            final_char = 'C'
                    # Fallback (Legacy)
                    elif b_tile.upper().startswith('R'):
                        final_char = 'R'

            # --- 3. Roof Layer (Forces construction blocks) ---
            if y < len(roof_layer) and x < len(roof_layer[y]):
                r_tile = roof_layer[y][x]
                if r_tile and r_tile != ' ':
                    final_char = 'C'

            if final_char != ' ':
                # Map the char to the actual RGB color
                color = MINIMAP_COLORS.get(final_char, MINIMAP_COLORS['default'])
                pixels[x, y] = color # PixelArray uses [x, y]

    pixels.close() # Unlock the surface
    return cache_surf

def draw_map_tab(surface, game, modal, assets):
    # --- 1. Get/Initialize Map State ---
    if 'map_zoom' not in modal:
        modal['map_zoom'] = 6
    if 'map_offset' not in modal:
        modal['map_offset'] = (0, 0)
    
    # --- 2. Define Draw Areas ---
    content_y_start = modal['rect'].y + 80
    content_x_start = modal['rect'].x + 10
    content_height = modal['rect'].height - 90
    content_width = modal['rect'].width - 20
    
    map_area_rect = pygame.Rect(content_x_start, content_y_start, content_width, content_height - 40) 
    modal['map_area_rect'] = map_area_rect

    # --- 3. Draw Map Background ---
    pygame.draw.rect(surface, (20, 20, 20), map_area_rect)
    
    if not game.player:
        return

    # --- 4. Render Map (Cached) ---
    # Check if we need to regenerate the cache (First load OR layer switch)
    current_layer = getattr(game, 'current_layer_index', 1)
    if 'cached_minimap' not in modal or modal.get('cached_layer') != current_layer:
        modal['cached_minimap'] = generate_minimap_cache(game)
        modal['cached_layer'] = current_layer

    cached_surf = modal.get('cached_minimap')
    
    if cached_surf:
        map_zoom = int(modal['map_zoom'])
        
        # Calculate Viewport
        player_grid_x = game.player.rect.centerx // TILE_SIZE
        player_grid_y = game.player.rect.centery // TILE_SIZE

        # Determine how many tiles fit in the view at current zoom
        tiles_in_view_w = map_area_rect.width / map_zoom
        tiles_in_view_h = map_area_rect.height / map_zoom
        
        off_x, off_y = modal['map_offset']

        # [FIXED] Apply offset to the source coordinates
        src_x = (player_grid_x - (tiles_in_view_w / 2)) - off_x
        src_y = (player_grid_y - (tiles_in_view_h / 2)) - off_y
        src_w = tiles_in_view_w
        src_h = tiles_in_view_h

        src_rect = pygame.Rect(src_x, src_y, src_w, src_h)
        
        # Get the intersection with the actual map bounds
        map_rect = cached_surf.get_rect()
        clipped_src = src_rect.clip(map_rect)
        
        if clipped_src.width > 0 and clipped_src.height > 0:
            # 1. Cut out the visible chunk from cache (1px = 1tile)
            sub_surf = cached_surf.subsurface(clipped_src)
            
            # 2. Scale it up to screen size (zoom factor)
            dest_w = int(clipped_src.width * map_zoom)
            dest_h = int(clipped_src.height * map_zoom)
            scaled_surf = pygame.transform.scale(sub_surf, (dest_w, dest_h))
            
            # 3. Calculate where to place it on screen
            # (Adjust for the clipping if we were near an edge)
            draw_offset_x = (clipped_src.x - src_x) * map_zoom
            draw_offset_y = (clipped_src.y - src_y) * map_zoom
            
            surface.blit(scaled_surf, (map_area_rect.x + draw_offset_x, map_area_rect.y + draw_offset_y))

        # --- Draw Player Icon ---
        # The map is now drawn relative to the player being roughly in center
        # We calculate player position relative to the drawn map surface
        
        screen_player_x = map_area_rect.x + (player_grid_x - src_x) * map_zoom
        screen_player_y = map_area_rect.y + (player_grid_y - src_y) * map_zoom
        
        player_rect = pygame.Rect(screen_player_x, screen_player_y, map_zoom, map_zoom)
        
        # Only draw if inside the view (technically always true if centering, but good practice)
        if map_area_rect.collidepoint(player_rect.center):
            pygame.draw.rect(surface, MINIMAP_PLAYER_COLOR, player_rect, 0)
            pygame.draw.rect(surface, (0, 0, 0), player_rect, 1)

    # --- 5. Draw Zoom Buttons ---
    button_y = map_area_rect.bottom + 10
    zoom_in_rect = pygame.Rect(map_area_rect.centerx - 35, button_y, 30, 30)
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
    
    modal['map_zoom_in_rect'] = zoom_in_rect
    modal['map_zoom_out_rect'] = zoom_out_rect

    return {
        'id': modal['id'], 'type': 'map_zoom_in', 'rect': zoom_in_rect
    }, {
        'id': modal['id'], 'type': 'map_zoom_out', 'rect': zoom_out_rect
    }

def draw_big_map_modal(surface, game, modal, assets):
    # Create the window frame
    base_modal = BaseModal(surface, modal, assets, f"{modal['item'].name}")
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    
    close_button, minimize_button = base_modal.get_buttons()
    
    if base_modal.minimized:
        return [close_button, minimize_button]

    # Draw the map content inside
    zoom_in, zoom_out = draw_map_tab(surface, game, modal, assets)
    
    return [close_button, minimize_button, zoom_in, zoom_out]