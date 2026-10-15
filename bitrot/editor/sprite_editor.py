import os
import pygame
from editor.config import SPRITE_ROOT, TILE_SIZE
from editor.ui import (
    UITextBox, UIDropdown, UITheme, 
    draw_styled_button, FocusManager
)

# 10 Base Colors
BASE_COLORS = [
    (255, 255, 255),  # White
    (50, 50, 50),     # Black
    (220, 50, 50),    # Red
    (50, 200, 50),    # Green
    (50, 50, 220),    # Blue
    (220, 220, 50),   # Yellow
    (255, 105, 180),  # Pink
    (255, 165, 0),    # Orange
    (139, 69, 19),    # Brown
    (128, 128, 128)   # Gray
]

def generate_palette():
    """Generates 5 tone variations for each of the 10 base colors."""
    palette = []
    for r, g, b in BASE_COLORS:
        tones = []
        if (r, g, b) == (255, 255, 255):
            tones = [(100, 100, 100), (140, 140, 140), (180, 180, 180), (220, 220, 220), (255, 255, 255)]
        elif (r, g, b) == (50, 50, 50):
            tones = [(15, 15, 15), (30, 30, 30), (50, 50, 50), (75, 75, 75), (105, 105, 105)]
        else:
            factors = [0.4, 0.7, 1.0, 1.3, 1.6]
            for f in factors:
                if f <= 1.0:
                    tr = max(0, min(255, int(r * f)))
                    tg = max(0, min(255, int(g * f)))
                    tb = max(0, min(255, int(b * f)))
                else:
                    tint = f - 1.0
                    tr = max(0, min(255, int(r + (255 - r) * tint)))
                    tg = max(0, min(255, int(g + (255 - g) * tint)))
                    tb = max(0, min(255, int(b + (255 - b) * tint)))
                tones.append((tr, tg, tb))
        palette.append(tones)
    return palette

PALETTE_GRID = generate_palette()

