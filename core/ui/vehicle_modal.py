import pygame
import math
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.inventory_modal import draw_text_shadow
from core.ui.tooltip import draw_tooltip
from core.ui.tabs import Tabs
from core.data.localization import tr

# --- CONFIGURATION: LAYOUT & COLORS ---
STYLE = {
    "MARGIN_TOP": 45,        
    "MARGIN_LEFT": 15,       
    "COL_2_OFFSET": 230,     
    
    "SECTION_SPACING": 35,   
    "TITLE_SPACING": 15,      
    
    "BAR_WIDTH": 100,        
    "BAR_HEIGHT": 8,         
    "SLOT_SIZE": 48,         
    "SLOT_GAP": 25,          
    "SEAT_GAP": 20,          
    
    "TEXT_MAIN": WHITE,
    "TEXT_DIM": GRAY,        
    "ACTIVE": GREEN,         
    "INACTIVE": RED,         
    "WARN": ORANGE,          
    "BAR_BG": (40, 40, 40),  
    "SLOT_BG": (30, 30, 30), 
    "BORDER": GRAY,          
    "DRIVER_LBL": YELLOW,    
    "TRUNK_BAR": BLUE        
}

def draw_vehicle_info_tab(surface, vehicle, start_x, start_y, modal_w, mouse_pos, modal, assets):
    """
    Draws the content of the vehicle info tab in a 3-column dashboard layout.
    Left: Controls | Center: Speedometer | Right: Statuses
    """
    # Define the three column X positions
    center_x = start_x - STYLE["MARGIN_LEFT"] + (modal_w // 2)
    left_x = start_x
    right_x = start_x - STYLE["MARGIN_LEFT"] + modal_w - 110
    
    y_base = start_y + 20

    # ==========================================
    # --- 1. LEFT COLUMN: ENGINE & LIGHTS ---
    # ==========================================
    
    # Engine
    eng_lbl = font.render(tr('vehicle', "Engine:"), True, STYLE["TEXT_MAIN"])
    surface.blit(eng_lbl, (left_x, y_base))
    
    is_engine_on = vehicle.active
    e_on_color = STYLE["ACTIVE"] if is_engine_on else STYLE["TEXT_DIM"]
    e_off_color = STYLE["INACTIVE"] if not is_engine_on else STYLE["TEXT_DIM"]
    
    e_on_txt = font.render(tr('vehicle', "[ON]"), True, e_on_color)
    e_off_txt = font.render(tr('vehicle', "[OFF]"), True, e_off_color)
    
    e_on_rect = e_on_txt.get_rect(topleft=(left_x, y_base + 25))
    surface.blit(e_on_txt, e_on_rect)
    e_off_rect = e_off_txt.get_rect(topleft=(left_x + e_on_txt.get_width() + 10, y_base + 25))
    surface.blit(e_off_txt, e_off_rect)
    
    # Lights
    lht_lbl = font.render(tr('vehicle', "Lights:"), True, STYLE["TEXT_MAIN"])
    surface.blit(lht_lbl, (left_x, y_base + 65))
    
    is_lights_on = getattr(vehicle, 'lights', 'off') == 'on'
    l_on_color = STYLE["ACTIVE"] if is_lights_on else STYLE["TEXT_DIM"]
    l_off_color = STYLE["INACTIVE"] if not is_lights_on else STYLE["TEXT_DIM"]
    
    l_on_txt = font.render(tr('vehicle', "[ON]"), True, l_on_color)
    l_off_txt = font.render(tr('vehicle', "[OFF]"), True, l_off_color)
    
    l_on_rect = l_on_txt.get_rect(topleft=(left_x, y_base + 90))
    surface.blit(l_on_txt, l_on_rect)
    l_off_rect = l_off_txt.get_rect(topleft=(left_x + l_on_txt.get_width() + 10, y_base + 90))
    surface.blit(l_off_txt, l_off_rect)
    
    # Store rects for click interaction
    modal['rects'] = {
        'engine_on': e_on_rect,
        'engine_off': e_off_rect,
        'lights_on': l_on_rect,
        'lights_off': l_off_rect
    }

    # ==========================================
    # --- 2. MIDDLE COLUMN: SPEEDOMETER ---
    # ==========================================
    radius = 65
    speedo_cx = center_x
    speedo_cy = y_base + 80
    
    # Draw Background Arc
    arc_rect = pygame.Rect(speedo_cx - radius, speedo_cy - radius, radius * 2, radius * 2)
    pygame.draw.arc(surface, STYLE["BORDER"], arc_rect, 0, math.pi, 4)
    
    # Draw Gauge Ticks
    for i in range(11):
        angle = math.pi - (i / 10.0) * math.pi
        tick_len = 12 if i % 5 == 0 else 6
        outer_x = speedo_cx + radius * math.cos(angle)
        outer_y = speedo_cy - radius * math.sin(angle)
        inner_x = speedo_cx + (radius - tick_len) * math.cos(angle)
        inner_y = speedo_cy - (radius - tick_len) * math.sin(angle)
        pygame.draw.line(surface, STYLE["BORDER"], (inner_x, inner_y), (outer_x, outer_y), 2)

    # Speed & Needle calculations
    speed_kmh = int(vehicle.current_speed_val * 10)
    max_speed_kmh = max(int(vehicle.max_speed * 10), 1)
    clamped_speed = min(speed_kmh, max_speed_kmh)
    
    # Angle maps from Pi (0 speed) to 0 (Max speed)
    theta = math.pi - (clamped_speed / max_speed_kmh) * math.pi
    needle_x = speedo_cx + (radius * 0.85) * math.cos(theta)
    needle_y = speedo_cy - (radius * 0.85) * math.sin(theta)
    
    # Draw Needle and Base
    needle_color = STYLE["WARN"] if speed_kmh > max_speed_kmh * 0.75 else STYLE["TEXT_MAIN"]
    pygame.draw.line(surface, needle_color, (speedo_cx, speedo_cy), (needle_x, needle_y), 3)
    pygame.draw.circle(surface, STYLE["ACTIVE"], (speedo_cx, speedo_cy), 6)
    
    # Current Speed Text
    speed_surf = font.render(f"{speed_kmh} {tr('vehicle', 'km/h')}", True, needle_color)
    surface.blit(speed_surf, speed_surf.get_rect(center=(speedo_cx, speedo_cy + 20)))

    # ==========================================
    # --- 3. RIGHT COLUMN: STATUSES ---
    # ==========================================
    
    # Cache icons to prevent reloading every frame
    if 'status_icons' not in modal:
        modal['status_icons'] = {}
        icon_paths = {
            'motor': 'game/lib/sprites/items/car_motor.png',
            'fuel': 'game/lib/sprites/items/car_fuel_unit.png',
            'battery': 'game/lib/sprites/items/car_battery.png'
        }
        for key, path in icon_paths.items():
            try:
                img = pygame.image.load(path).convert_alpha()
                modal['status_icons'][key] = pygame.transform.scale(img, (26, 26))
            except Exception as e:
                print(f"Error loading {key} icon: {e}")
                modal['status_icons'][key] = None

    # Motor Data
    motor_item = vehicle.equipment.get('motor')
    motor_val, motor_max = 0.0, 100.0
    if motor_item:
        if hasattr(motor_item, 'load') and motor_item.load is not None:
             motor_val, motor_max = float(motor_item.load), float(getattr(motor_item, 'capacity', 100.0))
        elif hasattr(motor_item, 'durability') and motor_item.durability is not None:
             motor_val, motor_max = float(motor_item.durability), float(getattr(motor_item, 'max_durability', 100.0))
    motor_pct = int((motor_val / motor_max * 100) if motor_max > 0 else 0)

    # Battery Data
    batt_item = vehicle.equipment.get('battery')
    batt_val, batt_max = 0.0, 100.0
    if batt_item:
        if hasattr(batt_item, 'durability') and batt_item.durability is not None:
             batt_val, batt_max = float(batt_item.durability), float(getattr(batt_item, 'max_durability', 100.0))
        elif hasattr(batt_item, 'load') and batt_item.load is not None:
             batt_val, batt_max = float(batt_item.load), float(getattr(batt_item, 'capacity', 100.0))
    batt_pct = int((batt_val / batt_max * 100) if batt_max > 0 else 0)

    # Fuel Data
    fuel_item = vehicle.equipment.get('fuel')
    fuel_val, fuel_max = 0.0, 100.0
    if fuel_item:
        if hasattr(fuel_item, 'load'): fuel_val = float(fuel_item.load)
        if hasattr(fuel_item, 'capacity'): fuel_max = float(fuel_item.capacity)

    # Text rendering
    m_txt = font.render(f"{motor_pct}%", True, STYLE["TEXT_MAIN"])
    b_txt = font.render(f"{batt_pct}%", True, STYLE["TEXT_MAIN"])
    f_txt = font.render(f"{int(fuel_val)}/{int(fuel_max)}", True, STYLE["TEXT_MAIN"])
    
    m_ico = modal['status_icons'].get('motor')
    b_ico = modal['status_icons'].get('battery')
    f_ico = modal['status_icons'].get('fuel')
    
    icon_w = 26
    inner_gap = 8
    
    ry = y_base + 10
    ry_gap = 35
    
    # Motor Block
    if m_ico: surface.blit(m_ico, (right_x, ry))
    else: pygame.draw.rect(surface, STYLE["BORDER"], (right_x, ry, icon_w, icon_w), 1)
    surface.blit(m_txt, (right_x + icon_w + inner_gap, ry + (icon_w - m_txt.get_height())//2))
    ry += ry_gap
    
    # Fuel Block
    if f_ico: surface.blit(f_ico, (right_x, ry))
    else: pygame.draw.rect(surface, STYLE["WARN"], (right_x, ry, icon_w, icon_w), 1)
    surface.blit(f_txt, (right_x + icon_w + inner_gap, ry + (icon_w - f_txt.get_height())//2))
    ry += ry_gap

    # Battery Block
    if b_ico: surface.blit(b_ico, (right_x, ry))
    else: pygame.draw.rect(surface, (0, 255, 255), (right_x, ry, icon_w, icon_w), 1)
    surface.blit(b_txt, (right_x + icon_w + inner_gap, ry + (icon_w - b_txt.get_height())//2))


def draw_vehicle_seats_tab(surface, vehicle, start_x, start_y, modal_w, mouse_pos, modal, assets):
    """
    Draws the content of the vehicle seats tab.
    """
    x = start_x + 45
    y = start_y + 7
    
    seat_size = STYLE["SLOT_SIZE"]
    seat_gap = STYLE["SLOT_GAP"]
    
    for i, occupant in enumerate(vehicle.seats):
        # Position seats in a single horizontal row
        slot_x = x + (i * (seat_size + seat_gap))
        slot_y = y 
        
        slot_rect = pygame.Rect(slot_x, slot_y, seat_size, seat_size)
        
        pygame.draw.rect(surface, STYLE["SLOT_BG"], slot_rect)
        pygame.draw.rect(surface, STYLE["BORDER"], slot_rect, 1)
        
        # Label (Driver vs Passenger)
        if i == 0:
            lbl = font_14.render(tr('vehicle', "D"), True, STYLE["DRIVER_LBL"])
            surface.blit(lbl, (slot_rect.x + 3, slot_rect.y + 3))
        else:
            lbl = font_14.render(str(i+1), True, STYLE["TEXT_DIM"])
            surface.blit(lbl, (slot_rect.x + 3, slot_rect.y + 3))

        # Render Occupant
        if occupant:
            if type(occupant).__name__ == 'Player':
                txt = font.render(tr('vehicle', "YOU"), True, (0, 255, 255))
                txt_rect = txt.get_rect(center=slot_rect.center)
                surface.blit(txt, txt_rect)
            elif hasattr(occupant, 'image') and occupant.image:
                icon = pygame.transform.scale(occupant.image, (32, 32))
                surface.blit(icon, icon.get_rect(center=slot_rect.center))
                if hasattr(occupant, 'load') and occupant.load > 1:
                     draw_text_shadow(surface, font_14, str(int(occupant.load)), STYLE["TEXT_MAIN"], 
                                    (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')

        modal['seat_rects'][i] = slot_rect

def draw_vehicle_mechanics_tab(surface, vehicle, start_x, start_y, modal_w, mouse_pos, modal, assets):
    """
    Draws the content of the vehicle mechanics tab (Equipment Slots).
    """
    x = start_x + 45
    y = start_y + 7

    # Equipment Slots
    slots_row_1 = ['motor','key', 'fuel', 'battery']
    slots_row_2 = ['tire_fl', 'tire_fr', 'tire_bl', 'tire_br']
    slot_size = STYLE["SLOT_SIZE"]
    slot_gap = STYLE["SLOT_GAP"]
    
    # Draw Row 1
    current_x = x
    for slot_name in slots_row_1:
        slot_rect = pygame.Rect(current_x, y, slot_size, slot_size)
        
        pygame.draw.rect(surface, STYLE["SLOT_BG"], slot_rect)
        pygame.draw.rect(surface, STYLE["BORDER"], slot_rect, 1)
        
        lbl_text = tr('vehicle', slot_name.capitalize())
        lbl = font_14.render(lbl_text, True, STYLE["TEXT_DIM"])
        surface.blit(lbl, lbl.get_rect(midtop=(slot_rect.centerx, slot_rect.top - 14)))
        
        item = vehicle.equipment.get(slot_name)
        if item:
             if getattr(item, 'image', None):
                 icon = pygame.transform.scale(item.image, (32, 32))
                 surface.blit(icon, icon.get_rect(center=slot_rect.center))
             if hasattr(item, 'load') and item.load is not None and item.load > 0:
                 draw_text_shadow(surface, font_14, str(int(item.load)), STYLE["TEXT_MAIN"], 
                                (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')

        modal['equipment_rects'][slot_name] = slot_rect
        current_x += slot_size + slot_gap

    # Draw Row 2 (Tires)
    current_x = x
    y += slot_size + 35 # Move down for the next row
    for slot_name in slots_row_2:
        slot_rect = pygame.Rect(current_x, y, slot_size, slot_size)
        
        pygame.draw.rect(surface, STYLE["SLOT_BG"], slot_rect)
        pygame.draw.rect(surface, STYLE["BORDER"], slot_rect, 1)
        
        # Format "tire_fl" -> "FL TIRE", etc.
        lbl_text = slot_name.split('_')[1].upper() + " " + tr('vehicle', 'TIRE')
        lbl = font_14.render(lbl_text, True, STYLE["TEXT_DIM"])
        surface.blit(lbl, lbl.get_rect(midtop=(slot_rect.centerx, slot_rect.top - 14)))
        
        item = vehicle.equipment.get(slot_name)
        if item:
             if getattr(item, 'image', None):
                 icon = pygame.transform.scale(item.image, (32, 32))
                 surface.blit(icon, icon.get_rect(center=slot_rect.center))
             if hasattr(item, 'durability') and item.durability is not None and item.durability > 0:
                 draw_text_shadow(surface, font_14, str(int(item.durability)), STYLE["TEXT_MAIN"], 
                                (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')

        modal['equipment_rects'][slot_name] = slot_rect
        current_x += slot_size + slot_gap


def draw_vehicle_modal(surface, game, modal, assets, mouse_pos):
    vehicle = modal['vehicle']
    base_modal = BaseModal(surface, modal, assets, vehicle.name)
    base_modal.draw_base()
    
    close_btn, min_btn = base_modal.get_buttons()
    if base_modal.minimized: return [close_btn, min_btn]

    # Initialize tabs data if not already set (Added 'Seats')
    tabs_data = [
        {'label': 'Vehicle', 'icon': assets.get('vehicle_icon')},
        {'label': 'Mechanics', 'icon': assets.get('mechanics_icon')},
        {'label': 'Seats', 'icon': assets.get('seats_icon')}
    ]
    
    if 'active_tab' not in modal or modal['active_tab'] not in ['Vehicle', 'Mechanics', 'Seats']:
        modal['active_tab'] = 'Vehicle'
        
    # Draw Tabs
    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw(game, mouse_pos)

    # Shift content down to account for the tab bar height (roughly 30px)
    content_y = base_modal.modal_y + STYLE["MARGIN_TOP"] + 30
    content_x = base_modal.modal_x + STYLE["MARGIN_LEFT"]
    
    # Clean up old rects to avoid ghost clicks/interactions across tabs
    modal['seat_rects'] = {}
    modal['equipment_rects'] = {}
    modal.setdefault('rects', {})
    
    active_tab = modal.get('active_tab')
    
    # Route drawing logic based on the active tab
    if active_tab == 'Vehicle':
        draw_vehicle_info_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)
    elif active_tab == 'Mechanics':
        draw_vehicle_mechanics_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)
    elif active_tab == 'Seats':
        draw_vehicle_seats_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)
    
    # Draw hover tooltips for equipment
    if 'equipment_rects' in modal:
        for slot_name, rect in modal['equipment_rects'].items():
            if rect.collidepoint(mouse_pos):
                # Retrieve the actual item object from the vehicle's equipment
                item = vehicle.equipment.get(slot_name)
                if item:
                    draw_tooltip(surface, item, mouse_pos)

    return [close_btn, min_btn]