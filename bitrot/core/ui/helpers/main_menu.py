import pygame
import os
import xml.etree.ElementTree as ET
import core.data.config
from core.data.config import *
from datetime import datetime
from core.data.localization import tr

_logo_img = None
_language_cache = None
_help_img_menu = None
_controls_img_menu = None  # NEW: global for the controls icon

def get_available_languages():
    global _language_cache
    if _language_cache is not None:
        return _language_cache
    
    _language_cache = []
    xml_path = os.path.join(BASE_DIR, 'data.rot', 'lib', 'lang', 'languages.xml')
    
    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for lang_node in root.findall('language'):
                name = lang_node.get('name')
                props = lang_node.find('properties')
                if props is not None:
                    sprite_node = props.find('sprite')
                    wip_node = props.find('wip')
                    
                    sprite_file = sprite_node.get('file') if sprite_node is not None else None
                    wip_val = wip_node.get('value').lower() == 'true' if wip_node is not None else False
                    
                    if sprite_file:
                        full_path = os.path.join(BASE_DIR, 'data.rot', 'lib', 'sprites', 'ui', sprite_file)
                        _language_cache.append({'name': name, 'sprite_path': full_path, 'wip': wip_val, 'img': None})
        except Exception as e:
            print(f"Error parsing languages.xml: {e}")
    
    if not _language_cache:
        _language_cache = [
            {'name': 'en_US', 'sprite_path': os.path.join(BASE_DIR, 'data.rot', 'lib', 'sprites', 'ui', 'lang_en.png'), 'wip': False, 'img': None},
            {'name': 'pt_BR', 'sprite_path': os.path.join(BASE_DIR, 'data.rot', 'lib', 'sprites', 'ui', 'lang_pt_BR.png'), 'wip': True, 'img': None}
        ]
            
    for lang in _language_cache:
        try:
            if os.path.exists(lang['sprite_path']):
                img = pygame.image.load(lang['sprite_path']).convert_alpha()
                lang['img'] = pygame.transform.scale(img, (int(32 * UI_SCALE), int(24 * UI_SCALE)))
        except Exception:
            pass
            
    return _language_cache

def draw_btn(surface, rect, text, mouse_pos, enabled=True):
    is_hovered = rect.collidepoint(mouse_pos)
    
    if not enabled:
        bg_color = (40, 40, 40)
        text_color = (100, 100, 100)
    else:
        bg_color = (80, 80, 80) if is_hovered else (60, 60, 60)
        text_color = WHITE

    pygame.draw.rect(surface, bg_color, rect, border_radius=6)

    txt_surf = font_16.render(text, False, text_color)
    txt_rect = txt_surf.get_rect(center=rect.center)
    surface.blit(txt_surf, txt_rect)

