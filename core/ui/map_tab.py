import pygame
import math
import os
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

    # --- [NEW] Try loading full map image ---
    # We initialize this if it doesn't exist to avoid KeyErrors later
    if 'full_map_image' not in modal:
        modal['full_map_image'] = None
        if hasattr(game, 'map_manager'):
            try:
                img_path = os.path.join(game.map_manager.map_folder, "full_map.jpg")
                if os.path.exists(img_path):
                    img = pygame.image.load(img_path).convert()
                    modal['full_map_image'] = img
                    
                    # Calculate scale relative to world dimensions
                    world_w = MAP_CHUNKS * CHUNK_SIZE * TILE_SIZE
                    if world_w > 0:
                        modal['img_scale'] = img.get_width() / world_w
                    else:
                        modal['img_scale'] = 0.1 
                    
                    # Reset zoom to a reasonable default for image mode
                    modal['map_zoom'] = 1.0
            except Exception as e:
                print(f"Error loading minimap image: {e}")

    # --- 2. Define Draw Areas ---
    content_y_start = modal['rect'].y + 80
    content_x_start = modal['rect'].x + 10
    content_height = modal['rect'].height - 90
    content_width = modal['rect'].width - 20
    
    map_area_rect = pygame.Rect(content_x_start, content_y_start, content_width, content_height - 40) 
    modal['map_area_rect'] = map_area_rect

    # --- 3. Draw Map Background ---
    pygame.draw.rect(surface, (20, 20, 20), map_area_rect)
    
    # Check Player availability
    if not game.player:
        text_surf = font.render("Player not found.", True, GRAY)
        text_rect = text_surf.get_rect(center=map_area_rect.center)
        surface.blit(text_surf, text_rect)
        return

    # --- 4. Render Map (Image or Tile Fallback) ---
    # [FIX] Use .get() to avoid KeyError if initialization failed or key is missing
    if modal.get('full_map_image'):
        # === IMAGE MODE ===
        img = modal['full_map_image']
        scale = modal.get('img_scale', 0.1)
        zoom = max(0.2, float(modal['map_zoom'])) # Prevent negative zoom
        
        # Optimization: Only re-scale image if zoom changed
        if modal.get('cached_zoom') != zoom or 'cached_map_surf' not in modal:
            # [FIX] Ensure dimensions are at least 1px to prevent pygame crash
            new_w = max(1, int(img.get_width() * zoom))
            new_h = max(1, int(img.get_height() * zoom))
            
            # Use smoothscale for quality, but fallback to scale if image is massive for perf
            if new_w < 4000:
                modal['cached_map_surf'] = pygame.transform.smoothscale(img, (new_w, new_h))
            else:
                modal['cached_map_surf'] = pygame.transform.scale(img, (new_w, new_h))
            modal['cached_zoom'] = zoom
        
        map_surf = modal['cached_map_surf']
        
        # Center view on Player
        # Player World Pos -> Image Pos -> Scaled/Zoomed Pos
        px_scaled = game.player.rect.centerx * scale * zoom
        py_scaled = game.player.rect.centery * scale * zoom
        
        # Calculate offset to center the scaled player pos in the view rect
        offset_x = map_area_rect.centerx - px_scaled
        offset_y = map_area_rect.centery - py_scaled
        
        # Clip and Blit
        old_clip = surface.get_clip()
        surface.set_clip(map_area_rect)
        
        surface.blit(map_surf, (offset_x, offset_y))
        
        # Draw Player Indicator (Always center of view)
        pygame.draw.circle(surface, MINIMAP_PLAYER_COLOR, map_area_rect.center, 5)
        pygame.draw.circle(surface, WHITE, map_area_rect.center, 6, 1)
        
        surface.set_clip(old_clip)

    else:
        # === TILE MODE (Legacy Fallback) ===
        if 'construction_cache' not in modal:
            valid_chars = set()
            for char, defn in game.tile_manager.definitions.items():
                if defn.get('is_obstacle', False):
                    base_char = char[0].upper()
                    if base_char not in ['F', 'W']:
                        valid_chars.add(char)
            modal['construction_cache'] = valid_chars
        
        valid_construction_chars = modal['construction_cache']
        map_zoom = int(modal['map_zoom']) # Ensure int for legacy logic

        map_data = getattr(game, 'map_data', [])
        if not map_data: return

        player_grid_x = game.player.rect.centerx // TILE_SIZE
        player_grid_y = game.player.rect.centery // TILE_SIZE

        map_height = len(map_data)
        map_width = len(map_data[0]) if map_height > 0 else 0

        try:
            sub_surface = surface.subsurface(map_area_rect)
        except ValueError:
            return

        offset_x = (map_area_rect.width / 2) - (player_grid_x * map_zoom)
        offset_y = (map_area_rect.height / 2) - (player_grid_y * map_zoom)

        start_col = max(0, int(-offset_x // map_zoom))
        end_col = min(map_width, int((map_area_rect.width - offset_x) // map_zoom) + 1)
        start_row = max(0, int(-offset_y // map_zoom))
        end_row = min(map_height, int((map_area_rect.height - offset_y) // map_zoom) + 1)

        for y in range(start_row, end_row):
            for x in range(start_col, end_col):
                tile_char = map_data[y][x]
                if not tile_char: continue
                if tile_char not in valid_construction_chars: continue

                draw_x = offset_x + (x * map_zoom)
                draw_y = offset_y + (y * map_zoom)
                
                base_char = tile_char[0].upper()
                color = MINIMAP_COLORS.get(base_char, MINIMAP_COLORS['default'])

                pygame.draw.rect(sub_surface, color, (draw_x, draw_y, map_zoom, map_zoom))

        # Player Icon
        player_draw_x = offset_x + (player_grid_x * map_zoom)
        player_draw_y = offset_y + (player_grid_y * map_zoom)
        player_rect = pygame.Rect(player_draw_x, player_draw_y, map_zoom, map_zoom)
        border_width = 0 if map_zoom < 4 else (2 if map_zoom > 6 else 1)
        pygame.draw.rect(sub_surface, MINIMAP_PLAYER_COLOR, player_rect, border_width)

    # --- 5. Draw Zoom Buttons ---
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
    
    # --- 6. Store button rects ---
    modal['map_zoom_in_rect'] = zoom_in_rect
    modal['map_zoom_out_rect'] = zoom_out_rect

    return {
        'id': modal['id'], 'type': 'map_zoom_in', 'rect': zoom_in_rect
    }, {
        'id': modal['id'], 'type': 'map_zoom_out', 'rect': zoom_out_rect
    }