import pygame
import os
import xml.etree.ElementTree as ET
from editor.config import GAME_ROOT
from editor.ui import UITextBox, UIDropdown, UITextArea, UIAttributeList

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
        self.save_btn = pygame.Rect(0, 0, 80, 30)
        self.delete_btn = pygame.Rect(0, 0, 80, 30)
        self.cancel_btn = pygame.Rect(0, 0, 80, 30)

        # Added dynamic scroll support
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
            
            # Inject spacing for the group headers
            if f in ["req_level", "gain_xp"]:
                current_y += 30
            
            # Text Areas get much more vertical height
            if f in ["player_question", "npc_answer", "ingredients", "results"]:
                f_height = 80
            elif f in ["req_level", "gain_xp"]:
                f_height = 80 # Compact 4-column height
            else:
                f_height = 28
                
            f_rect = pygame.Rect(140, current_y, self.rect.width - 160, f_height)
            
            # Create Component Placeholder with temporary (0,0) position
            if f == "dialog_type":
                opts = [{"label": "None", "value": ""}, {"label": "once", "value": "once"}]
                self.inputs[f] = UIDropdown(0, 0, f_rect.width, f_rect.height, self.font, opts, val)
                
            elif f == "priority":
                opts = [{"label": str(x), "value": str(x)} for x in range(0, 101, 10)]
                self.inputs[f] = UIDropdown(0, 0, f_rect.width, f_rect.height, self.font, opts, val)
                
            elif f == "award_item":
                opts = [{"label": "None", "value": "", "icon": None}]
                for item_name, icon in sorted(self.item_tiles.items()):
                    opts.append({"label": item_name, "value": f"[{item_name}]", "icon": icon})
                self.inputs[f] = UIDropdown(0, 0, f_rect.width, f_rect.height, self.font, opts, val, searchable=True)
                
            elif f in ["req_level", "gain_xp"]:
                self.inputs[f] = UIAttributeList(0, 0, f_rect.width, f_rect.height, self.font, val)
            elif f in ["player_question", "npc_answer"]:
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
                
        # Expanded Dropdown priority
        for f, box in self.inputs.items():
            if hasattr(box, 'expanded') and box.expanded:
                if box.handle_event(event): return True
                
        consumed = False
        for f, box in self.inputs.items():
            if hasattr(box, 'expanded') and box.expanded: continue 
            if box.handle_event(event): consumed = True

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Scroll wheel handling
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
                # Custom Drag Scrollbar check
                if self.max_scroll > 0:
                    track_rect = pygame.Rect(self.rect.right - 12, self.rect.y + 40, 12, self.rect.height - 90)
                    content_h = (self.rect.height - 90) + self.max_scroll
                    thumb_h = max(20, ((self.rect.height - 90) / content_h) * (self.rect.height - 90))
                    thumb_y = self.rect.y + 40 + (self.scroll_y / self.max_scroll) * (self.rect.height - 90 - thumb_h) if self.max_scroll > 0 else self.rect.y + 40
                    thumb_rect = pygame.Rect(track_rect.x, thumb_y, 12, thumb_h)
                    
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

    def draw(self, surface):
        if not self.active: return
        s = pygame.Surface((self.rect.width, self.rect.height))
        s.fill((40, 40, 50))
        surface.blit(s, self.rect.topleft)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2)
        
        surface.blit(self.font.render(self.title, True, (255, 255, 0)), (self.rect.x + 20, self.rect.y + 15))
        
        # Scissor area for scroll clipping
        clip_rect = pygame.Rect(self.rect.x, self.rect.y + 40, self.rect.width, self.rect.height - 90)
        surface.set_clip(clip_rect)

        for f in self.fields:
            box = self.inputs[f]
            
            # Draw Dynamic Headers
            if f == "req_level":
                surface.blit(self.font.render("Required Level:", True, (255, 200, 0)), (self.rect.x + 10, box.rect.y - 25))
            elif f == "gain_xp":
                surface.blit(self.font.render("Gain XP:", True, (255, 200, 0)), (self.rect.x + 10, box.rect.y - 25))
            
            # Format labels nicely based on attribute names
            if f in ["req_level", "gain_xp"]:
                lbl = "" # Handled by the headers above
            else:
                lbl = f.replace("_", " ").title()[:13] + ":"
                
            if lbl: surface.blit(self.font.render(lbl, True, (180, 180, 180)), (self.rect.x + 10, box.rect.y + 5))
            box.draw(surface)

        surface.set_clip(None)
        
        # Draw Scrollbar
        if self.max_scroll > 0:
            track_rect = pygame.Rect(self.rect.right - 12, self.rect.y + 40, 12, self.rect.height - 90)
            pygame.draw.rect(surface, (30, 30, 35), track_rect)
            
            content_h = (self.rect.height - 90) + self.max_scroll
            thumb_h = max(20, ((self.rect.height - 90) / content_h) * (self.rect.height - 90))
            thumb_y = self.rect.y + 40 + (self.scroll_y / self.max_scroll) * (self.rect.height - 90 - thumb_h)
            
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, 12, thumb_h)
            pygame.draw.rect(surface, (150, 150, 150), thumb_rect)

        pygame.draw.rect(surface, (0, 150, 0), self.save_btn)
        surface.blit(self.font.render("Save", True, (255, 255, 255)), (self.save_btn.x + 20, self.save_btn.y + 5))
        pygame.draw.rect(surface, (150, 0, 0), self.delete_btn)
        surface.blit(self.font.render("Delete", True, (255, 255, 255)), (self.delete_btn.x + 15, self.delete_btn.y + 5))
        pygame.draw.rect(surface, (100, 100, 100), self.cancel_btn)
        surface.blit(self.font.render("Cancel", True, (255, 255, 255)), (self.cancel_btn.x + 15, self.cancel_btn.y + 5))

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
        
        self.cam_x = 0
        self.cam_y = 0
        self.dragging_camera = False
        self.drag_start = (0, 0)
        
        self.nodes = {} 
        self.dragging_node = None
        self.node_drag_offset = (0, 0)
        
        self.xml_dir = os.path.join(GAME_ROOT, 'lib', 'data', 'npc')
        self.xml_path = os.path.join(self.xml_dir, 'dialogs.xml')
        
        self.modal = FormModal(400, 300, font, item_tiles)
        
        self.new_node_btn = pygame.Rect(20, y_offset + 20, 120, 30)
        self.save_xml_btn = pygame.Rect(150, y_offset + 20, 120, 30)
        
        # Uses req_level and gain_xp to trigger the dynamic UIAttributeList
        self.opt_fields = [
            "player_question", "npc_answer", "unlock_flag", "priority", "dialog_type", "award_item",
            "req_level", "gain_xp"
        ]
        
        self.load_xml()

    def resize(self, width, height):
        self.width = width
        self.height = height

    def load_xml(self):
        self.nodes.clear()
        if not os.path.exists(self.xml_dir): os.makedirs(self.xml_dir)
        
        if not os.path.exists(self.xml_path):
            root = ET.Element("npc_dialog")
            tree = ET.ElementTree(root)
            tree.write(self.xml_path)

        try:
            tree = ET.parse(self.xml_path)
            root = tree.getroot()

            for node_el in root.findall('node'):
                n_id = node_el.get('id')
                nx = int(node_el.get('x', 100))
                ny = int(node_el.get('y', 100))
                
                options = []
                for opt_el in node_el.findall('options'):
                    options.append(opt_el.attrib.copy())
                    
                self.nodes[n_id] = {
                    "options": options,
                    "rect": pygame.Rect(nx, ny, 280, 100) 
                }
        except Exception as e:
            print(f"Error loading dialogs XML: {e}")

    def save_xml(self):
        root = ET.Element("npc_dialog")
        for n_id, data in self.nodes.items():
            attribs = {"id": n_id, "x": str(data["rect"].x), "y": str(data["rect"].y)}
            node_el = ET.SubElement(root, "node", attribs)
            
            for opt in data["options"]:
                clean_opt = {k: v for k, v in opt.items() if str(v).strip()}
                ET.SubElement(node_el, "options", clean_opt)
                
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ", level=0) 
        tree.write(self.xml_path, encoding="utf-8", xml_declaration=True)
        print(f"Saved Dialog XML to {self.xml_path}")

    def handle_event(self, event):
        if self.modal.active:
            res = self.modal.handle_event(event)
            if res is True: return True
            if res:
                action = res["action"]
                ctx = res["context"]
                vals = res.get("values", {})
                
                if action == "save":
                    if ctx["type"] == "node":
                        old_id, new_id = ctx["id"], vals["id"].strip()
                        if new_id and new_id != old_id:
                            self.nodes[new_id] = self.nodes.pop(old_id)
                            for n in self.nodes.values():
                                for o in n["options"]:
                                    if o.get("unlock_flag") == old_id: o["unlock_flag"] = new_id
                    elif ctx["type"] == "new_node":
                        new_id = vals["id"].strip()
                        if new_id and new_id not in self.nodes:
                            self.nodes[new_id] = {"options": [], "rect": pygame.Rect(-self.cam_x + self.width//2, -self.cam_y + self.height//2, 280, 100)}
                    elif ctx["type"] == "option":
                        self.nodes[ctx["id"]]["options"][ctx["idx"]] = vals
                    elif ctx["type"] == "new_option":
                        self.nodes[ctx["id"]]["options"].append(vals)
                
                elif action == "delete":
                    if ctx["type"] == "node" and ctx["id"] in self.nodes:
                        del self.nodes[ctx["id"]]
                    elif ctx["type"] == "option":
                        self.nodes[ctx["id"]]["options"].pop(ctx["idx"])
                        
                return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            if self.new_node_btn.collidepoint(mx, my):
                self.modal.open("New Node", ["id"], {"id": "new_node"}, {"type": "new_node"}, self.width//2, self.height//2)
                return True

            if self.save_xml_btn.collidepoint(mx, my):
                self.save_xml()
                return True

            if my > self.y_offset:
                if event.button == 3: 
                    world_x, world_y = mx - self.cam_x, my - self.cam_y
                    for n_id, data in reversed(list(self.nodes.items())):
                        if data["rect"].collidepoint(world_x, world_y):
                            rel_y = world_y - data["rect"].y
                            if rel_y < 30:
                                self.modal.open("Edit Node", ["id"], {"id": n_id}, {"type": "node", "id": n_id}, mx, my)
                            elif rel_y < 30 + len(data["options"]) * 25:
                                idx = (rel_y - 30) // 25
                                self.modal.open("Edit Option", self.opt_fields, data["options"][idx], {"type": "option", "id": n_id, "idx": idx}, self.width//2, self.height//2)
                            else: 
                                self.modal.open("New Option", self.opt_fields, {}, {"type": "new_option", "id": n_id}, self.width//2, self.height//2)
                            return True
                                        
                    self.dragging_camera = True
                    self.drag_start = event.pos
                    return True
                    
                elif event.button == 1: 
                    world_x, world_y = mx - self.cam_x, my - self.cam_y
                    for n_id, data in reversed(list(self.nodes.items())):
                        if data["rect"].collidepoint(world_x, world_y):
                            self.dragging_node = n_id
                            self.node_drag_offset = (data["rect"].x - world_x, data["rect"].y - world_y)
                            return True
                            
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging_camera = False
            self.dragging_node = None
            
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if self.dragging_camera:
                dx, dy = mx - self.drag_start[0], my - self.drag_start[1]
                self.cam_x += dx
                self.cam_y += dy
                self.drag_start = event.pos
                return True
            elif self.dragging_node and self.dragging_node in self.nodes:
                world_x, world_y = mx - self.cam_x, my - self.cam_y
                self.nodes[self.dragging_node]["rect"].x = world_x + self.node_drag_offset[0]
                self.nodes[self.dragging_node]["rect"].y = world_y + self.node_drag_offset[1]
                return True

        return False

    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, (30, 30, 40), bg_rect)
        surface.set_clip(bg_rect)

        for n_id, data in self.nodes.items():
            n_rect = data["rect"]
            n_rect.height = 30 + len(data["options"]) * 25 + 25 
            
            for i, opt in enumerate(data["options"]):
                target_id = opt.get("unlock_flag", "").strip()
                if target_id and target_id in self.nodes:
                    target_node = self.nodes[target_id]
                    opt_y = n_rect.y + 30 + i * 25 + 12
                    start_pos = (n_rect.right + self.cam_x, opt_y + self.cam_y)
                    end_pos = (target_node["rect"].left + self.cam_x, target_node["rect"].y + 15 + self.cam_y)
                    
                    pygame.draw.line(surface, (200, 200, 100), start_pos, end_pos, 2)
                    pygame.draw.circle(surface, (255, 255, 0), end_pos, 4)

        for n_id, data in self.nodes.items():
            draw_rect = data["rect"].move(self.cam_x, self.cam_y)
            pygame.draw.rect(surface, (80, 80, 90), draw_rect)
            pygame.draw.rect(surface, (200, 200, 200), draw_rect, 2)
            
            header_rect = pygame.Rect(draw_rect.x, draw_rect.y, draw_rect.width, 30)
            pygame.draw.rect(surface, (50, 50, 60), header_rect)
            surface.blit(self.font.render(n_id, True, (255, 255, 0)), (header_rect.x + 5, header_rect.y + 6))
            
            opt_y = draw_rect.y + 30
            for i, opt in enumerate(data["options"]):
                opt_rect = pygame.Rect(draw_rect.x, opt_y, draw_rect.width, 25)
                pygame.draw.rect(surface, (60, 60, 70), opt_rect)
                pygame.draw.rect(surface, (100, 100, 100), opt_rect, 1)
                
                q_text = opt.get("player_question", "...")[:25] + "..."
                surface.blit(self.font.render(f"Q: {q_text}", True, (200, 200, 200)), (opt_rect.x + 5, opt_rect.y + 5))
                
                if opt.get("unlock_flag"):
                    pygame.draw.circle(surface, (0, 255, 0), (opt_rect.right - 10, opt_rect.centery), 4)
                opt_y += 25
                
            add_rect = pygame.Rect(draw_rect.x, opt_y, draw_rect.width, 25)
            pygame.draw.rect(surface, (50, 100, 50), add_rect)
            surface.blit(self.font.render("+ Add Option", True, (200, 255, 200)), (add_rect.x + 5, add_rect.y + 5))

        surface.set_clip(None)

        pygame.draw.rect(surface, (0, 150, 0), self.new_node_btn)
        surface.blit(self.font.render("+ New Node", True, (255, 255, 255)), (self.new_node_btn.x + 10, self.new_node_btn.y + 5))
        
        pygame.draw.rect(surface, (0, 100, 200), self.save_xml_btn)
        surface.blit(self.font.render("Save XML", True, (255, 255, 255)), (self.save_xml_btn.x + 20, self.save_xml_btn.y + 5))
        
        surface.blit(self.font.render("Left-Click: Drag Node | Right-Click: Edit/Add | Right-Drag: Pan", True, (150, 150, 150)), (290, self.y_offset + 25))

        if self.modal.active: self.modal.draw(surface)