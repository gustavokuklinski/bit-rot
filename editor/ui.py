import pygame
import re
from editor.config import TILE_SIZE, SIDEBAR_WIDTH, SCREEN_HEIGHT, FILE_TREE_WIDTH, SCREEN_WIDTH, ICON_SIZE
from editor.assets import load_editor_icons

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
        self.icons = load_editor_icons("./game/resources/sprites/editor")

        button_definitions = [
            {"label": "NEW MAP", "icon": "new", "action": "NEW MAP"},
            {"label": "SAVE MAP", "icon": "save", "action": "SAVE MAP"},
            {"label": "EXPORT PNG", "icon": "new", "action": "EXPORT PNG"},
            {"label": "DELETE MAP", "icon": "delete", "action": "DELETE MAP"},
            {"label": "ERASER", "icon": "eraser", "action": "ERASER"},
            {"label": "UNDO", "icon": "undo", "action": "UNDO"},
            {"label": "COPY", "icon": "copy", "action": "COPY"},
            {"label": "PASTE", "icon": "paste", "action": "PASTE"},
            {"label": "CLEAR", "icon": "clear", "action": "CLEAR"},
            {"label": "PLAYER SPAWN", "icon": "player_spawn", "action": "PLAYER SPAWN"},
            {"label": "ZOMBIE SPAWN", "icon": "zombie_spawn", "action": "ZOMBIE SPAWN"},
            {"label": "ITEM SPAWN", "icon": "item", "action": "ITEM SPAWN"},
            {"label": "STAIR L1", "icon": "stair", "action": "STAIR L1"},
            {"label": "STAIR L2", "icon": "stair", "action": "STAIR L2"},
            {"label": "SELECTION", "icon": "selection", "action": "SELECTION"}
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
                "icon": self.icons[btn_def["icon"]],
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

        self.search_rect = pygame.Rect(self.x + 10, self.y + 10, SIDEBAR_WIDTH - 20, 30)
        self.search_text = ""
        self.search_active = False
        
        # Y-coordinate where tiles start drawing, below the search bar
        self.tile_area_y = self.y + self.search_rect.height + 20 

        # Scrolling
        self.scroll_offset = 0
        self.max_scroll = 0
        self.scroll_speed = 30

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
        # Draw sidebar background
        pygame.draw.rect(surface, (50, 50, 50), (self.x, self.y, SIDEBAR_WIDTH, SCREEN_HEIGHT))
        
        # --- Draw Search Bar ---
        # Draw border (yellow if active, black otherwise)
        border_color = (255, 255, 0) if self.search_active else (0, 0, 0)
        pygame.draw.rect(surface, (255, 255, 255), self.search_rect)
        pygame.draw.rect(surface, border_color, self.search_rect, 2)
        
        # Draw search text or placeholder
        if self.search_text:
            search_surf = self.font.render(self.search_text, True, (0, 0, 0))
        else:
            search_surf = self.font.render("Search tiles...", True, (150, 150, 150)) # Placeholder text
        
        # Blit text, clipping it if it's too long
        text_rect = search_surf.get_rect(centery=self.search_rect.centery)
        text_rect.x = self.search_rect.x + 5
        # Create a clipping area so text doesn't overflow the search box
        clip_rect = self.search_rect.inflate(-10, -10) # Small margin
        surface.set_clip(clip_rect)
        surface.blit(search_surf, text_rect)
        surface.set_clip(None) # Reset clipping area
        
        # --- Draw Tiles ---
        
        # Set clipping for the tile area so they don't draw over the search bar or off screen
        tile_view_rect = pygame.Rect(self.x, self.tile_area_y, SIDEBAR_WIDTH, SCREEN_HEIGHT - self.tile_area_y)
        surface.set_clip(tile_view_rect)

        row, col = 0, 0
        
        # --- Sort tiles alphabetically by name ---
        for name, image in sorted(self.tiles.items()):
            tile_x = self.x + col * (TILE_SIZE + 10) + 10
            tile_y = self.tile_area_y + row * (TILE_SIZE + 10) - self.scroll_offset # Apply scroll
            
            # Only draw if visible
            if tile_y + TILE_SIZE > self.tile_area_y and tile_y < self.y + SCREEN_HEIGHT:
                tile_rect = pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE)
                surface.blit(image, (tile_x, tile_y))
                
                # Draw border if this is the selected tile
                if self.selected_tile == name:
                    pygame.draw.rect(surface, (255, 255, 0), tile_rect, 3) # Yellow border, 3 pixels thick

            col += 1
            if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH:
                col = 0
                row += 1
        
        surface.set_clip(None)

        # Calculate total content height and update max_scroll
        total_rows = row + (1 if col > 0 else 0)
        content_height = total_rows * (TILE_SIZE + 10)
        view_height = SCREEN_HEIGHT - self.tile_area_y
        self.max_scroll = max(0, content_height - view_height)

        # --- Draw Scrollbar ---
        if self.max_scroll > 0:
            scrollbar_width = 10
            scrollbar_x = self.x + SIDEBAR_WIDTH - scrollbar_width
            
            # Draw Track
            track_rect = pygame.Rect(scrollbar_x, self.tile_area_y, scrollbar_width, view_height)
            pygame.draw.rect(surface, (40, 40, 40), track_rect)
            
            # Draw Thumb
            # Calculate thumb height based on viewport ratio
            full_content_height = self.max_scroll + view_height
            thumb_height = max(20, (view_height / full_content_height) * view_height)
            
            # Calculate thumb position
            scroll_ratio = self.scroll_offset / self.max_scroll
            thumb_y = self.tile_area_y + scroll_ratio * (view_height - thumb_height)
            
            thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_width, thumb_height)
            pygame.draw.rect(surface, (100, 100, 100), thumb_rect)


    def handle_event(self, event):
        """
        Returns True if the event was consumed by the sidebar, False otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos
            
            # Check if mouse is in sidebar
            if self.x <= mouse_x <= self.x + SIDEBAR_WIDTH:
                # Handle Scroll
                if event.button in (4, 5):
                    if event.button == 4: # Scroll up
                        self.scroll_offset = max(0, self.scroll_offset - self.scroll_speed)
                    elif event.button == 5: # Scroll down
                        self.scroll_offset = min(self.max_scroll, self.scroll_offset + self.scroll_speed)
                    return True # Event consumed

                if event.button == 1:
                    # Check search box click
                    if self.search_rect.collidepoint(mouse_x, mouse_y):
                        self.search_active = True
                    else:
                        self.search_active = False
                    
                    # Check tile selection click (must be in the tile area)
                    if self.x <= mouse_x <= self.x + SIDEBAR_WIDTH and mouse_y >= self.tile_area_y:
                        row, col = 0, 0
                        
                        # --- Sort tiles alphabetically for click detection ---
                        for name, image in sorted(self.tiles.items()):
                            tile_x = self.x + col * (TILE_SIZE + 10) + 10
                            tile_y = self.tile_area_y + row * (TILE_SIZE + 10) - self.scroll_offset # Apply scroll
                            
                            tile_rect = pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE)
                            if tile_rect.collidepoint(mouse_x, mouse_y):
                                self.selected_tile = name
                                break # Found the tile
                            
                            col += 1
                            if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH:
                                col = 0
                                row += 1
                                
                            # Stop checking if we've passed the click point (rough optimization)
                            if tile_y > mouse_y: 
                                break
                    
                    return True # Event consumed (clicked in sidebar)
        
        if event.type == pygame.KEYDOWN and self.search_active:
            # Handle typing in the search box
            if event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
            else:
                self.search_text += event.unicode
            self._filter_tiles() # Update the filtered list
            return True # Event consumed

        return False