class SpriteEditor:
    def __init__(self, y_offset, width, height, font):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        
        self.sprite_root = SPRITE_ROOT
        if not os.path.exists(self.sprite_root):
            try: os.makedirs(self.sprite_root)
            except: pass

        self.toolbar_h = 42
        self.tab_bar_h = 36
        self.sidebar_w = 280
        self.palette_panel_w = 280
        self.canvas_size = 16

        # Robust category path resolution checking both singular and plural forms
        self.categories = self._resolve_categories()
        self.active_category = "Items" if "Items" in self.categories else list(self.categories.keys())[0]
        self.files = []

        # Tabs
        self.open_tabs = []
        self.active_tab_idx = -1
        self.tab_scroll_x = 0
        self.max_tab_scroll = 0
        self.dragging_tab_scroll = False
        self.tab_scroll_start_x = 0
        self.tab_scroll_start_offset = 0
        self.tab_thumb_rect = None
        self.close_confirm_dialog = None
        self.new_sprite_dialog = None

        # Sidebar Controls
        cat_opts = [{"label": c, "value": c} for c in self.categories.keys()]
        self.category_dropdown = UIDropdown(10, self.y_offset + 38, self.sidebar_w - 20, 30, self.font, cat_opts, self.active_category)
        self.search_input = UITextBox(10, self.y_offset + 74, self.sidebar_w - 20, 28, self.font, "")
        self.new_btn = pygame.Rect(10, self.y_offset + 108, self.sidebar_w - 20, 30)

        self.sidebar_scroll = 0
        self.max_sidebar_scroll = 0
        self.dragging_sidebar = False
        self.sidebar_start_y = 0
        self.sidebar_start_offset = 0
        self.sidebar_thumb_rect = None

        # Zoom & Pan State
        self.zoom_levels = [4.0, 8.0, 12.0, 16.0, 20.0, 24.0, 32.0, 40.0]
        self.zoom_idx = 4
        self.pan_x = 0
        self.pan_y = 0
        self.dragging_pan = False
        self.pan_start = (0, 0)
        self.drawing_stroke = False

        # Tools: "pencil", "fill", "eraser", "select"
        self.tool = "pencil"
        self.selected_color = (220, 50, 50)
        self.palette = PALETTE_GRID

        # Selection, Copy & Paste state
        self.sel_rect = None
        self.sel_start = None
        self.is_selecting = False
        self.clipboard_surf = None

        # Top Toolbar Buttons
        self.save_btn = pygame.Rect(self.sidebar_w + 10, y_offset + 6, 110, 30)
        self.undo_btn = pygame.Rect(self.sidebar_w + 128, y_offset + 6, 70, 30)
        self.redo_btn = pygame.Rect(self.sidebar_w + 206, y_offset + 6, 70, 30)
        
        # Tool selectors: Pencil, Fill, Eraser, Select, Copy, Paste
        self.tool_pencil_btn = pygame.Rect(self.sidebar_w + 284, y_offset + 6, 80, 30)
        self.tool_fill_btn = pygame.Rect(self.sidebar_w + 372, y_offset + 6, 70, 30)
        self.tool_eraser_btn = pygame.Rect(self.sidebar_w + 450, y_offset + 6, 80, 30)
        self.tool_select_btn = pygame.Rect(self.sidebar_w + 538, y_offset + 6, 80, 30)
        self.tool_copy_btn = pygame.Rect(self.sidebar_w + 626, y_offset + 6, 70, 30)
        self.tool_paste_btn = pygame.Rect(self.sidebar_w + 704, y_offset + 6, 70, 30)

        self.refresh_file_list()
        if self.files:
            self.open_tab_sprite(os.path.join(self.categories[self.active_category], self.files[0]))

    def _resolve_categories(self):
        """Scans and resolves directory paths supporting singular/plural folder variants."""
        aliases = [
            ("Items", ["items", "item"]),
            ("Clothes", ["clothes", "cloth"]),
            ("Map", ["map", "maps"]),
            ("Zombie", ["zombie", "zombies"]),
            ("Player", ["player", "players"]),
            ("NPC", ["npc", "npcs"]),
            ("Animals", ["animals", "animal"]),
            ("Vehicle", ["vehicle", "vehicles"]),
        ]
        resolved = {}
        for label, variants in aliases:
            for v in variants:
                p = os.path.join(self.sprite_root, v)
                if os.path.exists(p) and os.path.isdir(p):
                    resolved[label] = p
                    break
            if label not in resolved:
                p = os.path.join(self.sprite_root, variants[0])
                os.makedirs(p, exist_ok=True)
                resolved[label] = p

        # Dynamically discover any other folders in SPRITE_ROOT
        if os.path.exists(self.sprite_root):
            for entry in sorted(os.listdir(self.sprite_root)):
                full_p = os.path.join(self.sprite_root, entry)
                if os.path.isdir(full_p):
                    lbl = entry.capitalize()
                    if lbl not in resolved:
                        resolved[lbl] = full_p
        return resolved

    def resize(self, width, height):
        self.width = width
        self.height = height

    def refresh_file_list(self):
        """Recursively scans the active category using os.walk to find all PNGs in subdirectories."""
        cat_dir = self.categories[self.active_category]
        self.files = []
        if cat_dir and os.path.exists(cat_dir):
            for root, dirs, files in os.walk(cat_dir):
                for f in sorted(files):
                    if f.lower().endswith('.png'):
                        full_p = os.path.join(root, f)
                        rel_p = os.path.relpath(full_p, cat_dir).replace('\\', '/')
                        self.files.append(rel_p)

    @property
    def filtered_files(self):
        query = self.search_input.text.strip().lower()
        if not query: return self.files
        return [f for f in self.files if query in f.lower()]

    def get_current_tab(self):
        if 0 <= self.active_tab_idx < len(self.open_tabs):
            return self.open_tabs[self.active_tab_idx]
        return None

    def create_tab(self, path, surface=None):
        if surface is None:
            if os.path.exists(path):
                try:
                    loaded = pygame.image.load(path).convert_alpha()
                    if loaded.get_size() != (16, 16):
                        loaded = pygame.transform.scale(loaded, (16, 16))
                    surf = loaded
                except:
                    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            else:
                surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        else:
            surf = surface

        return {
            "path": path,
            "name": os.path.basename(path),
            "surf": surf,
            "undo_stack": [surf.copy()],
            "redo_stack": [],
            "saved_snapshot": pygame.image.tostring(surf, 'RGBA')
        }

    def open_tab_sprite(self, path):
        for i, tab in enumerate(self.open_tabs):
            if tab["path"] == path:
                self.active_tab_idx = i
                self.ensure_tab_visible(i)
                self.center_canvas()
                return

        tab = self.create_tab(path)
        self.open_tabs.append(tab)
        self.active_tab_idx = len(self.open_tabs) - 1
        self.ensure_tab_visible(self.active_tab_idx)
        self.center_canvas()

    def is_tab_modified(self, tab):
        if not tab.get("saved_snapshot"): return False
        return pygame.image.tostring(tab["surf"], 'RGBA') != tab["saved_snapshot"]

    def request_close_tab(self, idx):
        if not (0 <= idx < len(self.open_tabs)): return
        tab = self.open_tabs[idx]
        if self.is_tab_modified(tab):
            self.close_confirm_dialog = {"idx": idx, "name": tab["name"]}
        else:
            self._force_close_tab(idx)

    def _force_close_tab(self, idx):
        self.open_tabs.pop(idx)
        if not self.open_tabs:
            self.active_tab_idx = -1
        elif self.active_tab_idx == idx:
            self.active_tab_idx = max(0, idx - 1)
        elif self.active_tab_idx > idx:
            self.active_tab_idx -= 1
        self.ensure_tab_visible(self.active_tab_idx)
        self.center_canvas()

    def center_canvas(self):
        canvas_view_w = self.width - self.sidebar_w - self.palette_panel_w
        canvas_view_h = self.height - self.y_offset - self.toolbar_h - self.tab_bar_h
        scale = self.zoom_levels[self.zoom_idx]
        self.pan_x = self.sidebar_w + (canvas_view_w - 16 * scale) // 2
        self.pan_y = self.y_offset + self.toolbar_h + self.tab_bar_h + (canvas_view_h - 16 * scale) // 2

    def save_current_tab(self):
        tab = self.get_current_tab()
        if not tab or not tab["path"]: return
        try:
            os.makedirs(os.path.dirname(tab["path"]), exist_ok=True)
            pygame.image.save(tab["surf"], tab["path"])
            tab["saved_snapshot"] = pygame.image.tostring(tab["surf"], 'RGBA')
            self.refresh_file_list()
        except Exception as e:
            print(f"Error saving sprite: {e}")

    def undo_current(self):
        tab = self.get_current_tab()
        if not tab or len(tab["undo_stack"]) <= 1: return
        last = tab["undo_stack"].pop()
        tab["redo_stack"].append(last)
        tab["surf"].blit(tab["undo_stack"][-1], (0, 0))

    def redo_current(self):
        tab = self.get_current_tab()
        if not tab or not tab["redo_stack"]: return
        nxt = tab["redo_stack"].pop()
        tab["undo_stack"].append(nxt)
        tab["surf"].blit(nxt, (0, 0))

    def push_undo_state(self):
        tab = self.get_current_tab()
        if not tab: return
        tab["undo_stack"].append(tab["surf"].copy())
        if len(tab["undo_stack"]) > 50:
            tab["undo_stack"].pop(0)
        tab["redo_stack"].clear()

    def flood_fill(self, surf, start_x, start_y, fill_color):
        target_color = surf.get_at((start_x, start_y))
        if target_color == fill_color: return
        self.push_undo_state()
        queue = [(start_x, start_y)]
        visited = set([(start_x, start_y)])
        while queue:
            cx, cy = queue.pop(0)
            surf.set_at((cx, cy), fill_color)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < 16 and 0 <= ny < 16 and (nx, ny) not in visited:
                    if surf.get_at((nx, ny)) == target_color:
                        visited.add((nx, ny))
                        queue.append((nx, ny))

    def copy_selection(self):
        tab = self.get_current_tab()
        if not tab or not self.sel_rect: return
        rect = self.sel_rect.clip(pygame.Rect(0, 0, 16, 16))
        if rect.width <= 0 or rect.height <= 0: return
        self.clipboard_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        self.clipboard_surf.blit(tab["surf"], (0, 0), rect)

    def paste_selection(self):
        tab = self.get_current_tab()
        if not tab or not self.clipboard_surf: return
        self.push_undo_state()
        px = self.sel_rect.x if self.sel_rect else 0
        py = self.sel_rect.y if self.sel_rect else 0
        tab["surf"].blit(self.clipboard_surf, (px, py))
        w, h = self.clipboard_surf.get_size()
        self.sel_rect = pygame.Rect(px, py, w, h)

    def apply_pixel_draw(self, px, py, is_first=False):
        tab = self.get_current_tab()
        if not tab or not (0 <= px < 16 and 0 <= py < 16): return

        if self.tool == "fill" and is_first:
            self.flood_fill(tab["surf"], px, py, (*self.selected_color, 255))
            return

        if self.tool in ["pencil", "eraser"]:
            color = (*self.selected_color, 255) if self.tool == "pencil" else (0, 0, 0, 0)
            if tab["surf"].get_at((px, py)) != color:
                if is_first:
                    self.push_undo_state()
                tab["surf"].set_at((px, py), color)

    def get_swatch_rect(self, col_idx, row_idx):
        palette_x = self.width - self.palette_panel_w
        start_y = self.y_offset + self.toolbar_h + 50
        swatch_w = 40
        swatch_h = 24
        spacing_x = 8
        spacing_y = 5
        x = palette_x + 20 + row_idx * (swatch_w + spacing_x)
        y = start_y + col_idx * (swatch_h + spacing_y)
        return pygame.Rect(x, y, swatch_w, swatch_h)

    def ensure_tab_visible(self, idx):
        if not (0 <= idx < len(self.open_tabs)): return
        start_x = self.sidebar_w
        view_w = self.width - start_x - self.palette_panel_w
        rel_x = 0
        target_left, target_right = 0, 0

        for i, tab in enumerate(self.open_tabs):
            display_name = f"*{tab['name']}" if self.is_tab_modified(tab) else tab['name']
            tab_w = max(90, self.font.size(display_name)[0] + 44)
            if i == idx:
                target_left, target_right = rel_x, rel_x + tab_w
            rel_x += tab_w + 2

        self.max_tab_scroll = max(0, rel_x - view_w)
        if target_right > self.tab_scroll_x + view_w:
            self.tab_scroll_x = (target_right + 15) - view_w
        elif target_left < self.tab_scroll_x:
            self.tab_scroll_x = max(0, target_left - 15)
        self.tab_scroll_x = max(0, min(self.max_tab_scroll, self.tab_scroll_x))

    def get_tab_rects(self):
        tab_rects = []
        cur_x = self.sidebar_w - self.tab_scroll_x
        tabs_y = self.y_offset + self.toolbar_h
        for i, tab in enumerate(self.open_tabs):
            display_name = f"*{tab['name']}" if self.is_tab_modified(tab) else tab['name']
            tab_w = max(90, self.font.size(display_name)[0] + 44)
            t_rect = pygame.Rect(cur_x, tabs_y, tab_w, self.tab_bar_h)
            c_rect = pygame.Rect(t_rect.right - 20, t_rect.y + 10, 16, 16)
            tab_rects.append({"index": i, "tab": tab, "rect": t_rect, "close_rect": c_rect, "display_name": display_name})
            cur_x += tab_w + 2
        view_w = self.width - self.sidebar_w - self.palette_panel_w
        self.max_tab_scroll = max(0, (cur_x + self.tab_scroll_x) - self.sidebar_w - view_w)
        return tab_rects

    def handle_event(self, event):
        # 1. Modals
        if self.close_confirm_dialog:
            modal_rect = pygame.Rect(self.width//2 - 280, self.height//2 - 95, 560, 190)
            btn_y = modal_rect.bottom - 46
            save_close_btn = pygame.Rect(modal_rect.x + 20, btn_y, 150, 34)
            close_nosave_btn = pygame.Rect(modal_rect.x + 185, btn_y, 240, 34)
            cancel_btn = pygame.Rect(modal_rect.x + 440, btn_y, 100, 34)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                idx = self.close_confirm_dialog["idx"]
                if save_close_btn.collidepoint(event.pos):
                    self.save_current_tab()
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

        if self.new_sprite_dialog:
            modal_rect = pygame.Rect(self.width//2 - 260, self.height//2 - 120, 520, 240)
            create_btn = pygame.Rect(modal_rect.x + 130, modal_rect.bottom - 45, 130, 34)
            cancel_btn = pygame.Rect(modal_rect.x + 280, modal_rect.bottom - 45, 110, 34)
            f_dd = self.new_sprite_dialog["folder_dd"]
            n_box = self.new_sprite_dialog["box"]

            if f_dd.expanded and f_dd.handle_event(event): return True
            if f_dd.handle_event(event): return True
            if n_box.handle_event(event): return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if create_btn.collidepoint(event.pos):
                    folder = f_dd.text or self.categories[self.active_category]
                    name = n_box.text.strip()
                    if name:
                        if not name.lower().endswith('.png'): name += ".png"
                        full_p = os.path.join(folder, name)
                        new_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
                        try:
                            os.makedirs(os.path.dirname(full_p), exist_ok=True)
                            pygame.image.save(new_surf, full_p)
                        except: pass
                        self.refresh_file_list()
                        self.open_tab_sprite(full_p)
                    self.new_sprite_dialog = None
                    return True
                elif cancel_btn.collidepoint(event.pos):
                    self.new_sprite_dialog = None
                    return True
            return True

        # Keyboard Shortcuts
        if event.type == pygame.KEYDOWN:
            ctrl = (event.mod & pygame.KMOD_CTRL)
            shift = (event.mod & pygame.KMOD_SHIFT)
            if ctrl and event.key == pygame.K_s:
                self.save_current_tab()
                return True
            elif ctrl and event.key == pygame.K_w:
                if 0 <= self.active_tab_idx < len(self.open_tabs):
                    self.request_close_tab(self.active_tab_idx)
                    return True
            elif ctrl and not shift and event.key == pygame.K_z:
                self.undo_current()
                return True
            elif ctrl and (event.key == pygame.K_y or (shift and event.key == pygame.K_z)):
                self.redo_current()
                return True
            elif ctrl and event.key == pygame.K_c:
                self.copy_selection()
                return True
            elif ctrl and event.key == pygame.K_v:
                self.paste_selection()
                return True
            elif event.key == pygame.K_ESCAPE:
                self.sel_rect = None
                return True

        # Sidebar Category Dropdown
        if self.category_dropdown.expanded:
            if self.category_dropdown.handle_event(event):
                if self.category_dropdown.text != self.active_category:
                    self.active_category = self.category_dropdown.text
                    self.search_input.text = ""
                    self.sidebar_scroll = 0
                    self.refresh_file_list()
                return True

        if self.category_dropdown.handle_event(event): return True

        # Top Toolbar Actions
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.save_btn.collidepoint(event.pos):
                self.save_current_tab()
                return True
            elif self.undo_btn.collidepoint(event.pos):
                self.undo_current()
                return True
            elif self.redo_btn.collidepoint(event.pos):
                self.redo_current()
                return True
            elif self.tool_pencil_btn.collidepoint(event.pos):
                self.tool = "pencil"
                self.sel_rect = None
                return True
            elif self.tool_fill_btn.collidepoint(event.pos):
                self.tool = "fill"
                self.sel_rect = None
                return True
            elif self.tool_eraser_btn.collidepoint(event.pos):
                self.tool = "eraser"
                self.sel_rect = None
                return True
            elif self.tool_select_btn.collidepoint(event.pos):
                self.tool = "select"
                return True
            elif self.tool_copy_btn.collidepoint(event.pos):
                self.copy_selection()
                return True
            elif self.tool_paste_btn.collidepoint(event.pos):
                self.paste_selection()
                return True

        # Palette Clicks
        palette_x = self.width - self.palette_panel_w
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and event.pos[0] >= palette_x:
            for col_idx, tones in enumerate(self.palette):
                for row_idx, tone in enumerate(tones):
                    rect = self.get_swatch_rect(col_idx, row_idx)
                    if rect.collidepoint(event.pos):
                        self.selected_color = tone
                        if self.tool in ["eraser", "select"]: self.tool = "pencil"
                        return True

        # Tab Strip Interaction
        tabs_w = self.width - self.sidebar_w - self.palette_panel_w
        tabs_rect = pygame.Rect(self.sidebar_w, self.y_offset + self.toolbar_h, tabs_w, self.tab_bar_h)
        if event.type == pygame.MOUSEBUTTONDOWN and tabs_rect.collidepoint(event.pos):
            if event.button == 4:
                self.tab_scroll_x = max(0, self.tab_scroll_x - 40)
                return True
            elif event.button == 5:
                self.tab_scroll_x = min(self.max_tab_scroll, self.tab_scroll_x + 40)
                return True
            elif event.button == 1:
                tab_rects = self.get_tab_rects()
                for t_info in tab_rects:
                    if t_info["close_rect"].collidepoint(event.pos):
                        self.request_close_tab(t_info["index"])
                        return True
                    elif t_info["rect"].collidepoint(event.pos):
                        self.active_tab_idx = t_info["index"]
                        self.center_canvas()
                        return True

        # Sidebar Search & Dragging
        if self.search_input.handle_event(event):
            list_h = self.height - self.y_offset - 145
            self.max_sidebar_scroll = max(0, len(self.filtered_files) * 26 + 10 - list_h)
            self.sidebar_scroll = max(0, min(self.sidebar_scroll, self.max_sidebar_scroll))
            return True

        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_sidebar = False
            self.dragging_pan = False
            self.drawing_stroke = False
            self.is_selecting = False

        if event.type == pygame.MOUSEMOTION:
            if self.dragging_sidebar and self.sidebar_thumb_rect and self.max_sidebar_scroll > 0:
                dy = event.pos[1] - self.sidebar_start_y
                list_h = self.height - self.y_offset - 145
                thumb_h = self.sidebar_thumb_rect.height
                track_space = list_h - thumb_h
                if track_space > 0:
                    self.sidebar_scroll = max(0, min(self.max_sidebar_scroll, self.sidebar_start_offset + dy * (self.max_sidebar_scroll / track_space)))
                return True

        sidebar_list_rect = pygame.Rect(0, self.y_offset + 145, self.sidebar_w, self.height - self.y_offset - 145)
        if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] < self.sidebar_w:
            if event.button == 4:
                self.sidebar_scroll = max(0, self.sidebar_scroll - 30)
                return True
            elif event.button == 5:
                self.sidebar_scroll = min(self.max_sidebar_scroll, self.sidebar_scroll + 30)
                return True
            elif event.button == 1:
                if self.sidebar_thumb_rect and self.sidebar_thumb_rect.collidepoint(event.pos):
                    self.dragging_sidebar = True
                    self.sidebar_start_y = event.pos[1]
                    self.sidebar_start_offset = self.sidebar_scroll
                    return True
                if self.new_btn.collidepoint(event.pos):
                    folder_opts = [{"label": c, "value": p} for c, p in self.categories.items()]
                    modal_rect = pygame.Rect(self.width//2 - 260, self.height//2 - 120, 520, 240)
                    f_dd = UIDropdown(modal_rect.x + 130, modal_rect.y + 55, 360, 30, self.font, folder_opts, self.categories[self.active_category], searchable=True)
                    n_box = UITextBox(modal_rect.x + 130, modal_rect.y + 105, 360, 30, self.font, "new_sprite.png")
                    n_box.active = True
                    FocusManager.set_focus(n_box)
                    self.new_sprite_dialog = {"folder_dd": f_dd, "box": n_box}
                    return True

                list_y = sidebar_list_rect.y + 5 - self.sidebar_scroll
                for fname in self.filtered_files:
                    r = pygame.Rect(10, list_y, self.sidebar_w - 24, 24)
                    if r.collidepoint(event.pos):
                        self.open_tab_sprite(os.path.join(self.categories[self.active_category], fname))
                        return True
                    list_y += 26

        # Canvas Interactions
        canvas_rect = pygame.Rect(self.sidebar_w, self.y_offset + self.toolbar_h + self.tab_bar_h, self.width - self.sidebar_w - self.palette_panel_w, self.height - self.y_offset - self.toolbar_h - self.tab_bar_h)
        if event.type == pygame.MOUSEBUTTONDOWN and canvas_rect.collidepoint(event.pos):
            scale = self.zoom_levels[self.zoom_idx]
            px = int((event.pos[0] - self.pan_x) // scale)
            py = int((event.pos[1] - self.pan_y) // scale)

            if event.button == 3:  # Pan
                self.dragging_pan = True
                self.pan_start = event.pos
                return True
            elif event.button in (4, 5):  # Smooth Zoom toward mouse
                old_zoom = self.zoom_levels[self.zoom_idx]
                if event.button == 4:
                    self.zoom_idx = min(len(self.zoom_levels) - 1, self.zoom_idx + 1)
                else:
                    self.zoom_idx = max(0, self.zoom_idx - 1)
                new_zoom = self.zoom_levels[self.zoom_idx]
                mx, my = event.pos
                self.pan_x = mx - (mx - self.pan_x) * (new_zoom / old_zoom)
                self.pan_y = my - (my - self.pan_y) * (new_zoom / old_zoom)
                return True
            elif event.button == 1:
                if self.tool == "select":
                    self.is_selecting = True
                    c_px = max(0, min(15, px))
                    c_py = max(0, min(15, py))
                    self.sel_start = (c_px, c_py)
                    self.sel_rect = pygame.Rect(c_px, c_py, 1, 1)
                    return True
                else:
                    self.drawing_stroke = True
                    self.apply_pixel_draw(px, py, is_first=True)
                    return True

        if event.type == pygame.MOUSEMOTION:
            scale = self.zoom_levels[self.zoom_idx]
            px = int((event.pos[0] - self.pan_x) // scale)
            py = int((event.pos[1] - self.pan_y) // scale)

            if self.dragging_pan:
                dx = event.pos[0] - self.pan_start[0]
                dy = event.pos[1] - self.pan_start[1]
                self.pan_x += dx
                self.pan_y += dy
                self.pan_start = event.pos
                return True
            elif self.is_selecting and pygame.mouse.get_pressed()[0]:
                x1, y1 = self.sel_start
                x2, y2 = max(0, min(15, px)), max(0, min(15, py))
                self.sel_rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1) + 1, abs(y2 - y1) + 1)
                return True
            elif self.drawing_stroke and pygame.mouse.get_pressed()[0]:
                self.apply_pixel_draw(px, py, is_first=False)
                return True

        return False

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect)

        # 1. Top Toolbar (Pencil, Fill, Eraser, Select, Copy, Paste)
        toolbar_rect = pygame.Rect(0, self.y_offset, self.width, self.toolbar_h)
        pygame.draw.rect(surface, UITheme.PANEL_BG, toolbar_rect)
        pygame.draw.line(surface, UITheme.BORDER, (0, toolbar_rect.bottom - 1), (self.width, toolbar_rect.bottom - 1))
        surface.blit(self.font.render("Art", True, UITheme.WARNING), (20, self.y_offset + 12))

        draw_styled_button(surface, self.save_btn, "Save PNG", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
        draw_styled_button(surface, self.undo_btn, "Undo", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)
        draw_styled_button(surface, self.redo_btn, "Redo", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)

        draw_styled_button(surface, self.tool_pencil_btn, "Pencil", self.font, mouse_pos, UITheme.ACCENT if self.tool == "pencil" else UITheme.PANEL_BG, UITheme.ACCENT_HOVER)
        draw_styled_button(surface, self.tool_fill_btn, "Fill", self.font, mouse_pos, UITheme.ACCENT if self.tool == "fill" else UITheme.PANEL_BG, UITheme.ACCENT_HOVER)
        draw_styled_button(surface, self.tool_eraser_btn, "Eraser", self.font, mouse_pos, UITheme.DANGER if self.tool == "eraser" else UITheme.PANEL_BG, UITheme.DANGER_HOVER)
        draw_styled_button(surface, self.tool_select_btn, "Select", self.font, mouse_pos, UITheme.WARNING if self.tool == "select" else UITheme.PANEL_BG, UITheme.WARNING_HOVER)
        draw_styled_button(surface, self.tool_copy_btn, "Copy", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)
        draw_styled_button(surface, self.tool_paste_btn, "Paste", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)

        zoom_text = f"Zoom: {int(self.zoom_levels[self.zoom_idx])}x"
        surface.blit(self.font.render(zoom_text, True, UITheme.TEXT_DIM), (self.sidebar_w + 785, self.y_offset + 12))

        # 2. Left Sidebar (Folder Dropdown, Search, New Button, Files)
        sidebar_rect = pygame.Rect(0, self.y_offset + self.toolbar_h, self.sidebar_w, self.height - self.y_offset - self.toolbar_h)
        pygame.draw.rect(surface, UITheme.PANEL_BG, sidebar_rect)
        pygame.draw.line(surface, UITheme.BORDER, (sidebar_rect.right - 1, sidebar_rect.top), (sidebar_rect.right - 1, sidebar_rect.bottom))
        
        self.category_dropdown.draw(surface)
        self.search_input.draw(surface)
        if not self.search_input.text and not self.search_input.active:
            surface.blit(self.font.render("Search sprites...", True, UITheme.TEXT_DIM), (self.search_input.rect.x + 6, self.search_input.rect.y + 6))
        draw_styled_button(surface, self.new_btn, "+ New Sprite", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)

        list_clip = pygame.Rect(0, self.y_offset + 145, self.sidebar_w, self.height - self.y_offset - 145)
        surface.set_clip(list_clip)
        
        active_tab = self.get_current_tab()
        active_path = active_tab["path"] if active_tab else None
        
        list_y = list_clip.y + 5 - self.sidebar_scroll
        for fname in self.filtered_files:
            full_p = os.path.join(self.categories[self.active_category], fname)
            r = pygame.Rect(8, list_y, self.sidebar_w - 20, 24)
            if full_p == active_path:
                pygame.draw.rect(surface, UITheme.LIST_HOVER, r, border_radius=4)
            elif r.collidepoint(mouse_pos):
                pygame.draw.rect(surface, UITheme.HOVER_BG, r, border_radius=4)
            surface.blit(self.font.render(fname[:25], True, UITheme.TEXT), (14, list_y + 4))
            list_y += 26
        surface.set_clip(None)

        # 3. Sidebar Scrollbar Track and Thumb
        self.max_sidebar_scroll = max(0, len(self.filtered_files) * 26 + 10 - list_clip.height)
        if self.max_sidebar_scroll > 0:
            track_rect = pygame.Rect(self.sidebar_w - 8, list_clip.y, 8, list_clip.height)
            content_h = len(self.filtered_files) * 26 + 10
            thumb_h = max(20, int((list_clip.height / content_h) * list_clip.height))
            thumb_y = list_clip.y + (self.sidebar_scroll / self.max_sidebar_scroll) * (list_clip.height - thumb_h)
            self.sidebar_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.sidebar_thumb_rect, border_radius=4)
        else:
            self.sidebar_thumb_rect = None

        # 4. Tab Bar
        tabs_y = self.y_offset + self.toolbar_h
        tabs_w = self.width - self.sidebar_w - self.palette_panel_w
        tabs_view_rect = pygame.Rect(self.sidebar_w, tabs_y, tabs_w, self.tab_bar_h)
        pygame.draw.rect(surface, UITheme.PANEL_BG, tabs_view_rect)
        pygame.draw.line(surface, UITheme.BORDER, (tabs_view_rect.left, tabs_view_rect.bottom - 1), (tabs_view_rect.right, tabs_view_rect.bottom - 1))

        prev_clip = surface.get_clip()
        surface.set_clip(tabs_view_rect.clip(prev_clip) if prev_clip else tabs_view_rect)

        tab_rects = self.get_tab_rects()
        for t_info in tab_rects:
            tab_rect = t_info["rect"]
            close_rect = t_info["close_rect"]
            is_active = (t_info["index"] == self.active_tab_idx)
            is_mod = self.is_tab_modified(t_info["tab"])
            hovered = tab_rect.collidepoint(mouse_pos)

            if is_mod:
                col = (55, 48, 15) if is_active else ((48, 42, 18) if hovered else (38, 35, 18))
                b_col = UITheme.WARNING
                txt_col = UITheme.WARNING
            else:
                col = UITheme.BG if is_active else (UITheme.HOVER_BG if hovered else UITheme.PANEL_BG)
                b_col = UITheme.BORDER
                txt_col = UITheme.TEXT if is_active or hovered else UITheme.TEXT_DIM

            pygame.draw.rect(surface, col, tab_rect)
            pygame.draw.rect(surface, b_col, tab_rect, 1)

            if is_active:
                pygame.draw.rect(surface, UITheme.WARNING if is_mod else UITheme.ACCENT, (tab_rect.x, tab_rect.y, tab_rect.width, 3))

            txt = self.font.render(t_info["display_name"], True, txt_col)
            surface.blit(txt, (tab_rect.x + 8, tab_rect.centery - txt.get_height()//2))

            c_hover = close_rect.collidepoint(mouse_pos)
            pygame.draw.rect(surface, UITheme.DANGER if c_hover else b_col, close_rect, border_radius=3)
            surface.blit(self.font.render("x", True, UITheme.TEXT), (close_rect.x + 4, close_rect.y + 1))

        surface.set_clip(prev_clip)

        # 5. Right Palette Bar
        palette_x = self.width - self.palette_panel_w
        palette_panel_y = tabs_y
        palette_rect = pygame.Rect(palette_x, palette_panel_y, self.palette_panel_w, self.height - palette_panel_y)
        pygame.draw.rect(surface, UITheme.PANEL_BG, palette_rect)
        pygame.draw.line(surface, UITheme.BORDER, (palette_rect.left, palette_rect.top), (palette_rect.left, palette_rect.bottom))

        surface.blit(self.font.render("Selected:", True, UITheme.TEXT_DIM), (palette_x + 20, palette_panel_y + 14))
        cur_swatch = pygame.Rect(palette_x + 180, palette_panel_y + 10, 75, 26)
        if self.tool == "eraser":
            pygame.draw.rect(surface, UITheme.DANGER, cur_swatch, border_radius=4)
            surface.blit(self.font.render("Eraser", True, UITheme.TEXT), (cur_swatch.x + 8, cur_swatch.y + 5))
        else:
            pygame.draw.rect(surface, self.selected_color, cur_swatch, border_radius=4)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, cur_swatch, 1, border_radius=4)

        for col_idx, tones in enumerate(self.palette):
            for row_idx, tone in enumerate(tones):
                rect = self.get_swatch_rect(col_idx, row_idx)
                pygame.draw.rect(surface, tone, rect, border_radius=3)
                if self.selected_color == tone and self.tool not in ["eraser", "select"]:
                    pygame.draw.rect(surface, (255, 255, 255), rect, 2, border_radius=3)
                else:
                    pygame.draw.rect(surface, (45, 45, 50), rect, 1, border_radius=3)

        # Previews (1x, 2x, 4x)
        preview_y = palette_panel_y + 50 + 10 * 29 + 15
        surface.blit(self.font.render("Preview (1x, 2x, 4x):", True, UITheme.WARNING), (palette_x + 20, preview_y))
        
        tab = self.get_current_tab()
        if tab:
            p_surf = tab["surf"]
            p_box = pygame.Rect(palette_x + 20, preview_y + 25, 64, 64)
            pygame.draw.rect(surface, (26, 26, 28), p_box)
            pygame.draw.rect(surface, UITheme.BORDER, p_box, 1)
            surface.blit(pygame.transform.scale(p_surf, (64, 64)), (p_box.x, p_box.y))

            p_box32 = pygame.Rect(palette_x + 105, preview_y + 25, 32, 32)
            pygame.draw.rect(surface, (26, 26, 28), p_box32)
            pygame.draw.rect(surface, UITheme.BORDER, p_box32, 1)
            surface.blit(pygame.transform.scale(p_surf, (32, 32)), (p_box32.x, p_box32.y))

            p_box16 = pygame.Rect(palette_x + 160, preview_y + 25, 16, 16)
            pygame.draw.rect(surface, (26, 26, 28), p_box16)
            pygame.draw.rect(surface, UITheme.BORDER, p_box16, 1)
            surface.blit(p_surf, (p_box16.x, p_box16.y))

        # 6. Canvas Drawing Area (Clear Outline, No Alternating Transparency Colors)
        canvas_view = pygame.Rect(self.sidebar_w, tabs_y + self.tab_bar_h, self.width - self.sidebar_w - self.palette_panel_w, self.height - tabs_y - self.tab_bar_h)
        surface.set_clip(canvas_view)

        if tab:
            scale = self.zoom_levels[self.zoom_idx]
            canvas_w = int(16 * scale)
            canvas_h = int(16 * scale)

            canvas_rect_screen = pygame.Rect(self.pan_x, self.pan_y, canvas_w, canvas_h)
            pygame.draw.rect(surface, (26, 26, 28), canvas_rect_screen)

            for cx in range(16):
                for cy in range(16):
                    px = self.pan_x + cx * scale
                    py = self.pan_y + cy * scale
                    pixel_color = tab["surf"].get_at((cx, cy))
                    if pixel_color.a > 0:
                        pygame.draw.rect(surface, pixel_color, (px, py, scale, scale))

            # Grid lines
            grid_color = (55, 55, 60)
            for gx in range(17):
                x_pos = self.pan_x + gx * scale
                pygame.draw.line(surface, grid_color, (x_pos, self.pan_y), (x_pos, self.pan_y + canvas_h), 1)
            for gy in range(17):
                y_pos = self.pan_y + gy * scale
                pygame.draw.line(surface, grid_color, (self.pan_x, y_pos), (self.pan_x + canvas_w, y_pos), 1)

            # Selection Highlight Rect
            if self.sel_rect:
                sx = self.pan_x + self.sel_rect.x * scale
                sy = self.pan_y + self.sel_rect.y * scale
                sw = self.sel_rect.width * scale
                sh = self.sel_rect.height * scale
                sel_hl = pygame.Surface((sw, sh), pygame.SRCALPHA)
                sel_hl.fill((255, 200, 0, 70))
                surface.blit(sel_hl, (sx, sy))
                pygame.draw.rect(surface, UITheme.WARNING, (sx, sy, sw, sh), 2)

            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, canvas_rect_screen, 2)
            
        surface.set_clip(None)

        if self.category_dropdown.expanded:
            self.category_dropdown.draw_list(surface)

        # 7. Modals
        if self.close_confirm_dialog:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            modal_rect = pygame.Rect(self.width//2 - 280, self.height//2 - 95, 560, 190)
            pygame.draw.rect(surface, UITheme.PANEL_BG, modal_rect, border_radius=8)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, modal_rect, 2, border_radius=8)
            surface.blit(self.font.render("Unsaved Changes", True, UITheme.WARNING), (modal_rect.x + 20, modal_rect.y + 15))
            pygame.draw.line(surface, UITheme.BORDER, (modal_rect.x, modal_rect.y + 40), (modal_rect.right, modal_rect.y + 40))
            surface.blit(self.font.render("Save changes to sprite?", True, UITheme.TEXT), (modal_rect.x + 25, modal_rect.y + 55))
            surface.blit(self.font.render(self.close_confirm_dialog["name"], True, UITheme.WARNING), (modal_rect.x + 25, modal_rect.y + 82))
            btn_y = modal_rect.bottom - 46
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 20, btn_y, 150, 34), "Save & Close", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 185, btn_y, 240, 34), "Close Without Save", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 440, btn_y, 100, 34), "Cancel", self.font, mouse_pos, UITheme.BORDER, UITheme.BORDER_ACTIVE)

        if self.new_sprite_dialog:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            modal_rect = pygame.Rect(self.width//2 - 260, self.height//2 - 120, 520, 240)
            pygame.draw.rect(surface, UITheme.PANEL_BG, modal_rect, border_radius=8)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, modal_rect, 2, border_radius=8)
            surface.blit(self.font.render("Create New 16x16 Sprite", True, UITheme.WARNING), (modal_rect.x + 20, modal_rect.y + 15))
            pygame.draw.line(surface, UITheme.BORDER, (modal_rect.x, modal_rect.y + 40), (modal_rect.right, modal_rect.y + 40))

            surface.blit(self.font.render("Target Folder:", True, UITheme.TEXT_DIM), (modal_rect.x + 25, modal_rect.y + 60))
            self.new_sprite_dialog["folder_dd"].draw(surface)
            surface.blit(self.font.render("Filename (.png):", True, UITheme.TEXT_DIM), (modal_rect.x + 25, modal_rect.y + 110))
            self.new_sprite_dialog["box"].draw(surface)

            btn_y = modal_rect.bottom - 45
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 130, btn_y, 130, 34), "Create", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 280, btn_y, 110, 34), "Cancel", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

            if self.new_sprite_dialog["folder_dd"].expanded:
                self.new_sprite_dialog["folder_dd"].draw_list(surface)