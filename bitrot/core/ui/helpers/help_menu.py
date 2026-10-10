# core/ui/helpers/help_menu.py

import os
import re
import pygame
import core.data.config as config_module
from core.data.config import *
from core.data.localization import tr
from core.ui.text_modal import wrap_text
from core.ui.modals import draw_scrollbar

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class HelpMenuUI:
    def __init__(self):
        self.active = False
        self.active_tab = 0
        self.scroll_offset_y = 0.0
        self.is_dragging_scrollbar = False
        self.is_scrolling_content = False
        self.content_drag_last_y = 0
        self.tabs = []
        self.loaded_lang = None
        self.last_width = 0

    def toggle(self):
        self.active = not self.active
        self.scroll_offset_y = 0.0
        self.is_dragging_scrollbar = False
        self.is_scrolling_content = False
        if self.active:
            self._load_markdown()

    def _load_markdown(self):
        current_lang = getattr(config_module, 'GAME_LANGUAGE', 'en_US')
        scale = UI_SCALE
        def S(val): return int(val * scale)
        usable_w = S(900) - S(70)

        if self.tabs and self.loaded_lang == current_lang and self.last_width == usable_w:
            return

        tabs = []
        current_tab = {'title': 'Home', 'layout': [], 'curr_y': S(10), 'total_h': 0}
        tabs.append(current_tab)

        if current_lang == "en_US":
            target_path = os.path.join(config_module.BASE_DIR, "data.rot", "lib", "data", "help", "en_US_help.md")
        else:
            target_path = os.path.join(config_module.BASE_DIR, "data.rot", "lib", "lang", f"{current_lang}_help.md")

        if not os.path.exists(target_path):
            target_path = os.path.join(config_module.BASE_DIR, "data.rot", "lib", "data", "help", "en_US_help.md")

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                md_lines = f.readlines()

            for line in md_lines:
                line = line.strip()
                if not line:
                    current_tab['curr_y'] += S(10)
                    continue

                if line.startswith("### "):
                    tab_title = line[4:].strip().replace("**", "").replace("[", "").replace("]", "").strip()
                    if current_tab['curr_y'] <= S(15) and not current_tab['layout']:
                        current_tab['title'] = tab_title
                    else:
                        current_tab['total_h'] = current_tab['curr_y']
                        current_tab = {'title': tab_title, 'layout': [], 'curr_y': S(15), 'total_h': 0}
                        tabs.append(current_tab)

                elif line.startswith("# "):
                    title_txt = line[2:].strip().replace("**", "")
                    title_surf = font_16.render(title_txt, False, WHITE)
                    current_tab['layout'].append({
                        'type': 'text',
                        'surf': title_surf,
                        'pos': ((usable_w // 2) - (title_surf.get_width() // 2), current_tab['curr_y'])
                    })
                    current_tab['curr_y'] += title_surf.get_height() + S(25)

                elif line.startswith("* ") or line.startswith("- "):
                    bold_match = re.search(r'^[\*\-]\s+\*\*(.*?)\*\*(.*)', line)
                    if bold_match:
                        key_txt = "• " + bold_match.group(1).strip()
                        desc_txt = bold_match.group(2).strip()
                        if desc_txt.startswith(":"):
                            desc_txt = desc_txt[1:].strip()

                        font_16.set_bold(True)
                        key_surf = font_16.render(key_txt, False, WHITE)
                        font_16.set_bold(False)

                        current_tab['layout'].append({'type': 'text', 'surf': key_surf, 'pos': (S(20), current_tab['curr_y'])})

                        ALIGN_X = S(220)
                        desc_x = S(20) + max(ALIGN_X, key_surf.get_width() + S(15))
                        wrapped = wrap_text(desc_txt, usable_w - desc_x - S(10), font_16)

                        temp_y = current_tab['curr_y']
                        for w_line in wrapped:
                            l_surf = font_16.render(w_line, False, WHITE)
                            current_tab['layout'].append({'type': 'text', 'surf': l_surf, 'pos': (desc_x, temp_y)})
                            temp_y += font_16.get_height() + S(4)

                        current_tab['curr_y'] = max(current_tab['curr_y'] + font_16.get_height() + S(4), temp_y) + S(6)
                    else:
                        i_txt = "• " + line[2:].strip().replace("**", "")
                        wrapped = wrap_text(i_txt, usable_w - S(30), font_16)
                        for w_line in wrapped:
                            l_surf = font_16.render(w_line, False, WHITE)
                            current_tab['layout'].append({'type': 'text', 'surf': l_surf, 'pos': (S(20), current_tab['curr_y'])})
                            temp_y = current_tab['curr_y'] + font_16.get_height() + S(4)
                            current_tab['curr_y'] = temp_y
                        current_tab['curr_y'] += S(6)

                elif line.startswith("![") and "](" in line and line.endswith(")"):
                    img_path = re.search(r'\((.*?)\)', line)
                    if img_path:
                        clean_path = img_path.group(1).strip()
                        if os.path.exists(clean_path):
                            try:
                                if clean_path.lower().endswith('.gif') and PIL_AVAILABLE:
                                    pil_img = Image.open(clean_path)
                                    frames, durations = [], []
                                    for f_idx in range(pil_img.n_frames):
                                        pil_img.seek(f_idx)
                                        f_rgba = pil_img.convert("RGBA")
                                        img_w, img_h = f_rgba.size
                                        pg_img = pygame.image.fromstring(f_rgba.tobytes(), (img_w, img_h), "RGBA").convert_alpha()
                                        scale_f = min(1.0, usable_w / img_w)
                                        scaled_img = pygame.transform.smoothscale(pg_img, (int(img_w * scale_f), int(img_h * scale_f)))
                                        frames.append(scaled_img)
                                        durations.append(pil_img.info.get('duration', 100))

                                    current_tab['layout'].append({
                                        'type': 'gif', 'frames': frames, 'durations': durations,
                                        'current_frame': 0, 'last_update': pygame.time.get_ticks(),
                                        'pos': (S(10), current_tab['curr_y'])
                                    })
                                    current_tab['curr_y'] += frames[0].get_height() + S(15)
                                else:
                                    raw_img = pygame.image.load(clean_path).convert_alpha()
                                    img_w, img_h = raw_img.get_size()
                                    scale_f = min(1.0, usable_w / img_w)
                                    scaled_img = pygame.transform.smoothscale(raw_img, (int(img_w * scale_f), int(img_h * scale_f)))
                                    current_tab['layout'].append({'type': 'image', 'surf': scaled_img, 'pos': (S(10), current_tab['curr_y'])})
                                    current_tab['curr_y'] += scaled_img.get_height() + S(15)
                            except Exception as e:
                                print(f"[HelpMenu] Error loading image {clean_path}: {e}")

                else:
                    p_txt = line.replace("**", "")
                    wrapped = wrap_text(p_txt, usable_w - S(30), font_16)
                    for w_line in wrapped:
                        l_surf = font_16.render(w_line, False, WHITE)
                        current_tab['layout'].append({'type': 'text', 'surf': l_surf, 'pos': (S(10), current_tab['curr_y'])})
                        current_tab['curr_y'] += font_16.get_height() + S(4)
                    current_tab['curr_y'] += S(6)

            current_tab['total_h'] = current_tab['curr_y']
            self.tabs = tabs
            self.loaded_lang = current_lang
            self.last_width = usable_w
            self.active_tab = max(0, min(self.active_tab, len(tabs) - 1))
        except Exception as e:
            print(f"[HelpMenu] Error loading markdown: {e}")

    def get_rects(self):
        scale = UI_SCALE
        def S(val): return int(val * scale)
        center_x = GAME_WIDTH // 2
        center_y = GAME_HEIGHT // 2
        w = S(900)
        h = S(480)

        bg_rect = pygame.Rect(center_x - w // 2, center_y - h // 2, w, h)
        header_rect = pygame.Rect(bg_rect.x, bg_rect.y, bg_rect.width, S(50))

        tab_h = S(38)
        tab_y = header_rect.bottom
        total_tabs = max(1, len(self.tabs))
        tab_w = bg_rect.width // total_tabs
        tab_rects = []
        for i in range(total_tabs):
            cur_w = tab_w if i < total_tabs - 1 else (bg_rect.width - (tab_w * i))
            tab_rects.append(pygame.Rect(bg_rect.x + (i * tab_w), tab_y, cur_w, tab_h))

        padding = S(20)
        list_y = tab_y + tab_h + padding
        list_height = bg_rect.bottom - list_y - padding

        scrollbar_width = S(12)
        list_rect = pygame.Rect(bg_rect.x + padding, list_y, bg_rect.width - (padding * 2) - scrollbar_width - S(10), list_height)
        bar_rect = pygame.Rect(list_rect.right + S(10), list_y, scrollbar_width, list_height)

        btn_width = S(200)
        btn_height = S(45)
        back_btn_rect = pygame.Rect(center_x - btn_width // 2, bg_rect.bottom + S(20), btn_width, btn_height)

        return center_x, center_y, bg_rect, header_rect, tab_rects, list_rect, bar_rect, back_btn_rect

    def handle_events(self, game, events):
        if not self.active:
            return False

        scale = UI_SCALE
        def S(val): return int(val * scale)

        active_tab_data = self.tabs[self.active_tab] if (self.tabs and self.active_tab < len(self.tabs)) else {'total_h': 0}
        _, _, _, _, tab_rects, list_rect, bar_rect, back_btn = self.get_rects()
        max_scroll = max(0.0, float(active_tab_data.get('total_h', 0) - list_rect.height))

        for event in events:
            mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else (event.pos if hasattr(event, 'pos') else pygame.mouse.get_pos())

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.active = False
                continue

            if event.type == pygame.MOUSEWHEEL:
                self.scroll_offset_y = max(0.0, min(self.scroll_offset_y - (event.y * S(35)), max_scroll))
                continue

            if event.type == pygame.MOUSEMOTION:
                if self.is_dragging_scrollbar and max_scroll > 0:
                    handle_h = max(20, (list_rect.height / max(1.0, float(active_tab_data['total_h']))) * list_rect.height)
                    track_h = bar_rect.height - handle_h
                    if track_h > 0:
                        rel_y = mouse_pos[1] - bar_rect.y - (handle_h / 2)
                        ratio = max(0.0, min(1.0, rel_y / track_h))
                        self.scroll_offset_y = ratio * max_scroll
                elif self.is_scrolling_content and max_scroll > 0:
                    delta_y = mouse_pos[1] - self.content_drag_last_y
                    self.content_drag_last_y = mouse_pos[1]
                    self.scroll_offset_y = max(0.0, min(self.scroll_offset_y - delta_y, max_scroll))
                continue

            if event.type == pygame.MOUSEBUTTONUP and getattr(event, 'button', 1) == 1:
                self.is_dragging_scrollbar = False
                self.is_scrolling_content = False
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
                if back_btn.collidepoint(mouse_pos):
                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_ui_hover()
                    self.active = False
                    continue

                for i, r in enumerate(tab_rects):
                    if r.collidepoint(mouse_pos):
                        if self.active_tab != i:
                            self.active_tab = i
                            self.scroll_offset_y = 0.0
                            if hasattr(game, 'sound_manager'):
                                game.sound_manager.play_ui_hover()
                        break

                if bar_rect.collidepoint(mouse_pos) and max_scroll > 0:
                    self.is_dragging_scrollbar = True
                    handle_h = max(20, (list_rect.height / max(1.0, float(active_tab_data['total_h']))) * list_rect.height)
                    track_h = bar_rect.height - handle_h
                    if track_h > 0:
                        rel_y = mouse_pos[1] - bar_rect.y - (handle_h / 2)
                        ratio = max(0.0, min(1.0, rel_y / track_h))
                        self.scroll_offset_y = ratio * max_scroll
                elif list_rect.collidepoint(mouse_pos) and max_scroll > 0:
                    self.is_scrolling_content = True
                    self.content_drag_last_y = mouse_pos[1]

        return True

    def draw(self, screen, mouse_pos, game=None):
        if not self.active:
            return

        self._load_markdown()
        center_x, center_y, bg_rect, header_rect, tab_rects, list_rect, bar_rect, back_btn = self.get_rects()

        # Background Panel
        screen.fill(DARK_GRAY)
        pygame.draw.rect(screen, (35, 35, 35), bg_rect, border_radius=10)
        pygame.draw.rect(screen, GRAY_80, bg_rect, width=2, border_radius=10)

        # Header Title
        pygame.draw.rect(screen, (45, 45, 45), header_rect, border_top_left_radius=10, border_top_right_radius=10)
        pygame.draw.line(screen, GRAY_80, header_rect.bottomleft, header_rect.bottomright, 2)
        title_surf = font_16.render(tr('ui', "Help and Tutorial"), False, WHITE)
        screen.blit(title_surf, (header_rect.x + 20, header_rect.centery - title_surf.get_height() // 2))

        # Category Tabs (Exact match with Controls & Preferences modal tabs)
        for i, r in enumerate(tab_rects):
            is_active_tab = (i == self.active_tab)
            tab_color = (35, 35, 35) if is_active_tab else (25, 25, 25)
            if not is_active_tab and r.collidepoint(mouse_pos):
                tab_color = (45, 45, 45)

            pygame.draw.rect(screen, tab_color, r)
            pygame.draw.rect(screen, WHITE, r, width=1)

            t_title = self.tabs[i]['title'] if i < len(self.tabs) else f"Tab {i+1}"
            tab_surf = font_16.render(tr('ui', t_title), False, WHITE)
            screen.blit(tab_surf, tab_surf.get_rect(center=r.center))

        # Markdown Content
        active_tab_data = self.tabs[self.active_tab] if (self.tabs and self.active_tab < len(self.tabs)) else {'layout': [], 'total_h': 0}
        total_h = active_tab_data.get('total_h', 0)
        max_scroll = max(0.0, float(total_h - list_rect.height))
        self.scroll_offset_y = max(0.0, min(self.scroll_offset_y, max_scroll))

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        try:
            content_surf = screen.subsurface(list_rect)
            y_offset = -int(self.scroll_offset_y)

            for el in active_tab_data.get('layout', []):
                if el['type'] == 'text':
                    draw_y = el['pos'][1] + y_offset
                    if draw_y + el['surf'].get_height() > 0 and draw_y < list_rect.height:
                        content_surf.blit(el['surf'], (el['pos'][0], draw_y))
                elif el['type'] == 'image':
                    draw_y = el['pos'][1] + y_offset
                    if draw_y + el['surf'].get_height() > 0 and draw_y < list_rect.height:
                        content_surf.blit(el['surf'], (el['pos'][0], draw_y))
                elif el['type'] == 'gif':
                    now = pygame.time.get_ticks()
                    cur_idx = el.get('current_frame', 0)
                    durations = el.get('durations', [100])
                    dur = durations[cur_idx] if cur_idx < len(durations) else 100
                    if now - el.get('last_update', 0) > dur:
                        el['current_frame'] = (cur_idx + 1) % len(el['frames'])
                        el['last_update'] = now
                    frame_surf = el['frames'][el['current_frame']]
                    draw_y = el['pos'][1] + y_offset
                    if draw_y + frame_surf.get_height() > 0 and draw_y < list_rect.height:
                        content_surf.blit(frame_surf, (el['pos'][0], draw_y))
        except ValueError:
            pass

        screen.set_clip(old_clip)
        draw_scrollbar(screen, {}, bar_rect, list_rect.height, total_h, int(self.scroll_offset_y))

        # Bottom Back Button
        is_hover_back = back_btn.collidepoint(mouse_pos)
        col = (110, 110, 110) if is_hover_back else (80, 80, 80)
        pygame.draw.rect(screen, col, back_btn, border_radius=4)
        back_txt = font_16.render(tr('ui', "Back"), False, WHITE)
        screen.blit(back_txt, back_txt.get_rect(center=back_btn.center))

help_ui = HelpMenuUI()