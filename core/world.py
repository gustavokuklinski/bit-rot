import pygame
import random

from data.config import *
from core.entities.item import Item
from core.entities.zombie import Zombie
from core.placement import find_free_tile

def create_obstacles_from_map(layout):
    """Creates a list of obstacle Rects from a text-based map layout."""
    obstacles = []
    for y, row in enumerate(layout):
        for x, char in enumerate(row):
            if char == '#':
                obstacles.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
    return obstacles

def spawn_initial_items(obstacles):
    items_on_ground = []
    for _ in range(5):
        item = Item.generate_random()
        if find_free_tile(item.rect, obstacles, items_on_ground):
            items_on_ground.append(item)
    return items_on_ground

def spawn_initial_zombies():
    return [Zombie.create_random(random.randint(50, GAME_WIDTH-50), random.randint(50, GAME_HEIGHT-50)) for _ in range(3)]
