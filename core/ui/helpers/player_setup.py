import pygame
import xml.etree.ElementTree as ET
import xml.dom.minidom
import os
from datetime import datetime
from core.data.config import *
import core.data.config
import core.data.player_xml_parser
from core.entities.item.item import Item, ITEM_TEMPLATES
from core.entities.zombie.zombie import Zombie
import random
from faker import Faker
fake = Faker()
from types import SimpleNamespace
from core.ui.tooltip import draw_tooltip
from core.ui.helpers.trait_config_loader import _load_config_presets, save_config_xml, load_config_data, TRAIT_DEFINITIONS
from core.ui.helpers.settings import _draw_settings_screen, handle_settings_events

_stat_icons_cache = {}

STARTING_POINTS = 5

CLOTHING_COLORS = [
    (255, 255, 255), # White
    (50, 50, 50),    # Black
    (220, 50, 50),   # Red
    (50, 200, 50),   # Green
    (50, 50, 220),   # Blue
    (220, 220, 50),  # Yellow
    (255, 105, 180), # Pink
    (255, 165, 0),   # Orange
    (139, 69, 19),   # Brown
    (128, 128, 128)  # Gray
]

# --- CENTRALIZED CONFIG FOR COLORABLE ITEMS ---
VALID_COLOR_ITEMS = {
    'hair': ['Bald','Mowalk','Cut','Crew','Long'],
    'arms': ['Jacket'],
    'body': ['Tshirt', 'TShirt'],
    'feet': ['Sneakers'],
    'legs': ['Pants']
}
 
def _load_stat_icons():
    """Loads all stat and skill icons into a global cache."""
    if _stat_icons_cache: # Don't reload
        return

    icon_size = (20, 20) # A bit smaller than the line height
    icon_files = {
        # Stats
        "health": SPRITE_PATH + "ui/hp.png",
        "stamina": SPRITE_PATH + "ui/stamina.png",
        "water": SPRITE_PATH + "ui/water.png",
        "food": SPRITE_PATH + "ui/food.png",
        "anxiety": SPRITE_PATH + "ui/axiety.png", # Assuming 'anxiety.png'
        "tireness": SPRITE_PATH + "ui/tireness.png", # Assuming 'tireness.png'
        "infection": SPRITE_PATH + "ui/infection.png",
        "strength": SPRITE_PATH + "ui/strength.png",
        "fitness": SPRITE_PATH + "ui/fitness.png",
        "melee": SPRITE_PATH + "ui/melee.png",
        "maintenance": SPRITE_PATH + "ui/maintenance.png",
        "ranged": SPRITE_PATH + "ui/range.png",
        "lucky": SPRITE_PATH + "ui/lucky.png",
        "agility": SPRITE_PATH + "ui/agility.png",
        "intelligence": SPRITE_PATH + "ui/intelligence.png",
    }
    
    for key, path in icon_files.items():
        img = pygame.image.load(path).convert_alpha()
        _stat_icons_cache[key] = pygame.transform.scale(img, icon_size)


