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
        self.item_type = None
        self.durability = None
        self.defence = None
        self.load = None
        self.capacity = None
        self.min_damage = None
        self.max_damage = None
        self.ammo_type = None

def _player_has_mobile(player):
    """Recursively checks if player possesses a Mobile device."""
    def search_inv(inventory):
        if not inventory: return False
        for item in inventory:
            if item:
                # Check exact name or internal name
                if 'Mobile' in getattr(item, 'name', ''):
                    return True
                if hasattr(item, 'inventory') and search_inv(item.inventory):
                    return True
        return False

    if search_inv(player.inventory): return True
    if search_inv(player.belt): return True
    if search_inv(list(player.clothes.values())): return True
    return False

def draw_health_tab(surface, player, modal, assets, game=None):
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
        ("DEF", player.get_total_defence(), 100, GRAY)
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
            
        max_bar_width = int(col_width + 55)
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
                val_str = f"{int(value)}%"
            else:
                val_str = f"{int(value)}%"
                 
            active_tooltip_item = StatusTooltipItem(f"{translated_name}: {val_str}")

    # --- Column 2: Visuals & Attributes ---
    
    center_col2_x = col2_x - 45
    new_w = 0 
    
    if player.image:
        char_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        char_surface.blit(player.image, (0, 0))
        
        hidden_slots = set()
        for slot in player.clothes_slots:
            item = player.clothes.get(slot)
            if item:
                template = ITEM_TEMPLATES.get(tr('item', item.name))
                if template and 'properties' in template and 'hide_cloth' in template['properties']:
                    hidden_slots.update(template['properties']['hide_cloth'])
        
        for slot in player.clothes_slots:
            if slot in hidden_slots:
                continue
                
            item = player.clothes.get(slot)
            if item and item.image:
                img_to_draw = item.image
                if getattr(item, 'item_type', '') == 'container':
                    continue
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
        
    # --- NEW: Contextual Information Panel ---
    if game:
        player_has_mobile = _player_has_mobile(player)
        day_count = getattr(game.world_time, 'day_count', 0)
        
        if player_has_mobile:
            current_hour = game.world_time.current_hour
            mins = int((game.world_time.game_time_ms % (game.world_time.day_length_ms / 24)) / (game.world_time.day_length_ms / 24 / 60))
            
            # Snap to 10-minute increments
            mins = (mins // 10) * 10 
            
            time_str = f"{current_hour:02d}:{mins:02d}"
            
            # Translate real-time weather timer into in-game hours
            weather_state = getattr(game.world_time, 'weather', 'CLEAR')
            timer_ms = getattr(game.world_time, 'weather_timer', 0)
            
            game_ms_per_minute = game.world_time.day_length_ms / (24 * 60)
            total_game_mins_left = int(timer_ms / game_ms_per_minute) if game_ms_per_minute > 0 else 0
            
            w_hours = total_game_mins_left // 60
            
            if weather_state == 'CLEAR':
                weather_str = f"Clear ({w_hours}h)"
            else:
                weather_str = f"Rain ({w_hours}h)"
        else:
            time_str = "--:--"
            weather_state = getattr(game.world_time, 'weather', 'CLEAR')
            weather_str = "Rain" if weather_state == 'RAIN' else "Clear"

        day_str = f"{day_count} days"
        kills_str = str(getattr(game, 'zombies_killed', 0))
        
        info_x = center_col2_x + (new_w // 2) - 10
        info_y = start_y + 20
        
        # Determine day/night icon based on world state cleanly
        world_state = getattr(game.world_time, 'state', 'DAY')
        if world_state in ['NIGHT', 'TRANSITION_TO_NIGHT']:
            weather_icon = SPRITE_PATH + "ui/night.png"
        else:
            weather_icon = SPRITE_PATH + "ui/day.png"
        
        lines = [
            (SPRITE_PATH + "ui/clock.png", "Time", time_str),
            (None, "", day_str),  # Empty label, no icon, just the value directly below the time
            (weather_icon, "Weather", weather_str),
            (SPRITE_PATH + "ui/infection.png", "Kills", kills_str)
        ]
        
        # Draw elegant background panel 
        panel_width = 110
        panel_height = len(lines) * 24 + 16
        panel_rect = pygame.Rect(info_x, info_y, panel_width, panel_height)
        
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill((20, 20, 20, 220))
        surface.blit(s, panel_rect.topleft)
        pygame.draw.rect(surface, (80, 80, 80), panel_rect, 1, border_radius=4)
        
        text_y = info_y + 8
        
        # Mapping index to tooltip labels for the lines
        tooltip_texts = [
            "Current time",
            "Days Alive",
            "Weather and next rain hour",
            "Player kills"
        ]
        
        for idx, (icon_path, label, val) in enumerate(lines):
            # Check row-level hover for tooltip
            row_rect = pygame.Rect(info_x, text_y, panel_width, 24)
            if row_rect.collidepoint(mouse_pos):
                translated_tip = tr('tooltip', tooltip_texts[idx])
                active_tooltip_item = StatusTooltipItem(translated_tip)

            val_surf = font_14.render(val, True, WHITE)
            
            icon_drawn = False
            if icon_path:
                try:
                    img = pygame.image.load(icon_path).convert_alpha()
                    img = pygame.transform.scale(img, (18, 18))
                    surface.blit(img, (info_x + 10, text_y + 1))
                    icon_drawn = True
                except Exception:
                    pass
            
            # Only draw a label string if 'label' is not an empty string
            if not icon_drawn and label:
                lbl_surf = font_14.render(f"{label}:", True, (160, 160, 160))
                surface.blit(lbl_surf, (info_x + 10, text_y))
                
            surface.blit(val_surf, (info_x + panel_width - val_surf.get_width() - 10, text_y))
            text_y += 24

    # --- Draw Active Tooltip using Default System ---
    if active_tooltip_item:
        draw_tooltip(surface, active_tooltip_item, (mouse_pos[0], mouse_pos[1]))