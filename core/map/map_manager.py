import os
import re
import pygame
from data.config import *

class MapManager:
    def __init__(self, game, map_folder='game/map'):
        self.game = game
        self.map_folder = map_folder
        self.current_map_filename = 'map_L1_P0_0_1_0_0_map.csv' # Updated default filename
        self.map_files = self._discover_maps()

    def _discover_maps(self):
        maps = {}
        # Regex to match the new naming convention: map_L<layer>_P<position>_<top>_<right>_<bottom>_<left>_map.csv
        # Example: map_L1_P0_0_1_0_0_map.csv
        pattern = re.compile(r'map_L(\d+)_P(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_map\.csv')

        for filename in os.listdir(self.map_folder):
            match = pattern.match(filename)
            if match:
                try:
                    layer = int(match.group(1))
                    position = int(match.group(2))
                    connections = tuple(int(x) for x in match.groups()[2:])
                    maps[filename] = {
                        'layer': layer,
                        'position': position,
                        'connections': connections
                    }
                except ValueError:
                    print(f"Warning: Could not parse map filename {filename}")
        return maps

    def get_current_map_connections(self):
        map_info = self.map_files.get(self.current_map_filename)
        return map_info['connections'] if map_info else None

    def transition(self, direction):
        current_map_info = self.map_files.get(self.current_map_filename)
        if not current_map_info:
            return None

        connections = current_map_info['connections']
        current_layer = current_map_info['layer']

        connection_index = -1
        opposite_index = -1
        if direction == 'top':
            connection_index = 0
            opposite_index = 2 # bottom
        elif direction == 'right':
            connection_index = 1
            opposite_index = 3 # left
        elif direction == 'bottom':
            connection_index = 2
            opposite_index = 0 # top
        elif direction == 'left':
            connection_index = 3
            opposite_index = 1 # right

        connection_id = connections[connection_index]
        if connection_id == 0:
            return None

        for filename, map_info in self.map_files.items():
            if filename == self.current_map_filename:
                continue
            # Check if the target map has a matching connection ID and is on the same layer
            if map_info['connections'][opposite_index] == connection_id and map_info['layer'] == current_layer:
                self.current_map_filename = filename
                return filename
        
        print(f"Warning: No map found for transition '{direction}' from {self.current_map_filename}")
        return None

    def get_tile_at(self, grid_x, grid_y):
        """Gets the tile definition at a specific grid coordinate."""
        if 0 <= grid_y < len(self.game.map_data) and 0 <= grid_x < len(self.game.map_data[0]):
            char = self.game.map_data[grid_y][grid_x]
            if char in self.game.tile_manager.definitions:
                # Return the definition dictionary
                return self.game.tile_manager.definitions[char]
        return None

    def toggle_door_state(self, grid_x, grid_y):
        """Toggles a 'statable' tile (like a door) between its states."""
        current_char = self.game.map_data[grid_y][grid_x]
        current_def = self.game.tile_manager.definitions.get(current_char)

        if not current_def or not current_def.get('is_statable'):
            return

        current_state = current_def.get('state')
        new_state = "open" if current_state == "close" else "close"


        tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

        # Check if we are trying to close the door
        if new_state == "close":
            # Check if the player's collision box is overlapping with the tile
            if self.game.player.rect.colliderect(tile_rect):
                print("Player is in the doorway, cannot close.")
                return # Stop the function
        # Assumes naming convention: "char_name_close" <-> "char_name_open"
        base_name = current_char.replace("_open", "").replace("_close", "")
        new_char = f"{base_name}_{new_state}"

        if new_char in self.game.tile_manager.definitions:
            new_def = self.game.tile_manager.definitions[new_char]
            
            # 1. Update the map data (this is persistent for this layer)
            self.game.map_data[grid_y][grid_x] = new_char
            
            # 2. Update obstacles list
            tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            
            # Remove any matching rect first (handles both cases)
            self.game.obstacles = [rect for rect in self.game.obstacles if rect != tile_rect]
            
            # Add back if the new state is an obstacle
            if new_def['is_obstacle']:
                self.game.obstacles.append(tile_rect)
                
            # 3. Update renderable_tiles list
            original_image = current_def['image'] 
            
            for i, (img, rect) in enumerate(self.game.renderable_tiles):
                # Check for both rect AND the original image
                if rect == tile_rect and img == original_image: 
                    # Found the exact tile (e.g., the closed door, not the floor beneath it)
                    self.game.renderable_tiles[i] = (new_def['image'], rect)
                    break
        else:
            print(f"Warning: Could not find matching door state '{new_char}'")