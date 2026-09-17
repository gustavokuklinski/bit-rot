# core/map/procedural/generator.py

import os
import random
import pygame
import math
import json
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
        self.chunk_size = CHUNK_SIZE 
        self.tile_size = TILE_SIZE
        self.output_folder = output_folder if output_folder else MAP_DIR
        self.buildings_path = os.path.join(MAP_DIR, 'buildings')
        self.templates = load_building_templates(self.buildings_path)
        
        self.default_chunk_settings = {
            'urban_chunk_ratio': 0.8,
            'min_urban_chunks': 1,
            'military_chunk_count': 1,
            'force_start_urban': True
        }
        self.chunk_settings = self.default_chunk_settings.copy()
        if chunk_settings:
            self.chunk_settings.update(chunk_settings)

        self.global_building_limits = {
            'Warehouse': MAP_CHUNKS * 5,
            'Stores': MAP_CHUNKS * 2,
            'Shed': MAP_CHUNKS * 5,
            'Building': MAP_CHUNKS * 10,
            'Petrol': MAP_CHUNKS * 3,
            'Heli': 1,
            'Military': 1
        }
        
        self.global_l2_limits = {
            'Bunker': MAP_CHUNKS * 5,
            'Dungeon': MAP_CHUNKS * 5,
        }
        
        self.forest_border_width = 1
        self.water_tile = 'water_01'
        self.sand_tile = 'beach_sand_01'
        self.coast_width = 15

        self.grid_w = MAP_CHUNKS
        self.grid_h = MAP_CHUNKS
        self.chunk_path = []
        self.connections_grid = []
        self.chunk_priority_map = {}
        self.chunk_l2_priority_map = {}
        self.generated_chunks = set()

        self._init_templates()

    def _generate_hamiltonian_progression(self, w, h):
        """
        Generates a Hamiltonian path visiting all w * h chunks in sequence.
        Only consecutive steps in the path have open road connections.
        """
        total_nodes = w * h

        # Exact 2x2 order requested:
        # [MILITARY (0,0)][PLAYER (1,0)]
        # [CHUNK N.2 (0,1)][CHUNK N.1 (1,1)]
        # Path: (1,0) -> (1,1) -> (0,1) -> (0,0)
        if w == 2 and h == 2:
            path = [(1, 0), (1, 1), (0, 1), (0, 0)]
        else:
            def get_unvisited_neighbors(x, y, visited):
                nbrs = []
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                        nbrs.append((nx, ny))
                return nbrs

            found_path = None
            for _ in range(300):
                sx = random.randint(0, w - 1)
                sy = random.randint(0, h - 1)
                if total_nodes % 2 == 1 and (sx + sy) % 2 != 0:
                    continue

                curr_path = [(sx, sy)]
                visited = {(sx, sy)}

                while len(curr_path) < total_nodes:
                    cx, cy = curr_path[-1]
                    nbrs = get_unvisited_neighbors(cx, cy, visited)
                    if not nbrs:
                        break
                    # Warnsdorff heuristic
                    nbrs.sort(key=lambda n: (len(get_unvisited_neighbors(n[0], n[1], visited)), random.random()))
                    next_node = nbrs[0]
                    visited.add(next_node)
                    curr_path.append(next_node)

                if len(curr_path) == total_nodes:
                    found_path = curr_path
                    break

            if found_path:
                path = found_path
            else:
                # Serpentine fallback
                path = []
                for y in range(h):
                    xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
                    for x in xs:
                        path.append((x, y))

        connections_grid = [[{
            'top': False, 'bottom': False, 'left': False, 'right': False,
            'top_type': 'asphalt', 'bottom_type': 'asphalt', 'left_type': 'asphalt', 'right_type': 'asphalt'
        } for _ in range(w)] for _ in range(h)]

        # Open connections ONLY between consecutive chunks in the path
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            if x2 == x1 + 1:
                connections_grid[y1][x1]['right'] = True
                connections_grid[y2][x2]['left'] = True
            elif x2 == x1 - 1:
                connections_grid[y1][x1]['left'] = True
                connections_grid[y2][x2]['right'] = True
            elif y2 == y1 + 1:
                connections_grid[y1][x1]['bottom'] = True
                connections_grid[y2][x2]['top'] = True
            elif y2 == y1 - 1:
                connections_grid[y1][x1]['top'] = True
                connections_grid[y2][x2]['bottom'] = True

        return path, connections_grid

    def generate_world(self, seed_pattern=None, regenerate=False):
        self.chunk_size = core.data.config.CHUNK_SIZE
        self.tile_size = core.data.config.TILE_SIZE

        current_chunks = core.data.config.MAP_CHUNKS
        if not seed_pattern or seed_pattern == "5-DEFAULT":
            try: seed_pattern = generate_random_seed(current_chunks)
            except: seed_pattern = f"{current_chunks}-{random.randint(1000,9999)}"

        if '-' in seed_pattern:
            parts = seed_pattern.split('-', 1)
            n_part = parts[0] or str(current_chunks)
            grid_w = int(n_part)
            grid_h = int(n_part)
            actual_seed = parts[1] or "DEFAULT"
        else:
            grid_w, grid_h = current_chunks, current_chunks
            actual_seed = seed_pattern

        self.grid_w = grid_w
        self.grid_h = grid_h

        print(f"[ProceduralGenerator] Seed: {actual_seed} | Grid: {grid_w}x{grid_h}")
        random.seed(actual_seed)

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # 1. Generate Progression Path & Connections
        self.chunk_path, self.connections_grid = self._generate_hamiltonian_progression(grid_w, grid_h)
        start_gx, start_gy = self.chunk_path[0]
        military_gx, military_gy = self.chunk_path[-1]

        # 2. Build Building Decks
        global_deck = []
        self.heli_template = None
        self.military_template = None
        self.mil_petrol_template = None

        for category, limit in self.global_building_limits.items():
            if category == 'Cave': continue
            available = self.categorized_templates.get(category, [])
            if not available: continue
            
            selected = []
            pool = list(available)
            random.shuffle(pool)
            for _ in range(limit):
                if not pool:
                    pool = list(available)
                    random.shuffle(pool)
                if pool: selected.append(pool.pop())
            
            if category == 'Heli':
                self.heli_template = selected[0] if selected else None
            elif category == 'Military':
                self.military_template = selected[0] if selected else None
            elif category == 'Petrol':
                if selected: self.mil_petrol_template = selected.pop(0)
                global_deck.extend(selected)
            else:
                global_deck.extend(selected)

        random.shuffle(global_deck)

        global_l2_deck = []
        for category, limit in self.global_l2_limits.items():
            available = self.categorized_l2_templates.get(category, [])
            if not available: continue
            pool = list(available)
            random.shuffle(pool)
            for _ in range(limit):
                if not pool:
                    pool = list(available)
                    random.shuffle(pool)
                if pool: global_l2_deck.append(pool.pop())
        random.shuffle(global_l2_deck)

        # 3. Assign Buildings to Path
        all_coords = [(x, y) for x in range(grid_w) for y in range(grid_h)]
        self.chunk_priority_map = {coord: [] for coord in all_coords}
        self.chunk_l2_priority_map = {coord: [] for coord in all_coords}

        # Add Cave to each chunk
        cave_temps = self.categorized_templates.get('Cave', [])
        if cave_temps:
            for coord in all_coords:
                self.chunk_priority_map[coord].append(random.choice(cave_temps))

        # Assign Military Chunk
        mil_coord = (military_gx, military_gy)
        if self.military_template: self.chunk_priority_map[mil_coord].append(self.military_template)
        if self.heli_template: self.chunk_priority_map[mil_coord].append(self.heli_template)
        if self.mil_petrol_template: self.chunk_priority_map[mil_coord].append(self.mil_petrol_template)

        # Distribute remaining buildings across intermediate chunks
        intermediate_chunks = [c for c in self.chunk_path if c != mil_coord]
        if intermediate_chunks and global_deck:
            idx = 0
            for tmpl in global_deck:
                self.chunk_priority_map[intermediate_chunks[idx]].append(tmpl)
                idx = (idx + 1) % len(intermediate_chunks)

        if intermediate_chunks and global_l2_deck:
            idx = 0
            for tmpl in global_l2_deck:
                self.chunk_l2_priority_map[intermediate_chunks[idx]].append(tmpl)
                idx = (idx + 1) % len(intermediate_chunks)

        # 4. Attach Generator to Game
        self.game.generator = self
        self.generated_chunks = set()

        # 5. Generate Start Chunk and Military Chunk
        print(f"[ProceduralGenerator] Generating Player Start Chunk ({start_gx}, {start_gy})...")
        self.generate_chunk_on_demand(start_gx, start_gy)

        print(f"[ProceduralGenerator] Pre-generating Military Goal Chunk ({military_gx}, {military_gy})...")
        self.generate_chunk_on_demand(military_gx, military_gy)

        # Save macro world metadata
        macro_meta_path = os.path.join(self.output_folder, "macro_world.json")
        try:
            with open(macro_meta_path, "w") as f:
                json.dump({
                    'grid_w': grid_w,
                    'grid_h': grid_h,
                    'chunk_path': self.chunk_path,
                    'start_chunk': [start_gx, start_gy],
                    'military_chunk': [military_gx, military_gy],
                    'connections_grid': self.connections_grid,
                    'chunk_priority_map': {f"{k[0]}_{k[1]}": v for k, v in self.chunk_priority_map.items()},
                    'chunk_l2_priority_map': {f"{k[0]}_{k[1]}": v for k, v in self.chunk_l2_priority_map.items()},
                    'generated_chunks': [list(c) for c in self.generated_chunks]
                }, f, indent=4)
        except Exception as e:
            print(f"Error saving macro_world.json: {e}")

        return f"map_L1_{start_gx}_{start_gy}_map.csv"

    def generate_chunk_on_demand(self, gx, gy):
        """Generates a chunk dynamically as the player enters it."""
        if (gx, gy) in self.generated_chunks:
            return

        conns = self.connections_grid[gy][gx]
        is_start = ((gx, gy) == self.chunk_path[0])
        is_military = ((gx, gy) == self.chunk_path[-1])
        
        assigned_buildings = self.chunk_priority_map.get((gx, gy), [])
        assigned_l2 = self.chunk_l2_priority_map.get((gx, gy), [])

        # Outer world borders
        coast_left = (gx == 0)
        coast_right = (gx == self.grid_w - 1)
        coast_top = (gy == 0)
        coast_bottom = (gy == self.grid_h - 1)

        c_w = self.chunk_size
        c_h = self.chunk_size

        chunk_data = self._generate_chunk_data(
            gx, gy, conns,
            is_start=is_start,
            assigned_templates=assigned_buildings,
            assigned_l2_templates=assigned_l2,
            allow_buildings=True,
            force_forest=False,
            cell_w=c_w, cell_h=c_h,
            coast_left=coast_left,
            coast_right=coast_right,
            coast_top=coast_top,
            coast_bottom=coast_bottom
        )

        l1_layers = {k: chunk_data[k] for k in ['base', 'ground', 'spawn', 'roof', 'light'] if k in chunk_data}
        l2_layers = {k.replace('_L2', ''): chunk_data[k] for k in chunk_data if k.endswith('_L2')}

        # Apply terrain smoothing
        self._apply_terrain_smoothing(l1_layers, c_w, c_h)
        self._apply_sand_smoothing(l1_layers, c_w, c_h, 'sand_01')
        self._apply_sand_smoothing(l1_layers, c_w, c_h, 'beach_sand_01')
        self._apply_asphalt_smoothing(l1_layers, c_w, c_h)

        # Scatter vehicles, animals, and quest items
        self._scatter_vehicles(l1_layers, None, c_w, c_h)
        self._scatter_animals(l1_layers, None, c_w, c_h)
        if hasattr(self, '_scatter_quest_items'):
            self._scatter_quest_items(l1_layers, None, c_w, c_h, 1)

        # Starting Chunk Player Spawn
        if is_start:
            has_p = any('P' in row for row in l1_layers['spawn'])
            if not has_p:
                found = False
                for y in range(c_h):
                    for x in range(c_w):
                        if l1_layers['ground'][y][x] == 'house_floor_01' and l1_layers['base'][y][x] == ' ':
                            l1_layers['spawn'][y][x] = 'P'
                            found = True
                            break
                    if found: break
                if not found:
                    l1_layers['spawn'][c_h // 2][c_w // 2] = 'P'

        # Layer 2 Processing
        self._connect_l2_drunkards(l2_layers)
        self._enforce_l2_contained_borders(l2_layers, c_w, c_h, conns)
        self._populate_l2_spawns(l2_layers)
        if hasattr(self, '_scatter_animals'):
            self._scatter_animals(l2_layers, None, c_w, c_h)
        if hasattr(self, '_scatter_quest_items'):
            self._scatter_quest_items(l2_layers, None, c_w, c_h, 2)

        # Save Layer 1 and Layer 2 files
        self._save_chunk(f"map_L1_{gx}_{gy}", l1_layers)
        self._save_chunk(f"map_L2_{gx}_{gy}", l2_layers)

        self.generated_chunks.add((gx, gy))
        print(f"[ProceduralGenerator] On-demand generated chunk ({gx}, {gy}) successfully.")