# core/ui/status_health_tab.py

import pygame
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.entities.item.item_data import ITEM_TEMPLATES
from core.data.localization import tr

class StatusTooltipItem:
    def __init__(self, name, text=None):
        self.name = name
        self.tooltip_text = text
        self.item_type = None
        self.durability = None
        self.defence = None
        self.load = None
        self.capacity = None
        self.min_damage = None
        self.max_damage = None
        self.ammo_type = None

def _player_has_mobile(player):
    def search_inv(inventory):
        if not inventory: return False
        for item in inventory:
            if item:
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
    padding = 15
    content_width = modal['rect'].width - (padding * 2)
    start_x = modal['rect'].x + padding
    current_y = modal['rect'].y + 70
    
    mouse_pos = pygame.mouse.get_pos()
    active_tooltip_item = None

    # --- 1. PLAYER NAME (Centered) ---
    section_title = font_12.render(f"{player.name}", False, WHITE)
    # Center horizontally relative to the modal rect
    name_x = modal['rect'].x + (modal['rect'].width - section_title.get_width()) // 2
    surface.blit(section_title, (name_x, current_y))
    current_y += 35 

    # --- 2. PLAYER IMAGE ---
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
            if slot in hidden_slots: continue
            item = player.clothes.get(slot)
            if item and item.image:
                img_to_draw = item.image
                if getattr(item, 'item_type', '') == 'container': continue
                if hasattr(item, 'color') and item.color and item.color != (255, 255, 255):
                    if not hasattr(item, 'tinted_image') or getattr(item, 'last_color', None) != item.color:
                        item.tinted_image = item.image.copy()
                        item.tinted_image.fill((*item.color, 255)[:4], special_flags=pygame.BLEND_RGBA_MULT)
                        item.last_color = item.color
                    img_to_draw = item.tinted_image
                char_surface.blit(img_to_draw, (0, 0))
        
        scale_factor = 6 
        new_w = TILE_SIZE * scale_factor
        new_h = TILE_SIZE * scale_factor
        big_sprite = pygame.transform.scale(char_surface, (new_w, new_h))
        
        sprite_x = start_x + (content_width - new_w) // 2
        surface.blit(big_sprite, (sprite_x, current_y))
        current_y += new_h + 20

    # --- 3. PLAYER STATS ---
    stat_icons = {}
    icon_files = {
        "HP": SPRITE_PATH + "ui/hp.png", "STM": SPRITE_PATH + "ui/stamina.png",
        "WTR": SPRITE_PATH + "ui/water.png", "WGT": SPRITE_PATH + "ui/weight.png",
        "DEF": SPRITE_PATH + "ui/defence.png"
    }
    stat_names = { "HP": "Health", "STM": "Stamina", "WTR": "Water", "WGT": "Weight", "DEF": "Defence" }

    for k, path in icon_files.items():
        try:
            img = pygame.image.load(path).convert_alpha()
            stat_icons[k] = pygame.transform.scale(img, (24, 24))
        except: stat_icons[k] = None

    stats = [
        ("HP", player.health, player.max_health, GRAY),
        ("STM", player.stamina, player.max_stamina, GRAY),
        ("WTR", player.water, 100, GRAY),
        ("WGT", player.current_weight, player.max_carry_weight, GRAY),
        ("DEF", player.get_total_defence(), 100, GRAY)
    ]
    
    for i, (name, value, max_value, color) in enumerate(stats):
        y_pos = current_y + i * 27
        icon = stat_icons.get(name)
        if icon:
            surface.blit(icon, (start_x, y_pos - 4))
            label_x = start_x + 30
        else:
            text = font_12.render(f"{name}:", False, WHITE)
            surface.blit(text, (start_x, y_pos))
            label_x = start_x + 40
            
        bar_x = label_x + 5
        ratio = value / max_value if max_value > 0 else 0
        draw_color = RED if name == "WGT" and ratio > 1.0 else color
            
        max_bar_width = int(content_width - (bar_x - start_x))
        bar_width = int(max_bar_width * min(1.0, ratio))
        
        bar_rect = pygame.Rect(bar_x, y_pos + 2, bar_width, 10)
        border_rect = pygame.Rect(bar_x, y_pos + 2, max_bar_width, 10)
        
        pygame.draw.rect(surface, draw_color, bar_rect)
        pygame.draw.rect(surface, WHITE, border_rect, 1)

        if border_rect.collidepoint(mouse_pos):
            translated_name = tr('tooltip', stat_names.get(name, name))
            if name == "WGT": val_str = f"{value:.2f} / {max_value:.2f}"
            else: val_str = f"{int(value)}%"
            active_tooltip_item = StatusTooltipItem(f"{translated_name}: {val_str}")
            
    current_y += len(stats) * 27 + 20

    # --- 4. OTHER INFO ---
    if game:
        day_count = getattr(game.world_time, 'day_count', 0)
        player_has_mobile = _player_has_mobile(player)
        
        current_hour = game.world_time.current_hour
        mins = int((game.world_time.game_time_ms % (game.world_time.day_length_ms / 24)) / (game.world_time.day_length_ms / 24 / 60))
        mins = (mins // 10) * 10 
        time_ratio = (current_hour * 60 + mins) / 1440.0
        
        if player_has_mobile:
            time_str = f"{current_hour:02d}:{mins:02d}"
            time_color = WHITE
            weather_state = getattr(game.world_time, 'weather', 'CLEAR')
            timer_ms = getattr(game.world_time, 'weather_timer', 0)
            game_ms_per_minute = game.world_time.day_length_ms / (24 * 60)
            total_game_mins_left = int(timer_ms / game_ms_per_minute) if game_ms_per_minute > 0 else 0
            w_hours = total_game_mins_left // 60
            rain_val = f"{w_hours}h" if weather_state == 'CLEAR' else "Now"
            rain_color = (100, 200, 255) if weather_state != 'CLEAR' else ((255, 170, 100) if w_hours <= 2 else WHITE)
        else:
            time_str = "No Signal"
            time_color = (200, 80, 80)
            rain_val = "Offline"
            rain_color = (120, 120, 120)

        world_state = getattr(game.world_time, 'state', 'DAY')
        weather_icon = SPRITE_PATH + "ui/night.png" if world_state in ['NIGHT', 'TRANSITION_TO_NIGHT'] else SPRITE_PATH + "ui/day.png"
        day_night_str = "Darkness" if world_state in ['NIGHT', 'TRANSITION_TO_NIGHT'] else "Daylight"
        dn_color = (150, 150, 255) if world_state in ['NIGHT', 'TRANSITION_TO_NIGHT'] else (255, 220, 100)
        
        # Combined rows: (Icon, Label, Value, Value Color, Progress Bar Ratio)
        # Row 1: Time + Days
        # Row 2: Day/Night + Rain
        combined_lines = [
            (SPRITE_PATH + "ui/clock.png", "Time", f"{time_str} - {day_count} day", time_color, time_ratio),
            (weather_icon, "", f"{day_night_str} - Rain in: {rain_val}", rain_color, None),
        ]
        
        status_title = font_12.render("World Info", False, WHITE)
        surface.blit(status_title, (start_x, current_y))
        
        text_y = current_y + 35
        tooltip_texts = ["Current time cycle", "Time of day and rain"]
        panel_width = content_width - 10
        
        for idx, (icon_path, label, val, val_color, bar_ratio) in enumerate(combined_lines):
            row_rect = pygame.Rect(start_x, text_y, panel_width, 24)
            if row_rect.collidepoint(mouse_pos):
                active_tooltip_item = StatusTooltipItem(tr('tooltip', tooltip_texts[idx]))

            if icon_path:
                try:
                    img = pygame.image.load(icon_path).convert_alpha()
                    img = pygame.transform.scale(img, (18, 18))
                    surface.blit(img, (start_x, text_y + 1))
                except: pass
            
            current_x = start_x + 25 
            if label:
                lbl_surf = font_12.render(f"{label}: ", False, (160, 160, 160))
                surface.blit(lbl_surf, (current_x, text_y))
                current_x += lbl_surf.get_width()
                
            val_surf = font_12.render(val, False, val_color)
            surface.blit(val_surf, (current_x, text_y))
            text_y += 24
            
            if bar_ratio is not None:
                bar_x = start_x + 25
                max_bar_width = panel_width - 25
                bar_width = int(max_bar_width * bar_ratio)
                pygame.draw.rect(surface, GRAY, pygame.Rect(bar_x, text_y + 2, bar_width, 10))
                pygame.draw.rect(surface, WHITE, pygame.Rect(bar_x, text_y + 2, max_bar_width, 10), 1)
                text_y += 18
            else:
                text_y += 6

    if active_tooltip_item:
        draw_tooltip(surface, active_tooltip_item, (mouse_pos[0], mouse_pos[1]))