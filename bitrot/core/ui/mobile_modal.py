# In core/ui/mobile_modal.py:
import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs
from core.ui.mobile_clock_tab import draw_clock_tab
from core.ui.mobile_map_tab import draw_map_tab
from core.ui.mobile_apps_tab import draw_apps_tab
from core.ui.mobile_radio_tab import draw_radio_tab

def draw_mobile_modal(surface, game, modal, assets):
    try:
        day_progress = game.world_time.game_time_ms / game.world_time.day_length_ms
        total_minutes_in_day = int(day_progress * 24 * 60)
        hour = (total_minutes_in_day // 60) % 24
        raw_minute = total_minutes_in_day % 60
        minute = raw_minute - (raw_minute % 10)
        time_str = f"{hour:02d}:{minute:02d}"
    except:
        time_str = "00:00"

    title = f"Mobile {time_str}"

    tabs_data = [
        {'label': 'Clock', 'icon_path': SPRITE_PATH + 'ui/clock.png'},
        {'label': 'Map', 'icon_path':  SPRITE_PATH + 'ui/map.png'},
        {'label': 'Apps', 'icon_path':  SPRITE_PATH + 'ui/mp3.png'},
        {'label': 'Radio', 'icon_path': SPRITE_PATH + 'ui/mp3.png'},
    ]
    modal['tabs_data'] = tabs_data

    if 'active_tab' not in modal or modal['active_tab'] not in {t['label'] for t in tabs_data}:
        modal['active_tab'] = 'Clock'

    base_modal = BaseModal(surface, modal, assets, title)
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw()

    if modal['active_tab'] == 'Clock':
        draw_clock_tab(surface, game, modal, assets)
    elif modal['active_tab'] == 'Map':
        draw_map_tab(surface, game, modal, assets)
    elif modal['active_tab'] == 'Apps':
        draw_apps_tab(surface, game, modal, assets)
    elif modal['active_tab'] == 'Radio':
        draw_radio_tab(surface, game, modal, assets)

    return [close_button]