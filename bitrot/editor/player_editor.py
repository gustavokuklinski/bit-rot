import pygame
import os
import json
from editor.config import get_data_dir, LIB_ROOT
from editor.ui import (
    UITextBox, UIDropdown, UITextArea, UIAttributeList, UITheme, 
    draw_styled_button, FocusManager
)

FRIENDLY_NAMES = {
    "_tag": "Tag",
    "stage": "Quest Stage",
    "player_question": "Player Question",
    "npc_answer": "NPC Answer",
    "req_item": "Required Item",
    "rqst_item": "Requested Item",
    "award_item": "Award Item",
    "tip": "Tip Message",
    "unlock_flag": "Unlock Flag",
    "complete_flag": "Complete Flag",
    "priority": "Priority",
    "dialog_type": "Dialog Type",
    "name": "Name",
    "type": "Type",
    "entity": "Target Entity",
    "number": "Required Count",
    "message": "Notification Message",
    "cost": "Trait Cost",
    "tooltip": "Tooltip",
    "base_xp": "Base XP"
}

class PlayerEditor:
    def __init__(self, y_offset, width, height, font, item_tiles):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        self.item_tiles = item_tiles

        self.nodes = {}
        self.selected_node = None
        self.sidebar_w = 300

        self.sidebar_scroll = 0
        self.max_sidebar_scroll = 0
        self.dragging_sidebar = False
        self.sidebar_start_y = 0
        self.sidebar_start_offset = 0
        self.sidebar_thumb_rect = None

        self.form_scroll = 0
        self.max_form_scroll = 0
        self.dragging_form = False
        self.form_start_y = 0
        self.form_start_offset = 0
        self.form_thumb_rect = None

        self.current_file = None
        self.file_paths = {}

        self.file_dropdown = UIDropdown(10, self.y_offset + 38, self.sidebar_w - 20, 30, self.font, [])
        self.new_node_btn = pygame.Rect(10, self.y_offset + 74, self.sidebar_w - 20, 30)

        self.save_file_btn = pygame.Rect(self.width - 370, y_offset + 12, 130, 35)
        self.code_btn = pygame.Rect(self.width - 230, y_offset + 12, 100, 35)
        self.del_node_btn = pygame.Rect(self.width - 120, y_offset + 12, 100, 35)

        self.editing_context = None
        self.option_inputs = {}
        self.option_fields_order = []
        self.option_form_scroll = 0
        self.max_option_scroll = 0
        self.dragging_option_scroll = False
        self.option_scroll_start_y = 0
        self.option_scroll_start_offset = 0
        self.option_thumb_rect = None

        self.opt_save_btn = pygame.Rect(0, 0, 140, 35)
        self.opt_code_btn = pygame.Rect(0, 0, 100, 35)
        self.opt_back_btn = pygame.Rect(0, 0, 110, 35)
        self.opt_delete_btn = pygame.Rect(0, 0, 110, 35)
        self.add_field_dd = None

        self.refresh_files()

    def resize(self, width, height):
        self.width = width
        self.height = height
        self.save_file_btn.topleft = (self.width - 370, self.y_offset + 12)
        self.code_btn.topleft = (self.width - 230, self.y_offset + 12)
        self.del_node_btn.topleft = (self.width - 120, self.y_offset + 12)
        if self.editing_context:
            self._layout_option_editor()

    def refresh_files(self):
        self.file_paths.clear()
        search_dirs = [get_data_dir("player"), os.path.join(LIB_ROOT, 'data', 'player')]
        allowed_stems = ["player", "milestones", "quests", "progression", "traits", "civilian", "military", "worker"]
        
        for d in search_dirs:
            if os.path.exists(d) and os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    if f.endswith('.json'):
                        stem = os.path.splitext(f)[0].lower()
                        if stem in allowed_stems or f not in self.file_paths:
                            self.file_paths[f] = os.path.join(d, f)

        opts = [{"label": k, "value": k} for k in self.file_paths.keys()]
        self.file_dropdown.options = opts if opts else [{"label": "No files found", "value": ""}]
        if self.file_paths:
            if not self.current_file or self.current_file not in self.file_paths:
                self.current_file = list(self.file_paths.keys())[0]
            self.file_dropdown.selected_value = self.current_file
            self.file_dropdown._update_label()
        else:
            self.current_file = None
            self.file_dropdown.selected_value = ""
            self.file_dropdown._update_label()

        self.load_file()

    def load_file(self):
        self.nodes.clear()
        self.selected_node = None
        self.editing_context = None
        if not self.current_file or self.current_file not in self.file_paths:
            return

        path = self.file_paths[self.current_file]
        if not os.path.exists(path): return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if "quests" in data:
                for item in data["quests"]:
                    for sub_q in item.get("options", []):
                        q_id = sub_q.get("id", "Quest")
                        opts = [{"_tag": "options", **{k: str(v) for k, v in opt.items()}} for opt in sub_q.get("options", [])]
                        self.nodes[q_id] = {"options": opts}

            elif "milestones" in data:
                opts = [{"_tag": "milestone", **{k: str(v) for k, v in m.items()}} for m in data["milestones"]]
                self.nodes["milestones"] = {"options": opts}

            elif "player_traits" in data:
                for sec_name, sec_dict in data["player_traits"].items():
                    opts = []
                    if isinstance(sec_dict, dict):
                        for tid, tval in sec_dict.items():
                            opt_entry = {"_tag": sec_name, "id": tid}
                            if isinstance(tval, dict):
                                for k, v in tval.items(): opt_entry[k] = str(v)
                            opts.append(opt_entry)
                    self.nodes[sec_name] = {"options": opts}

            elif "progression" in data:
                for sec_name, sec_dict in data["progression"].items():
                    opts = []
                    if isinstance(sec_dict, dict):
                        for aid, aval in sec_dict.items():
                            opt_entry = {"_tag": sec_name, "id": aid}
                            if isinstance(aval, dict):
                                for k, v in aval.items(): opt_entry[k] = str(v)
                            opts.append(opt_entry)
                    self.nodes[sec_name] = {"options": opts}

            elif "player" in data:
                p_data = data["player"]
                opts = [{"_tag": "property", "name": k, "value": str(v)} for k, v in p_data.items()] if isinstance(p_data, dict) else []
                self.nodes["player"] = {"options": opts}

            elif "player_builds" in data:
                for bid, bdata in data["player_builds"].items():
                    opts = [{"_tag": "build", **{k: str(v) for k, v in bdata.items()}}] if isinstance(bdata, dict) else []
                    self.nodes[bid] = {"options": opts}

        except Exception as e:
            print(f"Error loading Player JSON {path}: {e}")

        if self.nodes and not self.selected_node:
            self.selected_node = list(self.nodes.keys())[0]

    def save_file(self):
        if not self.current_file or self.current_file not in self.file_paths:
            return
        path = self.file_paths[self.current_file]
        os.makedirs(os.path.dirname(path), exist_ok=True)

        fname = os.path.basename(path).lower()
        data_to_save = {}

        if "quest" in fname:
            quest_list = []
            for q_id, q_data in self.nodes.items():
                sub_opts = []
                for o in q_data["options"]:
                    clean_opt = {}
                    for k, v in o.items():
                        if k == "_tag" or not str(v).strip(): continue
                        clean_opt[k] = int(v) if (k == "priority" and str(v).isdigit()) else v
                    sub_opts.append(clean_opt)
                quest_list.append({"id": q_id, "options": sub_opts})
            data_to_save = {"quests": [{"id": "quests", "options": quest_list}]}

        elif "milestone" in fname:
            m_list = []
            for _, q_data in self.nodes.items():
                for o in q_data["options"]:
                    clean_m = {}
                    for k, v in o.items():
                        if k == "_tag" or not str(v).strip(): continue
                        clean_m[k] = int(v) if (k == "number" and str(v).isdigit()) else v
                    m_list.append(clean_m)
            data_to_save = {"milestones": m_list}
        else:
            try:
                with open(path, 'r', encoding='utf-8') as rf:
                    data_to_save = json.load(rf)
            except Exception:
                data_to_save = {}

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2)

    def open_option_editor(self, context_type, idx=None):
        self.editing_context = {"type": context_type, "idx": idx}
        self.option_inputs.clear()
        self.option_fields_order = []
        self.option_form_scroll = 0

        values = self.nodes[self.selected_node]["options"][idx].copy() if (context_type == "edit" and idx is not None) else {"_tag": "property"}
        self.option_fields_order = list(values.keys())

        content_w = max(400, self.width - self.sidebar_w - 60)
        for f in self.option_fields_order:
            self.option_inputs[f] = UITextBox(0, 0, content_w, 30, self.font, str(values.get(f, "")))

        self._layout_option_editor()

    def _layout_option_editor(self):
        content_w = max(400, self.width - self.sidebar_w - 60)
        form_x = self.sidebar_w + 30
        current_y = self.y_offset + 70 - self.option_form_scroll

        for f in self.option_fields_order:
            box = self.option_inputs[f]
            box.rect.x = form_x
            box.rect.y = current_y + 24
            box.rect.width = content_w
            current_y += box.rect.height + 36

        current_y += 10
        self.opt_save_btn.topleft = (form_x, current_y)
        self.opt_code_btn.topleft = (form_x + 155, current_y)
        self.opt_back_btn.topleft = (form_x + 270, current_y)
        self.opt_delete_btn.topleft = (form_x + 395, current_y)

        form_h = self.height - self.y_offset - 60
        self.max_option_scroll = max(0, (current_y + 70 + self.option_form_scroll) - (self.y_offset + 60 + form_h))

    def save_editing_option(self):
        if not self.editing_context or not self.selected_node: return
        vals = {f: box.text for f, box in self.option_inputs.items()}
        ctx = self.editing_context
        if ctx["type"] == "new":
            self.nodes[self.selected_node]["options"].append(vals)
        elif ctx["type"] == "edit" and ctx["idx"] is not None:
            self.nodes[self.selected_node]["options"][ctx["idx"]] = vals

        self.save_file()
        self.editing_context = None

    def cancel_editing_option(self):
        self.editing_context = None

    def delete_editing_option(self):
        if not self.editing_context or not self.selected_node: return
        ctx = self.editing_context
        if ctx["type"] == "edit" and ctx["idx"] is not None:
            self.nodes[self.selected_node]["options"].pop(ctx["idx"])
            self.save_file()
        self.editing_context = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            ctrl_held = (event.mod & pygame.KMOD_CTRL)
            if ctrl_held and event.key == pygame.K_s:
                if self.editing_context: self.save_editing_option()
                else: self.save_file()
                return True
            if (ctrl_held and event.key == pygame.K_w) or event.key == pygame.K_ESCAPE:
                if self.editing_context:
                    self.cancel_editing_option()
                    return True

        old_file = self.current_file
        if self.file_dropdown.handle_event(event):
            if self.file_dropdown.text != old_file:
                self.save_file()
                self.current_file = self.file_dropdown.text
                self.load_file()
            return True

        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_sidebar = False
            self.dragging_form = False
            self.dragging_option_scroll = False

        if event.type == pygame.MOUSEMOTION:
            if self.dragging_sidebar and self.sidebar_thumb_rect and self.max_sidebar_scroll > 0:
                dy = event.pos[1] - self.sidebar_start_y
                track_h = self.height - self.y_offset - 115
                thumb_h = self.sidebar_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    self.sidebar_scroll = max(0, min(self.max_sidebar_scroll, self.sidebar_start_offset + dy * (self.max_sidebar_scroll / track_space)))
                return True

        if self.editing_context:
            for box in self.option_inputs.values():
                if box.handle_event(event): return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] > self.sidebar_w and event.button == 1:
                FocusManager.clear_focus()
                if self.opt_save_btn.collidepoint(event.pos):
                    self.save_editing_option()
                    return True
                elif self.opt_code_btn.collidepoint(event.pos):
                    self.save_editing_option()
                    path = self.file_paths.get(self.current_file)
                    if path: return {"action": "open_in_code", "path": path}
                    return True
                elif self.opt_back_btn.collidepoint(event.pos):
                    self.cancel_editing_option()
                    return True
                elif self.opt_delete_btn.collidepoint(event.pos):
                    self.delete_editing_option()
                    return True
        else:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if mx <= self.sidebar_w:
                    if event.button == 4:
                        self.sidebar_scroll = max(0, self.sidebar_scroll - 40)
                        return True
                    elif event.button == 5:
                        self.sidebar_scroll = min(self.max_sidebar_scroll, self.sidebar_scroll + 40)
                        return True
                    elif event.button == 1:
                        list_y = self.y_offset + 120 - self.sidebar_scroll
                        for n_id in self.nodes.keys():
                            if pygame.Rect(10, list_y, self.sidebar_w - 30, 25).collidepoint(mx, my):
                                self.selected_node = n_id
                                self.form_scroll = 0
                                return True
                            list_y += 30
                else:
                    if event.button == 1:
                        if self.save_file_btn.collidepoint(mx, my):
                            self.save_file()
                            return True
                        if self.code_btn.collidepoint(mx, my):
                            self.save_file()
                            path = self.file_paths.get(self.current_file)
                            if path: return {"action": "open_in_code", "path": path}
                            return True

                        if self.selected_node:
                            rects, add_btn, total_h = self._get_cards_layout()
                            if self.del_node_btn.collidepoint(mx, my):
                                del self.nodes[self.selected_node]
                                self.selected_node = list(self.nodes.keys())[0] if self.nodes else None
                                self.save_file()
                                return True
                            if add_btn and add_btn.collidepoint(mx, my):
                                self.open_option_editor("new")
                                return True
                            for r in rects:
                                if r["edit"].collidepoint(mx, my):
                                    self.open_option_editor("edit", r["idx"])
                                    return True
                                if r["delete"].collidepoint(mx, my):
                                    self.nodes[self.selected_node]["options"].pop(r["idx"])
                                    self.save_file()
                                    return True
        return False

    def _get_cards_layout(self):
        if not self.selected_node: return [], None, 0
        current_y = self.y_offset + 70 - self.form_scroll
        rects = []
        for i, opt in enumerate(self.nodes[self.selected_node]["options"]):
            card_rect = pygame.Rect(self.sidebar_w + 20, current_y, self.width - self.sidebar_w - 60, 75)
            edit_btn = pygame.Rect(card_rect.right - 150, card_rect.y + 22, 65, 30)
            del_btn = pygame.Rect(card_rect.right - 75, card_rect.y + 22, 65, 30)
            rects.append({"card": card_rect, "edit": edit_btn, "delete": del_btn, "idx": i})
            current_y += 85
        add_btn = pygame.Rect(self.sidebar_w + 20, current_y, 160, 35)
        return rects, add_btn, current_y + 50

    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect)
        mouse_pos = pygame.mouse.get_pos()

        # Sidebar Header
        sidebar_header_rect = pygame.Rect(0, self.y_offset, self.sidebar_w, 115)
        pygame.draw.rect(surface, UITheme.PANEL_BG, sidebar_header_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset), (self.sidebar_w, self.height), 2)
        surface.blit(self.font.render("Player Manager", True, UITheme.WARNING), (15, self.y_offset + 10))

        self.file_dropdown.draw(surface)
        draw_styled_button(surface, self.new_node_btn, "+ Add Node", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)

        # Sidebar List
        list_view_rect = pygame.Rect(0, self.y_offset + 115, self.sidebar_w, self.height - self.y_offset - 115)
        surface.set_clip(list_view_rect)
        list_y = self.y_offset + 120 - self.sidebar_scroll
        for n_id in self.nodes.keys():
            r = pygame.Rect(10, list_y, self.sidebar_w - 30, 25)
            if n_id == self.selected_node:
                pygame.draw.rect(surface, UITheme.LIST_HOVER, r, border_radius=4)
            elif r.collidepoint(mouse_pos):
                pygame.draw.rect(surface, UITheme.HOVER_BG, r, border_radius=4)
            surface.blit(self.font.render(n_id[:25], True, UITheme.TEXT), (15, list_y + 4))
            list_y += 30
        surface.set_clip(None)

        if self.editing_context:
            self._draw_option_editor(surface, mouse_pos)
        elif self.selected_node:
            self._draw_node_overview(surface, mouse_pos)

        if self.file_dropdown.expanded:
            self.file_dropdown.draw_list(surface)

    def _draw_node_overview(self, surface, mouse_pos):
        rects, add_btn, total_h = self._get_cards_layout()
        form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset + 60, self.width - self.sidebar_w, self.height - self.y_offset - 60)
        surface.set_clip(form_view_rect)

        for r in rects:
            pygame.draw.rect(surface, UITheme.PANEL_BG, r["card"], border_radius=6)
            pygame.draw.rect(surface, UITheme.BORDER, r["card"], 1, border_radius=6)
            opt = self.nodes[self.selected_node]["options"][r["idx"]]

            title = opt.get("name") or opt.get("id") or opt.get("_tag", "Entry")
            snippet = ", ".join(f"{k}: {v}" for k, v in opt.items() if k not in ["_tag", "name", "id"])
            if len(snippet) > 80: snippet = snippet[:77] + "..."

            surface.blit(self.font.render(str(title), True, UITheme.WARNING), (r["card"].x + 10, r["card"].y + 10))
            surface.blit(self.font.render(snippet, True, UITheme.TEXT), (r["card"].x + 10, r["card"].y + 40))

            draw_styled_button(surface, r["edit"], "Edit", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
            draw_styled_button(surface, r["delete"], "Del", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

        draw_styled_button(surface, add_btn, "+ Add Entry", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        surface.set_clip(None)

        right_header_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, 60)
        pygame.draw.rect(surface, UITheme.BG, right_header_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset + 59), (self.width, self.y_offset + 59))

        surface.blit(self.font.render(f"Section: {self.selected_node}", True, UITheme.WARNING), (self.sidebar_w + 20, self.y_offset + 22))
        draw_styled_button(surface, self.save_file_btn, "Save File", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.code_btn, "Code", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)
        draw_styled_button(surface, self.del_node_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

    def _draw_option_editor(self, surface, mouse_pos):
        form_h = self.height - self.y_offset - 60
        form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset + 60, self.width - self.sidebar_w, form_h)
        surface.set_clip(form_view_rect)

        for f in self.option_fields_order:
            box = self.option_inputs[f]
            friendly = FRIENDLY_NAMES.get(f, f.replace("_", " ").title())
            surface.blit(self.font.render(f"{friendly}:", True, UITheme.TEXT_DIM), (box.rect.x, box.rect.y - 20))
            box.draw(surface)

        draw_styled_button(surface, self.opt_save_btn, "Save", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.opt_code_btn, "Code", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)
        draw_styled_button(surface, self.opt_back_btn, "Cancel", self.font, mouse_pos, UITheme.BORDER, UITheme.BORDER_ACTIVE)
        if self.editing_context.get("type") == "edit":
            draw_styled_button(surface, self.opt_delete_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

        surface.set_clip(None)