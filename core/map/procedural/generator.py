# core/map/procedural/generator.py

import os
import random
import pygame
import math
import core.data.config
from core.data.config import *
from core.map.building_loader import load_building_templates

from core.map.procedural.generator_utils import ProceduralGeneratorUtils
from core.map.procedural.generator_rendering import ProceduralGeneratorRendering
from core.map.procedural.generator_maze import ProceduralGeneratorMaze
from core.map.procedural.generator_spawning import ProceduralGeneratorSpawning
from core.map.procedural.generator_l2_logic import ProceduralGeneratorL2
from core.map.procedural.generator_chunk_logic import ProceduralGeneratorChunk
from core.map.procedural.generator_template_loader import ProceduralGeneratorTemplate

class ProceduralGenerator(ProceduralGeneratorUtils, ProceduralGeneratorRendering, 
                          ProceduralGeneratorMaze, ProceduralGeneratorSpawning, 
                          ProceduralGeneratorL2, ProceduralGeneratorChunk, 
                          ProceduralGeneratorTemplate):
    def __init__(self, game, output_folder=None, 
                 building_counts=None, 
                 chunk_settings=None):
        self.game = game
        # --- SIZE SETTINGS ---
        self.chunk_size = CHUNK_SIZE 
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
        
        # --- GLOBAL L2 LIMITS (Specific Templates) ---
        self.global_l2_limits = {
            'Bunker': MAP_CHUNKS * 2,
            'Dungeon': MAP_CHUNKS * 3,
        }
        
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

        self._init_templates()


    def _extract_dynamic_chunk(self, global_layers, offset_x, offset_y, w, h):
        """Extracts a dynamically sized chunk from the global map layer."""
        chunk_layers = {}
        for key, grid in global_layers.items():
            chunk_layers[key] = []
            for r in range(h):
                row = []
                for c in range(w):
                    row.append(grid[offset_y + r][offset_x + c])
                chunk_layers[key].append(row)
        return chunk_layers

    def generate_world(self, seed_pattern=None, regenerate=False):
        self.chunk_size = core.data.config.CHUNK_SIZE
        self.tile_size = core.data.config.TILE_SIZE

        if not regenerate and os.path.exists(self.output_folder):
            for f in os.listdir(self.output_folder):
                # Update check to scan for separated chunks
                if f.startswith("map_L1_") and f.endswith("_map.csv"):
                    print(f"World already exists at {self.output_folder}. Skipping generation.")
                    return f
            
        current_chunks = core.data.config.MAP_CHUNKS
        
        if not seed_pattern or seed_pattern == "5-DEFAULT": 
            try:
                seed_pattern = generate_random_seed(current_chunks)
            except NameError:
                seed_pattern = f"{current_chunks}-{random.randint(1000,9999)}"
            
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

        # 1. Generate Connections
        connections_grid = self._generate_maze_connections(grid_w, grid_h)

        # 2. Build Global Deck (L1)
        global_deck = []
        
        self.heli_template = None
        self.military_template = None
        self.mil_petrol_template = None

        for category, limit in self.global_building_limits.items():
            if category == 'Cave': continue

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

        # 2b. Build Global L2 Deck
        global_l2_deck = []
        print("Building Global L2 Deck...")
        for category, limit in self.global_l2_limits.items():
            available = self.categorized_l2_templates.get(category, [])
            if not available:
                print(f"  > Warning: No L2 templates found for category '{category}'")
                continue
            
            pool = list(available)
            random.shuffle(pool)
            for _ in range(limit):
                if not pool:
                    pool = list(available)
                    random.shuffle(pool)
                if pool:
                    global_l2_deck.append(pool.pop())
        
        random.shuffle(global_l2_deck)
        print(f"  > Total Controlled L2 Templates to Place: {len(global_l2_deck)}")

        # 3. Calculate Urban Chunks
        all_coords = [(x, y) for x in range(grid_w) for y in range(grid_h)]
        total_chunks = grid_w * grid_h
        
        deck_size_estimate_chunks = math.ceil(len(global_deck) / 2) 
        base_urban_count = int(total_chunks * self.chunk_settings.get('urban_chunk_ratio', 0.8))
        num_building_chunks = max(base_urban_count, deck_size_estimate_chunks, self.chunk_settings.get('min_urban_chunks', 1))
        num_building_chunks = min(num_building_chunks, total_chunks) 

        # 4. Assign Military/Urban
        urban_candidates = list(all_coords)
        military_chunk_coords = set()
        island_groups = []
        
        # Helper to randomly grow an island into an L-shape or Rectangle
        def grow_group(start_coord, max_size, candidates):
            group = {start_coord}
            opts = [start_coord]
            while len(group) < max_size and candidates:
                cx, cy = random.choice(opts)
                neighbors = [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
                valid = [n for n in neighbors if n in candidates]
                if valid:
                    nxt = random.choice(valid)
                    group.add(nxt)
                    opts.append(nxt)
                    candidates.remove(nxt)
                else:
                    opts.remove((cx, cy))
                    if not opts: break
            return group

        max_island_size = 1 if total_chunks <= 9 else 3

        if self.chunk_settings.get('military_chunk_count', 0) > 0:
            border_candidates = [(x, y) for x, y in urban_candidates if x == 0 or x == grid_w - 1 or y == 0 or y == grid_h - 1]
            mil_start = random.choice(border_candidates) if border_candidates else random.choice(urban_candidates)
                
            urban_candidates.remove(mil_start)
            mil_size = random.choice(range(1, max_island_size + 1))
            military_chunk_coords = grow_group(mil_start, mil_size, urban_candidates)
            num_building_chunks = max(0, num_building_chunks - len(military_chunk_coords))

        # Prevent extra random islands on heavily constrained maps like 2x2
        if grid_w <= 2:
            num_random_islands = 0
        elif grid_w <= 3:
            num_random_islands = 1
        else:
            num_random_islands = max(1, (grid_w - 4) * 2 - 1)

        for _ in range(num_random_islands):
            border_candidates = [(x, y) for x, y in urban_candidates if x == 0 or x == grid_w - 1 or y == 0 or y == grid_h - 1]
            if border_candidates:
                isl_start = random.choice(border_candidates)
                urban_candidates.remove(isl_start)
                isl_size = random.choice(range(1, max_island_size + 1))
                new_island = grow_group(isl_start, isl_size, urban_candidates)
                island_groups.append(new_island)
                num_building_chunks = max(0, num_building_chunks - len(new_island))
        
        island_coords = set().union(*island_groups) if island_groups else set()
        urban_coords = set(random.sample(urban_candidates, min(len(urban_candidates), num_building_chunks)))

        # [NEW Helper] Group Identification for smart coastlines
        def get_group(cx, cy):
            if cx < 0 or cx >= grid_w or cy < 0 or cy >= grid_h: return 'out'
            if (cx, cy) in military_chunk_coords: return 'military'
            for idx, ig in enumerate(island_groups):
                if (cx, cy) in ig: return f'island_{idx}'
            return 'mainland'
        
        # 5. Distribute Deck (L1)
        chunk_priority_map = {coord: [] for coord in all_coords}
        
        cave_temps = self.categorized_templates.get('Cave', [])
        if cave_temps:
            for c_coord in all_coords:
                chunk_priority_map[c_coord].append(random.choice(cave_temps))

        urban_list = list(urban_coords)
        
        if urban_list:
            random.shuffle(urban_list)
            if global_deck:
                chunk_idx = 0
                for tmpl in global_deck:
                    target_chunk = urban_list[chunk_idx]
                    chunk_priority_map[target_chunk].append(tmpl)
                    chunk_idx = (chunk_idx + 1) % len(urban_list)

        if military_chunk_coords:
            mil_list = list(military_chunk_coords)
            print(f"Populating Military Chunks at {mil_list}")
            
            # Spread the templates across the available grouped military chunks
            m_idx = 0
            if self.heli_template:
                chunk_priority_map[mil_list[m_idx]].append(self.heli_template)
                m_idx = (m_idx + 1) % len(mil_list)
            if self.military_template:
                chunk_priority_map[mil_list[m_idx]].append(self.military_template)
                m_idx = (m_idx + 1) % len(mil_list)
            if self.mil_petrol_template:
                chunk_priority_map[mil_list[m_idx]].append(self.mil_petrol_template)

        # 5b. Distribute L2 Deck
        chunk_l2_priority_map = {coord: [] for coord in all_coords}
        l2_candidates = list(all_coords)
        random.shuffle(l2_candidates)
        
        if global_l2_deck:
            idx = 0
            for tmpl in global_l2_deck:
                target = l2_candidates[idx]
                chunk_l2_priority_map[target].append(tmpl)
                idx = (idx + 1) % len(l2_candidates)

        start_gx = random.randint(0, grid_w - 1)
        start_gy = random.randint(0, grid_h - 1)
        
        # Ensure the player NEVER spawns on the military island or any random island
        while (start_gx, start_gy) in military_chunk_coords or (start_gx, start_gy) in island_coords:
            start_gx = random.randint(0, grid_w - 1)
            start_gy = random.randint(0, grid_h - 1)
            
        # Force bridges where paths cross DIFFERENT landmass groups (e.g., Mainland to Island)
        for gy in range(grid_h):
            for gx in range(grid_w):
                my_g = get_group(gx, gy)
                for direction, nx, ny in [('top', gx, gy-1), ('bottom', gx, gy+1), ('left', gx-1, gy), ('right', gx+1, gy)]:
                    if connections_grid[gy][gx][direction]:
                        n_g = get_group(nx, ny)
                        if my_g != n_g and n_g != 'out':
                            connections_grid[gy][gx][f'{direction}_type'] = 'asphalt'
                            #connections_grid[gy][gx][direction] = False


        # --- PASS 1: Generate all chunks dynamically to determine sizes ---
        col_widths = [self.chunk_size] * grid_w
        row_heights = [self.chunk_size] * grid_h
        
        for gy in range(grid_h):
            for gx in range(grid_w):
                assigned_buildings = chunk_priority_map.get((gx, gy), [])
                is_center_chunk = (gx == start_gx and gy == start_gy)
                is_military_chunk = (gx, gy) in military_chunk_coords
                
                my_g = get_group(gx, gy)
                coast_left = (my_g != get_group(gx-1, gy))
                coast_right = (my_g != get_group(gx+1, gy))
                coast_top = (my_g != get_group(gx, gy-1))
                coast_bottom = (my_g != get_group(gx, gy+1))

                is_urban = (gx, gy) in urban_coords or is_military_chunk or len(assigned_buildings) > 0
                
                if is_center_chunk and self.chunk_settings.get('force_start_urban', True):
                    is_urban = True
                    
                base_size = self.chunk_size
                if assigned_buildings and is_urban:
                    total_area = 0
                    max_dim = 0
                    for t_name in assigned_buildings:
                        if hasattr(self, 'templates') and t_name in self.templates:
                            tw = self.templates[t_name]['width']
                            th = self.templates[t_name]['height']
                            total_area += (tw * th)
                            max_dim = max(max_dim, tw, th)
                    
                    area_based_size = int(math.ceil(math.sqrt(total_area * 4)))
                    min_fit_size = max_dim + 30 
                    
                    # Only increase base_size if the buildings physically cannot fit inside 128
                    required_size = max(area_based_size, min_fit_size)
                    if required_size > base_size:
                        base_size = required_size

                col_widths[gx] = max(col_widths[gx], base_size)
                row_heights[gy] = max(row_heights[gy], base_size)

        # --- PASS 2: Generate chunks using Uniform Cell Dimensions ---
        generated_chunks = {}
        chunk_dims = {}
        
        for gy in range(grid_h):
            for gx in range(grid_w):
                conns = connections_grid[gy][gx]
                assigned_buildings = chunk_priority_map.get((gx, gy), [])
                assigned_l2 = chunk_l2_priority_map.get((gx, gy), [])
                
                is_center_chunk = (gx == start_gx and gy == start_gy)
                is_military_chunk = (gx, gy) in military_chunk_coords
                
                # --- NEW SMART COAST LOGIC ---
                my_g = get_group(gx, gy)
                coast_left = (my_g != get_group(gx-1, gy))
                coast_right = (my_g != get_group(gx+1, gy))
                coast_top = (my_g != get_group(gx, gy-1))
                coast_bottom = (my_g != get_group(gx, gy+1))
                # -----------------------------
                
                is_urban = (gx, gy) in urban_coords or is_military_chunk or len(assigned_buildings) > 0
                
                if is_center_chunk and self.chunk_settings.get('force_start_urban', True):
                    is_urban = True

                c_w = col_widths[gx]
                c_h = row_heights[gy]

                chunk_data = self._generate_chunk_data(gx, gy, conns, 
                                                       is_start=is_center_chunk, 
                                                       assigned_templates=assigned_buildings, 
                                                       assigned_l2_templates=assigned_l2,
                                                       allow_buildings=is_urban,
                                                       force_forest=False,
                                                       cell_w=c_w, cell_h=c_h,
                                                       coast_left=coast_left,
                                                       coast_right=coast_right,
                                                       coast_top=coast_top,
                                                       coast_bottom=coast_bottom) 
                
                generated_chunks[(gx, gy)] = chunk_data
                chunk_dims[(gx, gy)] = (c_w, c_h)

        # --- ALLOCATE GLOBAL LAYERS DYNAMICALLY ---
        global_tiles_w = sum(col_widths)
        global_tiles_h = sum(row_heights)
        
        total_map_w = global_tiles_w * self.tile_size
        total_map_h = global_tiles_h * self.tile_size
        
        # Surfaces
        full_map_surface = pygame.Surface((total_map_w, total_map_h))
        full_map_surface.fill((20, 100, 20)) 
        
        heat_map_surface = pygame.Surface((total_map_w, total_map_h))
        
        full_map_surface_l2 = pygame.Surface((total_map_w, total_map_h))
        full_map_surface_l2.fill((0, 0, 0))
        heat_map_surface_l2 = pygame.Surface((total_map_w, total_map_h))
        
        # Global Layers
        global_layers = {
            'base': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'ground': [['bg_grass' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'spawn': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'roof': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'light': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'protected_mask': [[0 for _ in range(global_tiles_w)] for _ in range(global_tiles_h)]
        }

        global_layers_l2 = {
            'base': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'ground': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'spawn': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'roof': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'light': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'protected_mask': [[0 for _ in range(global_tiles_w)] for _ in range(global_tiles_h)]
        }
        
        occupied_mask_L2 = [[0 for _ in range(global_tiles_w)] for _ in range(global_tiles_h)]

        # --- PASS 2: MERGE CHUNKS INTO GLOBAL LAYERS ---
        chunk_offsets = {}
        for gy in range(grid_h):
            for gx in range(grid_w):
                chunk_data = generated_chunks[(gx, gy)]
                c_w, c_h = chunk_dims[(gx, gy)]
                
                # Calculate absolute placement offsets in the dynamic global map
                offset_x = sum(col_widths[:gx])
                offset_y = sum(row_heights[:gy])
                chunk_offsets[(gx, gy)] = (offset_x, offset_y)
                
                for layer_key, layer_grid in chunk_data.items():
                    # Merge L2
                    if layer_key.endswith('_L2'):
                        base_key = layer_key.replace('_L2', '')
                        if base_key in global_layers_l2:
                            for r in range(c_h):
                                for c in range(c_w):
                                    global_layers_l2[base_key][offset_y + r][offset_x + c] = layer_grid[r][c]
                    # Merge L1
                    elif layer_key in global_layers:
                        for r in range(c_h):
                            for c in range(c_w):
                                global_layers[layer_key][offset_y + r][offset_x + c] = layer_grid[r][c]

        print("Applying terrain smoothing (L1)...")
        self._apply_terrain_smoothing(global_layers, global_tiles_w, global_tiles_h)
        self._apply_sand_smoothing(global_layers, global_tiles_w, global_tiles_h, 'sand_01')
        self._apply_sand_smoothing(global_layers, global_tiles_w, global_tiles_h, 'beach_sand_01')

        # --- SCATTER VEHICLES (L1 Global) ---
        print("Scattering Vehicles (L1)...")
        self._scatter_vehicles(global_layers, None, global_tiles_w, global_tiles_h)
        
        # --- SCATTER ANIMALS (L1 Global) ---
        print("Scattering Animals (L1)...")
        self._scatter_animals(global_layers, None, global_tiles_w, global_tiles_h)
        
        # Re-render L1 heat map to show vehicles AND animals
        self._render_full_map_to_surface(full_map_surface, heat_map_surface, global_layers)
        
        # --- SAVE L1 CHUNKS (Separated) ---
        print("Saving L1 separate chunk maps...")
        for gy in range(self.grid_h):
            for gx in range(self.grid_w):
                # We extract the MAXIMUM allocated dimensions for this chunk cell to ensure padding/global traits are kept
                c_w = col_widths[gx]
                c_h = row_heights[gy]
                offset_x, offset_y = chunk_offsets[(gx, gy)]
                chunk_layers = self._extract_dynamic_chunk(global_layers, offset_x, offset_y, c_w, c_h)
                self._save_chunk(f"map_L1_{gx}_{gy}", chunk_layers)
        
        # --- RE-SCAN FOR L2 TEMPLATE MASKS ---
        print("Building L2 Occupancy Mask...")
        for y in range(global_tiles_h):
            for x in range(global_tiles_w):
                if global_layers_l2['roof'][y][x] != ' ' or global_layers_l2['base'][y][x] != ' ':
                    occupied_mask_L2[y][x] = 1

        # --- POST-PROCESSING: Connect Isolated L2 Buildings ---
        self._connect_l2_drunkards(global_layers_l2)

        # --- DECORATE PATHWAYS ---
        self._decorate_l2_pathways(global_layers_l2, occupied_mask_L2)

        # --- POPULATE L2 SPAWNS (Zombies & NPCs) ---
        print("Populating L2 Spawns (Zombies on Paths)...")
        self._populate_l2_spawns(global_layers_l2)
        
        print("Scattering Animals (L2)...")
        self._scatter_animals(global_layers_l2, occupied_mask_L2, global_tiles_w, global_tiles_h)

        # --- RENDER COMPLETE L2 MAP ---
        print("Rendering global world map L2 with pathways...")
        self._render_full_map_to_surface(full_map_surface_l2, heat_map_surface_l2, global_layers_l2)
        
        # --- SAVE L2 CHUNKS (Separated) ---
        print("Saving L2 separate chunk maps...")
        for gy in range(self.grid_h):
            for gx in range(self.grid_w):
                c_w = col_widths[gx]
                c_h = row_heights[gy]
                offset_x, offset_y = chunk_offsets[(gx, gy)]
                chunk_layers_l2 = self._extract_dynamic_chunk(global_layers_l2, offset_x, offset_y, c_w, c_h)
                self._save_chunk(f"map_L2_{gx}_{gy}", chunk_layers_l2)
        
        # DEBUG images
        try:
            scale_factor = 0.5
            new_w = int(total_map_w * scale_factor)
            new_h = int(total_map_h * scale_factor)
            preview_size = (new_w, new_h)

            # L1
            small_map_surface = pygame.transform.scale(full_map_surface, preview_size)
            pygame.image.save(small_map_surface, os.path.join(self.output_folder, "full_map.jpg"))
            small_heat_surface = pygame.transform.scale(heat_map_surface, preview_size)
            pygame.image.save(small_heat_surface, os.path.join(self.output_folder, "full_map_heat.jpg"))

            # L2
            small_map_l2 = pygame.transform.scale(full_map_surface_l2, preview_size)
            pygame.image.save(small_map_l2, os.path.join(self.output_folder, "full_map_L2.jpg"))
            small_heat_l2 = pygame.transform.scale(heat_map_surface_l2, preview_size)
            pygame.image.save(small_heat_l2, os.path.join(self.output_folder, "full_map_L2_heat.jpg"))
            
            print(f"Saved compressed map previews to {self.output_folder}")
        except Exception as e:
            print(f"Error saving map images: {e}")

        # Return the starting chunk filename so the map loader knows where to drop the player initially
        return f"map_L1_{start_gx}_{start_gy}_map.csv"