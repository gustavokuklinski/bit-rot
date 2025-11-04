import pygame
from data.config import *

def draw_status_tab(surface, player, modal, assets, zombies_killed):
    y_offset = modal['rect'].y + 80
    x_offset = modal['rect'].x + 10

    name_text = font.render(f"{player.name}", True, WHITE)
    surface.blit(name_text, (x_offset, y_offset))
    y_offset += 20

    profession_text = font_small.render(f"Profession: {player.profession}", True, WHITE)
    surface.blit(profession_text, (x_offset, y_offset))
    y_offset += 20


    stat_icons = {}
    icon_files = {
        "HP": SPRITE_PATH + "ui/hp.png",
        "STM": SPRITE_PATH + "ui/stamina.png",
        "WTR": SPRITE_PATH + "ui/water.png",
        "FOD": SPRITE_PATH + "ui/food.png",
        "INF": SPRITE_PATH + "ui/infection.png",
        "XP": SPRITE_PATH + "ui/xp.png",
        "ANX": SPRITE_PATH + "ui/axiety.png",
        "TIR": SPRITE_PATH + "ui/tireness.png",
        "DEF": SPRITE_PATH + "ui/strength.png"
    }
    for k, path in icon_files.items():
        try:
            img = pygame.image.load(path).convert_alpha()
            stat_icons[k] = pygame.transform.scale(img, (24, 24))
        except Exception:
            stat_icons[k] = None

    stats = [
        ("HP", player.health, player.max_health, RED),
        ("STM", player.stamina, player.max_stamina, GRAY),
        ("WTR", player.water, 100, BLUE),
        ("FOD", player.food, 100, GREEN),
        ("INF", player.infection, 100, YELLOW),
        ("ANX", player.anxiety, 100, (150, 0, 150)),
        ("TIR", player.tireness, 100, (100, 100, 150)),
        ("DEF", player.get_total_defence(), 100, (160, 160, 160))
    ]
    for i, (name, value, max_value, color) in enumerate(stats):
        y_pos = y_offset + i * 28
        icon = stat_icons.get(name)
        if icon:
            surface.blit(icon, (x_offset, y_pos))
            label_x = x_offset + 28
        else:
            text = font.render(f"{name}:", True, WHITE)
            surface.blit(text, (x_offset, y_pos))
            label_x = x_offset + 110

        text = font_small.render(f"[{int(value)}%]", True, WHITE)
        surface.blit(text, (label_x, y_pos + 3))

        bar_x = label_x + 12
        bar_width = int(100 * (value / max_value))
        bar_rect = pygame.Rect(bar_x + 60, y_pos + 5, bar_width, 10)
        pygame.draw.rect(surface, color, bar_rect)
        pygame.draw.rect(surface, WHITE, (bar_x + 60, y_pos + 5, 100, 10), 1)

    y_pos = y_offset + len(stats) * 28

    try:
        if '_kills_img' not in globals() or _kills_img is None:
            _kills_img = pygame.image.load(f'{SPRITE_PATH}zombie/dead.png').convert_alpha()
            _kills_img = pygame.transform.scale(_kills_img, (24, 24))
    except Exception:
        _kills_img = None

    if _kills_img:
        surface.blit(_kills_img, (x_offset, y_pos + 35))
        num_text = font_small.render(f"{str(zombies_killed)} Killed", True, WHITE)
        surface.blit(num_text, (x_offset + _kills_img.get_width() + 10, y_pos + 35 + 6))
    else:
        zombies_killed_text = font_small.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
        surface.blit(zombies_killed_text, (x_offset, y_pos))
