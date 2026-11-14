# core/ui/alias_modal.py

import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.data.localization import tr

def draw_alias_modal(surface, game, modal, assets, mouse_pos):
    modal_w = modal['rect'].width if 'rect' in modal else 340
    modal_h = modal['rect'].height if 'rect' in modal else 145
    base_modal = BaseModal(surface, modal, assets, "Add Alias", w=modal_w, h=modal_h)
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    item = modal.get('item')
    pad = 15
    start_x = base_modal.modal_x + pad
    cur_y = base_modal.modal_y + base_modal.header_h + 10
    usable_w = modal_w - (pad * 2)

    # 1. Item Label + Character Counter (0/32)
    item_name = tr('item', item.name) if item else tr('ui', 'Item')
    if len(item_name) > 22:
        item_name = item_name[:20] + ".."
    lbl_surf = font_12.render(f"{item_name}:", False, WHITE)
    surface.blit(lbl_surf, (start_x, cur_y))

    cur_text = modal.get('input_text', '')
    count_col = YELLOW if len(cur_text) >= 32 else (170, 170, 170)
    count_surf = font_12.render(f"{len(cur_text)}/32", False, count_col)
    surface.blit(count_surf, (base_modal.modal_rect.right - pad - count_surf.get_width(), cur_y))

    cur_y += 20

    # 2. Text Input Box
    input_h = 28
    input_rect = pygame.Rect(start_x, cur_y, usable_w, input_h)
    modal['input_rect'] = input_rect

    is_active = modal.get('input_active', True)
    is_input_hover = input_rect.collidepoint(mouse_pos)
    pygame.draw.rect(surface, (15, 15, 15) if is_active else (28, 28, 28), input_rect, border_radius=3)
    pygame.draw.rect(surface, YELLOW if is_active else (WHITE if is_input_hover else GRAY_60), input_rect, 1, border_radius=3)

    if not cur_text and not is_active:
        txt_surf = font_12.render(tr('ui', "Type alias..."), False, (100, 100, 100))
    else:
        txt_surf = font_12.render(cur_text, False, WHITE)

    old_clip = surface.get_clip()
    surface.set_clip(input_rect.inflate(-8, -4))
    text_y = input_rect.centery - txt_surf.get_height() // 2
    text_x = input_rect.x + 8
    if txt_surf.get_width() > input_rect.width - 16:
        text_x = input_rect.right - 8 - txt_surf.get_width()
    surface.blit(txt_surf, (text_x, text_y))

    if is_active and (pygame.time.get_ticks() // 500) % 2 == 0:
        cursor_x = min(input_rect.right - 6, text_x + (txt_surf.get_width() if cur_text else 0) + 1)
        pygame.draw.line(surface, WHITE, (cursor_x, input_rect.y + 5), (cursor_x, input_rect.bottom - 5), 1)
    surface.set_clip(old_clip)

    cur_y += input_h + 14

    # 3. Save & Cancel Buttons
    btn_gap = 10
    btn_w = (usable_w - btn_gap) // 2
    btn_h = 28

    save_rect = pygame.Rect(start_x, cur_y, btn_w, btn_h)
    cancel_rect = pygame.Rect(save_rect.right + btn_gap, cur_y, usable_w - btn_w - btn_gap, btn_h)
    modal['save_btn_rect'] = save_rect
    modal['cancel_btn_rect'] = cancel_rect

    # Save Button
    is_save_hover = save_rect.collidepoint(mouse_pos)
    pygame.draw.rect(surface, (40, 120, 40) if is_save_hover else (30, 90, 30), save_rect, border_radius=4)
    pygame.draw.rect(surface, WHITE if is_save_hover else GRAY_60, save_rect, 1, border_radius=4)
    save_txt = font_12.render(tr('ui', "Save"), False, YELLOW if is_save_hover else WHITE)
    surface.blit(save_txt, save_txt.get_rect(center=save_rect.center))

    # Cancel Button
    is_cancel_hover = cancel_rect.collidepoint(mouse_pos)
    pygame.draw.rect(surface, (80, 50, 50) if is_cancel_hover else (55, 40, 40), cancel_rect, border_radius=4)
    pygame.draw.rect(surface, WHITE if is_cancel_hover else GRAY_60, cancel_rect, 1, border_radius=4)
    cancel_txt = font_12.render(tr('ui', "Cancel"), False, YELLOW if is_cancel_hover else WHITE)
    surface.blit(cancel_txt, cancel_txt.get_rect(center=cancel_rect.center))

    return close_button