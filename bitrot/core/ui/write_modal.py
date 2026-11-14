# core/ui/write_modal.py

import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.data.localization import tr
from core.entities.item.item_helpers import player_has_any_item

def _wrap_input_text(text, max_width, font):
    """Wraps text into visual lines while preserving trailing spaces and newlines."""
    lines = []
    for p in text.split('\n'):
        if p == "":
            lines.append("")
            continue
        cur_line = ""
        words = p.split(' ')
        for idx, word in enumerate(words):
            piece = word if idx == 0 else (" " + word)
            if font.size(cur_line + piece)[0] <= max_width:
                cur_line += piece
            else:
                if cur_line:
                    lines.append(cur_line)
                    cur_line = ""
                test_word = word if idx > 0 else piece
                if font.size(test_word)[0] <= max_width:
                    cur_line = test_word
                else:
                    for ch in test_word:
                        if font.size(cur_line + ch)[0] <= max_width:
                            cur_line += ch
                        else:
                            lines.append(cur_line)
                            cur_line = ch
        lines.append(cur_line)
    return lines if lines else [""]

def draw_write_modal(surface, game, modal, assets, mouse_pos):
    modal_w = modal['rect'].width if 'rect' in modal else 400
    modal_h = modal['rect'].height if 'rect' in modal else 260
    base_modal = BaseModal(surface, modal, assets, "Write", w=modal_w, h=modal_h)
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    item = modal.get('item')
    can_write = getattr(item, 'can_write', False) if item else False
    max_len = getattr(item, 'text_length', 128) if item else 128
    if max_len <= 0:
        max_len = 128

    if not can_write:
        modal['is_editing'] = False
        modal['input_active'] = False

    is_editing = bool(modal.get('is_editing', False) and can_write)
    is_active = bool(modal.get('input_active', False) and is_editing)
    has_eraser = player_has_any_item(game.player, ('Eraser',)) if getattr(game, 'player', None) else False

    pad = 15
    start_x = base_modal.modal_x + pad
    cur_y = base_modal.modal_y + base_modal.header_h + 10
    usable_w = modal_w - (pad * 2)

    # 1. Item Label + Character Counter (0 / max_len)
    item_name = tr('item', item.name) if item else tr('ui', 'Text')
    if len(item_name) > 24:
        item_name = item_name[:22] + ".."
    lbl_surf = font_12.render(f"{item_name}:", False, WHITE)
    surface.blit(lbl_surf, (start_x, cur_y))

    cur_text = modal.get('input_text', '')
    count_col = YELLOW if len(cur_text) >= max_len else (170, 170, 170)
    count_surf = font_12.render(f"{len(cur_text)}/{max_len}", False, count_col)
    surface.blit(count_surf, (base_modal.modal_rect.right - pad - count_surf.get_width(), cur_y))

    cur_y += 20

    # 2. Multi-line Input Textbox
    btn_h = 28
    input_h = base_modal.modal_rect.bottom - pad - btn_h - 12 - cur_y
    input_rect = pygame.Rect(start_x, cur_y, usable_w, input_h)
    modal['input_rect'] = input_rect

    is_input_hover = input_rect.collidepoint(mouse_pos)
    bg_col = (15, 15, 15) if is_active else ((24, 24, 24) if is_editing else (28, 28, 28))
    border_col = YELLOW if is_active else (WHITE if (is_editing and is_input_hover) else GRAY_60)
    pygame.draw.rect(surface, bg_col, input_rect, border_radius=3)
    pygame.draw.rect(surface, border_col, input_rect, 1, border_radius=3)

    line_height = font_12.get_height() + 4
    text_area_w = input_rect.width - 16
    wrapped_lines = _wrap_input_text(cur_text, text_area_w, font_12)

    total_text_h = len(wrapped_lines) * line_height
    visible_h = input_rect.height - 10
    max_scroll = max(0, total_text_h - visible_h)
    modal['max_scroll_offset'] = max_scroll

    if modal.pop('_scroll_to_bottom', False):
        modal['scroll_offset_y'] = max_scroll

    scroll_y = max(0, min(modal.get('scroll_offset_y', 0), max_scroll))
    modal['scroll_offset_y'] = scroll_y

    old_clip = surface.get_clip()
    surface.set_clip(input_rect.inflate(-8, -6))

    if not cur_text and not is_active:
        ph = tr('ui', "Type text...") if is_editing else tr('ui', "Empty")
        ph_surf = font_12.render(ph, False, (100, 100, 100))
        surface.blit(ph_surf, (input_rect.x + 6, input_rect.y + 6))
    else:
        for idx, line_str in enumerate(wrapped_lines):
            ly = input_rect.y + 5 + (idx * line_height) - scroll_y
            if ly + line_height >= input_rect.y and ly <= input_rect.bottom:
                l_surf = font_12.render(line_str, False, WHITE if is_editing else (200, 200, 200))
                surface.blit(l_surf, (input_rect.x + 6, ly))

    if is_active and (pygame.time.get_ticks() // 500) % 2 == 0:
        last_line = wrapped_lines[-1] if wrapped_lines else ""
        cursor_x = min(input_rect.right - 6, input_rect.x + 6 + font_12.size(last_line)[0] + 1)
        cursor_y = input_rect.y + 5 + ((len(wrapped_lines) - 1) * line_height) - scroll_y
        if cursor_y + line_height >= input_rect.y and cursor_y <= input_rect.bottom:
            pygame.draw.line(surface, WHITE, (cursor_x, cursor_y), (cursor_x, cursor_y + font_12.get_height()), 1)

    surface.set_clip(old_clip)

    cur_y += input_h + 12

    # 3. Save, Edit & Cancel Buttons
    btn_gap = 8
    btn_w = (usable_w - (btn_gap * 2)) // 3

    save_rect = pygame.Rect(start_x, cur_y, btn_w, btn_h)
    edit_rect = pygame.Rect(save_rect.right + btn_gap, cur_y, btn_w, btn_h)
    cancel_rect = pygame.Rect(edit_rect.right + btn_gap, cur_y, usable_w - (btn_w * 2) - (btn_gap * 2), btn_h)
    modal['save_btn_rect'] = save_rect
    modal['edit_btn_rect'] = edit_rect
    modal['cancel_btn_rect'] = cancel_rect

    # Save Button (Enabled only while editing)
    is_save_hover = save_rect.collidepoint(mouse_pos) and is_editing
    save_bg = (40, 120, 40) if is_save_hover else ((30, 90, 30) if is_editing else (38, 38, 38))
    save_border = WHITE if is_save_hover else (GRAY_60 if is_editing else (55, 55, 55))
    save_col = YELLOW if is_save_hover else (WHITE if is_editing else (110, 110, 110))
    pygame.draw.rect(surface, save_bg, save_rect, border_radius=4)
    pygame.draw.rect(surface, save_border, save_rect, 1, border_radius=4)
    save_txt = font_12.render(tr('ui', "Save"), False, save_col)
    surface.blit(save_txt, save_txt.get_rect(center=save_rect.center))

    # Edit Button (Enabled only when saved/locked, can_write=True, and player carries Eraser)
    can_click_edit = can_write and (not is_editing) and has_eraser
    is_edit_hover = edit_rect.collidepoint(mouse_pos) and can_click_edit
    edit_bg = (70, 95, 130) if is_edit_hover else ((45, 65, 95) if can_click_edit else (38, 38, 38))
    edit_border = WHITE if is_edit_hover else (GRAY_60 if can_click_edit else (55, 55, 55))
    edit_col = YELLOW if is_edit_hover else (WHITE if can_click_edit else (110, 110, 110))
    pygame.draw.rect(surface, edit_bg, edit_rect, border_radius=4)
    pygame.draw.rect(surface, edit_border, edit_rect, 1, border_radius=4)
    edit_txt = font_12.render(tr('ui', "Edit"), False, edit_col)
    surface.blit(edit_txt, edit_txt.get_rect(center=edit_rect.center))

    # Cancel Button
    is_cancel_hover = cancel_rect.collidepoint(mouse_pos)
    pygame.draw.rect(surface, (80, 50, 50) if is_cancel_hover else (55, 40, 40), cancel_rect, border_radius=4)
    pygame.draw.rect(surface, WHITE if is_cancel_hover else GRAY_60, cancel_rect, 1, border_radius=4)
    cancel_txt = font_12.render(tr('ui', "Cancel"), False, YELLOW if is_cancel_hover else WHITE)
    surface.blit(cancel_txt, cancel_txt.get_rect(center=cancel_rect.center))

    return close_button