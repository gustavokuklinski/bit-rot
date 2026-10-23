import pygame
import sys
import os
import re
import csv
import json
from editor.config import (
    GAME_ROOT, SCREEN_WIDTH, SCREEN_HEIGHT, SIDEBAR_WIDTH, TILE_SIZE, ZOOM_LEVELS, 
    INITIAL_ZOOM_INDEX, FILE_TREE_WIDTH, TOOLBAR_HEIGHT, 
    BUILDINGS_DIR, TAB_BAR_HEIGHT, MODS_DIR, get_active_content_root,
    get_available_mods, get_mod_descriptor, LIB_ROOT
)

from editor.assets import load_map_tiles_from_xml, load_sprite_images, load_items_from_xml
from editor.map import Map
from editor.ui import (
    Sidebar, Toolbar, NewBuildingModal, MenuBar, UITheme, 
    draw_tooltips, draw_styled_button, RenameBuildingModal, UIDropdown
)

import xml.etree.ElementTree as ET

from editor.file_tree import FileTree
from editor.dialog_editor import DialogEditor
from editor.crafts import CraftEditor
from editor.code_editor import CodeEditor
from editor.entity_editor import EntityEditor
from editor.sprite_editor import SpriteEditor
import editor.config as editor_config

pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Rot Engine - Game Editor")

def get_installed_mods():
    mods = ["Vanilla"]
    for m in get_available_mods().keys():
        if m not in mods:
            mods.append(m)
    return mods

def resolve_allowed_modes(mod_name):
    """Maps editor_config list to MenuBar tab titles. Vanilla enables all."""
    all_modes = ["Building", "NPC Dialog", "Crafts", "Entities", "Code", "Art"]
    if not mod_name or mod_name == "Vanilla":
        return all_modes

    desc = get_mod_descriptor(mod_name)
    if not desc or "editor_config" not in desc:
        return all_modes

    raw_config = [str(c).lower().strip() for c in desc.get("editor_config", [])]
    mode_map = {
        "building": "Building", "map": "Building", "buildings": "Building",
        "dialog": "NPC Dialog", "dialogs": "NPC Dialog", "npc dialog": "NPC Dialog", "npc_dialog": "NPC Dialog",
        "craft": "Crafts", "crafts": "Crafts",
        "entity": "Entities", "entities": "Entities",
        "code": "Code",
        "art": "Art", "sprite": "Art", "sprites": "Art"
    }

    allowed = []
    for c in raw_config:
        m = mode_map.get(c)
        if m and m not in allowed:
            allowed.append(m)

    return allowed if allowed else all_modes

try:
    from pygame._sdl2 import Window
    window = Window.from_display_module()
    window.maximize()
except Exception:
    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.RESIZABLE)

try: pygame.scrap.init()
except Exception: pass

font_path = os.path.join(GAME_ROOT, 'lib', 'font', 'PixelOperator8.ttf')
try:
    FONT = pygame.font.Font(font_path, 16) if os.path.exists(font_path) else pygame.font.Font(None, 24)
except Exception:
    FONT = pygame.font.Font(None, 24)

MAP_PATTERN = re.compile(r"(map_L\d+_P(?:\d+_)*\d+)(_light|_roof|_map|_spawn|_ground)?\.csv")
BUILDING_PATTERN = re.compile(r"(.+)(_light|_roof|_map|_spawn|_ground)\.csv")

def resolve_item_metadata(name, tab_type="Items"):
    """Finds the corresponding XML or JSON file, category, and sprite PNG across subfolders."""
    clean_name = name.strip("[]")
    name_alts = {clean_name.lower(), clean_name.lower().replace(" ", "_"), clean_name.lower().replace("_", " ")}

    active_root = get_active_content_root()
    item_dir = os.path.join(active_root, 'data', 'items')
    s_item_dir = os.path.join(active_root, 'sprites', 'items')

    if os.path.exists(item_dir):
        for root_d, dirs, files in os.walk(item_dir):
            for f in files:
                p = os.path.join(root_d, f)
                stem = os.path.splitext(f)[0].lower()
                if f.endswith('.xml'):
                    try:
                        root = ET.parse(p).getroot()
                        if root.attrib.get('name', '').lower() in name_alts or stem in name_alts:
                            sp_node = root.find(".//sprite")
                            sp_file = sp_node.attrib.get('file', f"{stem}.png") if sp_node is not None else f"{stem}.png"
                            if not sp_file.lower().endswith('.png'): sp_file += '.png'
                            return {"category": "Items", "xml_filename": f, "xml_path": p, "sprite_path": os.path.join(s_item_dir, sp_file)}
                    except Exception: pass
                elif f.endswith('.json'):
                    try:
                        with open(p, 'r', encoding='utf-8') as jf:
                            jd = json.load(jf)
                        if stem in name_alts or any(stem in k.lower() for k in jd.keys()):
                            return {"category": "Items", "xml_filename": f, "xml_path": p, "sprite_path": os.path.join(s_item_dir, f"{stem}.png")}
                    except Exception: pass

    target_dir = os.path.join(active_root, 'data', 'map' if tab_type == "Tiles" else 'items')
    target_s_dir = os.path.join(active_root, 'sprites', 'map' if tab_type == "Tiles" else 'items')
    return {
        "category": "Map" if tab_type == "Tiles" else "Items",
        "xml_filename": f"{clean_name}.json",
        "xml_path": os.path.join(target_dir, f"{clean_name}.json"),
        "sprite_path": os.path.join(target_s_dir, f"{clean_name}.png")
    }

