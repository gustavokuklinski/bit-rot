# core/ui/helpers/select_world.py

import os
import json
import pygame
import random
from datetime import datetime
from types import SimpleNamespace
from core.systems.save_manager import delete_pending_world_save

import core.data.config
from core.data.config import (
    GAME_WIDTH, GAME_HEIGHT, UI_SCALE, WHITE, GRAY, DARK_GRAY, BLACK,
    GRAY_60, GRAY_80, GREEN, RED, YELLOW, font_16, font_12, SPRITE_PATH,
    BASE_DIR, DATA_PATH, get_writable_dir
)
from core.data.localization import tr
from core.ui.helpers.trait_config_loader import load_config_data
from core.ui.tooltip import draw_tooltip
from core.systems.mod_manager import mod_manager

_world_icons_cache = {}

def _get_mode_icon(filename_or_relpath, size=(48, 48)):

    if filename_or_relpath in _world_icons_cache:
        return _world_icons_cache[filename_or_relpath]

    full_path = os.path.join(SPRITE_PATH, filename_or_relpath)
    if not os.path.exists(full_path):
        full_path = os.path.join(core.data.config.BASE_DIR, filename_or_relpath.lstrip('/\\'))

    full_path = mod_manager.get_override_path(full_path)

    try:
        if os.path.exists(full_path):
            img = pygame.image.load(full_path).convert_alpha()
            scaled = pygame.transform.scale(img, size)
            _world_icons_cache[filename_or_relpath] = scaled
            return scaled
    except Exception as e:
        pass

    fallback = pygame.Surface(size, pygame.SRCALPHA)
    fallback.fill((80, 80, 80))
    _world_icons_cache[filename_or_relpath] = fallback
    return fallback

def load_world_builds():
    """Dynamically loads world build modes from JSON files in world_builds/."""
    
    builds = []
    builds_dir = os.path.join(BASE_DIR, "data.rot", "lib", "data", "world_builds")
    
    if os.path.exists(builds_dir):
        for root_dir, _, full_paths in mod_manager.vfs_walk(builds_dir):
            for filepath in full_paths:
                if filepath.endswith(".json"):
                    filename = os.path.basename(filepath)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    raw_builds = data.get("builds", {})
                    # Support single build per file or multiple builds
                    if not raw_builds and "properties" in data:
                        raw_builds = {os.path.splitext(filename)[0]: data}

                    for bid, b_info in raw_builds.items():
                        props = b_info.get("properties", {})
                        name = props.get("name", bid.capitalize())
                        subtitle = props.get("subtitle", "")
                        icon_path = props.get("icon_path", "ui/infection.png")
                        
                        raw_accent = props.get("accent", [255, 255, 255])
                        if isinstance(raw_accent, (list, tuple)) and len(raw_accent) >= 3:
                            accent = tuple(int(c) for c in raw_accent[:3])
                        else:
                            accent = (255, 255, 255)
                            
                        tooltips = props.get("tooltips", [])
                        if not isinstance(tooltips, list):
                            tooltips = [str(tooltips)]

                        builds.append({
                            'id': bid,
                            'name': name,
                            'subtitle': subtitle,
                            'icon_path': icon_path,
                            'accent': accent,
                            'tooltip_lines': tooltips,
                            'filename': filename,
                            'world_data': b_info.get("world", {})
                        })
                except Exception as e:
                    print(f"[SelectWorld] Error loading {filename}: {e}")
                    
    builds.sort(key=lambda x: x['name'])
    return builds

WORLD_MODES = load_world_builds()

def _load_world_build_config(filename, mode_id=None):
    """Parses the 'world' block from the chosen JSON file."""
    if filename.endswith(".xml"):
        filename = os.path.splitext(filename)[0] + ".json"

    path = os.path.join(BASE_DIR, "data.rot", "lib", "data", "world_builds", filename)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        builds = data.get("builds", {})
        if mode_id and mode_id in builds:
            return builds[mode_id].get("world", {})
        if builds:
            first_build = next(iter(builds.values()))
            return first_build.get("world", {})
        return data.get("world", data)
    except Exception as e:
        print(f"Error parsing world data from {filename}: {e}")
        return {}

