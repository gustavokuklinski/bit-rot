# core/ui/messages_modal.py
import pygame
from core.data.config import *
from core.ui.modals import BaseModal, draw_scrollbar
from core.data.radio_manager import RadioManager
from core.data.localization import tr
from core.ui.messages_debug_tab import draw_messages_debug_tab
from core.entities.item.item_helpers import player_has_mobile

def draw_messages_modal(surface, game, modal, assets):
    modal_w = modal['rect'].width if 'rect' in modal else MESSAGES_MODAL_WIDTH
    modal_h = modal['rect'].height if 'rect' in modal else MESSAGES_MODAL_HEIGHT
    base_modal = BaseModal(surface, modal, assets, "Messages", w=modal_w, h=modal_h)
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()

    # Dynamic frequency label for the Radio tab
    current_freq = getattr(game, 'current_radio_freq', 110.42)
    radio_tab_label = f"Radio {current_freq:.2f}mhz"

    # Check conditions for dynamic tabs
    has_mobile = player_has_mobile(game.player) if getattr(game, 'player', None) else False
    has_debug = getattr(game, 'debug_tab_unlocked', False)

    # Build tabs: All | Radio [FREQ]mhz (only if player has mobile) | Debug (only if %rot debug typed)
    tab_keys = ['All']
    if has_mobile:
        tab_keys.append('Radio')
    if has_debug:
        tab_keys.append('Debug')

    # Normalize active tab state (revert to 'All' if mobile is lost)
    if 'active_tab' not in modal or modal['active_tab'] not in tab_keys:
        modal['active_tab'] = 'All'

    # --- Draw Tab Headers ---
    tab_bar_h = 22
    tab_y = base_modal.modal_y + base_modal.header_h + 2
    modal['tab_rects'] = []
    modal['tabs_data'] = []

    cur_x = base_modal.modal_x + 5
    for t_key in tab_keys:
        if t_key == 'Radio':
            disp_label = radio_tab_label
            btn_w = font_12.size(disp_label)[0] + 16
        else:
            disp_label = t_key
            btn_w = 60

        t_rect = pygame.Rect(cur_x, tab_y, btn_w, tab_bar_h)
        modal['tab_rects'].append(t_rect)
        modal['tabs_data'].append({'label': t_key, 'display': disp_label, 'rect': t_rect})

        is_act = (modal['active_tab'] == t_key)
        is_hov = t_rect.collidepoint(mouse_pos)

        bg = (55, 55, 55) if is_act else ((40, 40, 40) if is_hov else (25, 25, 25))
        pygame.draw.rect(surface, bg, t_rect, border_radius=3)
        pygame.draw.rect(surface, YELLOW if is_act else GRAY_60, t_rect, 1, border_radius=3)

        txt_col = YELLOW if is_act else (WHITE if is_hov else (170, 170, 170))
        t_surf = font_12.render(disp_label, False, txt_col)
        surface.blit(t_surf, t_surf.get_rect(center=t_rect.center))
        cur_x += btn_w + 4

    # Content Area Position
    content_y_start = tab_y + tab_bar_h + 4
    padding = 5
    input_height = 30
    send_btn_width = 50

    input_area_y = modal['rect'].bottom - input_height - padding
    content_height = input_area_y - content_y_start - padding
    content_width = modal['rect'].width - (padding * 2)
    content_rect = pygame.Rect(base_modal.modal_x + padding, content_y_start, content_width, content_height)
    modal['content_rect'] = content_rect

    send_btn_rect = pygame.Rect(
        base_modal.modal_x + modal['rect'].width - padding - send_btn_width,
        input_area_y,
        send_btn_width,
        input_height
    )
    input_rect = pygame.Rect(
        base_modal.modal_x + padding,
        input_area_y,
        modal['rect'].width - (padding * 2) - send_btn_width - 5,
        input_height
    )

    send_button = {'id': modal['id'], 'type': 'send_msg', 'rect': send_btn_rect}
    input_button = {'id': modal['id'], 'type': 'chat_input', 'rect': input_rect}

    # ==============================================================
    # RENDER TAB: DEBUG
    # ==============================================================
    if modal['active_tab'] == 'Debug' and has_debug:
        draw_messages_debug_tab(surface, game, modal, mouse_pos, content_rect)
        return None, close_button, send_button, input_button

    # ==============================================================
    # RENDER TAB: ALL OR RADIO
    # ==============================================================
    if modal['active_tab'] == 'Radio' and has_mobile:
        # Retrieve radio messages matching current frequency
        target_freq_tag = f"{current_freq:.2f}mhz"
        raw_radio_msgs = game.message_logs.get('Radio', [])
        
        # Match station frequencies or specific broadcast tags
        radio_stations = RadioManager.STATIONS if hasattr(RadioManager, 'STATIONS') else {}
        freq_station_names = [
            st_name for st_name, st_f in getattr(game, 'radio_frequencies', {}).items()
            if abs(float(st_f) - current_freq) <= 0.05
        ]

        active_log = []
        for msg in raw_radio_msgs:
            msg_str = str(msg)
            # 1. Packet format: [Radio 110.42mhz]
            if target_freq_tag in msg_str.lower():
                active_log.append(msg)
            # 2. Station format: Exxoil: ...
            elif any(msg_str.startswith(st + ":") for st in freq_station_names):
                active_log.append(msg)
    else:
        active_log = game.message_logs.get('All', [])

    def wrap_text(text, font_12, max_width):
        lines = []
        for paragraph in str(text).split('\n'):
            words = paragraph.split(' ')
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word]) if current_line else word
                if font_12.size(test_line)[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)
                        current_line = []
            if current_line:
                lines.append(' '.join(current_line))
        return lines

    max_text_width = max(50, content_width - 15)
    wrapped_log = []

    radio_stations = list(RadioManager.STATIONS.keys()) if hasattr(RadioManager, 'STATIONS') else []

    for msg in active_log:
        color = WHITE
        if msg.startswith("[Radio "):
            color = (50, 220, 255)
        elif msg.startswith("[") and "]: " in msg:
            color = YELLOW
        else:
            for st_name in radio_stations:
                if msg.startswith(st_name + ":"):
                    if "Exxoil" in st_name:
                        color = ORANGE
                    elif "Military" in st_name:
                        color = (100, 200, 255)
                    else:
                        color = (100, 255, 100)
                    break

        for line in wrap_text(msg, font_12, max_text_width):
            wrapped_log.append((line, color))

    line_height = font_12.get_height() + 4
    total_text_height = len(wrapped_log) * line_height
    max_scroll = max(0, total_text_height - content_height)

    # Track independent scroll offset per tab
    tab_suffix = modal['active_tab']
    log_len_key = f"last_len_{tab_suffix}"
    scroll_key = f"scroll_offset_y_{tab_suffix}"
    current_len = len(active_log)
    last_len = modal.get(log_len_key, 0)

    if current_len > last_len:
        modal[scroll_key] = max_scroll
        modal[log_len_key] = current_len
    elif log_len_key not in modal:
        modal[log_len_key] = current_len
        if scroll_key not in modal:
            modal[scroll_key] = max_scroll

    modal[log_len_key] = current_len
    modal[scroll_key] = max(0, min(modal.get(scroll_key, max_scroll), max_scroll))
    modal['scroll_offset_y'] = modal[scroll_key]

    try:
        content_surface = surface.subsurface(content_rect)
        content_surface.fill((20, 20, 20))

        if total_text_height < content_height:
            y_pos = content_height - total_text_height
        else:
            y_pos = -modal['scroll_offset_y']

        start_index = 0
        if y_pos < 0:
            skip_count = int(abs(y_pos) // line_height)
            start_index = skip_count
            y_pos += skip_count * line_height

        for i in range(start_index, len(wrapped_log)):
            msg_text, msg_color = wrapped_log[i]
            if y_pos > content_height:
                break
            txt_surf = font_12.render(msg_text, False, msg_color)
            content_surface.blit(txt_surf, (5, y_pos))
            y_pos += line_height

    except Exception:
        pass

    # Draw Scrollbar
    bar_rect = pygame.Rect(content_rect.right - 6, content_rect.top, 8, content_rect.height)
    draw_scrollbar(surface, modal, bar_rect, content_height, total_text_height, modal['scroll_offset_y'])

    # --- Draw Input Box ---
    border_col = YELLOW if game.chat_active else GRAY
    pygame.draw.rect(surface, (0, 0, 0), input_rect)
    pygame.draw.rect(surface, border_col, input_rect, 1)

    input_surf = font_12.render(game.chat_input_text, False, WHITE)
    area_width = input_rect.width - 10
    if input_surf.get_width() > area_width:
        crop_area = pygame.Rect(input_surf.get_width() - area_width, 0, area_width, input_surf.get_height())
        surface.blit(input_surf, (input_rect.x + 5, input_rect.y + 5), crop_area)
    else:
        surface.blit(input_surf, (input_rect.x + 5, input_rect.y + 5))

    if game.chat_active and (pygame.time.get_ticks() // 500) % 2 == 0:
        cursor_x = input_rect.x + 5 + min(input_surf.get_width(), area_width)
        pygame.draw.line(surface, WHITE, (cursor_x, input_rect.y + 5), (cursor_x, input_rect.bottom - 5))

    # --- Draw Send Button ---
    is_hovered = send_btn_rect.collidepoint(pygame.mouse.get_pos())
    btn_col = GRAY_80 if is_hovered else GRAY_60
    pygame.draw.rect(surface, btn_col, send_btn_rect, border_radius=4)
    pygame.draw.rect(surface, WHITE, send_btn_rect, 1, border_radius=4)

    send_txt = font_12.render("Send", False, WHITE)
    txt_rect = send_txt.get_rect(center=send_btn_rect.center)
    surface.blit(send_txt, txt_rect)

    return None, close_button, send_button, input_button