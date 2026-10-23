import pygame
import re
import os
from editor.assets import load_editor_icons
from editor.config import SPRITE_ROOT, ICON_SIZE
from editor.ui import UITheme, UITextBox

def parse_building_sort_key(map_name):
    """
    Sorts by:
    1) Prefix (e.g., 'Building')
    2) Building number (e.g., 6) so that L1_06 and L2_06 appear consecutively
    3) Layer number (e.g., L1 -> 1, L2 -> 2)
    """
    m = re.match(r"^(?P<prefix>.+?)_L(?P<layer>\d+)_(?P<num>\d+)(?P<suffix>.*)$", map_name, re.IGNORECASE)
    if m:
        prefix = m.group("prefix").lower()
        layer_num = int(m.group("layer"))
        try:
            b_num = int(m.group("num"))
        except ValueError:
            b_num = m.group("num")
        suffix = m.group("suffix").lower()
        return (prefix, b_num, layer_num, suffix)
    
    m2 = re.match(r"^(.+?)_L(\d+)(.*)$", map_name, re.IGNORECASE)
    if m2:
        return (m2.group(1).lower(), 999999, int(m2.group(2)), m2.group(3).lower())
    return (map_name.lower(), 999999, 999999, "")

class FileTree:
    def __init__(self, x, y, width, height, root_dir, file_pattern, font, show_saves=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font = font
        self.root_dir = root_dir
        self.file_pattern = file_pattern
        self.line_height = 26
        self.scroll_offset = 0
        self.show_saves = show_saves 
        
        icon_path = os.path.join(SPRITE_ROOT, 'editor')
        self.icons = load_editor_icons(icon_path)
        
        self.default_icon = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
        self.default_icon.fill((100, 100, 100))
        pygame.draw.rect(self.default_icon, (200, 200, 200), self.default_icon.get_rect(), 1)
        
        self.folders = []          
        self.map_data = {}
        self.grouped_maps = {}    # {folder: {group_name: [map_names]}}
        self.expanded_folders = {} 
        self.expanded_groups = {}  # {(folder, group_name): bool}
        self.expanded_maps = {}    # {(folder, map_name): bool}
        self.layer_properties = {} # {(folder, map_name, layer_name): {"visible": bool}}
        
        self.selected_map = None   
        
        # Search Box
        self.search_input = UITextBox(self.x + 10, self.y + 68, self.width - 20, 26, self.font, "")
        
        self.max_scroll = 0
        self.dragging_scroll = False
        self.scrollbar_track_rect = None
        self.scrollbar_thumb_rect = None
        self.scroll_start_mouse_y = 0
        self.scroll_start_offset = 0
        
        self.refresh()
        
    def resize(self, height):
        self.height = height

    def _determine_group(self, map_name):
        """Extracts prefix before _L\\d+ (e.g. Building_L1_01 -> Buildings)."""
        match = re.match(r"^(.+?)_L\d+.*$", map_name, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            if prefix.lower() == "building":
                return "Buildings"
            return f"{prefix}s" if not prefix.endswith("s") else prefix
        if "_" in map_name:
            prefix = map_name.split("_")[0]
            return f"{prefix}s" if not prefix.endswith("s") else prefix
        return "General"

    def refresh(self):
        self.folders = []
        self.map_data = {}
        self.grouped_maps = {}

        # Strictly prevent generating empty map/buildings folders
        if not os.path.exists(self.root_dir):
            return

        try: items = sorted(os.listdir(self.root_dir))
        except OSError: items = []
            
        root_files = [f for f in items if os.path.isfile(os.path.join(self.root_dir, f)) and self.file_pattern.match(f)]
        if root_files:
            folder = ""
            self.folders.append(folder)
            self.map_data[folder] = self._group_maps(root_files)
            self.expanded_folders[folder] = True

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
                except OSError: continue

        for folder in self.folders:
            self.grouped_maps[folder] = {}
            for map_name in self.map_data[folder].keys():
                grp = self._determine_group(map_name)
                if grp not in self.grouped_maps[folder]:
                    self.grouped_maps[folder][grp] = []
                    if (folder, grp) not in self.expanded_groups:
                        self.expanded_groups[(folder, grp)] = False
                self.grouped_maps[folder][grp].append(map_name)

            for grp in self.grouped_maps[folder]:
                self.grouped_maps[folder][grp].sort(key=parse_building_sort_key)

            for map_name in self.map_data[folder].keys():
                for layer_name in ['light', 'roof', 'map', 'spawn', 'ground']:
                    l_key = (folder, map_name, layer_name)
                    if l_key not in self.layer_properties:
                        self.layer_properties[l_key] = {"visible": True, "opacity": 255}

        if self.selected_map:
            sf, sm = self.selected_map
            if sf not in self.map_data or sm not in self.map_data[sf]:
                self.selected_map = None
        
        if not self.selected_map and self.folders:
            first_folder = self.folders[0]
            maps = sorted(self.map_data[first_folder].keys(), key=parse_building_sort_key)
            if maps:
                self.selected_map = (first_folder, maps[0])

    def _group_maps(self, file_list):
        grouped = {}
        for f in file_list:
            match = self.file_pattern.match(f)
            if match:
                base_name = match.group(1)
                if base_name not in grouped: grouped[base_name] = []
                grouped[base_name].append(f)
        return grouped

    def _get_visible_rows(self):
        query = self.search_input.text.strip().lower()
        rows = []
        for folder in self.folders:
            if folder != "":
                rows.append({"type": "folder", "folder": folder, "indent": 10})
            if folder == "" or self.expanded_folders.get(folder):
                groups = self.grouped_maps.get(folder, {})
                for grp_name, map_list in groups.items():
                    filtered_maps = [m for m in map_list if not query or query in m.lower() or query in grp_name.lower()]
                    if not filtered_maps and query:
                        continue
                    
                    rows.append({"type": "group", "folder": folder, "group": grp_name, "indent": 20 if folder else 10})
                    # Collapsed by default unless expanded by user or search query is active
                    if self.expanded_groups.get((folder, grp_name)) or query:
                        for map_name in filtered_maps:
                            rows.append({"type": "map", "folder": folder, "map_name": map_name, "indent": 35 if folder else 25})
                            if self.expanded_maps.get((folder, map_name)):
                                for layer_name in ['light', 'roof', 'map', 'spawn', 'ground']:
                                    rows.append({"type": "layer", "folder": folder, "map_name": map_name, "layer_name": layer_name, "indent": 50 if folder else 40})
        return rows

    def draw(self, surface, current_map_name, current_folder, active_layer_name, modified_maps=None):
        if modified_maps is None: modified_maps = set()
            
        pygame.draw.rect(surface, UITheme.PANEL_BG, (self.x, self.y, self.width, self.height))
        pygame.draw.line(surface, UITheme.BORDER, (self.x + self.width - 1, self.y), (self.x + self.width - 1, self.y + self.height))

        # 1. Active Header info
        surface.blit(self.font.render(f"Active: {current_map_name[:20]}", True, UITheme.TEXT), (self.x + 10, self.y + 12))
        surface.blit(self.font.render(f"Layer: {active_layer_name}", True, UITheme.TEXT_DIM), (self.x + 10, self.y + 36))

        # 2. Search Box
        self.search_input.draw(surface)
        if not self.search_input.text and not self.search_input.active:
            surface.blit(self.font.render("Search buildings...", True, UITheme.TEXT_DIM), (self.search_input.rect.x + 6, self.search_input.rect.y + 5))

        list_start_y = self.y + 105
        list_rect = pygame.Rect(self.x, list_start_y, self.width, self.height - 105)
        surface.set_clip(list_rect)

        rows = self._get_visible_rows()
        content_height = len(rows) * self.line_height + 10
        self.max_scroll = max(0, content_height - list_rect.height)
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

        mouse_pos = pygame.mouse.get_pos()
        display_y = list_start_y - self.scroll_offset

        for row in rows:
            if display_y + self.line_height > list_rect.y and display_y < list_rect.bottom:
                r_rect = pygame.Rect(self.x, display_y, self.width, self.line_height)
                
                if row["type"] == "folder":
                    icon = "[-]" if self.expanded_folders.get(row["folder"]) else "[+]"
                    surface.blit(self.font.render(f"{icon} {row['folder']}", True, UITheme.TEXT), (self.x + row["indent"], display_y + 4))
                
                elif row["type"] == "group":
                    grp_key = (row["folder"], row["group"])
                    icon = "[-]" if self.expanded_groups.get(grp_key) else "[+]"
                    surface.blit(self.font.render(f"{icon} {row['group']}", True, UITheme.WARNING), (self.x + row["indent"], display_y + 4))

                elif row["type"] == "map":
                    map_key = (row["folder"], row["map_name"])
                    is_active = (row["map_name"] == current_map_name and row["folder"] == current_folder)
                    if is_active:
                        pygame.draw.rect(surface, UITheme.LIST_HOVER, r_rect)
                    elif r_rect.collidepoint(mouse_pos):
                        pygame.draw.rect(surface, UITheme.HOVER_BG, r_rect)

                    is_mod = map_key in modified_maps
                    mod_tag = "*" if is_mod else ""
                    icon = "[-]" if self.expanded_maps.get(map_key) else "[+]"
                    surface.blit(self.font.render(f"{icon} {row['map_name']}{mod_tag}", True, UITheme.TEXT), (self.x + row["indent"], display_y + 4))

                elif row["type"] == "layer":
                    l_key = (row["folder"], row["map_name"], row["layer_name"])
                    prop = self.layer_properties.get(l_key, {"visible": True})
                    is_active_layer = (row["layer_name"] == active_layer_name and row["map_name"] == current_map_name and row["folder"] == current_folder)
                    if is_active_layer:
                        pygame.draw.rect(surface, UITheme.ACCENT, r_rect)
                    elif r_rect.collidepoint(mouse_pos):
                        pygame.draw.rect(surface, UITheme.HOVER_BG, r_rect)

                    surface.blit(self.font.render(row["layer_name"], True, UITheme.TEXT_DIM), (self.x + row["indent"] + 20, display_y + 4))
                    
                    eye_icon = self.icons.get("hide" if prop["visible"] else "view", self.default_icon)
                    vh_rect = pygame.Rect(self.x + self.width - ICON_SIZE - 10, display_y + 2, ICON_SIZE - 4, ICON_SIZE - 4)
                    surface.blit(pygame.transform.scale(eye_icon, (ICON_SIZE - 4, ICON_SIZE - 4)), vh_rect)

            display_y += self.line_height

        surface.set_clip(None)

        if self.max_scroll > 0:
            track_rect = pygame.Rect(self.x + self.width - 8, list_rect.y, 8, list_rect.height)
            self.scrollbar_track_rect = track_rect
            thumb_height = max(20, int((list_rect.height / content_height) * list_rect.height))
            thumb_y = list_rect.y + (self.scroll_offset / self.max_scroll) * (list_rect.height - thumb_height)
            self.scrollbar_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_height)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.scrollbar_thumb_rect, border_radius=4)
        else:
            self.scrollbar_track_rect = None
            self.scrollbar_thumb_rect = None

    def handle_event(self, event):
        if self.search_input.handle_event(event):
            self.scroll_offset = 0
            return True

        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_scroll = False

        if event.type == pygame.MOUSEMOTION and self.dragging_scroll and self.scrollbar_thumb_rect and self.max_scroll > 0:
            dy = event.pos[1] - self.scroll_start_mouse_y
            track_h = self.scrollbar_track_rect.height
            thumb_h = self.scrollbar_thumb_rect.height
            movable = track_h - thumb_h
            if movable > 0:
                self.scroll_offset = max(0, min(self.max_scroll, self.scroll_start_offset + (dy * self.max_scroll / movable)))
            return True

        list_start_y = self.y + 105
        list_rect = pygame.Rect(self.x, list_start_y, self.width, self.height - 105)

        if event.type == pygame.MOUSEBUTTONDOWN and list_rect.collidepoint(event.pos):
            if event.button == 4:
                self.scroll_offset = max(0, self.scroll_offset - self.line_height * 2)
                return True
            elif event.button == 5:
                self.scroll_offset = min(self.max_scroll, self.scroll_offset + self.line_height * 2)
                return True

            if event.button == 1:
                mx, my = event.pos
                if self.scrollbar_thumb_rect and self.scrollbar_thumb_rect.collidepoint(mx, my):
                    self.dragging_scroll = True
                    self.scroll_start_mouse_y = my
                    self.scroll_start_offset = self.scroll_offset
                    return True

                rows = self._get_visible_rows()
                display_y = list_start_y - self.scroll_offset

                for row in rows:
                    row_rect = pygame.Rect(self.x, display_y, self.width - 15, self.line_height)
                    if row_rect.collidepoint(mx, my):
                        # Exact [+] hitbox matching icon render location
                        icon_hitbox = pygame.Rect(self.x + row["indent"], display_y, 30, self.line_height)
                        clicked_expand = icon_hitbox.collidepoint(mx, my)

                        if row["type"] == "folder":
                            self.expanded_folders[row["folder"]] = not self.expanded_folders.get(row["folder"], False)
                            return True

                        elif row["type"] == "group":
                            grp_key = (row["folder"], row["group"])
                            self.expanded_groups[grp_key] = not self.expanded_groups.get(grp_key, False)
                            return True

                        elif row["type"] == "map":
                            map_key = (row["folder"], row["map_name"])
                            if clicked_expand:
                                self.expanded_maps[map_key] = not self.expanded_maps.get(map_key, False)
                                return True
                            else:
                                self.selected_map = map_key
                                return {"action": "select_map", "folder": row["folder"], "map_name": row["map_name"]}

                        elif row["type"] == "layer":
                            vh_rect = pygame.Rect(self.x + self.width - ICON_SIZE - 10, display_y, ICON_SIZE, ICON_SIZE)
                            l_key = (row["folder"], row["map_name"], row["layer_name"])
                            if vh_rect.collidepoint(mx, my):
                                self.layer_properties[l_key]["visible"] = not self.layer_properties[l_key]["visible"]
                                return {
                                    "action": "toggle_visibility", 
                                    "folder": row["folder"], 
                                    "map_name": row["map_name"], 
                                    "layer_name": row["layer_name"], 
                                    "visible": self.layer_properties[l_key]["visible"]
                                }
                            return {"action": "set_active_layer", "layer_name": row["layer_name"]}

                    display_y += self.line_height
        return None