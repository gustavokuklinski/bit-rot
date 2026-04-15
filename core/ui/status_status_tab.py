# core/ui/status_status_tab.py

import pygame
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.data.localization import tr

class StatusTooltipItem:
    def __init__(self, name, text=None):
        self.name = name
        self.tooltip_text = text
        self.item_type = self.durability = self.defence = None
        self.load = self.capacity = self.min_damage = self.max_damage = self.ammo_type = None

def draw_status_tab(surface, player, modal, assets, zombies_killed):
    padding = 10
    col_width = (modal['rect'].width - (padding * 3)) // 2
    
    start_y = modal['rect'].y + 80
    col1_x = modal['rect'].x + padding
    col2_x = modal['rect'].x + col_width + (padding * 2)
    
    mouse_pos = pygame.mouse.get_pos()
    active_tooltip_item = None

    
    
    stat_icons = {}
    icon_files = {
        "HP": SPRITE_PATH + "ui/hp.png", "STM": SPRITE_PATH + "ui/stamina.png",
        "TIR": SPRITE_PATH + "ui/tireness.png", "WTR": SPRITE_PATH + "ui/water.png",
        "FOD": SPRITE_PATH + "ui/food.png", "INF": SPRITE_PATH + "ui/infection.png",
        "XP": SPRITE_PATH + "ui/xp.png", "ANX": SPRITE_PATH + "ui/axiety.png",
        "DEF": SPRITE_PATH + "ui/defence.png", "WGT": SPRITE_PATH + "ui/weight.png"
    }
    
    stat_names = {
        "HP": "Health", "STM": "Stamina", "TIR": "Tiredness", "WTR": "Water",
        "FOD": "Food", "INF": "Sickness", "ANX": "Anxiety", "DEF": "Defence", "WGT": "Weight"
    }

    for k, path in icon_files.items():
        try:
            img = pygame.image.load(path).convert_alpha()
            stat_icons[k] = pygame.transform.scale(img, (24, 24))
        except: stat_icons[k] = None

    stats = [
        ("HP", player.health, player.max_health, GRAY),
        ("STM", player.stamina, player.max_stamina, GRAY),
        ("TIR", player.tireness, 100, GRAY),
        ("WTR", player.water, 100, GRAY),
        ("FOD", player.food, 100, GRAY),
        ("INF", player.infection, 100, GRAY),
        ("ANX", player.anxiety, 100, GRAY),
        ("DEF", player.get_total_defence(), 100, GRAY), 
        ("WGT", player.current_weight, player.max_carry_weight, GRAY)
    ]
    
    for i, (name, value, max_value, color) in enumerate(stats):
        is_col2 = i >= 5
        x_col = col2_x if is_col2 else col1_x
        row_idx = i - 5 if is_col2 else i
        
        y_pos = start_y + (row_idx * 28)
        
        icon = stat_icons.get(name)
        if icon:
            surface.blit(icon, (x_col, y_pos))
            label_x = x_col + 28
        else:
            text = font_14.render(f"{name}:", True, WHITE)
            surface.blit(text, (x_col, y_pos))
            label_x = x_col + 40

        bar_x = label_x + 10
        ratio = value / max_value if max_value > 0 else 0
        draw_color = RED if name == "WGT" and ratio > 1.0 else color
            
        max_bar_width = int(col_width - 60)
        bar_width = int(max_bar_width * min(1.0, ratio))
        
        bar_rect = pygame.Rect(bar_x, y_pos + 5, bar_width, 10)
        border_rect = pygame.Rect(bar_x, y_pos + 5, max_bar_width, 10)
        
        pygame.draw.rect(surface, draw_color, bar_rect)
        pygame.draw.rect(surface, WHITE, border_rect, 1)

        if border_rect.collidepoint(mouse_pos):
             translated_name = tr('tooltip', stat_names.get(name, name))
             if name == "WGT": val_str = f"{value:.2f} / {max_value:.2f}"
             else: val_str = f"{int(value)}%"
             active_tooltip_item = StatusTooltipItem(f"{translated_name}: {val_str}")

    if active_tooltip_item:
        draw_tooltip(surface, active_tooltip_item, (mouse_pos[0], mouse_pos[1]))