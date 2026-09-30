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
                if 'dirty' in g_char or 'asphalt' in g_char or 'path' in g_char or 'cave' in g_char or 'sand' in g_char:
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

    def _decorate_l2_pathways(self, layers, w, h, conns_l2=None):
        """
        Scatters requested decorations along L2 and L3 pathways:
        - Walkable grass: garden_grass_1, garden_grass_2, garden_grass_3, garden_tall_grass
        - Obstacle stones: garden_stone, garden_stone_iron, garden_stone_powder
        Ensures obstacle stones only hug cave walls and never obstruct doorways, building margins, or corridors.
        """
        ground = layers.get('ground')
        base = layers.get('base')
        protected = layers.get('protected_mask')
        spawn = layers.get('spawn')
        if not ground or not base: return

        cx, cy = w // 2, h // 2
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}

        walkable_decos = ['garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']
        stone_decos = ['garden_stone', 'garden_stone_iron', 'garden_stone_powder']

        placed_stone_coords = set()

        def is_connector_or_doorway_zone(x, y):
            if (y < 7 or y >= h - 7) and abs(x - cx) <= 4: return True
            if (x < 7 or x >= w - 7) and abs(y - cy) <= 4: return True

            # Never place obstacle decorations inside or near protected buildings
            if protected:
                for dy in range(-3, 4):
                    for dx in range(-3, 4):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and protected[ny][nx] == 1:
                            return True
            return False

        for y in range(4, h - 4):
            for x in range(4, w - 4):
                if is_connector_or_doorway_zone(x, y):
                    continue

                if base[y][x] != ' ':
                    continue

                if spawn and spawn[y][x] != ' ':
                    continue

                g_tile = ground[y][x]
                if g_tile in (' ', '@', '#') or 'water' in g_tile.lower():
                    continue

                if not (g_tile.startswith('dirty') or g_tile.startswith('cave') or g_tile.startswith('sand') or g_tile.startswith('asphalt')):
                    continue

                roll = random.random()
                if roll < 0.08:
                    base[y][x] = random.choice(walkable_decos)
                    continue

                elif roll < 0.12:
                    chosen_stone = random.choice(stone_decos)
                    tile_def = defs.get(chosen_stone, {})
                    is_stone_obstacle = tile_def.get('is_obstacle', True)

                    if is_stone_obstacle:
                        has_wall_neighbor = False
                        wall_dir = None
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < w and 0 <= ny < h and base[ny][nx] == '@':
                                has_wall_neighbor = True
                                wall_dir = (dx, dy)
                                break

                        if not has_wall_neighbor:
                            continue

                        opp_dx, opp_dy = -wall_dir[0], -wall_dir[1]
                        c1_x, c1_y = x + opp_dx, y + opp_dy
                        c2_x, c2_y = x + (opp_dx * 2), y + (opp_dy * 2)

                        if not (0 <= c1_x < w and 0 <= c1_y < h and 0 <= c2_x < w and 0 <= c2_y < h):
                            continue

                        if base[c1_y][c1_x] != ' ' or base[c2_y][c2_x] != ' ':
                            continue

                        if ground[c1_y][c1_x] in (' ', '@', '#') or ground[c2_y][c2_x] in (' ', '@', '#'):
                            continue

                        too_close_stone = False
                        for sx, sy in placed_stone_coords:
                            if abs(x - sx) + abs(y - sy) < 3:
                                too_close_stone = True
                                break

                        if too_close_stone:
                            continue

                        base[y][x] = chosen_stone
                        placed_stone_coords.add((x, y))
                    else:
                        base[y][x] = chosen_stone

    def _enforce_l2_contained_borders(self, layers, w, h, conns_l2=None):
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

        for y in range(h):
            for x in range(w):
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
        ground = layers.get('ground')
        base = layers.get('base')
        protected = layers.get('protected_mask')
        if not ground or not base: return

        h = len(ground)
        w = len(ground[0])
        cx, cy = w // 2, h // 2
        
        visited = set()
        components = []

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
                        # Never overwrite or carve through the building template
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
                                ground[ny][nx] = path_tile
                                base[ny][nx] = border_tile
            
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

    def _apply_l2_border(self, layers, tx, ty, tmpl_w, tmpl_h, mw, mh, suffix='_L2', margin=4):
        """
        Creates an open, walkable 4-tile floor margin around Cave, Dungeon, Bunker, and L2/L3 templates.
        The margin is cleared so incoming cave tunnels connect seamlessly without any blocking wall '@'.
        """
        ground_lx = layers.get('ground' + suffix)
        base_lx = layers.get('base' + suffix)
        if not ground_lx or not base_lx: return

        padding_tile = 'dirty_01'
        
        x1 = max(0, tx - margin)
        y1 = max(0, ty - margin)
        x2 = min(mw, tx + tmpl_w + margin)
        y2 = min(mh, ty + tmpl_h + margin)

        for y in range(y1, y2):
            for x in range(x1, x2):
                if not (tx <= x < tx + tmpl_w and ty <= y < ty + tmpl_h):
                    ground_lx[y][x] = padding_tile
                    # Keep base completely open so no wall '@' blocks the entrance or margin
                    base_lx[y][x] = ' '