import pygame
import os
import xml.etree.ElementTree as ET
from editor.config import GAME_ROOT
from editor.ui import (
    UITextBox, UIDropdown, UITextArea, UIAttributeList, UITheme, 
    draw_styled_button, FocusManager
)

# Friendly display names mapped to XML attributes
FRIENDLY_NAMES = {
    "_tag": "Option Tag",
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
    "npc_state_friendly": "NPC Friendly State",
    "npc_state_static": "NPC Static State",
    "req_level": "Required Level",
    "gain_xp": "Gain XP",
    "name": "Milestone Name",
    "type": "Milestone Type",
    "entity": "Target Entity",
    "number": "Required Count",
    "message": "Notification Message"
}

# The attributes actually used in each respective file
FILE_ATTRIBUTES = {
    "chat.xml": ["_tag", "player_question", "npc_answer", "priority", "gain_xp"],
    "tips.xml": ["_tag", "player_question", "npc_answer", "priority", "dialog_type", "award_item", "req_level", "gain_xp"],
    "quests.xml": [
        "_tag", "stage", "player_question", "npc_answer", "unlock_flag", "complete_flag",
        "req_item", "rqst_item", "award_item", "tip", "dialog_type", "priority",
        "npc_state_friendly", "npc_state_static", "gain_xp"
    ],
    "milestones.xml": ["_tag", "name", "type", "entity", "number", "message"]
}

MILESTONE_TYPES = ["kill", "hit", "craft_craft", "craft_repair", "craft_dismantle", "days"]
MILESTONE_ENTITIES = ["zombie", "hostile_npc", "animal", "static_npc", "item", "world_day"]

