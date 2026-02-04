import pygame
import sys
import os
import re
import csv

from editor.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SIDEBAR_WIDTH, TILE_SIZE, ZOOM_LEVELS, 
    INITIAL_ZOOM_INDEX, FILE_TREE_WIDTH, TOOLBAR_HEIGHT, 
    MAP_DEFAULT_WIDTH, MAP_DEFAULT_HEIGHT, MAP_DIR, BUILDINGS_DIR, TAB_BAR_HEIGHT
)
# CHANGED: Added load_items_from_xml to imports
from editor.assets import load_map_tiles_from_xml, load_sprite_images, load_items_from_xml
from editor.map import Map
from editor.ui import Sidebar, Toolbar, NewBuildingModal 
from editor.file_tree import FileTree

# Initialize Pygame
pygame.init()
pygame.font.init()

# Display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("Bit Rot - Map Editor")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (200, 200, 200)
DARK_GREY = (100, 100, 100)
LIGHT_GREY = (220, 220, 220)
YELLOW = (255, 255, 0)

FONT = pygame.font.Font(None, 24)

# Regex Patterns
MAP_PATTERN = re.compile(r"(map_L\d+_P(?:\d+_)*\d+)(_light|_roof|_map|_spawn|_ground)?\.csv")
BUILDING_PATTERN = re.compile(r"(.+)(_light|_roof|_map|_spawn|_ground)\.csv")

def get_map_dimensions(map_name, map_dir):
    """Attempts to determine map width and height by reading one of its files."""
    try:
        for f in os.listdir(map_dir):
            if f.startswith(f"{map_name}_") and f.endswith(".csv"):
                 try:
                     with open(os.path.join(map_dir, f), 'r') as csvfile:
                         reader = list(csv.reader(csvfile))
                         height = len(reader)
                         width = len(reader[0]) if height > 0 else 0
                         return width, height
                 except:
                     continue
    except OSError:
        pass
    return None

def load_map_layers(game_map, map_name, map_dir):
    """Loads map layers given a base name and directory, resizing game_map to fit."""
    
    # Resize map if we can determine dimensions from files
    dims = get_map_dimensions(map_name, map_dir)
    if dims:
        game_map.resize(dims[0], dims[1])
    
    game_map.layers = {}
    # Ensure all defaults exist after resize/clear
    for l in game_map.default_layers:
         if l not in game_map.layers:
             game_map.layers[l] = [[None for _ in range(game_map.width)] for _ in range(game_map.height)]
             
    game_map.active_layer_name = None
    detected_layers = []

    if os.path.exists(map_dir):
        for filename in os.listdir(map_dir):
            if filename.startswith(f'{map_name}_') and filename.endswith('.csv'):
                for suffix in ['light', 'roof', 'map', 'ground', 'spawn']:
                     if filename.endswith(f"_{suffix}.csv"):
                         # Check strict match to avoid partial matches
                         if filename == f"{map_name}_{suffix}.csv":
                             detected_layers.append(suffix)
                             game_map.load_from_csv(os.path.join(map_dir, filename), suffix)

    if detected_layers:
        detected_layers.sort()
        # Restore default layers if missing
        for l in ['light', 'roof', 'map', 'spawn', 'ground']:
             if l not in game_map.layers:
                 game_map.layers[l] = [[None for _ in range(game_map.width)] for _ in range(game_map.height)]
                 
        game_map.default_layers = detected_layers
        game_map.set_active_layer(detected_layers[0])
    else:
        # Default empty
        game_map.default_layers = ['light', 'roof', 'map', 'spawn', 'ground']
        for l in game_map.default_layers:
            game_map.layers[l] = [[None for _ in range(game_map.width)] for _ in range(game_map.height)]
        game_map.set_active_layer('map')

def save_map_layers(game_map, map_name, map_dir):
    for layer in game_map.layers.keys():
        path = os.path.join(map_dir, f"{map_name}_{layer}.csv")
        game_map.save_to_csv(path, layer)
        print(f"Saved {path}")
        
