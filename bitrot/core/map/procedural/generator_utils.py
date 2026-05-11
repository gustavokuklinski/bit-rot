# core/map/procedural/generator_utils.py

import os
import csv
import pygame

class ProceduralGeneratorUtils:
    def _maps_exist(self, expected_count):
        if not os.path.exists(self.output_folder): return False
        for f in os.listdir(self.output_folder):
            if f.startswith("map_L1_") and f.endswith("_map.csv"):
                return True
        return False

    def _extract_chunk(self, global_layers, gx, gy):
        """Extracts a self.chunk_size x self.chunk_size grid from the global layers."""
        chunk_layers = {}
        offset_x = gx * self.chunk_size
        offset_y = gy * self.chunk_size
        
        for layer_name, global_grid in global_layers.items():
            chunk_grid = []
            for r in range(self.chunk_size):
                row = global_grid[offset_y + r][offset_x : offset_x + self.chunk_size]
                chunk_grid.append(row)
            chunk_layers[layer_name] = chunk_grid
            
        return chunk_layers

    def _blit_template(self, target, source, ox, oy, mw, mh):
        for layer in ['base', 'light', 'ground', 'spawn', 'roof']:
            if layer not in source: continue
            grid = source[layer]
            for r in range(len(grid)):
                for c in range(len(grid[r])):
                    tile = grid[r][c]
                    if tile and tile != ' ':
                        gx, gy = ox + c, oy + r
                        if 0 <= gx < mw and 0 <= gy < mh:
                            target[layer][gy][gx] = tile

                            if layer == 'ground' and 'protected_mask' in target:
                                target['protected_mask'][gy][gx] = 1

    def _blit_template_mapped(self, target_layers, source_tmpl, tx, ty, mw, mh, suffix=''):
        for layer in ['base', 'light', 'ground', 'spawn', 'roof']:
            if layer not in source_tmpl: continue
            target_key = layer + suffix 
            if target_key not in target_layers:
                 target_layers[target_key] = [[' ' for _ in range(mw)] for _ in range(mh)]
            grid = source_tmpl[layer]

            mask_key = 'protected_mask' + suffix
            if mask_key not in target_layers:
                 target_layers[mask_key] = [[0 for _ in range(mw)] for _ in range(mh)]

            for r in range(len(grid)):
                for c in range(len(grid[r])):
                    tile = grid[r][c]
                    if tile and tile != ' ':
                        gx, gy = tx + c, ty + r
                        if 0 <= gx < mw and 0 <= gy < mh:
                            target_layers[target_key][gy][gx] = tile

                            if layer == 'ground':
                                target_layers[mask_key][gy][gx] = 1

    def _apply_terrain_smoothing(self, global_layers, w, h):
        """
        Post-processing pass to auto-tile dirt paths using a 4-bit bitmask approach.
        """
        ground = global_layers['ground']
        protected = global_layers.get('protected_mask')

        def is_dirt(x, y):
            # Treat out-of-bounds map edges as dirt so borders don't cut off abruptly
            if x < 0 or x >= w or y < 0 or y >= h:
                return True
            return ground[y][x].startswith('dirty')

        changes = {}
        
        # BITMASK LOGIC:
        # Top=1, Right=2, Bottom=4, Left=8
        # The number represents where the GRASS (non-dirt) is touching the dirt tile.
        
        tile_map = {
            # --- SOLID DIRT ---
            0: 'dirty_01',               
            1: 'dirty_top_01',           
            2: 'dirty_left_01',         
            4: 'dirty_bottom_01',        
            8: 'dirty_right_01',          
            3: 'dirty_top_left_01',     
            6: 'dirty_bottom_left_01',  
            9: 'dirty_top_right_01',      
            12: 'dirty_bottom_right_01',  
            
            5: 'dirty_01',               
            10: 'dirty_01',              
            7: 'dirty_01',               
            11: 'dirty_01',              
            13: 'dirty_01',              
            14: 'dirty_01',              
            15: 'dirty_01'               
        }

        for y in range(h):
            for x in range(w):
                if ground[y][x] == 'dirty_01':

                    if protected and protected[y][x] == 1:
                        continue

                    # 1 if neighbor is GRASS, 0 if it is DIRT
                    t = 0 if is_dirt(x, y - 1) else 1
                    r = 0 if is_dirt(x + 1, y) else 2
                    b = 0 if is_dirt(x, y + 1) else 4
                    l = 0 if is_dirt(x - 1, y) else 8
                    
                    mask = t + r + b + l
                    new_tile = tile_map.get(mask, 'dirty_01')
                    
                    if new_tile != 'dirty_01':
                        changes[(x, y)] = new_tile
                        
        # Apply all smoothed edges simultaneously
        for (x, y), tile in changes.items():
            ground[y][x] = tile
    
    def _apply_sand_smoothing(self, global_layers, w, h, base_sand):
        """
        Post-processing pass to auto-tile sand using a 4-bit bitmask approach.
        Uses the INVERTED Left/Right naming conventions (matches dirty_01).
        Supports multiple sand types (e.g., 'sand_01' and 'beach_sand_01').
        """
        ground = global_layers['ground']
        protected = global_layers.get('protected_mask')
        prefix = base_sand.replace('_01', '') 
        
        def is_sand_or_water(x, y):
            # Treat out-of-bounds map edges as sand so borders don't cut off abruptly
            if x < 0 or x >= w or y < 0 or y >= h:
                return True
            tile = ground[y][x]
            # We don't want grass borders drawing between ANY sand or water!
            return tile.startswith('sand_') or tile.startswith('beach_sand_')

        changes = {}
        
        # BITMASK LOGIC: Top=1, Right=2, Bottom=4, Left=8
        # INVERTED MAPPING: (Left/Right are swapped, just like dirty_01)
        tile_map = {
            # --- SOLID SAND ---
            0: f'{prefix}_01',               
            1: f'{prefix}_top_01',           
            2: f'{prefix}_left_01',         
            4: f'{prefix}_bottom_01',        
            8: f'{prefix}_right_01',          
            
            3: f'{prefix}_top_left_01',     
            6: f'{prefix}_bottom_left_01',  
            9: f'{prefix}_top_right_01',      
            
            12: f'{prefix}_bottom_right_01',  
            
            5: f'{prefix}_01',               
            10: f'{prefix}_01',              
            7: f'{prefix}_01',               
            11: f'{prefix}_01',              
            13: f'{prefix}_01',              
            14: f'{prefix}_01',              
            15: f'{prefix}_01'               
        }

        for y in range(h):
            for x in range(w):
                if ground[y][x] == base_sand:
                    if protected and protected[y][x] == 1:
                        continue

                    # 1 if neighbor is GRASS, 0 if it is SAND or WATER
                    t = 0 if is_sand_or_water(x, y - 1) else 1
                    r = 0 if is_sand_or_water(x + 1, y) else 2
                    b = 0 if is_sand_or_water(x, y + 1) else 4
                    l = 0 if is_sand_or_water(x - 1, y) else 8
                    
                    mask = t + r + b + l
                    new_tile = tile_map.get(mask, base_sand)
                    
                    if new_tile != base_sand:
                        changes[(x, y)] = new_tile
                        
        # Apply all smoothed edges simultaneously
        for (x, y), tile in changes.items():
            ground[y][x] = tile

    # [UPDATED] Apply auto-tiling borders to Asphalt exactly like Dirt and Sand
    def _apply_asphalt_smoothing(self, global_layers, w, h):
        ground = global_layers['ground']
        base = global_layers['base']
        protected = global_layers.get('protected_mask')
        
        def is_asphalt_or_no_border(x, y):
            if x < 0 or x >= w or y < 0 or y >= h:
                return True
                
            # If the adjacent tile is part of a building template or an obstacle, treat as seamless
            if protected and protected[y][x] == 1:
                return True
            if base[y][x] != ' ':
                return True
                
            tile = ground[y][x]
            # Treat water and beach_sand as if they are asphalt to prevent drawing the grass border
            return (tile.startswith('asphalt_') or 
                    tile.startswith('beach_sand_') or 
                    tile.startswith('water_'))

        changes = {}
        
        # BITMASK LOGIC: Top=1, Right=2, Bottom=4, Left=8
        tile_map = {
            0: 'asphalt_01',               
            1: 'asphalt_top_01',           
            2: 'asphalt_left_01',         
            4: 'asphalt_bottom_01',        
            8: 'asphalt_right_01',          
            
            3: 'asphalt_top_left_01',     
            6: 'asphalt_bottom_left_01',  
            9: 'asphalt_top_right_01',      
            
            12: 'asphalt_bottom_right_01',  
            
            5: 'asphalt_01',               
            10: 'asphalt_01',              
            7: 'asphalt_01',               
            11: 'asphalt_01',              
            13: 'asphalt_01',              
            14: 'asphalt_01',              
            15: 'asphalt_01'               
        }

        for y in range(h):
            for x in range(w):
                if ground[y][x] == 'asphalt_01':
                    if protected and protected[y][x] == 1:
                        continue

                    # 1 if neighbor requires a grass border (grass, dirt, sand), 0 if it is ASPHALT, BEACH_SAND, WATER, or BUILDING
                    t = 0 if is_asphalt_or_no_border(x, y - 1) else 1
                    r = 0 if is_asphalt_or_no_border(x + 1, y) else 2
                    b = 0 if is_asphalt_or_no_border(x, y + 1) else 4
                    l = 0 if is_asphalt_or_no_border(x - 1, y) else 8
                    
                    mask = t + r + b + l
                    new_tile = tile_map.get(mask, 'asphalt_01')
                    
                    if new_tile != 'asphalt_01':
                        changes[(x, y)] = new_tile
                        
        for (x, y), tile in changes.items():
            ground[y][x] = tile