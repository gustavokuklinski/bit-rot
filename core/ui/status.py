import pygame
from data.config import *
from core.ui.modals import BaseModal

def draw_status_modal(surface, player, modal, assets, zombies_killed):
    base_modal = BaseModal(surface, modal, assets, "Player Status")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return close_button, minimize_button

    y_offset = base_modal.modal_y + base_modal.header_h + 10
    x_offset = base_modal.modal_x + 10

    level_text = font.render(f"Level: {player.level}", True, WHITE)
    surface.blit(level_text, (x_offset, y_offset))
    y_offset += 20

    stat_icons = {}
    icon_files = {
        "HP": "game/ui/sprites/hp.png",
        "Stamina": "game/ui/sprites/stamina.png",
        "Water": "game/ui/sprites/water.png",
        "Food": "game/ui/sprites/food.png",
        "Infection": "game/ui/sprites/infection.png",
        "XP": "game/ui/sprites/xp.png"
    }
    for k, path in icon_files.items():
        try:
            img = pygame.image.load(path).convert_alpha()
            stat_icons[k] = pygame.transform.scale(img, (24, 24))
        except Exception:
            stat_icons[k] = None

    stats = [
        ("HP", player.health, player.max_health, RED),
        ("Stamina", player.stamina, player.max_stamina, GRAY),
        ("Water", player.water, 100, BLUE),
        ("Food", player.food, 100, GREEN),
        ("Infection", player.infection, 100, YELLOW),
        ("XP", player.experience, player.xp_to_next_level, YELLOW)
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

        bar_x = label_x + 12
        bar_width = int(100 * (value / max_value))
        bar_rect = pygame.Rect(bar_x, y_pos + 5, bar_width, 10)
        pygame.draw.rect(surface, color, bar_rect)
        pygame.draw.rect(surface, WHITE, (bar_x, y_pos + 5, 100, 10), 1)

    try:
        if '_kills_img' not in globals() or _kills_img is None:
            _kills_img = pygame.image.load('game/zombies/sprites/dead.png').convert_alpha()
            _kills_img = pygame.transform.scale(_kills_img, (24, 24))
    except Exception:
        _kills_img = None

    if _kills_img:
        surface.blit(_kills_img, (x_offset, y_pos + 35))
        num_text = font.render(f"{str(zombies_killed)} Killed", True, WHITE)
        surface.blit(num_text, (x_offset + _kills_img.get_width() + 16, y_pos + 35 + 6))
    else:
        zombies_killed_text = font.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
        surface.blit(zombies_killed_text, (x_offset, y_pos))
    
    return close_button, minimize_button
