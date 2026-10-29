# core/ui/messages_debug_tab.py

import pygame
from core.data.config import *
from core.data.localization import tr
from core.entities.item.item_data import ITEM_TEMPLATES, load_item_templates_data
from core.entities.vehicle.vehicle_data import VehicleData
from core.ui.modals import draw_scrollbar

_CACHED_ITEM_NAMES = []
_CACHED_CLOTH_NAMES = []
_CACHED_VEHICLE_NAMES = []

def _populate_item_caches():
    global _CACHED_ITEM_NAMES, _CACHED_CLOTH_NAMES, _CACHED_VEHICLE_NAMES
    if not _CACHED_ITEM_NAMES:
        if not ITEM_TEMPLATES:
            load_item_templates_data()
        items = []
        clothes = []
        for name, data in ITEM_TEMPLATES.items():
            if name.endswith(" on"):
                continue
            if data.get('type') == 'cloth':
                clothes.append(name)
            else:
                items.append(name)
        _CACHED_ITEM_NAMES = sorted(items)
        _CACHED_CLOTH_NAMES = sorted(clothes)

    if not _CACHED_VEHICLE_NAMES:
        if not VehicleData.VEHICLE_TEMPLATES:
            VehicleData.load_templates()
        _CACHED_VEHICLE_NAMES = sorted([v['name'] for v in VehicleData.VEHICLE_TEMPLATES if v.get('name')])

def _draw_button(surface, rect, text, mouse_pos, font=None, bg_col=(50, 50, 50), hover_col=(80, 80, 80)):
    f = font or font_12
    is_hover = rect.collidepoint(mouse_pos)
    col = hover_col if is_hover else bg_col
    pygame.draw.rect(surface, col, rect, border_radius=4)
    pygame.draw.rect(surface, WHITE if is_hover else GRAY_60, rect, 1, border_radius=4)
    txt_surf = f.render(text, False, YELLOW if is_hover else WHITE)
    surface.blit(txt_surf, txt_surf.get_rect(center=rect.center))
    return is_hover

