import pygame
import re
import os

from editor.assets import load_editor_icons
from editor.config import ICON_SIZE

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

        self.refresh()
        
        self.selected_map = self.map_names[0] if self.map_names else None
        self.expanded_maps = {}
        self.layer_properties = {}
        
        # Initialize default properties
        for base_name, layers in self.grouped_maps.items():
            self.expanded_maps[base_name] = False
            for layer_file in layers:
                self.layer_properties[layer_file] = {"visible": True, "opacity": 255}

    def refresh(self):
        """Refreshes the file list from the directory."""
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)
            
        files = sorted([f for f in os.listdir(self.root_dir) if self.file_pattern.match(f)])
        self.grouped_maps = self._group_maps(files)
        self.map_names = sorted(self.grouped_maps.keys())

    def _group_maps(self, map_files):
        grouped = {}
        for f in map_files:
            match = self.file_pattern.match(f)
            if match:
                # Group 1 is the base name (e.g., "map_L1..." or "House1")
                base_name = match.group(1)
                if base_name not in grouped:
                    grouped[base_name] = []
                grouped[base_name].append(f)
        return grouped

    def draw(self, surface, current_map_name, active_layer_name, modified_maps=None):
        if modified_maps is None:
            modified_maps = set()
        pygame.draw.rect(surface, (200, 200, 200), (self.x, self.y, self.width, self.height))

        # Display current map and layer info
        map_info_y = self.y + 5
        map_text = f"Active: {current_map_name}"
        layer_text = f"Layer: {active_layer_name}"
        map_surf = self.font.render(map_text, True, (0, 0, 0))
        layer_surf = self.font.render(layer_text, True, (0, 0, 0))
        surface.blit(map_surf, (self.x + 10, map_info_y))
        surface.blit(layer_surf, (self.x + 10, map_info_y + self.line_height))

        # Clipping area for the list
        list_rect = pygame.Rect(self.x, self.y + (self.line_height * 2.5), self.width, self.height - (self.line_height * 2.5))
        surface.set_clip(list_rect)

        display_y = list_rect.y - self.scroll_offset
        
        for map_name in self.map_names:
            # Draw base map name
            icon = "[-]" if self.expanded_maps.get(map_name) else "[+]"
            modified_indicator = "*" if map_name in modified_maps else ""
            text = f"{icon} {map_name}{modified_indicator}"
            
            # Highlight selected
            if map_name == current_map_name: # Highlight active map
                pygame.draw.rect(surface, (150, 150, 250), (self.x + 5, display_y, self.width - 10, self.line_height - 2))
            
            text_surface = self.font.render(text, True, (0, 0, 0))
            surface.blit(text_surface, (self.x + 10, display_y))
            display_y += self.line_height

            # Draw layers if expanded
            if self.expanded_maps.get(map_name):
                layer_order = ['roof', 'map', 'spawn', 'ground']
                
                layer_file_lookup = {}
                for lf in self.grouped_maps[map_name]:
                    # Attempt to extract layer suffix
                    # Check against known suffixes
                    found_layer = None
                    for suffix in layer_order:
                        if lf.endswith(f"_{suffix}.csv"):
                            found_layer = suffix
                            break
                    if found_layer:
                        layer_file_lookup[found_layer] = lf

                for layer_name in layer_order:
                    layer_file = layer_file_lookup.get(layer_name)
                    if not layer_file: 
                        continue

                    # Ensure properties exist (for new files refreshed)
                    if layer_file not in self.layer_properties:
                        self.layer_properties[layer_file] = {"visible": True, "opacity": 255}
                    
                    prop = self.layer_properties[layer_file]
                    
                    # Highlight active layer
                    if layer_name == active_layer_name and map_name == current_map_name:
                        pygame.draw.rect(surface, LIGHT_BLUE, (self.x + 10, display_y, self.width - 20, self.line_height - 2))

                    # Layer name
                    layer_text_str = f"    {layer_name}"
                    layer_surf = self.font.render(layer_text_str, True, (50, 50, 50))
                    surface.blit(layer_surf, (self.x + 15, display_y))

                    # View/Hide button
                    icon = self.icons["hide"] if prop["visible"] else self.icons["view"]
                    vh_rect = pygame.Rect(self.x + self.width - 150, display_y - 6, ICON_SIZE, ICON_SIZE)
                    surface.blit(icon, vh_rect)

                    # Opacity controls
                    op_rect = pygame.Rect(self.x + self.width - 80, display_y, 70, self.line_height - 5)
                    op_text = f"OP:{prop['opacity']}"
                    op_surf = self.font.render(op_text, True, (0,0,0))
                    surface.blit(op_surf, (op_rect.x + 5, op_rect.y + 2))

                    display_y += self.line_height
        
        surface.set_clip(None)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mouse_x, mouse_y = event.pos
                if self.x <= mouse_x <= self.x + self.width and self.y <= mouse_y <= self.y + self.height:
                    
                    list_start_y = self.y + (self.line_height * 2.5)
                    if mouse_y < list_start_y:
                        return None # Clicked header

                    current_y = list_start_y - self.scroll_offset
                    for map_name in self.map_names:
                        # Check click on base map name
                        base_rect = pygame.Rect(self.x, current_y, self.width, self.line_height)
                        if base_rect.collidepoint(mouse_x, mouse_y):
                            # Toggle expand/collapse
                            if mouse_x < self.x + 30:
                                self.expanded_maps[map_name] = not self.expanded_maps.get(map_name, False)
                                return None
                            else:
                                self.selected_map = map_name
                                return {"action": "select_map", "map_name": map_name}
                        
                        current_y += self.line_height

                        # Check click on layers if expanded
                        if self.expanded_maps.get(map_name):
                            layer_order = ['roof', 'map', 'spawn', 'ground']
                            layer_file_lookup = {}
                            for lf in self.grouped_maps[map_name]:
                                for suffix in layer_order:
                                    if lf.endswith(f"_{suffix}.csv"):
                                        layer_file_lookup[suffix] = lf
                                        break

                            for layer_name in layer_order:
                                layer_file = layer_file_lookup.get(layer_name)
                                if not layer_file: continue
                                
                                if layer_file not in self.layer_properties:
                                    self.layer_properties[layer_file] = {"visible": True, "opacity": 255}

                                layer_rect = pygame.Rect(self.x, current_y, self.width, self.line_height)
                                if layer_rect.collidepoint(mouse_x, mouse_y):
                                    # Check view/hide click
                                    vh_rect = pygame.Rect(self.x + self.width - 150, current_y, ICON_SIZE, ICON_SIZE)
                                    if vh_rect.collidepoint(mouse_x, mouse_y):
                                        self.layer_properties[layer_file]["visible"] = not self.layer_properties[layer_file]["visible"]
                                        # Pass back clean layer_name so editor can update Map
                                        return {
                                            "action": "toggle_visibility", 
                                            "layer_file": layer_file, 
                                            "layer_name": layer_name,
                                            "properties": self.layer_properties[layer_file]
                                        }
                                    
                                    # Check opacity click (placeholder)
                                    op_rect = pygame.Rect(self.x + self.width - 80, current_y, 70, self.line_height - 5)
                                    if op_rect.collidepoint(mouse_x, mouse_y):
                                        # Simple opacity toggle for now
                                        current_op = self.layer_properties[layer_file]["opacity"]
                                        self.layer_properties[layer_file]["opacity"] = 0 if current_op == 255 else 255
                                        return {
                                            "action": "set_opacity", 
                                            "layer_file": layer_file, 
                                            "layer_name": layer_name,
                                            "properties": self.layer_properties[layer_file]
                                        }
                                    else:
                                        # Clicked on layer name
                                        return {"action": "set_active_layer", "layer_name": layer_name}

                                current_y += self.line_height

            elif event.button == 4:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - self.line_height)
            elif event.button == 5:  # Scroll down
                # Recalculate total height
                total_height = len(self.map_names) * self.line_height
                for name, expanded in self.expanded_maps.items():
                    if expanded:
                        total_height += len(self.grouped_maps[name]) * self.line_height
                max_scroll = max(0, total_height - (self.height - self.line_height * 3))
                self.scroll_offset = min(max_scroll, self.scroll_offset + self.line_height)
        return None