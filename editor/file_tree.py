import pygame
import re

from editor.assets import load_editor_icons
from editor.config import ICON_SIZE
YELLOW = (255, 255, 0)
LIGHT_BLUE = (180, 180, 220)
class FileTree:
    def __init__(self, x, y, width, height, available_maps, font):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font = font
        self.line_height = 25
        self.scroll_offset = 0
        self.icons = load_editor_icons("./game/resources/sprites/editor")

        self.grouped_maps = self._group_maps(available_maps)
        self.map_names = sorted(self.grouped_maps.keys())
        self.selected_map = self.map_names[0] if self.map_names else None
        
        self.expanded_maps = {}
        self.layer_properties = {}
        for base_name, layers in self.grouped_maps.items():
            self.expanded_maps[base_name] = False
            for layer_file in layers:
                self.layer_properties[layer_file] = {"visible": True, "opacity": 255}

    def _group_maps(self, map_files):
        grouped = {}
        pattern = re.compile(r"(map_L\d+_P(?:\d+_)*\d+)(_map|_spawn|_ground)?\.csv")

        for f in map_files:
            match = pattern.match(f)
            if match:
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
        map_text = f"Active map: {current_map_name}"
        layer_text = f"Editing layer: {active_layer_name}"
        map_surf = self.font.render(map_text, True, (0, 0, 0))
        layer_surf = self.font.render(layer_text, True, (0, 0, 0))
        surface.blit(map_surf, (self.x + 10, map_info_y))
        surface.blit(layer_surf, (self.x + 10, map_info_y + self.line_height))

        display_y = self.y + 5 - self.scroll_offset + (self.line_height * 2)
        for map_name in self.map_names:
            # Draw base map name
            icon = "[-]" if self.expanded_maps.get(map_name) else "[+]"
            modified_indicator = "*" if map_name in modified_maps else ""
            text = f"{icon} {map_name}{modified_indicator}"
            text_surface = self.font.render(text, True, (0, 0, 0))
            
            if map_name == self.selected_map:
                pygame.draw.rect(surface, (150, 150, 250), (self.x + 5, display_y, self.width - 10, self.line_height - 2))
                
            surface.blit(text_surface, (self.x + 10, display_y))
            display_y += self.line_height

            # Draw layers if expanded
            if self.expanded_maps.get(map_name):
                layer_order = ['map', 'spawn', 'ground']
                
                layer_file_lookup = {}
                for lf in self.grouped_maps[map_name]:
                    # Extract layer name (e.g., "map", "spawn", "ground")
                    ln = lf.replace(map_name, "").replace(".csv", "")[1:]
                    layer_file_lookup[ln] = lf

                for layer_name in layer_order:
                    layer_file = layer_file_lookup.get(layer_name)
                    if not layer_file: # Skip if this map doesn't have this layer
                        continue

                    prop = self.layer_properties[layer_file]
                    
                    # --- NEW: Highlight active layer ---
                    if layer_name == active_layer_name and map_name == current_map_name:
                        pygame.draw.rect(surface, LIGHT_BLUE, (self.x + 10, display_y, self.width - 20, self.line_height - 2))

                    # Layer name
                    layer_text = f"    {layer_name}"
                    layer_surf = self.font.render(layer_text, True, (50, 50, 50))
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
                    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mouse_x, mouse_y = event.pos
                if self.x <= mouse_x <= self.x + self.width and self.y <= mouse_y <= self.y + self.height:
                    
                    current_y = self.y + 5 - self.scroll_offset + (self.line_height * 2)
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
                            # --- MODIFIED: Iterate in fixed order to match draw() ---
                            layer_order = ['map', 'spawn', 'ground']
                
                            layer_file_lookup = {}
                            for lf in self.grouped_maps[map_name]:
                                ln = lf.replace(map_name, "").replace(".csv", "")[1:]
                                layer_file_lookup[ln] = lf

                            for layer_name in layer_order:
                                layer_file = layer_file_lookup.get(layer_name)
                                if not layer_file:
                                    continue
                                
                                layer_rect = pygame.Rect(self.x, current_y, self.width, self.line_height)
                                if layer_rect.collidepoint(mouse_x, mouse_y):
                                    # Check view/hide click
                                    vh_rect = pygame.Rect(self.x + self.width - 150, current_y, ICON_SIZE, ICON_SIZE)
                                    if vh_rect.collidepoint(mouse_x, mouse_y):
                                        self.layer_properties[layer_file]["visible"] = not self.layer_properties[layer_file]["visible"]
                                        return {"action": "toggle_visibility", "layer": layer_file, "properties": self.layer_properties[layer_file]}
                                    
                                    # Check opacity click (placeholder)
                                    op_rect = pygame.Rect(self.x + self.width - 80, current_y, 70, self.line_height - 5)
                                    if op_rect.collidepoint(mouse_x, mouse_y):
                                        # Simple opacity toggle for now
                                        current_op = self.layer_properties[layer_file]["opacity"]
                                        self.layer_properties[layer_file]["opacity"] = 0 if current_op == 255 else 255
                                        return {"action": "set_opacity", "layer": layer_file, "properties": self.layer_properties[layer_file]}
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
                max_scroll = max(0, total_height - self.height)
                self.scroll_offset = min(max_scroll, self.scroll_offset + self.line_height)
        return None
