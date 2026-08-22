import os
import pygame
from editor.ui import UITextArea, UITextBox, UIDropdown
from editor.config import CODE_GLOBAL_ROOT, CODE_LOCAL_ROOT, ICON_SIZE

# ----------------------------------------------------------------------
# CodeTextArea – extends UITextArea with line numbers and proper scroll
# ----------------------------------------------------------------------
class CodeTextArea(UITextArea):
    def __init__(self, x, y, width, height, font, text=""):
        super().__init__(x, y, width, height, font, text)
        self.line_number_width = 40

    def _update_lines(self):
        super()._update_lines()
        self.scroll_y = max(0, min(self.scroll_y, self._max_scroll))

    def draw(self, surface):
        # 1. Background and border (no clip)
        pygame.draw.rect(surface, (40, 40, 40), self.rect)
        pygame.draw.rect(surface, (255, 255, 255) if self.active else (100, 100, 100), self.rect, 2)

        # 2. Draw line numbers (no clip)
        line_num_rect = pygame.Rect(self.rect.x + 2, self.rect.y + 2,
                                    self.line_number_width - 4, self.rect.height - 4)
        pygame.draw.rect(surface, (35, 35, 40), line_num_rect)

        font_height = self.line_height
        line_y = self.rect.y + 5 - self.scroll_y
        line_num = 1
        for i, (l_text, s_idx, e_idx) in enumerate(self.lines):
            if line_y + font_height > self.rect.y and line_y < self.rect.bottom:
                num_surf = self.font.render(str(line_num), True, (120, 120, 120))
                surface.blit(num_surf, (self.rect.x + 5, line_y))
            line_num += 1
            line_y += font_height

        # 3. Set clip for text area (excluding line numbers)
        text_rect = self.rect.inflate(-4, -4)
        text_rect.x += self.line_number_width
        text_rect.width -= self.line_number_width
        surface.set_clip(text_rect)

        # 4. Draw text, selection, cursor (same as parent, but with offset)
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
                    pygame.draw.rect(surface, (0, 100, 200),
                                     (self.rect.x + self.line_number_width + 5 + h_x, y_pos, h_w, self.line_height))

            ts = self.font.render(l_text, True, (255, 255, 255))
            surface.blit(ts, (self.rect.x + self.line_number_width + 5, y_pos))

        if self.active:
            self.blink_timer += 1
            if (self.blink_timer // 30) % 2 == 0:
                cx = self.rect.x + self.line_number_width + 5 + cursor_x
                cy = self.rect.y + 5 + cursor_y - self.scroll_y
                pygame.draw.line(surface, (255, 255, 255), (cx, cy), (cx, cy + self.line_height - 2), 2)

        surface.set_clip(None)

        # 5. Draw scrollbar
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

# ----------------------------------------------------------------------
# CodeFileTree – a simple file tree with expandable folders
# ----------------------------------------------------------------------
class CodeFileTree:
    # ... (keep your existing implementation, it's fine)
    # (I'll include it here for completeness, but you already have it)

    def __init__(self, x, y, width, height, font, root_dir):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.root_dir = root_dir
        self.selected_path = None
        self.scroll_offset = 0
        self.dragging_scroll = False
        self.scroll_start_y = 0
        self.scroll_start_offset = 0
        self.tree_data = []
        self.expanded = {}
        self.line_height = 25
        self.refresh()

    def refresh(self):
        self.tree_data = []
        if not os.path.isdir(self.root_dir):
            return

        def build_tree(dir_path, depth=0):
            items = []
            try:
                entries = os.listdir(dir_path)
            except OSError:
                return items
            dirs = []
            files = []
            for name in entries:
                full_path = os.path.join(dir_path, name)
                if os.path.isdir(full_path):
                    dirs.append(name)
                else:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in ['.txt', '.lua', '.py', '.json', '.cfg', '.xml', '.md', '.csv']:
                        files.append(name)
            dirs.sort(key=str.lower)
            files.sort(key=str.lower)

            for name in dirs + files:
                full_path = os.path.join(dir_path, name)
                is_dir = os.path.isdir(full_path)
                items.append({
                    'name': name,
                    'path': full_path,
                    'is_dir': is_dir,
                    'depth': depth,
                    'expanded': self.expanded.get(full_path, False),
                    'children': build_tree(full_path, depth+1) if is_dir else []
                })
            return items

        self.tree_data = build_tree(self.root_dir)
        if self.selected_path and not os.path.exists(self.selected_path):
            self.selected_path = None

    def get_selected_file(self):
        return self.selected_path if self.selected_path and os.path.isfile(self.selected_path) else None

    def _flatten(self, node_list, result=None, depth_offset=0):
        if result is None:
            result = []
        for node in node_list:
            result.append((node['depth'] + depth_offset, node['name'], node['is_dir'],
                           node['expanded'], node['path']))
            if node['is_dir'] and node['expanded']:
                self._flatten(node['children'], result, depth_offset + 1)
        return result

    def handle_event(self, event):
        mx, my = event.pos if hasattr(event, 'pos') else (0,0)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if hasattr(self, 'thumb_rect') and self.thumb_rect and self.thumb_rect.collidepoint(mx, my):
                    self.dragging_scroll = True
                    self.scroll_start_y = my
                    self.scroll_start_offset = self.scroll_offset
                    return True
                if self.track_rect and self.track_rect.collidepoint(mx, my) and self.max_scroll > 0:
                    if my < self.thumb_rect.y:
                        self.scroll_offset = max(0, self.scroll_offset - self.rect.height)
                    else:
                        self.scroll_offset = min(self.max_scroll, self.scroll_offset + self.rect.height)
                    return True
                if self.rect.collidepoint(mx, my):
                    self._handle_click(mx, my)
                    return True
            elif event.button in (4,5):
                if self.rect.collidepoint(mx, my):
                    self.scroll_offset += -30 if event.button == 4 else 30
                    self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset))
                    return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging_scroll = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_scroll and hasattr(self, 'thumb_rect') and self.thumb_rect and self.max_scroll > 0:
                dy = my - self.scroll_start_y
                track_h = self.track_rect.height
                thumb_h = self.thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    scroll_per_pixel = self.max_scroll / track_space
                    self.scroll_offset = self.scroll_start_offset + dy * scroll_per_pixel
                    self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset))
                return True
        return False

    def _handle_click(self, mx, my):
        flat = self._flatten(self.tree_data)
        y = self.rect.y - self.scroll_offset
        for depth, name, is_dir, expanded, path in flat:
            item_rect = pygame.Rect(self.rect.x + 8 + depth * 16, y,
                                    self.rect.width - depth*16 - 16, self.line_height)
            if item_rect.collidepoint(mx, my):
                if is_dir:
                    self.expanded[path] = not self.expanded.get(path, False)
                    self.refresh()
                else:
                    self.selected_path = path
                return True
            y += self.line_height
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, (30, 30, 35), self.rect)
        pygame.draw.line(surface, (60, 60, 70), (self.rect.right, self.rect.y),
                         (self.rect.right, self.rect.bottom), 2)
        surface.set_clip(self.rect)
        flat = self._flatten(self.tree_data)
        y = self.rect.y - self.scroll_offset
        for depth, name, is_dir, expanded, path in flat:
            if y + self.line_height < self.rect.y or y > self.rect.bottom:
                y += self.line_height
                continue
            x = self.rect.x + 8 + depth * 16
            if path == self.selected_path and not is_dir:
                pygame.draw.rect(surface, (60, 60, 100),
                                 (x, y, self.rect.width - depth*16 - 16, self.line_height))
            icon = "📁" if is_dir else "📄"
            if is_dir:
                icon = "📂" if expanded else "📁"
            txt = self.font.render(icon + " " + name, True, (220, 220, 220))
            surface.blit(txt, (x, y + 2))
            y += self.line_height
        surface.set_clip(None)
        content_h = len(flat) * self.line_height
        self.max_scroll = max(0, content_h - self.rect.height)
        if self.max_scroll > 0:
            self.track_rect = pygame.Rect(self.rect.right - 12, self.rect.y, 12, self.rect.height)
            pygame.draw.rect(surface, (40, 40, 40), self.track_rect)
            thumb_h = max(20, (self.rect.height / content_h) * self.rect.height)
            thumb_y = self.rect.y + (self.scroll_offset / self.max_scroll) * (self.rect.height - thumb_h)
            self.thumb_rect = pygame.Rect(self.track_rect.x, thumb_y, 12, thumb_h)
            pygame.draw.rect(surface, (100, 100, 100), self.thumb_rect)
        else:
            self.track_rect = None
            self.thumb_rect = None


