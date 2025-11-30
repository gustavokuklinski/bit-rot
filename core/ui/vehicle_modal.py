import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs
from core.ui.inventory_modal import draw_text_shadow

def draw_vehicle_info_tab(surface, vehicle, start_x, start_y, modal_w, mouse_pos, modal, assets):
    
    y_offset = start_y
    
    # 1. Car State
    car_state = "On" if vehicle.active else "Off"
    col = GREEN if vehicle.active else RED
    state_text = font.render(f"Car: {car_state}", True, col)
    surface.blit(state_text, (start_x, y_offset))
    y_offset += 25

    # 2. Stats Bars
    def draw_stat_bar(label, val, max_val, y, bar_col=GREEN):
        safe_val = max(0, min(val, max_val))
        
        # Display Units: 92/100
        label_str = f"{label}: {int(safe_val)}/{int(max_val)}"
        label_surf = font_notification.render(label_str, True, GRAY)
        surface.blit(label_surf, (start_x, y))
        
        bar_x = start_x + 110
        bar_w = 140
        bar_h = 8
        
        fill_pct = safe_val / max_val if max_val > 0 else 0
        
        pygame.draw.rect(surface, (40,40,40), (bar_x, y + 4, bar_w, bar_h))
        fill_w = int(bar_w * fill_pct)
        if fill_w > 0:
            pygame.draw.rect(surface, bar_col, (bar_x, y + 4, fill_w, bar_h))
        pygame.draw.rect(surface, WHITE, (bar_x, y + 4, bar_w, bar_h), 1)
        return y + 20

    # Health
    y_offset = draw_stat_bar("Health", vehicle.health, 100.0, y_offset, RED)
    
    # Fuel
    gas_item = vehicle.equipment.get('fuel')
    max_fuel = 25.0
    if gas_item and hasattr(gas_item, 'capacity') and gas_item.capacity:
        max_fuel = float(gas_item.capacity)
    y_offset = draw_stat_bar("Fuel", vehicle.fuel, max_fuel, y_offset, (255, 165, 0))

    # Battery
    batt_item = vehicle.equipment.get('battery')
    max_batt = 100.0
    if batt_item:
        # [FIX] Check max_durability first
        if hasattr(batt_item, 'max_durability') and batt_item.max_durability > 0:
            max_batt = float(batt_item.max_durability)
        elif hasattr(batt_item, 'capacity') and batt_item.capacity:
            max_batt = float(batt_item.capacity)
            
    y_offset = draw_stat_bar("Battery", vehicle.battery, max_batt, y_offset, (0, 255, 255))
    
    # Motor
    motor_item = vehicle.equipment.get('motor')
    motor_val = vehicle.motor * 100
    motor_max = 100.0
    if motor_item:
        if hasattr(motor_item, 'capacity') and motor_item.capacity:
            motor_max = float(motor_item.capacity)
            if hasattr(motor_item, 'load'):
                motor_val = float(motor_item.load)
    
    y_offset = draw_stat_bar("Motor", motor_val, motor_max, y_offset)
    y_offset += 15

    # ... (Rest of Lights/Slots/Draw code remains unchanged) ...
    # 3. Lights
    lights_lbl = font.render("Lights:", True, WHITE)
    surface.blit(lights_lbl, (start_x, y_offset))
    
    is_on = getattr(vehicle, 'lights', 'off') == 'on'
    on_txt = font.render("[ON]", True, WHITE if is_on else GRAY)
    off_txt = font.render("[OFF]", True, GRAY if is_on else WHITE)
    
    on_rect = on_txt.get_rect(topleft=(start_x + 70, y_offset))
    off_rect = off_txt.get_rect(topleft=(on_rect.right + 10, y_offset))
    
    surface.blit(on_txt, on_rect)
    surface.blit(off_txt, off_rect)
    
    modal['rects'] = {'lights_on': on_rect, 'lights_off': off_rect}
    y_offset += 40

    # 4. Equipment Slots
    slots = ['motor','key', 'fuel', 'battery']
    slot_size = 48
    gap = 15
    current_slot_x = start_x
    
    modal['equipment_rects'] = {}
    
    for slot_name in slots:
        slot_rect = pygame.Rect(current_slot_x, y_offset, slot_size, slot_size)
        pygame.draw.rect(surface, (30,30,30), slot_rect)
        pygame.draw.rect(surface, GRAY, slot_rect, 1)
        
        lbl = font_notification.render(slot_name.capitalize(), True, GRAY)
        text_rect = lbl.get_rect(midtop=(slot_rect.centerx, slot_rect.bottom + 2))
        surface.blit(lbl, text_rect)
        
        item = vehicle.equipment.get(slot_name)
        if item:
             if getattr(item, 'image', None):
                 icon = pygame.transform.scale(item.image, (32, 32))
                 icon_rect = icon.get_rect(center=slot_rect.center)
                 surface.blit(icon, icon_rect)
             else:
                 pygame.draw.rect(surface, item.color, slot_rect.inflate(-10,-10))
            
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

    # Tabs
    tabs_data = [
        {
            'label': 'Info', 
            'icon_path': './game/lib/sprites/ui/vehicle.png' # Uses custom engine icon
        }
    ]
    modal['tabs_data'] = tabs_data
    if 'active_tab' not in modal: modal['active_tab'] = 'Info'
    
    content_y = base_modal.modal_y + 65 
    content_x = base_modal.modal_x + 15
    
    if modal['active_tab'] == 'Info':
        draw_vehicle_info_tab(surface, vehicle, content_x, content_y, base_modal.modal_w, mouse_pos, modal, assets)
        
    
    return [close_btn, min_btn]