def _draw_player_build_screen(game, state, mouse_pos):
    """Draws the three-column layout and returns clickable rects."""
    
    clickable_rects = {
        "add_trait": [], 
        "remove_trait": [],
        "start_button": None,
        "gear_cycle_buttons": {}, 
        "slot_color_buttons": {}, 
        "name_input": None,
        "save_button": None,
        "delete_button": None,
        "load_dropdown_button": None,
        "load_dropdown_options": [],          
        "random_button": None
    }
    header_height = 30
    border_radius = 4

    _load_stat_icons()
    icon_padding = 24

    col1_x = 170
    col1_width = 270
    col2_x = col1_x + col1_width + 20
    col2_width = 225
    col3_x = col2_x + col2_width + 20
    col3_width = 225
    col4_x = col3_x + col3_width + 20
    col4_width = 275

    padding = 10
    
    # --- Column 1, Block 1: Preset Management Panel ---
    preset_rect = pygame.Rect(col1_x, 30, col1_width, 260)

    preset_header_rect = pygame.Rect(preset_rect.x, preset_rect.y, preset_rect.width, header_height)
    preset_body_rect = pygame.Rect(preset_rect.x, preset_rect.y + header_height, preset_rect.width, preset_rect.height - header_height)
    
    pygame.draw.rect(game.game_screen, (30, 30, 30), preset_body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, preset_header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, preset_rect, 1, border_radius=border_radius)
    game.game_screen.blit(font.render("Preset", True, WHITE), (preset_header_rect.x + 10, preset_header_rect.y + 7))

    # 1. Name Input
    game.game_screen.blit(font.render("Player Name:", True, WHITE), (preset_body_rect.x + padding, preset_body_rect.y + 10))
    name_input_rect = pygame.Rect(preset_body_rect.x + padding, preset_body_rect.y + 35, preset_body_rect.width - padding*2, 30)
    pygame.draw.rect(game.game_screen, (50, 50, 50), name_input_rect)
    pygame.draw.rect(game.game_screen, WHITE, name_input_rect, 1)
    
    name_text = state.get('player_name', "Survivor")
    text_surf = font.render(name_text, True, WHITE)
    game.game_screen.blit(text_surf, (name_input_rect.x + 5, name_input_rect.y + 5))
    
    if state.get('name_input_active') and int(pygame.time.get_ticks() / 500) % 2 == 0:
        cursor_x = name_input_rect.x + 5 + text_surf.get_width()
        pygame.draw.line(game.game_screen, WHITE, (cursor_x, name_input_rect.y + 5), (cursor_x, name_input_rect.bottom - 5), 2)
    
    clickable_rects['name_input'] = name_input_rect

    # 2. Buttons
    buttons_y = preset_body_rect.y + 80
    btn_width = 80
    btn_padding = (preset_body_rect.width - (btn_width * 3) - (padding * 2)) // 2
    
    save_btn_rect = pygame.Rect(preset_body_rect.x + padding, buttons_y, btn_width, 30)
    pygame.draw.rect(game.game_screen, GREEN, save_btn_rect, border_radius=4)
    game.game_screen.blit(font.render("Save", True, WHITE), (save_btn_rect.x + 20, save_btn_rect.y + 5))
    clickable_rects['save_button'] = save_btn_rect
    
    random_btn_rect = pygame.Rect(save_btn_rect.right + btn_padding, buttons_y, btn_width, 30)
    pygame.draw.rect(game.game_screen, (0, 100, 150), random_btn_rect, border_radius=4)
    game.game_screen.blit(font.render("Random", True, WHITE), (random_btn_rect.x + 10, random_btn_rect.y + 5))
    clickable_rects['random_button'] = random_btn_rect

    delete_btn_rect = pygame.Rect(random_btn_rect.right + btn_padding, buttons_y, btn_width, 30)
    pygame.draw.rect(game.game_screen, RED, delete_btn_rect, border_radius=4)
    game.game_screen.blit(font.render("Delete", True, WHITE), (delete_btn_rect.x + 15, delete_btn_rect.y + 5))
    clickable_rects['delete_button'] = delete_btn_rect
    
    # 3. Load Preset Dropdown
    load_dd_rect = pygame.Rect(preset_body_rect.x + padding, preset_body_rect.y + 125, preset_body_rect.width - padding*2, 30)
    clickable_rects['load_dropdown_button'] = load_dd_rect
    pygame.draw.rect(game.game_screen, (50, 50, 50), load_dd_rect)
    pygame.draw.rect(game.game_screen, WHITE, load_dd_rect, 1)
    selected_preset = state.get('selected_preset', "None")
    game.game_screen.blit(font.render(selected_preset, True, WHITE), (load_dd_rect.x + 5, load_dd_rect.y + 5))
    pygame.draw.polygon(game.game_screen, WHITE, [(load_dd_rect.right - 15, load_dd_rect.y + 10), (load_dd_rect.right - 5, load_dd_rect.y + 10), (load_dd_rect.right - 10, load_dd_rect.y + 15)])
    
    sex_y = load_dd_rect.bottom + 10
    game.game_screen.blit(font.render("Sex:", True, WHITE), (preset_body_rect.x + padding, sex_y))
    
    sex_btn_width = (preset_body_rect.width - (padding * 3)) // 2
    male_btn_rect = pygame.Rect(preset_body_rect.x + padding, sex_y + 25, sex_btn_width, 30)
    female_btn_rect = pygame.Rect(male_btn_rect.right + padding, sex_y + 25, sex_btn_width, 30)
    
    current_sex = state['base_data'].get('sex', 'Male')
    
    if current_sex == 'Male':
        pygame.draw.rect(game.game_screen, (80, 80, 80), male_btn_rect, 0, border_radius=3)
        pygame.draw.rect(game.game_screen, WHITE, male_btn_rect, 2, border_radius=3)
    else:
        pygame.draw.rect(game.game_screen, (50, 50, 50), male_btn_rect, 0, border_radius=3)
        pygame.draw.rect(game.game_screen, WHITE, male_btn_rect, 1, border_radius=3)
    game.game_screen.blit(font.render("Male", True, WHITE), (male_btn_rect.centerx - 20, male_btn_rect.y + 5))
    
    if current_sex == 'Female':
        pygame.draw.rect(game.game_screen, (80, 80, 80), female_btn_rect, 0, border_radius=3)
        pygame.draw.rect(game.game_screen, WHITE, female_btn_rect, 2, border_radius=3)
    else:
        pygame.draw.rect(game.game_screen, (50, 50, 50), female_btn_rect, 0, border_radius=3)
        pygame.draw.rect(game.game_screen, WHITE, female_btn_rect, 1, border_radius=3)
    game.game_screen.blit(font.render("Female", True, WHITE), (female_btn_rect.centerx - 28, female_btn_rect.y + 5))
    
    clickable_rects['sex_buttons'] = {'Male': male_btn_rect, 'Female': female_btn_rect}
 
    # --- Column 1, Block 2: Gear Selection ---
    gear_rect = pygame.Rect(col1_x, preset_rect.bottom + 20, col1_width, 360) 

    gear_header_rect = pygame.Rect(gear_rect.x, gear_rect.y, gear_rect.width, header_height)
    gear_body_rect = pygame.Rect(gear_rect.x, gear_rect.y + header_height, gear_rect.width, gear_rect.height - header_height)

    pygame.draw.rect(game.game_screen, (30, 30, 30), gear_body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, gear_header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, gear_rect, 1, border_radius=border_radius)
    game.game_screen.blit(font.render("Clothes", True, WHITE), (gear_header_rect.x + 10, gear_header_rect.y + 7))

    gear_content_rect = pygame.Rect(
        gear_rect.x + padding,
        gear_rect.y + 40, 
        gear_rect.width - (padding * 2),
        gear_rect.height - (padding * 2) - 30
    )

    drawable_gear_rect = game.game_screen.get_rect().clip(gear_content_rect)
    
    if drawable_gear_rect.width > 0 and drawable_gear_rect.height > 0:
        gear_content_surface = game.game_screen.subsurface(drawable_gear_rect)
        gear_content_surface.fill((30, 30, 30))
        label_width = 50
        color_btn_w = 25
        base_cycle_width = col1_width - label_width - (padding * 3) - 10
        y_offset = 0
        
        for slot_name in state['clothes_slots']:
            selected_item = state['chosen_clothes'].get(slot_name, "None")
            show_color_box = (slot_name in VALID_COLOR_ITEMS and selected_item in VALID_COLOR_ITEMS[slot_name])
            
            cycle_width = base_cycle_width
            if show_color_box:
                cycle_width -= (color_btn_w + 5)
            
            cycle_rect_abs = pygame.Rect(gear_content_rect.x + label_width + (padding * 2), gear_content_rect.y + y_offset, cycle_width, 25)
            
            if cycle_rect_abs.bottom > gear_content_rect.top and cycle_rect_abs.top < gear_content_rect.bottom:
                gear_content_surface.blit(font.render(f"{slot_name.capitalize()}:", True, WHITE), (0, y_offset + 5))
                
                cycle_rect_rel = pygame.Rect(cycle_rect_abs.x - gear_content_rect.x, y_offset, cycle_width, 25)
                
                hovered = cycle_rect_abs.collidepoint(mouse_pos)
                bg_color = (70, 70, 70) if hovered else (50, 50, 50)
                
                # Draw cycle button box
                pygame.draw.rect(gear_content_surface, bg_color, cycle_rect_rel, border_radius=3)
                pygame.draw.rect(gear_content_surface, WHITE, cycle_rect_rel, 1, border_radius=3)
                
                text = font.render(selected_item, True, WHITE)
                text_x = cycle_rect_rel.x + (cycle_rect_rel.width - text.get_width()) // 2
                text_y = cycle_rect_rel.y + (cycle_rect_rel.height - text.get_height()) // 2
                gear_content_surface.blit(text, (text_x, text_y))
                
                # Draw cycle arrows on sides
                pygame.draw.polygon(gear_content_surface, WHITE, [(cycle_rect_rel.right - 8, cycle_rect_rel.centery), (cycle_rect_rel.right - 14, cycle_rect_rel.centery - 4), (cycle_rect_rel.right - 14, cycle_rect_rel.centery + 4)])
                pygame.draw.polygon(gear_content_surface, WHITE, [(cycle_rect_rel.x + 8, cycle_rect_rel.centery), (cycle_rect_rel.x + 14, cycle_rect_rel.centery - 4), (cycle_rect_rel.x + 14, cycle_rect_rel.centery + 4)])
                
                clickable_rects['gear_cycle_buttons'][slot_name] = cycle_rect_abs
                
                if show_color_box:
                    color_rect_abs = pygame.Rect(cycle_rect_abs.right + 5, cycle_rect_abs.y, color_btn_w, 25)
                    color_rect_rel = pygame.Rect(cycle_rect_rel.right + 5, y_offset, color_btn_w, 25)
                    current_color = state['clothes_colors'].get(slot_name, (255, 255, 255))
                    
                    pygame.draw.rect(gear_content_surface, current_color, color_rect_rel, border_radius=3)
                    pygame.draw.rect(gear_content_surface, WHITE, color_rect_rel, 1, border_radius=3)
                    
                    clickable_rects['slot_color_buttons'][slot_name] = color_rect_abs
                
            y_offset += 35
    
    # --- Column 2: Available Traits (Middle-Left) ---
    prof_rect = pygame.Rect(col2_x, 30, col2_width, 160)
    prof_header_rect = pygame.Rect(prof_rect.x, prof_rect.y, prof_rect.width, header_height)
    prof_body_rect = pygame.Rect(prof_rect.x, prof_rect.y + header_height, prof_rect.width, prof_rect.height - header_height)
    
    pygame.draw.rect(game.game_screen, (30, 30, 30), prof_body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, prof_header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, prof_rect, 1, border_radius=border_radius)
    game.game_screen.blit(font.render("Available Professions", True, WHITE), (prof_header_rect.x + 10, prof_header_rect.y + 7))
    
    prof_content_rect = pygame.Rect(prof_rect.x + padding, prof_rect.y + header_height + padding, prof_rect.width - (padding * 2) - 10, prof_rect.height - header_height - (padding * 2))
    state['prof_content_rect'] = prof_content_rect
    line_height = 35
    
    total_prof_items = len(state.get('available_professions', []))
    total_prof_text_height = total_prof_items * line_height
    prof_max_scroll = max(0, total_prof_text_height - prof_content_rect.height)
    state['prof_max_scroll'] = prof_max_scroll
    prof_scroll_y = max(0, min(state.get('prof_scroll_offset_y', 0), prof_max_scroll))
    state['prof_scroll_offset_y'] = prof_scroll_y
    
    drawable_prof_rect = game.game_screen.get_rect().clip(prof_content_rect)
    hovered_trait_id = None
    
    if drawable_prof_rect.width > 0 and drawable_prof_rect.height > 0:
        prof_surface = game.game_screen.subsurface(drawable_prof_rect)
        prof_surface.fill((30, 30, 30))
        y_off = 0 - prof_scroll_y
        for p_id in state.get('available_professions', []):
            row_rect_rel = pygame.Rect(0, y_off, prof_content_rect.width, 30)
            row_rect_abs = pygame.Rect(prof_content_rect.x, prof_content_rect.y + y_off, prof_content_rect.width, 30)
            add_btn_rect_rel = pygame.Rect(row_rect_rel.right - 25, row_rect_rel.y, 25, 25)
            add_btn_rect_abs = pygame.Rect(prof_content_rect.x + add_btn_rect_rel.x, prof_content_rect.y + add_btn_rect_rel.y, 25, 25)
            
            if row_rect_rel.bottom > 0 and row_rect_rel.top < prof_content_rect.height:
                if row_rect_abs.collidepoint(mouse_pos): hovered_trait_id = p_id
                trait_cost = TRAIT_DEFINITIONS.get(p_id, {}).get('cost', 0)
                cost_color = (100, 255, 100) if trait_cost > 0 else (255, 100, 100) if trait_cost < 0 else WHITE
                name_surf = font.render(TRAIT_DEFINITIONS[p_id].get('name', p_id), True, WHITE)
                cost_surf = font.render(f"({trait_cost:+})", True, cost_color)
                
                prof_surface.blit(name_surf, (row_rect_rel.x, row_rect_rel.y))
                prof_surface.blit(cost_surf, (row_rect_rel.x + name_surf.get_width() + 5, row_rect_rel.y))
                pygame.draw.rect(prof_surface, GREEN, add_btn_rect_rel, border_radius=4)
                prof_surface.blit(font.render(">", True, WHITE), (add_btn_rect_rel.x + 7, add_btn_rect_rel.y + 2))
                
            clickable_rects["add_trait"].append((p_id, add_btn_rect_abs))
            y_off += line_height

    if total_prof_text_height > prof_content_rect.height:
        scroll_rect = pygame.Rect(prof_content_rect.right + 2, prof_content_rect.top, 8, prof_content_rect.height)
        handle_h = max(10, prof_content_rect.height * (prof_content_rect.height / total_prof_text_height))
        handle_pos = 0 if prof_max_scroll <= 0 else prof_scroll_y / prof_max_scroll
        handle_y = scroll_rect.top + (prof_content_rect.height - handle_h) * handle_pos
        prof_handle_rect = pygame.Rect(scroll_rect.left, handle_y, scroll_rect.width, handle_h)
        pygame.draw.rect(game.game_screen, GRAY, prof_handle_rect, 0, 2)
        state['prof_scrollbar_handle_rect'] = prof_handle_rect
    else: state['prof_scrollbar_handle_rect'] = None

    # --- Column 2B: Available Traits (Bottom 75%) ---
    available_rect = pygame.Rect(col2_x, prof_rect.bottom + 20, col2_width, 640 - 160 - 20)
    
    avail_header_rect = pygame.Rect(available_rect.x, available_rect.y, available_rect.width, header_height)
    avail_body_rect = pygame.Rect(available_rect.x, available_rect.y + header_height, available_rect.width, available_rect.height - header_height)
    pygame.draw.rect(game.game_screen, (30, 30, 30), avail_body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, avail_header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, available_rect, 1, border_radius=border_radius)
    game.game_screen.blit(font.render("Available Traits", True, WHITE), (avail_header_rect.x + 10, avail_header_rect.y + 7))
    
    traits_content_rect = pygame.Rect(available_rect.x + padding, available_rect.y + header_height + padding, available_rect.width - (padding * 2) - 10, available_rect.height - header_height - (padding * 2))
    state['traits_content_rect'] = traits_content_rect
    
    # Ensure this variable matches the rest of the file
    state['traits_line_height'] = line_height
    total_items = len(state['available_traits'])
    total_text_height = total_items * line_height
    visible_height = traits_content_rect.height
    max_scroll_offset = max(0, total_text_height - visible_height)
    state['traits_max_scroll'] = max_scroll_offset
    scroll_offset_y = max(0, min(state.get('traits_scroll_offset_y', 0), max_scroll_offset))
    state['traits_scroll_offset_y'] = scroll_offset_y
    drawable_traits_rect = game.game_screen.get_rect().clip(traits_content_rect)
    
    if drawable_traits_rect.width > 0 and drawable_traits_rect.height > 0:
        content_surface = game.game_screen.subsurface(drawable_traits_rect)
        content_surface.fill((30, 30, 30))
    else: content_surface = None
    
    y_offset = 0 - scroll_offset_y
    if content_surface:
        for i, trait_name in enumerate(state['available_traits']):
            row_rect_rel = pygame.Rect(0, y_offset, traits_content_rect.width, 30)
            row_rect_abs = pygame.Rect(traits_content_rect.x, traits_content_rect.y + y_offset, traits_content_rect.width, 30)
            add_btn_rect_rel = pygame.Rect(row_rect_rel.right - 25, row_rect_rel.y, 25, 25)
            add_btn_rect_abs = pygame.Rect(traits_content_rect.x + add_btn_rect_rel.x, traits_content_rect.y + add_btn_rect_rel.y, 25, 25)
            
            if row_rect_rel.bottom > 0 and row_rect_rel.top < traits_content_rect.height:
                if row_rect_abs.collidepoint(mouse_pos):
                    hovered_trait_id = trait_name
                trait_cost = TRAIT_DEFINITIONS.get(trait_name, {}).get('cost', 0)
                cost_color = (100, 255, 100) if trait_cost > 0 else (255, 100, 100) if trait_cost < 0 else WHITE
                name_surf = font.render(TRAIT_DEFINITIONS.get(trait_name, {}).get('name', trait_name.capitalize()), True, WHITE)
                cost_surf = font.render(f"({trait_cost:+})", True, cost_color)
                
                content_surface.blit(name_surf, (row_rect_rel.x, row_rect_rel.y))
                content_surface.blit(cost_surf, (row_rect_rel.x + name_surf.get_width() + 5, row_rect_rel.y))
                pygame.draw.rect(content_surface, GREEN, add_btn_rect_rel, border_radius=4)
                content_surface.blit(font.render(">", True, WHITE), (add_btn_rect_rel.x + 7, add_btn_rect_rel.y + 2))
                
            clickable_rects["add_trait"].append((trait_name, add_btn_rect_abs))
            y_offset += line_height

    if total_text_height > visible_height:
        scrollbar_area_height = traits_content_rect.height
        scrollbar_area_rect = pygame.Rect(traits_content_rect.right + 2, traits_content_rect.top, 8, scrollbar_area_height)
        handle_height_ratio = visible_height / total_text_height
        handle_height = max(10, scrollbar_area_height * handle_height_ratio)
        handle_pos_ratio = 0 if max_scroll_offset <= 0 else scroll_offset_y / max_scroll_offset
        handle_y = scrollbar_area_rect.top + (scrollbar_area_height - handle_height) * handle_pos_ratio
        traits_scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        pygame.draw.rect(game.game_screen, GRAY, traits_scrollbar_handle_rect, 0, 2)
        state['traits_scrollbar_handle_rect'] = traits_scrollbar_handle_rect
    else: state['traits_scrollbar_handle_rect'] = None

    # --- Column 3: Chosen Traits ---
    chosen_rect = pygame.Rect(col3_x, 30, col3_width, 640)
    header_rect = pygame.Rect(chosen_rect.x, chosen_rect.y, chosen_rect.width, header_height)
    body_rect = pygame.Rect(chosen_rect.x, chosen_rect.y + header_height, chosen_rect.width, chosen_rect.height - header_height)
    pygame.draw.rect(game.game_screen, (30, 30, 30), body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, chosen_rect, 1, border_radius=border_radius)
    game.game_screen.blit(font.render("Chosen Traits", True, WHITE), (header_rect.x + 10, header_rect.y + 7))
    total_cost = sum(TRAIT_DEFINITIONS.get(t, {}).get('cost', 0) for t in state['chosen_traits'])
    state['total_trait_cost'] = total_cost
    
    points_remaining = STARTING_POINTS - total_cost
    cost_text = f"Points: {points_remaining}"
    cost_color = (100, 255, 100) if points_remaining >= 0 else (255, 100, 100)
    
    cost_surf = font.render(cost_text, True, cost_color)
    cost_rect = cost_surf.get_rect(right=header_rect.right - padding, centery=header_rect.centery)
    game.game_screen.blit(cost_surf, cost_rect)
    
    chosen_content_rect = pygame.Rect(chosen_rect.x + padding, chosen_rect.y + header_height + padding, chosen_rect.width - (padding * 2) - 10, chosen_rect.height - header_height - (padding * 2))
    state['chosen_content_rect'] = chosen_content_rect 

    line_height = 35
    total_items = len(state['chosen_traits'])
    total_text_height = total_items * line_height
    visible_height = chosen_content_rect.height
    
    max_scroll_offset = max(0, total_text_height - visible_height)
    state['chosen_max_scroll'] = max_scroll_offset
    
    scroll_offset_y = max(0, min(state.get('chosen_scroll_offset_y', 0), max_scroll_offset))
    state['chosen_scroll_offset_y'] = scroll_offset_y
    
    drawable_chosen_rect = game.game_screen.get_rect().clip(chosen_content_rect)
    if drawable_chosen_rect.width > 0 and drawable_chosen_rect.height > 0:
        content_surface = game.game_screen.subsurface(drawable_chosen_rect)
        content_surface.fill((30, 30, 30))
    else:
        content_surface = None

    y_offset = 0 - scroll_offset_y
    
    if content_surface:
        for i, trait_name in enumerate(state['chosen_traits']):
            row_rect_rel = pygame.Rect(0, y_offset, chosen_content_rect.width, 30)
            row_rect_abs = pygame.Rect(chosen_content_rect.x, chosen_content_rect.y + y_offset, chosen_content_rect.width, 30)
            
            remove_btn_rect_rel = pygame.Rect(0, row_rect_rel.y, 25, 25)
            remove_btn_rect_abs = pygame.Rect(chosen_content_rect.x, chosen_content_rect.y + y_offset, 25, 25)

            if row_rect_rel.bottom > 0 and row_rect_rel.top < chosen_content_rect.height:
                if row_rect_abs.collidepoint(mouse_pos):
                    hovered_trait_id = trait_name
                pygame.draw.rect(content_surface, RED, remove_btn_rect_rel, border_radius=4)
                content_surface.blit(font.render("<", True, WHITE), (remove_btn_rect_rel.x + 7, remove_btn_rect_rel.y + 2))
                content_surface.blit(font.render(trait_name.capitalize(), True, WHITE), (remove_btn_rect_rel.right + 10, row_rect_rel.y))

            clickable_rects["remove_trait"].append((trait_name, remove_btn_rect_abs))
            y_offset += 35
            
    if total_text_height > visible_height:
        scrollbar_area_height = chosen_content_rect.height
        scrollbar_area_rect = pygame.Rect(chosen_content_rect.right + 2, chosen_content_rect.top, 8, scrollbar_area_height)
        
        handle_height_ratio = visible_height / total_text_height
        handle_height = max(10, scrollbar_area_height * handle_height_ratio)
        
        handle_pos_ratio = 0 if max_scroll_offset <= 0 else scroll_offset_y / max_scroll_offset
        handle_y = scrollbar_area_rect.top + (scrollbar_area_height - handle_height) * handle_pos_ratio
        
        chosen_scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        pygame.draw.rect(game.game_screen, GRAY, chosen_scrollbar_handle_rect, 0, 2)
        state['chosen_scrollbar_handle_rect'] = chosen_scrollbar_handle_rect
    else:
        state['chosen_scrollbar_handle_rect'] = None

    # --- Column 4 ---
    sprite_rect_container = pygame.Rect(col4_x, 30, col4_width, 310)
    pygame.draw.rect(game.game_screen, (30, 30, 30), sprite_rect_container)
    pygame.draw.rect(game.game_screen, WHITE, sprite_rect_container, 1,border_top_left_radius=4, border_top_right_radius=4,border_bottom_left_radius=4, border_bottom_right_radius=4)
    if state.get('player_sprite_large'):
        sprite_rect = state['player_sprite_large'].get_rect(center=sprite_rect_container.center)
        game.game_screen.blit(state['player_sprite_large'], sprite_rect)

        hidden_slots = set()
        for slot in state['clothes_slots']:
            item_name = state['chosen_clothes'].get(slot)
            if item_name and item_name != "None":
                template = ITEM_TEMPLATES.get(item_name)
                if template and 'properties' in template and 'hide_cloth' in template['properties']:
                    hidden_slots.update(template['properties']['hide_cloth'])

        for slot in state['clothes_slots']:
            if slot in hidden_slots:
                continue
            item_name = state['chosen_clothes'].get(slot)
            if item_name and item_name != "None":
                clothing_img = state['clothing_sprites'].get(item_name)
                if clothing_img: 
                    tint_color = state.get('clothes_colors', {}).get(slot, (255, 255, 255))
                    if tint_color != (255, 255, 255):
                        tinted = clothing_img.copy()
                        tinted.fill((*tint_color, 255)[:4], special_flags=pygame.BLEND_RGBA_MULT)
                        game.game_screen.blit(tinted, sprite_rect)
                    else:
                        game.game_screen.blit(clothing_img, sprite_rect)

    stats_rect = pygame.Rect(col4_x, sprite_rect_container.bottom + 20, col4_width, 240)
    stats_header_rect = pygame.Rect(stats_rect.x, stats_rect.y, stats_rect.width, header_height)
    stats_body_rect = pygame.Rect(stats_rect.x, stats_rect.y + header_height, stats_rect.width, stats_rect.height - header_height)
    pygame.draw.rect(game.game_screen, (30, 30, 30), stats_body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, GRAY_60, stats_header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.game_screen, WHITE, stats_rect, 1, border_radius=border_radius)
    game.game_screen.blit(font.render("Current Stats", True, WHITE), (stats_header_rect.x + 10, stats_header_rect.y + 7))
    stats_content_rect = pygame.Rect(stats_rect.x + padding, stats_rect.y + 40, stats_rect.width - (padding * 2) - 10, stats_rect.height - (padding * 2) - 30)
    state['stats_content_rect'] = stats_content_rect

    current_stats = state['base_data']['stats'].copy()
    current_attrs = state['base_data']['attributes'].copy()

    current_attrs = {k: (v.copy() if isinstance(v, dict) else v) for k, v in state['base_data']['attributes'].items()}

    display_modifiers = {}
    level_modifiers = {}
    
    for trait_name in state['chosen_traits']:
        effects = TRAIT_DEFINITIONS.get(trait_name, {})
        if "stats" in effects:
            for stat, value in effects["stats"].items():
                display_modifiers[stat] = display_modifiers.get(stat, 0) + value
        if "attributes" in effects:
            for attr, value in effects["attributes"].items():
                display_modifiers[attr] = display_modifiers.get(attr, 0) + value

        if "starting_levels" in effects:
            for attr, value in effects["starting_levels"].items():
                level_modifiers[attr] = level_modifiers.get(attr, 0) + value
                if attr in current_attrs:
                    curr_val = current_attrs[attr]
                    if isinstance(curr_val, dict):
                        curr_val['level'] = curr_val.get('level', 0) + value
                    else:
                        current_attrs[attr] = curr_val + value

    state['final_stats'] = current_stats
    state['final_attrs'] = current_attrs
    line_height = 25
    state['stats_line_height'] = line_height
    total_items = len(current_stats) + len(current_attrs)
    total_text_height = total_items * line_height
    visible_height = stats_content_rect.height
    max_scroll_offset = max(0, total_text_height - visible_height)
    state['stats_max_scroll'] = max_scroll_offset
    scroll_offset_y = max(0, min(state.get('stats_scroll_offset_y', 0), max_scroll_offset))
    state['stats_scroll_offset_y'] = scroll_offset_y
    drawable_stats_rect = game.game_screen.get_rect().clip(stats_content_rect)
    if drawable_stats_rect.width > 0 and drawable_stats_rect.height > 0:
        content_surface = game.game_screen.subsurface(drawable_stats_rect)
        content_surface.fill((30, 30, 30))
        y_offset = 0 - scroll_offset_y
        for stat, value in current_stats.items():
            icon = _stat_icons_cache.get(stat)
            if icon:
                content_surface.blit(icon, (0, y_offset + (line_height - icon.get_height()) // 2))
                text_x = icon_padding
            else: text_x = 0
            base_value = state['base_data']['stats'].get(stat, 100.0)

            trait_mod = display_modifiers.get(stat, 0)
            
            stat_name_str = f"{stat.capitalize()}"
            
            trait_str = f"{int(trait_mod):+}% Rate"
            
            mod_color = WHITE
            if trait_mod > 0: mod_color = (100, 255, 100) 
            elif trait_mod < 0: mod_color = (255, 100, 100) 

            text_surf = font.render(f"{stat_name_str}", True, WHITE)
            
            if trait_mod != 0:
                mod_surf = font.render(f"{trait_str}", True, mod_color)
                content_surface.blit(text_surf, (text_x, y_offset + 3))
                content_surface.blit(mod_surf, (text_x + 100, y_offset + 3))
            else:
                content_surface.blit(text_surf, (text_x, y_offset + 3))
                
            y_offset += line_height

        for attr, value_obj in current_attrs.items():
            icon = _stat_icons_cache.get(attr)
            if icon:
                content_surface.blit(icon, (0, y_offset + (line_height - icon.get_height()) // 2))
                text_x = icon_padding
            else: text_x = 0

            if isinstance(value_obj, dict):
                current_level = value_obj.get('level', 0)
            else:
                current_level = int(value_obj)

            xp_mod = display_modifiers.get(attr, 0)   
            lvl_mod = level_modifiers.get(attr, 0)    
            
            stat_name_str = f"{attr.capitalize()}"
            
            text_surf = font.render(f"{stat_name_str}", True, WHITE)
            content_surface.blit(text_surf, (text_x, y_offset + 3))
            
            current_draw_x = text_x + 100
            
            if lvl_mod > 0:
                lvl_surf = font.render(f"+{lvl_mod} Level", True, (100, 255, 100)) 
                content_surface.blit(lvl_surf, (current_draw_x, y_offset + 3))
                current_draw_x += lvl_surf.get_width() + 8
            
            if xp_mod != 0:
                mod_color = (100, 255, 100) if xp_mod > 0 else (255, 100, 100)
                mod_surf = font.render(f"{int(xp_mod):+}% XP", True, mod_color)
                content_surface.blit(mod_surf, (current_draw_x, y_offset + 3))
            
            y_offset += line_height

    if total_text_height > visible_height:
        scrollbar_area_height = stats_content_rect.height
        scrollbar_area_rect = pygame.Rect(stats_content_rect.right + 2, stats_content_rect.top, 8, scrollbar_area_height)
        handle_height_ratio = visible_height / total_text_height
        handle_height = max(10, scrollbar_area_height * handle_height_ratio)
        handle_pos_ratio = 0 if max_scroll_offset <= 0 else scroll_offset_y / max_scroll_offset
        handle_y = scrollbar_area_rect.top + (scrollbar_area_height - handle_height) * handle_pos_ratio
        stats_scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        pygame.draw.rect(game.game_screen, GRAY, stats_scrollbar_handle_rect, 0, 2)
        state['stats_scrollbar_handle_rect'] = stats_scrollbar_handle_rect
    else: state['stats_scrollbar_handle_rect'] = None

    start_btn_rect = pygame.Rect(col4_x, stats_rect.bottom + 20, col4_width, 70)
    is_balanced = (state.get('total_trait_cost', 0) <= STARTING_POINTS)
    if is_balanced:
        pygame.draw.rect(game.game_screen, (0, 100, 0), start_btn_rect, border_radius=border_radius)
        if start_btn_rect.collidepoint(mouse_pos):
            pygame.draw.rect(game.game_screen, (0, 150, 0), start_btn_rect.inflate(-4, -4), border_radius=border_radius)
        start_text = large_font.render("START GAME", True, WHITE)
    else:
        pygame.draw.rect(game.game_screen, (50, 50, 50), start_btn_rect, border_radius=border_radius)
        pygame.draw.rect(game.game_screen, GRAY, start_btn_rect, 1, border_radius=border_radius)
        start_text = large_font.render("START GAME", True, (100, 100, 100))
    text_rect = start_text.get_rect(center=start_btn_rect.center)
    game.game_screen.blit(start_text, text_rect)
    clickable_rects["start_button"] = start_btn_rect

    active_preset_dropdown = state.get('preset_dropdown_active', False)
    
    # 3. Preset List
    if active_preset_dropdown:
        options = state.get('preset_list', ["None"])
        option_height = 25
        list_height = len(options) * option_height
        list_rect = pygame.Rect(load_dd_rect.x, load_dd_rect.bottom, load_dd_rect.width, list_height)
        pygame.draw.rect(game.game_screen, (30, 30, 30), list_rect)
        pygame.draw.rect(game.game_screen, WHITE, list_rect, 1)
        y_offset = list_rect.y
        clickable_rects["load_dropdown_options"] = []
        for option_name in options:
            option_rect = pygame.Rect(list_rect.x, y_offset, list_rect.width, option_height)
            if option_rect.collidepoint(mouse_pos): pygame.draw.rect(game.game_screen, (70, 70, 70), option_rect)
            game.game_screen.blit(font.render(option_name, True, WHITE), (option_rect.x + 5, option_rect.y + 2))
            clickable_rects["load_dropdown_options"].append((option_name, option_rect))
            y_offset += option_height

    if hovered_trait_id:
        trait_data = TRAIT_DEFINITIONS.get(hovered_trait_id)
        if trait_data and trait_data.get('tooltip'):
            t_item = SimpleNamespace(
                name=trait_data.get('name', hovered_trait_id),
                tooltip_text=trait_data.get('tooltip'),
                item_type=None,
                durability=None,
                defence=None,
                load=None,
                min_damage=None,
                max_damage=None,
                ammo_type=None
            )
            draw_tooltip(game.game_screen, t_item, mouse_pos)

    return clickable_rects

def _update_available_traits(state):
    all_defs = state['all_traits']
    chosen = state['chosen_traits']
    
    disabled_ids = set()
    for t_id in chosen:
        t_def = all_defs.get(t_id)
        if t_def and 'conflicts' in t_def:
            for conflict_id in t_def['conflicts']:
                disabled_ids.add(conflict_id)
    
    valid_traits = []
    valid_profs = []
    
    for t_id in all_defs.keys():
        if t_id in chosen: continue        
        if t_id in disabled_ids: continue  
        
        if all_defs[t_id].get('is_profession', False):
            valid_profs.append(t_id)
        else:
            valid_traits.append(t_id)

    pos_traits = sorted(
        [t for t in valid_traits if all_defs[t].get('cost', 0) > 0], 
        key=lambda t: (all_defs[t].get('cost', 0), t)
    )
    neg_traits = sorted(
        [t for t in valid_traits if all_defs[t].get('cost', 0) < 0], 
        key=lambda t: (abs(all_defs[t].get('cost', 0)), t)
    )
    
    state['available_professions'] = sorted(valid_profs, key=lambda t: all_defs[t].get('name', t))
    state['available_traits'] = pos_traits + neg_traits


def handle_player_events(game, state, event, mouse_pos, clickable_rects):
    if event.type == pygame.MOUSEWHEEL:
        stats_rect = state.get('stats_content_rect')
        chosen_rect = state.get('chosen_content_rect')
        
        if state.get('traits_content_rect') and state['traits_content_rect'].collidepoint(mouse_pos):
             state['traits_scroll_offset_y'] = max(0, min(state['traits_scroll_offset_y'] - event.y * 70, state.get('traits_max_scroll', 0)))
        elif state.get('prof_content_rect') and state['prof_content_rect'].collidepoint(mouse_pos):
             state['prof_scroll_offset_y'] = max(0, min(state.get('prof_scroll_offset_y', 0) - event.y * 70, state.get('prof_max_scroll', 0)))
        elif stats_rect and stats_rect.collidepoint(mouse_pos):
             state['stats_scroll_offset_y'] = max(0, min(state['stats_scroll_offset_y'] - event.y * 50, state.get('stats_max_scroll', 0)))
        elif chosen_rect and chosen_rect.collidepoint(mouse_pos):
             state['chosen_scroll_offset_y'] = max(0, min(state['chosen_scroll_offset_y'] - event.y * 70, state.get('chosen_max_scroll', 0)))

    elif event.type == pygame.KEYDOWN:
        if state.get('name_input_active'):
            if event.key == pygame.K_BACKSPACE: 
                state['player_name'] = state['player_name'][:-1]
            elif event.key == pygame.K_RETURN: 
                state['name_input_active'] = False
            elif len(state['player_name']) <= 20: 
                state['player_name'] += event.unicode
            
        if state.get('seed_input_active'):
            if event.key == pygame.K_BACKSPACE:
                state['world_seed'] = state['world_seed'][:-1]
            elif event.key == pygame.K_RETURN:
                state['seed_input_active'] = False
            elif len(state.get('world_seed', "")) <= 10: 
                if event.unicode.isalnum() or event.unicode == '-':
                    state['world_seed'] += event.unicode.upper()

    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        dropdown_clicked = False
        scrollbar_clicked = False
        
        if state.get('stats_scrollbar_handle_rect') and state['stats_scrollbar_handle_rect'].collidepoint(mouse_pos):
            state['is_dragging_stats_scrollbar'] = True; state['stats_scroll_drag_last_y'] = mouse_pos[1]; scrollbar_clicked = True
        if not scrollbar_clicked and state.get('traits_scrollbar_handle_rect') and state['traits_scrollbar_handle_rect'].collidepoint(mouse_pos):
            state['is_dragging_traits_scrollbar'] = True; state['traits_scroll_drag_last_y'] = mouse_pos[1]; scrollbar_clicked = True
        if state.get('prof_scrollbar_handle_rect') and state['prof_scrollbar_handle_rect'].collidepoint(mouse_pos):
            state['is_dragging_prof_scrollbar'] = True; state['prof_scroll_drag_last_y'] = mouse_pos[1]; scrollbar_clicked = True
        if not scrollbar_clicked and state.get('chosen_scrollbar_handle_rect') and state['chosen_scrollbar_handle_rect'].collidepoint(mouse_pos):
             state['is_dragging_chosen_scrollbar'] = True; state['chosen_scroll_drag_last_y'] = mouse_pos[1]; scrollbar_clicked = True

        if scrollbar_clicked: return

        if clickable_rects.get('name_input') and clickable_rects['name_input'].collidepoint(mouse_pos): state['name_input_active'] = True
        else: state['name_input_active'] = False

        if clickable_rects.get('seed_input') and clickable_rects['seed_input'].collidepoint(mouse_pos):
            state['seed_input_active'] = True
            state['name_input_active'] = False 
        else:
            state['seed_input_active'] = False
        
        if clickable_rects.get('slot_color_buttons'):
            for slot_name, rect in clickable_rects['slot_color_buttons'].items():
                if rect.collidepoint(mouse_pos):
                    current_color = state['clothes_colors'].get(slot_name, (255, 255, 255))
                    try:
                        c_idx = CLOTHING_COLORS.index(current_color)
                        state['clothes_colors'][slot_name] = CLOTHING_COLORS[(c_idx + 1) % len(CLOTHING_COLORS)]
                    except ValueError:
                        state['clothes_colors'][slot_name] = CLOTHING_COLORS[0]
                    dropdown_clicked = True
                    break
            if dropdown_clicked: return

        if clickable_rects.get('gear_cycle_buttons'):
            for slot_name, rect in clickable_rects['gear_cycle_buttons'].items():
                if rect.collidepoint(mouse_pos):
                    options = state['available_clothes'].get(slot_name, [])
                    if options:
                        current_item = state['chosen_clothes'].get(slot_name, "None")
                        try:
                            current_index = options.index(current_item)
                        except ValueError:
                            current_index = 0
                            
                        next_index = (current_index + 1) % len(options)
                        new_item = options[next_index]
                        state['chosen_clothes'][slot_name] = new_item
                        
                        if slot_name not in VALID_COLOR_ITEMS or new_item not in VALID_COLOR_ITEMS[slot_name]:
                            state['clothes_colors'][slot_name] = (255, 255, 255)
                    dropdown_clicked = True
                    break
            if dropdown_clicked: return

        if clickable_rects.get("start_button") and clickable_rects["start_button"].collidepoint(mouse_pos):
            if state.get('total_trait_cost', 0) <= STARTING_POINTS:
                final_player_data = state['base_data'].copy()
                final_player_data['attributes'] = state['final_attrs']
                final_player_data['clothes'] = state['chosen_clothes']
                final_player_data['clothes_colors'] = state.get('clothes_colors', {})
                final_player_data['name'] = state.get('player_name', "Player")
                final_player_data['sex'] = state['base_data'].get('sex', 'Male')
                final_player_data['traits'] = state['chosen_traits']
                final_player_data['visuals'] = {'center': 'player.png', 'left': 'player_left.png', 'right': 'player_right.png'}
                final_player_data['sounds'] = { 'steps': 'steps.ogg' }
                
                final_player_data['game_settings'] = state.get('settings_data')

                raw_seed = state.get('world_seed', "").strip()
                if not raw_seed:
                    raw_seed = core.data.config.generate_random_seed()
                
                final_player_data['world_seed'] = raw_seed

                game.loading_data = final_player_data
                game.game_state = 'LOADING'
                game.loading_done = False
                return
        
        if state.get('preset_dropdown_active'):
            for option_name, option_rect in clickable_rects.get("load_dropdown_options", []):
                if option_rect.collidepoint(mouse_pos):
                    state['selected_preset'] = option_name; state['preset_dropdown_active'] = False; _load_preset(state); dropdown_clicked = True; break
            if dropdown_clicked: return

        if clickable_rects.get('load_dropdown_button') and clickable_rects['load_dropdown_button'].collidepoint(mouse_pos):
            state['preset_dropdown_active'] = not state.get('preset_dropdown_active', False); dropdown_clicked = True

        if not dropdown_clicked:
            state['preset_dropdown_active'] = False

        if 'sex_buttons' in clickable_rects:
            for sex, rect in clickable_rects['sex_buttons'].items():
                if rect.collidepoint(mouse_pos):
                    state['base_data']['sex'] = sex
                    if state['player_name'] == "Survivor" or not state['player_name']:
                         state['player_name'] = fake.name_male() if sex == 'Male' else fake.name_female()
                    break

        for trait_name, rect in clickable_rects.get("add_trait", []):
            if rect.collidepoint(mouse_pos):
                if trait_name in state['available_traits']:
                    state['chosen_traits'].append(trait_name)
                    _update_available_traits(state) 
                    break 
        
        for trait_name, rect in clickable_rects.get("remove_trait", []):
            if rect.collidepoint(mouse_pos):
                if trait_name in state['chosen_traits']:
                    state['chosen_traits'].remove(trait_name)
                    _update_available_traits(state) 
                    break
        
        if clickable_rects.get('save_button') and clickable_rects['save_button'].collidepoint(mouse_pos): _save_preset(state)
        if clickable_rects.get('random_button') and clickable_rects['random_button'].collidepoint(mouse_pos): 
            _randomize_character(state)
            _update_available_traits(state)
        if clickable_rects.get('delete_button') and clickable_rects['delete_button'].collidepoint(mouse_pos): _delete_preset(state)

    elif event.type == pygame.MOUSEBUTTONUP:
        state['is_dragging_stats_scrollbar'] = False
        state['is_dragging_traits_scrollbar'] = False
        state['is_dragging_chosen_scrollbar'] = False
        state['is_dragging_prof_scrollbar'] = False

    elif event.type == pygame.MOUSEMOTION:
        if state.get('is_dragging_stats_scrollbar'):
            mouse_delta_y = mouse_pos[1] - state['stats_scroll_drag_last_y']; state['stats_scroll_drag_last_y'] = mouse_pos[1]
            track_height = state['stats_content_rect'].height - state['stats_scrollbar_handle_rect'].height
            if track_height > 0:
                state['stats_scroll_offset_y'] = max(0, min(state.get('stats_scroll_offset_y', 0) + (mouse_delta_y * (state['stats_max_scroll'] / track_height)), state['stats_max_scroll']))
        
        elif state.get('is_dragging_traits_scrollbar'):
            mouse_delta_y = mouse_pos[1] - state['traits_scroll_drag_last_y']; state['traits_scroll_drag_last_y'] = mouse_pos[1]
            track_height = state['traits_content_rect'].height - state['traits_scrollbar_handle_rect'].height
            if track_height > 0:
                state['traits_scroll_offset_y'] = max(0, min(state.get('traits_scroll_offset_y', 0) + (mouse_delta_y * (state['traits_max_scroll'] / track_height)), state['traits_max_scroll']))

        elif state.get('is_dragging_chosen_scrollbar'):
            mouse_delta_y = mouse_pos[1] - state['chosen_scroll_drag_last_y']; state['chosen_scroll_drag_last_y'] = mouse_pos[1]
            track_height = state['chosen_content_rect'].height - state['chosen_scrollbar_handle_rect'].height
            if track_height > 0:
                 state['chosen_scroll_offset_y'] = max(0, min(state.get('chosen_scroll_offset_y', 0) + (mouse_delta_y * (state['chosen_max_scroll'] / track_height)), state['chosen_max_scroll']))
        
        elif state.get('is_dragging_prof_scrollbar'):
            mouse_delta_y = mouse_pos[1] - state['prof_scroll_drag_last_y']; state['prof_scroll_drag_last_y'] = mouse_pos[1]
            track_height = state['prof_content_rect'].height - state['prof_scrollbar_handle_rect'].height
            if track_height > 0:
                 state['prof_scroll_offset_y'] = max(0, min(state.get('prof_scroll_offset_y', 0) + (mouse_delta_y * (state['prof_max_scroll'] / track_height)), state['prof_max_scroll']))


def run_player_setup(game):
    # Initialize state on the game object the first time
    if 'base_data' not in game.player_setup_state:
        state = game.player_setup_state
        try:
            state['base_data'], trait_names = core.data.player_xml_parser.parse_player_data()
        except Exception as e:
            print(f"FATAL: Could not parse player.xml: {e}")
            game.running = False
            return
        state['all_traits'] = TRAIT_DEFINITIONS

        state['chosen_traits'] = []
        _update_available_traits(state)

        state['final_stats'] = state['base_data']['stats'].copy()
        state['final_attrs'] = state['base_data']['attributes'].copy()
        
        state['stats_scroll_offset_y'] = 0; state['stats_content_rect'] = None; state['stats_line_height'] = 25; state['stats_max_scroll'] = 0
        state['traits_scroll_offset_y'] = 0; state['traits_content_rect'] = None; state['traits_line_height'] = 35; state['traits_max_scroll'] = 0
        state['chosen_scroll_offset_y'] = 0; state['chosen_content_rect'] = None; state['chosen_max_scroll'] = 0; state['is_dragging_chosen_scrollbar'] = False; state['chosen_scroll_drag_last_y'] = 0
        
        state['is_dragging_stats_scrollbar'] = False; state['stats_scroll_drag_last_y'] = 0
        state['is_dragging_traits_scrollbar'] = False; state['traits_scroll_drag_last_y'] = 0
        state['total_trait_cost'] = 0

        Item.load_item_templates()
        Zombie.load_templates()

        state['clothes_slots'] = ['hair', 'head','legs', 'feet', 'body','util','arms', 'hands', 'facial']
        state['clothes_colors'] = {slot: (255, 255, 255) for slot in state['clothes_slots']}
        state['available_clothes'] = {slot: [] for slot in state['clothes_slots']}
        state['chosen_clothes'] = {slot: "None" for slot in state['clothes_slots']}
        state['clothing_sprites'] = {}

        for item_name, template in ITEM_TEMPLATES.items():
            if template.get('type') == 'cloth':
                
                if not template.get('builder', False):
                    continue

                slot = template.get('properties', {}).get('slot', {}).get('value')
                if slot == 'hand': slot = 'hands' 
                if slot in state['available_clothes']:
                    if not item_name.startswith("Empty"):
                        state['available_clothes'][slot].append(item_name)
                    sprite_file = template.get('properties', {}).get('sprite', {}).get('file')
                    if sprite_file:
                        try:
                            path = SPRITE_PATH + "clothes/" + sprite_file
                            img = pygame.image.load(path).convert_alpha()
                            state['clothing_sprites'][item_name] = pygame.transform.scale(img, (256, 256))
                        except Exception as e: print(f"Error loading cloth: {e}")
        for slot in state['available_clothes']: state['available_clothes'][slot].insert(0, "None")

        try:
            sprite_path = state['base_data']['visuals']['sprite']
            sprite_img = pygame.image.load(SPRITE_PATH + sprite_path).convert_alpha()
            state['player_sprite_large'] = pygame.transform.scale(sprite_img, (256, 256))
        except Exception:
            state['player_sprite_large'] = pygame.Surface((256, 256), pygame.SRCALPHA); state['player_sprite_large'].fill(BLUE)

        state['player_name'] = fake.name()
        state['name_input_active'] = False
        state['world_seed'] = ""
        state['seed_input_active'] = False
        state['preset_list'] = ["None"]
        state['selected_preset'] = "None"
        state['preset_dropdown_active'] = False
        _load_presets(state)

        if 'current_tab' not in state:
             state['current_tab'] = 'Player'

        state['settings_data'] = load_config_data("./game/save/config/config.xml")
        state['config_name'] = ""
        state['config_name_active'] = False
        state['settings_scroll_y'] = 0
        state['settings_max_scroll'] = 0
        state['is_dragging_settings_scrollbar'] = False 
        state['settings_scroll_drag_last_y'] = 0        
        state['active_setting'] = None
        state['config_dd_active'] = False
        state['prof_scroll_offset_y'] = 0 
        state['prof_content_rect'] = None 
        state['prof_max_scroll'] = 0 
        state['is_dragging_prof_scrollbar'] = False 
        state['prof_scroll_drag_last_y'] = 0

        state['config_preset_list'] = ["config"] 
        state['selected_config_preset'] = 'config'
        _load_config_presets(state)

    state = game.player_setup_state
    mouse_pos = game._get_scaled_mouse_pos()
    
    game.game_screen.fill(DARK_GRAY)
    
    sidebar_width = 150
    btn_h = 40
    player_btn = pygame.Rect(10, 30, sidebar_width, btn_h)
    settings_btn = pygame.Rect(10, 90, sidebar_width, btn_h)
    back_btn = pygame.Rect(10, GAME_HEIGHT - 91, sidebar_width, btn_h)

    p_col = GRAY_60 if state['current_tab'] == 'Player' else (40, 40, 40)
    s_col = GRAY_60 if state['current_tab'] == 'Settings' else (40, 40, 40)
    pygame.draw.rect(game.game_screen, p_col, player_btn, border_radius=4)
    pygame.draw.rect(game.game_screen, WHITE, player_btn, 1, border_radius=4)
    game.game_screen.blit(font.render("Player", True, WHITE), (player_btn.x + 10, player_btn.y + 10))
    pygame.draw.rect(game.game_screen, s_col, settings_btn, border_radius=4)
    pygame.draw.rect(game.game_screen, WHITE, settings_btn, 1, border_radius=4)
    game.game_screen.blit(font.render("Settings", True, WHITE), (settings_btn.x + 10, settings_btn.y + 10))

    b_col = GRAY_80
    pygame.draw.rect(game.game_screen, b_col, back_btn, border_radius=4)
  
    # Center text
    back_txt = font.render("Back", True, WHITE)
    txt_rect = back_txt.get_rect(center=back_btn.center)
    game.game_screen.blit(back_txt, txt_rect)

    clickable_rects = {}
    if state['current_tab'] == 'Player':
        clickable_rects = _draw_player_build_screen(game, state, mouse_pos)
    else:
        clickable_rects = _draw_settings_screen(game, state, mouse_pos)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False
            return
            
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if back_btn.collidepoint(mouse_pos):
                game.game_state = 'MENU'
                return
            if player_btn.collidepoint(mouse_pos):
                state['current_tab'] = 'Player'
                continue
            elif settings_btn.collidepoint(mouse_pos):
                state['current_tab'] = 'Settings'
                continue

        if state['current_tab'] == 'Settings':
            handle_settings_events(game, state, event, mouse_pos, clickable_rects)
        else:
            handle_player_events(game, state, event, mouse_pos, clickable_rects)

    game._update_screen()

def _load_presets(state):
    """Loads all .xml preset files from the save/player directory."""
    preset_dir = "./game/save/player"
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)
    
    presets = ["None"]
    try:
        files = [f for f in os.listdir(preset_dir) if f.endswith('.xml')]
        presets.extend([f.replace('.xml', '') for f in files])
    except Exception as e:
        print(f"Error loading presets: {e}")
        
    state['preset_list'] = presets

def _save_preset(state):
    """Saves the current traits and clothes to an XML file."""
    player_name = state.get('player_name')
    if not player_name or player_name == "Survivor":
        print("Cannot save preset with default name.")
        return 

    preset_dir = "./game/save/player"
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)
        
    filepath = os.path.join(preset_dir, f"{player_name}.xml")
    
    root = ET.Element("preset")
    
    ET.SubElement(root, "name").text = player_name
    ET.SubElement(root, "sex").text = state['base_data'].get('sex', 'Male')

    traits_node = ET.SubElement(root, "traits")
    for trait in state['chosen_traits']:
        ET.SubElement(traits_node, "trait").text = trait
        
    clothes_node = ET.SubElement(root, "clothes")
    for slot, item_name in state['chosen_clothes'].items():
        color = state['clothes_colors'].get(slot, (255, 255, 255))
        ET.SubElement(clothes_node, "slot", name=slot, r=str(color[0]), g=str(color[1]), b=str(color[2])).text = item_name

    try:
        raw_xml = ET.tostring(root, 'utf-8')
        pretty_xml = xml.dom.minidom.parseString(raw_xml).toprettyxml(indent="    ")
        
        with open(filepath, "w") as f:
            f.write(pretty_xml)
            
        print(f"Preset saved: {filepath}")
        _load_presets(state) 
        state['selected_preset'] = player_name 
    except Exception as e:
        print(f"Error saving preset: {e}")

def _load_preset(state):
    """Loads traits and clothes from a selected preset file."""
    preset_name = state.get('selected_preset')
    if not preset_name or preset_name == "None":
        return

    filepath = os.path.join("./game/save/player", f"{preset_name}.xml")
    if not os.path.exists(filepath):
        print(f"Error: Preset file not found: {filepath}")
        return

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        name_node = root.find('name')
        if name_node is not None:
            state['player_name'] = name_node.text
        
        sex_node = root.find('sex')
        if sex_node is not None:
            state['base_data']['sex'] = sex_node.text

        new_traits = []
        traits_node = root.find('traits')
        if traits_node is not None:
            new_traits = [node.text for node in traits_node.findall('trait')]
            
        state['chosen_traits'] = new_traits
        _update_available_traits(state)
        
        clothes_node = root.find('clothes')
        if clothes_node is not None:
            for node in clothes_node.findall('slot'):
                slot_name = node.attrib.get('name')
                item_name = node.text
                if slot_name in state['chosen_clothes']:
                    state['chosen_clothes'][slot_name] = item_name
                    # LOAD SAVED COLORS
                    r = int(node.attrib.get('r', 255))
                    g = int(node.attrib.get('g', 255))
                    b = int(node.attrib.get('b', 255))
                    state['clothes_colors'][slot_name] = (r, g, b)
                    
        print(f"Preset loaded: {preset_name}")
    except Exception as e:
        print(f"Error parsing preset file {filepath}: {e}")

def _delete_preset(state):
    """Deletes the currently selected preset file."""
    preset_name = state.get('selected_preset')
    if not preset_name or preset_name == "None":
        print("No preset selected to delete.")
        return

    filepath = os.path.join("./game/save/player", f"{preset_name}.xml")
    if not os.path.exists(filepath):
        print(f"Error: Preset file not found: {filepath}")
        return
        
    try:
        os.remove(filepath)
        print(f"Preset deleted: {preset_name}")
        _load_presets(state) 
        state['selected_preset'] = "None"
    except Exception as e:
        print(f"Error deleting preset: {e}")

def _randomize_character(state):
    print("Generating random character...")
    
    state['base_data']['sex'] = random.choice(['Male', 'Female'])
    if state['base_data']['sex'] == 'Male':
        state['player_name'] = fake.name_male()
    else:
        state['player_name'] = fake.name_female()
 
    all_profs = [t for t in state['all_traits'] if state['all_traits'][t].get('is_profession')]
    all_traits = [t for t in state['all_traits'] if not state['all_traits'][t].get('is_profession')]
    
    new_traits = []
    
    # Pick 1 Profession
    if all_profs:
        chosen_prof = random.choice(all_profs)
        new_traits.append(chosen_prof)
        disabled_ids = state['all_traits'][chosen_prof].get('conflicts', [])
        all_traits = [t for t in all_traits if t not in disabled_ids]
    
    # Randomize Traits
    pos_traits = [t for t in all_traits if state['all_traits'][t]['cost'] > 0]
    neg_traits = [t for t in all_traits if state['all_traits'][t]['cost'] < 0]
    
    num_pos = random.randint(1, 2)
    num_neg = random.randint(0, 1)
    
    if pos_traits: new_traits.extend(random.sample(pos_traits, min(num_pos, len(pos_traits))))
    if neg_traits: new_traits.extend(random.sample(neg_traits, min(num_neg, len(neg_traits))))
    
    state['chosen_traits'] = new_traits
    _update_available_traits(state)
    
    # 3. Randomize Clothes
    available_clothes = state['available_clothes']
    chosen_clothes = {}
    available_colors = list(CLOTHING_COLORS)
    random.shuffle(available_colors)
    
    for slot, options in available_clothes.items():
        if options:
            if slot == 'facial' and state['base_data']['sex'] == 'Female':
                chosen_item = "None"
            else:
                valid_options = options
                if slot in ['body', 'legs', 'feet']:
                    valid_options = [opt for opt in options if opt != "None"]
                    if not valid_options: valid_options = options
                        
                chosen_item = random.choice(valid_options)
                
            chosen_clothes[slot] = chosen_item
            
            if slot in VALID_COLOR_ITEMS and chosen_item in VALID_COLOR_ITEMS[slot]:
                if available_colors:
                    state['clothes_colors'][slot] = available_colors.pop()
                else:
                    state['clothes_colors'][slot] = random.choice(CLOTHING_COLORS)
            else:
                state['clothes_colors'][slot] = (255, 255, 255)
        else:
            chosen_clothes[slot] = "None"
            state['clothes_colors'][slot] = (255, 255, 255)
            
    state['chosen_clothes'] = chosen_clothes
    state['selected_preset'] = "None"