# core/ui/helpers/preferences.py
import pygame
import sys
import os
import subprocess
import core.data.config
from core.data.config import *
from core.data.localization import tr, load_language
from core.ui.modals import draw_scrollbar

def _get_friendly_value_display(key, value):
    try: val_float = float(value)
    except: return ""

    if 'seconds' in key or '_sec' in key: 
        if val_float >= 60: return f"({val_float/60:.1f} {tr('ui', 'min')})"
        return f"({tr('ui', 'sec')})"
        
    if 'volume' in key:
        return f"({val_float*100:.0f}%)"
    return ""

def load_preferences_data(filepath):
    if not os.path.exists(filepath):
        return {}
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(filepath)
        root = tree.getroot()
        data = {}
        for child in root:
            block_name = child.tag
            data[block_name] = {}
            for setting in child:
                key = setting.tag
                val = setting.get('value')
                display_name = setting.get('name', key)
                default_val = setting.get('default')
                setting_dict = {'value': val, 'name': display_name}
                if default_val is not None:
                    setting_dict['default'] = default_val
                data[block_name][key] = setting_dict
        return data
    except Exception as e:
        print(f"Error loading preferences {filepath}: {e}")
        return {}

def save_preferences_xml(data, filepath):
    import xml.etree.ElementTree as ET
    import xml.dom.minidom
    root = ET.Element("preferences")
    for block_name, settings in data.items():
        block_node = ET.SubElement(root, block_name)
        for key, val_data in settings.items():
            val = val_data.get('value', '')
            name = val_data.get('name', '')
            default_val = val_data.get('default')
            elem = ET.SubElement(block_node, key, value=str(val))
            if name: elem.set('name', name)
            if default_val is not None: elem.set('default', str(default_val))

    try:
        raw_xml = ET.tostring(root, 'utf-8')
        parsed = xml.dom.minidom.parseString(raw_xml)
        pretty_xml = parsed.toprettyxml(indent="    ")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(pretty_xml)
    except Exception as e:
        print(f"Error saving preferences XML: {e}")

