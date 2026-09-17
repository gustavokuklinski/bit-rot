# core/ui/status_record_tab.py

import pygame
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.data.localization import tr
from core.entities.item.item_helpers import get_sd_card_attr_info

_SKILL_ICON_CACHE = {}

def draw_record_tab(surface, player, modal, assets, mouse_pos):
    modal_rect = modal['rect']

    attribute_ids = [
        "strength", "fitness", "agility",
        "lucky", "melee", "ranged",
        "maintenance", "intelligence"
    ]

    start_x = modal_rect.left + 15
    start_y = modal_rect.top + 75
    line_height = 30
    
    pending_tooltip = None

    for i, attr_id in enumerate(attribute_ids):
        current_y = start_y + (i * line_height)
        
        attr_data = player.progression.attributes.get(attr_id, {})
        level = attr_data.get('level', 0)
        curr_xp = float(attr_data.get('xp', 0))
        req_xp = int(attr_data.get('xp_to_next_level', 100))

        # Check live SD card boosts
        boost_info = get_sd_card_attr_info(player, attr_id)
        level_boost = boost_info.get('level_boost', 0)
        is_boosted = level_boost > 0 or boost_info.get('xp_boost', 0) > 0 or boost_info.get('passive_amount', 0) > 0

        attr_config = player.progression.config.attributes.get(attr_id, {})
        image_rel_path = attr_config.get('image')
        label = attr_config.get('name', attr_id.capitalize())
        
        icon_size = 24
        if image_rel_path:
            if image_rel_path not in _SKILL_ICON_CACHE:
                try:
                    full_path = SPRITE_PATH + image_rel_path
                    img = pygame.image.load(full_path).convert_alpha()
                    img = pygame.transform.scale(img, (icon_size, icon_size))
                    _SKILL_ICON_CACHE[image_rel_path] = img
                except Exception:
                    _SKILL_ICON_CACHE[image_rel_path] = None

            icon_surf = _SKILL_ICON_CACHE.get(image_rel_path)
            if icon_surf:
                surface.blit(icon_surf, (start_x - 5, current_y - 3))

        text_x = start_x + icon_size + 10
        label_surf = font_12.render(f"{tr('ui', label)}:", False, WHITE)
        surface.blit(label_surf, (text_x - 3, current_y + 2))

        # --- LIVE LEVEL NUMBER: Highlight Green if Boosted ---
        value_x = text_x + 145
        if level_boost > 0:
            value_str = f"{level}/10 (+{level_boost})"
            value_col = (100, 255, 100)  # Vibrant Green
        elif is_boosted:
            value_str = f"{level}/10"
            value_col = (100, 255, 100)  # Vibrant Green
        else:
            value_str = f"{level}/10"
            value_col = WHITE

        value_surf = font_12.render(value_str, False, value_col)
        surface.blit(value_surf, (value_x, current_y + 2))

        # Entire row is hoverable
        row_rect = pygame.Rect(start_x, current_y, modal_rect.width - 30, line_height)
        if row_rect.collidepoint(mouse_pos):
            pending_tooltip = {
                "label": label, 
                "curr_xp": int(curr_xp), 
                "req_xp": req_xp,
                "boost_info": boost_info
            }

    if pending_tooltip:
        class RecordTooltip:
            def __init__(self, data):
                self.name = f"{tr('ui', data['label'])} {tr('ui', 'Experience')}"
                
                # Default white progress line
                self.tooltip_lines = [
                    f"{tr('ui', 'Progress:')} {data['curr_xp']} / {data['req_xp']} XP"
                ]

                b = data.get('boost_info', {})
                # Level Boost in GREEN
                if b.get('level_boost', 0) > 0:
                    self.tooltip_lines.append([
                        (f"{tr('ui', 'Card Boost:')} +{b['level_boost']} Level", (100, 255, 100))
                    ])

                # XP % Multiplier in GREEN
                if b.get('xp_boost', 0) > 0:
                    self.tooltip_lines.append([
                        (f"{tr('ui', 'Card XP Boost:')} +{int(b['xp_boost'])}%", (100, 255, 100))
                    ])

                # Live learning interval counter in GREEN
                if b.get('passive_amount', 0) > 0:
                    self.tooltip_lines.append([
                        (f"{tr('ui', 'Live Learning:')} +{b['passive_amount']} XP / {b['passive_interval']}s", (100, 255, 100))
                    ])

                self.item_type = self.durability = self.max_durability = None
                self.load = self.capacity = self.min_damage = self.max_damage = self.ammo_type = self.defence = None

        draw_tooltip(surface, RecordTooltip(pending_tooltip), (mouse_pos[0], mouse_pos[1]))