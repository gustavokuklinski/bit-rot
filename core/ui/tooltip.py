import pygame
from core.data.config import *
from core.data.recipe_manager import RecipeManager

def draw_tooltip(surface, item, pos):
    if not item:
        return

    lines = [item.name]

    if hasattr(item, 'tooltip_text') and item.tooltip_text:
        lines.append(item.tooltip_text)
        
    if item.item_type:
        lines.append(f"Type: {item.item_type}")

    if hasattr(item, 'require') and item.require:
        reqs = item.require if isinstance(item.require, list) else [item.require]
        lines.append(f"Requires: {' or '.join(reqs)}")

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
        
    # --- Durability Bar Logic ---
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
    
    # --- Weight Info (Updated) ---
    total_weight = 0
    if hasattr(item, 'get_total_weight'):
        total_weight = item.get_total_weight()
        weight_str = f"Weight: {total_weight:.2f}"
        
        # Only show unit weight if the item is stackable
        if item.is_stackable() and hasattr(item, 'weight'):
             weight_str += f" (unit: {item.weight:.2f})"
             
        # Add reduction to the same line if it exists
        if hasattr(item, 'weight_reduction') and item.weight_reduction > 0:
            weight_str += f" (Reduction: {int(item.weight_reduction * 100)}%)"
        
        lines.append(weight_str)
    elif hasattr(item, 'weight'):
        # Fallback if get_total_weight doesn't exist for some reason
        total_weight = item.weight
        weight_str = f"Weight: {item.weight:.2f}"
        if hasattr(item, 'weight_reduction') and item.weight_reduction > 0:
            weight_str += f" (Reduction: {int(item.weight_reduction * 100)}%)"
        lines.append(weight_str)

    # Calculate and display max weight based on base weight x 5
    if hasattr(item, 'inventory') and item.item_type in ['container', 'backpack', 'cloth'] and hasattr(item, 'weight'):
        max_weight = item.weight * 5.0
        if max_weight > 0:
            lines.append(f"Max weight: {total_weight:.2f} / {max_weight:.2f}")
    
    # Fixed allow_belt checking (moved out of elif structure so it doesn't get skipped)
    if hasattr(item, 'allow_belt') and item.allow_belt:
        lines.append(f"Allow belt: {item.allow_belt}")
    # -------------------

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

    # --- Item Preview ---
    if hasattr(item, 'inventory') and item.inventory:
        if len(item.inventory) > 0:
            lines.append({'type': 'item_preview', 'items': item.inventory[:5]})
    # -----------------------------------------------

    if hasattr(item, 'tip') and item.tip:
        # Replace literal "\n" from XML with actual newlines, then split into a list
        tip_lines = str(item.tip).replace('\\n', '\n').split('\n')
        
        # Add the first line with the yellow "Tip: " prefix
        lines.append([("Tip: ", (255, 255, 0)), (tip_lines[0].strip(), WHITE)])
        
        # Add any remaining lines with invisible spaces to align them perfectly under the first line
        for extra_line in tip_lines[1:]:
            lines.append([("", (255, 255, 0)), (extra_line.strip(), WHITE)])

    rendered_lines = []
    for line in lines:
        # --- Handle Durability Bar ---
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
        
        # --- Handle Item Preview Rendering ---
        elif isinstance(line, dict) and line.get('type') == 'item_preview':
            items_to_draw = line['items']
            slot_size = 32  # Small size for tooltip
            gap = 4
            
            total_w = len(items_to_draw) * (slot_size + gap)
            total_h = slot_size
            
            line_surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
            
            for i, p_item in enumerate(items_to_draw):
                x_pos = i * (slot_size + gap)
                slot_rect = pygame.Rect(x_pos, 0, slot_size, slot_size)
                
                # Draw dark background for the slot
                pygame.draw.rect(line_surf, (40, 40, 40), slot_rect)
                pygame.draw.rect(line_surf, (100, 100, 100), slot_rect, 1) # Border
                
                if p_item.image:
                    # Scale image to fit within slot with small padding
                    icon_size = slot_size - 4
                    scaled_icon = pygame.transform.scale(p_item.image, (icon_size, icon_size))
                    icon_rect = scaled_icon.get_rect(center=slot_rect.center)
                    line_surf.blit(scaled_icon, icon_rect)
                else:
                    # Fallback if no image
                    pygame.draw.rect(line_surf, p_item.color, slot_rect.inflate(-6, -6))

            rendered_lines.append(line_surf)
        # ------------------------------------------

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
    if tooltip_rect.right > GAME_WIDTH:
        tooltip_rect.right = GAME_WIDTH
    if tooltip_rect.bottom > GAME_HEIGHT:
        tooltip_rect.bottom = GAME_HEIGHT

    pygame.draw.rect(surface, (0, 0, 0, 220), tooltip_rect) # Slightly darker opacity
    pygame.draw.rect(surface, WHITE, tooltip_rect, 1)

    y_offset = tooltip_rect.y + 10
    for line in rendered_lines:
        surface.blit(line, (tooltip_rect.x + 10, y_offset))
        y_offset += line.get_height()