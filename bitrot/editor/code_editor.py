import os
import pygame
from editor.ui import UITextArea, UITextBox, UIDropdown, UITheme, draw_styled_button, FocusManager
from editor.config import XML_DATA_ROOT, GAME_ROOT, ICON_SIZE

# ----------------------------------------------------------------------
# CodeTextArea – Line Wrapping, Gutter Alignment, Free Scrolling
# ----------------------------------------------------------------------
class CodeTextArea(UITextArea):
    def __init__(self, x, y, width, height, font, text=""):
        super().__init__(x, y, width, height, font, text)
        self.line_number_width = 50

    def _update_lines(self):
        self.lines = []
        if not self.text:
            self.lines.append(("", 0, 0, True, 1))
            return

        # Available text width accounting for gutter, padding, and scrollbar
        avail_w = max(100, self.rect.width - self.line_number_width - 32)
        logical_line_num = 1
        pos = 0
        text_len = len(self.text)

        while pos <= text_len:
            nl_pos = self.text.find('\n', pos)
            if nl_pos == -1:
                chunk = self.text[pos:]
                end_pos = text_len
            else:
                chunk = self.text[pos:nl_pos]
                end_pos = nl_pos

            # Single logical line fits
            if not chunk or self.font.size(chunk)[0] <= avail_w:
                self.lines.append((chunk, pos, end_pos, True, logical_line_num))
            else:
                # Wrap long line into sub-lines
                c_start = 0
                is_first = True
                while c_start < len(chunk):
                    low, high = 1, len(chunk) - c_start
                    best_len = 1
                    while low <= high:
                        mid = (low + high) // 2
                        sub = chunk[c_start:c_start + mid]
                        if self.font.size(sub)[0] <= avail_w:
                            best_len = mid
                            low = mid + 1
                        else:
                            high = mid - 1
                    
                    # Word boundary wrap if space exists
                    if c_start + best_len < len(chunk):
                        last_space = chunk[c_start:c_start + best_len].rfind(' ')
                        if last_space > 0:
                            best_len = last_space + 1
                    
                    sub_str = chunk[c_start:c_start + best_len]
                    self.lines.append((sub_str, pos + c_start, pos + c_start + best_len, is_first, logical_line_num))
                    c_start += best_len
                    is_first = False

            logical_line_num += 1
            if nl_pos == -1:
                break
            pos = nl_pos + 1

    def _get_idx_from_pos(self, x, y):
        rel_y = y - self.rect.y + self.scroll_y - 8
        line_idx = int(rel_y // self.line_height)
        line_idx = max(0, min(len(self.lines) - 1, line_idx))
        
        line_text, start_idx, end_idx, *_ = self.lines[line_idx]
        
        # Account for line number gutter width + padding
        rel_x = x - (self.rect.x + self.line_number_width + 8)
        if rel_x <= 0:
            return start_idx
        
        for i in range(len(line_text)):
            w = self.font.size(line_text[:i])[0]
            cw = self.font.size(line_text[i])[0]
            if rel_x < w + cw / 2:
                return start_idx + i
        return end_idx

    def _ensure_cursor_visible(self):
        cursor_y = 0
        for i, item in enumerate(self.lines):
            s_idx, e_idx = item[1], item[2]
            if s_idx <= self.cursor_pos <= e_idx:
                cursor_y = i * self.line_height
                break
        if cursor_y < self.scroll_y:
            self.scroll_y = max(0, cursor_y)
        elif cursor_y + self.line_height > self.scroll_y + self.rect.height - 20:
            self.scroll_y = min(self._max_scroll, cursor_y + self.line_height - self.rect.height + 20)

    def handle_event(self, event):
        res = super().handle_event(event)
        if event.type == pygame.KEYDOWN and self.active:
            self._ensure_cursor_visible()
        return res

    def draw(self, surface):
        pygame.draw.rect(surface, UITheme.BG, self.rect)
        pygame.draw.rect(surface, UITheme.ACCENT if self.active else UITheme.BORDER, self.rect, 1)

        gutter_rect = pygame.Rect(self.rect.x, self.rect.y, self.line_number_width, self.rect.height)
        pygame.draw.rect(surface, UITheme.PANEL_BG, gutter_rect)
        pygame.draw.line(surface, UITheme.BORDER, (gutter_rect.right, gutter_rect.top), (gutter_rect.right, gutter_rect.bottom), 1)

        text_clip = pygame.Rect(gutter_rect.right, self.rect.y, self.rect.width - self.line_number_width, self.rect.height)
        prev_clip = surface.get_clip()
        surface.set_clip(text_clip.clip(prev_clip) if prev_clip else text_clip)

        cursor_y = 0
        cursor_x = 0
        for i, item in enumerate(self.lines):
            l_text, s_idx, e_idx = item[0], item[1], item[2]
            if s_idx <= self.cursor_pos <= e_idx:
                cursor_y = i * self.line_height
                cursor_x = self.font.size(l_text[:self.cursor_pos - s_idx])[0]
                break

        for i, item in enumerate(self.lines):
            l_text, s_idx, e_idx = item[0], item[1], item[2]
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

        surface.set_clip(prev_clip)

        # Draw line numbers (only for logical line starts)
        for i, item in enumerate(self.lines):
            is_first, line_num = item[3], item[4]
            if not is_first:
                continue
            y_pos = self.rect.y + 8 + i * self.line_height - self.scroll_y
            if y_pos + self.line_height > self.rect.y and y_pos < self.rect.bottom:
                num_surf = self.font.render(str(line_num), True, UITheme.TEXT_DIM)
                surface.blit(num_surf, (self.rect.x + 8, y_pos))

        if self._max_scroll > 0:
            sb_rect = pygame.Rect(self.rect.right - 8, self.rect.y + 2, 6, self.rect.height - 4)
            pygame.draw.rect(surface, UITheme.PANEL_BG, sb_rect, border_radius=3)
            thumb_h = max(20, int(self.rect.height * (self.rect.height / (len(self.lines) * self.line_height + 20))))
            thumb_y = self.rect.y + 2 + (self.scroll_y / self._max_scroll) * (self.rect.height - 4 - thumb_h)
            self.thumb_rect = pygame.Rect(sb_rect.x, thumb_y, 6, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.thumb_rect, border_radius=3)

# ----------------------------------------------------------------------
# CodeFileTree – Shows XML and Markdown files & Folder Enumeration
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
                elif name.lower().endswith(('.xml', '.md')):
                    items.append({
                        'name': name, 'path': full_path, 'is_dir': False, 'depth': depth,
                        'children': []
                    })
            return items

        self.tree_data = build_tree(self.root_dir)

    def get_folder_options(self):
        """Returns relative folder choices for the New File dropdown based on existing folders."""
        opts = [{"label": "/ (Root)", "value": self.root_dir}]
        def collect(nodes):
            for n in nodes:
                if n.get('is_dir'):
                    rel = os.path.relpath(n['path'], self.root_dir).replace('\\', '/')
                    opts.append({"label": rel, "value": n['path']})
                    collect(n.get('children', []))
        collect(self.tree_data)
        root_opt = opts[0]
        sub_opts = sorted(opts[1:], key=lambda x: x["label"].lower())
        return [root_opt] + sub_opts

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
# CodeEditor – Toolbar, Dynamic Tabs, Folder Dropdown on New File
# ----------------------------------------------------------------------
class CodeEditor:
    def __init__(self, y_offset, width, height, font):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        
        self.toolbar_h = 42
        self.tab_bar_h = 36
        content_y = y_offset + self.toolbar_h + self.tab_bar_h

        self.current_root = XML_DATA_ROOT
        self.file_tree = CodeFileTree(0, content_y, 250, height - content_y, font, self.current_root)
        
        self.open_files = []
        self.file_data = {}
        self.active_tab_idx = -1

        # Horizontal scrolling for tabs
        self.tab_scroll_x = 0
        self.max_tab_scroll = 0
        self.dragging_tab_scroll = False
        self.tab_scroll_start_x = 0
        self.tab_scroll_start_offset = 0
        self.tab_thumb_rect = None

        self.text_area = CodeTextArea(250, content_y, width - 250, height - content_y, font)

        # Toolbar Buttons with widened dimensions to prevent text clipping
        self.new_file_btn = pygame.Rect(260, y_offset + 6, 130, 30)
        self.save_btn = pygame.Rect(405, y_offset + 6, 130, 30)
        self.delete_btn = pygame.Rect(550, y_offset + 6, 120, 30)

        # Dialog states
        self.close_confirm_dialog = None
        self.new_file_dialog = None
        self.delete_confirm_dialog = None

    def resize(self, width, height):
        self.width = width
        self.height = height
        content_y = self.y_offset + self.toolbar_h + self.tab_bar_h
        self.file_tree.rect.y = content_y
        self.file_tree.rect.height = height - content_y
        self.text_area.rect.y = content_y
        self.text_area.rect.width = width - 250
        self.text_area.rect.height = height - content_y
        self.text_area._update_lines()

    def is_file_modified(self, path):
        if path not in self.file_data: return False
        if 0 <= self.active_tab_idx < len(self.open_files) and self.open_files[self.active_tab_idx] == path:
            return self.text_area.text != self.file_data[path]["saved_content"]
        return self.file_data[path]["content"] != self.file_data[path]["saved_content"]

    def open_file(self, path):
        # Save active tab state before switching
        if 0 <= self.active_tab_idx < len(self.open_files):
            old_path = self.open_files[self.active_tab_idx]
            if old_path in self.file_data:
                self.file_data[old_path]["content"] = self.text_area.text
                self.file_data[old_path]["cursor_pos"] = self.text_area.cursor_pos
                self.file_data[old_path]["scroll_y"] = self.text_area.scroll_y

        if path not in self.open_files:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.open_files.append(path)
                self.file_data[path] = {
                    "content": content,
                    "saved_content": content,
                    "cursor_pos": 0,
                    "scroll_y": 0
                }
            except Exception as e:
                print(f"Error opening file: {e}")
                return
        
        self.active_tab_idx = self.open_files.index(path)
        self._sync_text_area(is_new_open=True)

    def _sync_text_area(self, is_new_open=False):
        if 0 <= self.active_tab_idx < len(self.open_files):
            path = self.open_files[self.active_tab_idx]
            data = self.file_data.get(path)
            if data:
                self.text_area.text = data["content"]
                self.text_area._update_lines()
                # Clear selection & reset cursor on opening a file
                self.text_area.sel_start = None
                self.text_area.dragging = False
                self.text_area.cursor_pos = 0 if is_new_open else data.get("cursor_pos", 0)
                self.text_area.scroll_y = 0 if is_new_open else data.get("scroll_y", 0)
                self.text_area.history = [data["content"]]
                self.text_area.history_index = 0
                self.text_area.active = True
                FocusManager.set_focus(self.text_area)

    def _save_current_file(self):
        if 0 <= self.active_tab_idx < len(self.open_files):
            path = self.open_files[self.active_tab_idx]
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.text_area.text)
                if path in self.file_data:
                    self.file_data[path]["content"] = self.text_area.text
                    self.file_data[path]["saved_content"] = self.text_area.text
                print(f"Saved: {path}")
            except Exception as e:
                print(f"Save error: {e}")

    def request_close_tab(self, idx):
        if not (0 <= idx < len(self.open_files)):
            return
        path = self.open_files[idx]
        if self.is_file_modified(path):
            self.close_confirm_dialog = {
                "idx": idx,
                "path": path,
                "name": os.path.basename(path)
            }
        else:
            self._force_close_tab(idx)

    def _force_close_tab(self, idx):
        path = self.open_files.pop(idx)
        if path in self.file_data:
            del self.file_data[path]
        if self.active_tab_idx == idx:
            self.active_tab_idx = len(self.open_files) - 1 if self.open_files else -1
        elif self.active_tab_idx > idx:
            self.active_tab_idx -= 1
        self._sync_text_area()

    def get_tab_rects(self):
        tab_rects = []
        cur_x = 250 - self.tab_scroll_x
        tabs_y = self.y_offset + self.toolbar_h
        
        for i, path in enumerate(self.open_files):
            fname = os.path.basename(path)
            modified = self.is_file_modified(path)
            display_name = f"*{fname}" if modified else fname
            
            text_w = self.font.size(display_name)[0]
            tab_w = max(90, text_w + 44)
            
            tab_rect = pygame.Rect(cur_x, tabs_y, tab_w, self.tab_bar_h)
            close_rect = pygame.Rect(tab_rect.right - 20, tab_rect.y + 10, 16, 16)
            tab_rects.append({
                "index": i,
                "path": path,
                "rect": tab_rect,
                "close_rect": close_rect,
                "display_name": display_name,
                "modified": modified
            })
            cur_x += tab_w + 2
            
        total_tab_w = (cur_x + self.tab_scroll_x) - 250
        view_w = self.width - 250
        self.max_tab_scroll = max(0, total_tab_w - view_w)
        return tab_rects

    def handle_event(self, event):
        # 1. Unsaved Changes Close Modal
        if self.close_confirm_dialog:
            modal_rect = pygame.Rect(self.width//2 - 280, self.height//2 - 95, 560, 190)
            btn_y = modal_rect.bottom - 46
            save_close_btn = pygame.Rect(modal_rect.x + 20, btn_y, 150, 34)
            close_nosave_btn = pygame.Rect(modal_rect.x + 185, btn_y, 240, 34)
            cancel_btn = pygame.Rect(modal_rect.x + 440, btn_y, 100, 34)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                idx = self.close_confirm_dialog["idx"]
                if save_close_btn.collidepoint(event.pos):
                    self._save_current_file()
                    self._force_close_tab(idx)
                    self.close_confirm_dialog = None
                    return True
                elif close_nosave_btn.collidepoint(event.pos):
                    self._force_close_tab(idx)
                    self.close_confirm_dialog = None
                    return True
                elif cancel_btn.collidepoint(event.pos):
                    self.close_confirm_dialog = None
                    return True
            return True

        # 2. New File Modal with Folder Dropdown
        if self.new_file_dialog:
            modal_rect = pygame.Rect(self.width//2 - 260, self.height//2 - 120, 520, 240)
            create_btn = pygame.Rect(modal_rect.x + 130, modal_rect.bottom - 45, 130, 34)
            cancel_btn = pygame.Rect(modal_rect.x + 280, modal_rect.bottom - 45, 110, 34)

            folder_dd = self.new_file_dialog["folder_dd"]
            name_box = self.new_file_dialog["box"]

            if folder_dd.expanded:
                if folder_dd.handle_event(event):
                    return True

            if folder_dd.handle_event(event):
                return True
            if name_box.handle_event(event):
                return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if create_btn.collidepoint(event.pos):
                    selected_folder = folder_dd.text or self.current_root
                    name = name_box.text.strip()
                    if name:
                        if not name.endswith(('.xml', '.md')):
                            name += ".xml"
                        path = os.path.join(selected_folder, name)
                        if not os.path.exists(path):
                            os.makedirs(os.path.dirname(path), exist_ok=True)
                            with open(path, 'w', encoding='utf-8') as f:
                                f.write("<!-- New Document -->\n" if name.endswith('.xml') else "# New Document\n")
                            self.file_tree.refresh()
                        self.open_file(path)
                    self.new_file_dialog = None
                    return True
                elif cancel_btn.collidepoint(event.pos):
                    self.new_file_dialog = None
                    return True
            return True

        # 3. Delete File Confirm Modal
        if self.delete_confirm_dialog:
            modal_rect = pygame.Rect(self.width//2 - 230, self.height//2 - 85, 460, 170)
            del_yes_btn = pygame.Rect(modal_rect.x + 90, modal_rect.bottom - 45, 130, 34)
            del_no_btn = pygame.Rect(modal_rect.x + 240, modal_rect.bottom - 45, 110, 34)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if del_yes_btn.collidepoint(event.pos):
                    path = self.delete_confirm_dialog["path"]
                    idx = self.delete_confirm_dialog["idx"]
                    if os.path.exists(path):
                        try: os.remove(path)
                        except Exception as e: print(e)
                    self._force_close_tab(idx)
                    self.file_tree.refresh()
                    self.delete_confirm_dialog = None
                    return True
                elif del_no_btn.collidepoint(event.pos):
                    self.delete_confirm_dialog = None
                    return True
            return True

        # Mouse Dragging for Horizontal Tab Scrollbar
        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_tab_scroll = False

        if event.type == pygame.MOUSEMOTION and self.dragging_tab_scroll and self.max_tab_scroll > 0:
            dx = event.pos[0] - self.tab_scroll_start_x
            track_w = self.width - 250
            thumb_w = self.tab_thumb_rect.width if self.tab_thumb_rect else 40
            movable = track_w - thumb_w
            if movable > 0:
                self.tab_scroll_x = max(0, min(self.max_tab_scroll, self.tab_scroll_start_offset + (dx / movable) * self.max_tab_scroll))
            return True

        # Keyboard Shortcut: CTRL+W to close active tab
        if event.type == pygame.KEYDOWN:
            if (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_w:
                if 0 <= self.active_tab_idx < len(self.open_files):
                    self.request_close_tab(self.active_tab_idx)
                    return True

        # Toolbar Actions
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.new_file_btn.collidepoint(event.pos):
                folder_opts = self.file_tree.get_folder_options()
                
                # Determine default folder from current tree selection or root
                default_folder = self.current_root
                if self.file_tree.selected_path:
                    if os.path.isdir(self.file_tree.selected_path):
                        default_folder = self.file_tree.selected_path
                    else:
                        default_folder = os.path.dirname(self.file_tree.selected_path)
                if not os.path.isdir(default_folder):
                    default_folder = self.current_root

                modal_rect = pygame.Rect(self.width//2 - 260, self.height//2 - 120, 520, 240)
                folder_dd = UIDropdown(modal_rect.x + 140, modal_rect.y + 55, 350, 30, self.font, folder_opts, default_folder, searchable=True)
                name_box = UITextBox(modal_rect.x + 140, modal_rect.y + 105, 350, 30, self.font, "new_file.xml")
                name_box.active = True
                FocusManager.set_focus(name_box)
                self.new_file_dialog = {"folder_dd": folder_dd, "box": name_box}
                return True
            elif self.save_btn.collidepoint(event.pos):
                self._save_current_file()
                return True
            elif self.delete_btn.collidepoint(event.pos):
                if 0 <= self.active_tab_idx < len(self.open_files):
                    path = self.open_files[self.active_tab_idx]
                    self.delete_confirm_dialog = {
                        "path": path,
                        "idx": self.active_tab_idx,
                        "name": os.path.basename(path)
                    }
                return True

        # Horizontal Scrollbar interactions on Tabs
        tabs_view_rect = pygame.Rect(250, self.y_offset + self.toolbar_h, self.width - 250, self.tab_bar_h)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if tabs_view_rect.collidepoint(event.pos):
                if event.button == 4:
                    self.tab_scroll_x = max(0, self.tab_scroll_x - 40)
                    return True
                elif event.button == 5:
                    self.tab_scroll_x = min(self.max_tab_scroll, self.tab_scroll_x + 40)
                    return True

            if event.button == 1 and self.tab_thumb_rect and self.tab_thumb_rect.collidepoint(event.pos):
                self.dragging_tab_scroll = True
                self.tab_scroll_start_x = event.pos[0]
                self.tab_scroll_start_offset = self.tab_scroll_x
                return True

            # Tab click / close handling
            if event.button == 1 and tabs_view_rect.collidepoint(event.pos):
                tab_rects = self.get_tab_rects()
                for tab_info in tab_rects:
                    if tab_info["rect"].colliderect(tabs_view_rect):
                        if tab_info["close_rect"].collidepoint(event.pos):
                            self.request_close_tab(tab_info["index"])
                            return True
                        elif tab_info["rect"].collidepoint(event.pos):
                            if self.active_tab_idx != tab_info["index"]:
                                if 0 <= self.active_tab_idx < len(self.open_files):
                                    old_path = self.open_files[self.active_tab_idx]
                                    if old_path in self.file_data:
                                        self.file_data[old_path]["content"] = self.text_area.text
                                self.active_tab_idx = tab_info["index"]
                                self._sync_text_area(is_new_open=False)
                            return True

        # Left File Tree
        if self.file_tree.handle_event(event):
            if self.file_tree.selected_path:
                self.open_file(self.file_tree.selected_path)
            return True

        # Text Area editing
        if self.text_area.handle_event(event):
            if 0 <= self.active_tab_idx < len(self.open_files):
                path = self.open_files[self.active_tab_idx]
                if path in self.file_data:
                    self.file_data[path]["content"] = self.text_area.text
            return True

        return False

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect)

        # 1. Top Toolbar Area
        toolbar_rect = pygame.Rect(0, self.y_offset, self.width, self.toolbar_h)
        pygame.draw.rect(surface, UITheme.PANEL_BG, toolbar_rect)
        pygame.draw.line(surface, UITheme.BORDER, (0, toolbar_rect.bottom - 1), (self.width, toolbar_rect.bottom - 1))

        surface.blit(self.font.render("Code Editor", True, UITheme.WARNING), (20, self.y_offset + 12))
        draw_styled_button(surface, self.new_file_btn, "+ New File", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.save_btn, "Save File", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
        draw_styled_button(surface, self.delete_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

        # 2. Tabs Strip Area
        tabs_y = self.y_offset + self.toolbar_h
        tabs_view_rect = pygame.Rect(250, tabs_y, self.width - 250, self.tab_bar_h)
        pygame.draw.rect(surface, UITheme.PANEL_BG, (0, tabs_y, self.width, self.tab_bar_h))
        pygame.draw.line(surface, UITheme.BORDER, (0, tabs_y + self.tab_bar_h - 1), (self.width, tabs_y + self.tab_bar_h - 1))

        prev_clip = surface.get_clip()
        surface.set_clip(tabs_view_rect.clip(prev_clip) if prev_clip else tabs_view_rect)

        tab_rects = self.get_tab_rects()
        for tab_info in tab_rects:
            tab_rect = tab_info["rect"]
            close_rect = tab_info["close_rect"]
            is_active = (tab_info["index"] == self.active_tab_idx)
            is_modified = tab_info["modified"]
            hovered = tab_rect.collidepoint(mouse_pos)
            
            # Yellow theme when modified
            if is_modified:
                color = (55, 48, 15) if is_active else ((48, 42, 18) if hovered else (38, 35, 18))
                border_color = UITheme.WARNING
                txt_color = UITheme.WARNING
            else:
                color = UITheme.BG if is_active else (UITheme.HOVER_BG if hovered else UITheme.PANEL_BG)
                border_color = UITheme.BORDER
                txt_color = UITheme.TEXT if is_active or hovered else UITheme.TEXT_DIM

            pygame.draw.rect(surface, color, tab_rect)
            pygame.draw.rect(surface, border_color, tab_rect, 1)

            if is_active:
                accent_bar = UITheme.WARNING if is_modified else UITheme.ACCENT
                pygame.draw.rect(surface, accent_bar, (tab_rect.x, tab_rect.y, tab_rect.width, 3))

            txt = self.font.render(tab_info["display_name"], True, txt_color)
            surface.blit(txt, (tab_rect.x + 8, tab_rect.centery - txt.get_height()//2))

            c_hover = close_rect.collidepoint(mouse_pos)
            pygame.draw.rect(surface, UITheme.DANGER if c_hover else border_color, close_rect, border_radius=3)
            surface.blit(self.font.render("x", True, UITheme.TEXT), (close_rect.x + 4, close_rect.y + 1))

        surface.set_clip(prev_clip)

        # Horizontal Scrollbar for Tabs
        if self.max_tab_scroll > 0:
            track_rect = pygame.Rect(250, tabs_y + self.tab_bar_h - 4, self.width - 250, 4)
            pygame.draw.rect(surface, UITheme.PANEL_BG, track_rect)
            thumb_w = max(30, int((tabs_view_rect.width / (tabs_view_rect.width + self.max_tab_scroll)) * track_rect.width))
            thumb_x = track_rect.x + (self.tab_scroll_x / self.max_tab_scroll) * (track_rect.width - thumb_w)
            self.tab_thumb_rect = pygame.Rect(thumb_x, track_rect.y, thumb_w, 4)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.tab_thumb_rect, border_radius=2)
        else:
            self.tab_thumb_rect = None

        # 3. Main Content Area (File Tree & Text Area)
        self.file_tree.draw(surface)
        if self.open_files:
            self.text_area.draw(surface)

        # 4. Modals (Rendered above content)
        if self.close_confirm_dialog:
            self._draw_modal_backdrop(surface)
            modal_rect = pygame.Rect(self.width//2 - 280, self.height//2 - 95, 560, 190)
            self._draw_modal_box(surface, modal_rect, "Unsaved Changes")
            
            msg1 = self.font.render("You have unsaved changes in:", True, UITheme.TEXT)
            msg2 = self.font.render(self.close_confirm_dialog["name"][:45], True, UITheme.WARNING)
            surface.blit(msg1, (modal_rect.x + 25, modal_rect.y + 55))
            surface.blit(msg2, (modal_rect.x + 25, modal_rect.y + 82))

            btn_y = modal_rect.bottom - 46
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 20, btn_y, 150, 34), "Save & Close", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 185, btn_y, 240, 34), "Close Without Save", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 440, btn_y, 100, 34), "Cancel", self.font, mouse_pos, UITheme.BORDER, UITheme.BORDER_ACTIVE)

        if self.new_file_dialog:
            self._draw_modal_backdrop(surface)
            modal_rect = pygame.Rect(self.width//2 - 260, self.height//2 - 120, 520, 240)
            self._draw_modal_box(surface, modal_rect, "Create New File")
            
            surface.blit(self.font.render("Folder:", True, UITheme.TEXT_DIM), (modal_rect.x + 25, modal_rect.y + 60))
            self.new_file_dialog["folder_dd"].draw(surface)

            surface.blit(self.font.render("File Name:", True, UITheme.TEXT_DIM), (modal_rect.x + 25, modal_rect.y + 110))
            self.new_file_dialog["box"].draw(surface)

            btn_y = modal_rect.bottom - 45
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 130, btn_y, 130, 34), "Create", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 280, btn_y, 110, 34), "Cancel", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

            # Draw dropdown overlay list on top of inputs and buttons
            if self.new_file_dialog["folder_dd"].expanded:
                self.new_file_dialog["folder_dd"].draw_list(surface)

        if self.delete_confirm_dialog:
            self._draw_modal_backdrop(surface)
            modal_rect = pygame.Rect(self.width//2 - 230, self.height//2 - 85, 460, 170)
            self._draw_modal_box(surface, modal_rect, "Confirm Delete")
            
            surface.blit(self.font.render("Delete file from disk?", True, UITheme.TEXT), (modal_rect.x + 25, modal_rect.y + 55))
            surface.blit(self.font.render(self.delete_confirm_dialog["name"][:35], True, UITheme.WARNING), (modal_rect.x + 25, modal_rect.y + 80))

            btn_y = modal_rect.bottom - 45
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 90, btn_y, 130, 34), "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 240, btn_y, 110, 34), "Cancel", self.font, mouse_pos, UITheme.BORDER, UITheme.BORDER_ACTIVE)

    def _draw_modal_backdrop(self, surface):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

    def _draw_modal_box(self, surface, rect, title):
        pygame.draw.rect(surface, UITheme.PANEL_BG, rect, border_radius=8)
        pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, rect, 2, border_radius=8)
        surface.blit(self.font.render(title, True, UITheme.WARNING), (rect.x + 20, rect.y + 15))
        pygame.draw.line(surface, UITheme.BORDER, (rect.x, rect.y + 40), (rect.right, rect.y + 40))