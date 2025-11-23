import pygame
from core.data.config import *

def draw_record_tab(surface, player, modal, assets, mouse_pos):
    y_offset = modal['rect'].y + 80
    x_offset = modal['rect'].x + 10

    skill_icons = {}
    icon_files = {
        "STR": SPRITE_PATH + "ui/strength.png",
        "FIT": SPRITE_PATH + "ui/fitness.png",
        "MLE": SPRITE_PATH + "ui/melee.png",
        "RNG": SPRITE_PATH + "ui/range.png",
        "LCK": SPRITE_PATH + "ui/lucky.png",
        "SPD": SPRITE_PATH + "ui/speed.png",
    }
    for k, path in icon_files.items():
        try:
            img = pygame.image.load(path).convert_alpha()
            skill_icons[k] = pygame.transform.scale(img, (24, 24))
        except Exception:
            skill_icons[k] = None

    skills = [
        ("STR", player.progression.strength, RED),
        ("FIT", player.progression.fitness, GREEN),
        ("MLE", player.progression.melee, BLUE),
        ("RNG", player.progression.ranged, YELLOW),
        ("LCK", player.progression.lucky, WHITE),
        ("SPD", player.progression.speed, GRAY),
    ]

    attr_name_map = {
        "STR": "strength",
        "FIT": "fitness",
        "MLE": "melee",
        "RNG": "ranged",
        "LCK": "lucky",
        "SPD": "speed",
    }

    line_height = 38 # Was 28

    for i, (name, attr_data, color) in enumerate(skills):
        y_pos = y_offset + i * line_height # Use new line height
        
        icon = skill_icons.get(name)
        if icon:
            surface.blit(icon, (x_offset, y_pos)) # Y-pos is top of the slot
            label_x = x_offset + 28
        else:
            text = font.render(f"{name}:", True, WHITE) # Fallback text
            surface.blit(text, (x_offset, y_pos))
            label_x = x_offset + 110 # Should not happen if icons are correct

        # --- Bonus Percentage (Calculated first, drawn later) ---
        bonus_perc = 0.0
        attr_key = attr_name_map.get(name) # Get "lucky" from "LCK"
        if attr_key:
            bonus_perc = player.progression.get_item_attribute_bonus(player, attr_key)
            
        # --- Layout Logic ---
        top_line_y = y_pos
        bottom_line_y = y_pos + 18 # 18px down from the top line

        bonus_x_pos = 0 # Will be set below

        if isinstance(attr_data, dict): # Leveled attribute (STR, FIT, etc.)
            level = attr_data['level']
            xp = attr_data['xp']
            xp_to_next = attr_data['xp_to_next_level']
            
            # 1. Draw Text: "Strength | Level: 0 | XP: 0 / 100"
            text_str = f"Level: {int(level)} | XP: {int(xp)} / {int(xp_to_next)}"
            text_surf = font_notification.render(text_str, True, WHITE)
            surface.blit(text_surf, (label_x, top_line_y))

            # 2. Draw Bar
            bar_x = label_x
            # Bar width calculation to leave space for bonus
            bar_width_total = modal['rect'].width - (label_x - modal['rect'].x) - 55 
            
            full_bar_rect = pygame.Rect(bar_x, bottom_line_y, bar_width_total, 10)
            
            bar_width = int(bar_width_total * (xp / xp_to_next)) if xp_to_next > 0 else 0
            bar_rect = pygame.Rect(bar_x, bottom_line_y, bar_width, 10)
            
            pygame.draw.rect(surface, color, bar_rect)
            pygame.draw.rect(surface, WHITE, full_bar_rect, 1) # Border

            # 3. Set bonus text X pos (to the right of the bar)
            bonus_x_pos = full_bar_rect.right + 8
            

        else: # Static attribute (LCK, SPD)
            value = attr_data
            
            # 1. Draw Text: "Lucky | Level: 0"
            text_str = f"Level: {int(value)}"
            text_surf = font_notification.render(text_str, True, WHITE)
            surface.blit(text_surf, (label_x, top_line_y))
            
            # 2. Draw "Passive skill" text
            passive_surf = font_notification.render("Passive skill", True, GRAY)
            surface.blit(passive_surf, (label_x, bottom_line_y))
            
            # 3. Set bonus text X pos (to the right of the level text)
            bonus_x_pos = label_x + text_surf.get_width() + 15

        # --- Bonus Text Drawing ---
        if bonus_perc != 0:
            bonus_str = f"+{bonus_perc:.1f}%"
            bonus_color = (100, 255, 100) # Green
            if bonus_perc < 0:
                bonus_str = f"{bonus_perc:.1f}%" # Will include minus sign
                bonus_color = (255, 100, 100) # Red
            
            bonus_surf = font_notification.render(bonus_str, True, bonus_color)
            # Draw it aligned with the *top* text line
            surface.blit(bonus_surf, (bonus_x_pos, top_line_y)) 
            