def draw_rulers(surface, ox, oy, scale, w, h, view_rect, font):
    size = int(TILE_SIZE * scale)
    # Top
    top_y = view_rect.top - 20
    pygame.draw.rect(surface, DARK_GREY, (view_rect.left, top_y, view_rect.width, 20))
    for x in range(w):
        px = int(x * size + ox)
        if view_rect.left <= px <= view_rect.right:
            surface.blit(font.render(str(x), True, WHITE), (px+2, top_y+2))
    # Left
    left_x = view_rect.left - 20
    pygame.draw.rect(surface, DARK_GREY, (left_x, view_rect.top, 20, view_rect.height))
    for y in range(h):
        py = int(y * size + oy)
        if view_rect.top <= py <= view_rect.bottom:
            surface.blit(font.render(str(y), True, WHITE), (left_x+2, py+2))

def draw_grid(surface, offset_x, offset_y, zoom_scale, map_width, map_height, map_view_rect):
    scaled_tile_size = int(TILE_SIZE * zoom_scale)
    for x in range(map_width + 1):
        line_x = offset_x + x * scaled_tile_size
        if map_view_rect.left <= line_x <= map_view_rect.right:
            start_y = max(map_view_rect.top, offset_y)
            end_y = min(map_view_rect.bottom, offset_y + map_height * scaled_tile_size)
            if start_y < end_y:
                pygame.draw.line(surface, LIGHT_GREY, (line_x, start_y), (line_x, end_y))
    for y in range(map_height + 1):
        line_y = offset_y + y * scaled_tile_size
        if map_view_rect.top <= line_y <= map_view_rect.bottom:
            start_x = max(map_view_rect.left, offset_x)
            end_x = min(map_view_rect.right, offset_x + map_width * scaled_tile_size)
            if start_x < end_x:
                pygame.draw.line(surface, LIGHT_GREY, (start_x, line_y), (end_x, line_y))

def paste_building_on_map(game_map, building_name, building_dir, target_x, target_y):
    """Pastes all layers of a building onto the map."""
    if not os.path.exists(building_dir): return
    for f in os.listdir(building_dir):
        if f.startswith(f"{building_name}_") and f.endswith(".csv"):
             for suffix in ['light', 'roof', 'map', 'ground', 'spawn']:
                 if f == f"{building_name}_{suffix}.csv":
                     try:
                         with open(os.path.join(building_dir, f), 'r') as csvfile:
                             reader = list(csv.reader(csvfile))
                             data = [[(c if c != '' else None) for c in row] for row in reader]
                             game_map.paste_tiles((target_x, target_y), data, suffix)
                     except Exception as e:
                         print(f"Error pasting building layer {suffix}: {e}")

