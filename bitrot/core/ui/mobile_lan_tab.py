# core/ui/mobile_lan_tab.py

import pygame
from core.data.config import *
from core.data.localization import tr
from core.messages import display_message

def draw_lan_tab(surface, game, modal, assets):
    net_mgr = getattr(game, 'network_manager', None)
    if not net_mgr:
        return

    y_offset = modal['rect'].y + 72
    center_x = modal['rect'].centerx
    start_x = modal['rect'].x + 15
    usable_w = modal['rect'].width - 30

    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    mouse_just_pressed = mouse_pressed and not modal.get('_lan_last_mouse', False)
    modal['_lan_last_mouse'] = mouse_pressed

    # 1. Header Text: Connect LAN
    header_surf = font_12.render("Connect Remote Radio", False, WHITE)
    surface.blit(header_surf, (center_x - header_surf.get_width() // 2, y_offset))
    y_offset += 26

    # 2. Input Field: 127.0.0.1:7170
    if 'lan_input_text' not in modal:
        modal['lan_input_text'] = ""
    if 'lan_input_active' not in modal:
        modal['lan_input_active'] = False
    if 'lan_dropdown_open' not in modal:
        modal['lan_dropdown_open'] = False

    input_h = 24
    input_rect = pygame.Rect(start_x, y_offset, usable_w, input_h)
    modal['lan_input_rect'] = input_rect

    is_input_hover = input_rect.collidepoint(mouse_pos)
    is_active = modal.get('lan_input_active', False)

    # Click input to activate and show recent IPs dropdown
    if mouse_just_pressed:
        if is_input_hover:
            modal['lan_input_active'] = True
            modal['lan_dropdown_open'] = True
        else:
            # Dropdown options click check is handled below
            pass

    border_color = YELLOW if is_active else (GRAY if is_input_hover else GRAY_60)
    pygame.draw.rect(surface, (30, 30, 30), input_rect, border_radius=3)
    pygame.draw.rect(surface, border_color, input_rect, 1, border_radius=3)

    cur_text = modal.get('lan_input_text', "")
    if cur_text:
        text_surf = font_12.render(cur_text, False, WHITE)
    else:
        text_surf = font_12.render("127.0.0.1:7170", False, (120, 120, 120))

    surface.blit(text_surf, (input_rect.x + 6, input_rect.centery - text_surf.get_height() // 2))

    # Typing cursor
    if is_active and (pygame.time.get_ticks() // 500) % 2 == 0:
        cx = input_rect.x + 6 + (font_12.size(cur_text)[0] if cur_text else 0)
        pygame.draw.line(surface, WHITE, (cx, input_rect.y + 4), (cx, input_rect.bottom - 4), 1)

    y_offset += input_h + 12

    # 3. Open | Connect Buttons (Side-by-Side)
    btn_h = 32
    gap = 8
    btn_w = (usable_w - gap) // 2

    open_btn_rect = pygame.Rect(start_x, y_offset, btn_w, btn_h)
    connect_btn_rect = pygame.Rect(open_btn_rect.right + gap, y_offset, usable_w - btn_w - gap, btn_h)

    is_server = getattr(net_mgr, 'is_server', False) and net_mgr.is_connected
    is_conn = net_mgr.is_connected
    dd_open = modal.get('lan_dropdown_open', False)

    # State validation
    open_enabled = not (is_conn and not is_server) and not dd_open
    connect_enabled = not is_server and not dd_open

    is_open_hover = open_btn_rect.collidepoint(mouse_pos) and open_enabled
    is_conn_hover = connect_btn_rect.collidepoint(mouse_pos) and connect_enabled

    # --- Render Left Button (Open / Close) ---
    if is_server:
        open_bg = (200, 60, 60) if is_open_hover else (180, 50, 50)
        open_border = WHITE if is_open_hover else GRAY_60
        open_txt_col = WHITE
        open_label = tr('ui', "Close LAN")
    elif not open_enabled:
        open_bg = (35, 35, 35)
        open_border = (50, 50, 50)
        open_txt_col = (100, 100, 100)
        open_label = tr('ui', "Open LAN")
    else:
        open_bg = (65, 65, 65) if is_open_hover else (45, 45, 45)
        open_border = WHITE if is_open_hover else GRAY_60
        open_txt_col = YELLOW if is_open_hover else WHITE
        open_label = tr('ui', "Open LAN")

    pygame.draw.rect(surface, open_bg, open_btn_rect, border_radius=4)
    pygame.draw.rect(surface, open_border, open_btn_rect, 1, border_radius=4)
    open_txt_surf = font_12.render(open_label, False, open_txt_col)
    surface.blit(open_txt_surf, open_txt_surf.get_rect(center=open_btn_rect.center))

    # --- Render Right Button (Connect / Disconnect) ---
    if not connect_enabled:
        conn_bg = (35, 35, 35)
        conn_border = (50, 50, 50)
        conn_txt_col = (100, 100, 100)
        conn_label = tr('ui', "Connect")
    elif is_conn and not is_server:
        conn_bg = (200, 60, 60) if is_conn_hover else (180, 50, 50)
        conn_border = WHITE if is_conn_hover else GRAY_60
        conn_txt_col = WHITE
        conn_label = tr('ui', "Disconnect")
    else:
        conn_bg = (65, 65, 65) if is_conn_hover else (45, 45, 45)
        conn_border = WHITE if is_conn_hover else GRAY_60
        conn_txt_col = YELLOW if is_conn_hover else WHITE
        conn_label = tr('ui', "Connect")

    pygame.draw.rect(surface, conn_bg, connect_btn_rect, border_radius=4)
    pygame.draw.rect(surface, conn_border, connect_btn_rect, 1, border_radius=4)
    conn_txt_surf = font_12.render(conn_label, False, conn_txt_col)
    surface.blit(conn_txt_surf, conn_txt_surf.get_rect(center=connect_btn_rect.center))

    # --- Handle Click: Open / Close Server ---
    if mouse_just_pressed and is_open_hover:
        modal['lan_dropdown_open'] = False
        modal['lan_input_active'] = False
        if hasattr(game, 'sound_manager'):
            game.sound_manager.play_ui_hover()

        if is_server:
            net_mgr.disconnect()
            net_mgr.status_message = "Server closed"
            net_mgr.status_is_error = False
            display_message(game, "[LAN RADIO] Server closed.")
        else:
            port = 7170
            if cur_text.strip():
                if ":" in cur_text:
                    try:
                        port = int(cur_text.split(":")[-1])
                    except ValueError:
                        port = 7170
                elif cur_text.strip().isdigit():
                    port = int(cur_text.strip())
            net_mgr.open_server(port=port, max_peers=4)

    # --- Handle Click: Connect / Disconnect Client ---
    if mouse_just_pressed and is_conn_hover:
        modal['lan_dropdown_open'] = False
        modal['lan_input_active'] = False
        if hasattr(game, 'sound_manager'):
            game.sound_manager.play_ui_hover()

        if is_conn:
            net_mgr.disconnect()
            net_mgr.status_message = "Disconnected"
            net_mgr.status_is_error = False
        else:
            target_addr = cur_text if cur_text.strip() else "127.0.0.1:7170"
            net_mgr.connect_to_peer(target_addr)

    y_offset += btn_h + 16

    # 4. Status Notification Box
    status_box = pygame.Rect(start_x, y_offset, usable_w, 48)
    pygame.draw.rect(surface, (22, 22, 22), status_box, border_radius=4)
    pygame.draw.rect(surface, (50, 50, 50), status_box, 1, border_radius=4)

    msg = net_mgr.status_message
    if not msg:
        if is_conn:
            msg = f"Connected: Radio freq: {net_mgr.my_frequency:.2f}mhz"
        else:
            msg = "Ready to connect."

    msg_color = RED if net_mgr.status_is_error else (GREEN if "Connected" in msg else (180, 180, 180))
    
    # Word wrap status message if it exceeds width
    words = msg.split(" ")
    lines = []
    cur_line = ""
    for w in words:
        test = f"{cur_line} {w}".strip()
        if font_12.size(test)[0] <= usable_w - 12:
            cur_line = test
        else:
            if cur_line: lines.append(cur_line)
            cur_line = w
    if cur_line: lines.append(cur_line)

    msg_y = status_box.y + 6
    for l_str in lines:
        l_surf = font_12.render(l_str, False, msg_color)
        surface.blit(l_surf, (status_box.x + (usable_w - l_surf.get_width()) // 2, msg_y))
        msg_y += 14

    # 5. Dropdown Popup for the Last 3 Connected IPs
    if modal.get('lan_dropdown_open', False) and net_mgr.recent_ips:
        dd_items = net_mgr.recent_ips[:3]
        dd_item_h = 22
        dd_h = len(dd_items) * dd_item_h
        dd_popup_rect = pygame.Rect(input_rect.x, input_rect.bottom + 1, input_rect.width, dd_h)

        pygame.draw.rect(surface, (25, 25, 25), dd_popup_rect, border_radius=3)
        pygame.draw.rect(surface, WHITE, dd_popup_rect, 1, border_radius=3)

        for i, hist_ip in enumerate(dd_items):
            row_rect = pygame.Rect(dd_popup_rect.x, dd_popup_rect.y + i * dd_item_h, dd_popup_rect.width, dd_item_h)
            is_row_hover = row_rect.collidepoint(mouse_pos)
            if is_row_hover:
                pygame.draw.rect(surface, (55, 55, 55), row_rect)
                if mouse_just_pressed:
                    modal['lan_input_text'] = hist_ip
                    modal['lan_dropdown_open'] = False
                    modal['lan_input_active'] = False

            row_surf = font_12.render(hist_ip, False, YELLOW if is_row_hover else WHITE)
            surface.blit(row_surf, (row_rect.x + 8, row_rect.centery - row_surf.get_height() // 2))

        if mouse_just_pressed and not is_input_hover and not dd_popup_rect.collidepoint(mouse_pos):
            modal['lan_dropdown_open'] = False
            modal['lan_input_active'] = False