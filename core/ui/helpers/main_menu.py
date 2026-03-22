# core/ui/helpers/main_menu.py
import pygame
import os
import xml.etree.ElementTree as ET
import core.data.config
from core.data.config import *
from datetime import datetime
from core.data.localization import tr

_logo_img = None
_language_cache = None

def get_available_languages():
    """Parses the languages XML and caches the flags."""
    global _language_cache
    if _language_cache is not None:
        return _language_cache
    
    _language_cache = []
    xml_path = './game/lib/lang/languages.xml'
    
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
                        full_path = f"./game/lib/sprites/ui/{sprite_file}"
                        _language_cache.append({'name': name, 'sprite_path': full_path, 'wip': wip_val, 'img': None})
        except Exception as e:
            print(f"Error parsing languages.xml: {e}")
    
    # Elegant fallback just in case the XML isn't created yet
    if not _language_cache:
        _language_cache = [
            {'name': 'en_US', 'sprite_path': './game/lib/sprites/ui/lang_en.png', 'wip': False, 'img': None},
            {'name': 'pt_BR', 'sprite_path': './game/lib/sprites/ui/lang_pt_BR.png', 'wip': True, 'img': None}
        ]
            
    # Load and scale images into memory
    for lang in _language_cache:
        try:
            if os.path.exists(lang['sprite_path']):
                img = pygame.image.load(lang['sprite_path']).convert_alpha()
                lang['img'] = pygame.transform.scale(img, (32, 24))
        except Exception:
            pass
            
    return _language_cache

def draw_btn(surface, rect, text, mouse_pos, enabled=True):
    """Helper to draw a standardized menu button."""
    is_hovered = rect.collidepoint(mouse_pos)
    
    if not enabled:
        bg_color = (40, 40, 40)
        text_color = (100, 100, 100)
    else:
        bg_color = (80, 80, 80) if is_hovered else (60, 60, 60)
        text_color = WHITE

    pygame.draw.rect(surface, bg_color, rect, border_radius=6)

    txt_surf = large_font.render(text, True, text_color)
    txt_rect = txt_surf.get_rect(center=rect.center)
    surface.blit(txt_surf, txt_rect)

def draw_menu(screen, mouse_pos, has_save=False):
    global _logo_img
    screen.fill(DARK_GRAY)

    try:
        if _logo_img is None:
            _logo_img = pygame.image.load('./game/icons/logo.png').convert_alpha()
            target_w = 500
            scale_factor = target_w / _logo_img.get_width()
            target_h = int(_logo_img.get_height() * scale_factor)
            _logo_img = pygame.transform.scale(_logo_img, (target_w, target_h))
    except Exception:
        _logo_img = None

    if _logo_img:
        logo_rect = _logo_img.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT * 0.3))
        screen.blit(_logo_img, logo_rect)
    else:
        title_text = title_font.render("Bit Rot", True, RED)
        title_rect = title_text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT * 0.25))
        screen.blit(title_text, title_rect)

    btn_width = 400
    btn_height = 50
    spacing = 20
    
    center_x = GAME_WIDTH // 2
    start_y = GAME_HEIGHT * 0.55 

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
    footer_text = font_notification.render(footer_str, True, (100, 100, 100))
    footer_rect = footer_text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT - 20))
    screen.blit(footer_text, footer_rect)

    # --- NEW: Language Flags Rendering ---
    langs = get_available_languages()
    flag_rects = []
    
    flag_x = GAME_WIDTH - 20
    flag_y = 20
    hovered_wip = False
    
    for lang in reversed(langs):
        if lang['img']:
            # Create a button-like background rect around the flag (adds padding)
            bg_rect = pygame.Rect(0, 0, lang['img'].get_width() + 16, lang['img'].get_height() + 12)
            bg_rect.topright = (flag_x, flag_y)
            
            # Center the flag image inside the background rect
            rect = lang['img'].get_rect(center=bg_rect.center)
            
            is_hovered = bg_rect.collidepoint(mouse_pos)
            is_selected = (lang['name'] == core.data.config.GAME_LANGUAGE)
            
            # Background color matches the main menu buttons
            bg_color = (80, 80, 80) if is_hovered else (60, 60, 60)
            
            # Draw the rounded button background
            pygame.draw.rect(screen, bg_color, bg_rect, border_radius=6)
            
            # Draw the border (gray if selected, otherwise dark)
            if is_selected:
                pygame.draw.rect(screen, (150, 150, 150), bg_rect, width=2, border_radius=6)
            else:
                pygame.draw.rect(screen, (40, 40, 40), bg_rect, width=1, border_radius=6)
                
            # Draw the flag image over the center
            screen.blit(lang['img'], rect)
            
            # Use the larger bg_rect for the clickable area
            flag_rects.append({'rect': bg_rect, 'name': lang['name']})
            
            if bg_rect.collidepoint(mouse_pos) and lang['wip']:
                hovered_wip = True
                
            flag_x -= (bg_rect.width + 15)
            
    # Draw WIP Tooltip if hovering
    if hovered_wip:
        wip_text = "Some translations may be incomplete"
        tooltip_text = font_notification.render(wip_text, True, WHITE)
        # Shifted slightly lower (+45 instead of +35) to account for the new padded button
        tooltip_rect = tooltip_text.get_rect(topright=(GAME_WIDTH - 20, flag_y + 45))
        bg_rect = tooltip_rect.inflate(10, 10)
        
        # Transparent background for tooltip
        s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 220))
        screen.blit(s, bg_rect.topleft)
        pygame.draw.rect(screen, WHITE, bg_rect, 1)
        screen.blit(tooltip_text, tooltip_rect)

    # Return flag_rects along with the other buttons
    return start_rect, load_rect, settings_rect, quit_rect, flag_rects