def get_map_dimensions(map_name, map_dir):
    try:
        for f in os.listdir(map_dir):
            if f.startswith(f"{map_name}_") and f.endswith(".csv"):
                 try:
                     with open(os.path.join(map_dir, f), 'r') as csvfile:
                         reader = list(csv.reader(csvfile))
                         height = len(reader)
                         width = len(reader[0]) if height > 0 else 0
                         return width, height
                 except: continue
    except OSError: pass
    return None

def load_map_layers(game_map, map_name, map_dir):
    dims = get_map_dimensions(map_name, map_dir)
    if dims: game_map.resize(dims[0], dims[1])
    
    game_map.layers = {}
    detected_layers = []

    if os.path.exists(map_dir):
        for filename in os.listdir(map_dir):
            if filename.startswith(f'{map_name}_') and filename.endswith('.csv'):
                for suffix in ['light', 'roof', 'map', 'ground', 'spawn']:
                     if filename == f"{map_name}_{suffix}.csv":
                         detected_layers.append(suffix)
                         game_map.load_from_csv(os.path.join(map_dir, filename), suffix)

    all_layers = ['light', 'roof', 'map', 'spawn', 'ground']
    for l in all_layers:
        if l not in game_map.layers:
            game_map.layers[l] = [[None for _ in range(game_map.width)] for _ in range(game_map.height)]
            game_map.layer_properties[l] = {"visible": True, "opacity": 255}
                 
    game_map.default_layers = detected_layers if detected_layers else all_layers
    game_map.set_active_layer(game_map.default_layers[0])

def save_map_layers(game_map, map_name, map_dir):
    for layer in game_map.layers.keys():
        path = os.path.join(map_dir, f"{map_name}_{layer}.csv")
        game_map.save_to_csv(path, layer)
        print(f"Saved {path}")

