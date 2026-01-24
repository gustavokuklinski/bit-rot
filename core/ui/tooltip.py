import pygame
from core.data.config import *
from core.data.recipe_manager import RecipeManager

def draw_tooltip(surface, item, pos):
    if not item:
        return

    lines = [item.name]
    if item.item_type:
        lines.append(f"Type: {item.item_type}")
        
    if item.item_type == 'recipe':
        # Ensure recipes are loaded if checking from main menu or early state
        if not RecipeManager.RECIPES:
             RecipeManager.load_recipes()
             
        recipes = RecipeManager.get_recipes_by_magazine(item.name)
        if recipes:
            lines.append("Teaches:")
            for r in recipes:
                lines.append(f" - {r.output_name}")

    if hasattr(item, 'inventory') and item.inventory is not None:
        if item.item_type in ['container', 'backpack', 'cloth']:
            cap = item.capacity if item.capacity is not None else 0
            lines.append(f"Contents: {len(item.inventory)} / {cap}")
        
    # --- MODIFIED: Logic to trigger bar rendering ---
    if item.durability is not None:
        max_dur = item.max_durability # Get max from item property
        if max_dur > 0:
            pct = item.durability / max_dur
            # Insert a dictionary to signal the renderer to draw a bar
            lines.append({'type': 'durability_bar', 'pct': pct})
        else:
            # Fallback if max is 0 or undefined
            lines.append(f"{item.durability:.0f}")
    # ------------------------------------------------

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
        effective_defence = item.defence
        if item.durability is not None and item.max_durability > 0:
            effective_defence *= (item.durability / item.max_durability)
        
        lines.append(f"Defence: {effective_defence:.1f}")
    if item.load is not None and item.capacity is not None:
        lines.append(f"Load: {item.load:.0f}/{item.capacity:.0f}")
    elif item.load is not None:
        lines.append(f"Load: {item.load:.0f}")
    if item.min_damage is not None and item.max_damage is not None:
        min_damage, max_damage = item.current_damage_range
        lines.append(f"Damage: {min_damage}-{max_damage}")
    if item.ammo_type:
        lines.append(f"Ammo: {item.ammo_type}")
    
    if hasattr(item, 'repair_list') and item.repair_list:
        lines.append("Repairs:")
        for target_name in item.repair_list:
            # Display item name (replacing underscores for cleaner look if desired)
            display_str = target_name.replace('_', ' ')
            lines.append(f" - {display_str}")
    
    if item.item_type == 'charm' and hasattr(item, 'attribute_modifiers') and item.attribute_modifiers:
        lines.append("") # Add a spacer line
        lines.append("Passive (in Inventory):")
        for attr_name, value in item.attribute_modifiers.items():
            # Format as: "  Lucky: +0.5%"
            lines.append(f"  {attr_name.capitalize()}: +{value:.1f}%")


    # font = pygame.font.Font(None, 24) # Unused in original code effectively
    rendered_lines = []
    for line in lines:
        # --- NEW: Handle Durability Bar ---
        if isinstance(line, dict) and line.get('type') == 'durability_bar':
            # Settings
            bar_w = 100
            bar_h = 10
            pct = max(0, min(1, line['pct']))
            
            # Colors (Matching Inventory)
            if pct > 0.5: col = (0, 255, 0) # Green
            elif pct > 0.2: col = (255, 255, 0) # Yellow
            else: col = (255, 0, 0) # Red

            # Render Label "Durability:"
            label_surf = font_notification.render("", True, WHITE)
            
            # Create Surface for the whole line (Text + Spacing + Bar)
            total_w = label_surf.get_width() + 5 + bar_w
            total_h = max(label_surf.get_height(), bar_h)
            line_surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
            
            # Blit Label (Vertically Centered)
            label_y = (total_h - label_surf.get_height()) // 2
            line_surf.blit(label_surf, (0, label_y))
            
            # Draw Bar
            bar_x = label_surf.get_width()
            bar_y = (total_h - bar_h) // 2
            
            # Background
            pygame.draw.rect(line_surf, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
            # Fill
            fill_w = int(bar_w * pct)
            if fill_w > 0:
                pygame.draw.rect(line_surf, col, (bar_x, bar_y, fill_w, bar_h))
            # Border
            pygame.draw.rect(line_surf, (150, 150, 150), (bar_x, bar_y, bar_w, bar_h), 1)
            
            rendered_lines.append(line_surf)
        # ----------------------------------

        elif isinstance(line, list):
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
            rendered_lines.append(font_notification.render(str(line), True, WHITE))
    
    if not rendered_lines:
        return

    width = max(line.get_width() for line in rendered_lines) + 20
    height = sum(line.get_height() for line in rendered_lines) + 20
    
    tooltip_rect = pygame.Rect(pos[0], pos[1], width, height)
    
    # Adjust position to keep tooltip on screen
    if tooltip_rect.right > VIRTUAL_SCREEN_WIDTH:
        tooltip_rect.right = VIRTUAL_SCREEN_WIDTH
    if tooltip_rect.bottom > VIRTUAL_GAME_HEIGHT:
        tooltip_rect.bottom = VIRTUAL_GAME_HEIGHT

    pygame.draw.rect(surface, (0, 0, 0, 220), tooltip_rect) # Slightly darker opacity
    pygame.draw.rect(surface, WHITE, tooltip_rect, 1)

    y_offset = tooltip_rect.y + 10
    for line in rendered_lines:
        surface.blit(line, (tooltip_rect.x + 10, y_offset))
        y_offset += line.get_height()