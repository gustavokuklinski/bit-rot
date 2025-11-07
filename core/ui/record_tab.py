import pygame
from data.config import *

def draw_record_tab(surface, player, modal, assets, mouse_pos):
    y_offset = modal['rect'].y + 80
    x_offset = modal['rect'].x + 10
    tooltip_to_draw = None
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
        ("STR", player.progression.strength, RED),
        ("FIT", player.progression.fitness, GREEN),
        ("MLE", player.progression.melee, BLUE),
        ("RNG", player.progression.ranged, YELLOW),
        ("LCK", player.progression.lucky, WHITE),
        ("SPD", player.progression.speed, GRAY),
    ]

    for i, (name, attr_data, color) in enumerate(skills):
        y_pos = y_offset + i * 28
        
        icon = skill_icons.get(name)
        if icon:
            surface.blit(icon, (x_offset, y_pos))
            label_x = x_offset + 28
        else:
            text = font.render(f"{name}:", True, WHITE)
            surface.blit(text, (x_offset, y_pos))
            label_x = x_offset + 110

        if isinstance(attr_data, dict): # Leveled attribute
            level = attr_data['level']
            xp = attr_data['xp']
            xp_to_next = attr_data['xp_to_next_level']
            
            text = font_small.render(f"[{int(level)}]", True, WHITE)
            surface.blit(text, (label_x, y_pos + 3))

            bar_x = label_x + 40

            full_bar_rect = pygame.Rect(bar_x, y_pos + 5, 100, 10)

            bar_width = int(100 * (xp / xp_to_next)) if xp_to_next > 0 else 0
            bar_rect = pygame.Rect(bar_x, y_pos + 5, bar_width, 10)
            pygame.draw.rect(surface, color, bar_rect)
            pygame.draw.rect(surface, WHITE, full_bar_rect, 1) # Use full_bar_rect for the border

            # --- [FIX START] Check for hover and prepare tooltip
            if full_bar_rect.collidepoint(mouse_pos):
                tooltip_text = f"XP: {int(xp)} / {int(xp_to_next)}"
                tooltip_to_draw = (tooltip_text, full_bar_rect.midtop)

        else: # Static attribute
            value = attr_data
            text = font_small.render(f"[{int(value)}]", True, WHITE)
            surface.blit(text, (label_x, y_pos + 3))
    
    if tooltip_to_draw:
        text, pos = tooltip_to_draw
        
        # Render the text
        tip_surf = font_small.render(text, True, BLACK) # Black text
        
        # Create a padded rect for the background
        # Position it 10px above the middle of the bar
        tip_rect = tip_surf.get_rect(midbottom=(pos[0], pos[1] - 10))
        tip_rect.inflate_ip(10, 6) # Add padding
        
        # Adjust position to stay on screen
        if tip_rect.right > VIRTUAL_SCREEN_WIDTH:
            tip_rect.right = VIRTUAL_SCREEN_WIDTH
        if tip_rect.top < 0:
            tip_rect.top = 0
        
        # Draw background and text
        pygame.draw.rect(surface, (230, 230, 230), tip_rect, 0, 3) # Light grey background
        pygame.draw.rect(surface, BLACK, tip_rect, 1, 3) # Black border
        surface.blit(tip_surf, (tip_rect.x + 5, tip_rect.y + 3))
