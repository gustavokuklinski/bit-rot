# core/world_layers.py
import os
import re
import pygame
from data.config import *
from core.entities.item.item import Item
from core.entities.zombie.zombie import Zombie
from core.entities.zombie.corpse import Corpse
from core.map.map_loader import load_map_from_file, parse_layered_map_layout
from core.map.tile_manager import TileManager
from core.map.spawn_manager import spawn_initial_items, spawn_initial_zombies

def resize_map_layer(layer_data, target_width, target_height, fill_value=''):
    """
    Resizes a map layer to the target dimensions.
    - Pads with `fill_value` if smaller.
    - Trims if larger.
    """
    current_height = len(layer_data)

    # --- START FIX ---
    # Create a new blank layer with the target dimensions
    new_layer = [[fill_value for _ in range(target_width)] for _ in range(target_height)]

    # We must iterate over each row individually, as they may have
    # different lengths (sparse CSV).
    
    # Loop over the rows we want to *copy*
    for y in range(min(current_height, target_height)):
        
        # Get the actual width of the *current* row
        current_row_width = len(layer_data[y])
        
        # Loop over the columns we want to *copy*
        # This will copy up to `current_row_width` or `target_width`,
        # whichever is smaller.
        for x in range(min(current_row_width, target_width)):
            # Just copy the data.
            new_layer[y][x] = layer_data[y][x]
            
    return new_layer