# ----------------------------------------------------------------------
# NewFileModal – simple dialog to enter a new filename
# ----------------------------------------------------------------------
class NewFileModal:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.active = False
        self.name_input = UITextBox(x + 20, y + 50, width - 40, 30, font, "")
        self.create_btn = pygame.Rect(x + 20, y + 100, 80, 30)
        self.cancel_btn = pygame.Rect(x + width - 100, y + 100, 80, 30)

    def handle_event(self, event):
        if not self.active:
            return None
        if self.name_input.handle_event(event):
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.create_btn.collidepoint(event.pos):
                name = self.name_input.text.strip()
                if name:
                    self.active = False
                    return {"action": "create", "name": name}
            elif self.cancel_btn.collidepoint(event.pos):
                self.active = False
                return {"action": "cancel"}
        return None

    def draw(self, surface):
        if not self.active:
            return
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill((40, 40, 50, 240))
        surface.blit(s, self.rect.topleft)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2)
        surface.blit(self.font.render("New File", True, (255, 255, 255)),
                     (self.rect.x + 20, self.rect.y + 15))
        surface.blit(self.font.render("Filename:", True, (200, 200, 200)),
                     (self.rect.x + 20, self.rect.y + 35))
        self.name_input.draw(surface)
        pygame.draw.rect(surface, (0, 150, 0), self.create_btn)
        txt = self.font.render("Create", True, (255, 255, 255))
        surface.blit(txt, (self.create_btn.x + 10, self.create_btn.y + 5))
        pygame.draw.rect(surface, (150, 0, 0), self.cancel_btn)
        txt = self.font.render("Cancel", True, (255, 255, 255))
        surface.blit(txt, (self.cancel_btn.x + 10, self.cancel_btn.y + 5))


