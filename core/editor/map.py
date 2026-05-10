import csv
import os
import pygame

from editor.config import TILE_SIZE

class Map:
    def __init__(self, width, height, default_layers=None):
        self.width = width
        self.height = height
        self.layers = {}
        self.layer_properties = {}
        self.active_layer_name = None
        self.undo_stack = []

        if default_layers is None:
            default_layers = ['light', 'roof','map', 'ground', 'spawn'] 

        self.default_layers = default_layers 

        for layer_name in default_layers:
            self.layers[layer_name] = [[None for _ in range(width)] for _ in range(height)]
            self.layer_properties[layer_name] = {"visible": True, "opacity": 255}
        
        if default_layers:
            self.active_layer_name = default_layers[0]

    def resize(self, new_width, new_height):
        """Resizes the map and all its layers to the new dimensions."""
        self.width = new_width
        self.height = new_height
        
        layers_to_init = self.default_layers if hasattr(self, 'default_layers') else self.layers.keys()
        
        self.layers = {}
        for layer_name in layers_to_init:
            self.layers[layer_name] = [[None for _ in range(new_width)] for _ in range(new_height)]
            if layer_name not in self.layer_properties:
                self.layer_properties[layer_name] = {"visible": True, "opacity": 255}
            
        self.undo_stack.clear()

    def _push_to_undo(self, changes):
        """Internal helper to add a list of changes as a single undo step."""
        if changes:
            self.undo_stack.append(changes)
            
    def undo(self):
        """Undoes the last action."""
        if not self.undo_stack:
            return

        last_changes = self.undo_stack.pop()
        for (x, y, layer_name, old_tile_name) in last_changes:
            self.set_tile(x, y, old_tile_name, layer_name, undoing=True)


    def set_active_layer(self, layer_name):
        if layer_name in self.layers:
            self.active_layer_name = layer_name
        else:
            print(f"Warning: Layer '{layer_name}' does not exist.")

    def get_active_layer_grid(self):
        return self.layers.get(self.active_layer_name)

    def load_from_csv(self, filepath, layer_name):
        if layer_name not in self.layers:
            self.layers[layer_name] = [[None for _ in range(self.width)] for _ in range(self.height)]
            self.layer_properties[layer_name] = {"visible": True, "opacity": 255}

        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            for y, row in enumerate(reader):
                for x, tile in enumerate(row):
                    if x < self.width and y < self.height:
                        self.layers[layer_name][y][x] = tile if tile != '' else None
        
        self.undo_stack.clear()

    def save_to_csv(self, filepath, layer_name):
        if layer_name not in self.layers:
            print(f"Error: Layer '{layer_name}' does not exist to save.")
            return

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            for y in range(self.height):
                row_data = [tile if tile is not None else '' for tile in self.layers[layer_name][y]]
                writer.writerow(row_data)

    def set_tile(self, x, y, tile_name, layer_name=None, undoing=False):
        if layer_name is None:
            layer_name = self.active_layer_name

        if layer_name in self.layers and 0 <= x < self.width and 0 <= y < self.height:
            if not undoing:
                old_tile_name = self.layers[layer_name][y][x]
                if old_tile_name != tile_name:
                    self._push_to_undo([(x, y, layer_name, old_tile_name)])
            
            self.layers[layer_name][y][x] = tile_name
        else:
            pass
    
    def clear_rect(self, rect, layer_name):
        if layer_name not in self.layers:
            return
        
        changes = []
        for y in range(rect.top, rect.top + rect.height):
            for x in range(rect.left, rect.left + rect.width):
                if 0 <= x < self.width and 0 <= y < self.height:
                    old_tile = self.layers[layer_name][y][x]
                    if old_tile is not None:
                        changes.append((x, y, layer_name, old_tile))
                        self.layers[layer_name][y][x] = None
        
        self._push_to_undo(changes)
    
    def fill_rect(self, rect, tile_name, layer_name):
        if layer_name not in self.layers:
            return
        
        changes = []
        for y in range(rect.top, rect.top + rect.height):
            for x in range(rect.left, rect.left + rect.width):
                if 0 <= x < self.width and 0 <= y < self.height:
                    old_tile = self.layers[layer_name][y][x]
                    if old_tile != tile_name:
                        changes.append((x, y, layer_name, old_tile))
                        self.layers[layer_name][y][x] = tile_name
        
        self._push_to_undo(changes)

    def get_tiles_in_rect(self, rect, layer_name):
        if layer_name not in self.layers:
            return None
        
        clipboard = []
        for y in range(rect.top, rect.top + rect.height):
            row = []
            for x in range(rect.left, rect.left + rect.width):
                if 0 <= x < self.width and 0 <= y < self.height:
                    row.append(self.layers[layer_name][y][x])
                else:
                    row.append(None)
            clipboard.append(row)
        return clipboard

    def paste_tiles(self, topleft_coord, clipboard_data, layer_name):
        if layer_name not in self.layers or not clipboard_data:
            return

        start_x, start_y = topleft_coord
        changes = []
        
        for y_offset, row in enumerate(clipboard_data):
            for x_offset, tile_name in enumerate(row):
                
                map_x = start_x + x_offset
                map_y = start_y + y_offset

                if 0 <= map_x < self.width and 0 <= map_y < self.height:
                    old_tile = self.layers[layer_name][map_y][map_x]
                    if old_tile != tile_name:
                        changes.append((map_x, map_y, layer_name, old_tile))
                        self.layers[layer_name][map_y][map_x] = tile_name

        self._push_to_undo(changes)

    def render(self, surface, tiles, font, offset=(0, 0), zoom_scale=1.0):
        scaled_tile_size = int(TILE_SIZE * zoom_scale)
        
        # Render Order: Bottom -> Top
        render_order = ['ground', 'map', 'spawn', 'light', 'roof']

        for layer_name in render_order:
            if layer_name not in self.layers:
                continue
                
            layer_grid = self.layers[layer_name]
            properties = self.layer_properties.get(layer_name, {"visible": True, "opacity": 255})
            if not properties["visible"]:
                continue

            layer_surface = pygame.Surface((self.width * scaled_tile_size, self.height * scaled_tile_size), pygame.SRCALPHA)

            for y in range(self.height):
                for x in range(self.width):
                    tile_name = layer_grid[y][x]
                    if not tile_name:
                        continue

                    tile_rect = pygame.Rect(x * scaled_tile_size, y * scaled_tile_size, scaled_tile_size, scaled_tile_size)

                    if tile_name in tiles:
                        # Items usually have transparency, so this will blend correctly onto the layer surface
                        scaled_image = pygame.transform.scale(tiles[tile_name], (scaled_tile_size, scaled_tile_size))
                        layer_surface.blit(scaled_image, tile_rect.topleft)
                    else:
                        # Fallback for missing textures (including items if 'all_render_tiles' wasn't passed)
                        pygame.draw.rect(layer_surface, (240, 240, 240, 100), tile_rect)
                        text_surf = font.render(tile_name, True, (0, 0, 0))
                        text_rect = text_surf.get_rect(center=tile_rect.center)
                        layer_surface.blit(text_surf, text_rect)
            
            layer_surface.set_alpha(properties["opacity"])
            surface.blit(layer_surface, offset)