def editor():
    # Load Assets
    game_root = os.path.abspath(os.path.join('./game'))
    xml_path = os.path.join(game_root, 'lib', 'data', 'map')
    sprite_path = os.path.join(game_root, 'lib', 'sprites', 'map')
    
    # Paths for Items
    item_sprite_path = os.path.join(game_root, 'lib', 'sprites', 'items')
    item_xml_path = os.path.join(game_root, 'lib', 'data', 'items')

    # Load Tiles
    map_tiles = load_map_tiles_from_xml(xml_path, sprite_path)
    
    # Load Items (Create dirs if not exists)
    if not os.path.exists(item_sprite_path):
        try: os.makedirs(item_sprite_path)
        except OSError: pass
    if not os.path.exists(item_xml_path):
        try: os.makedirs(item_xml_path)
        except OSError: pass

    # CHANGED: Use the new XML loader for items
    item_tiles = load_items_from_xml(item_xml_path, item_sprite_path)

    # Combine for rendering (Items can override tiles if names collide)
    all_render_tiles = {**map_tiles, **item_tiles}

    # Initialize State
    building_map = Map(width=20, height=20) 
    editor_mode = "BUILDING" 
    
    content_y = TOOLBAR_HEIGHT
    
    building_file_tree = FileTree(0, content_y, FILE_TREE_WIDTH, SCREEN_HEIGHT - content_y, BUILDINGS_DIR, BUILDING_PATTERN, FONT, show_saves=False)
    
    toolbar = Toolbar(FILE_TREE_WIDTH, 0, SCREEN_WIDTH - FILE_TREE_WIDTH - SIDEBAR_WIDTH, TOOLBAR_HEIGHT, FONT)
    
    # Pass both map_tiles and item_tiles to Sidebar
    sidebar = Sidebar(SCREEN_WIDTH - SIDEBAR_WIDTH, content_y, map_tiles, item_tiles, FONT)
    
    # Current State Pointers
    current_map_obj = building_map
    current_file_tree = building_file_tree
    
    # Building tree init
    current_building_name = "NewBuilding"
    current_base_name = current_building_name
    current_folder = ""
    current_root_dir = BUILDINGS_DIR

    if building_file_tree.selected_map:
        folder, map_name = building_file_tree.selected_map
        current_building_name = map_name
        current_base_name = map_name
        b_root = os.path.join(BUILDINGS_DIR, folder) if folder else BUILDINGS_DIR
        load_map_layers(building_map, current_building_name, b_root)

    # Modals
    new_building_modal = NewBuildingModal(SCREEN_WIDTH//2-150, SCREEN_HEIGHT//2-150, 300, 300, FONT)

    # Camera
    camera_offset_x = FILE_TREE_WIDTH + 20
    camera_offset_y = content_y + 20
    zoom_index = INITIAL_ZOOM_INDEX
    
    # Interaction
    map_view_rect = pygame.Rect(FILE_TREE_WIDTH + 20, content_y + 20, SCREEN_WIDTH - FILE_TREE_WIDTH - SIDEBAR_WIDTH - 20, SCREEN_HEIGHT - content_y - 20)
    dragging = False
    drag_start = (0,0)
    
    modified_maps = set() 
    status_msg = ""
    status_timer = 0
    
    tile_to_place = None
    selection_start = None
    selection_rect = None
    is_selecting = False
    clipboard = None

    running = True
    while running:
        current_zoom = ZOOM_LEVELS[zoom_index]
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
            # Keyboard Shortcuts
            if event.type == pygame.KEYDOWN:
                ctrl_held = (event.mod & pygame.KMOD_CTRL)
                
                if ctrl_held and event.key == pygame.K_z: # Undo
                    current_map_obj.undo()
                    status_msg = "Undo"
                    status_timer = pygame.time.get_ticks() + 1000
                elif ctrl_held and event.key == pygame.K_s: # Save
                    save_map_layers(current_map_obj, current_base_name, current_root_dir)
                    modified_maps.discard((current_folder, current_base_name))
                    status_msg = "Saved!"
                    status_timer = pygame.time.get_ticks() + 1000
                elif ctrl_held and event.key == pygame.K_c: # Copy
                     if selection_rect:
                        clipboard = current_map_obj.get_tiles_in_rect(selection_rect, current_map_obj.active_layer_name)
                        status_msg = "Copied!"
                        status_timer = pygame.time.get_ticks() + 1000
                elif ctrl_held and event.key == pygame.K_v: # Paste
                     if clipboard:
                        tx, ty = (selection_rect.x, selection_rect.y) if selection_rect else (0,0)
                        current_map_obj.paste_tiles((tx, ty), clipboard, current_map_obj.active_layer_name)
                        status_msg = "Pasted!"
                        status_timer = pygame.time.get_ticks() + 1000
                        modified_maps.add((current_folder, current_base_name))
                elif event.key == pygame.K_DELETE: # Delete/Clear
                     if selection_rect:
                        current_map_obj.clear_rect(selection_rect, current_map_obj.active_layer_name)
                        modified_maps.add((current_folder, current_base_name))
                        status_msg = "Cleared Selection"
                        status_timer = pygame.time.get_ticks() + 1000
                elif event.key == pygame.K_ESCAPE:
                    is_selecting = False
                    selection_rect = None
                    selection_start = None
                    tile_to_place = None
                    sidebar.selected_tile = None
                    sidebar.selected_item = None
                    sidebar.selected_building = None
            
            # Modal Handling
            if new_building_modal.active:
                res = new_building_modal.handle_event(event)
                if res and res['action'] == 'create_building':
                    b_name = res['name']
                    w, h = res['width'], res['height']
                    
                    if not os.path.exists(BUILDINGS_DIR): os.makedirs(BUILDINGS_DIR)
                    
                    for suffix in ['light', 'roof', 'map', 'ground', 'spawn']:
                        path = os.path.join(BUILDINGS_DIR, f"{b_name}_{suffix}.csv")
                        with open(path, 'w', newline='') as f:
                            writer = csv.writer(f)
                            for _ in range(h): writer.writerow([''] * w)
                    
                    building_file_tree.refresh()
                    
                    current_folder = "" 
                    current_root_dir = BUILDINGS_DIR
                    current_base_name = b_name
                    current_building_name = b_name
                    
                    load_map_layers(building_map, b_name, BUILDINGS_DIR)
                    building_file_tree.selected_map = ("", b_name)
                    
                    sidebar.active_tab = "Tiles" 

                    status_msg = f"Created & Opened {b_name}"
                    status_timer = pygame.time.get_ticks() + 2000
                continue

            # Sidebar
            if sidebar.handle_event(event):
                if sidebar.selected_tile or sidebar.selected_item: 
                    tile_to_place = None
                    is_selecting = False
                if sidebar.selected_building:
                    tile_to_place = None
                    is_selecting = False
                continue

            # File Tree
            ft_res = current_file_tree.handle_event(event)
            if ft_res:
                if ft_res['action'] == 'select_map':
                    folder = ft_res['folder']
                    map_name = ft_res['map_name']
                    
                    current_folder = folder
                    current_base_name = map_name
                    current_root_dir = os.path.join(BUILDINGS_DIR, folder) if folder else BUILDINGS_DIR
                    current_building_name = map_name
                    
                    load_map_layers(current_map_obj, map_name, current_root_dir)
                    modified_maps.discard((folder, map_name))
                    
                elif ft_res['action'] == 'toggle_visibility':
                     layer_name = ft_res['layer_name']
                     properties = ft_res['properties']
                     if layer_name in current_map_obj.layer_properties:
                         current_map_obj.layer_properties[layer_name] = properties

                elif ft_res['action'] == 'set_active_layer':
                     current_map_obj.set_active_layer(ft_res['layer_name'])
            
            # Toolbar
            tb_action = toolbar.handle_event(event)
            if tb_action:
                if tb_action == "NEW MAP": pass 
                elif tb_action == "NEW BUILDING": new_building_modal.active = True
                elif tb_action == "SAVE MAP":
                    save_map_layers(current_map_obj, current_base_name, current_root_dir)
                    modified_maps.discard((current_folder, current_base_name))
                    status_msg = "Saved!"
                    status_timer = pygame.time.get_ticks() + 1000

                elif tb_action == "SELECTION":
                    is_selecting = True
                    tile_to_place = None
                    sidebar.selected_tile = None
                    sidebar.selected_item = None
                    sidebar.selected_building = None
                
                elif tb_action == "FILL":
                    if selection_rect and sidebar.selected_tile:
                        current_map_obj.fill_rect(selection_rect, sidebar.selected_tile, current_map_obj.active_layer_name)
                        modified_maps.add((current_folder, current_base_name))
                        status_msg = "Filled Selection!"
                        status_timer = pygame.time.get_ticks() + 1000
                    elif not selection_rect:
                        status_msg = "No Selection!"
                        status_timer = pygame.time.get_ticks() + 1000
                    elif not sidebar.selected_tile:
                        status_msg = "No Tile Selected!"
                        status_timer = pygame.time.get_ticks() + 1000

                elif tb_action == "ERASER":
                    tile_to_place = "eraser"
                    sidebar.selected_tile = None
                    sidebar.selected_item = None
                    sidebar.selected_building = None
                    is_selecting = False
                    
                elif tb_action == "UNDO":
                    current_map_obj.undo()
                    
                elif tb_action == "CLEAR":
                    if selection_rect:
                        current_map_obj.clear_rect(selection_rect, current_map_obj.active_layer_name)
                    else:
                        r = pygame.Rect(0, 0, current_map_obj.width, current_map_obj.height)
                        current_map_obj.clear_rect(r, current_map_obj.active_layer_name)
                    modified_maps.add((current_folder, current_base_name))
                        
                elif tb_action == "COPY":
                    if selection_rect:
                        clipboard = current_map_obj.get_tiles_in_rect(selection_rect, current_map_obj.active_layer_name)
                        status_msg = "Copied!"
                        status_timer = pygame.time.get_ticks() + 1000

                elif tb_action == "PASTE":
                    if clipboard:
                        tx, ty = (selection_rect.x, selection_rect.y) if selection_rect else (0,0)
                        current_map_obj.paste_tiles((tx, ty), clipboard, current_map_obj.active_layer_name)
                        modified_maps.add((current_folder, current_base_name))
                        status_msg = "Pasted!"
                        status_timer = pygame.time.get_ticks() + 1000

            # Map Interaction
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: zoom_index = min(len(ZOOM_LEVELS)-1, zoom_index+1)
                elif event.button == 5: zoom_index = max(0, zoom_index-1)
                elif event.button == 3: dragging = True; drag_start = event.pos
                elif event.button == 1:
                    mx, my = event.pos
                    if map_view_rect.collidepoint(mx, my):
                        map_x = int(((mx - camera_offset_x) / current_zoom) // TILE_SIZE)
                        map_y = int(((my - camera_offset_y) / current_zoom) // TILE_SIZE)
                        
                        if is_selecting:
                            selection_start = (map_x, map_y)
                            selection_rect = pygame.Rect(map_x, map_y, 1, 1)
                        
                        elif sidebar.selected_building and sidebar.active_tab == "Builds":
                             paste_building_on_map(current_map_obj, sidebar.selected_building, BUILDINGS_DIR, map_x, map_y)
                             modified_maps.add((current_folder, current_base_name))
                        
                        elif tile_to_place == "eraser":
                            current_map_obj.set_tile(map_x, map_y, None)
                            modified_maps.add((current_folder, current_base_name))
                        
                        elif sidebar.selected_tile:
                            current_map_obj.set_tile(map_x, map_y, sidebar.selected_tile)
                            modified_maps.add((current_folder, current_base_name))
                            
                        elif sidebar.selected_item:
                            # CONSTRAINT: Items only on spawn layer
                            if current_map_obj.active_layer_name == "spawn":
                                # Storing the item name (string) in the map grid.
                                # Because we mapped the name to the image in load_items_from_xml, 
                                # the sidebar.selected_item is now the user-friendly Name (e.g. "Sparkling Water")
                                current_map_obj.set_tile(map_x, map_y, sidebar.selected_item)
                                modified_maps.add((current_folder, current_base_name))
                            else:
                                status_msg = "Items only allowed on 'spawn' layer!"
                                status_timer = pygame.time.get_ticks() + 2000

            # Mouse Up / Motion
            if event.type == pygame.MOUSEBUTTONUP: 
                dragging = False
                if event.button == 1 and is_selecting and selection_start:
                    selection_start = None

            if event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                if dragging:
                    dx, dy = mx - drag_start[0], my - drag_start[1]
                    camera_offset_x += dx
                    camera_offset_y += dy
                    drag_start = event.pos
                
                if is_selecting and selection_start and pygame.mouse.get_pressed()[0]:
                     if map_view_rect.collidepoint(mx, my):
                        map_x = int(((mx - camera_offset_x) / current_zoom) // TILE_SIZE)
                        map_y = int(((my - camera_offset_y) / current_zoom) // TILE_SIZE)
                        
                        x1, y1 = selection_start
                        x2, y2 = map_x, map_y
                        selection_rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2-x1)+1, abs(y2-y1)+1)

        # Render
        screen.fill(GREY)
        
        # Render map using all_render_tiles.
        # Since 'all_render_tiles' now contains the mapping "Sparkling Water" -> Image,
        # the map will visually display the sprite even though the underlying data is the string "Sparkling Water".
        current_map_obj.render(screen, all_render_tiles, FONT, (camera_offset_x, camera_offset_y), current_zoom)
        
        draw_grid(screen, camera_offset_x, camera_offset_y, current_zoom, current_map_obj.width, current_map_obj.height, map_view_rect)

        if selection_rect:
             sx = selection_rect.x * TILE_SIZE * current_zoom + camera_offset_x
             sy = selection_rect.y * TILE_SIZE * current_zoom + camera_offset_y
             sw = selection_rect.width * TILE_SIZE * current_zoom
             sh = selection_rect.height * TILE_SIZE * current_zoom
             pygame.draw.rect(screen, YELLOW, (sx, sy, sw, sh), 2)

        # Rulers and UI
        draw_rulers(screen, camera_offset_x, camera_offset_y, current_zoom, current_map_obj.width, current_map_obj.height, map_view_rect, FONT)
        
        current_file_tree.draw(screen, current_base_name, current_folder, current_map_obj.active_layer_name, modified_maps)
        
        sidebar.draw(screen)
        toolbar.draw(screen)
        
        if new_building_modal.active: new_building_modal.draw(screen)
        
        if pygame.time.get_ticks() < status_timer:
            screen.blit(FONT.render(status_msg, True, BLACK), (FILE_TREE_WIDTH + 10, content_y + 50))

        pygame.display.flip()

if __name__ == "__main__":
    editor()