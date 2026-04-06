import pygame
from core.data.config import *
from core.data.recipe_manager import RecipeManager
from core.data.localization import tr

def draw_tooltip(surface, item, pos, parent_rect=None):
    if not item:
        return

    lines = [tr('item', item.name)]

    if hasattr(item, 'tooltip_text') and item.tooltip_text:
        lines.append(item.tooltip_text)
        
    if item.item_type:
        lines.append(f"{tr('tooltip', 'Type:')} {tr('tooltip', item.item_type)}")

    if hasattr(item, 'require') and item.require:
        reqs = item.require if isinstance(item.require, list) else [item.require]
        
        # Extract the localized 'or' separator to keep the f-string clean
        or_separator = f" {tr('tooltip', 'or')} "
        lines.append(f"{tr('tooltip', 'Requires:')} {or_separator.join(reqs)}")

    if getattr(item, 'fuel_type', None):
        raw_fuel = item.fuel_type
        if isinstance(raw_fuel, dict) and 'type' in raw_fuel:
            raw_fuel = raw_fuel['type']
            
        candidates = []
        if isinstance(raw_fuel, list):
            candidates = raw_fuel
        elif isinstance(raw_fuel, str):
            if raw_fuel.startswith('[') and raw_fuel.endswith(']'):
                candidates = [s.strip() for s in raw_fuel[1:-1].split(',')]
            else:
                candidates = [raw_fuel]
        
        translated_fuels = [tr('item', c) for c in candidates]
        lines.append(f"{tr('tooltip', 'Fuel:')} {', '.join(translated_fuels)}")

    if item.item_type == 'recipe':
        # Ensure recipes are loaded if checking from main menu or early state
        if not RecipeManager.RECIPES:
             RecipeManager.load_recipes()
             
        recipes = RecipeManager.get_recipes_by_magazine(tr('item', item.name))
        if recipes:
            lines.append(tr('tooltip', "Teaches:"))
            for r in recipes:
                lines.append(f" - {r.output_name}")

    if hasattr(item, 'inventory') and item.inventory is not None:
        if item.item_type in ['container', 'cloth']:
            cap = item.capacity if item.capacity is not None else 0
            lines.append(f"{tr('tooltip', 'Contents:')} {len(item.inventory)} / {cap}")
        
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
            targets_str = ", ".join([tr('tooltip', t.capitalize()) for t in effect['targets']])
            
            val = effect.get('value', 0)
            range_str = f"{val}"
            
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
        
        lines.append(f"{tr('tooltip', 'Defence:')} {effective_defence:.0f}%")
    if item.load is not None and item.capacity is not None:
        lines.append(f"{tr('tooltip', 'Load:')} {item.load:.0f}/{item.capacity:.0f}")
    elif item.load is not None:
        lines.append(f"{tr('tooltip', 'Load:')} {item.load:.0f}")
    
    # --- Weight Info (Updated) ---
    total_weight = 0
    if hasattr(item, 'get_total_weight'):
        total_weight = item.get_total_weight()
        weight_str = f"{tr('tooltip', 'Weight:')} {total_weight:.2f}"
        
        # Only show unit weight if the item is stackable
        if item.is_stackable() and hasattr(item, 'weight'):
             weight_str += f" ({tr('tooltip', 'unit:')} {item.weight:.2f})"
             
        # Add reduction to the same line if it exists
        if hasattr(item, 'weight_reduction') and item.weight_reduction > 0:
            weight_str += f" ({tr('tooltip', 'Reduction:')} {int(item.weight_reduction * 100)}%)"
        
        lines.append(weight_str)
    elif hasattr(item, 'weight'):
        # Fallback if get_total_weight doesn't exist for some reason
        total_weight = item.weight
        weight_str = f"{tr('tooltip', 'Weight:')} {item.weight:.2f}"
        if hasattr(item, 'weight_reduction') and item.weight_reduction > 0:
            weight_str += f" ({tr('tooltip', 'Reduction:')} {int(item.weight_reduction * 100)}%)"
        lines.append(weight_str)

    # Calculate and display max weight based on base weight x 5
    if hasattr(item, 'inventory') and item.item_type in ['container', 'cloth'] and hasattr(item, 'weight'):
        max_weight = item.weight * 5.0
        if max_weight > 0:
            lines.append(f"{tr('tooltip', 'Max weight:')} {max_weight:.2f}")
    
    # Fixed allow_belt checking (moved out of elif structure so it doesn't get skipped)
    if hasattr(item, 'allow_belt') and item.allow_belt:
        lines.append(f"{tr('tooltip', 'Allow belt:')} {tr('tooltip', str(item.allow_belt))}")
    # -------------------

    if item.min_damage is not None and item.max_damage is not None:
        min_damage, max_damage = item.current_damage_range
        lines.append(f"{tr('tooltip', 'Damage:')} {min_damage}-{max_damage}")
    if item.ammo_type:
        lines.append(f"{tr('tooltip', 'Ammo:')} {tr('item', item.ammo_type)}")
    
    if hasattr(item, 'repair_list') and item.repair_list:
        lines.append(tr('tooltip', "Repairs:"))
        for target_name in item.repair_list:
            # Display item name (replacing underscores for cleaner look if desired)
            display_str = target_name.replace('_', ' ')
            lines.append(f" - {display_str}")
    
    if item.item_type == 'charm' and hasattr(item, 'attribute_modifiers') and item.attribute_modifiers:
        lines.append("") # Add a spacer line
        lines.append(tr('tooltip', "Passive (in Inventory):"))
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
        lines.append([(tr('tooltip', "Tip: "), (255, 255, 0)), (tip_lines[0].strip(), WHITE)])
        
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
            label_surf = font_14.render("", True, WHITE)
            
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
            parts = [font_14.render(text, True, color) for text, color in line]
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
            rendered_lines.append(font_14.render(str(line), True, WHITE))
    
    if not rendered_lines:
        return

    width = max(line.get_width() for line in rendered_lines) + 20
    height = sum(line.get_height() for line in rendered_lines) + 20
    
    if parent_rect:
        # --- NEW: Static Modal Anchor Logic ---
        # Align to the Left of the modal
        tt_x = parent_rect.left - width - 5
        tt_y = parent_rect.top
        
        # Failsafe: If no room on the left edge of the screen, flip to the Right side
        if tt_x < 0:
            tt_x = parent_rect.right + 5
            
        # Failsafe: Keep it from bleeding off the bottom of the screen
        if tt_y + height > GAME_HEIGHT:
            tt_y = GAME_HEIGHT - height - 5
            
    else:
        # --- EXISTING: Cursor Follow Logic ---
        tt_x = pos[0] + 15
        tt_y = pos[1] + 15
        
        if tt_x + width > GAME_WIDTH:
            tt_x = pos[0] - width - 5
        if tt_y + height > GAME_HEIGHT:
            tt_y = pos[1] - height - 5

    # FIX: Use the calculated tt_x and tt_y instead of hardcoded pos[0] and pos[1]
    tooltip_rect = pygame.Rect(tt_x, tt_y, width, height)
    
    # Final safety net to keep it strictly on-screen globally
    if tooltip_rect.right > GAME_WIDTH:
        tooltip_rect.right = GAME_WIDTH
    if tooltip_rect.bottom > GAME_HEIGHT:
        tooltip_rect.bottom = GAME_HEIGHT
    if tooltip_rect.left < 0:
        tooltip_rect.left = 0
    if tooltip_rect.top < 0:
        tooltip_rect.top = 0

    pygame.draw.rect(surface, (0, 0, 0, 220), tooltip_rect) # Slightly darker opacity
    pygame.draw.rect(surface, WHITE, tooltip_rect, 1)

    y_offset = tooltip_rect.y + 10
    for line in rendered_lines:
        surface.blit(line, (tooltip_rect.x + 10, y_offset))
        y_offset += line.get_height()