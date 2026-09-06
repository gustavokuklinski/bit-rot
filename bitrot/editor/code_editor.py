import os
import pygame
from editor.ui import UITextArea, UITextBox, UIDropdown, UITheme, draw_styled_button
from editor.config import XML_DATA_ROOT, ICON_SIZE

# ----------------------------------------------------------------------
# CodeTextArea – polished with line numbers and robust scrolling
# ----------------------------------------------------------------------
class CodeTextArea(UITextArea):
    def __init__(self, x, y, width, height, font, text=""):
        super().__init__(x, y, width, height, font, text)
        self.line_number_width = 50

    def _update_lines(self):
        self.lines = []
        if not self.text:
            self.lines.append(("", 0, 0))
            return

        start_idx = 0
        for i, char in enumerate(self.text):
            if char == '\n':
                self.lines.append((self.text[start_idx:i], start_idx, i))
                start_idx = i + 1
        self.lines.append((self.text[start_idx:], start_idx, len(self.text)))

    def draw(self, surface):
        pygame.draw.rect(surface, UITheme.BG, self.rect)
        pygame.draw.rect(surface, UITheme.ACCENT if self.active else UITheme.BORDER, self.rect, 1)

        gutter_rect = pygame.Rect(self.rect.x, self.rect.y, self.line_number_width, self.rect.height)
        pygame.draw.rect(surface, UITheme.PANEL_BG, gutter_rect)
        pygame.draw.line(surface, UITheme.BORDER, (gutter_rect.right, gutter_rect.top), (gutter_rect.right, gutter_rect.bottom), 1)

        text_clip = pygame.Rect(gutter_rect.right, self.rect.y, self.rect.width - self.line_number_width, self.rect.height)
        surface.set_clip(text_clip)

        cursor_y = 0
        cursor_x = 0
        for i, (l_text, s_idx, e_idx) in enumerate(self.lines):
            if s_idx <= self.cursor_pos <= e_idx:
                cursor_y = i * self.line_height
                cursor_x = self.font.size(l_text[:self.cursor_pos - s_idx])[0]
                break

        if self.active:
            if cursor_y < self.scroll_y: self.scroll_y = cursor_y
            elif cursor_y + self.line_height > self.scroll_y + self.rect.height - 20:
                self.scroll_y = cursor_y + self.line_height - self.rect.height + 20

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
                    pygame.draw.rect(surface, UITheme.LIST_HOVER, (text_clip.x + 8 + h_x, y_pos, h_w, self.line_height))

            ts = self.font.render(l_text, True, UITheme.TEXT)
            surface.blit(ts, (text_clip.x + 8, y_pos))

        if self.active and (self.blink_timer // 30) % 2 == 0:
            cx = text_clip.x + 8 + cursor_x
            cy = self.rect.y + 8 + cursor_y - self.scroll_y
            pygame.draw.line(surface, UITheme.TEXT, (cx, cy), (cx, cy + self.line_height - 2), 2)

        surface.set_clip(None)

        for i in range(len(self.lines)):
            y_pos = self.rect.y + 8 + i * self.line_height - self.scroll_y
            if y_pos + self.line_height > self.rect.y and y_pos < self.rect.bottom:
                num_surf = self.font.render(str(i + 1), True, UITheme.TEXT_DIM)
                surface.blit(num_surf, (self.rect.x + 8, y_pos))

        if self._max_scroll > 0:
            sb_rect = pygame.Rect(self.rect.right - 8, self.rect.y + 2, 6, self.rect.height - 4)
            pygame.draw.rect(surface, UITheme.PANEL_BG, sb_rect, border_radius=3)
            thumb_h = max(20, self.rect.height * (self.rect.height / (len(self.lines) * self.line_height + 10)))
            thumb_y = self.rect.y + 2 + (self.scroll_y / self._max_scroll) * (self.rect.height - 4 - thumb_h)
            self.thumb_rect = pygame.Rect(sb_rect.x, thumb_y, 6, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.thumb_rect, border_radius=3)

# ----------------------------------------------------------------------
# CodeFileTree – XML specific file tree
# ----------------------------------------------------------------------
class CodeFileTree:
    def __init__(self, x, y, width, height, font, root_dir):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.root_dir = root_dir
        self.selected_path = None
        self.scroll_offset = 0
        self.tree_data = []
        self.expanded = {}
        self.line_height = 25
        self.refresh()

    def refresh(self):
        self.tree_data = []
        if not os.path.isdir(self.root_dir): return

        def build_tree(dir_path, depth=0):
            items = []
            try:
                entries = sorted(os.listdir(dir_path), key=str.lower)
            except OSError: return items
            
            for name in entries:
                full_path = os.path.join(dir_path, name)
                if os.path.isdir(full_path):
                    items.append({
                        'name': name, 'path': full_path, 'is_dir': True, 'depth': depth,
                        'expanded': self.expanded.get(full_path, False),
                        'children': build_tree(full_path, depth + 1)
                    })
                elif name.lower().endswith('.xml'):
                    items.append({
                        'name': name, 'path': full_path, 'is_dir': False, 'depth': depth,
                        'children': []
                    })
            return items

        self.tree_data = build_tree(self.root_dir)

    def _flatten(self, node_list, result=None):
        if result is None: result = []
        for node in node_list:
            result.append(node)
            if node['is_dir'] and node['expanded']:
                self._flatten(node['children'], result)
        return result

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                mx, my = event.pos
                flat = self._flatten(self.tree_data)
                y = self.rect.y - self.scroll_offset
                for node in flat:
                    item_rect = pygame.Rect(self.rect.x, y, self.rect.width, self.line_height)
                    if item_rect.collidepoint(mx, my):
                        if node['is_dir']:
                            self.expanded[node['path']] = not self.expanded.get(node['path'], False)
                            self.refresh()
                        else:
                            self.selected_path = node['path']
                        return True
                    y += self.line_height
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self.rect.collidepoint(event.pos):
                self.scroll_offset += -30 if event.button == 4 else 30
                self.scroll_offset = max(0, self.scroll_offset)
                return True
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, UITheme.PANEL_BG, self.rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.rect.right - 1, self.rect.y), (self.rect.right - 1, self.rect.bottom))
        
        surface.set_clip(self.rect)
        flat = self._flatten(self.tree_data)
        y = self.rect.y - self.scroll_offset
        mouse_pos = pygame.mouse.get_pos()
        
        for node in flat:
            if y + self.line_height < self.rect.y or y > self.rect.bottom:
                y += self.line_height
                continue
            
            x = self.rect.x + 10 + node['depth'] * 15
            row_rect = pygame.Rect(self.rect.x, y, self.rect.width, self.line_height)
            
            if self.selected_path == node['path'] and not node['is_dir']:
                pygame.draw.rect(surface, UITheme.LIST_HOVER, row_rect)
            elif row_rect.collidepoint(mouse_pos):
                pygame.draw.rect(surface, UITheme.HOVER_BG, row_rect)

            icon = "[-]" if node['is_dir'] and node['expanded'] else ("[+]" if node['is_dir'] else "")
            txt = self.font.render(f"{icon} {node['name']}", True, UITheme.TEXT)
            surface.blit(txt, (x, y + 4))
            y += self.line_height
        surface.set_clip(None)