class NewNodeModal:
    """Compact modal to create a new dialog node."""
    def __init__(self, font):
        self.font = font
        self.active = False
        self.box = None
        self.rect = pygame.Rect(0, 0, 420, 160)
        self.create_btn = pygame.Rect(0, 0, 120, 32)
        self.cancel_btn = pygame.Rect(0, 0, 110, 32)

    def open(self, center_x, center_y, default_prefix="Quest: New Node"):
        self.rect.center = (center_x, center_y)
        self.box = UITextBox(self.rect.x + 20, self.rect.y + 60, self.rect.width - 40, 30, self.font, default_prefix)
        self.box.active = True
        FocusManager.set_focus(self.box)
        btn_y = self.rect.bottom - 45
        self.create_btn.topleft = (self.rect.x + 80, btn_y)
        self.cancel_btn.topleft = (self.rect.x + 220, btn_y)
        self.active = True

    def handle_event(self, event):
        if not self.active: return None
        if self.box.handle_event(event): return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.create_btn.collidepoint(event.pos):
                val = self.box.text.strip()
                self.active = False
                return {"action": "create", "id": val} if val else True
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
        surface.blit(self.font.render("Create New Node", True, UITheme.WARNING), (self.rect.x + 20, self.rect.y + 15))
        pygame.draw.line(surface, UITheme.BORDER, (self.rect.x, self.rect.y + 40), (self.rect.right, self.rect.y + 40))

        surface.blit(self.font.render("Node ID (e.g., Quest: Title, greeting):", True, UITheme.TEXT_DIM), (self.rect.x + 20, self.rect.y + 43))
        self.box.draw(surface)

        mouse_pos = pygame.mouse.get_pos()
        draw_styled_button(surface, self.create_btn, "Create", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.cancel_btn, "Cancel", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

class DialogEditor:
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
        
        self.xml_dir = os.path.join(GAME_ROOT, 'lib', 'data', 'npc_dialogs')
        self.current_file = None
        self.files = []
        
        if not os.path.exists(self.xml_dir):
            os.makedirs(self.xml_dir)
            
        default_files = ["chat.xml", "quests.xml", "tips.xml", "milestones.xml"]
        for df in default_files:
            df_path = os.path.join(self.xml_dir, df)
            if not os.path.exists(df_path):
                root = ET.Element("npc_dialog")
                ET.ElementTree(root).write(df_path)

        self.new_node_modal = NewNodeModal(font)
        
        # Sidebar UI
        self.file_dropdown = UIDropdown(10, self.y_offset + 35, self.sidebar_w - 20, 30, self.font, [])
        self.new_node_btn = pygame.Rect(10, self.y_offset + 75, self.sidebar_w - 20, 32)
        
        # Header action buttons (Node overview)
        self.save_xml_btn = pygame.Rect(self.width - 370, y_offset + 12, 130, 35)
        self.code_btn = pygame.Rect(self.width - 230, y_offset + 12, 100, 35)
        self.del_node_btn = pygame.Rect(self.width - 120, y_offset + 12, 100, 35)

        # Full-Screen Option Editor State
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
        self.save_xml_btn.topleft = (self.width - 370, self.y_offset + 12)
        self.code_btn.topleft = (self.width - 230, self.y_offset + 12)
        self.del_node_btn.topleft = (self.width - 120, self.y_offset + 12)
        if self.editing_context:
            self._layout_option_editor()

    def refresh_files(self):
        self.files = sorted([f for f in os.listdir(self.xml_dir) if f.endswith('.xml')])
        opts = [{"label": f, "value": f} for f in self.files]
        self.file_dropdown.options = opts
        if not self.current_file and self.files:
            self.current_file = self.files[0]
            self.file_dropdown.selected_value = self.current_file
            self.file_dropdown._update_label()
        self.load_xml()

    def get_all_dialog_nodes(self):
        """Scans all dialog XML files in npc_dialogs to list available node flags."""
        node_ids = set()
        for fname in os.listdir(self.xml_dir):
            if fname.endswith('.xml'):
                path = os.path.join(self.xml_dir, fname)
                try:
                    tree = ET.parse(path)
                    for node_el in tree.getroot().findall('node'):
                        nid = node_el.get('id')
                        if nid: node_ids.add(nid)
                except Exception: pass
        for nid in self.nodes.keys():
            if nid: node_ids.add(nid)
        return [{"label": "None", "value": ""}] + [{"label": n, "value": n} for n in sorted(node_ids)]

    def load_xml(self):
        self.nodes.clear()
        self.selected_node = None
        self.editing_context = None
        if not self.current_file: return
        
        path = os.path.join(self.xml_dir, self.current_file)
        if not os.path.exists(path): return

        try:
            tree = ET.parse(path)
            root = tree.getroot()
            for node_el in root.findall('node'):
                n_id = node_el.get('id')
                options = []
                for child in node_el:
                    d = child.attrib.copy()
                    # Store exact tag: either 'options' or 'milestone'
                    d["_tag"] = child.tag
                    options.append(d)
                self.nodes[n_id] = {"options": options}
        except Exception: pass

    def save_xml(self):
        if not self.current_file: return
        path = os.path.join(self.xml_dir, self.current_file)
        root = ET.Element("npc_dialog")
        for n_id, data in self.nodes.items():
            node_el = ET.SubElement(root, "node", {"id": n_id})
            for opt in data["options"]:
                tag = opt.get("_tag", "milestone" if self.current_file == "milestones.xml" else "options")
                clean_opt = {k: v for k, v in opt.items() if str(v).strip() and k != "_tag"}
                ET.SubElement(node_el, tag, clean_opt)
                
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ", level=0) 
        tree.write(path, encoding="utf-8", xml_declaration=True)

    # ------------------------------------------------------------------
    # FULL-SCREEN OPTION EDITOR INITIALIZATION & LAYOUT
    # ------------------------------------------------------------------
    def open_option_editor(self, context_type, idx=None):
        self.editing_context = {"type": context_type, "idx": idx}
        self.option_inputs.clear()
        self.option_fields_order = []
        self.option_form_scroll = 0

        is_milestone_file = (self.current_file == "milestones.xml")
        default_tag = "milestone" if is_milestone_file else "options"

        # Gather values
        if context_type == "edit" and idx is not None:
            values = self.nodes[self.selected_node]["options"][idx].copy()
            tag = values.get("_tag", default_tag)
        else:
            tag = default_tag
            values = {"_tag": tag}
            if tag == "options":
                values["priority"] = "10"
                if self.current_file in ["tips.xml", "quests.xml"]:
                    values["dialog_type"] = "once"
            elif tag == "milestone":
                values["type"] = "kill"
                values["entity"] = "zombie"
                values["number"] = "1"

        # 1. Determine the relevant used attributes only
        if tag == "milestone":
            base_fields = ["_tag", "name", "type", "entity", "number", "message"]
        elif self.current_file in FILE_ATTRIBUTES:
            base_fields = list(FILE_ATTRIBUTES[self.current_file])
        else:
            base_fields = ["_tag", "stage", "player_question", "npc_answer", "unlock_flag", "complete_flag", "req_item", "rqst_item", "award_item", "tip", "dialog_type", "priority", "gain_xp"]

        # Preserve any existing attributes on this option
        for k, v in values.items():
            if k not in base_fields and k != "id" and str(v).strip():
                base_fields.append(k)

        self.option_fields_order = base_fields

        # 2. Build the input components
        content_w = max(400, self.width - self.sidebar_w - 60)
        node_flag_opts = self.get_all_dialog_nodes()

        item_options = [{"label": "None", "value": "", "icon": None}]
        for item_name, icon in sorted(self.item_tiles.items()):
            item_options.append({"label": item_name, "value": f"[{item_name}]", "icon": icon})

        for f in self.option_fields_order:
            self._create_field_input(f, str(values.get(f, "")), content_w, node_flag_opts, item_options)

        # 3. Build + Add Field dropdown for adding any optional unused fields
        self._update_add_field_dropdown(content_w)
        self._layout_option_editor()

    def _create_field_input(self, f, val, content_w, node_flag_opts, item_options):
        # Clean tags: ONLY options and milestone
        if f == "_tag":
            opts = [{"label": "options", "value": "options"}, {"label": "milestone", "value": "milestone"}]
            self.option_inputs[f] = UIDropdown(0, 0, content_w, 30, self.font, opts, val)
        elif f == "stage":
            opts = [{"label": "None", "value": ""}, {"label": "offer", "value": "offer"}, {"label": "turn_in", "value": "turn_in"}]
            self.option_inputs[f] = UIDropdown(0, 0, content_w, 30, self.font, opts, val)
        elif f == "dialog_type":
            opts = [{"label": "None", "value": ""}, {"label": "once", "value": "once"}]
            self.option_inputs[f] = UIDropdown(0, 0, content_w, 30, self.font, opts, val)
        elif f == "priority":
            opts = [{"label": str(x), "value": str(x)} for x in range(0, 101, 10)]
            self.option_inputs[f] = UIDropdown(0, 0, content_w, 30, self.font, opts, val)
        elif f in ["unlock_flag", "complete_flag"]:
            self.option_inputs[f] = UIDropdown(0, 0, content_w, 30, self.font, node_flag_opts, val, searchable=True)
        elif f in ["award_item", "rqst_item", "req_item"]:
            self.option_inputs[f] = UIDropdown(0, 0, content_w, 30, self.font, item_options, val, searchable=True)
        elif f in ["npc_state_friendly", "npc_state_static"]:
            opts = [{"label": "None", "value": ""}, {"label": "true", "value": "true"}, {"label": "false", "value": "false"}]
            self.option_inputs[f] = UIDropdown(0, 0, content_w, 30, self.font, opts, val)
        elif f in ["req_level", "gain_xp"]:
            self.option_inputs[f] = UIAttributeList(0, 0, content_w, 145, self.font, val)
        elif f in ["player_question", "npc_answer", "tip"]:
            self.option_inputs[f] = UITextArea(0, 0, content_w, 95, self.font, val)
        elif f == "type" and self.option_inputs.get("_tag") and self.option_inputs["_tag"].text == "milestone":
            opts = [{"label": t, "value": t} for t in MILESTONE_TYPES]
            self.option_inputs[f] = UIDropdown(0, 0, content_w, 30, self.font, opts, val)
        elif f == "entity" and self.option_inputs.get("_tag") and self.option_inputs["_tag"].text == "milestone":
            opts = [{"label": e, "value": e} for e in MILESTONE_ENTITIES]
            self.option_inputs[f] = UIDropdown(0, 0, content_w, 30, self.font, opts, val)
        else:
            self.option_inputs[f] = UITextBox(0, 0, content_w, 30, self.font, val)

    def _update_add_field_dropdown(self, content_w):
        all_possible = list(FRIENDLY_NAMES.keys())
        unused = [f for f in all_possible if f not in self.option_fields_order]
        opts = [{"label": "+ Add Optional Field...", "value": ""}]
        for f in unused:
            opts.append({"label": f"+ {FRIENDLY_NAMES.get(f, f)} ({f})", "value": f})
        self.add_field_dd = UIDropdown(0, 0, 260, 30, self.font, opts, "")

    def _layout_option_editor(self):
        content_w = max(400, self.width - self.sidebar_w - 60)
        form_x = self.sidebar_w + 30
        current_y = self.y_offset + 70 - self.option_form_scroll

        for f in self.option_fields_order:
            box = self.option_inputs[f]
            box.rect.x = form_x
            box.rect.y = current_y + 24
            box.rect.width = content_w
            if hasattr(box, '_relayout'):
                box._relayout()
            if isinstance(box, UIDropdown):
                box.list_rect.x = box.rect.x
                box.list_rect.y = box.rect.bottom
                box.list_rect.width = content_w

            current_y += box.rect.height + 36

        # Add optional field dropdown
        if self.add_field_dd:
            self.add_field_dd.rect.topleft = (form_x, current_y + 5)
            self.add_field_dd.list_rect.topleft = (form_x, current_y + 35)
            current_y += 50

        # Action Buttons layout
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

        self.save_xml()
        self.editing_context = None

    def cancel_editing_option(self):
        self.editing_context = None

    def delete_editing_option(self):
        if not self.editing_context or not self.selected_node: return
        ctx = self.editing_context
        if ctx["type"] == "edit" and ctx["idx"] is not None:
            self.nodes[self.selected_node]["options"].pop(ctx["idx"])
            self.save_xml()
        self.editing_context = None

    # ------------------------------------------------------------------
    # EVENT HANDLING
    # ------------------------------------------------------------------
    def handle_event(self, event):
        # 1. New Node Modal
        if self.new_node_modal.active:
            res = self.new_node_modal.handle_event(event)
            if res and isinstance(res, dict) and res.get("action") == "create":
                n_id = res["id"]
                if n_id and n_id not in self.nodes:
                    self.nodes[n_id] = {"options": []}
                    self.selected_node = n_id
                    self.save_xml()
            return True

        # 2. Keyboard Shortcuts (CTRL+S, CTRL+W, ESC)
        if event.type == pygame.KEYDOWN:
            ctrl_held = (event.mod & pygame.KMOD_CTRL)
            if ctrl_held and event.key == pygame.K_s:
                if self.editing_context: self.save_editing_option()
                else: self.save_xml()
                return True
            if (ctrl_held and event.key == pygame.K_w) or event.key == pygame.K_ESCAPE:
                if self.editing_context:
                    self.cancel_editing_option()
                    return True

        # 3. Sidebar File Dropdown
        old_file = self.current_file
        if self.file_dropdown.handle_event(event):
            if self.file_dropdown.text != old_file:
                self.save_xml()
                self.current_file = self.file_dropdown.text
                self.load_xml()
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
                if self.dragging_option_scroll and self.option_thumb_rect and self.max_option_scroll > 0:
                    dy = event.pos[1] - self.option_scroll_start_y
                    track_h = self.height - self.y_offset - 60
                    thumb_h = self.option_thumb_rect.height
                    track_space = track_h - thumb_h
                    if track_space > 0:
                        self.option_form_scroll = max(0, min(self.max_option_scroll, self.option_scroll_start_offset + dy * (self.max_option_scroll / track_space)))
                        self._layout_option_editor()
                    return True
            else:
                if self.dragging_form and self.form_thumb_rect and self.max_form_scroll > 0:
                    dy = event.pos[1] - self.form_start_y
                    track_h = self.height - self.y_offset - 60
                    thumb_h = self.form_thumb_rect.height
                    track_space = track_h - thumb_h
                    if track_space > 0:
                        self.form_scroll = max(0, min(self.max_form_scroll, self.form_start_offset + dy * (self.max_form_scroll / track_space)))
                    return True

        # 4. Handle Option Editor View Events
        if self.editing_context:
            if self.add_field_dd and self.add_field_dd.expanded:
                if self.add_field_dd.handle_event(event):
                    if self.add_field_dd.text:
                        chosen = self.add_field_dd.text
                        if chosen not in self.option_fields_order:
                            content_w = max(400, self.width - self.sidebar_w - 60)
                            node_flags = self.get_all_dialog_nodes()
                            items_opts = [{"label": "None", "value": "", "icon": None}]
                            for n, ic in sorted(self.item_tiles.items()):
                                items_opts.append({"label": n, "value": f"[{n}]", "icon": ic})
                            self.option_fields_order.append(chosen)
                            self._create_field_input(chosen, "", content_w, node_flags, items_opts)
                            self._update_add_field_dropdown(content_w)
                            self._layout_option_editor()
                    return True

            dropdowns = [box for box in self.option_inputs.values() if isinstance(box, UIDropdown)]
            for d in dropdowns:
                if d.expanded and d.handle_event(event):
                    # Handle tag switch (options <-> milestone)
                    if d == self.option_inputs.get("_tag"):
                        new_tag = d.text
                        if (new_tag == "milestone" and "name" not in self.option_fields_order) or \
                           (new_tag == "options" and "player_question" not in self.option_fields_order):
                            self.open_option_editor(self.editing_context["type"], self.editing_context["idx"])
                    return True

            if self.add_field_dd and self.add_field_dd.handle_event(event):
                if self.add_field_dd.text:
                    chosen = self.add_field_dd.text
                    if chosen not in self.option_fields_order:
                        content_w = max(400, self.width - self.sidebar_w - 60)
                        node_flags = self.get_all_dialog_nodes()
                        items_opts = [{"label": "None", "value": "", "icon": None}]
                        for n, ic in sorted(self.item_tiles.items()):
                            items_opts.append({"label": n, "value": f"[{n}]", "icon": ic})
                        self.option_fields_order.append(chosen)
                        self._create_field_input(chosen, "", content_w, node_flags, items_opts)
                        self._update_add_field_dropdown(content_w)
                        self._layout_option_editor()
                return True

            for box in self.option_inputs.values():
                if box.handle_event(event): return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] > self.sidebar_w:
                if event.button == 4:
                    self.option_form_scroll = max(0, self.option_form_scroll - 40)
                    self._layout_option_editor()
                    return True
                elif event.button == 5:
                    self.option_form_scroll = min(self.max_option_scroll, self.option_form_scroll + 40)
                    self._layout_option_editor()
                    return True
                elif event.button == 1:
                    FocusManager.clear_focus()
                    if self.option_thumb_rect and self.option_thumb_rect.collidepoint(event.pos):
                        self.dragging_option_scroll = True
                        self.option_scroll_start_y = event.pos[1]
                        self.option_scroll_start_offset = self.option_form_scroll
                        return True

                    if self.opt_save_btn.collidepoint(event.pos):
                        self.save_editing_option()
                        return True
                    elif self.opt_code_btn.collidepoint(event.pos):
                        self.save_editing_option()
                        path = os.path.join(self.xml_dir, self.current_file)
                        return {"action": "open_in_code", "path": path}
                    elif self.opt_back_btn.collidepoint(event.pos):
                        self.cancel_editing_option()
                        return True
                    elif self.opt_delete_btn.collidepoint(event.pos):
                        self.delete_editing_option()
                        return True

        # 5. Handle Node Overview Events (Cards View)
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
                        if self.sidebar_thumb_rect and self.sidebar_thumb_rect.collidepoint(mx, my):
                            self.dragging_sidebar = True
                            self.sidebar_start_y = my
                            self.sidebar_start_offset = self.sidebar_scroll
                            return True
                        if self.new_node_btn.collidepoint(mx, my):
                            default_pfx = "greeting" if self.current_file == "chat.xml" else ("milestones" if self.current_file == "milestones.xml" else "Quest: New Node")
                            self.new_node_modal.open(self.width//2, self.height//2, default_pfx)
                            return True
                        list_y = self.y_offset + 120 - self.sidebar_scroll
                        for n_id in self.nodes.keys():
                            if pygame.Rect(10, list_y, self.sidebar_w - 30, 25).collidepoint(mx, my):
                                if list_y > self.y_offset + 115:
                                    self.selected_node = n_id
                                    self.form_scroll = 0
                                return True
                            list_y += 30
                else:
                    if event.button == 4:
                        self.form_scroll = max(0, self.form_scroll - 40)
                        return True
                    elif event.button == 5:
                        self.form_scroll = min(self.max_form_scroll, self.form_scroll + 40)
                        return True
                    elif event.button == 1:
                        if self.form_thumb_rect and self.form_thumb_rect.collidepoint(mx, my):
                            self.dragging_form = True
                            self.form_start_y = my
                            self.form_start_offset = self.form_scroll
                            return True
                        if self.save_xml_btn.collidepoint(mx, my):
                            self.save_xml()
                            return True
                        if self.code_btn.collidepoint(mx, my):
                            self.save_xml()
                            path = os.path.join(self.xml_dir, self.current_file)
                            return {"action": "open_in_code", "path": path}

                        if self.selected_node:
                            rects, add_btn, total_h = self._get_cards_layout()
                            if self.del_node_btn.collidepoint(mx, my):
                                del self.nodes[self.selected_node]
                                self.selected_node = None
                                self.save_xml()
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
                                    self.save_xml()
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

    # ------------------------------------------------------------------
    # RENDERING
    # ------------------------------------------------------------------
    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect)
        mouse_pos = pygame.mouse.get_pos()
        
        # 1. Sidebar List
        list_view_rect = pygame.Rect(0, self.y_offset + 115, self.sidebar_w, self.height - self.y_offset - 115)
        surface.set_clip(list_view_rect)
        list_y = self.y_offset + 120 - self.sidebar_scroll
        for n_id in self.nodes.keys():
            r = pygame.Rect(10, list_y, self.sidebar_w - 30, 25)
            if n_id == self.selected_node:
                pygame.draw.rect(surface, UITheme.LIST_HOVER, r, border_radius=4)
            elif r.collidepoint(mouse_pos):
                pygame.draw.rect(surface, UITheme.HOVER_BG, r, border_radius=4)
            lbl = (n_id[:25] + '..') if len(n_id) > 27 else n_id
            surface.blit(self.font.render(lbl, True, UITheme.TEXT), (15, list_y + 4))
            list_y += 30
        surface.set_clip(None)
        
        # 2. Sidebar Header
        sidebar_header_rect = pygame.Rect(0, self.y_offset, self.sidebar_w, 115)
        pygame.draw.rect(surface, UITheme.PANEL_BG, sidebar_header_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset), (self.sidebar_w, self.height), 2)
        surface.blit(self.font.render("Dialog Nodes", True, UITheme.WARNING), (20, self.y_offset + 10))
        
        self.file_dropdown.draw(surface)
        draw_styled_button(surface, self.new_node_btn, "+ New Node", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)

        self.max_sidebar_scroll = max(0, len(self.nodes) * 30 + 10 - list_view_rect.height)
        if self.max_sidebar_scroll > 0:
            track_rect = pygame.Rect(self.sidebar_w - 8, list_view_rect.y, 8, list_view_rect.height)
            thumb_h = max(20, (list_view_rect.height / (list_view_rect.height + self.max_sidebar_scroll)) * list_view_rect.height)
            thumb_y = list_view_rect.y + (self.sidebar_scroll / self.max_sidebar_scroll) * (list_view_rect.height - thumb_h)
            self.sidebar_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.sidebar_thumb_rect, border_radius=4)

        # 3. Main Area Rendering
        if self.editing_context:
            self._draw_option_editor(surface, mouse_pos)
        elif self.selected_node:
            self._draw_node_overview(surface, mouse_pos)

        if self.file_dropdown.expanded:
            self.file_dropdown.draw_list(surface)

        if self.new_node_modal.active:
            self.new_node_modal.draw(surface)

    def _draw_node_overview(self, surface, mouse_pos):
        rects, add_btn, total_h = self._get_cards_layout()
        form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset + 60, self.width - self.sidebar_w, self.height - self.y_offset - 60)
        
        surface.set_clip(form_view_rect)
        for r in rects:
            pygame.draw.rect(surface, UITheme.PANEL_BG, r["card"], border_radius=6)
            pygame.draw.rect(surface, UITheme.BORDER, r["card"], 1, border_radius=6)
            
            opt = self.nodes[self.selected_node]["options"][r["idx"]]
            tag = opt.get("_tag", "options")
            stage = f"[{opt.get('stage')}] " if opt.get('stage') else ""
            
            snippet = ""
            if tag == "options":
                q = opt.get('player_question', '')
                a = opt.get('npc_answer', '')
                if q and a: snippet = f"{stage}Q: {q} | A: {a}"
                elif q: snippet = f"{stage}Q: {q}"
                elif a: snippet = f"{stage}A: {a}"
                else: snippet = f"{stage}Priority: {opt.get('priority', '10')}"
            elif tag == "milestone":
                snippet = f"Milestone: {opt.get('name', '')} ({opt.get('type', '')} {opt.get('entity', '')}) - \"{opt.get('message', '')}\""
            else:
                snippet = f"[{tag}] " + ", ".join(f"{k}={v}" for k, v in opt.items() if k != "_tag")
                
            if len(snippet) > 85: snippet = snippet[:82] + "..."
            
            surface.blit(self.font.render(f"[{tag}] {stage}", True, UITheme.WARNING), (r["card"].x + 10, r["card"].y + 10))
            surface.blit(self.font.render(snippet, True, UITheme.TEXT), (r["card"].x + 10, r["card"].y + 40))
            
            draw_styled_button(surface, r["edit"], "Edit", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
            draw_styled_button(surface, r["delete"], "Del", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
            
        draw_styled_button(surface, add_btn, "+ Add Option" if self.current_file != "milestones.xml" else "+ Add Milestone", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        surface.set_clip(None)

        # Overview Header
        right_header_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, 60)
        pygame.draw.rect(surface, UITheme.BG, right_header_rect) 
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset + 59), (self.width, self.y_offset + 59))
        
        node_lbl = f"Node: {self.selected_node}"
        surface.blit(self.font.render(node_lbl[:35], True, UITheme.WARNING), (self.sidebar_w + 20, self.y_offset + 22))
        
        draw_styled_button(surface, self.save_xml_btn, "Save XML", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.code_btn, "Code", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)
        draw_styled_button(surface, self.del_node_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

        self.max_form_scroll = max(0, total_h - (self.y_offset + 60 + form_view_rect.height))
        if self.max_form_scroll > 0:
            track_rect = pygame.Rect(self.width - 8, form_view_rect.y, 8, form_view_rect.height)
            thumb_h = max(20, (form_view_rect.height / (form_view_rect.height + self.max_form_scroll)) * form_view_rect.height)
            thumb_y = form_view_rect.y + (self.form_scroll / self.max_form_scroll) * (form_view_rect.height - thumb_h)
            self.form_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.form_thumb_rect, border_radius=4)

    def _draw_option_editor(self, surface, mouse_pos):
        form_h = self.height - self.y_offset - 60
        form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset + 60, self.width - self.sidebar_w, form_h)

        surface.set_clip(form_view_rect)
        for f in self.option_fields_order:
            box = self.option_inputs[f]
            friendly = FRIENDLY_NAMES.get(f, f.replace("_", " ").title())
            title_text = f"{friendly} ({f}):"
            
            surface.blit(self.font.render(title_text, True, UITheme.TEXT_DIM), (box.rect.x, box.rect.y - 20))
            box.draw(surface)

        if self.add_field_dd:
            self.add_field_dd.draw(surface)

        draw_styled_button(surface, self.opt_save_btn, "Save Option", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.opt_code_btn, "Code", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)
        draw_styled_button(surface, self.opt_back_btn, "Cancel", self.font, mouse_pos, UITheme.BORDER, UITheme.BORDER_ACTIVE)
        if self.editing_context.get("type") == "edit":
            draw_styled_button(surface, self.opt_delete_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

        # Draw overlays on top
        for f in self.option_fields_order:
            box = self.option_inputs[f]
            if isinstance(box, UIDropdown): box.draw_list(surface)
        if self.add_field_dd and self.add_field_dd.expanded:
            self.add_field_dd.draw_list(surface)

        surface.set_clip(None)

        # Option Editor Header
        header_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, 60)
        pygame.draw.rect(surface, UITheme.BG, header_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset + 59), (self.width, self.y_offset + 59))
        
        mode_title = "Edit" if self.editing_context.get("type") == "edit" else "New"
        tag_name = self.option_inputs.get("_tag").text if self.option_inputs.get("_tag") else "Option"
        surface.blit(self.font.render(f"{mode_title} {tag_name.capitalize()}  |  Node: {self.selected_node}", True, UITheme.WARNING), (self.sidebar_w + 20, self.y_offset + 22))

        if self.max_option_scroll > 0:
            track_rect = pygame.Rect(self.width - 8, form_view_rect.y, 8, form_view_rect.height)
            thumb_h = max(20, (form_view_rect.height / (form_view_rect.height + self.max_option_scroll)) * form_view_rect.height)
            thumb_y = form_view_rect.y + (self.option_form_scroll / self.max_option_scroll) * (form_view_rect.height - thumb_h)
            self.option_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.option_thumb_rect, border_radius=4)