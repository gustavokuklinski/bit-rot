# core/map/procedural/generator_chunk_logic.py

import math
import random
import pygame
from core.data.config import *

class ProceduralGeneratorChunk:
    def _generate_chunk_data(self, gx, gy, conns, is_start=False, assigned_templates=None, assigned_l2_templates=None, allow_buildings=True, force_forest=False, cell_w=None, cell_h=None, coast_left=False, coast_right=False, coast_top=False, coast_bottom=False):
        if cell_w is not None and cell_h is not None:
            w, h = cell_w, cell_h
        else:
            base_size = 64
            if assigned_templates and allow_buildings and not force_forest:
                total_area = 0
                max_dim = 0
                for t_name in assigned_templates:
                    if hasattr(self, 'templates') and t_name in self.templates:
                        tw = self.templates[t_name]['width']
                        th = self.templates[t_name]['height']
                        total_area += (tw * th)
                        max_dim = max(max_dim, tw, th)
                
                area_based_size = int(math.ceil(math.sqrt(total_area * 1.5)))
                min_fit_size = max_dim + 30 
                base_size = max(base_size, area_based_size, min_fit_size)
                base_size += random.randint(0, 15)
                
            elif force_forest:
                base_size = random.randint(50, 100)
                
            if coast_left or coast_right or coast_top or coast_bottom:
                base_size += 20
                
            w, h = base_size, base_size
            
        cx, cy = w // 2, h // 2
        
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
        sand_tile = 'sand_01'

        def draw_secondary_maze_road(start_x, start_y, target_x, target_y, tile_type=dirt_tile):
            current_x, current_y = start_x, start_y
            path = [(current_x, current_y)]
            
            if tile_type == road_tile:
                # FORCE STRAIGHT AXIS-ALIGNED PATH FOR ASPHALT
                while current_x != target_x:
                    current_x += 1 if target_x > current_x else -1
                    
                    # Stop drawing the road if it hits an already placed building
                    if any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                        break
                    path.append((current_x, current_y))
                
                # Only continue drawing Y if we didn't just crash into a building
                if not any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                    while current_y != target_y:
                        current_y += 1 if target_y > current_y else -1
                        
                        if any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                            break
                        path.append((current_x, current_y))
            else:
                # DRUNKARD WALK FOR DIRT/SAND (Organic pathways)
                steps = 0
                max_steps = w * 6
                while steps < max_steps:
                    steps += 1
                    if not (0 <= current_x < w and 0 <= current_y < h): break
                    
                    # Stop organic paths if they hit a building
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
                brush_size = 1
                extra_range = 1 if tile_type == road_tile else 2
                for oy in range(-brush_size, brush_size + extra_range):
                    for ox in range(-brush_size, brush_size + extra_range):
                        gx_pos, gy_pos = px + ox, py + oy
                        if 0 <= gx_pos < w and 0 <= gy_pos < h:
                            
                            # 2. FINAL CHECK: Never let the asphalt brush bleed over an existing building's floor
                            if any(pr.collidepoint(gx_pos, gy_pos) for pr in placed_rects):
                                continue
                                
                            if layers['base'][gy_pos][gx_pos] == ' ' and layers['ground'][gy_pos][gx_pos] != road_tile:
                                if layers['ground'][gy_pos][gx_pos] != getattr(self, 'water_tile', 'water_01'):
                                    layers['ground'][gy_pos][gx_pos] = tile_type
                                    occupied_mask[gy_pos][gx_pos] = 1

        # 1. Central Hub (Mark the center)
        for y in range(cy-2, cy+3):
            for x in range(cx-2, cx+3):
                layers['ground'][y][x] = road_tile
                occupied_mask[y][x] = 1

        # 2. Connections (All Drunkard)
        if conns['top']:
            if conns['top_type'] == 'asphalt': draw_secondary_maze_road(cx, 0, cx, cy, road_tile)
            elif conns['top_type'] == 'sand': draw_secondary_maze_road(cx, 0, cx, cy, sand_tile)
            else: draw_secondary_maze_road(cx, 0, cx, cy, dirt_tile)
            
        if conns['bottom']:
            if conns['bottom_type'] == 'asphalt': draw_secondary_maze_road(cx, h-1, cx, cy, road_tile)
            elif conns['bottom_type'] == 'sand': draw_secondary_maze_road(cx, h-1, cx, cy, sand_tile)
            else: draw_secondary_maze_road(cx, h-1, cx, cy, dirt_tile)
            
        if conns['left']:
            if conns['left_type'] == 'asphalt': draw_secondary_maze_road(0, cy, cx, cy, road_tile)
            elif conns['left_type'] == 'sand': draw_secondary_maze_road(0, cy, cx, cy, sand_tile)
            else: draw_secondary_maze_road(0, cy, cx, cy, dirt_tile)
            
        if conns['right']:
            if conns['right_type'] == 'asphalt': draw_secondary_maze_road(w-1, cy, cx, cy, road_tile)
            elif conns['right_type'] == 'sand': draw_secondary_maze_road(w-1, cy, cx, cy, sand_tile)
            else: draw_secondary_maze_road(w-1, cy, cx, cy, dirt_tile)

        # 3. Border (Forest)
        border_w = getattr(self, 'forest_border_width', 2)
        for y in range(h):
            for x in range(w):
                if x < border_w or x >= w - border_w or y < border_w or y >= h - border_w:
                    if occupied_mask[y][x] == 0:
                        tile = random.choice(getattr(self, 'forest_tiles', ['wall_stone']))
                        layers['base'][y][x] = tile
                        occupied_mask[y][x] = 1

        # 4. Organic Coastline
        if hasattr(self, 'grid_w') and hasattr(self, 'grid_h'):
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
                    global_y = gy * h + y
                    offset = get_coast_noise(global_y)
                    water_lim = (cw - 8) + offset 
                    sand_lim = cw + offset
                    for x in range(cw + 8):
                        if x >= w: break
                        if layers['ground'][y][x] == road_tile: continue
                        if x < water_lim:
                            layers['ground'][y][x] = getattr(self, 'water_tile', 'water_01')
                            layers['base'][y][x] = ' '
                            occupied_mask[y][x] = 1 
                        elif x < sand_lim:
                            if layers['ground'][y][x] != getattr(self, 'water_tile', 'water_01'):
                                layers['ground'][y][x] = getattr(self, 'sand_tile', 'sand_01')
                                layers['base'][y][x] = 'garden_tree_16' if random.random() < tree_chance else ' '
                                occupied_mask[y][x] = 1

            if coast_right:
                for y in range(h):
                    global_y = gy * h + y
                    offset = get_coast_noise(global_y)
                    water_lim = (cw - 8) + offset
                    sand_lim = cw + offset
                    min_x = w - (cw + 8)
                    for x in range(min_x, w):
                        if x < 0: continue
                        if layers['ground'][y][x] == road_tile: continue
                        dist = w - 1 - x
                        if dist < water_lim:
                            layers['ground'][y][x] = getattr(self, 'water_tile', 'water_01')
                            layers['base'][y][x] = ' '
                            occupied_mask[y][x] = 1
                        elif dist < sand_lim:
                            if layers['ground'][y][x] != getattr(self, 'water_tile', 'water_01'):
                                layers['ground'][y][x] = getattr(self, 'sand_tile', 'sand_01')
                                layers['base'][y][x] = 'garden_tree_16' if random.random() < tree_chance else ' '
                                occupied_mask[y][x] = 1

            if coast_top:
                for x in range(w):
                    global_x = gx * w + x
                    offset = get_coast_noise(global_x)
                    water_lim = (cw - 8) + offset
                    sand_lim = cw + offset
                    for y in range(cw + 8):
                        if y >= h: break
                        if layers['ground'][y][x] == road_tile: continue
                        if y < water_lim:
                            layers['ground'][y][x] = getattr(self, 'water_tile', 'water_01')
                            layers['base'][y][x] = ' '
                            occupied_mask[y][x] = 1
                        elif y < sand_lim:
                            if layers['ground'][y][x] != getattr(self, 'water_tile', 'water_01'):
                                layers['ground'][y][x] = getattr(self, 'sand_tile', 'sand_01')
                                layers['base'][y][x] = 'garden_tree_16' if random.random() < tree_chance else ' '
                                occupied_mask[y][x] = 1

            if coast_bottom:
                for x in range(w):
                    global_x = gx * w + x
                    offset = get_coast_noise(global_x)
                    water_lim = (cw - 8) + offset
                    sand_lim = cw + offset
                    min_y = h - (cw + 8)
                    for y in range(min_y, h):
                        if y < 0: continue
                        if layers['ground'][y][x] == road_tile: continue
                        dist = h - 1 - y
                        if dist < water_lim:
                            layers['ground'][y][x] = getattr(self, 'water_tile', 'water_01')
                            layers['base'][y][x] = ' '
                            occupied_mask[y][x] = 1
                        elif dist < sand_lim:
                            if layers['ground'][y][x] != getattr(self, 'water_tile', 'water_01'):
                                layers['ground'][y][x] = getattr(self, 'sand_tile', 'sand_01')
                                layers['base'][y][x] = 'garden_tree_16' if random.random() < tree_chance else ' '
                                occupied_mask[y][x] = 1

        # 5. Organic Trade Routes
        if allow_buildings and not force_forest:
            num_routes = 6
            safe_margin = getattr(self, 'coast_width', 15) + 3 
            for _ in range(num_routes):
                rx1 = random.randint(safe_margin, w - safe_margin)
                ry1 = random.randint(safe_margin, h - safe_margin)
                rx2 = random.randint(safe_margin, w - safe_margin)
                ry2 = random.randint(safe_margin, h - safe_margin)
                draw_secondary_maze_road(rx1, ry1, rx2, ry2, tile_type=dirt_tile)

        # Helper to intelligently map generic building types to requested L2 basements
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
        #placed_rects = [] 
        
        def get_tetris_candidates(tw, th, gap=1):
            """Calculates perfectly flush corner and center coordinates to block buildings together."""
            candidates = []
            if not placed_rects:
                # Start the first buildings tightly around the central crossroad hub
                candidates.extend([
                    (cx + 3, cy + 3),
                    (cx - tw - 3, cy - th - 3),
                    (cx + 3, cy - th - 3),
                    (cx - tw - 3, cy + 3)
                ])
                return candidates
            
            for pr in placed_rects:
                # Calculate exactly flush aligned locations to mimic blocks
                # Right side
                candidates.extend([
                    (pr.x + pr.width + gap, pr.y), # Top flush
                    (pr.x + pr.width + gap, pr.y + pr.height - th), # Bottom flush
                    (pr.x + pr.width + gap, pr.y + (pr.height - th) // 2) # Center flush
                ])
                # Left side
                candidates.extend([
                    (pr.x - tw - gap, pr.y), 
                    (pr.x - tw - gap, pr.y + pr.height - th), 
                    (pr.x - tw - gap, pr.y + (pr.height - th) // 2)
                ])
                # Bottom
                candidates.extend([
                    (pr.x, pr.y + pr.height + gap), 
                    (pr.x + pr.width - tw, pr.y + pr.height + gap),
                    (pr.x + (pr.width - tw) // 2, pr.y + pr.height + gap)
                ])
                # Top
                candidates.extend([
                    (pr.x, pr.y - th - gap), 
                    (pr.x + pr.width - tw, pr.y - th - gap),
                    (pr.x + (pr.width - tw) // 2, pr.y - th - gap)
                ])
                    
            # Sort strictly by distance to the central hub to grow outward seamlessly
            candidates.sort(key=lambda c: (c[0] + tw/2.0 - cx)**2 + (c[1] + th/2.0 - cy)**2)
            
            # Remove duplicates for efficiency
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
            
            # Central hub protector
            if not is_center_override:
                hub_rect = pygame.Rect(cx-2, cy-2, 5, 5)
                if t_rect.colliderect(hub_rect): return False
            
            # 1. Footprint Collision: Ensure the minimum gap between any two building structures is maintained.
            for pr in placed_rects:
                if t_rect.inflate(gap*2, gap*2).colliderect(pr): 
                    return False
                    
            # 2. Hard mask checks (Ignore asphalt overlap so they can seamlessly merge boundaries)
            if not ignore_mask:
                for ry in range(ty, ty+th):
                    for rx in range(tx, tx+tw):
                        ground_tile = layers['ground'][ry][rx]
                        if ground_tile == getattr(self, 'water_tile', 'water_01'): return False
                        if layers['base'][ry][rx] == '@': return False
                        
                        # Only reject if occupied by something that IS NOT asphalt.
                        # This allows the building footprints to freely snap onto each other's asphalt lots.
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
                # Ensure we catch all variants of military templates to force override
                is_military_base = "military" in tmpl_name.lower() or "heli" in tmpl_name.lower()
                
                placed = False
                
                if is_military_base:
                    tx = cx - (tw // 2)
                    ty = cy - (th // 2)
                    # Ignore mask AND bypass center protector so Military reliably spawns exactly in center
                    if is_area_free(tx, ty, tw, th, gap=1, ignore_mask=True, is_center_override=True):
                        self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, False, sand_tile, draw_secondary_maze_road)
                        placed = True

                if not placed and not is_cave:
                    # 'gap=1' enforces exactly 1 tile of space between building floors.
                    # Because finalize_placement adds exactly 1 tile of asphalt around the floors, 
                    # they will exactly share the asphalt border, giving the "glued together" town aesthetic.
                    candidates = get_tetris_candidates(tw, th, gap=2)
                    
                    for tx, ty in candidates:
                        if is_area_free(tx, ty, tw, th, gap=2):
                            self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile, draw_secondary_maze_road)
                            placed = True
                            break

                if not placed:
                    # Random fallback purely for caves or if Tetris physically hits a border wall
                    for _ in range(100): 
                        tx = random.randint(3, w - 3 - tw)
                        ty = random.randint(3, h - 3 - th)
                        if is_area_free(tx, ty, tw, th, gap=1):
                            self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile, draw_secondary_maze_road)
                            placed = True
                            break
                
                if placed:
                    found_l2_key = get_l2_counterpart(tmpl_name, is_forest=False)
                    if found_l2_key:
                        tmpl_l2 = self.templates[found_l2_key]
                        self._blit_template_mapped(layers, tmpl_l2, tx, ty, w, h, suffix='_L2')
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, tmpl_l2.get('width', 10), tmpl_l2.get('height', 10), w, h)
                        
                        l2_w, l2_h = tmpl_l2.get('width', 10), tmpl_l2.get('height', 10)
                        for ly in range(ty, min(h, ty + l2_h)):
                            for lx in range(tx, min(w, tx + l2_w)):
                                occupied_mask_L2[ly][lx] = 1

        # 7. Forest / Nature
        if hasattr(self, 'forest_templates') and self.forest_templates and not force_forest:
            for _ in range(20): 
                tmpl_name = random.choice(self.forest_templates)
                tmpl = self.templates[tmpl_name]
                tw, th = tmpl['width'], tmpl['height']
                tx = random.randint(2, w - tw - 2)
                ty = random.randint(2, h - th - 2)
                
                if is_area_free(tx, ty, tw, th, gap=2):
                    self._blit_template(layers, tmpl, tx, ty, w, h)
                    
                    found_l2_key = get_l2_counterpart(tmpl_name, is_forest=True)
                    if found_l2_key:
                        tmpl_l2 = self.templates[found_l2_key]
                        self._blit_template_mapped(layers, tmpl_l2, tx, ty, w, h, suffix='_L2')
                        if hasattr(self, '_apply_l2_border'):
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
                    if ground_tile != road_tile and ground_tile != sand_tile and ground_tile != dirt_tile and ground_tile != getattr(self, 'water_tile', 'water_01'):
                         layers['ground'][y][x] = 'bg_grass'
            cluster_count_range = random.randint(500, 1500)
            current_radius = 10
            current_density = 0.95
        else:
            cluster_count_range = random.randint(getattr(self, 'cluster_min_count', 50), getattr(self, 'cluster_max_count', 100))
            current_radius = getattr(self, 'cluster_radius', 4)
            current_density = getattr(self, 'cluster_density', 0.5)

        for _ in range(cluster_count_range):
            cgx = random.randint(border_w, w - border_w)
            cgy = random.randint(border_w, h - border_w)
            search_r = current_radius + 1 
            for y in range(cgy - search_r, cgy + search_r):
                for x in range(cgx - search_r, cgx + search_r):
                    if 0 <= x < w and 0 <= y < h:
                        if occupied_mask[y][x] == 0 and layers['base'][y][x] == ' ':
                            if math.hypot(x - cgx, y - cgy) <= current_radius: 
                                if random.random() < current_density: 
                                    layers['base'][y][x] = random.choice(getattr(self, 'forest_tiles', ['wall_stone']))

        # --- HARD BORDER ENFORCEMENT ---
        pathway_tiles = [road_tile, dirt_tile, sand_tile]
        clear_radius = 2 
        
        def apply_border_wall(bx, by, is_horizontal):
            ground = layers['ground'][by][bx]
            
            # Skip water tiles
            if ground == getattr(self, 'water_tile', 'water_01'):
                return
                
            # Skip global extreme map borders
            is_left_extreme = (gx == 0 and bx == 0)
            is_right_extreme = (hasattr(self, 'grid_w') and gx == self.grid_w - 1 and bx == w - 1)
            is_top_extreme = (gy == 0 and by == 0)
            is_bottom_extreme = (hasattr(self, 'grid_h') and gy == self.grid_h - 1 and by == h - 1)
            
            if is_left_extreme or is_right_extreme or is_top_extreme or is_bottom_extreme:
                return

            is_near_path = False
            
            if is_horizontal:
                if abs(bx - cx) <= clear_radius:
                    if (by == 0 and conns['top']) or (by == h-1 and conns['bottom']):
                        is_near_path = True
            else:
                if abs(by - cy) <= clear_radius:
                    if (bx == 0 and conns['left']) or (bx == w-1 and conns['right']):
                        is_near_path = True
                        
            if not is_near_path:
                layers['base'][by][bx] = '@'
            else:
                layers['base'][by][bx] = ' ' # Clear gap
                if layers['ground'][by][bx] not in pathway_tiles:
                    layers['ground'][by][bx] = dirt_tile
                
        # Horizontal Borders (Top and Bottom)
        for x in range(w):
            apply_border_wall(x, 0, True)
            apply_border_wall(x, h-1, True)
            
        # Vertical Borders (Left and Right)
        for y in range(h):
            apply_border_wall(0, y, False)
            apply_border_wall(w-1, y, False)
        # -------------------------------------

        # 9. Spawns
        if is_start: 
            layers['spawn'][cy][cx] = 'P'
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
                for _ in range(20): 
                    tx = random.randint(2, w - l2_w - 2)
                    ty = random.randint(2, h - l2_h - 2)
                    
                    collision = False
                    for ly in range(ty, ty + l2_h):
                        for lx in range(tx, tx + l2_w):
                            if occupied_mask_L2[ly][lx] == 1:
                                collision = True
                                break
                        if collision: break
                    
                    if not collision:
                        self._blit_template_mapped(layers, l2_tmpl, tx, ty, w, h, suffix='_L2')
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, l2_w, l2_h, w, h)

                        for ly in range(ty, ty + l2_h):
                            for lx in range(tx, tx + l2_w):
                                occupied_mask_L2[ly][lx] = 1
                        placed_l2 = True
                        break
        
        if hasattr(self, '_scatter_npcs_l2'):
            self._scatter_npcs_l2(layers, w, h)

        # -------------------------------------------------------------
        # 11. [NEW] Scatter Decorations (Vegetation, Pebbles, Shells)
        # -------------------------------------------------------------
        
        # Build a safe mask so we don't accidentally spawn a rock inside a building's empty floor space
        building_mask = [[False for _ in range(w)] for _ in range(h)]
        for pr in placed_rects:
            for ry in range(max(0, pr.y), min(h, pr.y + pr.height)):
                for rx in range(max(0, pr.x), min(w, pr.x + pr.width)):
                    building_mask[ry][rx] = True

        grass_decos = getattr(self, 'grass_decorations', ['garden_stone','garden_stone_powder', 'garden_tree_8','garden_tree_6', 'garden_dirty_1', 'garden_dirty_2', 'garden_dirty_3', 'garden_dirty_4'])
        dirt_decos = getattr(self, 'dirt_decorations', ['garden_stone', 'garden_stone_iron', 'garden_grass_1' , 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass'])
        sand_decos = getattr(self, 'sand_decorations', ['garden_stone', 'garden_dirty_1', 'garden_dirty_2', 'garden_dirty_3', 'garden_dirty_4'])
        
        grass_chance = 0.05
        dirt_chance = 0.03
        sand_chance = 0.02

        for y in range(h):
            for x in range(w):
                if not building_mask[y][x] and layers['base'][y][x] == ' ':
                    ground_tile = layers['ground'][y][x]
                    
                    if ground_tile == 'bg_grass':
                        if random.random() < grass_chance:
                            layers['base'][y][x] = random.choice(grass_decos)
                            
                    elif ground_tile.startswith('dirty_'):
                        if random.random() < dirt_chance:
                            layers['base'][y][x] = random.choice(dirt_decos)
                            
                    elif ground_tile.startswith('sand_') or ground_tile.startswith('beach_sand_'):
                        if random.random() < sand_chance:
                            layers['base'][y][x] = random.choice(sand_decos)

        return layers

    def _finalize_placement(self, layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile, draw_secondary_maze_road):
        is_cave = 'cave' in tmpl_name.lower()
        road_tile = 'asphalt_01'
        
        if not is_cave:
            lot_m = 2
            # 1. Draw the asphalt padding (lot) around the building
            for ry in range(ty-lot_m, ty+th+lot_m):
                for rx in range(tx-lot_m, tx+tw+lot_m):
                    if 1 <= rx < w-1 and 1 <= ry < h-1:
                        # Only apply asphalt if we're not running into water 
                        if layers['ground'][ry][rx] != getattr(self, 'water_tile', 'water_01'):
                            layers['ground'][ry][rx] = road_tile
                            occupied_mask[ry][rx] = 1
            
            bx, by = tx + tw // 2, ty + th // 2
            # 2. Draw the organic connector to the center crossroad using the passed method
            draw_secondary_maze_road(bx, by, cx, cy, road_tile)
        
        # 3. Blit the actual building on top
        self._blit_template(layers, tmpl, tx, ty, w, h)
        placed_rects.append(pygame.Rect(tx, ty, tw, th))
        for ry in range(ty, ty + th):
            for rx in range(tx, tx + tw): 
                occupied_mask[ry][rx] = 1