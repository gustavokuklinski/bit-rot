# core/ui/helpers/select_world.py

import os
import pygame
import random
from datetime import datetime
import xml.etree.ElementTree as ET

import core.data.config
from core.data.config import (
    GAME_WIDTH, GAME_HEIGHT, UI_SCALE, WHITE, GRAY, DARK_GRAY, BLACK,
    GRAY_60, GRAY_80, GREEN, RED, YELLOW, font_16, font_12, SPRITE_PATH,
    BASE_DIR, DATA_PATH, get_writable_dir
)
from core.data.localization import tr
from core.ui.helpers.trait_config_loader import load_config_data

_world_icons_cache = {}
_logo_cache = None

def _get_logo_image(width):
    global _logo_cache
    if _logo_cache is not None and _logo_cache.get_width() == width:
        return _logo_cache

    logo_path = os.path.join(BASE_DIR, "data.rot", "icons", "logo.png")
    if os.path.exists(logo_path):
        try:
            raw = pygame.image.load(logo_path).convert_alpha()
            scale_factor = width / raw.get_width()
            target_h = int(raw.get_height() * scale_factor)
            _logo_cache = pygame.transform.scale(raw, (width, target_h))
            return _logo_cache
        except Exception as e:
            print(f"[SelectWorld] Error loading logo: {e}")
    return None

def _get_mode_icon(filename_or_relpath, size=(48, 48)):
    if filename_or_relpath in _world_icons_cache:
        return _world_icons_cache[filename_or_relpath]

    full_path = os.path.join(SPRITE_PATH, filename_or_relpath)
    if not os.path.exists(full_path):
        full_path = os.path.join(core.data.config.BASE_DIR, filename_or_relpath.lstrip('/\\'))

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
    """Dynamically loads world build modes from XML files in world_builds/."""
    builds = []
    builds_dir = os.path.join(BASE_DIR, "data.rot", "lib", "data", "world_builds")
    
    if os.path.exists(builds_dir):
        for filename in os.listdir(builds_dir):
            if filename.endswith(".xml"):
                filepath = os.path.join(builds_dir, filename)
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    if root.tag == "build":
                        bid = root.get('id', 'unknown')
                        props = root.find('properties')
                        
                        name, subtitle, icon_path = "Unknown", "", "ui/infection.png"
                        accent, tooltips = (255, 255, 255), []
                        
                        if props is not None:
                            n_node = props.find('name')
                            if n_node is not None: name = n_node.get('value', 'Unknown')
                            
                            s_node = props.find('subtitle')
                            if s_node is not None: subtitle = s_node.get('value', '')
                            
                            i_node = props.find('icon_path')
                            if i_node is not None: icon_path = i_node.get('value', 'ui/infection.png')
                            
                            c_node = props.find('accent')
                            if c_node is not None:
                                try:
                                    parts = c_node.get('value', '(255,255,255)').strip("() ").split(',')
                                    accent = tuple(int(p.strip()) for p in parts)
                                except: pass
                                
                            t_node = props.find('tooltips')
                            if t_node is not None:
                                tt_str = t_node.get('value', '[]')
                                if tt_str.startswith('[') and tt_str.endswith(']'):
                                    tooltips = [s.strip() for s in tt_str[1:-1].split(',')]
                                    
                        builds.append({
                            'id': bid,
                            'name': name,
                            'subtitle': subtitle,
                            'icon_path': icon_path,
                            'accent': accent,
                            'tooltip_lines': tooltips,
                            'filename': filename
                        })
                except Exception as e:
                    print(f"[SelectWorld] Error loading {filename}: {e}")
                    
    builds.sort(key=lambda x: x['name'])
    return builds

WORLD_MODES = load_world_builds()

def _load_world_build_config(filename):
    """Parses the <world> block from the chosen XML file."""
    path = os.path.join(BASE_DIR, "data.rot", "lib", "data", "world_builds", filename)
    if not os.path.exists(path): return {}
    try:
        tree = ET.parse(path)
        world_node = tree.getroot().find('world')
        data = {}
        if world_node is not None:
            for child in world_node:
                block_name = child.tag
                data[block_name] = {}
                for setting in child:
                    key = setting.tag
                    val = setting.get('value')
                    display_name = setting.get('name', key)
                    default_val = setting.get('default')
                    setting_dict = {'value': val, 'name': display_name}
                    if default_val is not None:
                        setting_dict['default'] = default_val
                    data[block_name][key] = setting_dict
        return data
    except Exception as e:
        print(f"Error parsing world data from {filename}: {e}")
        return {}

