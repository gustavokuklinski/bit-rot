import pygame
import re
import os

from editor.assets import load_editor_icons
from editor.config import ICON_SIZE, GAME_ROOT

YELLOW = (255, 255, 0)
LIGHT_BLUE = (180, 180, 220)

class FileTree:
    def __init__(self, x, y, width, height, root_dir, file_pattern, font):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font = font
        self.root_dir = root_dir
        self.file_pattern = file_pattern
        self.line_height = 25
        self.scroll_offset = 0
        self.icons = load_editor_icons("./game/lib/sprites/editor")

        # Data structures
        self.folders = []          # List of folder names (or absolute paths for saves). "" for root.
        self.map_data = {}         # { folder: { map_name: [files] } }
        self.expanded_folders = {} # { folder: bool }
        self.expanded_maps = {}    # { (folder, map_name): bool }
        self.layer_properties = {} # { relative_path: dict }
        
        self.selected_map = None   # (folder, map_name)
        
        self.refresh()

    def refresh(self):
        """Refreshes the file list from the directory."""
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)
            
        self.folders = []
        self.map_data = {}
        
        # --- 1. Standard Maps (Root Directory) ---
        try:
            items = sorted(os.listdir(self.root_dir))
        except OSError:
            items = []
            
        # Root files
        root_files = [f for f in items if os.path.isfile(os.path.join(self.root_dir, f)) and self.file_pattern.match(f)]
        if root_files:
            folder = ""
            self.folders.append(folder)
            self.map_data[folder] = self._group_maps(root_files)
            self.expanded_folders[folder] = True

        # Standard Subdirectories
        for item in items:
            path = os.path.join(self.root_dir, item)
            if os.path.isdir(path):
                try:
                    sub_files = sorted([f for f in os.listdir(path) if self.file_pattern.match(f)])
                    if sub_files:
                        self.folders.append(item)
                        self.map_data[item] = self._group_maps(sub_files)
                        if item not in self.expanded_folders:
                            self.expanded_folders[item] = False
                except OSError:
                    continue

        # --- 2. Save Folders (External Directory) ---
        # Scan: ./game/save/game/save_TIMESTAMP/map
        save_root = os.path.join(GAME_ROOT, 'save', 'game')
        if os.path.exists(save_root):
            try:
                # Sort reverse to show newest saves first
                save_folders = sorted(os.listdir(save_root), reverse=True)
                for sf in save_folders:
                    sf_path = os.path.join(save_root, sf)
                    map_sub = os.path.join(sf_path, 'map')
                    
                    if os.path.isdir(map_sub):
                        try:
                            # Check for map files inside the 'map' subdirectory
                            save_maps = sorted([f for f in os.listdir(map_sub) if self.file_pattern.match(f)])
                            if save_maps:
                                # Use absolute path as the key so editor.py can load it
                                # os.path.join(base, absolute) returns absolute, bypassing base
                                folder_key = os.path.abspath(map_sub)
                                
                                self.folders.append(folder_key)
                                self.map_data[folder_key] = self._group_maps(save_maps)
                                
                                if folder_key not in self.expanded_folders:
                                    self.expanded_folders[folder_key] = False
                        except OSError:
                            pass
            except OSError:
                pass

        # Initialize default properties for new files
        for folder in self.folders:
            for map_name, files in self.map_data[folder].items():
                map_key = (folder, map_name)
                if map_key not in self.expanded_maps:
                    self.expanded_maps[map_key] = False
                
                for f in files:
                    rel_path = os.path.join(folder, f) if folder else f
                    if rel_path not in self.layer_properties:
                        self.layer_properties[rel_path] = {"visible": True, "opacity": 255}

        # Validate selection
        if self.selected_map:
            sf, sm = self.selected_map
            if sf not in self.map_data or sm not in self.map_data[sf]:
                self.selected_map = None
        
        if not self.selected_map and self.folders:
            first_folder = self.folders[0]
            maps = sorted(self.map_data[first_folder].keys())
            if maps:
                self.selected_map = (first_folder, maps[0])
                if first_folder != "":
                    self.expanded_folders[first_folder] = True

    def _group_maps(self, file_list):
        grouped = {}
        for f in file_list:
            match = self.file_pattern.match(f)
            if match:
                base_name = match.group(1)
                if base_name not in grouped:
                    grouped[base_name] = []
                grouped[base_name].append(f)
        return grouped

    def draw(self, surface, current_map_name, current_folder, active_layer_name, modified_maps=None):
        if modified_maps is None:
            modified_maps = set()
            
        pygame.draw.rect(surface, (200, 200, 200), (self.x, self.y, self.width, self.height))

        # Header
        map_info_y = self.y + 5
        
        # Make display name cleaner if it's a long absolute path
        display_current_folder = current_folder
        if os.path.isabs(current_folder) and current_folder.endswith("map"):
             try:
                 display_current_folder = os.path.basename(os.path.dirname(current_folder))
             except: pass

        disp_name = f"{display_current_folder}/{current_map_name}" if display_current_folder else current_map_name
        
        map_text = f"Active: {disp_name}"
        layer_text = f"Layer: {active_layer_name}"
        
        surface.blit(self.font.render(map_text, True, (0, 0, 0)), (self.x + 10, map_info_y))
        surface.blit(self.font.render(layer_text, True, (0, 0, 0)), (self.x + 10, map_info_y + self.line_height))

        # List Area
        list_rect = pygame.Rect(self.x, self.y + (self.line_height * 2.5), self.width, self.height - (self.line_height * 2.5))
        surface.set_clip(list_rect)

        display_y = list_rect.y - self.scroll_offset
        
        for folder in self.folders:
            indent = 10
            
            if folder != "":
                display_folder = folder
                
                # Check if this is a save folder (Absolute path ending in /map)
                if os.path.isabs(folder) and folder.endswith("map"):
                    try:
                        # Extract "save_TIMESTAMP" from ".../save_TIMESTAMP/map"
                        parent = os.path.dirname(folder)
                        display_folder = os.path.basename(parent)
                    except:
                        pass
                
                icon = "[-]" if self.expanded_folders.get(folder) else "[+]"
                text = f"{icon} {display_folder}"
                surface.blit(self.font.render(text, True, (0, 0, 0)), (self.x + 10, display_y))
                display_y += self.line_height
                indent = 25

            # Draw Maps
            if folder == "" or self.expanded_folders.get(folder):
                maps = self.map_data[folder]
                for map_name in sorted(maps.keys()):
                    map_key = (folder, map_name)
                    
                    is_modified = map_key in modified_maps
                    if not is_modified and isinstance(modified_maps, set):
                         if map_name in modified_maps:
                             is_modified = True
                    modified_indicator = "*" if is_modified else ""
                    
                    if map_name == current_map_name and folder == current_folder: 
                        pygame.draw.rect(surface, (150, 150, 250), (self.x + 5, display_y, self.width - 10, self.line_height - 2))
                    
                    icon = "[-]" if self.expanded_maps.get(map_key) else "[+]"
                    text = f"{icon} {map_name}{modified_indicator}"
                    
                    surface.blit(self.font.render(text, True, (0, 0, 0)), (self.x + indent, display_y))
                    display_y += self.line_height

                    # Draw Layers
                    if self.expanded_maps.get(map_key):
                        layer_order = ['roof','light', 'map', 'spawn', 'ground']
                        layer_file_lookup = {}
                        for lf in maps[map_name]:
                            for suffix in layer_order:
                                if lf.endswith(f"_{suffix}.csv"):
                                    layer_file_lookup[suffix] = lf
                                    break
                        
                        for layer_name in layer_order:
                            layer_file = layer_file_lookup.get(layer_name)
                            if not layer_file: continue
                            
                            rel_path = os.path.join(folder, layer_file) if folder else layer_file
                            if rel_path not in self.layer_properties:
                                self.layer_properties[rel_path] = {"visible": True, "opacity": 255}
                            
                            prop = self.layer_properties[rel_path]
                            
                            if layer_name == active_layer_name and map_name == current_map_name and folder == current_folder:
                                pygame.draw.rect(surface, LIGHT_BLUE, (self.x + indent + 5, display_y, self.width - (indent + 15), self.line_height - 2))

                            layer_text_str = f"    {layer_name}"
                            layer_surf = self.font.render(layer_text_str, True, (50, 50, 50))
                            surface.blit(layer_surf, (self.x + indent + 5, display_y))

                            icon = self.icons["hide"] if prop["visible"] else self.icons["view"]
                            vh_rect = pygame.Rect(self.x + self.width - 150, display_y - 6, ICON_SIZE, ICON_SIZE)
                            surface.blit(icon, vh_rect)

                            op_rect = pygame.Rect(self.x + self.width - 80, display_y, 70, self.line_height - 5)
                            op_text = f"OP:{prop['opacity']}"
                            op_surf = self.font.render(op_text, True, (0,0,0))
                            surface.blit(op_surf, (op_rect.x + 5, op_rect.y + 2))

                            display_y += self.line_height
        
        surface.set_clip(None)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_x, mouse_y = event.pos
                if self.x <= mouse_x <= self.x + self.width and self.y <= mouse_y <= self.y + self.height:
                    
                    list_start_y = self.y + (self.line_height * 2.5)
                    if mouse_y < list_start_y:
                        return None 

                    current_y = list_start_y - self.scroll_offset
                    
                    for folder in self.folders:
                        # Folder Click
                        if folder != "":
                            folder_rect = pygame.Rect(self.x, current_y, self.width, self.line_height)
                            if folder_rect.collidepoint(mouse_x, mouse_y):
                                self.expanded_folders[folder] = not self.expanded_folders.get(folder, False)
                                return None
                            current_y += self.line_height
                        
                        # Maps
                        if folder == "" or self.expanded_folders.get(folder):
                            maps = self.map_data[folder]
                            for map_name in sorted(maps.keys()):
                                map_key = (folder, map_name)
                                
                                map_rect = pygame.Rect(self.x, current_y, self.width, self.line_height)
                                if map_rect.collidepoint(mouse_x, mouse_y):
                                    toggle_width = 40 if folder else 30
                                    if mouse_x < self.x + toggle_width: 
                                        self.expanded_maps[map_key] = not self.expanded_maps.get(map_key, False)
                                        return None
                                    else:
                                        self.selected_map = map_key
                                        return {"action": "select_map", "folder": folder, "map_name": map_name}
                                
                                current_y += self.line_height
                                
                                # Layers
                                if self.expanded_maps.get(map_key):
                                    layer_order = ['roof', 'light','map', 'spawn', 'ground']
                                    layer_file_lookup = {}
                                    for lf in maps[map_name]:
                                        for suffix in layer_order:
                                            if lf.endswith(f"_{suffix}.csv"):
                                                layer_file_lookup[suffix] = lf
                                                break

                                    for layer_name in layer_order:
                                        layer_file = layer_file_lookup.get(layer_name)
                                        if not layer_file: continue
                                        
                                        rel_path = os.path.join(folder, layer_file) if folder else layer_file
                                        if rel_path not in self.layer_properties:
                                            self.layer_properties[rel_path] = {"visible": True, "opacity": 255}

                                        layer_rect = pygame.Rect(self.x, current_y, self.width, self.line_height)
                                        if layer_rect.collidepoint(mouse_x, mouse_y):
                                            vh_rect = pygame.Rect(self.x + self.width - 150, current_y, ICON_SIZE, ICON_SIZE)
                                            if vh_rect.collidepoint(mouse_x, mouse_y):
                                                self.layer_properties[rel_path]["visible"] = not self.layer_properties[rel_path]["visible"]
                                                return {
                                                    "action": "toggle_visibility", 
                                                    "layer_name": layer_name,
                                                    "properties": self.layer_properties[rel_path]
                                                }
                                            
                                            op_rect = pygame.Rect(self.x + self.width - 80, current_y, 70, self.line_height - 5)
                                            if op_rect.collidepoint(mouse_x, mouse_y):
                                                current_op = self.layer_properties[rel_path]["opacity"]
                                                self.layer_properties[rel_path]["opacity"] = 0 if current_op == 255 else 255
                                                return {
                                                    "action": "set_opacity", 
                                                    "layer_name": layer_name,
                                                    "properties": self.layer_properties[rel_path]
                                                }
                                            else:
                                                return {"action": "set_active_layer", "layer_name": layer_name}

                                        current_y += self.line_height

            elif event.button == 4:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - self.line_height)
            elif event.button == 5:  # Scroll down
                total_height = 0
                for f in self.folders:
                    if f != "": total_height += self.line_height
                    if f == "" or self.expanded_folders.get(f):
                         for m in self.map_data[f]:
                             total_height += self.line_height
                             if self.expanded_maps.get((f, m)):
                                 total_height += 4 * self.line_height
                
                max_scroll = max(0, total_height - (self.height - self.line_height * 3))
                self.scroll_offset = min(max_scroll, self.scroll_offset + self.line_height)
        return None