import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.text_modal import wrap_text

TUTORIAL_TEXT = """=== BIT ROT SURVIVAL GUIDE ===

[ COMMANDS & KEYBINDINGS ]
• W, A, S, D : Move your character
• E : Interact: Talk to NPCs, Open/Close Doors/Windows, Enter Vehicles, Use Stairs
• 1 to 5 : Use or Equip item from your Belt
• LCTRL / RCTRL / Right Mouse Button : Aim Weapon
• Left Click (while aiming) : Attack / Shoot / Melee
• Right Click (on items) : Context Menu (Equip, Drop, Consume)
• F2 : Pause / Save Menu
• F3 : Fast Forward Time
• Space : Wake up from sleep
• ? or / : Open this Help menu

[ INTERFACE SHORTCUTS ]
• I : Inventory - Player inventory and backpack
• H : Status - Player status
• G : Gear - Player clothes
• N : Nearby - Nearby items from containers
• M : Messages - Events happening in game
• C : Crafting - Craft recipes

[ INVENTORY & DRAG-DROP ]
• Left-click and hold an item to drag it across slots.
• Drop items into your Belt for quick access (keys 1-5).
• Drop items into the Gear menu to equip clothing and armor.
• Drop items outside the UI (world) to discard them.

[ PLAYER STATUS ]
• Health: Keep it above 0. Use bandages or meds to heal.
• Stamina: Depletes when running or attacking. Recovers when standby.
• Hunger & Thirst: Scavenge for food and water to stay alive.
• Tireness: Find a bed or safe place to sleep when exhausted.
• Infection: If hit by zombies, find antibiotics quickly!

[ USEFUL TIPS ]
• Vehicles: Approach a vehicle and press 'E' to enter. Press 'Q' to toggle the engine on/off - Remember to check Mechanics!
• Crafting: Open the Crafting menu ('C') to combine items and survive - Read books and collect Blueprints.
• Combat: Always aim before attacking.
• Lighting: Turn on the Mobile in your inventory or belt to see clearly at night.
"""

def draw_help_modal(surface, game, modal, assets):
    base_modal = BaseModal(surface, modal, assets, "Help & Tutorial (?)")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        return None, close_button, minimize_button

    # --- Scroll & Content Variables ---
    scroll_offset_y = modal.get('scroll_offset_y', 0)
    line_height = font_small.get_height() + 4
    padding = 15

    content_y_start = base_modal.modal_y + base_modal.header_h + padding
    content_width = modal['rect'].width - (padding * 2) - 15 # -15 for scrollbar
    content_height = modal['rect'].height - base_modal.header_h - (padding * 2)
    content_rect = pygame.Rect(base_modal.modal_x + padding, content_y_start, content_width, content_height)
    modal['content_rect'] = content_rect 

    # --- Text Wrapping & Height Calculation ---
    wrapped_lines = wrap_text(TUTORIAL_TEXT, content_width, font_small)
    total_text_height = len(wrapped_lines) * line_height

    max_scroll_offset = max(0, total_text_height - content_height)
    modal['max_scroll_offset'] = max_scroll_offset 
    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll_offset))
    modal['scroll_offset_y'] = scroll_offset_y

    # --- Draw Text ---
    try:
        content_surface = surface.subsurface(content_rect)
        y_pos = 0 - scroll_offset_y
        for line in wrapped_lines:
            text_surface = font_small.render(line, True, WHITE)
            content_surface.blit(text_surface, (0, y_pos))
            y_pos += line_height
    except ValueError:
        pass 

    # --- Draw Scrollbar ---
    if total_text_height > content_height:
        scrollbar_area_rect = pygame.Rect(content_rect.right + 5, content_rect.top, 8, content_height)
        handle_height = max(20, content_height * (content_height / total_text_height))
        handle_pos_ratio = scroll_offset_y / max_scroll_offset if max_scroll_offset > 0 else 0
        handle_y = scrollbar_area_rect.top + (content_height - handle_height) * handle_pos_ratio
        
        scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        pygame.draw.rect(surface, GRAY, scrollbar_handle_rect, 0, 4)
        modal['scrollbar_handle_rect'] = scrollbar_handle_rect
    else:
        modal['scrollbar_handle_rect'] = None

    return None, close_button, minimize_button