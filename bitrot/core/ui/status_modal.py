# core/ui/status_modal.py

import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs
from core.ui.status_status_tab import draw_status_tab
from core.ui.status_health_tab import draw_health_tab
from core.ui.status_record_tab import draw_record_tab
from core.ui.status_quests_tab import draw_quests_tab 

def _player_has_mobile(player):
    """Recursively checks if the player has a Mobile phone."""
    if not player: return False
    def search_inv(inventory):
        if not inventory: return False
        for item in inventory:
            if item:
                if 'Mobile' in getattr(item, 'name', ''):
                    return True
                if hasattr(item, 'inventory') and search_inv(item.inventory):
                    return True
        return False

    if search_inv(player.inventory): return True
    if search_inv(player.belt): return True
    if search_inv(list(player.clothes.values())): return True
    return False

def _has_app(game, app_value):
    """Checks if the player has a mobile phone equipped with the specific SD card app."""
    if not game:
        return False
        
    # [FIX] If the player doesn't have a mobile phone, they don't have the app.
    if not _player_has_mobile(game.player):
        return False
        
    for slot in getattr(game, 'app_state', {}).get('slots', []):
        if slot:
            map_val = getattr(slot, 'map_value', None)
            if not map_val and hasattr(slot, 'properties') and isinstance(slot.properties, dict):
                map_val = slot.properties.get('map', {}).get('value')
            if map_val and map_val.strip().lower() == app_value:
                return True
    return False

def draw_status_modal(surface, player, modal, assets, zombies_killed, mouse_pos, game=None):
    base_modal = BaseModal(surface, modal, assets, "Player Status")
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    # 1. By default, the player can only access the Health/Overview tab
    tabs_data = [
        {'label': 'Health', 'icon_path': SPRITE_PATH + 'ui/hp.png'}
    ]

    # 2. If the Mobile has the Personal Data SD Card installed
    if _has_app(game, 'personal_data'):
        tabs_data.extend([
            {'label': 'Status', 'icon_path': SPRITE_PATH + 'ui/status.png'},
            {'label': 'Record', 'icon_path': SPRITE_PATH + 'ui/xp.png'}
        ])

    # 3. If the Mobile has the Open Jobs SD Card installed
    if _has_app(game, 'open_jobs'):
        tabs_data.append(
            {'label': 'Quests', 'icon_path': SPRITE_PATH + 'ui/quest.png'}
        )

    modal['tabs_data'] = tabs_data
    
    # 4. Fallback: If the user removes the SD Card (or drops the phone) while looking at an advanced tab, bounce them back to Health
    valid_labels = {t['label'] for t in tabs_data}
    if modal.get('active_tab') not in valid_labels:
        modal['active_tab'] = 'Health'

    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw(game, mouse_pos)

    if modal['active_tab'] == 'Status':
        draw_status_tab(surface, player, modal, assets, zombies_killed)
    elif modal['active_tab'] == 'Health':
        draw_health_tab(surface, player, modal, assets, game)
    elif modal['active_tab'] == 'Record':
        draw_record_tab(surface, player, modal, assets, mouse_pos)
    elif modal['active_tab'] == 'Quests': 
        draw_quests_tab(surface, player, modal, assets, mouse_pos)

    return close_button