def _apply_build_and_proceed(game, state, mode_id, filename):
    """Loads world settings from JSON, creates save folder with world.json, and proceeds to Character Selection."""
    from datetime import datetime
    from core.data.config import get_writable_dir
    from core.ui.helpers.trait_config_loader import save_config_json

    if filename:
        world_data = _load_world_build_config(filename, mode_id=mode_id)
    else:
        path = core.data.config.get_world_config_path('world')
        world_data = load_config_data(path)

    # Apply checkbox states directly to world configuration
    if 'game' not in world_data:
        world_data['game'] = {}

    world_data['game']['all_visible'] = {
        'value': 'true' if state.get('all_visible', False) else 'false',
        'name': 'All containers are opened',
        'default': 'false'
    }
    
    world_data['game']['infinite_liquid'] = {
        'value': 'true' if state.get('infinite_liquid', True) else 'false',
        'name': 'Liquids are infinite',
        'default': 'true'
    }

    world_data['game']['permadeath'] = {
        'value': 'true' if state.get('permadeath', False) else 'false',
        'name': 'Delete save when die',
        'default': 'false'
    }

    state['world_data'] = world_data
    state['chosen_mode'] = mode_id
    
    if not state.get('world_seed'):
        state['world_seed'] = "".join(str(random.randint(0, 9)) for _ in range(12))

    # Create the save folder with world.json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_name = f"save_{mode_id}_{timestamp}"
    save_path = os.path.join(get_writable_dir(), "data.rot", "save", "game", save_name)
    os.makedirs(save_path, exist_ok=True)

    world_json_path = os.path.join(save_path, "world.json")
    save_config_json(world_data, world_json_path)

    game.current_save_folder_name = save_name
    state['save_folder_name'] = save_name
    state['world_json_path'] = world_json_path

    if not hasattr(game, 'world_setup_state'):
        game.world_setup_state = {}

    game.world_setup_state['world_data'] = world_data
    game.world_setup_state['chosen_mode'] = mode_id
    game.world_setup_state['world_seed'] = state['world_seed']
    game.world_setup_state['save_folder_name'] = save_name
    game.world_setup_state['world_xml_path'] = world_json_path
    game.world_setup_state['world_unsaved'] = False

    state['current_tab'] = 'SelectCharacter'


