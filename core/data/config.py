import pygame
import xml.etree.ElementTree as ET
import os
import subprocess

pygame.init()
infoObject = pygame.display.Info()

# --- Scalable Screen Setup ---
VIRTUAL_SCREEN_WIDTH = 1360
VIRTUAL_GAME_HEIGHT = 720

GAME_OFFSET_X = 0 # X position where the central game box starts (no left panel)
GAME_WIDTH = VIRTUAL_SCREEN_WIDTH
GAME_HEIGHT = VIRTUAL_GAME_HEIGHT


MAP_DIR = "./game/lib/map/" # Game map files
DATA_PATH = "./game/lib/data/" # Folders with XML data files
SPRITE_PATH = "./game/lib/sprites/" # Folders with PNG sprites
SOUND_PATH = "./game/lib/sfx/" # Sound OGG files

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
GREEN = (50, 200, 50)
BLUE = (50, 50, 200)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
ORANGE = (255, 140, 0)
DARK_GRAY = (30, 30, 30)
PANEL_COLOR = (20, 20, 20)
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
MESSAGES_MODAL_HEIGHT = 350

# Text modal
TEXT_MODAL_WIDTH = 300
TEXT_MODAL_HEIGHT = 300

VEHICLE_MODAL_WIDTH = 300
VEHICLE_MODAL_HEIGHT = 320

# Mobile modal
MOBILE_MODAL_WIDTH = 250
MOBILE_MODAL_HEIGHT = 400

# Gear Modal
GEAR_MODAL_WIDTH = 200
GEAR_MODAL_HEIGHT = 290


FONT_FACE = "./game/lib/font/Oxanium-Regular.ttf"

# Fonts
font = pygame.font.Font(FONT_FACE, 16)
font_small = pygame.font.Font(FONT_FACE, 16)
large_font = pygame.font.Font(FONT_FACE, 16)
title_font = pygame.font.Font(FONT_FACE, 16)
font_notification = pygame.font.Font(FONT_FACE, 14)


# Global Default game settings
TILE_SIZE = 16
TIME_DAYLENGTH = 0
TIME_SUNRISE_HR = 0.0
TIME_SUNSET_HR = 0.0
TIME_TRANSITION_HR = 0.0
TIME_START_HR = 0.0
MAX_DARKNESS_OPACITY = 0
START_ZOOM = 1.0
FAR_ZOOM = 0.5
NEAR_ZOOM = 2.0
PLAYER_SPEED = 1.5
DECAY_RATE_SECONDS = 0.0
FOOD_WATER_MULTIPLIER_DECAY = 1.0
FOOD_DECAY_AMOUNT = 0.0
WATER_DECAY_AMOUNT = 0.0
AUTO_DRINK = False
AUTO_DRINK_THRESHOLD = 0
BASE_PLAYER_VIEW_RADIUS = 0
PLAYER_FOW_RADIUS = 0
ZOMBIE_SPEED = 0.0
MAX_ZOMBIES_GLOBAL = 0
ZOMBIE_DROP = 0
ZOMBIE_DETECTION_RADIUS = 0
ZOMBIE_WANDER_ENABLED = True
ZOMBIE_WANDER_CHANGE_INTERVAL = 0
ZOMBIE_LINE_OF_SIGHT_CHECK = True
ZOMBIES_PER_SPAWN = 0
ZOMBIE_RESPAWN_TIMER_MS = 0
ZOMBIE_INFECTION_CHANCE = 0.0
DURABILITY_MULTIPLIER = 1.0
WEAPON_MELEE_DURABILITY_MULTIPLIER = 1.0
WEAPON_RANGED_DURABILITY_MULTIPLIER = 1.0
TOOL_DURABILITY_MULTIPLIER = 1.0
CLOTH_DURABILITY_MULTIPLIER = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_MELEE = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_RANGED = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_MOBILE = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_CONTAINER = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_BACKPACK = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_FOOD = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_DRINK = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_MEDICATION = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_AMMO = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_CURRENCY = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER_TEXT = 1.0


