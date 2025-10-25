import pygame

pygame.init()

# --- Scalable Screen Setup ---
VIRTUAL_SCREEN_WIDTH = 1312
VIRTUAL_GAME_HEIGHT = 720

GAME_OFFSET_X = 0 # X position where the central game box starts (no left panel)
GAME_WIDTH = VIRTUAL_SCREEN_WIDTH
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
GAME_BG_COLOR = (0, 0, 0)

# Modal Dimensions
INVENTORY_MODAL_WIDTH = 300
INVENTORY_MODAL_HEIGHT = 300
STATUS_MODAL_WIDTH = 200
STATUS_MODAL_HEIGHT = 300

# Fonts
font = pygame.font.Font(None, 16)
large_font = pygame.font.Font(None, 24)
title_font = pygame.font.Font(None, 24)


# Game Constants
TILE_SIZE = 16

# Player setup
PLAYER_SPEED = 2
DECAY_RATE_SECONDS = 5.0 # How often Water/Food decay
FOOD_DECAY_AMOUNT = 0.5 # Percentage loss per tick
WATER_DECAY_AMOUNT = FOOD_DECAY_AMOUNT * 1.5 # Water depletes 1.5x faster
START_ZOOM = 1.5
FAR_ZOOM = 1.0
NEAR_ZOOM = 5.0
PLAYER_VIEW_RADIUS = 20 * TILE_SIZE

# --- ZOMBIE AI SETTINGS ---
ZOMBIE_SPEED = 1 # Zombie speed
ZOMBIE_DROP = 1 # Drop percentage
ZOMBIE_DETECTION_RADIUS = 20 * TILE_SIZE # How far (in pixels) zombies can 'see' the player
ZOMBIE_WANDER_ENABLED = True          # Should zombies wander when idle?
ZOMBIE_WANDER_CHANGE_INTERVAL = 2000  # How often (ms) wandering zombies pick a new target
ZOMBIE_LINE_OF_SIGHT_CHECK = True    # Should obstacles block zombie sight?
ZOMBIES_PER_SPAWN = 3
# --- ZOMBIE AI SETTINGS ---