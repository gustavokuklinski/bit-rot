import json
import pygame
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
VEHICLE_MODAL_WIDTH = 256
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
PERMADEATH = False
ALL_VISIBLE = False
INFINITE_LIQUID = True
START_AT_THE_LOBBY = True
DISABLE_DISCOVER_ISLAND = False
NO_BOAT_TO_LOBBY = False
TIME_DAYLENGTH = 900000
TIME_SUNRISE_HR = 5.5
TIME_SUNSET_HR = 17.5
TIME_TRANSITION_HR = 1.0
TIME_START_HR = 6.0
MAX_DARKNESS_OPACITY = 255
PLAYER_SPEED = 1.7
AUTO_DRINK = True
AUTO_DRINK_THRESHOLD = 1.0
BASE_PLAYER_VIEW_RADIUS = 9 * 16
ZOMBIE_SPEED = 0.3
MAX_ZOMBIES_GLOBAL = 500
ZOMBIE_MAX_CHUNK = 6
BASE_ZOMBIE_MAX_CHUNK = 6
ZOMBIE_DROP = 1
ZOMBIE_DETECTION_RADIUS = 5 * 16
ZOMBIE_WANDER_ENABLED = True
ZOMBIE_WANDER_CHANGE_INTERVAL = 2000
ZOMBIE_LINE_OF_SIGHT_CHECK = True
ZOMBIES_PER_SPAWN = 3
ZOMBIE_RESPAWN = True
ZOMBIE_INFECTION_CHANCE = 0.25
DURABILITY_MULTIPLIER = 1.0
WEAPON_MELEE_DURABILITY_MULTIPLIER = 1.0
WEAPON_RANGED_DURABILITY_MULTIPLIER = 1.0
TOOL_DURABILITY_MULTIPLIER = 1.0
CLOTH_DURABILITY_MULTIPLIER = 1.0
ITEM_SPAWN_CHANCE_MULTIPLIER = 1.0
NPC_MAX_CHUNK = 6
NPC_HOSTILE_PERCENT = 0.60
MAX_NPCS_GLOBAL = 1500
NPC_SPAWN_CHANCE = 1.0
NPC_HEALTH_MULTIPLIER = 1.0
NPC_DAMAGE_MULTIPLIER = 1.0
NPC_SPEED_MULTIPLIER = 1.0
NPC_DETECTION_RADIUS = 5 * 16
NPC_STATIC_PERCENT = 0.40
NPC_RESPAWN = True
NPCS_PER_SPAWN = 3
MAX_VEH_CHUNK = 6
VEH_HAS_FUEL = 0.25
VEH_HAS_KEY = 0.25
VEH_HAS_MOTOR = 1.0
VEH_HAS_BATTERY = 0.75
VEH_HAS_TIRES = 1.0

MAP_CHUNKS = 2
CHUNK_SIZE = 128
WORLD_SEED = ""
SPAWN_LOBBY_CHUNK = True
SPAWN_MILITARY_CHUNK = True
GENERATE_IMAGES = True

ANIMAL_MAX_CHUNK = 6
ANIMAL_SPAWN_COUNT = 6
ANIMALS_PER_SPAWN = 3
ANIMAL_RESPAWN = True

# PREFERENCES DEFAULTS
UI_BACKGROUND_MUSIC = True
UI_SHOW_TUTORIAL_DEFAULT = True
UI_CRT_FILTER = True
CRT_FILTER = True
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



def generate_random_seed(chunks=None):
    if chunks is None:
        chunks = MAP_CHUNKS
    return f"{chunks}-{uuid.uuid4().hex[:8].upper()}"

