# editor/config.py
import os

# Screen dimensions
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

# Map default size
MAP_DEFAULT_WIDTH = 100
MAP_DEFAULT_HEIGHT = 100

# UI Dimensions
TAB_BAR_HEIGHT = 30
TOOLBAR_HEIGHT = 40
LOG_WINDOW_HEIGHT = 150

# Tile size
TILE_SIZE = 32
ICON_SIZE = 30

# Sidebar width
SIDEBAR_WIDTH = 300
FILE_TREE_WIDTH = 300

# Zoom levels
ZOOM_LEVELS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
INITIAL_ZOOM_INDEX = 5

# ----------------------------------------------------------------------
# PATHS - ABSOLUTE AND GLOBAL
# ----------------------------------------------------------------------
# _CONFIG_DIR: .../bit-rot/bitrot/editor
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))          
# PROJECT_ROOT: .../bit-rot/
PROJECT_ROOT = os.path.dirname(os.path.dirname(_CONFIG_DIR))      

# GAME_ROOT: .../bit-rot/bitrot/data.rot/
GAME_ROOT = os.path.join(PROJECT_ROOT, 'bitrot', 'data.rot')

# Asset sub-folders
MAP_DIR = os.path.join(GAME_ROOT, 'lib', 'map')
BUILDINGS_DIR = os.path.join(GAME_ROOT, 'lib', 'map', 'buildings')
XML_DATA_ROOT = os.path.join(GAME_ROOT, 'lib', 'data')
SPRITE_ROOT = os.path.join(GAME_ROOT, 'lib', 'sprites')

# Code Editor roots
CODE_GLOBAL_ROOT = os.path.join(PROJECT_ROOT, 'data.rot')
CODE_LOCAL_ROOT = GAME_ROOT

# Preview settings
BUILDING_PREVIEW_SIZE = (200, 150)