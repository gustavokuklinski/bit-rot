import pygame

pygame.init()

# --- Scalable Screen Setup ---
VIRTUAL_SCREEN_WIDTH = 1200
VIRTUAL_GAME_HEIGHT = 700

# UI/Layout Constants
# STATUS_PANEL_WIDTH = 220 # Removed as per user request
INVENTORY_PANEL_WIDTH = 220
GAME_OFFSET_X = 0 # X position where the central game box starts (no left panel)
GAME_WIDTH = VIRTUAL_SCREEN_WIDTH - INVENTORY_PANEL_WIDTH
GAME_HEIGHT = VIRTUAL_GAME_HEIGHT

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
GREEN = (50, 200, 50)
BLUE = (50, 50, 200)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
DARK_GRAY = (30, 30, 30)
PANEL_COLOR = (20, 20, 20)
GAME_BG_COLOR = (25.9, 17.8, 22.4) # Distinct color for the game box

# Fonts
font = pygame.font.Font(None, 24)
large_font = pygame.font.Font(None, 48)
title_font = pygame.font.Font(None, 72)

# Game Constants
TILE_SIZE = 16
PLAYER_SPEED = 4
ZOMBIE_SPEED = 0
ZOMBIE_DROP = 1
DECAY_RATE_SECONDS = 5.0 # How often Water/Food decay
FOOD_DECAY_AMOUNT = 0.5 # Percentage loss per tick
WATER_DECAY_AMOUNT = FOOD_DECAY_AMOUNT * 1.5 # Water depletes 1.5x faster

# --- Custom Map Layout ---
# Define the map using characters. '#' will be an obstacle.
MAP_LAYOUT = [

]
