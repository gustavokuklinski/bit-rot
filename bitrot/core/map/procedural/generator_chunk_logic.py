# core/map/procedural/generator_chunk_logic.py

import math
import random
import pygame
import core.data.config
from core.data.config import *

class ProceduralGeneratorChunk:

    def _generate_confusing_asphalt_maze(self, layers, occupied_mask, w, h, cx, cy):
        road_tile = 'dirty_01'
        road_width = 2
        num_arms = random.randint(2, 4)
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        def is_area_beach_free(x, y, rw):
            for ox in range(-rw // 2, rw // 2 + 1):
                for oy in range(-rw // 2, rw // 2 + 1):
                    tx, ty = x + ox, y + oy
                    if 0 <= tx < w and 0 <= ty < h:
                        ground = layers['ground'][ty][tx]
                        if ground == getattr(self, 'sand_tile', 'sand_01') or \
                           ground == getattr(self, 'water_tile', 'water_01'):
                            return False
                    else:
                        return False
            return True

        def paint_wide_segment(x1, y1, x2, y2):
            steps = max(abs(x2 - x1), abs(y2 - y1))
            if steps == 0: return
            dx = (x2 - x1) / steps
            dy = (y2 - y1) / steps
            for i in range(steps + 1):
                curr_x = int(x1 + dx * i)
                curr_y = int(y1 + dy * i)
                for ox in range(-road_width // 2, road_width // 2 + 1):
                    for oy in range(-road_width // 2, road_width // 2 + 1):
                        tx, ty = curr_x + ox, curr_y + oy
                        if 0 <= tx < w and 0 <= ty < h:
                            if not self._is_in_connector_zone_internal(tx, ty, w, h, cx, cy):
                                layers['ground'][ty][tx] = road_tile
                                occupied_mask[ty][tx] = 1

        for _ in range(num_arms):
            curr_x, curr_y = cx, cy
            num_segments = random.randint(2, 4)
            for _ in range(num_segments):
                direction = random.choice(directions)
                dx, dy = direction
                length = random.randint(6, 14)
                target_x = curr_x + (dx * length)
                target_y = curr_y + (dy * length)
                can_paint = True
                for step in range(length + 1):
                    check_x = curr_x + (dx * step)
                    check_y = curr_y + (dy * step)
                    if not is_area_beach_free(check_x, check_y, road_width):
                        can_paint = False
                        break
                if can_paint:
                    paint_wide_segment(curr_x, curr_y, target_x, target_y)
                    curr_x, curr_y = target_x, target_y
                else:
                    break

    def _is_in_connector_zone_internal(self, tx, ty, w, h, cx, cy):
        depth = 5
        radius = 3
        if ty < depth and abs(tx - cx) <= radius: return True
        if ty >= h - depth and abs(tx - cx) <= radius: return True
        if tx < depth and abs(ty - cy) <= radius: return True
        if tx >= w - depth and abs(ty - cy) <= radius: return True
        return False

    def _resolve_boat_char(self):
        if hasattr(self.game, 'tile_manager') and hasattr(self.game.tile_manager, 'definitions'):
            for char, defn in self.game.tile_manager.definitions.items():
                if char in ('tp_boat', 'teleport_boat') or defn.get('type') == 'maptile_teleport' or defn.get('name') in ('tp_boat', 'teleport_boat'):
                    return char
        return 'tp_boat'

    def _generate_lobby_chunk(self, gx, gy, w, h):
        boat_char = self._resolve_boat_char()
        water_tile = getattr(self, 'water_tile', 'water_01')

        layers = {
            'base': [[' ' for _ in range(w)] for _ in range(h)],
            'ground': [[water_tile for _ in range(w)] for _ in range(h)],
            'spawn': [[' ' for _ in range(w)] for _ in range(h)],
            'roof': [[' ' for _ in range(w)] for _ in range(h)],
            'light': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask': [[0 for _ in range(w)] for _ in range(h)],
            'base_L2': [['@' for _ in range(w)] for _ in range(h)],
            'ground_L2': [['dirty_01' for _ in range(w)] for _ in range(h)],
            'spawn_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'roof_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'light_L2': [[' ' for _ in range(w)] for _ in range(h)],
        }

        lobby_name = getattr(self, 'lobby_template', None)
        if not lobby_name:
            for k in self.templates.keys():
                if 'lobby' in k.lower():
                    lobby_name = k
                    break

        tmpl = self.templates.get(lobby_name) if lobby_name else None
        tx, ty = w // 2 - 15, h // 2 - 15
        tw, th = 30, 30

        if tmpl:
            tw, th = tmpl['width'], tmpl['height']
            tx = max(4, (w - tw) // 2)
            ty = max(4, (h - th) // 2)
            self._blit_template(layers, tmpl, tx, ty, w, h, clear_base=True)
        else:
            for dy in range(th):
                for dx in range(tw):
                    layers['ground'][ty + dy][tx + dx] = 'house_floor_01'

        for y in range(h):
            for x in range(w):
                sp = layers['spawn'][y][x]
                if sp in ('SNPC', 'NPC', 'Z', 'ANM'):
                    layers['spawn'][y][x] = ' '

        boat_coords = None
        for y in range(h):
            for x in range(w):
                if layers['base'][y][x] in (boat_char, 'tp_boat', 'teleport_boat'):
                    boat_coords = (x, y)
                    layers['base'][y][x] = boat_char
                    break
            if boat_coords:
                break

        if not boat_coords:
            for dy in range(-2, th + 2):
                for dx in range(-2, tw + 2):
                    bx = tx + dx
                    by = ty + dy
                    if 0 <= bx < w and 0 <= by < h:
                        if layers['ground'][by][bx] == water_tile and layers['base'][by][bx] == ' ':
                            has_land_adj = False
                            for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                nx, ny = bx + ox, by + oy
                                if 0 <= nx < w and 0 <= ny < h:
                                    if layers['ground'][ny][nx] != water_tile and layers['base'][ny][nx] == ' ':
                                        has_land_adj = True
                                        break
                            if has_land_adj:
                                layers['base'][by][bx] = boat_char
                                layers['spawn'][by][bx] = ' '
                                boat_coords = (bx, by)
                                break
                if boat_coords:
                    break

        # Set player spawn 'P' for Lobby
        if boat_coords:
            bx, by = boat_coords
            candidates = []
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    cx_tile = bx + dx
                    cy_tile = by + dy
                    if 0 <= cx_tile < w and 0 <= cy_tile < h:
                        dist = math.hypot(dx, dy)
                        if 1.4 <= dist <= 2.8:
                            if layers['ground'][cy_tile][cx_tile] != water_tile and layers['base'][cy_tile][cx_tile] == ' ':
                                candidates.append((abs(dist - 2.0), cx_tile, cy_tile))

            if candidates:
                candidates.sort(key=lambda c: c[0])
                px, py = candidates[0][1], candidates[0][2]
                layers['spawn'][py][px] = 'P'
            else:
                layers['spawn'][ty + th // 2][tx + tw // 2] = 'P'

        return layers

    def _place_single_teleport_boat(self, layers, w, h):
        boat_char = self._resolve_boat_char()
        for y in range(h):
            for x in range(w):
                if layers['base'][y][x] in (boat_char, 'tp_boat', 'teleport_boat'):
                    return

        cx, cy = w // 2, h // 2
        for y in range(2, h - 2):
            for x in range(2, w - 2):
                if self._is_in_connector_zone_internal(x, y, w, h, cx, cy):
                    continue
                g_tile = layers['ground'][y][x].lower()
                b_tile = layers['base'][y][x]
                if 'water' in g_tile and b_tile in (' ', ''):
                    layers['base'][y][x] = boat_char
                    layers['spawn'][y][x] = ' '
                    return

    def _place_port_at_shore(self, layers, occupied_mask, placed_rects, w, h, coast_left, coast_right, coast_top, coast_bottom, draw_secondary_maze_road):
        """Places Port_L1 at the shore, places boat, and marks player teleport spawn 'P2' on the sand tile."""
        port_name = getattr(self, 'port_template', None)
        if not port_name or port_name not in self.templates:
            for k in ['Port_L1', 'Port_01', 'port_l1', 'port_01', 'Port', 'port']:
                if k in self.templates:
                    port_name = k
                    break
        if not port_name or port_name not in self.templates:
            for k in self.templates.keys():
                if 'port' in k.lower():
                    port_name = k
                    break

        port_tmpl = self.templates.get(port_name) if port_name else None
        if not port_tmpl:
            self._place_single_teleport_boat(layers, w, h)
            return

        pw, ph = port_tmpl['width'], port_tmpl['height']
        cx, cy = w // 2, h // 2

        available_coasts = []
        if coast_bottom: available_coasts.append('bottom')
        if coast_top: available_coasts.append('top')
        if coast_left: available_coasts.append('left')
        if coast_right: available_coasts.append('right')
        if not available_coasts:
            available_coasts = ['bottom', 'top', 'left', 'right']

        random.shuffle(available_coasts)

        best_candidate = None
        best_score = -999999
        chosen_side = available_coasts[0]

        for side in available_coasts:
            if side == 'bottom':
                ty_min, ty_max = max(2, h - ph - 6), max(2, h - ph - 1)
                tx_min, tx_max = 6, max(7, w - pw - 6)
            elif side == 'top':
                ty_min, ty_max = 1, min(h - ph - 2, 6)
                tx_min, tx_max = 6, max(7, w - pw - 6)
            elif side == 'left':
                tx_min, tx_max = 1, min(w - pw - 2, 6)
                ty_min, ty_max = 6, max(7, h - ph - 6)
            else:  # right
                tx_min, tx_max = max(2, w - pw - 6), max(2, w - pw - 1)
                ty_min, ty_max = 6, max(7, h - ph - 6)

            for _ in range(40):
                tx = random.randint(tx_min, tx_max)
                ty = random.randint(ty_min, ty_max)

                collides_conn = False
                for ry in range(ty, ty + ph):
                    for rx in range(tx, tx + pw):
                        if self._is_in_connector_zone_internal(rx, ry, w, h, cx, cy):
                            collides_conn = True
                            break
                    if collides_conn: break
                if collides_conn: continue

                p_rect = pygame.Rect(tx, ty, pw, ph)
                if any(p_rect.colliderect(pr) for pr in placed_rects):
                    continue

                water_count = 0
                land_count = 0
                for ry in range(ty, ty + ph):
                    for rx in range(tx, tx + pw):
                        gt = layers['ground'][ry][rx].lower()
                        if 'water' in gt:
                            water_count += 1
                        else:
                            land_count += 1

                score = 0
                if water_count > 0 and land_count > 0:
                    score = 2000 - abs(water_count - land_count)
                elif water_count > 0:
                    score = 100 + water_count
                elif land_count > 0:
                    score = 50 + land_count

                if score > best_score:
                    best_score = score
                    best_candidate = (tx, ty)
                    chosen_side = side

        if not best_candidate:
            tx = max(4, min(w - pw - 4, cx - pw // 2))
            ty = max(4, min(h - ph - 4, h - ph - 6))
            best_candidate = (tx, ty)

        tx, ty = best_candidate
        
        # 1. Blit Port template clearing base layer obstacles
        self._blit_template(layers, port_tmpl, tx, ty, w, h, clear_base=True)
        
        port_rect = pygame.Rect(tx, ty, pw, ph)
        placed_rects.append(port_rect)

        # 2. Protect Port_L1 from decoration overlays
        for ry in range(ty, ty + ph):
            for rx in range(tx, tx + pw):
                if 0 <= rx < w and 0 <= ry < h:
                    occupied_mask[ry][rx] = 1
                    layers['protected_mask'][ry][rx] = 1
                    if layers['base'][ry][rx] == '@':
                        layers['base'][ry][rx] = ' '

        # 3. Ensure boat tile is present
        boat_char = self._resolve_boat_char()
        has_boat = False
        boat_pos = None
        for ry in range(ty, ty + ph):
            for rx in range(tx, tx + pw):
                if 0 <= rx < w and 0 <= ry < h:
                    b_tile = layers['base'][ry][rx]
                    g_tile = layers['ground'][ry][rx]
                    if b_tile in (boat_char, 'tp_boat', 'teleport_boat') or g_tile in (boat_char, 'tp_boat', 'teleport_boat'):
                        has_boat = True
                        boat_pos = (rx, ry)
                        layers['base'][ry][rx] = boat_char
                        layers['spawn'][ry][rx] = ' '
                        break
            if has_boat: break

        if not has_boat:
            water_tile = getattr(self, 'water_tile', 'water_01')
            for ry in range(max(0, ty - 2), min(h, ty + ph + 2)):
                for rx in range(max(0, tx - 2), min(w, tx + pw + 2)):
                    if layers['ground'][ry][rx] == water_tile and layers['base'][ry][rx] == ' ':
                        layers['base'][ry][rx] = boat_char
                        layers['spawn'][ry][rx] = ' '
                        has_boat = True
                        boat_pos = (rx, ry)
                        break
                if has_boat: break

        # 4. Find the walkable sand tile at Port_L1 and set spawn marker 'P2'
        sand_tile_type = getattr(self, 'sand_tile', 'beach_sand_01')
        ref_x = boat_pos[0] if boat_pos else (tx + pw // 2)
        ref_y = boat_pos[1] if boat_pos else (ty + ph // 2)

        sand_candidates = []
        for ry in range(max(0, ty - 3), min(h, ty + ph + 3)):
            for rx in range(max(0, tx - 3), min(w, tx + pw + 3)):
                gt = layers['ground'][ry][rx].lower()
                bt = layers['base'][ry][rx]
                if ('sand' in gt or 'beach' in gt) and bt == ' ':
                    d = math.hypot(rx - ref_x, ry - ref_y)
                    sand_candidates.append((d, rx, ry))

        if sand_candidates:
            sand_candidates.sort(key=lambda c: c[0])
            chosen_sand = (sand_candidates[0][1], sand_candidates[0][2])
        else:
            if chosen_side == 'bottom':
                chosen_sand = (tx + pw // 2, max(2, ty - 1))
            elif chosen_side == 'top':
                chosen_sand = (tx + pw // 2, min(h - 3, ty + ph))
            elif chosen_side == 'left':
                chosen_sand = (min(w - 3, tx + pw), ty + ph // 2)
            else:
                chosen_sand = (max(2, tx - 1), ty + ph // 2)
            layers['ground'][chosen_sand[1]][chosen_sand[0]] = sand_tile_type
            layers['base'][chosen_sand[1]][chosen_sand[0]] = ' '

        # Clear any old P or P2 in this chunk, and stamp 'P2' on the sand tile at Port_L1
        for y in range(h):
            for x in range(w):
                if layers['spawn'][y][x] in ('P', 'P2'):
                    layers['spawn'][y][x] = ' '

        layers['spawn'][chosen_sand[1]][chosen_sand[0]] = 'P2'

        # 5. Connect a pathway from the inland entrance of Port_L1 to the chunk road network
        if chosen_side == 'bottom':
            ent_x = max(2, min(w - 3, tx + pw // 2))
            ent_y = max(2, ty - 1)
        elif chosen_side == 'top':
            ent_x = max(2, min(w - 3, tx + pw // 2))
            ent_y = min(h - 3, ty + ph)
        elif chosen_side == 'left':
            ent_x = min(w - 3, tx + pw)
            ent_y = max(2, min(h - 3, ty + ph // 2))
        else:  # right
            ent_x = max(2, tx - 1)
            ent_y = max(2, min(h - 3, ty + ph // 2))

        draw_secondary_maze_road(ent_x, ent_y, cx, cy, 'dirty_01', path_width=2)

    def _generate_chunk_data(self, gx, gy, conns, is_start=False, assigned_templates=None, assigned_l2_templates=None, allow_buildings=True, force_forest=False, cell_w=None, cell_h=None, coast_left=False, coast_right=False, coast_top=False, coast_bottom=False, conns_l2=None):
        w = cell_w if cell_w is not None else 128
        h = cell_h if cell_h is not None else 128

        cx, cy = w // 2, h // 2
        connector_depth = 5
        connector_radius = 3

        def is_in_connector_zone(tx, ty):
            if conns['top'] and ty < connector_depth and abs(tx - cx) <= connector_radius:
                return True
            if conns['bottom'] and ty >= h - connector_depth and abs(tx - cx) <= connector_radius:
                return True
            if conns['left'] and tx < connector_depth and abs(ty - cy) <= connector_radius:
                return True
            if conns['right'] and tx >= w - connector_depth and abs(ty - cy) <= connector_radius:
                return True
            return False

        layers = {
            'base': [[' ' for _ in range(w)] for _ in range(h)],
            'ground': [['bg_grass' for _ in range(w)] for _ in range(h)],
            'spawn': [[' ' for _ in range(w)] for _ in range(h)],
            'roof': [[' ' for _ in range(w)] for _ in range(h)],
            'light': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask': [[0 for _ in range(w)] for _ in range(h)],
            
            # L2 Layers
            'base_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'ground_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'spawn_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'roof_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'light_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask_L2': [[0 for _ in range(w)] for _ in range(h)]
        }
        occupied_mask = [[0 for _ in range(w)] for _ in range(h)]
        occupied_mask_L2 = [[0 for _ in range(w)] for _ in range(h)]

        placed_rects = []
        road_tile = 'asphalt_01'
        dirt_tile = 'dirty_01'
        sand_tile = getattr(self, 'sand_tile', 'sand_01')

        def carve_straight_segment(x1, y1, x2, y2, tile_type, path_width=4):
            if path_width >= 4:
                r_min, r_max = -2, 2
            elif path_width == 3:
                r_min, r_max = -1, 2
            elif path_width == 2:
                r_min, r_max = -1, 1
            else:
                r_min, r_max = 0, 1

            cur_x, cur_y = x1, y1
            pts = [(cur_x, cur_y)]
            while cur_x != x2 or cur_y != y2:
                if cur_x < x2: cur_x += 1
                elif cur_x > x2: cur_x -= 1
                if cur_y < y2: cur_y += 1
                elif cur_y > y2: cur_y -= 1
                pts.append((cur_x, cur_y))

            for px, py in pts:
                for oy in range(r_min, r_max):
                    for ox in range(r_min, r_max):
                        gx_pos, gy_pos = px + ox, py + oy
                        if 0 <= gx_pos < w and 0 <= gy_pos < h:
                            layers['ground'][gy_pos][gx_pos] = tile_type
                            layers['base'][gy_pos][gx_pos] = ' '
                            occupied_mask[gy_pos][gx_pos] = 1

        def draw_secondary_maze_road(start_x, start_y, target_x, target_y, tile_type=dirt_tile, path_width=None):
            if path_width is None:
                path_width = 4 if tile_type == road_tile else 2
                
            current_x, current_y = start_x, start_y
            path = [(current_x, current_y)]
            
            if tile_type == road_tile:
                while current_x != target_x:
                    current_x += 1 if target_x > current_x else -1
                    if any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                        break
                    path.append((current_x, current_y))
                
                if not any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                    while current_y != target_y:
                        current_y += 1 if target_y > current_y else -1
                        if any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                            break
                        path.append((current_x, current_y))
            else:
                steps = 0
                max_steps = w * 6
                while steps < max_steps:
                    steps += 1
                    if not (0 <= current_x < w and 0 <= current_y < h): break
                    if any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                        break
                    if layers['ground'][current_y][current_x] == tile_type and steps > 5: break 
                    if layers['ground'][current_y][current_x] == getattr(self, 'water_tile', 'water_01'): break 

                    if math.hypot(target_x - current_x, target_y - current_y) < 2: break

                    moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    valid_moves = []
                    for dx, dy in moves:
                        nx, ny = current_x + dx, current_y + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            if layers['base'][ny][nx] == ' ' and layers['ground'][ny][nx] != getattr(self, 'water_tile', 'water_01'):
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
                if path_width >= 4:
                    r_min, r_max = -2, 2
                elif path_width == 3:
                    r_min, r_max = -1, 2
                elif path_width == 2:
                    r_min, r_max = -1, 1
                else:
                    r_min, r_max = 0, 1

                for oy in range(r_min, r_max):
                    for ox in range(r_min, r_max):
                        gx_pos, gy_pos = px + ox, py + oy
                        if 0 <= gx_pos < w and 0 <= gy_pos < h:
                            if any(pr.collidepoint(gx_pos, gy_pos) for pr in placed_rects):
                                continue
                            if layers['base'][gy_pos][gx_pos] == ' ' and layers['ground'][gy_pos][gx_pos] != road_tile:
                                if layers['ground'][gy_pos][gx_pos] != getattr(self, 'water_tile', 'water_01'):
                                    layers['ground'][gy_pos][gx_pos] = tile_type
                                    occupied_mask[gy_pos][gx_pos] = 1

        # 1. Central Hub
        hub_tile = road_tile if not force_forest else dirt_tile
        for y in range(cy-2, cy+3):
            for x in range(cx-2, cx+3):
                layers['ground'][y][x] = hub_tile
                occupied_mask[y][x] = 1

        # 2. Connections with Guaranteed Straight Padding
        lead_in = 4
        if conns['top']:
            conn_type = road_tile if conns['top_type'] == 'asphalt' else (sand_tile if conns['top_type'] == 'sand' else dirt_tile)
            carve_straight_segment(cx, 0, cx, lead_in, conn_type)
            draw_secondary_maze_road(cx, lead_in, cx, cy, conn_type)
            
        if conns['bottom']:
            conn_type = road_tile if conns['bottom_type'] == 'asphalt' else (sand_tile if conns['bottom_type'] == 'sand' else dirt_tile)
            carve_straight_segment(cx, h - 1, cx, h - 1 - lead_in, conn_type)
            draw_secondary_maze_road(cx, h - 1 - lead_in, cx, cy, conn_type)
            
        if conns['left']:
            conn_type = road_tile if conns['left_type'] == 'asphalt' else (sand_tile if conns['left_type'] == 'sand' else dirt_tile)
            carve_straight_segment(0, cy, lead_in, cy, conn_type)
            draw_secondary_maze_road(lead_in, cy, cx, cy, conn_type)
            
        if conns['right']:
            conn_type = road_tile if conns['right_type'] == 'asphalt' else (sand_tile if conns['right_type'] == 'sand' else dirt_tile)
            carve_straight_segment(w - 1, cy, w - 1 - lead_in, cy, conn_type)
            draw_secondary_maze_road(w - 1 - lead_in, cy, cx, cy, conn_type)

        # 3. Border Wall
        border_w = getattr(self, 'forest_border_width', 1)
        for y in range(h):
            for x in range(w):
                if is_in_connector_zone(x, y): continue
                if (x < border_w and coast_left) or (x >= w - border_w and coast_right):
                    continue
                if (y < border_w and coast_top) or (y >= h - border_w and coast_bottom):
                    continue
                if x < border_w or x >= w - border_w or y < border_w or y >= h - border_w:
                    if occupied_mask[y][x] == 0:
                        tile = random.choice(getattr(self, 'forest_tiles', ['wall_stone']))
                        layers['base'][y][x] = tile
                        occupied_mask[y][x] = 1

        # 4. Organic Beach Coastlines
        cw = getattr(self, 'coast_width', 15)
        def get_coast_noise(idx, scale=0.1, amp=4.0):
            q_idx = (idx // 4) * 4
            val = math.sin(q_idx * scale) * amp 
            val += math.sin(q_idx * scale * 2.1) * (amp * 0.5)
            pseudo_random = (math.sin(q_idx * 12.9898) * 43758.5453) % 4.0 - 2.0
            val += pseudo_random
            return int(val)

        tree_chance = 0.05

        if coast_left:
            for y in range(h):
                if is_in_connector_zone(0, y): continue
                global_y = gy * h + y
                offset = get_coast_noise(global_y)
                water_lim = max(4, (cw - 8) + offset)
                sand_lim = max(water_lim + 3, cw + offset)
                for x in range(cw + 8):
                    if x >= w or is_in_connector_zone(x, y): break
                    if layers['ground'][y][x] == road_tile: continue
                    dist = x
                    if dist < water_lim:
                        layers['ground'][y][x] = getattr(self, 'water_tile', 'water_01')
                        layers['base'][y][x] = ' '
                        occupied_mask[y][x] = 1 
                        layers['protected_mask'][y][x] = 1
                    elif dist < sand_lim:
                        if layers['ground'][y][x] != getattr(self, 'water_tile', 'water_01'):
                            layers['ground'][y][x] = getattr(self, 'sand_tile', 'sand_01')
                            layers['base'][y][x] = 'garden_tree_16' if random.random() < tree_chance else ' '
                            occupied_mask[y][x] = 1
                            layers['protected_mask'][y][x] = 1

        if coast_right:
            for y in range(h):
                if is_in_connector_zone(w - 1, y): continue
                global_y = gy * h + y
                offset = get_coast_noise(global_y)
                water_lim = max(4, (cw - 8) + offset)
                sand_lim = max(water_lim + 3, cw + offset)
                min_x = w - (cw + 8)
                for x in range(min_x, w):
                    if x < 0 or is_in_connector_zone(x, y): continue
                    if layers['ground'][y][x] == road_tile: continue
                    dist = w - 1 - x
                    if dist < water_lim:
                        layers['ground'][y][x] = getattr(self, 'water_tile', 'water_01')
                        layers['base'][y][x] = ' '
                        occupied_mask[y][x] = 1 
                        layers['protected_mask'][y][x] = 1
                    elif dist < sand_lim:
                        if layers['ground'][y][x] != getattr(self, 'water_tile', 'water_01'):
                            layers['ground'][y][x] = getattr(self, 'sand_tile', 'sand_01')
                            layers['base'][y][x] = 'garden_tree_16' if random.random() < tree_chance else ' '
                            occupied_mask[y][x] = 1
                            layers['protected_mask'][y][x] = 1

        if coast_top:
            for x in range(w):
                if is_in_connector_zone(x, 0): continue
                global_x = gx * w + x
                offset = get_coast_noise(global_x)
                water_lim = max(4, (cw - 8) + offset)
                sand_lim = max(water_lim + 3, cw + offset)
                for y in range(cw + 8):
                    if y >= h or is_in_connector_zone(x, y): break
                    if layers['ground'][y][x] == road_tile: continue
                    dist = y
                    if dist < water_lim:
                        layers['ground'][y][x] = getattr(self, 'water_tile', 'water_01')
                        layers['base'][y][x] = ' '
                        occupied_mask[y][x] = 1 
                        layers['protected_mask'][y][x] = 1
                    elif dist < sand_lim:
                        if layers['ground'][y][x] != getattr(self, 'water_tile', 'water_01'):
                            layers['ground'][y][x] = getattr(self, 'sand_tile', 'sand_01')
                            layers['base'][y][x] = 'garden_tree_16' if random.random() < tree_chance else ' '
                            occupied_mask[y][x] = 1
                            layers['protected_mask'][y][x] = 1

        if coast_bottom:
            for x in range(w):
                if is_in_connector_zone(x, h - 1): continue
                global_x = gx * w + x
                offset = get_coast_noise(global_x)
                water_lim = max(4, (cw - 8) + offset)
                sand_lim = max(water_lim + 3, cw + offset)
                min_y = h - (cw + 8)
                for y in range(min_y, h):
                    if y < 0 or is_in_connector_zone(x, y): continue
                    if layers['ground'][y][x] == road_tile: continue
                    dist = h - 1 - y
                    if dist < water_lim:
                        layers['ground'][y][x] = getattr(self, 'water_tile', 'water_01')
                        layers['base'][y][x] = ' '
                        occupied_mask[y][x] = 1 
                        layers['protected_mask'][y][x] = 1
                    elif dist < sand_lim:
                        if layers['ground'][y][x] != getattr(self, 'water_tile', 'water_01'):
                            layers['ground'][y][x] = getattr(self, 'sand_tile', 'sand_01')
                            layers['base'][y][x] = 'garden_tree_16' if random.random() < tree_chance else ' '
                            occupied_mask[y][x] = 1
                            layers['protected_mask'][y][x] = 1

        if getattr(self, 'lobby_chunk', None) and (gx, gy) == self.lobby_chunk:
            return self._generate_lobby_chunk(gx, gy, w, h)

        # 4.5 Place Port_L1 at the shore of all non-military chunks BEFORE buildings and walls
        is_military = (getattr(self, 'military_chunk', None) == (gx, gy))
        if not is_military:
            self._place_port_at_shore(layers, occupied_mask, placed_rects, w, h, coast_left, coast_right, coast_top, coast_bottom, draw_secondary_maze_road)

        # 5. Organic Trade Routes for Urban Chunks
        if allow_buildings and not force_forest:
            num_routes = 4
            safe_margin = getattr(self, 'coast_width', 15) + 3 
            for _ in range(num_routes):
                rx1 = random.randint(safe_margin, max(safe_margin + 1, w - safe_margin))
                ry1 = random.randint(safe_margin, max(safe_margin + 1, h - safe_margin))
                rx2 = random.randint(safe_margin, max(safe_margin + 1, w - safe_margin))
                ry2 = random.randint(safe_margin, max(safe_margin + 1, h - safe_margin))
                draw_secondary_maze_road(rx1, ry1, rx2, ry2, tile_type=dirt_tile)

        def get_l2_counterpart(tmpl_name, is_forest=False):
            potential_l2_names = []
            if 'l1' in tmpl_name.lower():
                potential_l2_names.append(tmpl_name.replace('L1', 'L2').replace('l1', 'l2'))
            potential_l2_names.append(f"{tmpl_name}_L2")
            parts = tmpl_name.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                potential_l2_names.append(f"{parts[0]}_L2_{parts[1]}")
                potential_l2_names.append(f"{parts[0]}_L2")
            low = tmpl_name.lower()
            if is_forest:
                potential_l2_names.append("Forest_L2")
            else:
                if "petrol" in low and "building" in low: potential_l2_names.append("Petrol_Building_L2")
                elif "petrol" in low: potential_l2_names.append("Petrol_L2")
                if "heli" in low: potential_l2_names.append("Heli_rescue_L2")
                if "shed" in low: potential_l2_names.append("Shed_L2")
                if "store" in low: potential_l2_names.append("Stores_L2")
                if "warehouse" in low: potential_l2_names.append("Warehouse_L2")
                if "building" in low or "condo" in low or "house" in low: potential_l2_names.append("Building_L2")

            for pot in potential_l2_names:
                for k in self.templates.keys():
                    if k.lower() == pot.lower():
                        return k
            return None

        # 6. Place Buildings (TETRIS METHOD)
        def get_tetris_candidates(tw, th, gap=1):
            candidates = []
            if not placed_rects:
                candidates.extend([
                    (cx + 3, cy + 3),
                    (cx - tw - 3, cy - th - 3),
                    (cx + 3, cy - th - 3),
                    (cx - tw - 3, cy + 3)
                ])
                return candidates
            
            for pr in placed_rects:
                candidates.extend([
                    (pr.x + pr.width + gap, pr.y),
                    (pr.x + pr.width + gap, pr.y + pr.height - th),
                    (pr.x + pr.width + gap, pr.y + (pr.height - th) // 2),
                    (pr.x - tw - gap, pr.y), 
                    (pr.x - tw - gap, pr.y + pr.height - th), 
                    (pr.x - tw - gap, pr.y + (pr.height - th) // 2),
                    (pr.x, pr.y + pr.height + gap), 
                    (pr.x + pr.width - tw, pr.y + pr.height + gap),
                    (pr.x + (pr.width - tw) // 2, pr.y + pr.height + gap),
                    (pr.x, pr.y - th - gap), 
                    (pr.x + pr.width - tw, pr.y - th - gap),
                    (pr.x + (pr.width - tw) // 2, pr.y - th - gap)
                ])
                    
            candidates.sort(key=lambda c: (c[0] + tw/2.0 - cx)**2 + (c[1] + th/2.0 - cy)**2)
            
            seen = set()
            unique_candidates = []
            for c in candidates:
                if c not in seen:
                    seen.add(c)
                    unique_candidates.append(c)
            return unique_candidates

        def is_area_free(tx, ty, tw, th, gap=1, ignore_mask=False, is_center_override=False):
            if tx < 2 or tx + tw > w - 2 or ty < 2 or ty + th > h - 2: return False
            
            t_rect = pygame.Rect(tx, ty, tw, th)
            
            for ry in range(ty, ty + th):
                for rx in range(tx, tx + tw):
                    if is_in_connector_zone(rx, ry):
                        return False
            
            if not is_center_override:
                hub_rect = pygame.Rect(cx-2, cy-2, 5, 5)
                if t_rect.colliderect(hub_rect): return False
            
            for pr in placed_rects:
                if t_rect.inflate(gap*2, gap*2).colliderect(pr): 
                    return False
                    
            if not ignore_mask:
                for ry in range(ty, ty+th):
                    for rx in range(tx, tx+tw):
                        ground_tile = layers['ground'][ry][rx]
                        if ground_tile == getattr(self, 'water_tile', 'water_01'): return False
                        if layers['base'][ry][rx] == '@': return False
                        if occupied_mask[ry][rx] == 1 and ground_tile != road_tile: 
                            return False
            return True

        if allow_buildings and assigned_templates:
            sorted_templates = []
            for t_name in assigned_templates:
                if hasattr(self, 'templates') and t_name in self.templates:
                    t = self.templates[t_name]
                    area = t['width'] * t['height']
                    sorted_templates.append((area, t_name))
            sorted_templates.sort(key=lambda x: x[0], reverse=True)
            ordered_names = [x[1] for x in sorted_templates]

            for tmpl_name in ordered_names:
                tmpl = self.templates[tmpl_name]
                tw, th = tmpl['width'], tmpl['height']
                is_building2 = "building2" in tmpl_name.lower()
                is_cave = 'cave' in tmpl_name.lower()
                is_military_base = "military" in tmpl_name.lower() or "heli" in tmpl_name.lower()

                found_l2_key = get_l2_counterpart(tmpl_name, is_forest=False)
                tmpl_l2 = self.templates.get(found_l2_key) if found_l2_key else None
                fit_w = max(tw, tmpl_l2['width']) if tmpl_l2 else tw
                fit_h = max(th, tmpl_l2['height']) if tmpl_l2 else th

                placed = False
                
                if is_military_base:
                    tx = max(4, min(cx - (fit_w // 2), w - fit_w - 4))
                    ty = max(4, min(cy - (fit_h // 2), h - fit_h - 4))
                    if is_area_free(tx, ty, fit_w, fit_h, gap=1, ignore_mask=True, is_center_override=True):
                        self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, False, sand_tile, draw_secondary_maze_road)
                        placed = True

                if not placed and not is_cave:
                    candidates = get_tetris_candidates(fit_w, fit_h, gap=2)
                    for tx, ty in candidates:
                        if is_area_free(tx, ty, fit_w, fit_h, gap=2):
                            self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile, draw_secondary_maze_road)
                            placed = True
                            break

                if not placed:
                    for _ in range(80): 
                        tx = random.randint(4, max(4, w - fit_w - 4))
                        ty = random.randint(4, max(4, h - fit_h - 4))
                        if is_area_free(tx, ty, fit_w, fit_h, gap=1):
                            self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile, draw_secondary_maze_road)
                            placed = True
                            break
                
                if placed and tmpl_l2:
                    self._blit_template_mapped(layers, tmpl_l2, tx, ty, w, h, suffix='_L2')
                    l2_w, l2_h = tmpl_l2['width'], tmpl_l2['height']
                    
                    if hasattr(self, '_apply_l2_border'):
                        self._apply_l2_border(layers, tx, ty, l2_w, l2_h, w, h)
                        
                    pad = 4
                    for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad)):
                        for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad)):
                            occupied_mask_L2[ly][lx] = 1

        # 7. Forest / Nature Rooms
        if force_forest:
            self._generate_confusing_asphalt_maze(layers, occupied_mask, w, h, cx, cy)
            
            if assigned_templates:
              for tmpl_name in assigned_templates:
                if tmpl_name in self.templates:
                  tmpl = self.templates[tmpl_name]
                  tw, th = tmpl['width'], tmpl['height']
                  for _ in range(25):
                    tx = random.randint(3, max(4, w - tw - 3))
                    ty = random.randint(3, max(4, h - th - 3))
                    if is_area_free(tx, ty, tw, th, gap=2):
                      self._blit_template(layers, tmpl, tx, ty, w, h, clear_base=True)
                      for ry in range(ty, ty + th):
                        for rx in range(tx, tx + tw):
                          if 0 <= rx < w and 0 <= ry < h:
                            occupied_mask[ry][rx] = 1
                      break

        if hasattr(self, 'forest_templates') and self.forest_templates and not force_forest:
            num_forest_patches = max(4, min(14, (w * h) // 400))
            for _ in range(num_forest_patches): 
                tmpl_name = random.choice(self.forest_templates)
                tmpl = self.templates[tmpl_name]
                tw, th = tmpl['width'], tmpl['height']
                tx = random.randint(2, max(3, w - tw - 2))
                ty = random.randint(2, max(3, h - th - 2))
                
                if is_area_free(tx, ty, tw, th, gap=2):
                    self._blit_template(layers, tmpl, tx, ty, w, h, clear_base=True)
                    
                    found_l2_key = get_l2_counterpart(tmpl_name, is_forest=True)
                    if found_l2_key:
                        tmpl_l2 = self.templates[found_l2_key]
                        self._blit_template_mapped(layers, tmpl_l2, tx, ty, w, h, suffix='_L2')
                        
                        l2_w, l2_h = tmpl_l2.get('width', 10), tmpl_l2.get('height', 10)
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, l2_w, l2_h, w, h)
                        
                        pad = 4
                        for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad)):
                            for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad)):
                                occupied_mask_L2[ly][lx] = 1

                    placed_rects.append(pygame.Rect(tx, ty, tw, th))
                    for ry in range(ty, ty + th):
                        for rx in range(tx, tx + tw): 
                            occupied_mask[ry][rx] = 1

        # 8. Ground Formatting
        if force_forest:
            for y in range(h):
                for x in range(w):
                    ground_tile = layers['ground'][y][x]
                    if ground_tile != road_tile and ground_tile != sand_tile and ground_tile != dirt_tile and ground_tile != getattr(self, 'water_tile', 'water_01'):
                         layers['ground'][y][x] = 'bg_grass'

        # Border enforcement
        pathway_tiles = [road_tile, dirt_tile, sand_tile]
        clear_radius = 2 
        
        def apply_border_wall(bx, by, is_horizontal):
            if is_in_connector_zone(bx, by):
                layers['base'][by][bx] = ' '
                return

            if layers.get('protected_mask') and layers['protected_mask'][by][bx] == 1:
                return
            if any(pr.collidepoint(bx, by) for pr in placed_rects):
                return

            ground = layers['ground'][by][bx]
            if ground == getattr(self, 'water_tile', 'water_01') or 'sand' in ground or 'beach' in ground:
                return

            if is_horizontal:
                if (by == 0 and coast_top) or (by == h - 1 and coast_bottom):
                    return
            else:
                if (bx == 0 and coast_left) or (bx == w - 1 and coast_right):
                    return

            is_near_path = False
            if is_horizontal:
                if abs(bx - cx) <= clear_radius:
                    if (by == 0 and conns['top']) or (by == h - 1 and conns['bottom']):
                        is_near_path = True
            else:
                if abs(by - cy) <= clear_radius:
                    if (bx == 0 and conns['left']) or (bx == w - 1 and conns['right']):
                        is_near_path = True
                        
            if not is_near_path:
                layers['base'][by][bx] = '@'
            else:
                layers['base'][by][bx] = ' '
                if layers['ground'][by][bx] not in pathway_tiles:
                    layers['ground'][by][bx] = dirt_tile
                
        for x in range(w):
            apply_border_wall(x, 0, True)
            apply_border_wall(x, h-1, True)
            
        for y in range(h):
            apply_border_wall(0, y, False)
            apply_border_wall(w-1, y, False)

        # 9. Spawns
        if hasattr(self, '_scatter_zombies'):
            self._scatter_zombies(layers, occupied_mask, w, h)
        if hasattr(self, '_scatter_npcs'):
            self._scatter_npcs(layers, occupied_mask, w, h)

        # 10. Assigned L2 Spawning
        if assigned_l2_templates:
            for l2_name in assigned_l2_templates:
                l2_tmpl = self.templates[l2_name]
                l2_w, l2_h = l2_tmpl['width'], l2_tmpl['height']
                
                placed_l2 = False
                pad = 4
                for _ in range(40): 
                    tx = random.randint(pad, max(pad, w - l2_w - pad))
                    ty = random.randint(pad, max(pad, h - l2_h - pad))
                    
                    collision = False
                    for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad)):
                        for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad)):
                            if occupied_mask_L2[ly][lx] == 1:
                                collision = True
                                break
                        if collision: break
                    
                    if not collision:
                        self._blit_template_mapped(layers, l2_tmpl, tx, ty, w, h, suffix='_L2')
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, l2_w, l2_h, w, h)
                            
                        for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad)):
                            for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad)):
                                occupied_mask_L2[ly][lx] = 1
                        placed_l2 = True
                        break
        
        if hasattr(self, '_scatter_npcs_l2'):
            self._scatter_npcs_l2(layers, w, h)

        # 11. Scatter Decorations & Vegetation
        building_mask = [[False for _ in range(w)] for _ in range(h)]
        for pr in placed_rects:
            for ry in range(max(0, pr.y - 1), min(h, pr.y + pr.height + 1)):
                for rx in range(max(0, pr.x - 1), min(w, pr.x + pr.width + 1)):
                    building_mask[ry][rx] = True

        dirty_decos = ['garden_stone', 'garden_stone_iron', 'garden_stone_powder', 'garden_grass_1' , 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']
        wall_decos = ['garden_tree_8','garden_tree_6', 'garden_dirty_1', 'garden_dirty_2', 'garden_dirty_3', 'garden_dirty_4']
        sand_decos = ['garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']
        asphalt_decos = ['garden_stone', 'garden_dirty_1', 'garden_dirty_2', 'garden_dirty_3', 'garden_dirty_4', 'garden_grass_1' , 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']

        path_tiles = set()
        for y in range(h):
            for x in range(w):
                gt = layers['ground'][y][x]
                if 'asphalt' in gt or 'dirty' in gt:
                    path_tiles.add((x, y))

        for y in range(h):
            for x in range(w):
                if is_in_connector_zone(x, y):
                    layers['base'][y][x] = ' '
                    continue

                if not building_mask[y][x] and layers['base'][y][x] == ' ':
                    ground_tile = layers['ground'][y][x]
                    
                    if 'water' in ground_tile or 'beach_sand' in ground_tile:
                        continue
                        
                    if 'sand_' in ground_tile:
                        if random.random() < 0.05:
                            layers['base'][y][x] = random.choice(sand_decos)
                        continue

                    if (x, y) in path_tiles:
                        if 'dirty' in ground_tile and random.random() < 0.05:
                            layers['base'][y][x] = random.choice(dirty_decos)
                        elif 'asphalt' in ground_tile and random.random() < 0.05:
                            layers['base'][y][x] = random.choice(asphalt_decos)
                    else:
                        dist_to_path = 999
                        for dy in range(-2, 3):
                            for dx in range(-2, 3):
                                if (x+dx, y+dy) in path_tiles:
                                    d = max(abs(dx), abs(dy))
                                    if d < dist_to_path:
                                        dist_to_path = d
                        
                        if dist_to_path == 1:
                            if random.random() < 0.6:
                                layers['base'][y][x] = random.choice(dirty_decos)
                        elif dist_to_path >= 2:
                            if random.random() < 0.90:
                                layers['base'][y][x] = random.choice(wall_decos)

        return layers

    def _finalize_placement(self, layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile, draw_secondary_maze_road):
        is_cave = 'cave' in tmpl_name.lower()
        road_tile = 'asphalt_01'
        
        if not is_cave:
            lot_m = 2
            for ry in range(ty-lot_m, ty+th+lot_m):
                for rx in range(tx-lot_m, tx+tw+lot_m):
                    if 1 <= rx < w-1 and 1 <= ry < h-1:
                        if layers['ground'][ry][rx] != getattr(self, 'water_tile', 'water_01'):
                            layers['ground'][ry][rx] = road_tile
                            occupied_mask[ry][rx] = 1
            
            bx, by = tx + tw // 2, ty + th // 2
            draw_secondary_maze_road(bx, by, cx, cy, road_tile)
        else:
            bx, by = tx + tw // 2, ty + th // 2
            draw_secondary_maze_road(bx, by, cx, cy, 'dirty_01', path_width=3)
            
        self._blit_template(layers, tmpl, tx, ty, w, h, clear_base=True)
        placed_rects.append(pygame.Rect(tx, ty, tw, th))
        for ry in range(ty, ty + th):
            for rx in range(tx, tx + tw): 
                occupied_mask[ry][rx] = 1