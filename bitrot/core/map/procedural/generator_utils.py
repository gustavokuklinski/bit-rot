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

    def _blit_template(self, target, source, ox, oy, mw, mh, clear_base=False):
        tw = source.get('width', len(source['base'][0]) if source.get('base') and source['base'] else 0)
        th = source.get('height', len(source['base']) if source.get('base') else 0)

        for layer in ['base', 'light', 'ground', 'spawn', 'roof']:
            if layer not in source: continue
            grid = source[layer]
            for r in range(len(grid)):
                for c in range(len(grid[r])):
                    tile = grid[r][c]
                    gx, gy = ox + c, oy + r
                    if 0 <= gx < mw and 0 <= gy < mh:
                        if layer == 'base':
                            if clear_base:
                                # Overwrite base completely so trees, rocks, and walls are cleared
                                target[layer][gy][gx] = tile if (tile and tile != '') else ' '
                            else:
                                if tile and tile != ' ':
                                    target[layer][gy][gx] = tile
                        elif layer == 'ground':
                            if tile and tile != ' ' and tile != '':
                                target[layer][gy][gx] = tile
                        else:
                            if tile and tile != ' ':
                                target[layer][gy][gx] = tile

                        if 'protected_mask' in target:
                            target['protected_mask'][gy][gx] = 1

    def _blit_template_mapped(self, target_layers, source_tmpl, tx, ty, mw, mh, suffix=''):
        mask_key = 'protected_mask' + suffix
        if mask_key not in target_layers:
            target_layers[mask_key] = [[0 for _ in range(mw)] for _ in range(mh)]

        for layer in ['base', 'light', 'ground', 'spawn', 'roof']:
            if layer not in source_tmpl: continue
            target_key = layer + suffix 
            if target_key not in target_layers:
                 target_layers[target_key] = [[' ' for _ in range(mw)] for _ in range(mh)]
            grid = source_tmpl[layer]

            for r in range(len(grid)):
                for c in range(len(grid[r])):
                    tile = grid[r][c]
                    gx, gy = tx + c, ty + r
                    if 0 <= gx < mw and 0 <= gy < mh:
                        if layer == 'base':
                            target_layers[target_key][gy][gx] = tile if (tile and tile != '') else ' '
                        elif layer == 'ground':
                            if tile and tile != ' ' and tile != '':
                                target_layers[target_key][gy][gx] = tile
                        else:
                            if tile and tile != ' ':
                                target_layers[target_key][gy][gx] = tile
                        target_layers[mask_key][gy][gx] = 1

        tw = source_tmpl.get('width', 0)
        th = source_tmpl.get('height', 0)
        for r in range(th):
            for c in range(tw):
                gx, gy = tx + c, ty + r
                if 0 <= gx < mw and 0 <= gy < mh:
                    target_layers[mask_key][gy][gx] = 1

    def _apply_terrain_smoothing(self, global_layers, w, h):
        ground = global_layers['ground']
        protected = global_layers.get('protected_mask')

        def is_dirt(x, y):
            if x < 0 or x >= w or y < 0 or y >= h:
                return True
            return ground[y][x].startswith('dirty')

        changes = {}
        tile_map = {
            0: 'dirty_01', 1: 'dirty_top_01', 2: 'dirty_left_01', 4: 'dirty_bottom_01',
            8: 'dirty_right_01', 3: 'dirty_top_left_01', 6: 'dirty_bottom_left_01',
            9: 'dirty_top_right_01', 12: 'dirty_bottom_right_01', 5: 'dirty_01',
            10: 'dirty_01', 7: 'dirty_01', 11: 'dirty_01', 13: 'dirty_01',
            14: 'dirty_01', 15: 'dirty_01'
        }

        for y in range(h):
            for x in range(w):
                if ground[y][x] == 'dirty_01':
                    if protected and protected[y][x] == 1:
                        continue
                    t = 0 if is_dirt(x, y - 1) else 1
                    r = 0 if is_dirt(x + 1, y) else 2
                    b = 0 if is_dirt(x, y + 1) else 4
                    l = 0 if is_dirt(x - 1, y) else 8
                    mask = t + r + b + l
                    new_tile = tile_map.get(mask, 'dirty_01')
                    if new_tile != 'dirty_01':
                        changes[(x, y)] = new_tile
                        
        for (x, y), tile in changes.items():
            ground[y][x] = tile
    
    def _apply_sand_smoothing(self, global_layers, w, h, base_sand):
        ground = global_layers['ground']
        protected = global_layers.get('protected_mask')
        prefix = base_sand.replace('_01', '') 
        
        def is_sand_or_water(x, y):
            if x < 0 or x >= w or y < 0 or y >= h:
                return True
            tile = ground[y][x]
            return tile.startswith('sand_') or tile.startswith('beach_sand_')

        changes = {}
        tile_map = {
            0: f'{prefix}_01', 1: f'{prefix}_top_01', 2: f'{prefix}_left_01',
            4: f'{prefix}_bottom_01', 8: f'{prefix}_right_01', 3: f'{prefix}_top_left_01',
            6: f'{prefix}_bottom_left_01', 9: f'{prefix}_top_right_01', 12: f'{prefix}_bottom_right_01',
            5: f'{prefix}_01', 10: f'{prefix}_01', 7: f'{prefix}_01', 11: f'{prefix}_01',
            13: f'{prefix}_01', 14: f'{prefix}_01', 15: f'{prefix}_01'
        }

        for y in range(h):
            for x in range(w):
                if ground[y][x] == base_sand:
                    if protected and protected[y][x] == 1:
                        continue
                    t = 0 if is_sand_or_water(x, y - 1) else 1
                    r = 0 if is_sand_or_water(x + 1, y) else 2
                    b = 0 if is_sand_or_water(x, y + 1) else 4
                    l = 0 if is_sand_or_water(x - 1, y) else 8
                    mask = t + r + b + l
                    new_tile = tile_map.get(mask, base_sand)
                    if new_tile != base_sand:
                        changes[(x, y)] = new_tile
                        
        for (x, y), tile in changes.items():
            ground[y][x] = tile

    def _apply_asphalt_smoothing(self, global_layers, w, h):
        ground = global_layers['ground']
        base = global_layers['base']
        protected = global_layers.get('protected_mask')
        
        def is_asphalt_or_no_border(x, y):
            if x < 0 or x >= w or y < 0 or y >= h:
                return True
            if protected and protected[y][x] == 1:
                return True
            if base[y][x] != ' ':
                return True
            tile = ground[y][x]
            return (tile.startswith('asphalt_') or tile.startswith('beach_sand_') or tile.startswith('water_'))

        changes = {}
        tile_map = {
            0: 'asphalt_01', 1: 'asphalt_top_01', 2: 'asphalt_left_01',
            4: 'asphalt_bottom_01', 8: 'asphalt_right_01', 3: 'asphalt_top_left_01',
            6: 'asphalt_bottom_left_01', 9: 'asphalt_top_right_01', 12: 'asphalt_bottom_right_01',
            5: 'asphalt_01', 10: 'asphalt_01', 7: 'asphalt_01', 11: 'asphalt_01',
            13: 'asphalt_01', 14: 'asphalt_01', 15: 'asphalt_01'
        }

        for y in range(h):
            for x in range(w):
                if ground[y][x] == 'asphalt_01':
                    if protected and protected[y][x] == 1:
                        continue
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