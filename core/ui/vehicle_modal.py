import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.inventory_modal import draw_text_shadow

def draw_vehicle_info_tab(surface, vehicle, start_x, start_y, modal_w, mouse_pos, modal, assets):
    
    y_offset = start_y
    
    # 1. Car State & Speed (Keep at top)
    car_state = "On" if vehicle.active else "Off"
    col = GREEN if vehicle.active else RED
    state_text = font.render(f"Car: {car_state}", True, col)
    surface.blit(state_text, (start_x, y_offset))

    speed_kmh = int(vehicle.current_speed_val * 10)
    speed_col = WHITE
    if speed_kmh > 50: speed_col = ORANGE
    if speed_kmh > 90: speed_col = RED
    
    speed_text = font.render(f"Speed: {speed_kmh} km/h", True, speed_col)
    surface.blit(speed_text, (start_x + 160, y_offset))

    
    # --- COLUMNS START ---
    y_offset += 35 
    
    # Column X positions
    col1_x = start_x
    col2_x = start_x + 230  # Second column for Seats
    
    # --- LEFT COLUMN: STATS ---
    
    # Header
    status_lbl = font.render("Status:", True, WHITE)
    surface.blit(status_lbl, (col1_x, y_offset - 20))

    # Helper for stat bars
    def draw_stat_bar(label, val, max_val, y, bar_col=GREEN):
        safe_val = max(0, min(val, max_val))
        label_str = f"{label}: {int(safe_val)}/{int(max_val)}"
        label_surf = font_notification.render(label_str, True, GRAY)
        surface.blit(label_surf, (col1_x, y))
        
        bar_x = col1_x + 100
        bar_w = 100 
        bar_h = 8
        fill_pct = safe_val / max_val if max_val > 0 else 0
        
        pygame.draw.rect(surface, (40,40,40), (bar_x, y + 4, bar_w, bar_h))
        fill_w = int(bar_w * fill_pct)
        if fill_w > 0:
            pygame.draw.rect(surface, bar_col, (bar_x, y + 4, fill_w, bar_h))
        pygame.draw.rect(surface, WHITE, (bar_x, y + 4, bar_w, bar_h), 1)
        return y + 20

    current_stat_y = y_offset
    current_stat_y = draw_stat_bar("Health", vehicle.health, 100.0, current_stat_y, RED)
    
    gas_item = vehicle.equipment.get('fuel')
    max_fuel = float(gas_item.capacity) if gas_item and hasattr(gas_item, 'capacity') else 25.0
    current_stat_y = draw_stat_bar("Fuel", vehicle.fuel, max_fuel, current_stat_y, (255, 165, 0))

    batt_item = vehicle.equipment.get('battery')
    max_batt = float(batt_item.max_durability) if batt_item and hasattr(batt_item, 'max_durability') else 100.0
    current_stat_y = draw_stat_bar("Battery", vehicle.battery, max_batt, current_stat_y, (0, 255, 255))

    motor_item = vehicle.equipment.get('motor')
    motor_val = vehicle.motor * 100
    motor_max = 100.0 
    current_stat_y = draw_stat_bar("Motor", motor_val, motor_max, current_stat_y)

    # Added Trunk/Storage Stat
    trunk_val = len(vehicle.inventory) if hasattr(vehicle, 'inventory') else 0
    trunk_cap = vehicle.capacity if hasattr(vehicle, 'capacity') else 20
    current_stat_y = draw_stat_bar("Trunk", trunk_val, trunk_cap, current_stat_y, BLUE)


    # --- RIGHT COLUMN: SEATS ---
    
    seat_y = y_offset
    seats_lbl = font.render("Seats:", True, WHITE)
    surface.blit(seats_lbl, (col2_x, seat_y - 20)) 
    
    seat_slot_size = 48
    seat_gap = 10
    
    modal['seat_rects'] = {} # Initialize rects for mouse interaction
    
    # Calculate rows needed
    rows_used = (len(vehicle.seats) + 1) // 2
    seats_height = rows_used * (seat_slot_size + seat_gap)
    current_seat_y_end = seat_y + seats_height

    # Draw Grid
    for i, occupant in enumerate(vehicle.seats):
        row = i // 2
        col = i % 2
        
        sx = col2_x + (col * (seat_slot_size + seat_gap))
        sy = seat_y + (row * (seat_slot_size + seat_gap))
        
        slot_rect = pygame.Rect(sx, sy, seat_slot_size, seat_slot_size)
        pygame.draw.rect(surface, (30,30,30), slot_rect)
        pygame.draw.rect(surface, GRAY, slot_rect, 1)
        
        # Label Seat 0 as Driver
        if i == 0:
            lbl = font_notification.render("Driver", True, YELLOW)
            surface.blit(lbl, (sx, sy - 12))
        else:
            lbl = font_notification.render(f"{i+1}", True, GRAY)
            surface.blit(lbl, (sx, sy - 12))

        # Draw Occupant
        if occupant:
            if type(occupant).__name__ == 'Player':
                # Draw Player indicator
                text_p = font.render("PLY", True, (0, 255, 255))
                text_rect = text_p.get_rect(center=slot_rect.center)
                surface.blit(text_p, text_rect)
            elif hasattr(occupant, 'image'):
                # Draw Item
                if occupant.image:
                    icon = pygame.transform.scale(occupant.image, (32, 32))
                    icon_rect = icon.get_rect(center=slot_rect.center)
                    surface.blit(icon, icon_rect)
                
                # Draw stack count
                if hasattr(occupant, 'load') and occupant.load > 1:
                     draw_text_shadow(surface, font_small, str(int(occupant.load)), WHITE, (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')

        modal['seat_rects'][i] = slot_rect

    # --- BOTTOM SECTION: LIGHTS & EQUIPMENT ---
    y_offset = max(current_stat_y, current_seat_y_end) + 20

    # 3. Lights
    lights_lbl = font.render("Lights:", True, WHITE)
    surface.blit(lights_lbl, (start_x, y_offset))
    is_on = getattr(vehicle, 'lights', 'off') == 'on'
    on_txt = font.render("[ON]", True, WHITE if is_on else GRAY)
    off_txt = font.render("[OFF]", True, GRAY if is_on else WHITE)
    on_rect = on_txt.get_rect(topleft=(start_x + 70, y_offset))
    off_rect = off_txt.get_rect(topleft=(on_rect.right + 10, y_offset))
    surface.blit(on_txt, on_rect); surface.blit(off_txt, off_rect)
    modal['rects'] = {'lights_on': on_rect, 'lights_off': off_rect}
    
    y_offset += 35 # Reduced spacing slightly

    # 4. Equipment Slots
    slots = ['motor','key', 'fuel', 'battery']
    slot_size = 48; gap = 15; current_slot_x = start_x
    modal['equipment_rects'] = {}
    
    for slot_name in slots:
        slot_rect = pygame.Rect(current_slot_x, y_offset, slot_size, slot_size)
        pygame.draw.rect(surface, (30,30,30), slot_rect)
        pygame.draw.rect(surface, GRAY, slot_rect, 1)
        lbl = font_notification.render(slot_name.capitalize(), True, GRAY)
        surface.blit(lbl, lbl.get_rect(midtop=(slot_rect.centerx, slot_rect.bottom + 2)))
        
        item = vehicle.equipment.get(slot_name)
        if item:
             if getattr(item, 'image', None):
                 icon = pygame.transform.scale(item.image, (32, 32))
                 surface.blit(icon, icon.get_rect(center=slot_rect.center))
             if hasattr(item, 'load') and item.load is not None and item.load > 0:
                 draw_text_shadow(surface, font_small, str(int(item.load)), WHITE, (slot_rect.right - 2, slot_rect.bottom - 2), align='bottomright')

        modal['equipment_rects'][slot_name] = slot_rect
        current_slot_x += slot_size + gap
        
def draw_vehicle_modal(surface, game, modal, assets, mouse_pos):
    vehicle = modal['vehicle']
    base_modal = BaseModal(surface, modal, assets, vehicle.name)
    base_modal.draw_base()
    
    close_btn, min_btn = base_modal.get_buttons()
    if base_modal.minimized: return [close_btn, min_btn]

    # [FIX] Start content higher (45 instead of 65) to fit all elements within 320px height
    content_y = base_modal.modal_y + 45 
    content_x = base_modal.modal_x + 15
    
    draw_vehicle_info_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)
        
    return [close_btn, min_btn]