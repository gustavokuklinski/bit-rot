# core/ui/mobile_radio_tab.py

import pygame
import math
import threading
from core.data.config import *
from core.data.localization import tr
from core.data.radio_manager import RadioManager

def get_all_radio_targets(game):
    """
    Collects and sorts all valid radio frequencies:
    - Base XML radio stations (from game.radio_frequencies)
    - Connected LAN VOIP peers/server (from game.network_manager)
    Returns: (sorted_freqs, freq_info_map)
    """
    # Ensure XML stations are synchronized
    RadioManager.sync_game_frequencies(game)

    freq_info_map = {}

    # 1. Base Radio Stations
    for name, st_f in getattr(game, 'radio_frequencies', {}).items():
        if isinstance(st_f, (int, float)):
            f_key = round(float(st_f), 2)
            freq_info_map.setdefault(f_key, []).append({
                'name': name,
                'type': 'station',
                'color': ORANGE if "Exxoil" in name else ((100, 200, 255) if "Military" in name else GREEN)
            })

    # 2. Connected LAN VOIP Peers & Host Frequency
    net_mgr = getattr(game, 'network_manager', None)
    if net_mgr and getattr(net_mgr, 'is_connected', False):
        # Local player's own broadcast frequency
        my_f = round(float(getattr(net_mgr, 'my_frequency', 114.0)), 2)
        freq_info_map.setdefault(my_f, []).append({
            'name': f"My Radio ({my_f:.2f} MHz)",
            'type': 'self',
            'color': (0, 255, 255)
        })

        # Connected remote peers
        lock = getattr(net_mgr, 'peer_lock', None)
        peers_copy = []
        if lock:
            with lock:
                peers_copy = list(getattr(net_mgr, 'connected_peers', []))
        else:
            peers_copy = list(getattr(net_mgr, 'connected_peers', []))

        for p in peers_copy:
            p_freq = p.get('freq')
            if p_freq is not None:
                f_key = round(float(p_freq), 2)
                p_role = p.get('role', 'C')
                p_ip = p.get('ip', 'LAN')
                label = f"Survivor [{p_role}] ({p_ip})"
                freq_info_map.setdefault(f_key, []).append({
                    'name': label,
                    'type': 'peer',
                    'color': (50, 255, 120) if p_role == 'S' else (0, 220, 255)
                })

    # Fallback if no stations exist
    if not freq_info_map:
        freq_info_map[114.20] = [{'name': 'Emergency Broadcast', 'type': 'station', 'color': GREEN}]

    sorted_freqs = sorted(freq_info_map.keys())
    return sorted_freqs, freq_info_map


