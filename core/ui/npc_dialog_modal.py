import pygame
from core.data.config import *
from core.ui.modals import BaseModal

# Layout Constants
COL_1_WIDTH = 180  # Width reserved for the Portrait/Stats column
PADDING = 20

def get_npc_dialog_option_rect(modal_pos, index):
    """Calculates the clickable area for a dialog option, shifted to Column 2."""
    x, y = modal_pos
    
    # [CHANGED] Shift X start position to the right of Column 1
    start_x = x + COL_1_WIDTH + PADDING
    start_y = y + 45 
    item_height = 30
    
    # [CHANGED] Reduce width to fit in the remaining space
    # Total Width - Col1 Width - Padding - Right Margin (20)
    option_width = NPC_DIALOG_MODAL_WIDTH - COL_1_WIDTH - PADDING - 20
    
    return pygame.Rect(start_x, start_y + (index * item_height), option_width, item_height)

def draw_npc_dialog_modal(surface, modal, game):
    # 1. Draw Base (Header, Background, Title)
    base = BaseModal(surface, modal, game.assets, f"Talking to: {modal['npc'].name}")
    base.draw_base()
    
    close_button, minimize_button = base.get_buttons()

    if base.minimized:
        return close_button, minimize_button

    x, y = modal['position']
    width, height = modal['rect'].size
    npc = modal['npc']
    
    # --- COLUMN 1: Portrait & Attributes ---
    
    # 1. Draw Portrait (Base + Clothes)
    # Create a surface for the portrait (assuming 32x32 tiles, scaled up 3x)
    scale_factor = 10
    if hasattr(npc, 'image') and npc.image:
        portrait_size = (npc.image.get_width() * scale_factor, npc.image.get_height() * scale_factor)
        portrait_surf = pygame.Surface(npc.image.get_size(), pygame.SRCALPHA)
        
        # Draw Base Body
        portrait_surf.blit(npc.image, (0, 0))
        
        # Draw Clothes (if available)
        if hasattr(npc, 'clothes') and npc.clothes:
            # Handle both list (older logic) or dict (newer logic) structures if uncertain, 
            # but usually it's a dict {slot: item}
            clothes_iter = npc.clothes.values() if isinstance(npc.clothes, dict) else npc.clothes
            for item in clothes_iter:
                if item and hasattr(item, 'image') and item.image:
                    portrait_surf.blit(item.image, (0, 0))
        
        # Scale and Blit to Modal
        scaled_portrait = pygame.transform.scale(portrait_surf, portrait_size)
        portrait_x = x + (COL_1_WIDTH - portrait_size[0])  # Center in Col 1
        portrait_y = y + 50
        surface.blit(scaled_portrait, (portrait_x, portrait_y))
        
        # Draw Border around portrait
        pygame.draw.rect(surface, WHITE, (portrait_x, portrait_y, portrait_size[0], portrait_size[1]), 1)
    
    # 2. Draw Attributes
    stats_start_y = y + (23 * scale_factor)
    line_height = 20
    stats_x = x + 20
    
    # Safe attribute access using getattr to prevent crashes if stats are missing
    stats = [
        f"Name: {npc.name}",
        f"HP: {npc.health}/{npc.max_health}",
        f"Vaccinated: {'Yes' if getattr(npc, 'vaccinated', False) else 'No'}"
    ]
    
    for i, stat in enumerate(stats):
        stat_surf = font.render(stat, True, WHITE)
        surface.blit(stat_surf, (stats_x, stats_start_y + (i * line_height)))

    # --- COLUMN 2: Dialog Content ---
    
    col2_x = x + COL_1_WIDTH + PADDING
    active_index = modal.get('active_dialog_index', -1)
    dialogs = modal.get('dialogs', [])

    if active_index == -1:
        # State: Showing Questions
        instruction = font.render("", True, GRAY_80)
        surface.blit(instruction, (col2_x, y + 50))
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, option in enumerate(dialogs):
            # Use the UPDATED rect function which now points to Column 2
            rect = get_npc_dialog_option_rect((x, y), i)
            
            # Hover effect
            is_hovered = rect.collidepoint(mouse_pos)
            color = YELLOW if is_hovered else WHITE
            
            # Draw Question
            q_text = font.render(f"- {option['q']}", True, color)
            
            # Clip text if it's too long
            if q_text.get_width() > rect.width:
                # Simple clipping or just let it render (pygame doesn't auto-wrap without logic)
                pass 

            surface.blit(q_text, (rect.x, rect.y + 5))
            
    else:
        # State: Showing Answer
        selected_opt = dialogs[active_index]
        
        # Draw Question (Dimmed)
        q_text = font.render(f"You: {selected_opt['q']}", True, GRAY)
        surface.blit(q_text, (col2_x, y + 50))
        
        # Draw Answer (Wrapped Text)
        a_text_str = f"{npc.name}: {selected_opt['a']}"
        
        words = a_text_str.split(' ')
        lines = []
        current_line = []
        
        # Available width for text in Column 2
        text_area_width = width - COL_1_WIDTH - PADDING - 20
        
        for word in words:
            current_line.append(word)
            test_surf = font.render(' '.join(current_line), True, WHITE)
            if test_surf.get_width() > text_area_width:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        
        start_text_y = y + 80
        for i, line in enumerate(lines):
            line_surf = font.render(line, True, WHITE)
            surface.blit(line_surf, (col2_x, start_text_y + (i * 20)))
            
        # Draw "Back" hint
        back_hint = font.render("[Click anywhere to go back]", True, YELLOW)
        # Check if the text went too far down
        hint_y = max(start_text_y + (len(lines) * 20) + 20, y + height - 30)
        surface.blit(back_hint, (col2_x, hint_y))

    return close_button, minimize_button