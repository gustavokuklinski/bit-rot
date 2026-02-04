# editor/file_tree.py
import pygame
import re
import os

from editor.assets import load_editor_icons
from editor.config import ICON_SIZE, GAME_ROOT

YELLOW = (255, 255, 0)
LIGHT_BLUE = (180, 180, 220)

class FileTree:
    def __init__(self, x, y, width, height, root_dir, file_pattern, font, show_saves=True):
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
        self.show_saves = show_saves # New flag to control save folder visibility

        # Data structures
        self.folders = []          # List of folder names (or absolute paths for saves). "" for root.
        self.map_data = {}         # { folder: { map_name: [files] } }
        self.expanded_folders = {} # { folder: bool }
        self.expanded_maps = {}    # { (folder, map_name): bool }
        self.layer_properties = {} # { relative_path: dict }
        
        self.selected_map = None   # (folder, map_name)
        
        # Scrollbar State
        self.max_scroll = 0
        self.dragging_scroll = False
        self.scrollbar_track_rect = None
        self.scrollbar_thumb_rect = None
        self.scroll_start_mouse_y = 0
        self.scroll_start_offset = 0
        
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
        # Only scan saves if explicitly enabled
        if self.show_saves:
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

    def _get_content_height(self):
        """Calculates the total height of the tree in pixels."""
        h = 0
        for folder in self.folders:
            if folder != "":
                h += self.line_height
            
            if folder == "" or self.expanded_folders.get(folder):
                if folder in self.map_data:
                    for map_name in self.map_data[folder]:
                        h += self.line_height
                        if self.expanded_maps.get((folder, map_name)):
                            # 5 layers: light, roof, map, spawn, ground
                            h += 5 * self.line_height 
        return h

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
        
        # Calculate Scrolling
        content_height = self._get_content_height()
        self.max_scroll = max(0, content_height - list_rect.height)
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

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
                
                # Optimization: Only draw if visible
                if display_y + self.line_height > list_rect.y and display_y < list_rect.bottom:
                    surface.blit(self.font.render(text, True, (0, 0, 0)), (self.x + 10, display_y))
                
                display_y += self.line_height
                indent = 25

            # Draw Maps
            if folder == "" or self.expanded_folders.get(folder):
                maps = self.map_data.get(folder, {})
                for map_name in sorted(maps.keys()):
                    map_key = (folder, map_name)
                    
                    is_modified = map_key in modified_maps
                    if not is_modified and isinstance(modified_maps, set):
                         if map_name in modified_maps:
                             is_modified = True
                    modified_indicator = "*" if is_modified else ""
                    
                    # Highlight selected map
                    if map_name == current_map_name and folder == current_folder: 
                        if display_y + self.line_height > list_rect.y and display_y < list_rect.bottom:
                            # Width reduced by 15 to account for scrollbar
                            pygame.draw.rect(surface, (150, 150, 250), (self.x + 5, display_y, self.width - 15, self.line_height - 2))
                    
                    icon = "[-]" if self.expanded_maps.get(map_key) else "[+]"
                    text = f"{icon} {map_name}{modified_indicator}"
                    
                    if display_y + self.line_height > list_rect.y and display_y < list_rect.bottom:
                        surface.blit(self.font.render(text, True, (0, 0, 0)), (self.x + indent, display_y))
                    
                    display_y += self.line_height

                    # Draw Layers
                    if self.expanded_maps.get(map_key):
                        layer_order = ['light','roof','map', 'spawn', 'ground']
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
                            
                            if display_y + self.line_height > list_rect.y and display_y < list_rect.bottom:
                                if layer_name == active_layer_name and map_name == current_map_name and folder == current_folder:
                                    pygame.draw.rect(surface, LIGHT_BLUE, (self.x + indent + 5, display_y, self.width - (indent + 25), self.line_height - 2))

                                layer_text_str = f"    {layer_name}"
                                layer_surf = self.font.render(layer_text_str, True, (50, 50, 50))
                                surface.blit(layer_surf, (self.x + indent + 5, display_y))

                                icon = self.icons["hide"] if prop["visible"] else self.icons["view"]
                                # Shifted left by 15px to make room for scrollbar
                                vh_rect = pygame.Rect(self.x + self.width - 165, display_y - 6, ICON_SIZE, ICON_SIZE)
                                surface.blit(icon, vh_rect)

                            display_y += self.line_height
        
        surface.set_clip(None)

        # Scrollbar Rendering
        if self.max_scroll > 0:
            track_rect = pygame.Rect(self.x + self.width - 12, list_rect.y, 12, list_rect.height)
            self.scrollbar_track_rect = track_rect
            pygame.draw.rect(surface, (180, 180, 180), track_rect)
            
            thumb_height = max(20, (list_rect.height / content_height) * list_rect.height)
            scroll_ratio = self.scroll_offset / self.max_scroll
            thumb_y = list_rect.y + scroll_ratio * (list_rect.height - thumb_height)
            
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, 12, thumb_height)
            self.scrollbar_thumb_rect = thumb_rect
            pygame.draw.rect(surface, (100, 100, 100), thumb_rect)
        else:
            self.scrollbar_track_rect = None
            self.scrollbar_thumb_rect = None

    def handle_event(self, event):
        # Global mouse up
        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_scroll = False

        # Mouse motion for dragging scrollbar
        if event.type == pygame.MOUSEMOTION:
            if self.dragging_scroll and self.scrollbar_thumb_rect and self.max_scroll > 0:
                dy = event.pos[1] - self.scroll_start_mouse_y
                
                track_h = self.scrollbar_track_rect.height
                thumb_h = self.scrollbar_thumb_rect.height
                movable_space = track_h - thumb_h
                
                if movable_space > 0:
                    # Calculate amount to scroll based on pixel movement
                    scroll_per_pixel = self.max_scroll / movable_space
                    scroll_change = dy * scroll_per_pixel
                    
                    self.scroll_offset = self.scroll_start_offset + scroll_change
                    self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
                return None 

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # Check Scrollbar Interactions first (if visible)
            if self.scrollbar_thumb_rect and self.scrollbar_thumb_rect.collidepoint(mx, my):
                self.dragging_scroll = True
                self.scroll_start_mouse_y = my
                self.scroll_start_offset = self.scroll_offset
                return None 
            elif self.scrollbar_track_rect and self.scrollbar_track_rect.collidepoint(mx, my):
                # Page jump on track click
                if my < self.scrollbar_thumb_rect.y:
                    self.scroll_offset = max(0, self.scroll_offset - self.height)
                else:
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + self.height)
                return None 

            if event.button == 1:
                # Content Area Clicks
                if self.x <= mx <= self.x + self.width and self.y <= my <= self.y + self.height:
                    
                    list_start_y = self.y + (self.line_height * 2.5)
                    if my < list_start_y:
                        return None 

                    current_y = list_start_y - self.scroll_offset
                    
                    for folder in self.folders:
                        # Folder Click
                        if folder != "":
                            # Use width-15 to avoid clicking through scrollbar
                            folder_rect = pygame.Rect(self.x, current_y, self.width - 15, self.line_height)
                            if folder_rect.collidepoint(mx, my):
                                self.expanded_folders[folder] = not self.expanded_folders.get(folder, False)
                                return None
                            current_y += self.line_height
                        
                        # Maps
                        if folder == "" or self.expanded_folders.get(folder):
                            maps = self.map_data[folder]
                            for map_name in sorted(maps.keys()):
                                map_key = (folder, map_name)
                                
                                map_rect = pygame.Rect(self.x, current_y, self.width - 15, self.line_height)
                                if map_rect.collidepoint(mx, my):
                                    toggle_width = 40 if folder else 30
                                    if mx < self.x + toggle_width: 
                                        self.expanded_maps[map_key] = not self.expanded_maps.get(map_key, False)
                                        return None
                                    else:
                                        self.selected_map = map_key
                                        return {"action": "select_map", "folder": folder, "map_name": map_name}
                                
                                current_y += self.line_height
                                
                                # Layers
                                if self.expanded_maps.get(map_key):
                                    layer_order = ['light', 'roof', 'map', 'spawn', 'ground']
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

                                        layer_rect = pygame.Rect(self.x, current_y, self.width - 15, self.line_height)
                                        if layer_rect.collidepoint(mx, my):
                                            # Adjusted click target for eye icon (shifted left)
                                            vh_rect = pygame.Rect(self.x + self.width - 165, current_y, ICON_SIZE, ICON_SIZE)
                                            if vh_rect.collidepoint(mx, my):
                                                self.layer_properties[rel_path]["visible"] = not self.layer_properties[rel_path]["visible"]
                                                return {
                                                    "action": "toggle_visibility", 
                                                    "layer_name": layer_name,
                                                    "properties": self.layer_properties[rel_path]
                                                }
                                            
                                            op_rect = pygame.Rect(self.x + self.width - 95, current_y, 70, self.line_height - 5)
                                            if op_rect.collidepoint(mx, my):
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
                if self.x <= mx <= self.x + self.width and self.y <= my <= self.y + self.height:
                    self.scroll_offset = max(0, self.scroll_offset - (self.line_height * 2))
                    return None
            elif event.button == 5:  # Scroll down
                if self.x <= mx <= self.x + self.width and self.y <= my <= self.y + self.height:
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + (self.line_height * 2))
                    return None
        return None