# --- FILE PATH HANDLERS ---
def get_preferences_path(for_save=False):
    """
    Gets the preferences.json path.
    - When for_save=True: Always returns the path in get_writable_dir().
    - When for_save=False: Checks get_writable_dir() first; if not found, falls back to BASE_DIR.
    """
    writable_root = get_writable_dir()
    filepath = os.path.join(writable_root, "data.rot", "save", "config", "preferences.json")
    
    if for_save:
        return filepath
        
    if os.path.exists(filepath):
        return filepath
        
    fallback = os.path.join(BASE_DIR, "data.rot", "save", "config", "preferences.json")
    if os.path.exists(fallback):
        return fallback
        
    return filepath

def get_world_config_path(preset="world"):
    """Gets the world configuration path, allowing absolute paths for per-save configs."""
    if not preset:
        preset = "world"

    if os.path.exists(preset):
        return preset
    if os.path.exists(preset + ".json"):
        return preset + ".json"

    if preset.endswith(".json") or preset.endswith(".xml"):
        preset = os.path.splitext(preset)[0]

    writable_root = get_writable_dir()

    if preset == "sandbox":
        sandbox_candidates = [
            os.path.join(writable_root, "data.rot", "save", "config", "world.json"),
            os.path.join(BASE_DIR, "data.rot", "save", "config", "world.json")
        ]
        for path in sandbox_candidates:
            if os.path.exists(path):
                return path
        return os.path.join(DATA_PATH, "world.json")

    if preset != "world":
        custom_candidates = [
            os.path.join(writable_root, "data.rot", "save", "config", f"{preset}.json"),
            os.path.join(BASE_DIR, "data.rot", "save", "config", f"{preset}.json")
        ]
        for path in custom_candidates:
            if os.path.exists(path):
                return path

    lib_candidates = [
        os.path.join(get_writable_dir(), "data.rot", "save", "config", "world.json"),
        os.path.join(DATA_PATH, "world.json"),
        os.path.join(DATA_PATH, "config", "world.json"),
        os.path.join(BASE_DIR, "data.rot", "lib", "data", "world.json"),
        os.path.join(BASE_DIR, "data.rot", "lib", "data", "config", "world.json")
    ]
    for path in lib_candidates:
        if os.path.exists(path):
            return path

    return os.path.join(DATA_PATH, "world.json")

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
    global WEAPON_RANGED_DURABILITY_MULTIPLIER, CLOTH_DURABILITY_MULTIPLIER, TOOL_DURABILITY_MULTIPLIER
    global ITEM_SPAWN_CHANCE_MULTIPLIER
    global MAX_NPCS_GLOBAL, NPC_SPAWN_CHANCE, NPC_HEALTH_MULTIPLIER
    global NPC_DAMAGE_MULTIPLIER, NPC_SPEED_MULTIPLIER, NPC_DETECTION_RADIUS, NPC_STATIC_PERCENT, NPC_HOSTILE_PERCENT
    global MAX_VEH_CHUNK, VEH_HAS_FUEL, VEH_HAS_KEY, VEH_HAS_MOTOR, VEH_HAS_BATTERY, VEH_HAS_TIRES
    global NPC_MAX_CHUNK, NPCS_PER_SPAWN, NPC_RESPAWN, ZOMBIE_MAX_CHUNK, BASE_ZOMBIE_MAX_CHUNK
    global MAP_CHUNKS, CHUNK_SIZE, WORLD_SEED, SPAWN_LOBBY_CHUNK, SPAWN_MILITARY_CHUNK
    global GENERATE_IMAGES
    global UI_BACKGROUND_MUSIC, UI_SHOW_TUTORIAL_DEFAULT, RESOLUTION, WINDOW_MODE
    global UI_CRT_FILTER, CRT_FILTER
    global ANIMAL_MAX_CHUNK, ANIMALS_PER_SPAWN, ANIMAL_RESPAWN, ANIMAL_SPAWN_COUNT
    global VOLUME_MUSIC, VOLUME_BACKGROUND, VOLUME_ATMOSPHERIC, VOLUME_ANIMAL, VOLUME_NPC, VOLUME_ZOMBIE, VOLUME_PLAYER, VOLUME_VEHICLE, VOLUME_ITEMS, VOLUME_MAP
    global GAME_LANGUAGE 
    global PERMADEATH, ALL_VISIBLE, INFINITE_LIQUID, START_AT_THE_LOBBY
    global DISABLE_DISCOVER_ISLAND, NO_BOAT_TO_LOBBY

    # 1. LOAD PREFERENCES JSON
    pref_path = get_preferences_path()
    try:
        if os.path.exists(pref_path):
            with open(pref_path, "r", encoding="utf-8") as f:
                pref_data = json.load(f)
            root = pref_data.get("preferences", pref_data)

            ui_config = root.get('ui', {})
            if ui_config:
                if 'ui_background_music' in ui_config:
                    UI_BACKGROUND_MUSIC = bool(ui_config['ui_background_music'].get('value', True))
                if 'ui_show_tutorial_default' in ui_config:
                    UI_SHOW_TUTORIAL_DEFAULT = bool(ui_config['ui_show_tutorial_default'].get('value', False))
                if 'language' in ui_config:
                    GAME_LANGUAGE = str(ui_config['language'].get('value', 'en_US'))
                if 'window_mode' in ui_config:
                    WINDOW_MODE = str(ui_config['window_mode'].get('value', 'windowed'))

                val_crt = ui_config.get('ui_crt_filter') or ui_config.get('crt_filter')
                if val_crt is not None:
                    UI_CRT_FILTER = bool(val_crt.get('value', True))
                    CRT_FILTER = UI_CRT_FILTER

                val_res = ui_config.get('ui_resolution') or ui_config.get('resolution')
                if val_res is not None:
                    res_str = str(val_res.get('value', '1280x720'))
                    RESOLUTION = res_str
                    if 'x' in res_str.lower():
                        try:
                            rw, rh = map(int, res_str.lower().split('x'))
                            if rw >= 1280 and rh >= 720:
                                GAME_WIDTH = rw
                                GAME_HEIGHT = rh
                        except Exception:
                            pass

            audio_config = root.get('audio', {})
            if audio_config:
                for k, attr in [
                    ('volume_music', 'VOLUME_MUSIC'), ('volume_background', 'VOLUME_BACKGROUND'),
                    ('volume_atmospheric', 'VOLUME_ATMOSPHERIC'), ('volume_map', 'VOLUME_MAP'),
                    ('volume_items', 'VOLUME_ITEMS'), ('volume_vehicle', 'VOLUME_VEHICLE'),
                    ('volume_player', 'VOLUME_PLAYER'), ('volume_zombie', 'VOLUME_ZOMBIE'),
                    ('volume_npc', 'VOLUME_NPC'), ('volume_animal', 'VOLUME_ANIMAL')
                ]:
                    node = audio_config.get(k)
                    if node is not None and 'value' in node:
                        globals()[attr] = float(node['value'])

            player_pref = root.get('player', {})
            if player_pref:
                if 'zoom_start' in player_pref: START_ZOOM = float(player_pref['zoom_start'].get('value', 3.0))
                if 'zoom_far' in player_pref: FAR_ZOOM = float(player_pref['zoom_far'].get('value', 2.0))
                if 'zoom_near' in player_pref: NEAR_ZOOM = float(player_pref['zoom_near'].get('value', 3.5))
    except Exception as e:
        print(f"Error loading preferences: {e}")

    def _get_val(parent, tags, default):
        if not parent or not isinstance(parent, dict):
            return default
        if isinstance(tags, str):
            tags = [tags]
        for tag in tags:
            if tag in parent:
                node = parent[tag]
                if isinstance(node, dict) and 'value' in node:
                    return node['value']
                return node
        return default

    # 2. LOAD WORLD CONFIG JSON
    world_path = get_world_config_path(world_preset)
    try:
        if os.path.exists(world_path):
            with open(world_path, "r", encoding="utf-8") as f:
                world_raw = json.load(f)
            root = world_raw.get("world", world_raw)

            game_config = root.get('game', {})
            if game_config:
                TIME_TRANSITION_HR = float(_get_val(game_config, ['time_transition_hr', 'transition_hr'], 1.0))
                MAX_DARKNESS_OPACITY = int(_get_val(game_config, ['max_darkness_opacity', 'darkness_opacity'], 255))
                TIME_DAYLENGTH = int(_get_val(game_config, ['time_daylength', 'daylength', 'day_length'], 900000))
                TIME_SUNRISE_HR = float(_get_val(game_config, ['time_sunrise_hr', 'sunrise_hr'], 5.5))
                TIME_SUNSET_HR = float(_get_val(game_config, ['time_sunset_hr', 'sunset_hr'], 17.5))
                TIME_START_HR = float(_get_val(game_config, ['time_start_hr', 'start_hr'], 6.0))

                PERMADEATH = str(_get_val(game_config, ['permadeath'], False)).lower() == 'true'
                ALL_VISIBLE = str(_get_val(game_config, ['all_visible'], False)).lower() == 'true'
                INFINITE_LIQUID = str(_get_val(game_config, ['infinite_liquid'], True)).lower() == 'true'

                # Parse generate_lobby_chunk and generate_military_chunk
                lobby_gen_val = _get_val(game_config, ['generate_lobby_chunk', 'lobby_chunk', 'spawn_lobby_chunk'], True)
                SPAWN_LOBBY_CHUNK = str(lobby_gen_val).lower() == 'true'

                mil_gen_val = _get_val(game_config, ['generate_military_chunk', 'military_chunk', 'spawn_military_chunk'], True)
                SPAWN_MILITARY_CHUNK = str(mil_gen_val).lower() == 'true'

                # If generate_lobby_chunk is false, start_at_the_lobby is forced false
                if not SPAWN_LOBBY_CHUNK:
                    START_AT_THE_LOBBY = False
                    NO_BOAT_TO_LOBBY = True
                else:
                    START_AT_THE_LOBBY = str(_get_val(game_config, ['start_at_the_lobby', 'start_lobby'], True)).lower() == 'true'
                    NO_BOAT_TO_LOBBY = str(_get_val(game_config, ['no_boat_to_lobby'], False)).lower() == 'true'

                DISABLE_DISCOVER_ISLAND = str(_get_val(game_config, ['disable_discover_island'], False)).lower() == 'true'

            map_config = root.get('map', {})
            if map_config:
                MAP_CHUNKS = int(_get_val(map_config, ['map_chunks', 'chunks'], 3))
                CHUNK_SIZE = int(_get_val(map_config, ['chunk_size', 'size'], 128))
                WORLD_SEED = str(_get_val(map_config, ['seed', 'world_seed'], ''))
                gen_img_val = _get_val(map_config, ['generate_images', 'images'], False)
                GENERATE_IMAGES = str(gen_img_val).lower() == 'false'

            player_config = root.get('player', {})
            if player_config:
                PLAYER_SPEED = float(_get_val(player_config, ['player_speed', 'speed'], 1.7))
                BASE_PLAYER_VIEW_RADIUS = int(_get_val(player_config, ['view_radius', 'player_view_radius'], 6)) * TILE_SIZE
                AUTO_DRINK = str(_get_val(player_config, ['water_autodrink', 'autodrink'], True)).lower() == 'true'
                AUTO_DRINK_THRESHOLD = int(_get_val(player_config, ['water_threshold', 'autodrink_threshold'], 100))

            zombie_config = root.get('zombie', {})
            if zombie_config:
                ZOMBIE_WANDER_ENABLED = str(_get_val(zombie_config, ['wander', 'zombie_wander'], True)).lower() == 'true'
                ZOMBIES_PER_SPAWN = int(_get_val(zombie_config, ['spawn', 'spawns', 'zombies_per_spawn', 'spawn_count'], 3))
                ZOMBIE_RESPAWN = str(_get_val(zombie_config, ['respawn', 'zombie_respawn'], True)).lower() == 'true'
                ZOMBIE_MAX_CHUNK = int(_get_val(zombie_config, ['zombie_spawn_per_chunk', 'spawn_per_chunk', 'max_chunk', 'zombie_max_chunk'], 4))
                BASE_ZOMBIE_MAX_CHUNK = ZOMBIE_MAX_CHUNK
                ZOMBIE_INFECTION_CHANCE = float(_get_val(zombie_config, ['infection_chance', 'zombie_infection_chance'], 0.4))
                ZOMBIE_LINE_OF_SIGHT_CHECK = str(_get_val(zombie_config, ['sight_check', 'line_of_sight_check'], True)).lower() == 'true'
                ZOMBIE_SPEED = float(_get_val(zombie_config, ['zombie_speed', 'speed'], 0.3))
                ZOMBIE_DETECTION_RADIUS = int(_get_val(zombie_config, ['detection_radius', 'zombie_detection_radius'], 5)) * TILE_SIZE
                ZOMBIE_DROP = int(_get_val(zombie_config, ['drop', 'zombie_drop'], 1))
                MAX_ZOMBIES_GLOBAL = int(_get_val(zombie_config, ['max_zombies_global', 'max_global', 'max_zombies'], 500))
                ZOMBIE_WANDER_CHANGE_INTERVAL = int(_get_val(zombie_config, ['wander_change_interval', 'wander_interval'], 2000))

            spawning_config = root.get('item_spawning', {})
            if spawning_config:
                ITEM_SPAWN_CHANCE_MULTIPLIER = float(_get_val(spawning_config, ['item_spawn_chance_multiplier', 'spawn_chance_multiplier'], 0.8))

            npc_config = root.get('npc', {})
            if npc_config:
                MAX_NPCS_GLOBAL = int(_get_val(npc_config, ['max_npcs_global', 'max_global', 'max_npcs'], 1500))
                NPC_SPAWN_CHANCE = float(_get_val(npc_config, ['spawn_chance', 'npc_spawn_chance'], 1.0))
                NPC_HEALTH_MULTIPLIER = float(_get_val(npc_config, ['health_multiplier', 'npc_health_multiplier'], 1.0))
                NPC_DAMAGE_MULTIPLIER = float(_get_val(npc_config, ['damage_multiplier', 'npc_damage_multiplier'], 1.0))
                NPC_SPEED_MULTIPLIER = float(_get_val(npc_config, ['speed_multiplier', 'npc_speed_multiplier'], 1.0))
                NPC_DETECTION_RADIUS = int(_get_val(npc_config, ['detection_radius', 'npc_detection_radius'], 5)) * TILE_SIZE
                NPC_MAX_CHUNK = int(_get_val(npc_config, ['npc_spawn_per_chunk', 'spawn_per_chunk', 'max_chunk', 'npc_max_chunk'], 4))
                NPCS_PER_SPAWN = int(_get_val(npc_config, ['spawn', 'spawns', 'npcs_per_spawn', 'spawn_count'], 3))
                NPC_STATIC_PERCENT = float(_get_val(npc_config, ['static_percent', 'npc_static_percent'], 0.8))    
                NPC_HOSTILE_PERCENT = float(_get_val(npc_config, ['hostile_percent', 'npc_hostile_percent'], 0.2))
                NPC_RESPAWN = str(_get_val(npc_config, ['respawn', 'npc_respawn'], False)).lower() == 'true'

            vehicle_config = root.get('vehicle', {})
            if vehicle_config:
                MAX_VEH_CHUNK = int(_get_val(vehicle_config, ['vehicle_spawn_per_chunk', 'spawn_per_chunk', 'max_chunk', 'vehicle_max_chunk'], 6))
                VEH_HAS_FUEL = float(_get_val(vehicle_config, ['has_fuel_chance', 'fuel_chance'], 0.8))
                VEH_HAS_KEY = float(_get_val(vehicle_config, ['has_key_chance', 'key_chance'], 0.8))
                VEH_HAS_MOTOR = float(_get_val(vehicle_config, ['has_motor_chance', 'motor_chance'], 1.0))
                VEH_HAS_BATTERY = float(_get_val(vehicle_config, ['has_battery_chance', 'battery_chance'], 0.8))
                VEH_HAS_TIRES = float(_get_val(vehicle_config, ['has_tires_chance', 'tires_chance'], 1.0))

            animal_config = root.get('animal', {})
            if animal_config:
                ANIMAL_MAX_CHUNK = int(_get_val(animal_config, ['animal_spawn_per_chunk', 'spawn_per_chunk', 'max_chunk', 'animal_max_chunk', 'animal_spawn_count'], 8))
                ANIMAL_SPAWN_COUNT = ANIMAL_MAX_CHUNK
                ANIMALS_PER_SPAWN = int(_get_val(animal_config, ['spawn', 'spawns', 'animals_per_spawn', 'spawn_count'], 3))
                ANIMAL_RESPAWN = str(_get_val(animal_config, ['respawn', 'animal_respawn'], True)).lower() == 'true'

    except Exception as e:
        print(f"Error loading world from {world_path}: {e}")

    # Fonts
    if font_16 is None:
        font_16 = ImageFontWrapper(FONT_FACE, 16)
        font_14 = ImageFontWrapper(FONT_FACE, 8)
        font_12 = ImageFontWrapper(FONT_FACE, 12)

