import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.inventory_modal import draw_text_shadow

# --- CONFIGURATION: LAYOUT & COLORS ---
STYLE = {
    # -- Dimensions & Spacing --
    "MARGIN_TOP": 45,        # Distance from top of modal window
    "MARGIN_LEFT": 15,       # Distance from left of modal window
    "COL_2_OFFSET": 230,     # Horizontal distance to the 'Seats' column
    
    "SECTION_SPACING": 35,   # Vertical gap between main sections (e.g., Header -> Stats)
    "TITLE_SPACING": 15,      # Gap between a Section Title (e.g. "Status:") and its content
    
    # -- Sizing --
    "BAR_WIDTH": 100,        # Width of the health/fuel/etc bars
    "BAR_HEIGHT": 8,         # Thickness of the bars
    "SLOT_SIZE": 48,         # Size of Equipment/Seat squares
    "SLOT_GAP": 25,          # Gap between equipment slots
    "SEAT_GAP": 20,          # Gap between seat slots
    
    # -- Colors --
    "TEXT_MAIN": WHITE,
    "TEXT_DIM": GRAY,        # Used for labels and seat numbers
    "ACTIVE": GREEN,         # Color when car is ON
    "INACTIVE": RED,         # Color when car is OFF / Damaged
    "WARN": ORANGE,          # Warning color (low fuel/high speed)
    "BAR_BG": (40, 40, 40),  # Dark background for empty part of bars
    "SLOT_BG": (30, 30, 30), # Background for item/seat slots
    "BORDER": GRAY,          # Border color for slots
    "DRIVER_LBL": YELLOW,    # Special color for the Driver label
    "TRUNK_BAR": BLUE        # Color for the Trunk bar
}

