import pygame
import re
import os
import csv
from datetime import datetime
from editor.config import GAME_ROOT, SPRITE_ROOT, TILE_SIZE, SIDEBAR_WIDTH, SCREEN_HEIGHT, FILE_TREE_WIDTH, SCREEN_WIDTH, ICON_SIZE, BUILDINGS_DIR, BUILDING_PREVIEW_SIZE, TAB_BAR_HEIGHT
from editor.assets import load_editor_icons

# ----------------------------------------------------------------------
# UI THEME & MODULAR UI UTILS
# ----------------------------------------------------------------------
class UITheme:
    BG = (30, 30, 32)
    PANEL_BG = (37, 37, 40)
    BORDER = (60, 60, 65)
    BORDER_ACTIVE = (100, 100, 110)
    TEXT = (220, 220, 220)
    TEXT_DIM = (150, 150, 150)
    
    # Modern Editor Accents
    ACCENT = (14, 99, 156)
    ACCENT_HOVER = (17, 119, 187)
    DANGER = (200, 50, 50)
    DANGER_HOVER = (220, 70, 70)
    SUCCESS = (50, 150, 50)
    SUCCESS_HOVER = (60, 170, 60)
    WARNING = (200, 150, 0)
    WARNING_HOVER = (220, 170, 20)
    
    HOVER_BG = (50, 50, 55)
    LIST_HOVER = (9, 71, 113)
    RADIUS = 6

_active_tooltip = None

def register_tooltip(pos, text):
    global _active_tooltip
    _active_tooltip = (pos, text)

def draw_styled_button(surface, rect, text, font, mouse_pos, base_color=UITheme.ACCENT, hover_color=UITheme.ACCENT_HOVER, tooltip=None, text_color=UITheme.TEXT, radius=UITheme.RADIUS):
    hovered = rect.collidepoint(mouse_pos)
    color = hover_color if hovered else base_color
    
    # Drop Shadow
    shadow_rect = rect.copy()
    shadow_rect.y += 2
    pygame.draw.rect(surface, (15, 15, 15), shadow_rect, border_radius=radius)
    
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, UITheme.BORDER, rect, 1, border_radius=radius)
    
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)
    
    if hovered and tooltip:
        register_tooltip(mouse_pos, tooltip)

def draw_tooltips(surface, font):
    global _active_tooltip
    if _active_tooltip:
        pos, text = _active_tooltip
        text_surf = font.render(text, True, UITheme.TEXT)
        pad_x, pad_y = 8, 6
        tt_rect = pygame.Rect(pos[0] + 15, pos[1] + 15, text_surf.get_width() + pad_x*2, text_surf.get_height() + pad_y*2)
        
        # Screen bounds constraint
        if tt_rect.right > surface.get_width(): tt_rect.right = surface.get_width() - 5
        if tt_rect.bottom > surface.get_height(): tt_rect.bottom = surface.get_height() - 5
        
        # Shadow & Box
        shadow = tt_rect.copy()
        shadow.y += 3
        pygame.draw.rect(surface, (10, 10, 10, 128), shadow, border_radius=4)
        pygame.draw.rect(surface, UITheme.PANEL_BG, tt_rect, border_radius=4)
        pygame.draw.rect(surface, UITheme.BORDER, tt_rect, 1, border_radius=4)
        surface.blit(text_surf, (tt_rect.x + pad_x, tt_rect.y + pad_y))
        _active_tooltip = None

# ----------------------------------------------------------------------
# GLOBAL FOCUS MANAGER
# ----------------------------------------------------------------------
class FocusManager:
    focused_widget = None

    @classmethod
    def set_focus(cls, widget):
        if cls.focused_widget is not None and cls.focused_widget is not widget:
            cls.focused_widget.active = False
            if hasattr(cls.focused_widget, 'sel_start'):
                cls.focused_widget.sel_start = None
        cls.focused_widget = widget

    @classmethod
    def clear_focus(cls):
        if cls.focused_widget is not None:
            cls.focused_widget.active = False
            if hasattr(cls.focused_widget, 'sel_start'):
                cls.focused_widget.sel_start = None
        cls.focused_widget = None

    @classmethod
    def is_focused(cls, widget):
        return cls.focused_widget is widget

