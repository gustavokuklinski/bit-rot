import pygame
from core.data.config import GAME_WIDTH, GAME_HEIGHT

def adapt_modals_for_mobile(game):
    """
    Forces modals to be optimized for touch screens natively.
    Call this right before drawing the UI in game.py.
    """
    if not hasattr(game, 'modals') or not game.modals:
        return

    # To avoid clutter, on mobile we only allow one un-minimized modal at a time.
    # Optional logic: auto-minimize background modals
    
    for modal_data in game.modals:
        if modal_data.get('minimized'):
            continue
            
        # 1. Disable Dragging completely on mobile
        modal_data['is_dragging'] = False 
        
        # 2. Force center positioning (or full screen snapping)
        modal_w = modal_data['rect'].width
        modal_h = modal_data['rect'].height
        
        # Snap to absolute center of the screen
        center_x = (GAME_WIDTH // 2) - (modal_w // 2)
        center_y = (GAME_HEIGHT // 2) - (modal_h // 2)
        
        # Update dictionaries
        modal_data['position'] = (center_x, center_y)
        modal_data['rect'].x = center_x
        modal_data['rect'].y = center_y