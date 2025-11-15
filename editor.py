import pygame
import sys
import os
import re

from editor.config import SCREEN_WIDTH, SCREEN_HEIGHT, SIDEBAR_WIDTH, TILE_SIZE, ZOOM_LEVELS, INITIAL_ZOOM_INDEX, FILE_TREE_WIDTH, TOOLBAR_HEIGHT, MAP_DEFAULT_WIDTH, MAP_DEFAULT_HEIGHT
from editor.assets import load_map_tiles_from_xml
from editor.map import Map
from editor.ui import Sidebar, Toolbar, NewMapModal
from editor.file_tree import FileTree

# Initialize Pygame
pygame.init()
pygame.font.init() # Initialize font module

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)

pygame.display.set_caption("Bit Rot - Map Editor")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (200, 200, 200)
LIGHT_GREY = (220, 220, 220)
DARK_GREY = (100, 100, 100)
YELLOW = (255, 255, 0)

FONT = pygame.font.Font(None, 24) # Default font for UI text


def get_max_id(map_dir):
    """Finds the highest ID used in any map filename (for connections or position)."""
    max_id = 0
    # Pattern from game's MapManager: map_L<layer>_P<position>_<top>_<right>_<bottom>_<left>
    pattern = re.compile(r"map_L\d+_P(\d+)_(\d+)_(\d+)_(\d+)_(\d+)")
    for filename in os.listdir(map_dir):
        match = pattern.match(filename)
        if match:
            try:
                # Check all 5 ID numbers (pos, t, r, b, l)
                ids = [int(g) for g in match.groups()]
                map_max = max(ids)
                if map_max > max_id:
                    max_id = map_max
            except ValueError:
                continue
    return max_id

def find_connecting_map(target_id, opposite_side, current_layer, map_dir):
    """Finds the base name of a map that connects to the target ID."""
    pattern = re.compile(r"map_L(\d+)_P(\d+)_(\d+)_(\d+)_(\d+)_(\d+)")
    for filename in os.listdir(map_dir):
        match = pattern.match(filename)
        if match:
            try:
                layer = int(match.group(1))
                if layer != current_layer:
                    continue
                
                connections = {
                    'TOP': int(match.group(3)),
                    'RIGHT': int(match.group(4)),
                    'BOTTOM': int(match.group(5)),
                    'LEFT': int(match.group(6)),
                }
                
                if connections[opposite_side] == target_id:
                    # Found the map. Return its base name.
                    return f"map_L{layer}_P{match.group(2)}_{connections['TOP']}_{connections['RIGHT']}_{connections['BOTTOM']}_{connections['LEFT']}"
            except ValueError:
                continue
    return None

def draw_connection_ui(surface, map_view_rect, font, current_map_name):
    """Draws the connection helper UI on the map edges."""
    # Parse current map connections
    connections = {'TOP': 0, 'RIGHT': 0, 'BOTTOM': 0, 'LEFT': 0}
    layer = 0
    pos_id = 0
    match = re.match(r"map_L(\d+)_P(\d+)_(\d+)_(\d+)_(\d+)_(\d+)", current_map_name)
    if match:
        layer = int(match.group(1))
        pos_id = int(match.group(2))
        connections['TOP'] = int(match.group(3))
        connections['RIGHT'] = int(match.group(4))
        connections['BOTTOM'] = int(match.group(5))
        connections['LEFT'] = int(match.group(6))
    
    # Store rects for click detection
    connection_rects = {}

    # Helper to draw text
    def draw_text(text, center_pos, color):
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=center_pos)
        # Draw a dark, semi-transparent background for readability
        bg_rect = rect.inflate(10, 6)
        s = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        surface.blit(s, bg_rect.topleft)
        surface.blit(surf, rect.topleft)
        return bg_rect

    # Draw TOP
    top_pos = (map_view_rect.centerx, map_view_rect.top + 20)
    top_id = connections['TOP']
    top_color = YELLOW if top_id > 0 else (150, 150, 150)
    connection_rects['TOP'] = draw_text(f"TOP ({top_id})", top_pos, top_color)

    # Draw BOTTOM
    bottom_pos = (map_view_rect.centerx, map_view_rect.bottom - 20)
    bottom_id = connections['BOTTOM']
    bottom_color = YELLOW if bottom_id > 0 else (150, 150, 150)
    connection_rects['BOTTOM'] = draw_text(f"BOTTOM ({bottom_id})", bottom_pos, bottom_color)

    # Draw LEFT
    left_pos = (map_view_rect.left + 45, map_view_rect.centery)
    left_id = connections['LEFT']
    left_color = YELLOW if left_id > 0 else (150, 150, 150)
    connection_rects['LEFT'] = draw_text(f"LEFT ({left_id})", left_pos, left_color)

    # Draw RIGHT
    right_pos = (map_view_rect.right - 45, map_view_rect.centery)
    right_id = connections['RIGHT']
    right_color = YELLOW if right_id > 0 else (150, 150, 150)
    connection_rects['RIGHT'] = draw_text(f"RIGHT ({right_id})", right_pos, right_color)
    
    return connection_rects, connections, layer