def draw_radio_tab(surface, game, modal, assets):
    sorted_freqs, freq_info_map = get_all_radio_targets(game)

    min_f = sorted_freqs[0]
    max_f = sorted_freqs[-1]
    span = max(0.01, max_f - min_f)

    y_offset = modal['rect'].y + 70
    center_x = modal['rect'].centerx

    # 1. Title
    title_surf = font_12.render(tr('ui', "Radio Frequency"), False, WHITE)
    surface.blit(title_surf, title_surf.get_rect(center=(center_x, y_offset)))
    y_offset += 35

    # 2. Current Frequency (Snap to valid list if uninitialized or out of bounds)
    freq = getattr(game, 'current_radio_freq', None)
    if freq is None or not any(abs(freq - f_cand) < 0.001 for f_cand in sorted_freqs):
        # Snap to closest existing valid frequency
        closest_f = min(sorted_freqs, key=lambda f_val: abs(f_val - (freq if freq is not None else min_f)))
        game.current_radio_freq = closest_f
        freq = closest_f

    # Frequency Text Display
    freq_surf = font_16.render(f"{freq:.2f} MHz", False, GREEN)
    surface.blit(freq_surf, freq_surf.get_rect(center=(center_x, y_offset)))
    y_offset += 45

    # 3. Slider Track and Button Layout
    track_w, track_h = 140, 10
    btn_size = 24

    track_rect = pygame.Rect(center_x - track_w // 2, y_offset, track_w, track_h)
    btn_back_rect = pygame.Rect(track_rect.left - btn_size - 8, y_offset - (btn_size - track_h) // 2, btn_size, btn_size)
    btn_fwd_rect = pygame.Rect(track_rect.right + 8, y_offset - (btn_size - track_h) // 2, btn_size, btn_size)

    # 4. Mouse Interactions
    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    mouse_just_pressed = mouse_pressed and not modal.get('radio_mouse_last', False)
    modal['radio_mouse_last'] = mouse_pressed

    is_back_hover = btn_back_rect.collidepoint(mouse_pos)
    is_fwd_hover = btn_fwd_rect.collidepoint(mouse_pos)

    # Find current index in discrete frequency list
    cur_idx = min(range(len(sorted_freqs)), key=lambda i: abs(sorted_freqs[i] - freq))

    # --- ONE-BY-ONE ARROW LOOPING ---
    if mouse_just_pressed:
        if is_back_hover:
            new_idx = (cur_idx - 1) % len(sorted_freqs)
            game.current_radio_freq = sorted_freqs[new_idx]
            freq = game.current_radio_freq
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()

        elif is_fwd_hover:
            new_idx = (cur_idx + 1) % len(sorted_freqs)
            game.current_radio_freq = sorted_freqs[new_idx]
            freq = game.current_radio_freq
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()

    # Slider Handle Geometry
    pct = (freq - min_f) / span if span > 0 else 0.5
    handle_x = track_rect.x + int(pct * track_w)
    handle_rect = pygame.Rect(handle_x - 8, y_offset - 8, 16, 26)

    # --- SLIDER DRAG SNAPPING (Discrete step-by-step) ---
    if 'radio_dragging' not in modal:
        modal['radio_dragging'] = False

    if mouse_pressed:
        if not (is_back_hover or is_fwd_hover):
            if handle_rect.collidepoint(mouse_pos) or track_rect.collidepoint(mouse_pos):
                modal['radio_dragging'] = True
    else:
        modal['radio_dragging'] = False

    if modal['radio_dragging']:
        clamped_x = max(track_rect.x, min(mouse_pos[0], track_rect.right))
        drag_pct = (clamped_x - track_rect.x) / float(track_w)
        target_f = min_f + (drag_pct * span)

        # Snap directly to the closest valid frequency
        snapped_f = min(sorted_freqs, key=lambda f_val: abs(f_val - target_f))
        
        if snapped_f != game.current_radio_freq:
            game.current_radio_freq = snapped_f
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()

        freq = game.current_radio_freq
        pct = (freq - min_f) / span if span > 0 else 0.5
        handle_x = track_rect.x + int(pct * track_w)
        handle_rect.x = handle_x - 8

    # 5. Render Buttons and Slider
    # Back Button (<)
    bg_back = GRAY_60 if is_back_hover else (35, 35, 35)
    border_back = YELLOW if is_back_hover else GRAY
    pygame.draw.rect(surface, bg_back, btn_back_rect, border_radius=4)
    pygame.draw.rect(surface, border_back, btn_back_rect, 1, border_radius=4)
    txt_back = font_12.render("<", False, YELLOW if is_back_hover else WHITE)
    surface.blit(txt_back, txt_back.get_rect(center=btn_back_rect.center))

    # Track Background
    pygame.draw.rect(surface, GRAY_40, track_rect, border_radius=5)
    pygame.draw.rect(surface, GRAY_60, track_rect, 1, border_radius=5)

    # Dial Frequency Ticks on the Track
    for f_val in sorted_freqs:
        t_pct = (f_val - min_f) / span if span > 0 else 0.5
        tick_x = track_rect.x + int(t_pct * track_w)
        
        is_peer_target = any(info['type'] in ('peer', 'self') for info in freq_info_map.get(f_val, []))
        tick_color = (0, 220, 255) if is_peer_target else (120, 120, 120)
        tick_h = 6 if is_peer_target else 4
        pygame.draw.line(surface, tick_color, (tick_x, track_rect.centery - tick_h // 2), (tick_x, track_rect.centery + tick_h // 2), 1)

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

    # 6. Tuned Status Display
    status_text = "[ STATIC NOISE ]"
    color = GRAY

    # Exact match lookup
    target_entries = freq_info_map.get(freq, [])
    if not target_entries:
        # Near match fallback
        for f_val, entries in freq_info_map.items():
            if abs(freq - f_val) <= 0.05:
                target_entries = entries
                break

    if target_entries:
        entry = target_entries[0]
        status_text = f"Tuned: {entry['name']}"
        color = entry['color']

    # Text wrapping and truncation
    max_status_w = modal['rect'].width - 24
    if font_12.size(status_text)[0] > max_status_w:
        trimmed = status_text
        while len(trimmed) > 3 and font_12.size(trimmed + "...")[0] > max_status_w:
            trimmed = trimmed[:-1]
        status_text = trimmed + "..."

    status_surf = font_12.render(status_text, False, color)
    surface.blit(status_surf, status_surf.get_rect(center=(center_x, y_offset)))

    return []