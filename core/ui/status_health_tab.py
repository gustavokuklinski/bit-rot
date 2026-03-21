# core/ui/status_health_tab.py

import pygame
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.entities.item.item_data import ITEM_TEMPLATES
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

def draw_health_tab(surface, player, modal, assets):
    # Define Column Regions
    padding = 10
    col_width = (modal['rect'].width - (padding * 3)) // 2
    
    start_y = modal['rect'].y + 75
    col1_x = modal['rect'].x + padding
    col2_x = modal['rect'].x + col_width
    
    mouse_pos = pygame.mouse.get_pos()
    active_tooltip_item = None # Store the item to draw tooltip for

    # --- Column 1: Body Parts Section ---
    y_offset = start_y
    
    # Title
    section_title = font.render(f"{player.name}", True, WHITE)
    surface.blit(section_title, (col1_x, y_offset))
    y_offset += 140 
    
    # Icons loading
    stat_icons = {}
    icon_files = {
        "HP": SPRITE_PATH + "ui/hp.png",
        "STM": SPRITE_PATH + "ui/stamina.png",
        "WTR": SPRITE_PATH + "ui/water.png",
        "WGT": SPRITE_PATH + "ui/weight.png",
        "DEF": SPRITE_PATH + "ui/defence.png"
    }
    
    # Full names mapping for tooltip
    stat_names = {
        "HP": "Health",
        "STM": "Stamina",
        "WTR": "Water",
        "WGT": "Weight",
        "DEF": "Defence"
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
        ("WTR", player.water, 100, GRAY),
        ("WGT", player.current_weight, player.max_carry_weight, GRAY),
        ("DEF", player.get_total_defence(), 5.0, GRAY)
    ]
    
    for i, (name, value, max_value, color) in enumerate(stats):
        y_pos = y_offset + i * 28
        
        icon = stat_icons.get(name)
        if icon:
            surface.blit(icon, (col1_x, y_pos))
            label_x = col1_x + 28
        else:
            text = font_notification.render(f"{name}:", True, WHITE)
            surface.blit(text, (col1_x, y_pos))
            label_x = col1_x + 40
            
        bar_x = label_x + 10
        
        ratio = value / max_value if max_value > 0 else 0
        draw_color = color
        
        if name == "WGT" and ratio > 1.0:
            draw_color = RED 
            
        max_bar_width = int(col_width + 55)
        bar_width = int(max_bar_width * min(1.0, ratio))
        
        bar_rect = pygame.Rect(bar_x, y_pos + 5, bar_width, 10)
        border_rect = pygame.Rect(bar_x, y_pos + 5, max_bar_width, 10)
        
        pygame.draw.rect(surface, draw_color, bar_rect)
        pygame.draw.rect(surface, WHITE, border_rect, 1)

        # Hover Logic
        if border_rect.collidepoint(mouse_pos):
            full_name = stat_names.get(name, name)
            translated_name = tr('tooltip', full_name) # <-- Translate the name part first
            if name == "WGT":
                val_str = f"{value:.2f} / {max_value:.2f}"
            elif name == "DEF":
                val_str = f"{(value / 5.0) * 100:.0f}%"
            else:
                val_str = f"{int(value)}%"
                 
            active_tooltip_item = StatusTooltipItem(f"{translated_name}: {val_str}")

    # --- Column 2: Visuals & Attributes ---
    
    center_col2_x = col2_x - 30
    
    if player.image:
        char_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        char_surface.blit(player.image, (0, 0))
        
        # --- NEW: Accumulate slots that are designated to be hidden by currently worn clothes ---
        hidden_slots = set()
        for slot in player.clothes_slots:
            item = player.clothes.get(slot)
            if item:
                template = ITEM_TEMPLATES.get(item.name)
                if template and 'properties' in template and 'hide_cloth' in template['properties']:
                    hidden_slots.update(template['properties']['hide_cloth'])
        
        for slot in player.clothes_slots:
            if slot in hidden_slots:
                continue
                
            item = player.clothes.get(slot)
            if item and item.image:
                img_to_draw = item.image
                
                # Apply dynamic tint if the item has a custom color
                if hasattr(item, 'color') and item.color and item.color != (255, 255, 255):
                    if not hasattr(item, 'tinted_image') or getattr(item, 'last_color', None) != item.color:
                        item.tinted_image = item.image.copy()
                        item.tinted_image.fill((*item.color, 255)[:4], special_flags=pygame.BLEND_RGBA_MULT)
                        item.last_color = item.color
                    img_to_draw = item.tinted_image

                char_surface.blit(img_to_draw, (0, 0))
        
        scale_factor = 7
        new_w = TILE_SIZE * scale_factor
        new_h = TILE_SIZE * scale_factor
        
        big_sprite = pygame.transform.scale(char_surface, (new_w, new_h))
        sprite_rect = big_sprite.get_rect(centerx=center_col2_x, top=start_y + 20)
        surface.blit(big_sprite, sprite_rect)
    
    # --- Draw Active Tooltip using Default System ---
    if active_tooltip_item:
        draw_tooltip(surface, active_tooltip_item, (mouse_pos[0], mouse_pos[1]))