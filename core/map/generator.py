import os
import random
import csv
import pygame
import math
import core.data.config
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
            'urban_chunk_ratio': 0.8,
            'min_urban_chunks': 1,
            'military_chunk_count': 1,
            'force_start_urban': True
        }
        self.chunk_settings = self.default_chunk_settings.copy()
        if chunk_settings:
            self.chunk_settings.update(chunk_settings)

        # --- GLOBAL BUILDING LIMITS (MAX ON FULL MAP) ---
        self.global_building_limits = {
            'Warehouse': MAP_CHUNKS * 2,
            'Stores': MAP_CHUNKS * 2,
            'Shed': MAP_CHUNKS * 2,
            'Building': MAP_CHUNKS * 3,
            'Petrol': MAP_CHUNKS * 3,
            'Heli': 1,
            'Military': 1
        }
        # ------------------------------------------------

        # Forest settings
        self.forest_border_width = 1
        self.cluster_min_count = 20
        self.cluster_max_count = 100
        self.cluster_radius = 4
        self.cluster_density = 0.85

        # --- Island/Coast Settings ---
        self.water_tile = 'water_01'
        self.sand_tile = 'beach_sand_01'
        self.coast_width = 15
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
            'Heli': [],
            'Military': []
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
            if "military" in lower_name:
                self.categorized_templates['Military'].append(name)
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


    def generate_world(self, seed_pattern=None, regenerate=False):
        if not regenerate and os.path.exists(self.output_folder):
            # Check for the new single map format first
            for f in os.listdir(self.output_folder):
                if f.startswith("map_L1_world") and f.endswith("_map.csv"):
                    print(f"World already exists at {self.output_folder}. Skipping generation.")
                    return f
            # Fallback check (though we are moving away from this)
            for f in os.listdir(self.output_folder):
                if f.startswith("map_L1_P0_") and f.endswith("_map.csv"):
                    print(f"World already exists at {self.output_folder}. Skipping generation.")
                    return f

        current_chunks = core.data.config.MAP_CHUNKS
        
        if not seed_pattern or seed_pattern == "5-DEFAULT": 
            seed_pattern = generate_random_seed(current_chunks)
            
        if '-' in seed_pattern:
            parts = seed_pattern.split('-', 1)
            n_part = parts[0]
            if not n_part: n_part = str(current_chunks)
            grid_w = int(n_part)
            grid_h = int(n_part)
            actual_seed = parts[1]
            if not actual_seed: actual_seed = "DEFAULT"
        else:
            grid_w, grid_h = current_chunks, current_chunks
            actual_seed = seed_pattern

        self.grid_w = grid_w
        self.grid_h = grid_h

        print(f"Applying World Seed: {actual_seed} | Size: {grid_w}x{grid_h}")
        random.seed(actual_seed)

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # 1. Generate the Connection Matrix
        connections_grid = self._generate_maze_connections(grid_w, grid_h)

        # 2. Build the Global Building Deck
        global_deck = []
        
        self.heli_template = None
        self.military_template = None
        self.mil_petrol_template = None

        for category, limit in self.global_building_limits.items():
            available = self.categorized_templates.get(category, [])
            if not available:
                if category in ['Heli', 'Military', 'Petrol']:
                    print(f"CRITICAL WARNING: No templates found for mandatory category '{category}'!")
                else:
                    print(f"Warning: No templates found for category '{category}'")
                continue
            
            selected_for_category = []
            pool = list(available)
            random.shuffle(pool)
            
            for _ in range(limit):
                if not pool:
                    pool = list(available)
                    random.shuffle(pool)
                if pool:
                    tmpl = pool.pop()
                    selected_for_category.append(tmpl)
            
            # --- SPECIAL HANDLING ---
            if category == 'Heli':
                self.heli_template = selected_for_category[0] if selected_for_category else None
            elif category == 'Military':
                self.military_template = selected_for_category[0] if selected_for_category else None
            elif category == 'Petrol':
                if selected_for_category:
                    self.mil_petrol_template = selected_for_category.pop(0)
                global_deck.extend(selected_for_category)
            else:
                global_deck.extend(selected_for_category)

        random.shuffle(global_deck)

        # 3. Calculate Urban Chunks
        all_coords = [(x, y) for x in range(grid_w) for y in range(grid_h)]
        total_chunks = grid_w * grid_h
        
        deck_size_estimate_chunks = math.ceil(len(global_deck) / 2) 
        base_urban_count = int(total_chunks * self.chunk_settings.get('urban_chunk_ratio', 0.8))
        num_building_chunks = max(base_urban_count, deck_size_estimate_chunks, self.chunk_settings.get('min_urban_chunks', 1))
        num_building_chunks = min(num_building_chunks, total_chunks) 

        # 4. Assign Military/Urban Chunks
        urban_candidates = list(all_coords)
        military_chunk_coord = None
        
        if self.chunk_settings.get('military_chunk_count', 0) > 0:
            military_chunk_coord = random.choice(urban_candidates)
            urban_candidates.remove(military_chunk_coord)
            num_building_chunks = max(0, num_building_chunks - 1)
        
        urban_coords = set(random.sample(urban_candidates, min(len(urban_candidates), num_building_chunks)))
        
        # 5. Distribute Deck
        chunk_priority_map = {coord: [] for coord in all_coords}
        urban_list = list(urban_coords)
        
        if urban_list:
            random.shuffle(urban_list)
            if global_deck:
                chunk_idx = 0
                for tmpl in global_deck:
                    target_chunk = urban_list[chunk_idx]
                    chunk_priority_map[target_chunk].append(tmpl)
                    chunk_idx = (chunk_idx + 1) % len(urban_list)

        # --- ASSIGN MANDATORY SPECIALS TO MILITARY CHUNK ---
        if military_chunk_coord:
            print(f"Populating Military Chunk at {military_chunk_coord}")
            if self.heli_template:
                chunk_priority_map[military_chunk_coord].append(self.heli_template)
            
            if self.military_template:
                chunk_priority_map[military_chunk_coord].append(self.military_template)

            if self.mil_petrol_template:
                chunk_priority_map[military_chunk_coord].append(self.mil_petrol_template)

        start_gx = random.randint(0, grid_w - 1)
        start_gy = random.randint(0, grid_h - 1)
        
        total_map_w = grid_w * self.chunk_size * self.tile_size
        total_map_h = grid_h * self.chunk_size * self.tile_size
        full_map_surface = pygame.Surface((total_map_w, total_map_h))
        heat_map_surface = pygame.Surface((total_map_w, total_map_h))
        
        # --- PREPARE GLOBAL LAYERS ---
        global_tiles_w = grid_w * self.chunk_size
        global_tiles_h = grid_h * self.chunk_size
        
        global_layers = {
            'base': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'ground': [['bg_grass' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'spawn': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'roof': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'light': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)]
        }
        # -----------------------------

        for gy in range(grid_h):
            for gx in range(grid_w):
                pos_id = (gy * grid_w) + gx
                conns = connections_grid[gy][gx]
                
                assigned_buildings = chunk_priority_map.get((gx, gy), [])
                is_center_chunk = (gx == start_gx and gy == start_gy)
                is_military_chunk = (gx, gy) == military_chunk_coord
                
                is_urban = (gx, gy) in urban_coords or is_military_chunk or len(assigned_buildings) > 0
                
                if is_center_chunk and self.chunk_settings.get('force_start_urban', True):
                    is_urban = True

                chunk_data = self._generate_chunk_data(gx, gy, conns, 
                                                       is_start=is_center_chunk, 
                                                       assigned_templates=assigned_buildings, 
                                                       allow_buildings=is_urban,
                                                       force_forest=False) 
                
                # --- MERGE CHUNK INTO GLOBAL MAP ---
                offset_x = gx * self.chunk_size
                offset_y = gy * self.chunk_size
                
                for layer_key, layer_grid in chunk_data.items():
                    if layer_key in global_layers:
                        for r in range(self.chunk_size):
                            for c in range(self.chunk_size):
                                global_layers[layer_key][offset_y + r][offset_x + c] = layer_grid[r][c]
                # -----------------------------------

                self._render_chunk_to_surface(full_map_surface, heat_map_surface, gx, gy, chunk_data)

        # SAVE GLOBAL MAP
        print("Saving global world map...")
        filename_base = "map_L1_world"
        self._save_chunk(filename_base, global_layers)
        
        # DEBUG images
        try:
            scale_factor = 0.5
            new_w = int(total_map_w * scale_factor)
            new_h = int(total_map_h * scale_factor)
            preview_size = (new_w, new_h)

            small_map_surface = pygame.transform.smoothscale(full_map_surface, preview_size)
            pygame.image.save(small_map_surface, os.path.join(self.output_folder, "full_map.jpg"))
            
            small_heat_surface = pygame.transform.smoothscale(heat_map_surface, preview_size)
            pygame.image.save(small_heat_surface, os.path.join(self.output_folder, "full_map_heat.jpg"))
            
            print(f"Saved compressed map previews ({new_w}x{new_h}) to {self.output_folder}")
        except Exception as e:
            print(f"Error saving map images: {e}")

        return filename_base + "_map.csv"

    def _maps_exist(self, expected_count):
        if not os.path.exists(self.output_folder): return False
        # Check for global map
        for f in os.listdir(self.output_folder):
            if f.startswith("map_L1_world") and f.endswith("_map.csv"):
                return True
        return False


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
                if layers['ground'][current_y][current_x] == road_tile: break 
                if layers['ground'][current_y][current_x] == self.water_tile: break 

                if math.hypot(target_x - current_x, target_y - current_y) < 2: break

                moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                valid_moves = []
                for dx, dy in moves:
                    nx, ny = current_x + dx, current_y + dy
                    if 0 <= nx < w and 0 <= ny < h:
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

        # 4. Organic Coastline
        if hasattr(self, 'grid_w') and hasattr(self, 'grid_h'):
            cw = self.coast_width
            def get_coast_noise(idx, scale=0.1, amp=4.0):
                val = math.sin(idx * scale) * amp 
                val += math.sin(idx * scale * 2.1) * (amp * 0.5)
                val += random.uniform(-2.0, 2.0)
                return int(val)

            if gx == 0: # Left
                for y in range(h):
                    global_y = gy * h + y
                    offset = get_coast_noise(global_y)
                    water_lim = (cw - 8) + offset 
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

            if gx == self.grid_w - 1: # Right
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

            if gy == 0: # Top
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

            if gy == self.grid_h - 1: # Bottom
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

        # 5. Organic Trade Routes (Only if NOT mandatory/overcrowded)
        if allow_buildings and not force_forest:
            num_routes = 6
            safe_margin = self.coast_width + 3 
            for _ in range(num_routes):
                rx1 = random.randint(safe_margin, w - safe_margin)
                ry1 = random.randint(safe_margin, h - safe_margin)
                rx2 = random.randint(safe_margin, w - safe_margin)
                ry2 = random.randint(safe_margin, h - safe_margin)
                draw_secondary_maze_road(rx1, ry1, rx2, ry2, tile_type=dirt_tile)

        # 6. Place Buildings (MANDATORY LOGIC)
        placed_rects = [] 
        
        def is_area_free(tx, ty, tw, th, margin=0, ignore_mask=False):
            t_rect = pygame.Rect(tx, ty, tw, th)
            # 1. Check Collision with other buildings
            for pr in placed_rects:
                if t_rect.inflate(margin*2, margin*2).colliderect(pr): return False
            
            # 2. Check Map Boundaries
            if tx < 0 or tx + tw > w or ty < 0 or ty + th > h: return False

            # 3. Check Mask (Trees, Water, Roads) - unless forced
            if not ignore_mask:
                mx1, my1 = max(0, tx - margin), max(0, ty - margin)
                mx2, my2 = min(w, tx + tw + margin), min(h, ty + th + margin)
                for ry in range(my1, my2):
                    for rx in range(mx1, mx2):
                        if 0 <= ry < h and 0 <= rx < w:
                            if occupied_mask[ry][rx] == 1: 
                                return False
            else:
                # Even if ignoring mask, NEVER place on Water or Map Edges (Connection Roads)
                # Let's say connection roads are at x=cx/cy range? 
                # Better safe check: Don't place on water_tile
                mx1, my1 = tx, ty
                mx2, my2 = tx + tw, ty + th
                for ry in range(my1, my2):
                    for rx in range(mx1, mx2):
                         if 0 <= ry < h and 0 <= rx < w:
                             if layers['ground'][ry][rx] == self.water_tile:
                                 return False
            return True

        if allow_buildings and assigned_templates:
            # SORT MANDATORY BUILDINGS BY SIZE (Largest First)
            # This ensures the Heli/Mil base get spots before smaller sheds
            sorted_templates = []
            for t_name in assigned_templates:
                if t_name in self.templates:
                    t = self.templates[t_name]
                    area = t['width'] * t['height']
                    sorted_templates.append((area, t_name))
            sorted_templates.sort(key=lambda x: x[0], reverse=True)
            
            ordered_names = [x[1] for x in sorted_templates]

            for tmpl_name in ordered_names:
                tmpl = self.templates[tmpl_name]
                tw, th = tmpl['width'], tmpl['height']
                is_building2 = "building2" in tmpl_name.lower()
                
                placed = False
                
                # --- STRATEGY 1: Random Attempts (Standard) ---
                for _ in range(100): 
                    if is_building2:
                        # (Keep existing building2 random logic)
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
                    else:
                        safe_pad = 2
                        if w - safe_pad*2 < tw or h - safe_pad*2 < th: break
                        tx = random.randint(safe_pad, w - safe_pad - tw)
                        ty = random.randint(safe_pad, h - safe_pad - th)
                    
                    if is_area_free(tx, ty, tw, th, margin=1):
                        self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile)
                        placed = True
                        break
                
                # --- STRATEGY 2: Exhaustive Grid Scan (If Random Failed) ---
                if not placed:
                    print(f"Random placement failed for {tmpl_name}, trying scan...")
                    stride = 2 # Step size
                    for sy in range(border_w + 2, h - border_w - th - 2, stride):
                        if placed: break
                        for sx in range(border_w + 2, w - border_w - tw - 2, stride):
                            if is_area_free(sx, sy, tw, th, margin=1):
                                self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, sx, sy, tw, th, cx, cy, w, h, is_building2, sand_tile)
                                placed = True
                                break
                
                # --- STRATEGY 3: Force Placement (Clear Obstacles) ---
                if not placed:
                    print(f"FORCE PLACING Mandatory Building: {tmpl_name}")
                    # Try random spots again, but IGNORE obstacles (except water/edge)
                    for _ in range(50):
                        tx = random.randint(5, w - 5 - tw)
                        ty = random.randint(5, h - 5 - th)
                        
                        # Ensure we don't block the absolute center road intersection (hub)
                        # Hub is roughly cx-2 to cx+2
                        hub_rect = pygame.Rect(cx-3, cy-3, 6, 6)
                        new_rect = pygame.Rect(tx, ty, tw, th)
                        
                        if not hub_rect.colliderect(new_rect):
                            if is_area_free(tx, ty, tw, th, margin=0, ignore_mask=True):
                                # Clear the area first
                                for cy_clr in range(ty, ty + th):
                                    for cx_clr in range(tx, tx + tw):
                                        if 0 <= cy_clr < h and 0 <= cx_clr < w:
                                            layers['base'][cy_clr][cx_clr] = ' ' # Remove tree
                                            layers['ground'][cy_clr][cx_clr] = sand_tile # Prepare ground
                                            occupied_mask[cy_clr][cx_clr] = 0 # Temp clear mask
                                
                                self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile)
                                placed = True
                                break

                if not placed:
                    print(f"CRITICAL FAILURE: Could not place {tmpl_name} even with force!")

        # 7. Forest / Nature (Fill remaining gaps)
        if self.forest_templates and not force_forest:
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

    def _finalize_placement(self, layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile):
        road_tile = 'asphalt_01'
        # Lot -> Sand
        lot_m = 2
        for ry in range(ty-lot_m, ty+th+lot_m):
            for rx in range(tx-lot_m, tx+tw+lot_m):
                if 0<=rx<w and 0<=ry<h and layers['ground'][ry][rx] == 'bg_grass':
                    layers['ground'][ry][rx] = sand_tile
                    occupied_mask[ry][rx] = 1
        
        # Driveway
        bx, by = tx + tw // 2, ty + th // 2
        
        def draw_secondary_road(start_x, start_y, target_x, target_y):
            # Simple Manhattan connector for driveway
            cur_x, cur_y = start_x, start_y
            while cur_x != target_x or cur_y != target_y:
                if cur_x < target_x: cur_x += 1
                elif cur_x > target_x: cur_x -= 1
                elif cur_y < target_y: cur_y += 1
                elif cur_y > target_y: cur_y -= 1
                
                if 0<=cur_x<w and 0<=cur_y<h:
                     if layers['ground'][cur_y][cur_x] != road_tile and layers['ground'][cur_y][cur_x] != self.water_tile:
                         layers['ground'][cur_y][cur_x] = sand_tile
                         occupied_mask[cur_y][cur_x] = 1

        if (tw > 30 or th > 30) and not is_building2:
            draw_secondary_road(bx, by, cx, cy)
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
        print(f"PLACED: {tmpl_name} at ({tx},{ty})")

        if NPC_STATIC_SPAWN > 0:
            for sy in range(ty + 1, ty + th - 1):
                for sx in range(tx + 1, tx + tw - 1):
                    if 0 <= sx < w and 0 <= sy < h:
                        # Check if tile is empty ground (no furniture/walls in base layer)
                        # and no other spawn marker exists
                        if layers['base'][sy][sx] == ' ' and layers['spawn'][sy][sx] == ' ':
                            if random.random() < NPC_STATIC_SPAWN:
                                layers['spawn'][sy][sx] = 'S'

    def _scatter_zombies(self, layers, mask, w, h):
        building_tiles = []
        street_tiles = []
        woods_tiles = []
        
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                
                ground = layers['ground'][y][x]
                if ground == self.water_tile: continue 

                if ground == 'sand_01' or ground == 'dirty_01':
                    building_tiles.append((x, y))
                elif ground == 'asphalt_01':
                    street_tiles.append((x, y))
                elif ground == 'bg_grass':
                    woods_tiles.append((x, y))

        total_zombies = ZOMBIE_MAX_CHUNK
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
        min_npcs_per_chunk = NPC_MAX_CHUNK
        max_npcs_per_chunk = NPC_MAX_CHUNK

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
                if ground == self.water_tile: continue 

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
                if s_char in ['Z', 'P', 'I', 'NPC', 'S']:
                    color = (0, 0, 0)
                    if s_char == 'Z': color = (255, 0, 0)
                    elif s_char == 'P': color = (0, 255, 0)
                    elif s_char == 'I': color = (0, 0, 255)
                    elif s_char == 'NPC': color = (255, 255, 0)
                    elif s_char == 'S': color = (0, 0, 255) # Blue for Static NPCs
                    pygame.draw.rect(heat_surf, color, (px, py, self.tile_size, self.tile_size))