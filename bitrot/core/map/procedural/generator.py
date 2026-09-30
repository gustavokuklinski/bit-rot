# core/map/procedural/generator.py

import json
import math
import os
import random
import core.data.config
from core.data.config import *
from core.map.building_loader import load_building_templates
from core.map.procedural.generator_chunk_logic import ProceduralGeneratorChunk
from core.map.procedural.generator_l2_logic import ProceduralGeneratorL2
from core.map.procedural.generator_maze import ProceduralGeneratorMaze
from core.map.procedural.generator_rendering import ProceduralGeneratorRendering
from core.map.procedural.generator_spawning import ProceduralGeneratorSpawning
from core.map.procedural.generator_template_loader import (
    ProceduralGeneratorTemplate,
)
from core.map.procedural.generator_utils import ProceduralGeneratorUtils


class ProceduralGenerator(
    ProceduralGeneratorUtils,
    ProceduralGeneratorRendering,
    ProceduralGeneratorMaze,
    ProceduralGeneratorSpawning,
    ProceduralGeneratorL2,
    ProceduralGeneratorChunk,
    ProceduralGeneratorTemplate,
):

  def __init__(
      self, game, output_folder=None, building_counts=None, chunk_settings=None
  ):
    self.game = game
    self.chunk_size = core.data.config.CHUNK_SIZE
    self.tile_size = core.data.config.TILE_SIZE
    self.output_folder = output_folder if output_folder else MAP_DIR
    self.buildings_path = os.path.join(MAP_DIR, 'buildings')
    self.templates = load_building_templates(self.buildings_path)

    self.default_chunk_settings = {
        'urban_chunk_ratio': 0.55,
        'min_urban_chunks': 1,
        'military_chunk_count': 1,
        'force_start_urban': True,
    }
    self.chunk_settings = self.default_chunk_settings.copy()
    if chunk_settings:
      self.chunk_settings.update(chunk_settings)

    self.forest_border_width = 1
    self.water_tile = 'water_01'
    self.sand_tile = 'beach_sand_01'
    self.coast_width = 15

    self.grid_w = MAP_CHUNKS
    self.grid_h = MAP_CHUNKS
    self.chunk_path = []
    self.active_chunks = set()
    self.isolated_island_chunks = set()
    self.start_chunk = (0, 0)
    self.military_chunk = (0, 0)
    self.connections_grid = []
    self.chunk_priority_map = {}
    self.chunk_l2_priority_map = {}
    self.chunk_l3_priority_map = {}
    self.forest_chunks = set()
    self.urban_chunks = set()
    self.generated_chunks = set()

    self._init_templates()

  def _link_conns(self, grid, x1, y1, x2, y2, road_type='asphalt', link_l1=True, link_l2=True, link_l3=True):
    if x2 == x1 + 1 and y2 == y1:
      if link_l1:
        grid[y1][x1]['right'] = True
        grid[y1][x1]['right_type'] = road_type
        grid[y2][x2]['left'] = True
        grid[y2][x2]['left_type'] = road_type
      if link_l2:
        grid[y1][x1]['l2_right'] = True
        grid[y2][x2]['l2_left'] = True
      if link_l3:
        grid[y1][x1]['l3_right'] = True
        grid[y2][x2]['l3_left'] = True
    elif x2 == x1 - 1 and y2 == y1:
      if link_l1:
        grid[y1][x1]['left'] = True
        grid[y1][x1]['left_type'] = road_type
        grid[y2][x2]['right'] = True
        grid[y2][x2]['right_type'] = road_type
      if link_l2:
        grid[y1][x1]['l2_left'] = True
        grid[y2][x2]['l2_right'] = True
      if link_l3:
        grid[y1][x1]['l3_left'] = True
        grid[y2][x2]['l3_right'] = True
    elif y2 == y1 + 1 and x2 == x1:
      if link_l1:
        grid[y1][x1]['bottom'] = True
        grid[y1][x1]['bottom_type'] = road_type
        grid[y2][x2]['top'] = True
        grid[y2][x2]['top_type'] = road_type
      if link_l2:
        grid[y1][x1]['l2_bottom'] = True
        grid[y2][x2]['l2_top'] = True
      if link_l3:
        grid[y1][x1]['l3_bottom'] = True
        grid[y2][x2]['l3_top'] = True
    elif y2 == y1 - 1 and x2 == x1:
      if link_l1:
        grid[y1][x1]['top'] = True
        grid[y1][x1]['top_type'] = road_type
        grid[y2][x2]['bottom'] = True
        grid[y2][x2]['bottom_type'] = road_type
      if link_l2:
        grid[y1][x1]['l2_top'] = True
        grid[y2][x2]['l2_bottom'] = True
      if link_l3:
        grid[y1][x1]['l3_top'] = True
        grid[y2][x2]['l3_bottom'] = True

  def _generate_evolving_island_path(self, target_count):
    DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    best_result = None

    for attempt in range(300):
      current = (0, 0)
      spine = [current]
      visited = {current}
      current_dir = (1, 0)
      spine_target = max(2, int(target_count * 0.70))

      while len(spine) < spine_target:
        valid_dirs = []
        for d in DIRS:
          nxt = (current[0] + d[0], current[1] + d[1])
          if nxt not in visited:
            valid_dirs.append(d)

        if not valid_dirs:
          break

        if current_dir in valid_dirs and random.random() < 0.65:
          chosen_dir = current_dir
        else:
          perp_dirs = [d for d in valid_dirs if d != current_dir and (d[0] == -current_dir[0] or d[1] == -current_dir[1])]
          if perp_dirs and random.random() < 0.80:
            chosen_dir = random.choice(perp_dirs)
          else:
            chosen_dir = random.choice(valid_dirs)

        current_dir = chosen_dir
        current = (current[0] + chosen_dir[0], current[1] + chosen_dir[1])
        visited.add(current)
        spine.append(current)

      all_cells = list(spine)
      branch_attempts = 0
      while len(all_cells) < target_count and branch_attempts < 600:
        branch_attempts += 1
        parent = random.choice(all_cells)
        free_neighbors = []
        for d in DIRS:
          cand = (parent[0] + d[0], parent[1] + d[1])
          if cand not in visited:
            free_neighbors.append(cand)

        if free_neighbors:
          new_cell = random.choice(free_neighbors)
          visited.add(new_cell)
          all_cells.append(new_cell)

      if len(all_cells) >= target_count:
        best_result = (spine, all_cells[:target_count])
        break

    if not best_result:
      spine = []
      all_cells = []
      w_fallback = 6
      x, y = 0, 0
      dx = 1
      while len(all_cells) < target_count:
        cell = (x, y)
        all_cells.append(cell)
        spine.append(cell)
        x += dx
        if x >= w_fallback:
          x = w_fallback - 1
          y += 1
          dx = -1
        elif x < 0:
          x = 0
          y += 1
          dx = 1
      best_result = (spine, all_cells)

    spine, all_cells = best_result

    min_x = min(c[0] for c in all_cells)
    min_y = min(c[1] for c in all_cells)

    norm_cells = [(c[0] - min_x, c[1] - min_y) for c in all_cells]
    norm_spine = [(c[0] - min_x, c[1] - min_y) for c in spine]

    active_set = set(norm_cells)
    start_chunk = norm_spine[0]
    military_chunk = norm_spine[-1]

    max_w = max(c[0] for c in norm_cells) + 1
    max_h = max(c[1] for c in norm_cells) + 1

    connections_grid = [[
        {
            'top': False,
            'bottom': False,
            'left': False,
            'right': False,
            'top_type': 'asphalt',
            'bottom_type': 'asphalt',
            'left_type': 'asphalt',
            'right_type': 'asphalt',
            'l2_top': False,
            'l2_bottom': False,
            'l2_left': False,
            'l2_right': False,
            'l3_top': False,
            'l3_bottom': False,
            'l3_left': False,
            'l3_right': False,
        }
        for _ in range(max_w)
    ] for _ in range(max_h)]

    for i in range(len(norm_spine) - 1):
      x1, y1 = norm_spine[i]
      x2, y2 = norm_spine[i + 1]
      self._link_conns(connections_grid, x1, y1, x2, y2, 'asphalt', link_l1=True, link_l2=True, link_l3=True)

    for cell in norm_cells:
      cx, cy = cell
      for dx, dy in DIRS:
        nx, ny = cx + dx, cy + dy
        if (nx, ny) in active_set:
          already_connected = False
          if dx == 1 and connections_grid[cy][cx]['right']: already_connected = True
          elif dx == -1 and connections_grid[cy][cx]['left']: already_connected = True
          elif dy == 1 and connections_grid[cy][cx]['bottom']: already_connected = True
          elif dy == -1 and connections_grid[cy][cx]['top']: already_connected = True

          if not already_connected:
            has_any_conn = (connections_grid[cy][cx]['top'] or connections_grid[cy][cx]['bottom'] or
                            connections_grid[cy][cx]['left'] or connections_grid[cy][cx]['right'])
            if not has_any_conn or random.random() < 0.25:
              self._link_conns(connections_grid, cx, cy, nx, ny, 'dirty', link_l1=True, link_l2=True, link_l3=True)

    for cell in norm_cells:
      cx, cy = cell
      for dx, dy in DIRS:
        nx, ny = cx + dx, cy + dy
        if (nx, ny) in active_set:
          self._link_conns(connections_grid, cx, cy, nx, ny, link_l1=False, link_l2=True, link_l3=True)

    num_islands = max(1, target_count // 2)
    isolated_islands = {military_chunk}

    other_candidates = [c for c in norm_cells if c != start_chunk and c != military_chunk]
    if other_candidates and num_islands > 1:
      needed_additional = num_islands - 1
      leaf_candidates = []
      for c in other_candidates:
        cx, cy = c
        l1_count = sum(1 for d in [connections_grid[cy][cx]['top'], connections_grid[cy][cx]['bottom'],
                                   connections_grid[cy][cx]['left'], connections_grid[cy][cx]['right']] if d)
        if l1_count <= 1:
          leaf_candidates.append(c)

      random.shuffle(leaf_candidates)
      random.shuffle(other_candidates)

      pool = leaf_candidates + [c for c in other_candidates if c not in leaf_candidates]
      for c in pool[:needed_additional]:
        isolated_islands.add(c)

    for island_coord in isolated_islands:
      ix, iy = island_coord
      if connections_grid[iy][ix]['top']:
        connections_grid[iy][ix]['top'] = False
        connections_grid[iy - 1][ix]['bottom'] = False
      if connections_grid[iy][ix]['bottom']:
        connections_grid[iy][ix]['bottom'] = False
        connections_grid[iy + 1][ix]['top'] = False
      if connections_grid[iy][ix]['left']:
        connections_grid[iy][ix]['left'] = False
        connections_grid[iy][ix - 1]['right'] = False
      if connections_grid[iy][ix]['right']:
        connections_grid[iy][ix]['right'] = False
        connections_grid[iy][ix + 1]['left'] = False

      has_l2 = (connections_grid[iy][ix]['l2_top'] or connections_grid[iy][ix]['l2_bottom'] or
                connections_grid[iy][ix]['l2_left'] or connections_grid[iy][ix]['l2_right'])
      if not has_l2:
        for dx, dy in DIRS:
          nx, ny = ix + dx, iy + dy
          if (nx, ny) in active_set:
            self._link_conns(connections_grid, ix, iy, nx, ny, link_l1=False, link_l2=True, link_l3=False)
            break

      has_l3 = (connections_grid[iy][ix]['l3_top'] or connections_grid[iy][ix]['l3_bottom'] or
                connections_grid[iy][ix]['l3_left'] or connections_grid[iy][ix]['l3_right'])
      if not has_l3:
        for dx, dy in DIRS:
          nx, ny = ix + dx, iy + dy
          if (nx, ny) in active_set:
            self._link_conns(connections_grid, ix, iy, nx, ny, link_l1=False, link_l2=False, link_l3=True)
            break

    return norm_spine, norm_cells, active_set, connections_grid, max_w, max_h, start_chunk, military_chunk, isolated_islands

  def generate_world(self, seed_pattern=None, regenerate=False):
    self.chunk_size = core.data.config.CHUNK_SIZE
    self.tile_size = core.data.config.TILE_SIZE

    macro_meta_path = os.path.join(self.output_folder, 'macro_world.json')
    if not regenerate and os.path.exists(macro_meta_path):
      try:
        with open(macro_meta_path, 'r') as f:
          meta = json.load(f)
        self.grid_w = meta.get('grid_w', core.data.config.MAP_CHUNKS)
        self.grid_h = meta.get('grid_h', core.data.config.MAP_CHUNKS)
        self.chunk_path = [tuple(c) for c in meta.get('chunk_path', [])]
        self.active_chunks = {tuple(c) for c in meta.get('active_chunks', self.chunk_path)}
        self.isolated_island_chunks = {tuple(c) for c in meta.get('isolated_island_chunks', [])}
        self.start_chunk = tuple(meta.get('start_chunk', self.chunk_path[0]))
        self.military_chunk = tuple(meta.get('military_chunk', self.chunk_path[-1]))
        self.lobby_chunk = tuple(meta.get('lobby_chunk', self.start_chunk))
        self.connections_grid = meta.get('connections_grid', [])
        self.chunk_priority_map = {
            tuple(map(int, k.split('_'))): v
            for k, v in meta.get('chunk_priority_map', {}).items()
        }
        self.chunk_l2_priority_map = {
            tuple(map(int, k.split('_'))): v
            for k, v in meta.get('chunk_l2_priority_map', {}).items()
        }
        self.chunk_l3_priority_map = {
            tuple(map(int, k.split('_'))): v
            for k, v in meta.get('chunk_l3_priority_map', {}).items()
        }
        self.forest_chunks = {
            tuple(c) for c in meta.get('forest_chunks', [])
        }
        self.urban_chunks = {
            tuple(c) for c in meta.get('urban_chunks', [])
        }
        self.generated_chunks = {
            tuple(c) for c in meta.get('generated_chunks', [])
        }
        self.game.generator = self
        start_gx, start_gy = self.start_chunk
        return f'map_L1_{start_gx}_{start_gy}_map.csv'
      except Exception as e:
        print(f'Error reading existing macro_world.json: {e}')

    current_chunks = core.data.config.MAP_CHUNKS

    if seed_pattern and '-' in seed_pattern:
      parts = seed_pattern.split('-', 1)
      n_part = parts[0] or str(current_chunks)
      try:
        req_n = int(n_part)
      except ValueError:
        req_n = current_chunks
      actual_seed = parts[1] or 'DEFAULT'
    else:
      req_n = current_chunks
      actual_seed = seed_pattern or 'DEFAULT'

    target_chunks = max(2, req_n)
    print(f'[ProceduralGenerator] Seed: {actual_seed} | Target Chunks: {target_chunks} (Fixed 128x128)')
    random.seed(actual_seed)

    if not os.path.exists(self.output_folder):
      os.makedirs(self.output_folder)

    (self.chunk_path, all_cells, self.active_chunks,
     self.connections_grid, self.grid_w, self.grid_h,
     island_start_chunk, self.military_chunk,
     self.isolated_island_chunks) = self._generate_evolving_island_path(target_chunks)

    # Find a cardinal neighbor directly adjacent to island_start_chunk to place the Lobby chunk
    sx, sy = island_start_chunk
    candidate_dirs = [(-1, 0), (0, -1), (1, 0), (0, 1)]
    chosen_dir = None
    for dx, dy in candidate_dirs:
      if (sx + dx, sy + dy) not in self.active_chunks:
        chosen_dir = (dx, dy)
        break

    if not chosen_dir:
      for c in all_cells:
        if c != self.military_chunk:
          for dx, dy in candidate_dirs:
            if (c[0] + dx, c[1] + dy) not in self.active_chunks:
              sx, sy = c
              chosen_dir = (dx, dy)
              break
          if chosen_dir:
            break

    if not chosen_dir:
      chosen_dir = (1, 0)
      sx, sy = self.grid_w - 1, 0

    cand_lx = sx + chosen_dir[0]
    cand_ly = sy + chosen_dir[1]

    # If coordinates are negative, shift all chunk coordinates so all values stay >= 0
    shift_x = 1 if cand_lx < 0 else 0
    shift_y = 1 if cand_ly < 0 else 0

    if shift_x > 0 or shift_y > 0:
      self.chunk_path = [(c[0] + shift_x, c[1] + shift_y) for c in self.chunk_path]
      all_cells = [(c[0] + shift_x, c[1] + shift_y) for c in all_cells]
      self.active_chunks = {(c[0] + shift_x, c[1] + shift_y) for c in self.active_chunks}
      self.isolated_island_chunks = {(c[0] + shift_x, c[1] + shift_y) for c in self.isolated_island_chunks}
      island_start_chunk = (island_start_chunk[0] + shift_x, island_start_chunk[1] + shift_y)
      self.military_chunk = (self.military_chunk[0] + shift_x, self.military_chunk[1] + shift_y)

      old_grid = self.connections_grid
      old_h = len(old_grid)
      old_w = len(old_grid[0]) if old_h > 0 else 0
      new_grid_w = old_w + shift_x
      new_grid_h = old_h + shift_y

      def _empty_conn():
        return {
            'top': False, 'bottom': False, 'left': False, 'right': False,
            'top_type': 'asphalt', 'bottom_type': 'asphalt',
            'left_type': 'asphalt', 'right_type': 'asphalt',
            'l2_top': False, 'l2_bottom': False, 'l2_left': False, 'l2_right': False,
            'l3_top': False, 'l3_bottom': False, 'l3_left': False, 'l3_right': False
        }

      new_conns = [[_empty_conn() for _ in range(new_grid_w)] for _ in range(new_grid_h)]
      for y in range(old_h):
        for x in range(old_w):
          new_conns[y + shift_y][x + shift_x] = old_grid[y][x]

      self.connections_grid = new_conns
      self.grid_w = new_grid_w
      self.grid_h = new_grid_h

    lobby_gx = cand_lx + shift_x
    lobby_gy = cand_ly + shift_y
    self.lobby_chunk = (lobby_gx, lobby_gy)
    self.start_chunk = self.lobby_chunk
    self.active_chunks.add(self.lobby_chunk)

    needed_w = max(self.grid_w, lobby_gx + 1)
    needed_h = max(self.grid_h, lobby_gy + 1)
    for y in range(len(self.connections_grid)):
      while len(self.connections_grid[y]) < needed_w:
        self.connections_grid[y].append({
            'top': False, 'bottom': False, 'left': False, 'right': False,
            'top_type': 'asphalt', 'bottom_type': 'asphalt',
            'left_type': 'asphalt', 'right_type': 'asphalt',
            'l2_top': False, 'l2_bottom': False, 'l2_left': False, 'l2_right': False,
            'l3_top': False, 'l3_bottom': False, 'l3_left': False, 'l3_right': False
        })
    while len(self.connections_grid) < needed_h:
      self.connections_grid.append([{
          'top': False, 'bottom': False, 'left': False, 'right': False,
          'top_type': 'asphalt', 'bottom_type': 'asphalt',
          'left_type': 'asphalt', 'right_type': 'asphalt',
          'l2_top': False, 'l2_bottom': False, 'l2_left': False, 'l2_right': False,
          'l3_top': False, 'l3_bottom': False, 'l3_left': False, 'l3_right': False
      } for _ in range(needed_w)])

    self.grid_w = needed_w
    self.grid_h = needed_h

    # Connect Lobby chunk to the adjacent Island chunk ON LAYER 3 ONLY
    connect_target = (sx + shift_x, sy + shift_y)
    self._link_conns(
        self.connections_grid,
        lobby_gx,
        lobby_gy,
        connect_target[0],
        connect_target[1],
        link_l1=False,
        link_l2=False,
        link_l3=True
    )

    mil_coord = self.military_chunk

    intermediate = [c for c in all_cells if c != mil_coord]
    non_start = [c for c in intermediate if c != island_start_chunk]
    random.shuffle(non_start)

    num_forest = max(0, int(len(non_start) * 0.40)) if non_start else 0
    self.forest_chunks = set(non_start[:num_forest])
    self.urban_chunks = set(non_start[num_forest:])
    self.urban_chunks.add(island_start_chunk)

    num_urban = max(1, len(self.urban_chunks))

    self.global_building_limits = {
        'Building': num_urban * 3,
        'Stores': num_urban * 2,
        'Warehouse': num_urban * 2,
        'Shed': num_urban * 2,
        'Petrol': max(1, num_urban // 2),
    }

    self.global_l2_limits = {
        'Bunker': num_urban * 2,
        'Dungeon': num_urban * 2,
    }

    self.global_l3_limits = {
        'Bunker': num_urban * 2,
        'Dungeon': num_urban * 2,
    }

    self.military_deck = []
    for t_name in list(self.templates.keys()):
      low = t_name.lower()
      if 'military' in low or low.startswith('military_'):
        self.military_deck.append(t_name)

    self.heli_template = next(
        (t for t in self.categorized_templates.get('Heli', [])), None
    )
    self.mil_petrol_template = next(
        (t for t in self.categorized_templates.get('Petrol', [])), None
    )

    military_l3_deck = [t for t in self.l3_templates if 'military' in t.lower()]
    for cat in ['Bunker', 'Dungeon']:
        for t in self.categorized_l3_templates.get(cat, []):
            if 'military' in t.lower() and t not in military_l3_deck:
                military_l3_deck.append(t)

    global_deck = []
    for category, limit in self.global_building_limits.items():
      if category in ('Cave', 'Military', 'Heli', 'Lobby', 'Port'):
        continue
      available = [
          t for t in self.categorized_templates.get(category, [])
          if 'military' not in t.lower() and 'lobby' not in t.lower() and 'port' not in t.lower()
      ]
      if not available:
        continue
      pool = list(available)
      random.shuffle(pool)
      for _ in range(limit):
        if not pool:
          pool = list(available)
          random.shuffle(pool)
        if pool:
          global_deck.append(pool.pop())
    random.shuffle(global_deck)

    global_l2_deck = []
    for category, limit in self.global_l2_limits.items():
      available = self.categorized_l2_templates.get(category, [])
      if not available:
        continue
      pool = list(available)
      random.shuffle(pool)
      for _ in range(limit):
        if not pool:
          pool = list(available)
          random.shuffle(pool)
        if pool:
          global_l2_deck.append(pool.pop())
    if self.l2_templates:
      global_l2_deck.extend(self.l2_templates)
    random.shuffle(global_l2_deck)

    global_l3_deck = []
    for category, limit in self.global_l3_limits.items():
      available = self.categorized_l3_templates.get(category, [])
      if not available:
        continue
      pool = list(available)
      random.shuffle(pool)
      for _ in range(limit):
        if not pool:
          pool = list(available)
          random.shuffle(pool)
        if pool:
          global_l3_deck.append(pool.pop())
    if self.l3_templates:
      global_l3_deck.extend(self.l3_templates)
    random.shuffle(global_l3_deck)

    self.chunk_priority_map = {coord: [] for coord in all_cells}
    self.chunk_l2_priority_map = {coord: [] for coord in all_cells}
    self.chunk_l3_priority_map = {coord: [] for coord in all_cells}
    self.chunk_priority_map[self.lobby_chunk] = []
    self.chunk_l2_priority_map[self.lobby_chunk] = []
    self.chunk_l3_priority_map[self.lobby_chunk] = []

    if military_l3_deck:
      self.chunk_l3_priority_map[mil_coord].extend(military_l3_deck)

    cave_temps = [t for t in self.categorized_templates.get('Cave', []) if 'l2' not in t.lower() and 'l3' not in t.lower()]
    if not cave_temps:
      cave_temps = self.categorized_templates.get('Cave', [])
    if cave_temps:
      for coord in all_cells:
        self.chunk_priority_map[coord].append(random.choice(cave_temps))

    if self.military_deck:
      self.chunk_priority_map[mil_coord].extend(self.military_deck)
    if self.heli_template:
      self.chunk_priority_map[mil_coord].append(self.heli_template)
    if self.mil_petrol_template:
      self.chunk_priority_map[mil_coord].append(self.mil_petrol_template)

    urban_list = [c for c in self.urban_chunks if c != mil_coord]
    if urban_list and global_deck:
      idx = 0
      for tmpl in global_deck:
        self.chunk_priority_map[urban_list[idx]].append(tmpl)
        idx = (idx + 1) % len(urban_list)

    if urban_list and global_l2_deck:
      idx = 0
      for tmpl in global_l2_deck:
        self.chunk_l2_priority_map[urban_list[idx]].append(tmpl)
        idx = (idx + 1) % len(urban_list)

    if urban_list and global_l3_deck:
      idx = 0
      for tmpl in global_l3_deck:
        self.chunk_l3_priority_map[urban_list[idx]].append(tmpl)
        idx = (idx + 1) % len(urban_list)

    self.game.generator = self
    self.generated_chunks = set()

    for (gx, gy) in self.active_chunks:
      self.generate_chunk_on_demand(gx, gy)

    try:
      with open(macro_meta_path, 'w') as f:
        json.dump(
            {
                'grid_w': self.grid_w,
                'grid_h': self.grid_h,
                'active_chunks': [list(c) for c in self.active_chunks],
                'isolated_island_chunks': [list(c) for c in self.isolated_island_chunks],
                'chunk_path': self.chunk_path,
                'start_chunk': list(self.start_chunk),
                'lobby_chunk': list(self.lobby_chunk),
                'military_chunk': list(self.military_chunk),
                'connections_grid': self.connections_grid,
                'chunk_priority_map': {
                    f'{k[0]}_{k[1]}': v
                    for k, v in self.chunk_priority_map.items()
                },
                'chunk_l2_priority_map': {
                    f'{k[0]}_{k[1]}': v
                    for k, v in self.chunk_l2_priority_map.items()
                },
                'chunk_l3_priority_map': {
                    f'{k[0]}_{k[1]}': v
                    for k, v in self.chunk_l3_priority_map.items()
                },
                'forest_chunks': [list(c) for c in self.forest_chunks],
                'urban_chunks': [list(c) for c in self.urban_chunks],
                'generated_chunks': [list(c) for c in self.generated_chunks],
            },
            f,
            indent=4,
        )
    except Exception as e:
      print(f'Error saving macro_world.json: {e}')

    start_gx, start_gy = self.start_chunk
    return f'map_L1_{start_gx}_{start_gy}_map.csv'

  def generate_chunk_on_demand(self, gx, gy):
    if (gx, gy) in self.generated_chunks or (gx, gy) not in self.active_chunks:
      return

    is_lobby = (getattr(self, 'lobby_chunk', None) == (gx, gy))
    conns_raw = self.connections_grid[gy][gx]
    is_start = ((gx, gy) == self.start_chunk)
    is_military = ((gx, gy) == self.military_chunk)
    is_forest = ((gx, gy) in self.forest_chunks)
    is_isolated = ((gx, gy) in self.isolated_island_chunks)

    conns_l1 = {
        'top': conns_raw.get('top', False),
        'bottom': conns_raw.get('bottom', False),
        'left': conns_raw.get('left', False),
        'right': conns_raw.get('right', False),
        'top_type': conns_raw.get('top_type', 'asphalt'),
        'bottom_type': conns_raw.get('bottom_type', 'asphalt'),
        'left_type': conns_raw.get('left_type', 'asphalt'),
        'right_type': conns_raw.get('right_type', 'asphalt'),
    }

    conns_l2 = {
        'top': conns_raw.get('l2_top', False),
        'bottom': conns_raw.get('l2_bottom', False),
        'left': conns_raw.get('l2_left', False),
        'right': conns_raw.get('l2_right', False),
    }

    conns_l3 = {
        'top': conns_raw.get('l3_top', False),
        'bottom': conns_raw.get('l3_bottom', False),
        'left': conns_raw.get('l3_left', False),
        'right': conns_raw.get('l3_right', False),
    }

    assigned_buildings = self.chunk_priority_map.get((gx, gy), [])
    assigned_l2 = self.chunk_l2_priority_map.get((gx, gy), [])
    assigned_l3 = self.chunk_l3_priority_map.get((gx, gy), [])

    if is_isolated:
      coast_left = coast_right = coast_top = coast_bottom = True
    else:
      coast_left = not conns_l1['left']
      coast_right = not conns_l1['right']
      coast_top = not conns_l1['top']
      coast_bottom = not conns_l1['bottom']

    c_w = self.chunk_size
    c_h = self.chunk_size

    chunk_data = self._generate_chunk_data(
        gx,
        gy,
        conns_l1,
        is_start=is_start,
        assigned_templates=assigned_buildings,
        assigned_l2_templates=assigned_l2,
        assigned_l3_templates=assigned_l3,
        allow_buildings=(not is_forest or bool(assigned_buildings)),
        force_forest=is_forest,
        cell_w=c_w,
        cell_h=c_h,
        coast_left=coast_left,
        coast_right=coast_right,
        coast_top=coast_top,
        coast_bottom=coast_bottom,
        conns_l2=conns_l2,
        conns_l3=conns_l3,
    )

    l1_layers = {
        k: chunk_data[k]
        for k in ['base', 'ground', 'spawn', 'roof', 'light']
        if k in chunk_data
    }
    l2_layers = {
        k.replace('_L2', ''): chunk_data[k]
        for k in chunk_data
        if k.endswith('_L2')
    }
    l3_layers = {
        k.replace('_L3', ''): chunk_data[k]
        for k in chunk_data
        if k.endswith('_L3')
    }

    # If this is the lobby chunk, connect L3 to the adjacent chunk doorway and save
    if is_lobby:
      self._connect_l2_drunkards(l3_layers, conns_l2=conns_l3)
      self._enforce_l2_contained_borders(l3_layers, c_w, c_h, conns_l2=conns_l3)
      self._decorate_l2_pathways(l3_layers, c_w, c_h, conns_l2=conns_l3)
      self._populate_l2_spawns(l3_layers)

      for y in range(c_h):
        for x in range(c_w):
          if l3_layers['ground'][y][x] == ' ':
            l3_layers['ground'][y][x] = 'dirty_01'
            l3_layers['base'][y][x] = '@'

      self._save_chunk(f'map_L1_{gx}_{gy}', l1_layers)
      self._save_chunk(f'map_L2_{gx}_{gy}', l2_layers)
      self._save_chunk(f'map_L3_{gx}_{gy}', l3_layers)
      self.generated_chunks.add((gx, gy))
      print(f'[ProceduralGenerator] Saved clean Lobby Chunk ({gx}, {gy}) [L1 Isolated, L3 Connected & Discovered] successfully.')
      return

    # Format Layer 1 (Surface)
    self._apply_terrain_smoothing(l1_layers, c_w, c_h)
    self._apply_sand_smoothing(l1_layers, c_w, c_h, 'sand_01')
    self._apply_sand_smoothing(l1_layers, c_w, c_h, 'beach_sand_01')
    self._apply_asphalt_smoothing(l1_layers, c_w, c_h)

    self._scatter_vehicles(l1_layers, None, c_w, c_h)
    self._scatter_animals(l1_layers, None, c_w, c_h, multiplier=2 if is_forest else 1, is_l2=False)

    if hasattr(self, '_scatter_quest_items'):
      self._scatter_quest_items(l1_layers, None, c_w, c_h, 1)

    # Format Layer 2 (Caves 1)
    self._connect_l2_drunkards(l2_layers, conns_l2=conns_l2)
    self._enforce_l2_contained_borders(l2_layers, c_w, c_h, conns_l2=conns_l2)
    self._decorate_l2_pathways(l2_layers, c_w, c_h, conns_l2=conns_l2)
    self._populate_l2_spawns(l2_layers)

    if hasattr(self, '_scatter_animals'):
      self._scatter_animals(l2_layers, None, c_w, c_h, multiplier=4 if is_forest else 2, is_l2=True)
    if hasattr(self, '_scatter_quest_items'):
      self._scatter_quest_items(l2_layers, None, c_w, c_h, 2)

    for y in range(c_h):
        for x in range(c_w):
            if l2_layers['ground'][y][x] == ' ':
                l2_layers['ground'][y][x] = 'dirty_01'
                l2_layers['base'][y][x] = '@'

    # Format Layer 3 (Caves 2 / Deep Underground)
    self._connect_l2_drunkards(l3_layers, conns_l2=conns_l3)
    self._enforce_l2_contained_borders(l3_layers, c_w, c_h, conns_l2=conns_l3)
    self._decorate_l2_pathways(l3_layers, c_w, c_h, conns_l2=conns_l3)
    self._populate_l2_spawns(l3_layers)

    if hasattr(self, '_scatter_animals'):
      self._scatter_animals(l3_layers, None, c_w, c_h, multiplier=4 if is_forest else 2, is_l2=True)
    if hasattr(self, '_scatter_quest_items'):
      self._scatter_quest_items(l3_layers, None, c_w, c_h, 3)

    for y in range(c_h):
        for x in range(c_w):
            if l3_layers['ground'][y][x] == ' ':
                l3_layers['ground'][y][x] = 'dirty_01'
                l3_layers['base'][y][x] = '@'

    # Save chunks for all three layers
    self._save_chunk(f'map_L1_{gx}_{gy}', l1_layers)
    self._save_chunk(f'map_L2_{gx}_{gy}', l2_layers)
    self._save_chunk(f'map_L3_{gx}_{gy}', l3_layers)

    # Format Layer 1 (Surface)
    self._apply_terrain_smoothing(l1_layers, c_w, c_h)
    self._apply_sand_smoothing(l1_layers, c_w, c_h, 'sand_01')
    self._apply_sand_smoothing(l1_layers, c_w, c_h, 'beach_sand_01')
    self._apply_asphalt_smoothing(l1_layers, c_w, c_h)

    self._scatter_vehicles(l1_layers, None, c_w, c_h)
    self._scatter_animals(l1_layers, None, c_w, c_h, multiplier=2 if is_forest else 1, is_l2=False)

    if hasattr(self, '_scatter_quest_items'):
      self._scatter_quest_items(l1_layers, None, c_w, c_h, 1)

    # Format Layer 2 (Caves 1)
    self._connect_l2_drunkards(l2_layers, conns_l2=conns_l2)
    self._enforce_l2_contained_borders(l2_layers, c_w, c_h, conns_l2=conns_l2)
    self._populate_l2_spawns(l2_layers)

    if hasattr(self, '_scatter_animals'):
      self._scatter_animals(l2_layers, None, c_w, c_h, multiplier=4 if is_forest else 2, is_l2=True)
    if hasattr(self, '_scatter_quest_items'):
      self._scatter_quest_items(l2_layers, None, c_w, c_h, 2)

    for y in range(c_h):
        for x in range(c_w):
            if l2_layers['ground'][y][x] == ' ':
                l2_layers['ground'][y][x] = 'dirty_01'
                l2_layers['base'][y][x] = '@'

    # Format Layer 3 (Caves 2 / Deep Underground - Same logic as Layer 2)
    self._connect_l2_drunkards(l3_layers, conns_l2=conns_l3)
    self._enforce_l2_contained_borders(l3_layers, c_w, c_h, conns_l2=conns_l3)
    self._populate_l2_spawns(l3_layers)

    if hasattr(self, '_scatter_animals'):
      self._scatter_animals(l3_layers, None, c_w, c_h, multiplier=4 if is_forest else 2, is_l2=True)
    if hasattr(self, '_scatter_quest_items'):
      self._scatter_quest_items(l3_layers, None, c_w, c_h, 3)

    for y in range(c_h):
        for x in range(c_w):
            if l3_layers['ground'][y][x] == ' ':
                l3_layers['ground'][y][x] = 'dirty_01'
                l3_layers['base'][y][x] = '@'

    # Save chunks for all three layers
    self._save_chunk(f'map_L1_{gx}_{gy}', l1_layers)
    self._save_chunk(f'map_L2_{gx}_{gy}', l2_layers)
    self._save_chunk(f'map_L3_{gx}_{gy}', l3_layers)

    self.generated_chunks.add((gx, gy))
    chunk_type_lbl = (
        'MILITARY ISLAND' if is_military else ('ISOLATED ISLAND' if is_isolated else ('FOREST' if is_forest else 'URBAN'))
    )
    print(
        f'[ProceduralGenerator] Generated {chunk_type_lbl} chunk ({gx},'
        f' {gy}) [Layers 1, 2, 3 - 128x128] successfully.'
    )