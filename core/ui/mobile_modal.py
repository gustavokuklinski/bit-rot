import pygame
from data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs
from core.ui.clock_tab import draw_clock_tab
from core.ui.map_tab import draw_map_tab

def draw_mobile_modal(surface, game, modal, assets):
    base_modal = BaseModal(surface, modal, assets, "Mobile")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return close_button, minimize_button

    # --- Tabs ---
    tabs_data = [
        {'label': 'Clock', 'icon_path': SPRITE_PATH + 'ui/clock.png'}, # Add icon paths if you have them
        {'label': 'Map', 'icon_path':  SPRITE_PATH + 'ui/map.png'},
    ]
    modal['tabs_data'] = tabs_data

    # Ensure active_tab is set correctly
    if 'active_tab' not in modal or modal['active_tab'] not in {t['label'] for t in tabs_data}:
        modal['active_tab'] = 'Clock' # Default to Clock

    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw() # Draws tabs below the header

    # --- Draw Tab Content ---
    if modal['active_tab'] == 'Clock':
        draw_clock_tab(surface, game, modal, assets)
    elif modal['active_tab'] == 'Map':
        draw_map_tab(surface, game, modal, assets)
    
    return close_button, minimize_button