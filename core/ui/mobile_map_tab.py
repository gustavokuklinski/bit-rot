# core/ui/map_tab.py

import pygame
import math
import os
import re
import time
from core.data.config import *
from core.ui.modals import BaseModal
from core.map.map_loader import load_map_from_file
from core.entities.npc.npc_dialog import NPCDialog

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

def generate_minimap_cache(game, full_map=False):
    """
    Generates a 1:1 pixel representation of the map.
    If full_map is True, stitches all chunks. Otherwise, uses current chunk.
    """
    current_layer = getattr(game, 'current_layer_index', 1)
    tile_defs = game.tile_manager.definitions

    if full_map and not getattr(game, 'is_giant_map', False):
        # --- BUILD FULL STITCHED MAP ---
        map_files = game.map_manager.map_files
        max_gx = 0
        max_gy = 0
        pattern = re.compile(rf'map_L{current_layer}_(\d+)_(\d+)_map\.csv')
        
        for filename in map_files:
            match = pattern.match(filename)
            if match:
                max_gx = max(max_gx, int(match.group(1)))
                max_gy = max(max_gy, int(match.group(2)))

        chunk_size = getattr(game, 'CHUNK_SIZE', 32)
        map_width = (max_gx + 1) * chunk_size
        map_height = (max_gy + 1) * chunk_size

        cache_surf = pygame.Surface((map_width, map_height))
        cache_surf.fill(MINIMAP_COLORS[' '])
        pixels = pygame.PixelArray(cache_surf)

        map_folder = game.map_manager.map_folder
        
        for gy in range(max_gy + 1):
            for gx in range(max_gx + 1):
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
                        final_char = ' '
                        
                        # Ground
                        if y < len(g_data) and x < len(g_data[y]):
                            g_tile = g_data[y][x]
                            if g_tile and g_tile != ' ':
                                g_def = tile_defs.get(g_tile)
                                g_name = g_def.get('name', '').lower() if g_def else ''
                                if 'water' in g_name or g_tile.upper().startswith('W'):
                                    final_char = 'W'
                                elif 'grass' in g_name or g_tile.upper().startswith('G'):
                                    final_char = 'G'
                                elif 'forest' in g_name:
                                    final_char = 'F'
                        
                        # Base
                        if y < len(b_data) and x < len(b_data[y]):
                            b_tile = b_data[y][x]
                            if b_tile and b_tile != ' ':
                                b_def = tile_defs.get(b_tile)
                                if b_def:
                                    b_name = b_def.get('name', '').lower()
                                    if any(k in b_name for k in ['road', 'street', 'asphalt', 'path']):
                                        final_char = 'R'
                                    elif b_def.get('is_obstacle') or 'wall' in b_name or ('floor' in b_name and 'grass' not in b_name):
                                        final_char = 'C'
                                elif b_tile.upper().startswith('R'):
                                    final_char = 'R'

                        # Roof
                        if y < len(r_data) and x < len(r_data[y]):
                            r_tile = r_data[y][x]
                            if r_tile and r_tile != ' ':
                                final_char = 'C'

                        if final_char != ' ':
                            try:
                                pixels[offset_x + x, offset_y + y] = MINIMAP_COLORS.get(final_char, MINIMAP_COLORS['default'])
                            except IndexError:
                                pass
        pixels.close()
        return cache_surf

    else:
        # --- BUILD SINGLE CHUNK MAP (Mobile Default) ---
        base_layer = getattr(game, 'map_data', [])
        if not base_layer:
            return None

        map_height = len(base_layer)
        map_width = len(base_layer[0]) if map_height > 0 else 0
        
        cache_surf = pygame.Surface((map_width, map_height))
        cache_surf.fill(MINIMAP_COLORS[' '])
        pixels = pygame.PixelArray(cache_surf)
        
        ground_layer = game.all_ground_layers.get(current_layer, [])
        roof_layer = game.all_roof_layers.get(current_layer, [])

        for y in range(map_height):
            for x in range(map_width):
                final_char = ' '
                
                # Ground
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
                
                # Base
                if y < len(base_layer) and x < len(base_layer[y]):
                    b_tile = base_layer[y][x]
                    if b_tile and b_tile != ' ':
                        b_def = tile_defs.get(b_tile)
                        if b_def:
                            b_name = b_def.get('name', '').lower()
                            if any(k in b_name for k in ['road', 'street', 'asphalt', 'path']):
                                final_char = 'R'
                            elif b_def.get('is_obstacle') or 'wall' in b_name or ('floor' in b_name and 'grass' not in b_name):
                                final_char = 'C'
                        elif b_tile.upper().startswith('R'):
                            final_char = 'R'

                # Roof
                if y < len(roof_layer) and x < len(roof_layer[y]):
                    r_tile = roof_layer[y][x]
                    if r_tile and r_tile != ' ':
                        final_char = 'C'

                if final_char != ' ':
                    pixels[x, y] = MINIMAP_COLORS.get(final_char, MINIMAP_COLORS['default'])

        pixels.close()
        return cache_surf

