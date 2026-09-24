# core/ui/helpers/select_world.py

import os
import pygame
import random
from types import SimpleNamespace

import core.data.config
from core.data.config import (
    GAME_WIDTH, GAME_HEIGHT, UI_SCALE, WHITE, GRAY, DARK_GRAY,
    GRAY_60, GRAY_80, GREEN, RED, YELLOW, font_16, font_12, SPRITE_PATH, BASE_DIR
)
from core.data.localization import tr
from core.ui.helpers.trait_config_loader import load_config_data

_world_icons_cache = {}
_logo_cache = None

def _get_logo_image(width):
    """Loads, scales, and caches the game logo."""
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
    """Safely loads and caches mode icons with a fallback surface."""
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
        print(f"[SelectWorld] Warning loading icon '{filename_or_relpath}': {e}")

    fallback = pygame.Surface(size, pygame.SRCALPHA)
    fallback.fill((80, 80, 80))
    _world_icons_cache[filename_or_relpath] = fallback
    return fallback


def _apply_preset_and_proceed(game, state, preset_name):
    """Loads world preset config and moves directly to Character Selection."""
    path = core.data.config.get_world_config_path(preset_name)
    world_data = load_config_data(path)
    
    state['world_data'] = world_data
    state['selected_config_preset'] = preset_name
    state['world_preset_name'] = preset_name
    core.data.config.load_settings(preset_name)

    # Ensure 12-digit world seed is initialized
    if not state.get('world_seed'):
        state['world_seed'] = "".join(str(random.randint(0, 9)) for _ in range(12))

    if hasattr(game, 'world_setup_state'):
        game.world_setup_state['world_data'] = world_data
        game.world_setup_state['selected_config_preset'] = preset_name
        game.world_setup_state['world_preset_name'] = preset_name
        game.world_setup_state['world_seed'] = state['world_seed']
        game.world_setup_state['world_unsaved'] = False

    state['current_tab'] = 'SelectCharacter'  # Advance to Character Selection


