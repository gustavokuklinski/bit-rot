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

        # Initialize Templates via 
        self._init_templates()

    def generate_world(self, seed_pattern=None, regenerate=False):
        # [FIX] Force refresh size settings from config to ensure consistency
        self.chunk_size = core.data.config.CHUNK_SIZE
        self.tile_size = core.data.config.TILE_SIZE

        if not regenerate and os.path.exists(self.output_folder):
            for f in os.listdir(self.output_folder):
                if f.startswith("map_L1_world") and f.endswith("_map.csv"):
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

        # 2b. Build Global L2 Deck (Controlled)
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
        military_chunk_coord = None
        
        if self.chunk_settings.get('military_chunk_count', 0) > 0:
            military_chunk_coord = random.choice(urban_candidates)
            urban_candidates.remove(military_chunk_coord)
            num_building_chunks = max(0, num_building_chunks - 1)
        
        urban_coords = set(random.sample(urban_candidates, min(len(urban_candidates), num_building_chunks)))
        
        # 5. Distribute Deck (L1)
        chunk_priority_map = {coord: [] for coord in all_coords}
        
        # MANDATORY: 1 Cave Per Chunk
        cave_temps = self.categorized_templates.get('Cave', [])
        if cave_temps:
            for c_coord in all_coords:
                chunk_priority_map[c_coord].append(random.choice(cave_temps))
        else:
            print("WARNING: No L1 Cave templates found to place in chunks.")

        urban_list = list(urban_coords)
        
        if urban_list:
            random.shuffle(urban_list)
            if global_deck:
                chunk_idx = 0
                for tmpl in global_deck:
                    target_chunk = urban_list[chunk_idx]
                    chunk_priority_map[target_chunk].append(tmpl)
                    chunk_idx = (chunk_idx + 1) % len(urban_list)

        if military_chunk_coord:
            print(f"Populating Military Chunk at {military_chunk_coord}")
            if self.heli_template:
                chunk_priority_map[military_chunk_coord].append(self.heli_template)
            if self.military_template:
                chunk_priority_map[military_chunk_coord].append(self.military_template)
            if self.mil_petrol_template:
                chunk_priority_map[military_chunk_coord].append(self.mil_petrol_template)

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
        
        total_map_w = grid_w * self.chunk_size * self.tile_size
        total_map_h = grid_h * self.chunk_size * self.tile_size
        
        # Surfaces
        full_map_surface = pygame.Surface((total_map_w, total_map_h))
        full_map_surface.fill((20, 100, 20)) 
        
        heat_map_surface = pygame.Surface((total_map_w, total_map_h))
        
        full_map_surface_l2 = pygame.Surface((total_map_w, total_map_h))
        full_map_surface_l2.fill((0, 0, 0))
        heat_map_surface_l2 = pygame.Surface((total_map_w, total_map_h))
        
        # Global Layers
        global_tiles_w = grid_w * self.chunk_size
        global_tiles_h = grid_h * self.chunk_size
        
        global_layers = {
            'base': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'ground': [['bg_grass' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'spawn': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'roof': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'light': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)]
        }

        global_layers_l2 = {
            'base': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'ground': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'spawn': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'roof': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)],
            'light': [[' ' for _ in range(global_tiles_w)] for _ in range(global_tiles_h)]
        }
        
        # L2 Occupied Mask (Tracks Template Interiors)
        occupied_mask_L2 = [[0 for _ in range(global_tiles_w)] for _ in range(global_tiles_h)]

        # --- CHUNK GENERATION LOOP ---
        for gy in range(grid_h):
            for gx in range(grid_w):
                conns = connections_grid[gy][gx]
                assigned_buildings = chunk_priority_map.get((gx, gy), [])
                assigned_l2 = chunk_l2_priority_map.get((gx, gy), [])
                
                is_center_chunk = (gx == start_gx and gy == start_gy)
                is_military_chunk = (gx, gy) == military_chunk_coord
                is_urban = (gx, gy) in urban_coords or is_military_chunk or len(assigned_buildings) > 0
                
                if is_center_chunk and self.chunk_settings.get('force_start_urban', True):
                    is_urban = True

                chunk_data = self._generate_chunk_data(gx, gy, conns, 
                                                       is_start=is_center_chunk, 
                                                       assigned_templates=assigned_buildings, 
                                                       assigned_l2_templates=assigned_l2,
                                                       allow_buildings=is_urban,
                                                       force_forest=False) 
                
                offset_x = gx * self.chunk_size
                offset_y = gy * self.chunk_size
                
                render_data_l1 = {}

                for layer_key, layer_grid in chunk_data.items():
                    # Merge L2
                    if layer_key.endswith('_L2'):
                        base_key = layer_key.replace('_L2', '')
                        if base_key in global_layers_l2:
                            for r in range(self.chunk_size):
                                for c in range(self.chunk_size):
                                    global_layers_l2[base_key][offset_y + r][offset_x + c] = layer_grid[r][c]
                    # Merge L1
                    elif layer_key in global_layers:
                        for r in range(self.chunk_size):
                            for c in range(self.chunk_size):
                                global_layers[layer_key][offset_y + r][offset_x + c] = layer_grid[r][c]
                        render_data_l1[layer_key] = layer_grid

                # Render L1 (Chunk by chunk is fine for L1)
                self._render_chunk_to_surface(full_map_surface, heat_map_surface, gx, gy, render_data_l1)
        # -----------------------------

        # SAVE L1
        print("Saving global world map L1...")
        self._save_chunk("map_L1_world", global_layers)
        
        # --- RE-SCAN FOR L2 TEMPLATE MASKS ---
        # Build mask based on roof/base presence to prevent vegetation inside templates
        print("Building L2 Occupancy Mask...")
        for y in range(global_tiles_h):
            for x in range(global_tiles_w):
                # If there is a roof or a wall, it is a template.
                if global_layers_l2['roof'][y][x] != ' ' or global_layers_l2['base'][y][x] != ' ':
                    occupied_mask_L2[y][x] = 1

        # --- POST-PROCESSING: Connect Isolated L2 Buildings (Pathways) ---
        self._connect_l2_drunkards(global_layers_l2)
        # -----------------------------------------------------------------

        # --- DECORATE PATHWAYS (VEGETATION) ---
        # [UPDATED] Now accepts the mask to avoid decorating inside templates
        self._decorate_l2_pathways(global_layers_l2, occupied_mask_L2)
        # --------------------------------------

        # --- POPULATE L2 SPAWNS (Zombies & NPCs) ---
        print("Populating L2 Spawns (Zombies on Paths)...")
        self._populate_l2_spawns(global_layers_l2)
        # -------------------------------------------

        # --- RENDER COMPLETE L2 MAP ---
        # Now that pathways are generated, we render the FULL L2 map
        print("Rendering global world map L2 with pathways...")
        self._render_full_map_to_surface(full_map_surface_l2, heat_map_surface_l2, global_layers_l2)
        # ------------------------------

        # SAVE L2
        print("Saving global world map L2...")
        self._save_chunk("map_L2_world", global_layers_l2)
        
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

        return "map_L1_world_map.csv"