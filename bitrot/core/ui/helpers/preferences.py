# core/ui/helpers/preferences.py
import pygame
import sys
import os
import subprocess
import core.data.config
from core.data.config import *
from core.data.localization import tr
from core.ui.modals import draw_scrollbar

def get_available_resolutions():
    """Returns sorted unique resolutions from 1280x720 up to the hardware max."""
    max_w, max_h = 1280, 720

    # 1. Query display video modes from the driver
    modes = []
    try:
        raw_modes = pygame.display.list_modes()
        if raw_modes and raw_modes != -1:
            modes = raw_modes
            for w, h in modes:
                if w > max_w: max_w = w
                if h > max_h: max_h = h
    except Exception:
        modes = []

    # 2. Query true physical desktop monitor dimensions
    if hasattr(pygame.display, 'get_desktop_sizes'):
        try:
            sizes = pygame.display.get_desktop_sizes()
            if sizes:
                for w, h in sizes:
                    if w > max_w: max_w = w
                    if h > max_h: max_h = h
        except Exception:
            pass

    res_set = set()

    for w, h in modes:
        if w >= 1280 and h >= 720 and w <= max_w and h <= max_h:
            res_set.add((w, h))

    standard_modes = [
        (1280, 720),
        (1360, 768),
        (1366, 768),
        (1440, 900),
        (1600, 900),
        (1680, 1050),
        (1920, 1080),
        (1920, 1200),
        (2560, 1080),
        (2560, 1440),
        (3440, 1440),
        (3840, 2160)
    ]
    for w, h in standard_modes:
        if 1280 <= w <= max_w and 720 <= h <= max_h:
            res_set.add((w, h))

    res_set.add((1280, 720))
    if max_w >= 1280 and max_h >= 720:
        res_set.add((max_w, max_h))

    sorted_modes = sorted(list(res_set), key=lambda r: (r[0], r[1]))
    return [f"{w}x{h}" for w, h in sorted_modes]

def _get_friendly_value_display(key, value):
    try:
        val_float = float(value)
    except Exception:
        return ""

    if 'seconds' in key or '_sec' in key: 
        if val_float >= 60:
            return f"({val_float/60:.1f} {tr('ui', 'min')})"
        return f"({tr('ui', 'sec')})"
        
    return ""

def load_preferences_data(filepath):
    if filepath.endswith('.xml'):
        filepath = os.path.splitext(filepath)[0] + '.json'
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        return raw.get('preferences', raw)
    except Exception as e:
        print(f"Error loading preferences {filepath}: {e}")
        return {}

def save_preferences_json(data, filepath=None):
    if filepath is None:
        filepath = core.data.config.get_preferences_path(for_save=True)
    if filepath.endswith('.xml'):
        filepath = os.path.splitext(filepath)[0] + '.json'

    existing_prefs = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            existing_prefs = raw.get('preferences', raw)
        except Exception:
            existing_prefs = {}

    merged = dict(existing_prefs)
    merged.update(data)
    out = {"preferences": merged}
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2)
    except Exception as e:
        print(f"Error saving preferences JSON: {e}")

save_preferences_xml = save_preferences_json