def draw_select_world_screen(game, state, mouse_pos):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_x = GAME_WIDTH // 2

    # Dimensions
    title_text = font_16.render(tr('ui', "SELECT GAME WORLD"), False, WHITE)
    sub_text = font_12.render(tr('ui', "Choose your game mode to begin your journey"), False, (160, 160, 160))

    card_w = S(270)
    card_h = S(345)
    spacing = S(25)

    box_size = S(18)
    cb_gap = S(30)

    btn_w = S(200)
    btn_h = S(42)
    gap = S(20)

    # --- VERTICAL CENTERING CALCULATION ---
    total_screen_h = (
        title_text.get_height()
        + S(10)
        + sub_text.get_height()
        + S(16)
        + card_h
        + S(16)
        + box_size
        + S(16)
        + btn_h
    )
    start_top_y = max(S(20), (GAME_HEIGHT - total_screen_h) // 2)

    # Title & Subtitle
    title_rect = title_text.get_rect(center=(center_x, start_top_y + (title_text.get_height() // 2)))
    game.game_screen.blit(title_text, title_rect)

    sub_rect = sub_text.get_rect(center=(center_x, title_rect.bottom + S(10) + (sub_text.get_height() // 2)))
    game.game_screen.blit(sub_text, sub_rect)

    # Cards Layout
    modes_count = len(WORLD_MODES)
    total_w = (card_w * modes_count) + (spacing * max(0, modes_count - 1))
    start_x = center_x - (total_w // 2)
    card_y = sub_rect.bottom + S(16)

    clickable_rects = {'cards': [], 'back_button': None, 'sandbox_button': None}

    for i, mode in enumerate(WORLD_MODES):
        cx = start_x + i * (card_w + spacing)
        card_rect = pygame.Rect(cx, card_y, card_w, card_h)
        is_hovered = card_rect.collidepoint(mouse_pos)

        bg_col = (45, 45, 45) if is_hovered else (32, 32, 32)
        border_col = mode['accent'] if is_hovered else GRAY_60
        border_width = 2 if is_hovered else 1

        pygame.draw.rect(game.game_screen, bg_col, card_rect, border_radius=S(8))
        pygame.draw.rect(game.game_screen, border_col, card_rect, width=border_width, border_radius=S(8))

        icon_box_size = S(64)
        icon_box = pygame.Rect(0, 0, icon_box_size, icon_box_size)
        icon_box.center = (card_rect.centerx, card_rect.top + S(55))
        pygame.draw.rect(game.game_screen, (22, 22, 22), icon_box, border_radius=S(6))
        pygame.draw.rect(game.game_screen, border_col, icon_box, width=1, border_radius=S(6))

        icon_surf = _get_mode_icon(mode['icon_path'], size=(S(44), S(44)))
        if icon_surf:
            game.game_screen.blit(icon_surf, icon_surf.get_rect(center=icon_box.center))

        name_surf = font_16.render(tr('ui', mode['name']), False, mode['accent'] if is_hovered else WHITE)
        game.game_screen.blit(name_surf, name_surf.get_rect(center=(card_rect.centerx, card_rect.top + S(110))))

        sub_surf = font_12.render(tr('ui', mode['subtitle']), False, (180, 180, 180))
        game.game_screen.blit(sub_surf, sub_surf.get_rect(center=(card_rect.centerx, card_rect.top + S(134))))

        pygame.draw.line(game.game_screen, (55, 55, 55), (card_rect.left + S(20), card_rect.top + S(155)), (card_rect.right - S(20), card_rect.top + S(155)), 1)

        line_cursor_y = card_rect.top + S(172)
        for line_str in mode['tooltip_lines']:
            b_surf = font_12.render(f"- {tr('ui', line_str)}", False, (220, 220, 220))
            game.game_screen.blit(b_surf, (card_rect.left + S(25), line_cursor_y))
            line_cursor_y += S(22)

        card_btn_h = S(38)
        card_btn_rect = pygame.Rect(card_rect.left + S(20), card_rect.bottom - card_btn_h - S(14), card_rect.width - S(40), card_btn_h)
        
        btn_hovered = card_btn_rect.collidepoint(mouse_pos)
        btn_bg = mode['accent'] if btn_hovered else (55, 55, 55)
        btn_text_col = (10, 10, 10) if btn_hovered else WHITE
        pygame.draw.rect(game.game_screen, btn_bg, card_btn_rect, border_radius=S(5))

        btn_txt = font_12.render(tr('ui', "Select Mode"), False, btn_text_col)
        game.game_screen.blit(btn_txt, btn_txt.get_rect(center=card_btn_rect.center))
        clickable_rects['cards'].append((mode, card_btn_rect))

    # --- CHECKBOXES: ALL VISIBLE, PERMADEATH & INFINITE LIQUID ---
    if 'all_visible' not in state:
        state['all_visible'] = True
    if 'infinite_liquid' not in state:
        state['infinite_liquid'] = True
    if 'permadeath' not in state:
        state['permadeath'] = False

    cb_y = card_y + card_h + S(16)

    txt_all_vis = tr('ui', "All visible")
    txt_inf_liq = tr('ui', "Infinite liquid")
    txt_perma = tr('ui', "Permadeath")

    w1 = box_size + S(8) + font_12.size(txt_all_vis)[0]
    w2 = box_size + S(8) + font_12.size(txt_inf_liq)[0]
    w3 = box_size + S(8) + font_12.size(txt_perma)[0]
    total_cb_w = w1 + cb_gap + w2 + cb_gap + w3 + cb_gap
    cb_start_x = center_x - (total_cb_w // 2)

    hovered_cb_tooltip = None

    # Checkbox 1: All visible
    cb1_click_rect = pygame.Rect(cb_start_x, cb_y, w1, box_size)
    cb1_box_rect = pygame.Rect(cb_start_x, cb_y, box_size, box_size)
    is_hover_cb1 = cb1_click_rect.collidepoint(mouse_pos)

    pygame.draw.rect(game.game_screen, (45, 45, 45), cb1_box_rect, border_radius=S(3))
    pygame.draw.rect(game.game_screen, WHITE if is_hover_cb1 else GRAY, cb1_box_rect, 1, border_radius=S(3))
    if state.get('all_visible', False):
        inner_rect1 = cb1_box_rect.inflate(-S(6), -S(6))
        pygame.draw.rect(game.game_screen, GREEN, inner_rect1, border_radius=S(2))

    lbl1 = font_12.render(txt_all_vis, False, YELLOW if is_hover_cb1 else WHITE)
    game.game_screen.blit(lbl1, (cb1_box_rect.right + S(8), cb1_box_rect.centery - lbl1.get_height() // 2))
    clickable_rects['checkbox_all_visible'] = cb1_click_rect
    if is_hover_cb1:
        hovered_cb_tooltip = (txt_all_vis, tr('ui', "All containers are opened"))

    # Checkbox 2: Infinite liquid
    cb2_x = cb_start_x + w1 + cb_gap
    cb2_click_rect = pygame.Rect(cb2_x, cb_y, w2, box_size)
    cb2_box_rect = pygame.Rect(cb2_x, cb_y, box_size, box_size)
    is_hover_cb2 = cb2_click_rect.collidepoint(mouse_pos)

    pygame.draw.rect(game.game_screen, (45, 45, 45), cb2_box_rect, border_radius=S(3))
    pygame.draw.rect(game.game_screen, WHITE if is_hover_cb2 else GRAY, cb2_box_rect, 1, border_radius=S(3))
    if state.get('infinite_liquid', True):
        inner_rect2 = cb2_box_rect.inflate(-S(6), -S(6))
        pygame.draw.rect(game.game_screen, GREEN, inner_rect2, border_radius=S(2))

    lbl2 = font_12.render(txt_inf_liq, False, YELLOW if is_hover_cb2 else WHITE)
    game.game_screen.blit(lbl2, (cb2_box_rect.right + S(8), cb2_box_rect.centery - lbl2.get_height() // 2))
    clickable_rects['checkbox_infinite_liquid'] = cb2_click_rect
    if is_hover_cb2:
        hovered_cb_tooltip = (txt_inf_liq, tr('ui', "Liquids are infinite"))

    # Checkbox 3: Permadeath
    cb3_x = cb2_x + w2 + cb_gap
    cb3_click_rect = pygame.Rect(cb3_x, cb_y, w3, box_size)
    cb3_box_rect = pygame.Rect(cb3_x, cb_y, box_size, box_size)
    is_hover_cb3 = cb3_click_rect.collidepoint(mouse_pos)

    pygame.draw.rect(game.game_screen, (45, 45, 45), cb3_box_rect, border_radius=S(3))
    pygame.draw.rect(game.game_screen, WHITE if is_hover_cb3 else GRAY, cb3_box_rect, 1, border_radius=S(3))
    if state.get('permadeath', False):
        inner_rect3 = cb3_box_rect.inflate(-S(6), -S(6))
        pygame.draw.rect(game.game_screen, GREEN, inner_rect3, border_radius=S(2))

    lbl3 = font_12.render(txt_perma, False, YELLOW if is_hover_cb3 else WHITE)
    game.game_screen.blit(lbl3, (cb3_box_rect.right + S(8), cb3_box_rect.centery - lbl3.get_height() // 2))
    clickable_rects['checkbox_permadeath'] = cb3_click_rect
    if is_hover_cb3:
        hovered_cb_tooltip = (txt_perma, tr('ui', "Delete save when die"))



    # --- 4. BOTTOM BAR: BACK & SANDBOX ---
    btn_w = S(200)
    btn_h = S(42)
    gap = S(20)
    total_bottom_w = (btn_w * 2) + gap
    start_bottom_x = center_x - (total_bottom_w // 2)
    bottom_y = cb_y + box_size + S(16)

    back_rect = pygame.Rect(start_bottom_x, bottom_y, btn_w, btn_h)
    is_back_hover = back_rect.collidepoint(mouse_pos)
    back_bg = (80, 80, 80) if is_back_hover else (60, 60, 60)
    pygame.draw.rect(game.game_screen, back_bg, back_rect, border_radius=S(6))
    back_txt = font_16.render(tr('ui', "Back"), False, WHITE)
    game.game_screen.blit(back_txt, back_txt.get_rect(center=back_rect.center))
    clickable_rects['back_button'] = back_rect

    sandbox_rect = pygame.Rect(back_rect.right + gap, bottom_y, btn_w, btn_h)
    is_sandbox_hover = sandbox_rect.collidepoint(mouse_pos)
    sandbox_bg = (80, 80, 80) if is_sandbox_hover else (60, 60, 60)
    pygame.draw.rect(game.game_screen, sandbox_bg, sandbox_rect, border_radius=S(6))
    sandbox_txt = font_16.render(tr('ui', "Sandbox"), False, WHITE)
    game.game_screen.blit(sandbox_txt, sandbox_txt.get_rect(center=sandbox_rect.center))
    clickable_rects['sandbox_button'] = sandbox_rect

    all_world_buttons = [back_rect, sandbox_rect, cb1_click_rect, cb2_click_rect, cb3_click_rect]
    for _, b_rect in clickable_rects.get('cards', []):
        all_world_buttons.append(b_rect)

    all_world_buttons = [b for b in all_world_buttons if b is not None]
    hovered_idx = None
    for idx, b_rect in enumerate(all_world_buttons):
        if b_rect.collidepoint(mouse_pos):
            hovered_idx = idx
            break

    if hovered_idx is not None and hovered_idx != getattr(game, '_world_select_hovered_btn_idx', None):
        if hasattr(game, 'sound_manager'):
            game.sound_manager.play_ui_hover()
    game._world_select_hovered_btn_idx = hovered_idx
    # -----------------------------------

    if hovered_cb_tooltip:
        t_proxy = SimpleNamespace(
            name=hovered_cb_tooltip[0],
            tooltip_lines=[hovered_cb_tooltip[1]],
            tooltip_text=None,
            item_type=None,
            durability=None,
            defence=None,
            load=None,
            capacity=None,
            min_damage=None,
            max_damage=None,
            ammo_type=None
        )
        draw_tooltip(game.game_screen, t_proxy, (mouse_pos[0] + S(2), mouse_pos[1] + S(2)))

    return clickable_rects

def handle_select_world_events(game, state, event, mouse_pos, clickable_rects):
    if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
        if clickable_rects.get('checkbox_all_visible') and clickable_rects['checkbox_all_visible'].collidepoint(mouse_pos):
            state['all_visible'] = not state.get('all_visible', False)
            return

        if clickable_rects.get('checkbox_infinite_liquid') and clickable_rects['checkbox_infinite_liquid'].collidepoint(mouse_pos):
            state['infinite_liquid'] = not state.get('infinite_liquid', True)
            return
        
        if clickable_rects.get('checkbox_permadeath') and clickable_rects['checkbox_permadeath'].collidepoint(mouse_pos):
            state['permadeath'] = not state.get('permadeath', False)
            return
        

        if clickable_rects.get('back_button') and clickable_rects['back_button'].collidepoint(mouse_pos):
            delete_pending_world_save(game, state)
            game.game_state = 'MENU'
            return
            
        if clickable_rects.get('sandbox_button') and clickable_rects['sandbox_button'].collidepoint(mouse_pos):
            state['chosen_mode'] = 'sandbox'
            state['current_tab'] = 'World'
            path = core.data.config.get_world_config_path('sandbox')
            world_data = load_config_data(path)

            if 'game' not in world_data:
                world_data['game'] = {}
            world_data['game']['all_visible'] = {
                'value': 'true' if state.get('all_visible', False) else 'false',
                'name': 'All containers are opened',
                'default': 'false'
            }
            
            world_data['game']['infinite_liquid'] = {
                'value': 'true' if state.get('infinite_liquid', True) else 'false',
                'name': 'Liquids are infinite',
                'default': 'false'
            }
            world_data['game']['permadeath'] = {
                'value': 'true' if state.get('permadeath', False) else 'false',
                'name': 'Delete save when die',
                'default': 'false'
            }

            state['world_data'] = world_data

            if not hasattr(game, 'world_setup_state'):
                game.world_setup_state = {}
            game.world_setup_state['world_data'] = world_data
            game.world_setup_state['chosen_mode'] = 'sandbox'
            return

        for mode, rect in clickable_rects.get('cards', []):
            if rect.collidepoint(mouse_pos):
                _apply_build_and_proceed(game, state, mode['id'], mode.get('filename'))
                return