import pygame
import re
import os
import csv
from editor.config import TILE_SIZE, SIDEBAR_WIDTH, SCREEN_HEIGHT, FILE_TREE_WIDTH, SCREEN_WIDTH, ICON_SIZE, BUILDINGS_DIR, BUILDING_PREVIEW_SIZE, TAB_BAR_HEIGHT
from editor.assets import load_editor_icons

class ModeTabs:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.modes = ["MAP", "BUILDING"]
        self.active_mode = "MAP"
        self.tabs = []
        
        tab_w = 150
        for i, mode in enumerate(self.modes):
            self.tabs.append({
                "mode": mode,
                "rect": pygame.Rect(x + i*tab_w, y, tab_w, height),
                "label": f"{mode} EDITOR"
            })

    def draw(self, surface):
        # Draw background bar
        pygame.draw.rect(surface, (40, 40, 40), self.rect)
        
        for tab in self.tabs:
            is_active = (tab["mode"] == self.active_mode)
            # visual style for active vs inactive
            color = (80, 80, 100) if is_active else (50, 50, 50)
            pygame.draw.rect(surface, color, tab["rect"])
            pygame.draw.rect(surface, (20, 20, 20), tab["rect"], 1)
            
            text_color = (255, 255, 255) if is_active else (150, 150, 150)
            lbl = self.font.render(tab["label"], True, text_color)
            surface.blit(lbl, (tab["rect"].centerx - lbl.get_width()//2, tab["rect"].centery - lbl.get_height()//2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab in self.tabs:
                if tab["rect"].collidepoint(event.pos):
                    if self.active_mode != tab["mode"]:
                        self.active_mode = tab["mode"]
                        return self.active_mode
        return None

# --- New Building Modal ---
class NewBuildingModal:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.active = False
        
        self.name_text = "Building"
        self.width_text = "10"
        self.height_text = "10"
        
        self.active_field = "name" # name, width, height
        
        # Rects for inputs
        self.name_rect = pygame.Rect(x + 70, y + 50, 200, 30)
        self.width_rect = pygame.Rect(x + 70, y + 100, 80, 30)
        self.height_rect = pygame.Rect(x + 70, y + 150, 80, 30)
        
        self.create_btn = pygame.Rect(x + 50, y + 200, 80, 30)
        self.cancel_btn = pygame.Rect(x + 170, y + 200, 80, 30)

    def handle_event(self, event):
        if not self.active: return None
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.name_rect.collidepoint(event.pos): self.active_field = "name"
            elif self.width_rect.collidepoint(event.pos): self.active_field = "width"
            elif self.height_rect.collidepoint(event.pos): self.active_field = "height"
            elif self.create_btn.collidepoint(event.pos):
                try:
                    w = int(self.width_text)
                    h = int(self.height_text)
                    self.active = False
                    return {"action": "create_building", "name": self.name_text, "width": w, "height": h}
                except ValueError:
                    print("Invalid dimensions")
            elif self.cancel_btn.collidepoint(event.pos):
                self.active = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                if self.active_field == "name": self.name_text = self.name_text[:-1]
                elif self.active_field == "width": self.width_text = self.width_text[:-1]
                elif self.active_field == "height": self.height_text = self.height_text[:-1]
            else:
                if self.active_field == "name": self.name_text += event.unicode
                elif self.active_field == "width" and event.unicode.isdigit(): self.width_text += event.unicode
                elif self.active_field == "height" and event.unicode.isdigit(): self.height_text += event.unicode
        return None

    def draw(self, surface):
        if not self.active: return
        
        # Draw background
        s = pygame.Surface((self.rect.width, self.rect.height))
        s.fill((60, 60, 60))
        surface.blit(s, self.rect.topleft)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2)
        
        # Title
        surface.blit(self.font.render("New Building", True, (255, 255, 255)), (self.rect.x + 20, self.rect.y + 10))
        
        # Labels and Inputs
        surface.blit(self.font.render("Name:", True, (200, 200, 200)), (self.rect.x + 10, self.name_rect.y + 5))
        pygame.draw.rect(surface, (255, 255, 255) if self.active_field == "name" else (200, 200, 200), self.name_rect, 2)
        surface.blit(self.font.render(self.name_text, True, (255, 255, 255)), (self.name_rect.x + 5, self.name_rect.y + 5))

        surface.blit(self.font.render("W:", True, (200, 200, 200)), (self.rect.x + 10, self.width_rect.y + 5))
        pygame.draw.rect(surface, (255, 255, 255) if self.active_field == "width" else (200, 200, 200), self.width_rect, 2)
        surface.blit(self.font.render(self.width_text, True, (255, 255, 255)), (self.width_rect.x + 5, self.width_rect.y + 5))

        surface.blit(self.font.render("H:", True, (200, 200, 200)), (self.rect.x + 10, self.height_rect.y + 5))
        pygame.draw.rect(surface, (255, 255, 255) if self.active_field == "height" else (200, 200, 200), self.height_rect, 2)
        surface.blit(self.font.render(self.height_text, True, (255, 255, 255)), (self.height_rect.x + 5, self.height_rect.y + 5))

        # Buttons
        pygame.draw.rect(surface, (0, 150, 0), self.create_btn)
        create_txt = self.font.render("Create", True, (255, 255, 255))
        surface.blit(create_txt, (self.create_btn.centerx - create_txt.get_width()//2, self.create_btn.centery - create_txt.get_height()//2))

        pygame.draw.rect(surface, (150, 0, 0), self.cancel_btn)
        cancel_txt = self.font.render("Cancel", True, (255, 255, 255))
        surface.blit(cancel_txt, (self.cancel_btn.centerx - cancel_txt.get_width()//2, self.cancel_btn.centery - cancel_txt.get_height()//2))


class NewMapModal:
    def __init__(self, x, y, width, height, font, current_map_name):
        self.font = font
        self.active = False
        self.current_map_name = current_map_name
        
        self.connection = None # 'TOP', 'RIGHT', 'BOTTOM', 'LEFT'
        self.layer = 1         # Default to layer 1

        # Parse current map connections
        self.current_connections = {'TOP': 0, 'RIGHT': 0, 'BOTTOM': 0, 'LEFT': 0}
        self.current_layer = 1
        self.current_pos_id = 0
        
        match = re.match(r"map_L(\d+)_P(\d+)_(\d+)_(\d+)_(\d+)_(\d+)", current_map_name)
        if match:
            self.current_layer = int(match.group(1))
            self.current_pos_id = int(match.group(2))
            self.current_connections['TOP'] = int(match.group(3))
            self.current_connections['RIGHT'] = int(match.group(4))
            self.current_connections['BOTTOM'] = int(match.group(5))
            self.current_connections['LEFT'] = int(match.group(6))

        # --- LAYOUT CALCULATIONS ---
        # Define positions relative to 'y' to ensure they fit
        self.conn_title_y = y + 65
        conn_btn_y = self.conn_title_y + 25
        
        # Connection buttons occupy roughly 70px height (30px btn + 10px gap + 30px btn)
        conn_section_bottom = conn_btn_y + 70
        
        self.layer_title_y = conn_section_bottom + 15
        layer_btn_y = self.layer_title_y + 25
        
        # Layer buttons occupy 30px
        layer_section_bottom = layer_btn_y + 30
        
        # Calculate minimum required height to fit everything with padding
        # 20px gap before create buttons, 30px buttons, 20px bottom padding
        min_required_height = (layer_section_bottom + 20 + 30 + 20) - y
        
        if height < min_required_height:
            height = min_required_height

        self.rect = pygame.Rect(x, y, width, height)

        # Define button rects using calculated Y positions
        self.conn_buttons = {
            'TOP': pygame.Rect(x + 20, conn_btn_y, 100, 30),
            'RIGHT': pygame.Rect(x + 140, conn_btn_y, 100, 30),
            'BOTTOM': pygame.Rect(x + 20, conn_btn_y + 40, 100, 30),
            'LEFT': pygame.Rect(x + 140, conn_btn_y + 40, 100, 30),
        }
        
        self.layer_buttons = {
            1: pygame.Rect(x + 20, layer_btn_y, 100, 30),
            2: pygame.Rect(x + 140, layer_btn_y, 100, 30),
        }

        # Place Create/Cancel buttons at the bottom of the (potentially resized) rect
        btn_y = y + height - 50
        self.create_button_rect = pygame.Rect(x + 20, btn_y, 100, 30)
        self.cancel_button_rect = pygame.Rect(x + 140, btn_y, 100, 30)


    def preselect_direction(self, direction):
        """Called if user clicks a '0' connection on the map hud"""
        if direction in self.conn_buttons and self.current_connections[direction] == 0:
            self.connection = direction
        else:
            self.connection = None # Reset if invalid
            
    def handle_event(self, event):
        if not self.active:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check connection buttons
            for direction, rect in self.conn_buttons.items():
                if rect.collidepoint(event.pos):
                    # Only allow selection if connection is 0 (not set)
                    if self.current_connections[direction] == 0:
                        self.connection = direction
                    return None # Handled click

            # Check layer buttons
            for layer_num, rect in self.layer_buttons.items():
                if rect.collidepoint(event.pos):
                    self.layer = layer_num
                    return None # Handled click

            if self.create_button_rect.collidepoint(event.pos):
                if self.connection and self.layer:
                    self.active = False
                    # Return the creation parameters
                    return {
                        "action": "create_map",
                        "direction": self.connection,
                        "layer": self.layer,
                        "source_map": self.current_map_name,
                        "source_connections": self.current_connections,
                        "source_pos_id": self.current_pos_id,
                        "source_layer": self.current_layer
                    }
            elif self.cancel_button_rect.collidepoint(event.pos):
                self.active = False
                return {"action": "cancel"}
        return None

    def draw(self, surface):
        if not self.active:
            return

        # Draw modal background (semi-transparent dark)
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill((50, 50, 50, 230))
        surface.blit(s, self.rect.topleft)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2)

        # Title
        title_surf = self.font.render("Create New Map", True, (255, 255, 255))
        surface.blit(title_surf, (self.rect.x + 20, self.rect.y + 20))

        # Help text
        help_surf = self.font.render(f"Source: {self.current_map_name}", True, (200, 200, 200))
        surface.blit(help_surf, (self.rect.x + 20, self.rect.y + 45))

        # Connection buttons
        conn_title = self.font.render("Select connection:", True, (255, 255, 255))
        surface.blit(conn_title, (self.rect.x + 20, self.conn_title_y))
        
        for direction, rect in self.conn_buttons.items():
            color = (80, 80, 80) # Disabled
            text_color = (100, 100, 100)
            
            if self.current_connections[direction] == 0:
                text_color = (255, 255, 255) # Enabled
                if self.connection == direction:
                    color = (0, 150, 0) # Selected
                else:
                    color = (50, 50, 50) # Enabled, not selected
            
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (255, 255, 255), rect, 1)
            text_surf = self.font.render(direction, True, text_color)
            surface.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))

        # Layer buttons
        layer_title = self.font.render("Select Layer:", True, (255, 255, 255))
        surface.blit(layer_title, (self.rect.x + 20, self.layer_title_y))
        
        for layer_num, rect in self.layer_buttons.items():
            color = (50, 50, 50)
            text_color = (255, 255, 255)
            
            if self.layer == layer_num:
                color = (0, 150, 0) # Selected
                
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (255, 255, 255), rect, 1)
            text_surf = self.font.render(f"[{layer_num}]", True, text_color)
            surface.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))

        # Create/Cancel buttons
        pygame.draw.rect(surface, (0, 200, 0), self.create_button_rect)
        create_text = self.font.render("Create", True, (255, 255, 255))
        surface.blit(create_text, (self.create_button_rect.centerx - create_text.get_width() // 2, self.create_button_rect.centery - create_text.get_height() // 2))

        pygame.draw.rect(surface, (200, 0, 0), self.cancel_button_rect)
        cancel_text = self.font.render("Cancel", True, (255, 255, 255))
        surface.blit(cancel_text, (self.cancel_button_rect.centerx - cancel_text.get_width() // 2, self.cancel_button_rect.centery - cancel_text.get_height() // 2))

        
class Toolbar:
    def __init__(self, x, y, width, height, font):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font = font
        self.buttons = []
        self.icons = load_editor_icons("./game/lib/sprites/editor")

        button_definitions = [
            # Added FILL button
            {"label": "NEW MAP", "icon": "new", "action": "NEW MAP"},
            {"label": "NEW BUILDING", "icon": "building", "action": "NEW BUILDING"},
            {"label": "SAVE", "icon": "save", "action": "SAVE MAP"},
            {"label": "EXPORT", "icon": "export", "action": "EXPORT PNG"},
            {"label": "DELETE", "icon": "delete", "action": "DELETE MAP"},
            {"label": "ERASER", "icon": "eraser", "action": "ERASER"},
            {"label": "SELECT", "icon": "selection", "action": "SELECTION"},
            {"label": "FILL", "icon": "fill", "action": "FILL"},
            {"label": "UNDO", "icon": "undo", "action": "UNDO"},
            {"label": "COPY", "icon": "copy", "action": "COPY"},
            {"label": "PASTE", "icon": "paste", "action": "PASTE"},
            {"label": "CLEAR", "icon": "clear", "action": "CLEAR"},
            {"label": "P_SPAWN", "icon": "player_spawn", "action": "PLAYER SPAWN"},
            {"label": "Z_SPAWN", "icon": "zombie_spawn", "action": "ZOMBIE SPAWN"},
            {"label": "ITEM", "icon": "item", "action": "ITEM SPAWN"},
            {"label": "L1", "icon": "stair", "action": "STAIR L1"},
            {"label": "L2", "icon": "stair", "action": "STAIR L2"},
            
        ]

        button_width = ICON_SIZE + 10
        button_height = ICON_SIZE + 10
        padding = 5
        current_x = x + padding

        for btn_def in button_definitions:
            rect = pygame.Rect(current_x, y + (height - button_height) // 2, button_width, button_height)
            self.buttons.append({
                "rect": rect,
                "label": btn_def["label"],
                "icon": self.icons.get(btn_def["icon"], self.icons['new']),
                "action": btn_def["action"]
            })
            current_x += button_width + padding

    def draw(self, surface):
        pygame.draw.rect(surface, (80, 80, 80), (self.x, self.y, self.width, self.height))
        mouse_pos = pygame.mouse.get_pos()
        hovered_button = None

        for button in self.buttons:
            pygame.draw.rect(surface, (120, 120, 120), button["rect"])
            surface.blit(button["icon"], (button["rect"].x + 5, button["rect"].y + 5))
            if button["rect"].collidepoint(mouse_pos):
                hovered_button = button

        if hovered_button:
            pygame.draw.rect(surface, (150, 150, 150), hovered_button["rect"], 2)
            
            # Draw tooltip
            text_surf = self.font.render(hovered_button["label"], True, (255, 255, 255))
            tooltip_rect = text_surf.get_rect(center=(mouse_pos[0], mouse_pos[1] + 20))
            pygame.draw.rect(surface, (0, 0, 0), tooltip_rect.inflate(10, 5))
            surface.blit(text_surf, tooltip_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button["rect"].collidepoint(event.pos):
                    return button["action"]
        return None

class Sidebar:
    def __init__(self, x, y, tiles, font):
        self.x = x
        self.y = y
        self.font = font
        self.all_tiles = tiles.copy() # Store all tiles
        self.tiles = tiles.copy() # Tiles to be displayed (filtered)
        self.selected_tile = None
        
        # Tabs
        self.tabs = ["Tiles", "Builds"]
        self.active_tab = "Tiles"
        self.tab_height = 30
        self.tab_rects = {
            "Tiles": pygame.Rect(x, y, SIDEBAR_WIDTH // 2, self.tab_height),
            "Builds": pygame.Rect(x + SIDEBAR_WIDTH // 2, y, SIDEBAR_WIDTH // 2, self.tab_height)
        }

        # Search / Filter
        self.search_rect = pygame.Rect(self.x + 10, self.y + self.tab_height + 10, SIDEBAR_WIDTH - 20, 30)
        self.search_text = ""
        self.search_active = False
        
        # Y-coordinate where content starts drawing
        self.content_area_y = self.y + self.tab_height + self.search_rect.height + 20 

        # Scrolling
        self.scroll_offset = 0
        self.max_scroll = 0
        self.scroll_speed = 30
        
        # Building Previews
        self.building_previews = {} # {name: surface}
        self.building_dimensions = {} # {name: (cols, rows)}
        self.selected_building = None

    def refresh_buildings(self, building_dir, tile_map):
        """Loads/Reloads building previews and dimensions."""
        self.building_previews = {}
        self.building_dimensions = {}
        if not os.path.exists(building_dir):
            os.makedirs(building_dir)
            
        # Group files
        building_groups = {}
        for f in os.listdir(building_dir):
            if f.endswith(".csv"):
                # Pattern: Name_Layer.csv
                parts = f.rsplit('_', 1)
                if len(parts) == 2:
                    name = parts[0]
                    if name not in building_groups: building_groups[name] = []
                    building_groups[name].append(f)

        # Generate previews
        for name, files in building_groups.items():
            # Create a small surface
            preview = pygame.Surface(BUILDING_PREVIEW_SIZE, pygame.SRCALPHA)
            preview.fill((30, 30, 30))
            
            try:
                # Load one representative layer
                target_file = None
                layer_priority = ['ground', 'map', 'roof']
                for prio in layer_priority:
                    fname = f"{name}_{prio}.csv"
                    if fname in files:
                        target_file = fname
                        break
                
                rows, cols = 0, 0
                if target_file:
                    path = os.path.join(building_dir, target_file)
                    with open(path, 'r') as f:
                        reader = list(csv.reader(f))
                        rows = len(reader)
                        cols = len(reader[0]) if rows > 0 else 0
                        
                        scale = min(BUILDING_PREVIEW_SIZE[0] / (cols * TILE_SIZE), BUILDING_PREVIEW_SIZE[1] / (rows * TILE_SIZE))
                        scale = min(scale, 1.0) # Don't zoom in too much
                        
                        scaled_size = int(TILE_SIZE * scale)
                        
                        for r, row in enumerate(reader):
                            for c, tile in enumerate(row):
                                if tile and tile in tile_map:
                                    img = pygame.transform.scale(tile_map[tile], (scaled_size, scaled_size))
                                    preview.blit(img, (c * scaled_size, r * scaled_size))
                
                # Store dimensions
                self.building_dimensions[name] = (cols, rows)
                
            except Exception as e:
                print(f"Failed preview for {name}: {e}")
                self.building_dimensions[name] = (1, 1) # Default
            
            self.building_previews[name] = preview

    def _filter_tiles(self):
        """Filters the displayed tiles based on the search text."""
        if not self.search_text:
            self.tiles = self.all_tiles.copy()
        else:
            self.tiles = {}
            for name, image in self.all_tiles.items():
                if self.search_text.lower() in name.lower():
                    self.tiles[name] = image
        self.scroll_offset = 0 # Reset scroll on search

    def draw(self, surface):
        # Background
        pygame.draw.rect(surface, (50, 50, 50), (self.x, self.y, SIDEBAR_WIDTH, SCREEN_HEIGHT))
        
        # Tabs
        for tab in self.tabs:
            rect = self.tab_rects[tab]
            color = (80, 80, 80) if self.active_tab == tab else (40, 40, 40)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (0, 0, 0), rect, 1)
            text = self.font.render(tab, True, (255, 255, 255))
            surface.blit(text, (rect.centerx - text.get_width()//2, rect.centery - text.get_height()//2))

        # Search Bar
        border_color = (255, 255, 0) if self.search_active else (0, 0, 0)
        pygame.draw.rect(surface, (255, 255, 255), self.search_rect)
        pygame.draw.rect(surface, border_color, self.search_rect, 2)
        
        if self.search_text:
            search_surf = self.font.render(self.search_text, True, (0, 0, 0))
        else:
            search_surf = self.font.render("Search...", True, (150, 150, 150))
        
        text_rect = search_surf.get_rect(centery=self.search_rect.centery)
        text_rect.x = self.search_rect.x + 5
        surface.set_clip(self.search_rect.inflate(-10, -10))
        surface.blit(search_surf, text_rect)
        surface.set_clip(None)
        
        # Content Area
        view_rect = pygame.Rect(self.x, self.content_area_y, SIDEBAR_WIDTH, SCREEN_HEIGHT - self.content_area_y)
        surface.set_clip(view_rect)

        content_height = 0
        
        if self.active_tab == "Tiles":
            row, col = 0, 0
            for name, image in sorted(self.tiles.items()):
                tile_x = self.x + col * (TILE_SIZE + 10) + 10
                tile_y = self.content_area_y + row * (TILE_SIZE + 10) - self.scroll_offset
                
                if tile_y + TILE_SIZE > self.content_area_y and tile_y < self.y + SCREEN_HEIGHT:
                    surface.blit(image, (tile_x, tile_y))
                    if self.selected_tile == name:
                        pygame.draw.rect(surface, (255, 255, 0), (tile_x, tile_y, TILE_SIZE, TILE_SIZE), 3)

                col += 1
                if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH:
                    col = 0
                    row += 1
            content_height = (row + 1) * (TILE_SIZE + 10)

        elif self.active_tab == "Builds":
            y_off = self.content_area_y - self.scroll_offset
            for name, preview in self.building_previews.items():
                if self.search_text.lower() in name.lower():
                    # Draw Name
                    name_surf = self.font.render(name, True, (255, 255, 255))
                    surface.blit(name_surf, (self.x + 10, y_off))
                    
                    # Draw Preview
                    p_rect = pygame.Rect(self.x + 10, y_off + 20, BUILDING_PREVIEW_SIZE[0], BUILDING_PREVIEW_SIZE[1])
                    surface.blit(preview, p_rect.topleft)
                    pygame.draw.rect(surface, (100, 100, 100), p_rect, 1)
                    
                    if self.selected_building == name:
                         pygame.draw.rect(surface, (255, 255, 0), p_rect, 3)

                    y_off += BUILDING_PREVIEW_SIZE[1] + 30
            content_height = y_off - (self.content_area_y - self.scroll_offset)

        surface.set_clip(None)

        # Scrollbar
        self.max_scroll = max(0, content_height - view_rect.height)
        if self.max_scroll > 0:
            track = pygame.Rect(self.x + SIDEBAR_WIDTH - 10, self.content_area_y, 10, view_rect.height)
            pygame.draw.rect(surface, (40, 40, 40), track)
            
            thumb_h = max(20, (view_rect.height / (content_height + view_rect.height)) * view_rect.height) # Simplified
            ratio = self.scroll_offset / self.max_scroll
            thumb_y = self.content_area_y + ratio * (view_rect.height - thumb_h)
            pygame.draw.rect(surface, (100, 100, 100), (track.x, thumb_y, 10, thumb_h))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if self.x <= mx <= self.x + SIDEBAR_WIDTH:
                # Check Tabs
                if my < self.y + self.tab_height:
                    if mx < self.x + SIDEBAR_WIDTH // 2: self.active_tab = "Tiles"
                    else: self.active_tab = "Builds"
                    self.scroll_offset = 0
                    return True
                
                # Check Search
                if self.search_rect.collidepoint(mx, my):
                    self.search_active = True
                    return True
                else:
                    self.search_active = False

                # Content Scroll
                if event.button == 4:
                    self.scroll_offset = max(0, self.scroll_offset - self.scroll_speed)
                    return True
                if event.button == 5:
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + self.scroll_speed)
                    return True

                # Click Selection
                if my > self.content_area_y:
                    if self.active_tab == "Tiles":
                        row, col = 0, 0
                        for name, image in sorted(self.tiles.items()):
                            tile_x = self.x + col * (TILE_SIZE + 10) + 10
                            tile_y = self.content_area_y + row * (TILE_SIZE + 10) - self.scroll_offset
                            if pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE).collidepoint(mx, my):
                                self.selected_tile = name
                                self.selected_building = None
                                return True
                            col += 1
                            if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH:
                                col = 0
                                row += 1
                    elif self.active_tab == "Builds":
                        y_off = self.content_area_y - self.scroll_offset
                        for name in self.building_previews.keys():
                            if self.search_text.lower() in name.lower():
                                rect = pygame.Rect(self.x + 10, y_off + 20, BUILDING_PREVIEW_SIZE[0], BUILDING_PREVIEW_SIZE[1])
                                if rect.collidepoint(mx, my):
                                    self.selected_building = name
                                    self.selected_tile = None
                                    return True
                                y_off += BUILDING_PREVIEW_SIZE[1] + 30
                return True
        
        if event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_BACKSPACE: self.search_text = self.search_text[:-1]
            else: self.search_text += event.unicode
            self._filter_tiles()
            return True
        return False