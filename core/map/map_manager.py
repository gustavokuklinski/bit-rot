import os
import re
import pygame
import random
from core.data.config import *
from core.messages import display_message_player
class MapManager:
    def __init__(self, game, map_folder='./game/lib/map'):
        self.game = game
        self.map_folder = map_folder
        self.current_map_filename = 'map_L1_P0_0_1_0_0_map.csv' # Updated default filename
        self.map_files = self._discover_maps()
    
    def refresh_maps(self):
        """Re-scans the map folder and updates the map_files list."""
        print("Refreshing map file list...")
        self.map_files = self._discover_maps()
        print(f"Found {len(self.map_files)} map files.")

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
                        'filename': filename,
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
            print(f"Error: Could not find current map info for {self.current_map_filename}")
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

        if connection_index == -1:
            print(f"Error: Invalid transition direction '{direction}'")
            return None
            
        connection_id = connections[connection_index]
        if connection_id == 0:
            # print("No connection in that direction.")
            return None

        for filename, map_info in self.map_files.items():
            if filename == self.current_map_filename:
                continue
                
            # Check if the target map has a matching connection ID and is on the same layer
            if map_info['connections'][opposite_index] == connection_id and map_info['layer'] == current_layer:
                
                # --- [THIS IS THE FIX] ---
                
                # 1. Update the manager's state to the new map
                self.current_map_filename = filename
                
                # 2. Get the base name (e.g., "map_L1_P0_0_0_0_1")
                base_name = filename.rsplit('_map.csv', 1)[0]
                
                # 3. Construct the other filenames
                ground_filename = f"{base_name}_ground.csv"
                spawn_filename = f"{base_name}_spawn.csv"
                
                # 4. Return all three so the game can fully load them
                print(f"Transitioning to map: {filename}")
                return (filename, ground_filename, spawn_filename)
                # --- [END FIX] ---
        
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
                display_message_player("Player is in the doorway, cannot close.")
                return # Stop the function
        
        base_name = current_char.replace("_open", "").replace("_close", "")
        new_char = f"{base_name}_{new_state}"

        if new_char in self.game.tile_manager.definitions:
            new_def = self.game.tile_manager.definitions[new_char]
            
            # 1. Update the map data
            self.game.map_data[grid_y][grid_x] = new_char
            
            # 2. Update obstacles list
            self.game.obstacles = [rect for rect in self.game.obstacles if rect != tile_rect]
            if new_def['is_obstacle']:
                self.game.obstacles.append(tile_rect)
                
            # 3. Update renderable_tiles list AND gather tiles for redraw in ONE pass.
            # This prevents iterating the massive list twice, eliminating the delay.
            original_image = current_def['image'] 
            tiles_to_redraw = []
            door_updated = False
            
            for i, (img, rect) in enumerate(self.game.renderable_tiles):
                # We only care about tiles at this specific location
                if rect.colliderect(tile_rect):
                    # Check if this is the door we need to update
                    if not door_updated and rect == tile_rect and img == original_image:
                        # Update the main list in-place
                        self.game.renderable_tiles[i] = (new_def['image'], rect)
                        # Add the NEW image to the local redraw list
                        tiles_to_redraw.append((new_def['image'], rect))
                        door_updated = True
                    else:
                        # This is a floor or other overlapping tile; add to redraw list as is
                        tiles_to_redraw.append((img, rect))
            
            # 4. Patch the cache directly using the small gathered list
            if hasattr(self.game, '_tile_cache_surface') and self.game._tile_cache_surface:
                try:
                    origin_x, origin_y = self.game._tile_cache_world_origin
                    
                    cache_rect = pygame.Rect(
                        tile_rect.x - origin_x, 
                        tile_rect.y - origin_y, 
                        tile_rect.width, 
                        tile_rect.height
                    )
                    
                    # Clear the specific spot (erasing old door AND floor)
                    self.game._tile_cache_surface.fill(PANEL_COLOR, cache_rect)
                    
                    # Redraw only the gathered tiles (Floor + New Door)
                    # This loop is now instant because tiles_to_redraw has only ~2 items
                    for img, r in tiles_to_redraw:
                        draw_pos = (r.x - origin_x, r.y - origin_y)
                        self.game._tile_cache_surface.blit(img, draw_pos)
                    
                    self.game.dynamic_tiles_dirty = False
                    
                except Exception as e:
                    print(f"Error patching tile cache: {e}")
                    self.game.dynamic_tiles_dirty = True
            else:
                self.game.dynamic_tiles_dirty = True

            if new_def.get('sound_src'):
                self.game.sound_manager.play_sound(
                    new_def['sound_src'],
                    subdir='map', # As requested: game/lib/sfx/map/
                    game=self.game,
                    source_pos=tile_rect.center,
                    base_volume=random.uniform(0.2, 0.7)
                )

        else:
            print(f"Warning: Could not find matching door state '{new_char}'")