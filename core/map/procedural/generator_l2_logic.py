import random
from core.data.config import *

class ProceduralGeneratorL2:
    def _populate_l2_spawns(self, layers):
        """
        Populates Layer 2 with Zombies on Pathways only.
        NPCs are now handled during chunk generation via _scatter_npcs_l2.
        """
        ground = layers.get('ground')
        base = layers.get('base')
        spawn = layers.get('spawn')
        
        if not ground or not base or not spawn: return
        
        h = len(ground)
        w = len(ground[0])
        
        pathway_candidates = []
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}
        # 1. Categorize Candidates (Pathways ONLY)
        for y in range(2, h-2):
            for x in range(2, w-2):
                # Basic validity: Floor exists, Base empty, No existing spawn
                base_tile = layers['base'][y][x]
                if base_tile != ' ':
                    if base_tile in defs and defs[base_tile].get('is_obstacle', False):
                        continue
                    if base_tile == '@': # Explicitly skip border tiles
                        continue
                
                # STUCK FIX: Check 4 neighbors
                empty_neighbors = 0
                for dy, dx in [(-1,0), (1,0), (0,-1), (0,1)]:
                    if base[y+dy][x+dx] == ' ':
                        empty_neighbors += 1
                
                if empty_neighbors < 4: 
                    continue 
                
                g_char = ground[y][x].lower()
                
                # STRICT RULE: Zombies only on pathways
                if 'dirty' in g_char or 'asphalt' in g_char or 'path' in g_char:
                    pathway_candidates.append((x, y))

        # 2. Calculate Targets [MODIFIED - Fix Global L2 Count]
        # Calculate total chunks based on map dimensions
        chunks_x = w // self.chunk_size
        chunks_y = h // self.chunk_size
        total_chunks = max(1, chunks_x * chunks_y)
        
        # Total zombies for the entire L2 map = Limit Per Chunk * Total Chunks
        total_zombies = ZOMBIE_MAX_CHUNK * total_chunks
        
        # 3. Spawn Zombies on Pathways
        if pathway_candidates:
            count = min(len(pathway_candidates), total_zombies)
            chosen = random.sample(pathway_candidates, count)
            for (zx, zy) in chosen:
                spawn[zy][zx] = 'Z'
                
        print(f"  > Spawning Report L2: {count if pathway_candidates else 0} Zombies on Pathways (Map Limit: {total_zombies}).")

    def _decorate_l2_pathways(self, layers, mask):
        """
        [UPDATED] Decorates L2 pathways with vegetation.
        Uses 'mask' (1=occupied/template, 0=path/void) to prevent spawning inside templates.
        """
        ground = layers.get('ground')
        base = layers.get('base')
        if not ground or not base: return

        h = len(ground)
        w = len(ground[0])
        
        veg_options = ['garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_stone', 'garden_tree_11']

        print("Decorating L2 Pathways with vegetation...")

        for y in range(h):
            for x in range(w):
                # Place only on dirty_01 (Pathways & Padding) and where base is empty
                # AND ensure we are NOT inside a template (mask == 0)
                if ground[y][x] == 'dirty_01' and base[y][x] == ' ' and mask[y][x] == 0:
                    # 15% chance to place random vegetation
                    if random.random() < 0.15:
                        base[y][x] = random.choice(veg_options)

    def _connect_l2_drunkards(self, layers):
        ground = layers.get('ground')
        if not ground: return

        h = len(ground)
        w = len(ground[0])
        
        visited = set()
        components = []

        for y in range(h):
            for x in range(w):
                if (x, y) not in visited and ground[y][x] != ' ':
                    stack = [(x, y)]
                    visited.add((x, y))
                    island_pixels = []
                    while stack:
                        cx, cy = stack.pop()
                        island_pixels.append((cx, cy))
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < w and 0 <= ny < h:
                                if (nx, ny) not in visited and ground[ny][nx] != ' ':
                                    visited.add((nx, ny))
                                    stack.append((nx, ny))
                    if island_pixels:
                        avg_x = sum(p[0] for p in island_pixels) // len(island_pixels)
                        avg_y = sum(p[1] for p in island_pixels) // len(island_pixels)
                        components.append((avg_x, avg_y))

        if len(components) < 2:
            return

        print(f"L2 Processing: Found {len(components)} isolated structures. Connecting via Drunkard's Walk...")

        connected_set = [components[0]]
        unconnected_set = components[1:]

        while unconnected_set:
            best_dist = float('inf')
            best_link = None 

            for c_pos in connected_set:
                for i, u_pos in enumerate(unconnected_set):
                    dist = (c_pos[0] - u_pos[0])**2 + (c_pos[1] - u_pos[1])**2
                    if dist < best_dist:
                        best_dist = dist
                        best_link = (c_pos, i)
            
            if best_link:
                start_pos, u_index = best_link
                target_pos = unconnected_set[u_index]
                self._carve_drunkard_path(layers, start_pos, target_pos)
                connected_set.append(target_pos)
                unconnected_set.pop(u_index)

    def _carve_drunkard_path(self, layers, start, end):
        cx, cy = start
        tx, ty = end
        
        ground = layers['ground']
        base = layers['base']
        h, w = len(ground), len(ground[0])
        
        path_tile = 'dirty_01' 
        border_tile = '@' # Border tile as requested
        
        max_steps = (abs(tx - cx) + abs(ty - cy)) * 5 
        steps = 0
        
        while (cx != tx or cy != ty) and steps < max_steps:
            steps += 1
            
            # Dig with border (Brush size 3x3 for path, 5x5 for border ring)
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        is_core = (abs(dx) <= 2 and abs(dy) <= 2)
                        
                        if is_core:
                            # Core Path: Only modify if tile is currently VOID (' ') or BORDER ('@')
                            # This preserves existing building tiles (like wood, sand, etc.)
                            current_tile = ground[ny][nx]
                            if current_tile == ' ' or current_tile == border_tile:
                                ground[ny][nx] = path_tile
                                
                                # Only clear walls/objects if we are creating a NEW path on void.
                                # If we are walking over an existing template, we leave the base (walls) alone.
                                if base[ny][nx] != ' ':
                                    base[ny][nx] = ' '
                        else:
                            # Border Ring: Only place on void
                            if ground[ny][nx] == ' ':
                                ground[ny][nx] = border_tile
            
            # Move logic (Biased Random Walk)
            dx, dy = 0, 0
            dist_x = tx - cx
            dist_y = ty - cy
            
            choice = random.random()
            
            if choice < 0.4 and dist_x != 0:
                dx = 1 if dist_x > 0 else -1
            elif choice < 0.8 and dist_y != 0:
                dy = 1 if dist_y > 0 else -1
            else:
                if random.random() < 0.5: dx = random.choice([-1, 1])
                else: dy = random.choice([-1, 1])

            cx += dx
            cy += dy
            
            # Clamp bounds (keep 2 tile margin for border safety)
            cx = max(2, min(w - 3, cx))
            cy = max(2, min(h - 3, cy))
            
            if abs(cx - tx) <= 1 and abs(cy - ty) <= 1:
                break

    def _apply_l2_border(self, layers, tx, ty, tmpl_w, tmpl_h, mw, mh):
        ground = layers.get('ground_L2')
        if not ground: return
        
        padding = 4
        border_tile = '@'
        padding_tile = 'dirty_01'
        
        # Determine bounds
        x1 = max(0, tx - padding)
        y1 = max(0, ty - padding)
        x2 = min(mw, tx + tmpl_w + padding)
        y2 = min(mh, ty + tmpl_h + padding)
        
        for y in range(y1, y2):
            for x in range(x1, x2):
                # If outside the building rectangle
                if not (tx <= x < tx + tmpl_w and ty <= y < ty + tmpl_h):
                    # Only overwrite void
                    if ground[y][x] == ' ':
                        # Identify outermost border of the 4-tile padding
                        # We use the CLAMPED bounds (x1, x2) to ensure borders are drawn 
                        # even if the padding area is cut off by the map edge.
                        
                        is_border = False
                        if x == x1 or x == x2 - 1:
                            is_border = True
                        if y == y1 or y == y2 - 1:
                            is_border = True
                        
                        if is_border:
                            ground[y][x] = border_tile
                        else:
                            ground[y][x] = padding_tile