class PreferencesMenuUI:
    def __init__(self):
        self.active = False
        self.scroll_offset_y = 0
        self.is_dragging_scrollbar = False
        self.is_scrolling_content = False
        self.content_drag_last_y = 0
        self.settings_data = {}
        self.active_setting = None
        self.item_height = int(45 * UI_SCALE)

    def toggle(self):
        self.active = not self.active
        self.scroll_offset_y = 0
        if self.active:
            path = core.data.config.get_preferences_path()
            self.settings_data = load_preferences_data(path)

    def _clamp_scroll(self):
        _, _, _, list_rect, _, _, _, _ = self.get_rects()
        total_h = self._get_total_content_height()
        max_scroll = max(0, total_h - list_rect.height)
        self.scroll_offset_y = max(0, min(self.scroll_offset_y, max_scroll))

    def _handle_scroll_drag(self, my):
        _, _, _, list_rect, bar_rect, _, _, _ = self.get_rects()
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
        count = 0
        for block, settings in self.settings_data.items():
            count += 1 
            count += len(settings)
        return count * self.item_height

    def get_rects(self):
        scale = UI_SCALE
        def S(val): return int(val * scale)
        center_x = GAME_WIDTH // 2
        center_y = GAME_HEIGHT // 2
        w = S(900)
        h = S(480)
        
        bg_rect = pygame.Rect(center_x - w//2, center_y - h//2, w, h)
        header_rect = pygame.Rect(bg_rect.x, bg_rect.y, bg_rect.width, S(50))
        
        padding = S(20)
        list_y = header_rect.bottom + padding
        list_height = bg_rect.bottom - list_y - padding
        
        scrollbar_width = S(12)
        list_rect = pygame.Rect(bg_rect.x + padding, list_y, bg_rect.width - (padding * 2) - scrollbar_width - S(10), list_height)
        bar_rect = pygame.Rect(list_rect.right + S(10), list_y, scrollbar_width, list_height)

        btn_width = S(200)
        btn_height = S(45)
        spacing = S(20)
        
        # Reorder buttons: Apply -> Reset -> Back
        total_btn_width = (btn_width * 3) + (spacing * 2)
        start_btn_x = center_x - (total_btn_width // 2)
        
        apply_btn_rect = pygame.Rect(start_btn_x, bg_rect.bottom + S(20), btn_width, btn_height)
        reset_btn_rect = pygame.Rect(apply_btn_rect.right + spacing, bg_rect.bottom + S(20), btn_width, btn_height)
        back_btn_rect = pygame.Rect(reset_btn_rect.right + spacing, bg_rect.bottom + S(20), btn_width, btn_height)
        
        return center_x, center_y, bg_rect, list_rect, bar_rect, apply_btn_rect, reset_btn_rect, back_btn_rect

    def handle_events(self, game, events):
        if not self.active: return False
        
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.active = False
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
                mouse_pos = event.pos if hasattr(event, 'pos') else pygame.mouse.get_pos()
                if self.is_dragging_scrollbar:
                    self._handle_scroll_drag(mouse_pos[1])
                elif self.is_scrolling_content:
                    delta_y = mouse_pos[1] - self.content_drag_last_y
                    self.content_drag_last_y = mouse_pos[1]
                    self.scroll_offset_y -= delta_y 
                    self._clamp_scroll()
                continue 

            if event.type == pygame.MOUSEBUTTONUP and getattr(event, 'button', 1) == 1:
                self.is_dragging_scrollbar = False
                self.is_scrolling_content = False
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
                self.active_setting = None
                mouse_pos = event.pos if hasattr(event, 'pos') else pygame.mouse.get_pos()
                _, _, _, list_rect, bar_rect, apply_btn, reset_btn, back_btn = self.get_rects()

                if back_btn.collidepoint(mouse_pos):
                    self.active = False
                    continue

                if apply_btn.collidepoint(mouse_pos):
                    save_preferences_xml(self.settings_data, core.data.config.get_preferences_path())
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
                    continue

                if bar_rect.collidepoint(mouse_pos):
                    self.is_dragging_scrollbar = True
                    self._handle_scroll_drag(mouse_pos[1])
                    continue

                clicked_input = False
                if list_rect.collidepoint(mouse_pos):
                    y_off = list_rect.y - self.scroll_offset_y
                    for block, settings in self.settings_data.items():
                        y_off += self.item_height # header
                        for key, val_data in settings.items():
                            row_rect = pygame.Rect(list_rect.x, y_off, list_rect.width, self.item_height)
                            if row_rect.collidepoint(mouse_pos) and row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                                input_w = int(250 * UI_SCALE)
                                input_rect = pygame.Rect(row_rect.right - input_w, row_rect.centery - int(15*UI_SCALE), input_w, int(30*UI_SCALE))
                                
                                if input_rect.collidepoint(mouse_pos):
                                    str_val = str(val_data.get('value')).lower()
                                    is_bool = str_val in ('true', 'false')
                                    is_cycle = ('volume' in key) or (key in ['language', 'resolution', 'window_mode'])

                                    if is_bool:
                                        new_val = "false" if str_val == "true" else "true"
                                        self.settings_data[block][key]['value'] = new_val
                                    elif is_cycle:
                                        if key == 'language':
                                            langs = ['en_US', 'pt_BR']
                                            idx = langs.index(str(val_data['value'])) if str(val_data['value']) in langs else 0
                                            new_val = langs[(idx + 1) % len(langs)]
                                            self.settings_data[block][key]['value'] = new_val
                                        elif key == 'resolution':
                                            modes = pygame.display.list_modes()
                                            res_list = [f"{w}x{h}" for w, h in reversed(modes) if w >= 1280 and h >= 720] if modes != -1 else []
                                            res_list = list(dict.fromkeys(res_list)) + ['max']
                                            current_val = str(val_data['value']).lower()
                                            idx = res_list.index(current_val) if current_val in res_list else 0
                                            self.settings_data[block][key]['value'] = res_list[(idx + 1) % len(res_list)]
                                        elif key == 'window_mode':
                                            modes = ['windowed', 'fullscreen']
                                            current_val = str(val_data['value']).lower()
                                            idx = modes.index(current_val) if current_val in modes else 0
                                            self.settings_data[block][key]['value'] = modes[(idx + 1) % len(modes)]
                                        elif 'volume' in key:
                                            try: comp_val = float(val_data['value'])
                                            except: comp_val = 0.5
                                            if comp_val < 0.25: new_val = 0.25
                                            elif comp_val < 0.50: new_val = 0.50
                                            elif comp_val < 0.75: new_val = 0.75
                                            elif comp_val < 1.0: new_val = 1.0
                                            else: new_val = 0.0
                                            self.settings_data[block][key]['value'] = str(new_val)
                                    else:
                                        self.active_setting = (block, key)
                                    clicked_input = True
                            y_off += self.item_height

                if list_rect.collidepoint(mouse_pos) and not clicked_input:
                    self.is_scrolling_content = True
                    self.content_drag_last_y = mouse_pos[1]

        return True

    def draw(self, screen, mouse_pos):
        if not self.active: return

        def S(val): return int(val * UI_SCALE)
        center_x, center_y, bg_rect, list_rect, bar_rect, apply_btn, reset_btn, back_btn = self.get_rects()

        screen.fill(DARK_GRAY)
        pygame.draw.rect(screen, (35, 35, 35), bg_rect, border_radius=10)
        pygame.draw.rect(screen, GRAY_80, bg_rect, width=2, border_radius=10)

        header_rect = pygame.Rect(bg_rect.x, bg_rect.y, bg_rect.width, int(50 * UI_SCALE))
        pygame.draw.rect(screen, (45, 45, 45), header_rect, border_top_left_radius=10, border_top_right_radius=10)
        pygame.draw.line(screen, GRAY_80, header_rect.bottomleft, header_rect.bottomright, 2)
        title_surf = font_16.render(tr('ui', "Global Preferences"), False, WHITE)
        screen.blit(title_surf, (header_rect.x + 20, header_rect.centery - title_surf.get_height() // 2))

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)
        self._clamp_scroll()

        y_off = list_rect.y - self.scroll_offset_y
        for block, settings in self.settings_data.items():
            row_rect = pygame.Rect(list_rect.x, y_off, list_rect.width, self.item_height)
            if row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                header_name = tr('ui', block.capitalize())
                text = font_12.render(header_name.upper(), False, YELLOW)
                screen.blit(text, (row_rect.x, row_rect.centery - text.get_height()//2))
            y_off += self.item_height

            for key, val_data in settings.items():
                row_rect = pygame.Rect(list_rect.x, y_off, list_rect.width, self.item_height)
                if row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                    pygame.draw.line(screen, (55, 55, 55), (row_rect.left, row_rect.bottom - 1), (row_rect.right, row_rect.bottom - 1), 1)

                    raw_label = val_data.get('name', key)
                    display_label = tr('ui', raw_label)
                    lbl = font_12.render(display_label + ":", False, WHITE)
                    screen.blit(lbl, (row_rect.x + S(10), row_rect.centery - lbl.get_height()//2))

                    val = val_data.get('value')
                    input_w = S(250)
                    input_rect = pygame.Rect(row_rect.right - input_w, row_rect.centery - S(15), input_w, S(30))
                    
                    str_val = str(val).lower()
                    is_bool = str_val in ('true', 'false')
                    is_cycle = ('volume' in key) or (key in ['language', 'resolution', 'window_mode'])

                    friendly_text = _get_friendly_value_display(key, val)
                    if friendly_text and not is_bool and not is_cycle:
                        info_surf = font_12.render(friendly_text, False, GRAY)
                        screen.blit(info_surf, (input_rect.x - info_surf.get_width() - S(15), row_rect.centery - info_surf.get_height()//2))

                    hovered = input_rect.collidepoint(mouse_pos)
                    
                    if is_bool or is_cycle:
                        bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                        pygame.draw.rect(screen, bg_color, input_rect, border_radius=3)
                        pygame.draw.rect(screen, WHITE, input_rect, 1, border_radius=3)
                        
                        if is_bool: label_str = tr('ui', "True") if str_val == "true" else tr('ui', "False")
                        elif key == 'language': label_str = str(val)
                        elif key == 'resolution' and str(val).lower() == 'max': label_str = tr('ui', "Native (Max)")
                        elif key == 'window_mode': label_str = tr('ui', str(val).capitalize())
                        elif 'volume' in key:
                            try: comp = float(val)
                            except: comp = 0.5
                            if abs(comp - 0.0) < 0.001: label_str = tr('ui', "Muted")
                            elif abs(comp - 0.25) < 0.001: label_str = tr('ui', "Low")
                            elif abs(comp - 0.50) < 0.001: label_str = tr('ui', "Balanced")
                            elif abs(comp - 0.75) < 0.001: label_str = tr('ui', "High")
                            elif abs(comp - 1.0) < 0.001: label_str = tr('ui', "Extreme High")
                            else: label_str = f"{tr('ui', 'Custom')} ({comp*100:.0f}%)"
                        else: label_str = str(val)

                        txt_surf = font_12.render(label_str, False, WHITE)
                        screen.blit(txt_surf, (input_rect.centerx - txt_surf.get_width()//2, input_rect.centery - txt_surf.get_height()//2))
                        pygame.draw.polygon(screen, WHITE, [(input_rect.right - S(8), input_rect.centery), (input_rect.right - S(14), input_rect.centery - S(4)), (input_rect.right - S(14), input_rect.centery + S(4))])
                        pygame.draw.polygon(screen, WHITE, [(input_rect.x + S(8), input_rect.centery), (input_rect.x + S(14), input_rect.centery - S(4)), (input_rect.x + S(14), input_rect.centery + S(4))])
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

        # Draw Buttons with no borders
        def _draw_btn(rect, text, col):
            hovered = rect.collidepoint(mouse_pos)
            color = (min(255, col[0]+30), min(255, col[1]+30), min(255, col[2]+30)) if hovered else col
            pygame.draw.rect(screen, color, rect, border_radius=4)
            t_surf = font_16.render(tr('ui', text), False, WHITE)
            screen.blit(t_surf, (rect.centerx - t_surf.get_width()//2, rect.centery - t_surf.get_height()//2))

        _draw_btn(apply_btn, "Apply & Restart", (23, 162, 184))
        _draw_btn(reset_btn, "Reset Default", (200, 50, 50))
        _draw_btn(back_btn, "Back", (80, 80, 80))

preferences_ui = PreferencesMenuUI()