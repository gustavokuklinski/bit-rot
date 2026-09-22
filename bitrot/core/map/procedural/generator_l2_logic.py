# core/map/procedural/generator_l2_logic.py

import math
import random
import core.data.config
from core.data.config import *

class ProceduralGeneratorL2:
    def _populate_l2_spawns(self, layers):
        ground = layers.get('ground')
        base = layers.get('base')
        spawn = layers.get('spawn')
        
        if not ground or not base or not spawn: return
        
        h = len(ground)
        w = len(ground[0])
        cx, cy = w // 2, h // 2
        
        pathway_candidates = []
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}

        for y in range(4, h - 4):
            for x in range(4, w - 4):
                if (y < 6 or y >= h - 6) and abs(x - cx) <= 3: continue
                if (x < 6 or x >= w - 6) and abs(y - cy) <= 3: continue

                base_tile = base[y][x]
                ground_tile = ground[y][x]
                spawn_tile = spawn[y][x]

                if base_tile != ' ': continue
                if base_tile in ['@', '#']: continue
                if base_tile in defs and defs[base_tile].get('is_obstacle', False): continue

                if ground_tile in ['@', '#', ' ', '']: continue
                if ground_tile in defs and defs[ground_tile].get('is_obstacle', False): continue

                if spawn_tile != ' ': continue

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
                if 'dirty' in g_char or 'asphalt' in g_char or 'path' in g_char or 'cave_l2' in g_char or 'sand' in g_char:
                    pathway_candidates.append((x, y))

        chunks_x = max(1, w // self.chunk_size)
        chunks_y = max(1, h // self.chunk_size)
        total_chunks = max(1, chunks_x * chunks_y)
        zombie_max = getattr(core.data.config, 'ZOMBIE_MAX_CHUNK', 6)
        total_zombies = zombie_max * total_chunks

        chosen = []
        if pathway_candidates and total_zombies > 0:
            count = min(len(pathway_candidates), total_zombies)
            chosen = random.sample(pathway_candidates, count)
            for (zx, zy) in chosen:
                spawn[zy][zx] = 'Z'
                
        print(f"  > Spawning Report L2: {len(chosen)} Zombies on Pathways (Map Limit: {total_zombies}).")

    def _decorate_l2_pathways(self, layers, mask):
        ground = layers.get('ground')
        base = layers.get('base')
        if not ground or not base: return

        h = len(ground)
        w = len(ground[0])
        veg_options = ['garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_stone', 'garden_tree_11', 'garden_tall_grass', 'garden_stone_powder', 'garden_stone_iron']

        for y in range(h):
            for x in range(w):
                if ground[y][x] in ['dirty_01', 'sand_01'] and base[y][x] == ' ' and mask[y][x] == 0:
                    if random.random() < 0.15:
                        base[y][x] = random.choice(veg_options)

    def _enforce_l2_contained_borders(self, layers, w, h, conns_l2=None):
        """
        Enforces Layer 2 boundaries with guaranteed 4-tile wide safe passages
        without overwriting or modifying any protected building tiles.
        """
        ground = layers.get('ground')
        base = layers.get('base')
        protected = layers.get('protected_mask')
        if not ground or not base: return

        border_tile = '@'
        path_tile = 'dirty_01'
        cx, cy = w // 2, h // 2
        conn_depth = 5
        c_min, c_max = -2, 2

        conns = conns_l2 or {}

        # 1. Open 4-tile wide safe passages on boundaries where L2 connects
        if conns.get('top'):
            for y in range(conn_depth):
                for x in range(max(0, cx + c_min), min(w, cx + c_max)):
                    if protected and protected[y][x] == 1: continue
                    ground[y][x] = path_tile
                    base[y][x] = ' '

        if conns.get('bottom'):
            for y in range(h - conn_depth, h):
                for x in range(max(0, cx + c_min), min(w, cx + c_max)):
                    if protected and protected[y][x] == 1: continue
                    ground[y][x] = path_tile
                    base[y][x] = ' '

        if conns.get('left'):
            for x in range(conn_depth):
                for y in range(max(0, cy + c_min), min(h, cy + c_max)):
                    if protected and protected[y][x] == 1: continue
                    ground[y][x] = path_tile
                    base[y][x] = ' '

        if conns.get('right'):
            for x in range(w - conn_depth, w):
                for y in range(max(0, cy + c_min), min(h, cy + c_max)):
                    if protected and protected[y][x] == 1: continue
                    ground[y][x] = path_tile
                    base[y][x] = ' '

        # 2. Seal the outer perimeter everywhere EXCEPT in doorways and protected buildings
        for y in range(h):
            for x in range(w):
                # Never overwrite protected building walls or floors
                if protected and protected[y][x] == 1:
                    continue

                is_doorway = False
                if conns.get('top') and y < conn_depth and (cx + c_min <= x < cx + c_max):
                    is_doorway = True
                elif conns.get('bottom') and y >= h - conn_depth and (cx + c_min <= x < cx + c_max):
                    is_doorway = True
                elif conns.get('left') and x < conn_depth and (cy + c_min <= y < cy + c_max):
                    is_doorway = True
                elif conns.get('right') and x >= w - conn_depth and (cy + c_min <= y < cy + c_max):
                    is_doorway = True

                if not is_doorway:
                    if x < 2 or x >= w - 2 or y < 2 or y >= h - 2:
                        base[y][x] = border_tile
                        if ground[y][x] == ' ':
                            ground[y][x] = 'cave_floor_01' if 'cave_floor_01' in ground[y][x] else 'dirty_01'

    def _connect_l2_drunkards(self, layers, conns_l2=None):
        """
        Connects L2 structures to doorway exits without ever carving through buildings.
        """
        ground = layers.get('ground')
        base = layers.get('base')
        protected = layers.get('protected_mask')
        if not ground or not base: return

        h = len(ground)
        w = len(ground[0])
        cx, cy = w // 2, h // 2
        
        visited = set()
        components = []

        # Find existing underground structures and select connection points at their perimeters
        for y in range(h):
            for x in range(w):
                if (x, y) not in visited and ground[y][x] not in [' ', '@', '#']:
                    stack = [(x, y)]
                    visited.add((x, y))
                    island_pixels = []
                    while stack:
                        cur_x, cur_y = stack.pop()
                        island_pixels.append((cur_x, cur_y))
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nx, ny = cur_x + dx, cur_y + dy
                            if 0 <= nx < w and 0 <= ny < h:
                                if (nx, ny) not in visited and ground[ny][nx] not in [' ', '@', '#']:
                                    visited.add((nx, ny))
                                    stack.append((nx, ny))

                    if island_pixels and len(island_pixels) >= 4:
                        # Find a perimeter entrance point bordering outside space so we connect to the door
                        entrance_point = None
                        for px, py in island_pixels:
                            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                                nx, ny = px + dx, py + dy
                                if 0 <= nx < w and 0 <= ny < h:
                                    if (not protected or protected[ny][nx] == 0) and ground[ny][nx] in [' ', '@', '#']:
                                        entrance_point = (nx, ny)
                                        break
                            if entrance_point:
                                break

                        if not entrance_point:
                            avg_x = sum(p[0] for p in island_pixels) // len(island_pixels)
                            avg_y = sum(p[1] for p in island_pixels) // len(island_pixels)
                            entrance_point = (avg_x, avg_y)

                        components.append(entrance_point)

        conns = conns_l2 or {}
        doorway_points = []
        if conns.get('top'): doorway_points.append((cx, 4))
        if conns.get('bottom'): doorway_points.append((cx, h - 5))
        if conns.get('left'): doorway_points.append((4, cy))
        if conns.get('right'): doorway_points.append((w - 5, cy))

        if not components:
            components.append((cx, cy))

        for dp in doorway_points:
            if dp not in components:
                components.append(dp)

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

        if len(components) >= 3:
            for i in range(len(components)):
                c1 = components[i]
                c2 = components[(i + 2) % len(components)]
                if random.random() < 0.65:
                    self._carve_drunkard_path(layers, c1, c2, path_width=4, path_tile='dirty_01')

    def _carve_drunkard_path(self, layers, start, end, path_width=4, path_tile='dirty_01'):
        """
        Carves a 4-tile wide safe pathway. Protects all building tiles from being altered.
        """
        cx, cy = start
        tx, ty = end
        
        ground = layers['ground']
        base = layers['base']
        protected = layers.get('protected_mask')
        h, w = len(ground), len(ground[0])
        
        border_tile = '@'
        core_min, core_max = -2, 2
        border_min, border_max = -3, 3
        
        max_steps = (abs(tx - cx) + abs(ty - cy)) * 6 + 40
        steps = 0
        
        while (cx != tx or cy != ty) and steps < max_steps:
            steps += 1
            
            for dy in range(border_min, border_max):
                for dx in range(border_min, border_max):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        # NEVER overwrite or clear any part of an L2 building
                        if protected and protected[ny][nx] == 1:
                            continue

                        is_core = (core_min <= dx < core_max and core_min <= dy < core_max)
                        
                        if is_core:
                            current_tile = ground[ny][nx]
                            if current_tile in [' ', border_tile, '#']:
                                ground[ny][nx] = path_tile
                            if base[ny][nx] != ' ':
                                base[ny][nx] = ' '
                        else:
                            if ground[ny][nx] in [' ', '#']:
                                ground[ny][nx] = border_tile
            
            dist_x = tx - cx
            dist_y = ty - cy
            choice = random.random()
            
            if choice < 0.50 and dist_x != 0:
                dx_step = 1 if dist_x > 0 else -1
                dy_step = 0
            elif choice < 0.95 and dist_y != 0:
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
            
            cx = max(3, min(w - 4, cx))
            cy = max(3, min(h - 4, cy))
            
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