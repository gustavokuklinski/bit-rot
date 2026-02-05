import os
import csv
import pygame

class ProceduralGeneratorRendering:
    def _save_chunk(self, fname, layers):
        for name, data in layers.items():
            suffix = f"_{name}.csv" if name != 'base' else "_map.csv"
            with open(os.path.join(self.output_folder, fname + suffix), 'w', newline='') as f:
                csv.writer(f).writerows(data)

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
                    if s_char in ['Z', 'P', 'I', 'NPC', 'S']:
                        color = (0, 0, 0)
                        if s_char == 'Z': color = (255, 0, 0)
                        elif s_char == 'P': color = (0, 255, 0)
                        elif s_char == 'I': color = (0, 0, 255)
                        elif s_char == 'NPC': color = (255, 255, 0)
                        elif s_char == 'S': color = (0, 0, 255) 
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
                    if s_char in ['Z', 'P', 'I', 'NPC', 'S']:
                        color = (0, 0, 0)
                        if s_char == 'Z': color = (255, 0, 0)
                        elif s_char == 'P': color = (0, 255, 0)
                        elif s_char == 'I': color = (0, 0, 255)
                        elif s_char == 'NPC': color = (255, 255, 0)
                        elif s_char == 'S': color = (0, 0, 255)
                        pygame.draw.rect(heat_surf, color, (px, py, self.tile_size, self.tile_size))