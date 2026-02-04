import os
import re
import csv
import pygame
import random
import time
from core.data.config import *
from core.messages import display_message_player
from core.entities.item.item import Item
from core.placement import find_free_tile

class MapManager:
    def __init__(self, game, map_folder='./game/lib/map'):
        self.game = game
        self.map_folder = map_folder
        self.current_map_filename = 'map_L1_world_map.csv' 
        self.map_files = self._discover_maps()
        self.shaking_tiles = {}

    def refresh_maps(self):
        """Re-scans the map folder and updates the map_files list."""
        print("Refreshing map file list...")
        self.map_files = self._discover_maps()
        print(f"Found {len(self.map_files)} map files.")


    def _discover_maps(self):
        maps = {}
        # Regex for single world map: map_L<layer>_world_map.csv
        pattern_world = re.compile(r'map_L(\d+)_world_map\.csv')

        if not os.path.exists(self.map_folder):
            print(f"Warning: Map folder '{self.map_folder}' does not exist.")
            return maps

        for filename in os.listdir(self.map_folder):
            match = pattern_world.match(filename)
            if match:
                try:
                    layer = int(match.group(1))
                    maps[filename] = {
                        'filename': filename,
                        'layer': layer,
                        'position': 0,
                    }
                except ValueError:
                    print(f"Warning: Could not parse world map filename {filename}")
        return maps

    def get_current_map_connections(self):
        return None

    def transition(self, direction):
        return None

    def get_tile_at(self, grid_x, grid_y):
        """Gets the tile definition at a specific grid coordinate."""
        if self.game.map_data and 0 <= grid_y < len(self.game.map_data) and 0 <= grid_x < len(self.game.map_data[0]):
            char = self.game.map_data[grid_y][grid_x]
            if char in self.game.tile_manager.definitions:
                return self.game.tile_manager.definitions[char]
        return None

    def save_map_to_file(self, save_dir):
        """Saves the current state of map layers to CSV files in the save directory."""
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # We assume self.game has the layout data loaded in memory:
        # self.game.map_data (Base Layer - Modified by destruction)
        # self.game.spawn_layout (Spawn Layer - Modified by pickups)
        # self.game.ground_layout (Ground Layer)
        
        # Helper to write a layer
        def write_layer(layout, filename):
            path = os.path.join(save_dir, filename)
            try:
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(layout)
                print(f"Saved map layer to {path}")
            except Exception as e:
                print(f"Error saving map layer {filename}: {e}")

        # Determine filenames based on current layer index (assuming standard naming)
        # Currently the game uses map_L{i}_world_map.csv. 
        # But this single CSV usually contains ALL data in blocks, or the game loads separate files.
        # Based on map_loader logic, it usually reads one file.
        # If the game structure separates layers into variables in 'game', we can save them individually
        # or implies we should overwrite the single file structure. 
        # For this implementation, we will save specific layer files if they are available in 'game'.
        
        # NOTE: This assumes the game engine supports loading from these split files or 
        # that 'map_data' corresponds to the file being loaded.
        
        if hasattr(self.game, 'map_data'):
            # Save Base Layer (Walls/Obstacles)
            write_layer(self.game.map_data, f'map_L{self.game.current_layer_index}_world_map.csv')
            
        if hasattr(self.game, 'spawn_layout'):
            # Save Spawn Layer (Items/Entities)
            write_layer(self.game.spawn_layout, f'map_L{self.game.current_layer_index}_world_spawn.csv')

        # If you need to overwrite the main map file, you would combine them here, 
        # but safely we usually save the modified state separately.

    def toggle_door_state(self, grid_x, grid_y):
        """Toggles a 'statable' tile (like a door) between its states."""
        if not self.game.map_data: return

        current_char = self.game.map_data[grid_y][grid_x]
        current_def = self.game.tile_manager.definitions.get(current_char)

        if not current_def or not current_def.get('is_statable'):
            return

        current_state = current_def.get('state')
        new_state = "open" if current_state == "close" else "close"

        tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

        if new_state == "close":
            if self.game.player.rect.colliderect(tile_rect):
                display_message_player("Player is in the doorway, cannot close.")
                return 
        
        base_name = current_char.replace("_open", "").replace("_close", "")
        new_char = f"{base_name}_{new_state}"

        if new_char in self.game.tile_manager.definitions:
            new_def = self.game.tile_manager.definitions[new_char]
            
            self.game.map_data[grid_y][grid_x] = new_char
            
            self.game.obstacles = [rect for rect in self.game.obstacles if rect != tile_rect]
            if new_def['is_obstacle']:
                self.game.obstacles.append(tile_rect)
            
            if new_def.get('sound_src'):
                self.game.sound_manager.play_sound(
                    new_def['sound_src'],
                    subdir='map',
                    game=self.game,
                    source_pos=tile_rect.center,
                    base_volume=random.uniform(0.2, 0.7)
                )

        else:
            print(f"Warning: Could not find matching door state '{new_char}'")
    
    def hit_tile(self, grid_x, grid_y, damage, weapon=None):
        if not self.game.map_data or not (0 <= grid_y < len(self.game.map_data) and 0 <= grid_x < len(self.game.map_data[0])):
            return False

        char = self.game.map_data[grid_y][grid_x]
        definition = self.game.tile_manager.definitions.get(char)
        
        if not definition or not definition.get('destructible'):
            return False

        valid_axes = ["Axe", "Primitive Axe", 'Knife', 'Primitive Knife', 'Picaxe']
        has_axe = False
        if weapon:
            for axe_name in valid_axes:
                if axe_name in weapon.name:
                    has_axe = True
                    break
        
        # [UPDATED] Allow hands (weapon=None) to hit, but block invalid weapons
        if weapon and not has_axe:
             display_message_player("You need an axe to chop this.")
             return True
             
        STAMINA_COST = 0.5
        if self.game.player.stamina < STAMINA_COST:
            display_message_player("You are too exhausted to chop!")
            return True

        self.game.player.stamina = max(0, self.game.player.stamina - STAMINA_COST)
        self.game.player.tireness = min(self.game.player.max_tireness, self.game.player.tireness + 0.5)

        if weapon and weapon.durability is not None:
            DURABILITY_COST = 0.7
            weapon.durability = max(0, weapon.durability - DURABILITY_COST)
            if weapon.durability <= 0:
                self.game.player.active_weapon = None
                display_message_player(f"{weapon.name} is broken and unequipped.")
                return True
        
        # [NOTE] Shaking logic is reached now that we don't return early for hands
        if definition.get('sound_src'):
            tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            self.game.sound_manager.play_sound(
                definition['sound_src'],
                subdir='map',
                game=self.game,
                source_pos=tile_rect.center,
                base_volume=random.uniform(0.2, 0.7)
            )

        self.shaking_tiles[(grid_x, grid_y)] = time.time()

        map_name = self.current_map_filename
        if map_name not in self.game.map_states:
            self.game.map_states[map_name] = {}
        if 'tile_health' not in self.game.map_states[map_name]:
            self.game.map_states[map_name]['tile_health'] = {}
        
        pos_key = (grid_x, grid_y)
        if pos_key not in self.game.map_states[map_name]['tile_health']:
            self.game.map_states[map_name]['tile_health'][pos_key] = random.randint(
                definition.get('health_min', 60), 
                definition.get('health_max', 100)
            )
        
        self.game.map_states[map_name]['tile_health'][pos_key] -= damage
        current_hp = self.game.map_states[map_name]['tile_health'][pos_key]
        display_message_player(f"({max(0, current_hp)} HP left)")
        
        if current_hp <= 0:
            del self.game.map_states[map_name]['tile_health'][pos_key]
            
            if (grid_x, grid_y) in self.shaking_tiles:
                del self.shaking_tiles[(grid_x, grid_y)]

            try:
                # Fallback to ground layer beneath it
                ground_char = self.game.all_ground_layers[self.game.current_layer_index][grid_y][grid_x]
            except (KeyError, IndexError, AttributeError):
                ground_char = "." 

            self._replace_tile(grid_x, grid_y, char, ground_char)

            if 'drops' in definition:
                for drop in definition['drops']:
                     if random.random() <= drop['chance']:
                         qty = random.randint(drop.get('min_qty', 1), drop.get('max_qty', 1))
                         for _ in range(qty):
                             item = Item.create_from_name(drop['item'])
                             if item:
                                 center_x = grid_x * TILE_SIZE + TILE_SIZE // 2
                                 center_y = grid_y * TILE_SIZE + TILE_SIZE // 2
                                 item.rect.center = (center_x, center_y)
                                 
                                 if find_free_tile(item.rect, self.game.obstacles, self.game.items_on_ground, initial_pos=(item.rect.x, item.rect.y), max_radius=2):
                                     self.game.items_on_ground.append(item)
                                 else:
                                     print(f"Warning: Could not place dropped item {item.name}")
                             else:
                                 print(f"Warning: Drop item '{drop['item']}' not found in templates.")

        return True

    def _replace_tile(self, grid_x, grid_y, old_char, new_char):
        new_def = self.game.tile_manager.definitions.get(new_char)
        old_def = self.game.tile_manager.definitions.get(old_char)
        if not new_def or not old_def: return

        tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

        # 1. Update Map Data (This changes the in-memory layout which save_map_to_file will read)
        self.game.map_data[grid_y][grid_x] = new_char
        
        # 2. Update Obstacles
        self.game.obstacles = [rect for rect in self.game.obstacles if rect != tile_rect]
        if new_def['is_obstacle']:
            self.game.obstacles.append(tile_rect)