def editor():
    pygame.event.pump()
    current_screen_width, current_screen_height = screen.get_size()

    xml_path = os.path.join(GAME_ROOT, 'lib', 'data', 'map')
    sprite_path = os.path.join(GAME_ROOT, 'lib', 'sprites', 'map')
    item_sprite_path = os.path.join(GAME_ROOT, 'lib', 'sprites', 'items')
    item_xml_path = os.path.join(GAME_ROOT, 'lib', 'data', 'items')
    clothes_sprite_path = os.path.join(GAME_ROOT, 'lib', 'sprites', 'clothes')
    clothes_xml_path = os.path.join(GAME_ROOT, 'lib', 'data', 'clothes')
    
    map_tiles = load_map_tiles_from_xml(xml_path, sprite_path)
    item_tiles = load_items_from_xml(item_xml_path, item_sprite_path) if os.path.exists(item_xml_path) else {}
    if os.path.exists(clothes_xml_path):
        item_tiles.update(load_items_from_xml(clothes_xml_path, clothes_sprite_path))

    all_sprites_dict = {
        **map_tiles, **item_tiles,
        **load_sprite_images(os.path.join(GAME_ROOT, 'lib', 'sprites', 'zombie')),
        **load_sprite_images(os.path.join(GAME_ROOT, 'lib', 'sprites', 'vehicle')),
        **load_sprite_images(os.path.join(GAME_ROOT, 'lib', 'sprites', 'animals')),
        **load_sprite_images(os.path.join(GAME_ROOT, 'lib', 'sprites', 'npc')),
        **load_sprite_images(os.path.join(GAME_ROOT, 'lib', 'sprites', 'player'))
    }
    all_render_tiles = {**map_tiles, **item_tiles}

    installed_mods = get_installed_mods()
    mod_options = [{"label": f"Mod: {m}", "value": m} for m in installed_mods]
    mod_dropdown = UIDropdown(current_screen_width - 220, 5, 210, 30, FONT, mod_options, editor_config.ACTIVE_MOD)

    initial_modes = resolve_allowed_modes(editor_config.ACTIVE_MOD)
    menu_bar = MenuBar(current_screen_width - 230, TAB_BAR_HEIGHT, FONT, initial_modes)
    editor_mode = initial_modes[0]

    building_file_tree = FileTree(0, TAB_BAR_HEIGHT, FILE_TREE_WIDTH, current_screen_height - TAB_BAR_HEIGHT, BUILDINGS_DIR, BUILDING_PATTERN, FONT)
    toolbar = Toolbar(FILE_TREE_WIDTH, TAB_BAR_HEIGHT, current_screen_width - FILE_TREE_WIDTH - SIDEBAR_WIDTH, TOOLBAR_HEIGHT, FONT)
    sidebar = Sidebar(current_screen_width - SIDEBAR_WIDTH, TAB_BAR_HEIGHT, map_tiles, item_tiles, FONT)

    dialog_editor = DialogEditor(TAB_BAR_HEIGHT, current_screen_width, current_screen_height, FONT, item_tiles)
    craft_editor = CraftEditor(TAB_BAR_HEIGHT, current_screen_width, current_screen_height, FONT, item_tiles)
    entity_editor = EntityEditor(TAB_BAR_HEIGHT, current_screen_width, current_screen_height, FONT, all_sprites_dict)
    code_editor = CodeEditor(TAB_BAR_HEIGHT, current_screen_width, current_screen_height, FONT)
    sprite_editor = SpriteEditor(TAB_BAR_HEIGHT, current_screen_width, current_screen_height, FONT)

    new_building_modal = NewBuildingModal(current_screen_width//2-150, current_screen_height//2-150, 300, 300, FONT)
    rename_modal = RenameBuildingModal(FONT)

    building_tabs = []
    active_b_idx = -1
    b_tab_scroll_x = 0
    max_b_tab_scroll = 0
    b_tab_bar_h = 34
    content_y = TAB_BAR_HEIGHT + TOOLBAR_HEIGHT + b_tab_bar_h

    def reload_editor_environment(selected_mod):
        nonlocal map_tiles, item_tiles, all_sprites_dict, all_render_tiles, editor_mode
        editor_config.ACTIVE_MOD = selected_mod

        # 1. Update MenuBar modes according to mod editor_config
        allowed_modes = resolve_allowed_modes(selected_mod)
        menu_bar.set_modes(allowed_modes)
        if editor_mode not in allowed_modes:
            editor_mode = allowed_modes[0]

        active_root = get_active_content_root(selected_mod)
        b_dir = os.path.join(active_root, 'map', 'buildings')

        # 2. Reload sprites: Vanilla baseline + Mod overrides
        vanilla_sprites = os.path.join(LIB_ROOT, 'sprites')
        mod_sprites = os.path.join(active_root, 'sprites')

        base_sprites = {}
        for sub in ['map', 'items', 'clothes', 'zombie', 'vehicle', 'animals', 'npc', 'player']:
            v_sub = os.path.join(vanilla_sprites, sub)
            if os.path.exists(v_sub):
                base_sprites.update(load_sprite_images(v_sub))

        if os.path.exists(mod_sprites):
            for sub in ['map', 'items', 'clothes', 'zombie', 'vehicle', 'animals', 'npc', 'player']:
                m_sub = os.path.join(mod_sprites, sub)
                if os.path.exists(m_sub):
                    base_sprites.update(load_sprite_images(m_sub))

        all_sprites_dict = base_sprites

        x_map = os.path.join(active_root, 'data', 'map')
        s_map = os.path.join(active_root, 'sprites', 'map')
        x_item = os.path.join(active_root, 'data', 'items')
        s_item = os.path.join(active_root, 'sprites', 'items')
        
        map_tiles = load_map_tiles_from_xml(x_map, s_map if os.path.exists(s_map) else os.path.join(vanilla_sprites, 'map'))
        item_tiles = load_items_from_xml(x_item, s_item if os.path.exists(s_item) else os.path.join(vanilla_sprites, 'items')) if os.path.exists(x_item) else {}
        all_render_tiles = {**map_tiles, **item_tiles}

        # 3. Dynamic sync across all sub-editors
        building_file_tree.root_dir = b_dir
        building_file_tree.refresh()

        dialog_editor.refresh_files()
        craft_editor.craft_dir = os.path.join(active_root, 'data', 'craft')
        craft_editor.load_xmls()

        code_editor.file_tree.root_dir = os.path.join(active_root, 'data')
        code_editor.file_tree.refresh()

        sprite_editor.reload_for_mod(mod_sprites)
        entity_editor.reload_for_mod(all_sprites_dict)

    RULER_W = 28
    RULER_H = 18
    RULER_FONT = pygame.font.Font(None, 15)

    def open_building_tab(folder, name, root_dir):
        nonlocal active_b_idx, b_tab_scroll_x, max_b_tab_scroll
        for i, tab in enumerate(building_tabs):
            if tab["folder"] == folder and tab["name"] == name:
                active_b_idx = i
                ensure_b_tab_visible(i)
                return

        g_map = Map(width=20, height=20)
        load_map_layers(g_map, name, root_dir)
        
        for l_name in g_map.layers.keys():
            l_key = (folder, name, l_name)
            if l_key in building_file_tree.layer_properties:
                g_map.layer_properties[l_name]["visible"] = building_file_tree.layer_properties[l_key]["visible"]

        building_tabs.append({
            "map": g_map,
            "folder": folder,
            "name": name,
            "root_dir": root_dir,
            "cam_x": FILE_TREE_WIDTH + 20 + RULER_W,
            "cam_y": content_y + 20 + RULER_H,
            "zoom_idx": INITIAL_ZOOM_INDEX,
            "sel_rect": None,
            "sel_start": None,
            "is_selecting": False,
            "modified": False
        })
        active_b_idx = len(building_tabs) - 1
        ensure_b_tab_visible(active_b_idx)

    def ensure_b_tab_visible(idx):
        nonlocal b_tab_scroll_x, max_b_tab_scroll
        if not (0 <= idx < len(building_tabs)): return
        start_x = FILE_TREE_WIDTH
        view_w = current_screen_width - FILE_TREE_WIDTH - SIDEBAR_WIDTH
        rel_x = 0
        target_l, target_r = 0, 0
        for i, t in enumerate(building_tabs):
            d_name = f"*{t['name']}" if t["modified"] else t["name"]
            tw = max(90, FONT.size(d_name)[0] + 44)
            if i == idx:
                target_l, target_r = rel_x, rel_x + tw
            rel_x += tw + 2
        total_w = rel_x - 2 if rel_x > 0 else 0
        max_b_tab_scroll = max(0, total_w - view_w)
        if target_r > b_tab_scroll_x + view_w:
            b_tab_scroll_x = (target_r + 15) - view_w
        elif target_l < b_tab_scroll_x:
            b_tab_scroll_x = max(0, target_l - 15)
        b_tab_scroll_x = max(0, min(max_b_tab_scroll, b_tab_scroll_x))

    def close_building_tab(idx):
        nonlocal active_b_idx
        if not (0 <= idx < len(building_tabs)): return
        building_tabs.pop(idx)
        if not building_tabs:
            active_b_idx = -1
        elif active_b_idx == idx:
            active_b_idx = max(0, idx - 1)
        elif active_b_idx > idx:
            active_b_idx -= 1
        ensure_b_tab_visible(active_b_idx)

    if building_file_tree.selected_map:
        fld, m_name = building_file_tree.selected_map
        b_root = os.path.join(BUILDINGS_DIR, fld) if fld else BUILDINGS_DIR
        open_building_tab(fld, m_name, b_root)

    clipboard = None
    tile_to_place = None
    dragging_cam = False
    drag_start = (0, 0)

    running = True
    while running:
        cur_tab = building_tabs[active_b_idx] if 0 <= active_b_idx < len(building_tabs) else None
        
        total_view_rect = pygame.Rect(FILE_TREE_WIDTH + 10, content_y + 10, current_screen_width - FILE_TREE_WIDTH - SIDEBAR_WIDTH - 20, current_screen_height - content_y - 20)
        ruler_top_rect = pygame.Rect(total_view_rect.left + RULER_W, total_view_rect.top, total_view_rect.width - RULER_W, RULER_H)
        ruler_left_rect = pygame.Rect(total_view_rect.left, total_view_rect.top + RULER_H, RULER_W, total_view_rect.height - RULER_H)
        ruler_corner_rect = pygame.Rect(total_view_rect.left, total_view_rect.top, RULER_W, RULER_H)
        map_view_rect = pygame.Rect(total_view_rect.left + RULER_W, total_view_rect.top + RULER_H, total_view_rect.width - RULER_W, total_view_rect.height - RULER_H)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False

            if event.type == pygame.VIDEORESIZE:
                current_screen_width, current_screen_height = event.w, event.h
                pygame.display.set_mode((current_screen_width, current_screen_height), pygame.RESIZABLE)
                mod_dropdown.rect.x = current_screen_width - 220
                mod_dropdown.list_rect.x = mod_dropdown.rect.x
                menu_bar.resize(current_screen_width - 230)
                sidebar.resize(current_screen_width - SIDEBAR_WIDTH, TAB_BAR_HEIGHT, current_screen_height)
                building_file_tree.resize(current_screen_height - TAB_BAR_HEIGHT)
                toolbar.resize(current_screen_width - FILE_TREE_WIDTH - SIDEBAR_WIDTH)
                dialog_editor.resize(current_screen_width, current_screen_height)
                craft_editor.resize(current_screen_width, current_screen_height)
                entity_editor.resize(current_screen_width, current_screen_height)
                code_editor.resize(current_screen_width, current_screen_height)
                sprite_editor.resize(current_screen_width, current_screen_height)

            # Mod Switcher Interaction
            if mod_dropdown.expanded:
                if mod_dropdown.handle_event(event):
                    if mod_dropdown.text != editor_config.ACTIVE_MOD:
                        reload_editor_environment(mod_dropdown.text)
                    continue
            if mod_dropdown.handle_event(event):
                if mod_dropdown.text != editor_config.ACTIVE_MOD:
                    reload_editor_environment(mod_dropdown.text)
                continue

            menu_action = menu_bar.handle_event(event)
            if menu_action:
                editor_mode = menu_action
                continue

            if editor_mode == "NPC Dialog":
                res = dialog_editor.handle_event(event)
                if isinstance(res, dict) and res.get("action") == "open_in_code":
                    code_editor.open_file(res["path"])
                    editor_mode = "Code"
                    menu_bar.active_mode = "Code"
                continue
            elif editor_mode == "Crafts":
                res = craft_editor.handle_event(event)
                if isinstance(res, dict) and res.get("action") == "open_in_code":
                    code_editor.open_file(res["path"])
                    editor_mode = "Code"
                    menu_bar.active_mode = "Code"
                continue
            elif editor_mode == "Entities":
                res = entity_editor.handle_event(event)
                if isinstance(res, dict):
                    if res.get("action") == "open_in_code":
                        code_editor.open_file(res["path"])
                        editor_mode = "Code"
                        menu_bar.active_mode = "Code"
                    elif res.get("action") == "open_in_art":
                        sprite_editor.open_tab_sprite(res["path"])
                        editor_mode = "Art"
                        menu_bar.active_mode = "Art"
                continue
            elif editor_mode == "Code":
                code_editor.handle_event(event)
                continue
            elif editor_mode == "Art":
                sprite_editor.handle_event(event)
                continue

            # Building Modals
            if new_building_modal.active:
                res = new_building_modal.handle_event(event)
                if isinstance(res, dict) and res.get('action') == 'create_building':
                    b_name, w, h = res['name'], res['width'], res['height']
                    target_b_dir = os.path.join(get_active_content_root(), 'map', 'buildings')
                    os.makedirs(target_b_dir, exist_ok=True)
                    for suffix in ['light', 'roof', 'map', 'ground', 'spawn']:
                        path = os.path.join(target_b_dir, f"{b_name}_{suffix}.csv")
                        with open(path, 'w', newline='') as f:
                            csv.writer(f).writerows([[''] * w for _ in range(h)])
                    building_file_tree.refresh()
                    open_building_tab("", b_name, target_b_dir)
                continue

            if rename_modal.active:
                res = rename_modal.handle_event(event)
                if isinstance(res, dict) and res.get('action') == 'rename_building':
                    o_name, n_name, r_dir = res['old_name'], res['new_name'], res['root_dir']
                    for suffix in ['light', 'roof', 'map', 'ground', 'spawn']:
                        op = os.path.join(r_dir, f"{o_name}_{suffix}.csv")
                        np = os.path.join(r_dir, f"{n_name}_{suffix}.csv")
                        if os.path.exists(op): os.rename(op, np)
                    
                    for tab in building_tabs:
                        if tab["name"] == o_name and tab.get("folder") == res.get("folder"):
                            tab["name"] = n_name
                            
                    building_file_tree.refresh()
                continue

            if sidebar.context_menu:
                sb_res = sidebar.handle_event(event)
                if sb_res and isinstance(sb_res, dict) and sb_res.get("action") == "item_context_action":
                    item_name = sb_res["item_name"]
                    option = sb_res["option"]
                    meta = resolve_item_metadata(item_name, sb_res["tab"])
                    
                    if option == "edit_entity":
                        cat = meta.get("category", "Items")
                        entity_editor.active_category = cat
                        entity_editor.category_dropdown.selected_value = cat
                        entity_editor.category_dropdown._update_label()
                        entity_editor.refresh_file_list()
                        entity_editor.open_tab_file(meta.get("xml_filename", f"{item_name}.xml"))
                        editor_mode = "Entities"
                        menu_bar.active_mode = "Entities"
                    elif option == "edit_sprite":
                        sp_p = meta.get("sprite_path")
                        if sp_p:
                            if not os.path.exists(sp_p):
                                os.makedirs(os.path.dirname(sp_p), exist_ok=True)
                                pygame.image.save(pygame.Surface((16, 16), pygame.SRCALPHA), sp_p)
                            sprite_editor.open_tab_sprite(sp_p)
                            editor_mode = "Art"
                            menu_bar.active_mode = "Art"
                    elif option == "edit_code":
                        x_p = meta.get("xml_path")
                        if x_p:
                            if not os.path.exists(x_p):
                                os.makedirs(os.path.dirname(x_p), exist_ok=True)
                                with open(x_p, 'w', encoding='utf-8') as f:
                                    f.write(f'<!-- {item_name} -->\n<item name="{item_name}" />\n')
                                code_editor.file_tree.refresh()
                            code_editor.open_file(x_p)
                            editor_mode = "Code"
                            menu_bar.active_mode = "Code"
                continue

            if toolbar.tools_expanded:
                tb_action = toolbar.handle_event(event)
                if tb_action and tb_action is not True:
                    if tb_action == "SELECTION" and cur_tab:
                        cur_tab["is_selecting"] = True
                        tile_to_place = None
                        toolbar.active_tool = "SELECTION"
                    elif tb_action == "FILL" and cur_tab:
                        if cur_tab["sel_rect"] and sidebar.selected_tile:
                            cur_tab["map"].fill_rect(cur_tab["sel_rect"], sidebar.selected_tile, cur_tab["map"].active_layer_name)
                            cur_tab["modified"] = True
                    elif tb_action == "ERASER":
                        tile_to_place = "eraser"
                        toolbar.active_tool = "ERASER"
                    elif tb_action == "UNDO" and cur_tab:
                        cur_tab["map"].undo()
                    elif tb_action == "CLEAR" and cur_tab:
                        rect = cur_tab["sel_rect"] if cur_tab["sel_rect"] else pygame.Rect(0, 0, cur_tab["map"].width, cur_tab["map"].height)
                        cur_tab["map"].clear_rect(rect, cur_tab["map"].active_layer_name)
                        cur_tab["modified"] = True
                    elif tb_action == "COPY" and cur_tab and cur_tab["sel_rect"]:
                        clipboard = cur_tab["map"].get_tiles_in_rect(cur_tab["sel_rect"], cur_tab["map"].active_layer_name)
                    elif tb_action == "PASTE" and cur_tab and clipboard:
                        tx, ty = (cur_tab["sel_rect"].x, cur_tab["sel_rect"].y) if cur_tab["sel_rect"] else (0, 0)
                        cur_tab["map"].paste_tiles((tx, ty), clipboard, cur_tab["map"].active_layer_name)
                        cur_tab["modified"] = True
                continue

            if event.type == pygame.KEYDOWN:
                ctrl = (event.mod & pygame.KMOD_CTRL)
                if ctrl and event.key == pygame.K_s and cur_tab:
                    save_map_layers(cur_tab["map"], cur_tab["name"], cur_tab["root_dir"])
                    cur_tab["modified"] = False
                elif ctrl and event.key == pygame.K_w and cur_tab:
                    close_building_tab(active_b_idx)
                elif ctrl and event.key == pygame.K_z and cur_tab:
                    cur_tab["map"].undo()
                elif ctrl and event.key == pygame.K_c and cur_tab and cur_tab["sel_rect"]:
                    clipboard = cur_tab["map"].get_tiles_in_rect(cur_tab["sel_rect"], cur_tab["map"].active_layer_name)
                elif ctrl and event.key == pygame.K_v and cur_tab and clipboard:
                    tx, ty = (cur_tab["sel_rect"].x, cur_tab["sel_rect"].y) if cur_tab["sel_rect"] else (0, 0)
                    cur_tab["map"].paste_tiles((tx, ty), clipboard, cur_tab["map"].active_layer_name)
                    cur_tab["modified"] = True
                elif event.key == pygame.K_ESCAPE and cur_tab:
                    cur_tab["is_selecting"] = False
                    cur_tab["sel_rect"] = None
                    tile_to_place = None
                    toolbar.active_tool = None

            b_tabs_rect = pygame.Rect(FILE_TREE_WIDTH, TAB_BAR_HEIGHT + TOOLBAR_HEIGHT, current_screen_width - FILE_TREE_WIDTH - SIDEBAR_WIDTH, b_tab_bar_h)
            if event.type == pygame.MOUSEBUTTONDOWN and b_tabs_rect.collidepoint(event.pos):
                if event.button == 4:
                    b_tab_scroll_x = max(0, b_tab_scroll_x - 40)
                    continue
                elif event.button == 5:
                    b_tab_scroll_x = min(max_b_tab_scroll, b_tab_scroll_x + 40)
                    continue
                elif event.button == 1:
                    cur_tx = FILE_TREE_WIDTH - b_tab_scroll_x
                    for i, t in enumerate(building_tabs):
                        tw = max(90, FONT.size(f"*{t['name']}" if t['modified'] else t['name'])[0] + 44)
                        t_box = pygame.Rect(cur_tx, b_tabs_rect.y, tw, b_tab_bar_h)
                        c_box = pygame.Rect(t_box.right - 20, t_box.y + 9, 16, 16)
                        if c_box.collidepoint(event.pos):
                            close_building_tab(i)
                            break
                        elif t_box.collidepoint(event.pos):
                            active_b_idx = i
                            ensure_b_tab_visible(i)
                            break
                        cur_tx += tw + 2
                    continue

            tb_action = toolbar.handle_event(event)
            if tb_action:
                if tb_action == "NEW BUILDING":
                    new_building_modal.open(BUILDINGS_DIR, current_screen_width // 2, current_screen_height // 2)
                elif tb_action == "RENAME" and cur_tab:
                    rename_modal.open(cur_tab["name"], cur_tab["folder"], cur_tab["root_dir"], current_screen_width//2, current_screen_height//2)
                elif tb_action == "SAVE MAP" and cur_tab:
                    save_map_layers(cur_tab["map"], cur_tab["name"], cur_tab["root_dir"])
                    cur_tab["modified"] = False
                continue

            sb_res = sidebar.handle_event(event)
            if sb_res:
                if isinstance(sb_res, dict) and sb_res.get("action") == "item_context_action":
                    item_name = sb_res["item_name"]
                    option = sb_res["option"]
                    meta = resolve_item_metadata(item_name, sb_res["tab"])
                    
                    if option == "edit_entity":
                        cat = meta.get("category", "Items")
                        entity_editor.active_category = cat
                        entity_editor.category_dropdown.selected_value = cat
                        entity_editor.category_dropdown._update_label()
                        entity_editor.refresh_file_list()
                        entity_editor.open_tab_file(meta.get("xml_filename", f"{item_name}.xml"))
                        editor_mode = "Entities"
                        menu_bar.active_mode = "Entities"
                    elif option == "edit_sprite":
                        sp_p = meta.get("sprite_path")
                        if sp_p:
                            if not os.path.exists(sp_p):
                                os.makedirs(os.path.dirname(sp_p), exist_ok=True)
                                pygame.image.save(pygame.Surface((16, 16), pygame.SRCALPHA), sp_p)
                            sprite_editor.open_tab_sprite(sp_p)
                            editor_mode = "Art"
                            menu_bar.active_mode = "Art"
                    elif option == "edit_code":
                        x_p = meta.get("xml_path")
                        if x_p:
                            if not os.path.exists(x_p):
                                os.makedirs(os.path.dirname(x_p), exist_ok=True)
                                with open(x_p, 'w', encoding='utf-8') as f:
                                    f.write(f'<!-- {item_name} -->\n<item name="{item_name}" />\n')
                                code_editor.file_tree.refresh()
                            code_editor.open_file(x_p)
                            editor_mode = "Code"
                            menu_bar.active_mode = "Code"
                    continue
                else:
                    if sidebar.selected_tile or sidebar.selected_item:
                        tile_to_place = None
                        toolbar.active_tool = None
                    continue

            ft_res = building_file_tree.handle_event(event)
            if ft_res:
                if isinstance(ft_res, dict):
                    if ft_res.get('action') == 'select_map':
                        fld, m_name = ft_res['folder'], ft_res['map_name']
                        r_dir = os.path.join(BUILDINGS_DIR, fld) if fld else BUILDINGS_DIR
                        open_building_tab(fld, m_name, r_dir)
                    elif ft_res.get('action') == 'toggle_visibility':
                        for tab in building_tabs:
                            if tab["folder"] == ft_res["folder"] and tab["name"] == ft_res["map_name"]:
                                tab["map"].layer_properties[ft_res["layer_name"]]["visible"] = ft_res["visible"]
                    elif ft_res.get('action') == 'set_active_layer' and cur_tab:
                        cur_tab["map"].set_active_layer(ft_res['layer_name'])
                continue

            if cur_tab:
                z_scale = ZOOM_LEVELS[cur_tab["zoom_idx"]]
                if event.type == pygame.MOUSEBUTTONDOWN and map_view_rect.collidepoint(event.pos):
                    if event.button == 3:
                        dragging_cam = True
                        drag_start = event.pos
                    elif event.button == 4:
                        cur_tab["zoom_idx"] = min(len(ZOOM_LEVELS)-1, cur_tab["zoom_idx"]+1)
                    elif event.button == 5:
                        cur_tab["zoom_idx"] = max(0, cur_tab["zoom_idx"]-1)
                    elif event.button == 1:
                        mx, my = event.pos
                        map_x = int(((mx - cur_tab["cam_x"]) / z_scale) // TILE_SIZE)
                        map_y = int(((my - cur_tab["cam_y"]) / z_scale) // TILE_SIZE)

                        if cur_tab["is_selecting"]:
                            cur_tab["sel_start"] = (map_x, map_y)
                            cur_tab["sel_rect"] = pygame.Rect(map_x, map_y, 1, 1)
                        elif tile_to_place == "eraser":
                            cur_tab["map"].set_tile(map_x, map_y, None)
                            cur_tab["modified"] = True
                        elif sidebar.selected_tile:
                            cur_tab["map"].set_tile(map_x, map_y, sidebar.selected_tile)
                            cur_tab["modified"] = True
                        elif sidebar.selected_item and cur_tab["map"].active_layer_name == "spawn":
                            cur_tab["map"].set_tile(map_x, map_y, sidebar.selected_item)
                            cur_tab["modified"] = True

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 3: dragging_cam = False
                    elif event.button == 1 and cur_tab["is_selecting"]:
                        cur_tab["sel_start"] = None

                if event.type == pygame.MOUSEMOTION:
                    if dragging_cam:
                        cur_tab["cam_x"] += event.pos[0] - drag_start[0]
                        cur_tab["cam_y"] += event.pos[1] - drag_start[1]
                        drag_start = event.pos
                    elif cur_tab["is_selecting"] and cur_tab["sel_start"] and pygame.mouse.get_pressed()[0]:
                        if map_view_rect.collidepoint(event.pos):
                            map_x = int(((event.pos[0] - cur_tab["cam_x"]) / z_scale) // TILE_SIZE)
                            map_y = int(((event.pos[1] - cur_tab["cam_y"]) / z_scale) // TILE_SIZE)
                            x1, y1 = cur_tab["sel_start"]
                            cur_tab["sel_rect"] = pygame.Rect(min(x1, map_x), min(y1, map_y), abs(map_x - x1) + 1, abs(map_y - y1) + 1)
                    elif not cur_tab["is_selecting"] and pygame.mouse.get_pressed()[0] and map_view_rect.collidepoint(event.pos):
                        map_x = int(((event.pos[0] - cur_tab["cam_x"]) / z_scale) // TILE_SIZE)
                        map_y = int(((event.pos[1] - cur_tab["cam_y"]) / z_scale) // TILE_SIZE)
                        if tile_to_place == "eraser":
                            cur_tab["map"].set_tile(map_x, map_y, None)
                            cur_tab["modified"] = True
                        elif sidebar.selected_tile:
                            cur_tab["map"].set_tile(map_x, map_y, sidebar.selected_tile)
                            cur_tab["modified"] = True
                        elif sidebar.selected_item and cur_tab["map"].active_layer_name == "spawn":
                            cur_tab["map"].set_tile(map_x, map_y, sidebar.selected_item)
                            cur_tab["modified"] = True

        screen.fill(UITheme.BG)
        
        if editor_mode == "NPC Dialog": dialog_editor.draw(screen)
        elif editor_mode == "Crafts": craft_editor.draw(screen)
        elif editor_mode == "Entities": entity_editor.draw(screen)
        elif editor_mode == "Code": code_editor.draw(screen)
        elif editor_mode == "Art": sprite_editor.draw(screen)
        else:
            surface_clip = screen.get_clip()
            screen.set_clip(map_view_rect)
            if cur_tab:
                z_scale = ZOOM_LEVELS[cur_tab["zoom_idx"]]
                cur_tab["map"].render(screen, all_render_tiles, FONT, (cur_tab["cam_x"], cur_tab["cam_y"]), z_scale)

                scaled_ts = int(TILE_SIZE * z_scale)
                for gx in range(cur_tab["map"].width + 1):
                    lx = cur_tab["cam_x"] + gx * scaled_ts
                    pygame.draw.line(screen, UITheme.BORDER, (lx, max(map_view_rect.top, cur_tab["cam_y"])), (lx, min(map_view_rect.bottom, cur_tab["cam_y"] + cur_tab["map"].height * scaled_ts)))
                for gy in range(cur_tab["map"].height + 1):
                    ly = cur_tab["cam_y"] + gy * scaled_ts
                    pygame.draw.line(screen, UITheme.BORDER, (max(map_view_rect.left, cur_tab["cam_x"]), ly), (min(map_view_rect.right, cur_tab["cam_x"] + cur_tab["map"].width * scaled_ts), ly))

                if cur_tab["sel_rect"]:
                    sx = cur_tab["sel_rect"].x * TILE_SIZE * z_scale + cur_tab["cam_x"]
                    sy = cur_tab["sel_rect"].y * TILE_SIZE * z_scale + cur_tab["cam_y"]
                    pygame.draw.rect(screen, UITheme.WARNING, (sx, sy, cur_tab["sel_rect"].width * TILE_SIZE * z_scale, cur_tab["sel_rect"].height * TILE_SIZE * z_scale), 2)
            screen.set_clip(surface_clip)

            if cur_tab:
                z_scale = ZOOM_LEVELS[cur_tab["zoom_idx"]]
                scaled_ts = int(TILE_SIZE * z_scale)
                step = 1 if scaled_ts >= 20 else (2 if scaled_ts >= 10 else 5)

                screen.set_clip(ruler_top_rect)
                pygame.draw.rect(screen, UITheme.PANEL_BG, ruler_top_rect)
                pygame.draw.line(screen, UITheme.BORDER, (ruler_top_rect.left, ruler_top_rect.bottom - 1), (ruler_top_rect.right, ruler_top_rect.bottom - 1))
                for col in range(cur_tab["map"].width):
                    col_x = cur_tab["cam_x"] + col * scaled_ts
                    if col_x + scaled_ts >= ruler_top_rect.left and col_x <= ruler_top_rect.right:
                        pygame.draw.line(screen, UITheme.BORDER, (col_x, ruler_top_rect.bottom - 5), (col_x, ruler_top_rect.bottom - 1))
                        if col % step == 0:
                            num_surf = RULER_FONT.render(str(col), True, UITheme.TEXT_DIM)
                            screen.blit(num_surf, (col_x + (scaled_ts - num_surf.get_width()) // 2, ruler_top_rect.centery - num_surf.get_height() // 2))
                end_x = cur_tab["cam_x"] + cur_tab["map"].width * scaled_ts
                if ruler_top_rect.left <= end_x <= ruler_top_rect.right:
                    pygame.draw.line(screen, UITheme.BORDER, (end_x, ruler_top_rect.bottom - 8), (end_x, ruler_top_rect.bottom - 1))
                screen.set_clip(surface_clip)

                screen.set_clip(ruler_left_rect)
                pygame.draw.rect(screen, UITheme.PANEL_BG, ruler_left_rect)
                pygame.draw.line(screen, UITheme.BORDER, (ruler_left_rect.right - 1, ruler_left_rect.top), (ruler_left_rect.right - 1, ruler_left_rect.bottom))
                for row in range(cur_tab["map"].height):
                    row_y = cur_tab["cam_y"] + row * scaled_ts
                    if row_y + scaled_ts >= ruler_left_rect.top and row_y <= ruler_left_rect.bottom:
                        pygame.draw.line(screen, UITheme.BORDER, (ruler_left_rect.right - 5, row_y), (ruler_left_rect.right - 1, row_y))
                        if row % step == 0:
                            num_surf = RULER_FONT.render(str(row), True, UITheme.TEXT_DIM)
                            screen.blit(num_surf, (ruler_left_rect.centerx - num_surf.get_width() // 2, row_y + (scaled_ts - num_surf.get_height()) // 2))
                end_y = cur_tab["cam_y"] + cur_tab["map"].height * scaled_ts
                if ruler_left_rect.top <= end_y <= ruler_left_rect.bottom:
                    pygame.draw.line(screen, UITheme.BORDER, (ruler_left_rect.right - 8, end_y), (ruler_left_rect.right - 1, end_y))
                screen.set_clip(surface_clip)

                pygame.draw.rect(screen, UITheme.PANEL_BG, ruler_corner_rect)
                pygame.draw.rect(screen, UITheme.BORDER, ruler_corner_rect, 1)
                lbl_xy = RULER_FONT.render("XY", True, UITheme.TEXT_DIM)
                screen.blit(lbl_xy, (ruler_corner_rect.centerx - lbl_xy.get_width() // 2, ruler_corner_rect.centery - lbl_xy.get_height() // 2))

            tab_bar_rect = pygame.Rect(FILE_TREE_WIDTH, TAB_BAR_HEIGHT + TOOLBAR_HEIGHT, current_screen_width - FILE_TREE_WIDTH - SIDEBAR_WIDTH, b_tab_bar_h)
            pygame.draw.rect(screen, UITheme.PANEL_BG, tab_bar_rect)
            pygame.draw.line(screen, UITheme.BORDER, (tab_bar_rect.left, tab_bar_rect.bottom - 1), (tab_bar_rect.right, tab_bar_rect.bottom - 1))

            screen.set_clip(tab_bar_rect)
            mouse_pos = pygame.mouse.get_pos()
            cur_tx = FILE_TREE_WIDTH - b_tab_scroll_x

            for i, t in enumerate(building_tabs):
                is_active = (i == active_b_idx)
                d_name = f"*{t['name']}" if t["modified"] else t["name"]
                tw = max(90, FONT.size(d_name)[0] + 44)
                t_box = pygame.Rect(cur_tx, tab_bar_rect.y, tw, b_tab_bar_h)
                c_box = pygame.Rect(t_box.right - 20, t_box.y + 9, 16, 16)
                
                if t["modified"]:
                    col, bcol, tcol = (55, 48, 15) if is_active else (38, 35, 18), UITheme.WARNING, UITheme.WARNING
                else:
                    col, bcol, tcol = (UITheme.BG if is_active else UITheme.PANEL_BG), UITheme.BORDER, (UITheme.TEXT if is_active else UITheme.TEXT_DIM)
                
                pygame.draw.rect(screen, col, t_box)
                pygame.draw.rect(screen, bcol, t_box, 1)
                if is_active:
                    pygame.draw.rect(screen, UITheme.WARNING if t["modified"] else UITheme.ACCENT, (t_box.x, t_box.y, t_box.width, 3))
                
                txt = FONT.render(d_name, True, tcol)
                screen.blit(txt, (t_box.x + 8, t_box.centery - txt.get_height()//2))

                chov = c_box.collidepoint(mouse_pos)
                pygame.draw.rect(screen, UITheme.DANGER if chov else bcol, c_box, border_radius=3)
                screen.blit(FONT.render("x", True, UITheme.TEXT), (c_box.x + 4, c_box.y + 1))
                cur_tx += tw + 2
            screen.set_clip(surface_clip)

            building_file_tree.draw(screen, cur_tab["name"] if cur_tab else "", cur_tab["folder"] if cur_tab else "", cur_tab["map"].active_layer_name if cur_tab else "")
            sidebar.draw(screen)
            toolbar.draw(screen)

            if new_building_modal.active: new_building_modal.draw(screen)
            if rename_modal.active: rename_modal.draw(screen)

        menu_bar.draw(screen)
        mod_dropdown.draw(screen)
        if mod_dropdown.expanded:
            mod_dropdown.draw_list(screen)
        draw_tooltips(screen, FONT)
        pygame.display.flip()

if __name__ == "__main__":
    editor()