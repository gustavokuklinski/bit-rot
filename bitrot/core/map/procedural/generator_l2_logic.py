# core/map/procedural/generator_l2_logic.py

import math
import random
from core.data.config import *

class ProceduralGeneratorL2:
    def _populate_l2_spawns(self, layers):
        """
        Populates Layer 2 with Zombies on Pathways only.
        Guarantees NO zombies spawn on obstacles, walls, '@', '#', or void tiles.
        """
        ground = layers.get('ground')
        base = layers.get('base')
        spawn = layers.get('spawn')
        
        if not ground or not base or not spawn: return
        
        h = len(ground)
        w = len(ground[0])
        
        pathway_candidates = []
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}

        for y in range(2, h - 2):
            for x in range(2, w - 2):
                base_tile = base[y][x]
                ground_tile = ground[y][x]
                spawn_tile = spawn[y][x]

                # Base must be completely empty (no obstacles, no walls, no @, no #)
                if base_tile != ' ': continue
                if base_tile in ['@', '#']: continue
                if base_tile in defs and defs[base_tile].get('is_obstacle', False): continue

                # Ground must be a valid walkable tile (NOT void ' ', NOT @, NOT #, NOT obstacle)
                if ground_tile in ['@', '#', ' ', '']: continue
                if ground_tile in defs and defs[ground_tile].get('is_obstacle', False): continue

                if spawn_tile != ' ': continue

                # Check neighbors to avoid spawning right against walls, void, or @ / #
                has_wall_neighbor = False
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = base[y + dy][x + dx]
                    ng = ground[y + dy][x + dx]
                    if nb in ['@', '#'] or ng in ['@', '#', ' ']:
                        has_wall_neighbor = True
                        break
                    if nb in defs and defs[nb].get('is_obstacle', False):
                        has_wall_neighbor = True
                        break
                if has_wall_neighbor: continue

                g_char = ground_tile.lower()
                # Include sand_01 pathway as valid candidate
                if 'dirty' in g_char or 'asphalt' in g_char or 'path' in g_char or 'cave_l2' in g_char or 'sand' in g_char:
                    pathway_candidates.append((x, y))

        chunks_x = max(1, w // self.chunk_size)
        chunks_y = max(1, h // self.chunk_size)
        total_chunks = max(1, chunks_x * chunks_y)
        total_zombies = ZOMBIE_MAX_CHUNK * total_chunks

        if pathway_candidates:
            count = min(len(pathway_candidates), total_zombies)
            chosen = random.sample(pathway_candidates, count)
            for (zx, zy) in chosen:
                spawn[zy][zx] = 'Z'
                
        print(f"  > Spawning Report L2: {len(chosen) if pathway_candidates else 0} Zombies on Pathways (Map Limit: {total_zombies}).")

    def _decorate_l2_pathways(self, layers, mask):
        """
        Decorates L2 pathways with vegetation.
        """
        ground = layers.get('ground')
        base = layers.get('base')
        if not ground or not base: return

        h = len(ground)
        w = len(ground[0])
        
        veg_options = ['garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_stone', 'garden_tree_11', 'garden_tall_grass', 'garden_stone_powder', 'garden_stone_iron']

        print("Decorating L2 Pathways with vegetation...")

        for y in range(h):
            for x in range(w):
                if ground[y][x] in ['dirty_01', 'sand_01'] and base[y][x] == ' ' and mask[y][x] == 0:
                    if random.random() < 0.15:
                        base[y][x] = random.choice(veg_options)

    def _enforce_l2_contained_borders(self, layers, w, h, conns=None):
        """
        Keeps Layer 2 contained within the chunk.
        Where chunks connect (and along outer chunk edges), creates a wall with '@'.
        """
        ground = layers.get('ground')
        base = layers.get('base')
        if not ground or not base: return

        border_tile = '@'
        cx, cy = w // 2, h // 2
        conn_depth = 4
        conn_radius = 4

        # 1. At all chunk connection points, create a wall with '@' on Layer 2
        if conns:
            if conns.get('top'):
                for y in range(conn_depth):
                    for x in range(max(0, cx - conn_radius), min(w, cx + conn_radius + 1)):
                        base[y][x] = border_tile
            if conns.get('bottom'):
                for y in range(h - conn_depth, h):
                    for x in range(max(0, cx - conn_radius), min(w, cx + conn_radius + 1)):
                        base[y][x] = border_tile
            if conns.get('left'):
                for x in range(conn_depth):
                    for y in range(max(0, cy - conn_radius), min(h, cy + conn_radius + 1)):
                        base[y][x] = border_tile
            if conns.get('right'):
                for x in range(w - conn_depth, w):
                    for y in range(max(0, cy - conn_radius), min(h, cy + conn_radius + 1)):
                        base[y][x] = border_tile

        # 2. Seal the outer 2-tile perimeter of the chunk so paths never leak into the void
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w - 2 or y < 2 or y >= h - 2:
                    if ground[y][x] != ' ' or base[y][x] != ' ':
                        base[y][x] = border_tile

    def _connect_l2_drunkards(self, layers):
        """
        Carves a 3-tier connected maze contained on Layer 2:
        1. Primary pathways (width 4, dirty_01).
        2. Secondary drunkard maze (width 3, dirty_01) with loops and cross-branches.
        3. Third pathway (strictly 2 tiles narrow, sand_01).
        Everything is 100% connected.
        """
        ground = layers.get('ground')
        base = layers.get('base')
        if not ground or not base: return

        h = len(ground)
        w = len(ground[0])
        
        visited = set()
        components = []

        # Identify all rooms/structures inside this chunk
        for y in range(h):
            for x in range(w):
                if (x, y) not in visited and ground[y][x] not in [' ', '@', '#']:
                    stack = [(x, y)]
                    visited.add((x, y))
                    island_pixels = []
                    while stack:
                        cx, cy = stack.pop()
                        island_pixels.append((cx, cy))
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < w and 0 <= ny < h:
                                if (nx, ny) not in visited and ground[ny][nx] not in [' ', '@', '#']:
                                    visited.add((nx, ny))
                                    stack.append((nx, ny))
                    if island_pixels and len(island_pixels) >= 4:
                        avg_x = sum(p[0] for p in island_pixels) // len(island_pixels)
                        avg_y = sum(p[1] for p in island_pixels) // len(island_pixels)
                        components.append((avg_x, avg_y))

        if not components:
            return  # No L2 structures in this chunk

        # If only 1 structure, create internal anchors around it to build an underground maze
        if len(components) == 1:
            cx, cy = components[0]
            for angle in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
                dist = random.randint(15, 25)
                nx = max(6, min(w - 7, int(cx + math.cos(angle) * dist)))
                ny = max(6, min(h - 7, int(cy + math.sin(angle) * dist)))
                if (nx, ny) != (cx, cy):
                    components.append((nx, ny))

        print(f"L2 Contained Maze: Connecting {len(components)} points inside chunk...")

        # ------------------------------------------------------------------
        # 1. PRIMARY PATHWAYS (Width 4, dirty_01): Guaranteed Spanning Tree Connection
        # ------------------------------------------------------------------
        connected_set = [components[0]]
        unconnected_set = list(components[1:])

        while unconnected_set:
            best_dist = float('inf')
            best_link = None 

            for c_pos in connected_set:
                for i, u_pos in enumerate(unconnected_set):
                    dist = (c_pos[0] - u_pos[0])**2 + (c_pos[1] - u_pos[1])**2
                    if dist < best_dist:
                        best_dist = dist
                        best_link = (c_pos, i)
            
            if best_link is not None:
                start_pos, u_index = best_link
                target_pos = unconnected_set[u_index]
                self._carve_drunkard_path(layers, start_pos, target_pos, path_width=4, path_tile='dirty_01')
                connected_set.append(target_pos)
                unconnected_set.pop(u_index)
            else:
                break

        # ------------------------------------------------------------------
        # 2. SECONDARY DRUNKARD PATHWAY (Width 3, dirty_01): Connected Maze Loops
        # ------------------------------------------------------------------
        if len(components) >= 3:
            for i in range(len(components)):
                c1 = components[i]
                c2 = components[(i + 2) % len(components)]
                if random.random() < 0.75:
                    self._carve_drunkard_path(layers, c1, c2, path_width=3, path_tile='dirty_01')
        elif len(components) == 2:
            self._carve_drunkard_path(layers, components[0], components[1], path_width=3, path_tile='dirty_01')

        num_maze_loops = max(2, len(components))
        for _ in range(num_maze_loops):
            start_comp = random.choice(components)
            angle = random.uniform(0, math.pi * 2)
            dist = random.randint(12, 28)
            mid_x = max(6, min(w - 7, int(start_comp[0] + math.cos(angle) * dist)))
            mid_y = max(6, min(h - 7, int(start_comp[1] + math.sin(angle) * dist)))
            
            end_comp = random.choice(components)
            self._carve_drunkard_path(layers, start_comp, (mid_x, mid_y), path_width=3, path_tile='dirty_01')
            self._carve_drunkard_path(layers, (mid_x, mid_y), end_comp, path_width=3, path_tile='dirty_01')

        # ------------------------------------------------------------------
        # 3. THIRD PATHWAY (Width 2, sand_01): 2-Tile Narrow Walkthrough
        # ------------------------------------------------------------------
        num_narrow = max(2, len(components) // 2 + 1)
        for i in range(num_narrow):
            c1 = components[i % len(components)]
            c2 = components[(i + max(1, len(components) // 2)) % len(components)]
            # [FIX] Carve third pathway strictly with sand_01
            self._carve_drunkard_path(layers, c1, c2, path_width=2, path_tile='sand_01')

    def _carve_drunkard_path(self, layers, start, end, path_width=4, path_tile='dirty_01'):
        """
        Carves a drunkard pathway with support for widths 4, 3, and 2, and selectable path_tile.
        - path_width 2 creates a strictly 2-tile narrow crawlway.
        - Automatically clears walls in the core and walls borders with '@'.
        """
        cx, cy = start
        tx, ty = end
        
        ground = layers['ground']
        base = layers['base']
        h, w = len(ground), len(ground[0])
        
        border_tile = '@'
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}

        if path_width >= 4:
            core_min, core_max = -2, 2
            border_min, border_max = -3, 3
        elif path_width == 3:
            core_min, core_max = -1, 2
            border_min, border_max = -2, 3
        else:  # path_width == 2 (strictly 2 tiles narrow)
            core_min, core_max = 0, 2
            border_min, border_max = -1, 3
        
        max_steps = (abs(tx - cx) + abs(ty - cy)) * 6 + 40
        steps = 0
        
        while (cx != tx or cy != ty) and steps < max_steps:
            steps += 1
            
            for dy in range(border_min, border_max):
                for dx in range(border_min, border_max):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        is_core = (core_min <= dx < core_max and core_min <= dy < core_max)
                        
                        if is_core:
                            current_tile = ground[ny][nx]
                            if current_tile in [' ', border_tile, '#']:
                                ground[ny][nx] = path_tile
                                if base[ny][nx] in ['@', '#', ' '] or (defs.get(base[ny][nx], {}).get('is_obstacle', False) and base[ny][nx] != '@'):
                                    base[ny][nx] = ' '
                        else:
                            if ground[ny][nx] in [' ', '#']:
                                ground[ny][nx] = border_tile
            
            # Biased random walk towards target
            dist_x = tx - cx
            dist_y = ty - cy
            choice = random.random()
            
            if choice < 0.45 and dist_x != 0:
                dx_step = 1 if dist_x > 0 else -1
                dy_step = 0
            elif choice < 0.90 and dist_y != 0:
                dx_step = 0
                dy_step = 1 if dist_y > 0 else -1
            else:
                if random.random() < 0.5:
                    dx_step = random.choice([-1, 1])
                    dy_step = 0
                else:
                    dx_step = 0
                    dy_step = random.choice([-1, 1])

            cx += dx_step
            cy += dy_step
            
            # Keep paths contained safely inside the chunk
            cx = max(4, min(w - 5, cx))
            cy = max(4, min(h - 5, cy))
            
            if abs(cx - tx) <= 1 and abs(cy - ty) <= 1:
                break

    def _apply_l2_border(self, layers, tx, ty, tmpl_w, tmpl_h, mw, mh):
        ground = layers.get('ground_L2')
        if not ground: return
        
        padding = 4
        border_tile = '@'
        padding_tile = 'dirty_01'
        
        x1 = max(0, tx - padding)
        y1 = max(0, ty - padding)
        x2 = min(mw, tx + tmpl_w + padding)
        y2 = min(mh, ty + tmpl_h + padding)
        
        for y in range(y1, y2):
            for x in range(x1, x2):
                if not (tx <= x < tx + tmpl_w and ty <= y < ty + tmpl_h):
                    if ground[y][x] == ' ':
                        is_border = False
                        if x == x1 or x == x2 - 1 or y == y1 or y == y2 - 1:
                            is_border = True
                        
                        if is_border:
                            ground[y][x] = border_tile
                        else:
                            ground[y][x] = padding_tile