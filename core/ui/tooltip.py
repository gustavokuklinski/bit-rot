import pygame
from data.config import *

def draw_tooltip(surface, item, pos):
    if not item:
        return

    lines = [item.name]
    if item.item_type:
        lines.append(f"Type: {item.item_type}")
    if item.durability is not None:
        lines.append(f"Durability: {item.durability:.0f}")
    if item.defence is not None and item.defence > 0:
        lines.append(f"Defence: {item.defence:.0f}")
    if item.load is not None and item.capacity is not None:
        lines.append(f"Load: {item.load:.0f}/{item.capacity:.0f}")
    elif item.load is not None:
        lines.append(f"Load: {item.load:.0f}")
    if item.min_damage is not None and item.max_damage is not None:
        min_damage, max_damage = item.current_damage_range
        lines.append(f"Damage: {min_damage}-{max_damage}")
    if item.min_restore is not None and item.max_restore is not None:
        stat = getattr(item, 'status_effect', 'Stat').capitalize()
        if item.min_restore == item.max_restore:
            lines.append(f"Restores: {item.min_restore} {stat}")
        else:
            lines.append(f"Restores: {item.min_restore}-{item.max_restore} {stat}")
    if item.min_reduce is not None and item.max_reduce is not None:
        stat = getattr(item, 'status_effect', 'Stat').capitalize()
        if item.min_reduce == item.max_reduce:
            lines.append(f"Reduce: {item.min_reduce} {stat}")
        else:
            lines.append(f"Reduce: {item.min_reduce}-{item.max_reduce} {stat}")
    
        
    if item.item_type == 'skill' and hasattr(item, 'attribute_modifiers') and item.attribute_modifiers:
        lines.append("") # Add a spacer line
        lines.append("Passive (in Inventory):")
        for attr_name, value in item.attribute_modifiers.items():
            # Format as: "  Lucky: +0.5%"
            lines.append(f"  {attr_name.capitalize()}: +{value:.1f}%")


    font = pygame.font.Font(None, 24)
    rendered_lines = [font_small.render(line, True, WHITE) for line in lines]
    
    width = max(line.get_width() for line in rendered_lines) + 20
    height = sum(line.get_height() for line in rendered_lines) + 20
    
    tooltip_rect = pygame.Rect(pos[0], pos[1], width, height)
    
    # Adjust position to keep tooltip on screen
    if tooltip_rect.right > VIRTUAL_SCREEN_WIDTH:
        tooltip_rect.right = VIRTUAL_SCREEN_WIDTH
    if tooltip_rect.bottom > VIRTUAL_GAME_HEIGHT:
        tooltip_rect.bottom = VIRTUAL_GAME_HEIGHT

    pygame.draw.rect(surface, (0, 0, 0, 200), tooltip_rect)
    pygame.draw.rect(surface, WHITE, tooltip_rect, 1)

    y_offset = tooltip_rect.y + 10
    for line in rendered_lines:
        surface.blit(line, (tooltip_rect.x + 10, y_offset))
        y_offset += line.get_height()
