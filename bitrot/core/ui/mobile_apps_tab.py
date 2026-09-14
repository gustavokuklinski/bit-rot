# core/ui/mobile_apps_tab.py
import pygame
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.data.localization import tr

APP_MODULE_NAMES = {
    'show_hostile_npc': ('Military Registry', ORANGE),
    'show_static_hostile': ('Workers Registry', ORANGE),
    'show_static_npc': ('Civilians Registry', GREEN),
    'show_zombies': ('Vaccine Registry', RED),
    'show_animals': ('Next Petrol Fauna', YELLOW),
    'show_vehicles': ('Vehicle Registry', BLUE)
}

def get_card_map_value(item):
    if not item: 
        return None
    val = getattr(item, 'map_value', None)
    if not val and hasattr(item, 'properties') and isinstance(item.properties, dict):
        val = item.properties.get('map', {}).get('value')
    return val.strip().lower() if val else None

def draw_apps_tab(surface, game, modal, assets):
    if not hasattr(game, 'app_state'):
        game.app_state = {
            'slots': [None] * 5
        }
    state = game.app_state

    y_offset = modal['rect'].y + 75
    center_x = modal['rect'].centerx

    mouse_pos = getattr(game, 'scaled_mouse_pos', pygame.mouse.get_pos())

    # Check top modal
    is_top_modal = True
    for m in reversed(game.modals):
        if m['rect'].collidepoint(mouse_pos):
            if m.get('id') != modal.get('id'):
                is_top_modal = False
            break

    modal['app_slot_rects'] = []
    hovered_item = None

    # Title
    title_surf = font_12.render("Installed Apps (5 Slots)", False, WHITE)
    surface.blit(title_surf, title_surf.get_rect(center=(center_x, y_offset)))
    y_offset += 20

    # 5 SD Card Slots
    slot_size = 40
    gap = 6
    total_width = (slot_size * 5) + (gap * 4)
    start_x = center_x - (total_width // 2)

    for i in range(5):
        slot_rect = pygame.Rect(start_x + i * (slot_size + gap), y_offset, slot_size, slot_size)
        modal['app_slot_rects'].append({'rect': slot_rect, 'index': i})

        pygame.draw.rect(surface, GRAY_40, slot_rect, 0, 3)
        border_color = WHITE if getattr(game, 'is_dragging', False) and slot_rect.collidepoint(mouse_pos) and is_top_modal else GRAY
        pygame.draw.rect(surface, border_color, slot_rect, 1, 3)

        item = state['slots'][i]
        if item:
            if getattr(item, 'image', None):
                surface.blit(pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8)), slot_rect.move(4, 4))
            else:
                text_surf = font_12.render("SD", False, YELLOW)
                surface.blit(text_surf, text_surf.get_rect(center=slot_rect.center))

            if slot_rect.collidepoint(mouse_pos) and is_top_modal:
                hovered_item = item

    # Reduced gap to save vertical space
    y_offset += slot_size + 10

    # Active Modules Dashboard (Reduced height to 80 to fit inside modal)
    panel_rect = pygame.Rect(start_x, y_offset, total_width, 80)
    pygame.draw.rect(surface, (25, 25, 25), panel_rect, border_radius=4)
    pygame.draw.rect(surface, GRAY_60, panel_rect, 1, border_radius=4)

    list_y = y_offset + 6
    # Changed to font_14 for tighter spacing
    heading = font_14.render("Active Map Radars:", False, (200, 200, 200))
    surface.blit(heading, (start_x + 8, list_y))
    list_y += 14

    active_count = 0
    for item in state['slots']:
        if not item: 
            continue
        map_val = get_card_map_value(item)
        if map_val and map_val in APP_MODULE_NAMES:
            label, color = APP_MODULE_NAMES[map_val]
            bullet = font_14.render(f"• {label}", False, color)
            surface.blit(bullet, (start_x + 8, list_y))
            list_y += 11 # Tighter line height for up to 5 items
            active_count += 1

    if active_count == 0:
        for line in ["No SD Cards active.", "Drag SD Cards into slots", "above to activate map radars."]:
            surface.blit(font_14.render(line, False, GRAY), (start_x + 8, list_y))
            list_y += 12

    if hovered_item and not getattr(game, 'is_dragging', False):
        draw_tooltip(surface, hovered_item, mouse_pos)

    return []