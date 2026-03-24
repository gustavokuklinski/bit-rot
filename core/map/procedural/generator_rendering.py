# core/map/procedural/generator_rendering.py

import os
import csv
import pygame

class ProceduralGeneratorRendering:
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