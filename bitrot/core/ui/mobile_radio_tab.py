# core/ui/mobile_radio_tab.py

import pygame
from core.data.config import *
from core.data.localization import tr
from core.data.radio_manager import RadioManager

def draw_radio_tab(surface, game, modal, assets):
    # Ensure all XML radio stations are loaded and synchronized
    RadioManager.sync_game_frequencies(game)

    y_offset = modal['rect'].y + 70
    center_x = modal['rect'].centerx

    # 1. Title
    title_surf = font_12.render(tr('ui', "Radio Frequency"), False, WHITE)
    surface.blit(title_surf, title_surf.get_rect(center=(center_x, y_offset)))
    y_offset += 35

    # 2. Dynamic Frequency Range covering all stations
    station_freqs = [f for f in game.radio_frequencies.values() if isinstance(f, (int, float))]
    min_f = min([110.42] + station_freqs)
    max_f = max([123.58] + station_freqs)

    freq = getattr(game, 'current_radio_freq', min_f)
    freq = max(min_f, min(freq, max_f))

    # Frequency Text Display
    freq_surf = font_16.render(f"{freq:.2f} MHz", False, GREEN)
    surface.blit(freq_surf, freq_surf.get_rect(center=(center_x, y_offset)))
    y_offset += 45

    # 3. Slider and Navigation Buttons Layout
    track_w, track_h = 140, 10
    btn_size = 24

    track_rect = pygame.Rect(center_x - track_w // 2, y_offset, track_w, track_h)
    btn_back_rect = pygame.Rect(track_rect.left - btn_size - 8, y_offset - (btn_size - track_h) // 2, btn_size, btn_size)
    btn_fwd_rect = pygame.Rect(track_rect.right + 8, y_offset - (btn_size - track_h) // 2, btn_size, btn_size)

    # 4. Handle Mouse Interactions
    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    mouse_just_pressed = mouse_pressed and not modal.get('radio_mouse_last', False)
    modal['radio_mouse_last'] = mouse_pressed

    # Sorted list of stations for seeking
    sorted_stations = sorted(game.radio_frequencies.items(), key=lambda item: item[1])

    # Button Clicks: Back (<) and Forward (>)
    is_back_hover = btn_back_rect.collidepoint(mouse_pos)
    is_fwd_hover = btn_fwd_rect.collidepoint(mouse_pos)

    if mouse_just_pressed:
        if is_back_hover:
            # Slide to previous station
            prev_station_freq = None
            for _, st_f in reversed(sorted_stations):
                if st_f < freq - 0.05:
                    prev_station_freq = st_f
                    break
            if prev_station_freq is not None:
                game.current_radio_freq = prev_station_freq
            elif sorted_stations:
                # Wrap around to highest frequency station
                game.current_radio_freq = sorted_stations[-1][1]
            else:
                game.current_radio_freq = max(min_f, round(freq - 0.20, 2))
            freq = game.current_radio_freq

        elif is_fwd_hover:
            # Slide to next station
            next_station_freq = None
            for _, st_f in sorted_stations:
                if st_f > freq + 0.05:
                    next_station_freq = st_f
                    break
            if next_station_freq is not None:
                game.current_radio_freq = next_station_freq
            elif sorted_stations:
                # Wrap around to lowest frequency station
                game.current_radio_freq = sorted_stations[0][1]
            else:
                game.current_radio_freq = min(max_f, round(freq + 0.20, 2))
            freq = game.current_radio_freq

    # Slider Handle Position
    span = max(0.01, max_f - min_f)
    pct = (freq - min_f) / span
    handle_x = track_rect.x + int(pct * track_w)
    handle_rect = pygame.Rect(handle_x - 8, y_offset - 8, 16, 26)

    # Click-and-Drag Slider Interaction
    if 'radio_dragging' not in modal:
        modal['radio_dragging'] = False

    if mouse_pressed:
        if not (is_back_hover or is_fwd_hover):
            if handle_rect.collidepoint(mouse_pos) or track_rect.collidepoint(mouse_pos):
                modal['radio_dragging'] = True
    else:
        modal['radio_dragging'] = False

    if modal['radio_dragging']:
        new_x = max(track_rect.x, min(mouse_pos[0], track_rect.right))
        new_pct = (new_x - track_rect.x) / track_w
        raw_freq = round(min_f + new_pct * span, 2)

        # Magnetic snapping within 0.12 MHz of any station
        snapped_freq = raw_freq
        for _, st_f in sorted_stations:
            if abs(raw_freq - st_f) <= 0.12:
                snapped_freq = st_f
                break

        game.current_radio_freq = snapped_freq
        freq = snapped_freq
        handle_x = track_rect.x + int(((freq - min_f) / span) * track_w)
        handle_rect.x = handle_x - 8

    # 5. Render Buttons and Slider
    # Back Button (<)
    bg_back = GRAY_60 if is_back_hover else (35, 35, 35)
    border_back = YELLOW if is_back_hover else GRAY
    pygame.draw.rect(surface, bg_back, btn_back_rect, border_radius=4)
    pygame.draw.rect(surface, border_back, btn_back_rect, 1, border_radius=4)
    txt_back = font_12.render("<", False, YELLOW if is_back_hover else WHITE)
    surface.blit(txt_back, txt_back.get_rect(center=btn_back_rect.center))

    # Track
    pygame.draw.rect(surface, GRAY_40, track_rect, border_radius=5)
    pygame.draw.rect(surface, GRAY_60, track_rect, 1, border_radius=5)

    # Handle
    pygame.draw.rect(surface, WHITE, handle_rect, border_radius=4)
    pygame.draw.rect(surface, GRAY, handle_rect, 1, border_radius=4)

    # Forward Button (>)
    bg_fwd = GRAY_60 if is_fwd_hover else (35, 35, 35)
    border_fwd = YELLOW if is_fwd_hover else GRAY
    pygame.draw.rect(surface, bg_fwd, btn_fwd_rect, border_radius=4)
    pygame.draw.rect(surface, border_fwd, btn_fwd_rect, 1, border_radius=4)
    txt_fwd = font_12.render(">", False, YELLOW if is_fwd_hover else WHITE)
    surface.blit(txt_fwd, txt_fwd.get_rect(center=btn_fwd_rect.center))

    y_offset += 45

    # 6. Tuned Status / Noise Indication
    status_text = "[ STATIC NOISE ]"
    color = GRAY

    for name, st_freq in sorted_stations:
        if abs(freq - st_freq) <= 0.08:
            status_text = f"Tuned: {name}"
            color = ORANGE if "Exxoil" in name else (BLUE if "Military" in name else GREEN)
            break

    # Keep text pixel-sharp and truncate with ellipsis if it exceeds the modal width
    max_status_w = modal['rect'].width - 24
    if font_12.size(status_text)[0] > max_status_w:
        trimmed = status_text
        while len(trimmed) > 3 and font_12.size(trimmed + "...")[0] > max_status_w:
            trimmed = trimmed[:-1]
        status_text = trimmed + "..."

    status_surf = font_12.render(status_text, False, color)
    surface.blit(status_surf, status_surf.get_rect(center=(center_x, y_offset)))

    return []