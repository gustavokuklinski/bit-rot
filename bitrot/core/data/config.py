import pygame
import xml.etree.ElementTree as ET
import os
import sys
import platform
import subprocess
import uuid
from collections import OrderedDict

def get_writable_dir():
    return os.path.abspath(".")

pygame.init()
infoObject = pygame.display.Info()

GAME_OFFSET_X = 0 
GAME_WIDTH = 1280
GAME_HEIGHT = 720

if getattr(sys, 'frozen', False) or '__compiled__' in globals():
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(current_dir, "..", ".."))

VERSION_PATH = os.path.join(BASE_DIR, "data.rot", "lib", "VERSION")
MAP_DIR      = os.path.join(BASE_DIR, "data.rot", "lib", "map") + os.sep
DATA_PATH    = os.path.join(BASE_DIR, "data.rot", "lib", "data") + os.sep
SPRITE_PATH  = os.path.join(BASE_DIR, "data.rot", "lib", "sprites") + os.sep
SOUND_PATH   = os.path.join(BASE_DIR, "data.rot", "lib", "sfx") + os.sep
FONT_FACE    = os.path.join(BASE_DIR, "data.rot", "lib", "font", "PixelOperator8.ttf")

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

INVENTORY_MODAL_WIDTH = 256
INVENTORY_MODAL_HEIGHT = 240
STATUS_MODAL_WIDTH = 256
STATUS_MODAL_HEIGHT = 480
NEARBY_MODAL_WIDTH = 256
NEARBY_MODAL_HEIGHT = 240
CONTAINER_MODAL_WIDTH = 256
CONTAINER_MODAL_HEIGHT = 240
GEAR_MODAL_WIDTH = 256
GEAR_MODAL_HEIGHT = 240
MOBILE_MODAL_WIDTH = 256
MOBILE_MODAL_HEIGHT = 240
SLOTS_MODAL_WIDTH = 256
SLOTS_MODAL_HEIGHT = 240
TEXT_MODAL_WIDTH = 256
TEXT_MODAL_HEIGHT = 240
VEHICLE_MODAL_WIDTH = 512
VEHICLE_MODAL_HEIGHT = 240
MESSAGES_MODAL_WIDTH = 512
MESSAGES_MODAL_HEIGHT = 240
CRAFTING_MODAL_WIDTH = 920
CRAFTING_MODAL_HEIGHT = 600
MAP_MODAL_WIDTH = 720
MAP_MODAL_HEIGHT = 600
HELP_MODAL_WIDTH = 720
HELP_MODAL_HEIGHT = 600
NPC_DIALOG_MODAL_WIDTH = 720
NPC_DIALOG_MODAL_HEIGHT = 450

font_16 = None
font_14 = None
font_12 = None
TILE_SIZE = 16

# WORLD DEFAULTS
TIME_DAYLENGTH = 0
TIME_SUNRISE_HR = 0.0
TIME_SUNSET_HR = 0.0
TIME_TRANSITION_HR = 0.0
TIME_START_HR = 0.0
MAX_DARKNESS_OPACITY = 0
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
ZOMBIE_RESPAWN = True
ZOMBIE_INFECTION_CHANCE = 0.0
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
NPC_RESPAWN = True
MAX_VEH_CHUNK = 0
VEH_HAS_FUEL = 1.0
VEH_HAS_KEY = 1.0
VEH_HAS_MOTOR = 1.0
VEH_HAS_BATTERY = 1.0
VEH_HAS_TIRES = 1.0
MAP_CHUNKS = 0
CHUNK_SIZE = 128
ANIMAL_MAX_CHUNK = 10
ANIMAL_SPAWN_COUNT = 10
ANIMALS_PER_SPAWN = 5
ANIMAL_RESPAWN = True

# PREFERENCES DEFAULTS
UI_BACKGROUND_MUSIC = True
UI_SHOW_TUTORIAL_DEFAULT = True
RESOLUTION = "1280x720"
WINDOW_MODE = "fullscreen"
UI_SCALE = 1
START_ZOOM = 1.0
FAR_ZOOM = 0.5
NEAR_ZOOM = 2.0
VOLUME_MUSIC = 0.50
VOLUME_BACKGROUND = 0.50
VOLUME_ATMOSPHERIC = 0.50
VOLUME_ANIMAL = 0.50
VOLUME_NPC = 0.50
VOLUME_ZOMBIE = 0.50
VOLUME_PLAYER = 0.50
VOLUME_VEHICLE = 0.50
VOLUME_ITEMS = 0.50
VOLUME_MAP = 0.50
GAME_LANGUAGE = "en_US"

MAX_CLIENTS = 16

def generate_random_seed(chunks=None):
    if chunks is None:
        chunks = MAP_CHUNKS
    return f"{chunks}-{uuid.uuid4().hex[:8].upper()}"

