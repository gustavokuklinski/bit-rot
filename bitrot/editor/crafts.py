import pygame
import os
import re
import xml.etree.ElementTree as ET
from editor.config import GAME_ROOT
from editor.ui import (
    UITextBox, UIDropdown, UIAttributeList, UITheme, 
    draw_styled_button, FocusManager
)

# ----------------------------------------------------------------------
# CRAFT EDITOR WITH TAB SYSTEM & IN-PLACE SYNC
# ----------------------------------------------------------------------
class CraftEditor:
    def __init__(self, y_offset, width, height, font, item_tiles):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        self.item_tiles = item_tiles
        
        self.tab_bar_h = 36
        self.sidebar_w = 300
        self.craft_dir = os.path.join(GAME_ROOT, 'lib', 'data', 'craft')
        self.recipes = {} 

        # Multi-tab system
        self.open_tabs = []
        self.active_tab_idx = -1
        self.tab_scroll_x = 0
        self.max_tab_scroll = 0
        self.dragging_tab_scroll = False
        self.tab_scroll_start_x = 0
        self.tab_scroll_start_offset = 0
        self.tab_thumb_rect = None
        self.close_confirm_dialog = None

        # Sidebar Scroll
        self.sidebar_scroll = 0
        self.max_sidebar_scroll = 0
        self.dragging_sidebar = False
        self.sidebar_start_y = 0
        self.sidebar_start_offset = 0
        self.sidebar_thumb_rect = None

        # Form Scroll Dragging
        self.dragging_form = False
        self.form_start_y = 0
        self.form_start_offset = 0
        self.form_thumb_rect = None
        
        self.save_btn = pygame.Rect(0, 0, 130, 35)
        self.duplicate_btn = pygame.Rect(0, 0, 130, 35)
        self.delete_btn = pygame.Rect(0, 0, 110, 35)
        self.code_btn = pygame.Rect(0, 0, 110, 35)
        self.add_ing_btn = pygame.Rect(0, 0, 90, 28)
        self.add_res_btn = pygame.Rect(0, 0, 90, 28)
        
        self.search_input = UITextBox(10, self.y_offset + 38, self.sidebar_w - 20, 28, self.font, "")
        self.new_btn = pygame.Rect(10, self.y_offset + 72, self.sidebar_w - 20, 30)

        self.type_opts = []
        self.item_opts = []
        self.magazine_opts = []

        self.load_xmls()
        if self.recipes:
            self.open_tab_recipe(sorted(self.recipes.keys())[0])
        
    @property
    def filtered_recipes(self):
        query = self.search_input.text.strip().lower()
        if not query:
            return list(self.recipes.keys())
        return [f for f in self.recipes.keys() if query in f.lower()]

    def resize(self, width, height):
        self.width = width
        self.height = height
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
                    except: pass

    def load_xmls(self):
        self.recipes.clear()
        if not os.path.exists(self.craft_dir): os.makedirs(self.craft_dir)
            
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
                        # Ensure destroy boolean is accurately parsed
                        d_val = ing.get('destroy', 'false').lower() in ['true', '1', 'yes']
                        ings.append({
                            "name": ing.get('name', ''),
                            "destroy": d_val,
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
                except: pass
                    
        self.build_dynamic_options()

    def ensure_tab_visible(self, idx):
        if not (0 <= idx < len(self.open_tabs)):
            return

        start_x = self.sidebar_w
        view_w = self.width - start_x
        rel_x = 0
        target_left = 0
        target_right = 0

        for i, tab in enumerate(self.open_tabs):
            fname = tab["filename"] or tab["base_inputs"]["filename"].text or "new_craft.xml"
            modified = self.is_tab_modified(tab)
            display_name = f"*{fname}" if modified else fname
            text_w = self.font.size(display_name)[0]
            tab_w = max(90, text_w + 44)

            if i == idx:
                target_left = rel_x
                target_right = rel_x + tab_w

            rel_x += tab_w + 2

        total_w = rel_x - 2 if rel_x > 0 else 0
        self.max_tab_scroll = max(0, total_w - view_w)

        # Auto-scroll horizontally if tab is outside the visible view
        if target_right > self.tab_scroll_x + view_w:
            self.tab_scroll_x = (target_right + 15) - view_w
        elif target_left < self.tab_scroll_x:
            self.tab_scroll_x = max(0, target_left - 15)

        self.tab_scroll_x = max(0, min(self.max_tab_scroll, self.tab_scroll_x))

    def get_current_tab(self):
        if 0 <= self.active_tab_idx < len(self.open_tabs):
            return self.open_tabs[self.active_tab_idx]
        return None

    def get_tab_snapshot(self, tab):
        return {
            "fname": tab["base_inputs"]["filename"].text.strip(),
            "craft": tab["base_inputs"]["craft"].text,
            "type": tab["base_inputs"]["type"].text,
            "output": tab["base_inputs"]["output"].text,
            "magazine": tab["base_inputs"]["magazine"].text,
            "req_level": tab["base_inputs"]["req_level"].text,
            "gain_xp": tab["base_inputs"]["gain_xp"].text,
            "time": tab["base_inputs"]["time"].text.strip(),
            "amount": tab["base_inputs"]["amount"].text.strip(),
            "ings": [(r["item"].text, r["destroy"], r["amount"].text.strip(), r["group"]) for r in tab["ing_rows"]],
            "ress": [(r["item"].text, r["amount"].text.strip(), r["chance"].text.strip(), r["group"]) for r in tab["res_rows"]]
        }

    def is_tab_modified(self, tab):
        if not tab.get("saved_snapshot"): return False
        return self.get_tab_snapshot(tab) != tab["saved_snapshot"]

    def create_tab_structure(self, filename, data):
        base_inputs = {}
        base_inputs["filename"] = UITextBox(0, 0, 480, 30, self.font, filename or "new_craft.xml")
        craft_opts = [{"label": "Create", "value": "create"}, {"label": "Repair", "value": "repair"}, {"label": "Dismantle", "value": "dismantle"}]
        base_inputs["craft"] = UIDropdown(0, 0, 480, 30, self.font, craft_opts, data.get("craft", "create"))
        base_inputs["type"] = UIDropdown(0, 0, 480, 30, self.font, self.type_opts, data.get("type", ""), searchable=True)
        base_inputs["output"] = UIDropdown(0, 0, 480, 30, self.font, self.item_opts, data.get("output", ""), searchable=True)
        base_inputs["magazine"] = UIDropdown(0, 0, 480, 30, self.font, self.magazine_opts, data.get("magazine", ""), searchable=True)
        
        for f in ["time", "amount"]:
            base_inputs[f] = UITextBox(0, 0, 480, 30, self.font, data.get(f, ""))
            
        base_inputs["req_level"] = UIAttributeList(0, 0, 480, 145, self.font, data.get("req_level", ""))
        base_inputs["gain_xp"] = UIAttributeList(0, 0, 480, 145, self.font, data.get("gain_xp", ""))

        ing_rows = []
        for ing in data.get("ingredients", []):
            n = ing["name"]
            d_val = ing["destroy"]
            is_destroy = d_val.lower() in ["true", "1", "yes"] if isinstance(d_val, str) else bool(d_val)
            
            if n.startswith('[') and n.endswith(']'):
                items = [x.strip() for x in n[1:-1].split(',')]
                if items:
                    ing_rows.append(self._build_ing_row(items[0], is_destroy, ing["amount"], group=False))
                    for item in items[1:]:
                        ing_rows.append(self._build_ing_row(item, is_destroy, ing["amount"], group=True))
            else:
                ing_rows.append(self._build_ing_row(n, is_destroy, ing["amount"], group=False))
            
        res_rows = []
        for res in data.get("results", []):
            n = res["name"]
            if n.startswith('[') and n.endswith(']'):
                items = [x.strip() for x in n[1:-1].split(',')]
                if items:
                    res_rows.append(self._build_res_row(items[0], res["amount"], res.get("chance", ""), group=False))
                    for item in items[1:]:
                        res_rows.append(self._build_res_row(item, res["amount"], res.get("chance", ""), group=True))
            else:
                res_rows.append(self._build_res_row(n, res["amount"], res.get("chance", ""), group=False))

        tab = {
            "filename": filename,
            "base_inputs": base_inputs,
            "ing_rows": ing_rows,
            "res_rows": res_rows,
            "form_scroll": 0,
            "max_scroll": 0
        }
        tab["saved_snapshot"] = self.get_tab_snapshot(tab)
        return tab

    def _build_ing_row(self, name="", destroy=False, amount="1", group=False):
        is_dest = destroy.lower() in ["true", "1", "yes"] if isinstance(destroy, str) else bool(destroy)
        return {
            "group": group,
            "group_btn": pygame.Rect(0, 0, 65, 28),
            "item": UIDropdown(0, 0, 290, 28, self.font, self.item_opts, name, searchable=True),
            "destroy": is_dest,
            "destroy_btn": pygame.Rect(0, 0, 80, 28),
            "amount": UITextBox(0, 0, 50, 28, self.font, str(amount)),
            "del_btn": pygame.Rect(0, 0, 28, 28)
        }

    def _build_res_row(self, name="", amount="1", chance="", group=False):
        return {
            "group": group,
            "group_btn": pygame.Rect(0, 0, 60, 28),
            "item": UIDropdown(0, 0, 290, 28, self.font, self.item_opts, name, searchable=True),
            "amount": UITextBox(0, 0, 60, 28, self.font, str(amount)),
            "chance": UITextBox(0, 0, 60, 28, self.font, str(chance)),
            "del_btn": pygame.Rect(0, 0, 28, 28)
        }

    def open_tab_recipe(self, filename):
        for i, tab in enumerate(self.open_tabs):
            if tab["filename"] == filename:
                self.active_tab_idx = i
                self.layout_form()
                self.ensure_tab_visible(self.active_tab_idx)
                return
        data = self.recipes.get(filename, {}).get("data", {}) if filename else {}
        
        new_tab = self.create_tab_structure(filename, data)
        self.open_tabs.append(new_tab)
        self.active_tab_idx = len(self.open_tabs) - 1
        self.layout_form()
        self.ensure_tab_visible(self.active_tab_idx)

    def request_close_tab(self, idx):
        if not (0 <= idx < len(self.open_tabs)): return
        tab = self.open_tabs[idx]
        if self.is_tab_modified(tab):
            self.close_confirm_dialog = {
                "idx": idx,
                "name": tab["filename"] or tab["base_inputs"]["filename"].text
            }
        else:
            self._force_close_tab(idx)

    def _force_close_tab(self, idx):
        self.open_tabs.pop(idx)
        if not self.open_tabs:
            self.active_tab_idx = -1
        elif self.active_tab_idx == idx:
            # Focus the adjacent tab to the left (or index 0 if the first tab was closed)
            self.active_tab_idx = max(0, idx - 1)
        elif self.active_tab_idx > idx:
            self.active_tab_idx -= 1

        self.layout_form()
        self.ensure_tab_visible(self.active_tab_idx)

    def layout_form(self):
        content_h = len(self.filtered_recipes) * 30 + 10
        self.max_sidebar_scroll = max(0, content_h - (self.height - self.y_offset - 110))

        tab = self.get_current_tab()
        if not tab: return
        
        form_x = self.sidebar_w
        start_x = form_x + 150 
        current_y = self.y_offset + self.tab_bar_h + 20 - tab["form_scroll"]
        
        for f in ["filename", "craft", "type", "output", "magazine", "req_level", "gain_xp", "time", "amount"]:
            tab["base_inputs"][f].rect.x = start_x
            tab["base_inputs"][f].rect.y = current_y
            if hasattr(tab["base_inputs"][f], '_relayout'):
                tab["base_inputs"][f]._relayout()
            if isinstance(tab["base_inputs"][f], UIDropdown):
                tab["base_inputs"][f].list_rect.x = tab["base_inputs"][f].rect.x
                tab["base_inputs"][f].list_rect.y = tab["base_inputs"][f].rect.bottom
            current_y += tab["base_inputs"][f].rect.height + 10
            
        current_y += 50 
        for row in tab["ing_rows"]:
            row["group_btn"].topleft = (form_x + 20, current_y)
            row["item"].rect.topleft = (form_x + 90, current_y)
            row["item"].list_rect.topleft = (form_x + 90, current_y + 28)
            row["destroy_btn"].topleft = (form_x + 400, current_y)
            row["amount"].rect.topleft = (form_x + 480, current_y)
            row["del_btn"].topleft = (form_x + 550, current_y)
            current_y += 35
            
        self.add_ing_btn.topleft = (form_x + 20, current_y)
        current_y += 35 
        
        is_dismantle = tab["base_inputs"]["craft"].text.lower() == "dismantle"
        if is_dismantle:
            current_y += 50
            for row in tab["res_rows"]:
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
        self.duplicate_btn.topleft = (form_x + 165, current_y)
        self.delete_btn.topleft = (form_x + 310, current_y)
        self.code_btn.topleft = (form_x + 435, current_y)
        
        tab["max_scroll"] = max(0, current_y + tab["form_scroll"] - self.height + 40)

    def get_tab_rects(self):
        tab_rects = []
        cur_x = self.sidebar_w - self.tab_scroll_x
        tabs_y = self.y_offset
        
        for i, tab in enumerate(self.open_tabs):
            fname = tab["filename"] or tab["base_inputs"]["filename"].text or "new_craft.xml"
            modified = self.is_tab_modified(tab)
            display_name = f"*{fname}" if modified else fname
            
            text_w = self.font.size(display_name)[0]
            tab_w = max(90, text_w + 44)
            
            tab_rect = pygame.Rect(cur_x, tabs_y, tab_w, self.tab_bar_h)
            close_rect = pygame.Rect(tab_rect.right - 20, tab_rect.y + 10, 16, 16)
            tab_rects.append({
                "index": i,
                "tab": tab,
                "rect": tab_rect,
                "close_rect": close_rect,
                "display_name": display_name,
                "modified": modified
            })
            cur_x += tab_w + 2
            
        total_w = (cur_x + self.tab_scroll_x) - self.sidebar_w
        view_w = self.width - self.sidebar_w
        self.max_tab_scroll = max(0, total_w - view_w)
        return tab_rects

    def save_current_tab(self):
        tab = self.get_current_tab()
        if not tab: return

        new_file = tab["base_inputs"]["filename"].text.strip()
        if not new_file: return
        if not new_file.endswith(".xml"): new_file += ".xml"
        
        data = {}
        for attr in ["type", "craft", "output", "magazine", "req_level", "gain_xp", "time", "amount"]:
            data[attr] = tab["base_inputs"][attr].text

        merged_ings = []
        for r in tab["ing_rows"]:
            item_val = r["item"].text.strip()
            if not item_val: continue
            if r["group"] and merged_ings:
                merged_ings[-1]["names"].append(item_val)
            else:
                merged_ings.append({
                    "names": [item_val],
                    "destroy": "true" if r["destroy"] else "false",
                    "amount": r["amount"].text
                })
                
        data["ingredients"] = []
        for m in merged_ings:
            name_str = f"[{', '.join(m['names'])}]" if len(m['names']) > 1 else m['names'][0]
            data["ingredients"].append({"name": name_str, "destroy": m["destroy"], "amount": m["amount"]})

        is_dismantle = tab["base_inputs"]["craft"].text.lower() == "dismantle"
        data["results"] = []
        if is_dismantle:
            merged_res = []
            for r in tab["res_rows"]:
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
        
        root = ET.Element("recipe")
        for attr in ["type", "craft", "output", "magazine", "req_level", "gain_xp", "amount", "time"]:
            if data.get(attr): root.set(attr, data[attr])
        for ing in data.get("ingredients", []):
            if ing["name"]: ET.SubElement(root, "ingredient", {"name": ing["name"], "destroy": ing["destroy"], "amount": ing["amount"]})
        for res in data.get("results", []):
            if res["name"]:
                res_attr = {"name": res["name"], "amount": res["amount"]}
                if res.get("chance"): res_attr["chance"] = res["chance"]
                ET.SubElement(root, "result", res_attr)
                    
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ", level=0)
        path = os.path.join(self.craft_dir, new_file)
        tree.write(path, encoding="utf-8", xml_declaration=True)

        if tab["filename"] and tab["filename"] != new_file and tab["filename"] in self.recipes:
            old_path = os.path.join(self.craft_dir, tab["filename"])
            if os.path.exists(old_path):
                try: os.remove(old_path)
                except: pass
            del self.recipes[tab["filename"]]

        self.recipes[new_file] = {"data": data}
        tab["filename"] = new_file
        tab["saved_snapshot"] = self.get_tab_snapshot(tab)
        self.build_dynamic_options()

    def duplicate_current_tab(self):
        tab = self.get_current_tab()
        if not tab or tab["filename"] is False: return

        base_name = tab["filename"]
        if base_name.endswith(".xml"): base_name = base_name[:-4]
        base_no_idx = re.sub(r'_\d+$', '', base_name)
        
        counter = 1
        while True:
            dup_fname = f"{base_no_idx}_{counter}.xml"
            if dup_fname not in self.recipes and not os.path.exists(os.path.join(self.craft_dir, dup_fname)):
                break
            counter += 1

        self.save_current_tab()
        with open(os.path.join(self.craft_dir, tab["filename"]), 'r', encoding='utf-8') as src:
            with open(os.path.join(self.craft_dir, dup_fname), 'w', encoding='utf-8') as dst:
                dst.write(src.read())

        self.load_xmls()
        self.open_tab_recipe(dup_fname)

    def delete_current_tab(self):
        tab = self.get_current_tab()
        if not tab: return
        if tab["filename"] and tab["filename"] in self.recipes:
            path = os.path.join(self.craft_dir, tab["filename"])
            if os.path.exists(path):
                try: os.remove(path)
                except: pass
            del self.recipes[tab["filename"]]
        self._force_close_tab(self.active_tab_idx)
        self.build_dynamic_options()

    def handle_event(self, event):
        # 1. Close Confirmation Modal
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

        if event.type == pygame.KEYDOWN:
            if (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_w:
                if 0 <= self.active_tab_idx < len(self.open_tabs):
                    self.request_close_tab(self.active_tab_idx)
                    return True
            if (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_s:
                self.save_current_tab()
                return True

        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_sidebar = False
            self.dragging_form = False
            self.dragging_tab_scroll = False
            
        if event.type == pygame.MOUSEMOTION:
            if self.dragging_sidebar and self.sidebar_thumb_rect and self.max_sidebar_scroll > 0:
                dy = event.pos[1] - self.sidebar_start_y
                track_h = self.sidebar_track_rect.height
                thumb_h = self.sidebar_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    self.sidebar_scroll = max(0, min(self.max_sidebar_scroll, self.sidebar_start_offset + dy * (self.max_sidebar_scroll / track_space)))
                return True
                
            tab = self.get_current_tab()
            if tab and self.dragging_form and self.form_thumb_rect and tab["max_scroll"] > 0:
                dy = event.pos[1] - self.form_start_y
                track_h = self.form_track_rect.height
                thumb_h = self.form_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    tab["form_scroll"] = max(0, min(tab["max_scroll"], self.form_start_offset + dy * (tab["max_scroll"] / track_space)))
                    self.layout_form()
                return True

            if self.dragging_tab_scroll and self.max_tab_scroll > 0:
                dx = event.pos[0] - self.tab_scroll_start_x
                track_w = self.width - self.sidebar_w
                thumb_w = self.tab_thumb_rect.width if self.tab_thumb_rect else 40
                movable = track_w - thumb_w
                if movable > 0:
                    self.tab_scroll_x = max(0, min(self.max_tab_scroll, self.tab_scroll_start_offset + (dx / movable) * self.max_tab_scroll))
                return True

        if self.search_input.handle_event(event):
            self.max_sidebar_scroll = max(0, len(self.filtered_recipes) * 30 + 10 - (self.height - self.y_offset - 110))
            self.sidebar_scroll = max(0, min(self.sidebar_scroll, self.max_sidebar_scroll))
            return True

        # Tab Strip Selection
        tabs_view_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, self.tab_bar_h)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if tabs_view_rect.collidepoint(event.pos):
                if event.button == 4:
                    self.tab_scroll_x = max(0, self.tab_scroll_x - 40)
                    return True
                elif event.button == 5:
                    self.tab_scroll_x = min(self.max_tab_scroll, self.tab_scroll_x + 40)
                    return True
                elif event.button == 1:
                    if self.tab_thumb_rect and self.tab_thumb_rect.collidepoint(event.pos):
                        self.dragging_tab_scroll = True
                        self.tab_scroll_start_x = event.pos[0]
                        self.tab_scroll_start_offset = self.tab_scroll_x
                        return True
                    tab_rects = self.get_tab_rects()
                    for t_info in tab_rects:
                        if t_info["close_rect"].collidepoint(event.pos):
                            self.request_close_tab(t_info["index"])
                            return True
                        elif t_info["rect"].collidepoint(event.pos):
                            self.active_tab_idx = t_info["index"]
                            self.layout_form()
                            self.ensure_tab_visible(self.active_tab_idx)
                            return True

        tab = self.get_current_tab()
        if tab:
            is_dismantle = tab["base_inputs"]["craft"].text.lower() == "dismantle"
            dropdowns = [f for f in tab["base_inputs"].values() if isinstance(f, UIDropdown)]
            dropdowns += [r["item"] for r in tab["ing_rows"]]
            if is_dismantle: dropdowns += [r["item"] for r in tab["res_rows"]]
            
            for d in dropdowns:
                if getattr(d, 'expanded', False):
                    if d.handle_event(event):
                        if d == tab["base_inputs"]["craft"]: self.layout_form()
                        return True
                                  
            consumed = False
            for c in tab["base_inputs"].values():
                if c.handle_event(event): consumed = True
            for r in tab["ing_rows"]:
                if r["item"].handle_event(event): consumed = True
                if not r["group"] and r["amount"].handle_event(event): consumed = True
            if is_dismantle:
                for r in tab["res_rows"]:
                    if r["item"].handle_event(event): consumed = True
                    if not r["group"]:
                        if r["amount"].handle_event(event): consumed = True
                        if r["chance"].handle_event(event): consumed = True
                              
            if consumed:
                self.layout_form()
                return True
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                FocusManager.clear_focus()
                mx, my = event.pos
                if mx > self.sidebar_w:
                    if self.form_thumb_rect and self.form_thumb_rect.collidepoint(mx, my):
                        self.dragging_form = True
                        self.form_start_y = my
                        self.form_start_offset = tab["form_scroll"]
                        return True
                        
                    for i, row in enumerate(tab["ing_rows"]):
                        if row["group_btn"].collidepoint(mx, my):
                            row["group"] = not row["group"]
                            return True
                        if not row["group"] and row["destroy_btn"].collidepoint(mx, my):
                            row["destroy"] = not row["destroy"]
                            return True
                        if row["del_btn"].collidepoint(mx, my):
                            tab["ing_rows"].pop(i)
                            self.layout_form()
                            return True
                            
                    if is_dismantle:
                        for i, row in enumerate(tab["res_rows"]):
                            if row["group_btn"].collidepoint(mx, my):
                                row["group"] = not row["group"]
                                return True
                            if row["del_btn"].collidepoint(mx, my):
                                tab["res_rows"].pop(i)
                                self.layout_form()
                                return True
                            
                    if self.add_ing_btn.collidepoint(mx, my):
                        tab["ing_rows"].append(self._build_ing_row())
                        self.layout_form()
                        return True
                    if is_dismantle and self.add_res_btn.collidepoint(mx, my):
                        tab["res_rows"].append(self._build_res_row())
                        self.layout_form()
                        return True
                    if self.save_btn.collidepoint(mx, my):
                        self.save_current_tab()
                        return True
                    if self.duplicate_btn.collidepoint(mx, my):
                        self.duplicate_current_tab()
                        return True
                    if self.delete_btn.collidepoint(mx, my):
                        self.delete_current_tab()
                        return True
                    if self.code_btn.collidepoint(mx, my):
                        self.save_current_tab()
                        path = os.path.join(self.craft_dir, tab["filename"])
                        return {"action": "open_in_code", "path": path}
                        
            if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] > self.sidebar_w:
                if event.button == 4:
                    tab["form_scroll"] = max(0, tab["form_scroll"] - 40)
                    self.layout_form()
                    return True
                elif event.button == 5:
                    tab["form_scroll"] = min(tab["max_scroll"], tab["form_scroll"] + 40)
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
                    if self.new_btn.collidepoint(mx, my):
                        self.open_tab_recipe(False)
                        return True
                    list_y = self.y_offset + 115 - self.sidebar_scroll
                    for fname in self.filtered_recipes:
                        if pygame.Rect(10, list_y, self.sidebar_w - 30, 25).collidepoint(mx, my):
                            if list_y > self.y_offset + 110:
                                self.open_tab_recipe(fname)
                            return True
                        list_y += 30
        return False

    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect) 
        mouse_pos = pygame.mouse.get_pos()
        
        # 1. Sidebar List
        list_view_rect = pygame.Rect(0, self.y_offset + 110, self.sidebar_w, self.height - self.y_offset - 110)
        surface.set_clip(list_view_rect)
        active_tab = self.get_current_tab()
        selected_fname = active_tab["filename"] if active_tab else None
        
        list_y = self.y_offset + 115 - self.sidebar_scroll
        for fname in self.filtered_recipes:
            r = pygame.Rect(10, list_y, self.sidebar_w - 30, 25)
            if fname == selected_fname:
                pygame.draw.rect(surface, UITheme.LIST_HOVER, r, border_radius=4)
            elif r.collidepoint(mouse_pos):
                pygame.draw.rect(surface, UITheme.HOVER_BG, r, border_radius=4)
            
            lbl = (fname[:25] + '..') if len(fname) > 27 else fname
            surface.blit(self.font.render(lbl, True, UITheme.TEXT), (15, list_y + 5))
            list_y += 30
        surface.set_clip(None)
        
        # 2. Sidebar Header
        sidebar_header_rect = pygame.Rect(0, self.y_offset, self.sidebar_w, 110)
        pygame.draw.rect(surface, UITheme.PANEL_BG, sidebar_header_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset), (self.sidebar_w, self.height), 2)
        surface.blit(self.font.render("Crafting Recipes", True, UITheme.WARNING), (20, self.y_offset + 12))
        
        self.search_input.draw(surface)
        if not self.search_input.text and not self.search_input.active:
            surface.blit(self.font.render("Search crafts...", True, UITheme.TEXT_DIM), (self.search_input.rect.x + 8, self.search_input.rect.y + 6))
        
        draw_styled_button(surface, self.new_btn, "+ New Craft", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)

        if self.max_sidebar_scroll > 0:
            track_rect = pygame.Rect(self.sidebar_w - 8, list_view_rect.y, 8, list_view_rect.height)
            self.sidebar_track_rect = track_rect
            thumb_h = max(20, (list_view_rect.height / (list_view_rect.height + self.max_sidebar_scroll)) * list_view_rect.height)
            thumb_y = list_view_rect.y + (self.sidebar_scroll / self.max_sidebar_scroll) * (list_view_rect.height - thumb_h)
            self.sidebar_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.sidebar_thumb_rect, border_radius=4)

        # 3. Tab Bar Strip
        tabs_view_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, self.tab_bar_h)
        pygame.draw.rect(surface, UITheme.PANEL_BG, tabs_view_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset + self.tab_bar_h - 1), (self.width, self.y_offset + self.tab_bar_h - 1))

        prev_clip = surface.get_clip()
        surface.set_clip(tabs_view_rect.clip(prev_clip) if prev_clip else tabs_view_rect)

        tab_rects = self.get_tab_rects()
        for t_info in tab_rects:
            tab_rect = t_info["rect"]
            close_rect = t_info["close_rect"]
            is_active = (t_info["index"] == self.active_tab_idx)
            is_modified = t_info["modified"]
            hovered = tab_rect.collidepoint(mouse_pos)
            
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

            txt = self.font.render(t_info["display_name"], True, txt_color)
            surface.blit(txt, (tab_rect.x + 8, tab_rect.centery - txt.get_height()//2))

            c_hover = close_rect.collidepoint(mouse_pos)
            pygame.draw.rect(surface, UITheme.DANGER if c_hover else border_color, close_rect, border_radius=3)
            surface.blit(self.font.render("x", True, UITheme.TEXT), (close_rect.x + 4, close_rect.y + 1))
        surface.set_clip(prev_clip)

        if self.max_tab_scroll > 0:
            track_rect = pygame.Rect(self.sidebar_w, self.y_offset + self.tab_bar_h - 4, self.width - self.sidebar_w, 4)
            pygame.draw.rect(surface, UITheme.PANEL_BG, track_rect)
            thumb_w = max(30, int((tabs_view_rect.width / (tabs_view_rect.width + self.max_tab_scroll)) * track_rect.width))
            thumb_x = track_rect.x + (self.tab_scroll_x / self.max_tab_scroll) * (track_rect.width - thumb_w)
            self.tab_thumb_rect = pygame.Rect(thumb_x, track_rect.y, thumb_w, 4)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.tab_thumb_rect, border_radius=2)
        else:
            self.tab_thumb_rect = None

        # 4. Active Tab Form
        tab = self.get_current_tab()
        if tab:
            form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset + self.tab_bar_h, self.width - self.sidebar_w, self.height - self.y_offset - self.tab_bar_h)
            surface.set_clip(form_view_rect)
            form_x = self.sidebar_w
            is_dismantle = tab["base_inputs"]["craft"].text.lower() == "dismantle"
            
            for f in ["filename", "craft", "type", "output", "magazine", "req_level", "gain_xp", "time", "amount"]:
                lbl = f.replace("_", " ").title() + ":"
                y_pos = tab["base_inputs"][f].rect.y
                surface.blit(self.font.render(lbl, True, UITheme.TEXT_DIM), (form_x + 20, y_pos + 6))
                tab["base_inputs"][f].draw(surface)
                
            ing_title_y = tab["base_inputs"]["amount"].rect.bottom + 15
            surface.blit(self.font.render("Ingredients:", True, UITheme.WARNING), (form_x + 20, ing_title_y))
            surface.blit(self.font.render("Link", True, UITheme.TEXT_DIM), (form_x + 20, ing_title_y + 25))
            surface.blit(self.font.render("Item", True, UITheme.TEXT_DIM), (form_x + 90, ing_title_y + 25))
            surface.blit(self.font.render("Destroy", True, UITheme.TEXT_DIM), (form_x + 400, ing_title_y + 25))
            surface.blit(self.font.render("Amount", True, UITheme.TEXT_DIM), (form_x + 480, ing_title_y + 25))
            
            for row in tab["ing_rows"]:
                g_txt = "|_ OR" if row["group"] else "---"
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
                
                for row in tab["res_rows"]:
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
            if tab["filename"] is not False:
                draw_styled_button(surface, self.duplicate_btn, "Duplicate", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
                draw_styled_button(surface, self.delete_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
                draw_styled_button(surface, self.code_btn, "Code", self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG)
                
            for f in tab["base_inputs"].values():
                if isinstance(f, UIDropdown): f.draw_list(surface)
            for row in tab["ing_rows"]: row["item"].draw_list(surface)
            if is_dismantle:
                for row in tab["res_rows"]: row["item"].draw_list(surface)
                
            surface.set_clip(None)
            
            if tab["max_scroll"] > 0:
                track_rect = pygame.Rect(self.width - 8, form_view_rect.y, 8, form_view_rect.height)
                self.form_track_rect = track_rect
                thumb_h = max(20, (form_view_rect.height / (form_view_rect.height + tab["max_scroll"])) * form_view_rect.height)
                thumb_y = form_view_rect.y + (tab["form_scroll"] / tab["max_scroll"]) * (form_view_rect.height - thumb_h)
                self.form_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
                pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.form_thumb_rect, border_radius=4)

        # 5. Unsaved Changes Modal
        if self.close_confirm_dialog:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            
            modal_rect = pygame.Rect(self.width//2 - 280, self.height//2 - 95, 560, 190)
            pygame.draw.rect(surface, UITheme.PANEL_BG, modal_rect, border_radius=8)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, modal_rect, 2, border_radius=8)
            surface.blit(self.font.render("Unsaved Changes", True, UITheme.WARNING), (modal_rect.x + 20, modal_rect.y + 15))
            pygame.draw.line(surface, UITheme.BORDER, (modal_rect.x, modal_rect.y + 40), (modal_rect.right, modal_rect.y + 40))

            surface.blit(self.font.render("You have unsaved changes in:", True, UITheme.TEXT), (modal_rect.x + 25, modal_rect.y + 55))
            surface.blit(self.font.render(self.close_confirm_dialog["name"][:45], True, UITheme.WARNING), (modal_rect.x + 25, modal_rect.y + 82))

            btn_y = modal_rect.bottom - 46
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 20, btn_y, 150, 34), "Save & Close", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 185, btn_y, 240, 34), "Close Without Save", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
            draw_styled_button(surface, pygame.Rect(modal_rect.x + 440, btn_y, 100, 34), "Cancel", self.font, mouse_pos, UITheme.BORDER, UITheme.BORDER_ACTIVE)