def draw_map_tab(surface, game, modal, assets, full_map=False):
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

    # --- 2.5 Handle Mouse Dragging (Panning) ---
    if 'is_dragging_map' not in modal or 'last_drag_pos' not in modal:
        modal['is_dragging_map'] = False
        modal['last_drag_pos'] = (0, 0)

    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    
    if mouse_pressed:
        if modal['is_dragging_map']:
            dx = mouse_pos[0] - modal['last_drag_pos'][0]
            dy = mouse_pos[1] - modal['last_drag_pos'][1]
            zoom = modal['map_zoom']
            modal['map_offset'] = (
                modal['map_offset'][0] + (dx / zoom),
                modal['map_offset'][1] + (dy / zoom)
            )
            modal['last_drag_pos'] = mouse_pos
        elif map_area_rect.collidepoint(mouse_pos):
             modal['is_dragging_map'] = True
             modal['last_drag_pos'] = mouse_pos
    else:
        modal['is_dragging_map'] = False

    # --- 3. Draw Map Background ---
    pygame.draw.rect(surface, (20, 20, 20), map_area_rect)
    
    if not game.player:
        return

    # --- 4. Render Map (Cached) ---
    current_layer = getattr(game, 'current_layer_index', 1)
    current_map_file = getattr(game.map_manager, 'current_map_filename', '')
    
    # Distinct cache keys prevent overwriting between Map Item and Mobile tabs
    cache_key = 'cached_minimap_full' if full_map else 'cached_minimap_chunk'
    
    # Check for layer changes AND chunk map file changes
    needs_update = False
    if cache_key not in modal:
        needs_update = True
    elif modal.get('cached_layer') != current_layer:
        needs_update = True
    elif not full_map and modal.get('cached_map_file') != current_map_file:
        needs_update = True

    if needs_update:
        modal[cache_key] = generate_minimap_cache(game, full_map)
        modal['cached_layer'] = current_layer
        modal['cached_map_file'] = current_map_file

    cached_surf = modal.get(cache_key)
    
    if cached_surf:
        map_zoom = int(modal['map_zoom'])
        
        # Calculate Viewport
        player_grid_x = game.player.rect.centerx // TILE_SIZE
        player_grid_y = game.player.rect.centery // TILE_SIZE

        # Offset the player's grid tile if we are on the full map stitched grid
        gx_offset, gy_offset = 0, 0
        if full_map and not getattr(game, 'is_giant_map', False):
            current_map = game.map_manager.current_map_filename
            match = re.search(r'map_L\d+_(\d+)_(\d+)_map\.csv', current_map)
            if match:
                gx, gy = int(match.group(1)), int(match.group(2))
                chunk_size = getattr(game, 'CHUNK_SIZE', 32)
                gx_offset = (gx * chunk_size)
                gy_offset = (gy * chunk_size)
                player_grid_x += gx_offset
                player_grid_y += gy_offset

        tiles_in_view_w = map_area_rect.width / map_zoom
        tiles_in_view_h = map_area_rect.height / map_zoom
        
        off_x, off_y = modal['map_offset']

        src_x = (player_grid_x - (tiles_in_view_w / 2)) - off_x
        src_y = (player_grid_y - (tiles_in_view_h / 2)) - off_y
        src_w = tiles_in_view_w
        src_h = tiles_in_view_h

        src_rect = pygame.Rect(src_x, src_y, src_w, src_h)
        map_rect = cached_surf.get_rect()
        clipped_src = src_rect.clip(map_rect)
        
        if clipped_src.width > 0 and clipped_src.height > 0:
            sub_surf = cached_surf.subsurface(clipped_src)
            dest_w = int(clipped_src.width * map_zoom)
            dest_h = int(clipped_src.height * map_zoom)
            scaled_surf = pygame.transform.scale(sub_surf, (dest_w, dest_h))
            
            draw_offset_x = (clipped_src.x - src_x) * map_zoom
            draw_offset_y = (clipped_src.y - src_y) * map_zoom
            
            surface.blit(scaled_surf, (map_area_rect.x + draw_offset_x, map_area_rect.y + draw_offset_y))
        
        # --- Draw Player Icon ---
        screen_player_x = map_area_rect.x + (player_grid_x - src_x) * map_zoom
        screen_player_y = map_area_rect.y + (player_grid_y - src_y) * map_zoom
        
        marker_size = max(8, int(map_zoom * 1.5))
        center_x = screen_player_x + (map_zoom / 2)
        center_y = screen_player_y + (map_zoom / 2)
        
        player_rect = pygame.Rect(0, 0, marker_size, marker_size)
        player_rect.center = (center_x, center_y)
        
        if map_area_rect.collidepoint(player_rect.center):
            pygame.draw.rect(surface, MINIMAP_PLAYER_COLOR, player_rect, 0)
            pygame.draw.rect(surface, (0, 0, 0), player_rect, 1)

        # --- [NEW] Draw Dynamic Quest Markers ---
        if hasattr(game.player, 'quests'):
            if NPCDialog.NPC_DIALOGS is None:
                NPCDialog.load_dialogs()
                
            active_req_items = set()
            
            # 1. Identify which items the player is tasked to find
            for node_id in game.player.quests:
                options = NPCDialog.NPC_DIALOGS.get(node_id, [])
                for opt in options:
                    dialog_key = f"{node_id}_{opt['q']}"
                    # If this specific dialog option has NOT been spoken/concluded yet
                    if dialog_key not in getattr(game.player, 'dialog_history', []):
                        req_item = opt.get('req_item')
                        if req_item:
                            item_names = [i.strip() for i in req_item.replace('[', '').replace(']', '').split(',')]
                            active_req_items.update(item_names)
            
            if active_req_items:
                quest_locations = []
                
                # 2. Scan world items and containers for the active quest requirements
                for item in getattr(game, 'items_on_ground', []) + getattr(game, 'visible_items', []):
                    if item.name in active_req_items:
                        quest_locations.append((item.rect.centerx, item.rect.centery))
                
                for container in getattr(game, 'containers', []) + getattr(game, 'visible_containers', []):
                    if hasattr(container, 'inventory'):
                        for item in container.inventory:
                            if item and item.name in active_req_items:
                                quest_locations.append((container.rect.centerx, container.rect.centery))
                                break # Prevent overlapping markers for the same container
                
                # 3. Draw the markers dynamically over the map
                pulse = (math.sin(time.time() * 5) + 1) / 2 # Generates a smooth 0.0 to 1.0 pulse wave

                for qx, qy in quest_locations:
                    q_grid_x = (qx // TILE_SIZE) + gx_offset
                    q_grid_y = (qy // TILE_SIZE) + gy_offset
                    
                    screen_q_x = map_area_rect.x + (q_grid_x - src_x) * map_zoom
                    screen_q_y = map_area_rect.y + (q_grid_y - src_y) * map_zoom
                    
                    q_center_x = screen_q_x + (map_zoom / 2)
                    q_center_y = screen_q_y + (map_zoom / 2)
                    
                    if map_area_rect.collidepoint(q_center_x, q_center_y):
                        # Pulsating marker base
                        marker_radius = max(6, int(map_zoom)) + (pulse * 3)
                        pygame.draw.circle(surface, (255, 215, 0), (int(q_center_x), int(q_center_y)), int(marker_radius))
                        pygame.draw.circle(surface, (0, 0, 0), (int(q_center_x), int(q_center_y)), int(marker_radius), 1)
                        
                        # Add the '!' in the center
                        if 'font_14' in globals():
                            excl_surf = font_14.render("!", True, (0, 0, 0))
                            excl_rect = excl_surf.get_rect(center=(int(q_center_x), int(q_center_y)))
                            surface.blit(excl_surf, excl_rect)


    # --- 5. Draw Zoom Buttons ---
    button_y = map_area_rect.bottom + 10
    zoom_in_rect = pygame.Rect(map_area_rect.centerx - 35, button_y, 30, 30)
    zoom_out_rect = pygame.Rect(map_area_rect.centerx + 5, button_y, 30, 30)

    pygame.draw.rect(surface, GRAY_60, zoom_in_rect, 0, 3)
    pygame.draw.rect(surface, WHITE, zoom_in_rect, 1, 3)
    plus_surf = font_14.render("+", True, WHITE)
    plus_rect = plus_surf.get_rect(center=zoom_in_rect.center)
    surface.blit(plus_surf, plus_rect)

    pygame.draw.rect(surface, GRAY_60, zoom_out_rect, 0, 3)
    pygame.draw.rect(surface, WHITE, zoom_out_rect, 1, 3)
    minus_surf = font_14.render("-", True, WHITE)
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

    # Draw the map content inside, requesting the full world map
    zoom_in, zoom_out = draw_map_tab(surface, game, modal, assets, full_map=True)
    
    return [close_button, minimize_button, zoom_in, zoom_out]