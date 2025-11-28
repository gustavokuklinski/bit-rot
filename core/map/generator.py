import os
import random
import csv
import pygame
import math
from core.data.config import *
from core.map.building_loader import load_building_templates

class ProceduralGenerator:
    def __init__(self, game, output_folder=None):
        self.game = game
        self.chunk_size = 100 # 100x100 tiles per chunk
        self.tile_size = TILE_SIZE
        self.output_folder = output_folder if output_folder else MAP_DIR
        self.buildings_path = os.path.join(MAP_DIR, 'buildings')
        self.templates = load_building_templates(self.buildings_path)
        
        # 1. Identify Forest Tiles (Single tiles for scattering/borders)
        self.forest_tiles = []
        if hasattr(self.game, 'tile_manager'):
            # Find all tiles that start with "Forest_" to use for nature
            self.forest_tiles = [k for k in self.game.tile_manager.definitions.keys() if k.startswith('Forest_')]
        
        if not self.forest_tiles:
            # Fallback defaults
            self.forest_tiles = ['garden_tree_1', 'garden_tree_8', 'garden_stone', 'Forest_Tree_1']

        # 2. Identify Templates
        self.building_categories = ["Building", "Stores", "Condo", "Warehouses"]
        
        self.target_templates = []   # Main buildings (Stores, etc.)
        self.forest_templates = []   # Forest structures (Forest_1, Forest_2, etc.)

        for name in self.templates.keys():
            # Check for Forest templates
            if name.startswith("Forest_"):
                self.forest_templates.append(name)
            # Check for Target Buildings
            elif any(cat in name for cat in self.building_categories):
                self.target_templates.append(name)
        
        # Fallback: If no specific targets, use everything not Forest
        if not self.target_templates:
             self.target_templates = [k for k in self.templates.keys() if not k.startswith("Forest_")]

    def generate_world(self, seed_pattern="30DEFAULT", regenerate=False):
        """
        Generates a grid of maps using a Maze-based Chunk approach.
        """
        try:
            if '0' in seed_pattern:
                parts = seed_pattern.split('0', 1)
                n_part = parts[0]
                if not n_part: n_part = "5"
                grid_w = int(n_part)
                grid_h = int(n_part)
                actual_seed = parts[1]
                if not actual_seed: actual_seed = "DEFAULT"
            else:
                grid_w, grid_h = 3, 3
                actual_seed = seed_pattern
        except ValueError:
            print(f"Invalid seed pattern '{seed_pattern}'. Defaulting to 5x5.")
            grid_w, grid_h = 3, 3
            actual_seed = "DEFAULT"

        print(f"Applying World Seed: {actual_seed} | Size: {grid_w}x{grid_h}")
        random.seed(actual_seed)

        expected_chunks = grid_w * grid_h
        
        if not regenerate and self._maps_exist(expected_chunks):
            print("World already exists in save folder. Skipping generation.")
            for f in os.listdir(self.output_folder):
                if f.startswith("map_L1_P0_") and f.endswith("_map.csv"):
                    return f
            return None

        print(f"Generating {grid_w}x{grid_h} Dungeon-Crawler World...")        
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # 1. Generate the Connection Matrix
        connections_grid = self._generate_maze_connections(grid_w, grid_h)

        # 2. Render each Chunk
        total_map_w = grid_w * self.chunk_size * self.tile_size
        total_map_h = grid_h * self.chunk_size * self.tile_size
        full_map_surface = pygame.Surface((total_map_w, total_map_h))
        start_map_filename = None

        for gy in range(grid_h):
            for gx in range(grid_w):
                pos_id = (gy * grid_w) + gx
                conns = connections_grid[gy][gx]
                
                conn_top = 1 if conns['top'] else 0
                conn_right = 1 if conns['right'] else 0
                conn_bottom = 1 if conns['bottom'] else 0
                conn_left = 1 if conns['left'] else 0
                
                chunk_data = self._generate_chunk_data(gx, gy, conns, is_start=(pos_id==0))
                
                filename_base = f"map_L1_P{pos_id}_{conn_top}_{conn_right}_{conn_bottom}_{conn_left}"
                
                self._save_chunk(filename_base, chunk_data)
                self._render_chunk_to_surface(full_map_surface, gx, gy, chunk_data)

                if pos_id == 0:
                    start_map_filename = filename_base + "_map.csv"

        try:
            image_path = os.path.join(self.output_folder, "full_map.jpg")
            pygame.image.save(full_map_surface, image_path)
            print(f"Full map image saved to {image_path}")
        except Exception as e:
            print(f"Error saving full map image: {e}")

        return start_map_filename

    def _maps_exist(self, expected_count):
        if not os.path.exists(self.output_folder): return False
        return len([f for f in os.listdir(self.output_folder) if f.endswith('_map.csv')]) >= expected_count

    def _generate_maze_connections(self, w, h):
        grid = [[{'visited': False, 'top': False, 'right': False, 'bottom': False, 'left': False} for _ in range(w)] for _ in range(h)]
        stack = [(0, 0)]
        grid[0][0]['visited'] = True
        
        while stack:
            cx, cy = stack[-1]
            neighbors = []
            
            if cy > 0 and not grid[cy-1][cx]['visited']: neighbors.append(('top', cx, cy-1))
            if cx < w - 1 and not grid[cy][cx+1]['visited']: neighbors.append(('right', cx+1, cy))
            if cy < h - 1 and not grid[cy+1][cx]['visited']: neighbors.append(('bottom', cx, cy+1))
            if cx > 0 and not grid[cy][cx-1]['visited']: neighbors.append(('left', cx-1, cy))
                
            if neighbors:
                direction, nx, ny = random.choice(neighbors)
                if direction == 'top':
                    grid[cy][cx]['top'] = True; grid[ny][nx]['bottom'] = True
                elif direction == 'right':
                    grid[cy][cx]['right'] = True; grid[ny][nx]['left'] = True
                elif direction == 'bottom':
                    grid[cy][cx]['bottom'] = True; grid[ny][nx]['top'] = True
                elif direction == 'left':
                    grid[cy][cx]['left'] = True; grid[ny][nx]['right'] = True
                grid[ny][nx]['visited'] = True
                stack.append((nx, ny))
            else:
                stack.pop()
        
        extra_connections = int((w * h) * 0.2)
        for _ in range(extra_connections):
            rx = random.randint(0, w-1)
            ry = random.randint(0, h-1)
            possible = []
            if ry > 0 and not grid[ry][rx]['top']: possible.append('top')
            if rx < w - 1 and not grid[ry][rx]['right']: possible.append('right')
            if ry < h - 1 and not grid[ry][rx]['bottom']: possible.append('bottom')
            if rx > 0 and not grid[ry][rx]['left']: possible.append('left')
            if possible:
                d = random.choice(possible)
                if d == 'top': grid[ry][rx]['top'] = True; grid[ry-1][rx]['bottom'] = True
                elif d == 'right': grid[ry][rx]['right'] = True; grid[ry][rx+1]['left'] = True
                elif d == 'bottom': grid[ry][rx]['bottom'] = True; grid[ry+1][rx]['top'] = True
                elif d == 'left': grid[ry][rx]['left'] = True; grid[ry][rx-1]['right'] = True
        return grid

    def _generate_chunk_data(self, gx, gy, conns, is_start=False):
        w, h = self.chunk_size, self.chunk_size
        cx, cy = w // 2, h // 2
        
        layers = {
            'base': [[' ' for _ in range(w)] for _ in range(h)],
            'ground': [['bg_grass' for _ in range(w)] for _ in range(h)],
            'spawn': [[' ' for _ in range(w)] for _ in range(h)],
            'roof': [[' ' for _ in range(w)] for _ in range(h)]
        }
        # Mask: 0 = free, 1 = occupied (roads, borders, buildings)
        occupied_mask = [[0 for _ in range(w)] for _ in range(h)]

        # 1. Draw Roads
        road_tile = 'dirty_01'
        road_r = 2 
        
        def draw_road(x1, y1, x2, y2):
            sx, ex = min(x1, x2), max(x1, x2)
            sy, ey = min(y1, y2), max(y1, y2)
            for y in range(sy - road_r, ey + road_r + 1):
                for x in range(sx - road_r, ex + road_r + 1):
                    if 0 <= x < w and 0 <= y < h:
                        layers['ground'][y][x] = road_tile
                        occupied_mask[y][x] = 1
        
        draw_road(cx, cy, cx, cy) # Hub
        if conns['top']: draw_road(cx, 0, cx, cy)
        if conns['bottom']: draw_road(cx, cy, cx, h-1)
        if conns['left']: draw_road(0, cy, cx, cy)
        if conns['right']: draw_road(cx, cy, w-1, cy)

        # 2. Draw Border (Single Tiles)
        border_w = 2
        for y in range(h):
            for x in range(w):
                if x < border_w or x >= w - border_w or y < border_w or y >= h - border_w:
                    if occupied_mask[y][x] == 0:
                        tile = random.choice(self.forest_tiles) if self.forest_tiles else 'wall_stone'
                        layers['base'][y][x] = tile
                        occupied_mask[y][x] = 1

        # 3. Place Target Buildings (at least 5)
        placed_rects = [] 
        buildings_placed = 0
        target_count = 5 
        attempts = 0
        
        # Helper to check if a rect is free
        def is_area_free(tx, ty, tw, th, margin=0):
            # Check overlap with existing rects
            t_rect = pygame.Rect(tx, ty, tw, th)
            for pr in placed_rects:
                if t_rect.inflate(margin*2, margin*2).colliderect(pr):
                    return False
            # Check overlap with mask
            mx1, my1 = max(0, tx - margin), max(0, ty - margin)
            mx2, my2 = min(w, tx + tw + margin), min(h, ty + th + margin)
            for ry in range(my1, my2):
                for rx in range(mx1, mx2):
                    if occupied_mask[ry][rx] == 1:
                        return False
            return True

        while buildings_placed < target_count and attempts < 200 and self.target_templates:
            attempts += 1
            tmpl_name = random.choice(self.target_templates)
            tmpl = self.templates[tmpl_name]
            tw, th = tmpl['width'], tmpl['height']
            
            safe_pad = 4 # Border(2) + Lot(2)
            if w - safe_pad*2 < tw or h - safe_pad*2 < th: continue

            tx = random.randint(safe_pad, w - safe_pad - tw)
            ty = random.randint(safe_pad, h - safe_pad - th)
            
            if not is_area_free(tx, ty, tw, th, margin=2):
                continue
            
            # Draw Lot & Driveway
            lot_m = 2
            lx1, ly1 = max(0, tx - lot_m), max(0, ty - lot_m)
            lx2, ly2 = min(w, tx + tw + lot_m), min(h, ty + th + lot_m)
            
            # Lot
            for ry in range(ly1, ly2):
                for rx in range(lx1, lx2):
                    if layers['ground'][ry][rx] == 'bg_grass':
                         layers['ground'][ry][rx] = 'dirty_01'
                         occupied_mask[ry][rx] = 1
            
            # Driveway (L-shape to center)
            bx, by = tx + tw // 2, ty + th // 2
            def paint_driveway(px, py):
                if 0 <= px < w and 0 <= py < h and layers['base'][py][px] == ' ':
                    layers['ground'][py][px] = 'dirty_01'
                    occupied_mask[py][px] = 1

            x_s, x_e = min(cx, bx), max(cx, bx)
            for rx in range(x_s, x_e + 1): paint_driveway(rx, cy); paint_driveway(rx, cy+1)
            y_s, y_e = min(cy, by), max(cy, by)
            for ry in range(y_s, y_e + 1): paint_driveway(bx, ry); paint_driveway(bx+1, ry)

            # Place
            self._blit_template(layers, tmpl, tx, ty, w, h)
            placed_rects.append(pygame.Rect(tx, ty, tw, th))
            buildings_placed += 1
            
            # Mark mask
            for ry in range(ty, ty + th):
                for rx in range(tx, tx + tw):
                    occupied_mask[ry][rx] = 1

        # 4. Place Forest Templates (Randomly, don't count, no lot)
        # Try to place a few Forest structures if available
        if self.forest_templates:
            forest_attempts = 15 # Try 15 times
            for _ in range(forest_attempts):
                tmpl_name = random.choice(self.forest_templates)
                tmpl = self.templates[tmpl_name]
                tw, th = tmpl['width'], tmpl['height']
                
                pad = 3
                if w - pad*2 < tw or h - pad*2 < th: continue
                
                tx = random.randint(pad, w - pad - tw)
                ty = random.randint(pad, h - pad - th)
                
                # Check free space (no margin needed for nature usually, but good to avoid overlap)
                if is_area_free(tx, ty, tw, th, margin=0):
                    self._blit_template(layers, tmpl, tx, ty, w, h)
                    placed_rects.append(pygame.Rect(tx, ty, tw, th))
                    # Mark mask
                    for ry in range(ty, ty + th):
                        for rx in range(tx, tx + tw):
                            occupied_mask[ry][rx] = 1

        # 5. Organic Nature (Single Tile Clusters) - Filler
        num_groves = random.randint(5, 12)
        for _ in range(num_groves):
            gx = random.randint(border_w, w - border_w)
            gy = random.randint(border_w, h - border_w)
            g_radius = random.randint(3, 8)
            for y in range(gy - g_radius, gy + g_radius):
                for x in range(gx - g_radius, gx + g_radius):
                    if 0 <= x < w and 0 <= y < h:
                        if occupied_mask[y][x] == 0 and layers['base'][y][x] == ' ':
                            if math.hypot(x - gx, y - gy) <= g_radius:
                                if random.random() < 0.65:
                                    tile = random.choice(self.forest_tiles)
                                    layers['base'][y][x] = tile

        # 6. Spawns
        if is_start:
            layers['spawn'][cy][cx] = 'P'
        else:
            self._scatter_zombies(layers, occupied_mask, w, h)

        return layers

    def _blit_template(self, target, source, ox, oy, mw, mh):
        for layer in ['base', 'ground', 'spawn', 'roof']:
            if layer not in source: continue
            grid = source[layer]
            for r in range(len(grid)):
                for c in range(len(grid[r])):
                    tile = grid[r][c]
                    if tile and tile != ' ':
                        gx, gy = ox + c, oy + r
                        if 0 <= gx < mw and 0 <= gy < mh:
                            target[layer][gy][gx] = tile

    def _scatter_zombies(self, layers, mask, w, h):
        density = 0.01
        for y in range(5, h - 5):
            for x in range(5, w - 5):
                if mask[y][x] == 0 and layers['base'][y][x] == ' ':
                    if random.random() < density:
                        layers['spawn'][y][x] = 'Z'

    def _save_chunk(self, fname, layers):
        for name, data in layers.items():
            suffix = f"_{name}.csv" if name != 'base' else "_map.csv"
            with open(os.path.join(self.output_folder, fname + suffix), 'w', newline='') as f:
                csv.writer(f).writerows(data)

    def _render_chunk_to_surface(self, surface, gx, gy, data):
        if not hasattr(self.game, 'tile_manager'): return
        defs = self.game.tile_manager.definitions
        ox = gx * self.chunk_size * self.tile_size
        oy = gy * self.chunk_size * self.tile_size
        
        ground = data['ground']
        base = data['base']
        
        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                char = ground[y][x]
                if char in defs:
                    surface.blit(defs[char]['image'], (ox + x * self.tile_size, oy + y * self.tile_size))
                char = base[y][x]
                if char in defs and char != ' ':
                    surface.blit(defs[char]['image'], (ox + x * self.tile_size, oy + y * self.tile_size))