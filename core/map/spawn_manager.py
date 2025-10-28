import pygame
import random

from data.config import *
from core.entities.item import Item
from core.entities.zombie import Zombie
from core.placement import find_free_tile

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
        # Spawn one zombie per 'Z' marker, or adjust ZOMBIES_PER_SPAWN if needed
        # ZOMBIES_PER_SPAWN = 1 # Usually 1 per marker is intended
        for _ in range(ZOMBIES_PER_SPAWN): # <-- Your uncommented loop
            
            # Create a zombie at the spawn point's location
            zombie = Zombie.create_random(pos[0], pos[1]) 

            # Now, ask find_free_tile to place it.
            # We pass 'all_spawned_entities' as the list of items to avoid.
            # This makes the 2nd and 3rd zombies automatically find a spot
            # next to the 1st zombie.
            if find_free_tile(zombie.rect, obstacles, all_spawned_entities, initial_pos=pos):
                zombie.x = zombie.rect.x
                zombie.y = zombie.rect.y
                zombies.append(zombie)
                all_spawned_entities.append(zombie) # Add to the list for the *next* zombie to check against
            else:
                print(f"Warning: Could not find free space to spawn zombie near {pos}.")
    return zombies