import pygame
import os
import xml.etree.ElementTree as ET
from editor.config import GAME_ROOT
from editor.ui import UITextBox, UIDropdown, UITextArea, UIAttributeList, UITheme, draw_styled_button

class FormModal:
    """A dynamic modal using UITextBox and UIDropdown to handle Node and Option editing."""
    def __init__(self, width, height, font, item_tiles):
        self.rect = pygame.Rect(0, 0, width, height)
        self.font = font
        self.item_tiles = item_tiles
        self.active = False
        
        self.title = ""
        self.fields = []
        self.inputs = {}
        self.context = {}

        self.save_btn = pygame.Rect(0, 0, 90, 30)
        self.delete_btn = pygame.Rect(0, 0, 90, 30)
        self.cancel_btn = pygame.Rect(0, 0, 90, 30)

        self.scroll_y = 0
        self.max_scroll = 0
        self.dragging_scroll = False
        self.scroll_start_y = 0
        self.scroll_start_offset = 0

    def open(self, title, fields, values_dict, context, center_x, center_y):
        self.title = title
        self.fields = fields
        self.context = context
        self.active = True
        self.inputs.clear()
        self.scroll_y = 0
        
        current_y = 45
        self.rect.width = 800
        
        for f in self.fields:
            val = str(values_dict.get(f, ""))
            
            if f in ["req_level", "gain_xp"]:
                current_y += 30
                
            if f in ["player_question", "npc_answer", "tip"]:
                f_height = 80
            elif f in ["req_level", "gain_xp"]:
                f_height = 145 
            else:
                f_height = 28
                
            f_rect = pygame.Rect(140, current_y, self.rect.width - 160, f_height)
            
            if f == "_tag":
                opts = [
                    {"label": "options", "value": "options"},
                    {"label": "player_question", "value": "player_question"},
                    {"label": "npc_awnser", "value": "npc_awnser"},
                    {"label": "npc_rqst", "value": "npc_rqst"},
                    {"label": "player_award", "value": "player_award"}
                ]
                self.inputs[f] = UIDropdown(0, 0, f_rect.width, f_rect.height, self.font, opts, val)
                
            elif f == "dialog_type":
                opts = [{"label": "None", "value": ""}, {"label": "once", "value": "once"}]
                self.inputs[f] = UIDropdown(0, 0, f_rect.width, f_rect.height, self.font, opts, val)
                
            elif f == "priority":
                opts = [{"label": str(x), "value": str(x)} for x in range(0, 101, 10)]
                self.inputs[f] = UIDropdown(0, 0, f_rect.width, f_rect.height, self.font, opts, val)
                
            elif f in ["award_item", "rqst_item", "req_item"]:
                opts = [{"label": "None", "value": "", "icon": None}]
                for item_name, icon in sorted(self.item_tiles.items()):
                    opts.append({"label": item_name, "value": f"[{item_name}]", "icon": icon})
                self.inputs[f] = UIDropdown(0, 0, f_rect.width, f_rect.height, self.font, opts, val, searchable=True)
                
            elif f in ["req_level", "gain_xp"]:
                self.inputs[f] = UIAttributeList(0, 0, f_rect.width, f_rect.height, self.font, val)
            elif f in ["player_question", "npc_answer", "tip"]:
                self.inputs[f] = UITextArea(0, 0, f_rect.width, f_rect.height, self.font, val)
            else:
                self.inputs[f] = UITextBox(0, 0, f_rect.width, f_rect.height, self.font, val)

            self.inputs[f]._rel_rect = f_rect
            current_y += f_height + 10

        self.max_scroll = max(0, current_y + 50 - 600)
        self.rect.height = min(600, current_y + 50) 
        self.rect.center = (center_x, center_y)
        self.update_layout()

    def update_layout(self):
        for f, box in self.inputs.items():
            box.rect.x = self.rect.x + box._rel_rect.x
            box.rect.y = self.rect.y + box._rel_rect.y - self.scroll_y
            if hasattr(box, '_relayout'):
                box._relayout()
            if isinstance(box, UIDropdown):
                box.list_rect.x = box.rect.x
                box.list_rect.y = box.rect.bottom

        btn_y = self.rect.bottom - 45
        self.save_btn.topleft = (self.rect.x + 50, btn_y)
        self.delete_btn.topleft = (self.rect.x + 160, btn_y)
        self.cancel_btn.topleft = (self.rect.x + 270, btn_y)

    def handle_event(self, event):
        if not self.active: return None
        
        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_scroll = False

        if event.type == pygame.MOUSEMOTION:
            if getattr(self, 'dragging_scroll', False) and self.max_scroll > 0:
                dy = event.pos[1] - self.scroll_start_y
                track_h = self.rect.height - 90
                content_h = track_h + self.max_scroll
                thumb_h = max(20, (track_h / content_h) * track_h)
                track_space = track_h - thumb_h
                if track_space > 0:
                    scroll_per_pixel = self.max_scroll / track_space
                    self.scroll_y = max(0, min(self.max_scroll, self.scroll_start_offset + dy * scroll_per_pixel))
                    self.update_layout()
                return True
                
        for f, box in self.inputs.items():
            if hasattr(box, 'expanded') and box.expanded:
                if box.handle_event(event): return True
                
        consumed = False
        for f, box in self.inputs.items():
            if hasattr(box, 'expanded') and box.expanded: continue 
            if box.handle_event(event): consumed = True

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if event.button == 4:
                    self.scroll_y = max(0, self.scroll_y - 30)
                    self.update_layout()
                    return True
                elif event.button == 5:
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 30)
                    self.update_layout()
                    return True
                    
            if event.button == 1:
                if self.max_scroll > 0:
                    track_rect = pygame.Rect(self.rect.right - 8, self.rect.y + 40, 8, self.rect.height - 90)
                    content_h = (self.rect.height - 90) + self.max_scroll
                    thumb_h = max(20, ((self.rect.height - 90) / content_h) * (self.rect.height - 90))
                    thumb_y = self.rect.y + 40 + (self.scroll_y / self.max_scroll) * (self.rect.height - 90 - thumb_h) if self.max_scroll > 0 else self.rect.y + 40
                    thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
                    
                    if thumb_rect.collidepoint(event.pos):
                        self.dragging_scroll = True
                        self.scroll_start_y = event.pos[1]
                        self.scroll_start_offset = self.scroll_y
                        return True
                    elif track_rect.collidepoint(event.pos):
                        if event.pos[1] < thumb_rect.y:
                            self.scroll_y = max(0, self.scroll_y - 100)
                        else:
                            self.scroll_y = min(self.max_scroll, self.scroll_y + 100)
                        self.update_layout()
                        return True

            if self.save_btn.collidepoint(event.pos):
                self.active = False
                values = {f: box.text for f, box in self.inputs.items()}
                return {"action": "save", "values": values, "context": self.context}
            elif self.delete_btn.collidepoint(event.pos):
                self.active = False
                return {"action": "delete", "context": self.context}
            elif self.cancel_btn.collidepoint(event.pos):
                self.active = False
                return True
                
        return consumed

    def _shift_component(self, comp, dx, dy):
        comp.rect.x += dx
        comp.rect.y += dy
        if hasattr(comp, 'list_rect'):
            comp.list_rect.x += dx
            comp.list_rect.y += dy
        if hasattr(comp, 'thumb_rect') and comp.thumb_rect:
            comp.thumb_rect.x += dx
            comp.thumb_rect.y += dy
        if hasattr(comp, 'data') and isinstance(comp.data, dict):
            for attr, info in comp.data.items():
                if "cb_rect" in info:
                    info["cb_rect"].x += dx
                    info["cb_rect"].y += dy
                if "box" in info:
                    self._shift_component(info["box"], dx, dy)

    def draw(self, surface):
        if not self.active: return
        
        shadow = self.rect.copy()
        shadow.y += 10
        pygame.draw.rect(surface, (0, 0, 0, 150), shadow, border_radius=8)

        pygame.draw.rect(surface, UITheme.PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.rect, 2, border_radius=8)
        surface.blit(self.font.render(self.title, True, UITheme.WARNING), (self.rect.x + 20, self.rect.y + 15))
        pygame.draw.line(surface, UITheme.BORDER, (self.rect.x, self.rect.y + 40), (self.rect.right, self.rect.y + 40))
        
        clip_rect = pygame.Rect(self.rect.x, self.rect.y + 40, self.rect.width, self.rect.height - 90)
        content_surf = pygame.Surface((clip_rect.width, clip_rect.height), pygame.SRCALPHA)
        content_surf.fill((37, 37, 40)) 
        
        dx, dy = -clip_rect.x, -clip_rect.y
        for f, box in self.inputs.items():
            self._shift_component(box, dx, dy)

        for f in self.fields:
            box = self.inputs[f]
            if f == "req_level":
                content_surf.blit(self.font.render("Required Level:", True, UITheme.WARNING), (10, box.rect.y - 25))
            elif f == "gain_xp":
                content_surf.blit(self.font.render("Gain XP:", True, UITheme.WARNING), (10, box.rect.y - 25))
            
            if f in ["req_level", "gain_xp"]:
                lbl = "" 
            else:
                lbl = f.replace("_", " ").title()[:15] + ":"
                
            if lbl: 
                content_surf.blit(self.font.render(lbl, True, UITheme.TEXT_DIM), (10, box.rect.y + 5))
            
            box.draw(content_surf)

        surface.blit(content_surf, clip_rect.topleft)
        self.update_layout()
        
        if self.max_scroll > 0:
            track_rect = pygame.Rect(self.rect.right - 8, self.rect.y + 40, 8, self.rect.height - 90)
            content_h = (self.rect.height - 90) + self.max_scroll
            thumb_h = max(20, ((self.rect.height - 90) / content_h) * (self.rect.height - 90))
            thumb_y = self.rect.y + 40 + (self.scroll_y / self.max_scroll) * (self.rect.height - 90 - thumb_h)
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, thumb_rect, border_radius=4)

        mouse_pos = pygame.mouse.get_pos()
        draw_styled_button(surface, self.save_btn, "Save", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
        draw_styled_button(surface, self.delete_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
        draw_styled_button(surface, self.cancel_btn, "Cancel", self.font, mouse_pos, UITheme.BORDER, UITheme.BORDER_ACTIVE)

        for f in self.fields:
            box = self.inputs[f]
            if hasattr(box, 'draw_list'):
                box.draw_list(surface)

class DialogEditor:
    def __init__(self, y_offset, width, height, font, item_tiles):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        
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
        
        # Build dialog directory & defaults if they don't exist
        if not os.path.exists(self.xml_dir):
            os.makedirs(self.xml_dir)
            
        default_files = ["chat.xml", "item_quests.xml", "quests.xml", "tips.xml"]
        for df in default_files:
            df_path = os.path.join(self.xml_dir, df)
            if not os.path.exists(df_path):
                root = ET.Element("npc_dialog")
                ET.ElementTree(root).write(df_path)
        
        self.modal = FormModal(400, 300, font, item_tiles)
        
        self.file_dropdown = UIDropdown(10, self.y_offset + 35, self.sidebar_w - 20, 30, self.font, [])
        self.new_node_btn = pygame.Rect(10, self.y_offset + 75, self.sidebar_w - 20, 32)
        self.save_xml_btn = pygame.Rect(self.sidebar_w + 300, y_offset + 12, 120, 35)
        
        self.opt_fields = [
            "_tag", "player_question", "npc_answer", "unlock_flag", "priority", "dialog_type", 
            "award_item", "rqst_item", "req_item", "tip", "complete_flag", "npc_state_friendly", 
            "npc_state_static", "req_level", "gain_xp"
        ]
        
        self.refresh_files()

    def resize(self, width, height):
        self.width = width
        self.height = height

    def refresh_files(self):
        self.files = sorted([f for f in os.listdir(self.xml_dir) if f.endswith('.xml')])
        opts = [{"label": f, "value": f} for f in self.files]
        self.file_dropdown.options = opts
        if not self.current_file and self.files:
            self.current_file = self.files[0]
            self.file_dropdown.selected_value = self.current_file
            self.file_dropdown._update_label()
        self.load_xml()

    def load_xml(self):
        self.nodes.clear()
        self.selected_node = None
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
                    d["_tag"] = child.tag
                    if child.tag == "player_question" and "p" in d:
                        d["player_question"] = d.pop("p")
                    elif child.tag == "npc_awnser" and "n" in d:
                        d["npc_answer"] = d.pop("n")
                        
                    options.append(d)
                    
                self.nodes[n_id] = {"options": options}
        except Exception as e:
            pass

    def save_xml(self):
        if not self.current_file: return
        path = os.path.join(self.xml_dir, self.current_file)
        root = ET.Element("npc_dialog")
        for n_id, data in self.nodes.items():
            node_el = ET.SubElement(root, "node", {"id": n_id})
            
            for opt in data["options"]:
                tag = opt.get("_tag", "options")
                clean_opt = {k: v for k, v in opt.items() if str(v).strip() and k != "_tag"}
                
                if tag == "player_question" and "player_question" in clean_opt:
                    clean_opt["p"] = clean_opt.pop("player_question")
                elif tag == "npc_awnser" and "npc_answer" in clean_opt:
                    clean_opt["n"] = clean_opt.pop("npc_answer")
                    
                ET.SubElement(node_el, tag, clean_opt)
                
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ", level=0) 
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def get_layout_rects(self):
        if not self.selected_node: return [], None, None, 0
        
        current_y = self.y_offset + 70 - self.form_scroll
        del_node_btn = pygame.Rect(self.width - 150, self.y_offset + 12, 130, 35)
        
        rects = []
        for i, opt in enumerate(self.nodes[self.selected_node]["options"]):
            card_rect = pygame.Rect(self.sidebar_w + 20, current_y, self.width - self.sidebar_w - 60, 75)
            edit_btn = pygame.Rect(card_rect.right - 150, card_rect.y + 22, 60, 30)
            del_btn = pygame.Rect(card_rect.right - 80, card_rect.y + 22, 60, 30)
            
            rects.append({"card": card_rect, "edit": edit_btn, "delete": del_btn, "idx": i})
            current_y += 85
            
        add_btn = pygame.Rect(self.sidebar_w + 20, current_y, 140, 35)
        return rects, add_btn, del_node_btn, current_y + 50

    def handle_event(self, event):
        if self.modal.active:
            res = self.modal.handle_event(event)
            if res is True: return True
            if res:
                action = res["action"]
                ctx = res["context"]
                vals = res.get("values", {})
                
                if action == "save":
                    if ctx["type"] == "new_node":
                        n_id = vals["id"].strip()
                        if n_id and n_id not in self.nodes:
                            self.nodes[n_id] = {"options": []}
                            self.selected_node = n_id
                    elif ctx["type"] == "option":
                        self.nodes[self.selected_node]["options"][ctx["idx"]] = vals
                    elif ctx["type"] == "new_option":
                        self.nodes[self.selected_node]["options"].append(vals)
                        
                elif action == "delete":
                    if ctx["type"] == "option":
                        self.nodes[self.selected_node]["options"].pop(ctx["idx"])
                        
                return True

        # Process the Dropdown before other clicks, prioritizing it if it's expanded
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
            
        if event.type == pygame.MOUSEMOTION:
            if self.dragging_sidebar and self.sidebar_thumb_rect and self.max_sidebar_scroll > 0:
                dy = event.pos[1] - self.sidebar_start_y
                track_h = self.height - self.y_offset - 115
                thumb_h = self.sidebar_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    self.sidebar_scroll = max(0, min(self.max_sidebar_scroll, self.sidebar_start_offset + dy * (self.max_sidebar_scroll / track_space)))
                return True
                
            if self.dragging_form and self.form_thumb_rect and self.max_form_scroll > 0:
                dy = event.pos[1] - self.form_start_y
                track_h = self.height - self.y_offset - 60
                thumb_h = self.form_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    self.form_scroll = max(0, min(self.max_form_scroll, self.form_start_offset + dy * (self.max_form_scroll / track_space)))
                return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx <= self.sidebar_w:
                if event.button == 4:
                    self.sidebar_scroll = max(0, self.sidebar_scroll - 40)
                    return True
                elif event.button == 5:
                    self.sidebar_scroll = min(self.max_sidebar_scroll, self.sidebar_scroll + 40)
                    return True
                    
                if event.button == 1:
                    if self.sidebar_thumb_rect and self.sidebar_thumb_rect.collidepoint(mx, my):
                        self.dragging_sidebar = True
                        self.sidebar_start_y = my
                        self.sidebar_start_offset = self.sidebar_scroll
                        return True
                        
                    if self.new_node_btn.collidepoint(mx, my):
                        self.modal.open("New Node", ["id"], {"id": "new_node"}, {"type": "new_node"}, self.width//2, self.height//2)
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
                    
                if event.button == 1:
                    if self.form_thumb_rect and self.form_thumb_rect.collidepoint(mx, my):
                        self.dragging_form = True
                        self.form_start_y = my
                        self.form_start_offset = self.form_scroll
                        return True
                        
                    if self.save_xml_btn.collidepoint(mx, my):
                        self.save_xml()
                        return True
                        
                    if self.selected_node:
                        rects, add_btn, del_node_btn, _ = self.get_layout_rects()
                        if del_node_btn and del_node_btn.collidepoint(mx, my):
                            del self.nodes[self.selected_node]
                            self.selected_node = None
                            return True
                            
                        if add_btn and add_btn.collidepoint(mx, my):
                            self.modal.open("New Option", self.opt_fields, {"_tag": "options"}, {"type": "new_option"}, self.width//2, self.height//2)
                            return True
                            
                        for r in rects:
                            if r["edit"].collidepoint(mx, my):
                                opt_data = self.nodes[self.selected_node]["options"][r["idx"]]
                                self.modal.open("Edit Option", self.opt_fields, opt_data, {"type": "option", "idx": r["idx"]}, self.width//2, self.height//2)
                                return True
                            if r["delete"].collidepoint(mx, my):
                                self.nodes[self.selected_node]["options"].pop(r["idx"])
                                return True
        return False

    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect)
        
        list_view_rect = pygame.Rect(0, self.y_offset + 115, self.sidebar_w, self.height - self.y_offset - 115)
        surface.set_clip(list_view_rect)
        
        mouse_pos = pygame.mouse.get_pos()
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

        if self.selected_node:
            rects, add_btn, del_node_btn, total_h = self.get_layout_rects()
            
            form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset + 60, self.width - self.sidebar_w, self.height - self.y_offset - 60)
            surface.set_clip(form_view_rect)
            
            for r in rects:
                pygame.draw.rect(surface, UITheme.PANEL_BG, r["card"], border_radius=6)
                pygame.draw.rect(surface, UITheme.BORDER, r["card"], 1, border_radius=6)
                
                opt = self.nodes[self.selected_node]["options"][r["idx"]]
                tag = opt.get("_tag", "options")
                
                snippet = ""
                if tag == "player_question": snippet = f"Q: {opt.get('player_question', '')}"
                elif tag == "npc_awnser": snippet = f"A: {opt.get('npc_answer', '')}"
                elif tag == "options": snippet = f"Q: {opt.get('player_question', '')} | A: {opt.get('npc_answer', '')}"
                else: snippet = f"{tag} -> {opt.get('rqst_item', opt.get('award_item', ''))}"
                    
                if len(snippet) > 85: snippet = snippet[:82] + "..."
                
                surface.blit(self.font.render(f"[{tag}]", True, UITheme.WARNING), (r["card"].x + 10, r["card"].y + 10))
                surface.blit(self.font.render(snippet, True, UITheme.TEXT), (r["card"].x + 10, r["card"].y + 40))
                
                draw_styled_button(surface, r["edit"], "Edit", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
                draw_styled_button(surface, r["delete"], "Del", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
                
            draw_styled_button(surface, add_btn, "+ Add Option", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            surface.set_clip(None)

            right_header_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, 60)
            pygame.draw.rect(surface, UITheme.BG, right_header_rect) 
            pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset + 59), (self.width, self.y_offset + 59))
            
            surface.blit(self.font.render(f"Node: {self.selected_node}", True, UITheme.WARNING), (self.sidebar_w + 20, self.y_offset + 22))
            
            draw_styled_button(surface, self.save_xml_btn, "Save XML", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
            draw_styled_button(surface, del_node_btn, "Delete Node", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)

            self.max_form_scroll = max(0, total_h - (self.y_offset + 60 + form_view_rect.height))
            if self.max_form_scroll > 0:
                track_rect = pygame.Rect(self.width - 8, form_view_rect.y, 8, form_view_rect.height)
                thumb_h = max(20, (form_view_rect.height / (form_view_rect.height + self.max_form_scroll)) * form_view_rect.height)
                thumb_y = form_view_rect.y + (self.form_scroll / self.max_form_scroll) * (form_view_rect.height - thumb_h)
                self.form_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
                pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.form_thumb_rect, border_radius=4)

        if self.file_dropdown.expanded:
            self.file_dropdown.draw_list(surface)
            
        if self.modal.active: self.modal.draw(surface)