def save_language_to_config(lang_code):
    global GAME_LANGUAGE
    GAME_LANGUAGE = lang_code
    filepath = get_preferences_path(for_save=True)
    
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {}
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            read_path = get_preferences_path(for_save=False)
            if os.path.exists(read_path):
                with open(read_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

        if "preferences" not in data:
            data["preferences"] = {}
        if "ui" not in data["preferences"]:
            data["preferences"]["ui"] = {}
        if "language" not in data["preferences"]["ui"]:
            data["preferences"]["ui"]["language"] = {}

        data["preferences"]["ui"]["language"]["value"] = lang_code
        data["preferences"]["ui"]["language"]["name"] = "Language"
        data["preferences"]["ui"]["language"]["default"] = "en_US"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving language to preferences.json: {e}")


def apply_player_traits_config(player_or_traits):
    """
    Recalculates ZOMBIE_MAX_CHUNK by adding trait modifiers to BASE_ZOMBIE_MAX_CHUNK.
    Example: Base (4) + Runner (2) + Vaccine (5) = 11.
    """
    global ZOMBIE_MAX_CHUNK, BASE_ZOMBIE_MAX_CHUNK
    base = BASE_ZOMBIE_MAX_CHUNK

    traits = []
    if isinstance(player_or_traits, (list, tuple, set)):
        traits = list(player_or_traits)
    elif hasattr(player_or_traits, 'traits'):
        traits = list(player_or_traits.traits)

    bonus_zombies = 0
    from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS
    for trait_id in traits:
        t_def = TRAIT_DEFINITIONS.get(trait_id)
        if t_def and 'config_modifiers' in t_def:
            val = t_def['config_modifiers'].get('ZOMBIE_MAX_CHUNK')
            if val is not None:
                bonus_zombies += int(val)

    ZOMBIE_MAX_CHUNK = max(0, int(base + bonus_zombies))
    return ZOMBIE_MAX_CHUNK

version_file_path = VERSION_PATH
try:
    with open(version_file_path, "r") as f:
        GAME_VERSION = f.read().strip()
except Exception:
    GAME_VERSION = "0.0.6"

load_settings()