# ----------------------------------------------------------------------
# COMPONENTS
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# COMPONENTS
# ----------------------------------------------------------------------
class UITextBox:
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
        self.history = [text]
        self.history_index = 0
        self.undo_redo_suspended = False

    def _push_history(self):
        if self.undo_redo_suspended: return
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        if self.history and self.history[-1] == self.text: return
        self.history.append(self.text)
        self.history_index = len(self.history) - 1
        if len(self.history) > 100:
            self.history = self.history[-100:]
            self.history_index = len(self.history) - 1

    def delete_selection(self):
        if self.sel_start is not None and self.sel_start != self.cursor_pos:
            s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
            self.text = self.text[:s] + self.text[e:]
            self.cursor_pos = s
            self.sel_start = None
            return True
        return False

    def _get_idx_from_x(self, x):
        rel_x = x - (self.rect.x + 8) + self.scroll_x
        if rel_x <= 0:
            return 0
        for i in range(len(self.text)):
            w = self.font.size(self.text[:i])[0]
            cw = self.font.size(self.text[i])[0]
            if rel_x < w + cw / 2:
                return i
        return len(self.text)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                FocusManager.set_focus(self)
                self.active = True
                self.cursor_pos = self._get_idx_from_x(event.pos[0])
                self.sel_start = self.cursor_pos
                self.dragging = True
                return True
            else:
                if self.active:
                    self.active = False
                    if FocusManager.focused_widget is self:
                        FocusManager.clear_focus()
                return False
                
        if not self.active or FocusManager.focused_widget is not self:
            self.active = False
            return False

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
            
            # COPY
            if ctrl and event.key == pygame.K_c:
                if self.sel_start is not None and self.sel_start != self.cursor_pos:
                    s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
                    try: pygame.scrap.put(pygame.SCRAP_TEXT, self.text[s:e].encode('utf-8'))
                    except: pass
                return True
            # PASTE
            elif ctrl and event.key == pygame.K_v:
                try:
                    t = pygame.scrap.get(pygame.SCRAP_TEXT).decode('utf-8').strip('\x00')
                    self.delete_selection()
                    self.text = self.text[:self.cursor_pos] + t + self.text[self.cursor_pos:]
                    self.cursor_pos += len(t)
                    self.sel_start = None
                    self._push_history()
                except: pass
                return True
            # CUT
            elif ctrl and event.key == pygame.K_x:
                if self.sel_start is not None and self.sel_start != self.cursor_pos:
                    s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
                    try: pygame.scrap.put(pygame.SCRAP_TEXT, self.text[s:e].encode('utf-8'))
                    except: pass
                    self.delete_selection()
                    self._push_history()
                return True
            # UNDO (CTRL+Z)
            elif ctrl and not shift and event.key == pygame.K_z:
                if self.history_index > 0:
                    self.undo_redo_suspended = True
                    self.history_index -= 1
                    self.text = self.history[self.history_index]
                    self.cursor_pos = min(self.cursor_pos, len(self.text))
                    self.sel_start = None
                    self.undo_redo_suspended = False
                return True
            # REDO (CTRL+Y or CTRL+SHIFT+Z)
            elif ctrl and (event.key == pygame.K_y or (shift and event.key == pygame.K_z)):
                if self.history_index < len(self.history) - 1:
                    self.undo_redo_suspended = True
                    self.history_index += 1
                    self.text = self.history[self.history_index]
                    self.cursor_pos = min(self.cursor_pos, len(self.text))
                    self.sel_start = None
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
            elif event.key == pygame.K_BACKSPACE:
                if not self.delete_selection():
                    if self.cursor_pos > 0:
                        self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                        self.cursor_pos -= 1
                self._push_history()
            elif event.key == pygame.K_DELETE:
                if not self.delete_selection():
                    if self.cursor_pos < len(self.text):
                        self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
                self._push_history()
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
                    self._push_history()
            return True
        return False

    def draw(self, surface):
        cursor_x = self.font.size(self.text[:self.cursor_pos])[0]
        if cursor_x - self.scroll_x < 0: self.scroll_x = cursor_x
        elif cursor_x - self.scroll_x > self.rect.width - 15: self.scroll_x = cursor_x - self.rect.width + 15

        # Background and Border
        pygame.draw.rect(surface, UITheme.BG, self.rect, border_radius=4)
        border_color = UITheme.ACCENT if self.active else UITheme.BORDER
        pygame.draw.rect(surface, border_color, self.rect, max(1, 2 if self.active else 1), border_radius=4)
        
        # Save previous clip rect and restore it so it does not reset panel clipping
        prev_clip = surface.get_clip()
        box_clip = self.rect.inflate(-8, -4)
        if prev_clip:
            box_clip = box_clip.clip(prev_clip)
        surface.set_clip(box_clip)
        
        if self.sel_start is not None and self.sel_start != self.cursor_pos:
            s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
            sx = self.font.size(self.text[:s])[0] - self.scroll_x + self.rect.x + 8
            sw = self.font.size(self.text[s:e])[0]
            pygame.draw.rect(surface, UITheme.LIST_HOVER, (sx, self.rect.y + 2, sw, self.rect.height - 4))
        
        ts = self.font.render(self.text, True, UITheme.TEXT)
        surface.blit(ts, (self.rect.x + 8 - self.scroll_x, self.rect.y + (self.rect.height - ts.get_height())//2))
        
        if self.active:
            self.blink_timer += 1
            if (self.blink_timer // 30) % 2 == 0:
                cx = self.rect.x + 8 + cursor_x - self.scroll_x
                pygame.draw.line(surface, UITheme.TEXT, (cx, self.rect.y + 6), (cx, self.rect.bottom - 6), 2)
                
        surface.set_clip(prev_clip)

class UIDropdown:
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
        self.max_visible_items = 5
        
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
            
        cur_surf = pygame.display.get_surface()
        screen_h = cur_surf.get_height() if cur_surf else 720
        self.list_rect.height = base_h
        if self.rect.bottom + base_h > screen_h - 10:
            self.list_rect.bottom = self.rect.top
        else:
            self.list_rect.top = self.rect.bottom

    def handle_event(self, event):
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
                
                if max_scroll > 0:
                    sb_rect = pygame.Rect(self.list_rect.right - 8, self.list_rect.y + (self.item_height if self.searchable else 0), 8, list_view_h)
                    if sb_rect.collidepoint(event.pos):
                        self.dragging_scroll = True
                        self.scroll_start_y = event.pos[1]
                        self.scroll_start_offset = self.scroll_offset
                        return True

                if self.list_rect.collidepoint(event.pos):
                    if self.searchable and event.pos[1] < self.list_rect.y + self.item_height:
                        return True 

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
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        bg_color = UITheme.HOVER_BG if hover else UITheme.BG
        
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=4)
        border_color = UITheme.ACCENT if self.expanded else UITheme.BORDER
        pygame.draw.rect(surface, border_color, self.rect, 1 if not self.expanded else 2, border_radius=4)
        
        lbl_surf = self.font.render(self.selected_label or "None", True, UITheme.TEXT)
        selected_icon = next((opt.get('icon') for opt in self.options if opt['value'] == self.selected_value), None)
        
        draw_x = self.rect.x + 8
        if selected_icon:
            ic_size = self.rect.height - 8
            scaled_ic = pygame.transform.scale(selected_icon, (ic_size, ic_size))
            surface.blit(scaled_ic, (draw_x, self.rect.y + 4))
            draw_x += ic_size + 8
            
        surface.set_clip(self.rect.inflate(-8, -4))
        surface.blit(lbl_surf, (draw_x, self.rect.y + (self.rect.height - lbl_surf.get_height())//2))
        surface.set_clip(None)
        
        # Draw Arrow
        arrow_x = self.rect.right - 14
        arrow_y = self.rect.centery
        if self.expanded:
            pygame.draw.polygon(surface, UITheme.TEXT_DIM, [(arrow_x-5, arrow_y+2), (arrow_x+5, arrow_y+2), (arrow_x, arrow_y-3)])
        else:
            pygame.draw.polygon(surface, UITheme.TEXT_DIM, [(arrow_x-5, arrow_y-2), (arrow_x+5, arrow_y-2), (arrow_x, arrow_y+3)])

    def draw_list(self, surface):
        if not self.expanded: return
        
        pygame.draw.rect(surface, UITheme.PANEL_BG, self.list_rect, border_radius=4)
        pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.list_rect, 1, border_radius=4)
        
        start_y = self.list_rect.y
        if self.searchable:
            search_rect = pygame.Rect(self.list_rect.x, self.list_rect.y, self.list_rect.width, self.item_height)
            pygame.draw.rect(surface, UITheme.BG, search_rect, border_top_left_radius=4, border_top_right_radius=4)
            pygame.draw.rect(surface, UITheme.BORDER, search_rect, 1)
            
            self.blink_timer += 1
            cursor = "|" if (self.blink_timer // 30) % 2 == 0 else ""
            s_txt = self.font.render("Search: " + self.search_text + cursor, True, UITheme.WARNING)
            surface.set_clip(search_rect.inflate(-8, -4))
            surface.blit(s_txt, (search_rect.x + 8, search_rect.y + (self.item_height - s_txt.get_height())//2))
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
                pygame.draw.rect(surface, UITheme.LIST_HOVER, opt_rect)
            elif opt['value'] == self.selected_value:
                pygame.draw.rect(surface, UITheme.HOVER_BG, opt_rect)
            
            draw_x = opt_rect.x + 8
            if opt.get('icon'):
                ic_size = self.item_height - 8
                scaled_ic = pygame.transform.scale(opt.get('icon'), (ic_size, ic_size))
                surface.blit(scaled_ic, (draw_x, opt_rect.y + 4))
                draw_x += ic_size + 8
                
            opt_lbl = self.font.render(opt['label'], True, UITheme.TEXT)
            surface.blit(opt_lbl, (draw_x, opt_rect.y + (self.item_height - opt_lbl.get_height())//2))

        surface.set_clip(None)
        
        content_h = len(filtered) * self.item_height
        list_view_h = view_rect.height
        max_scroll = max(0, content_h - list_view_h)
        
        if max_scroll > 0:
            sb_rect = pygame.Rect(self.list_rect.right - 6, start_y, 6, list_view_h)
            pygame.draw.rect(surface, UITheme.BG, sb_rect)
            thumb_h = max(10, list_view_h * (list_view_h / content_h))
            thumb_y = start_y + (self.scroll_offset / max_scroll) * (list_view_h - thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, pygame.Rect(sb_rect.x, thumb_y, 6, thumb_h), border_radius=3)

class UITextArea:
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
        self.line_height = self.font.get_linesize() + 4
        self.lines = []
        self.thumb_rect = None
        self._update_lines()
        self.history = [text]          
        self.history_index = 0         
        self.undo_redo_suspended = False  

    def _push_history(self):
        if self.undo_redo_suspended: return
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        if self.history and self.history[-1] == self.text: return
        self.history.append(self.text)
        self.history_index = len(self.history) - 1
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
        rel_y = y - self.rect.y + self.scroll_y - 8
        line_idx = int(rel_y // self.line_height)
        line_idx = max(0, min(len(self.lines) - 1, line_idx))
        
        line_text, start_idx, end_idx = self.lines[line_idx]
        rel_x = x - self.rect.x - 8
        
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
                    
                sb_track = pygame.Rect(self.rect.right - 10, self.rect.y, 10, self.rect.height)
                if sb_track.collidepoint(event.pos) and self._max_scroll > 0:
                    return True

                if self.rect.collidepoint(event.pos):
                    FocusManager.set_focus(self)
                    self.active = True
                    self.cursor_pos = self._get_idx_from_pos(*event.pos)
                    self.sel_start = self.cursor_pos
                    self.dragging = True
                    return True
                else:
                    if self.active:
                        self.active = False
                        if FocusManager.focused_widget is self:
                            FocusManager.clear_focus()
                    return False
                    
            elif event.button in (4, 5) and self.rect.collidepoint(event.pos):
                if event.button == 4: self.scroll_y = max(0, self.scroll_y - 20)
                else: self.scroll_y = min(self._max_scroll, self.scroll_y + 20)
                return True

        if not self.active or FocusManager.focused_widget is not self:
            self.active = False
            if not self.dragging_scroll: return False

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
            
            # COPY
            if ctrl and event.key == pygame.K_c:
                if self.sel_start is not None and self.sel_start != self.cursor_pos:
                    s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
                    try: pygame.scrap.put(pygame.SCRAP_TEXT, self.text[s:e].encode('utf-8'))
                    except: pass
                return True
            # PASTE
            elif ctrl and event.key == pygame.K_v:
                try:
                    t = pygame.scrap.get(pygame.SCRAP_TEXT).decode('utf-8').strip('\x00')
                    self.delete_selection()
                    self.text = self.text[:self.cursor_pos] + t + self.text[self.cursor_pos:]
                    self.cursor_pos += len(t)
                    self.sel_start = None
                    self._update_lines()
                    self._push_history()
                except: pass
                return True
            # CUT
            elif ctrl and event.key == pygame.K_x:
                if self.sel_start is not None and self.sel_start != self.cursor_pos:
                    s, e = min(self.sel_start, self.cursor_pos), max(self.sel_start, self.cursor_pos)
                    try: pygame.scrap.put(pygame.SCRAP_TEXT, self.text[s:e].encode('utf-8'))
                    except: pass
                    self.delete_selection()
                    self._push_history()
                return True
            # UNDO (CTRL+Z)
            elif ctrl and not shift and event.key == pygame.K_z:
                if self.history_index > 0:
                    self.undo_redo_suspended = True
                    self.history_index -= 1
                    self.text = self.history[self.history_index]
                    self.cursor_pos = min(self.cursor_pos, len(self.text))
                    self.sel_start = None
                    self._update_lines()
                    self.undo_redo_suspended = False
                return True
            # REDO (CTRL+Y or CTRL+SHIFT+Z)
            elif ctrl and (event.key == pygame.K_y or (shift and event.key == pygame.K_z)):
                if self.history_index < len(self.history) - 1:
                    self.undo_redo_suspended = True
                    self.history_index += 1
                    self.text = self.history[self.history_index]
                    self.cursor_pos = min(self.cursor_pos, len(self.text))
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
                self._push_history()
            elif event.key == pygame.K_DELETE:
                if not self.delete_selection() and self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
                    self._update_lines()
                self._push_history()
            elif event.key == pygame.K_RETURN:
                self.delete_selection()
                self.text = self.text[:self.cursor_pos] + "\n" + self.text[self.cursor_pos:]
                self.cursor_pos += 1
                self._update_lines()
                self._push_history()
            else:
                if event.unicode and event.unicode.isprintable():
                    self.delete_selection()
                    self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                    self.cursor_pos += len(event.unicode)
                    self._update_lines()
                    self._push_history()
            return True
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, UITheme.BG, self.rect, border_radius=4)
        border_color = UITheme.ACCENT if self.active else UITheme.BORDER
        pygame.draw.rect(surface, border_color, self.rect, max(1, 2 if self.active else 1), border_radius=4)
        
        prev_clip = surface.get_clip()
        area_clip = self.rect.inflate(-8, -4)
        if prev_clip:
            area_clip = area_clip.clip(prev_clip)
        surface.set_clip(area_clip)
        
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
            y_pos = self.rect.y + 8 + i * self.line_height - self.scroll_y
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
                    pygame.draw.rect(surface, UITheme.LIST_HOVER, (self.rect.x + 8 + h_x, y_pos, h_w, self.line_height))
                    
            ts = self.font.render(l_text, True, UITheme.TEXT)
            surface.blit(ts, (self.rect.x + 8, y_pos))
            
        if self.active:
            self.blink_timer += 1
            if (self.blink_timer // 30) % 2 == 0:
                cx = self.rect.x + 8 + cursor_x
                cy = self.rect.y + 8 + cursor_y - self.scroll_y
                pygame.draw.line(surface, UITheme.TEXT, (cx, cy), (cx, cy + self.line_height - 2), 2)
                
        surface.set_clip(prev_clip)
        
        if self._max_scroll > 0:
            sb_rect = pygame.Rect(self.rect.right - 8, self.rect.y + 2, 6, self.rect.height - 4)
            pygame.draw.rect(surface, UITheme.BG, sb_rect, border_radius=3)
            content_h = len(self.lines) * self.line_height + 10
            thumb_h = max(15, self.rect.height * (self.rect.height / content_h))
            thumb_y = self.rect.y + 2 + (self.scroll_y / self._max_scroll) * (self.rect.height - 4 - thumb_h)
            self.thumb_rect = pygame.Rect(sb_rect.x, thumb_y, 6, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.thumb_rect, border_radius=3)
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
        tab_w = 160
        for i, mode in enumerate(self.modes):
            self.tabs.append({
                "mode": mode,
                "rect": pygame.Rect(i*tab_w, self.rect.y, tab_w, self.rect.height),
                "label": mode
            })

    def draw(self, surface):
        pygame.draw.rect(surface, UITheme.PANEL_BG, self.rect)
        pygame.draw.line(surface, UITheme.BORDER, self.rect.bottomleft, self.rect.bottomright, 2)
        
        mouse_pos = pygame.mouse.get_pos()
        for tab in self.tabs:
            is_active = (tab["mode"] == self.active_mode)
            hovered = tab["rect"].collidepoint(mouse_pos)
            
            bg_color = UITheme.BG if is_active else (UITheme.HOVER_BG if hovered else UITheme.PANEL_BG)
            pygame.draw.rect(surface, bg_color, tab["rect"])
            
            if is_active:
                pygame.draw.rect(surface, UITheme.ACCENT, (tab["rect"].x, tab["rect"].bottom - 2, tab["rect"].width, 2))
            
            text_color = UITheme.TEXT if is_active or hovered else UITheme.TEXT_DIM
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
        full_msg = f"[{timestamp}] {text}"
        self.messages.append(full_msg)
        total_h = len(self.messages) * self.line_height
        if total_h > self.rect.height:
            self.scroll_offset = total_h - self.rect.height

    def draw(self, surface):
        pygame.draw.rect(surface, (20, 20, 22), self.rect)
        pygame.draw.line(surface, UITheme.BORDER, self.rect.topleft, self.rect.topright)
        
        surface.set_clip(self.rect)
        start_y = self.rect.y + 5 - self.scroll_offset
        for i, msg in enumerate(self.messages):
            y = start_y + i * self.line_height
            if y + self.line_height > self.rect.y and y < self.rect.bottom:
                text_surf = self.font.render(msg, True, UITheme.TEXT_DIM)
                surface.blit(text_surf, (self.rect.x + 10, y))
        surface.set_clip(None)
        
        content_height = len(self.messages) * self.line_height + 10
        self.max_scroll = max(0, content_height - self.rect.height)
        
        if self.max_scroll > 0:
            track_x = self.rect.right - 8
            self.scrollbar_track_rect = pygame.Rect(track_x, self.rect.y, 8, self.rect.height)
            view_h = self.rect.height
            thumb_h = max(20, (view_h / content_height) * view_h)
            ratio = self.scroll_offset / self.max_scroll
            thumb_y = self.rect.y + ratio * (view_h - thumb_h)
            self.scrollbar_thumb_rect = pygame.Rect(track_x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER, self.scrollbar_thumb_rect, border_radius=4)
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

class NewBuildingModal:
    """Modal to create a new building with Category, Layer, and Size."""
    def __init__(self, x, y, width, height, font):
        self.font = font
        self.active = False
        self.rect = pygame.Rect(x, y, 520, 290)
        self.buildings_dir = ""

        # Category / Type Dropdown
        self.categories = [
            "Building",
            "Bunker",
            "Cave",
            "Dungeon",
            "Forest",
            "Military_base"
        ]
        cat_opts = [{"label": c, "value": c} for c in self.categories]
        self.category_dropdown = UIDropdown(0, 0, 160, 30, self.font, cat_opts, "Building")

        # Layer Dropdown
        layer_opts = [
            {"label": "L1", "value": "L1"},
            {"label": "L2", "value": "L2"},
            {"label": "L3", "value": "L3"}
        ]
        self.layer_dropdown = UIDropdown(0, 0, 100, 30, self.font, layer_opts, "L1")
        
        self.next_number_str = "01"
        self.width_input = UITextBox(0, 0, 100, 30, font, "10")
        self.height_input = UITextBox(0, 0, 100, 30, font, "10")
        
        self.create_btn = pygame.Rect(0, 0, 130, 34)
        self.cancel_btn = pygame.Rect(0, 0, 110, 34)

    def _calc_next_number(self):
        category = self.category_dropdown.text or "Building"
        max_num = 0
        if self.buildings_dir and os.path.exists(self.buildings_dir):
            pattern = re.compile(rf"^{re.escape(category)}_L\d+_(\d+)", re.IGNORECASE)
            for root, dirs, files in os.walk(self.buildings_dir):
                for f in files:
                    m = pattern.search(f)
                    if m:
                        try:
                            n = int(m.group(1))
                            if n > max_num: max_num = n
                        except ValueError: pass
        self.next_number_str = f"{max_num + 1:02d}"

    def open(self, buildings_dir, center_x, center_y):
        self.buildings_dir = buildings_dir
        self.rect.center = (center_x, center_y)
        
        self.category_dropdown.selected_value = "Building"
        self.category_dropdown._update_label()
        self.layer_dropdown.selected_value = "L1"
        self.layer_dropdown._update_label()
        
        self._calc_next_number()

        # Layout positions
        self.category_dropdown.rect.topleft = (self.rect.x + 85, self.rect.y + 60)
        self.category_dropdown.list_rect.topleft = (self.rect.x + 85, self.rect.y + 90)

        self.layer_dropdown.rect.topleft = (self.rect.x + 360, self.rect.y + 60)
        self.layer_dropdown.list_rect.topleft = (self.rect.x + 360, self.rect.y + 90)
        
        self.width_input.rect.topleft = (self.rect.x + 85, self.rect.y + 115)
        self.height_input.rect.topleft = (self.rect.x + 360, self.rect.y + 115)
        
        btn_y = self.rect.bottom - 48
        self.create_btn.topleft = (self.rect.x + 130, btn_y)
        self.cancel_btn.topleft = (self.rect.x + 280, btn_y)
        self.active = True

    def get_generated_name(self):
        category = self.category_dropdown.text or "Building"
        layer = self.layer_dropdown.text or "L1"
        return f"{category}_{layer}_{self.next_number_str}"

    def handle_event(self, event):
        if not self.active: return None
        
        # Dropdown priority
        if self.category_dropdown.expanded:
            if self.category_dropdown.handle_event(event):
                self._calc_next_number()
                return True
        if self.layer_dropdown.expanded:
            if self.layer_dropdown.handle_event(event):
                return True
            
        old_cat = self.category_dropdown.text
        if self.category_dropdown.handle_event(event):
            if self.category_dropdown.text != old_cat:
                self._calc_next_number()
            return True

        if self.layer_dropdown.handle_event(event): return True
        if self.width_input.handle_event(event): return True
        if self.height_input.handle_event(event): return True
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.create_btn.collidepoint(event.pos):
                try:
                    w = int(self.width_input.text)
                    h = int(self.height_input.text)
                    self.active = False
                    return {
                        "action": "create_building", 
                        "name": self.get_generated_name(), 
                        "width": w, 
                        "height": h
                    }
                except ValueError:
                    print("Invalid dimensions")
            elif self.cancel_btn.collidepoint(event.pos):
                self.active = False
                return True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.active = False
            return True
        return True

    def draw(self, surface):
        if not self.active: return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        pygame.draw.rect(surface, UITheme.PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.rect, 2, border_radius=8)
        surface.blit(self.font.render("New Building", True, UITheme.WARNING), (self.rect.x + 20, self.rect.y + 15))
        pygame.draw.line(surface, UITheme.BORDER, (self.rect.x, self.rect.y + 40), (self.rect.right, self.rect.y + 40))

        # Row 1: Type (Category) & Layer
        surface.blit(self.font.render("Type:", True, UITheme.TEXT_DIM), (self.rect.x + 20, self.rect.y + 66))
        self.category_dropdown.draw(surface)

        surface.blit(self.font.render("Layer:", True, UITheme.TEXT_DIM), (self.rect.x + 280, self.rect.y + 66))
        self.layer_dropdown.draw(surface)

        # Row 2: Dimensions
        surface.blit(self.font.render("Size W:", True, UITheme.TEXT_DIM), (self.rect.x + 20, self.rect.y + 121))
        self.width_input.draw(surface)
        
        surface.blit(self.font.render("Size H:", True, UITheme.TEXT_DIM), (self.rect.x + 280, self.rect.y + 121))
        self.height_input.draw(surface)

        # Row 3: Live Generated Name Preview
        gen_name = self.get_generated_name()
        surface.blit(self.font.render(f"Generated Name: {gen_name}", True, UITheme.WARNING), (self.rect.x + 20, self.rect.y + 172))

        mouse_pos = pygame.mouse.get_pos()
        draw_styled_button(surface, self.create_btn, "Create", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.cancel_btn, "Cancel", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

        # Draw dropdown popup lists last on top
        if self.category_dropdown.expanded:
            self.category_dropdown.draw_list(surface)
        if self.layer_dropdown.expanded:
            self.layer_dropdown.draw_list(surface)

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
        s.fill((37, 37, 40, 245))
        surface.blit(s, self.rect.topleft)
        pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.rect, 2, border_radius=8)

        surface.blit(self.font.render("Create New Map", True, UITheme.TEXT), (self.rect.x + 20, self.rect.y + 20))
        surface.blit(self.font.render(f"Source: {self.current_map_name}", True, UITheme.TEXT_DIM), (self.rect.x + 20, self.rect.y + 45))
        surface.blit(self.font.render("Select connection:", True, UITheme.TEXT), (self.rect.x + 20, self.conn_title_y))
        
        mouse_pos = pygame.mouse.get_pos()
        for direction, rect in self.conn_buttons.items():
            if self.current_connections[direction] == 0:
                base_color = UITheme.SUCCESS if self.connection == direction else UITheme.BG
                draw_styled_button(surface, rect, direction, self.font, mouse_pos, base_color, UITheme.SUCCESS_HOVER)
            else:
                pygame.draw.rect(surface, UITheme.BORDER, rect, border_radius=UITheme.RADIUS)
                text_surf = self.font.render(direction, True, UITheme.TEXT_DIM)
                surface.blit(text_surf, (rect.centerx - text_surf.get_width() // 2, rect.centery - text_surf.get_height() // 2))

        surface.blit(self.font.render("Select Layer:", True, UITheme.TEXT), (self.rect.x + 20, self.layer_title_y))
        
        for layer_num, rect in self.layer_buttons.items():
            base_color = UITheme.SUCCESS if self.layer == layer_num else UITheme.BG
            draw_styled_button(surface, rect, f"[{layer_num}]", self.font, mouse_pos, base_color, UITheme.SUCCESS_HOVER)

        draw_styled_button(surface, self.create_button_rect, "Create", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.cancel_button_rect, "Cancel", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

class Toolbar:
    def __init__(self, x, y, width, height, font):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font = font
        self.buttons = []
        self._active_tool = None

        self.direct_button_defs = [
            {"label": "+ New Building", "action": "NEW BUILDING", "color": UITheme.SUCCESS},
            {"label": "Rename", "action": "RENAME", "color": UITheme.PANEL_BG},
            {"label": "Save Map", "action": "SAVE MAP", "color": UITheme.ACCENT},
        ]
        
        self.menu_tool_defs = [
            {"label": "Select", "action": "SELECTION"},
            {"label": "Fill", "action": "FILL"},
            {"label": "Eraser", "action": "ERASER"},
            {"label": "Undo", "action": "UNDO"},
            {"label": "Clear", "action": "CLEAR"},
            {"label": "Copy", "action": "COPY"},
            {"label": "Paste", "action": "PASTE"},
        ]
        
        self.tools_expanded = False
        self.tools_btn_rect = pygame.Rect(0, 0, 110, 30)
        self.menu_item_height = 28
        self._rebuild_buttons()

    @property
    def active_tool(self):
        return self._active_tool

    @active_tool.setter
    def active_tool(self, val):
        self._active_tool = val
        self._rebuild_buttons()

    def _rebuild_buttons(self):
        self.buttons = []
        padding = 8
        cur_x = self.x + padding
        for b_def in self.direct_button_defs:
            w = self.font.size(b_def["label"])[0] + 24
            rect = pygame.Rect(cur_x, self.y + 6, w, self.height - 12)
            self.buttons.append({
                "rect": rect,
                "label": b_def["label"],
                "action": b_def["action"],
                "color": b_def["color"]
            })
            cur_x += w + padding

        tool_name = self.active_tool.capitalize() if self.active_tool else "Tools"
        tools_label = f"☰ {tool_name}"
        tools_w = max(120, self.font.size(tools_label)[0] + 24)
        self.tools_btn_rect = pygame.Rect(cur_x, self.y + 6, tools_w, self.height - 12)

    def resize(self, width):
        self.width = width
        self._rebuild_buttons()

    def get_dropdown_rect(self):
        menu_w = max(160, self.tools_btn_rect.width + 20)
        menu_h = len(self.menu_tool_defs) * self.menu_item_height + 8
        return pygame.Rect(self.tools_btn_rect.x, self.tools_btn_rect.bottom + 2, menu_w, menu_h)

    def draw(self, surface):
        pygame.draw.rect(surface, UITheme.PANEL_BG, (self.x, self.y, self.width, self.height))
        pygame.draw.line(surface, UITheme.BORDER, (self.x, self.y + self.height - 1), (self.x + self.width, self.y + self.height - 1))

        mouse_pos = pygame.mouse.get_pos()
        for b in self.buttons:
            draw_styled_button(surface, b["rect"], b["label"], self.font, mouse_pos, b["color"], UITheme.HOVER_BG if b["color"] == UITheme.PANEL_BG else UITheme.SUCCESS_HOVER)

        tool_name = self.active_tool.capitalize() if self.active_tool else "Tools"
        tools_label = f"☰ {tool_name}"
        btn_color = UITheme.ACCENT if (self.tools_expanded or self.active_tool) else UITheme.PANEL_BG
        btn_hover = UITheme.ACCENT_HOVER if (self.tools_expanded or self.active_tool) else UITheme.HOVER_BG
        draw_styled_button(surface, self.tools_btn_rect, tools_label, self.font, mouse_pos, btn_color, btn_hover)

        if self.tools_expanded:
            dd_rect = self.get_dropdown_rect()
            shadow = dd_rect.copy()
            shadow.y += 3
            pygame.draw.rect(surface, (10, 10, 10, 160), shadow, border_radius=6)
            pygame.draw.rect(surface, UITheme.PANEL_BG, dd_rect, border_radius=6)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, dd_rect, 1, border_radius=6)

            for i, tool in enumerate(self.menu_tool_defs):
                item_rect = pygame.Rect(dd_rect.x + 4, dd_rect.y + 4 + i * self.menu_item_height, dd_rect.width - 8, self.menu_item_height - 2)
                is_active = (self.active_tool == tool["action"])
                hovered = item_rect.collidepoint(mouse_pos)

                if is_active:
                    pygame.draw.rect(surface, UITheme.ACCENT, item_rect, border_radius=4)
                elif hovered:
                    pygame.draw.rect(surface, UITheme.HOVER_BG, item_rect, border_radius=4)

                prefix = "✓ " if is_active else "  "
                lbl_color = UITheme.TEXT if (is_active or hovered) else UITheme.TEXT_DIM
                txt_surf = self.font.render(f"{prefix}{tool['label']}", True, lbl_color)
                surface.blit(txt_surf, (item_rect.x + 8, item_rect.centery - txt_surf.get_height() // 2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.tools_expanded:
                dd_rect = self.get_dropdown_rect()
                if dd_rect.collidepoint(event.pos):
                    rel_y = event.pos[1] - (dd_rect.y + 4)
                    idx = int(rel_y // self.menu_item_height)
                    if 0 <= idx < len(self.menu_tool_defs):
                        action = self.menu_tool_defs[idx]["action"]
                        self.tools_expanded = False
                        self._rebuild_buttons()
                        return action
                    return True
                elif self.tools_btn_rect.collidepoint(event.pos):
                    self.tools_expanded = False
                    return True
                else:
                    self.tools_expanded = False
                    for b in self.buttons:
                        if b["rect"].collidepoint(event.pos):
                            return b["action"]
                    return True

            if self.tools_btn_rect.collidepoint(event.pos):
                self.tools_expanded = not self.tools_expanded
                return True

            for b in self.buttons:
                if b["rect"].collidepoint(event.pos):
                    return b["action"]
        return None

class RenameBuildingModal:
    """Modal to rename all files associated with a building."""
    def __init__(self, font):
        self.font = font
        self.active = False
        self.old_name = ""
        self.folder = ""
        self.root_dir = ""
        self.box = None
        self.rect = pygame.Rect(0, 0, 440, 170)
        self.rename_btn = pygame.Rect(0, 0, 130, 34)
        self.cancel_btn = pygame.Rect(0, 0, 110, 34)

    def open(self, old_name, folder, root_dir, center_x, center_y):
        self.old_name = old_name
        self.folder = folder
        self.root_dir = root_dir
        self.rect.center = (center_x, center_y)
        self.box = UITextBox(self.rect.x + 20, self.rect.y + 65, self.rect.width - 40, 30, self.font, old_name)
        self.box.active = True
        FocusManager.set_focus(self.box)

        btn_y = self.rect.bottom - 48
        self.rename_btn.topleft = (self.rect.x + 85, btn_y)
        self.cancel_btn.topleft = (self.rect.x + 235, btn_y)
        self.active = True

    def handle_event(self, event):
        if not self.active: return None
        if self.box.handle_event(event): return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rename_btn.collidepoint(event.pos):
                new_n = self.box.text.strip()
                self.active = False
                if new_n and new_n != self.old_name:
                    return {
                        "action": "rename_building",
                        "old_name": self.old_name,
                        "new_name": new_n,
                        "folder": self.folder,
                        "root_dir": self.root_dir
                    }
                return True
            elif self.cancel_btn.collidepoint(event.pos):
                self.active = False
                return True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.active = False
            return True
        return True

    def draw(self, surface):
        if not self.active: return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        pygame.draw.rect(surface, UITheme.PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.rect, 2, border_radius=8)
        surface.blit(self.font.render(f"Rename Building: {self.old_name[:20]}", True, UITheme.WARNING), (self.rect.x + 20, self.rect.y + 15))
        pygame.draw.line(surface, UITheme.BORDER, (self.rect.x, self.rect.y + 40), (self.rect.right, self.rect.y + 40))

        surface.blit(self.font.render("New Building Name:", True, UITheme.TEXT_DIM), (self.rect.x + 20, self.rect.y + 46))
        self.box.draw(surface)

        mouse_pos = pygame.mouse.get_pos()
        draw_styled_button(surface, self.rename_btn, "Rename", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.cancel_btn, "Cancel", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

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
        self.tab_height = 35
        
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

        # Context Menu for Right-Click
        self.context_menu = None  # {"name": str, "tab": str, "rect": Rect, "options": list}
        self.context_item_h = 30

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
        pygame.draw.rect(surface, UITheme.PANEL_BG, (self.x, self.y, SIDEBAR_WIDTH, self.height))
        pygame.draw.line(surface, UITheme.BORDER, (self.x, self.y), (self.x, self.y + self.height))

        mouse_pos = pygame.mouse.get_pos()
        for tab in self.tabs:
            rect = self.tab_rects[tab]
            is_active = (self.active_tab == tab)
            hovered = rect.collidepoint(mouse_pos)
            
            color = UITheme.BG if is_active else (UITheme.HOVER_BG if hovered else UITheme.PANEL_BG)
            pygame.draw.rect(surface, color, rect)
            
            if is_active:
                pygame.draw.rect(surface, UITheme.ACCENT, (rect.x, rect.bottom - 2, rect.width, 2))

            text_color = UITheme.TEXT if is_active or hovered else UITheme.TEXT_DIM
            text = self.font.render(tab, True, text_color)
            surface.blit(text, (rect.centerx - text.get_width()//2, rect.centery - text.get_height()//2))

        # Search Bar
        border_color = UITheme.ACCENT if self.search_active else UITheme.BORDER
        pygame.draw.rect(surface, UITheme.BG, self.search_rect, border_radius=4)
        pygame.draw.rect(surface, border_color, self.search_rect, 1 if not self.search_active else 2, border_radius=4)
        
        if self.search_text:
            self.blink_timer = getattr(self, 'blink_timer', 0) + 1
            cursor = "|" if self.search_active and (self.blink_timer // 30) % 2 == 0 else ""
            search_surf = self.font.render(self.search_text + cursor, True, UITheme.TEXT)
        else: 
            search_surf = self.font.render("Search...", True, UITheme.TEXT_DIM)
        
        text_rect = search_surf.get_rect(centery=self.search_rect.centery)
        text_rect.x = self.search_rect.x + 8
        surface.set_clip(self.search_rect.inflate(-8, -4))
        surface.blit(search_surf, text_rect)
        surface.set_clip(None)
        
        view_height = self.y + self.height - self.content_area_y
        view_rect = pygame.Rect(self.x, self.content_area_y, SIDEBAR_WIDTH, view_height)
        surface.set_clip(view_rect)

        content_height = 0
        items_to_draw = self.filtered_tiles if self.active_tab == "Tiles" else self.filtered_items
        selected_name = self.selected_tile if self.active_tab == "Tiles" else self.selected_item

        row, col = 0, 0
        for name, image in sorted(items_to_draw.items()):
            tile_x = self.x + col * (TILE_SIZE + 10) + 10
            tile_y = self.content_area_y + row * (TILE_SIZE + 10) - self.scroll_offset

            if tile_y + TILE_SIZE > self.content_area_y and tile_y < self.y + self.height:
                t_rect = pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE)
                
                # Checkered background for transparency preview
                pygame.draw.rect(surface, (100, 100, 100), t_rect)
                pygame.draw.rect(surface, (150, 150, 150), (t_rect.x, t_rect.y, TILE_SIZE//2, TILE_SIZE//2))
                pygame.draw.rect(surface, (150, 150, 150), (t_rect.x + TILE_SIZE//2, t_rect.y + TILE_SIZE//2, TILE_SIZE//2, TILE_SIZE//2))
                
                surface.blit(image, (tile_x, tile_y))

                if selected_name == name:
                    pygame.draw.rect(surface, UITheme.ACCENT, t_rect, 2)
                elif t_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(surface, UITheme.TEXT, t_rect, 1)
                    register_tooltip(mouse_pos, name)

            col += 1
            if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH - 15:
                col = 0
                row += 1
                
        content_height = (row + 1) * (TILE_SIZE + 10)
        surface.set_clip(None)

        self.max_scroll = max(0, content_height - view_rect.height)
        
        if self.max_scroll > 0:
            self.scrollbar_track_rect = pygame.Rect(self.x + SIDEBAR_WIDTH - 10, self.content_area_y, 8, view_rect.height)
            thumb_h = max(20, (view_rect.height / (content_height + view_rect.height)) * view_rect.height)
            ratio = self.scroll_offset / self.max_scroll if self.max_scroll > 0 else 0
            thumb_y = self.content_area_y + ratio * (view_rect.height - thumb_h)
            self.scrollbar_thumb_rect = pygame.Rect(self.scrollbar_track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER, self.scrollbar_thumb_rect, border_radius=4)
        else:
            self.scrollbar_thumb_rect = None
            self.scrollbar_track_rect = None

        # Draw Right-Click Context Menu on top
        if self.context_menu:
            cm_rect = self.context_menu["rect"]
            shadow = cm_rect.copy()
            shadow.y += 3
            pygame.draw.rect(surface, (10, 10, 10, 160), shadow, border_radius=6)
            pygame.draw.rect(surface, UITheme.PANEL_BG, cm_rect, border_radius=6)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, cm_rect, 1, border_radius=6)

            for i, opt in enumerate(self.context_menu["options"]):
                opt_rect = pygame.Rect(cm_rect.x + 4, cm_rect.y + 4 + i * self.context_item_h, cm_rect.width - 8, self.context_item_h - 2)
                if opt_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(surface, UITheme.LIST_HOVER, opt_rect, border_radius=4)
                lbl_color = UITheme.TEXT if opt_rect.collidepoint(mouse_pos) else UITheme.TEXT_DIM
                lbl = self.font.render(opt["label"], True, lbl_color)
                surface.blit(lbl, (opt_rect.x + 10, opt_rect.centery - lbl.get_height() // 2))

    def handle_event(self, event):
        # 1. Floating Right-Click Context Menu Priority
        if self.context_menu:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cm_rect = self.context_menu["rect"]
                if cm_rect.collidepoint(event.pos):
                    rel_y = event.pos[1] - (cm_rect.y + 4)
                    idx = int(rel_y // self.context_item_h)
                    if 0 <= idx < len(self.context_menu["options"]):
                        opt = self.context_menu["options"][idx]
                        action = opt["action"]
                        item_name = self.context_menu["name"]
                        tab_kind = self.context_menu["tab"]
                        self.context_menu = None
                        return {
                            "action": "item_context_action",
                            "option": action,
                            "item_name": item_name,
                            "tab": tab_kind
                        }
                self.context_menu = None
                return True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.context_menu = None
                return True

        if event.type == pygame.MOUSEBUTTONUP: 
            self.dragging_scroll = False

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
                if event.button == 1:
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

                if my < self.y + self.tab_height and event.button == 1:
                    for tab_name, rect in self.tab_rects.items():
                        if rect.collidepoint(mx, my):
                            self.active_tab = tab_name
                            self.scroll_offset = 0
                            return True
                    return True
                
                if self.search_rect.collidepoint(mx, my) and event.button == 1:
                    self.search_active = True
                    return True
                else: 
                    self.search_active = False

                if event.button == 4:
                    self.scroll_offset = max(0, self.scroll_offset - self.scroll_speed)
                    return True
                if event.button == 5:
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + self.scroll_speed)
                    return True

                if my > self.content_area_y:
                    items_to_check = self.filtered_tiles if self.active_tab == "Tiles" else self.filtered_items
                    row, col = 0, 0
                    for name, image in sorted(items_to_check.items()):
                        tile_x = self.x + col * (TILE_SIZE + 10) + 10
                        tile_y = self.content_area_y + row * (TILE_SIZE + 10) - self.scroll_offset

                        if pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE).collidepoint(mx, my):
                            if event.button == 1:
                                if self.active_tab == "Tiles":
                                    self.selected_tile = name
                                    self.selected_item = None
                                elif self.active_tab == "Items":
                                    self.selected_item = name
                                    self.selected_tile = None
                                self.selected_building = None
                                return True
                            elif event.button == 3:
                                cm_w, cm_h = 160, 3 * self.context_item_h + 8
                                
                                # Query the current real window resolution dynamically
                                cur_surf = pygame.display.get_surface()
                                screen_w, screen_h = cur_surf.get_size() if cur_surf else (self.x + SIDEBAR_WIDTH, self.y + self.height)
                                
                                # Anchor at cursor; flip left/up if overflowing window boundary
                                cm_x = mx if (mx + cm_w <= screen_w - 5) else max(5, mx - cm_w)
                                cm_y = my if (my + cm_h <= screen_h - 5) else max(5, screen_h - cm_h - 5)

                                self.context_menu = {
                                    "name": name,
                                    "tab": self.active_tab,
                                    "rect": pygame.Rect(cm_x, cm_y, cm_w, cm_h),
                                    "options": [
                                        {"label": "Edit Entity", "action": "edit_entity"},
                                        {"label": "Edit Sprite", "action": "edit_sprite"},
                                        {"label": "Edit Code", "action": "edit_code"},
                                    ]
                                }
                                return True

                        col += 1
                        if col * (TILE_SIZE + 10) + 10 > SIDEBAR_WIDTH - 15:
                            col = 0
                            row += 1
                return True
                
        if event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_BACKSPACE: 
                self.search_text = self.search_text[:-1]
            else: 
                self.search_text += event.unicode
            self._filter_content()
            return True
        return False


class UIAttributeList:
    def __init__(self, x, y, width, height, font, text=""):
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
            
            self.data[attr]["cb_rect"] = pygame.Rect(bx, by + 4, 20, 20)
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
            
            pygame.draw.rect(surface, UITheme.BG, cb, border_radius=4)
            if info["enabled"]:
                pygame.draw.rect(surface, UITheme.ACCENT, cb.inflate(-4, -4), border_radius=2)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, cb, 1, border_radius=4)
            
            lbl = attr.capitalize()
            surface.blit(self.font.render(lbl, True, UITheme.TEXT), (cb.right + 10, cb.y + 2))
            
            if info["enabled"]:
                info["box"].draw(surface)