# ----------------------------------------------------------------------
# CodeEditor – the main editor for the CODE tab
# ----------------------------------------------------------------------
class CodeEditor:
    def __init__(self, y_offset, width, height, font):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        self.root_choice = "Local"
        self.current_root = CODE_LOCAL_ROOT

        self.root_opts = [
            {"label": "Local (game)", "value": "Local"},
            {"label": "Global (bitrot)", "value": "Global"}
        ]
        self.root_dropdown = UIDropdown(20, y_offset + 15, 180, 28, font, self.root_opts, "Local")

        self.save_btn = pygame.Rect(220, y_offset + 15, 80, 28)
        self.new_btn = pygame.Rect(310, y_offset + 15, 80, 28)
        self.delete_btn = pygame.Rect(400, y_offset + 15, 80, 28)
        self.refresh_btn = pygame.Rect(490, y_offset + 15, 80, 28)

        tree_w = 280
        tree_h = height - y_offset - 70
        self.file_tree = CodeFileTree(0, y_offset + 55, tree_w, tree_h, font, self.current_root)

        # Text area with line numbers
        text_x = tree_w + 5
        text_w = width - tree_w - 10
        text_h = tree_h
        self.text_area = CodeTextArea(text_x, y_offset + 55, text_w, text_h, font, "")
        self.current_file_path = None
        self.unsaved = False

        self.new_modal = NewFileModal(width//2 - 150, height//2 - 100, 300, 180, font)

    def resize(self, width, height):
        self.width = width
        self.height = height
        tree_w = 280
        tree_h = height - self.y_offset - 70
        self.file_tree.rect.width = tree_w
        self.file_tree.rect.height = tree_h
        text_x = tree_w + 5
        text_w = width - tree_w - 10
        self.text_area.rect.x = text_x
        self.text_area.rect.y = self.y_offset + 55
        self.text_area.rect.width = text_w
        self.text_area.rect.height = tree_h
        # line number width is fixed inside CodeTextArea

    def _load_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_area.text = content
            self.text_area._update_lines()
            # Reset undo history
            self.text_area.history = [content]
            self.text_area.history_index = 0
            self.current_file_path = path
            self.unsaved = False
        except Exception as e:
            print(f"Error loading {path}: {e}")
            self.text_area.text = f"Error loading file:\n{str(e)}"
            self.text_area._update_lines()

    def _save_file(self):
        if self.current_file_path:
            try:
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_area.text)
                self.unsaved = False
                print(f"Saved {self.current_file_path}")
            except Exception as e:
                print(f"Error saving: {e}")

    def _delete_file(self):
        if self.current_file_path and os.path.exists(self.current_file_path):
            try:
                os.remove(self.current_file_path)
                self.current_file_path = None
                self.text_area.text = ""
                self.text_area._update_lines()
                self.unsaved = False
                self.file_tree.selected_path = None
                self.file_tree.refresh()
            except Exception as e:
                print(f"Error deleting: {e}")

    def _new_file(self, name):
        if not name:
            return
        path = os.path.join(self.current_root, name)
        if os.path.exists(path):
            print(f"File {name} already exists")
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("")
            self.file_tree.refresh()
            self.file_tree.selected_path = path
            self._load_file(path)
        except Exception as e:
            print(f"Error creating file: {e}")

    def handle_event(self, event):
        if self.new_modal.active:
            res = self.new_modal.handle_event(event)
            if res:
                if res['action'] == 'create':
                    self._new_file(res['name'])
                self.new_modal.active = False
            return True

        if self.root_dropdown.handle_event(event):
            if self.root_dropdown.text != self.root_choice:
                self.root_choice = self.root_dropdown.text
                self.current_root = CODE_GLOBAL_ROOT if self.root_choice == "Global" else CODE_LOCAL_ROOT
                self.file_tree.root_dir = self.current_root
                self.file_tree.refresh()
                self.current_file_path = None
                self.text_area.text = ""
                self.text_area._update_lines()
                self.unsaved = False
            return True

        if self.file_tree.handle_event(event):
            sel = self.file_tree.get_selected_file()
            if sel and sel != self.current_file_path:
                self._load_file(sel)
            return True

        if self.text_area.handle_event(event):
            self.unsaved = True
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.save_btn.collidepoint(mx, my):
                self._save_file()
                return True
            if self.new_btn.collidepoint(mx, my):
                self.new_modal.active = True
                self.new_modal.name_input.text = ""
                return True
            if self.delete_btn.collidepoint(mx, my):
                self._delete_file()
                return True
            if self.refresh_btn.collidepoint(mx, my):
                self.file_tree.refresh()
                return True

        if event.type == pygame.KEYDOWN:
            if (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_s:
                self._save_file()
                return True
            if event.key == pygame.K_ESCAPE and self.new_modal.active:
                self.new_modal.active = False
                return True

        return False

    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, (25, 25, 30), bg_rect)

        self.root_dropdown.draw(surface)

        for btn, label, color in [
            (self.save_btn, "Save", (0, 120, 0)),
            (self.new_btn, "New", (0, 100, 150)),
            (self.delete_btn, "Delete", (150, 0, 0)),
            (self.refresh_btn, "Refresh", (80, 80, 80))
        ]:
            pygame.draw.rect(surface, color, btn)
            txt = self.font.render(label, True, (255, 255, 255))
            surface.blit(txt, (btn.x + 5, btn.y + 5))

        self.file_tree.draw(surface)
        self.text_area.draw(surface)

        if self.unsaved and self.current_file_path:
            indicator = self.font.render("* Unsaved", True, (255, 200, 50))
            surface.blit(indicator, (self.width - 120, self.y_offset + 20))

        self.root_dropdown.draw_list(surface)

        if self.new_modal.active:
            self.new_modal.draw(surface)