def load_map(game_map, map_name, map_dir):
    # Clear existing layers before loading new ones
    game_map.layers = {}
    game_map.active_layer_name = None

    detected_layers = []
    for filename in os.listdir(map_dir):
        # Check if the filename starts with the base map name and ends with .csv
        if filename.startswith(f'{map_name}_') and filename.endswith('.csv'):
            # Extract layer name from filename, e.g., map_L1_P0_0_0_0_1_ground.csv -> ground
            match = re.match(rf'{map_name}_(.*)\.csv', filename)
            if match:
                layer_name = match.group(1)
                detected_layers.append(layer_name)
                map_file_path = os.path.join(map_dir, filename)
                game_map.load_from_csv(map_file_path, layer_name)
                print(f"Loaded {layer_name} layer from {map_file_path}")
    
    if detected_layers:
        # Sort layers for consistent order, e.g., ground, spawn
        detected_layers.sort()
        game_map.default_layers = detected_layers # Store detected layers for cycling
        game_map.set_active_layer(detected_layers[0])
    else:
        print(f"No layers found for map '{map_name}'. Initializing with default empty layers.")
        # If no layers found, re-initialize with default empty layers
        game_map.default_layers = ['ground', 'spawn', 'map']
        for layer_name in game_map.default_layers:
            game_map.layers[layer_name] = [[None for _ in range(game_map.width)] for _ in range(game_map.height)]
        game_map.set_active_layer(game_map.default_layers[0])

def save_map(game_map, map_name, map_dir):
    for layer_name in game_map.layers.keys(): # Iterate through all existing layers
        map_file_path = os.path.join(map_dir, f'{map_name}_{layer_name}.csv')
        game_map.save_to_csv(map_file_path, layer_name)
        print(f"Saved {layer_name} layer to {map_file_path}")

def draw_grid(surface, offset_x, offset_y, zoom_scale, map_width, map_height, map_view_rect):
    scaled_tile_size = TILE_SIZE * zoom_scale
    map_display_width = map_width * scaled_tile_size
    map_display_height = map_height * scaled_tile_size

    # Only draw grid lines within the visible map view rectangle
    # Vertical lines
    for x in range(map_width + 1):
        line_x = int(x * scaled_tile_size + offset_x)
        if map_view_rect.left <= line_x <= map_view_rect.right:
            pygame.draw.line(surface, DARK_GREY, (line_x, map_view_rect.top), (line_x, map_view_rect.bottom), 1)

    # Horizontal lines
    for y in range(map_height + 1):
        line_y = int(y * scaled_tile_size + offset_y)
        if map_view_rect.top <= line_y <= map_view_rect.bottom:
            pygame.draw.line(surface, DARK_GREY, (map_view_rect.left, line_y), (map_view_rect.right, line_y), 1)

