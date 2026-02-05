import os
import csv
import pygame

class ProceduralGeneratorUtils:
    def _maps_exist(self, expected_count):
        if not os.path.exists(self.output_folder): return False
        for f in os.listdir(self.output_folder):
            if f.startswith("map_L1_world") and f.endswith("_map.csv"):
                return True
        return False

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

    def _blit_template_mapped(self, target_layers, source_tmpl, tx, ty, mw, mh, suffix=''):
        for layer in ['base', 'light', 'ground', 'spawn', 'roof']:
            if layer not in source_tmpl: continue
            target_key = layer + suffix 
            if target_key not in target_layers:
                 target_layers[target_key] = [[' ' for _ in range(mw)] for _ in range(mh)]
            grid = source_tmpl[layer]
            for r in range(len(grid)):
                for c in range(len(grid[r])):
                    tile = grid[r][c]
                    if tile and tile != ' ':
                        gx, gy = tx + c, ty + r
                        if 0 <= gx < mw and 0 <= gy < mh:
                            target_layers[target_key][gy][gx] = tile