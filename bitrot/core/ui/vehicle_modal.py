# core/ui/vehicle_modal.py

import pygame
import math
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.inventory_modal import draw_text_shadow
from core.ui.tooltip import draw_tooltip
from core.ui.tabs import Tabs
from core.data.localization import tr

STYLE = {
    "MARGIN_LEFT": 10,
    "TEXT_MAIN": WHITE,
    "TEXT_DIM": GRAY,
    "ACTIVE": GREEN,
    "INACTIVE": RED,
    "WARN": ORANGE,
    "BAR_BG": (35, 35, 35),
    "SLOT_BG": GRAY_40,
    "BORDER": GRAY_60
}

def _draw_switch(surface, x, y, width, height, is_on, is_hovered, on_color=GREEN, off_color=(130, 130, 130)):
    """Draws a tactile toggle switch widget with track and sliding knob."""
    switch_rect = pygame.Rect(x, y, width, height)
    
    # 1. Track background & border
    if is_on:
        track_bg = (18, 55, 24)
        border_col = on_color if is_hovered else (45, 140, 55)
    else:
        track_bg = (26, 26, 26)
        border_col = WHITE if is_hovered else (65, 65, 65)

    pygame.draw.rect(surface, track_bg, switch_rect, border_radius=height // 2)
    pygame.draw.rect(surface, border_col, switch_rect, 1, border_radius=height // 2)

    # 2. Sliding Knob / Thumb
    knob_size = height - 4
    if is_on:
        knob_x = switch_rect.right - knob_size - 2
        knob_col = on_color
    else:
        knob_x = switch_rect.left + 2
        knob_col = off_color

    knob_y = switch_rect.top + 2
    knob_rect = pygame.Rect(knob_x, knob_y, knob_size, knob_size)
    pygame.draw.rect(surface, knob_col, knob_rect, border_radius=knob_size // 2)
    pygame.draw.rect(surface, WHITE if is_hovered else (40, 40, 40), knob_rect, 1, border_radius=knob_size // 2)

    return switch_rect

def draw_vehicle_info_tab(surface, vehicle, start_x, start_y, modal_w, mouse_pos, modal, assets):
    """
    Renders TAB VEHICLE for 256px width:
    1. Switches (Motor: [Switch] | Light: [Switch])
    2. Speedometer
    3. Vehicle Dashboard (Motor, Fuel, Battery bars)
    """
    center_x = modal['rect'].centerx
    curr_y = start_y + 10

    # ==========================================
    # --- 1. TOGGLE SWITCH CONTROLS ---
    # ==========================================
    is_engine_on = bool(vehicle.active)
    is_lights_on = getattr(vehicle, 'lights', 'off') == 'on'

    eng_lbl = font_12.render(tr('vehicle', "Motor:"), True, STYLE["TEXT_MAIN"])
    lht_lbl = font_12.render(tr('vehicle', "Light:"), True, STYLE["TEXT_MAIN"])
    div_surf = font_12.render("|", True, STYLE["BORDER"])

    switch_w = 28
    switch_h = 14

    line_h = max(eng_lbl.get_height(), switch_h)

    # Calculate layout dimensions to center both controls with the divider
    eng_block_w = eng_lbl.get_width() + 5 + switch_w
    divider_w = div_surf.get_width() + 16
    lht_block_w = lht_lbl.get_width() + 5 + switch_w
    total_w = eng_block_w + divider_w + lht_block_w
    draw_x = center_x - (total_w // 2)

    # --- MOTOR SWITCH ---
    eng_lbl_y = curr_y + (line_h - eng_lbl.get_height()) // 2
    surface.blit(eng_lbl, (draw_x, eng_lbl_y))
    draw_x += eng_lbl.get_width() + 5

    veh_switch_x = draw_x
    veh_switch_y = curr_y + (line_h - switch_h) // 2
    veh_click_rect = pygame.Rect(veh_switch_x, veh_switch_y, switch_w, switch_h).inflate(4, 4)
    is_veh_hovered = veh_click_rect.collidepoint(mouse_pos)

    _draw_switch(surface, veh_switch_x, veh_switch_y, switch_w, switch_h, is_engine_on, is_veh_hovered, on_color=STYLE["ACTIVE"])
    draw_x += switch_w + 8

    # --- DIVIDER ---
    div_y = curr_y + (line_h - div_surf.get_height()) // 2
    surface.blit(div_surf, (draw_x, div_y))
    draw_x += div_surf.get_width() + 8

    # --- LIGHT SWITCH ---
    lht_lbl_y = curr_y + (line_h - lht_lbl.get_height()) // 2
    surface.blit(lht_lbl, (draw_x, lht_lbl_y))
    draw_x += lht_lbl.get_width() + 5

    lgt_switch_x = draw_x
    lgt_switch_y = curr_y + (line_h - switch_h) // 2
    lgt_click_rect = pygame.Rect(lgt_switch_x, lgt_switch_y, switch_w, switch_h).inflate(4, 4)
    is_lgt_hovered = lgt_click_rect.collidepoint(mouse_pos)

    _draw_switch(surface, lgt_switch_x, lgt_switch_y, switch_w, switch_h, is_lights_on, is_lgt_hovered, on_color=(60, 220, 255))

    # Seamless hitboxes for clicking toggles
    if is_engine_on:
        modal['rects']['engine_off'] = veh_click_rect
        modal['rects']['engine_on'] = pygame.Rect(-999, -999, 1, 1)
    else:
        modal['rects']['engine_on'] = veh_click_rect
        modal['rects']['engine_off'] = pygame.Rect(-999, -999, 1, 1)

    if is_lights_on:
        modal['rects']['lights_off'] = lgt_click_rect
        modal['rects']['lights_on'] = pygame.Rect(-999, -999, 1, 1)
    else:
        modal['rects']['lights_on'] = lgt_click_rect
        modal['rects']['lights_off'] = pygame.Rect(-999, -999, 1, 1)

    curr_y += 30

    # ==========================================
    # --- 2. SPEEDOMETER ---
    # ==========================================
    radius = 34
    speedo_cx = center_x
    speedo_cy = curr_y + radius + 2

    arc_rect = pygame.Rect(speedo_cx - radius, speedo_cy - radius, radius * 2, radius * 2)
    pygame.draw.arc(surface, STYLE["BORDER"], arc_rect, 0, math.pi, 2)

    for i in range(7):
        angle = math.pi - (i / 6.0) * math.pi
        tick_len = 5 if i % 3 == 0 else 3
        ox = speedo_cx + radius * math.cos(angle)
        oy = speedo_cy - radius * math.sin(angle)
        ix = speedo_cx + (radius - tick_len) * math.cos(angle)
        iy = speedo_cy - (radius - tick_len) * math.sin(angle)
        pygame.draw.line(surface, STYLE["BORDER"], (ix, iy), (ox, oy), 1)

    speed_kmh = int(vehicle.current_speed_val * 10)
    max_speed_kmh = max(int(vehicle.max_speed * 10), 1)
    clamped_speed = min(speed_kmh, max_speed_kmh)

    theta = math.pi - (clamped_speed / max_speed_kmh) * math.pi
    needle_x = speedo_cx + (radius * 0.8) * math.cos(theta)
    needle_y = speedo_cy - (radius * 0.8) * math.sin(theta)

    needle_color = STYLE["WARN"] if speed_kmh > max_speed_kmh * 0.75 else STYLE["TEXT_MAIN"]
    pygame.draw.line(surface, needle_color, (speedo_cx, speedo_cy), (needle_x, needle_y), 2)
    pygame.draw.circle(surface, STYLE["ACTIVE"], (speedo_cx, speedo_cy), 3)

    speed_surf = font_12.render(f"{speed_kmh} {tr('vehicle', 'km/h')}", True, needle_color)
    surface.blit(speed_surf, speed_surf.get_rect(center=(speedo_cx, speedo_cy + 10)))

    curr_y = speedo_cy + 22

    # ==========================================
    # --- 3. VEHICLE DASH (MOTOR, FUEL, BATTERY) ---
    # ==========================================
    if 'status_icons' not in modal:
        modal['status_icons'] = {}
        icon_paths = {
            'motor': SPRITE_PATH + 'items/car_motor.png',
            'fuel': SPRITE_PATH + 'items/car_fuel_unit.png',
            'battery': SPRITE_PATH + 'items/car_battery.png'
        }
        for key, path in icon_paths.items():
            try:
                img = pygame.image.load(path).convert_alpha()
                modal['status_icons'][key] = pygame.transform.scale(img, (16, 16))
            except Exception:
                modal['status_icons'][key] = None

    motor_item = vehicle.equipment.get('motor')
    motor_val, motor_max = 0.0, 100.0
    if motor_item:
        if hasattr(motor_item, 'load') and motor_item.load is not None:
            motor_val, motor_max = float(motor_item.load), float(getattr(motor_item, 'capacity', 100.0))
        elif hasattr(motor_item, 'durability') and motor_item.durability is not None:
            motor_val, motor_max = float(motor_item.durability), float(getattr(motor_item, 'max_durability', 100.0))
    motor_pct = max(0.0, min(1.0, (motor_val / motor_max) if motor_max > 0 else 0.0))

    fuel_item = vehicle.equipment.get('fuel')
    fuel_val, fuel_max = 0.0, 100.0
    if fuel_item:
        if hasattr(fuel_item, 'load') and fuel_item.load is not None:
            fuel_val = float(fuel_item.load)
        if hasattr(fuel_item, 'capacity') and fuel_item.capacity is not None:
            fuel_max = float(fuel_item.capacity)
    fuel_pct = max(0.0, min(1.0, (fuel_val / fuel_max) if fuel_max > 0 else 0.0))

    batt_item = vehicle.equipment.get('battery')
    batt_val, batt_max = 0.0, 100.0
    if batt_item:
        if hasattr(batt_item, 'durability') and batt_item.durability is not None:
            batt_val, batt_max = float(batt_item.durability), float(getattr(batt_item, 'max_durability', 100.0))
        elif hasattr(batt_item, 'load') and batt_item.load is not None:
            batt_val, batt_max = float(batt_item.load), float(getattr(batt_item, 'capacity', 100.0))
    batt_pct = max(0.0, min(1.0, (batt_val / batt_max) if batt_max > 0 else 0.0))

    meters = [
        ('motor', motor_pct, f"{int(motor_pct * 100)}%", GREEN if motor_pct > 0.5 else (YELLOW if motor_pct > 0.25 else RED)),
        ('fuel', fuel_pct, f"{int(fuel_val)}/{int(fuel_max)}", ORANGE if fuel_pct > 0.25 else RED),
        ('battery', batt_pct, f"{int(batt_pct * 100)}%", (0, 220, 255) if batt_pct > 0.25 else RED)
    ]

    bar_w = 120
    bar_h = 7
    dash_start_x = modal['rect'].x + (modal['rect'].width - (18 + 6 + bar_w + 6 + 46)) // 2

    for icon_key, pct, txt, col in meters:
        ico = modal['status_icons'].get(icon_key)
        if ico:
            surface.blit(ico, (dash_start_x, curr_y))
        else:
            pygame.draw.rect(surface, col, (dash_start_x, curr_y, 16, 16), 1)

        bx = dash_start_x + 22
        by = curr_y + 4
        pygame.draw.rect(surface, STYLE["BAR_BG"], (bx, by, bar_w, bar_h), border_radius=2)
        if pct > 0:
            pygame.draw.rect(surface, col, (bx, by, int(bar_w * pct), bar_h), border_radius=2)
        pygame.draw.rect(surface, STYLE["BORDER"], (bx, by, bar_w, bar_h), 1, border_radius=2)

        val_surf = font_12.render(txt, True, STYLE["TEXT_MAIN"])
        surface.blit(val_surf, (bx + bar_w + 6, curr_y + 1))
        curr_y += 18


def draw_vehicle_mechanics_tab(surface, vehicle, start_x, start_y, modal_w, mouse_pos, modal, assets):
    """
    Renders TAB MECHANICS for 256px width:
    MOTOR KEY FUEL BATTERY
    [SLOT] [SLOT] [SLOT] [SLOT]

    TIRES
    [SLOT] [SLOT]...
    """
    slot_size = 40
    gap = 16
    curr_y = start_y + 4

    slots_row_1 = ['motor', 'key', 'fuel', 'battery']
    row1_w = len(slots_row_1) * slot_size + (len(slots_row_1) - 1) * gap
    row1_x = modal['rect'].x + (modal['rect'].width - row1_w) // 2

    # --- ROW 1: MOTOR, KEY, FUEL, BATTERY ---
    for i, slot_name in enumerate(slots_row_1):
        sx = row1_x + i * (slot_size + gap)
        slot_rect = pygame.Rect(sx, curr_y + 14, slot_size, slot_size)

        short_names = {'motor': 'MOTOR', 'key': 'KEY', 'fuel': 'FUEL', 'battery': 'BATT'}
        lbl_text = short_names.get(slot_name, slot_name.upper())
        lbl = font_12.render(lbl_text, True, STYLE["TEXT_DIM"])
        surface.blit(lbl, lbl.get_rect(center=(slot_rect.centerx, curr_y + 6)))

        pygame.draw.rect(surface, STYLE["SLOT_BG"], slot_rect, 0, 3)
        pygame.draw.rect(surface, STYLE["BORDER"], slot_rect, 1, 3)

        item = vehicle.equipment.get(slot_name)
        if item:
            if getattr(item, 'image', None):
                icon = pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8))
                surface.blit(icon, icon.get_rect(center=slot_rect.center))

            cur_val, max_val = None, None
            if hasattr(item, 'durability') and item.durability is not None and getattr(item, 'max_durability', None):
                cur_val, max_val = item.durability, item.max_durability
            elif hasattr(item, 'load') and item.load is not None and getattr(item, 'capacity', None):
                cur_val, max_val = item.load, item.capacity

            if cur_val is not None and max_val is not None and float(max_val) > 0:
                pct = max(0.0, min(1.0, float(cur_val) / float(max_val)))
                bar_w, bar_h = slot_rect.width - 8, 3
                bar_x, bar_y = slot_rect.x + 4, slot_rect.bottom - 5
                col = GREEN if pct > 0.5 else (YELLOW if pct > 0.2 else RED)
                pygame.draw.rect(surface, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h))
                if pct > 0:
                    pygame.draw.rect(surface, col, (bar_x, bar_y, int(bar_w * pct), bar_h))
            elif hasattr(item, 'load') and item.load is not None and item.load > 0:
                draw_text_shadow(surface, font_12, str(int(item.load)), STYLE["TEXT_MAIN"],
                                (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')

        modal['equipment_rects'][slot_name] = slot_rect

    curr_y += 14 + slot_size + 10

    # --- ROW 2: TIRES ---
    slots_row_2 = getattr(vehicle, 'required_tires', [])
    tires_title = font_12.render(tr('vehicle', "TIRES"), True, STYLE["TEXT_MAIN"])
    surface.blit(tires_title, tires_title.get_rect(center=(modal['rect'].centerx, curr_y + 8)))
    curr_y += 18

    row2_w = len(slots_row_2) * slot_size + max(0, len(slots_row_2) - 1) * gap
    row2_x = modal['rect'].x + (modal['rect'].width - row2_w) // 2

    for i, slot_name in enumerate(slots_row_2):
        sx = row2_x + i * (slot_size + gap)
        slot_rect = pygame.Rect(sx, curr_y + 16, slot_size, slot_size)

        name_parts = slot_name.split('_')[1:]
        short_name = "".join([p[0].upper() for p in name_parts]) if name_parts else f"T{i+1}"
        lbl = font_12.render(short_name, True, STYLE["TEXT_DIM"])
        surface.blit(lbl, lbl.get_rect(center=(slot_rect.centerx, curr_y + 5)))

        pygame.draw.rect(surface, STYLE["SLOT_BG"], slot_rect, 0, 3)
        pygame.draw.rect(surface, STYLE["BORDER"], slot_rect, 1, 3)

        item = vehicle.equipment.get(slot_name)
        if item:
            if getattr(item, 'image', None):
                icon = pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8))
                surface.blit(icon, icon.get_rect(center=slot_rect.center))

            cur_val, max_val = None, None
            if hasattr(item, 'durability') and item.durability is not None and getattr(item, 'max_durability', None):
                cur_val, max_val = item.durability, item.max_durability

            if cur_val is not None and max_val is not None and float(max_val) > 0:
                pct = max(0.0, min(1.0, float(cur_val) / float(max_val)))
                bar_w, bar_h = slot_rect.width - 8, 3
                bar_x, bar_y = slot_rect.x + 4, slot_rect.bottom - 5
                col = GREEN if pct > 0.5 else (YELLOW if pct > 0.2 else RED)
                pygame.draw.rect(surface, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h))
                if pct > 0:
                    pygame.draw.rect(surface, col, (bar_x, bar_y, int(bar_w * pct), bar_h))

        modal['equipment_rects'][slot_name] = slot_rect


def draw_vehicle_modal(surface, game, modal, assets, mouse_pos):
    vehicle = modal['vehicle']
    base_modal = BaseModal(surface, modal, assets, vehicle.name)
    base_modal.draw_base()
    close_btn = base_modal.get_buttons()

    tabs_data = [
        {'label': 'Vehicle', 'icon': assets.get('vehicle_icon')},
        {'label': 'Mechanics', 'icon': assets.get('mechanics_icon')}
    ]

    if 'active_tab' not in modal or modal['active_tab'] not in ['Vehicle', 'Mechanics']:
        modal['active_tab'] = 'Vehicle'

    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw(game, mouse_pos)

    content_y = base_modal.modal_y + 70
    content_x = base_modal.modal_x + STYLE["MARGIN_LEFT"]

    modal['equipment_rects'] = {}
    modal.setdefault('rects', {})

    active_tab = modal.get('active_tab')
    if active_tab == 'Vehicle':
        draw_vehicle_info_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)
    elif active_tab == 'Mechanics':
        draw_vehicle_mechanics_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)

    if 'equipment_rects' in modal:
        for slot_name, rect in modal['equipment_rects'].items():
            if rect.collidepoint(mouse_pos):
                item = vehicle.equipment.get(slot_name)
                if item:
                    draw_tooltip(surface, item, mouse_pos)

    return [close_btn]