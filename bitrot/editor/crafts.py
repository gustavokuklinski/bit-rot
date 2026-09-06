import pygame
import os
import xml.etree.ElementTree as ET
from editor.config import GAME_ROOT
from editor.ui import UITextBox, UIDropdown, UIAttributeList, UITheme, draw_styled_button

class CraftEditor:
    def __init__(self, y_offset, width, height, font, item_tiles):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        self.item_tiles = item_tiles
        
        self.craft_dir = os.path.join(GAME_ROOT, 'lib', 'data', 'craft')
        self.recipes = {} 
        self.selected_file = None
        
        self.form_scroll = 0
        self.max_scroll = 0
        self.dragging_form = False
        self.form_start_y = 0
        self.form_start_offset = 0
        self.form_thumb_rect = None
        self.form_track_rect = None
        
        self.sidebar_w = 300
        self.sidebar_scroll = 0
        self.max_sidebar_scroll = 0
        self.dragging_sidebar = False
        self.sidebar_start_y = 0
        self.sidebar_start_offset = 0
        self.sidebar_thumb_rect = None
        self.sidebar_track_rect = None
        
        self.base_inputs = {}
        self.ing_rows = [] 
        self.res_rows = []
        
        self.save_btn = pygame.Rect(0, 0, 120, 35)
        self.delete_btn = pygame.Rect(0, 0, 100, 35)
        self.add_ing_btn = pygame.Rect(0, 0, 80, 28)
        self.add_res_btn = pygame.Rect(0, 0, 80, 28)
        
        self.type_opts = []
        self.item_opts = []
        self.magazine_opts = []

        self.load_xmls()
        
    def resize(self, width, height):
        self.width = width
        self.height = height
        if self.selected_file is not None:
            self.layout_form()

    def build_dynamic_options(self):
        types = set()
        for info in self.recipes.values():
            t = info.get("data", {}).get("type", "")
            if t: types.add(t)
        self.type_opts = [{"label": "None", "value": ""}] + [{"label": t, "value": t} for t in sorted(types)]
        
        opts_dict = {"": {"label": "None", "value": ""}}
        for name, icon in sorted(self.item_tiles.items()):
            opts_dict[name] = {"label": name, "value": name, "icon": icon}
            
        for info in self.recipes.values():
            for ing in info.get("data", {}).get("ingredients", []):
                n = ing["name"]
                if n.startswith('[') and n.endswith(']'):
                    for sub_n in n[1:-1].split(','):
                        sub_n = sub_n.strip()
                        if sub_n and sub_n not in opts_dict: opts_dict[sub_n] = {"label": sub_n, "value": sub_n}
                elif n and n not in opts_dict: 
                    opts_dict[n] = {"label": n, "value": n}
                    
            for res in info.get("data", {}).get("results", []):
                n = res["name"]
                if n.startswith('[') and n.endswith(']'):
                    for sub_n in n[1:-1].split(','):
                        sub_n = sub_n.strip()
                        if sub_n and sub_n not in opts_dict: opts_dict[sub_n] = {"label": sub_n, "value": sub_n}
                elif n and n not in opts_dict: 
                    opts_dict[n] = {"label": n, "value": n}
                
        self.item_opts = list(opts_dict.values())
        
        self.magazine_opts = [{"label": "None", "value": ""}]
        item_xml_dir = os.path.join(GAME_ROOT, 'lib', 'data', 'items')
        
        if os.path.exists(item_xml_dir):
            for filename in os.listdir(item_xml_dir):
                if filename.endswith(".xml"):
                    try:
                        tree = ET.parse(os.path.join(item_xml_dir, filename))
                        root = tree.getroot()
                        if root.tag in ['item', 'cloth'] and root.get('type') == 'recipe':
                            name = root.get('name', '')
                            if name:
                                icon = self.item_tiles.get(name)
                                self.magazine_opts.append({"label": name, "value": name, "icon": icon})
                    except Exception as e: pass
                        
        if "type" in self.base_inputs: self.base_inputs["type"].options = self.type_opts
        if "output" in self.base_inputs: self.base_inputs["output"].options = self.item_opts
        if "magazine" in self.base_inputs: self.base_inputs["magazine"].options = self.magazine_opts

    def load_xmls(self):
        self.recipes.clear()
        if not os.path.exists(self.craft_dir): 
            os.makedirs(self.craft_dir)
            
        for filename in sorted(os.listdir(self.craft_dir)):
            if filename.endswith(".xml"):
                path = os.path.join(self.craft_dir, filename)
                try:
                    tree = ET.parse(path)
                    root = tree.getroot()
                    if root.tag != 'recipe': continue
                    
                    data = {}
                    for attr in ["type", "craft", "output", "magazine", "req_level", "gain_xp", "amount", "time"]:
                        data[attr] = root.get(attr, "")
                        
                    ings = []
                    for ing in root.findall('ingredient'):
                        ings.append({
                            "name": ing.get('name', ''),
                            "destroy": ing.get('destroy', 'false').lower() == 'true',
                            "amount": ing.get('amount', '1')
                        })
                    data["ingredients"] = ings
                    
                    ress = []
                    for res in root.findall('result'):
                        ress.append({
                            "name": res.get('name', ''),
                            "amount": res.get('amount', '1'),
                            "chance": res.get('chance', '')
                        })
                    data["results"] = ress
                    
                    self.recipes[filename] = {"data": data}
                        
                except Exception as e: pass
                    
        self.build_dynamic_options()

    def generate_auto_filename(self):
        if self.selected_file is False:
            c = self.base_inputs.get("craft").text.lower() if "craft" in self.base_inputs else ""
            t = self.base_inputs.get("type").text.lower().replace(" ", "_") if "type" in self.base_inputs else ""
            o = self.base_inputs.get("output").text.lower().replace(" ", "_").strip("[]") if "output" in self.base_inputs else ""
            
            parts = [x for x in [c, t, o] if x]
            if not parts:
                auto_name = "new_craft.xml"
            else:
                auto_name = "_".join(parts) + ".xml"
                
            self.base_inputs["filename"].text = auto_name

    def select_recipe(self, filename):
        self.selected_file = filename
        self.form_scroll = 0
        self.base_inputs.clear()
        self.ing_rows.clear()
        self.res_rows.clear()
        
        data = self.recipes.get(filename, {}).get("data", {}) if filename else {}
        
        self.base_inputs["filename"] = UITextBox(0, 0, 480, 30, self.font, filename or "")
        
        craft_opts = [{"label": "Create", "value": "create"}, {"label": "Repair", "value": "repair"}, {"label": "Dismantle", "value": "dismantle"}]
        self.base_inputs["craft"] = UIDropdown(0, 0, 480, 30, self.font, craft_opts, data.get("craft", "create"))
        self.base_inputs["type"] = UIDropdown(0, 0, 480, 30, self.font, self.type_opts, data.get("type", ""), searchable=True)
        self.base_inputs["output"] = UIDropdown(0, 0, 480, 30, self.font, self.item_opts, data.get("output", ""), searchable=True)
        
        self.base_inputs["magazine"] = UIDropdown(0, 0, 480, 30, self.font, self.magazine_opts, data.get("magazine", ""), searchable=True)
        
        for f in ["time", "amount"]:
            self.base_inputs[f] = UITextBox(0, 0, 480, 30, self.font, data.get(f, ""))
            
        self.base_inputs["req_level"] = UIAttributeList(0, 0, 480, 145, self.font, data.get("req_level", ""))
        self.base_inputs["gain_xp"] = UIAttributeList(0, 0, 480, 145, self.font, data.get("gain_xp", ""))
            
        if self.selected_file is False:
            self.generate_auto_filename()
            
        for ing in data.get("ingredients", []):
            n = ing["name"]
            if n.startswith('[') and n.endswith(']'):
                items = [x.strip() for x in n[1:-1].split(',')]
                if items:
                    self.add_ing_row(items[0], ing["destroy"], ing["amount"], group=False)
                    for item in items[1:]:
                        self.add_ing_row(item, ing["destroy"], ing["amount"], group=True)
            else:
                self.add_ing_row(n, ing["destroy"], ing["amount"], group=False)
            
        for res in data.get("results", []):
            n = res["name"]
            if n.startswith('[') and n.endswith(']'):
                items = [x.strip() for x in n[1:-1].split(',')]
                if items:
                    self.add_res_row(items[0], res["amount"], res.get("chance", ""), group=False)
                    for item in items[1:]:
                        self.add_res_row(item, res["amount"], res.get("chance", ""), group=True)
            else:
                self.add_res_row(n, res["amount"], res.get("chance", ""), group=False)
            
        self.layout_form()

    def add_ing_row(self, name="", destroy=False, amount="1", group=False):
        row = {
            "group": group,
            "group_btn": pygame.Rect(0, 0, 60, 28),
            "item": UIDropdown(0, 0, 290, 28, self.font, self.item_opts, name, searchable=True),
            "destroy": destroy,
            "destroy_btn": pygame.Rect(0, 0, 70, 28),
            "amount": UITextBox(0, 0, 50, 28, self.font, amount),
            "del_btn": pygame.Rect(0, 0, 28, 28)
        }
        self.ing_rows.append(row)
        self.layout_form()

    def add_res_row(self, name="", amount="1", chance="", group=False):
        row = {
            "group": group,
            "group_btn": pygame.Rect(0, 0, 60, 28),
            "item": UIDropdown(0, 0, 290, 28, self.font, self.item_opts, name, searchable=True),
            "amount": UITextBox(0, 0, 60, 28, self.font, amount),
            "chance": UITextBox(0, 0, 60, 28, self.font, chance),
            "del_btn": pygame.Rect(0, 0, 28, 28)
        }
        self.res_rows.append(row)
        self.layout_form()

    def layout_form(self):
        if self.selected_file is None: return
        
        form_x = self.sidebar_w
        start_x = form_x + 150 
        current_y = self.y_offset + 20 - self.form_scroll
        
        for f in ["filename", "craft", "type", "output", "magazine", "req_level", "gain_xp", "time", "amount"]:
            self.base_inputs[f].rect.x = start_x
            self.base_inputs[f].rect.y = current_y
            
            if hasattr(self.base_inputs[f], '_relayout'):
                self.base_inputs[f]._relayout()
                
            if isinstance(self.base_inputs[f], UIDropdown):
                self.base_inputs[f].list_rect.x = self.base_inputs[f].rect.x
                self.base_inputs[f].list_rect.y = self.base_inputs[f].rect.bottom
                
            current_y += self.base_inputs[f].rect.height + 10
            
        current_y += 50 
        
        for row in self.ing_rows:
            row["group_btn"].topleft = (form_x + 20, current_y)
            row["item"].rect.topleft = (form_x + 90, current_y)
            row["item"].list_rect.topleft = (form_x + 90, current_y + 28)
            row["destroy_btn"].topleft = (form_x + 400, current_y)
            row["amount"].rect.topleft = (form_x + 480, current_y)
            row["del_btn"].topleft = (form_x + 550, current_y)
            current_y += 35
            
        self.add_ing_btn.topleft = (form_x + 20, current_y)
        current_y += 35 
        
        is_dismantle = self.base_inputs.get("craft") and self.base_inputs["craft"].text.lower() == "dismantle"
        
        if is_dismantle:
            current_y += 50
            for row in self.res_rows:
                row["group_btn"].topleft = (form_x + 20, current_y)
                row["item"].rect.topleft = (form_x + 90, current_y)
                row["item"].list_rect.topleft = (form_x + 90, current_y + 28)
                row["amount"].rect.topleft = (form_x + 400, current_y)
                row["chance"].rect.topleft = (form_x + 470, current_y)
                row["del_btn"].topleft = (form_x + 550, current_y)
                current_y += 35
                
            self.add_res_btn.topleft = (form_x + 20, current_y)
            current_y += 35 
            
        current_y += 25 
        self.save_btn.topleft = (form_x + 20, current_y)
        self.delete_btn.topleft = (form_x + 160, current_y)
        
        self.max_scroll = max(0, current_y + self.form_scroll - self.height + 40)
        content_h = len(self.recipes) * 30 + 80
        self.max_sidebar_scroll = max(0, content_h - (self.height - self.y_offset))

    def save_xml(self, filename, data):
        if not os.path.exists(self.craft_dir): os.makedirs(self.craft_dir)
        path = os.path.join(self.craft_dir, filename)
        
        root = ET.Element("recipe")
        for attr in ["type", "craft", "output", "magazine", "req_level", "gain_xp", "amount", "time"]:
            if data.get(attr): root.set(attr, data[attr])
                
        for ing in data.get("ingredients", []):
            if ing["name"]:
                ET.SubElement(root, "ingredient", {"name": ing["name"], "destroy": ing["destroy"], "amount": ing["amount"]})
                    
        for res in data.get("results", []):
            if res["name"]:
                res_attr = {"name": res["name"], "amount": res["amount"]}
                if res.get("chance"): res_attr["chance"] = res["chance"]
                ET.SubElement(root, "result", res_attr)
                    
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ", level=0)
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_sidebar = False
            self.dragging_form = False
            
        if event.type == pygame.MOUSEMOTION:
            if self.dragging_sidebar and self.sidebar_thumb_rect and self.max_sidebar_scroll > 0:
                dy = event.pos[1] - self.sidebar_start_y
                track_h = self.sidebar_track_rect.height
                thumb_h = self.sidebar_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    scroll_per_pixel = self.max_sidebar_scroll / track_space
                    self.sidebar_scroll = max(0, min(self.max_sidebar_scroll, self.sidebar_start_offset + dy * scroll_per_pixel))
                return True
                
            if self.dragging_form and self.form_thumb_rect and self.max_scroll > 0:
                dy = event.pos[1] - self.form_start_y
                track_h = self.form_track_rect.height
                thumb_h = self.form_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    scroll_per_pixel = self.max_scroll / track_space
                    self.form_scroll = max(0, min(self.max_scroll, self.form_start_offset + dy * scroll_per_pixel))
                    self.layout_form()
                return True

        if self.selected_file is not None:
            old_craft = self.base_inputs.get("craft").text.lower() if "craft" in self.base_inputs else ""
            is_dismantle = old_craft == "dismantle"
            
            dropdowns = [f for f in self.base_inputs.values() if isinstance(f, UIDropdown)]
            dropdowns += [r["item"] for r in self.ing_rows]
            if is_dismantle:
                dropdowns += [r["item"] for r in self.res_rows]
            
            for d in dropdowns:
                if getattr(d, 'expanded', False):
                    if d.handle_event(event):
                        if d == self.base_inputs.get("craft"): self.layout_form()
                        if self.selected_file is False and d in [self.base_inputs.get("craft"), self.base_inputs.get("type"), self.base_inputs.get("output")]:
                            self.generate_auto_filename()
                        return True
                                  
            consumed = False
            for k, c in self.base_inputs.items():
                if c.handle_event(event): 
                    consumed = True
                    if self.selected_file is False and k in ["craft", "type", "output"]:
                        self.generate_auto_filename()
                        
            for r in self.ing_rows:
                if r["item"].handle_event(event): consumed = True
                if not r["group"] and r["amount"].handle_event(event): consumed = True
                
            if is_dismantle:
                for r in self.res_rows:
                    if r["item"].handle_event(event): consumed = True
                    if not r["group"]:
                        if r["amount"].handle_event(event): consumed = True
                        if r["chance"].handle_event(event): consumed = True
                              
            if consumed: 
                new_craft = self.base_inputs.get("craft").text.lower() if "craft" in self.base_inputs else ""
                if old_craft != new_craft:
                    self.layout_form()
                return True
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if mx > self.sidebar_w:
                    
                    if self.form_thumb_rect and self.form_thumb_rect.collidepoint(mx, my):
                        self.dragging_form = True
                        self.form_start_y = my
                        self.form_start_offset = self.form_scroll
                        return True
                        
                    for i, row in enumerate(self.ing_rows):
                        if row["group_btn"].collidepoint(mx, my):
                            row["group"] = not row["group"]
                            return True
                        if not row["group"] and row["destroy_btn"].collidepoint(mx, my):
                            row["destroy"] = not row["destroy"]
                            return True
                        if row["del_btn"].collidepoint(mx, my):
                            self.ing_rows.pop(i)
                            self.layout_form()
                            return True
                            
                    if is_dismantle:
                        for i, row in enumerate(self.res_rows):
                            if row["group_btn"].collidepoint(mx, my):
                                row["group"] = not row["group"]
                                return True
                            if row["del_btn"].collidepoint(mx, my):
                                self.res_rows.pop(i)
                                self.layout_form()
                                return True
                            
                    if self.add_ing_btn.collidepoint(mx, my):
                        self.add_ing_row()
                        return True
                    if is_dismantle and self.add_res_btn.collidepoint(mx, my):
                        self.add_res_row()
                        return True
                    if self.save_btn.collidepoint(mx, my):
                        self.save_current()
                        return True
                    if self.selected_file and self.delete_btn.collidepoint(mx, my):
                        self.delete_current()
                        return True
                        
            if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] > self.sidebar_w:
                if event.button == 4:
                    self.form_scroll = max(0, self.form_scroll - 40)
                    self.layout_form()
                    return True
                elif event.button == 5:
                    self.form_scroll = min(self.max_scroll, self.form_scroll + 40)
                    self.layout_form()
                    return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx <= self.sidebar_w:
                if event.button == 1 and self.sidebar_thumb_rect and self.sidebar_thumb_rect.collidepoint(mx, my):
                    self.dragging_sidebar = True
                    self.sidebar_start_y = my
                    self.sidebar_start_offset = self.sidebar_scroll
                    return True
                
                if event.button == 4:
                    self.sidebar_scroll = max(0, self.sidebar_scroll - 40)
                    return True
                elif event.button == 5:
                    self.sidebar_scroll = min(self.max_sidebar_scroll, self.sidebar_scroll + 40)
                    return True
                
                if event.button == 1:
                    if pygame.Rect(10, self.y_offset + 40, 230, 30).collidepoint(mx, my):
                        self.select_recipe(False)
                        return True
                    
                    list_y = self.y_offset + 85 - self.sidebar_scroll
                    for fname in self.recipes.keys():
                        if pygame.Rect(10, list_y, self.sidebar_w - 30, 25).collidepoint(mx, my):
                            if list_y > self.y_offset + 70:
                                self.select_recipe(fname)
                            return True
                        list_y += 30
                    
        return False

    def save_current(self):
        new_file = self.base_inputs["filename"].text.strip()
        if not new_file: return
        if not new_file.endswith(".xml"): new_file += ".xml"
        
        data = {}
        for attr in ["type", "craft", "output", "magazine", "req_level", "gain_xp", "time", "amount"]:
            data[attr] = self.base_inputs[attr].text

        merged_ings = []
        for r in self.ing_rows:
            item_val = r["item"].text.strip()
            if not item_val: continue
            if r["group"] and merged_ings:
                merged_ings[-1]["names"].append(item_val)
            else:
                merged_ings.append({
                    "names": [item_val],
                    "destroy": str(r["destroy"]).lower(),
                    "amount": r["amount"].text
                })
                
        data["ingredients"] = []
        for m in merged_ings:
            name_str = f"[{', '.join(m['names'])}]" if len(m['names']) > 1 else m['names'][0]
            data["ingredients"].append({"name": name_str, "destroy": m["destroy"], "amount": m["amount"]})

        is_dismantle = self.base_inputs.get("craft") and self.base_inputs["craft"].text.lower() == "dismantle"
        data["results"] = []
        
        if is_dismantle:
            merged_res = []
            for r in self.res_rows:
                item_val = r["item"].text.strip()
                if not item_val: continue
                if r["group"] and merged_res:
                    merged_res[-1]["names"].append(item_val)
                else:
                    merged_res.append({
                        "names": [item_val],
                        "amount": r["amount"].text,
                        "chance": r["chance"].text
                    })
                    
            for m in merged_res:
                name_str = f"[{', '.join(m['names'])}]" if len(m['names']) > 1 else m['names'][0]
                data["results"].append({"name": name_str, "amount": m["amount"], "chance": m["chance"]})
        
        if self.selected_file and self.selected_file != new_file and self.selected_file in self.recipes:
            old_path = os.path.join(self.craft_dir, self.selected_file)
            if os.path.exists(old_path): os.remove(old_path)
            del self.recipes[self.selected_file]
            
        self.recipes[new_file] = {"data": data}
        self.save_xml(new_file, data)
        self.build_dynamic_options()
        self.select_recipe(new_file)

    def delete_current(self):
        if self.selected_file and self.selected_file in self.recipes:
            path = os.path.join(self.craft_dir, self.selected_file)
            if os.path.exists(path): os.remove(path)
            del self.recipes[self.selected_file]
            self.selected_file = None
            self.build_dynamic_options()

    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect) 
        
        sidebar_rect = pygame.Rect(0, self.y_offset, self.sidebar_w, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.PANEL_BG, sidebar_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset), (self.sidebar_w, self.height), 2)
        
        surface.blit(self.font.render("Crafting Recipes", True, UITheme.WARNING), (10, self.y_offset + 10))
        
        mouse_pos = pygame.mouse.get_pos()
        new_btn_rect = pygame.Rect(10, self.y_offset + 40, self.sidebar_w - 20, 32)
        btn_color = UITheme.SUCCESS if self.selected_file is False else UITheme.BG
        draw_styled_button(surface, new_btn_rect, "+ New Craft", self.font, mouse_pos, btn_color, UITheme.SUCCESS_HOVER)
        
        list_view_rect = pygame.Rect(0, self.y_offset + 80, self.sidebar_w, self.height - self.y_offset - 80)
        surface.set_clip(list_view_rect)
        
        list_y = self.y_offset + 85 - self.sidebar_scroll
        for fname in self.recipes.keys():
            r = pygame.Rect(10, list_y, self.sidebar_w - 30, 25)
            if fname == self.selected_file:
                pygame.draw.rect(surface, UITheme.LIST_HOVER, r, border_radius=4)
            elif r.collidepoint(mouse_pos):
                pygame.draw.rect(surface, UITheme.HOVER_BG, r, border_radius=4)
            
            lbl = (fname[:25] + '..') if len(fname) > 27 else fname
            surface.blit(self.font.render(lbl, True, UITheme.TEXT), (15, list_y + 5))
            list_y += 30
            
        surface.set_clip(None)
        
        if self.max_sidebar_scroll > 0:
            track_rect = pygame.Rect(self.sidebar_w - 8, list_view_rect.y, 8, list_view_rect.height)
            self.sidebar_track_rect = track_rect
            content_h = len(self.recipes) * 30 + 80
            thumb_h = max(20, (list_view_rect.height / content_h) * list_view_rect.height)
            thumb_y = list_view_rect.y + (self.sidebar_scroll / self.max_sidebar_scroll) * (list_view_rect.height - thumb_h)
            self.sidebar_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.sidebar_thumb_rect, border_radius=4)
            
        if self.selected_file is not None:
            form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, self.height - self.y_offset)
            surface.set_clip(form_view_rect)
            
            form_x = self.sidebar_w
            is_dismantle = self.base_inputs.get("craft") and self.base_inputs["craft"].text.lower() == "dismantle"
            
            for f in ["filename", "craft", "type", "output", "magazine", "req_level", "gain_xp", "time", "amount"]:
                lbl = f.replace("_", " ").title() + ":"
                y_pos = self.base_inputs[f].rect.y
                surface.blit(self.font.render(lbl, True, UITheme.TEXT_DIM), (form_x + 20, y_pos + 6))
                self.base_inputs[f].draw(surface)
                
            ing_title_y = self.base_inputs["amount"].rect.bottom + 15
            surface.blit(self.font.render("Ingredients:", True, UITheme.WARNING), (form_x + 20, ing_title_y))
            surface.blit(self.font.render("Link", True, UITheme.TEXT_DIM), (form_x + 20, ing_title_y + 25))
            surface.blit(self.font.render("Item", True, UITheme.TEXT_DIM), (form_x + 90, ing_title_y + 25))
            surface.blit(self.font.render("Destroy", True, UITheme.TEXT_DIM), (form_x + 400, ing_title_y + 25))
            surface.blit(self.font.render("Amount", True, UITheme.TEXT_DIM), (form_x + 480, ing_title_y + 25))
            
            for row in self.ing_rows:
                g_txt = "└ OR" if row["group"] else "---"
                g_color = UITheme.WARNING if row["group"] else UITheme.BG
                draw_styled_button(surface, row["group_btn"], g_txt, self.font, mouse_pos, g_color, UITheme.WARNING_HOVER)
                row["item"].draw(surface)
                
                if not row["group"]:
                    btn_color = UITheme.DANGER if row["destroy"] else UITheme.SUCCESS
                    draw_styled_button(surface, row["destroy_btn"], "True" if row["destroy"] else "False", self.font, mouse_pos, btn_color, btn_color)
                    row["amount"].draw(surface)
                else:
                    pygame.draw.line(surface, UITheme.BORDER_ACTIVE, (form_x + 50, row["group_btn"].y - 7), (form_x + 50, row["group_btn"].y), 2)
                    
                draw_styled_button(surface, row["del_btn"], "X", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
                
            draw_styled_button(surface, self.add_ing_btn, "+ Add", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)

            if is_dismantle:
                res_title_y = self.add_ing_btn.bottom + 15
                surface.blit(self.font.render("Results:", True, UITheme.WARNING), (form_x + 20, res_title_y))
                surface.blit(self.font.render("Link", True, UITheme.TEXT_DIM), (form_x + 20, res_title_y + 25))
                surface.blit(self.font.render("Item", True, UITheme.TEXT_DIM), (form_x + 90, res_title_y + 25))
                surface.blit(self.font.render("Amount", True, UITheme.TEXT_DIM), (form_x + 400, res_title_y + 25))
                surface.blit(self.font.render("Chance", True, UITheme.TEXT_DIM), (form_x + 470, res_title_y + 25))
                
                for row in self.res_rows:
                    g_txt = "└ OR" if row["group"] else "---"
                    g_color = UITheme.WARNING if row["group"] else UITheme.BG
                    draw_styled_button(surface, row["group_btn"], g_txt, self.font, mouse_pos, g_color, UITheme.WARNING_HOVER)
                    row["item"].draw(surface)
                    
                    if not row["group"]:
                        row["amount"].draw(surface)
                        row["chance"].draw(surface)
                    else:
                        pygame.draw.line(surface, UITheme.BORDER_ACTIVE, (form_x + 50, row["group_btn"].y - 7), (form_x + 50, row["group_btn"].y), 2)
                        
                    draw_styled_button(surface, row["del_btn"], "X", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
                    
                draw_styled_button(surface, self.add_res_btn, "+ Add", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
                
            draw_styled_button(surface, self.save_btn, "Save XML", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            if self.selected_file:
                draw_styled_button(surface, self.delete_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
                
            for f in self.base_inputs.values():
                if isinstance(f, UIDropdown): f.draw_list(surface)
            for row in self.ing_rows: row["item"].draw_list(surface)
            if is_dismantle:
                for row in self.res_rows: row["item"].draw_list(surface)
                
            surface.set_clip(None)
            
            if self.max_scroll > 0:
                track_rect = pygame.Rect(self.width - 8, form_view_rect.y, 8, form_view_rect.height)
                self.form_track_rect = track_rect
                content_h = form_view_rect.height + self.max_scroll
                thumb_h = max(20, (form_view_rect.height / content_h) * form_view_rect.height)
                thumb_y = form_view_rect.y + (self.form_scroll / self.max_scroll) * (form_view_rect.height - thumb_h)
                self.form_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
                pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.form_thumb_rect, border_radius=4)