import pygame
from core.data.config import *

def draw_tooltip(surface, item, pos):
    if not item:
        return

    lines = [item.name]
    if item.item_type:
        lines.append(f"Type: {item.item_type}")
    if item.durability is not None:
        max_dur = item.max_durability # Get max from item property
        if max_dur > 0:
            pct = (item.durability / max_dur) * 100
            lines.append(f"Durability: {int(pct)}%")
        else:
            # Fallback if max is 0 or undefined
            lines.append(f"Durability: {item.durability:.0f}")
    if hasattr(item, 'effects') and item.effects:
        for effect in item.effects:
            # Format targets nicely: "Health, Tireness"
            targets_str = ", ".join([t.capitalize() for t in effect['targets']])
            
            min_v = effect['min']
            max_v = effect['max']
            range_str = f"{min_v}" if min_v == max_v else f"{min_v}-{max_v}"
            
            # Determine Sign and Color
            if effect['type'] == 'restore':
                sign_part = ("[+] ", GREEN)
            else: # reduce
                sign_part = ("[-] ", RED)
            
            # Add as a list of parts: [(Sign, Color), (Rest of text, White)]
            lines.append([
                sign_part, 
                (f"{targets_str} ({range_str})", WHITE)
            ])

    if item.defence is not None and item.defence > 0:
        lines.append(f"Defence: {item.defence:.0f}")
    if item.load is not None and item.capacity is not None:
        lines.append(f"Load: {item.load:.0f}/{item.capacity:.0f}")
    elif item.load is not None:
        lines.append(f"Load: {item.load:.0f}")
    if item.min_damage is not None and item.max_damage is not None:
        min_damage, max_damage = item.current_damage_range
        lines.append(f"Damage: {min_damage}-{max_damage}")
    
    #if item.min_restore is not None and item.max_restore is not None:
    #    stat = getattr(item, 'status_effect', 'Stat').capitalize()
    #    if item.min_restore == item.max_restore:
    #        lines.append(f"Restores: {item.min_restore} {stat}")
    #    else:
    #        lines.append(f"Restores: {item.min_restore}-{item.max_restore} {stat}")
    #if item.min_reduce is not None and item.max_reduce is not None:
    #    stat = getattr(item, 'status_effect', 'Stat').capitalize()
    #    if item.min_reduce == item.max_reduce:
    #        lines.append(f"Reduce: {item.min_reduce} {stat}")
    #    else:
    #        lines.append(f"Reduce: {item.min_reduce}-{item.max_reduce} {stat}")
    
        
    if item.item_type == 'skill' and hasattr(item, 'attribute_modifiers') and item.attribute_modifiers:
        lines.append("") # Add a spacer line
        lines.append("Passive (in Inventory):")
        for attr_name, value in item.attribute_modifiers.items():
            # Format as: "  Lucky: +0.5%"
            lines.append(f"  {attr_name.capitalize()}: +{value:.1f}%")


    font = pygame.font.Font(None, 24)
    rendered_lines = []
    for line in lines:
        if isinstance(line, list):
            # Handle composite line: [(text, color), (text, color)]
            parts = [font_notification.render(text, True, color) for text, color in line]
            total_w = sum(p.get_width() for p in parts)
            max_h = max(p.get_height() for p in parts)
            
            # Create a surface for this line
            line_surf = pygame.Surface((total_w, max_h), pygame.SRCALPHA)
            curr_x = 0
            for p in parts:
                line_surf.blit(p, (curr_x, 0))
                curr_x += p.get_width()
            rendered_lines.append(line_surf)
        else:
            # Handle standard string line (Default White)
            rendered_lines.append(font_notification.render(line, True, WHITE))
    
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
