import pygame
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
    Draws the content of the vehicle info tab (Condition, Stats, Seats).
    """
    x = start_x
    y = start_y
    
    # --- 1. HEADER SECTION (Engine, Lights, & Speed) ---
    
    # Engine
    surface.blit(font.render(tr('vehicle', "Engine:"), True, STYLE["TEXT_MAIN"]), (x, y))
    is_engine_on = vehicle.active
    e_on_color = STYLE["TEXT_MAIN"] if is_engine_on else STYLE["TEXT_DIM"]
    e_off_color = STYLE["TEXT_DIM"] if is_engine_on else STYLE["TEXT_MAIN"]
    
    e_on_txt = font.render(tr('vehicle', "[ON]"), True, e_on_color)
    e_off_txt = font.render(tr('vehicle', "[OFF]"), True, e_off_color)
    
    e_on_rect = e_on_txt.get_rect(topleft=(x + 70, y))
    e_off_rect = e_off_txt.get_rect(topleft=(e_on_rect.right + 10, y))
    
    surface.blit(e_on_txt, e_on_rect)
    surface.blit(e_off_txt, e_off_rect)

    # Draw Speed
    speed_kmh = int(vehicle.current_speed_val * 10)
    speed_color = STYLE["TEXT_MAIN"]
    if speed_kmh > 50: speed_color = STYLE["WARN"]
    if speed_kmh > 90: speed_color = STYLE["INACTIVE"]
    
    speed_surf = font.render(f"{tr('vehicle', 'Speed:')} {speed_kmh} {tr('vehicle', 'km/h')}", True, speed_color)
    surface.blit(speed_surf, (x + 180, y))

    y += 25 
    
    # Lights
    surface.blit(font.render(tr('vehicle', "Lights:"), True, STYLE["TEXT_MAIN"]), (x, y))
    is_lights_on = getattr(vehicle, 'lights', 'off') == 'on'
    
    l_on_color = STYLE["TEXT_MAIN"] if is_lights_on else STYLE["TEXT_DIM"]
    l_off_color = STYLE["TEXT_DIM"] if is_lights_on else STYLE["TEXT_MAIN"]
    
    l_on_txt = font.render(tr('vehicle', "[ON]"), True, l_on_color)
    l_off_txt = font.render(tr('vehicle', "[OFF]"), True, l_off_color)
    
    l_on_rect = l_on_txt.get_rect(topleft=(x + 70, y))
    l_off_rect = l_off_txt.get_rect(topleft=(l_on_rect.right + 10, y))
    
    surface.blit(l_on_txt, l_on_rect)
    surface.blit(l_off_txt, l_off_rect)
    
    # Store rects for click handling
    modal['rects'] = {
        'engine_on': e_on_rect,
        'engine_off': e_off_rect,
        'lights_on': l_on_rect,
        'lights_off': l_off_rect
    }

    y += STYLE["SECTION_SPACING"] - 5
    
    # --- 2. COLUMNS SETUP ---
    col1_x = x
    col2_x = x + STYLE["COL_2_OFFSET"]
    
    # --- LEFT COLUMN: STATS ---
    surface.blit(font.render(tr('vehicle', "Status:"), True, STYLE["TEXT_MAIN"]), (col1_x, y))
    
    current_stat_y = y + 20 + STYLE["TITLE_SPACING"] 

    def draw_stat_bar(label, val, max_val, current_y, fill_color=STYLE["ACTIVE"]):
        safe_val = max(0, min(val, max_val))
        
        # Label
        label_str = f"{tr('vehicle', label)}: {int(safe_val)}/{int(max_val)}"
        surface.blit(font_notification.render(label_str, True, STYLE["TEXT_DIM"]), (col1_x, current_y))
        
        # Bar Background
        bar_x = col1_x + 100 
        bar_rect = (bar_x, current_y + 4, STYLE["BAR_WIDTH"], STYLE["BAR_HEIGHT"])
        pygame.draw.rect(surface, STYLE["BAR_BG"], bar_rect)
        
        # Bar Fill
        fill_pct = safe_val / max_val if max_val > 0 else 0
        fill_width = int(STYLE["BAR_WIDTH"] * fill_pct)
        if fill_width > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, current_y + 4, fill_width, STYLE["BAR_HEIGHT"]))
            
        # Border
        pygame.draw.rect(surface, STYLE["TEXT_MAIN"], bar_rect, 1)
        
        return current_y + 20 

    stats_y = current_stat_y
    
    # Fuel
    fuel_item = vehicle.equipment.get('fuel')
    fuel_val = 0.0
    fuel_max = 100.0
    if fuel_item:
        if hasattr(fuel_item, 'load'): fuel_val = float(fuel_item.load)
        if hasattr(fuel_item, 'capacity'): fuel_max = float(fuel_item.capacity)
    stats_y = draw_stat_bar("Fuel", fuel_val, fuel_max, stats_y, STYLE["WARN"])

    # Battery
    batt_item = vehicle.equipment.get('battery')
    batt_val = 0.0
    batt_max = 100.0
    if batt_item:
        if hasattr(batt_item, 'durability') and batt_item.durability is not None:
             batt_val = float(batt_item.durability)
             if hasattr(batt_item, 'max_durability'): batt_max = float(batt_item.max_durability)
        elif hasattr(batt_item, 'load') and batt_item.load is not None:
             batt_val = float(batt_item.load)
             if hasattr(batt_item, 'capacity'): batt_max = float(batt_item.capacity)
    stats_y = draw_stat_bar("Battery", batt_val, batt_max, stats_y, (0, 255, 255))

    # Motor
    motor_item = vehicle.equipment.get('motor')
    motor_val = 0.0
    motor_max = 100.0
    if motor_item:
        if hasattr(motor_item, 'load') and motor_item.load is not None:
             motor_val = float(motor_item.load)
             if hasattr(motor_item, 'capacity'): motor_max = float(motor_item.capacity)
        elif hasattr(motor_item, 'durability') and motor_item.durability is not None:
             motor_val = float(motor_item.durability)
             if hasattr(motor_item, 'max_durability'): motor_max = float(motor_item.max_durability)
    stats_y = draw_stat_bar("Motor", motor_val, motor_max, stats_y)

    trunk_val = len(vehicle.inventory) if hasattr(vehicle, 'inventory') else 0
    trunk_cap = vehicle.capacity if hasattr(vehicle, 'capacity') else 20
    stats_y = draw_stat_bar("Trunk", trunk_val, trunk_cap, stats_y, STYLE["TRUNK_BAR"])

    # --- RIGHT COLUMN: SEATS ---
    surface.blit(font.render(tr('vehicle', "Seats:"), True, STYLE["TEXT_MAIN"]), (col2_x, y))
    
    seats_y = y + 20 + STYLE["TITLE_SPACING"]
    
    seat_size = STYLE["SLOT_SIZE"]
    seat_gap = STYLE["SEAT_GAP"]
    
    for i, occupant in enumerate(vehicle.seats):
        row = i // 2
        col = i % 2
        
        slot_x = col2_x + (col * (seat_size + seat_gap))
        slot_y = seats_y + (row * (seat_size + seat_gap))
        
        slot_rect = pygame.Rect(slot_x, slot_y, seat_size, seat_size)
        
        pygame.draw.rect(surface, STYLE["SLOT_BG"], slot_rect)
        pygame.draw.rect(surface, STYLE["BORDER"], slot_rect, 1)
        
        if i == 0:
            lbl = font_notification.render(tr('vehicle', "D"), True, STYLE["DRIVER_LBL"])
            surface.blit(lbl, (slot_rect.x + 3, slot_rect.y + 3))
        else:
            lbl = font_notification.render(str(i+1), True, STYLE["TEXT_DIM"])
            surface.blit(lbl, (slot_rect.x + 3, slot_rect.y + 3))

        if occupant:
            if type(occupant).__name__ == 'Player':
                txt = font.render(tr('vehicle', "YOU"), True, (0, 255, 255))
                txt_rect = txt.get_rect(center=slot_rect.center)
                surface.blit(txt, txt_rect)
            elif hasattr(occupant, 'image') and occupant.image:
                icon = pygame.transform.scale(occupant.image, (32, 32))
                surface.blit(icon, icon.get_rect(center=slot_rect.center))
                if hasattr(occupant, 'load') and occupant.load > 1:
                     draw_text_shadow(surface, font_small, str(int(occupant.load)), STYLE["TEXT_MAIN"], 
                                    (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')

        modal['seat_rects'][i] = slot_rect

def draw_vehicle_mechanics_tab(surface, vehicle, start_x, start_y, modal_w, mouse_pos, modal, assets):
    """
    Draws the content of the vehicle mechanics tab (Equipment Slots).
    """
    x = start_x + 45
    y = start_y + 35

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
        lbl = font_notification.render(lbl_text, True, STYLE["TEXT_DIM"])
        surface.blit(lbl, lbl.get_rect(midtop=(slot_rect.centerx, slot_rect.top - 14)))
        
        item = vehicle.equipment.get(slot_name)
        if item:
             if getattr(item, 'image', None):
                 icon = pygame.transform.scale(item.image, (32, 32))
                 surface.blit(icon, icon.get_rect(center=slot_rect.center))
             if hasattr(item, 'load') and item.load is not None and item.load > 0:
                 draw_text_shadow(surface, font_small, str(int(item.load)), STYLE["TEXT_MAIN"], 
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
        lbl = font_notification.render(lbl_text, True, STYLE["TEXT_DIM"])
        surface.blit(lbl, lbl.get_rect(midtop=(slot_rect.centerx, slot_rect.top - 14)))
        
        item = vehicle.equipment.get(slot_name)
        if item:
             if getattr(item, 'image', None):
                 icon = pygame.transform.scale(item.image, (32, 32))
                 surface.blit(icon, icon.get_rect(center=slot_rect.center))
             if hasattr(item, 'durability') and item.durability is not None and item.durability > 0:
                 draw_text_shadow(surface, font_small, str(int(item.durability)), STYLE["TEXT_MAIN"], 
                                (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')

        modal['equipment_rects'][slot_name] = slot_rect
        current_x += slot_size + slot_gap


def draw_vehicle_modal(surface, game, modal, assets, mouse_pos):
    vehicle = modal['vehicle']
    base_modal = BaseModal(surface, modal, assets, vehicle.name)
    base_modal.draw_base()
    
    close_btn, min_btn = base_modal.get_buttons()
    if base_modal.minimized: return [close_btn, min_btn]

    # Initialize tabs data if not already set
    tabs_data = [
        {'label': tr('tab', 'Info')},
        {'label': tr('tab', 'Mechanics')}
    ]
    
    if 'active_tab' not in modal:
        modal['active_tab'] = tr('tab', 'Info')
        
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
    
    if active_tab == tr('tab', 'Info'):
        draw_vehicle_info_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)
    elif active_tab == tr('tab', 'Mechanics'):
        draw_vehicle_mechanics_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)
    
    if 'equipment_rects' in modal:
        for slot_name, rect in modal['equipment_rects'].items():
            if rect.collidepoint(mouse_pos):
                # Retrieve the actual item object from the vehicle's equipment
                item = vehicle.equipment.get(slot_name)
                if item:
                    draw_tooltip(surface, item, mouse_pos)

    return [close_btn, min_btn]