# core/map/procedural/generator_rendering.py

import os
import csv
import pygame
from core.ui.mobile_map_tab import get_map_pixel_color, MINIMAP_COLORS

class ProceduralGeneratorRendering:
    def export_world_image(self, layer_idx, output_filename):
        """Exports the stitched 128x128 map layer to a JPG image using the unified color palette."""
        def load_csv(path):
            if not os.path.exists(path): return []
            with open(path, 'r', newline='') as f:
                return list(csv.reader(f))

        chunk_w = getattr(self, 'chunk_size', 128)
        chunk_h = getattr(self, 'chunk_size', 128)
        map_w = self.grid_w * chunk_w
        map_h = self.grid_h * chunk_h
        
        scale = 4 
        surf = pygame.Surface((map_w * scale, map_h * scale))
        bg_fill = MINIMAP_COLORS['void_l1'] if layer_idx == 1 else MINIMAP_COLORS['void_caves']
        surf.fill(bg_fill)
        
        tile_defs = getattr(self.game.tile_manager, 'definitions', {}) if hasattr(self.game, 'tile_manager') else {}

        for gy in range(self.grid_h):
            for gx in range(self.grid_w):
                if hasattr(self, 'active_chunks') and (gx, gy) not in self.active_chunks:
                    continue

                base_name = f"map_L{layer_idx}_{gx}_{gy}"
                b_path = os.path.join(self.output_folder, base_name + "_map.csv")
                g_path = os.path.join(self.output_folder, base_name + "_ground.csv")
                r_path = os.path.join(self.output_folder, base_name + "_roof.csv")
                
                b_data = load_csv(b_path)
                g_data = load_csv(g_path)
                r_data = load_csv(r_path)
                
                if not b_data and not g_data:
                    continue
                
                offset_px_x = gx * chunk_w * scale
                offset_px_y = gy * chunk_h * scale

                for y in range(chunk_h):
                    for x in range(chunk_w):
                        g_char = g_data[y][x] if y < len(g_data) and x < len(g_data[y]) else ' '
                        b_char = b_data[y][x] if y < len(b_data) and x < len(b_data[y]) else ' '
                        r_char = r_data[y][x] if y < len(r_data) and x < len(r_data[y]) else ' '

                        color = get_map_pixel_color(g_char, b_char, r_char, tile_defs, layer_idx=layer_idx)
                        rect = (offset_px_x + x * scale, offset_px_y + y * scale, scale, scale)
                        pygame.draw.rect(surf, color, rect)
                        
        out_path = os.path.join(self.output_folder, output_filename)
        try:
            pygame.image.save(surf, out_path)
            print(f"[ProceduralGenerator] Saved map image to {out_path}")
        except Exception as e:
            print(f"[ProceduralGenerator] Failed to save map image: {e}")
            
    def _save_chunk(self, fname, layers):
        for name, data in layers.items():
            suffix = f"_{name}.csv" if name != 'base' else "_map.csv"
            with open(os.path.join(self.output_folder, fname + suffix), 'w', newline='') as f:
                csv.writer(f).writerows(data)

    def _get_adjacent_bg(self, grid, x, y, w, h):
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, 1), (-1, 1), (-1, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                neighbor = grid[ny][nx]
                is_transparent_overlay = neighbor and (
                    neighbor.startswith('dirty_') or 
                    neighbor.startswith('beach_sand_') or 
                    neighbor.startswith('sand_') or 
                    neighbor.startswith('asphalt_')
                )
                if neighbor and not is_transparent_overlay and neighbor != ' ':
                    return neighbor
        return 'bg_grass'

    def _is_transparent_border(self, g_char):
        if not g_char: return False
        if g_char.startswith('dirty_') and g_char != 'dirty_01': return True
        if g_char.startswith('sand_') and g_char != 'sand_01': return True
        if g_char.startswith('beach_sand_') and g_char != 'beach_sand_01': return True
        if g_char.startswith('asphalt_') and g_char != 'asphalt_01': return True
        return False