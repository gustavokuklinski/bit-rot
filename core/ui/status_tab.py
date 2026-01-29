import pygame
from core.data.config import *

def draw_status_tab(surface, player, modal, assets, zombies_killed):
    # Define Column Regions
    padding = 10
    col_width = (modal['rect'].width - (padding * 3)) // 2
    
    start_y = modal['rect'].y + 80
    col1_x = modal['rect'].x + padding
    col2_x = modal['rect'].x + col_width + (padding * 2)
    
    # --- Column 1: General Stats & Body Condition ---
    
    # 1. Header
    name_text = font.render(f"{player.name}", True, WHITE)
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
        "DEF": SPRITE_PATH + "ui/defence.png"
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
        ("DEF", player.get_total_defence(), 100, GRAY)
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

        text = font_notification.render(f"[{int(value)}%]", True, WHITE)
        surface.blit(text, (label_x, y_pos + 3))

        bar_x = label_x + 50
        bar_width = int(100 * (value / max_value)) if max_value > 0 else 0
        bar_rect = pygame.Rect(bar_x, y_pos + 5, bar_width, 10)
        pygame.draw.rect(surface, color, bar_rect)
        pygame.draw.rect(surface, WHITE, (bar_x, y_pos + 5, 100, 10), 1)

    # 3. Body Parts Section
    y_offset += 80
    section_title = font_notification.render("", True, YELLOW)
    surface.blit(section_title, (col1_x, y_offset))
    y_offset += 23
    
    for part, data in player.body_parts.items():
        val = data.get('value', 100.0)
        max_val = 100.0
        
        # Color based on damage
        #p_color = GREEN if val > 80 else (255, 165, 0) if val > 40 else RED
        
        part_name = font_notification.render(part.capitalize(), True, WHITE)
        surface.blit(part_name, (col1_x + 200, y_offset))
        
        bar_w = 60
        fill_w = int(bar_w * (val / max_val))
        pygame.draw.rect(surface, WHITE, (col1_x + 294, y_offset + 2, bar_w +2, 10))
        pygame.draw.rect(surface, (40, 40, 40), (col1_x + 295, y_offset + 3, bar_w, 8))
        pygame.draw.rect(surface, GRAY, (col1_x + 295, y_offset + 3, fill_w, 8))
        
        val_text = font_notification.render(f"[{int(val)}%]", True, WHITE)
        surface.blit(val_text, (col1_x + 240, y_offset))
        
        y_offset += 20

    # --- Column 2: Visuals & Attributes ---
    
    # 1. Player Image (Center of Col 2)
    center_col2_x = col2_x + (col_width // 2)
    
    if player.image:
        # Create a composed surface for player + clothes
        # Assuming TILE_SIZE is imported from config
        char_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        
        # Draw Base Player
        char_surface.blit(player.image, (0, 0))
        
        # Draw Clothes (using player.clothes_slots for order)
        # We check if clothes have images and blit them
        for slot in player.clothes_slots:
            item = player.clothes.get(slot)
            if item and item.image:
                char_surface.blit(item.image, (0, 0))
        
        # Scale up the composed sprite
        scale_factor = 8
        new_w = TILE_SIZE * scale_factor
        new_h = TILE_SIZE * scale_factor
        
        big_sprite = pygame.transform.scale(char_surface, (new_w, new_h))
        sprite_rect = big_sprite.get_rect(centerx=center_col2_x, top=start_y - 9)
        surface.blit(big_sprite, sprite_rect)
        attr_y_start = sprite_rect.bottom + 30
    else:
        attr_y_start = start_y + 150