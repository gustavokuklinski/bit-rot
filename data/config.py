import pygame
import xml.etree.ElementTree as ET

pygame.init()

# --- Scalable Screen Setup ---
VIRTUAL_SCREEN_WIDTH = 1312
VIRTUAL_GAME_HEIGHT = 720

GAME_OFFSET_X = 0 # X position where the central game box starts (no left panel)
GAME_WIDTH = VIRTUAL_SCREEN_WIDTH
GAME_HEIGHT = VIRTUAL_GAME_HEIGHT

DATA_PATH = "game/data/" # Folders with XML data files
SPRITE_PATH = "game/sprites/" # Folders with PNG sprites

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
GRAY_60 = (60, 60, 60)
GRAY_40 = (40, 40, 40)
GRAY_80 = (80, 80, 80)

# Modal Dimensions
INVENTORY_MODAL_WIDTH = 300
INVENTORY_MODAL_HEIGHT = 300
STATUS_MODAL_WIDTH = 250
STATUS_MODAL_HEIGHT = 360
NEARBY_MODAL_WIDTH = 300
NEARBY_MODAL_HEIGHT = 300

FONT_FACE = "game/font/Oxanium-Regular.ttf"
FONT_TITLE = "game/font/VT323-Regular.ttf"

# Fonts
font = pygame.font.Font(FONT_FACE, 16)
font_small = pygame.font.Font(FONT_FACE, 16)
large_font = pygame.font.Font(FONT_FACE, 16)
title_font = pygame.font.Font(FONT_TITLE, 16)


# Game Constants
TILE_SIZE = 16

# --- XML Parsing ---
tree = ET.parse('config.xml')
root = tree.getroot()

# Player settings
player_config = root.find('player')
PLAYER_SPEED = float(player_config.find('speed').get('value'))
DECAY_RATE_SECONDS = float(player_config.find('food_water_decay_seconds').get('value'))
FOOD_WATER_MULTIPLIER_DECAY = float(player_config.find('food_water_multiplier_decay').get('value'))
FOOD_DECAY_AMOUNT = float(player_config.find('food_decay').get('value')) * FOOD_WATER_MULTIPLIER_DECAY
WATER_DECAY_AMOUNT = float(player_config.find('water_decay').get('value')) * FOOD_WATER_MULTIPLIER_DECAY * 1.5
START_ZOOM = float(player_config.find('zoom_start').get('value'))
FAR_ZOOM = float(player_config.find('zoom_far').get('value'))
NEAR_ZOOM = float(player_config.find('zoom_near').get('value'))

# Zombie settings
zombie_config = root.find('zombie')
ZOMBIE_SPEED = float(zombie_config.find('speed').get('value'))
ZOMBIE_DROP = int(zombie_config.find('drop').get('value'))
ZOMBIE_DETECTION_RADIUS = int(zombie_config.find('detection').get('value')) * TILE_SIZE
ZOMBIE_WANDER_ENABLED = zombie_config.find('wander').get('value') == 'true'
ZOMBIE_WANDER_CHANGE_INTERVAL = int(zombie_config.find('wander_interval').get('value'))
ZOMBIE_LINE_OF_SIGHT_CHECK = zombie_config.find('sight_check').get('value') == 'true'
ZOMBIES_PER_SPAWN = int(zombie_config.find('spawn').get('value'))