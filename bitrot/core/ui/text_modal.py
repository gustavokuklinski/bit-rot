import pygame
from core.data.config import *
from core.ui.modals import BaseModal, draw_scrollbar
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS
from core.data.localization import tr

def wrap_text(text, width, font_12):
    """Wraps text to fit within a specific width."""
    lines = []
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        if paragraph == "":
            lines.append("") # Add empty lines for paragraph breaks
            continue
            
        words = paragraph.split(' ')
        current_line = ""
        while words:
            word = words.pop(0)
            
            # Check if word itself is too long
            if font_12.size(word)[0] > width:
                # Handle very long words (e.g., URLs) by breaking them
                for char in word:
                    if font_12.size(current_line + char)[0] <= width:
                        current_line += char
                    else:
                        lines.append(current_line)
                        current_line = char
                # Add the remainder
                if current_line:
                    words.insert(0, current_line) # Put it back to be processed
                current_line = "" # Reset
                
            elif font_12.size(current_line + " " + word)[0] <= width:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
            
    return lines

def draw_text_modal(surface, game, modal, assets):
    item = modal.get('item')
    if not item:
        return None, None
        
    base_modal = BaseModal(surface, modal, assets, tr('item', item.name))
    base_modal.draw_base()
    close_button = base_modal.get_buttons()


    # --- Scroll & Content Variables ---
    scroll_offset_y = modal.get('scroll_offset_y', 0)
    line_height = font_12.get_height() + 2
    padding = 10

    # Define the content area
    content_y_start = base_modal.modal_y + base_modal.header_h + padding
    content_width = modal['rect'].width - (padding * 2) - 10 # -10 for scrollbar
    content_height = modal['rect'].height - base_modal.header_h - (padding * 2)
    content_rect = pygame.Rect(base_modal.modal_x + padding, content_y_start, content_width, content_height)
    
    modal['content_rect'] = content_rect # Store for input handling

    # --- Text Wrapping & Height Calculation ---
    raw_text = getattr(item, 'text', "This item has no text.")
    processed_text = raw_text
    
    if game.player:
        player = game.player
        
        # 1. Replace Player Name
        processed_text = processed_text.replace("[PLAYER NAME]", player.name)
        
        # 2. Replace Player Sex
        processed_text = processed_text.replace("[PLAYER SEX]", getattr(player, 'sex', 'Unknown'))
        
        # 3. Replace Traits List
        player_traits = getattr(player, 'traits', [])
        
        # Note: The "            " spaces are to match the indentation in your XML
        if player_traits:
            # Format the trait list using TRAIT_DEFINITIONS to get the actual name
            trait_list_str = "\n".join([f"            - {TRAIT_DEFINITIONS.get(trait, {}).get('name', trait.capitalize())}" for trait in player_traits])
            processed_text = processed_text.replace("- [LIST TO TRAITS]", trait_list_str)
        else:
            # If no traits, replace placeholder with "- None"
            processed_text = processed_text.replace("- [LIST TO TRAITS]", "            - None")

        # 4. Replace Recipes List
        player_recipes = getattr(player, 'known_recipes', [])
        
        if player_recipes:
            # Format the recipe list
            recipe_list_str = "\n".join([f"            - {recipe.title()}" for recipe in player_recipes])
            processed_text = processed_text.replace("- [LIST TO RECIPES]", recipe_list_str)
        else:
            # If no recipes, replace placeholder with "- None"
            processed_text = processed_text.replace("- [LIST TO RECIPES]", "            - None")
    
    text_to_display = processed_text

    wrapped_lines = wrap_text(text_to_display, content_width, font_12)
    
    total_text_height = len(wrapped_lines) * line_height

    # Calculate and store scroll limits
    max_scroll_offset = max(0, total_text_height - content_height)
    modal['max_scroll_offset'] = max_scroll_offset # Store for input.py
    
    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll_offset))
    modal['scroll_offset_y'] = scroll_offset_y # Update modal state

    # --- Draw Text (Clipped) ---
    try:
        content_surface = surface.subsurface(content_rect)
        content_surface.fill((20, 20, 20)) # Background color

        y_pos = 0 - scroll_offset_y
        for line in wrapped_lines:
            text_surface = font_12.render(line, False, WHITE)
            draw_pos_in_subsurface = (0, y_pos)
            content_surface.blit(text_surface, draw_pos_in_subsurface)
            y_pos += line_height
            
    except ValueError as e:
        print(f"Error creating subsurface for text modal: {e}. Rect: {content_rect}")
        pass # Skip drawing content if rect is invalid

    # --- Draw Scrollbar ---
    bar_rect = pygame.Rect(content_rect.right + 2, content_rect.top, 8, content_height)
    draw_scrollbar(surface, modal, bar_rect, content_height, total_text_height, scroll_offset_y)

    return None, close_button