import os
import re

from data.config import *

class MapManager:
    def __init__(self, map_folder='game/map'):
        self.map_folder = map_folder
        self.current_map_filename = 'map_L1_P0_0_1_0_0.csv' # Updated default filename
        self.map_files = self._discover_maps()

    def _discover_maps(self):
        maps = {}
        # Regex to match the new naming convention: map_L<layer>_P<position>_<top>_<right>_<bottom>_<left>.csv
        # Example: map_L1_P0_0_1_0_0.csv
        pattern = re.compile(r'map_L(\d+)_P(\d+)_(\d+)_(\d+)_(\d+)_(\d+)\.csv')

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