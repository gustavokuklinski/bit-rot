
# editor/map.py
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

        if default_layers is None:
            default_layers = ['map', 'ground', 'spawn'] # Default layers

        for layer_name in default_layers:
            self.layers[layer_name] = [[None for _ in range(width)] for _ in range(height)]
            self.layer_properties[layer_name] = {"visible": True, "opacity": 255}
        
        if default_layers:
            self.active_layer_name = default_layers[0]

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
                        self.layers[layer_name][y][x] = tile if tile != '' else None # Store empty strings as None

    def save_to_csv(self, filepath, layer_name):
        if layer_name not in self.layers:
            print(f"Error: Layer '{layer_name}' does not exist to save.")
            return

        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            for y in range(self.height):
                row_data = [tile if tile is not None else '' for tile in self.layers[layer_name][y]]
                writer.writerow(row_data)

    def set_tile(self, x, y, tile_name, layer_name=None):
        if layer_name is None:
            layer_name = self.active_layer_name

        if layer_name in self.layers and 0 <= x < self.width and 0 <= y < self.height:
            self.layers[layer_name][y][x] = tile_name
        else:
            print(f"Error: Cannot set tile. Layer '{layer_name}' not found or coordinates out of bounds.")

    def render(self, surface, tiles, font, offset=(0, 0), zoom_scale=1.0):
        scaled_tile_size = int(TILE_SIZE * zoom_scale)

        for layer_name, layer_grid in self.layers.items():
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
                        scaled_image = pygame.transform.scale(tiles[tile_name], (scaled_tile_size, scaled_tile_size))
                        layer_surface.blit(scaled_image, tile_rect.topleft)
                    else:
                        # If not a regular tile, render as text (for Z, P, I, etc.)
                        pygame.draw.rect(layer_surface, (240, 240, 240, 100), tile_rect) # Draw a light grey background for visibility
                        text_surf = font.render(tile_name, True, (0, 0, 0))
                        text_rect = text_surf.get_rect(center=tile_rect.center)
                        layer_surface.blit(text_surf, text_rect)
            
            layer_surface.set_alpha(properties["opacity"])
            surface.blit(layer_surface, offset)
