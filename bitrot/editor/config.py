import os
import json

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

MAP_DEFAULT_WIDTH = 100
MAP_DEFAULT_HEIGHT = 100

TAB_BAR_HEIGHT = 40
TOOLBAR_HEIGHT = 45
LOG_WINDOW_HEIGHT = 150

TILE_SIZE = 32
ICON_SIZE = 30

SIDEBAR_WIDTH = 300
FILE_TREE_WIDTH = 300

ZOOM_LEVELS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
INITIAL_ZOOM_INDEX = 5

_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))          
PROJECT_ROOT = os.path.dirname(os.path.dirname(_CONFIG_DIR))      

GAME_ROOT = os.path.join(PROJECT_ROOT, 'bitrot', 'data.rot')

ACTIVE_MOD = "Vanilla"

def get_mod_search_dirs():
    """Returns candidate mod directories without creating them."""
    candidates = [
        os.path.join(PROJECT_ROOT, 'bitrot', 'data.rot', 'mods'),
        os.path.join(PROJECT_ROOT, 'bitrot', 'data.rot', 'mod'),
        os.path.join(PROJECT_ROOT, 'data.rot', 'mods'),
        os.path.join(PROJECT_ROOT, 'data.rot', 'mod'),
        os.path.join(GAME_ROOT, 'mods'),
        os.path.join(GAME_ROOT, 'mod')
    ]
    seen = set()
    unique_dirs = []
    for c in candidates:
        norm = os.path.normpath(os.path.abspath(c))
        if norm not in seen:
            seen.add(norm)
            unique_dirs.append(norm)
    return unique_dirs

def get_available_mods():
    """Discovers all installed mods across candidate directories without creating folders."""
    mods = {}
    for base_dir in get_mod_search_dirs():
        if os.path.exists(base_dir) and os.path.isdir(base_dir):
            try:
                for entry in sorted(os.listdir(base_dir)):
                    full_p = os.path.join(base_dir, entry)
                    if os.path.isdir(full_p) and entry not in mods:
                        mods[entry] = full_p
            except OSError:
                pass
    return mods

def get_mod_descriptor(mod_name):
    """Finds and parses the mod descriptor JSON if present."""
    if not mod_name or mod_name == "Vanilla":
        return None
    mods = get_available_mods()
    mod_path = mods.get(mod_name)
    if not mod_path or not os.path.isdir(mod_path):
        return None

    # Check common metadata names
    for fname in ["mod.json", "info.json", "metadata.json"]:
        p = os.path.join(mod_path, fname)
        if os.path.isfile(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass

    # Check any root JSON containing 'editor_config' or 'name'
    for f in os.listdir(mod_path):
        if f.endswith('.json'):
            p = os.path.join(mod_path, f)
            try:
                with open(p, 'r', encoding='utf-8') as jf:
                    data = json.load(jf)
                if isinstance(data, dict) and ("editor_config" in data or "name" in data):
                    return data
            except Exception:
                pass
    return None

def get_active_content_root(mod_name=None):
    """Returns content root for Vanilla (lib) or selected Mod folder."""
    target = mod_name if mod_name is not None else ACTIVE_MOD
    if not target or target == "Vanilla":
        return os.path.join(GAME_ROOT, 'lib')
    mods = get_available_mods()
    if target in mods:
        return mods[target]
    return os.path.join(GAME_ROOT, 'mods', target)

def get_data_dir(sub=""):
    return os.path.join(get_active_content_root(), 'data', sub) if sub else os.path.join(get_active_content_root(), 'data')

def get_map_dir(sub=""):
    return os.path.join(get_active_content_root(), 'map', sub) if sub else os.path.join(get_active_content_root(), 'map')

def get_sprites_dir(sub=""):
    return os.path.join(get_active_content_root(), 'sprites', sub) if sub else os.path.join(get_active_content_root(), 'sprites')

LIB_ROOT = os.path.join(GAME_ROOT, 'lib')
MAP_DIR = os.path.join(LIB_ROOT, 'map')
BUILDINGS_DIR = os.path.join(LIB_ROOT, 'map', 'buildings')
XML_DATA_ROOT = os.path.join(LIB_ROOT, 'data')
SPRITE_ROOT = os.path.join(LIB_ROOT, 'sprites')
MODS_DIR = os.path.join(GAME_ROOT, 'mods')

CODE_GLOBAL_ROOT = os.path.join(PROJECT_ROOT, 'data.rot')
CODE_LOCAL_ROOT = GAME_ROOT

BUILDING_PREVIEW_SIZE = (200, 150)