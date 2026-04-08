# core/android/ui_adapter.py
import pygame
from core.data.config import GAME_WIDTH, GAME_HEIGHT, INVENTORY_MODAL_HEIGHT

def adapt_modals_for_mobile(game):
    """
    Forces modals to be optimized for touch screens natively.
    Call this right before drawing the UI in game.py.
    """
    if not hasattr(game, 'modals'):
        return

    # 1. Ensure only Inventory and Nearby are open at Android startup
    if not getattr(game, '_android_startup_modals_filtered', False):
        game.modals = [m for m in game.modals if m.get('type') in ('inventory', 'nearby')]
        game._android_startup_modals_filtered = True

    # --- FIX: Tell the virtual controller to dynamically shift buttons! ---
    right_modals_open = any(m.get('type') in ('inventory', 'nearby') for m in game.modals)
    if getattr(game, 'joystick_handler', None) and hasattr(game.joystick_handler, 'update_layout'):
        game.joystick_handler.update_layout(right_modals_open)

    if not game.modals:
        return

    modals_to_remove = []
    allowed_other_modal = None

    # 1. Evaluate modals: Close minimized and restrict to ONE "other" modal
    # Iterate backwards to prioritize the most recently opened modal
    for i in range(len(game.modals) - 1, -1, -1):
        m = game.modals[i]
        
        # Rule: Make Minimize close the modal entirely
        if m.get('minimized'):
            modals_to_remove.append(m)
            continue
            
        # Rule: Only allow ONE "other" modal at a time, but keep Inventory/Nearby open
        if m.get('type') not in ('inventory', 'nearby'):
            if allowed_other_modal is None:
                allowed_other_modal = m # This is the active one, keep it
            else:
                modals_to_remove.append(m) # Close previously open modals

    # --- FIX 2: Apply removals cleanly using object identity ---
    # Python's list.remove(dict) evaluates by value, which causes the "blink" bug 
    # (removing the new modal instead of the old one). Using id() solves this.
    ids_to_remove = {id(m) for m in modals_to_remove}
    if ids_to_remove:
        game.modals = [m for m in game.modals if id(m) not in ids_to_remove]

    # 2. Enforce fixed positions & disable dragging
    for modal_data in game.modals:
        modal_data['is_dragging'] = False 
        
        if 'rect' not in modal_data:
            continue
            
        modal_w = modal_data['rect'].width
        modal_h = modal_data['rect'].height
        
        if modal_data.get('type') == 'inventory':
            # Rule: Fixed Top Right
            target_x = GAME_WIDTH - modal_w
            target_y = 0
            
        elif modal_data.get('type') == 'nearby':
            # Rule: Fixed Right Side, directly below Inventory
            target_x = GAME_WIDTH - modal_w
            target_y = INVENTORY_MODAL_HEIGHT
            
        else:
            # Rule: Any other modal must be 2px from the bottom center
            target_x = (GAME_WIDTH // 2) - (modal_w // 2)
            target_y = GAME_HEIGHT - modal_h - 2
        
        # Update coordinate dictionaries safely
        modal_data['position'] = (target_x, target_y)
        modal_data['rect'].x = target_x
        modal_data['rect'].y = target_y