def load_settings(preset="default"):
    """Loads configuration from XML and updates global variables."""
    global TIME_DAYLENGTH, TIME_SUNRISE_HR, TIME_SUNSET_HR, TIME_TRANSITION_HR, TIME_START_HR
    global MAX_DARKNESS_OPACITY, START_ZOOM, FAR_ZOOM, NEAR_ZOOM, PLAYER_SPEED
    global DECAY_RATE_SECONDS, FOOD_WATER_MULTIPLIER_DECAY, FOOD_DECAY_AMOUNT, WATER_DECAY_AMOUNT
    global AUTO_DRINK, AUTO_DRINK_THRESHOLD, BASE_PLAYER_VIEW_RADIUS, PLAYER_FOW_RADIUS
    global ZOMBIE_SPEED, MAX_ZOMBIES_GLOBAL, ZOMBIE_DROP, ZOMBIE_DETECTION_RADIUS
    global ZOMBIE_WANDER_ENABLED, ZOMBIE_WANDER_CHANGE_INTERVAL, ZOMBIE_LINE_OF_SIGHT_CHECK
    global ZOMBIES_PER_SPAWN, ZOMBIE_RESPAWN_TIMER_MS, ZOMBIE_INFECTION_CHANCE
    global DURABILITY_MULTIPLIER, WEAPON_MELEE_DURABILITY_MULTIPLIER, TOOL_DURABILITY_MULTIPLIER
    global WEAPON_RANGED_DURABILITY_MULTIPLIER, CLOTH_DURABILITY_MULTIPLIER
    global ITEM_SPAWN_CHANCE_MULTIPLIER
    global ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_MELEE, ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_RANGED
    global ITEM_SPAWN_CHANCE_MULTIPLIER_MOBILE, ITEM_SPAWN_CHANCE_MULTIPLIER_CONTAINER
    global ITEM_SPAWN_CHANCE_MULTIPLIER_BACKPACK, ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE
    global ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_FOOD, ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_DRINK
    global ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_MEDICATION, ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_AMMO
    global ITEM_SPAWN_CHANCE_MULTIPLIER_CURRENCY, ITEM_SPAWN_CHANCE_MULTIPLIER_TEXT

    filepath = f'./game/save/config/{preset}.xml'
    if not os.path.exists(filepath):
        print(f"Config file not found: {filepath}. Loading default.")
        filepath = './game/save/config/default.xml'

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        game_config = root.find('game')
        TIME_DAYLENGTH = int(game_config.find('time_daylength').get('value'))
        TIME_SUNRISE_HR = float(game_config.find('time_sunrise_hr').get('value'))
        TIME_SUNSET_HR = float(game_config.find('time_sunset_hr').get('value'))
        TIME_TRANSITION_HR = float(game_config.find('time_transition_hr').get('value'))
        TIME_START_HR = float(game_config.find('time_start_hr').get('value'))
        MAX_DARKNESS_OPACITY = int(game_config.find('day_night_cycle_darkness').get('value'))

        START_ZOOM = float(game_config.find('zoom_start').get('value'))
        FAR_ZOOM = float(game_config.find('zoom_far').get('value'))
        NEAR_ZOOM = float(game_config.find('zoom_near').get('value'))

        player_config = root.find('player')
        PLAYER_SPEED = 3.0 # Hardcoded as per original file

        DECAY_RATE_SECONDS = float(player_config.find('food_water_decay_seconds').get('value'))
        FOOD_WATER_MULTIPLIER_DECAY = float(player_config.find('food_water_multiplier_decay').get('value'))
        FOOD_DECAY_AMOUNT = float(player_config.find('food_decay').get('value')) * FOOD_WATER_MULTIPLIER_DECAY
        WATER_DECAY_AMOUNT = float(player_config.find('water_decay').get('value')) * FOOD_WATER_MULTIPLIER_DECAY * 1.5
        
        # Parse booleans correctly
        val_auto_drink = player_config.find('water_autodrink').get('value')
        AUTO_DRINK = str(val_auto_drink).lower() == 'true'
        
        AUTO_DRINK_THRESHOLD = int(player_config.find('water_threshold').get('value'))
        BASE_PLAYER_VIEW_RADIUS = int(player_config.find('view_radius').get('value')) * TILE_SIZE
        PLAYER_FOW_RADIUS = int(player_config.find('fow_radius').get('value'))

        zombie_config = root.find('zombie')
        ZOMBIE_SPEED = float(zombie_config.find('speed').get('value'))
        MAX_ZOMBIES_GLOBAL = int(zombie_config.find('max_zombies').get('value'))
        ZOMBIE_DROP = int(zombie_config.find('drop').get('value'))
        ZOMBIE_DETECTION_RADIUS = int(zombie_config.find('detection').get('value')) * TILE_SIZE
        
        val_wander = zombie_config.find('wander').get('value')
        ZOMBIE_WANDER_ENABLED = str(val_wander).lower() == 'true'
        
        ZOMBIE_WANDER_CHANGE_INTERVAL = int(zombie_config.find('wander_interval').get('value'))
        
        val_sight = zombie_config.find('sight_check').get('value')
        ZOMBIE_LINE_OF_SIGHT_CHECK = str(val_sight).lower() == 'true'
        
        ZOMBIES_PER_SPAWN = int(zombie_config.find('spawn').get('value'))
        ZOMBIE_RESPAWN_TIMER_MS = int(zombie_config.find('respawn_timer').get('value'))
        
        # Maintain override from original file
        ZOMBIE_DETECTION_RADIUS = 100
        
        ZOMBIE_INFECTION_CHANCE = float(zombie_config.find('infection_chance').get('value'))

        durability_config = root.find('durability')
        DURABILITY_MULTIPLIER = float(durability_config.find('multiplier').get('value'))
        WEAPON_MELEE_DURABILITY_MULTIPLIER = float(durability_config.find('weapon_melee_multiplier').get('value'))
        WEAPON_RANGED_DURABILITY_MULTIPLIER = float(durability_config.find('weapon_ranged_multiplier').get('value'))
        TOOL_DURABILITY_MULTIPLIER = float(durability_config.find('tool_multiplier').get('value'))
        CLOTH_DURABILITY_MULTIPLIER = float(durability_config.find('cloth_multiplier').get('value'))

        spawning_config = root.find('item_spawning')
        ITEM_SPAWN_CHANCE_MULTIPLIER = float(spawning_config.find('item_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_MELEE = float(spawning_config.find('item_weapon_melee_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_WEAPON_RANGED = float(spawning_config.find('item_weapon_ranged_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_MOBILE = float(spawning_config.find('item_mobile_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_CONTAINER = float(spawning_config.find('item_container_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_BACKPACK = float(spawning_config.find('item_backpack_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE = float(spawning_config.find('item_consumable_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_FOOD = float(spawning_config.find('item_consumable_food_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_DRINK = float(spawning_config.find('item_consumable_drink_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_MEDICATION = float(spawning_config.find('item_consumable_medication_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_CONSUMABLE_AMMO = float(spawning_config.find('item_consumable_ammo_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_CURRENCY = float(spawning_config.find('item_currency_spawn_chance_multiplier').get('value'))
        ITEM_SPAWN_CHANCE_MULTIPLIER_TEXT = float(spawning_config.find('item_text_spawn_chance_multiplier').get('value'))
        
        print(f"Configuration loaded from {filepath}")

    except Exception as e:
        print(f"Error loading config from {filepath}: {e}")

try:
    # Get the short hash (e.g., "a1b2c3d")
    GAME_VERSION =  "git+" + subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip() + "(main)"
except Exception:
    GAME_VERSION = "pre+Alpha(0.0.1)"

# Initial load
load_settings()