# ----------------------------------------------------------------------
# CodeEditor – Now featuring Tabs and XML focus
# ----------------------------------------------------------------------
class CodeEditor:
    def __init__(self, y_offset, width, height, font):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        
        self.current_root = XML_DATA_ROOT
        self.file_tree = CodeFileTree(0, y_offset + 40, 250, height - y_offset - 40, font, self.current_root)
        
        self.open_files = []
        self.active_tab_idx = -1
        self.tab_width = 140
        self.tab_height = 40

        self.text_area = CodeTextArea(250, y_offset + 40, width - 250, height - y_offset - 40, font)
        self.save_btn = pygame.Rect(260, y_offset + 5, 100, 30)

    def resize(self, width, height):
        self.width = width
        self.height = height
        self.file_tree.rect.width = 250
        self.text_area.rect.x = 250
        self.text_area.rect.width = width - 250

    def open_file(self, path):
        if path not in self.open_files:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.open_files.append(path)
            except Exception as e:
                print(f"Error opening file: {e}")
                return
        
        self.active_tab_idx = self.open_files.index(path)
        self._sync_text_area()

    def _sync_text_area(self):
        if 0 <= self.active_tab_idx < len(self.open_files):
            path = self.open_files[self.active_tab_idx]
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.text_area.text = f.read()
                self.text_area._update_lines()
                self.text_area.cursor_pos = len(self.text_area.text)
                self.text_area.active = True
            except Exception as e:
                self.text_area.text = f"Error loading file: {e}"
                self.text_area._update_lines()

    def _save_current_file(self):
        if self.active_tab_idx != -1:
            path = self.open_files[self.active_tab_idx]
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.text_area.text)
                print(f"Saved: {path}")
            except Exception as e:
                print(f"Save error: {e}")

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, path in enumerate(self.open_files):
                tab_rect = pygame.Rect(250 + i * self.tab_width, self.y_offset, self.tab_width, self.tab_height)
                
                close_rect = pygame.Rect(tab_rect.right - 20, tab_rect.y + 10, 16, 16)
                if close_rect.collidepoint(event.pos):
                    self.open_files.pop(i)
                    if self.active_tab_idx == i:
                        self.active_tab_idx = len(self.open_files) - 1 if self.open_files else -1
                    self._sync_text_area()
                    return True
                    
                if tab_rect.collidepoint(event.pos):
                    self.active_tab_idx = i
                    self._sync_text_area()
                    return True

        if self.file_tree.handle_event(event):
            if self.file_tree.selected_path:
                self.open_file(self.file_tree.selected_path)
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.save_btn.collidepoint(event.pos):
                self._save_current_file()
                return True

        if self.text_area.handle_event(event):
            return True

        if event.type == pygame.KEYDOWN:
            if (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_s:
                self._save_current_file()
                return True

        return False

    def draw(self, surface):
        pygame.draw.rect(surface, UITheme.BG, (0, self.y_offset, self.width, self.height - self.y_offset))
        pygame.draw.rect(surface, UITheme.PANEL_BG, (0, self.y_offset, self.width, 40))
        pygame.draw.line(surface, UITheme.BORDER, (0, self.y_offset + 39), (self.width, self.y_offset + 39))

        mouse_pos = pygame.mouse.get_pos()
        if self.open_files:
            self.save_btn.x = 250 + len(self.open_files) * self.tab_width + 10
            draw_styled_button(surface, self.save_btn, "Save File", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)

        for i, path in enumerate(self.open_files):
            tab_rect = pygame.Rect(250 + i * self.tab_width, self.y_offset, self.tab_width, self.tab_height)
            is_active = (i == self.active_tab_idx)
            hovered = tab_rect.collidepoint(mouse_pos)
            
            color = UITheme.BG if is_active else (UITheme.HOVER_BG if hovered else UITheme.PANEL_BG)
            pygame.draw.rect(surface, color, tab_rect)
            pygame.draw.rect(surface, UITheme.BORDER, tab_rect, 1)
            
            if is_active:
                pygame.draw.rect(surface, UITheme.ACCENT, (tab_rect.x, tab_rect.y, tab_rect.width, 2))
                
            fname = os.path.basename(path)
            txt_color = UITheme.TEXT if is_active or hovered else UITheme.TEXT_DIM
            txt = self.font.render(fname[:12], True, txt_color)
            surface.blit(txt, (tab_rect.x + 10, tab_rect.centery - txt.get_height()//2))
            
            close_rect = pygame.Rect(tab_rect.right - 20, tab_rect.y + 12, 16, 16)
            c_hover = close_rect.collidepoint(mouse_pos)
            pygame.draw.rect(surface, UITheme.DANGER if c_hover else UITheme.BORDER, close_rect, border_radius=3)
            surface.blit(self.font.render("x", True, UITheme.TEXT), (close_rect.x + 4, close_rect.y + 1))

        self.file_tree.draw(surface)
        if self.open_files:
            self.text_area.draw(surface)