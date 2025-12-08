import os
import random
import csv
import pygame
import math
from core.data.config import *
from core.map.building_loader import load_building_templates

class ProceduralGenerator:
    def __init__(self, game, output_folder=None, 
                 building_counts=None, 
                 chunk_settings=None):
        self.game = game
        self.chunk_size = 100 # 100x100 tiles per chunk
        self.tile_size = TILE_SIZE
        self.output_folder = output_folder if output_folder else MAP_DIR
        self.buildings_path = os.path.join(MAP_DIR, 'buildings')
        self.templates = load_building_templates(self.buildings_path)
        
        # --- NEW: World Generation Settings (Settable at initialization) ---
        
        # Map/Chunk Settings - Control world structure
        self.default_chunk_settings = {
            'urban_chunk_ratio': 0.6,    # Ratio of chunks that will be "urban" (contain buildings, max 1.0)
            'min_urban_chunks': 1,       # Minimum number of urban chunks to guarantee
            'military_chunk_count': 1,   # Number of chunks dedicated to military templates (0 or 1)
            'force_start_urban': True    # If True, the starting chunk is always urban
        }
        self.chunk_settings = self.default_chunk_settings.copy()
        if chunk_settings:
            self.chunk_settings.update(chunk_settings)

        # Building Counts - Total number of specific buildings across the entire map
        self.default_building_counts = {
            'Stores': 5,
            'Warehouses': 3,
            'Condo': 3,
            'Building2': 3,
            'Generic': 5  # Max number of generic buildings placed per urban chunk
        }
        self.building_counts = self.default_building_counts.copy()
        if building_counts:
            self.building_counts.update(building_counts)
        
        # Forest settings - Control forest density
        self.forest_border_width = 2      # Width of the solid tree border (in tiles)
        self.cluster_min_count = 50       # Minimum number of forest clusters per chunk
        self.cluster_max_count = 250      # Maximum number of forest clusters per chunk
        self.cluster_radius = 4           # Radius of scatter for each cluster (in tiles)
        self.cluster_density = 0.85       # Probability (0.0 to 1.0) of a tile becoming forest

        self.num_building_per_chunk = self.building_counts.get('Generic', 10) 
        # ---------------------------------------------------------------------

        # 1. Identify Forest Tiles
        self.forest_tiles = []
        if hasattr(self.game, 'tile_manager'):
            self.forest_tiles = [k for k in self.game.tile_manager.definitions.keys() if k.startswith('Forest_')]
        
        if not self.forest_tiles:
            self.forest_tiles = ['garden_tree_1', 'garden_tree_8', 'garden_stone', 'bg_grass', 'garden_dirty_1', 'garden_dirty_2', 'garden_grass_3', 'garden_grass_1', 'garden_grass_2']

        # 2. Identify Templates
        self.building_categories = ["Building", "Stores", "Condo", "Warehouses", "Shed"]
        
        self.target_templates = []      # Generic buildings
        self.forest_templates = []      # Forest structures
        self.unique_templates = []      # Military/Unique
        self.store_templates = []       # Stores
        self.warehouse_templates = []   # Warehouses
        self.condo_templates = []
        self.building2_templates = []

        print("--- Template Discovery ---")
        for name in self.templates.keys():
            lower_name = name.lower()
            
            if lower_name.startswith("military_") or "military" in lower_name:
                self.unique_templates.append(name)
                print(f"Found Unique Template: {name}")
            elif name.startswith("Forest_"):
                self.forest_templates.append(name)
            elif name.startswith("Stores"):
                self.store_templates.append(name)
            elif name.startswith("Warehouse"):
                self.warehouse_templates.append(name)
            elif name.startswith("Condo"):
                self.condo_templates.append(name)
            elif name.startswith("Building2"):
                self.building2_templates.append(name)
            elif any(cat in name for cat in self.building_categories):
                self.target_templates.append(name)
        
        if not self.target_templates:
             self.target_templates = [k for k in self.templates.keys() if not k.startswith("Forest_")]

    def generate_world(self, seed_pattern="5-DEFAULT", regenerate=False):
        try:
            # Check for new pattern: Size-Seed (e.g., "5-B1TR0T")
            if '-' in seed_pattern:
                parts = seed_pattern.split('-', 1)
                n_part = parts[0]
                if not n_part: n_part = "5"
                grid_w = int(n_part)
                grid_h = int(n_part)
                actual_seed = parts[1]
                if not actual_seed: actual_seed = "DEFAULT"
            else:
                grid_w, grid_h = 5, 5
                actual_seed = seed_pattern
        except ValueError:
            print(f"Invalid seed pattern '{seed_pattern}'. Defaulting to 3x3.")
            grid_w, grid_h = 5, 5
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

        # Distribution Logic - USES self.building_counts for total counts
        limit_stores = self.building_counts.get('Stores', 0)
        limit_warehouses = self.building_counts.get('Warehouses', 0)
        limit_condo = self.building_counts.get('Condo', 0)
        limit_building2 = self.building_counts.get('Building2', 0)
        
        print(f"Distribution Targets -> Stores: {limit_stores}, Warehouses: {limit_warehouses}, Building2: {limit_building2}")

        # 1. Isolate Military Templates
        military_templates = self.unique_templates[:]
        required_military_chunks = self.chunk_settings.get('military_chunk_count', 0)
        
        # 2. Populate General Special Building Pool (excluding military)
        special_buildings_pool = []
        if self.store_templates:
            for _ in range(limit_stores): special_buildings_pool.append(random.choice(self.store_templates))
        if self.warehouse_templates:
            for _ in range(limit_warehouses): special_buildings_pool.append(random.choice(self.warehouse_templates))
        if self.condo_templates:
            for _ in range(limit_condo): special_buildings_pool.append(random.choice(self.condo_templates))
        if self.building2_templates:
            for _ in range(limit_building2): special_buildings_pool.append(random.choice(self.building2_templates))

        # 3. Calculate Urban Chunks (Uses self.chunk_settings)
        all_coords = [(x, y) for x in range(grid_w) for y in range(grid_h)]
        total_chunks = grid_w * grid_h
        
        base_urban_count = int(total_chunks * self.chunk_settings.get('urban_chunk_ratio', 0.6))
        required_special_chunks = math.ceil(len(special_buildings_pool) / 1) 
        
        num_building_chunks = max(base_urban_count, required_special_chunks, self.chunk_settings.get('min_urban_chunks', 0))
        num_building_chunks = min(num_building_chunks, total_chunks) 

        # 4. Assign Military/Urban Chunks
        urban_candidates = list(all_coords)
        military_chunk_coord = None
        
        # --- FIX: Initialize urban_coords before it's first referenced ---
        urban_coords = set() 
        
        if military_templates and required_military_chunks > 0:
            # Prioritize selecting a chunk that hasn't been designated urban yet
            forest_candidates = [coord for coord in urban_candidates if coord not in urban_coords]
            
            if forest_candidates:
                military_chunk_coord = random.choice(forest_candidates)
                urban_candidates.remove(military_chunk_coord)
            else:
                military_chunk_coord = random.choice(urban_candidates)
                urban_candidates.remove(military_chunk_coord)
            
            num_building_chunks = max(0, num_building_chunks - 1)
        
        # Select "Urban" chunks from the remaining candidates
        urban_coords = set(random.sample(urban_candidates, min(len(urban_candidates), num_building_chunks)))
        # --- END FIX ---
        
        # 5. Build Priority Map
        print(f"Selected Urban Chunks ({len(urban_coords)}): {urban_coords}")
        chunk_priority_map = {coord: [] for coord in all_coords}
        
        # Assign NON-MILITARY special buildings to urban chunks
        urban_list = list(urban_coords) 
        if urban_list:
            random.shuffle(urban_list)
            coord_idx = 0
            if special_buildings_pool:
                for tmpl in special_buildings_pool:
                    coord = urban_list[coord_idx]
                    chunk_priority_map[coord].append(tmpl)
                    print(f"Assigning PRIORITY {tmpl} to Chunk {coord}")
                    coord_idx = (coord_idx + 1) % len(urban_list)

        # Assign MILITARY buildings to the chosen forest chunk
        if military_chunk_coord:
            chunk_priority_map[military_chunk_coord].extend(military_templates)
            print(f"Assigning {len(military_templates)} Military Templates to Chunk {military_chunk_coord}")
            
        # --- END NEW DISTRIBUTION LOGIC ---

        start_gx = random.randint(0, grid_w - 1)
        start_gy = random.randint(0, grid_h - 1)
        print(f"Randomly selected Start Chunk: ({start_gx}, {start_gy})")

        # 2. Render each Chunk
        total_map_w = grid_w * self.chunk_size * self.tile_size
        total_map_h = grid_h * self.chunk_size * self.tile_size
        
        # Create 3 separate surfaces for visualization
        full_map_surface = pygame.Surface((total_map_w, total_map_h))
        heat_map_surface = pygame.Surface((total_map_w, total_map_h))
        
        start_map_filename = None

        for gy in range(grid_h):
            for gx in range(grid_w):
                pos_id = (gy * grid_w) + gx
                conns = connections_grid[gy][gx]
                
                priority_list = chunk_priority_map.get((gx, gy), [])

                is_center_chunk = (gx == start_gx and gy == start_gy)
                is_military_chunk = (gx, gy) == military_chunk_coord
                
                # Check if the chunk is designated urban OR if it's the start chunk (if forced) OR military
                is_urban = (gx, gy) in urban_coords or is_military_chunk
                if is_center_chunk and self.chunk_settings.get('force_start_urban', True):
                    is_urban = True

                # Pass flag to enforce forest generation and skip generic buildings
                chunk_data = self._generate_chunk_data(gx, gy, conns, 
                                                       is_start=is_center_chunk, 
                                                       priority_templates=priority_list, 
                                                       allow_buildings=is_urban,
                                                       force_forest=is_military_chunk) 
                
                conn_top = conns.get('top_id', 0)
                conn_right = conns.get('right_id', 0)
                conn_bottom = conns.get('bottom_id', 0)
                conn_left = conns.get('left_id', 0)
                
                filename_base = f"map_L1_P{pos_id}_{conn_top}_{conn_right}_{conn_bottom}_{conn_left}"
                
                self._save_chunk(filename_base, chunk_data)
                
                # Pass 2 surfaces to the render function
                self._render_chunk_to_surface(full_map_surface, heat_map_surface, gx, gy, chunk_data)

                if pos_id == 0:
                    start_map_filename = filename_base + "_map.csv"

        # Save 2 map images
        try:
            # 1. Full Map (Base + Roofs) -> JPG
            bg_path = os.path.join(self.output_folder, "full_map.jpg")
            pygame.image.save(full_map_surface, bg_path)
            
            # 2. Heat Map -> JPG
            heat_path = os.path.join(self.output_folder, "full_map_heat.jpg")
            pygame.image.save(heat_map_surface, heat_path)
            
            print(f"Saved Maps: {bg_path}, {heat_path}")
        except Exception as e:
            print(f"Error saving map images: {e}")

        return start_map_filename

    def _maps_exist(self, expected_count):
        if not os.path.exists(self.output_folder): return False
        return len([f for f in os.listdir(self.output_folder) if f.endswith('_map.csv')]) >= expected_count

    def _generate_maze_connections(self, w, h):
        grid = [[{
            'visited': False, 
            'top': False, 'right': False, 'bottom': False, 'left': False,
            'top_id': 0, 'right_id': 0, 'bottom_id': 0, 'left_id': 0,
            'top_type': 'asphalt', 'right_type': 'asphalt', 'bottom_type': 'asphalt', 'left_type': 'asphalt'
        } for _ in range(w)] for _ in range(h)]
        
        stack = [(0, 0)]
        grid[0][0]['visited'] = True
        next_connection_id = 1
        
        while stack:
            cx, cy = stack[-1]
            neighbors = []
            if cy > 0 and not grid[cy-1][cx]['visited']: neighbors.append(('top', cx, cy-1))
            if cx < w - 1 and not grid[cy][cx+1]['visited']: neighbors.append(('right', cx+1, cy))
            if cy < h - 1 and not grid[cy+1][cx]['visited']: neighbors.append(('bottom', cx, cy+1))
            if cx > 0 and not grid[cy][cx-1]['visited']: neighbors.append(('left', cx-1, cy))
                
            if neighbors:
                direction, nx, ny = random.choice(neighbors)
                cid = next_connection_id
                next_connection_id += 1
                
                r = random.random()
                if r < 0.5: conn_type = 'asphalt'
                elif r < 0.8: conn_type = 'sand' 
                else: conn_type = 'dirty'
                
                if direction == 'top':
                    grid[cy][cx]['top'] = True; grid[cy][cx]['top_id'] = cid; grid[cy][cx]['top_type'] = conn_type
                    grid[ny][nx]['bottom'] = True; grid[ny][nx]['bottom_id'] = cid; grid[ny][nx]['bottom_type'] = conn_type
                elif direction == 'right':
                    grid[cy][cx]['right'] = True; grid[cy][cx]['right_id'] = cid; grid[cy][cx]['right_type'] = conn_type
                    grid[ny][nx]['left'] = True; grid[ny][nx]['left_id'] = cid; grid[ny][nx]['left_type'] = conn_type
                elif direction == 'bottom':
                    grid[cy][cx]['bottom'] = True; grid[cy][cx]['bottom_id'] = cid; grid[cy][cx]['bottom_type'] = conn_type
                    grid[ny][nx]['top'] = True; grid[ny][nx]['top_id'] = cid; grid[ny][nx]['top_type'] = conn_type
                elif direction == 'left':
                    grid[cy][cx]['left'] = True; grid[cy][cx]['left_id'] = cid; grid[cy][cx]['left_type'] = conn_type
                    grid[ny][nx]['right'] = True; grid[ny][nx]['right_id'] = cid; grid[ny][nx]['right_type'] = conn_type
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
                cid = next_connection_id
                next_connection_id += 1
                
                r = random.random()
                if r < 0.3: conn_type = 'asphalt'
                elif r < 0.7: conn_type = 'sand'
                else: conn_type = 'dirty'

                if d == 'top': 
                    grid[ry][rx]['top'] = True; grid[ry][rx]['top_id'] = cid; grid[ry][rx]['top_type'] = conn_type
                    grid[ry-1][rx]['bottom'] = True; grid[ry-1][rx]['bottom_id'] = cid; grid[ry-1][rx]['bottom_type'] = conn_type
                elif d == 'right': 
                    grid[ry][rx]['right'] = True; grid[ry][rx]['right_id'] = cid; grid[ry][rx]['right_type'] = conn_type
                    grid[ry][rx+1]['left'] = True; grid[ry][rx+1]['left_id'] = cid; grid[ry][rx+1]['left_type'] = conn_type
                elif d == 'bottom': 
                    grid[ry][rx]['bottom'] = True; grid[ry][rx]['bottom_id'] = cid; grid[ry][rx]['bottom_type'] = conn_type
                    grid[ry+1][rx]['top'] = True; grid[ry+1][rx]['top_id'] = cid; grid[ry+1][rx]['top_type'] = conn_type
                elif d == 'left': 
                    grid[ry][rx]['left'] = True; grid[ry][rx]['left_id'] = cid; grid[ry][rx]['left_type'] = conn_type
                    grid[ry][rx-1]['right'] = True; grid[ry][rx-1]['right_id'] = cid; grid[ry][rx-1]['right_type'] = conn_type
        return grid

    def _generate_chunk_data(self, gx, gy, conns, is_start=False, priority_templates=None, allow_buildings=True, force_forest=False):
        w, h = self.chunk_size, self.chunk_size
        cx, cy = w // 2, h // 2
        
        layers = {
            'base': [[' ' for _ in range(w)] for _ in range(h)],
            'ground': [['bg_grass' for _ in range(w)] for _ in range(h)],
            'spawn': [[' ' for _ in range(w)] for _ in range(h)],
            'roof': [[' ' for _ in range(w)] for _ in range(h)],
            'light': [[' ' for _ in range(w)] for _ in range(h)]
        }
        occupied_mask = [[0 for _ in range(w)] for _ in range(h)]

        road_tile = 'asphalt_01'
        dirt_tile = 'dirty_01'
        sand_tile = 'sand_01'
        
        def draw_straight_road(x1, y1, x2, y2, tile_type):
            sx, ex = min(x1, x2), max(x1, x2)
            sy, ey = min(y1, y2), max(y1, y2)
            r = 2 if tile_type == road_tile else 1
            for y in range(sy - r, ey + r + 1):
                for x in range(sx - r, ex + r + 1):
                    if 0 <= x < w and 0 <= y < h:
                        layers['ground'][y][x] = tile_type
                        occupied_mask[y][x] = 1

        def draw_secondary_maze_road(start_x, start_y, target_x, target_y, tile_type=dirt_tile):
            current_x, current_y = start_x, start_y
            path = [(current_x, current_y)]
            steps = 0
            max_steps = 400 
            
            while steps < max_steps:
                steps += 1
                if not (0 <= current_x < w and 0 <= current_y < h): break
                if layers['ground'][current_y][current_x] == road_tile: break 
                if math.hypot(target_x - current_x, target_y - current_y) < 2: break

                moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                valid_moves = []
                for dx, dy in moves:
                    nx, ny = current_x + dx, current_y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        if layers['base'][ny][nx] == ' ': valid_moves.append((dx, dy))
                
                if not valid_moves: break 
                
                scored_moves = []
                for dx, dy in valid_moves:
                    nx, ny = current_x + dx, current_y + dy
                    dist = math.hypot(target_x - nx, target_y - ny)
                    noise = random.uniform(-10.0, 10.0) 
                    score = dist + noise
                    scored_moves.append((score, dx, dy))
                
                scored_moves.sort(key=lambda x: x[0])
                _, best_dx, best_dy = scored_moves[0]
                current_x += best_dx; current_y += best_dy
                path.append((current_x, current_y))

            for px, py in path:
                for oy in range(2):
                    for ox in range(2):
                        gx, gy = px + ox, py + oy
                        if 0 <= gx < w and 0 <= gy < h:
                            if layers['base'][gy][gx] == ' ' and layers['ground'][gy][gx] != road_tile:
                                layers['ground'][gy][gx] = tile_type
                                occupied_mask[gy][gx] = 1

        # 1. Central Hub
        draw_straight_road(cx, cy, cx, cy, road_tile)

        # 2. Connections
        if conns['top']:
            if conns['top_type'] == 'asphalt': draw_straight_road(cx, 0, cx, cy, road_tile)
            elif conns['top_type'] == 'sand': draw_secondary_maze_road(cx, 0, cx, cy, sand_tile)
            else: draw_secondary_maze_road(cx, 0, cx, cy, dirt_tile)
            
        if conns['bottom']:
            if conns['bottom_type'] == 'asphalt': draw_straight_road(cx, cy, cx, h-1, road_tile)
            elif conns['bottom_type'] == 'sand': draw_secondary_maze_road(cx, h-1, cx, cy, sand_tile)
            else: draw_secondary_maze_road(cx, h-1, cx, cy, dirt_tile)
            
        if conns['left']:
            if conns['left_type'] == 'asphalt': draw_straight_road(0, cy, cx, cy, road_tile)
            elif conns['left_type'] == 'sand': draw_secondary_maze_road(0, cy, cx, cy, sand_tile)
            else: draw_secondary_maze_road(0, cy, cx, cy, dirt_tile)
            
        if conns['right']:
            if conns['right_type'] == 'asphalt': draw_straight_road(cx, cy, w-1, cy, road_tile)
            elif conns['right_type'] == 'sand': draw_secondary_maze_road(w-1, cy, cx, cy, sand_tile)
            else: draw_secondary_maze_road(w-1, cy, cx, cy, dirt_tile)

        # 3. Border
        border_w = self.forest_border_width
        for y in range(h):
            for x in range(w):
                if x < border_w or x >= w - border_w or y < border_w or y >= h - border_w:
                    if occupied_mask[y][x] == 0:
                        tile = random.choice(self.forest_tiles) if self.forest_tiles else 'wall_stone'
                        layers['base'][y][x] = tile
                        occupied_mask[y][x] = 1

        # 4. Place Buildings (Only if allowed)
        placed_rects = [] 
        buildings_placed = 0
        
        # Target count for GENERIC buildings. 
        # Set to 0 if we are forcing forest (military chunk) to prevent generic buildings from spawning.
        target_count = 0
        if allow_buildings and not force_forest:
            target_count = self.num_building_per_chunk # Uses 'Generic' count from init
        
        attempts = 0
        
        def is_area_free(tx, ty, tw, th, margin=0):
            t_rect = pygame.Rect(tx, ty, tw, th)
            for pr in placed_rects:
                if t_rect.inflate(margin*2, margin*2).colliderect(pr): return False
            mx1, my1 = max(0, tx - margin), max(0, ty - margin)
            mx2, my2 = min(w, tx + tw + margin), min(h, ty + th + margin)
            for ry in range(my1, my2):
                for rx in range(mx1, mx2):
                    if 0 <= ry < h and 0 <= rx < w:
                        if occupied_mask[ry][rx] == 1: return False
            return True

        if allow_buildings:
            # Priority Buildings Loop (Includes Military/Store/Condo)
            if priority_templates:
                for tmpl_name in priority_templates:
                    if tmpl_name in self.templates:
                        tmpl = self.templates[tmpl_name]
                        tw, th = tmpl['width'], tmpl['height']
                        
                        is_building2 = "building2" in tmpl_name.lower()
                        
                        for _ in range(500):
                            if is_building2:
                                axis = random.choice(['vert', 'horz'])
                                road_radius = 2 
                                
                                if axis == 'vert':
                                    side = random.choice([-1, 1])
                                    if side == -1: tx = cx - road_radius - 1 - tw
                                    else: tx = cx + road_radius + 1 + 1
                                    ty = random.randint(border_w + 2, h - border_w - th - 2)
                                else:
                                    side = random.choice([-1, 1])
                                    if side == -1: ty = cy - road_radius - 1 - th
                                    else: ty = cy + road_radius + 1 + 1
                                    tx = random.randint(border_w + 2, w - border_w - tw - 2)
                                    
                                if tx < 0 or tx + tw >= w or ty < 0 or ty + th >= h: continue
                            else:
                                safe_pad = 2
                                if w - safe_pad*2 < tw or h - safe_pad*2 < th: break 
                                tx = random.randint(safe_pad, w - safe_pad - tw)
                                ty = random.randint(safe_pad, h - safe_pad - th)
                            
                            if is_area_free(tx, ty, tw, th, margin=1):
                                # Lot -> Sand (lot_m is 2 here)
                                lot_m = 2
                                for ry in range(ty-lot_m, ty+th+lot_m):
                                    for rx in range(tx-lot_m, tx+tw+lot_m):
                                        if 0<=rx<w and 0<=ry<h and layers['ground'][ry][rx] == 'bg_grass':
                                            layers['ground'][ry][rx] = sand_tile
                                            occupied_mask[ry][rx] = 1
                                
                                # Connect to Hub -> Sand
                                bx, by = tx + tw // 2, ty + th // 2
                                if (tw > 30 or th > 30) and not is_building2:
                                    draw_secondary_maze_road(bx, by, cx, cy, sand_tile)
                                else:
                                    x_s, x_e = min(cx, bx), max(cx, bx)
                                    for rx in range(x_s, x_e + 1): 
                                        for off in range(2): 
                                            yy = cy + off
                                            if 0<=rx<w and 0<=yy<h and layers['ground'][yy][rx]!=road_tile: 
                                                layers['ground'][yy][rx]=sand_tile; occupied_mask[yy][rx]=1
                                    
                                    y_s, y_e = min(cy, by), max(cy, by)
                                    for ry in range(y_s, y_e + 1):
                                        for off in range(2): 
                                            xx = bx + off
                                            if 0<=ry<h and 0<=xx<w and layers['ground'][ry][xx]!=road_tile: 
                                                layers['ground'][ry][xx]=sand_tile; occupied_mask[ry][xx]=1
                                
                                self._blit_template(layers, tmpl, tx, ty, w, h)
                                placed_rects.append(pygame.Rect(tx, ty, tw, th))
                                buildings_placed += 1
                                for ry in range(ty, ty + th):
                                    for rx in range(tx, tx + tw): occupied_mask[ry][rx] = 1
                                print(f"Placed Priority Building: {tmpl_name} at ({tx},{ty})")
                                break

            # Standard Generic Buildings: Only place if NOT a dedicated forest/military chunk
            if not force_forest:
                while buildings_placed < target_count and attempts < 3000 and self.target_templates:
                    attempts += 1
                    tmpl_name = random.choice(self.target_templates)
                    tmpl = self.templates[tmpl_name]
                    tw, th = tmpl['width'], tmpl['height']
                    
                    safe_pad = 2 
                    if w - safe_pad*2 < tw or h - safe_pad*2 < th: continue
                    tx = random.randint(safe_pad, w - safe_pad - tw)
                    ty = random.randint(safe_pad, h - safe_pad - th)
                    
                    if not is_area_free(tx, ty, tw, th, margin=1): continue
                    
                    # Lot -> Sand
                    for ry in range(ty-1, ty+th+1):
                        for rx in range(tx-1, tx+tw+1):
                            if 0<=rx<w and 0<=ry<h and layers['ground'][ry][rx] == 'bg_grass':
                                layers['ground'][ry][rx] = sand_tile
                                occupied_mask[ry][rx] = 1
                    
                    # Driveway -> Sand
                    bx, by = tx + tw // 2, ty + th // 2
                    if tw > 30 or th > 30:
                        draw_secondary_maze_road(bx, by, cx, cy, sand_tile)
                    else:
                        x_s, x_e = min(cx, bx), max(cx, bx)
                        for rx in range(x_s, x_e + 1): 
                            for off in range(2): 
                                yy = cy + off
                                if 0<=rx<w and 0<=yy<h and layers['ground'][yy][rx]!=road_tile: 
                                    layers['ground'][yy][rx]=sand_tile; occupied_mask[yy][rx]=1
                        
                        y_s, y_e = min(cy, by), max(cy, by)
                        for ry in range(y_s, y_e + 1):
                            for off in range(2): 
                                xx = bx + off
                                if 0<=ry<h and 0<=xx<w and layers['ground'][ry][xx]!=road_tile: 
                                    layers['ground'][ry][xx]=sand_tile; occupied_mask[ry][xx]=1

                    self._blit_template(layers, tmpl, tx, ty, w, h)
                    placed_rects.append(pygame.Rect(tx, ty, tw, th))
                    buildings_placed += 1
                    for ry in range(ty, ty + th):
                        for rx in range(tx, tx + tw): occupied_mask[ry][rx] = 1

        # Forest / Nature (Template Placement)
        if self.forest_templates and not force_forest:
            for _ in range(15):
                tmpl_name = random.choice(self.forest_templates)
                tmpl = self.templates[tmpl_name]
                tw, th = tmpl['width'], tmpl['height']
                tx = random.randint(1, w - tw - 1)
                ty = random.randint(1, h - th - 1)
                if is_area_free(tx, ty, tw, th, margin=0):
                    self._blit_template(layers, tmpl, tx, ty, w, h)
                    placed_rects.append(pygame.Rect(tx, ty, tw, th))
                    for ry in range(ty, ty + th):
                        for rx in range(tx, tx + tw): occupied_mask[ry][rx] = 1

        # Tile Clusters (Forest Generation)
        
        # If forcing forest, use high density variables
        if force_forest:
            # Overwrite non-road ground tiles to guarantee forest density
            for y in range(h):
                for x in range(w):
                    ground_tile = layers['ground'][y][x]
                    # Only change tiles that are not main roads or immediate building lots
                    if ground_tile != road_tile and ground_tile != sand_tile and ground_tile != dirt_tile:
                         layers['ground'][y][x] = 'bg_grass'
                         
            # Set extremely high density variables for filling the chunk
            cluster_count_range = random.randint(500, 1500)
            current_radius = 10
            current_density = 0.95
        else:
            # Use configurable normal cluster settings
            cluster_count_range = random.randint(self.cluster_min_count, self.cluster_max_count)
            current_radius = self.cluster_radius
            current_density = self.cluster_density

        # Apply cluster logic
        for _ in range(cluster_count_range):
            gx = random.randint(border_w, w - border_w)
            gy = random.randint(border_w, h - border_w)
            
            search_r = current_radius + 1 
            
            for y in range(gy - search_r, gy + search_r):
                for x in range(gx - search_r, gx + search_r):
                    if 0 <= x < w and 0 <= y < h:
                        if occupied_mask[y][x] == 0 and layers['base'][y][x] == ' ':
                            if math.hypot(x - gx, y - gy) <= current_radius: 
                                if random.random() < current_density: 
                                    layers['base'][y][x] = random.choice(self.forest_tiles)

        # Spawns
        if is_start: 
            layers['spawn'][cy][cx] = 'P'
        else: 
            self._scatter_zombies(layers, occupied_mask, w, h)
        
        # Place random NPC spawn points in all chunks
        self._scatter_npcs(layers, occupied_mask, w, h)

        return layers

    def _scatter_zombies(self, layers, mask, w, h):
        # 1. Identify Zones
        building_tiles = []
        street_tiles = []
        woods_tiles = []
        
        for y in range(h):
            for x in range(w):
                # Safety margin from edges
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                
                # Must be walkable (no wall, no existing spawn)
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ':
                    continue
                
                ground = layers['ground'][y][x]
                
                if ground == 'sand_01' or ground == 'dirty_01':
                    building_tiles.append((x, y))
                elif ground == 'asphalt_01':
                    street_tiles.append((x, y))
                elif ground == 'bg_grass':
                    woods_tiles.append((x, y))

        # 2. Determine Counts
        total_zombies = random.randint(40, 60) # Adjustable difficulty
        
        count_building = int(total_zombies * 0.45)
        count_street = int(total_zombies * 0.25)
        count_woods = total_zombies - count_building - count_street
        
        # 3. Spawn (Helper function to place)
        def place_zombies(target_count, available_tiles):
            if not available_tiles: return
            # Shuffle or sample
            chosen = random.sample(available_tiles, min(target_count, len(available_tiles)))
            for (zx, zy) in chosen:
                layers['spawn'][zy][zx] = 'Z'

        place_zombies(count_building, building_tiles)
        place_zombies(count_street, street_tiles)
        place_zombies(count_woods, woods_tiles)

    def _scatter_npcs(self, layers, mask, w, h):
        """
        Places NPC spawn markers ('NPC') on valid tiles.
        Ensures strict separation from Zombie spawn points.
        """
        
        # --- QUANTITY CONFIGURATION (Per Chunk) ---
        min_npcs_per_chunk = 1
        max_npcs_per_chunk = 2
        # ------------------------------------------

        # 1. Identify where Zombies are (so we can avoid them)
        zombie_locs = []
        for y in range(h):
            for x in range(w):
                if layers['spawn'][y][x] == 'Z':
                    zombie_locs.append((x, y))
        
        # 2. Find valid potential tiles
        potential_tiles = []
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                
                # Must be walkable and empty
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                
                # Use ground info to prefer civil areas
                ground = layers['ground'][y][x]
                if ground in ['asphalt_01', 'sand_01', 'dirty_01']:
                    potential_tiles.append((x, y))
        
        if not potential_tiles: return

        # 3. Filter candidates based on safety distance
        safe_candidates = []
        # Distance is squared to avoid sqrt (15 tiles = 225)
        SAFE_DISTANCE_SQ = 15 * 15 
        
        for px, py in potential_tiles:
            too_close = False
            for zx, zy in zombie_locs:
                dist_sq = (px - zx)**2 + (py - zy)**2
                if dist_sq < SAFE_DISTANCE_SQ:
                    too_close = True
                    break
            
            if not too_close:
                safe_candidates.append((px, py))

        # 4. Place Markers
        count = random.randint(min_npcs_per_chunk, max_npcs_per_chunk)
        if safe_candidates:
            # Pick from safe tiles if any exist
            chosen = random.sample(safe_candidates, min(count, len(safe_candidates)))
            for nx, ny in chosen:
                layers['spawn'][ny][nx] = 'NPC'
        else:
            # Optional: Fallback (commented out) - or simply don't spawn if unsafe
            # print("Warning: No safe NPC spawn spots found in chunk.")
            pass

    def _blit_template(self, target, source, ox, oy, mw, mh):
        for layer in ['base', 'light', 'ground', 'spawn', 'roof']:
            if layer not in source: continue
            grid = source[layer]
            for r in range(len(grid)):
                for c in range(len(grid[r])):
                    tile = grid[r][c]
                    if tile and tile != ' ':
                        gx, gy = ox + c, oy + r
                        if 0 <= gx < mw and 0 <= gy < mh:
                            target[layer][gy][gx] = tile

    def _save_chunk(self, fname, layers):
        for name, data in layers.items():
            suffix = f"_{name}.csv" if name != 'base' else "_map.csv"
            with open(os.path.join(self.output_folder, fname + suffix), 'w', newline='') as f:
                csv.writer(f).writerows(data)

    def _render_chunk_to_surface(self, bg_surf, heat_surf, gx, gy, data):
        if not hasattr(self.game, 'tile_manager'): return
        defs = self.game.tile_manager.definitions
        
        ox = gx * self.chunk_size * self.tile_size
        oy = gy * self.chunk_size * self.tile_size
        
        ground = data['ground']
        base = data['base']
        roof = data['roof']
        light = data['light']
        spawn = data['spawn']
        
        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                px = ox + x * self.tile_size
                py = oy + y * self.tile_size
                
                # 1. Background
                g_char = ground[y][x]
                if g_char in defs: 
                    bg_surf.blit(defs[g_char]['image'], (px, py))
                
                b_char = base[y][x]
                if b_char in defs and b_char != ' ': 
                    bg_surf.blit(defs[b_char]['image'], (px, py))
                
                # 2. Roof (Now drawn directly on the full map surface)
                r_char = roof[y][x]
                if r_char in defs and r_char != ' ':
                    bg_surf.blit(defs[r_char]['image'], (px, py))
                
                l_char = light[y][x]
                if l_char in defs and l_char != ' ':
                    bg_surf.blit(defs[l_char]['image'], (px, py))
                
                # 3. Heatmap
                s_char = spawn[y][x]
                if s_char in ['Z', 'P', 'I', 'NPC']:
                    color = (0, 0, 0)
                    if s_char == 'Z': color = (255, 0, 0)
                    elif s_char == 'P': color = (0, 255, 0)
                    elif s_char == 'I': color = (0, 0, 255)
                    elif s_char == 'NPC': color = (255, 255, 0) # Yellow for NPC
                    
                    pygame.draw.rect(heat_surf, color, (px, py, self.tile_size, self.tile_size))