def draw_menu(screen, mouse_pos, has_save=False):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_offset_x = (GAME_WIDTH - S(1280)) // 2
    center_offset_y = (GAME_HEIGHT - S(720)) // 2

    global _logo_img, _help_img_menu, _controls_img_menu
    screen.fill(DARK_GRAY)

    try:
        if _logo_img is None:
            logo_path = os.path.join(BASE_DIR, 'data.rot', 'icons', 'logo.png')
            _logo_img = pygame.image.load(logo_path).convert_alpha()
            target_w = S(500)
            scale_factor = target_w / _logo_img.get_width()
            target_h = int(_logo_img.get_height() * scale_factor)
            _logo_img = pygame.transform.scale(_logo_img, (target_w, target_h))
    except Exception:
        _logo_img = None
        
    try:
        if _help_img_menu is None:
            help_path = os.path.join(BASE_DIR, 'data.rot', 'lib', 'sprites', 'ui', 'help.png')
            _help_img_menu = pygame.image.load(help_path).convert_alpha()
            _help_img_menu = pygame.transform.scale(_help_img_menu, (S(32), S(32)))
    except Exception as e:
        pass

    try:
        if _controls_img_menu is None:
            controls_path = os.path.join(BASE_DIR, 'data.rot', 'lib', 'sprites', 'ui', 'controls.png')
            _controls_img_menu = pygame.image.load(controls_path).convert_alpha()
            _controls_img_menu = pygame.transform.scale(_controls_img_menu, (S(32), S(32)))
    except Exception as e:
        pass

    center_x = GAME_WIDTH // 2

    if _logo_img:
        logo_rect = _logo_img.get_rect(center=(center_x, center_offset_y + S(216)))
        screen.blit(_logo_img, logo_rect)
    else:
        title_text = font_16.render("Bit Rot", False, RED)
        title_rect = title_text.get_rect(center=(center_x, center_offset_y + S(180)))
        screen.blit(title_text, title_rect)

    btn_width = S(400)
    btn_height = S(50)
    spacing = S(20)
    
    start_y = center_offset_y + S(396) 

    load_rect = pygame.Rect(center_x - btn_width // 2, start_y, btn_width, btn_height)
    draw_btn(screen, load_rect, tr('ui', "Load Game"), mouse_pos, enabled=has_save)

    start_rect = pygame.Rect(center_x - btn_width // 2, load_rect.bottom + spacing, btn_width, btn_height)
    draw_btn(screen, start_rect, tr('ui', "New Game"), mouse_pos)

    split_width = (btn_width - spacing) // 2
    settings_rect = pygame.Rect(center_x - btn_width // 2, start_rect.bottom + spacing, split_width, btn_height)
    quit_rect = pygame.Rect(settings_rect.right + spacing, start_rect.bottom + spacing, split_width, btn_height)

    draw_btn(screen, settings_rect, tr('ui', "Settings"), mouse_pos)
    draw_btn(screen, quit_rect, tr('ui', "Quit"), mouse_pos)

    current_year = datetime.now().year
    footer_str = f"Bit Rot - All Rights Reserved - 2025 - {current_year} | version: {GAME_VERSION}"
    footer_text = font_12.render(footer_str, False, (100, 100, 100))
    footer_rect = footer_text.get_rect(center=(center_x, center_offset_y + S(700)))
    screen.blit(footer_text, footer_rect)

    help_rect = None
    controls_rect = None

    # Draw Help Icon
    if _help_img_menu:
        help_bg_rect = pygame.Rect(0, 0, S(48), S(48))
        help_bg_rect.bottomleft = (center_offset_x + S(20), center_offset_y + S(700)) 
        
        is_hovered_help = help_bg_rect.collidepoint(mouse_pos)
        bg_color = (80, 80, 80) if is_hovered_help else (60, 60, 60)
        
        pygame.draw.rect(screen, bg_color, help_bg_rect, border_radius=6)
        pygame.draw.rect(screen, (40, 40, 40), help_bg_rect, width=1, border_radius=6)
        
        img_rect = _help_img_menu.get_rect(center=help_bg_rect.center)
        screen.blit(_help_img_menu, img_rect)
        
        help_rect = help_bg_rect 

    # Draw Controls Icon next to Help Icon
    if _controls_img_menu:
        controls_bg_rect = pygame.Rect(0, 0, S(48), S(48))
        if help_rect:
            controls_bg_rect.bottomleft = (help_rect.right + S(10), help_rect.bottom)
        else:
            controls_bg_rect.bottomleft = (center_offset_x + S(20), center_offset_y + S(700))
            
        is_hovered_controls = controls_bg_rect.collidepoint(mouse_pos)
        bg_color = (80, 80, 80) if is_hovered_controls else (60, 60, 60)
        
        pygame.draw.rect(screen, bg_color, controls_bg_rect, border_radius=6)
        pygame.draw.rect(screen, (40, 40, 40), controls_bg_rect, width=1, border_radius=6)
        
        img_rect = _controls_img_menu.get_rect(center=controls_bg_rect.center)
        screen.blit(_controls_img_menu, img_rect)
        
        controls_rect = controls_bg_rect

    langs = get_available_languages()
    flag_rects = []
    
    flag_x = center_offset_x + S(1260)
    flag_y = center_offset_y + S(20)
    hovered_wip = False
    
    for lang in reversed(langs):
        if lang['img']:
            bg_rect = pygame.Rect(0, 0, lang['img'].get_width() + S(16), lang['img'].get_height() + S(12))
            bg_rect.topright = (flag_x, flag_y)
            
            rect = lang['img'].get_rect(center=bg_rect.center)
            
            is_hovered = bg_rect.collidepoint(mouse_pos)
            is_selected = (lang['name'] == core.data.config.GAME_LANGUAGE)
            
            bg_color = (80, 80, 80) if is_hovered else (60, 60, 60)
            
            pygame.draw.rect(screen, bg_color, bg_rect, border_radius=6)
            
            if is_selected:
                pygame.draw.rect(screen, (150, 150, 150), bg_rect, width=2, border_radius=6)
            else:
                pygame.draw.rect(screen, (40, 40, 40), bg_rect, width=1, border_radius=6)
                
            screen.blit(lang['img'], rect)
            flag_rects.append({'rect': bg_rect, 'name': lang['name']})
            
            if bg_rect.collidepoint(mouse_pos) and lang['wip']:
                hovered_wip = True
                
            flag_x -= (bg_rect.width + S(15))
            
    if hovered_wip:
        wip_text = "Some translations may be incomplete"
        tooltip_text = font_16.render(wip_text, False, WHITE)
        tooltip_rect = tooltip_text.get_rect(topright=(center_offset_x + S(1260), flag_y + S(45)))
        bg_rect = tooltip_rect.inflate(S(10), S(10))
        
        s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 220))
        screen.blit(s, bg_rect.topleft)
        pygame.draw.rect(screen, WHITE, bg_rect, 1)
        screen.blit(tooltip_text, tooltip_rect)

    return start_rect, load_rect, settings_rect, quit_rect, flag_rects, help_rect, controls_rect