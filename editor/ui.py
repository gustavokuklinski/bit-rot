import pygame
from editor.config import TILE_SIZE, SIDEBAR_WIDTH, SCREEN_HEIGHT, FILE_TREE_WIDTH, SCREEN_WIDTH, ICON_SIZE
from editor.assets import load_editor_icons

class NewMapModal:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.input_text = ""
        self.active = False

        self.input_rect = pygame.Rect(x + 20, y + 50, width - 40, 30)
        self.create_button_rect = pygame.Rect(x + 20, y + 100, 100, 30)
        self.cancel_button_rect = pygame.Rect(x + 140, y + 100, 100, 30)

    def handle_event(self, event):
        if not self.active:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.create_button_rect.collidepoint(event.pos):
                self.active = False
                return self.input_text
            elif self.cancel_button_rect.collidepoint(event.pos):
                self.active = False
                return None
        return None

    def draw(self, surface):
        if not self.active:
            return

        pygame.draw.rect(surface, (150, 150, 150), self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)

        title_surf = self.font.render("Create New Map", True, (0, 0, 0))
        surface.blit(title_surf, (self.rect.x + 20, self.rect.y + 20))

        pygame.draw.rect(surface, (255, 255, 255), self.input_rect)
        pygame.draw.rect(surface, (0, 0, 0), self.input_rect, 2)
        input_surf = self.font.render(self.input_text, True, (0, 0, 0))
        surface.blit(input_surf, (self.input_rect.x + 5, self.input_rect.y + 5))

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
        self.icons = load_editor_icons("game/sprites/editor")

        button_definitions = [
            {"label": "NEW MAP", "icon": "new", "action": "NEW MAP"},
            {"label": "SAVE MAP", "icon": "save", "action": "SAVE MAP"},
            {"label": "DELETE MAP", "icon": "delete", "action": "DELETE MAP"},
            {"label": "ERASER", "icon": "eraser", "action": "ERASER"},
            {"label": "PLAYER SPAWN", "icon": "player_spawn", "action": "PLAYER SPAWN"},
            {"label": "ZOMBIE SPAWN", "icon": "zombie_spawn", "action": "ZOMBIE SPAWN"},
            {"label": "ITEM SPAWN", "icon": "item", "action": "ITEM SPAWN"},
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
        self.tiles = tiles.copy() # Make a copy to not modify the original dict
        self.selected_tile = None

    def draw(self, surface):
        pygame.draw.rect(surface, (50, 50, 50), (self.x, self.y, SIDEBAR_WIDTH, SCREEN_HEIGHT))
        
        row, col = 0, 0
        for name, image in self.tiles.items():
            tile_x = self.x + col * (TILE_SIZE + 10) + 10
            tile_y = self.y + row * (TILE_SIZE + 10) + 10
            tile_rect = pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE)
            surface.blit(image, (tile_x, tile_y))
            
            # Draw border if this is the selected tile
            if self.selected_tile == name:
                pygame.draw.rect(surface, (255, 255, 0), tile_rect, 3) # Yellow border, 3 pixels thick

            col += 1
            if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH:
                col = 0
                row += 1

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_x, mouse_y = event.pos
                if self.x <= mouse_x <= self.x + SIDEBAR_WIDTH:
                    row, col = 0, 0
                    for name, image in self.tiles.items():
                        tile_x = self.x + col * (TILE_SIZE + 10) + 10
                        tile_y = self.y + row * (TILE_SIZE + 10) + 10
                        tile_rect = pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE)
                        if tile_rect.collidepoint(mouse_x, mouse_y):
                            self.selected_tile = name
                            break
                        
                        col += 1
                        if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH:
                            col = 0
                            row += 1
