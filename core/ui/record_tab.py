import pygame
from data.config import *

def draw_record_tab(surface, player, modal, assets):
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
        ("STR", player.progression.strength, 10, RED),
        ("FIT", player.progression.fitness, 10, GREEN),
        ("MLE", player.progression.melee, 10, BLUE),
        ("RNG", player.progression.ranged, 10, YELLOW),
        ("LCK", player.progression.lucky, 10, WHITE),
        ("SPD", player.progression.speed, 10, GRAY),
    ]

    for i, (name, value, max_value, color) in enumerate(skills):
        y_pos = y_offset + i * 28
        
        icon = skill_icons.get(name)
        if icon:
            surface.blit(icon, (x_offset, y_pos))
            label_x = x_offset + 28
        else:
            text = font.render(f"{name}:", True, WHITE)
            surface.blit(text, (x_offset, y_pos))
            label_x = x_offset + 110

        text = font_small.render(f"[{int(value)}/{max_value}]", True, WHITE)
        surface.blit(text, (label_x, y_pos + 3))

        bar_x = label_x + 60
        bar_width = int(100 * (value / max_value))
        bar_rect = pygame.Rect(bar_x, y_pos + 5, bar_width, 20)
        pygame.draw.rect(surface, color, bar_rect)
        pygame.draw.rect(surface, WHITE, (bar_x, y_pos + 5, 100, 10), 1)