def draw_vehicle_info_tab(surface, vehicle, start_x, start_y, modal_w, mouse_pos, modal, assets):
    """
    Draws the content of the vehicle tab using the STYLE configuration.
    """
    x = start_x
    y = start_y
    
    # --- 1. HEADER SECTION (State & Speed) ---
    car_state = "ON" if vehicle.active else "OFF"
    state_color = STYLE["ACTIVE"] if vehicle.active else STYLE["INACTIVE"]
    
    # Draw State
    state_surf = font.render(f"Car (Press: Q): {car_state}", True, state_color)
    surface.blit(state_surf, (x, y))

    # Draw Speed
    speed_kmh = int(vehicle.current_speed_val * 10)
    speed_color = STYLE["TEXT_MAIN"]
    if speed_kmh > 50: speed_color = STYLE["WARN"]
    if speed_kmh > 90: speed_color = STYLE["INACTIVE"]
    
    speed_surf = font.render(f"{speed_kmh} km/h", True, speed_color)
    surface.blit(speed_surf, (x + 160, y))

    # Move Y down for the next main section
    y += STYLE["SECTION_SPACING"]
    
    
    # --- 2. COLUMNS SETUP ---
    col1_x = x
    col2_x = x + STYLE["COL_2_OFFSET"]
    
    # Define vertical start for columns (Header text + Spacing)
    # We render titles first, then apply TITLE_SPACING
    
    
    # --- LEFT COLUMN: STATS ---
    # 1. Title
    surface.blit(font.render("Status:", True, STYLE["TEXT_MAIN"]), (col1_x, y))
    
    # 2. Content Start Y
    current_stat_y = y + 20 + STYLE["TITLE_SPACING"] # 20 is approx height of font

    # Helper function for bars
    def draw_stat_bar(label, val, max_val, current_y, fill_color=STYLE["ACTIVE"]):
        safe_val = max(0, min(val, max_val))
        
        # Label
        label_str = f"{label}: {int(safe_val)}/{int(max_val)}"
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
        
        return current_y + 20 # Return new Y position

    # Draw Stats
    stats_y = current_stat_y
    stats_y = draw_stat_bar("Health", vehicle.health, 100.0, stats_y, STYLE["INACTIVE"])
    
    gas_item = vehicle.equipment.get('fuel')
    max_fuel = float(gas_item.capacity) if gas_item and hasattr(gas_item, 'capacity') else 25.0
    stats_y = draw_stat_bar("Fuel", vehicle.fuel, max_fuel, stats_y, STYLE["WARN"])

    batt_item = vehicle.equipment.get('battery')
    max_batt = float(batt_item.max_durability) if batt_item and hasattr(batt_item, 'max_durability') else 100.0
    stats_y = draw_stat_bar("Battery", vehicle.battery, max_batt, stats_y, (0, 255, 255))

    motor_item = vehicle.equipment.get('motor')
    motor_val = vehicle.motor * 100
    stats_y = draw_stat_bar("Motor", motor_val, 100.0, stats_y)

    trunk_val = len(vehicle.inventory) if hasattr(vehicle, 'inventory') else 0
    trunk_cap = vehicle.capacity if hasattr(vehicle, 'capacity') else 20
    stats_y = draw_stat_bar("Trunk", trunk_val, trunk_cap, stats_y, STYLE["TRUNK_BAR"])


    # --- RIGHT COLUMN: SEATS ---
    # 1. Title (Aligned with Status title)
    surface.blit(font.render("Seats:", True, STYLE["TEXT_MAIN"]), (col2_x, y))
    
    # 2. Grid Content Start
    seats_y = y + 20 + STYLE["TITLE_SPACING"]
    
    modal['seat_rects'] = {} 
    seat_size = STYLE["SLOT_SIZE"]
    seat_gap = STYLE["SEAT_GAP"]
    
    for i, occupant in enumerate(vehicle.seats):
        row = i // 2
        col = i % 2
        
        slot_x = col2_x + (col * (seat_size + seat_gap))
        slot_y = seats_y + (row * (seat_size + seat_gap))
        
        slot_rect = pygame.Rect(slot_x, slot_y, seat_size, seat_size)
        
        # Background
        pygame.draw.rect(surface, STYLE["SLOT_BG"], slot_rect)
        pygame.draw.rect(surface, STYLE["BORDER"], slot_rect, 1)
        
        # --- SEAT NUMBER / DRIVER LBL ---
        # Logic: If seat 0, show "Driver" (maybe small text inside or just 'D'?)
        # User requested numbers inside.
        if i == 0:
            # Special case for driver, keep it clear
            lbl = font_notification.render("D", True, STYLE["DRIVER_LBL"])
            surface.blit(lbl, (slot_rect.x + 3, slot_rect.y + 3))
        else:
            # Regular seats: Number inside, top-left
            lbl = font_notification.render(str(i+1), True, STYLE["TEXT_DIM"])
            surface.blit(lbl, (slot_rect.x + 3, slot_rect.y + 3))

        # --- OCCUPANT ---
        if occupant:
            if type(occupant).__name__ == 'Player':
                txt = font.render("YOU", True, (0, 255, 255))
                txt_rect = txt.get_rect(center=slot_rect.center)
                surface.blit(txt, txt_rect)
            elif hasattr(occupant, 'image') and occupant.image:
                icon = pygame.transform.scale(occupant.image, (32, 32))
                surface.blit(icon, icon.get_rect(center=slot_rect.center))
                # Stack size
                if hasattr(occupant, 'load') and occupant.load > 1:
                     draw_text_shadow(surface, font_small, str(int(occupant.load)), STYLE["TEXT_MAIN"], 
                                    (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')

        modal['seat_rects'][i] = slot_rect

    # Calculate height used by seats
    rows_used = (len(vehicle.seats) + 1) // 2
    seats_height = rows_used * (seat_size + seat_gap)
    seats_end_y = seats_y + seats_height


    # --- BOTTOM SECTION: LIGHTS & EQUIPMENT ---
    # Start below the lowest column + spacing
    y = max(stats_y, seats_end_y) + STYLE["SECTION_SPACING"]

    # 1. Lights Title & Controls
    surface.blit(font.render("Lights:", True, STYLE["TEXT_MAIN"]), (x, y))
    
    # Controls (Placed to the right of the title)
    is_on = getattr(vehicle, 'lights', 'off') == 'on'
    
    on_color = STYLE["TEXT_MAIN"] if is_on else STYLE["TEXT_DIM"]
    off_color = STYLE["TEXT_DIM"] if is_on else STYLE["TEXT_MAIN"]
    
    on_txt = font.render("[ON]", True, on_color)
    off_txt = font.render("[OFF]", True, off_color)
    
    # Position: Title X + ~70px
    on_rect = on_txt.get_rect(topleft=(x + 70, y))
    off_rect = off_txt.get_rect(topleft=(on_rect.right + 10, y))
    
    surface.blit(on_txt, on_rect)
    surface.blit(off_txt, off_rect)
    modal['rects'] = {'lights_on': on_rect, 'lights_off': off_rect}
    
    # Move down for Equipment
    y += 20 + STYLE["TITLE_SPACING"] # 20 is approx height of lights text

    # 2. Equipment Slots
    slots = ['motor','key', 'fuel', 'battery']
    slot_size = STYLE["SLOT_SIZE"]
    slot_gap = STYLE["SLOT_GAP"]
    current_x = x
    modal['equipment_rects'] = {}
    
    for slot_name in slots:
        slot_rect = pygame.Rect(current_x, y, slot_size, slot_size)
        
        # Draw Box
        pygame.draw.rect(surface, STYLE["SLOT_BG"], slot_rect)
        pygame.draw.rect(surface, STYLE["BORDER"], slot_rect, 1)
        
        # Label (centered above or inside? User didn't specify, but "inside" was for seats. 
        # Keeping equipment labels outside/above is cleaner for text like "Battery")
        lbl = font_notification.render(slot_name.capitalize(), True, STYLE["TEXT_DIM"])
        surface.blit(lbl, lbl.get_rect(midtop=(slot_rect.centerx, slot_rect.top - 14)))
        
        # Item Icon
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

def draw_vehicle_modal(surface, game, modal, assets, mouse_pos):
    vehicle = modal['vehicle']
    base_modal = BaseModal(surface, modal, assets, vehicle.name)
    base_modal.draw_base()
    
    close_btn, min_btn = base_modal.get_buttons()
    if base_modal.minimized: return [close_btn, min_btn]

    # Apply Margins
    content_y = base_modal.modal_y + STYLE["MARGIN_TOP"]
    content_x = base_modal.modal_x + STYLE["MARGIN_LEFT"]
    
    draw_vehicle_info_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)
        
    return [close_btn, min_btn]