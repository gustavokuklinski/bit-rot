import pygame
import random
import math
import core.data.config  # Import full config module to safely access constants if needed
from core.data.config import *
from core.entities.item.item import Item
from core.entities.zombie.zombie import Zombie

def spawn_initial_items(obstacles, item_spawns):
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
        
        item.x = pos[0]
        item.y = pos[1]

        # Check against the set (much faster)
        item_tile = (item.rect.x // TILE_SIZE, item.rect.y // TILE_SIZE)
        
        if item_tile not in occupied_tiles:
            items_on_ground.append(item)
            occupied_tiles.add(item_tile) # Add new item to set
        else:
            # print(f"Warning: Could not spawn item at {pos} due to collision with obstacle.")
            pass
    return items_on_ground

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
                
                # [ADD BOUNDARY CHECK]
                if not (0 <= check_x_tile < max_x_tile and 0 <= check_y_tile < max_y_tile):
                    continue # This tile is outside the map boundaries
                
                tile_coord = (check_x_tile, check_y_tile)

                if tile_coord not in occupied_tiles:
                    # Found a free spot!
                    occupied_tiles.add(tile_coord) # Occupy it
                    return (check_x_tile * TILE_SIZE, check_y_tile * TILE_SIZE) # Return pixel coords
                    
    return None # No free tile found within radius

def spawn_initial_zombies(obstacles, zombie_spawns, items_on_ground, limit=1000, spawns_per_marker=None, map_width_px=None, map_height_px=None, player=None):
    zombies = []
    
    # Increase safe radius slightly to ensure they spawn nicely off-screen
    SAFE_RADIUS_TILES = 35 
    safe_dist_px = SAFE_RADIUS_TILES * TILE_SIZE
    
    # 1. Thin out the spawn markers (Spatial Filtering)
    # This enforces the "5 tiles between Z spawns" rule and significantly reduces lag 
    # by processing fewer markers.
    filtered_spawns = []
    marker_exclusion_zone = set()
    
    # Spacing of 5 tiles means we block a radius of ~2-3 tiles around each selected marker,
    # or strictly block the 5x5 grid area.
    min_spacing_tiles = 5
    
    for pos in zombie_spawns:
        tx = int(pos[0] // TILE_SIZE)
        ty = int(pos[1] // TILE_SIZE)
        
        if (tx, ty) in marker_exclusion_zone:
            continue
            
        filtered_spawns.append(pos)
        
        # Mark the area around this marker as taken so neighbors are skipped
        for i in range(-min_spacing_tiles, min_spacing_tiles + 1):
            for j in range(-min_spacing_tiles, min_spacing_tiles + 1):
                marker_exclusion_zone.add((tx + i, ty + j))

    # 2. Create the collision map for actual entity placement
    # This prevents spawning inside walls or on top of existing items
    occupied_tiles = set()
    
    for ob in obstacles:
        # Add all tiles this obstacle might cover
        for x_tile in range(ob.left // TILE_SIZE, (ob.right + TILE_SIZE - 1) // TILE_SIZE):
            for y_tile in range(ob.top // TILE_SIZE, (ob.bottom + TILE_SIZE - 1) // TILE_SIZE):
                occupied_tiles.add((x_tile, y_tile))
                
    # Add items and other entities to collision map
    # Note: items_on_ground here usually includes other zombies/player if passed from update.py
    for entity in items_on_ground:
        occupied_tiles.add((entity.rect.x // TILE_SIZE, entity.rect.y // TILE_SIZE))
    
    if player:
        occupied_tiles.add((player.rect.x // TILE_SIZE, player.rect.y // TILE_SIZE))

    # Default spawn count logic
    if spawns_per_marker is None:
        try:
            spawns_per_marker = ZOMBIES_PER_SPAWN
        except NameError:
             spawns_per_marker = 3 # Fallback default

    # 3. Main Spawn Loop using Filtered Markers
    for pos in filtered_spawns:
        if len(zombies) >= limit: break

        # Check distance to player to prevent "appearing from nowhere"
        if player:
            dist = math.hypot(pos[0] - player.x, pos[1] - player.y)
            if dist < safe_dist_px:
                continue

        for _ in range(spawns_per_marker): 
            if len(zombies) >= limit: break
            
            # Find a free tile near the marker
            spawn_spot_px = _find_spawn_spot_near(pos, occupied_tiles, map_width_px, map_height_px)
            
            if spawn_spot_px:
                # Create the zombie
                zombie = Zombie.create_random(spawn_spot_px[0], spawn_spot_px[1])
                zombies.append(zombie)
                # Note: The tile is already added to 'occupied_tiles' by the helper function,
                # preventing the next zombie in this loop from overlapping.
            else:
                # Area is full, stop trying to spawn more at this specific marker
                break 
                
    return zombies