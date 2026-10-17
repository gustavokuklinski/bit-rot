# core/map/map_manager.py

import os
import re
import csv
import pygame
import random
import time
import core.data.config
from core.data.config import *
from core.messages import display_message
from core.entities.item.item import Item
from core.placement import find_free_tile
from core.data.localization import tr
from core.entities.animal.animal import Animal

class MapManager:
    def __init__(self, game, map_folder=f"{os.path.join(BASE_DIR, 'data.rot', 'lib', 'map')}"):
        
        self.game = game
        self.map_folder = map_folder
        self.current_map_filename = 'map_L1_world_map.csv' 
        self.map_files = self._discover_maps()
        self.shaking_tiles = {}
        self.tile_hit_timers = {}
        
        # [NEW] Chunk Caching System
        self.chunk_surfaces = {} 
        self.offchunk_grids = {}      # (layer, 'gx_gy') -> grid of a chunk that is NOT the loaded one
        self.CHUNK_SIZE = CHUNK_SIZE if 'CHUNK_SIZE' in globals() else 32

        # [NEW] Performance: Chunk Generation Throttling
        self.chunks_generated_this_frame = 0
        self.MAX_CHUNKS_PER_FRAME = 2  # Throttling limit per frame

        if not hasattr(self.game, 'vehicles'):
            self.game.vehicles = []

    def refresh_maps(self):
        """Re-scans the map folder and updates the map_files list."""
        print("Refreshing map file list...")
        self.map_files = self._discover_maps()
        print(f"Found {len(self.map_files)} map files.")

    def _discover_maps(self):
        maps = {}
        # Regex for single world map
        pattern_world = re.compile(r'map_L(\d+)_world_map\.csv')
        # Regex for separated chunks
        pattern_chunk = re.compile(r'map_L(\d+)_(\d+)_(\d+)_map\.csv')

        if not os.path.exists(self.map_folder):
            print(f"Warning: Map folder '{self.map_folder}' does not exist.")
            return maps

        for filename in os.listdir(self.map_folder):
            match_world = pattern_world.match(filename)
            match_chunk = pattern_chunk.match(filename)
            
            if match_chunk:
                try:
                    layer = int(match_chunk.group(1))
                    maps[filename] = {
                        'filename': filename,
                        'layer': layer,
                        'gx': int(match_chunk.group(2)),
                        'gy': int(match_chunk.group(3)),
                        'position': 0,
                    }
                except ValueError:
                    print(f"Warning: Could not parse chunk map filename {filename}")
            elif match_world:
                try:
                    layer = int(match_world.group(1))
                    maps[filename] = {
                        'filename': filename,
                        'layer': layer,
                        'position': 0,
                    }
                except ValueError:
                    print(f"Warning: Could not parse world map filename {filename}")
        return maps

    def get_current_map_connections(self):
        return None

    def transition(self, direction):
        return None

    # [NEW] Chunk Caching Methods
    def clear_cache(self):
        """Clears all cached chunk surfaces."""
        self.chunk_surfaces.clear()
        self.offchunk_grids.clear()

    def reset_frame_metrics(self):
        """Called by Game loop every frame to reset generation limits."""
        self.chunks_generated_this_frame = 0

    def update_chunks(self, player_center_pos):
        pass

    def unload_far_chunks(self, center_cx, center_cy, keep_radius):
        """Unloads chunks outside the keep_radius to free memory."""
        keys_to_remove = []
        for key in self.chunk_surfaces:
            l, cx, cy, mode = key
            if abs(cx - center_cx) > keep_radius or abs(cy - center_cy) > keep_radius:
                keys_to_remove.append(key)
        
        for k in keys_to_remove:
            del self.chunk_surfaces[k]

    def invalidate_chunk(self, grid_x, grid_y, layer_idx=None):
        """Removes the cached surface for the chunk containing (grid_x, grid_y) so it redraws next frame."""
        if layer_idx is None: 
            layer_idx = self.game.current_layer_index
            
        cx = grid_x // self.CHUNK_SIZE
        cy = grid_y // self.CHUNK_SIZE
        
        # Identify keys to remove (matching layer and chunk coordinates)
        keys_to_remove = [k for k in self.chunk_surfaces if k[0] == layer_idx and k[1] == cx and k[2] == cy]
        
        for k in keys_to_remove:
            del self.chunk_surfaces[k]

    @staticmethod
    def _chunk_key(filename):
        """'map_L2_3_1_map.csv' -> '3_1' | 'map_L1_world_map.csv' -> 'world' | else None"""
        m = re.match(r'map_L\d+_(\d+)_(\d+)_map\.csv', filename or '')
        if m:
            return f"{m.group(1)}_{m.group(2)}"
        if re.match(r'map_L\d+_world_map\.csv', filename or ''):
            return 'world'
        return None

    def _is_loaded_chunk(self, map_filename):
        """True if map_filename belongs to the chunk currently loaded in game.all_map_layers."""
        if not map_filename:
            return True
        k = self._chunk_key(map_filename)
        cur = self._chunk_key(self.current_map_filename)
        if k is None or cur is None:
            return True
        return k == cur

    def _layer_csv_path(self, layer, map_filename):
        fname = re.sub(r'^map_L\d+_', f'map_L{layer}_', map_filename or self.current_map_filename)
        return os.path.join(self.map_folder, fname)

    def _get_layer_grid(self, layer, map_filename=None):
        """Returns the base-tile grid of `layer` for the chunk named by `map_filename`.
        Loaded chunk -> live in-memory grid. Any other chunk -> grid read from its CSV."""
        if self._is_loaded_chunk(map_filename):
            layers = getattr(self.game, 'all_map_layers', None) or {}
            if layer in layers:
                return layers[layer]
            if layer == getattr(self.game, 'current_layer_index', 1):
                return self.game.map_data
            return None

        key = (layer, self._chunk_key(map_filename))
        grid = self.offchunk_grids.get(key)
        if grid is None:
            path = self._layer_csv_path(layer, map_filename)
            if not os.path.exists(path):
                return None
            try:
                with open(path, 'r', newline='', encoding='utf-8') as f:
                    grid = list(csv.reader(f))
            except Exception as e:
                print(f"Error loading off-chunk grid {path}: {e}")
                return None
            self.offchunk_grids[key] = grid
        return grid

    def _write_layer_grid(self, layer, map_filename, grid):
        path = self._layer_csv_path(layer, map_filename)
        try:
            if os.path.isdir(os.path.dirname(path)):
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerows(grid)
        except Exception as e:
            print(f"Error persisting tile change to {path}: {e}")

    def apply_network_tile_change(self, grid_x, grid_y, new_char, layer, map_filename=None):
        """CLIENT: applies a server 'tile_change' to the chunk it belongs to (and to the local
        cache CSV, so re-entering that chunk shows the right state).
        Returns True if the change is visible in the live viewport."""
        grid = self._get_layer_grid(layer, map_filename)
        if not grid or not (0 <= grid_y < len(grid) and 0 <= grid_x < len(grid[grid_y])):
            return False
        grid[grid_y][grid_x] = new_char
        self._write_layer_grid(layer, map_filename, grid)
        return self._is_loaded_chunk(map_filename) and layer == getattr(self.game, 'current_layer_index', 1)

    def _get_adjacent_bg(self, grid, x, y):
        """Helper to find the adjacent solid terrain to fill transparent gaps in live chunks."""
        h = len(grid)
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= ny < h:
                row = grid[ny]
                if 0 <= nx < len(row):
                    neighbor = row[nx]
                    # [UPDATED] Include asphalt in the transparency check
                    is_transparent_overlay = neighbor and (
                        (neighbor.startswith('dirty_') and neighbor != 'dirty_01') or 
                        (neighbor.startswith('beach_sand_') and neighbor != 'beach_sand_01') or 
                        (neighbor.startswith('sand_') and neighbor != 'sand_01') or 
                        (neighbor.startswith('asphalt_') and neighbor != 'asphalt_01')
                    )
                    if neighbor and not is_transparent_overlay and neighbor != ' ':
                        return neighbor
        return 'dirty_01' if getattr(self.game, 'current_layer_index', 1) in (2, 3) else 'bg_grass'

    def get_chunk_surface(self, cx, cy, layer_idx, layer_type='world'):
        """
        Returns a cached surface for a specific chunk. 
        layer_type: 'world' (Ground + Base objects) or 'roof'
        """
        key = (layer_idx, cx, cy, layer_type)
        if key in self.chunk_surfaces:
            return self.chunk_surfaces[key]

        # [NEW] Throttling: If we generated too many chunks this frame, postpone this one.
        if self.chunks_generated_this_frame >= self.MAX_CHUNKS_PER_FRAME:
            return None

        self.chunks_generated_this_frame += 1

        # Calculate dimensions
        pixel_size = self.CHUNK_SIZE * TILE_SIZE
        surface = pygame.Surface((pixel_size, pixel_size), pygame.SRCALPHA)
        
        min_x = cx * self.CHUNK_SIZE
        min_y = cy * self.CHUNK_SIZE
        max_x = min_x + self.CHUNK_SIZE
        max_y = min_y + self.CHUNK_SIZE

        # Determine data sources
        ground_data = None
        base_data = None
        roof_data = None
        light_data = None

        # If requesting the currently active layer, use the direct references for speed
        if layer_idx == self.game.current_layer_index:
            ground_data = getattr(self.game, 'ground_data', None)
            base_data = getattr(self.game, 'map_data', None)
            roof_data = getattr(self.game, 'roof_data', None)
            light_data = getattr(self.game, 'light_data', None)
        else:
            # Otherwise fetch from storage
            if hasattr(self.game, 'all_ground_layers'):
                ground_data = self.game.all_ground_layers.get(layer_idx)
            if hasattr(self.game, 'all_map_layers'):
                base_data = self.game.all_map_layers.get(layer_idx)
            if hasattr(self.game, 'all_roof_layers'):
                roof_data = self.game.all_roof_layers.get(layer_idx)
            if hasattr(self.game, 'all_light_layers'):
                light_data = self.game.all_light_layers.get(layer_idx)

        tm = self.game.tile_manager

        # Render Tiles to Surface
        if layer_type == 'world':
            # 1. Ground Layer
            if ground_data:
                # [FIX] Safer bounds checking (ragged array support + negative index prevention)
                y_start = max(0, min_y)
                y_end = min(max_y, len(ground_data))
                
                for y in range(y_start, y_end):
                    row_data = ground_data[y]
                    # Calculate row length per row to prevent IndexError on ragged maps
                    row_len = len(row_data) 
                    
                    x_start = max(0, min_x)
                    x_end = min(max_x, row_len)
                    
                    for x in range(x_start, x_end):
                        char = row_data[x]
                        if char and char != ' ':
                            is_dirty_overlay = char.startswith('dirty_') and char != 'dirty_01'
                            is_sand_overlay = char.startswith('sand_') and char != 'sand_01'
                            is_beach_sand_overlay = char.startswith('beach_sand_') and char != 'beach_sand_01'
                            # [UPDATED] Add Asphalt overlay check
                            is_asphalt_overlay = char.startswith('asphalt_') and char != 'asphalt_01'
                            
                            if is_dirty_overlay or is_sand_overlay or is_beach_sand_overlay or is_asphalt_overlay:
                                bg_tile = self._get_adjacent_bg(ground_data, x, y)
                                if bg_tile in tm.definitions:
                                    surface.blit(tm.definitions[bg_tile]['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))

                            defn = tm.definitions.get(char)
                            if defn:
                                surface.blit(defn['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))
                        else:
                            fallback = 'dirty_01' if layer_idx in (2, 3) else 'bg_grass'
                            if fallback in tm.definitions:
                                surface.blit(tm.definitions[fallback]['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))
            
            # 2. Base Layer (Walls, Objects)
            if base_data:
                y_start = max(0, min_y)
                y_end = min(max_y, len(base_data))

                for y in range(y_start, y_end):
                    row_data = base_data[y]
                    row_len = len(row_data)

                    x_start = max(0, min_x)
                    x_end = min(max_x, row_len)

                    for x in range(x_start, x_end):
                        char = row_data[x]
                        if char and char != ' ':
                            defn = tm.definitions.get(char)
                            if defn:
                                surface.blit(defn['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))

            # 3. Light Layer (Light source tiles)
            if light_data:
                y_start = max(0, min_y)
                y_end = min(max_y, len(light_data))

                for y in range(y_start, y_end):
                    row_data = light_data[y]
                    row_len = len(row_data)

                    x_start = max(0, min_x)
                    x_end = min(max_x, row_len)

                    for x in range(x_start, x_end):
                        char = row_data[x]
                        if char and char != ' ':
                            defn = tm.definitions.get(char)
                            if defn:
                                surface.blit(defn['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))

        elif layer_type == 'roof':
            if roof_data:
                y_start = max(0, min_y)
                y_end = min(max_y, len(roof_data))
                
                for y in range(y_start, y_end):
                    row_data = roof_data[y]
                    row_len = len(row_data)

                    x_start = max(0, min_x)
                    x_end = min(max_x, row_len)

                    for x in range(x_start, x_end):
                        char = row_data[x]
                        if char and char != ' ':
                            defn = tm.definitions.get(char)
                            if defn:
                                surface.blit(defn['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))

        surface = surface.convert_alpha() 
        self.chunk_surfaces[key] = surface
        return surface

    def get_vehicle_at(self, grid_x, grid_y):
        """
        Finds a dynamic vehicle object located at the given grid coordinates.
        Used by handle_right_click in mouse.py.
        """
        for vehicle in self.game.vehicles:
            veh_grid_x = int(vehicle.x // TILE_SIZE)
            veh_grid_y = int(vehicle.y // TILE_SIZE)
            tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if vehicle.rect.colliderect(tile_rect):
                return vehicle
        return None

    def get_tile_at(self, grid_x, grid_y):
        """Gets the tile definition at a specific grid coordinate."""
        if self.game.map_data and 0 <= grid_y < len(self.game.map_data) and 0 <= grid_x < len(self.game.map_data[0]):
            char = self.game.map_data[grid_y][grid_x]
            if char in self.game.tile_manager.definitions:
                return self.game.tile_manager.definitions[char]
            if hasattr(self.game, 'ground_data') and self.game.ground_data:
                if 0 <= grid_y < len(self.game.ground_data) and 0 <= grid_x < len(self.game.ground_data[0]):
                    g_char = self.game.ground_data[grid_y][grid_x]
                    if g_char in self.game.tile_manager.definitions:
                        return self.game.tile_manager.definitions[g_char]
        return None

    def save_map_to_file(self, save_dir):
        """Saves the current state of map layers to CSV files in the save directory."""
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        def write_layer(layout, filename):
            path = os.path.join(save_dir, filename)
            try:
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(layout)
                print(f"Saved map layer to {path}")
            except Exception as e:
                print(f"Error saving map layer {filename}: {e}")

        # Extract base prefix to save using chunk nomenclature
        current_name = self.current_map_filename
        chunk_match = re.match(r'map_L\d+_(\d+)_(\d+)_map\.csv', current_name)

        if hasattr(self.game, 'all_map_layers'):
            for layer_idx, layout in self.game.all_map_layers.items():
                if chunk_match:
                    gx, gy = chunk_match.groups()
                    filename = f'map_L{layer_idx}_{gx}_{gy}_map.csv'
                else:
                    filename = f'map_L{layer_idx}_world_map.csv'
                write_layer(layout, filename)
        
        if hasattr(self.game, 'all_spawn_layers'):
            for layer_idx, layout in self.game.all_spawn_layers.items():
                if chunk_match:
                    gx, gy = chunk_match.groups()
                    filename = f'map_L{layer_idx}_{gx}_{gy}_spawn.csv'
                else:
                    filename = f'map_L{layer_idx}_world_spawn.csv'
                write_layer(layout, filename)

    def toggle_door_state(self, grid_x, grid_y, layer=None, map_filename=None):
        """Toggles a 'statable' tile (like a door) between its states.
        layer/map_filename identify the chunk+layer the door lives in - a client can be in a
        different chunk than the one the server has loaded."""
        if layer is None:
            layer = getattr(self.game, 'current_layer_index', 1)
        if map_filename is None:
            map_filename = self.current_map_filename

        if getattr(self.game, 'is_client', False):
            from core.server.network import NetMsg, send_msg
            send_msg(self.game.client.socket, {
                'type': NetMsg.WORLD_ACTION, 'action': 'toggle_door',
                'x': grid_x, 'y': grid_y, 'layer': layer,
                'map_filename': map_filename
            })
            return

        if self.get_barricade(grid_x, grid_y, map_filename):
            display_message(tr('msg', "Door is barricaded!"))
            return

        is_loaded = self._is_loaded_chunk(map_filename)
        target_map = self._get_layer_grid(layer, map_filename)
        if not target_map or not (0 <= grid_y < len(target_map) and 0 <= grid_x < len(target_map[grid_y])):
            return

        current_char = target_map[grid_y][grid_x]
        current_def = self.game.tile_manager.definitions.get(current_char)

        if not current_def or not current_def.get('is_statable'):
            return

        if 'barricate' in current_char or 'barricad' in current_char:
            return

        current_state = current_def.get('state')
        new_state = "open" if current_state == "close" else "close"

        tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        door_cx = tile_rect.centerx
        door_cy = tile_rect.centery

        if new_state == "close":
            target_key = self._chunk_key(map_filename)
            is_dedicated = getattr(self.game, 'is_dedicated', False)

            def in_target_chunk(e):
                # Dedicated server / remote players carry their own map; host-local entities live in the loaded chunk
                if is_dedicated or type(e).__name__ == 'RemotePlayer':
                    ek = self._chunk_key(getattr(e, 'map_filename', ''))
                    if ek is not None:
                        return ek == target_key
                return is_loaded

            entities_to_check = []
            player = getattr(self.game, 'player', None)
            if player and not getattr(player, 'is_dead', False):
                if is_loaded and getattr(self.game, 'current_layer_index', 1) == layer:
                    entities_to_check.append(player)
            for z in getattr(self.game, 'zombies', []):
                if not getattr(z, 'is_dead', False) and getattr(z, 'health', 0) > 0:
                    if getattr(z, 'layer', 1) == layer and in_target_chunk(z):
                        entities_to_check.append(z)
            for n in getattr(self.game, 'npcs', []):
                if not getattr(n, 'is_dead', False) and getattr(n, 'health', 0) > 0:
                    if getattr(n, 'layer', 1) == layer and in_target_chunk(n):
                        entities_to_check.append(n)
            for a in getattr(self.game, 'active_animals', []):
                if not getattr(a, 'is_dead', False) and getattr(a, 'health', 0) > 0:
                    if getattr(a, 'layer', 1) == layer and in_target_chunk(a):
                        entities_to_check.append(a)
            for rp in getattr(self.game, 'remote_players', {}).values():
                if not getattr(rp, 'is_dead', False) and getattr(rp, 'layer', 1) == layer and in_target_chunk(rp):
                    entities_to_check.append(rp)

            entities_in_door = [e for e in entities_to_check if e.rect.colliderect(tile_rect)]

            def is_tile_walkable(tx, ty):
                if not (0 <= ty < len(target_map) and 0 <= tx < len(target_map[ty])):
                    return False
                t_def = self.game.tile_manager.definitions.get(target_map[ty][tx])
                if t_def and t_def.get('is_obstacle', False):
                    return False
                return True

            for entity in entities_in_door:
                ex = entity.rect.centerx
                ey = entity.rect.centery
                dx = ex - door_cx
                dy = ey - door_cy

                target_candidates = [
                    (grid_x, grid_y - 1), (grid_x, grid_y + 1),
                    (grid_x - 1, grid_y), (grid_x + 1, grid_y)
                ]
                if abs(dx) > abs(dy):
                    target_candidates.sort(key=lambda c: -abs(c[0] - grid_x))
                else:
                    target_candidates.sort(key=lambda c: -abs(c[1] - grid_y))

                for tgx, tgy in target_candidates:
                    if is_tile_walkable(tgx, tgy):
                        target_rect = pygame.Rect(tgx * TILE_SIZE, tgy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        entity.rect.center = target_rect.center
                        if hasattr(entity, 'x'): entity.x = float(entity.rect.x)
                        if hasattr(entity, 'y'): entity.y = float(entity.rect.y)
                        break

        base_name = current_char.replace("_open", "").replace("_close", "")
        new_char = f"{base_name}_{new_state}"

        if new_char in self.game.tile_manager.definitions:
            new_def = self.game.tile_manager.definitions[new_char]
            self._replace_tile(grid_x, grid_y, current_char, new_char, layer=layer, map_filename=map_filename)

            # Positional sound only makes sense for the chunk we actually have loaded
            if new_def.get('sound_src') and is_loaded:
                self.game.sound_manager.play_sound(
                    new_def['sound_src'],
                    subdir='map',
                    game=self.game,
                    source_pos=tile_rect.center,
                    base_volume=0.4,
                    pitch_variance=0.15,
                    is_critical=True
                )
        else:
            print(f"Warning: Could not find matching door state '{new_char}'")
    

    def draw_tile_health_bars(self, surface, offset_x, offset_y):
        if not self.tile_hit_timers:
            return

        coords = list(self.tile_hit_timers.keys())
        map_name = self.current_map_filename

        for pos in coords:
            grid_x, grid_y = pos
            barricade = self.get_barricade(grid_x, grid_y)
            
            draw_x = grid_x * TILE_SIZE + offset_x
            draw_y = grid_y * TILE_SIZE + offset_y - 6

            bg_bar_rect = pygame.Rect(draw_x, draw_y, TILE_SIZE, 4)

            # --- FIX: Clean Game-Standard UI design (No outlines) ---
            if barricade:
                pygame.draw.rect(surface, (30, 30, 30), bg_bar_rect)
                pct = max(0.0, min(1.0, barricade['health'] / barricade['max_health']))
                bar_rect = pygame.Rect(draw_x, draw_y, int(pct * TILE_SIZE), 4)
                pygame.draw.rect(surface, YELLOW, bar_rect)

            elif map_name in self.game.map_states and 'tile_health' in self.game.map_states[map_name]:
                if pos in self.game.map_states[map_name]['tile_health']:
                    current_hp = self.game.map_states[map_name]['tile_health'][pos]
                    char = self.game.map_data[grid_y][grid_x]
                    defn = self.game.tile_manager.definitions.get(char)
                    
                    base_name = char.replace("_open", "").replace("_close", "").replace("_broke", "")
                    close_def = self.game.tile_manager.definitions.get(f"{base_name}_close")
                    max_hp = (defn.get('health_max') if defn and defn.get('health_max') else 
                              (close_def.get('health_max', 100) if close_def else 100))

                    pygame.draw.rect(surface, (30, 30, 30), bg_bar_rect)
                    pct = max(0.0, min(1.0, current_hp / max_hp))
                    bar_color = GREEN if pct > 0.5 else (YELLOW if pct > 0.25 else RED)
                    bar_rect = pygame.Rect(draw_x, draw_y, int(pct * TILE_SIZE), 4)
                    pygame.draw.rect(surface, bar_color, bar_rect)

            self.tile_hit_timers[pos] -= 1
            if self.tile_hit_timers[pos] <= 0:
                del self.tile_hit_timers[pos]

    
    def is_tile_destructible(self, grid_x, grid_y):
        """Checks if a tile can receive damage (has a barricade, destructible tag, or door/window)."""
        if not self.game.map_data or not (0 <= grid_y < len(self.game.map_data) and 0 <= grid_x < len(self.game.map_data[0])):
            return False
        if self.get_barricade(grid_x, grid_y):
            return True
        char = self.game.map_data[grid_y][grid_x]
        tile_def = self.game.tile_manager.definitions.get(char)
        if not tile_def:
            return False
        if tile_def.get('destructible'):
            return True
        if '_open' in char or '_close' in char or 'door' in char.lower() or 'window' in char.lower():
            base_name = char.replace("_open", "").replace("_close", "").replace("_broke", "")
            if f"{base_name}_broke" in self.game.tile_manager.definitions:
                return True
        return False

    def get_barricade(self, grid_x, grid_y, map_filename=None):
        map_name = map_filename or self.current_map_filename
        if map_name in self.game.map_states and 'barricades' in self.game.map_states[map_name]:
            return self.game.map_states[map_name]['barricades'].get((grid_x, grid_y))
        return None

    def add_barricade(self, grid_x, grid_y, item):
        map_name = self.current_map_filename
        if map_name not in self.game.map_states:
            self.game.map_states[map_name] = {}
        if 'barricades' not in self.game.map_states[map_name]:
            self.game.map_states[map_name]['barricades'] = {}

        max_hp = getattr(item, 'barricade_health', 30) or 30
        sprite_img = getattr(item, 'image', None)
        if not sprite_img:
            item_def = Item.create_from_name(item.name)
            if item_def and item_def.image:
                sprite_img = item_def.image

        self.game.map_states[map_name]['barricades'][(grid_x, grid_y)] = {
            'item': item,
            'item_name': item.name,
            'health': max_hp,
            'max_health': max_hp,
            'remove_items': getattr(item, 'remove_items', ['Crowbar', 'Hammer']),
            'remove_time': getattr(item, 'remove_time', 1.5),
            'sprite': sprite_img
        }

        tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        if tile_rect not in self.game.obstacles:
            self.game.obstacles.append(tile_rect)

        self.invalidate_chunk(grid_x, grid_y)

    def remove_barricade(self, grid_x, grid_y):
        map_name = self.current_map_filename
        if map_name in self.game.map_states and 'barricades' in self.game.map_states[map_name]:
            b_data = self.game.map_states[map_name]['barricades'].pop((grid_x, grid_y), None)
            
            tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            char = self.game.map_data[grid_y][grid_x]
            tile_def = self.game.tile_manager.definitions.get(char)
            
            is_obstacle = tile_def and tile_def.get('is_obstacle', False)
            if not is_obstacle and tile_rect in self.game.obstacles:
                self.game.obstacles.remove(tile_rect)
            elif is_obstacle and tile_rect not in self.game.obstacles:
                self.game.obstacles.append(tile_rect)

            self.invalidate_chunk(grid_x, grid_y)
            return b_data
        return None

    def hit_tile(self, grid_x, grid_y, damage, weapon=None, is_projectile=False, attacker=None, layer=None):
        if layer is None:
            layer = getattr(self.game, 'current_layer_index', 1)

        if getattr(self.game, 'is_client', False) and not getattr(self, '_ignore_net', False):
            from core.server.network import NetMsg, send_msg
            send_msg(self.game.client.socket, {
                'type': NetMsg.WORLD_ACTION, 'action': 'hit_tile',
                'x': grid_x, 'y': grid_y, 'damage': damage, 'layer': layer
            })
            import time
            self.shaking_tiles[(grid_x, grid_y)] = time.time()
            return True
            
        if not self.game.map_data or not (0 <= grid_y < len(self.game.map_data) and 0 <= grid_x < len(self.game.map_data[0])):
            return False

        char = self.game.map_data[grid_y][grid_x]
        definition = self.game.tile_manager.definitions.get(char)
        
        barricade = self.get_barricade(grid_x, grid_y)
        if not barricade and not self.is_tile_destructible(grid_x, grid_y):
            return False

        self.tile_hit_timers[(grid_x, grid_y)] = 60
        is_player = (attacker is None) or (attacker == getattr(self.game, 'player', None))

        if not is_projectile and is_player:
            STAMINA_COST = 0.05
            if self.game.player.stamina < STAMINA_COST:
                display_message(tr('msg', "You are too exhausted to chop/mine!"))
                return True
            self.game.player.stamina = max(0, self.game.player.stamina - STAMINA_COST)

            if weapon and weapon.durability is not None:
                DURABILITY_COST = 0.05
                weapon.durability = max(0, weapon.durability - DURABILITY_COST)
                if weapon.durability <= 0:
                    self.game.player.active_weapon = None
                    display_message(f"{tr('item', weapon.name)} {tr('msg', 'is broken and unequipped.')}")
                    return True

        # Play sound
        if definition and definition.get('sound_src'):
            tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            self.game.sound_manager.play_sound(
                definition['sound_src'], 
                subdir='map', 
                game=self.game,
                source_pos=tile_rect.center, 
                base_volume=0.4, 
                pitch_variance=0.15
            )

        import time
        # Trigger shake effect
        self.shaking_tiles[(grid_x, grid_y)] = time.time()
        if getattr(self.game, 'is_server', False):
            from core.server.network import NetMsg, send_msg
            for s in self.game.server.clients:
                send_msg(s, {
                    'type': NetMsg.WORLD_ACTION, 'action': 'shake_tile',
                    'x': grid_x, 'y': grid_y
                })

        # 1. BARRICADE ABSORPTION
        if barricade:
            barricade['health'] -= damage
            if barricade['health'] <= 0:
                self.remove_barricade(grid_x, grid_y)
                display_message(tr('msg', "Barricade destroyed!"))
                return True
            else:
                return True

        # 2. DOOR / WINDOW / DESTRUCTIBLE TILE DAMAGE
        map_name = self.current_map_filename
        if map_name not in self.game.map_states:
            self.game.map_states[map_name] = {}
        if 'tile_health' not in self.game.map_states[map_name]:
            self.game.map_states[map_name]['tile_health'] = {}

        pos_key = (grid_x, grid_y)
        if pos_key not in self.game.map_states[map_name]['tile_health']:
            max_h = definition.get('health_max') if definition else None
            min_h = definition.get('health_min') if definition else None
            if not max_h:
                base_name = char.replace("_open", "").replace("_close", "").replace("_broke", "")
                close_def = self.game.tile_manager.definitions.get(f"{base_name}_close")
                if close_def and close_def.get('health_max'):
                    max_h = close_def.get('health_max')
                    min_h = close_def.get('health_min', max_h)
                else:
                    max_h = 100
                    min_h = 60
            self.game.map_states[map_name]['tile_health'][pos_key] = random.randint(min_h, max_h)

        if barricade:
            barricade['health'] -= damage
            if barricade['health'] <= 0:
                self.remove_barricade(grid_x, grid_y)
                display_message(tr('msg', "Barricade destroyed!"))
                return True
            else:
                return True

        self.game.map_states[map_name]['tile_health'][pos_key] -= damage
        current_hp = self.game.map_states[map_name]['tile_health'][pos_key]

        if current_hp <= 0:
            del self.game.map_states[map_name]['tile_health'][pos_key]
            if (grid_x, grid_y) in self.shaking_tiles:
                del self.shaking_tiles[(grid_x, grid_y)]

            # 1. Process and spawn tile item drops
            if definition and definition.get('drops'):
                spawn_x = grid_x * TILE_SIZE
                spawn_y = grid_y * TILE_SIZE

                m = getattr(core.data.config, 'ITEM_SPAWN_CHANCE_MULTIPLIER', 1.0)
                lucky_bonus = 0.0
                if is_player and getattr(self.game, 'player', None):
                    lucky_bonus = self.game.player.progression.get_lucky(self.game.player) * 0.05

                for drop in definition['drops']:
                    item_name = drop.get('item')
                    if not item_name:
                        continue

                    chance = drop.get('chance', 1.0) * m * (1.0 + lucky_bonus)
                    if random.random() <= chance:
                        min_q = drop.get('min_qty', 1)
                        max_q = drop.get('max_qty', 1)
                        qty = random.randint(min_q, max_q)

                        for _ in range(qty):
                            new_item = Item.create_from_name(item_name)
                            if new_item:
                                new_item.rect.topleft = (spawn_x, spawn_y)
                                new_item.x = spawn_x
                                new_item.y = spawn_y
                                new_item.is_placed = False
                                new_item.layer = getattr(self.game, 'current_layer_index', 1)
                                new_item.map_filename = getattr(self, 'current_map_filename', '')

                                free_spot = find_free_tile(new_item.rect, self.game.obstacles, initial_pos=(spawn_x, spawn_y), max_radius=2)
                                if free_spot:
                                    new_item.rect.topleft = free_spot
                                    new_item.x, new_item.y = free_spot

                                self.game.items_on_ground.append(new_item)

                if hasattr(self.game, 'spatial_manager'):
                    self.game.spatial_manager.rebuild_item_grid(force=True)

            # 2. Determine target tile state (broken sprite or empty space)
            base_name = char.replace("_open", "").replace("_close", "").replace("_broke", "")
            broken_char = f"{base_name}_broke"
            if broken_char in self.game.tile_manager.definitions:
                target_char = broken_char
                display_message(tr('msg', "Door/Window broken!"))
            else:
                target_char = ' '
                tile_name = definition.get('name', 'Object') if definition else 'Object'
                display_message(f"{tr('tile', tile_name)} {tr('msg', 'destroyed!')}")

            self._replace_tile(grid_x, grid_y, char, target_char)
        return True

    def _replace_tile(self, grid_x, grid_y, old_char, new_char, layer=None, map_filename=None):
        if layer is None:
            layer = getattr(self.game, 'current_layer_index', 1)
        if map_filename is None:
            map_filename = getattr(self, 'current_map_filename', '')

        new_def = self.game.tile_manager.definitions.get(new_char) if new_char != ' ' else None
        tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        is_loaded = self._is_loaded_chunk(map_filename)

        # 1. Update the grid of the chunk the tile REALLY belongs to (loaded grid or off-chunk CSV grid)
        layer_grid = self._get_layer_grid(layer, map_filename)
        if layer_grid and 0 <= grid_y < len(layer_grid) and 0 <= grid_x < len(layer_grid[grid_y]):
            layer_grid[grid_y][grid_x] = new_char
        else:
            layer_grid = None

        # 2. Update active map_data and obstacles only if that chunk+layer is currently rendered
        if is_loaded and layer == getattr(self.game, 'current_layer_index', 1):
            if self.game.map_data and 0 <= grid_y < len(self.game.map_data) and 0 <= grid_x < len(self.game.map_data[grid_y]):
                self.game.map_data[grid_y][grid_x] = new_char
            self.game.obstacles = [rect for rect in self.game.obstacles if rect != tile_rect]
            if new_def and new_def.get('is_obstacle', False):
                self.game.obstacles.append(tile_rect)
            self.invalidate_chunk(grid_x, grid_y)
            self.game.cached_obstacle_count = -1

        # 3. Server: persist to the correct chunk file and tell the clients
        if getattr(self.game, 'is_server', False):
            if layer_grid is not None and self.map_folder and os.path.exists(self.map_folder):
                self._write_layer_grid(layer, map_filename, layer_grid)

            from core.server.network import NetMsg, send_msg
            for s in self.game.server.clients:
                send_msg(s, {
                    'type': NetMsg.WORLD_ACTION, 'action': 'tile_change',
                    'x': grid_x, 'y': grid_y, 'char': new_char, 'layer': layer,
                    'map_filename': map_filename
                })
    
    def remove_vehicle_tile(self, grid_x, grid_y):
        """
        Call this when a player starts driving to remove the static tile 
        representation of the car from the map data.
        """
        try:
            ground_char = self.game.all_ground_layers[self.game.current_layer_index][grid_y][grid_x]
        except (KeyError, IndexError, AttributeError):
            ground_char = "."
            
        self._replace_tile(grid_x, grid_y, self.game.map_data[grid_y][grid_x], ground_char)