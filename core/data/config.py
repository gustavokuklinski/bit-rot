# core/data/config.py
import pygame
import xml.etree.ElementTree as ET
import os
import subprocess
import uuid

pygame.init()
infoObject = pygame.display.Info()

GAME_OFFSET_X = 0 
GAME_WIDTH = 1280
GAME_HEIGHT = 720

MAP_DIR = "./game/lib/map/" 
DATA_PATH = "./game/lib/data/" 
SPRITE_PATH = "./game/lib/sprites/" 
SOUND_PATH = "./game/lib/sfx/" 

# Colors
TRANSPARENT = (0, 0, 0, 0)
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

INVENTORY_MODAL_WIDTH = 300
INVENTORY_MODAL_HEIGHT = 345
STATUS_MODAL_WIDTH = 230 
STATUS_MODAL_HEIGHT = 360
NEARBY_MODAL_WIDTH = 300
NEARBY_MODAL_HEIGHT = 320
CONTAINER_MODAL_WIDTH = 300
CONTAINER_MODAL_HEIGHT = 300
MESSAGES_MODAL_WIDTH = 400
MESSAGES_MODAL_HEIGHT = 300
TEXT_MODAL_WIDTH = 300
TEXT_MODAL_HEIGHT = 300
VEHICLE_MODAL_WIDTH = 400
VEHICLE_MODAL_HEIGHT = 300
MOBILE_MODAL_WIDTH = 250
MOBILE_MODAL_HEIGHT = 350
GEAR_MODAL_WIDTH = 300
GEAR_MODAL_HEIGHT = 320
CRAFTING_MODAL_WIDTH = 700
CRAFTING_MODAL_HEIGHT = 560
MAP_MODAL_WIDTH = 950
MAP_MODAL_HEIGHT = 700
NPC_DIALOG_MODAL_WIDTH = 500
NPC_DIALOG_MODAL_HEIGHT = 400
HELP_MODAL_WIDTH = 900
HELP_MODAL_HEIGHT = 570

FONT_FACE = "./game/lib/font/Oxanium-Regular.ttf"

font = pygame.font.Font(FONT_FACE, 14)
font_14 = pygame.font.Font(FONT_FACE, 14)
font_xl = pygame.font.Font(FONT_FACE, 16)
font_xxl = pygame.font.Font(FONT_FACE, 24)

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
PLAYER_SPEED = 1.6
AUTO_DRINK = False
AUTO_DRINK_THRESHOLD = 0
BASE_PLAYER_VIEW_RADIUS = 0
ZOMBIE_SPEED = 0.0
MAX_ZOMBIES_GLOBAL = 0
ZOMBIE_MAX_CHUNK = 0
ZOMBIE_DROP = 0
ZOMBIE_DETECTION_RADIUS = 0
ZOMBIE_WANDER_ENABLED = True
ZOMBIE_WANDER_CHANGE_INTERVAL = 0
ZOMBIE_LINE_OF_SIGHT_CHECK = True
ZOMBIES_PER_SPAWN = 0
ZOMBIE_RESPAWN_TIMER_MS = 0
ZOMBIE_INFECTION_CHANCE = 0.0
ZOMBIE_MULTIPLIER = 2
DURABILITY_MULTIPLIER = 1.0
WEAPON_MELEE_DURABILITY_MULTIPLIER = 1.0
WEAPON_RANGED_DURABILITY_MULTIPLIER = 1.0
CLOTH_DURABILITY_MULTIPLIER = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER = 1.0
NPC_MAX_CHUNK = 0
NPC_HOSTILE_PERCENT = 0
MAX_NPCS_GLOBAL = 0
NPC_SPAWN_CHANCE = 0.0
NPC_HEALTH_MULTIPLIER = 1.0
NPC_DAMAGE_MULTIPLIER = 1.0
NPC_SPEED_MULTIPLIER = 1.0
NPC_DETECTION_RADIUS = 0
NPC_STATIC_PERCENT = 0.0
MAX_VEH_CHUNK = 0
VEH_HAS_FUEL = 1.0
VEH_HAS_KEY = 1.0
VEH_HAS_MOTOR = 1.0
VEH_HAS_BATTERY = 1.0
VEH_HAS_TIRES = 1.0
MAP_CHUNKS = 0
UI_BACKGROUND_MUSIC = True
UI_SHOW_TUTORIAL_DEFAULT = True
ANIMAL_SPAWN_COUNT = 0
ANIMAL_RESPAWN_TIMER_MS = 0

VOLUME_MUSIC = 0.50
VOLUME_BACKGROUND = 0.50
VOLUME_ATMOSPHERIC = 0.50

GAME_LANGUAGE = "en_US"

def generate_random_seed(chunks=None):
    if chunks is None:
        chunks = MAP_CHUNKS
    return f"{chunks}-{uuid.uuid4().hex[:8].upper()}"

