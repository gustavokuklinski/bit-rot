# core/ui/status_tab.py

import pygame
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.data.localization import tr

class StatusTooltipItem:
    """Helper class to mock an item for the generic tooltip system."""
    def __init__(self, name, text=None):
        self.name = name
        self.tooltip_text = text
        
        # Attributes required by draw_tooltip to avoid KeyErrors/AttributeErrors
        # These are accessed directly in tooltip.py, not via hasattr()
        self.item_type = None
        self.durability = None
        self.defence = None
        self.load = None
        self.capacity = None
        self.min_damage = None
        self.max_damage = None
        self.ammo_type = None
        # Other attributes (weight, effects, etc.) are checked with hasattr, 
        # so we don't need to define them here.

def draw_status_tab(surface, player, modal, assets, zombies_killed):
    # Define Column Regions
    padding = 10
    col_width = (modal['rect'].width - (padding * 3)) // 2
    
    start_y = modal['rect'].y + 75
    col1_x = modal['rect'].x + padding
    # col2_x = modal['rect'].x + col_width + (padding * 2) # Not used in simplified status tab
    
    mouse_pos = pygame.mouse.get_pos()
    active_tooltip_item = None # Store the item to draw tooltip for

    # --- Column 1: General Stats ---
    
    # 1. Header
    name_text = font.render(tr('ui', "Condition"), True, WHITE)
    surface.blit(name_text, (col1_x, start_y))
    
    y_offset = start_y + 30
    
    # 2. General Stats Icons
    stat_icons = {}
    icon_files = {
        "HP": SPRITE_PATH + "ui/hp.png",
        "STM": SPRITE_PATH + "ui/stamina.png",
        "TIR": SPRITE_PATH + "ui/tireness.png",
        "WTR": SPRITE_PATH + "ui/water.png",
        "FOD": SPRITE_PATH + "ui/food.png",
        "INF": SPRITE_PATH + "ui/infection.png",
        "XP": SPRITE_PATH + "ui/xp.png",
        "ANX": SPRITE_PATH + "ui/axiety.png",
        "DEF": SPRITE_PATH + "ui/defence.png",
        "WGT": SPRITE_PATH + "ui/weight.png"
    }
    
    # Full names mapping for tooltip
    stat_names = {
        "HP": "Health",
        "STM": "Stamina",
        "TIR": "Tiredness",
        "WTR": "Water",
        "FOD": "Food",
        "INF": "Sickness or Infection",
        "ANX": "Anxiety",
        "DEF": "Defence",
        "WGT": "Weight"
    }

    for k, path in icon_files.items():
        try:
            img = pygame.image.load(path).convert_alpha()
            stat_icons[k] = pygame.transform.scale(img, (24, 24))
        except Exception:
            stat_icons[k] = None

    stats = [
        ("HP", player.health, player.max_health, GRAY),
        ("STM", player.stamina, player.max_stamina, GRAY),
        ("TIR", player.tireness, 100, GRAY),
        ("WTR", player.water, 100, GRAY),
        ("FOD", player.food, 100, GRAY),
        ("INF", player.infection, 100, GRAY),
        ("ANX", player.anxiety, 100, GRAY),
        ("DEF", player.get_total_defence(), 5.0, GRAY), 
        ("WGT", player.current_weight, player.max_carry_weight, GRAY)
    ]
    
    for i, (name, value, max_value, color) in enumerate(stats):
        y_pos = y_offset + i * 28
        icon = stat_icons.get(name)
        if icon:
            surface.blit(icon, (col1_x, y_pos))
            label_x = col1_x + 28
        else:
            text = font_14.render(f"{name}:", True, WHITE)
            surface.blit(text, (col1_x, y_pos))
            label_x = col1_x + 40

        bar_x = label_x + 10
        
        ratio = value / max_value if max_value > 0 else 0
        draw_color = color
        
        if name == "WGT" and ratio > 1.0:
            draw_color = RED 
            
        # [CHANGED] Calculate max width dynamically based on column width
        # This ensures the bars fill the available space instead of being fixed at 100px
        max_bar_width = int((col1_x + col_width) - bar_x - 10) + 100
        
        bar_width = int(max_bar_width * min(1.0, ratio))
        
        bar_rect = pygame.Rect(bar_x, y_pos + 5, bar_width, 10)
        border_rect = pygame.Rect(bar_x, y_pos + 5, max_bar_width, 10)
        
        pygame.draw.rect(surface, draw_color, bar_rect)
        pygame.draw.rect(surface, WHITE, border_rect, 1)

        # Hover Logic
        if border_rect.collidepoint(mouse_pos):
             full_name = stat_names.get(name, name)
             translated_name = tr('tooltip', full_name)

             if name == "WGT":
                 val_str = f"{value:.2f} / {max_value:.2f}"
             elif name == "DEF":
                 val_str = f"{(value / 5.0) * 100:.0f}%"
             else:
                 val_str = f"{int(value)}%"
                 
             active_tooltip_item = StatusTooltipItem(f"{translated_name}: {val_str}")

    # --- Draw Active Tooltip using Default System ---
    if active_tooltip_item:
        draw_tooltip(surface, active_tooltip_item, (mouse_pos[0], mouse_pos[1]))