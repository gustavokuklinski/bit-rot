import pygame
from core.data.config import *

# Module-level cache to store loaded skill icons
_SKILL_ICON_CACHE = {}

def draw_record_tab(surface, player, modal, assets, mouse_pos):
    
    # [FIX] Access 'rect' from the dictionary using ['rect'] instead of .rect
    modal_rect = modal['rect']
    

    # 2. Define attributes to display (Label, Attribute ID)
    attributes_to_draw = [
        ("Strength", "strength"),
        ("Fitness", "fitness"),
        ("Melee", "melee"),
        ("Ranged", "ranged"),
        ("Maintenance", "maintenance"),
        ("Agility", "speed"),
        ("Luck", "lucky"), 
    ]

    # 3. Setup Layout
    start_x = modal_rect.left + 15
    start_y = modal_rect.top + 75
    line_height = 32 # [CHANGED] Increased line height to fit icons
    
    # 4. Loop and Draw Text
    for i, (label, attr_id) in enumerate(attributes_to_draw):
        current_y = start_y + (i * line_height)
        
        # Fetch level dynamically using the new helper method
        if hasattr(player.progression, "get_level"):
            level = player.progression.get_level(attr_id)
        else:
            # Fallback if you haven't fully refactored PlayerProgression yet
            level = player.progression.attributes.get(attr_id, {}).get("level", 0)

        # --- Draw Icon ---
        # Get image path from config loaded from XML
        attr_config = player.progression.config.attributes.get(attr_id, {})
        image_rel_path = attr_config.get('image')
        
        icon_size = 24
        icon_x = start_x
        
        if image_rel_path:
            # Check cache first
            if image_rel_path not in _SKILL_ICON_CACHE:
                try:
                    full_path = SPRITE_PATH + image_rel_path
                    img = pygame.image.load(full_path).convert_alpha()
                    img = pygame.transform.scale(img, (icon_size, icon_size))
                    _SKILL_ICON_CACHE[image_rel_path] = img
                except Exception as e:
                    print(f"Error loading skill icon '{image_rel_path}': {e}")
                    _SKILL_ICON_CACHE[image_rel_path] = None # Prevent continuous retry

            # Draw if loaded successfully
            icon_surf = _SKILL_ICON_CACHE.get(image_rel_path)
            if icon_surf:
                surface.blit(icon_surf, (icon_x, current_y))

        # --- Draw Label (e.g., "Strength:") ---
        bonus_perc = player.progression.get_total_attribute_bonus(player, attr_id)
        bonus_color = (100, 255, 100) if bonus_perc > 0 else (255, 100, 100)
        
        text_x = icon_x + icon_size + 10
        label_surf = font_notification.render(f"{label}:", True, GRAY)
        surface.blit(label_surf, (text_x, current_y + 2)) # +2 for vertical centering

        if bonus_perc != 0:
            bonus_surf = font_notification.render(f"({int(bonus_perc):+}% )", True, bonus_color)
            surface.blit(bonus_surf, (text_x + label_surf.get_width() + 5, current_y + 2))

        # --- Draw Value (e.g., "5") ---
        value_x = text_x + 160
        value_surf = font_notification.render(str(level), True, WHITE)
        surface.blit(value_surf, (value_x, current_y + 2))

        # --- Draw XP Progress Bar ---
        if hasattr(player.progression, "attributes"):
            attr_data = player.progression.attributes.get(attr_id)
            if attr_data:
                curr_xp = int(attr_data.get('xp', 0))
                req_xp = int(attr_data.get('xp_to_next_level', 100))
                
                # Bar Dimensions
                bar_width = 120
                bar_height = 10
                bar_x = value_x + 40
                bar_y = current_y + 8 # Center relative to text
                
                # Calculate fill ratio
                ratio = 0.0
                if req_xp > 0:
                    ratio = min(1.0, max(0.0, curr_xp / req_xp))
                
                # Draw Background (Dark Gray)
                pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))
                
                # Draw Fill (Green)
                fill_width = int(bar_width * ratio)
                if fill_width > 0:
                    pygame.draw.rect(surface, (50, 180, 50), (bar_x, bar_y, fill_width, bar_height))
                
                # Draw Border (Light Gray)
                pygame.draw.rect(surface, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)

                # Optional: Tooltip or text on hover could be added here later