# --- FILE PATH HANDLERS ---
def get_preferences_path():
    """Gets the global preferences.xml path."""
    writable_root = get_writable_dir()
    filepath = os.path.join(writable_root, "data.rot", "save", "config", "preferences.xml")
    if not os.path.exists(filepath):
        filepath = os.path.join(BASE_DIR, "data.rot", "save", "config", "preferences.xml")
    return filepath

def get_world_config_path(preset="world"):
    """Gets the world configuration path."""
    if not preset or preset == "default":
        preset = "world"

    writable_root = get_writable_dir()
    candidates = [
        os.path.join(writable_root, "data.rot", "save", "config", f"{preset}.xml"),
        os.path.join(BASE_DIR, "data.rot", "save", "config", f"{preset}.xml"),
        os.path.join(DATA_PATH, "config", f"{preset}.xml"),
        os.path.join(DATA_PATH, f"{preset}.xml"),
        os.path.join(BASE_DIR, "data.rot", "lib", "data", "config", f"{preset}.xml"),
        os.path.join(BASE_DIR, "data.rot", "lib", "config", f"{preset}.xml"),
        # Fallbacks to world.xml
        os.path.join(writable_root, "data.rot", "save", "config", "world.xml"),
        os.path.join(BASE_DIR, "data.rot", "save", "config", "world.xml"),
        os.path.join(DATA_PATH, "config", "world.xml"),
        os.path.join(DATA_PATH, "world.xml"),
        os.path.join(BASE_DIR, "data.rot", "lib", "data", "config", "world.xml"),
        os.path.join(BASE_DIR, "data.rot", "lib", "config", "world.xml"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]

class ImageFontWrapper:
    def __init__(self, font_path, size, is_sysfont=False, max_cache_size=256):
        if is_sysfont: self.font = pygame.font.SysFont(font_path, size)
        else: self.font = pygame.font.Font(font_path, size)
        self.cache = OrderedDict()
        self.max_cache_size = max_cache_size

    def render(self, text, antialias, color, background=None):
        text_str = str(text)
        color_key = tuple(color) if isinstance(color, (list, tuple, pygame.Color)) else color
        bg_key = tuple(background) if isinstance(background, (list, tuple, pygame.Color)) else background
        style_key = (self.font.get_bold(), self.font.get_italic())
        cache_key = (text_str, color_key, bg_key, style_key)

        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]

        if len(self.cache) >= self.max_cache_size:
            self.cache.popitem(last=False)

        rendered_surface = self.font.render(text_str, False, color, background)
        self.cache[cache_key] = rendered_surface
        return rendered_surface

    def clear_cache(self):
        self.cache.clear()

    def __getattr__(self, name):
        return getattr(self.font, name)