def load_settings(preset="default"):
    global TIME_DAYLENGTH, TIME_SUNRISE_HR, TIME_SUNSET_HR, TIME_TRANSITION_HR, TIME_START_HR
    global MAX_DARKNESS_OPACITY, START_ZOOM, FAR_ZOOM, NEAR_ZOOM, PLAYER_SPEED
    global AUTO_DRINK, AUTO_DRINK_THRESHOLD, BASE_PLAYER_VIEW_RADIUS
    global ZOMBIE_SPEED, MAX_ZOMBIES_GLOBAL, ZOMBIE_DROP, ZOMBIE_DETECTION_RADIUS
    global ZOMBIE_WANDER_ENABLED, ZOMBIE_WANDER_CHANGE_INTERVAL, ZOMBIE_LINE_OF_SIGHT_CHECK
    global ZOMBIES_PER_SPAWN, ZOMBIE_RESPAWN_TIMER_MS, ZOMBIE_INFECTION_CHANCE, ZOMBIE_MULTIPLIER
    global DURABILITY_MULTIPLIER, WEAPON_MELEE_DURABILITY_MULTIPLIER
    global WEAPON_RANGED_DURABILITY_MULTIPLIER, CLOTH_DURABILITY_MULTIPLIER
    global ITEM_SPAWN_CHANCE_MULTIPLIER
    global MAX_NPCS_GLOBAL, NPC_SPAWN_CHANCE, NPC_HEALTH_MULTIPLIER
    global NPC_DAMAGE_MULTIPLIER, NPC_SPEED_MULTIPLIER, NPC_DETECTION_RADIUS, NPC_STATIC_PERCENT, NPC_HOSTILE_PERCENT
    global MAX_VEH_CHUNK, VEH_HAS_FUEL, VEH_HAS_KEY, VEH_HAS_MOTOR, VEH_HAS_BATTERY, VEH_HAS_TIRES
    global NPC_MAX_CHUNK, ZOMBIE_MAX_CHUNK
    global MAP_CHUNKS, CHUNK_SIZE
    global UI_BACKGROUND_MUSIC, UI_SHOW_TUTORIAL_DEFAULT
    global ANIMAL_SPAWN_COUNT, ANIMAL_RESPAWN_TIMER_MS
    global VOLUME_MUSIC, VOLUME_BACKGROUND, VOLUME_ATMOSPHERIC
    global GAME_LANGUAGE 

    filepath = f'./game/save/config/{preset}.xml'
    if not os.path.exists(filepath):
        print(f"Config file not found: {filepath}. Loading default.")
        filepath = './game/save/config/config.xml'

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        game_config = root.find('game')
        TIME_TRANSITION_HR = 1.0
        MAX_DARKNESS_OPACITY = 255
        TIME_DAYLENGTH = int(game_config.find('time_daylength').get('value'))
        TIME_SUNRISE_HR = float(game_config.find('time_sunrise_hr').get('value'))
        TIME_SUNSET_HR = float(game_config.find('time_sunset_hr').get('value'))
        TIME_START_HR = float(game_config.find('time_start_hr').get('value'))

        map_config = root.find('map')
        MAP_CHUNKS = int(map_config.find('map_chunks').get('value'))
        CHUNK_SIZE = 128
        
        player_config = root.find('player')
        PLAYER_SPEED = 1.6 

        BASE_PLAYER_VIEW_RADIUS = int(player_config.find('view_radius').get('value')) * TILE_SIZE
        START_ZOOM = float(player_config.find('zoom_start').get('value'))
        FAR_ZOOM = float(player_config.find('zoom_far').get('value'))
        NEAR_ZOOM = float(player_config.find('zoom_near').get('value'))

        val_auto_drink = player_config.find('water_autodrink').get('value')
        AUTO_DRINK = str(val_auto_drink).lower() == 'true'
        AUTO_DRINK_THRESHOLD = int(player_config.find('water_threshold').get('value'))

        zombie_config = root.find('zombie')
        val_wander = zombie_config.find('wander').get('value')
        ZOMBIE_WANDER_ENABLED = str(val_wander).lower() == 'true'
        ZOMBIES_PER_SPAWN = int(zombie_config.find('spawn').get('value'))
        ZOMBIE_RESPAWN_TIMER_MS = int(zombie_config.find('respawn_timer').get('value'))
        ZOMBIE_MAX_CHUNK = int(zombie_config.find('zombie_spawn_per_chunk').get('value'))
        ZOMBIE_MULTIPLIER = int(zombie_config.find('zombie_multiplier').get('value'))
        ZOMBIE_INFECTION_CHANCE = 0.4
        ZOMBIE_LINE_OF_SIGHT_CHECK = True
        ZOMBIE_SPEED = 0.3
        ZOMBIE_DETECTION_RADIUS = 5 * TILE_SIZE
        ZOMBIE_DROP = 1
        MAX_ZOMBIES_GLOBAL = 10000
        ZOMBIE_WANDER_CHANGE_INTERVAL = 2000

        DURABILITY_MULTIPLIER = 1.0
        WEAPON_MELEE_DURABILITY_MULTIPLIER = 1.0
        WEAPON_RANGED_DURABILITY_MULTIPLIER = 1.0
        CLOTH_DURABILITY_MULTIPLIER = 1.0

        spawning_config = root.find('item_spawning')
        if spawning_config is not None:
            multiplier_node = spawning_config.find('item_spawn_chance_multiplier')
            if multiplier_node is not None:
                ITEM_SPAWN_CHANCE_MULTIPLIER = float(multiplier_node.get('value'))

        npc_config = root.find('npc')
        MAX_NPCS_GLOBAL = 1500
        NPC_SPAWN_CHANCE = 1.0
        NPC_HEALTH_MULTIPLIER = 1.0
        NPC_DAMAGE_MULTIPLIER = 1.0
        NPC_SPEED_MULTIPLIER = 1.0
        NPC_DETECTION_RADIUS = 10 * TILE_SIZE

        NPC_MAX_CHUNK = int(npc_config.find('npc_spawn_per_chunk').get('value'))
        NPC_STATIC_PERCENT = float(npc_config.find('static_percent').get('value'))    
        NPC_HOSTILE_PERCENT = float(npc_config.find('hostile_percent').get('value'))

        vehicle_config = root.find('vehicle')
        MAX_VEH_CHUNK = int(vehicle_config.find('vehicle_spawn_per_chunk').get('value'))
        VEH_HAS_FUEL = float(vehicle_config.find('has_fuel_chance').get('value'))
        VEH_HAS_KEY = float(vehicle_config.find('has_key_chance').get('value'))
        VEH_HAS_MOTOR = float(vehicle_config.find('has_motor_chance').get('value'))
        VEH_HAS_BATTERY = float(vehicle_config.find('has_battery_chance').get('value'))
        VEH_HAS_TIRES = float(vehicle_config.find('has_tires_chance').get('value'))

        ui_config = root.find('ui')
        val_music = ui_config.find('ui_background_music').get('value')
        UI_BACKGROUND_MUSIC = str(val_music).lower() == 'true'
        val_tutorial = ui_config.find('ui_show_tutorial_default')
        UI_SHOW_TUTORIAL_DEFAULT = str(val_tutorial.get('value')).lower() == 'true'

        val_lang = ui_config.find('language')
        if val_lang is not None:
            GAME_LANGUAGE = val_lang.get('value', 'en_US')
        else:
            GAME_LANGUAGE = 'en_US'
        
        audio_config = root.find('audio')
        vol_m = audio_config.find('volume_music')
        VOLUME_MUSIC = float(vol_m.get('value'))
        
        vol_b = audio_config.find('volume_background')
        VOLUME_BACKGROUND = float(vol_b.get('value'))
        
        vol_a = audio_config.find('volume_atmospheric')
        VOLUME_ATMOSPHERIC = float(vol_a.get('value'))

        animal_config = root.find('animal')
        ANIMAL_SPAWN_COUNT = int(animal_config.find('animal_spawn_per_chunk').get('value'))
        ANIMAL_RESPAWN_TIMER_MS = int(animal_config.find('animal_respawn_ms_timer').get('value'))
        
        print(f"Configuration loaded from {filepath}")

    except Exception as e:
        print(f"Error loading config from {filepath}: {e}")

