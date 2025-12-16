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
        # --- SIZE SETTINGS ---
        self.chunk_size = CHUNK_SIZE # Reset to 100x100
        # ---------------------
        self.tile_size = TILE_SIZE
        self.output_folder = output_folder if output_folder else MAP_DIR
        self.buildings_path = os.path.join(MAP_DIR, 'buildings')
        self.templates = load_building_templates(self.buildings_path)
        
        # Map/Chunk Settings
        self.default_chunk_settings = {
            'urban_chunk_ratio': 0.8, # Increased to spread buildings out more
            'min_urban_chunks': 1,
            'military_chunk_count': 1,
            'force_start_urban': True
        }
        self.chunk_settings = self.default_chunk_settings.copy()
        if chunk_settings:
            self.chunk_settings.update(chunk_settings)

        # --- GLOBAL BUILDING LIMITS (MAX ON FULL MAP) ---
        # This defines exactly how many of each type will spawn in the entire world.
        self.global_building_limits = {
            'Warehouse': 3,
            'Stores': 5,
            'Shed': 25,
            'Building': 50,
            'Petrol': 10,
            'Heli': 1
        }
        # ------------------------------------------------

        # Forest settings
        self.forest_border_width = 2
        self.cluster_min_count = 20
        self.cluster_max_count = 100
        self.cluster_radius = 4
        self.cluster_density = 0.85

        # --- Island/Coast Settings ---
        self.water_tile = 'water_01'
        self.sand_tile = 'beach_sand_01'
        self.coast_width = 25 # Adjusted for 100x100 map
        # -----------------------------

        # 1. Identify Forest Tiles
        self.forest_tiles = []
        if hasattr(self.game, 'tile_manager'):
            self.forest_tiles = [k for k in self.game.tile_manager.definitions.keys() if k.startswith('Forest_')]
        
        if not self.forest_tiles:
            self.forest_tiles = ['garden_tree_1', 'garden_tree_8', 'garden_stone', 'bg_grass', 'garden_dirty_1', 'garden_dirty_2', 'garden_grass_3', 'garden_grass_1', 'garden_grass_2']

        # 2. Identify & Categorize Templates
        self.categorized_templates = {
            'Warehouse': [],
            'Stores': [],
            'Shed': [],
            'Building': [],
            'Petrol': [],
            'Heli': []
        }
        self.forest_templates = []

        print("--- Template Discovery & Categorization ---")
        for name in self.templates.keys():
            lower_name = name.lower()
            
            if name.startswith("Forest_"):
                self.forest_templates.append(name)
                continue

            # Categorize based on name prefixes or keywords
            assigned = False
            
            if "heli" in lower_name:
                self.categorized_templates['Heli'].append(name)
                assigned = True
            elif "warehouse" in lower_name:
                self.categorized_templates['Warehouse'].append(name)
                assigned = True
            elif "store" in lower_name:
                self.categorized_templates['Stores'].append(name)
                assigned = True
            elif "shed" in lower_name:
                self.categorized_templates['Shed'].append(name)
                assigned = True
            elif "petrol" in lower_name or "gas" in lower_name:
                self.categorized_templates['Petrol'].append(name)
                assigned = True
            
            # If not assigned to a special category, it's a generic "Building"
            if not assigned:
                self.categorized_templates['Building'].append(name)

        # Debug prints
        for cat, lst in self.categorized_templates.items():
            print(f"Category {cat}: Found {len(lst)} templates.")

    def generate_world(self, seed_pattern="5-DEFAULT", regenerate=False):
        try:
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

        self.grid_w = grid_w
        self.grid_h = grid_h

        print(f"Applying World Seed: {actual_seed} | Size: {grid_w}x{grid_h}")
        random.seed(actual_seed)

        expected_chunks = grid_w * grid_h
        
        if not regenerate and self._maps_exist(expected_chunks):
            print("World already exists. Skipping.")
            for f in os.listdir(self.output_folder):
                if f.startswith("map_L1_P0_") and f.endswith("_map.csv"):
                    return f
            return None

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # 1. Generate the Connection Matrix
        connections_grid = self._generate_maze_connections(grid_w, grid_h)

        # 2. Build the Global Building Deck (The Master List)
        global_deck = []
        
        for category, limit in self.global_building_limits.items():
            available = self.categorized_templates.get(category, [])
            if not available:
                print(f"Warning: No templates found for category '{category}'")
                continue
            
            # Select 'limit' number of buildings. 
            # Try to use unique ones first, then repeat if we run out.
            selected_for_category = []
            pool = list(available)
            random.shuffle(pool)
            
            for _ in range(limit):
                if not pool:
                    pool = list(available) # Refill pool if we need more
                    random.shuffle(pool)
                if pool:
                    tmpl = pool.pop()
                    selected_for_category.append(tmpl)
            
            # Special handling: Heli usually goes to one specific chunk, but here we put it in the deck
            if category == 'Heli':
                self.heli_template = selected_for_category[0] if selected_for_category else None
            else:
                global_deck.extend(selected_for_category)

        # Shuffle the deck to mix Warehouses, Sheds, and Buildings
        random.shuffle(global_deck)
        print(f"Global Building Deck Constructed: {len(global_deck)} buildings to place.")

        # 3. Calculate Urban Chunks (Where buildings can go)
        all_coords = [(x, y) for x in range(grid_w) for y in range(grid_h)]
        total_chunks = grid_w * grid_h
        
        # Ensure we have enough urban chunks to fit the deck, or use ratio
        deck_size_estimate_chunks = math.ceil(len(global_deck) / 2) # approx 2 per chunk
        base_urban_count = int(total_chunks * self.chunk_settings.get('urban_chunk_ratio', 0.8))
        num_building_chunks = max(base_urban_count, deck_size_estimate_chunks, self.chunk_settings.get('min_urban_chunks', 1))
        num_building_chunks = min(num_building_chunks, total_chunks) 

        # 4. Assign Military/Urban Chunks
        urban_candidates = list(all_coords)
        military_chunk_coord = None
        
        # Select Military Chunk
        if self.heli_template and self.chunk_settings.get('military_chunk_count', 0) > 0:
            military_chunk_coord = random.choice(urban_candidates)
            urban_candidates.remove(military_chunk_coord)
            num_building_chunks = max(0, num_building_chunks - 1)
        
        urban_coords = set(random.sample(urban_candidates, min(len(urban_candidates), num_building_chunks)))
        
        # 5. Distribute the Deck to Chunks
        chunk_priority_map = {coord: [] for coord in all_coords}
        urban_list = list(urban_coords)
        
        if urban_list:
            random.shuffle(urban_list)
            
            # Round-Robin Distribution
            if global_deck:
                chunk_idx = 0
                for tmpl in global_deck:
                    target_chunk = urban_list[chunk_idx]
                    chunk_priority_map[target_chunk].append(tmpl)
                    chunk_idx = (chunk_idx + 1) % len(urban_list)

        # Assign Heli to Military Chunk
        if military_chunk_coord and self.heli_template:
            chunk_priority_map[military_chunk_coord].append(self.heli_template)

        start_gx = random.randint(0, grid_w - 1)
        start_gy = random.randint(0, grid_h - 1)
        print(f"Start Chunk: ({start_gx}, {start_gy})")

        total_map_w = grid_w * self.chunk_size * self.tile_size
        total_map_h = grid_h * self.chunk_size * self.tile_size
        full_map_surface = pygame.Surface((total_map_w, total_map_h))
        heat_map_surface = pygame.Surface((total_map_w, total_map_h))
        
        start_map_filename = None

        for gy in range(grid_h):
            for gx in range(grid_w):
                pos_id = (gy * grid_w) + gx
                conns = connections_grid[gy][gx]
                
                # These are the ONLY buildings allowed for this chunk
                assigned_buildings = chunk_priority_map.get((gx, gy), [])

                is_center_chunk = (gx == start_gx and gy == start_gy)
                is_military_chunk = (gx, gy) == military_chunk_coord
                
                # A chunk is urban if it has assigned buildings OR is in the urban set
                is_urban = (gx, gy) in urban_coords or is_military_chunk or len(assigned_buildings) > 0
                
                if is_center_chunk and self.chunk_settings.get('force_start_urban', True):
                    is_urban = True

                chunk_data = self._generate_chunk_data(gx, gy, conns, 
                                                       is_start=is_center_chunk, 
                                                       assigned_templates=assigned_buildings, 
                                                       allow_buildings=is_urban,
                                                       force_forest=is_military_chunk) 
                
                conn_top = conns.get('top_id', 0)
                conn_right = conns.get('right_id', 0)
                conn_bottom = conns.get('bottom_id', 0)
                conn_left = conns.get('left_id', 0)
                
                filename_base = f"map_L1_P{pos_id}_{conn_top}_{conn_right}_{conn_bottom}_{conn_left}"
                self._save_chunk(filename_base, chunk_data)
                self._render_chunk_to_surface(full_map_surface, heat_map_surface, gx, gy, chunk_data)

                if pos_id == 0:
                    start_map_filename = filename_base + "_map.csv"

        try:
            pygame.image.save(full_map_surface, os.path.join(self.output_folder, "full_map.jpg"))
            pygame.image.save(heat_map_surface, os.path.join(self.output_folder, "full_map_heat.jpg"))
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
                conn_type = 'asphalt' if r < 0.5 else ('sand' if r < 0.8 else 'dirty')
                
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
            rx, ry = random.randint(0, w-1), random.randint(0, h-1)
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
                conn_type = 'asphalt' if r < 0.3 else ('sand' if r < 0.7 else 'dirty')

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

    def _generate_chunk_data(self, gx, gy, conns, is_start=False, assigned_templates=None, allow_buildings=True, force_forest=False):
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
            max_steps = self.chunk_size * 6
            
            while steps < max_steps:
                steps += 1
                if not (0 <= current_x < w and 0 <= current_y < h): break
                # Stop if we hit main road OR Water
                if layers['ground'][current_y][current_x] == road_tile: break 
                if layers['ground'][current_y][current_x] == self.water_tile: break 

                if math.hypot(target_x - current_x, target_y - current_y) < 2: break

                moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                valid_moves = []
                for dx, dy in moves:
                    nx, ny = current_x + dx, current_y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        # Avoid obstacles AND Water
                        if layers['base'][ny][nx] == ' ' and layers['ground'][ny][nx] != self.water_tile:
                            valid_moves.append((dx, dy))
                
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
                        gx_pos, gy_pos = px + ox, py + oy
                        if 0 <= gx_pos < w and 0 <= gy_pos < h:
                            if layers['base'][gy_pos][gx_pos] == ' ' and layers['ground'][gy_pos][gx_pos] != road_tile:
                                if layers['ground'][gy_pos][gx_pos] != self.water_tile:
                                    layers['ground'][gy_pos][gx_pos] = tile_type
                                    occupied_mask[gy_pos][gx_pos] = 1

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

        # 3. Border (Forest)
        border_w = self.forest_border_width
        for y in range(h):
            for x in range(w):
                if x < border_w or x >= w - border_w or y < border_w or y >= h - border_w:
                    if occupied_mask[y][x] == 0:
                        tile = random.choice(self.forest_tiles) if self.forest_tiles else 'wall_stone'
                        layers['base'][y][x] = tile
                        occupied_mask[y][x] = 1

        # 4. Organic "Drunkward" Coastline
        if hasattr(self, 'grid_w') and hasattr(self, 'grid_h'):
            cw = self.coast_width
            
            def get_coast_noise(idx, scale=0.1, amp=4.0):
                val = math.sin(idx * scale) * amp 
                val += math.sin(idx * scale * 2.1) * (amp * 0.5)
                val += random.uniform(-2.0, 2.0)
                return int(val)

            # Left Edge
            if gx == 0:
                for y in range(h):
                    global_y = gy * h + y
                    offset = get_coast_noise(global_y)
                    water_lim = (cw - 8) + offset # Reduced variance for smaller chunk
                    sand_lim = cw + offset
                    for x in range(cw + 8):
                        if x >= w: break
                        if x < water_lim:
                            layers['ground'][y][x] = self.water_tile
                            layers['base'][y][x] = ' '
                            occupied_mask[y][x] = 1 
                        elif x < sand_lim:
                            if layers['ground'][y][x] != self.water_tile:
                                layers['ground'][y][x] = self.sand_tile
                                layers['base'][y][x] = ' '
                                occupied_mask[y][x] = 1

            # Right Edge
            if gx == self.grid_w - 1:
                for y in range(h):
                    global_y = gy * h + y
                    offset = get_coast_noise(global_y)
                    water_lim = (cw - 8) + offset
                    sand_lim = cw + offset
                    min_x = w - (cw + 8)
                    for x in range(min_x, w):
                        if x < 0: continue
                        dist = w - 1 - x
                        if dist < water_lim:
                            layers['ground'][y][x] = self.water_tile
                            layers['base'][y][x] = ' '
                            occupied_mask[y][x] = 1
                        elif dist < sand_lim:
                            if layers['ground'][y][x] != self.water_tile:
                                layers['ground'][y][x] = self.sand_tile
                                layers['base'][y][x] = ' '
                                occupied_mask[y][x] = 1

            # Top Edge
            if gy == 0:
                for x in range(w):
                    global_x = gx * w + x
                    offset = get_coast_noise(global_x)
                    water_lim = (cw - 8) + offset
                    sand_lim = cw + offset
                    for y in range(cw + 8):
                        if y >= h: break
                        if y < water_lim:
                            layers['ground'][y][x] = self.water_tile
                            layers['base'][y][x] = ' '
                            occupied_mask[y][x] = 1
                        elif y < sand_lim:
                            if layers['ground'][y][x] != self.water_tile:
                                layers['ground'][y][x] = self.sand_tile
                                layers['base'][y][x] = ' '
                                occupied_mask[y][x] = 1

            # Bottom Edge
            if gy == self.grid_h - 1:
                for x in range(w):
                    global_x = gx * w + x
                    offset = get_coast_noise(global_x)
                    water_lim = (cw - 8) + offset
                    sand_lim = cw + offset
                    min_y = h - (cw + 8)
                    for y in range(min_y, h):
                        if y < 0: continue
                        dist = h - 1 - y
                        if dist < water_lim:
                            layers['ground'][y][x] = self.water_tile
                            layers['base'][y][x] = ' '
                            occupied_mask[y][x] = 1
                        elif dist < sand_lim:
                            if layers['ground'][y][x] != self.water_tile:
                                layers['ground'][y][x] = self.sand_tile
                                layers['base'][y][x] = ' '
                                occupied_mask[y][x] = 1

        # 5. Generate "Organic" Trade Routes
        if allow_buildings and not force_forest:
            num_routes = 6 # Reduced for smaller chunk
            safe_margin = self.coast_width + 3 
            
            for _ in range(num_routes):
                rx1 = random.randint(safe_margin, w - safe_margin)
                ry1 = random.randint(safe_margin, h - safe_margin)
                rx2 = random.randint(safe_margin, w - safe_margin)
                ry2 = random.randint(safe_margin, h - safe_margin)
                
                draw_secondary_maze_road(rx1, ry1, rx2, ry2, tile_type=dirt_tile)

        # 6. Place Buildings (STRICTLY ASSIGNED ONLY)
        placed_rects = [] 
        
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

        if allow_buildings and assigned_templates:
            # We strictly loop through the assigned templates for this chunk.
            # No random filling afterwards.
            for tmpl_name in assigned_templates:
                if tmpl_name in self.templates:
                    tmpl = self.templates[tmpl_name]
                    tw, th = tmpl['width'], tmpl['height']
                    
                    is_building2 = "building2" in tmpl_name.lower()
                    
                    placed = False
                    for _ in range(200): # Attempts per building
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
                                if side == -1: 
                                    ty = cy - road_radius - 1 - th
                                else: 
                                    ty = cy + road_radius + 1 + 1
                                tx = random.randint(border_w + 2, w - border_w - tw - 2)
                            
                            if tx < 0 or tx + tw >= w or ty < 0 or ty + th >= h: 
                                continue
                        else:
                            safe_pad = 2
                            if w - safe_pad*2 < tw or h - safe_pad*2 < th: break 
                            tx = random.randint(safe_pad, w - safe_pad - tw)
                            ty = random.randint(safe_pad, h - safe_pad - th)
                        
                        if is_area_free(tx, ty, tw, th, margin=1):
                            # Lot -> Sand
                            lot_m = 2
                            for ry in range(ty-lot_m, ty+th+lot_m):
                                for rx in range(tx-lot_m, tx+tw+lot_m):
                                    if 0<=rx<w and 0<=ry<h and layers['ground'][ry][rx] == 'bg_grass':
                                        layers['ground'][ry][rx] = sand_tile
                                        occupied_mask[ry][rx] = 1
                            
                            # Driveway
                            bx, by = tx + tw // 2, ty + th // 2
                            if (tw > 30 or th > 30) and not is_building2:
                                draw_secondary_maze_road(bx, by, cx, cy, sand_tile)
                            else:
                                x_s, x_e = min(cx, bx), max(cx, bx)
                                for rx in range(x_s, x_e + 1): 
                                    for off in range(2): 
                                        yy = cy + off
                                        if 0<=rx<w and 0<=yy<h and layers['ground'][yy][rx]!=road_tile and layers['ground'][yy][rx]!=self.water_tile: 
                                            layers['ground'][yy][rx]=sand_tile; occupied_mask[yy][rx]=1
                                
                                y_s, y_e = min(cy, by), max(cy, by)
                                for ry in range(y_s, y_e + 1):
                                    for off in range(2): 
                                        xx = bx + off
                                        if 0<=ry<h and 0<=xx<w and layers['ground'][ry][xx]!=road_tile and layers['ground'][ry][xx]!=self.water_tile: 
                                            layers['ground'][ry][xx]=sand_tile; occupied_mask[ry][xx]=1
                            
                            self._blit_template(layers, tmpl, tx, ty, w, h)
                            placed_rects.append(pygame.Rect(tx, ty, tw, th))
                            for ry in range(ty, ty + th):
                                for rx in range(tx, tx + tw): occupied_mask[ry][rx] = 1
                            print(f"Placed Assigned: {tmpl_name} at ({tx},{ty}) in chunk ({gx},{gy})")
                            placed = True

                            # Connect to neighbor
                            if len(placed_rects) > 1:
                                target_index = random.randint(0, len(placed_rects) - 2)
                                target_rect = placed_rects[target_index]
                                px, py = target_rect.centerx, target_rect.centery
                                bx, by = tx + tw // 2, ty + th // 2
                                draw_secondary_maze_road(bx, by, px, py, tile_type=sand_tile)
                            break
                    if not placed:
                        print(f"Failed to place {tmpl_name} in chunk ({gx},{gy})")

        # 7. Forest / Nature
        if self.forest_templates and not force_forest:
            # Add some nature to fill emptiness since we aren't spamming buildings
            for _ in range(12): 
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

        # 8. Tile Clusters
        if force_forest:
            for y in range(h):
                for x in range(w):
                    ground_tile = layers['ground'][y][x]
                    if ground_tile != road_tile and ground_tile != sand_tile and ground_tile != dirt_tile and ground_tile != self.water_tile:
                         layers['ground'][y][x] = 'bg_grass'
            cluster_count_range = random.randint(500, 1500)
            current_radius = 10
            current_density = 0.95
        else:
            cluster_count_range = random.randint(self.cluster_min_count, self.cluster_max_count)
            current_radius = self.cluster_radius
            current_density = self.cluster_density

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

        # 9. Spawns
        if is_start: 
            layers['spawn'][cy][cx] = 'P'
        else: 
            self._scatter_zombies(layers, occupied_mask, w, h)
        
        self._scatter_npcs(layers, occupied_mask, w, h)

        return layers

    def _scatter_zombies(self, layers, mask, w, h):
        building_tiles = []
        street_tiles = []
        woods_tiles = []
        
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                
                ground = layers['ground'][y][x]
                if ground == self.water_tile: continue # No water spawns

                if ground == 'sand_01' or ground == 'dirty_01':
                    building_tiles.append((x, y))
                elif ground == 'asphalt_01':
                    street_tiles.append((x, y))
                elif ground == 'bg_grass':
                    woods_tiles.append((x, y))

        total_zombies = random.randint(40, 60)
        count_building = int(total_zombies * 0.45)
        count_street = int(total_zombies * 0.25)
        count_woods = total_zombies - count_building - count_street
        
        def place_zombies(target_count, available_tiles):
            if not available_tiles: return
            chosen = random.sample(available_tiles, min(target_count, len(available_tiles)))
            for (zx, zy) in chosen:
                layers['spawn'][zy][zx] = 'Z'

        place_zombies(count_building, building_tiles)
        place_zombies(count_street, street_tiles)
        place_zombies(count_woods, woods_tiles)

    def _scatter_npcs(self, layers, mask, w, h):
        min_npcs_per_chunk = 1
        max_npcs_per_chunk = 2

        zombie_locs = []
        for y in range(h):
            for x in range(w):
                if layers['spawn'][y][x] == 'Z':
                    zombie_locs.append((x, y))
        
        potential_tiles = []
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                
                ground = layers['ground'][y][x]
                if ground == self.water_tile: continue # No water spawns

                if ground in ['asphalt_01', 'sand_01', 'dirty_01']:
                    potential_tiles.append((x, y))
        
        if not potential_tiles: return

        safe_candidates = []
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

        count = random.randint(min_npcs_per_chunk, max_npcs_per_chunk)
        if safe_candidates:
            chosen = random.sample(safe_candidates, min(count, len(safe_candidates)))
            for nx, ny in chosen:
                layers['spawn'][ny][nx] = 'NPC'

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
                
                g_char = ground[y][x]
                if g_char in defs: 
                    bg_surf.blit(defs[g_char]['image'], (px, py))
                
                b_char = base[y][x]
                if b_char in defs and b_char != ' ': 
                    bg_surf.blit(defs[b_char]['image'], (px, py))
                
                r_char = roof[y][x]
                if r_char in defs and r_char != ' ':
                    bg_surf.blit(defs[r_char]['image'], (px, py))
                
                l_char = light[y][x]
                if l_char in defs and l_char != ' ':
                    bg_surf.blit(defs[l_char]['image'], (px, py))
                
                s_char = spawn[y][x]
                if s_char in ['Z', 'P', 'I', 'NPC']:
                    color = (0, 0, 0)
                    if s_char == 'Z': color = (255, 0, 0)
                    elif s_char == 'P': color = (0, 255, 0)
                    elif s_char == 'I': color = (0, 0, 255)
                    elif s_char == 'NPC': color = (255, 255, 0)
                    pygame.draw.rect(heat_surf, color, (px, py, self.tile_size, self.tile_size))