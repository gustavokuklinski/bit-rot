# core/map/procedural/generator_rendering.py

import os
import csv
import pygame

class ProceduralGeneratorRendering:
    def export_world_image(self, layer_idx, output_filename):
        """Exports the entire stitched map layer to a JPG image."""
        chunk_w = getattr(self, 'chunk_size', 128)
        chunk_h = getattr(self, 'chunk_size', 128)
        map_w = self.grid_w * chunk_w
        map_h = self.grid_h * chunk_h
        
        # Scale defines pixels per tile (e.g., 4x4 pixels = 1 tile)
        scale = 4 
        surf = pygame.Surface((map_w * scale, map_h * scale))
        surf.fill((30, 30, 30))
        
        def load_csv(path):
            if not os.path.exists(path): return []
            with open(path, 'r', newline='') as f:
                return list(csv.reader(f))
                
        for gy in range(self.grid_h):
            for gx in range(self.grid_w):
                base_name = f"map_L{layer_idx}_{gx}_{gy}"
                b_path = os.path.join(self.output_folder, base_name + "_map.csv")
                g_path = os.path.join(self.output_folder, base_name + "_ground.csv")
                r_path = os.path.join(self.output_folder, base_name + "_roof.csv")
                
                b_data = load_csv(b_path)
                g_data = load_csv(g_path)
                r_data = load_csv(r_path)
                
                if not b_data and not g_data:
                    continue
                
                for y in range(chunk_h):
                    for x in range(chunk_w):
                        color = (30, 30, 30)
                        
                        g_char = g_data[y][x] if y < len(g_data) and x < len(g_data[y]) else ' '
                        b_char = b_data[y][x] if y < len(b_data) and x < len(b_data[y]) else ' '
                        r_char = r_data[y][x] if y < len(r_data) and x < len(r_data[y]) else ' '
                        
                        # Interpret Ground
                        if g_char != ' ':
                            g_low = g_char.lower()
                            if 'water' in g_low: color = (30, 144, 255)
                            elif 'sand' in g_low: color = (238, 214, 175)
                            elif 'dirty' in g_low: color = (139, 69, 19)
                            elif 'asphalt' in g_low or 'road' in g_low: color = (80, 80, 80)
                            elif 'grass' in g_low: color = (34, 139, 34)
                            elif 'cave' in g_low: color = (60, 50, 40)
                            else: color = (100, 100, 100)
                            
                        # Interpret Obstacles / Walls
                        if b_char != ' ':
                            b_low = b_char.lower()
                            if b_char in ['@', '#'] or 'wall' in b_low: color = (150, 150, 150)
                            elif 'tree' in b_low: color = (20, 80, 20)
                            else: color = (120, 120, 120)
                            
                        # Interpret Roofs
                        if r_char != ' ':
                            color = (70, 70, 70)
                            
                        rect = ((gx * chunk_w + x) * scale, (gy * chunk_h + y) * scale, scale, scale)
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
        """Helper to find the adjacent solid terrain (grass, sand, etc.) to fill transparent gaps."""
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                neighbor = grid[ny][nx]
                # Ignore ALL pathway overlays when looking for the solid base ground
                is_transparent_overlay = neighbor and (
                    neighbor.startswith('dirty_') or 
                    neighbor.startswith('beach_sand_') or 
                    neighbor.startswith('sand_') or 
                    neighbor.startswith('asphalt_')
                )
                if neighbor and not is_transparent_overlay and neighbor != ' ':
                    return neighbor
        return 'bg_grass' # Fallback if totally isolated

    def _is_transparent_border(self, g_char):
        """Returns True if the tile is a rounded border tile needing an underlay."""
        if not g_char: return False
        if g_char.startswith('dirty_') and g_char != 'dirty_01': return True
        if g_char.startswith('sand_') and g_char != 'sand_01': return True
        if g_char.startswith('beach_sand_') and g_char != 'beach_sand_01': return True
        if g_char.startswith('asphalt_') and g_char != 'asphalt_01': return True
        return False

    def _render_chunk_to_surface(self, bg_surf, heat_surf, gx, gy, data):
        if not hasattr(self.game, 'tile_manager'): return
        defs = self.game.tile_manager.definitions
        
        ox = gx * self.chunk_size * self.tile_size
        oy = gy * self.chunk_size * self.tile_size
        
        ground = data.get('ground', [])
        base = data.get('base', [])
        roof = data.get('roof', [])
        light = data.get('light', [])
        spawn = data.get('spawn', [])
        
        h = len(ground) if ground else self.chunk_size
        w = len(ground[0]) if ground and h > 0 else self.chunk_size

        for y in range(h):
            for x in range(w):
                px = ox + x * self.tile_size
                py = oy + y * self.tile_size
                
                if ground:
                    g_char = ground[y][x]
                    
                    # --- UPDATED LOGIC: Smart Underlay for Transparent Borders ---
                    if self._is_transparent_border(g_char):
                        bg_tile = self._get_adjacent_bg(ground, x, y, w, h)
                        if bg_tile in defs:
                            bg_surf.blit(defs[bg_tile]['image'], (px, py))
                    # ---------------------------------------------------------
                    
                    if g_char in defs: 
                        bg_surf.blit(defs[g_char]['image'], (px, py))
                
                if base:
                    b_char = base[y][x]
                    if b_char in defs and b_char != ' ': 
                        bg_surf.blit(defs[b_char]['image'], (px, py))
                
                if roof:
                    r_char = roof[y][x]
                    if r_char in defs and r_char != ' ':
                        bg_surf.blit(defs[r_char]['image'], (px, py))
                
                if light:
                    l_char = light[y][x]
                    if l_char in defs and l_char != ' ':
                        bg_surf.blit(defs[l_char]['image'], (px, py))
                
                if spawn:
                    s_char = spawn[y][x]
                    # [CHANGED] Added 'SNPC' and 'QNPC'
                    if s_char in ['Z', 'P', 'I', 'NPC', 'SNPC', 'QNPC', 'VEH', 'ANM']:
                        color = (0, 0, 0)
                        if s_char == 'Z': color = (255, 0, 0)
                        elif s_char == 'P': color = (0, 255, 0)
                        elif s_char == 'I': color = (0, 0, 255)
                        elif s_char == 'NPC': color = (255, 255, 0)        # Hostile (Yellow)
                        elif s_char == 'SNPC': color = (0, 200, 255)       # Static (Light Blue)
                        elif s_char == 'QNPC': color = (0, 255, 128)       # Quest (Mint Green)
                        elif s_char == 'VEH': color = (255, 165, 0) 
                        elif s_char == 'ANM': color = (255, 0, 255) 
                        pygame.draw.rect(heat_surf, color, (px, py, self.tile_size, self.tile_size))

    def _render_full_map_to_surface(self, bg_surf, heat_surf, layers):
        """Renders the entire global map dictionary to the surface."""
        if not hasattr(self.game, 'tile_manager'): return
        defs = self.game.tile_manager.definitions
        
        ground = layers.get('ground', [])
        base = layers.get('base', [])
        roof = layers.get('roof', [])
        light = layers.get('light', [])
        spawn = layers.get('spawn', [])
        
        if not ground: return
        
        h = len(ground)
        w = len(ground[0])

        for y in range(h):
            for x in range(w):
                px = x * self.tile_size
                py = y * self.tile_size
                
                # Ground
                if ground:
                    g_char = ground[y][x]
                    
                    # --- UPDATED LOGIC: Smart Underlay for Transparent Borders ---
                    if self._is_transparent_border(g_char):
                        bg_tile = self._get_adjacent_bg(ground, x, y, w, h)
                        if bg_tile in defs:
                            bg_surf.blit(defs[bg_tile]['image'], (px, py))
                    # ---------------------------------------------------------
                            
                    if g_char in defs: 
                        bg_surf.blit(defs[g_char]['image'], (px, py))
                
                # Base
                if base:
                    b_char = base[y][x]
                    if b_char in defs and b_char != ' ': 
                        bg_surf.blit(defs[b_char]['image'], (px, py))
                
                # Roof
                if roof:
                    r_char = roof[y][x]
                    if r_char in defs and r_char != ' ':
                        bg_surf.blit(defs[r_char]['image'], (px, py))
                
                # Light
                if light:
                    l_char = light[y][x]
                    if l_char in defs and l_char != ' ':
                        bg_surf.blit(defs[l_char]['image'], (px, py))
                
                # Heatmap (Spawns)
                if spawn:
                    s_char = spawn[y][x]
                    # [CHANGED] Added 'SNPC' and 'QNPC'
                    if s_char in ['Z', 'P', 'I', 'NPC', 'SNPC', 'QNPC', 'VEH', 'ANM']:
                        color = (0, 0, 0)
                        if s_char == 'Z': color = (255, 0, 0)
                        elif s_char == 'P': color = (0, 255, 0)
                        elif s_char == 'I': color = (0, 0, 255)
                        elif s_char == 'NPC': color = (255, 255, 0)        # Hostile (Yellow)
                        elif s_char == 'SNPC': color = (0, 200, 255)       # Static (Light Blue)
                        elif s_char == 'QNPC': color = (0, 255, 128)       # Quest (Mint Green)
                        elif s_char == 'VEH': color = (255, 165, 0) 
                        elif s_char == 'ANM': color = (255, 0, 255) 
                        pygame.draw.rect(heat_surf, color, (px, py, self.tile_size, self.tile_size))