class PreferencesMenuUI:
    def __init__(self):
        self.active = False
        self.active_tab = 'ui'
        self.scroll_offset_y = 0
        self.is_dragging_scrollbar = False
        self.is_scrolling_content = False
        self.content_drag_last_y = 0
        self.settings_data = {}
        self.active_setting = None
        self.item_height = int(45 * UI_SCALE)
        self.dragging_slider = None
        self.available_resolutions = []

    def toggle(self):
        self.active = not self.active
        self.scroll_offset_y = 0
        self.dragging_slider = None
        self.active_setting = None
        if self.active:
            path = core.data.config.get_preferences_path()
            self.settings_data = load_preferences_data(path)
            self.available_resolutions = get_available_resolutions()
            if self.settings_data and self.active_tab not in self.settings_data:
                self.active_tab = list(self.settings_data.keys())[0]

    def _clamp_scroll(self):
        _, _, _, _, _, list_rect, _, _, _, _ = self.get_rects()
        total_h = self._get_total_content_height()
        max_scroll = max(0, total_h - list_rect.height)
        self.scroll_offset_y = max(0, min(self.scroll_offset_y, max_scroll))

    def _handle_scroll_drag(self, my):
        _, _, _, _, _, list_rect, bar_rect, _, _, _ = self.get_rects()
        total_h = self._get_total_content_height()
        visible_h = list_rect.height
        if total_h <= visible_h:
            self.scroll_offset_y = 0
            return
        thumb_h = max(20, (visible_h / total_h) * bar_rect.height)
        track_h = bar_rect.height - thumb_h
        rel_y = my - bar_rect.y - thumb_h / 2
        ratio = max(0.0, min(1.0, rel_y / track_h))
        self.scroll_offset_y = int(ratio * (total_h - visible_h))

    def _get_total_content_height(self):
        if self.active_tab == 'mods':
            from core.systems.mod_manager import mod_manager
            return len(mod_manager.available_mods) * (self.item_height * 2 + int(5 * UI_SCALE))
        settings = self.settings_data.get(self.active_tab, {})
        return len(settings) * self.item_height

    def _update_volume_setting(self, game, block, key, new_val):
        new_val = round(max(0.0, min(1.0, float(new_val))), 2)

        if block in self.settings_data and key in self.settings_data[block]:
            self.settings_data[block][key]['value'] = str(new_val)

        attr_name = key.upper()
        if hasattr(core.data.config, attr_name):
            setattr(core.data.config, attr_name, new_val)

        if key == 'volume_music':
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(new_val)

        if key in ('volume_atmospheric', 'volume_background'):
            wt = getattr(game, 'world_time', None)
            if wt:
                vol_atm = getattr(core.data.config, 'VOLUME_ATMOSPHERIC', new_val)
                for ch in [
                    getattr(wt, 'day_channel', None),
                    getattr(wt, 'night_channel', None),
                    getattr(wt, 'cave_channel', None),
                    getattr(wt, 'rain_channel', None)
                ]:
                    if ch and ch.get_busy():
                        ch.set_volume(0.6 * vol_atm, 0.6 * vol_atm)

    def get_rects(self):
        scale = UI_SCALE
        def S(val): return int(val * scale)
        center_x = GAME_WIDTH // 2
        center_y = GAME_HEIGHT // 2
        w = S(900)
        h = S(480)
        
        bg_rect = pygame.Rect(center_x - w//2, center_y - h//2, w, h)
        header_rect = pygame.Rect(bg_rect.x, bg_rect.y, bg_rect.width, S(50))
        
        # Tabs placed flush under header (matching Keybinds / Controls modal)
        tab_h = S(38)
        tab_y = header_rect.bottom
        categories = list(self.settings_data.keys())
        
        if 'mods' not in categories:
            categories.append('mods')
            
        cat_order = ['ui', 'audio', 'player', 'mods']
        ordered_cats = [c for c in cat_order if c in categories]
        for c in categories:
            if c not in ordered_cats:
                ordered_cats.append(c)
        categories = ordered_cats

        total_tabs = max(1, len(categories))

        tab_w = bg_rect.width // total_tabs
        tab_rects = {}
        for i, cat in enumerate(categories):
            cur_w = tab_w if i < total_tabs - 1 else (bg_rect.width - (tab_w * i))
            tab_rects[cat] = pygame.Rect(bg_rect.x + (i * tab_w), tab_y, cur_w, tab_h)

        padding = S(20)
        list_y = tab_y + tab_h + padding
        list_height = bg_rect.bottom - list_y - padding
        
        scrollbar_width = S(12)
        list_rect = pygame.Rect(bg_rect.x + padding, list_y, bg_rect.width - (padding * 2) - scrollbar_width - S(10), list_height)
        bar_rect = pygame.Rect(list_rect.right + S(10), list_y, scrollbar_width, list_height)

        btn_width = S(200)
        btn_height = S(45)
        spacing = S(20)
        
        total_btn_width = (btn_width * 3) + (spacing * 2)
        start_btn_x = center_x - (total_btn_width // 2)
        
        apply_btn_rect = pygame.Rect(start_btn_x, bg_rect.bottom + S(20), btn_width, btn_height)
        reset_btn_rect = pygame.Rect(apply_btn_rect.right + spacing, bg_rect.bottom + S(20), btn_width, btn_height)
        back_btn_rect = pygame.Rect(reset_btn_rect.right + spacing, bg_rect.bottom + S(20), btn_width, btn_height)
        
        return center_x, center_y, bg_rect, header_rect, tab_rects, list_rect, bar_rect, apply_btn_rect, reset_btn_rect, back_btn_rect

    def handle_events(self, game, events):
        if not self.active: 
            return False

        scale = UI_SCALE
        def S(val): return int(val * scale)
        
        for event in events:
            mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else (event.pos if hasattr(event, 'pos') else pygame.mouse.get_pos())

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.active = False
                    self.dragging_slider = None
                    continue

                if self.active_setting:
                    block, key = self.active_setting
                    setting_obj = self.settings_data[block][key]
                    current_val = str(setting_obj['value'])
                    if event.key == pygame.K_BACKSPACE:
                        setting_obj['value'] = current_val[:-1]
                    elif event.key == pygame.K_RETURN: 
                        self.active_setting = None
                    else: 
                        setting_obj['value'] = current_val + event.unicode
                    continue

            if event.type == pygame.MOUSEWHEEL:
                self.scroll_offset_y -= event.y * int(30 * UI_SCALE)
                self._clamp_scroll()
                continue
                
            if event.type == pygame.MOUSEMOTION:
                if self.dragging_slider:
                    block, key = self.dragging_slider
                    _, _, _, _, _, list_rect, _, _, _, _ = self.get_rects()
                    input_w = S(250)
                    slider_track_x = list_rect.right - input_w + S(8)
                    slider_track_w = input_w - S(68)
                    pct = max(0.0, min(1.0, (mouse_pos[0] - slider_track_x) / max(1, slider_track_w)))
                    self._update_volume_setting(game, block, key, pct)
                    continue

                if self.is_dragging_scrollbar:
                    self._handle_scroll_drag(mouse_pos[1])
                elif self.is_scrolling_content:
                    delta_y = mouse_pos[1] - self.content_drag_last_y
                    self.content_drag_last_y = mouse_pos[1]
                    self.scroll_offset_y -= delta_y 
                    self._clamp_scroll()
                continue 

            if event.type == pygame.MOUSEBUTTONUP and getattr(event, 'button', 1) == 1:
                if self.dragging_slider:
                    self.dragging_slider = None
                    save_preferences_xml(self.settings_data, core.data.config.get_preferences_path(for_save=True))

                self.is_dragging_scrollbar = False
                self.is_scrolling_content = False
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
                self.active_setting = None
                _, _, _, _, tab_rects, list_rect, bar_rect, apply_btn, reset_btn, back_btn = self.get_rects()

                if back_btn.collidepoint(mouse_pos):
                    self.active = False
                    self.dragging_slider = None
                    continue

                if apply_btn.collidepoint(mouse_pos):
                    save_preferences_xml(self.settings_data, core.data.config.get_preferences_path(for_save=True))
                    pygame.quit()
                    if sys.argv[0].endswith('.py'):
                        subprocess.Popen([sys.executable] + sys.argv)
                    else:
                        executable_path = os.path.abspath(sys.argv[0])
                        subprocess.Popen([executable_path] + sys.argv[1:])
                    sys.exit(0)

                if reset_btn.collidepoint(mouse_pos):
                    for block, settings in self.settings_data.items():
                        for key, setting_obj in settings.items():
                            if 'default' in setting_obj:
                                setting_obj['value'] = setting_obj['default']
                                if key in ('ui_crt_filter', 'crt_filter'):
                                    bool_state = str(setting_obj['default']).lower() == 'true'
                                    setattr(core.data.config, 'UI_CRT_FILTER', bool_state)
                                    setattr(core.data.config, 'CRT_FILTER', bool_state)
                                if 'volume' in key:
                                    try:
                                        def_val = float(setting_obj['default'])
                                        self._update_volume_setting(game, block, key, def_val)
                                    except Exception:
                                        pass
                    save_preferences_xml(self.settings_data, core.data.config.get_preferences_path(for_save=True))

                    continue

                # Category Tab Clicks (Exact keybinds tab pattern)
                tab_clicked = False
                for cat, r in tab_rects.items():
                    if r.collidepoint(mouse_pos):
                        if self.active_tab != cat:
                            self.active_tab = cat
                            self.scroll_offset_y = 0
                            self.dragging_slider = None
                            self.active_setting = None
                            if game and hasattr(game, 'sound_manager'):
                                game.sound_manager.play_ui_hover()
                        tab_clicked = True
                        break
                if tab_clicked:
                    continue

                if bar_rect.collidepoint(mouse_pos):
                    self.is_dragging_scrollbar = True
                    self._handle_scroll_drag(mouse_pos[1])
                    continue

                clicked_input = False
                if list_rect.collidepoint(mouse_pos):
                    y_off = list_rect.y - self.scroll_offset_y
                    
                    if self.active_tab == 'mods':
                        from core.systems.mod_manager import mod_manager
                        for mod_name, mod_info in mod_manager.available_mods.items():
                            row_rect = pygame.Rect(list_rect.x, y_off, list_rect.width, self.item_height * 2)
                            if row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                                cb_size = int(24 * UI_SCALE)
                                cb_rect = pygame.Rect(row_rect.right - cb_size - int(20 * UI_SCALE), row_rect.centery - cb_size//2, cb_size, cb_size)
                                if cb_rect.collidepoint(mouse_pos) or row_rect.collidepoint(mouse_pos):
                                    is_enabled = mod_name in mod_manager.enabled_mods
                                    if is_enabled:
                                        mod_manager.enabled_mods.remove(mod_name)
                                    else:
                                        mod_manager.enabled_mods.append(mod_name)
                                    mod_manager.save_enabled_mods(mod_manager.enabled_mods)
                                    self.settings_data['mods'] = {'enabled': mod_manager.enabled_mods}
                                    if game and hasattr(game, 'sound_manager'):
                                        game.sound_manager.play_ui_hover()
                                    clicked_input = True
                                    break
                            y_off += self.item_height * 2 + int(5 * UI_SCALE)
                        if clicked_input:
                            continue

                    block = self.active_tab
                    settings = self.settings_data.get(block, {})

                    for key, val_data in settings.items():
                        row_rect = pygame.Rect(list_rect.x, y_off, list_rect.width, self.item_height)
                        if row_rect.collidepoint(mouse_pos) and row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                            input_w = S(250)
                            input_rect = pygame.Rect(row_rect.right - input_w, row_rect.centery - S(15), input_w, S(30))
                            
                            if 'volume' in key:
                                if input_rect.collidepoint(mouse_pos):
                                    self.dragging_slider = (block, key)
                                    slider_track_x = input_rect.x + S(8)
                                    slider_track_w = input_w - S(68)
                                    pct = max(0.0, min(1.0, (mouse_pos[0] - slider_track_x) / max(1, slider_track_w)))
                                    self._update_volume_setting(game, block, key, pct)
                                    clicked_input = True
                                    break
                            elif input_rect.collidepoint(mouse_pos):
                                str_val = str(val_data.get('value')).lower()
                                is_bool = str_val in ('true', 'false')
                                is_cycle = (key in ['language', 'resolution', 'ui_resolution', 'window_mode'])

                                dir_step = -1 if mouse_pos[0] < input_rect.centerx else 1

                                if is_bool:
                                    new_val = "false" if str_val == "true" else "true"
                                    self.settings_data[block][key]['value'] = new_val

                                    if key in ('ui_crt_filter', 'crt_filter'):
                                        bool_state = (new_val == 'true')
                                        setattr(core.data.config, 'UI_CRT_FILTER', bool_state)
                                        setattr(core.data.config, 'CRT_FILTER', bool_state)

                                    if game and hasattr(game, 'sound_manager'):
                                        game.sound_manager.play_ui_hover()
                                elif is_cycle:
                                    if key in ['resolution', 'ui_resolution']:
                                        res_list = self.available_resolutions or get_available_resolutions()
                                        self.available_resolutions = res_list
                                        current_val = str(val_data.get('value', '1280x720')).strip().lower()
                                        idx = 0
                                        for i, r_cand in enumerate(res_list):
                                            if r_cand.lower() == current_val:
                                                idx = i
                                                break
                                        new_idx = (idx + dir_step) % len(res_list)
                                        self.settings_data[block][key]['value'] = res_list[new_idx]
                                        if game and hasattr(game, 'sound_manager'):
                                            game.sound_manager.play_ui_hover()

                                    elif key == 'language':
                                        langs = ['en_US', 'pt_BR']
                                        idx = langs.index(str(val_data['value'])) if str(val_data['value']) in langs else 0
                                        new_val = langs[(idx + dir_step) % len(langs)]
                                        self.settings_data[block][key]['value'] = new_val
                                        if game and hasattr(game, 'sound_manager'):
                                            game.sound_manager.play_ui_hover()

                                    elif key == 'window_mode':
                                        modes = ['windowed', 'fullscreen']
                                        current_val = str(val_data['value']).lower()
                                        idx = modes.index(current_val) if current_val in modes else 0
                                        self.settings_data[block][key]['value'] = modes[(idx + dir_step) % len(modes)]
                                        if game and hasattr(game, 'sound_manager'):
                                            game.sound_manager.play_ui_hover()
                                else:
                                    self.active_setting = (block, key)
                                clicked_input = True
                        y_off += self.item_height

                if list_rect.collidepoint(mouse_pos) and not clicked_input:
                    self.is_scrolling_content = True
                    self.content_drag_last_y = mouse_pos[1]

        return True

    def draw(self, screen, mouse_pos, game=None):
        if not self.active: 
            return

        def S(val): return int(val * UI_SCALE)
        center_x, center_y, bg_rect, header_rect, tab_rects, list_rect, bar_rect, apply_btn, reset_btn, back_btn = self.get_rects()

        screen.fill(DARK_GRAY)
        pygame.draw.rect(screen, (35, 35, 35), bg_rect, border_radius=10)
        pygame.draw.rect(screen, GRAY_80, bg_rect, width=2, border_radius=10)

        # Header Title
        pygame.draw.rect(screen, (45, 45, 45), header_rect, border_top_left_radius=10, border_top_right_radius=10)
        pygame.draw.line(screen, GRAY_80, header_rect.bottomleft, header_rect.bottomright, 2)
        title_surf = font_16.render(tr('ui', "Global Preferences"), False, WHITE)
        screen.blit(title_surf, (header_rect.x + 20, header_rect.centery - title_surf.get_height() // 2))

        # Category Tabs (Exact match with Controls / Keybinds modal tabs)
        hovered_pref_id = None
        for cat, r in tab_rects.items():
            is_active_tab = (cat == self.active_tab)
            tab_color = (35, 35, 35) if is_active_tab else (25, 25, 25)
            if not is_active_tab and r.collidepoint(mouse_pos):
                tab_color = (45, 45, 45)
                hovered_pref_id = f"tab_{cat}"

            pygame.draw.rect(screen, tab_color, r)
            pygame.draw.rect(screen, WHITE, r, width=1)

            display_tab = "UI" if cat.lower() == 'ui' else cat.capitalize()
            tab_surf = font_16.render(tr('ui', display_tab), False, WHITE)
            screen.blit(tab_surf, tab_surf.get_rect(center=r.center))

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)
        self._clamp_scroll()

        # Render Active Tab Settings
        y_off = list_rect.y - self.scroll_offset_y
        
        if self.active_tab == 'mods':
            from core.systems.mod_manager import mod_manager
            for mod_name, mod_info in mod_manager.available_mods.items():
                cfg = mod_info['config']
                version = cfg.get('version', '1.0.0')
                description = cfg.get('description', 'No description.')
                repo = cfg.get('repository', '')
                
                row_rect = pygame.Rect(list_rect.x, y_off, list_rect.width, self.item_height * 2)
                if row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                    is_hovered = row_rect.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (50, 50, 50) if is_hovered else (35, 35, 35), row_rect, border_radius=4)
                    pygame.draw.rect(screen, (70, 70, 70), row_rect, 1, border_radius=4)
                    
                    is_enabled = mod_name in mod_manager.enabled_mods
                    cb_size = int(24 * UI_SCALE)
                    cb_rect = pygame.Rect(row_rect.right - cb_size - int(20 * UI_SCALE), row_rect.centery - cb_size//2, cb_size, cb_size)
                    
                    pygame.draw.rect(screen, (40, 40, 40), cb_rect, border_radius=4)
                    pygame.draw.rect(screen, WHITE if cb_rect.collidepoint(mouse_pos) else GRAY, cb_rect, 1, border_radius=4)
                    
                    if is_enabled:
                        pygame.draw.rect(screen, GREEN, cb_rect.inflate(-8, -8), border_radius=2)
                    
                    name_surf = font_16.render(mod_name, False, GREEN if is_enabled else WHITE)
                    screen.blit(name_surf, (row_rect.x + int(15 * UI_SCALE), row_rect.y + int(10 * UI_SCALE)))
                    
                    ver_surf = font_12.render(f"v{version}", False, GRAY)
                    screen.blit(ver_surf, (row_rect.x + int(15 * UI_SCALE) + name_surf.get_width() + 10, row_rect.y + int(13 * UI_SCALE)))
                    
                    if is_hovered:
                        desc_text = description
                        if repo:
                            desc_text += f"\nRepo: {repo}"
                        status = "ENABLED" if is_enabled else "DISABLED"
                        color = GREEN if is_enabled else RED
                        self._mod_tooltip = (mod_name, desc_text, status, color)
                        
                y_off += self.item_height * 2 + int(5 * UI_SCALE)
        else:
            block = self.active_tab
            settings = self.settings_data.get(block, {})

            for key, val_data in settings.items():
                row_rect = pygame.Rect(list_rect.x, y_off, list_rect.width, self.item_height)
                if row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                    pygame.draw.line(screen, (55, 55, 55), (row_rect.left, row_rect.bottom - 1), (row_rect.right, row_rect.bottom - 1), 1)

                    raw_label = val_data.get('name', key)
                    if key in ['ui_resolution', 'resolution']:
                        raw_label = "Resolution"
                    elif key in ['ui_crt_filter', 'crt_filter']:
                        raw_label = "CRT Filter"
                    display_label = tr('ui', raw_label)
                    lbl = font_12.render(display_label + ":", False, WHITE)
                    screen.blit(lbl, (row_rect.x + S(10), row_rect.centery - lbl.get_height()//2))

                    val = val_data.get('value')
                    input_w = S(250)
                    input_rect = pygame.Rect(row_rect.right - input_w, row_rect.centery - S(15), input_w, S(30))
                    
                    if input_rect.collidepoint(mouse_pos):
                        hovered_pref_id = f"{block}_{key}"

                    str_val = str(val).lower()
                    is_bool = str_val in ('true', 'false')
                    is_volume = 'volume' in key
                    is_cycle = (key in ['language', 'resolution', 'ui_resolution', 'window_mode'])

                    friendly_text = _get_friendly_value_display(key, val)
                    if friendly_text and not is_bool and not is_cycle and not is_volume:
                        info_surf = font_12.render(friendly_text, False, GRAY)
                        screen.blit(info_surf, (input_rect.x - info_surf.get_width() - S(15), row_rect.centery - info_surf.get_height()//2))

                    hovered = input_rect.collidepoint(mouse_pos)

                    # 1. Volume Sliders
                    if is_volume:
                        try:
                            val_float = max(0.0, min(1.0, float(val)))
                        except Exception:
                            val_float = 0.50

                        is_active_slider = (self.dragging_slider == (block, key)) or hovered

                        slider_track_x = input_rect.x + S(8)
                        slider_track_w = input_w - S(68)
                        slider_track_h = S(8)
                        slider_track_y = input_rect.centery - slider_track_h // 2
                        track_rect = pygame.Rect(slider_track_x, slider_track_y, slider_track_w, slider_track_h)

                        pygame.draw.rect(screen, GRAY_40, track_rect, border_radius=S(4))
                        pygame.draw.rect(screen, GRAY_60, track_rect, 1, border_radius=S(4))

                        fill_w = max(0, min(slider_track_w, int(val_float * slider_track_w)))
                        if fill_w > 0:
                            fill_rect = pygame.Rect(slider_track_x, slider_track_y, fill_w, slider_track_h)
                            pygame.draw.rect(screen, (23, 162, 184), fill_rect, border_radius=S(4))

                        handle_w = S(12)
                        handle_h = S(20)
                        handle_x = slider_track_x + fill_w
                        handle_rect = pygame.Rect(handle_x - handle_w // 2, input_rect.centery - handle_h // 2, handle_w, handle_h)
                        handle_col = YELLOW if is_active_slider else WHITE
                        pygame.draw.rect(screen, handle_col, handle_rect, border_radius=S(3))
                        pygame.draw.rect(screen, GRAY, handle_rect, 1, border_radius=S(3))

                        pct_text = f"{int(round(val_float * 100))}%"
                        txt_surf = font_12.render(pct_text, False, YELLOW if is_active_slider else WHITE)
                        txt_rect = txt_surf.get_rect(midleft=(track_rect.right + S(12), input_rect.centery))
                        screen.blit(txt_surf, txt_rect)

                    # 2. Carousels & Selectors (Resolution, Language, Window Mode, Booleans)
                    # Rendered with exact standard polygon arrows matching world.py and player_setup.py
                    elif is_bool or is_cycle:
                        bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                        pygame.draw.rect(screen, bg_color, input_rect, border_radius=3)
                        pygame.draw.rect(screen, WHITE, input_rect, 1, border_radius=3)

                        if is_bool:
                            label_str = tr('ui', "True") if str_val == "true" else tr('ui', "False")
                        elif key in ['resolution', 'ui_resolution']:
                            label_str = str(val)
                        elif key == 'language':
                            label_str = str(val)
                        elif key == 'window_mode':
                            label_str = tr('ui', str(val).capitalize())
                        else:
                            label_str = str(val)

                        txt_surf = font_12.render(label_str, False, WHITE)
                        screen.blit(txt_surf, (input_rect.centerx - txt_surf.get_width()//2, input_rect.centery - txt_surf.get_height()//2))

                        # Standard right arrow polygon
                        pygame.draw.polygon(screen, WHITE, [
                            (input_rect.right - S(8), input_rect.centery),
                            (input_rect.right - S(14), input_rect.centery - S(4)),
                            (input_rect.right - S(14), input_rect.centery + S(4))
                        ])
                        # Standard left arrow polygon
                        pygame.draw.polygon(screen, WHITE, [
                            (input_rect.x + S(8), input_rect.centery),
                            (input_rect.x + S(14), input_rect.centery - S(4)),
                            (input_rect.x + S(14), input_rect.centery + S(4))
                        ])

                    # 3. Numeric / Text Inputs
                    else:
                        is_active = (self.active_setting == (block, key))
                        col = WHITE if is_active else GRAY
                        pygame.draw.rect(screen, (50, 50, 50), input_rect)
                        pygame.draw.rect(screen, col, input_rect, 1)
                        txt_surf = font_12.render(str(val), False, WHITE)
                        screen.blit(txt_surf, (input_rect.x + S(5), input_rect.centery - txt_surf.get_height()//2))

                y_off += self.item_height

        screen.set_clip(old_clip)
        draw_scrollbar(screen, {}, bar_rect, list_rect.height, self._get_total_content_height(), self.scroll_offset_y)

        # Hover audio tracker
        if apply_btn.collidepoint(mouse_pos):
            hovered_pref_id = "btn_apply"
        elif reset_btn.collidepoint(mouse_pos):
            hovered_pref_id = "btn_reset"
        elif back_btn.collidepoint(mouse_pos):
            hovered_pref_id = "btn_back"

        if hovered_pref_id is not None and hovered_pref_id != getattr(self, '_last_hovered_id', None):
            if game and hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
        self._last_hovered_id = hovered_pref_id

        def _draw_btn(rect, text, col):
            hovered = rect.collidepoint(mouse_pos)
            color = (min(255, col[0]+30), min(255, col[1]+30), min(255, col[2]+30)) if hovered else col
            pygame.draw.rect(screen, color, rect, border_radius=4)
            t_surf = font_16.render(tr('ui', text), False, WHITE)
            screen.blit(t_surf, (rect.centerx - t_surf.get_width()//2, rect.centery - t_surf.get_height()//2))

        _draw_btn(apply_btn, "Apply & Restart", (80, 80, 80))
        _draw_btn(reset_btn, "Reset Default", (80, 80, 80))
        _draw_btn(back_btn, "Back", (80, 80, 80))

        if self.active_tab == 'mods' and hasattr(self, '_mod_tooltip') and self._mod_tooltip:
            name, desc, status, col = self._mod_tooltip
            lines = desc.split('\n')
            w = max(font_12.size(name)[0], font_12.size(status)[0], max([font_12.size(l)[0] for l in lines] + [0])) + 20
            h = 20 + 20 + len(lines)*15 + 10
            
            tt_x = min(mouse_pos[0] + 15, GAME_WIDTH - w - 5)
            tt_y = min(mouse_pos[1] + 15, GAME_HEIGHT - h - 5)
            
            tt_rect = pygame.Rect(tt_x, tt_y, w, h)
            pygame.draw.rect(screen, BLACK, tt_rect)
            pygame.draw.rect(screen, WHITE, tt_rect, 1)
            
            screen.blit(font_12.render(name, False, WHITE), (tt_rect.x+10, tt_rect.y+10))
            screen.blit(font_12.render(status, False, col), (tt_rect.x+10, tt_rect.y+30))
            cy = tt_rect.y+50
            for l in lines:
                screen.blit(font_12.render(l, False, GRAY), (tt_rect.x+10, cy))
                cy+=15
            self._mod_tooltip = None

preferences_ui = PreferencesMenuUI()