def draw_messages_debug_tab(surface, game, modal, mouse_pos, content_rect):
    """Renders the Debug tools inside the Messages modal area."""
    _populate_item_caches()

    subtabs = ['Player', 'Item', 'Weather', 'ZAN']
    if 'debug_subtab' not in modal or modal['debug_subtab'] not in subtabs:
        modal['debug_subtab'] = 'Player'

    active_sub = modal['debug_subtab']

    # --- 1. Sub-tab Buttons Header ---
    tab_bar_h = 24
    tab_w = content_rect.width // len(subtabs)
    modal['debug_subtab_rects'] = []

    for idx, st_name in enumerate(subtabs):
        tab_r = pygame.Rect(content_rect.x + (idx * tab_w), content_rect.y, tab_w, tab_bar_h)
        modal['debug_subtab_rects'].append((st_name, tab_r))
        is_cur = (st_name == active_sub)
        is_hov = tab_r.collidepoint(mouse_pos)

        bg = (60, 60, 60) if is_cur else ((45, 45, 45) if is_hov else (25, 25, 25))
        pygame.draw.rect(surface, bg, tab_r)
        pygame.draw.rect(surface, YELLOW if is_cur else GRAY_60, tab_r, 1)

        t_col = YELLOW if is_cur else (WHITE if is_hov else (180, 180, 180))
        t_surf = font_12.render(st_name, False, t_col)
        surface.blit(t_surf, t_surf.get_rect(center=tab_r.center))

    body_y = content_rect.y + tab_bar_h + 8
    body_h = content_rect.height - tab_bar_h - 12
    body_rect = pygame.Rect(content_rect.x, body_y, content_rect.width, body_h)

    modal['debug_clickable_buttons'] = []

    # ==============================================================
    # SUBTAB 1: PLAYER
    # ==============================================================
    if active_sub == 'Player':
        btn_w, btn_h = 200, 36
        btn_rect = pygame.Rect(body_rect.x + (body_rect.width - btn_w) // 2, body_rect.y + 40, btn_w, btn_h)
        _draw_button(surface, btn_rect, "God Mode (%rot god)", mouse_pos)
        modal['debug_clickable_buttons'].append((btn_rect, "%rot god"))

    # ==============================================================
    # SUBTAB 2: ITEM (Item, Cloth, Vehicle search + dropdowns)
    # ==============================================================
    elif active_sub == 'Item':
        categories = [
            ('item', 'Item', _CACHED_ITEM_NAMES, 'item'),
            ('cloth', 'Cloth', _CACHED_CLOTH_NAMES, 'cloth'),
            ('vehicle', 'Vehicle', _CACHED_VEHICLE_NAMES, 'vehicle')
        ]

        row_h = 30
        gap_y = 10
        cur_y = body_rect.y + 4

        open_dd = modal.get('debug_open_dropdown', None)

        for cat_key, cat_label, name_pool, cmd_type in categories:
            lbl_surf = font_12.render(f"{cat_label}:", False, (220, 220, 220))
            surface.blit(lbl_surf, (body_rect.x + 4, cur_y + 8))

            field_x = body_rect.x + 70
            spawn_btn_w = 60
            field_w = body_rect.width - 70 - spawn_btn_w - 12

            sel_box = pygame.Rect(field_x, cur_y + 2, field_w, 26)
            modal[f'debug_box_{cat_key}'] = sel_box

            cur_sel = modal.get(f'debug_sel_{cat_key}', '')
            search_str = modal.get(f'debug_search_{cat_key}', '')
            is_active_input = (modal.get('debug_active_input') == cat_key)

            box_bg = (35, 35, 35) if not is_active_input else (20, 20, 20)
            pygame.draw.rect(surface, box_bg, sel_box, border_radius=3)
            pygame.draw.rect(surface, YELLOW if is_active_input else GRAY_60, sel_box, 1, border_radius=3)

            disp_txt = search_str if is_active_input else (cur_sel or f"Select {cat_label}...")
            txt_col = WHITE if (is_active_input or cur_sel) else (140, 140, 140)

            old_clip = surface.get_clip()
            surface.set_clip(sel_box.inflate(-8, -4))
            t_surf = font_12.render(disp_txt, False, txt_col)
            surface.blit(t_surf, (sel_box.x + 6, sel_box.centery - t_surf.get_height() // 2))

            if is_active_input and (pygame.time.get_ticks() // 500) % 2 == 0:
                cx = sel_box.x + 6 + t_surf.get_width()
                pygame.draw.line(surface, WHITE, (cx, sel_box.y + 4), (cx, sel_box.bottom - 4), 1)
            surface.set_clip(old_clip)

            arrow_txt = "^" if open_dd == cat_key else "v"
            a_surf = font_12.render(arrow_txt, False, (180, 180, 180))
            surface.blit(a_surf, (sel_box.right - 14, sel_box.centery - a_surf.get_height() // 2))

            # Spawn Button
            spawn_btn = pygame.Rect(sel_box.right + 6, cur_y + 2, spawn_btn_w, 26)
            _draw_button(surface, spawn_btn, "Spawn", mouse_pos)
            if cur_sel:
                modal['debug_clickable_buttons'].append((spawn_btn, f"%rot {cmd_type} \"{cur_sel}\""))

            cur_y += row_h + gap_y

        # --- DRAW DROPDOWN POPUP OVERLAY (WITH AUTO-INVERT LOGIC) ---
        if open_dd in ('item', 'cloth', 'vehicle'):
            cat_key = open_dd
            name_pool = _CACHED_ITEM_NAMES if cat_key == 'item' else (_CACHED_CLOTH_NAMES if cat_key == 'cloth' else _CACHED_VEHICLE_NAMES)
            search_str = modal.get(f'debug_search_{cat_key}', '').strip().lower()

            filtered_pool = [n for n in name_pool if search_str in n.lower()] if search_str else list(name_pool)
            sel_box = modal[f'debug_box_{cat_key}']

            opt_h = 20
            max_visible = 6
            visible_count = min(len(filtered_pool), max_visible)
            popup_h = max(24, visible_count * opt_h)

            # Check if there is enough space downward within content_rect
            space_below = content_rect.bottom - sel_box.bottom
            if space_below < popup_h + 4:
                # INVERT: Open upward (clamped so it doesn't go off the top of the screen)
                popup_y = max(4, sel_box.top - popup_h - 1)
            else:
                # Open downward
                popup_y = sel_box.bottom + 1

            popup_rect = pygame.Rect(sel_box.x, popup_y, sel_box.width, popup_h)
            modal['debug_dd_popup_rect'] = popup_rect
            modal['debug_dd_filtered'] = filtered_pool

            # Popup background & border
            pygame.draw.rect(surface, (20, 20, 20), popup_rect, border_radius=3)
            pygame.draw.rect(surface, WHITE, popup_rect, 1, border_radius=3)

            scroll_offset = modal.get(f'debug_dd_scroll_{cat_key}', 0)
            max_s = max(0, len(filtered_pool) - max_visible)
            scroll_offset = max(0, min(scroll_offset, max_s))
            modal[f'debug_dd_scroll_{cat_key}'] = scroll_offset

            old_clip = surface.get_clip()
            surface.set_clip(popup_rect.inflate(-2, -2))

            modal['debug_dd_option_rects'] = []
            for i in range(min(len(filtered_pool), max_visible)):
                idx = i + scroll_offset
                if idx >= len(filtered_pool):
                    break
                row_name = filtered_pool[idx]
                r_rect = pygame.Rect(popup_rect.x, popup_rect.y + (i * opt_h), popup_rect.width, opt_h)
                modal['debug_dd_option_rects'].append((r_rect, row_name, cat_key))

                is_h = r_rect.collidepoint(mouse_pos)
                if is_h:
                    pygame.draw.rect(surface, (50, 50, 50), r_rect)

                r_txt = font_12.render(row_name, False, YELLOW if is_h else WHITE)
                surface.blit(r_txt, (r_rect.x + 6, r_rect.centery - r_txt.get_height() // 2))

            surface.set_clip(old_clip)

            if len(filtered_pool) > max_visible:
                bar_r = pygame.Rect(popup_rect.right - 8, popup_rect.y + 2, 6, popup_rect.height - 4)
                draw_scrollbar(surface, modal, bar_r, max_visible, len(filtered_pool), scroll_offset)
        else:
            modal['debug_dd_popup_rect'] = None
            modal['debug_dd_option_rects'] = []

    # ==============================================================
    # SUBTAB 3: WEATHER
    # ==============================================================
    elif active_sub == 'Weather':
        w_buttons = [
            ("Rain", "%rot weather rain"),
            ("Fog", "%rot weather fog"),
            ("Rain and Fog", "%rot weather rain_fog"),
            ("Clear All", "%rot weather clear"),
            ("Day", "%rot time sun"),
            ("Night", "%rot time night")
        ]

        grid_w = (body_rect.width - 24) // 2
        btn_h = 32
        for idx, (label, cmd) in enumerate(w_buttons):
            col = idx % 2
            row = idx // 2
            bx = body_rect.x + 8 + (col * (grid_w + 8))
            by = body_rect.y + 12 + (row * (btn_h + 10))
            b_rect = pygame.Rect(bx, by, grid_w, btn_h)
            _draw_button(surface, b_rect, label, mouse_pos)
            modal['debug_clickable_buttons'].append((b_rect, cmd))

    # ==============================================================
    # SUBTAB 4: ZAN (Zombies, Animals, NPCs)
    # ==============================================================
    elif active_sub == 'ZAN':
        zan_rows = [
            [("Remove Zombies", "%rot remove zombies"), ("Spawn Zombies", "%rot spawn zombies"), ("Show Radius", "%rot radius all")],
            [("Remove NPC", "%rot remove npc"), ("Spawn NPC", "%rot spawn npc"), ("Show Radius", "%rot radius hostilenpc")],
            [("Remove Animals", "%rot remove animals"), ("Spawn Animals", "%rot spawn animals"), ("Show Radius", "%rot radius all")]
        ]

        btn_h = 26
        gap_x = 6
        gap_y = 8
        cur_y = body_rect.y + 6
        col_w = (body_rect.width - 16 - (gap_x * 2)) // 3

        for row in zan_rows:
            for col_idx, (label, cmd) in enumerate(row):
                bx = body_rect.x + 8 + (col_idx * (col_w + gap_x))
                b_rect = pygame.Rect(bx, cur_y, col_w, btn_h)
                _draw_button(surface, b_rect, label, mouse_pos)
                modal['debug_clickable_buttons'].append((b_rect, cmd))
            cur_y += btn_h + gap_y

        cur_y += 4
        off_w = body_rect.width - 16
        off_rect = pygame.Rect(body_rect.x + 8, cur_y, off_w, 28)
        _draw_button(surface, off_rect, "Turn off Radius (%rot radius off)", mouse_pos, bg_col=(60, 40, 40), hover_col=(90, 50, 50))
        modal['debug_clickable_buttons'].append((off_rect, "%rot radius off"))

def handle_messages_debug_click(game, modal, mouse_pos):
    """Processes clicks on debug tabs, subtabs, buttons, and dropdown options."""
    from core.events.keyboard import send_chat_message

    # 1. PRIORITY 1: Check clicks on the Dropdown Popup items (Always on top of title bar, subtabs, etc.)
    dd_popup = modal.get('debug_dd_popup_rect')
    if dd_popup and dd_popup.collidepoint(mouse_pos):
        for opt_rect, opt_name, cat_key in modal.get('debug_dd_option_rects', []):
            if opt_rect.collidepoint(mouse_pos):
                modal[f'debug_sel_{cat_key}'] = opt_name
                modal[f'debug_search_{cat_key}'] = ""
                modal['debug_open_dropdown'] = None
                modal['debug_active_input'] = None
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                return True
        # Clicked inside the popup area (e.g. scrollbar track or background), consume click
        return True

    # 2. Check clicks on the 3 Selector Boxes (allows seamless opening & switching between Item, Cloth, Vehicle)
    if modal.get('debug_subtab') == 'Item':
        for cat_key in ('item', 'cloth', 'vehicle'):
            sel_box = modal.get(f'debug_box_{cat_key}')
            if sel_box and sel_box.collidepoint(mouse_pos):
                if modal.get('debug_open_dropdown') == cat_key:
                    # Toggle closed
                    modal['debug_open_dropdown'] = None
                    modal['debug_active_input'] = None
                else:
                    # Switch immediately to this category dropdown
                    modal['debug_open_dropdown'] = cat_key
                    modal['debug_active_input'] = cat_key
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
                return True

    # 3. Sub-tab navigation
    for st_name, tab_r in modal.get('debug_subtab_rects', []):
        if tab_r.collidepoint(mouse_pos):
            modal['debug_subtab'] = st_name
            modal['debug_open_dropdown'] = None
            modal['debug_active_input'] = None
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
            return True

    # 4. Check Action Buttons (Spawn, Weather, ZAN, God mode)
    for btn_rect, cmd in modal.get('debug_clickable_buttons', []):
        if btn_rect.collidepoint(mouse_pos):
            send_chat_message(game, cmd)
            modal['debug_open_dropdown'] = None
            modal['debug_active_input'] = None
            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
            return True

    # 5. Clicking anywhere else inside the modal closes open dropdowns and unfocuses input
    modal['debug_open_dropdown'] = None
    modal['debug_active_input'] = None
    return False

def handle_messages_debug_key(game, modal, event):
    """Processes typing into the active dropdown search box."""
    active_cat = modal.get('debug_active_input')
    if not active_cat:
        return False

    search_key = f'debug_search_{active_cat}'
    cur = modal.get(search_key, '')

    if event.key == pygame.K_BACKSPACE:
        modal[search_key] = cur[:-1]
        modal[f'debug_dd_scroll_{active_cat}'] = 0
        return True
    elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
        modal['debug_active_input'] = None
        return True
    elif event.unicode and event.unicode.isprintable() and len(cur) < 25:
        modal[search_key] = cur + event.unicode
        modal[f'debug_dd_scroll_{active_cat}'] = 0
        return True

    return False