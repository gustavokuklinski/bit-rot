import pygame
import os
import core.data.config 
from core.data.config import *
from core.entities.item.item_data import ITEM_TEMPLATES
from core.ui.tooltip import draw_tooltip

def draw_mp3_tab(surface, game, modal, assets):
    # Initialize MP3 State within the game object to persist playback state
    if not hasattr(game, 'mp3_state'):
        game.mp3_state = {
            'slots': [None] * 5, 
            'playing_idx': -1,
            'status': 'stopped',
            'volume': 1.0,
            'track_lengths': {}
        }
        
    state = game.mp3_state

    # --- Auto-Play Next Track Logic ---
    try:
        # If status is playing, but the music stream finished natively, advance automatically!
        if state['status'] == 'playing' and not pygame.mixer.music.get_busy():
            handle_control(game, 'next')
    except Exception:
        pass

    y_offset = modal['rect'].y + 80
    center_x = modal['rect'].centerx

    # Local debouncer to prevent rapid multi-clicks
    if 'mp3_mouse_down' not in modal:
        modal['mp3_mouse_down'] = False
        
    mouse_pressed = pygame.mouse.get_pressed()[0]
    mouse_pos = getattr(game, 'scaled_mouse_pos', pygame.mouse.get_pos())
    
    clicked = mouse_pressed and not modal['mp3_mouse_down']
    modal['mp3_mouse_down'] = mouse_pressed

    # Determine if this modal is the top-most one under the mouse cursor
    is_top_modal = True
    for m in reversed(game.modals):
        if m['rect'].collidepoint(mouse_pos):
            if m.get('id') != modal.get('id'):
                is_top_modal = False
            break

    # Cache for mouse_drag.py and tooltips
    modal['mp3_slot_rects'] = []
    hovered_item = None

    # --- Draw the 5 SD Card Slots ---
    slot_size = 40
    gap = 6
    total_width = (slot_size * 5) + (gap * 4)
    start_x = center_x - (total_width // 2)

    for i in range(5):
        slot_rect = pygame.Rect(start_x + i * (slot_size + gap), y_offset, slot_size, slot_size)
        
        modal['mp3_slot_rects'].append({'rect': slot_rect, 'index': i})
        
        # Fill background with GRAY_40 to match inventory slots
        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        
        # Default border is GRAY, changes to WHITE when highlighted or GREEN if playing
        border_color = GRAY
        if state['playing_idx'] == i and state['status'] != 'stopped':
            border_color = GREEN
        elif getattr(game, 'is_dragging', False) and slot_rect.collidepoint(mouse_pos) and is_top_modal:
            border_color = WHITE # Highlight color
            
        pygame.draw.rect(surface, border_color, slot_rect, 1, 3)

        # Render item inside slot
        item = state['slots'][i]
        if item:
            if getattr(item, 'image', None):
                surface.blit(pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8)), slot_rect.move(4, 4))
            else:
                text_surf = font_14.render("SD", True, YELLOW)
                surface.blit(text_surf, text_surf.get_rect(center=slot_rect.center))
                
            if slot_rect.collidepoint(mouse_pos) and is_top_modal:
                hovered_item = item

        # Handle Interaction with Slots (Play manually)
        if clicked and slot_rect.collidepoint(mouse_pos) and not getattr(game, 'is_dragging', False) and is_top_modal:
            if state['slots'][i]:
                play_track(game, i)

    y_offset += slot_size + 20

    # --- Draw Playback Controls ---
    control_w = 40
    control_h = 30
    control_padding = 8
    
    controls = [
        {'label': '«', 'action': 'prev'},
        {'label': '||' if state['status'] == 'playing' else '►', 'action': 'play_pause'},
        {'label': '■', 'action': 'stop'},
        {'label': '»', 'action': 'next'}
    ]
    
    total_ctrl_w = (control_w * len(controls)) + (control_padding * (len(controls) - 1))
    ctrl_start_x = center_x - (total_ctrl_w // 2)

    for i, ctrl in enumerate(controls):
        ctrl_rect = pygame.Rect(ctrl_start_x + i * (control_w + control_padding), y_offset, control_w, control_h)
        
        # UI Hover
        color = GRAY_60
        if ctrl_rect.collidepoint(mouse_pos) and is_top_modal:
            color = GRAY_40
            if clicked:
                handle_control(game, ctrl['action'])
                
        pygame.draw.rect(surface, color, ctrl_rect, 0, 3)
        pygame.draw.rect(surface, WHITE, ctrl_rect, 1, 3)

        text_surf = font_14.render(ctrl['label'], True, WHITE)
        surface.blit(text_surf, text_surf.get_rect(center=ctrl_rect.center))

    y_offset += control_h + 15
    
    # --- Draw Volume Controls ---
    vol_w = 30
    vol_h = 25
    vol_padding = 10
    vol_text = f"Vol: {int(state['volume'] * 100)}%"
    vol_text_surf = font_14.render(vol_text, True, WHITE)
    
    total_vol_w = vol_w * 2 + vol_padding * 2 + vol_text_surf.get_width()
    vol_start_x = center_x - (total_vol_w // 2)

    # Vol Down Button
    btn_down = pygame.Rect(vol_start_x, y_offset, vol_w, vol_h)
    col_down = GRAY_40 if btn_down.collidepoint(mouse_pos) and is_top_modal else GRAY_60
    pygame.draw.rect(surface, col_down, btn_down, 0, 3)
    pygame.draw.rect(surface, WHITE, btn_down, 1, 3)
    lbl_down = font_14.render("-", True, WHITE)
    surface.blit(lbl_down, lbl_down.get_rect(center=btn_down.center))
    if clicked and btn_down.collidepoint(mouse_pos) and is_top_modal:
        handle_control(game, 'vol_down')

    # Vol Label
    text_x = vol_start_x + vol_w + vol_padding
    surface.blit(vol_text_surf, (text_x, y_offset + (vol_h - vol_text_surf.get_height()) // 2))

    # Vol Up Button
    btn_up = pygame.Rect(text_x + vol_text_surf.get_width() + vol_padding, y_offset, vol_w, vol_h)
    col_up = GRAY_40 if btn_up.collidepoint(mouse_pos) and is_top_modal else GRAY_60
    pygame.draw.rect(surface, col_up, btn_up, 0, 3)
    pygame.draw.rect(surface, WHITE, btn_up, 1, 3)
    lbl_up = font_14.render("+", True, WHITE)
    surface.blit(lbl_up, lbl_up.get_rect(center=btn_up.center))
    if clicked and btn_up.collidepoint(mouse_pos) and is_top_modal:
        handle_control(game, 'vol_up')

    y_offset += vol_h + 20
    
    # --- Currently Playing UI Info ---
    if state['playing_idx'] != -1 and state['slots'][state['playing_idx']]:
        item = state['slots'][state['playing_idx']]
        item_name = getattr(item, 'name', '') if hasattr(item, 'name') else item.get('name', 'Unknown') if isinstance(item, dict) else str(item)
        
        # Load audio duration dynamically if we know the path
        length_str = ""
        template = ITEM_TEMPLATES.get(item_name)
        if template and 'audio' in template.get('properties', {}):
            audio_path = SOUND_PATH + template['properties']['audio'].get('value')
            if audio_path in state['track_lengths']:
                length = state['track_lengths'][audio_path]
                mins = int(length // 60)
                secs = int(length % 60)
                length_str = f" ({mins}:{secs:02d})"
                
        status_text = "Playing: " if state['status'] == 'playing' else "Paused: "
        
        # Truncate and assemble text safely
        display_text = status_text + item_name
        if len(display_text) > 25:
            display_text = display_text[:22] + "..."
            
        display_text += length_str
            
        track_surf = font_14.render(display_text, True, WHITE)
        surface.blit(track_surf, track_surf.get_rect(center=(center_x, y_offset)))
        
    # --- Render Tooltip over everything else ---
    if hovered_item and not getattr(game, 'is_dragging', False):
        draw_tooltip(surface, hovered_item, mouse_pos)
        
    return []

# --- Logic Controllers ---
def play_track(game, index):
    state = game.mp3_state
    item = state['slots'][index]
    if not item: return
    
    item_name = getattr(item, 'name', '') if hasattr(item, 'name') else item.get('name', '') if isinstance(item, dict) else str(item)
    template = ITEM_TEMPLATES.get(item_name)
    
    if template and 'audio' in template.get('properties', {}):
        audio_path = SOUND_PATH + template['properties']['audio'].get('value')
        if audio_path:
            # Pre-load length metrics
            if audio_path not in state['track_lengths']:
                try:
                    snd = pygame.mixer.Sound(audio_path)
                    state['track_lengths'][audio_path] = snd.get_length()
                except Exception:
                    state['track_lengths'][audio_path] = 0

            try:
                # Bypass SoundManager to prevent endless loop hijacks. 
                # Play strictly once (0) so the native get_busy() flag drops correctly when complete.
                pygame.mixer.music.stop()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.set_volume(state.get('volume', 1.0) * core.data.config.VOLUME_MUSIC)
                pygame.mixer.music.play(0)
                
                # Check that it actually started properly (prevents broken audio file infinite loop spam)
                if pygame.mixer.music.get_busy():
                    state['playing_idx'] = index
                    state['status'] = 'playing'
                else:
                    state['status'] = 'stopped'
            except Exception:
                state['status'] = 'stopped'

def handle_control(game, action):
    state = game.mp3_state
    
    if action == 'play_pause':
        if state['status'] == 'playing':
            pygame.mixer.music.pause()
            state['status'] = 'paused'
        elif state['status'] == 'paused':
            pygame.mixer.music.unpause()
            state['status'] = 'playing'
        else:
            # Resume or play first available when stopped
            idx = max(0, state['playing_idx'])
            if state['slots'][idx]:
                play_track(game, idx)
            else:
                for i in range(5):
                    if state['slots'][i]:
                        play_track(game, i)
                        break
                        
    elif action == 'stop':
        pygame.mixer.music.stop()
        state['status'] = 'stopped'
        
    elif action == 'next':
        idx = max(0, state['playing_idx'])
        played = False
        for _ in range(5):
            idx = (idx + 1) % 5
            if state['slots'][idx]:
                play_track(game, idx)
                # Ensure the newly loaded track is verified functioning before marking as handled
                if state['status'] == 'playing':
                    played = True
                    break
        if not played:
            pygame.mixer.music.stop()
            state['status'] = 'stopped'
                
    elif action == 'prev':
        idx = max(0, state['playing_idx'])
        played = False
        for _ in range(5):
            idx = (idx - 1) % 5
            if state['slots'][idx]:
                play_track(game, idx)
                # Ensure the newly loaded track is verified functioning before marking as handled
                if state['status'] == 'playing':
                    played = True
                    break
        if not played:
            pygame.mixer.music.stop()
            state['status'] = 'stopped'
                
    elif action == 'vol_down':
        state['volume'] = max(0.0, round(state['volume'] - 0.1, 1))
        pygame.mixer.music.set_volume(state['volume'] * core.data.config.VOLUME_MUSIC)
        
    elif action == 'vol_up':
        state['volume'] = min(2.0, round(state['volume'] + 0.1, 1)) 
        pygame.mixer.music.set_volume(state['volume'] * core.data.config.VOLUME_MUSIC)