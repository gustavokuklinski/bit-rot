import pygame
import xml.etree.ElementTree as ET

pygame.init()

# --- Scalable Screen Setup ---
VIRTUAL_SCREEN_WIDTH = 1280
VIRTUAL_GAME_HEIGHT = 720

GAME_OFFSET_X = 0 # X position where the central game box starts (no left panel)
GAME_WIDTH = VIRTUAL_SCREEN_WIDTH
GAME_HEIGHT = VIRTUAL_GAME_HEIGHT

# Tile size
TILE_SIZE = 16

MAP_DIR = "game/map/" # Game map files
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
GAME_BG_COLOR = (53, 173, 220)
GRAY_60 = (60, 60, 60)
GRAY_40 = (40, 40, 40)
GRAY_80 = (80, 80, 80)

# Inventory Modal
INVENTORY_MODAL_WIDTH = 300
INVENTORY_MODAL_HEIGHT = 330

# Status Modal
STATUS_MODAL_WIDTH = 250
STATUS_MODAL_HEIGHT = 360

# Nearby Modal
NEARBY_MODAL_WIDTH = 300
NEARBY_MODAL_HEIGHT = 320

# Container Modal
CONTAINER_MODAL_WIDTH = 300
CONTAINER_MODAL_HEIGHT = 300

# Messages Modal
MESSAGES_MODAL_WIDTH = 400
MESSAGES_MODAL_HEIGHT = 150

TEXT_MODAL_WIDTH = 300
TEXT_MODAL_HEIGHT = 300

MOBILE_MODAL_WIDTH = 250
MOBILE_MODAL_HEIGHT = 400


FONT_FACE = "game/font/Oxanium-Regular.ttf"

# Fonts
font = pygame.font.Font(FONT_FACE, 16)
font_small = pygame.font.Font(FONT_FACE, 16)
large_font = pygame.font.Font(FONT_FACE, 16)
title_font = pygame.font.Font(FONT_FACE, 16)
font_notification = pygame.font.Font(FONT_FACE, 10)

# Game XML Config
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
AUTO_DRINK = player_config.find('water_autodrink').get('value') == 'true'
AUTO_DRINK_THRESHOLD = int(player_config.find('water_threshold').get('value'))

BASE_PLAYER_VIEW_RADIUS = int(player_config.find('view_radius').get('value')) * TILE_SIZE
PLAYER_FOW_RADIUS = int(player_config.find('fow_radius').get('value'))

START_HOUR = int(player_config.find('start_hour').get('value'))
DAY_NIGHT_CYCLE_MS = int(player_config.find('day_night_cycle').get('value'))
TRANSITION_DURATION_MS = int(player_config.find('day_night_cycle_transition').get('value'))
MAX_DARKNESS_OPACITY = int(player_config.find('day_night_cycle_darkness').get('value'))

# Zombie settings
zombie_config = root.find('zombie')
ZOMBIE_SPEED = float(zombie_config.find('speed').get('value'))
MAX_ZOMBIES_GLOBAL = int(zombie_config.find('max_zombies').get('value'))
ZOMBIE_DROP = int(zombie_config.find('drop').get('value'))
ZOMBIE_DETECTION_RADIUS = int(zombie_config.find('detection').get('value')) * TILE_SIZE
ZOMBIE_WANDER_ENABLED = zombie_config.find('wander').get('value')
ZOMBIE_WANDER_CHANGE_INTERVAL = int(zombie_config.find('wander_interval').get('value'))
ZOMBIE_LINE_OF_SIGHT_CHECK = zombie_config.find('sight_check').get('value')
ZOMBIES_PER_SPAWN = int(zombie_config.find('spawn').get('value'))
ZOMBIE_RESPAWN_TIMER_MS = int(zombie_config.find('respawn_timer').get('value'))
ZOMBIE_DETECTION_RADIUS = 100

# Durability settings
durability_config = root.find('durability')
DURABILITY_MULTIPLIER = float(durability_config.find('multiplier').get('value'))
WEAPON_DURABILITY_MULTIPLIER = float(durability_config.find('weapon_multiplier').get('value'))
TOOL_DURABILITY_MULTIPLIER = float(durability_config.find('tool_multiplier').get('value'))

# Spawning settings
spawning_config = root.find('spawning')
ITEM_SPAWN_CHANCE_MULTIPLIER = float(spawning_config.find('item_spawn_chance_multiplier').get('value'))