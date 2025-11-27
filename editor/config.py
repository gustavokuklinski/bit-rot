# editor/config.py

import os

# Screen dimensions
SCREEN_WIDTH = 1480
SCREEN_HEIGHT = 820

# Map default size
MAP_DEFAULT_WIDTH = 100
MAP_DEFAULT_HEIGHT = 100

# UI Dimensions
TAB_BAR_HEIGHT = 30   # New top bar for switching modes
TOOLBAR_HEIGHT = 40

# Toolbar height
TOOLBAR_HEIGHT = 40

# Tile size
TILE_SIZE = 32
ICON_SIZE = 30

# Sidebar width (for tiles)
SIDEBAR_WIDTH = 300

# File tree width (new sidebar on the left)
FILE_TREE_WIDTH = 300

# Zoom levels
ZOOM_LEVELS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
INITIAL_ZOOM_INDEX = 5 # Corresponds to 1.0

# Paths
GAME_ROOT = os.path.abspath(os.path.join('./game'))
MAP_DIR = os.path.join(GAME_ROOT, 'lib', 'map')
BUILDINGS_DIR = os.path.join(GAME_ROOT, 'lib','map', 'buildings')

# Preview settings
BUILDING_PREVIEW_SIZE = (200, 150)