def load_settings(world_preset="world"):
    global GAME_WIDTH, GAME_HEIGHT, UI_SCALE, RESOLUTION_VALUE
    global font_16, font_14, font_12
    global TIME_DAYLENGTH, TIME_SUNRISE_HR, TIME_SUNSET_HR, TIME_TRANSITION_HR, TIME_START_HR
    global MAX_DARKNESS_OPACITY, START_ZOOM, FAR_ZOOM, NEAR_ZOOM, PLAYER_SPEED
    global AUTO_DRINK, AUTO_DRINK_THRESHOLD, BASE_PLAYER_VIEW_RADIUS
    global ZOMBIE_SPEED, MAX_ZOMBIES_GLOBAL, ZOMBIE_DROP, ZOMBIE_DETECTION_RADIUS
    global ZOMBIE_WANDER_ENABLED, ZOMBIE_WANDER_CHANGE_INTERVAL, ZOMBIE_LINE_OF_SIGHT_CHECK
    global ZOMBIES_PER_SPAWN, ZOMBIE_RESPAWN, ZOMBIE_INFECTION_CHANCE
    global DURABILITY_MULTIPLIER, WEAPON_MELEE_DURABILITY_MULTIPLIER
    global WEAPON_RANGED_DURABILITY_MULTIPLIER, CLOTH_DURABILITY_MULTIPLIER
    global ITEM_SPAWN_CHANCE_MULTIPLIER
    global MAX_NPCS_GLOBAL, NPC_SPAWN_CHANCE, NPC_HEALTH_MULTIPLIER
    global NPC_DAMAGE_MULTIPLIER, NPC_SPEED_MULTIPLIER, NPC_DETECTION_RADIUS, NPC_STATIC_PERCENT, NPC_HOSTILE_PERCENT
    global MAX_VEH_CHUNK, VEH_HAS_FUEL, VEH_HAS_KEY, VEH_HAS_MOTOR, VEH_HAS_BATTERY, VEH_HAS_TIRES
    global NPC_MAX_CHUNK, NPCS_PER_SPAWN, NPC_RESPAWN, ZOMBIE_MAX_CHUNK
    global MAP_CHUNKS, CHUNK_SIZE
    global UI_BACKGROUND_MUSIC, UI_SHOW_TUTORIAL_DEFAULT, RESOLUTION, WINDOW_MODE
    global ANIMAL_MAX_CHUNK, ANIMALS_PER_SPAWN, ANIMAL_RESPAWN, ANIMAL_SPAWN_COUNT
    global VOLUME_MUSIC, VOLUME_BACKGROUND, VOLUME_ATMOSPHERIC, VOLUME_ANIMAL, VOLUME_NPC, VOLUME_ZOMBIE, VOLUME_PLAYER, VOLUME_VEHICLE, VOLUME_ITEMS, VOLUME_MAP
    global GAME_LANGUAGE 

    pref_path = get_preferences_path()
    try:
        tree = ET.parse(pref_path)
        root = tree.getroot()
        ui_config = root.find('ui')
        if ui_config is not None:
            val_music = ui_config.find('ui_background_music')
            if val_music is not None: UI_BACKGROUND_MUSIC = str(val_music.get('value')).lower() == 'true'
            val_tutorial = ui_config.find('ui_show_tutorial_default')
            if val_tutorial is not None: UI_SHOW_TUTORIAL_DEFAULT = str(val_tutorial.get('value')).lower() == 'true'
            val_lang = ui_config.find('language')
            if val_lang is not None: GAME_LANGUAGE = val_lang.get('value', 'en_US')
            val_mode = ui_config.find('window_mode')
            if val_mode is not None: WINDOW_MODE = val_mode.get('value', 'windowed')

        audio_config = root.find('audio')
        if audio_config is not None:
            VOLUME_MUSIC = float(audio_config.find('volume_music').get('value', '0.5'))
            VOLUME_BACKGROUND = float(audio_config.find('volume_background').get('value', '0.5'))
            VOLUME_ATMOSPHERIC = float(audio_config.find('volume_atmospheric').get('value', '0.5'))
            VOLUME_MAP = float(audio_config.find('volume_map').get('value', '0.5'))
            VOLUME_ITEMS = float(audio_config.find('volume_items').get('value', '0.5'))
            VOLUME_VEHICLE = float(audio_config.find('volume_vehicle').get('value', '0.5'))
            VOLUME_PLAYER = float(audio_config.find('volume_player').get('value', '0.5'))
            VOLUME_ZOMBIE = float(audio_config.find('volume_zombie').get('value', '0.5'))
            VOLUME_NPC = float(audio_config.find('volume_npc').get('value', '0.5'))
            VOLUME_ANIMAL = float(audio_config.find('volume_animal').get('value', '0.5'))

        player_pref = root.find('player')
        if player_pref is not None:
            START_ZOOM = float(player_pref.find('zoom_start').get('value', '3.0'))
            FAR_ZOOM = float(player_pref.find('zoom_far').get('value', '2.0'))
            NEAR_ZOOM = float(player_pref.find('zoom_near').get('value', '3.5'))
    except Exception as e:
        print(f"Error loading preferences: {e}")

    def _get_val(parent, tag, default):
        if parent is None: return default
        node = parent.find(tag)
        return node.get('value', default) if node is not None else default

    world_path = get_world_config_path(world_preset)
    try:
        tree = ET.parse(world_path)
        root = tree.getroot()

        game_config = root.find('game')
        if game_config is not None:
            TIME_TRANSITION_HR = 1.0
            MAX_DARKNESS_OPACITY = 255
            TIME_DAYLENGTH = int(_get_val(game_config, 'time_daylength', '900000'))
            TIME_SUNRISE_HR = float(_get_val(game_config, 'time_sunrise_hr', '5.5'))
            TIME_SUNSET_HR = float(_get_val(game_config, 'time_sunset_hr', '17.5'))
            TIME_START_HR = float(_get_val(game_config, 'time_start_hr', '6.0'))

        map_config = root.find('map')
        if map_config is not None:
            MAP_CHUNKS = int(_get_val(map_config, 'map_chunks', '2'))
            CHUNK_SIZE = 128
        
        player_config = root.find('player')
        if player_config is not None:
            PLAYER_SPEED = 1.6 
            BASE_PLAYER_VIEW_RADIUS = int(_get_val(player_config, 'view_radius', '9')) * TILE_SIZE
            val_auto_drink = _get_val(player_config, 'water_autodrink', 'true')
            AUTO_DRINK = str(val_auto_drink).lower() == 'true'
            AUTO_DRINK_THRESHOLD = int(_get_val(player_config, 'water_threshold', '100'))

        zombie_config = root.find('zombie')
        if zombie_config is not None:
            ZOMBIE_WANDER_ENABLED = str(_get_val(zombie_config, 'wander', 'true')).lower() == 'true'
            ZOMBIES_PER_SPAWN = int(_get_val(zombie_config, 'spawn', '3'))
            ZOMBIE_RESPAWN = str(_get_val(zombie_config, 'respawn', 'true')).lower() == 'true'
            ZOMBIE_MAX_CHUNK = int(_get_val(zombie_config, 'zombie_spawn_per_chunk', '6'))
            ZOMBIE_INFECTION_CHANCE = float(_get_val(zombie_config, 'infection_chance', '0.25'))
            ZOMBIE_LINE_OF_SIGHT_CHECK = str(_get_val(zombie_config, 'sight_check', 'true')).lower() == 'true'
            ZOMBIE_SPEED = 0.3
            ZOMBIE_DETECTION_RADIUS = 5 * TILE_SIZE
            ZOMBIE_DROP = 1
            MAX_ZOMBIES_GLOBAL = 500
            ZOMBIE_WANDER_CHANGE_INTERVAL = 2000

        spawning_config = root.find('item_spawning')
        if spawning_config is not None:
            ITEM_SPAWN_CHANCE_MULTIPLIER = float(_get_val(spawning_config, 'item_spawn_chance_multiplier', '1.0'))

        npc_config = root.find('npc')
        if npc_config is not None:
            MAX_NPCS_GLOBAL = 1500
            NPC_SPAWN_CHANCE = 1.0
            NPC_HEALTH_MULTIPLIER = 1.0
            NPC_DAMAGE_MULTIPLIER = 1.0
            NPC_SPEED_MULTIPLIER = 1.0
            NPC_DETECTION_RADIUS = 5 * TILE_SIZE
            NPC_MAX_CHUNK = int(_get_val(npc_config, 'npc_spawn_per_chunk', '12'))
            NPCS_PER_SPAWN = int(_get_val(npc_config, 'spawn', '6'))
            NPC_STATIC_PERCENT = float(_get_val(npc_config, 'static_percent', '0.40'))    
            NPC_HOSTILE_PERCENT = float(_get_val(npc_config, 'hostile_percent', '0.60'))
            NPC_RESPAWN = str(_get_val(npc_config, 'respawn', 'true')).lower() == 'true'

        vehicle_config = root.find('vehicle')
        if vehicle_config is not None:
            MAX_VEH_CHUNK = int(_get_val(vehicle_config, 'vehicle_spawn_per_chunk', '5'))
            VEH_HAS_FUEL = float(_get_val(vehicle_config, 'has_fuel_chance', '0.25'))
            VEH_HAS_KEY = float(_get_val(vehicle_config, 'has_key_chance', '0.25'))
            VEH_HAS_MOTOR = float(_get_val(vehicle_config, 'has_motor_chance', '1.0'))
            VEH_HAS_BATTERY = float(_get_val(vehicle_config, 'has_battery_chance', '0.75'))
            VEH_HAS_TIRES = float(_get_val(vehicle_config, 'has_tires_chance', '1.0'))

        animal_config = root.find('animal')
        if animal_config is not None:
            ANIMAL_MAX_CHUNK = int(_get_val(animal_config, 'animal_spawn_per_chunk', '6'))
            ANIMAL_SPAWN_COUNT = ANIMAL_MAX_CHUNK
            ANIMALS_PER_SPAWN = int(_get_val(animal_config, 'spawn', '3'))
            ANIMAL_RESPAWN = str(_get_val(animal_config, 'respawn', 'true')).lower() == 'true'

    except Exception as e:
        print(f"Error loading world from {world_path}: {e}")

    # Fonts
    font_16  = ImageFontWrapper(FONT_FACE, 16)
    font_14  = ImageFontWrapper(FONT_FACE, 8)
    font_12  = ImageFontWrapper(FONT_FACE, 12)

def save_language_to_config(lang_code):
    global GAME_LANGUAGE
    GAME_LANGUAGE = lang_code
    filepath = get_preferences_path()
    
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if not os.path.exists(filepath):
            root = ET.Element('preferences')
        else:
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
        
        import xml.dom.minidom
        raw_xml = ET.tostring(root, 'utf-8')
        pretty_xml = xml.dom.minidom.parseString(raw_xml).toprettyxml(indent="    ")
        pretty_xml = os.linesep.join([s for s in pretty_xml.splitlines() if s.strip()])
        
        with open(filepath, "w") as f:
            f.write(pretty_xml)
    except Exception as e:
        print(f"Error saving language to preferences.xml: {e}")

version_file_path = VERSION_PATH
try:
    with open(version_file_path, "r") as f:
        GAME_VERSION = f.read().strip()
except:
    GAME_VERSION = "0.0.6"

load_settings()