def _apply_build_and_proceed(game, state, mode_id, filename):
    """Loads world settings in memory, creates save folder with world.xml, and proceeds to Character Selection."""
    from datetime import datetime
    from core.data.config import get_writable_dir
    from core.ui.helpers.trait_config_loader import save_config_xml

    if filename:
        world_data = _load_world_build_config(filename)
    else:
        path = core.data.config.get_world_config_path('world')
        world_data = load_config_data(path)

    state['world_data'] = world_data
    state['chosen_mode'] = mode_id
    
    if not state.get('world_seed'):
        state['world_seed'] = "".join(str(random.randint(0, 9)) for _ in range(12))

    # Create the save folder immediately with world.xml inside
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_name = f"save_{mode_id}_{timestamp}"
    save_path = os.path.join(get_writable_dir(), "data.rot", "save", "game", save_name)
    os.makedirs(save_path, exist_ok=True)

    world_xml_path = os.path.join(save_path, "world.xml")
    save_config_xml(world_data, world_xml_path)

    game.current_save_folder_name = save_name
    state['save_folder_name'] = save_name
    state['world_xml_path'] = world_xml_path

    if not hasattr(game, 'world_setup_state'):
        game.world_setup_state = {}

    game.world_setup_state['world_data'] = world_data
    game.world_setup_state['chosen_mode'] = mode_id
    game.world_setup_state['world_seed'] = state['world_seed']
    game.world_setup_state['save_folder_name'] = save_name
    game.world_setup_state['world_xml_path'] = world_xml_path
    game.world_setup_state['world_unsaved'] = False

    state['current_tab'] = 'SelectCharacter'


def draw_select_world_screen(game, state, mouse_pos):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_x = GAME_WIDTH // 2
    logo_w = S(240)
    logo_img = _get_logo_image(logo_w)
    
    top_cursor_y = S(42)
    if logo_img:
        logo_rect = logo_img.get_rect(center=(center_x, top_cursor_y + (logo_img.get_height() // 2)))
        game.game_screen.blit(logo_img, logo_rect)
        top_cursor_y = logo_rect.bottom + S(10)
    else:
        top_cursor_y = S(45)

    title_text = font_16.render(tr('ui', "SELECT GAME WORLD"), False, WHITE)
    title_rect = title_text.get_rect(center=(center_x, top_cursor_y + S(40)))
    game.game_screen.blit(title_text, title_rect)

    sub_text = font_12.render(tr('ui', "Choose your game mode to begin your journey"), False, (160, 160, 160))
    sub_rect = sub_text.get_rect(center=(center_x, title_rect.bottom + S(12)))
    game.game_screen.blit(sub_text, sub_rect)

    card_w = S(270)
    card_h = S(345)
    spacing = S(25)
    
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

        btn_h = S(38)
        btn_rect = pygame.Rect(card_rect.left + S(20), card_rect.bottom - btn_h - S(14), card_rect.width - S(40), btn_h)
        
        btn_hovered = btn_rect.collidepoint(mouse_pos)
        btn_bg = mode['accent'] if btn_hovered else (55, 55, 55)
        btn_text_col = (10, 10, 10) if btn_hovered else WHITE
        pygame.draw.rect(game.game_screen, btn_bg, btn_rect, border_radius=S(5))

        btn_txt = font_12.render(tr('ui', "Select Mode"), False, btn_text_col)
        game.game_screen.blit(btn_txt, btn_txt.get_rect(center=btn_rect.center))
        clickable_rects['cards'].append((mode, btn_rect))

    # --- 4. BOTTOM BAR: BACK & SANDBOX ---
    btn_w = S(200)
    btn_h = S(42)
    gap = S(20)
    total_bottom_w = (btn_w * 2) + gap
    start_bottom_x = center_x - (total_bottom_w // 2)
    bottom_y = card_y + card_h + S(60)

    back_rect = pygame.Rect(start_bottom_x, bottom_y, btn_w, btn_h)
    is_back_hover = back_rect.collidepoint(mouse_pos)
    back_bg = (80, 80, 80) if is_back_hover else (60, 60, 60)
    pygame.draw.rect(game.game_screen, back_bg, back_rect, border_radius=S(6))
    back_txt = font_16.render(tr('ui', "Back"), False, WHITE)
    game.game_screen.blit(back_txt, back_txt.get_rect(center=back_rect.center))
    clickable_rects['back_button'] = back_rect

    sandbox_rect = pygame.Rect(back_rect.right + gap, bottom_y, btn_w, btn_h)
    is_sandbox_hover = sandbox_rect.collidepoint(mouse_pos)
    sandbox_bg = (255, 200, 50) if is_sandbox_hover else (200, 150, 30)
    pygame.draw.rect(game.game_screen, sandbox_bg, sandbox_rect, border_radius=S(6))
    sandbox_txt = font_16.render(tr('ui', "Sandbox Mode"), False, WHITE if is_sandbox_hover else BLACK)
    game.game_screen.blit(sandbox_txt, sandbox_txt.get_rect(center=sandbox_rect.center))
    clickable_rects['sandbox_button'] = sandbox_rect

    return clickable_rects

def handle_select_world_events(game, state, event, mouse_pos, clickable_rects):
    if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
        if clickable_rects.get('back_button') and clickable_rects['back_button'].collidepoint(mouse_pos):
            game.game_state = 'MENU'
            return
            
        if clickable_rects.get('sandbox_button') and clickable_rects['sandbox_button'].collidepoint(mouse_pos):
            state['chosen_mode'] = 'sandbox'
            state['current_tab'] = 'World'
            path = core.data.config.get_world_config_path('sandbox')
            world_data = load_config_data(path)
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