def draw_rulers(surface, offset_x, offset_y, zoom_scale, map_width, map_height, map_view_rect, font):
    scaled_tile_size = TILE_SIZE * zoom_scale
    ruler_size = 20 # Size of the ruler area

    # Horizontal Ruler (Top)
    ruler_top_rect = pygame.Rect(map_view_rect.left, TOOLBAR_HEIGHT, map_view_rect.width, ruler_size)
    pygame.draw.rect(surface, DARK_GREY, ruler_top_rect)
    for x in range(map_width):
        num_x = int(x * scaled_tile_size + offset_x)
        if map_view_rect.left <= num_x <= map_view_rect.right:
            text_surface = font.render(str(x), True, WHITE)
            surface.blit(text_surface, (num_x + 2, TOOLBAR_HEIGHT + 2))

    # Vertical Ruler (Left)
    ruler_left_rect = pygame.Rect(FILE_TREE_WIDTH, map_view_rect.top, ruler_size, map_view_rect.height)
    pygame.draw.rect(surface, DARK_GREY, ruler_left_rect)
    for y in range(map_height):
        num_y = int(y * scaled_tile_size + offset_y)
        if map_view_rect.top <= num_y <= map_view_rect.bottom:
            text_surface = font.render(str(y), True, WHITE)
            surface.blit(text_surface, (FILE_TREE_WIDTH + 2, num_y + 2))

