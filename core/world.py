import pygame
import random
import os

from data.config import *
from core.entities.item import Item
from core.entities.zombie import Zombie
from core.placement import find_free_tile

class MapManager:
    def __init__(self, map_folder='game/map'):
        self.map_folder = map_folder
        self.current_map_filename = 'map_0_1_0_0.txt' # Starting map
        self.map_files = self._discover_maps()

    def _discover_maps(self):
        maps = {}
        for filename in os.listdir(self.map_folder):
            if filename.startswith('map_') and filename.endswith('.txt'):
                try:
                    parts = filename.replace('map_', '').replace('.txt', '').split('_')
                    if len(parts) == 4:
                        connections = tuple(int(p) for p in parts)
                        maps[filename] = connections
                except ValueError:
                    print(f"Warning: Could not parse map filename {filename}")
        return maps

    def get_current_map_connections(self):
        return self.map_files.get(self.current_map_filename)

    def transition(self, direction):
        connections = self.get_current_map_connections()
        if not connections:
            return None

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

        for filename, file_connections in self.map_files.items():
            if filename == self.current_map_filename:
                continue
            if file_connections[opposite_index] == connection_id:
                self.current_map_filename = filename
                return filename
        
        print(f"Warning: No map found for transition '{direction}' from {self.current_map_filename}")
        return None

def parse_map_layout(layout):
    """Creates a list of obstacle Rects and spawn points from a text-based map layout."""
    obstacles = []
    player_spawn = None
    zombie_spawns = []
    item_spawns = []
    expected_width = GAME_WIDTH // TILE_SIZE
    for y, row in enumerate(layout):
        if len(row) != expected_width:
            print(f"Warning: Map layout row {y} has length {len(row)}, expected {expected_width}")
        for x, char in enumerate(row):
            if char == '#':
                obstacles.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            elif char == 'P':
                player_spawn = (x * TILE_SIZE, y * TILE_SIZE)
            elif char == 'Z':
                zombie_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
            elif char == 'I':
                item_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
    return obstacles, player_spawn, zombie_spawns, item_spawns

def spawn_initial_items(obstacles, item_spawns):
    items_on_ground = []
    for pos in item_spawns:
        item = Item.generate_random()
        item.rect.topleft = pos
        collision = any(item.rect.colliderect(ob) for ob in obstacles)
        if not collision:
            items_on_ground.append(item)
        else:
            print(f"Warning: Could not spawn item at {pos} due to collision with obstacle.")
    return items_on_ground

def spawn_initial_zombies(obstacles, zombie_spawns, items_on_ground):
    zombies = []
    all_spawned_entities = list(items_on_ground)
    spacing_obstacles = []

    for pos in zombie_spawns:
        for _ in range(ZOMBIES_PER_SPAWN):
            zombie = Zombie.create_random(pos[0], pos[1])
            
            current_obstacles = obstacles + spacing_obstacles
            
            if find_free_tile(zombie.rect, current_obstacles, all_spawned_entities, initial_pos=pos):
                zombie.x = zombie.rect.x
                zombie.y = zombie.rect.y
                zombies.append(zombie)
                all_spawned_entities.append(zombie)
                spacing_obstacles.append(zombie.rect.inflate(TILE_SIZE, TILE_SIZE))
            else:
                print(f"Warning: Could not spawn zombie near {pos}.")
    return zombies

def load_map_from_file(filepath):
    """Loads a map layout from a text file."""
    with open(filepath, 'r') as f:
        return [line.rstrip('\n') for line in f.readlines()]
