import pygame
import os
import json
from editor.config import get_data_dir, get_active_content_root, LIB_ROOT, GAME_ROOT, PROJECT_ROOT
from editor.ui import UITextBox, UIDropdown, UITheme, draw_styled_button, FocusManager

class UIToggle:
    def __init__(self, x, y, width, height, font, state=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        if isinstance(state, str):
            self.state = state.lower() in ["true", "1", "yes"]
        else:
            self.state = bool(state)

    @property
    def text(self): return "true" if self.state else "false"

    @text.setter
    def text(self, val):
        if isinstance(val, str):
            self.state = val.lower() in ["true", "1", "yes"]
        else:
            self.state = bool(val)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = not self.state
                return True
        return False

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        color = UITheme.SUCCESS if self.state else UITheme.DANGER
        hover = UITheme.SUCCESS_HOVER if self.state else UITheme.DANGER_HOVER
        draw_styled_button(surface, self.rect, "True" if self.state else "False", self.font, mouse_pos, color, hover)

class WorldEditor:
    def __init__(self, y_offset, width, height, font):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font

        self.sidebar_w = 300
        self.files = []
        self.selected_file = None
        self.world_data = {}
        self.raw_data = {}
        self.field_inputs = {}
        self.field_labels = {}
        self.section_headers = []

        self.sidebar_scroll = 0
        self.max_sidebar_scroll = 0
        self.form_scroll = 0
        self.max_form_scroll = 0
        self.dragging_form = False
        self.form_start_y = 0
        self.form_start_offset = 0
        self.form_thumb_rect = None

        # Source Dropdown: Global vs Presets
        self.selected_source = "Global"
        source_opts = [
            {"label": "Global (Sandbox)", "value": "Global"},
            {"label": "Presets", "value": "Presets"}
        ]
        self.source_dropdown = UIDropdown(10, self.y_offset + 36, self.sidebar_w - 20, 28, self.font, source_opts, self.selected_source)
        self.search_input = UITextBox(10, self.y_offset + 72, self.sidebar_w - 20, 28, self.font, "")

        self.save_btn = pygame.Rect(self.width - 240, self.y_offset + 12, 110, 34)
        self.code_btn = pygame.Rect(self.width - 120, self.y_offset + 12, 100, 34)

        self.refresh_files()

    def resize(self, width, height):
        self.width = width
        self.height = height
        self.save_btn.topleft = (self.width - 240, self.y_offset + 12)
        self.code_btn.topleft = (self.width - 120, self.y_offset + 12)
        self.layout_form()

    def refresh_files(self):
        """Discovers files based on the chosen dropdown source (Global or Presets)."""
        self.files = []
        seen = set()

        if self.selected_source == "Global":
            # Target: /data.rot/save/config/world.json
            sandbox_candidates = [
                os.path.join(GAME_ROOT, 'save', 'config', 'world.json'),
                os.path.join(PROJECT_ROOT, 'data.rot', 'save', 'config', 'world.json'),
                os.path.join(PROJECT_ROOT, 'bitrot', 'data.rot', 'save', 'config', 'world.json'),
                os.path.join(get_active_content_root(), 'save', 'config', 'world.json')
            ]
            found = False
            for p in sandbox_candidates:
                if os.path.exists(p) and p not in seen:
                    seen.add(p)
                    self.files.append({"name": "world.json", "path": p})
                    found = True
                    break
            if not found:
                # Provide standard path even if not yet saved on disk
                default_p = os.path.join(GAME_ROOT, 'save', 'config', 'world.json')
                self.files.append({"name": "world.json", "path": default_p})

        else:  # Presets
            # Target: /data.rot/lib/data/world_builds/*.json and active Mod presets
            preset_dirs = [
                os.path.join(get_active_content_root(), 'data', 'world_builds'),
                os.path.join(LIB_ROOT, 'data', 'world_builds'),
                os.path.join(GAME_ROOT, 'lib', 'data', 'world_builds'),
                os.path.join(PROJECT_ROOT, 'data.rot', 'lib', 'data', 'world_builds'),
                get_data_dir("world_builds")
            ]
            for d in preset_dirs:
                if os.path.exists(d) and os.path.isdir(d):
                    for f in sorted(os.listdir(d)):
                        if f.endswith('.json'):
                            fp = os.path.join(d, f)
                            if fp not in seen:
                                seen.add(fp)
                                self.files.append({"name": f, "path": fp})

        if self.files:
            if not self.selected_file or not any(f["path"] == self.selected_file for f in self.files):
                self.load_file(self.files[0]["path"])
        else:
            self.selected_file = None
            self.world_data = {}
            self.field_inputs.clear()

    @property
    def filtered_files(self):
        q = self.search_input.text.strip().lower()
        if not q: return self.files
        return [f for f in self.files if q in f["name"].lower()]

    def load_file(self, path):
        self.selected_file = path
        self.world_data = {}
        self.field_inputs.clear()
        self.raw_data = {}
        self.form_scroll = 0

        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.raw_data = json.load(f)

                if "builds" in self.raw_data and isinstance(self.raw_data["builds"], dict) and self.raw_data["builds"]:
                    build_key = list(self.raw_data["builds"].keys())[0]
                    self.world_data = self.raw_data["builds"][build_key].get("world", {})
                elif "world" in self.raw_data:
                    self.world_data = self.raw_data["world"]
                else:
                    self.world_data = self.raw_data
            except Exception as e:
                print(f"Error loading world file {path}: {e}")

        self.layout_form()

    def layout_form(self):
        self.field_inputs.clear()
        self.field_labels.clear()
        self.section_headers = []
        if not self.world_data: return

        form_x = self.sidebar_w + 25
        content_w = max(420, self.width - self.sidebar_w - 60)
        current_y = self.y_offset + 75 - self.form_scroll

        for sec_name, sec_dict in self.world_data.items():
            if isinstance(sec_dict, dict):
                header_title = f"-- {sec_name.replace('_', ' ').upper()} --"
                self.section_headers.append((header_title, current_y))
                current_y += 30

                for k, v in sec_dict.items():
                    if isinstance(v, dict) and "value" in v:
                        val = v["value"]
                        friendly_name = v.get("name") or k.replace("_", " ").title()
                    else:
                        val = v
                        friendly_name = k.replace("_", " ").title()

                    full_key = f"{sec_name}.{k}"
                    self.field_labels[full_key] = (friendly_name, current_y)

                    if isinstance(val, bool) or str(val).lower() in ["true", "false"]:
                        ui_elem = UIToggle(form_x + 320, current_y, 90, 26, self.font, state=val)
                    else:
                        ui_elem = UITextBox(form_x + 320, current_y, max(120, content_w - 340), 26, self.font, str(val))

                    self.field_inputs[full_key] = ui_elem
                    current_y += 34
                current_y += 12

        form_h = self.height - self.y_offset - 60
        self.max_form_scroll = max(0, (current_y + 40 + self.form_scroll) - (self.y_offset + 60 + form_h))

    def save_file(self):
        if not self.selected_file: return
        try:
            raw = self.raw_data if self.raw_data else {}
            if os.path.exists(self.selected_file):
                try:
                    with open(self.selected_file, 'r', encoding='utf-8') as f:
                        raw = json.load(f)
                except Exception: pass

            target_world = raw
            if "builds" in raw and isinstance(raw["builds"], dict) and raw["builds"]:
                build_key = list(raw["builds"].keys())[0]
                if "world" not in raw["builds"][build_key]:
                    raw["builds"][build_key]["world"] = {}
                target_world = raw["builds"][build_key]["world"]
            elif "world" in raw:
                target_world = raw["world"]

            for full_key, widget in self.field_inputs.items():
                sec, k = full_key.split('.', 1)
                if sec not in target_world or not isinstance(target_world[sec], dict):
                    target_world[sec] = {}

                val_str = widget.text.strip()
                if isinstance(widget, UIToggle):
                    parsed_val = widget.state
                elif val_str.lower() == "true": parsed_val = True
                elif val_str.lower() == "false": parsed_val = False
                elif "." in val_str:
                    try: parsed_val = float(val_str)
                    except ValueError: parsed_val = val_str
                elif val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
                    try: parsed_val = int(val_str)
                    except ValueError: parsed_val = val_str
                else:
                    parsed_val = val_str

                if isinstance(target_world[sec].get(k), dict) and "value" in target_world[sec][k]:
                    target_world[sec][k]["value"] = parsed_val
                else:
                    target_world[sec][k] = parsed_val

            os.makedirs(os.path.dirname(self.selected_file), exist_ok=True)
            with open(self.selected_file, 'w', encoding='utf-8') as f:
                json.dump(raw, f, indent=2)
            print(f"Saved world: {self.selected_file}")
        except Exception as e:
            print(f"Error saving world {self.selected_file}: {e}")

    def handle_event(self, event):
        # 1. Source Dropdown Interaction (Global vs Presets)
        if self.source_dropdown.expanded:
            if self.source_dropdown.handle_event(event):
                if self.source_dropdown.text != self.selected_source:
                    self.selected_source = self.source_dropdown.text
                    self.refresh_files()
                return True

        if self.source_dropdown.handle_event(event):
            if self.source_dropdown.text != self.selected_source:
                self.selected_source = self.source_dropdown.text
                self.refresh_files()
            return True

        if self.search_input.handle_event(event): return True

        for box in self.field_inputs.values():
            if box.handle_event(event): return True

        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_form = False

        if event.type == pygame.MOUSEMOTION and self.dragging_form and self.form_thumb_rect and self.max_form_scroll > 0:
            dy = event.pos[1] - self.form_start_y
            track_h = self.height - self.y_offset - 60
            thumb_h = self.form_thumb_rect.height
            track_space = track_h - thumb_h
            if track_space > 0:
                self.form_scroll = max(0, min(self.max_form_scroll, self.form_start_offset + dy * (self.max_form_scroll / track_space)))
                self.layout_form()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx <= self.sidebar_w:
                if event.button == 4:
                    self.sidebar_scroll = max(0, self.sidebar_scroll - 30)
                    return True
                elif event.button == 5:
                    self.sidebar_scroll = min(self.max_sidebar_scroll, self.sidebar_scroll + 30)
                    return True
                elif event.button == 1:
                    list_y = self.y_offset + 115 - self.sidebar_scroll
                    for f_info in self.filtered_files:
                        r = pygame.Rect(10, list_y, self.sidebar_w - 20, 26)
                        if r.collidepoint(mx, my):
                            self.load_file(f_info["path"])
                            return True
                        list_y += 30
            else:
                if event.button == 4:
                    self.form_scroll = max(0, self.form_scroll - 40)
                    self.layout_form()
                    return True
                elif event.button == 5:
                    self.form_scroll = min(self.max_form_scroll, self.form_scroll + 40)
                    self.layout_form()
                    return True
                elif event.button == 1:
                    FocusManager.clear_focus()
                    if self.form_thumb_rect and self.form_thumb_rect.collidepoint(mx, my):
                        self.dragging_form = True
                        self.form_start_y = my
                        self.form_start_offset = self.form_scroll
                        return True
                    if self.save_btn.collidepoint(mx, my):
                        self.save_file()
                        return True
                    elif self.code_btn.collidepoint(mx, my):
                        self.save_file()
                        return {"action": "open_in_code", "path": self.selected_file}

        return False

    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect)
        mouse_pos = pygame.mouse.get_pos()

        # 1. Left Sidebar Header
        sidebar_header_rect = pygame.Rect(0, self.y_offset, self.sidebar_w, 115)
        pygame.draw.rect(surface, UITheme.PANEL_BG, sidebar_header_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset), (self.sidebar_w, self.height), 2)
        surface.blit(self.font.render("World Settings", True, UITheme.WARNING), (15, self.y_offset + 10))

        # Dropdown for Global vs Presets & Search Input
        self.source_dropdown.draw(surface)
        self.search_input.draw(surface)

        # 2. File List in Sidebar
        list_clip = pygame.Rect(0, self.y_offset + 115, self.sidebar_w, self.height - self.y_offset - 115)
        surface.set_clip(list_clip)
        list_y = list_clip.y + 5 - self.sidebar_scroll

        for f_info in self.filtered_files:
            r = pygame.Rect(8, list_y, self.sidebar_w - 18, 26)
            is_active = (f_info["path"] == self.selected_file)
            if is_active: pygame.draw.rect(surface, UITheme.LIST_HOVER, r, border_radius=4)
            elif r.collidepoint(mouse_pos): pygame.draw.rect(surface, UITheme.HOVER_BG, r, border_radius=4)

            surface.blit(self.font.render(f_info["name"][:25], True, UITheme.TEXT), (14, list_y + 5))
            list_y += 30

        surface.set_clip(None)
        self.max_sidebar_scroll = max(0, len(self.filtered_files) * 30 + 10 - list_clip.height)

        # 3. Main Content Header
        right_header = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, 60)
        pygame.draw.rect(surface, UITheme.BG, right_header)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset + 59), (self.width, self.y_offset + 59))

        fname = os.path.basename(self.selected_file) if self.selected_file else "None"
        surface.blit(self.font.render(f"World: {fname} [{self.selected_source}]", True, UITheme.WARNING), (self.sidebar_w + 20, self.y_offset + 20))
        draw_styled_button(surface, self.save_btn, "Save File", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.code_btn, "Code", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)

        # 4. Form Fields Area
        form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset + 60, self.width - self.sidebar_w, self.height - self.y_offset - 60)
        surface.set_clip(form_view_rect)

        for h_title, h_y in self.section_headers:
            surface.blit(self.font.render(h_title, True, UITheme.WARNING), (self.sidebar_w + 25, h_y))

        for full_key, box in self.field_inputs.items():
            friendly_name, l_y = self.field_labels[full_key]
            lbl = friendly_name if len(friendly_name) <= 30 else friendly_name[:28] + ".."
            surface.blit(self.font.render(lbl, True, UITheme.TEXT_DIM), (self.sidebar_w + 25, l_y + 5))
            box.draw(surface)

        surface.set_clip(None)

        # 5. Form Scrollbar
        if self.max_form_scroll > 0:
            track_rect = pygame.Rect(self.width - 8, form_view_rect.y, 8, form_view_rect.height)
            thumb_h = max(20, int((form_view_rect.height / (form_view_rect.height + self.max_form_scroll)) * form_view_rect.height))
            thumb_y = form_view_rect.y + (self.form_scroll / self.max_form_scroll) * (form_view_rect.height - thumb_h)
            self.form_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.form_thumb_rect, border_radius=4)
        else:
            self.form_thumb_rect = None

        # 6. Draw Dropdown List on top (Ensures popup is not clipped)
        if self.source_dropdown.expanded:
            self.source_dropdown.draw_list(surface)