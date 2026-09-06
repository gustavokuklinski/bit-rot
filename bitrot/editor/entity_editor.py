import pygame
import os
import re
import xml.etree.ElementTree as ET
from editor.config import GAME_ROOT, TILE_SIZE
from editor.ui import UITextBox, UIDropdown, UITheme, draw_styled_button, register_tooltip

# ----------------------------------------------------------------------
# CUSTOM UI COMPONENTS FOR ENTITY EDITOR
# ----------------------------------------------------------------------
class UIToggle:
    def __init__(self, x, y, width, height, font, state=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.state = state

    @property
    def text(self): return "true" if self.state else "false"

    @text.setter
    def text(self, val): self.state = str(val).lower() == "true"

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

class UIStepButton:
    def __init__(self, x, y, width, height, font, val, steps):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.steps = [str(s) for s in steps]
        self.text = str(val)
        
        if self.text not in self.steps:
            try:
                num_val = float(self.text)
                self.text = min(self.steps, key=lambda s: abs(float(s) - num_val))
            except ValueError:
                self.text = self.steps[0]

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                idx = self.steps.index(self.text)
                if event.button == 1: 
                    self.text = self.steps[(idx + 1) % len(self.steps)]
                    return True
                elif event.button == 3: 
                    self.text = self.steps[(idx - 1) % len(self.steps)]
                    return True
        return False

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        draw_styled_button(surface, self.rect, self.text, self.font, mouse_pos, UITheme.PANEL_BG, UITheme.HOVER_BG, tooltip="L-Click: Up | R-Click: Down")


# ----------------------------------------------------------------------
# STATIC BOILERPLATES
# ----------------------------------------------------------------------
BOILERPLATES = {
    "Animal": """<animal name="Boar" attack_player="true" type="animal" spawn_weight="20" spawn_layer="[1, 2]">
    <name value="Boar" />
    <stats><health min="20" max="30" /><speed min="1" max="2" /><attack min="6" max="15" /><infection min="15" max="35" /></stats>
    <capacity value="3" />
    <visuals><sprite id="center" file="boar.png" /><sprite id="left" file="boar_left.png" /><sprite id="right" file="boar_right.png" /></visuals>
    <loot><item item="Rot Meat" chance="1.0" /></loot>
    <sound><hit src="" /><attack src="" /><dead src="" /><steps src="" /></sound>
</animal>""",

    "Clothes": """<cloth name="New Cloth" type="cloth" id="body" builder="true">
    <properties><defence value="1" /><durability min="1" max="100" /><sprite file="" /><weight weight="0.0" /></properties>
    <spawn chance="1" />
</cloth>""",

    "NPC": """<npc type="common" spawn_weight="55" is_friendly="false" is_static="false">
    <name value="RANDOM" />
    <sex value="RANDOM" />
    <stats><health min="100" max="100" /><speed min="1" max="1" /><attack min="1" max="15" /><infection min="1" max="5" /></stats>
    <clothes><head></head><util></util><hair></hair><facial></facial><feet></feet><hand></hand><body></body><arms></arms><legs></legs></clothes>
    <visuals><sprite id="center" file="player.png" /><sprite id="left" file="player_left.png" /><sprite id="right" file="player_right.png" /></visuals>
    <loot><item item="Kukaroach" chance="0.1" /></loot>
    <sound><hit src="npc_hit.ogg" /><attack src="npc_attack.ogg" /><dead src="npc_dead.ogg" /><steps src="npc_steps.ogg" /></sound>
</npc>""",

    "Vehicle": """<vehicle name="car_new" type="car" is_obstacle="true" spawn_weight="40">
    <capacity value="10" />
    <car>
        <max_speed value="8" /><key value="" /><fuel value="1.0" /><motor value="1.0" /><battery value="1.0" />
        <tire_front_left value="" /><tire_front_right value="" /><tire_back_left value="" /><tire_back_right value="" />
        <lights min="5" max="100" radius="8" /><seats value="4" /> 
    </car>
    <loot><item item="Car Tire" chance="0.3" /></loot>
    <visuals><sprite id="top" file="car_top.png" /><sprite id="down" file="car_down.png" /><sprite id="left" file="car_left.png" /><sprite id="right" file="car_right.png" /></visuals>
</vehicle>""",

    "Zombie": """<zombie type="common">
    <name value="RANDOM" />
    <sex value="RANDOM" />
    <xp min="1" max="15" />
    <stats><health min="10" max="100" /><speed min="1" max="2" /><attack min="1" max="15" /><infection min="1" max="5" /></stats>
    <clothes><head></head><util></util><hair></hair><facial></facial><feet></feet><hand></hand><body></body><arms></arms><legs></legs></clothes>
    <visuals><sprite id="center" file="zombie.png" /><sprite id="left" file="zombie_left.png" /><sprite id="right" file="zombie_right.png" /></visuals>
    <loot><item item="Zombie Meat" chance="1.0" /></loot>
    <sound><hit src="zombie_hit.ogg" /><wander src="zombie_wandering.ogg" /><dead src="zombie_dead.ogg" /><attack src="zombie_attack.ogg" /><steps src="zombie_steps.ogg" /></sound>
</zombie>"""
}

# ----------------------------------------------------------------------
# MAIN EDITOR CLASS
# ----------------------------------------------------------------------
class EntityEditor:
    def __init__(self, y_offset, width, height, font, all_sprites):
        self.y_offset = y_offset
        self.width = width
        self.height = height
        self.font = font
        self.all_sprites = all_sprites 
        
        self.categories = {
            "Zombie": os.path.join(GAME_ROOT, 'lib', 'data', 'zombie'),
            "Vehicle": os.path.join(GAME_ROOT, 'lib', 'data', 'vehicle'),
            "Clothes": os.path.join(GAME_ROOT, 'lib', 'data', 'clothes'),
            "Animal": os.path.join(GAME_ROOT, 'lib', 'data', 'animals'),
            "NPC": os.path.join(GAME_ROOT, 'lib', 'data', 'npc')
        }
        
        for path in self.categories.values():
            if not os.path.exists(path):
                try: os.makedirs(path)
                except: pass
                
        self.active_category = "Zombie"
        self.files = []
        self.selected_file = None
        self.original_tree = None
        self.root_tag = "entity"
        
        # Dynamic Options
        self.item_opts = [{"label": "None", "value": "", "icon": None}]
        self.cloth_opts = [{"label": "None", "value": "", "icon": None}]
        self.cloth_sprites = {} 
        self._build_options()
        
        # UI State
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
        
        # Sidebar UI
        cat_opts = [{"label": c, "value": c} for c in self.categories.keys()]
        self.category_dropdown = UIDropdown(10, self.y_offset + 40, self.sidebar_w - 20, 32, self.font, cat_opts, self.active_category)
        self.new_btn = pygame.Rect(10, self.y_offset + 80, self.sidebar_w - 20, 32)
        
        # Form UI
        self.filename_input = UITextBox(0, 0, 200, 30, self.font, "")
        self.root_tag_input = UITextBox(0, 0, 150, 30, self.font, "")
        
        self.save_btn = pygame.Rect(0, 0, 110, 35)
        self.delete_btn = pygame.Rect(0, 0, 110, 35)
        self.add_loot_btn = pygame.Rect(0, 0, 110, 30)
        
        self.fields = [] 
        self.loot_rows = []
        self.refresh_files()

    def _build_options(self):
        c_dir = self.categories["Clothes"]
        if os.path.exists(c_dir):
            for f in os.listdir(c_dir):
                if f.endswith(".xml"):
                    try:
                        root = ET.parse(os.path.join(c_dir, f)).getroot()
                        name = root.get("name")
                        sprite_node = root.find("properties/sprite")
                        sprite_file = sprite_node.get("file") if sprite_node is not None else ""
                        if name:
                            # FIX: The sprite dict maps by the actual Cloth Name, not the sprite filename
                            icon = self.all_sprites.get(name)
                            self.cloth_opts.append({"label": name, "value": name, "icon": icon})
                            self.cloth_sprites[name] = sprite_file
                    except: pass
                    
        i_dir = os.path.join(GAME_ROOT, 'lib', 'data', 'items')
        if os.path.exists(i_dir):
            for f in os.listdir(i_dir):
                if f.endswith(".xml"):
                    try:
                        name = ET.parse(os.path.join(i_dir, f)).getroot().get("name")
                        if name: 
                            icon = self.all_sprites.get(name)
                            self.item_opts.append({"label": name, "value": name, "icon": icon})
                    except: pass

    def resize(self, width, height):
        self.width = width
        self.height = height
        if self.selected_file is not None:
            self.layout_form()

    def refresh_files(self):
        cat_dir = self.categories[self.active_category]
        if os.path.exists(cat_dir):
            self.files = sorted([f for f in os.listdir(cat_dir) if f.endswith('.xml')])
        else:
            self.files = []
            
        self.selected_file = None
        self.sidebar_scroll = 0      
        self.max_sidebar_scroll = 0  
        
        self.fields.clear()
        self.loot_rows.clear()
        
        if self.files:
            self.select_file(self.files[0])
        else:
            self.layout_form() 

    def flatten_xml(self, root):
        self.fields.clear()
        self.loot_rows.clear()
        self.root_tag = root.tag
        self.root_tag_input.text = root.tag
        
        HEALTH_STEPS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        SPEED_STEPS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        STAT_STEPS = [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        def create_field(path, attr, val, opts=None):
            t_val = str(val).lower()
            tag_name = path.split('/')[-1].split('[')[0] if path else root.tag

            if opts:
                ui_elem = UIDropdown(0, 0, 300, 28, self.font, opts, val, searchable=True)
            elif t_val in ["true", "false"]:
                ui_elem = UIToggle(0, 0, 100, 28, self.font, t_val == "true")
            elif tag_name == "health":
                ui_elem = UIStepButton(0, 0, 100, 28, self.font, val, HEALTH_STEPS)
            elif tag_name in ["speed", "max_speed"]:
                ui_elem = UIStepButton(0, 0, 100, 28, self.font, val, SPEED_STEPS)
            elif tag_name in ["attack", "xp", "infection"]:
                ui_elem = UIStepButton(0, 0, 100, 28, self.font, val, STAT_STEPS)
            else:
                ui_elem = UITextBox(0, 0, 300, 28, self.font, val)
                
            return {"path": path, "attr": attr, "input": ui_elem}

        def traverse(node, path):
            if node.tag in ["visuals", "sound"]: return
            
            if node.tag == "loot":
                for item in node.findall("item"):
                    item_val = item.get("item")
                    attr_name = "item"
                    if item_val is None:
                        item_val = item.get("name", "")
                        attr_name = "name"
                        
                    self.loot_rows.append({
                        "item": UIDropdown(0, 0, 280, 28, self.font, self.item_opts, item_val, searchable=True),
                        "chance": UITextBox(0, 0, 80, 28, self.font, item.get("chance", "1.0")),
                        "del_btn": pygame.Rect(0, 0, 30, 28),
                        "attr_name": attr_name
                    })
                return

            if "clothes" in path and node.tag in ['head', 'util', 'hair', 'facial', 'feet', 'hand', 'body', 'arms', 'legs']:
                cloth_node = node.find('cloth')
                val = cloth_node.get('name', '') if cloth_node is not None else ""
                child_path = f"{path}/{node.tag}[1]"
                self.fields.append(create_field(child_path, "cloth_name", val, opts=self.cloth_opts))
                return 

            for k, v in node.attrib.items():
                self.fields.append(create_field(path, k, v))
                
            if len(node) == 0:
                text_val = node.text.strip() if node.text else ""
                if text_val or not node.attrib:
                    self.fields.append(create_field(path, "#text", text_val))
                
            tag_counts = {}
            for child in node:
                tag = child.tag
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                child_path = f"{path}/{tag}[{tag_counts[tag]}]" if path else f"{tag}[{tag_counts[tag]}]"
                traverse(child, child_path)
                
        traverse(root, "")

    def select_file(self, filename):
        self.selected_file = filename
        self.form_scroll = 0
        
        if filename is False:
            self.filename_input.text = f"new_{self.active_category.lower()}.xml"
            self.original_tree = ET.ElementTree(ET.fromstring(BOILERPLATES[self.active_category]))
            self.flatten_xml(self.original_tree.getroot())
        else:
            self.filename_input.text = filename
            path = os.path.join(self.categories[self.active_category], filename)
            try:
                self.original_tree = ET.parse(path)
                self.flatten_xml(self.original_tree.getroot())
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                self.original_tree = ET.ElementTree(ET.fromstring(BOILERPLATES[self.active_category]))
                self.flatten_xml(self.original_tree.getroot())
                
        self.layout_form()

    def layout_form(self):
        content_h = len(self.files) * 30 + 130
        self.max_sidebar_scroll = max(0, content_h - (self.height - self.y_offset))
        
        if self.selected_file is None: 
            self.max_form_scroll = 0
            return
        
        form_x = self.sidebar_w
        current_y = self.y_offset + 20 - self.form_scroll
        
        self.filename_input.rect.topleft = (form_x + 130, current_y)
        self.root_tag_input.rect.topleft = (form_x + 450, current_y)
        current_y += 60
        
        col_y = current_y
        current_y += 30
        
        for row in self.fields:
            row["input"].rect.topleft = (form_x + 440, current_y)
            if hasattr(row["input"], 'list_rect'):
                row["input"].list_rect.topleft = (form_x + 440, current_y + 28)
            current_y += 35
            
        if self.loot_rows or self.active_category in ["Animal", "Zombie", "Vehicle", "NPC", "Clothes"]:
            current_y += 20
            self.loot_header_y = current_y
            current_y += 30
            
            for row in self.loot_rows:
                row["item"].rect.topleft = (form_x + 20, current_y)
                row["item"].list_rect.topleft = (form_x + 20, current_y + 28)
                row["chance"].rect.topleft = (form_x + 320, current_y)
                row["del_btn"].topleft = (form_x + 420, current_y)
                current_y += 35
                
            self.add_loot_btn.topleft = (form_x + 20, current_y)
            current_y += 45
            
        current_y += 10
        self.save_btn.topleft = (form_x + 20, current_y)
        self.delete_btn.topleft = (form_x + 140, current_y)
        
        self.max_form_scroll = max(0, current_y + self.form_scroll - self.height + 40)

    def save_xml(self):
        fname = self.filename_input.text.strip()
        if not fname: return
        if not fname.endswith(".xml"): fname += ".xml"
        
        root = self.original_tree.getroot()
        root.tag = self.root_tag_input.text.strip() or self.root_tag
        
        def get_node(parent, path_str):
            if not path_str: return parent
            curr = parent
            for p in path_str.split('/'):
                tag = p.split('[')[0]
                idx = int(p.split('[')[1][:-1]) - 1
                found = curr.findall(tag)
                if len(found) > idx:
                    curr = found[idx]
            return curr

        for f in self.fields:
            node = get_node(root, f["path"])
            if node is not None:
                val = f["input"].text.strip()
                
                if f["attr"] == "cloth_name":
                    node.clear() 
                    if val: ET.SubElement(node, "cloth", {"name": val})
                elif f["attr"] == "#text":
                    node.text = val
                else:
                    node.set(f["attr"], val)
                    
        if self.loot_rows or self.active_category in ["Animal", "Zombie", "Vehicle", "NPC", "Clothes"]:
            loot_node = root.find("loot")
            if loot_node is not None:
                loot_node.clear()
            else:
                loot_node = ET.SubElement(root, "loot")
                
            for row in self.loot_rows:
                attr_key = row.get("attr_name", "item" if self.active_category != "Clothes" else "name")
                ET.SubElement(loot_node, "item", {attr_key: row["item"].text, "chance": row["chance"].text})
                
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ", level=0)
        
        path = os.path.join(self.categories[self.active_category], fname)
        tree.write(path, encoding="utf-8", xml_declaration=True)
        
        if self.selected_file and self.selected_file != fname and self.selected_file != False:
            old_path = os.path.join(self.categories[self.active_category], self.selected_file)
            if os.path.exists(old_path): os.remove(old_path)
            
        self.refresh_files()
        self.select_file(fname)

    def delete_xml(self):
        if self.selected_file and self.selected_file != False:
            path = os.path.join(self.categories[self.active_category], self.selected_file)
            if os.path.exists(path): os.remove(path)
            self.refresh_files()

    def get_preview_image(self):
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        base_img = None
        
        if self.original_tree:
            root = self.original_tree.getroot()
            for sprite in root.findall(".//visuals/sprite"):
                if sprite.get("id") in ["center", "top", "body"] or base_img is None:
                    base_img = sprite.get("file")
                    if sprite.get("id") in ["center", "top", "body"]: break
            if not base_img and self.active_category == "Clothes":
                sprite_node = root.find("properties/sprite")
                if sprite_node is not None: base_img = sprite_node.get("file")
                    
        def load_img(fname):
            if not fname: return None
            c_name = os.path.splitext(fname)[0]
            if c_name in self.all_sprites: return self.all_sprites[c_name]
            s_dir = os.path.join(GAME_ROOT, 'lib', 'sprites')
            for sub in ['clothes', 'zombie', 'player', 'npc', 'animals', 'vehicle']:
                p = os.path.join(s_dir, sub, fname)
                if os.path.exists(p):
                    try:
                        img = pygame.image.load(p).convert_alpha()
                        return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                    except: pass
            return None

        img = load_img(base_img)
        if img: surf.blit(img, (0,0))
                
        layer_order = ['legs', 'feet', 'body', 'arms', 'head', 'facial', 'hair', 'util', 'hand']
        clothes_to_draw = []
        
        for f in self.fields:
            if "clothes" in f["path"] and f["attr"] == "cloth_name":
                tag = f["path"].split('/')[-1].split('[')[0]
                if tag in layer_order:
                    cloth_name = f["input"].text.strip()
                    if cloth_name and cloth_name in self.cloth_sprites:
                        s_file = self.cloth_sprites[cloth_name]
                        img = load_img(s_file)
                        if img: clothes_to_draw.append((layer_order.index(tag), img))
                                
        clothes_to_draw.sort(key=lambda x: x[0]) 
        for _, c_img in clothes_to_draw:
            surf.blit(c_img, (0,0))
            
        return surf

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_sidebar = False
            self.dragging_form = False
            
        if event.type == pygame.MOUSEMOTION:
            if self.dragging_sidebar and self.sidebar_thumb_rect and self.max_sidebar_scroll > 0:
                dy = event.pos[1] - self.sidebar_start_y
                track_h = self.height - self.y_offset - 125
                thumb_h = self.sidebar_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    scroll_per_pixel = self.max_sidebar_scroll / track_space
                    self.sidebar_scroll = max(0, min(self.max_sidebar_scroll, self.sidebar_start_offset + dy * scroll_per_pixel))
                return True
                
            if self.dragging_form and self.form_thumb_rect and self.max_form_scroll > 0:
                dy = event.pos[1] - self.form_start_y
                track_h = self.height - self.y_offset
                thumb_h = self.form_thumb_rect.height
                track_space = track_h - thumb_h
                if track_space > 0:
                    scroll_per_pixel = self.max_form_scroll / track_space
                    self.form_scroll = max(0, min(self.max_form_scroll, self.form_start_offset + dy * scroll_per_pixel))
                    self.layout_form()
                return True

        if self.category_dropdown.expanded:
            if self.category_dropdown.handle_event(event):
                if self.category_dropdown.text != self.active_category:
                    self.active_category = self.category_dropdown.text
                    self.refresh_files()
                return True

        if self.category_dropdown.handle_event(event): return True

        if self.selected_file is not None:
            dropdowns = [row["input"] for row in self.fields if isinstance(row["input"], UIDropdown)]
            dropdowns += [row["item"] for row in self.loot_rows]
            
            for d in dropdowns:
                if getattr(d, 'expanded', False):
                    if d.handle_event(event): return True
            
            if self.filename_input.handle_event(event): return True
            if self.root_tag_input.handle_event(event): return True
            for row in self.fields:
                if row["input"].handle_event(event): return True
                
            for row in self.loot_rows:
                if row["item"].handle_event(event): return True
                if row["chance"].handle_event(event): return True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if mx > self.sidebar_w:
                    if self.form_thumb_rect and self.form_thumb_rect.collidepoint(mx, my):
                        self.dragging_form = True
                        self.form_start_y = my
                        self.form_start_offset = self.form_scroll
                        return True
                        
                    if hasattr(self, 'add_loot_btn') and self.add_loot_btn.collidepoint(mx, my):
                        self.loot_rows.append({
                            "item": UIDropdown(0, 0, 280, 28, self.font, self.item_opts, "", searchable=True),
                            "chance": UITextBox(0, 0, 80, 28, self.font, "1.0"),
                            "del_btn": pygame.Rect(0, 0, 30, 28),
                            "attr_name": "item" if self.active_category != "Clothes" else "name"
                        })
                        self.layout_form()
                        return True
                        
                    for i, row in enumerate(self.loot_rows):
                        if row["del_btn"].collidepoint(mx, my):
                            self.loot_rows.pop(i)
                            self.layout_form()
                            return True
                            
                    if self.save_btn.collidepoint(mx, my):
                        self.save_xml()
                        return True
                    if self.selected_file and self.delete_btn.collidepoint(mx, my):
                        self.delete_xml()
                        return True
                        
            if event.type == pygame.MOUSEBUTTONDOWN and event.pos[0] > self.sidebar_w:
                if event.button == 4:
                    self.form_scroll = max(0, self.form_scroll - 40)
                    self.layout_form()
                    return True
                elif event.button == 5:
                    self.form_scroll = min(self.max_form_scroll, self.form_scroll + 40)
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
                        self.select_file(False)
                        return True
                    
                    list_y = self.y_offset + 125 - self.sidebar_scroll
                    for fname in self.files:
                        if pygame.Rect(10, list_y, self.sidebar_w - 30, 25).collidepoint(mx, my):
                            if list_y > self.y_offset + 120:
                                self.select_file(fname)
                            return True
                        list_y += 30
                    
        return False

    def draw(self, surface):
        bg_rect = pygame.Rect(0, self.y_offset, self.width, self.height - self.y_offset)
        pygame.draw.rect(surface, UITheme.BG, bg_rect)
        
        # Sidebar View
        list_view_rect = pygame.Rect(0, self.y_offset + 125, self.sidebar_w, self.height - self.y_offset - 125)
        surface.set_clip(list_view_rect)
        
        mouse_pos = pygame.mouse.get_pos()
        list_y = self.y_offset + 130 - self.sidebar_scroll
        for fname in self.files:
            r = pygame.Rect(10, list_y, self.sidebar_w - 30, 25)
            if fname == self.selected_file:
                pygame.draw.rect(surface, UITheme.LIST_HOVER, r, border_radius=4)
            elif r.collidepoint(mouse_pos):
                pygame.draw.rect(surface, UITheme.HOVER_BG, r, border_radius=4)
                
            lbl = (fname[:25] + '..') if len(fname) > 27 else fname
            surface.blit(self.font.render(lbl, True, UITheme.TEXT), (15, list_y + 4))
            list_y += 30
            
        surface.set_clip(None)
        
        # Sidebar Header
        sidebar_header_rect = pygame.Rect(0, self.y_offset, self.sidebar_w, 125)
        pygame.draw.rect(surface, UITheme.PANEL_BG, sidebar_header_rect)
        pygame.draw.line(surface, UITheme.BORDER, (self.sidebar_w, self.y_offset), (self.sidebar_w, self.height), 2)
        surface.blit(self.font.render("Entity Manager", True, UITheme.WARNING), (20, self.y_offset + 15))
        
        self.category_dropdown.draw(surface)
        btn_color = UITheme.SUCCESS if self.selected_file is False else UITheme.BG
        draw_styled_button(surface, self.new_btn, "+ New Entity", self.font, mouse_pos, btn_color, UITheme.SUCCESS_HOVER)

        if self.max_sidebar_scroll > 0:
            track_rect = pygame.Rect(self.sidebar_w - 8, list_view_rect.y, 8, list_view_rect.height)
            thumb_h = max(20, (list_view_rect.height / (list_view_rect.height + self.max_sidebar_scroll)) * list_view_rect.height)
            thumb_y = list_view_rect.y + (self.sidebar_scroll / self.max_sidebar_scroll) * (list_view_rect.height - thumb_h)
            self.sidebar_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.sidebar_thumb_rect, border_radius=4)

        # Main Form Area
        if self.selected_file is not None:
            form_view_rect = pygame.Rect(self.sidebar_w, self.y_offset, self.width - self.sidebar_w, self.height - self.y_offset)
            surface.set_clip(form_view_rect)
            
            form_x = self.sidebar_w
            
            surface.blit(self.font.render("File Name:", True, UITheme.TEXT_DIM), (form_x + 20, self.filename_input.rect.y + 6))
            self.filename_input.draw(surface)
            
            surface.blit(self.font.render("Root Tag:", True, UITheme.TEXT_DIM), (form_x + 350, self.root_tag_input.rect.y + 6))
            self.root_tag_input.draw(surface)
            
            # Live Feedback Preview Box
            preview_rect = pygame.Rect(self.width - 180, self.y_offset + 20, 150, 150)
            pygame.draw.rect(surface, UITheme.PANEL_BG, preview_rect, border_radius=8)
            pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, preview_rect, 2, border_radius=8)
            
            img = self.get_preview_image()
            if img:
                scaled_img = pygame.transform.scale(img, (128, 128))
                surface.blit(scaled_img, (preview_rect.centerx - 64, preview_rect.centery - 64))
            else:
                surface.blit(self.font.render("No Sprite", True, UITheme.TEXT_DIM), (preview_rect.centerx - 45, preview_rect.centery - 8))
            
            # Fields Headers
            col_y = self.filename_input.rect.bottom + 15
            surface.blit(self.font.render("Node Path", True, UITheme.WARNING), (form_x + 20, col_y))
            surface.blit(self.font.render("Attribute", True, UITheme.WARNING), (form_x + 280, col_y))
            surface.blit(self.font.render("Value", True, UITheme.WARNING), (form_x + 440, col_y))
            
            for row in self.fields:
                path_str = row["path"] or f"<{self.root_tag}>"
                display_path = path_str.replace("/", " > ")
                display_path = re.sub(r'\[\d+\]', '', display_path)
                if len(display_path) > 22: display_path = "..." + display_path[-19:]
                
                attr_str = row["attr"]
                if attr_str == "#text":
                    attr_str = "[Content]"
                elif attr_str == "cloth_name":
                    attr_str = "[Cloth Item]"
                    
                if len(attr_str) > 16: attr_str = attr_str[:13] + "..."
                
                p_text = self.font.render(display_path, True, UITheme.TEXT_DIM)
                a_text = self.font.render(attr_str, True, UITheme.ACCENT)
                
                surface.blit(p_text, (form_x + 20, row["input"].rect.y + 6))
                surface.blit(a_text, (form_x + 280, row["input"].rect.y + 6))
                row["input"].draw(surface)
                
            # Loot UI 
            if hasattr(self, 'loot_header_y'):
                surface.blit(self.font.render("Loot Drops:", True, UITheme.WARNING), (form_x + 20, self.loot_header_y))
                surface.blit(self.font.render("Item", True, UITheme.TEXT_DIM), (form_x + 20, self.loot_header_y + 25))
                surface.blit(self.font.render("Chance", True, UITheme.TEXT_DIM), (form_x + 320, self.loot_header_y + 25))
                
                for row in self.loot_rows:
                    row["item"].draw(surface)
                    row["chance"].draw(surface)
                    draw_styled_button(surface, row["del_btn"], "X", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
                    
                draw_styled_button(surface, self.add_loot_btn, "+ Loot", self.font, mouse_pos, UITheme.ACCENT, UITheme.ACCENT_HOVER)
                
            draw_styled_button(surface, self.save_btn, "Save XML", self.font, mouse_pos, UITheme.SUCCESS, UITheme.SUCCESS_HOVER)
            if self.selected_file:
                draw_styled_button(surface, self.delete_btn, "Delete", self.font, mouse_pos, UITheme.DANGER, UITheme.DANGER_HOVER)
                
            # Draw Overlays (Dropdowns last so they sit on top)
            for row in self.fields:
                if isinstance(row["input"], UIDropdown): row["input"].draw_list(surface)
            for row in self.loot_rows:
                row["item"].draw_list(surface)
                
            surface.set_clip(None)
            
            if self.max_form_scroll > 0:
                track_rect = pygame.Rect(self.width - 8, form_view_rect.y, 8, form_view_rect.height)
                self.form_track_rect = track_rect
                thumb_h = max(20, (form_view_rect.height / (form_view_rect.height + self.max_form_scroll)) * form_view_rect.height)
                thumb_y = form_view_rect.y + (self.form_scroll / self.max_form_scroll) * (form_view_rect.height - thumb_h)
                self.form_thumb_rect = pygame.Rect(track_rect.x, thumb_y, 8, thumb_h)
                pygame.draw.rect(surface, UITheme.BORDER_ACTIVE, self.form_thumb_rect, border_radius=4)

        if self.category_dropdown.expanded:
            self.category_dropdown.draw_list(surface)