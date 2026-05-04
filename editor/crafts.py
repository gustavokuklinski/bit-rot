import pygame
import os
import xml.etree.ElementTree as ET
from editor.config import GAME_ROOT
from editor.ui import UITextBox, UIDropdown, UIAttributeList

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
        
        # Form Scrolling State
        self.form_scroll = 0
        self.max_scroll = 0
        self.dragging_form = False
        self.form_start_y = 0
        self.form_start_offset = 0
        self.form_thumb_rect = None
        self.form_track_rect = None
        
        # Sidebar Scrolling State
        self.sidebar_w = 300
        self.sidebar_scroll = 0
        self.max_sidebar_scroll = 0
        self.dragging_sidebar = False
        self.sidebar_start_y = 0
        self.sidebar_start_offset = 0
        self.sidebar_thumb_rect = None
        self.sidebar_track_rect = None
        
        # Form Components
        self.base_inputs = {}
        self.ing_rows = [] 
        self.res_rows = []
        
        self.save_btn = pygame.Rect(0, 0, 120, 30)
        self.delete_btn = pygame.Rect(0, 0, 100, 30)
        self.add_ing_btn = pygame.Rect(0, 0, 80, 25)
        self.add_res_btn = pygame.Rect(0, 0, 80, 25)
        
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
        """Scrapes existing XMLs and game assets to build complete dropdown options."""
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
                        # Filter for items specifically tagged as a recipe
                        if root.tag in ['item', 'cloth'] and root.get('type') == 'recipe':
                            name = root.get('name', '')
                            if name:
                                icon = self.item_tiles.get(name)
                                self.magazine_opts.append({"label": name, "value": name, "icon": icon})
                    except Exception as e:
                        print(f"Error parsing item for magazine: {e}")
                        
        # Safely update existing inputs if they are already active
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
                        
                except Exception as e:
                    print(f"Error loading craft XML {filename}: {e}")
                    
        self.build_dynamic_options()

    def generate_auto_filename(self):
        """Automatically generates the filename matching the pattern: [craft]_[type]_[item].xml"""
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
        
        self.base_inputs["filename"] = UITextBox(0, 0, 480, 28, self.font, filename or "")
        
        craft_opts = [{"label": "Create", "value": "create"}, {"label": "Repair", "value": "repair"}, {"label": "Dismantle", "value": "dismantle"}]
        self.base_inputs["craft"] = UIDropdown(0, 0, 480, 28, self.font, craft_opts, data.get("craft", "create"))
        self.base_inputs["type"] = UIDropdown(0, 0, 480, 28, self.font, self.type_opts, data.get("type", ""), searchable=True)
        self.base_inputs["output"] = UIDropdown(0, 0, 480, 28, self.font, self.item_opts, data.get("output", ""), searchable=True)
        
        self.base_inputs["magazine"] = UIDropdown(0, 0, 480, 28, self.font, self.magazine_opts, data.get("magazine", ""), searchable=True)
        
        for f in ["time", "amount"]:
            self.base_inputs[f] = UITextBox(0, 0, 480, 28, self.font, data.get(f, ""))
            
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
        start_x = form_x + 120 
        current_y = self.y_offset + 20 - self.form_scroll
        
        for f in ["filename", "craft", "type", "output", "magazine", "req_level", "gain_xp", "time", "amount"]:
            self.base_inputs[f].rect.x = start_x
            self.base_inputs[f].rect.y = current_y
            
            if hasattr(self.base_inputs[f], '_relayout'):
                self.base_inputs[f]._relayout()
                
            if isinstance(self.base_inputs[f], UIDropdown):
                self.base_inputs[f].list_rect.x = self.base_inputs[f].rect.x
                self.base_inputs[f].list_rect.y = self.base_inputs[f].rect.bottom
                
            current_y += self.base_inputs[f].rect.height + 7
            
        current_y += 60 # Extra spacing for the Ingredients Titles
        
        for row in self.ing_rows:
            row["group_btn"].topleft = (form_x + 20, current_y)
            row["item"].rect.topleft = (form_x + 90, current_y)
            row["item"].list_rect.topleft = (form_x + 90, current_y + 28)
            row["destroy_btn"].topleft = (form_x + 400, current_y)
            row["amount"].rect.topleft = (form_x + 480, current_y)
            row["del_btn"].topleft = (form_x + 550, current_y)
            current_y += 35
            
        self.add_ing_btn.topleft = (form_x + 20, current_y)
        current_y += 35 # Move past Add button
        
        # Determine if Results should be shown
        is_dismantle = self.base_inputs.get("craft") and self.base_inputs["craft"].text.lower() == "dismantle"
        
        if is_dismantle:
            current_y += 60 # Extra spacing for the Results Titles
            for row in self.res_rows:
                row["group_btn"].topleft = (form_x + 20, current_y)
                row["item"].rect.topleft = (form_x + 90, current_y)
                row["item"].list_rect.topleft = (form_x + 90, current_y + 28)
                row["amount"].rect.topleft = (form_x + 400, current_y)
                row["chance"].rect.topleft = (form_x + 470, current_y)
                row["del_btn"].topleft = (form_x + 550, current_y)
                current_y += 35
                
            self.add_res_btn.topleft = (form_x + 20, current_y)
            current_y += 35 # Move past Add button
            
        current_y += 25 # Padding before save
        self.save_btn.topleft = (form_x + 20, current_y)
        self.delete_btn.topleft = (form_x + 160, current_y)
        
        self.max_scroll = max(0, current_y + self.form_scroll - self.height + 40)
        
        # Sidebar Scroll Layout
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
        print(f"Saved Craft XML to {path}")

    def handle_event(self, event):
        # Handle Scroll Drags
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
            
            # 1. Expand dropdown checks first (top layer priority)
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
                # Trigger a layout update instantly if craft type changed
                new_craft = self.base_inputs.get("craft").text.lower() if "craft" in self.base_inputs else ""
                if old_craft != new_craft:
                    self.layout_form()
                return True
            
            # Form button/scroll clicks
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if mx > self.sidebar_w:
                    
                    # Form Scrollbar Click
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
                        
            # Mouse Wheel Scrolling Form Area
            if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] > self.sidebar_w:
                if event.button == 4:
                    self.form_scroll = max(0, self.form_scroll - 40)
                    self.layout_form()
                    return True
                elif event.button == 5:
                    self.form_scroll = min(self.max_scroll, self.form_scroll + 40)
                    self.layout_form()
                    return True

        # 2. Sidebar interactions
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx <= self.sidebar_w:
                # Sidebar scroll drag
                if event.button == 1 and self.sidebar_thumb_rect and self.sidebar_thumb_rect.collidepoint(mx, my):
                    self.dragging_sidebar = True
                    self.sidebar_start_y = my
                    self.sidebar_start_offset = self.sidebar_scroll
                    return True
                
                # Sidebar mouse wheel scroll
                if event.button == 4:
                    self.sidebar_scroll = max(0, self.sidebar_scroll - 40)
                    return True
                elif event.button == 5:
                    self.sidebar_scroll = min(self.max_sidebar_scroll, self.sidebar_scroll + 40)
                    return True
                
                # Clicks
                if event.button == 1:
                    if pygame.Rect(10, self.y_offset + 40, 230, 30).collidepoint(mx, my):
                        self.select_recipe(False)
                        return True
                    
                    list_y = self.y_offset + 80 - self.sidebar_scroll
                    for fname in self.recipes.keys():
                        if pygame.Rect(10, list_y, self.sidebar_w - 30, 25).collidepoint(mx, my):
                            if list_y > self.y_offset + 70: # Ensure it doesn't click under the fixed header
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

        # Group Ingredients Logic
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

        # Group Results Logic (Only run if dismantle)
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
        pygame.draw.rect(surface, (30, 30, 35), bg_rect) 
        
        # ------------------ SIDEBAR ------------------
        sidebar_rect = pygame.Rect(0, self.y_offset, self.sidebar_w, self.height - self.y_offset)
        pygame.draw.rect(surface, (40, 40, 45), sidebar_rect)
        pygame.draw.line(surface, (80, 80, 90), (self.sidebar_w, self.y_offset), (self.sidebar_w, self.height), 2)
        
        # Header (Fixed)
        surface.blit(self.font.render("Crafting Recipes", True, (255, 255, 0)), (10, self.y_offset + 10))
        new_color = (0, 150, 0) if self.selected_file is False else (40, 100, 40)
        pygame.draw.rect(surface, new_color, pygame.Rect(10, self.y_offset + 40, self.sidebar_w - 20, 30))
        surface.blit(self.font.render("+ New Craft", True, (255, 255, 255)), (75, self.y_offset + 45))
        
        # Scrollable List
        list_view_rect = pygame.Rect(0, self.y_offset + 80, self.sidebar_w, self.height - self.y_offset - 80)
        surface.set_clip(list_view_rect)
        
        list_y = self.y_offset + 80 - self.sidebar_scroll
        for fname in self.recipes.keys():
            r = pygame.Rect(10, list_y, self.sidebar_w - 30, 25)
            if fname == self.selected_file:
                pygame.draw.rect(surface, (80, 80, 150), r)
            
            lbl = (fname[:25] + '..') if len(fname) > 27 else fname
            surface.blit(self.font.render(lbl, True, (220, 220, 220)), (15, list_y + 3))
            list_y += 30
            
        surface.set_clip(None)
        
        # Sidebar Scrollbar
        if self.max_sidebar_scroll > 0:
            track_rect = pygame.Rect(self.sidebar_w - 12, list_view_rect.y, 12, list_view_rect.height)
            self.sidebar_track_rect = track_rect
            pygame.draw.rect(surface, (30, 30, 35), track_rect)
            
            content_h = len(self.recipes) * 30 + 80
            thumb_h = max(20, (list_view_rect.height / content_h) * list_view_rect.height)
            thumb_y = list_view_rect.y + (self.sidebar_scroll / self.max_sidebar_scroll) * (list_view_rect.height - thumb_h)
            
            self.sidebar_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 12, thumb_h)
            pygame.draw.rect(surface, (100, 100, 100), self.sidebar_thumb_rect)
            
        # ------------------ FORM AREA ------------------
        if self.selected_file is not None:
            form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, self.height - self.y_offset)
            surface.set_clip(form_view_rect)
            
            form_x = self.sidebar_w
            is_dismantle = self.base_inputs.get("craft") and self.base_inputs["craft"].text.lower() == "dismantle"
            
            # Base Fields
            for f in ["filename", "craft", "type", "output", "magazine", "req_level", "gain_xp", "time", "amount"]:
                lbl = f.replace("_", " ").title() + ":"
                y_pos = self.base_inputs[f].rect.y
                surface.blit(self.font.render(lbl, True, (180, 180, 180)), (form_x + 20, y_pos + 5))
                self.base_inputs[f].draw(surface)
                
            # Ingredients Section
            ing_title_y = self.base_inputs["amount"].rect.bottom + 15
            surface.blit(self.font.render("Ingredients:", True, (255, 200, 0)), (form_x + 20, ing_title_y))
            surface.blit(self.font.render("Link", True, (150, 150, 150)), (form_x + 20, ing_title_y + 25))
            surface.blit(self.font.render("Item", True, (150, 150, 150)), (form_x + 90, ing_title_y + 25))
            surface.blit(self.font.render("Destroy", True, (150, 150, 150)), (form_x + 400, ing_title_y + 25))
            surface.blit(self.font.render("Amount", True, (150, 150, 150)), (form_x + 480, ing_title_y + 25))
            
            for row in self.ing_rows:
                # Link / Group Btn
                pygame.draw.rect(surface, (70, 70, 80), row["group_btn"])
                pygame.draw.rect(surface, (100, 100, 110), row["group_btn"], 1)
                g_txt = "L OR" if row["group"] else "---"
                surface.blit(self.font.render(g_txt, True, (255, 255, 100) if row["group"] else (150, 150, 150)), (row["group_btn"].x + 6, row["group_btn"].y + 5))
                
                row["item"].draw(surface)
                
                # Only draw other fields if NOT grouped
                if not row["group"]:
                    btn_color = (150, 50, 50) if row["destroy"] else (50, 150, 50)
                    pygame.draw.rect(surface, btn_color, row["destroy_btn"])
                    txt = "True" if row["destroy"] else "False"
                    surface.blit(self.font.render(txt, True, (255, 255, 255)), (row["destroy_btn"].x + 12, row["destroy_btn"].y + 5))
                    row["amount"].draw(surface)
                else:
                    # Visual grouping line to link it upwards
                    pygame.draw.line(surface, (150, 150, 150), (form_x + 40, row["group_btn"].y - 7), (form_x + 40, row["group_btn"].y), 2)
                    
                pygame.draw.rect(surface, (200, 50, 50), row["del_btn"])
                surface.blit(self.font.render("X", True, (255, 255, 255)), (row["del_btn"].x + 8, row["del_btn"].y + 5))
                
            pygame.draw.rect(surface, (50, 100, 150), self.add_ing_btn)
            surface.blit(self.font.render("+ Add", True, (255, 255, 255)), (self.add_ing_btn.x + 15, self.add_ing_btn.y + 4))

            # Results Section (Only if Dismantle is selected)
            if is_dismantle:
                res_title_y = self.add_ing_btn.bottom + 15
                surface.blit(self.font.render("Results:", True, (255, 200, 0)), (form_x + 20, res_title_y))
                surface.blit(self.font.render("Link", True, (150, 150, 150)), (form_x + 20, res_title_y + 25))
                surface.blit(self.font.render("Item", True, (150, 150, 150)), (form_x + 90, res_title_y + 25))
                surface.blit(self.font.render("Amount", True, (150, 150, 150)), (form_x + 400, res_title_y + 25))
                surface.blit(self.font.render("Chance", True, (150, 150, 150)), (form_x + 470, res_title_y + 25))
                
                for row in self.res_rows:
                    pygame.draw.rect(surface, (70, 70, 80), row["group_btn"])
                    pygame.draw.rect(surface, (100, 100, 110), row["group_btn"], 1)
                    g_txt = "└ OR" if row["group"] else "---"
                    surface.blit(self.font.render(g_txt, True, (255, 255, 100) if row["group"] else (150, 150, 150)), (row["group_btn"].x + 6, row["group_btn"].y + 5))
                    
                    row["item"].draw(surface)
                    
                    if not row["group"]:
                        row["amount"].draw(surface)
                        row["chance"].draw(surface)
                    else:
                        pygame.draw.line(surface, (150, 150, 150), (form_x + 40, row["group_btn"].y - 7), (form_x + 40, row["group_btn"].y), 2)
                        
                    pygame.draw.rect(surface, (200, 50, 50), row["del_btn"])
                    surface.blit(self.font.render("X", True, (255, 255, 255)), (row["del_btn"].x + 8, row["del_btn"].y + 5))
                    
                pygame.draw.rect(surface, (50, 100, 150), self.add_res_btn)
                surface.blit(self.font.render("+ Add", True, (255, 255, 255)), (self.add_res_btn.x + 15, self.add_res_btn.y + 4))
                
            # Action Buttons
            pygame.draw.rect(surface, (0, 150, 0), self.save_btn)
            surface.blit(self.font.render("Save XML", True, (255, 255, 255)), (self.save_btn.x + 20, self.save_btn.y + 5))
            if self.selected_file:
                pygame.draw.rect(surface, (150, 0, 0), self.delete_btn)
                surface.blit(self.font.render("Delete", True, (255, 255, 255)), (self.delete_btn.x + 160, self.delete_btn.y + 5))
                
            # OVERLAYS (Draw Dropdowns last so they render on top)
            for f in self.base_inputs.values():
                if isinstance(f, UIDropdown): f.draw_list(surface)
            for row in self.ing_rows: row["item"].draw_list(surface)
            if is_dismantle:
                for row in self.res_rows: row["item"].draw_list(surface)
                
            surface.set_clip(None)
            
            # Draw Form Scrollbar overlay
            if self.max_scroll > 0:
                track_rect = pygame.Rect(self.width - 12, form_view_rect.y, 12, form_view_rect.height)
                self.form_track_rect = track_rect
                pygame.draw.rect(surface, (30, 30, 35), track_rect)
                
                content_h = form_view_rect.height + self.max_scroll
                thumb_h = max(20, (form_view_rect.height / content_h) * form_view_rect.height)
                thumb_y = form_view_rect.y + (self.form_scroll / self.max_scroll) * (form_view_rect.height - thumb_h)
                
                self.form_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 12, thumb_h)
                pygame.draw.rect(surface, (100, 100, 100), self.form_thumb_rect)