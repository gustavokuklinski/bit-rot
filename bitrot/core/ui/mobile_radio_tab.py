# core/ui/mobile_radio_tab.py

import pygame
from core.data.config import *
from core.data.localization import tr

def draw_radio_tab(surface, game, modal, assets):
    y_offset = modal['rect'].y + 75
    center_x = modal['rect'].centerx

    # Title
    title_surf = font_12.render(tr('ui', "Radio Frequency"), False, WHITE)
    surface.blit(title_surf, title_surf.get_rect(center=(center_x, y_offset)))
    y_offset += 40

    # Frequency Display
    freq = getattr(game, 'current_radio_freq', 110.42)
    freq_surf = font_16.render(f"{freq:.2f} MHz", False, GREEN)
    surface.blit(freq_surf, freq_surf.get_rect(center=(center_x, y_offset)))
    y_offset += 50

    # Slider Track
    min_f, max_f = 110.42, 123.58
    track_w, track_h = 200, 10
    track_rect = pygame.Rect(center_x - track_w//2, y_offset, track_w, track_h)
    pygame.draw.rect(surface, GRAY_40, track_rect, border_radius=5)
    pygame.draw.rect(surface, GRAY_60, track_rect, 1, border_radius=5)

    # Slider Handle Position
    pct = (freq - min_f) / (max_f - min_f)
    handle_x = track_rect.x + int(pct * track_w)
    handle_rect = pygame.Rect(handle_x - 8, y_offset - 8, 16, 26)

    # Handle Mouse Interaction
    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]

    if 'radio_dragging' not in modal:
        modal['radio_dragging'] = False

    if mouse_pressed:
        if handle_rect.collidepoint(mouse_pos) or track_rect.collidepoint(mouse_pos):
            modal['radio_dragging'] = True
    else:
        modal['radio_dragging'] = False

    if modal['radio_dragging']:
        new_x = max(track_rect.x, min(mouse_pos[0], track_rect.right))
        new_pct = (new_x - track_rect.x) / track_w
        game.current_radio_freq = round(min_f + new_pct * (max_f - min_f), 2)
        handle_x = track_rect.x + int(new_pct * track_w)
        handle_rect.x = handle_x - 8

    # Draw Handle
    pygame.draw.rect(surface, WHITE, handle_rect, border_radius=4)
    pygame.draw.rect(surface, GRAY, handle_rect, 1, border_radius=4)
    
    y_offset += 60

    # Status / Noise Indication
    status_text = "[ STATIC NOISE ]"
    color = GRAY
    
    if hasattr(game, 'radio_frequencies'):
        # Sort colors based on name roughly for nice UI visual matching
        for name, st_freq in game.radio_frequencies.items():
            if abs(freq - st_freq) <= 0.05:
                status_text = f"Tuned: {name}"
                color = ORANGE if "Exxoil" in name else (BLUE if "Military" in name else GREEN)
                break
    
    status_surf = font_12.render(status_text, False, color)
    surface.blit(status_surf, status_surf.get_rect(center=(center_x, y_offset)))
    
    return []