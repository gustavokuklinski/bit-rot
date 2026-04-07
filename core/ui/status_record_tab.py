import pygame
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.data.localization import tr

_SKILL_ICON_CACHE = {}

def draw_record_tab(surface, player, modal, assets, mouse_pos):
    modal_rect = modal['rect']

    attributes_to_draw = [
        ("Strength", "strength"), ("Fitness", "fitness"),
        ("Agility", "agility"), ("Luck", "lucky"),
        ("Melee", "melee"), ("Ranged", "ranged"),
        ("Maintenance", "maintenance"), ("Intelligence", "intelligence")
    ]

    start_x_1 = modal_rect.left + 15
    start_x_2 = modal_rect.left + modal_rect.width // 2 + 5
    start_y = modal_rect.top + 75
    line_height = 30
    
    pending_tooltip = None

    for i, (label, attr_id) in enumerate(attributes_to_draw):
        is_col2 = i >= 4
        current_x = start_x_2 if is_col2 else start_x_1
        row_idx = i - 4 if is_col2 else i
        current_y = start_y + (row_idx * line_height)
        
        if hasattr(player.progression, "get_level"):
            level = player.progression.get_level(attr_id)
        else:
            level = player.progression.attributes.get(attr_id, {}).get("level", 0)

        attr_config = player.progression.config.attributes.get(attr_id, {})
        image_rel_path = attr_config.get('image')
        
        icon_size = 24
        icon_x = current_x
        
        if image_rel_path:
            if image_rel_path not in _SKILL_ICON_CACHE:
                try:
                    full_path = SPRITE_PATH + image_rel_path
                    img = pygame.image.load(full_path).convert_alpha()
                    img = pygame.transform.scale(img, (icon_size, icon_size))
                    _SKILL_ICON_CACHE[image_rel_path] = img
                except: _SKILL_ICON_CACHE[image_rel_path] = None

            icon_surf = _SKILL_ICON_CACHE.get(image_rel_path)
            if icon_surf:
                surface.blit(icon_surf, (icon_x - 5, current_y - 3))

        bonus_perc = player.progression.get_total_attribute_bonus(player, attr_id)
        bonus_color = (100, 255, 100) if bonus_perc > 0 else (255, 100, 100)
        
        text_x = icon_x + icon_size + 10
        label_surf = font_14.render(f"{tr('ui', label)}:", True, WHITE)
        surface.blit(label_surf, (text_x - 3, current_y + 2))

        if bonus_perc != 0:
            bonus_surf = font_14.render(f"[{int(bonus_perc):+}%]", True, bonus_color)
            surface.blit(bonus_surf, (text_x + label_surf.get_width() + 5, current_y + 2))

        # Adjusted horizontal position to fit the 50% column constraint nicely
        value_x = text_x + 95 
        value_surf = font_14.render(f"{str(level)}/10", True, WHITE)
        value_pos = (value_x, current_y + 2)
        surface.blit(value_surf, value_pos)

        value_rect = pygame.Rect(value_pos[0], value_pos[1], value_surf.get_width(), value_surf.get_height())

        if hasattr(player.progression, "attributes"):
            attr_data = player.progression.attributes.get(attr_id)
            if attr_data:
                curr_xp = float(attr_data.get('xp', 0))
                req_xp = int(attr_data.get('xp_to_next_level', 100))
                
                if value_rect.collidepoint(mouse_pos):
                    pending_tooltip = {
                        "label": label, "curr_xp": int(curr_xp), "req_xp": req_xp
                    }

    if pending_tooltip:
        class XPTooltip:
            def __init__(self, data):
                self.name = f"{tr('ui', data['label'])} {tr('ui', 'Experience')}"
                self.tooltip_text = f"{tr('ui', 'Progress:')} {data['curr_xp']} / {data['req_xp']} XP"
                self.item_type = self.durability = self.max_durability = None
                self.load = self.capacity = self.min_damage = self.max_damage = self.ammo_type = self.defence = None
        draw_tooltip(surface, XPTooltip(pending_tooltip), (mouse_pos[0], mouse_pos[1]))