import pygame
import re
import os
import csv
from datetime import datetime
from editor.config import GAME_ROOT,SPRITE_ROOT, TILE_SIZE, SIDEBAR_WIDTH, SCREEN_HEIGHT, FILE_TREE_WIDTH, SCREEN_WIDTH, ICON_SIZE, BUILDINGS_DIR, BUILDING_PREVIEW_SIZE, TAB_BAR_HEIGHT
from editor.assets import load_editor_icons

class UITextBox:
    """A robust text input handling drag selection, cursor blinking, and clipboard."""
    def __init__(self, x, y, width, height, font, text=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = text
        self.cursor_pos = len(text)
        self.sel_start = None
        self.active = False
        self.scroll_x = 0
        self.blink_timer = 0
        self.dragging = False

    def delete_selection(self):
        if self.sel_start is not None and self.sel_start != self.cursor_pos:
            s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
            self.text = self.text[:s] + self.text[e:]
            self.cursor_pos = s
            self.sel_start = None
            return True
        return False

    def _get_idx_from_x(self, x):
        rel_x = x - self.rect.x + self.scroll_x
        for i in range(len(self.text)):
            w = self.font.size(self.text[:i])[0]
            cw = self.font.size(self.text[i])[0]
            if rel_x < w + cw / 2: return i
        return len(self.text)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.active = True
                self.cursor_pos = self._get_idx_from_x(event.pos[0])
                self.sel_start = self.cursor_pos
                self.dragging = True
                return True
            else:
                self.active = False
                return False
                
        if not self.active: return False

        if event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.cursor_pos = self._get_idx_from_x(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return True
        elif event.type == pygame.KEYDOWN:
            ctrl = event.mod & pygame.KMOD_CTRL
            shift = event.mod & pygame.KMOD_SHIFT
            
            if ctrl and event.key == pygame.K_c:
                if self.sel_start is not None and self.sel_start != self.cursor_pos:
                    s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
                    try: pygame.scrap.put(pygame.SCRAP_TEXT, self.text[s:e].encode('utf-8'))
                    except: pass
            elif ctrl and event.key == pygame.K_v:
                try:
                    t = pygame.scrap.get(pygame.SCRAP_TEXT).decode('utf-8').strip('\x00')
                    self.delete_selection()
                    self.text = self.text[:self.cursor_pos] + t + self.text[self.cursor_pos:]
                    self.cursor_pos += len(t)
                    self.sel_start = None
                except: pass
            elif ctrl and event.key == pygame.K_x:
                if self.sel_start is not None and self.sel_start != self.cursor_pos:
                    s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
                    try: pygame.scrap.put(pygame.SCRAP_TEXT, self.text[s:e].encode('utf-8'))
                    except: pass
                    self.delete_selection()
            elif event.key == pygame.K_LEFT:
                if shift:
                    if self.sel_start is None: self.sel_start = self.cursor_pos
                else: self.sel_start = None
                self.cursor_pos = max(0, self.cursor_pos - 1)
            elif event.key == pygame.K_RIGHT:
                if shift:
                    if self.sel_start is None: self.sel_start = self.cursor_pos
                else: self.sel_start = None
                self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
            elif event.key == pygame.K_BACKSPACE:
                if not self.delete_selection():
                    if self.cursor_pos > 0:
                        self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                        self.cursor_pos -= 1
            elif event.key == pygame.K_DELETE:
                if not self.delete_selection():
                    if self.cursor_pos < len(self.text):
                        self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
            elif event.key == pygame.K_HOME:
                if shift:
                    if self.sel_start is None: self.sel_start = self.cursor_pos
                else: self.sel_start = None
                self.cursor_pos = 0
            elif event.key == pygame.K_END:
                if shift:
                    if self.sel_start is None: self.sel_start = self.cursor_pos
                else: self.sel_start = None
                self.cursor_pos = len(self.text)
            else:
                if event.unicode and event.unicode.isprintable():
                    self.delete_selection()
                    self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                    self.cursor_pos += len(event.unicode)
            return True
        return False

    def draw(self, surface):
        cursor_x = self.font.size(self.text[:self.cursor_pos])[0]
        if cursor_x - self.scroll_x < 0: self.scroll_x = cursor_x
        elif cursor_x - self.scroll_x > self.rect.width - 10: self.scroll_x = cursor_x - self.rect.width + 10

        pygame.draw.rect(surface, (40, 40, 40), self.rect)
        pygame.draw.rect(surface, (255, 255, 255) if self.active else (100, 100, 100), self.rect, 2)
        
        surface.set_clip(self.rect.inflate(-4, -4))
        
        if self.sel_start is not None and self.sel_start != self.cursor_pos:
            s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
            sx = self.font.size(self.text[:s])[0] - self.scroll_x + self.rect.x + 5
            sw = self.font.size(self.text[s:e])[0]
            pygame.draw.rect(surface, (0, 100, 200), (sx, self.rect.y + 2, sw, self.rect.height - 4))
        
        ts = self.font.render(self.text, True, (255, 255, 255))
        surface.blit(ts, (self.rect.x + 5 - self.scroll_x, self.rect.y + (self.rect.height - ts.get_height())//2))
        
        if self.active:
            self.blink_timer += 1
            if (self.blink_timer // 30) % 2 == 0:
                cx = self.rect.x + 5 + cursor_x - self.scroll_x
                pygame.draw.line(surface, (255, 255, 255), (cx, self.rect.y + 4), (cx, self.rect.bottom - 4), 2)
                
        surface.set_clip(None)

class UIDropdown:
    """A dropdown menu component handling text, selection, icons, and scroll dragging."""
    def __init__(self, x, y, width, height, font, options, selected_value="", searchable=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.options = options  
        self.selected_value = selected_value
        self.expanded = False
        self.searchable = searchable
        self.search_text = ""
        
        self.scroll_offset = 0
        self.item_height = 30
        self.max_visible_items = 5 # Reduced to 5 to keep it compact
        
        self.list_rect = pygame.Rect(x, y + height, width, 0)
        
        self.selected_label = ""
        self.dragging_scroll = False
        self.scroll_start_y = 0
        self.scroll_start_offset = 0
        self.blink_timer = 0
        self._update_label()

    def _update_label(self):
        self.selected_label = ""
        for opt in self.options:
            if opt['value'] == self.selected_value:
                self.selected_label = opt['label']
                break

    @property
    def text(self):
        return self.selected_value

    def get_filtered_options(self):
        if not self.searchable or not self.search_text:
            return self.options
        return [o for o in self.options if self.search_text.lower() in o['label'].lower()]

    def _recalc_list_rect(self):
        filtered = self.get_filtered_options()
        visible_count = min(len(filtered), self.max_visible_items)
        base_h = visible_count * self.item_height
        if self.searchable:
            base_h += self.item_height
            
        from editor.config import SCREEN_HEIGHT
        self.list_rect.height = base_h
        
        # Smart positioning: If it clips the bottom, open upwards!
        if self.rect.bottom + base_h > SCREEN_HEIGHT - 10:
            self.list_rect.bottom = self.rect.top
        else:
            self.list_rect.top = self.rect.bottom

    def handle_event(self, event):
        # Handle typing for search filter
        if event.type == pygame.KEYDOWN and self.expanded and self.searchable:
            if event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
            else:
                if event.unicode and event.unicode.isprintable():
                    self.search_text += event.unicode
            self.scroll_offset = 0
            self._recalc_list_rect()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.expanded:
                filtered = self.get_filtered_options()
                content_h = len(filtered) * self.item_height
                list_view_h = self.list_rect.height - (self.item_height if self.searchable else 0)
                max_scroll = max(0, content_h - list_view_h)
                
                # Scrollbar drag click
                if max_scroll > 0:
                    sb_rect = pygame.Rect(self.list_rect.right - 8, self.list_rect.y + (self.item_height if self.searchable else 0), 8, list_view_h)
                    if sb_rect.collidepoint(event.pos):
                        self.dragging_scroll = True
                        self.scroll_start_y = event.pos[1]
                        self.scroll_start_offset = self.scroll_offset
                        return True

                # Option or Search bar click
                if self.list_rect.collidepoint(event.pos):
                    if self.searchable and event.pos[1] < self.list_rect.y + self.item_height:
                        return True # Clicked the search bar, don't close

                    start_y = self.list_rect.y + (self.item_height if self.searchable else 0)
                    rel_y = event.pos[1] - start_y + self.scroll_offset
                    idx = int(rel_y // self.item_height)
                    
                    if 0 <= idx < len(filtered):
                        self.selected_value = filtered[idx]['value']
                        self._update_label()
                        self.expanded = False
                        self.search_text = ""
                    return True
                elif self.rect.collidepoint(event.pos):
                    self.expanded = False
                    self.search_text = ""
                    return True
                else:
                    self.expanded = False
                    self.search_text = ""
                    return False
            else:
                if self.rect.collidepoint(event.pos):
                    self.expanded = True
                    self.search_text = ""
                    self.scroll_offset = 0
                    self._recalc_list_rect()
                    return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_scroll:
                self.dragging_scroll = False
                return True

        elif event.type == pygame.MOUSEMOTION:
            if getattr(self, 'dragging_scroll', False):
                filtered = self.get_filtered_options()
                content_h = len(filtered) * self.item_height
                list_view_h = self.list_rect.height - (self.item_height if self.searchable else 0)
                max_scroll = max(0, content_h - list_view_h)
                
                thumb_h = max(10, list_view_h * (list_view_h / content_h)) if content_h > 0 else list_view_h
                track_space = list_view_h - thumb_h
                
                if track_space > 0:
                    dy = event.pos[1] - self.scroll_start_y
                    scroll_per_pixel = max_scroll / track_space
                    self.scroll_offset = max(0, min(max_scroll, self.scroll_start_offset + dy * scroll_per_pixel))
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self.expanded and self.list_rect.collidepoint(event.pos):
                if event.button == 4:
                    self.scroll_offset = max(0, self.scroll_offset - 25)
                elif event.button == 5:
                    filtered = self.get_filtered_options()
                    content_h = len(filtered) * self.item_height
                    list_view_h = self.list_rect.height - (self.item_height if self.searchable else 0)
                    max_scroll = max(0, content_h - list_view_h)
                    self.scroll_offset = min(max_scroll, self.scroll_offset + 25)
                return True
                
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, (40, 40, 40), self.rect)
        pygame.draw.rect(surface, (255, 255, 0) if self.expanded else (100, 100, 100), self.rect, 2)
        
        lbl_surf = self.font.render(self.selected_label or "None", True, (255, 255, 255))
        selected_icon = next((opt.get('icon') for opt in self.options if opt['value'] == self.selected_value), None)
        
        draw_x = self.rect.x + 5
        if selected_icon:
            ic_size = self.rect.height - 6
            scaled_ic = pygame.transform.scale(selected_icon, (ic_size, ic_size))
            surface.blit(scaled_ic, (draw_x, self.rect.y + 3))
            draw_x += ic_size + 8
            
        surface.set_clip(self.rect.inflate(-4, -4))
        surface.blit(lbl_surf, (draw_x, self.rect.y + (self.rect.height - lbl_surf.get_height())//2))
        surface.set_clip(None)
        
        pygame.draw.polygon(surface, (150, 150, 150), [
            (self.rect.right - 18, self.rect.centery - 2),
            (self.rect.right - 6, self.rect.centery - 2),
            (self.rect.right - 12, self.rect.centery + 4)
        ])

    def draw_list(self, surface):
        if not self.expanded: return
        
        pygame.draw.rect(surface, (50, 50, 50), self.list_rect)
        pygame.draw.rect(surface, (200, 200, 200), self.list_rect, 1)
        
        start_y = self.list_rect.y
        if self.searchable:
            search_rect = pygame.Rect(self.list_rect.x, self.list_rect.y, self.list_rect.width, self.item_height)
            pygame.draw.rect(surface, (30, 30, 40), search_rect)
            pygame.draw.rect(surface, (150, 150, 150), search_rect, 1)
            
            self.blink_timer += 1
            cursor = "|" if (self.blink_timer // 30) % 2 == 0 else ""
            s_txt = self.font.render("Search: " + self.search_text + cursor, True, (255, 255, 100))
            surface.set_clip(search_rect.inflate(-4, -4))
            surface.blit(s_txt, (search_rect.x + 5, search_rect.y + (self.item_height - s_txt.get_height())//2))
            surface.set_clip(None)
            start_y += self.item_height

        view_rect = pygame.Rect(self.list_rect.x, start_y, self.list_rect.width, self.list_rect.height - (self.item_height if self.searchable else 0))
        surface.set_clip(view_rect)
        
        mouse_pos = pygame.mouse.get_pos()
        filtered = self.get_filtered_options()
        
        for i, opt in enumerate(filtered):
            opt_y = start_y + i * self.item_height - self.scroll_offset
            if opt_y + self.item_height < start_y or opt_y > self.list_rect.bottom:
                continue
                
            opt_rect = pygame.Rect(self.list_rect.x, opt_y, self.list_rect.width, self.item_height)
            
            if opt_rect.collidepoint(mouse_pos):
                pygame.draw.rect(surface, (70, 70, 90), opt_rect)
            
            draw_x = opt_rect.x + 5
            if opt.get('icon'):
                ic_size = self.item_height - 6
                scaled_ic = pygame.transform.scale(opt.get('icon'), (ic_size, ic_size))
                surface.blit(scaled_ic, (draw_x, opt_rect.y + 3))
                draw_x += ic_size + 8
                
            opt_lbl = self.font.render(opt['label'], True, (255, 255, 255))
            surface.blit(opt_lbl, (draw_x, opt_rect.y + (self.item_height - opt_lbl.get_height())//2))

        surface.set_clip(None)
        
        content_h = len(filtered) * self.item_height
        list_view_h = view_rect.height
        max_scroll = max(0, content_h - list_view_h)
        
        if max_scroll > 0:
            sb_rect = pygame.Rect(self.list_rect.right - 8, start_y, 8, list_view_h)
            pygame.draw.rect(surface, (30, 30, 30), sb_rect)
            thumb_h = max(10, list_view_h * (list_view_h / content_h))
            thumb_y = start_y + (self.scroll_offset / max_scroll) * (list_view_h - thumb_h)
            pygame.draw.rect(surface, (150, 150, 150), pygame.Rect(sb_rect.x, thumb_y, 8, thumb_h))

class UITextArea:
    """A multi-line text input field supporting word wrap and scrollbars."""
    def __init__(self, x, y, width, height, font, text=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = text
        self.cursor_pos = len(text)
        self.sel_start = None
        self.active = False
        self.scroll_y = 0
        self.blink_timer = 0
        self.dragging = False
        self.dragging_scroll = False
        self.scroll_start_y = 0
        self.scroll_start_offset = 0
        self.line_height = self.font.get_linesize() + 2
        self.lines = []
        self.thumb_rect = None
        self._update_lines()
        self.history = [text]          # stack of text snapshots
        self.history_index = 0         # current position in history
        self.undo_redo_suspended = False  # avoid re-triggering during undo/redo

    def _push_history(self):
        if self.undo_redo_suspended:
            return
        # If we are not at the end, truncate future
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        # Avoid duplicate consecutive entries
        if self.history and self.history[-1] == self.text:
            return
        self.history.append(self.text)
        self.history_index = len(self.history) - 1
        # Limit history size (optional)
        if len(self.history) > 100:
            self.history = self.history[-100:]
            self.history_index = len(self.history) - 1

    def _update_lines(self):
        self.lines = []
        if not self.text:
            self.lines.append(("", 0, 0))
            return

        start_idx = 0
        current_line = ""
        for i, char in enumerate(self.text):
            if char == '\n':
                self.lines.append((current_line, start_idx, i))
                current_line = ""
                start_idx = i + 1
                continue
                
            test_line = current_line + char
            if self.font.size(test_line)[0] > self.rect.width - 25: 
                last_space = current_line.rfind(' ')
                if last_space != -1 and last_space > 0:
                    split_idx = start_idx + last_space
                    self.lines.append((current_line[:last_space], start_idx, split_idx))
                    start_idx = split_idx + 1 
                    current_line = current_line[last_space+1:] + char
                else:
                    self.lines.append((current_line, start_idx, i))
                    start_idx = i
                    current_line = char
            else:
                current_line = test_line
                
        self.lines.append((current_line, start_idx, len(self.text)))

    @property
    def _max_scroll(self):
        return max(0, len(self.lines) * self.line_height + 10 - self.rect.height)

    def delete_selection(self):
        if self.sel_start is not None and self.sel_start != self.cursor_pos:
            s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
            self.text = self.text[:s] + self.text[e:]
            self.cursor_pos = s
            self.sel_start = None
            self._update_lines()
            return True
        return False

    def _get_idx_from_pos(self, x, y):
        rel_y = y - self.rect.y + self.scroll_y - 5
        line_idx = int(rel_y // self.line_height)
        line_idx = max(0, min(len(self.lines) - 1, line_idx))
        
        line_text, start_idx, end_idx = self.lines[line_idx]
        rel_x = x - self.rect.x - 5
        
        for i in range(len(line_text)):
            w = self.font.size(line_text[:i])[0]
            cw = self.font.size(line_text[i])[0]
            if rel_x < w + cw / 2: return start_idx + i
        return end_idx

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.thumb_rect and self.thumb_rect.collidepoint(event.pos):
                    self.dragging_scroll = True
                    self.scroll_start_y = event.pos[1]
                    self.scroll_start_offset = self.scroll_y
                    return True
                    
                sb_track = pygame.Rect(self.rect.right - 12, self.rect.y, 12, self.rect.height)
                if sb_track.collidepoint(event.pos) and self._max_scroll > 0:
                    return True

                if self.rect.collidepoint(event.pos):
                    self.active = True
                    self.cursor_pos = self._get_idx_from_pos(*event.pos)
                    self.sel_start = self.cursor_pos
                    self.dragging = True
                    return True
                else:
                    self.active = False
                    return False
                    
            elif event.button in (4, 5) and self.rect.collidepoint(event.pos):
                if event.button == 4: self.scroll_y = max(0, self.scroll_y - 20)
                else: self.scroll_y = min(self._max_scroll, self.scroll_y + 20)
                return True

        if not self.active and not self.dragging_scroll: return False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            self.dragging_scroll = False
            return True

        if event.type == pygame.MOUSEMOTION:
            if self.dragging_scroll:
                thumb_h = max(15, self.rect.height * (self.rect.height / (len(self.lines) * self.line_height + 10)))
                track_space = self.rect.height - thumb_h
                if track_space > 0:
                    dy = event.pos[1] - self.scroll_start_y
                    self.scroll_y = max(0, min(self._max_scroll, self.scroll_start_offset + dy * (self._max_scroll / track_space)))
                return True
            elif self.dragging:
                self.cursor_pos = self._get_idx_from_pos(*event.pos)
                return True

        if event.type == pygame.KEYDOWN and self.active:
            ctrl = event.mod & pygame.KMOD_CTRL
            shift = event.mod & pygame.KMOD_SHIFT
            
            if ctrl and event.key == pygame.K_c:
                if self.sel_start is not None and self.sel_start != self.cursor_pos:
                    s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
                    try: pygame.scrap.put(pygame.SCRAP_TEXT, self.text[s:e].encode('utf-8'))
                    except: pass
            elif ctrl and event.key == pygame.K_v:
                try:
                    t = pygame.scrap.get(pygame.SCRAP_TEXT).decode('utf-8').strip('\x00')
                    self.delete_selection()
                    self.text = self.text[:self.cursor_pos] + t + self.text[self.cursor_pos:]
                    self.cursor_pos += len(t)
                    self.sel_start = None
                    self._update_lines()
                except: pass
            elif ctrl and event.key == pygame.K_x:
                if self.sel_start is not None and self.sel_start != self.cursor_pos:
                    s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
                    try: pygame.scrap.put(pygame.SCRAP_TEXT, self.text[s:e].encode('utf-8'))
                    except: pass
                    self.delete_selection()
            elif ctrl and event.key == pygame.K_z:
                # Undo
                if self.history_index > 0:
                    self.undo_redo_suspended = True
                    self.history_index -= 1
                    self.text = self.history[self.history_index]
                    self.cursor_pos = len(self.text)
                    self.sel_start = None
                    self._update_lines()
                    self.undo_redo_suspended = False
                    return True
            elif ctrl and event.key == pygame.K_u:
                # Redo
                if self.history_index < len(self.history) - 1:
                    self.undo_redo_suspended = True
                    self.history_index += 1
                    self.text = self.history[self.history_index]
                    self.cursor_pos = len(self.text)
                    self.sel_start = None
                    self._update_lines()
                    self.undo_redo_suspended = False
                    return True
            elif event.key == pygame.K_LEFT:
                if shift:
                    if self.sel_start is None: self.sel_start = self.cursor_pos
                else: self.sel_start = None
                self.cursor_pos = max(0, self.cursor_pos - 1)
            elif event.key == pygame.K_RIGHT:
                if shift:
                    if self.sel_start is None: self.sel_start = self.cursor_pos
                else: self.sel_start = None
                self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
            elif event.key == pygame.K_UP:
                if shift:
                    if self.sel_start is None: self.sel_start = self.cursor_pos
                else: self.sel_start = None
                for i, (l_text, s_idx, e_idx) in enumerate(self.lines):
                    if s_idx <= self.cursor_pos <= e_idx:
                        if i > 0:
                            p_text, ps_idx, pe_idx = self.lines[i-1]
                            curr_x = self.font.size(l_text[:self.cursor_pos - s_idx])[0]
                            best_idx = pe_idx
                            for j in range(len(p_text)):
                                if self.font.size(p_text[:j])[0] >= curr_x:
                                    best_idx = ps_idx + j
                                    break
                            self.cursor_pos = best_idx
                        break
            elif event.key == pygame.K_DOWN:
                if shift:
                    if self.sel_start is None: self.sel_start = self.cursor_pos
                else: self.sel_start = None
                for i, (l_text, s_idx, e_idx) in enumerate(self.lines):
                    if s_idx <= self.cursor_pos <= e_idx:
                        if i < len(self.lines) - 1:
                            n_text, ns_idx, ne_idx = self.lines[i+1]
                            curr_x = self.font.size(l_text[:self.cursor_pos - s_idx])[0]
                            best_idx = ne_idx
                            for j in range(len(n_text)):
                                if self.font.size(n_text[:j])[0] >= curr_x:
                                    best_idx = ns_idx + j
                                    break
                            self.cursor_pos = best_idx
                        break
            elif event.key == pygame.K_BACKSPACE:
                if not self.delete_selection() and self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
                    self._update_lines()
            elif event.key == pygame.K_DELETE:
                if not self.delete_selection() and self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
                    self._update_lines()
            elif event.key == pygame.K_RETURN:
                self.delete_selection()
                self.text = self.text[:self.cursor_pos] + "\n" + self.text[self.cursor_pos:]
                self.cursor_pos += 1
                self._update_lines()
            else:
                if event.unicode and event.unicode.isprintable():
                    self.delete_selection()
                    self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                    self.cursor_pos += len(event.unicode)
                    self._update_lines()
            return True
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, (40, 40, 40), self.rect)
        pygame.draw.rect(surface, (255, 255, 255) if self.active else (100, 100, 100), self.rect, 2)
        
        surface.set_clip(self.rect.inflate(-4, -4))
        
        cursor_y, cursor_x = 0, 0
        for i, (l_text, s_idx, e_idx) in enumerate(self.lines):
            if s_idx <= self.cursor_pos <= e_idx:
                cursor_y = i * self.line_height
                sub = l_text[:self.cursor_pos - s_idx]
                cursor_x = self.font.size(sub)[0]
                break
                
        if self.active:
            if cursor_y < self.scroll_y:
                self.scroll_y = cursor_y
            elif cursor_y + self.line_height > self.scroll_y + self.rect.height - 10:
                self.scroll_y = cursor_y + self.line_height - self.rect.height + 10
        
        for i, (l_text, s_idx, e_idx) in enumerate(self.lines):
            y_pos = self.rect.y + 5 + i * self.line_height - self.scroll_y
            if y_pos + self.line_height < self.rect.y or y_pos > self.rect.bottom:
                continue
                
            if self.sel_start is not None and self.sel_start != self.cursor_pos:
                s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
                if s <= e_idx and e >= s_idx:
                    h_start = max(s, s_idx)
                    h_end = min(e, e_idx)
                    h_x = self.font.size(l_text[:h_start - s_idx])[0]
                    h_w = self.font.size(l_text[h_start - s_idx : h_end - s_idx])[0]
                    if e > e_idx: h_w += 5 
                    pygame.draw.rect(surface, (0, 100, 200), (self.rect.x + 5 + h_x, y_pos, h_w, self.line_height))
                    
            ts = self.font.render(l_text, True, (255, 255, 255))
            surface.blit(ts, (self.rect.x + 5, y_pos))
            
        if self.active:
            self.blink_timer += 1
            if (self.blink_timer // 30) % 2 == 0:
                cx = self.rect.x + 5 + cursor_x
                cy = self.rect.y + 5 + cursor_y - self.scroll_y
                pygame.draw.line(surface, (255, 255, 255), (cx, cy), (cx, cy + self.line_height - 2), 2)
                
        surface.set_clip(None)
        
        if self._max_scroll > 0:
            sb_rect = pygame.Rect(self.rect.right - 12, self.rect.y, 12, self.rect.height)
            pygame.draw.rect(surface, (30, 30, 30), sb_rect)
            content_h = len(self.lines) * self.line_height + 10
            thumb_h = max(15, self.rect.height * (self.rect.height / content_h))
            thumb_y = self.rect.y + (self.scroll_y / self._max_scroll) * (self.rect.height - thumb_h)
            self.thumb_rect = pygame.Rect(sb_rect.x + 2, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, (150, 150, 150), self.thumb_rect)
        else:
            self.thumb_rect = None

class MenuBar:
    def __init__(self, width, height, font, modes):
        self.rect = pygame.Rect(0, 0, width, height)
        self.font = font
        self.modes = modes
        self.active_mode = modes[0]
        self.tabs = []
        self._update_tabs()

    def resize(self, width):
        self.rect.width = width
        self._update_tabs()

    def _update_tabs(self):
        self.tabs = []
        tab_w = 150
        for i, mode in enumerate(self.modes):
            self.tabs.append({
                "mode": mode,
                "rect": pygame.Rect(i*tab_w, self.rect.y, tab_w, self.rect.height),
                "label": mode
            })

    def draw(self, surface):
        pygame.draw.rect(surface, (30, 30, 30), self.rect)
        for tab in self.tabs:
            is_active = (tab["mode"] == self.active_mode)
            color = (70, 70, 90) if is_active else (40, 40, 40)
            pygame.draw.rect(surface, color, tab["rect"])
            pygame.draw.rect(surface, (0, 0, 0), tab["rect"], 1)
            
            text_color = (255, 255, 255) if is_active else (150, 150, 150)
            lbl = self.font.render(tab["label"], True, text_color)
            surface.blit(lbl, (tab["rect"].centerx - lbl.get_width()//2, tab["rect"].centery - lbl.get_height()//2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab in self.tabs:
                if tab["rect"].collidepoint(event.pos):
                    if self.active_mode != tab["mode"]:
                        self.active_mode = tab["mode"]
                        return self.active_mode
        return None

# --- Log Console ---
class LogConsole:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.messages = [] 
        self.line_height = 20
        self.scroll_offset = 0
        self.max_scroll = 0
        
        self.dragging_scroll = False
        self.scrollbar_track_rect = None
        self.scrollbar_thumb_rect = None
        self.scroll_start_mouse_y = 0
        self.scroll_start_offset = 0

    def resize(self, width, height, y=None):
        if y is not None: self.rect.y = y
        self.rect.width = width
        self.rect.height = height

    def add_message(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"<{timestamp}> {text}"
        self.messages.append(full_msg)
        total_h = len(self.messages) * self.line_height
        if total_h > self.rect.height:
            self.scroll_offset = total_h - self.rect.height

    def draw(self, surface):
        pygame.draw.rect(surface, (20, 20, 20), self.rect)
        pygame.draw.line(surface, (100, 100, 100), self.rect.topleft, self.rect.topright)
        surface.set_clip(self.rect)
        start_y = self.rect.y + 5 - self.scroll_offset
        for i, msg in enumerate(self.messages):
            y = start_y + i * self.line_height
            if y + self.line_height > self.rect.y and y < self.rect.bottom:
                text_surf = self.font.render(msg, True, (200, 200, 200))
                surface.blit(text_surf, (self.rect.x + 10, y))
        surface.set_clip(None)
        content_height = len(self.messages) * self.line_height + 10
        self.max_scroll = max(0, content_height - self.rect.height)
        
        if self.max_scroll > 0:
            track_x = self.rect.right - 12
            self.scrollbar_track_rect = pygame.Rect(track_x, self.rect.y, 12, self.rect.height)
            pygame.draw.rect(surface, (40, 40, 40), self.scrollbar_track_rect)
            view_h = self.rect.height
            thumb_h = max(20, (view_h / content_height) * view_h)
            ratio = self.scroll_offset / self.max_scroll
            thumb_y = self.rect.y + ratio * (view_h - thumb_h)
            self.scrollbar_thumb_rect = pygame.Rect(track_x, thumb_y, 12, thumb_h)
            pygame.draw.rect(surface, (100, 100, 100), self.scrollbar_thumb_rect)
        else:
            self.scrollbar_thumb_rect = None
            self.scrollbar_track_rect = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP: self.dragging_scroll = False
        if event.type == pygame.MOUSEMOTION:
            if self.dragging_scroll and self.scrollbar_thumb_rect and self.max_scroll > 0:
                dy = event.pos[1] - self.scroll_start_mouse_y
                view_h = self.scrollbar_track_rect.height
                thumb_h = self.scrollbar_thumb_rect.height
                track_space = view_h - thumb_h
                if track_space > 0:
                    scroll_per_pixel = self.max_scroll / track_space
                    self.scroll_offset = self.scroll_start_offset + (dy * scroll_per_pixel)
                    self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
                return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if self.rect.collidepoint(mx, my):
                if self.scrollbar_thumb_rect and self.scrollbar_thumb_rect.collidepoint(mx, my):
                    self.dragging_scroll = True
                    self.scroll_start_mouse_y = my
                    self.scroll_start_offset = self.scroll_offset
                    return True
                if event.button == 4:
                    self.scroll_offset = max(0, self.scroll_offset - 40)
                    return True
                if event.button == 5:
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + 40)
                    return True
        return False

# --- New Building Modal ---
class NewBuildingModal:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.active = False
        
        self.name_input = UITextBox(x + 70, y + 50, 200, 30, font, "Building")
        self.width_input = UITextBox(x + 70, y + 100, 80, 30, font, "10")
        self.height_input = UITextBox(x + 70, y + 150, 80, 30, font, "10")
        
        self.create_btn = pygame.Rect(x + 50, y + 200, 80, 30)
        self.cancel_btn = pygame.Rect(x + 170, y + 200, 80, 30)

    def handle_event(self, event):
        if not self.active: return None
        
        if self.name_input.handle_event(event): return None
        if self.width_input.handle_event(event): return None
        if self.height_input.handle_event(event): return None
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.create_btn.collidepoint(event.pos):
                try:
                    w = int(self.width_input.text)
                    h = int(self.height_input.text)
                    self.active = False
                    return {"action": "create_building", "name": self.name_input.text, "width": w, "height": h}
                except ValueError:
                    print("Invalid dimensions")
            elif self.cancel_btn.collidepoint(event.pos):
                self.active = False
        return None

    def draw(self, surface):
        if not self.active: return
        
        s = pygame.Surface((self.rect.width, self.rect.height))
        s.fill((60, 60, 60))
        surface.blit(s, self.rect.topleft)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2)
        
        surface.blit(self.font.render("New Building", True, (255, 255, 255)), (self.rect.x + 20, self.rect.y + 10))
        
        surface.blit(self.font.render("Name:", True, (200, 200, 200)), (self.rect.x + 10, self.name_input.rect.y + 5))
        self.name_input.draw(surface)
        surface.blit(self.font.render("W:", True, (200, 200, 200)), (self.rect.x + 10, self.width_input.rect.y + 5))
        self.width_input.draw(surface)
        surface.blit(self.font.render("H:", True, (200, 200, 200)), (self.rect.x + 10, self.height_input.rect.y + 5))
        self.height_input.draw(surface)

        pygame.draw.rect(surface, (0, 150, 0), self.create_btn)
        create_txt = self.font.render("Create", True, (255, 255, 255))
        surface.blit(create_txt, (self.create_btn.centerx - create_txt.get_width()//2, self.create_btn.centery - create_txt.get_height()//2))

        pygame.draw.rect(surface, (150, 0, 0), self.cancel_btn)
        cancel_txt = self.font.render("Cancel", True, (255, 255, 255))
        surface.blit(cancel_txt, (self.cancel_btn.centerx - cancel_txt.get_width()//2, self.cancel_btn.centery - cancel_txt.get_height()//2))

class NewMapModal:
    def __init__(self, x, y, width, height, font, current_map_name):
        self.font = font
        self.active = False
        self.current_map_name = current_map_name
        self.connection = None
        self.layer = 1 

        self.current_connections = {'TOP': 0, 'RIGHT': 0, 'BOTTOM': 0, 'LEFT': 0}
        self.current_layer = 1
        self.current_pos_id = 0
        
        match = re.match(r"map_L(\d+)_P(?:\d+_)*(\d+)_(\d+)_(\d+)_(\d+)_(\d+)", current_map_name)
        if match:
            self.current_layer = int(match.group(1))
            self.current_pos_id = int(match.group(2))
            self.current_connections['TOP'] = int(match.group(3))
            self.current_connections['RIGHT'] = int(match.group(4))
            self.current_connections['BOTTOM'] = int(match.group(5))
            self.current_connections['LEFT'] = int(match.group(6))

        self.conn_title_y = y + 65
        conn_btn_y = self.conn_title_y + 25
        conn_section_bottom = conn_btn_y + 70

        self.layer_title_y = conn_section_bottom + 15
        layer_btn_y = self.layer_title_y + 25
        layer_section_bottom = layer_btn_y + 30

        min_required_height = (layer_section_bottom + 20 + 30 + 20) - y
        
        if height < min_required_height: height = min_required_height
        self.rect = pygame.Rect(x, y, width, height)

        self.conn_buttons = {
            'TOP': pygame.Rect(x + 20, conn_btn_y, 100, 30),
            'RIGHT': pygame.Rect(x + 140, conn_btn_y, 100, 30),
            'BOTTOM': pygame.Rect(x + 20, conn_btn_y + 40, 100, 30),
            'LEFT': pygame.Rect(x + 140, conn_btn_y + 40, 100, 30),
        }
        
        self.layer_buttons = {
            1: pygame.Rect(x + 20, layer_btn_y, 100, 30),
            2: pygame.Rect(x + 140, layer_btn_y, 100, 30),
        }

        btn_y = y + height - 50
        self.create_button_rect = pygame.Rect(x + 20, btn_y, 100, 30)
        self.cancel_button_rect = pygame.Rect(x + 140, btn_y, 100, 30)

    def preselect_direction(self, direction):
        if direction in self.conn_buttons and self.current_connections[direction] == 0:
            self.connection = direction
        else: self.connection = None
        
    def handle_event(self, event):
        if not self.active: return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for direction, rect in self.conn_buttons.items():
                if rect.collidepoint(event.pos):
                    if self.current_connections[direction] == 0: self.connection = direction
                    return None
            for layer_num, rect in self.layer_buttons.items():
                if rect.collidepoint(event.pos):
                    self.layer = layer_num
                    return None

            if self.create_button_rect.collidepoint(event.pos):
                if self.connection and self.layer:
                    self.active = False
                    return {
                        "action": "create_map",
                        "direction": self.connection,
                        "layer": self.layer,
                        "source_map": self.current_map_name,
                        "source_connections": self.current_connections,
                        "source_pos_id": self.current_pos_id,
                        "source_layer": self.current_layer
                    }
            elif self.cancel_button_rect.collidepoint(event.pos):
                self.active = False
                return {"action": "cancel"}
        return None

    def draw(self, surface):
        if not self.active: return
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill((50, 50, 50, 230))
        surface.blit(s, self.rect.topleft)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2)

        title_surf = self.font.render("Create New Map", True, (255, 255, 255))
        surface.blit(title_surf, (self.rect.x + 20, self.rect.y + 20))

        help_surf = self.font.render(f"Source: {self.current_map_name}", True, (200, 200, 200))
        surface.blit(help_surf, (self.rect.x + 20, self.rect.y + 45))

        conn_title = self.font.render("Select connection:", True, (255, 255, 255))
        surface.blit(conn_title, (self.rect.x + 20, self.conn_title_y))
        
        for direction, rect in self.conn_buttons.items():
            color = (80, 80, 80)
            text_color = (100, 100, 100)
            if self.current_connections[direction] == 0:
                text_color = (255, 255, 255)
                if self.connection == direction: color = (0, 150, 0)
                else: color = (50, 50, 50)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (255, 255, 255), rect, 1)
            text_surf = self.font.render(direction, True, text_color)
            surface.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))

        layer_title = self.font.render("Select Layer:", True, (255, 255, 255))
        surface.blit(layer_title, (self.rect.x + 20, self.layer_title_y))
        
        for layer_num, rect in self.layer_buttons.items():
            color = (50, 50, 50)
            text_color = (255, 255, 255)
            if self.layer == layer_num: color = (0, 150, 0)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (255, 255, 255), rect, 1)
            text_surf = self.font.render(f"[{layer_num}]", True, text_color)
            surface.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))

        pygame.draw.rect(surface, (0, 200, 0), self.create_button_rect)
        create_text = self.font.render("Create", True, (255, 255, 255))
        surface.blit(create_text, (self.create_button_rect.centerx - create_text.get_width() // 2, self.create_button_rect.centery - create_text.get_height() // 2))

        pygame.draw.rect(surface, (200, 0, 0), self.cancel_button_rect)
        cancel_text = self.font.render("Cancel", True, (255, 255, 255))
        surface.blit(cancel_text, (self.cancel_button_rect.centerx - cancel_text.get_width() // 2, self.cancel_button_rect.centery - cancel_text.get_height() // 2))
        
class Toolbar:
    def __init__(self, x, y, width, height, font):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font = font
        self.buttons = []

        # FIX: Only one path assignment, and it must be simply SPRITE_ROOT + 'editor'
        icon_path = os.path.join(SPRITE_ROOT, 'editor')
        self.icons = load_editor_icons(icon_path)

        # Create a default placeholder icon for missing files
        self.default_icon = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
        self.default_icon.fill((100, 100, 100))
        pygame.draw.rect(self.default_icon, (200, 200, 200), self.default_icon.get_rect(), 2)

        button_definitions = [
            {"label": "NEW BUILDING", "icon": "building", "action": "NEW BUILDING"},
            {"label": "SAVE", "icon": "save", "action": "SAVE MAP"},
            {"label": "EXPORT", "icon": "export", "action": "EXPORT PNG"},
            {"label": "DELETE", "icon": "delete", "action": "DELETE MAP"},
            {"label": "ERASER", "icon": "eraser", "action": "ERASER"},
            {"label": "SELECT", "icon": "selection", "action": "SELECTION"},
            {"label": "FILL", "icon": "fill", "action": "FILL"},
            {"label": "UNDO", "icon": "undo", "action": "UNDO"},
            {"label": "COPY", "icon": "copy", "action": "COPY"},
            {"label": "PASTE", "icon": "paste", "action": "PASTE"},
            {"label": "CLEAR", "icon": "clear", "action": "CLEAR"},
        ]
        
        button_width = ICON_SIZE + 10
        button_height = ICON_SIZE + 10
        padding = 5

        current_x = x + padding

        for btn_def in button_definitions:
            rect = pygame.Rect(current_x, y + (height - button_height) // 2, button_width, button_height)
            self.buttons.append({
                "rect": rect,
                "label": btn_def["label"],
                "icon": self.icons.get(btn_def["icon"], self.default_icon),
                "action": btn_def["action"]
            })
            current_x += button_width + padding

    def resize(self, width):
        self.width = width

    def draw(self, surface):
        pygame.draw.rect(surface, (80, 80, 80), (self.x, self.y, self.width, self.height))

        mouse_pos = pygame.mouse.get_pos()
        hovered_button = None

        for button in self.buttons:
            pygame.draw.rect(surface, (120, 120, 120), button["rect"])
            surface.blit(button["icon"], (button["rect"].x + 5, button["rect"].y + 5))

            if button["rect"].collidepoint(mouse_pos):
                hovered_button = button

        if hovered_button:
            pygame.draw.rect(surface, (150, 150, 150), hovered_button["rect"], 2)
            text_surf = self.font.render(hovered_button["label"], True, (255, 255, 255))
            tooltip_rect = text_surf.get_rect(center=(mouse_pos[0], mouse_pos[1] + 20))
            pygame.draw.rect(surface, (0, 0, 0), tooltip_rect.inflate(10, 5))
            surface.blit(text_surf, tooltip_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button["rect"].collidepoint(event.pos):
                    return button["action"]
        return None

class Sidebar:
    def __init__(self, x, y, tiles, items, font):
        self.x = x
        self.y = y
        self.font = font
        self.height = SCREEN_HEIGHT - y 

        self.all_tiles = tiles.copy()
        self.filtered_tiles = tiles.copy()
        self.selected_tile = None

        self.all_items = items.copy()
        self.filtered_items = items.copy()
        self.selected_item = None

        self.tabs = ["Tiles", "Items"]
        self.active_tab = "Tiles"
        self.tab_height = 30
        
        tab_w = SIDEBAR_WIDTH // 2
        self.tab_rects = {
            "Tiles": pygame.Rect(x, y, tab_w, self.tab_height),
            "Items": pygame.Rect(x + tab_w, y, tab_w, self.tab_height)
        }

        self.search_rect = pygame.Rect(self.x + 10, self.y + self.tab_height + 10, SIDEBAR_WIDTH - 20, 30)
        self.search_text = ""
        self.search_active = False

        self.content_area_y = self.y + self.tab_height + self.search_rect.height + 20 
        self.scroll_offset = 0
        self.max_scroll = 0
        self.scroll_speed = 30
        
        self.dragging_scroll = False
        self.scrollbar_track_rect = None
        self.scrollbar_thumb_rect = None
        self.scroll_start_mouse_y = 0
        self.scroll_start_offset = 0

        self.building_previews = {} 
        self.building_dimensions = {} 
        self.selected_building = None

    def refresh_buildings(self, building_dir, tile_map): pass

    def resize(self, x, y, total_screen_height):
        self.x = x
        self.y = y
        self.height = total_screen_height - y

        tab_w = SIDEBAR_WIDTH // 2
        self.tab_rects = {
            "Tiles": pygame.Rect(x, y, tab_w, self.tab_height),
            "Items": pygame.Rect(x + tab_w, y, tab_w, self.tab_height)
        }
        self.search_rect = pygame.Rect(self.x + 10, self.y + self.tab_height + 10, SIDEBAR_WIDTH - 20, 30)
        self.content_area_y = self.y + self.tab_height + self.search_rect.height + 20

    def _filter_content(self):
        if not self.search_text:
            self.filtered_tiles = self.all_tiles.copy()
            self.filtered_items = self.all_items.copy()
        else:
            text = self.search_text.lower()
            self.filtered_tiles = {k: v for k, v in self.all_tiles.items() if text in k.lower()}
            self.filtered_items = {k: v for k, v in self.all_items.items() if text in k.lower()}
        self.scroll_offset = 0

    def draw(self, surface):
        pygame.draw.rect(surface, (50, 50, 50), (self.x, self.y, SIDEBAR_WIDTH, self.height))

        for tab in self.tabs:
            rect = self.tab_rects[tab]
            is_active = (self.active_tab == tab)
            color = (80, 80, 80) if is_active else (40, 40, 40)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (0, 0, 0), rect, 1)

            text_color = (255, 255, 255) if is_active else (150, 150, 150)
            text = self.font.render(tab, True, text_color)
            surface.blit(text, (rect.centerx - text.get_width()//2, rect.centery - text.get_height()//2))

        border_color = (255, 255, 0) if self.search_active else (0, 0, 0)
        pygame.draw.rect(surface, (255, 255, 255), self.search_rect)
        pygame.draw.rect(surface, border_color, self.search_rect, 2)
        
        if self.search_text: search_surf = self.font.render(self.search_text, True, (0, 0, 0))
        else: search_surf = self.font.render("Search...", True, (150, 150, 150))
        
        text_rect = search_surf.get_rect(centery=self.search_rect.centery)
        text_rect.x = self.search_rect.x + 5
        surface.set_clip(self.search_rect.inflate(-10, -10))
        surface.blit(search_surf, text_rect)
        surface.set_clip(None)
        
        view_height = self.y + self.height - self.content_area_y
        view_rect = pygame.Rect(self.x, self.content_area_y, SIDEBAR_WIDTH, view_height)
        surface.set_clip(view_rect)

        content_height = 0
        items_to_draw = {}
        selected_name = None
        
        if self.active_tab == "Tiles":
            items_to_draw = self.filtered_tiles
            selected_name = self.selected_tile
        elif self.active_tab == "Items":
            items_to_draw = self.filtered_items
            selected_name = self.selected_item

        row, col = 0, 0
        for name, image in sorted(items_to_draw.items()):
            tile_x = self.x + col * (TILE_SIZE + 10) + 10
            tile_y = self.content_area_y + row * (TILE_SIZE + 10) - self.scroll_offset

            if tile_y + TILE_SIZE > self.content_area_y and tile_y < self.y + self.height:
                surface.blit(image, (tile_x, tile_y))

                if selected_name == name:
                    pygame.draw.rect(surface, (255, 255, 0), (tile_x, tile_y, TILE_SIZE, TILE_SIZE), 3)

            col += 1
            if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH:
                col = 0
                row += 1
                
        content_height = (row + 1) * (TILE_SIZE + 10)
        surface.set_clip(None)

        self.max_scroll = max(0, content_height - view_rect.height)

        self.scrollbar_track_rect = pygame.Rect(self.x + SIDEBAR_WIDTH - 10, self.content_area_y, 10, view_rect.height)
        
        if self.max_scroll > 0:
            pygame.draw.rect(surface, (40, 40, 40), self.scrollbar_track_rect)
            thumb_h = max(20, (view_rect.height / (content_height + view_rect.height)) * view_rect.height)
            ratio = self.scroll_offset / self.max_scroll if self.max_scroll > 0 else 0
            thumb_y = self.content_area_y + ratio * (view_rect.height - thumb_h)
            self.scrollbar_thumb_rect = pygame.Rect(self.scrollbar_track_rect.x, thumb_y, 10, thumb_h)
            pygame.draw.rect(surface, (100, 100, 100), self.scrollbar_thumb_rect)
        else:
            self.scrollbar_thumb_rect = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP: self.dragging_scroll = False
        if event.type == pygame.MOUSEMOTION:
            if self.dragging_scroll and self.scrollbar_thumb_rect and self.max_scroll > 0:
                dy = event.pos[1] - self.scroll_start_mouse_y
                view_h = self.scrollbar_track_rect.height
                thumb_h = self.scrollbar_thumb_rect.height
                track_space = view_h - thumb_h
                if track_space > 0:
                    scroll_per_pixel = self.max_scroll / track_space
                    self.scroll_offset = self.scroll_start_offset + (dy * scroll_per_pixel)
                    self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
                return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            if self.x <= mx <= self.x + SIDEBAR_WIDTH:
                if self.scrollbar_thumb_rect and self.scrollbar_thumb_rect.collidepoint(mx, my):
                    self.dragging_scroll = True
                    self.scroll_start_mouse_y = my
                    self.scroll_start_offset = self.scroll_offset
                    return True
                elif self.scrollbar_track_rect and self.scrollbar_track_rect.collidepoint(mx, my) and self.max_scroll > 0:
                     view_h = self.scrollbar_track_rect.height
                     thumb_h = self.scrollbar_thumb_rect.height if self.scrollbar_thumb_rect else 20
                     track_space = view_h - thumb_h
                     if track_space > 0:
                        rel_y = my - self.scrollbar_track_rect.y - (thumb_h / 2)
                        ratio = rel_y / track_space
                        self.scroll_offset = ratio * self.max_scroll
                        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
                        self.dragging_scroll = True
                        self.scroll_start_mouse_y = my
                        self.scroll_start_offset = self.scroll_offset
                        return True

                if my < self.y + self.tab_height:
                    for tab_name, rect in self.tab_rects.items():
                        if rect.collidepoint(mx, my):
                            self.active_tab = tab_name
                            self.scroll_offset = 0
                            return True
                    return True
                
                if self.search_rect.collidepoint(mx, my):
                    self.search_active = True
                    return True
                else: self.search_active = False

                if event.button == 4:
                    self.scroll_offset = max(0, self.scroll_offset - self.scroll_speed)
                    return True
                if event.button == 5:
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + self.scroll_speed)
                    return True

                if my > self.content_area_y:
                    items_to_check = {}
                    if self.active_tab == "Tiles": items_to_check = self.filtered_tiles
                    elif self.active_tab == "Items": items_to_check = self.filtered_items
                    
                    row, col = 0, 0
                    for name, image in sorted(items_to_check.items()):
                        tile_x = self.x + col * (TILE_SIZE + 10) + 10
                        tile_y = self.content_area_y + row * (TILE_SIZE + 10) - self.scroll_offset

                        if pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE).collidepoint(mx, my):
                            if self.active_tab == "Tiles":
                                self.selected_tile = name
                                self.selected_item = None
                            elif self.active_tab == "Items":
                                self.selected_item = name
                                self.selected_tile = None
                            self.selected_building = None
                            return True

                        col += 1
                        if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH:
                            col = 0
                            row += 1

                return True
                
        if event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_BACKSPACE: self.search_text = self.search_text[:-1]
            else: self.search_text += event.unicode
            self._filter_content()
            return True

        return False

# --- New UIAttributeList Component ---
# --- New UIAttributeList Component ---
class UIAttributeList:
    def __init__(self, x, y, width, height, font, text=""):
        # height parameter is ignored intentionally as this component is fixed in size (145px)
        self.rect = pygame.Rect(x, y, width, 145)
        self.font = font
        self.attributes = ["strength", "fitness", "melee", "ranged", "maintenance", "lucky", "agility", "intelligence"]
        self.data = {attr: {"enabled": False, "box": UITextBox(0, 0, 45, 26, font, "")} for attr in self.attributes}
        
        self.parse_text(text)
        self._relayout()

    def parse_text(self, text):
        t = text.strip("[] ")
        if not t: return
        parts = [p.strip() for p in t.split(',')]
        for p in parts:
            if ':' in p:
                attr, val = p.split(':', 1)
                attr = attr.strip()
                if attr in self.data:
                    self.data[attr]["enabled"] = True
                    self.data[attr]["box"].text = val.strip()

    @property
    def text(self):
        parts = []
        for attr in self.attributes:
            if self.data[attr]["enabled"]:
                val = self.data[attr]['box'].text.strip()
                if not val: val = "1"
                parts.append(f"{attr}:{val}")
        if not parts: return ""
        return f"[{', '.join(parts)}]"

    def _relayout(self):
        col_w = self.rect.width // 2
        for i, attr in enumerate(self.attributes):
            col = i // 4
            row = i % 4
            bx = self.rect.x + col * col_w
            by = self.rect.y + row * 35
            
            # Checkbox rect
            self.data[attr]["cb_rect"] = pygame.Rect(bx, by + 4, 20, 20)
            
            # Textbox rect (Dynamically anchored to the right side of its assigned column width)
            self.data[attr]["box"].rect.x = bx + col_w - 65
            self.data[attr]["box"].rect.y = by + 2

    def handle_event(self, event):
        consumed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for attr, info in self.data.items():
                if info["cb_rect"].collidepoint(event.pos):
                    info["enabled"] = not info["enabled"]
                    consumed = True
                    
        for info in self.data.values():
            if info["enabled"]:
                if info["box"].handle_event(event):
                    consumed = True
        return consumed

    def draw(self, surface):
        for i, attr in enumerate(self.attributes):
            info = self.data[attr]
            cb = info["cb_rect"]
            
            # Draw Checkbox
            pygame.draw.rect(surface, (60, 60, 70), cb)
            if info["enabled"]:
                pygame.draw.rect(surface, (0, 200, 0), cb.inflate(-4, -4))
            pygame.draw.rect(surface, (150, 150, 150), cb, 1)
            
            # Draw Label
            lbl = attr.capitalize()
            surface.blit(self.font.render(lbl, True, (200, 200, 200)), (cb.right + 10, cb.y + 2))
            
            # Draw Textbox
            if info["enabled"]:
                info["box"].draw(surface)