def load_giant_map(game):
    """
    Discovers all map chunks, builds a world grid,
    and stitches them into a single giant map.
    """
    print("Starting giant map load...")
    map_files = game.map_manager.map_files
    if not map_files:
        raise Exception("No map files found by MapManager.")
        
    map_folder = game.map_manager.map_folder
    
    world_grid = {} # Stores (grid_x, grid_y) -> map_info
    layouts = {}    # Stores (grid_x, grid_y) -> (base, ground, spawn) layouts
    to_process = [] # Queue for BFS: (grid_x, grid_y, map_info)
    processed_files = set()
    
    # These track the dimensions of the map grid (e.g., 2x1, 3x3)
    min_x, max_x, min_y, max_y = 0, 0, 0, 0

    # 1. Start with the player's initial map
    start_file = game.map_manager.current_map_filename
    if start_file not in map_files:
         raise Exception(f"Starting map file {start_file} not found in discovered maps.")
         
    start_info = map_files[start_file]
    
    world_grid[(0, 0)] = start_info
    to_process.append((0, 0, start_info))
    processed_files.add(start_file)
    
    print("Building world grid...")
    
    # 2. Loop 1: Discover grid layout and load all layouts
    while to_process:
        (cx, cy, c_info) = to_process.pop(0)
        
        # Update world grid boundaries
        min_x, max_x = min(min_x, cx), max(max_x, cx)
        min_y, max_y = min(min_y, cy), max(max_y, cy)

        # Load this chunk's 3 layouts
        try:
            base_name = c_info['filename'].rsplit('_map.csv', 1)[0]
            base_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_map.csv"))
            ground_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_ground.csv"))
            spawn_layout = load_map_from_file(os.path.join(map_folder, f"{base_name}_spawn.csv"))
            
            if not base_layout or not ground_layout or not spawn_layout:
                print(f"Warning: Missing layout files for {base_name}. Skipping chunk.")
                continue
                
            layouts[(cx, cy)] = (base_layout, ground_layout, spawn_layout)
        except Exception as e:
            print(f"Error loading layouts for {c_info['filename']}: {e}")
            continue

        # Check neighbors: (connection_index, dx, dy, opposite_connection_index)
        neighbors = [
            (0, 0, -1, 2), # Top
            (1, 1, 0, 3),  # Right
            (2, 0, 1, 0),  # Bottom
            (3, -1, 0, 1)  # Left
        ]
        
        for conn_idx, dx, dy, opp_idx in neighbors:
            conn_id = c_info['connections'][conn_idx]
            if conn_id == 0:
                continue
            
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in world_grid:
                continue # Already processed or queued

            # Find the neighbor map that matches this connection
            found_neighbor = False
            for filename, n_info in map_files.items():
                if filename in processed_files:
                    continue
                
                # Check for matching layer and connection ID
                if n_info['layer'] == c_info['layer'] and n_info['connections'][opp_idx] == conn_id:
                    print(f"Found neighbor {filename} at ({nx}, {ny})")
                    world_grid[(nx, ny)] = n_info
                    to_process.append((nx, ny, n_info))
                    processed_files.add(filename)
                    found_neighbor = True
                    break
            if not found_neighbor:
                print(f"Warning: Could not find neighbor for map {c_info['filename']} connection {conn_id}")

    # 3. Loop 2: Create Mega-Layouts
    # Assume all chunks are 100x100
    chunk_w, chunk_h = 100, 100 
    grid_w = (max_x - min_x) + 1
    grid_h = (max_y - min_y) + 1
    
    mega_w, mega_h = grid_w * chunk_w, grid_h * chunk_h
    print(f"Creating {grid_w}x{grid_h} mega-map ({mega_w}x{mega_h} tiles)...")

    # Create empty 2D lists
    mega_base = [[' ' for _ in range(mega_w)] for _ in range(mega_h)]
    mega_ground = [[' ' for _ in range(mega_w)] for _ in range(mega_h)]
    mega_spawn = [[' ' for _ in range(mega_w)] for _ in range(mega_h)]

    # 4. Loop 3: Blit all chunks onto the Mega-Layouts
    for (grid_x, grid_y), (base, ground, spawn) in layouts.items():
        # Calculate offset from the top-left (min_x, min_y)
        offset_x = (grid_x - min_x) * chunk_w
        offset_y = (grid_y - min_y) * chunk_h
        
        is_start_chunk = (world_grid[(grid_x, grid_y)]['filename'] == start_file)

        # Blit each layout tile by tile
        for r in range(chunk_h):
            for c in range(chunk_w):
                # Base Layer
                if r < len(base) and c < len(base[r]) and base[r][c] and base[r][c] != ' ':
                    mega_base[offset_y + r][offset_x + c] = base[r][c]
                # Ground Layer
                if r < len(ground) and c < len(ground[r]) and ground[r][c] and ground[r][c] != ' ':
                    mega_ground[offset_y + r][offset_x + c] = ground[r][c]
                # Spawn Layer
                if r < len(spawn) and c < len(spawn[r]) and spawn[r][c] and spawn[r][c] != ' ':
                    char = spawn[r][c]
                    # CRITICAL: Only keep the 'P' from the *starting* chunk
                    if char == 'P' and not is_start_chunk:
                        mega_spawn[offset_y + r][offset_x + c] = ' ' # Clear extra player spawns
                    else:
                        mega_spawn[offset_y + r][offset_x + c] = char

    # 5. Parse the single Mega-Layout
    print("Parsing mega-layouts...")
    (game.obstacles, 
     game.renderable_tiles, 
     game.player_spawn, 
     game.zombie_spawns, 
     game.item_spawns, 
     game.containers) = parse_layered_map_layout(
         mega_base, mega_ground, mega_spawn, game.tile_manager
     )
    
    # Store the final map data for lookups (e.g., toggling doors)
    game.map_data = mega_base
    game.current_zombie_spawns = game.zombie_spawns # Keep compatible with existing code
    
    game.all_map_layers[1] = mega_base
    game.all_ground_layers[1] = mega_ground
    game.all_spawn_layers[1] = mega_spawn


    # 6. Set pixel dimensions for the *entire* world
    game.world_min_x = 0
    game.world_min_y = 0
    game.world_width_pixels = mega_w * TILE_SIZE
    game.world_height_pixels = mega_h * TILE_SIZE

    # 7. Add world boundary obstacles to keep the player inside
    print("Adding world boundary obstacles...")
    game.obstacles.append(pygame.Rect(-100, -100, 100, game.world_height_pixels + 200)) # Left wall
    game.obstacles.append(pygame.Rect(game.world_width_pixels, -100, 100, game.world_height_pixels + 200)) # Right wall
    game.obstacles.append(pygame.Rect(-100, -100, game.world_width_pixels + 200, 100)) # Top wall
    game.obstacles.append(pygame.Rect(-100, game.world_height_pixels, game.world_width_pixels + 200, 100)) # Bottom wall

    print(f"Giant map load complete. Player spawn: {game.player_spawn}")

    game.is_giant_map = True
    # CRITICAL: Sync the map_width/height to the new giant world_width/height
    game.map_width_pixels = game.world_width_pixels
    game.map_height_pixels = game.world_height_pixels

    print("Populating spawn point grid for giant map...")

    game.spawn_point_grid.clear()
    GRID_SIZE_SPAWNS = game.SPAWN_GRID_SIZE # 512
    for sp_pos in game.current_zombie_spawns:
        grid_x = int(sp_pos[0] // GRID_SIZE_SPAWNS)
        grid_y = int(sp_pos[1] // GRID_SIZE_SPAWNS)
        cell = (grid_x, grid_y)
        if cell not in game.spawn_point_grid:
            game.spawn_point_grid[cell] = [sp_pos] 
        else:
            game.spawn_point_grid[cell].append(sp_pos)

def load_all_map_layers(base_map_filename, master_width=None, master_height=None):
    """
    Loads all map layers (1-9) associated with a base map name.
    If master_width/master_height are provided, it resizes all layers to that.
    Otherwise, it determines dimensions from the base_map_filename.
    """
    all_map_layers = {}
    all_ground_layers = {}
    all_spawn_layers = {}

    # Use the same regex as MapManager to correctly parse the filename
    pattern = re.compile(r'map_L(\d+)_P(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_map\.csv')
    base_name_match = pattern.match(base_map_filename)
    
    if not base_name_match:
        print(f"CRITICAL: Base map filename does not match expected pattern: {base_map_filename}")
        return {}, {}, {}

    # Correctly separate all components
    base_pos_id = base_name_match.group(2)          # e.g., 0
    base_conn_tuple = base_name_match.groups()[2:]  # e.g., ('0', '1', '0', '0')
    base_connections_str = "_".join(base_conn_tuple)  # e.g., "0_1_0_0"

    print(f"Loading all layers for base map prefix: P{base_pos_id}_{base_connections_str}")

    # --- Determine target dimensions ---
    if master_width is not None and master_height is not None:
        # Use the dimensions passed in (e.g., by load_giant_map)
        target_width = master_width
        target_height = master_height
        print(f"Using master dimensions: {target_width}x{target_height}")
    else:
        # Original behavior: get dimensions from the file itself
        base_map_file = os.path.join(MAP_DIR, base_map_filename)
        if not os.path.exists(base_map_file):
            print(f"CRITICAL: Base map file not found: {base_map_file}")
            # Failsafe logic to find *any* layer file for dimensions
            found_any = False
            for i in range(1, 10):
                any_layer_file = os.path.join(MAP_DIR, f"map_L{i}_P{base_pos_id}_{base_connections_str}_map.csv")
                if os.path.exists(any_layer_file):
                    base_map_file = any_layer_file
                    print(f"Using {any_layer_file} for dimensions instead.")
                    found_any = True
                    break
            if not found_any:
                 print(f"CRITICAL: No map files found at all for base prefix P{base_pos_id}.")
                 return {}, {}, {}
        
        base_map_data = load_map_from_file(base_map_file)
        if not base_map_data or not base_map_data[0]:
            print(f"CRITICAL: Base map file is empty or invalid: {base_map_file}")
            return {}, {}, {}

        target_height = len(base_map_data)
        target_width = 0
        # Find the first non-empty row to determine width
        for row in base_map_data:
            if row: # If row is not empty
                target_width = len(row)
                break
        
        if target_width == 0:
            print(f"Warning: Map file {base_map_file} seems to be completely empty. Defaulting to 100.")
            target_width = 100
        print(f"Using file dimensions: {target_width}x{target_height}")

    # --- Now, loop and load all layers, resizing them to match the TARGET ---
    for i in range(1, 10): # i = 1, 2, 3, ..., 9
        
        # Reconstruct the prefix using the correct components
        layer_prefix = f"map_L{i}_P{base_pos_id}_{base_connections_str}"

        layer_map_file_relative = f"{layer_prefix}_map.csv"
        layer_ground_file_relative = f"{layer_prefix}_ground.csv"
        layer_spawn_file_relative = f"{layer_prefix}_spawn.csv"
        
        # --- START FIX ---
        # We must check for all 3 files *independently*
        # Do not 'continue' just because _map.csv is missing
        
        layer_map_file = os.path.join(MAP_DIR, layer_map_file_relative)
        layer_ground_file = os.path.join(MAP_DIR, layer_ground_file_relative)
        layer_spawn_file = os.path.join(MAP_DIR, layer_spawn_file_relative)

        map_data = load_map_from_file(layer_map_file)
        ground_data = load_map_from_file(layer_ground_file)
        spawn_data = load_map_from_file(layer_spawn_file)

        # If ALL files for this layer are empty, *then* we can skip
        if not map_data and not ground_data and not spawn_data:
            continue
            
        print(f"Processing layer {i} from prefix {layer_prefix}...")

        # Process and store data
        if map_data:
            map_data = resize_map_layer(map_data, target_width, target_height)
            all_map_layers[i] = map_data
        
        if ground_data:
            ground_data = resize_map_layer(ground_data, target_width, target_height)
            all_ground_layers[i] = ground_data
        
        if spawn_data:
            spawn_data = resize_map_layer(spawn_data, target_width, target_height, fill_value=' ') 
            all_spawn_layers[i] = spawn_data
        # --- END FIX ---

    return all_map_layers, all_ground_layers, all_spawn_layers

def _rebuild_world_from_data(game):
    """
    (Internal) Clears and repopulates obstacles, entities, etc., from the
    CURRENTLY active game.map_data and game.spawn_data.
    """
    # Clear all current-layer entities
    game.obstacles.clear()
    game.containers.clear()

    # Call parse_layered_map_layout to get the new world data
    obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers = \
        parse_layered_map_layout(game.map_data, game.ground_data, game.spawn_data, game.tile_manager)

    # Assign the new data to the game object
    game.obstacles = obstacles
    game.renderable_tiles = renderable_tiles
    game.containers = containers

    # Return spawn points for set_active_layer to handle
    return item_spawns, zombie_spawns

def set_active_layer(game, layer_index):
    """
    Switches the game's active map data to the specified layer and rebuilds the world.
    """
    if layer_index not in game.all_map_layers:
        print(f"Error: Attempted to switch to non-existent layer {layer_index}")
        return False

    # Find and set the new current_map_filename for the map manager
    current_filename = game.map_manager.current_map_filename
    # Construct the new filename by replacing the layer number (e.g., "map_L1_..." -> "map_L2_...")
    new_filename = re.sub(r'map_L(\d+)_', f'map_L{layer_index}_', current_filename)

    if new_filename in game.map_manager.map_files:
        game.map_manager.current_map_filename = new_filename
        print(f"MapManager current_map_filename set to: {new_filename}") # Debug print
    else:
        # This case should be rare if all_map_layers is populated correctly
        print(f"Error: Could not find matching filename {new_filename} for layer {layer_index} in map_manager.map_files")
        return False

    # --- State Saving ---
    if game.current_layer_index in game.layer_items:
        game.layer_items[game.current_layer_index] = game.items_on_ground[:]
    if game.current_layer_index in game.layer_zombies:
        game.layer_zombies[game.current_layer_index] = game.zombies[:]

    print(f"Setting active layer to: {layer_index}")
    game.current_layer_index = layer_index
    
    # Set the game's main data properties to point to the new layer's data
    game.map_data = game.all_map_layers[layer_index]
    game.ground_data = game.all_ground_layers.get(layer_index, [])
    game.spawn_data = game.all_spawn_layers.get(layer_index, [])

    if not getattr(game, 'is_giant_map', False) and layer_index == 1:
        if game.map_data:
            game.map_height_pixels = len(game.map_data) * TILE_SIZE
            game.map_width_pixels = len(game.map_data[0]) * TILE_SIZE
        else:
            # We are on a non-giant-map layer (L2, L3...), use the layer's specific dimensions
            if game.map_data:
                game.map_height_pixels = len(game.map_data) * TILE_SIZE
                game.map_width_pixels = len(game.map_data[0]) * TILE_SIZE
            else:
                game.map_height_pixels = 0
                game.map_width_pixels = 0

    print(f"Active map_data shape: ({len(game.map_data)}, {len(game.map_data[0]) if game.map_data else 0})")
    print(f"Active ground_data shape: ({len(game.ground_data)}, {len(game.ground_data[0]) if game.ground_data else 0})")
    print(f"Active spawn_data shape: ({len(game.spawn_data)}, {len(game.spawn_data[0]) if game.spawn_data else 0})")
    
    # Rebuild obstacles and get spawn points
    item_spawns, zombie_spawns = _rebuild_world_from_data(game)

    # Store the list of 'Z' markers for the dynamic spawner
    game.current_zombie_spawns = zombie_spawns
    # Ensure the triggered set exists for this layer
    game.layer_spawn_triggers.setdefault(layer_index, set())

    if getattr(game, 'is_giant_map', False) and layer_index == 1:
        # We are on the giant map (L1). DO NOTHING.
        # The giant grid was already built by load_giant_map and must be preserved.
        pass
    else:
        # We are on a non-giant-map layer (L2, etc.). Build a new, local grid.
        print(f"[DEBUG] Building spawn grid for non-giant layer {layer_index}")
        game.spawn_point_grid.clear()
        GRID_SIZE_SPAWNS = game.SPAWN_GRID_SIZE # 512
        for sp_pos in game.current_zombie_spawns:
            grid_x = int(sp_pos[0] // GRID_SIZE_SPAWNS)
            grid_y = int(sp_pos[1] // GRID_SIZE_SPAWNS)
            cell = (grid_x, grid_y)
            if cell not in game.spawn_point_grid:
                game.spawn_point_grid[cell] = [sp_pos]
            else:
                game.spawn_point_grid[cell].append(sp_pos)


    # --- State Loading ---
    # Items: Load if they exist for the new layer, otherwise spawn them
    if layer_index in game.layer_items:
        game.items_on_ground = game.layer_items[layer_index][:]
    else:
        game.items_on_ground = spawn_initial_items(game.obstacles, item_spawns)
        game.layer_items[layer_index] = game.items_on_ground[:]

    # Zombies: Load if they exist and respawn is OFF, otherwise spawn them
    if layer_index in game.layer_zombies:
        game.zombies = game.layer_zombies[layer_index][:]
    else:
        game.zombies = [] # Start empty
        game.layer_zombies[layer_index] = []
    
    return True

def check_for_layer_teleport(game):
    """
    Checks if player is on a teleport tile (e.g., [2]) and switches layers.
    Called every frame from update.py.
    """
    if game.player.layer_switch_cooldown > 0:
        return # Player is in cooldown

    player = game.player
    
    try:
        tile_x = player.rect.centerx // TILE_SIZE
        tile_y = player.rect.centery // TILE_SIZE
    except (AttributeError, TypeError):
        return # Player rect not ready

    # Get the tile ID from the CURRENTLY active map
    current_map_data = game.map_data
    if not current_map_data:
        return
        
    # Check bounds
    if not (0 <= tile_y < len(current_map_data) and 0 <= tile_x < len(current_map_data[0])):
        return # Player is out of bounds
        
    tile_id = current_map_data[tile_y][tile_x]
    
    # Check for teleporter tile like [1], [2], ... [9]
    match = re.match(r'\[(\d)\]', tile_id)
    
    if match:
        target_layer = int(match.group(1))
        
        # Check if target is valid and not the *current* layer
        if 0 < target_layer <= 9 and target_layer != game.current_layer_index:
            
            # Try to set the new layer
            if set_active_layer(game, target_layer):
                # Success! Set cooldown to prevent instant-return
                game.player.layer_switch_cooldown = 30 # 30 frames (approx 0.5 sec)
            else:
                print(f"Warning: Tile [ {target_layer} ] points to non-existent layer.")

def check_for_map_transition(game):
    """
    Checks if the player has moved off the edge of the map and attempts
    to transition to an adjacent map.
    Called every frame from update.py.
    """
    if getattr(game, 'is_giant_map', False):
        return

    # Cooldown to prevent immediate re-transitioning
    if hasattr(game.player, 'map_transition_cooldown') and game.player.map_transition_cooldown > 0:
        game.player.map_transition_cooldown -= 1
        return

    player = game.player
    direction = None

    # 1. Check if player is off the *current map's* boundaries
    #    (Using the correct map_width_pixels variables)
    if player.rect.right < 0:
        direction = 'left'
    elif player.rect.left > game.map_width_pixels:
        direction = 'right'
    elif player.rect.bottom < 0:
        direction = 'top'
    elif player.rect.top > game.map_height_pixels:
        direction = 'bottom'

    if not direction:
        return # Player is not transitioning

    # 2. Get the OLD map name *before* transitioning
    #    This is crucial for saving state correctly if you add it later
    old_map_filename = game.map_manager.current_map_filename

    # 3. Attempt to transition using the MapManager
    new_map_filename = game.map_manager.transition(direction)

    if new_map_filename:
        print(f"Transitioning from {old_map_filename} to map: {new_map_filename}")

        # 4. Reload all map layers from the new base map file
        # This repopulates all_map_layers, all_ground_layers, etc.
        game.all_map_layers, game.all_ground_layers, game.all_spawn_layers = \
            load_all_map_layers(new_map_filename)

        # 5. Clear all stored layer states for the *previous map*
        game.layer_items.clear()
        game.layer_zombies.clear()
        game.layer_spawn_triggers.clear()

        # 6. Set the active layer to the *same* layer index the player was on.
        # This will now use the newly loaded map data for that layer
        # and correctly recalculate game.map_width_pixels and game.map_height_pixels.
        if not set_active_layer(game, game.current_layer_index):
            print(f"CRITICAL: Failed to set active layer {game.current_layer_index} on new map {new_map_filename}")
            # As a fallback, try to load layer 1
            if not set_active_layer(game, 1):
                print("CRITICAL: Failed to load layer 1 as fallback. Transition aborted.")
                return # Abort transition

        # 7. Reposition the player on the opposite side of the new map
        # We use the NEWLY calculated map dimensions from set_active_layer
        if direction == 'left':
            player.rect.right = game.map_width_pixels - 5 # Place at right edge
            player.x = player.rect.x
        elif direction == 'right':
            player.rect.left = 5 # Place at left edge
            player.x = player.rect.x
        elif direction == 'top':
            player.rect.bottom = game.map_height_pixels - 5 # Place at bottom edge
            player.y = player.rect.y
        elif direction == 'bottom':
            player.rect.top = 5 # Place at top edge
            player.y = player.rect.y
            
        # 8. Set a cooldown to prevent immediate return
        if not hasattr(game.player, 'map_transition_cooldown'):
            game.player.map_transition_cooldown = 0
        game.player.map_transition_cooldown = 30 # 30 frames