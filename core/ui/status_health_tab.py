# core/ui/health_tab.py

import pygame
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.entities.item.item_data import ITEM_TEMPLATES

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
    
    start_y = modal['rect'].y + 80
    col1_x = modal['rect'].x + padding
    col2_x = modal['rect'].x + col_width
    
    mouse_pos = pygame.mouse.get_pos()
    active_tooltip_item = None # Store the item to draw tooltip for

    # --- Column 1: Body Parts Section ---
    y_offset = start_y
    
    # Title
    section_title = font.render(f"{player.name}", True, WHITE)
    surface.blit(section_title, (col1_x, y_offset))
    y_offset += 150
    
    for part, data in player.body_parts.items():
        val = data.get('value', 100.0)
        max_val = 100.0
        
        part_name = font_notification.render(part.capitalize(), True, WHITE)
        # Adjusted X offset slightly since there are no icons to the left
        surface.blit(part_name, (col1_x + 5, y_offset)) 
        
        bar_w = 100
        fill_w = int(bar_w * (val / max_val))
        
        bar_x_pos = col1_x + 80 
        
        bg_rect = pygame.Rect(bar_x_pos - 1, y_offset + 2, bar_w + 2, 10)
        
        pygame.draw.rect(surface, WHITE, bg_rect)
        pygame.draw.rect(surface, (40, 40, 40), (bar_x_pos, y_offset + 3, bar_w, 8))
        pygame.draw.rect(surface, GRAY, (bar_x_pos, y_offset + 3, fill_w, 8))
        
        if bg_rect.collidepoint(mouse_pos):
             active_tooltip_item = StatusTooltipItem(f"{part.capitalize()}: {int(val)}%")
        
        y_offset += 20

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
        
        scale_factor = 8
        new_w = TILE_SIZE * scale_factor
        new_h = TILE_SIZE * scale_factor
        
        big_sprite = pygame.transform.scale(char_surface, (new_w, new_h))
        sprite_rect = big_sprite.get_rect(centerx=center_col2_x, top=start_y + 20)
        surface.blit(big_sprite, sprite_rect)
    
    # --- Draw Active Tooltip using Default System ---
    if active_tooltip_item:
        draw_tooltip(surface, active_tooltip_item, (mouse_pos[0], mouse_pos[1]))