def main():
    """Main function for the map editor."""
    # Load assets

    game_root = os.path.abspath(os.path.join('./game'))
    
    xml_map_data_path = os.path.join(game_root, 'resources', 'data', 'map')
    sprite_map_path = os.path.join(game_root, 'resources', 'sprites', 'map')
    map_tiles = load_map_tiles_from_xml(xml_map_data_path, sprite_map_path)

    # Set up map and UI components
    game_map = Map(width=MAP_DEFAULT_WIDTH, height=MAP_DEFAULT_HEIGHT) # Correct map dimensions

    map_dir = os.path.join(game_root, 'resources', 'map')
    
    # Find all map files using the *game's* pattern ---
    map_pattern = re.compile(r"map_L\d+_P(?:\d+_)*\d+(_map|_spawn|_ground)?\.csv")
    all_map_files = sorted([f for f in os.listdir(map_dir) if map_pattern.match(f)])

    file_tree = FileTree(0, TOOLBAR_HEIGHT, FILE_TREE_WIDTH, SCREEN_HEIGHT - TOOLBAR_HEIGHT, all_map_files, FONT)
    toolbar = Toolbar(FILE_TREE_WIDTH, 0, SCREEN_WIDTH - FILE_TREE_WIDTH - SIDEBAR_WIDTH, TOOLBAR_HEIGHT, FONT)

    # Initialize modal with first map name ---
    current_base_map_name = file_tree.selected_map.replace("_map.csv", "") if file_tree.selected_map else "map_L1_P0_0_0_0_0"
    
    # Pass current map name to modal ---
    new_map_modal = NewMapModal(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 125, 300, 250, FONT, current_base_map_name)

    # Load map using the base name ---
    load_map(game_map, current_base_map_name, map_dir)

    sidebar = Sidebar(SCREEN_WIDTH - SIDEBAR_WIDTH, TOOLBAR_HEIGHT, map_tiles, FONT)


    # Camera and Zoom variables
    camera_offset_x = FILE_TREE_WIDTH
    camera_offset_y = TOOLBAR_HEIGHT
    camera_speed = 5

    zoom_level_index = INITIAL_ZOOM_INDEX
    current_zoom_scale = ZOOM_LEVELS[zoom_level_index]

    status_message = ""
    status_message_timer = 0

    # Define the rectangle for the main map view area
    # Adjust map_view_rect to account for rulers
    RULER_SIZE = 20
    map_view_rect = pygame.Rect(FILE_TREE_WIDTH + RULER_SIZE, TOOLBAR_HEIGHT + RULER_SIZE, SCREEN_WIDTH - FILE_TREE_WIDTH - SIDEBAR_WIDTH - RULER_SIZE, SCREEN_HEIGHT - TOOLBAR_HEIGHT - RULER_SIZE)

    # Dragging variables
    dragging = False
    drag_start_pos = (0, 0)

    # Selection variables
    selection_mode = False
    is_selecting = False
    selection_start_pos = None
    selection_rect = None

    # --- NEW: Clipboard for copy/paste ---
    clipboard = None

    modified_maps = set()
    
    # --- MODIFIED: Unify tool selection to one variable ---
    tile_to_place = None # This will store "[1]", "[2]", etc.
    # sidebar.selected_tile will still be used by the sidebar UI, but we'll sync it


    connection_ui_rects = {}
    current_map_connections = {}
    current_map_layer = 1


    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if new_map_modal.active:
                modal_action = new_map_modal.handle_event(event)
                if modal_action:
                    if modal_action['action'] == 'create_map':
                        # 1. Get info from modal
                        source_map = modal_action['source_map']
                        source_conns = modal_action['source_connections']
                        source_pos_id = modal_action['source_pos_id']
                        source_layer = modal_action['source_layer']
                        direction = modal_action['direction']
                        new_layer = modal_action['layer']
                        
                        # 2. Generate new IDs
                        new_conn_id = get_max_id(map_dir) + 1
                        new_pos_id = get_max_id(map_dir) + 1 # Simple unique ID
                        
                        # 3. Define opposite direction and new map's connections
                        opposite_dir_map = {'TOP': 'BOTTOM', 'BOTTOM': 'TOP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}
                        opposite_dir = opposite_dir_map[direction]
                        
                        new_map_conns = {'TOP': 0, 'RIGHT': 0, 'BOTTOM': 0, 'LEFT': 0}
                        new_map_conns[opposite_dir] = new_conn_id
                        
                        # 4. Create new map base name
                        new_map_name = f"map_L{new_layer}_P{new_pos_id}_{new_map_conns['TOP']}_{new_map_conns['RIGHT']}_{new_map_conns['BOTTOM']}_{new_map_conns['LEFT']}"
                        
                        # 5. Update old map's connections
                        source_conns[direction] = new_conn_id
                        updated_source_name = f"map_L{source_layer}_P{source_pos_id}_{source_conns['TOP']}_{source_conns['RIGHT']}_{source_conns['BOTTOM']}_{source_conns['LEFT']}"

                        # 6. Rename old map files
                        try:
                            for layer_suffix in ['map', 'ground', 'spawn']:
                                old_file = os.path.join(map_dir, f"{source_map}_{layer_suffix}.csv")
                                if os.path.exists(old_file):
                                    new_file = os.path.join(map_dir, f"{updated_source_name}_{layer_suffix}.csv")
                                    os.rename(old_file, new_file)
                            status_message = f"Updated {source_map}."
                            status_message_timer = pygame.time.get_ticks() + 4000
                        except Exception as e:
                            status_message = f"Error renaming {source_map}: {e}"
                            status_message_timer = pygame.time.get_ticks() + 4000
                            continue # Abort if rename fails
                        
                        # 7. Create new empty map files
                        for layer_suffix in ['map', 'ground', 'spawn']:
                            new_filepath = os.path.join(map_dir, f"{new_map_name}_{layer_suffix}.csv")
                            with open(new_filepath, 'w', newline='') as f:
                                # Create an empty 100x100 grid
                                writer = csv.writer(f)
                                for _ in range(MAP_DEFAULT_HEIGHT):
                                    writer.writerow([''] * MAP_DEFAULT_WIDTH)
                        
                        # 8. Refresh FileTree
                        all_map_files = sorted([f for f in os.listdir(map_dir) if map_pattern.match(f)])
                        file_tree = FileTree(0, TOOLBAR_HEIGHT, FILE_TREE_WIDTH, SCREEN_HEIGHT - TOOLBAR_HEIGHT, all_map_files, FONT)
                        
                        # 9. Load the new map
                        current_base_map_name = new_map_name
                        file_tree.selected_map = f"{new_map_name}_map.csv" # Select it in the tree
                        load_map(game_map, current_base_map_name, map_dir)
                        modified_maps.add(current_base_map_name) # Mark new map as modified
                        
                    elif modal_action['action'] == 'cancel':
                        pass # Just close the modal
                continue

            # Handle events for UI components
            # --- MODIFIED: Sync sidebar selection with tile_to_place ---
            sidebar.handle_event(event)
            if sidebar.selected_tile:
                tile_to_place = None # Deactivate stair tool if a sidebar tile is clicked
                selection_mode = False
            # --- END MODIFICATION ---

            tree_action = file_tree.handle_event(event)
            if tree_action:
                if tree_action['action'] == 'select_map':
                    selected_map_from_tree = tree_action['map_name'].replace("_map.csv", "")
                    if selected_map_from_tree and selected_map_from_tree != current_base_map_name:
                        current_base_map_name = selected_map_from_tree
                        load_map(game_map, current_base_map_name, map_dir)
                        # Reset camera position and zoom when loading a new map
                        camera_offset_x = FILE_TREE_WIDTH + RULER_SIZE
                        camera_offset_y = TOOLBAR_HEIGHT + RULER_SIZE
                        zoom_level_index = INITIAL_ZOOM_INDEX
                        current_zoom_scale = ZOOM_LEVELS[zoom_level_index]
                        status_message = f"Switched to map '{current_base_map_name}'"
                        status_message_timer = pygame.time.get_ticks() + 2000
                elif tree_action['action'] == 'toggle_visibility':
                    layer_name = tree_action['layer'].replace(f"{current_base_map_name}_", "").replace(".csv","")
                    game_map.layer_properties[layer_name] = tree_action['properties']
                elif tree_action['action'] == 'set_opacity':
                    layer_name = tree_action['layer'].replace(f"{current_base_map_name}_", "").replace(".csv","")
                    game_map.layer_properties[layer_name] = tree_action['properties']
                elif tree_action['action'] == 'set_active_layer':
                    game_map.set_active_layer(tree_action['layer_name'])

            action = toolbar.handle_event(event)
            if action:
                if action == "NEW MAP":
                    new_map_modal = NewMapModal(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 125, 300, 250, FONT, current_base_map_name)
                    new_map_modal.active = True
                elif action == "DELETE MAP":
                    for filename in os.listdir(map_dir):
                        if filename.startswith(current_base_map_name):
                            os.remove(os.path.join(map_dir, filename))
                    if current_base_map_name in modified_maps:
                        modified_maps.remove(current_base_map_name)
                    all_map_files = sorted([f for f in os.listdir(map_dir) if map_pattern.match(f)])
                    file_tree = FileTree(0, TOOLBAR_HEIGHT, FILE_TREE_WIDTH, SCREEN_HEIGHT - TOOLBAR_HEIGHT, all_map_files, FONT)
                    current_base_map_name = file_tree.selected_map.replace("_map.csv", "") if file_tree.selected_map else "map_L1_P0_0_0_0_0"
                    load_map(game_map, current_base_map_name, map_dir)
                
                # --- MODIFIED: All tools now sync variables ---
                elif action == "ERASER":
                    sidebar.selected_tile = "eraser"
                    tile_to_place = None 
                    selection_mode = False
                elif action == "PLAYER SPAWN":
                    sidebar.selected_tile = "P"
                    tile_to_place = None
                    selection_mode = False
                elif action == "ZOMBIE SPAWN":
                    sidebar.selected_tile = "Z"
                    tile_to_place = None
                    selection_mode = False
                elif action == "ITEM SPAWN":
                    sidebar.selected_tile = "I"
                    tile_to_place = None
                    selection_mode = False
                elif action == "SELECTION":
                    selection_mode = True
                    sidebar.selected_tile = None
                    tile_to_place = None
                elif action == "STAIR L1":
                    tile_to_place = "[1]"
                    sidebar.selected_tile = None # Deactivate sidebar tool
                    status_message = "Stair tool: [1] (To Layer 1)"
                    status_message_timer = pygame.time.get_ticks()
                elif action == "STAIR L2":
                    tile_to_place = "[2]"
                    sidebar.selected_tile = None # Deactivate sidebar tool
                    status_message = "Stair tool: [2] (To Layer 2)"
                    status_message_timer = pygame.time.get_ticks()

                    
                elif action == "SAVE MAP":
                    save_map(game_map, current_base_map_name, map_dir)
                    status_message = f"Map '{current_base_map_name}' saved!"
                    status_message_timer = pygame.time.get_ticks() + 2000
                    if current_base_map_name in modified_maps:
                        modified_maps.remove(current_base_map_name)

                elif action == "EXPORT PNG":
                    if game_map and current_base_map_name:
                        try:
                            print("Exporting map to PNG...")
                            # 1. Calculate full map size in pixels
                            map_width_px = game_map.width * TILE_SIZE
                            map_height_px = game_map.height * TILE_SIZE
                            
                            # 2. Create a new surface for the export
                            #    Using pygame.SRCALPHA allows layers with opacity to blend correctly
                            export_surface = pygame.Surface((map_width_px, map_height_px), pygame.SRCALPHA)
                            export_surface.fill((0, 0, 0, 0)) # Fill with transparency

                            # 3. Render the map at 1:1 scale (zoom_scale=1.0)
                            #    This uses your existing render function, which respects
                            #    layer visibility and opacity from the file tree.
                            game_map.render(
                                surface=export_surface,
                                tiles=map_tiles,
                                font=toolbar.font,
                                offset=(0, 0),
                                zoom_scale=1.0
                            )

                            # 4. Define filename and save
                            export_filename = f"{current_base_map_name}_export.png"
                            pygame.image.save(export_surface, export_filename)
                            
                            # 5. Set status message
                            status_message = f"Saved {export_filename}"
                            status_message_timer = pygame.time.get_ticks()
                            print(f"Successfully exported map to {export_filename}")

                        except Exception as e:
                            status_message = f"Error exporting map: {e}"
                            status_message_timer = pygame.time.get_ticks()
                            print(e)


            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if event.key == pygame.K_TAB: # Cycle through layers
                    if game_map.default_layers: # Use default_layers which now stores detected layers
                        current_layer_index = game_map.default_layers.index(game_map.active_layer_name)
                        next_layer_index = (current_layer_index + 1) % len(game_map.default_layers)
                        game_map.set_active_layer(game_map.default_layers[next_layer_index])
                elif event.key == pygame.K_s and (mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META): # Save map
                    save_map(game_map, current_base_map_name, map_dir)
                    status_message = f"Map '{current_base_map_name}' saved!"
                    status_message_timer = pygame.time.get_ticks() + 2000 # Display for 2 seconds
                    if current_base_map_name in modified_maps:
                        modified_maps.remove(current_base_map_name)
                elif event.key == pygame.K_n and (mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META):
                    new_map_modal.active = True

                # --- NEW: Handle CTRL+Z for Undo ---
                elif event.key == pygame.K_z and (mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META):
                    game_map.undo()
                    modified_maps.add(current_base_map_name)
                    status_message = "Undo!"
                    status_message_timer = pygame.time.get_ticks() + 1000

                # --- NEW: Handle CTRL+C for Copy ---
                elif event.key == pygame.K_c and (mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META):
                    if selection_rect:
                        clipboard = game_map.get_tiles_in_rect(selection_rect, game_map.active_layer_name)
                        status_message = "Area copied!"
                        status_message_timer = pygame.time.get_ticks() + 2000
                
                # --- NEW: Handle CTRL+V for Paste ---
                elif event.key == pygame.K_v and (mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META):
                    if clipboard:
                        # Get current mouse position in map coordinates to paste
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        if map_view_rect.collidepoint(mouse_x, mouse_y):
                            adjusted_mouse_x = (mouse_x - camera_offset_x) / current_zoom_scale
                            adjusted_mouse_y = (mouse_y - camera_offset_y) / current_zoom_scale
                            map_x = int(adjusted_mouse_x // TILE_SIZE)
                            map_y = int(adjusted_mouse_y // TILE_SIZE)
                            
                            game_map.paste_tiles((map_x, map_y), clipboard, game_map.active_layer_name)
                            modified_maps.add(current_base_map_name)
                            status_message = "Pasted!"
                            status_message_timer = pygame.time.get_ticks() + 2000

                # --- NEW: Handle DELETE to clear selection ---
                elif event.key == pygame.K_DELETE:
                    if selection_rect:
                        game_map.clear_rect(selection_rect, game_map.active_layer_name)
                        modified_maps.add(current_base_map_name)
                        status_message = "Area cleared!"
                        status_message_timer = pygame.time.get_ticks() + 2000


            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos

                clicked_ui_element = False
                for direction, rect in connection_ui_rects.items():
                    if rect.collidepoint(mouse_x, mouse_y):
                        conn_id = current_map_connections[direction]
                        if conn_id > 0:
                            # Find and load the connected map
                            opposite_dir_map = {'TOP': 'BOTTOM', 'BOTTOM': 'TOP', 'LEFT': 'RIGHT', 'RIGHT': 'LEFT'}
                            opposite_dir = opposite_dir_map[direction]
                            
                            found_map = find_connecting_map(conn_id, opposite_dir, current_map_layer, map_dir)
                            
                            if found_map:
                                current_base_map_name = found_map
                                file_tree.selected_map = f"{found_map}_map.csv"
                                load_map(game_map, current_base_map_name, map_dir)
                                status_message = f"Switched to connected map: {found_map}"
                                status_message_timer = pygame.time.get_ticks() + 2000
                            else:
                                status_message = f"Error: No map found for connection {direction} ({conn_id})"
                                status_message_timer = pygame.time.get_ticks() + 2000
                        else:
                            # ID is 0, open the new map modal pre-filled
                            new_map_modal = NewMapModal(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 125, 300, 250, FONT, current_base_map_name)
                            new_map_modal.preselect_direction(direction)
                            new_map_modal.active = True
                        
                        clicked_ui_element = True
                        break
                
                if clicked_ui_element:
                    continue

                # Scroll wheel for zoom
                if event.button == 4: # Scroll up (zoom in)
                    zoom_level_index = min(len(ZOOM_LEVELS) - 1, zoom_level_index + 1)
                    current_zoom_scale = ZOOM_LEVELS[zoom_level_index]
                elif event.button == 5: # Scroll down (zoom out)
                    zoom_level_index = max(0, zoom_level_index - 1)
                    current_zoom_scale = ZOOM_LEVELS[zoom_level_index]
                elif event.button == 3: # Right click for dragging
                    dragging = True
                    drag_start_pos = event.pos

                if event.button == 1:
                    if map_view_rect.collidepoint(mouse_x, mouse_y):
                        adjusted_mouse_x = (mouse_x - camera_offset_x) / current_zoom_scale
                        adjusted_mouse_y = (mouse_y - camera_offset_y) / current_zoom_scale
                        map_x = int(adjusted_mouse_x // TILE_SIZE)
                        map_y = int(adjusted_mouse_y // TILE_SIZE)

                        # --- LOGIC RE-ORDERED AND CLEANED ---
                        
                        # Determine what tool is active
                        current_tool = tile_to_place if tile_to_place is not None else sidebar.selected_tile

                        if selection_mode:
                            is_selecting = True
                            selection_start_pos = (map_x, map_y)
                            selection_rect = pygame.Rect(selection_start_pos[0], selection_start_pos[1], 0, 0)
                        
                        # --- MODIFIED: Fill selection (uses current_tool) ---
                        elif current_tool and selection_rect and selection_rect.collidepoint(map_x, map_y):
                            tool_to_fill = None if current_tool == "eraser" else current_tool
                            
                            game_map.fill_rect(selection_rect, tool_to_fill, game_map.active_layer_name)
                            modified_maps.add(current_base_map_name)
                            
                        # --- MODIFIED: Placing a single tile (uses current_tool) ---
                        elif current_tool:
                            if 0 <= map_x < game_map.width and 0 <= map_y < game_map.height:
                                tool_to_set = None if current_tool == "eraser" else current_tool
                                active_layer_name = game_map.active_layer_name
                                
                                # Check for stair tile rule
                                is_stair_tile = isinstance(tool_to_set, str) and tool_to_set.startswith("[") and tool_to_set.endswith("]")
                                
                                if is_stair_tile and active_layer_name != 'map':
                                    # If it's a stair AND we are NOT on the 'map' layer, show an error
                                    status_message = "Stairs can ONLY be placed on the 'map' layer."
                                    status_message_timer = pygame.time.get_ticks() + 2000 # Show for 2 seconds
                                else:
                                    # Otherwise, place the tile (either a normal tile or a stair on the 'map' layer)
                                    game_map.set_tile(map_x, map_y, tool_to_set, active_layer_name)
                                    modified_maps.add(current_base_map_name)
                                
                                # Placing a single tile clears the selection
                                selection_rect = None

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    is_selecting = False
                if event.button == 3: # Right click release
                    dragging = False

            if event.type == pygame.MOUSEMOTION:
                if dragging:
                    mouse_x, mouse_y = event.pos
                    prev_mouse_x, prev_mouse_y = drag_start_pos
                    camera_offset_x += (mouse_x - prev_mouse_x)
                    camera_offset_y += (mouse_y - prev_mouse_y)
                    drag_start_pos = event.pos
                elif is_selecting:
                    mouse_x, mouse_y = event.pos
                    if map_view_rect.collidepoint(mouse_x, mouse_y):
                        adjusted_mouse_x = (mouse_x - camera_offset_x) / current_zoom_scale
                        adjusted_mouse_y = (mouse_y - camera_offset_y) / current_zoom_scale
                        map_x = int(adjusted_mouse_x // TILE_SIZE)
                        map_y = int(adjusted_mouse_y // TILE_SIZE)
                        
                        if selection_start_pos:
                            x = min(selection_start_pos[0], map_x)
                            y = min(selection_start_pos[1], map_y)
                            width = abs(selection_start_pos[0] - map_x) + 1
                            height = abs(selection_start_pos[1] - map_y) + 1
                            selection_rect = pygame.Rect(x, y, width, height)

        # Update window title if map is modified
        caption = "Bit Rot - Map Editor"
        if current_base_map_name in modified_maps:
            caption += " *"
        pygame.display.set_caption(caption)

        # Drawing
        screen.fill(GREY) # Fill background

        # Draw map
        game_map.render(screen, map_tiles, FONT, offset=(camera_offset_x, camera_offset_y), zoom_scale=current_zoom_scale)

        # Draw grid (only within map view area)
        draw_grid(screen, camera_offset_x, camera_offset_y, current_zoom_scale, game_map.width, game_map.height, map_view_rect)

        # Draw selection rect
        if selection_rect and not is_selecting:
            scaled_tile_size = TILE_SIZE * current_zoom_scale
            screen_rect = pygame.Rect(
                selection_rect.x * scaled_tile_size + camera_offset_x,
                selection_rect.y * scaled_tile_size + camera_offset_y,
                selection_rect.width * scaled_tile_size,
                selection_rect.height * scaled_tile_size
            )
            pygame.draw.rect(screen, YELLOW, screen_rect, 2)
        elif is_selecting and selection_rect:
            scaled_tile_size = TILE_SIZE * current_zoom_scale
            screen_rect = pygame.Rect(
                selection_rect.x * scaled_tile_size + camera_offset_x,
                selection_rect.y * scaled_tile_size + camera_offset_y,
                selection_rect.width * scaled_tile_size,
                selection_rect.height * scaled_tile_size
            )
            pygame.draw.rect(screen, YELLOW, screen_rect, 2)

        # Draw rulers
        draw_rulers(screen, camera_offset_x, camera_offset_y, current_zoom_scale, game_map.width, game_map.height, map_view_rect, FONT)

        connection_ui_rects, current_map_connections, current_map_layer = draw_connection_ui(screen, map_view_rect, FONT, current_base_map_name)

        # Draw File Tree
        file_tree.draw(screen, current_base_map_name, game_map.active_layer_name, modified_maps)

        # Draw sidebar
        sidebar.draw(screen)
        toolbar.draw(screen)

        if new_map_modal.active:
            new_map_modal.draw(screen)

        # Display status message (moved to avoid file tree)
        if pygame.time.get_ticks() < status_message_timer:
            status_text = FONT.render(status_message, True, BLACK)
            screen.blit(status_text, (FILE_TREE_WIDTH + 10, TOOLBAR_HEIGHT + 70))

        # Update the display
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()