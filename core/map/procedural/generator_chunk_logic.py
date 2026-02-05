import math
import random
import pygame
from core.data.config import *

class ProceduralGeneratorChunk:
    def _generate_chunk_data(self, gx, gy, conns, is_start=False, assigned_templates=None, allow_buildings=True, force_forest=False):
        w, h = self.chunk_size, self.chunk_size
        cx, cy = w // 2, h // 2
        
        layers = {
            'base': [[' ' for _ in range(w)] for _ in range(h)],
            'ground': [['bg_grass' for _ in range(w)] for _ in range(h)],
            'spawn': [[' ' for _ in range(w)] for _ in range(h)],
            'roof': [[' ' for _ in range(w)] for _ in range(h)],
            'light': [[' ' for _ in range(w)] for _ in range(h)],
            
            # L2 Layers
            'base_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'ground_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'spawn_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'roof_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'light_L2': [[' ' for _ in range(w)] for _ in range(h)]
        }
        occupied_mask = [[0 for _ in range(w)] for _ in range(h)]
        occupied_mask_L2 = [[0 for _ in range(w)] for _ in range(h)] # NEW: L2 Mask

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

        # 5. Organic Trade Routes
        if allow_buildings and not force_forest:
            num_routes = 6
            safe_margin = self.coast_width + 3 
            for _ in range(num_routes):
                rx1 = random.randint(safe_margin, w - safe_margin)
                ry1 = random.randint(safe_margin, h - safe_margin)
                rx2 = random.randint(safe_margin, w - safe_margin)
                ry2 = random.randint(safe_margin, h - safe_margin)
                draw_secondary_maze_road(rx1, ry1, rx2, ry2, tile_type=dirt_tile)

        # 6. Place Buildings
        placed_rects = [] 
        
        def is_area_free(tx, ty, tw, th, margin=0, ignore_mask=False):
            t_rect = pygame.Rect(tx, ty, tw, th)
            for pr in placed_rects:
                if t_rect.inflate(margin*2, margin*2).colliderect(pr): return False
            if tx < 0 or tx + tw > w or ty < 0 or ty + th > h: return False
            if not ignore_mask:
                mx1, my1 = max(0, tx - margin), max(0, ty - margin)
                mx2, my2 = min(w, tx + tw + margin), min(h, ty + th + margin)
                for ry in range(my1, my2):
                    for rx in range(mx1, mx2):
                        if 0 <= ry < h and 0 <= rx < w:
                            if occupied_mask[ry][rx] == 1: 
                                return False
            else:
                mx1, my1 = tx, ty
                mx2, my2 = tx + tw, ty + th
                for ry in range(my1, my2):
                    for rx in range(mx1, mx2):
                         if 0 <= ry < h and 0 <= rx < w:
                             if layers['ground'][ry][rx] == self.water_tile:
                                 return False
            return True

        if allow_buildings and assigned_templates:
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
                
                for _ in range(100): 
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
                
                if not placed:
                    print(f"Random placement failed for {tmpl_name}, trying scan...")
                    stride = 2 
                    for sy in range(border_w + 2, h - border_w - th - 2, stride):
                        if placed: break
                        for sx in range(border_w + 2, w - border_w - tw - 2, stride):
                            if is_area_free(sx, sy, tw, th, margin=1):
                                self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, sx, sy, tw, th, cx, cy, w, h, is_building2, sand_tile)
                                placed = True
                                break
                
                if not placed:
                    print(f"FORCE PLACING Mandatory Building: {tmpl_name}")
                    for _ in range(50):
                        tx = random.randint(5, w - 5 - tw)
                        ty = random.randint(5, h - 5 - th)
                        hub_rect = pygame.Rect(cx-3, cy-3, 6, 6)
                        new_rect = pygame.Rect(tx, ty, tw, th)
                        if not hub_rect.colliderect(new_rect):
                            if is_area_free(tx, ty, tw, th, margin=0, ignore_mask=True):
                                for cy_clr in range(ty, ty + th):
                                    for cx_clr in range(tx, tx + tw):
                                        if 0 <= cy_clr < h and 0 <= cx_clr < w:
                                            layers['base'][cy_clr][cx_clr] = ' ' 
                                            layers['ground'][cy_clr][cx_clr] = sand_tile 
                                            occupied_mask[cy_clr][cx_clr] = 0 
                                self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile)
                                placed = True
                                break
                
                if placed:
                    if 'l1' in tmpl_name.lower():
                        potential_l2_name_base = tmpl_name.replace('L1', 'L2').replace('l1', 'l2') 
                        found_l2_key = None
                        for key in self.templates.keys():
                            if key.lower() == potential_l2_name_base.lower():
                                found_l2_key = key
                                break
                        if found_l2_key:
                            print(f"  > LINKING: Spawning {found_l2_key} at ({tx}, {ty}) on Layer 2")
                            tmpl_l2 = self.templates[found_l2_key]
                            self._blit_template_mapped(layers, tmpl_l2, tx, ty, w, h, suffix='_L2')
                            
                            # NEW: Apply border
                            self._apply_l2_border(layers, tx, ty, tmpl_l2.get('width', 10), tmpl_l2.get('height', 10), w, h)
                            
                            # UPDATE L2 MASK to prevent random spawn overlapping linked spawn
                            l2_w, l2_h = tmpl_l2.get('width', 10), tmpl_l2.get('height', 10)
                            for ly in range(ty, min(h, ty + l2_h)):
                                for lx in range(tx, min(w, tx + l2_w)):
                                    occupied_mask_L2[ly][lx] = 1
                        else:
                            if 'cave' in tmpl_name.lower():
                                print(f"  > WARNING: Linked map {tmpl_name} placed, but L2 counterpart not found!")

                if not placed:
                    print(f"CRITICAL FAILURE: Could not place {tmpl_name} even with force!")

        # 7. Forest / Nature
        if self.forest_templates and not force_forest:
            for _ in range(20): 
                tmpl_name = random.choice(self.forest_templates)
                tmpl = self.templates[tmpl_name]
                tw, th = tmpl['width'], tmpl['height']
                tx = random.randint(1, w - tw - 1)
                ty = random.randint(1, h - th - 1)
                if is_area_free(tx, ty, tw, th, margin=0):
                    self._blit_template(layers, tmpl, tx, ty, w, h)
                    if 'l1' in tmpl_name.lower():
                        potential_l2 = tmpl_name.replace('L1', 'L2').replace('l1', 'l2')
                        found_l2_key = next((k for k in self.templates if k.lower() == potential_l2.lower()), None)
                        if found_l2_key:
                            tmpl_l2 = self.templates[found_l2_key]
                            self._blit_template_mapped(layers, tmpl_l2, tx, ty, w, h, suffix='_L2')
                            
                            # NEW: Apply border
                            self._apply_l2_border(layers, tx, ty, tmpl_l2.get('width', 10), tmpl_l2.get('height', 10), w, h)
                            
                            l2_w, l2_h = tmpl_l2.get('width', 10), tmpl_l2.get('height', 10)
                            for ly in range(ty, min(h, ty + l2_h)):
                                for lx in range(tx, min(w, tx + l2_w)):
                                    occupied_mask_L2[ly][lx] = 1

                    placed_rects.append(pygame.Rect(tx, ty, tw, th))
                    for ry in range(ty, ty + th):
                        for rx in range(tx, tx + tw): 
                            occupied_mask[ry][rx] = 1

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
        
        # [UPDATED] L1 NPC SCATTER
        self._scatter_npcs(layers, occupied_mask, w, h)

        # 10. Random L2 Spawning (Independent of L1)
        if self.l2_templates:
            # Try to spawn 3 random L2 templates per chunk
            for _ in range(MAP_CHUNKS):
                l2_name = random.choice(self.l2_templates)
                l2_tmpl = self.templates[l2_name]
                l2_w, l2_h = l2_tmpl['width'], l2_tmpl['height']
                
                placed_l2 = False
                for _ in range(20): # Attempts
                    tx = random.randint(2, w - l2_w - 2)
                    ty = random.randint(2, h - l2_h - 2)
                    
                    # Check collision on L2 mask
                    collision = False
                    for ly in range(ty, ty + l2_h):
                        for lx in range(tx, tx + l2_w):
                            if occupied_mask_L2[ly][lx] == 1:
                                collision = True
                                break
                        if collision: break
                    
                    if not collision:
                        # Place it
                        self._blit_template_mapped(layers, l2_tmpl, tx, ty, w, h, suffix='_L2')
                        
                        # NEW: Apply border
                        self._apply_l2_border(layers, tx, ty, l2_w, l2_h, w, h)

                        # Mark mask
                        for ly in range(ty, ty + l2_h):
                            for lx in range(tx, tx + l2_w):
                                occupied_mask_L2[ly][lx] = 1
                        placed_l2 = True
                        print(f"Spawned Random L2 Template: {l2_name} at ({tx}, {ty})")
                        break
        
        # [NEW] DISTRIBUTE L2 NPCS - Using strict scatter method instead of candidate lists
        self._scatter_npcs_l2(layers, w, h)

        return layers

    def _finalize_placement(self, layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile):
        is_cave = 'cave' in tmpl_name.lower()
        road_tile = 'asphalt_01'
        
        if not is_cave:
            lot_m = 2
            for ry in range(ty-lot_m, ty+th+lot_m):
                for rx in range(tx-lot_m, tx+tw+lot_m):
                    if 0<=rx<w and 0<=ry<h and layers['ground'][ry][rx] == 'bg_grass':
                        layers['ground'][ry][rx] = sand_tile
                        occupied_mask[ry][rx] = 1
            
            bx, by = tx + tw // 2, ty + th // 2
            def draw_secondary_road(start_x, start_y, target_x, target_y):
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