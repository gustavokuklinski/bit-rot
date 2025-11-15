import pygame
import random

from data.config import *
from core.entities.item.item import Item
from core.entities.zombie.zombie import Zombie
# We no longer need find_free_tile for this, as we'll write a faster, local version
# from core.placement import find_free_tile 

def spawn_initial_items(obstacles, item_spawns):
    # This function is probably fine, but let's optimize it just in case
    items_on_ground = []
    
    # --- Optimization ---
    # Create a set of occupied tiles for fast lookups
    occupied_tiles = set()
    for ob in obstacles:
        occupied_tiles.add((ob.x // TILE_SIZE, ob.y // TILE_SIZE))
    # --- End Optimization ---

    for pos in item_spawns:
        item = Item.generate_random()
        item.rect.topleft = pos
        
        # Check against the set (much faster)
        item_tile = (item.rect.x // TILE_SIZE, item.rect.y // TILE_SIZE)
        
        if item_tile not in occupied_tiles:
            items_on_ground.append(item)
            occupied_tiles.add(item_tile) # Add new item to set
        else:
            print(f"Warning: Could not spawn item at {pos} due to collision with obstacle.")
    return items_on_ground

# --- NEW HELPER FUNCTION ---
def _find_spawn_spot_near(initial_pos_px, occupied_tiles, map_width_px, map_height_px, max_radius=5):
    """
    Finds the first available tile near the initial position.
    Adds the found tile to the occupied_tiles set.
    """
    start_x_tile = initial_pos_px[0] // TILE_SIZE
    start_y_tile = initial_pos_px[1] // TILE_SIZE

    if map_width_px is None: map_width_px = 99999
    if map_height_px is None: map_height_px = 99999
    
    max_x_tile = map_width_px // TILE_SIZE
    max_y_tile = map_height_px // TILE_SIZE

    # Check 0,0 (the marker itself) first
    tile_coord = (start_x_tile, start_y_tile)
    if tile_coord not in occupied_tiles:
        if 0 <= tile_coord[0] < max_x_tile and 0 <= tile_coord[1] < max_y_tile:
            occupied_tiles.add(tile_coord) # Occupy this tile
            return (start_x_tile * TILE_SIZE, start_y_tile * TILE_SIZE) # Return pixel coords

    # Spiral search outwards
    for radius in range(1, max_radius + 1):
        for i in range(-radius, radius + 1):
            for j in range(-radius, radius + 1):
                if abs(i) < radius and abs(j) < radius:
                    continue # Skip inner tiles, already checked

                check_x_tile = start_x_tile + i
                check_y_tile = start_y_tile + j
                
                tile_coord = (check_x_tile, check_y_tile)
                
                # [ADD BOUNDARY CHECK]
                if not (0 <= check_x_tile < max_x_tile and 0 <= check_y_tile < max_y_tile):
                    continue # This tile is outside the map boundaries

                if tile_coord not in occupied_tiles:
                    # Found a free spot!
                    occupied_tiles.add(tile_coord) # Occupy it
                    return (check_x_tile * TILE_SIZE, check_y_tile * TILE_SIZE) # Return pixel coords
                    
    return None # No free tile found within radius

# --- REWRITTEN ZOMBIE SPAWNER ---
def spawn_initial_zombies(obstacles, zombie_spawns, items_on_ground, limit=1000, spawns_per_marker=None, map_width_px=None, map_height_px=None):
    zombies = []
    
    # 1. Create a set of all tiles that are *already* occupied.
    #    This is O(Obstacles + Items) and is done ONCE.
    occupied_tiles = set()
    for ob in obstacles:
        # Add all tiles this obstacle might cover
        for x in range(ob.left, ob.right, TILE_SIZE):
             for y in range(ob.top, ob.bottom, TILE_SIZE):
                occupied_tiles.add((x // TILE_SIZE, y // TILE_SIZE))
                
    for item in items_on_ground:
        occupied_tiles.add((item.rect.x // TILE_SIZE, item.rect.y // TILE_SIZE))
    
    # Also add the player's tile
    # (We need to get the 'game' object... instead, we'll just pass in 'all_spawned_entities')
    # This function's signature is a bit limiting. Let's pass 'items_on_ground' as 'all_current_entities'
    # and update the helper.
    
    # Re-reading: The original call from update.py passed `items_on_ground + game.zombies`
    # and `check_dynamic_zombie_spawns` passed `game.items_on_ground + game.zombies + [game.player]`
    # So `items_on_ground` in this function *already contains* all entities. Let's rename it.
    
    all_current_entities = items_on_ground
    occupied_tiles = set()
    for ob in obstacles:
        # Add all tiles this obstacle might cover
        # This is safer for obstacles larger than 1 tile
        for x_tile in range(ob.left // TILE_SIZE, (ob.right + TILE_SIZE - 1) // TILE_SIZE):
            for y_tile in range(ob.top // TILE_SIZE, (ob.bottom + TILE_SIZE - 1) // TILE_SIZE):
                occupied_tiles.add((x_tile, y_tile))
                
    for entity in all_current_entities:
        occupied_tiles.add((entity.rect.x // TILE_SIZE, entity.rect.y // TILE_SIZE))
    

    if spawns_per_marker is None:
        spawns_per_marker = ZOMBIES_PER_SPAWN

    for pos in zombie_spawns: # Loop 1: Over each 'Z' marker (e.g., 50 markers)
        if len(zombies) >= limit: break

        for _ in range(spawns_per_marker): # Loop 2: N zombies per marker (e.g., 3)
            if len(zombies) >= limit: break
            
            # 2. Find a free tile using our *new* fast function.
            #    This function checks against the 'occupied_tiles' set O(1)
            #    and modifies the set.
            spawn_spot_px = _find_spawn_spot_near(pos, occupied_tiles, map_width_px, map_height_px)
            
            if spawn_spot_px:
                # 3. Create the zombie *at the free spot*.
                zombie = Zombie.create_random(spawn_spot_px[0], spawn_spot_px[1])
                zombies.append(zombie)
                # The tile is already added to 'occupied_tiles' by the helper
            else:
                # This warning is much more useful.
                print(f"Warning: Could not find free space to spawn zombie near {pos}. Area is full.")
                
    return zombies