def draw_select_world_screen(game, state, mouse_pos):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_x = GAME_WIDTH // 2

    # --- 1. GAME LOGO AT THE TOP ---
    logo_w = S(240)
    logo_img = _get_logo_image(logo_w)
    
    top_cursor_y = S(42)
    if logo_img:
        logo_rect = logo_img.get_rect(center=(center_x, top_cursor_y + (logo_img.get_height() // 2)))
        game.game_screen.blit(logo_img, logo_rect)
        top_cursor_y = logo_rect.bottom + S(10)
    else:
        top_cursor_y = S(45)

    # --- 2. SCREEN TITLE & SUBTITLE ---
    title_text = font_16.render(tr('ui', "SELECT GAME WORLD"), False, WHITE)
    title_rect = title_text.get_rect(center=(center_x, top_cursor_y + S(40)))
    game.game_screen.blit(title_text, title_rect)

    sub_text = font_12.render(tr('ui', "Choose your game mode to begin your journey"), False, (160, 160, 160))
    sub_rect = sub_text.get_rect(center=(center_x, title_rect.bottom + S(12)))
    game.game_screen.blit(sub_text, sub_rect)

    # --- 3. MODE CARDS ---
    MODES = [
        {
            'id': 'casual',
            'name': "Casual",
            'subtitle': tr('ui', "Fast and play"),
            'icon_path': 'ui/infection.png',
            'preset': 'world-casual',
            'accent': (50, 205, 50),
            'tooltip_lines': [
                tr('ui', "Fast and play"),
                tr('ui', "Small map"),
                tr('ui', "Lower rotters"),
                tr('ui', "High loot")
            ]
        },
        {
            'id': 'hardcore',
            'name': "Hardcore",
            'subtitle': tr('ui', "High risk survival"),
            'icon_path': 'zombie/dead.png',
            'preset': 'world-hardcore',
            'accent': (220, 60, 60),
            'tooltip_lines': [
                tr('ui', "Large map"),
                tr('ui', "Lot of rotters"),
                tr('ui', "Low loot")
            ]
        },
        {
            'id': 'sandbox',
            'name': "Sandbox",
            'subtitle': tr('ui', "Custom world rules"),
            'icon_path': 'items/consumable_book_general_content.png',
            'preset': 'world',
            'accent': (255, 200, 50),
            'tooltip_lines': [
                tr('ui', "Tailor how you will rot")
            ]
        }
    ]

    card_w = S(270)
    card_h = S(345)
    spacing = S(25)
    total_w = (card_w * 3) + (spacing * 2)
    start_x = center_x - (total_w // 2)
    card_y = sub_rect.bottom + S(16)

    clickable_rects = {
        'cards': [],
        'back_button': None
    }

    hovered_mode = None

    for i, mode in enumerate(MODES):
        cx = start_x + i * (card_w + spacing)
        card_rect = pygame.Rect(cx, card_y, card_w, card_h)
        is_hovered = card_rect.collidepoint(mouse_pos)

        if is_hovered:
            hovered_mode = mode

        # Background and card frame
        bg_col = (45, 45, 45) if is_hovered else (32, 32, 32)
        border_col = mode['accent'] if is_hovered else GRAY_60
        border_width = 2 if is_hovered else 1

        pygame.draw.rect(game.game_screen, bg_col, card_rect, border_radius=S(8))
        pygame.draw.rect(game.game_screen, border_col, card_rect, width=border_width, border_radius=S(8))

        # Icon Frame
        icon_box_size = S(64)
        icon_box = pygame.Rect(0, 0, icon_box_size, icon_box_size)
        icon_box.center = (card_rect.centerx, card_rect.top + S(55))
        pygame.draw.rect(game.game_screen, (22, 22, 22), icon_box, border_radius=S(6))
        pygame.draw.rect(game.game_screen, border_col, icon_box, width=1, border_radius=S(6))

        # Draw Icon
        icon_surf = _get_mode_icon(mode['icon_path'], size=(S(44), S(44)))
        if icon_surf:
            game.game_screen.blit(icon_surf, icon_surf.get_rect(center=icon_box.center))

        # Mode Title
        name_surf = font_16.render(tr('ui', mode['name']), False, mode['accent'] if is_hovered else WHITE)
        game.game_screen.blit(name_surf, name_surf.get_rect(center=(card_rect.centerx, card_rect.top + S(110))))

        # Subtitle
        sub_surf = font_12.render(mode['subtitle'], False, (180, 180, 180))
        game.game_screen.blit(sub_surf, sub_surf.get_rect(center=(card_rect.centerx, card_rect.top + S(134))))

        # Divider
        pygame.draw.line(
            game.game_screen, (55, 55, 55),
            (card_rect.left + S(20), card_rect.top + S(155)),
            (card_rect.right - S(20), card_rect.top + S(155)), 1
        )

        # Overview Bullet Summary inside Card
        line_cursor_y = card_rect.top + S(172)
        for line_str in mode['tooltip_lines']:
            b_surf = font_12.render(f"- {line_str}", False, (220, 220, 220))
            game.game_screen.blit(b_surf, (card_rect.left + S(25), line_cursor_y))
            line_cursor_y += S(22)

        # Select Mode Button
        btn_h = S(38)
        btn_rect = pygame.Rect(card_rect.left + S(20), card_rect.bottom - btn_h - S(14), card_rect.width - S(40), btn_h)
        btn_bg = mode['accent'] if is_hovered else (55, 55, 55)
        btn_text_col = (10, 10, 10) if is_hovered else WHITE
        pygame.draw.rect(game.game_screen, btn_bg, btn_rect, border_radius=S(5))

        btn_txt = font_12.render(tr('ui', "Select Mode"), False, btn_text_col)
        game.game_screen.blit(btn_txt, btn_txt.get_rect(center=btn_rect.center))

        clickable_rects['cards'].append((mode, card_rect))

    # --- 4. BOTTOM BACK BUTTON ---
    back_w = S(200)
    back_h = S(42)
    back_rect = pygame.Rect(center_x - back_w // 2, card_y + card_h + S(60), back_w, back_h)
    is_back_hover = back_rect.collidepoint(mouse_pos)
    back_bg = (80, 80, 80) if is_back_hover else (60, 60, 60)
    pygame.draw.rect(game.game_screen, back_bg, back_rect, border_radius=S(6))
    back_txt = font_16.render(tr('ui', "Back"), False, WHITE)
    game.game_screen.blit(back_txt, back_txt.get_rect(center=back_rect.center))
    clickable_rects['back_button'] = back_rect


    return clickable_rects


def handle_select_world_events(game, state, event, mouse_pos, clickable_rects):
    if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
        # Check Back Button
        if clickable_rects.get('back_button') and clickable_rects['back_button'].collidepoint(mouse_pos):
            game.game_state = 'MENU'
            return

        # Check Cards Click
        for mode, rect in clickable_rects.get('cards', []):
            if rect.collidepoint(mouse_pos):
                state['chosen_mode'] = mode['id']
                if mode['id'] in ('casual', 'hardcore'):
                    _apply_preset_and_proceed(game, state, mode['preset'])
                elif mode['id'] == 'sandbox':
                    state['current_tab'] = 'World'
                return