# --- NEW: Independent save override for Language to strictly respect XML ---
def save_language_to_config(lang_code, preset="config"):
    global GAME_LANGUAGE
    GAME_LANGUAGE = lang_code
    filepath = f'./game/save/config/{preset}.xml'
    
    if not os.path.exists(filepath):
        return
        
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        ui_config = root.find('ui')
        if ui_config is None:
            ui_config = ET.SubElement(root, 'ui')
            
        lang_node = ui_config.find('language')
        if lang_node is None:
            lang_node = ET.SubElement(ui_config, 'language')
            
        lang_node.set('value', lang_code)
        lang_node.set('name', 'Language')
        
        # Cleanly Format
        import xml.dom.minidom
        raw_xml = ET.tostring(root, 'utf-8')
        pretty_xml = xml.dom.minidom.parseString(raw_xml).toprettyxml(indent="    ")
        pretty_xml = os.linesep.join([s for s in pretty_xml.splitlines() if s.strip()])
        
        with open(filepath, "w") as f:
            f.write(pretty_xml)
    except Exception as e:
        print(f"Error saving language to config: {e}")

version_file_path = "game/lib/VERSION"

try:
    with open(version_file_path, "r") as f:
        GAME_VERSION = f.read().strip()
except:
    GAME_VERSION = "0.0.1"

load_settings()