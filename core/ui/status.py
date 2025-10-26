import pygame
from data.config import *
from core.ui.modals import BaseModal

def draw_record_tab(surface, player, modal, assets):
    y_offset = modal['rect'].y + 80
    x_offset = modal['rect'].x + 10

    skill_icons = {}
    icon_files = {
        "Strength": SPRITE_PATH + "ui/strength.png",
        "Fitness": SPRITE_PATH + "ui/fitness.png",
        "Melee": SPRITE_PATH + "ui/melee.png",
        "Ranged": SPRITE_PATH + "ui/range.png",
        "Lucky": SPRITE_PATH + "ui/lucky.png",
        "Speed": SPRITE_PATH + "ui/speed.png",
    }
    for k, path in icon_files.items():
        try:
            img = pygame.image.load(path).convert_alpha()
            skill_icons[k] = pygame.transform.scale(img, (24, 24))
        except Exception:
            skill_icons[k] = None

    skills = [
        ("Strength", player.progression.strength, 10, RED),
        ("Fitness", player.progression.fitness, 10, GREEN),
        ("Melee", player.progression.melee, 10, BLUE),
        ("Ranged", player.progression.ranged, 10, YELLOW),
        ("Lucky", player.progression.lucky, 10, WHITE),
        ("Speed", player.progression.speed, 10, GRAY),
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

def draw_status_modal(surface, player, modal, assets, zombies_killed):
    if 'active_tab' not in modal:
        modal['active_tab'] = 'Status'

    base_modal = BaseModal(surface, modal, assets, "Player Status")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return close_button, minimize_button

    # Add tabs
    status_tab_rect = pygame.Rect(base_modal.modal_x, base_modal.modal_y + base_modal.header_h, base_modal.modal_w / 2, 30)
    record_tab_rect = pygame.Rect(base_modal.modal_x + base_modal.modal_w / 2, base_modal.modal_y + base_modal.header_h, base_modal.modal_w / 2, 30)

    # Draw tabs
    pygame.draw.rect(surface, GRAY_60 if modal['active_tab'] == 'Status' else DARK_GRAY, status_tab_rect)
    pygame.draw.rect(surface, GRAY_60 if modal['active_tab'] == 'Record' else DARK_GRAY, record_tab_rect)
    pygame.draw.rect(surface, WHITE, status_tab_rect, 1)
    pygame.draw.rect(surface, WHITE, record_tab_rect, 1)

    status_text = font_small.render("Status", True, WHITE)
    record_text = font_small.render("Record", True, WHITE)
    surface.blit(status_text, (status_tab_rect.centerx - status_text.get_width() / 2, status_tab_rect.centery - status_text.get_height() / 2))
    surface.blit(record_text, (record_tab_rect.centerx - record_text.get_width() / 2, record_tab_rect.centery - record_text.get_height() / 2))

    # Handle tab switching
    if pygame.mouse.get_pressed()[0]:
        mouse_pos = pygame.mouse.get_pos()
        scaled_mouse_pos = (mouse_pos[0] * (VIRTUAL_SCREEN_WIDTH / surface.get_width()), mouse_pos[1] * (VIRTUAL_GAME_HEIGHT / surface.get_height()))
        if status_tab_rect.collidepoint(scaled_mouse_pos):
            modal['active_tab'] = 'Status'
        elif record_tab_rect.collidepoint(scaled_mouse_pos):
            modal['active_tab'] = 'Record'

    if modal['active_tab'] == 'Status':
        y_offset = base_modal.modal_y + base_modal.header_h + 40
        x_offset = base_modal.modal_x + 10

        name_text = font.render(f"{player.name}", True, WHITE)
        surface.blit(name_text, (x_offset, y_offset))
        y_offset += 20

        profession_text = font_small.render(f"Profession: {player.profession}", True, WHITE)
        surface.blit(profession_text, (x_offset, y_offset))
        y_offset += 20

        level_text = font_small.render(f"Level: {player.progression.level}", True, WHITE)
        surface.blit(level_text, (x_offset, y_offset))
        y_offset += 20

        stat_icons = {}
        icon_files = {
            "HP": SPRITE_PATH + "ui/hp.png",
            "Stamina": SPRITE_PATH + "ui/stamina.png",
            "Water": SPRITE_PATH + "ui/water.png",
            "Food": SPRITE_PATH + "ui/food.png",
            "Infection": SPRITE_PATH + "ui/infection.png",
            "XP": SPRITE_PATH + "ui/xp.png"
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
            ("XP", player.progression.experience, player.progression.xp_to_next_level, YELLOW)
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

            text = font_small.render(f"[{int(value)}/{max_value}]", True, WHITE)
            surface.blit(text, (label_x, y_pos + 3))

            bar_x = label_x + 12
            bar_width = int(100 * (value / max_value))
            bar_rect = pygame.Rect(bar_x + 60, y_pos + 5, bar_width, 10)
            pygame.draw.rect(surface, color, bar_rect)
            pygame.draw.rect(surface, WHITE, (bar_x + 60, y_pos + 5, 100, 10), 1)

        try:
            if '_kills_img' not in globals() or _kills_img is None:
                _kills_img = pygame.image.load('game/zombies/sprites/dead.png').convert_alpha()
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
    
    elif modal['active_tab'] == 'Record':
        draw_record_tab(surface, player, modal, assets)

    return close_button, minimize_button
