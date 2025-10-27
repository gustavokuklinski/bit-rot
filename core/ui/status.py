import pygame
from data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs
from core.ui.status_tab import draw_status_tab
from core.ui.record_tab import draw_record_tab

def draw_status_modal(surface, player, modal, assets, zombies_killed):
    base_modal = BaseModal(surface, modal, assets, "Player Status")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return close_button, minimize_button

    tabs_data = [
        {'label': 'Status', 'icon_path': SPRITE_PATH + 'ui/status.png'},
        {'label': 'Record', 'icon_path': SPRITE_PATH + 'ui/xp.png'}
    ]

    modal['tabs_data'] = tabs_data
    tabs = Tabs(surface, modal, tabs_data, assets)
    # modal['tabs_instance'] = tabs # Store the instance
    tabs.draw()

    if modal['active_tab'] == 'Status':
        draw_status_tab(surface, player, modal, assets, zombies_killed)
    
    elif modal['active_tab'] == 'Record':
        draw_record_tab(surface, player, modal, assets)

    return close_button, minimize_button
