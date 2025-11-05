import pygame
import xml.etree.ElementTree as ET
import os
import xml.dom.minidom
from data.config import *
import data.player_xml_parser
from core.entities.item.item import Item, ITEM_TEMPLATES
import random
from faker import Faker
fake = Faker()

TRAIT_DEFINITIONS = {
    "vaccine": {"cost": 1, "stats": {"infection": -15}}, # Example cost, adjust as needed
    "athletic": {"cost": 2, "stats": {"stamina": 10}}, # XML says -10%, let's make it +10%
    "strong": {"cost": 2, "attributes": {"strength": 2}},
    "weak": {"cost": -2, "attributes": {"strength": -2}},
    "luck": {"cost": 2, "attributes": {"lucky": 1}}, # Bonus logic is in progression
    "unlucky": {"cost": -2, "attributes": {"lucky": -1}},
    "runner": {"cost": 1, "attributes": {"speed": 1}},
    "smoker": {"cost": -1, "stats": {"stamina": -15, "anxiety": 15}},
    "drunk": {"cost": -1, "attributes": {"speed": -15}, "stats": {"anxiety": 15}},
    "illnes": {"cost": -1, "stats": {"infection": 15}}, # This is infection rate, logic not fully here
    "sedentary": {"cost": -2, "stats": {"stamina": -15}, "attributes": {"strength": -2}},
    "myopia": {"cost": -1, "attributes": {"ranged": -10}},
    "collateral_effect": {"cost": -5, "attributes": {"strength": -1, "fitness": -1, "ranged": -1, "melee": -1}, "stats": {"health": -30, "infection": 60,"stamina": -15, "anxiety": 15}}, # Vaccine colateral effect: -1 stregth, -1 fitness, -1 ranged, -1 melee, -30 health, -60 infection, -15 stamina, +15 anxiety
}

# cached logo image
_logo_img = None
_stat_icons_cache = {}
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
        "ranged": SPRITE_PATH + "ui/range.png",
        "lucky": SPRITE_PATH + "ui/lucky.png",
        "speed": SPRITE_PATH + "ui/speed.png",
    }
    
    for key, path in icon_files.items():
        img = pygame.image.load(path).convert_alpha()
        _stat_icons_cache[key] = pygame.transform.scale(img, icon_size)

# Buttons and status modal
_inventory_img = None
_status_img = None
def draw_inventory_button(surface):
    global _inventory_img
    if _inventory_img is None:
        try:
            _inventory_img = pygame.image.load(SPRITE_PATH + 'ui/inventory.png').convert_alpha()
            _inventory_img = pygame.transform.scale(_inventory_img, (40, 40))
        except pygame.error:
            _inventory_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _inventory_img.fill(GRAY)
    button_inventory_rect = pygame.Rect(10, 50, 60, 60)
    surface.blit(_inventory_img, button_inventory_rect)
    return button_inventory_rect

def draw_status_button(surface):
    global _status_img
    if _status_img is None:
        try:
            _status_img = pygame.image.load(SPRITE_PATH + 'ui/status.png').convert_alpha()
            _status_img = pygame.transform.scale(_status_img, (40, 40))
        except pygame.error:
            _status_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _status_img.fill(GRAY)
    button_rect = pygame.Rect(10, 10, 40, 40)
    surface.blit(_status_img, button_rect)
    return button_rect

_nearby_img = None
def draw_nearby_button(surface):
    global _nearby_img
    if _nearby_img is None:
        try:
            _nearby_img = pygame.image.load(SPRITE_PATH + 'ui/nearby.png').convert_alpha()
            _nearby_img = pygame.transform.scale(_nearby_img, (40, 40))
        except pygame.error:
            _nearby_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _nearby_img.fill(GRAY)
    button_nearby_rect = pygame.Rect(10, 110, 60, 60)
    surface.blit(_nearby_img, button_nearby_rect)
    return button_nearby_rect


def draw_menu(screen):
    global _logo_img
    screen.fill(DARK_GRAY)

    # try to load and draw logo image instead of text title
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load(SPRITE_PATH + 'ui/logo.png').convert_alpha()
            logo_w = 300
            logo_h = int(_logo_img.get_height() * (logo_w / _logo_img.get_width()))
            _logo_img = pygame.transform.scale(_logo_img, (logo_w, logo_h))
    except Exception:
        _logo_img = None

    if _logo_img:
        title_rect = _logo_img.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
        screen.blit(_logo_img, title_rect)
    else:
        title_text = title_font.render("Bit Rot", True, RED)
        title_rect = title_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
        screen.blit(title_text, title_rect)

    start_text = large_font.render("START", True, WHITE)
    start_rect = start_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2))
    quit_text = large_font.render("QUIT", True, WHITE)
    quit_rect = quit_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 + 60))
    mouse_pos = pygame.mouse.get_pos()
    scale_x = VIRTUAL_SCREEN_WIDTH / screen.get_width()
    scale_y = VIRTUAL_GAME_HEIGHT / screen.get_height()
    scaled_mouse_pos = (mouse_pos[0] * scale_x, mouse_pos[1] * scale_y)
    if start_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, start_rect.inflate(20, 10))
    if quit_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, quit_rect.inflate(20, 10))
    screen.blit(start_text, start_rect)
    screen.blit(quit_text, quit_rect)
    return start_rect, quit_rect

def draw_game_over(screen, zombies_killed):
    screen.fill(DARK_GRAY)
    # draw same logo at top for game over screen (fallback to text if missing)
    global _logo_img
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load(SPRITE_PATH + 'ui/logo.png').convert_alpha()
            logo_w = 300
            logo_h = int(_logo_img.get_height() * (logo_w / _logo_img.get_width()))
            _logo_img = pygame.transform.scale(_logo_img, (logo_w, logo_h))
    except Exception:
        _logo_img = None

    if _logo_img:
        title_rect = _logo_img.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
        screen.blit(_logo_img, title_rect)
    else:
        title_text = title_font.render("YOU DIED", True, RED)
        title_rect = title_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
        screen.blit(title_text, title_rect)

    score_text = large_font.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
    score_rect = score_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 - 60))
    screen.blit(score_text, score_rect)
    restart_text = large_font.render("Restart", True, WHITE)
    restart_rect = restart_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 + 20))
    quit_text = large_font.render("Quit", True, WHITE)
    quit_rect = quit_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 + 80))
    mouse_pos = pygame.mouse.get_pos()
    scale_x = VIRTUAL_SCREEN_WIDTH / screen.get_width()
    scale_y = VIRTUAL_GAME_HEIGHT / screen.get_height()
    scaled_mouse_pos = (mouse_pos[0] * scale_x, mouse_pos[1] * scale_y)
    if restart_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, restart_rect.inflate(20, 10))
    if quit_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, quit_rect.inflate(20, 10))
    screen.blit(restart_text, restart_rect)
    screen.blit(quit_text, quit_rect)
    return restart_rect, quit_rect


# This function is no longer used, but we keep it in case other parts of the code still reference it.
def _parse_player_xml_data(xml_string):
    """(DEPRECATED) Parses the player.xml string and returns base data."""
    root = ET.fromstring(xml_string)
    base_data = {"stats": {}, "attributes": {}, "initial_loot": [], "visuals": {}}
    base_data["name"] = root.find("name").get("value")
    base_data["sex"] = root.find("sex").get("value")
    base_data["profession"] = root.find("profession").get("value")
    for stat in root.find("stats"): base_data["stats"][stat.tag] = float(stat.get("value"))
    for attr in root.find("attributes"): base_data["attributes"][attr.tag] = float(attr.get("value"))
    sprite_node = root.find("visuals/sprite")
    if sprite_node is not None: base_data["visuals"]["sprite"] = sprite_node.get("file")
    trait_names = [trait.tag for trait in root.find("traits")]
    return base_data, trait_names



def _draw_dropdown(surface, state, slot_name, rect, mouse_pos):
    """Draws a single dropdown menu and its options if active."""
    clickable_rects = {
        'button': rect,
        'options': [] # List of (option_name, rect)
    }
    
    # 1. Draw the main button
    pygame.draw.rect(surface, (50, 50, 50), rect)
    pygame.draw.rect(surface, WHITE, rect, 1)
    
    selected_item = state['chosen_clothes'].get(slot_name, "None") or "None"
    text = font.render(selected_item, True, WHITE)
    surface.blit(text, (rect.x + 5, rect.y + 5))
    
    # Draw arrow
    pygame.draw.polygon(surface, WHITE, [(rect.right - 15, rect.y + 10), (rect.right - 5, rect.y + 10), (rect.right - 10, rect.y + 15)])

    # 2. Check if this dropdown is active
    if state.get('active_dropdown') == slot_name:
        options = state['available_clothes'].get(slot_name, [])
        if not options:
            return clickable_rects # No options to draw
            
        option_height = 25
        
        # --- NEW: SCROLLING LOGIC ---
        max_options_visible = 4 # Max items to show before scrolling
        max_list_height = max_options_visible * option_height
        
        total_options_height = len(options) * option_height
        
        # Determine final list height (clamped)
        list_height = min(max_list_height, total_options_height)
        
        # Get scroll state for this *specific* dropdown
        scroll_state = state['gear_dropdown_scrolls'][slot_name]
        max_scroll_offset = max(0, total_options_height - list_height)
        scroll_state['max_scroll'] = max_scroll_offset
        
        # Clamp offset
        scroll_offset_y = max(0, min(scroll_state['offset'], max_scroll_offset))
        scroll_state['offset'] = scroll_offset_y
        
        # Define rects
        list_rect = pygame.Rect(rect.x, rect.bottom, rect.width, list_height)
        # --- FIX: Content rect needs to be clipped by the *screen* edge ---
        if list_rect.bottom > VIRTUAL_GAME_HEIGHT:
            list_rect.height = VIRTUAL_GAME_HEIGHT - list_rect.top
        
        content_rect = pygame.Rect(list_rect.x, list_rect.y, list_rect.width - 10, list_rect.height) # Room for scrollbar
        
        # --- FIX: Handle ValueError by clipping content_rect to surface ---
        drawable_rect = surface.get_rect().clip(content_rect)
        if drawable_rect.width <= 0 or drawable_rect.height <= 0:
             return clickable_rects # Cannot draw subsurface
             
        # Create clipping subsurface
        content_surface = surface.subsurface(drawable_rect)
        content_surface.fill((30, 30, 30))
        
        # Draw options onto subsurface
        y_offset = 0 - scroll_offset_y
        for option_name in options:
            option_rect_rel = pygame.Rect(0, y_offset, content_rect.width, option_height)
            
            # Get screen-space rect for hover/click
            option_rect_abs = pygame.Rect(content_rect.x, content_rect.y + y_offset, content_rect.width, option_height)
            
            # Draw highlight only if visible
            if option_rect_abs.bottom > content_rect.top and option_rect_abs.top < content_rect.bottom:
                if option_rect_abs.collidepoint(mouse_pos):
                    pygame.draw.rect(content_surface, (70, 70, 70), option_rect_rel)
                
                text = font.render(option_name, True, WHITE)
                content_surface.blit(text, (option_rect_rel.x + 5, option_rect_rel.y + 2))
            
            # Add the *absolute* screen rect for click detection
            clickable_rects['options'].append((option_name, option_rect_abs))
            y_offset += option_height

        # Draw Scrollbar
        if total_options_height > list_height:
            scrollbar_area_rect = pygame.Rect(content_rect.right, list_rect.top, 10, list_rect.height)
            
            handle_height_ratio = list_height / total_options_height
            handle_height = max(10, scrollbar_area_rect.height * handle_height_ratio)
            
            handle_pos_ratio = 0
            if max_scroll_offset > 0:
                 handle_pos_ratio = scroll_offset_y / max_scroll_offset
            
            handle_y = scrollbar_area_rect.top + (scrollbar_area_rect.height - handle_height) * handle_pos_ratio
            
            handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
            pygame.draw.rect(surface, GRAY, handle_rect, 0, 2)
            scroll_state['handle_rect'] = handle_rect # Store for click/drag
        else:
            scroll_state['handle_rect'] = None
        # --- END SCROLLING LOGIC ---

    return clickable_rects

def _draw_player_build_screen(game, state, mouse_pos):
    """Draws the three-column layout and returns clickable rects."""
    game.virtual_screen.fill(DARK_GRAY)
    
    clickable_rects = {
        "add_trait": [], 
        "remove_trait": [],
        "start_button": None,
        "dropdown_buttons": {},
        "dropdown_options": [],
        "name_input": None,
        "save_button": None,
        "delete_button": None,
        "load_dropdown_button": None,
        "load_dropdown_options": [],
        "random_button": None
    }
    header_height = 30 # Height for the new title bars
    border_radius = 4

    _load_stat_icons()
    icon_padding = 24


    col1_x = 50
    col1_width = 280
    col2_x = col1_x + col1_width + 20 # 350
    col2_width = 280
    col3_x = col2_x + col2_width + 20 # 650
    col3_width = 280
    col4_x = col3_x + col3_width + 20 # 950
    col4_width = 280 # Adjusted to fit

    padding = 10
    
    # --- Column 1, Block 1: Preset Management Panel (Top-Left) ---
    #preset_rect = pygame.Rect(col1_x, 50, col1_width, 170)
    #pygame.draw.rect(game.virtual_screen, (30, 30, 30), preset_rect)
    #pygame.draw.rect(game.virtual_screen, WHITE, preset_rect, 1, border_top_left_radius=4, border_top_right_radius=4,border_bottom_left_radius=4, border_bottom_right_radius=4)
    preset_rect = pygame.Rect(col1_x, 50, col1_width, 210)

    preset_header_rect = pygame.Rect(preset_rect.x, preset_rect.y, preset_rect.width, header_height)
    preset_body_rect = pygame.Rect(preset_rect.x, preset_rect.y + header_height, preset_rect.width, preset_rect.height - header_height)
    
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), preset_body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, preset_header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, preset_rect, 1, border_radius=border_radius)
    game.virtual_screen.blit(font.render("Preset", True, WHITE), (preset_header_rect.x + 10, preset_header_rect.y + 7))

    # 1. Name Input
    game.virtual_screen.blit(font.render("Player Name:", True, WHITE), (preset_body_rect.x + padding, preset_body_rect.y + 10))
    name_input_rect = pygame.Rect(preset_body_rect.x + padding, preset_body_rect.y + 35, preset_body_rect.width - padding*2, 30)
    pygame.draw.rect(game.virtual_screen, (50, 50, 50), name_input_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, name_input_rect, 1)
    
    name_text = state.get('player_name', "Survivor")
    text_surf = font.render(name_text, True, WHITE)
    game.virtual_screen.blit(text_surf, (name_input_rect.x + 5, name_input_rect.y + 5))
    
    if state.get('name_input_active') and int(pygame.time.get_ticks() / 500) % 2 == 0:
        cursor_x = name_input_rect.x + 5 + text_surf.get_width()
        pygame.draw.line(game.virtual_screen, WHITE, (cursor_x, name_input_rect.y + 5), (cursor_x, name_input_rect.bottom - 5), 2)
    
    clickable_rects['name_input'] = name_input_rect

    # 2. Buttons
    btn_width = 80
    # Calculate padding between buttons
    btn_padding = (preset_body_rect.width - (btn_width * 3) - (padding * 2)) // 2
    
    save_btn_rect = pygame.Rect(preset_body_rect.x + padding, preset_body_rect.y + 80, btn_width, 30)
    pygame.draw.rect(game.virtual_screen, GREEN, save_btn_rect)
    game.virtual_screen.blit(font.render("Save", True, WHITE), (save_btn_rect.x + 20, save_btn_rect.y + 5))
    clickable_rects['save_button'] = save_btn_rect
    
    random_btn_rect = pygame.Rect(save_btn_rect.right + btn_padding, preset_body_rect.y + 80, btn_width, 30)
    pygame.draw.rect(game.virtual_screen, (0, 100, 150), random_btn_rect) # Blue-ish color
    game.virtual_screen.blit(font.render("Random", True, WHITE), (random_btn_rect.x + 10, random_btn_rect.y + 5))
    clickable_rects['random_button'] = random_btn_rect

    delete_btn_rect = pygame.Rect(random_btn_rect.right + btn_padding, preset_body_rect.y + 80, btn_width, 30)
    pygame.draw.rect(game.virtual_screen, RED, delete_btn_rect)
    game.virtual_screen.blit(font.render("Delete", True, WHITE), (delete_btn_rect.x + 15, delete_btn_rect.y + 5))
    clickable_rects['delete_button'] = delete_btn_rect
    
    # 3. Load Dropdown
    load_dd_rect = pygame.Rect(preset_body_rect.x + padding, preset_body_rect.y + 125, preset_body_rect.width - padding*2, 30)
    clickable_rects['load_dropdown_button'] = load_dd_rect
    
 

    # --- Column 1, Block 2: Gear Selection (Bottom-Left) ---
    gear_rect = pygame.Rect(col1_x, preset_rect.bottom + 20, col1_width, 410) # Bottom half

    gear_header_rect = pygame.Rect(gear_rect.x, gear_rect.y, gear_rect.width, header_height)
    gear_body_rect = pygame.Rect(gear_rect.x, gear_rect.y + header_height, gear_rect.width, gear_rect.height - header_height)

    pygame.draw.rect(game.virtual_screen, (30, 30, 30), gear_body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, gear_header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, gear_rect, 1, border_radius=border_radius)
    game.virtual_screen.blit(font.render("Clothes", True, WHITE), (gear_header_rect.x + 10, gear_header_rect.y + 7))

    gear_content_rect = pygame.Rect(
        gear_rect.x + padding,
        gear_rect.y + 40, 
        gear_rect.width - (padding * 2), # Use full width
        gear_rect.height - (padding * 2) - 30
    )
    state['gear_content_rect'] = gear_content_rect 

    # Create Subsurface for clipping
    drawable_gear_rect = game.virtual_screen.get_rect().clip(gear_content_rect)
    dropdown_draw_list = [] # Store (slot_name, rect) to draw buttons later
    
    if drawable_gear_rect.width > 0 and drawable_gear_rect.height > 0:
        gear_content_surface = game.virtual_screen.subsurface(drawable_gear_rect)
        gear_content_surface.fill((30, 30, 30))

        label_width = 80
        dropdown_width = col1_width - label_width - (padding * 3)
        
        y_offset = 0 # Start relative to subsurface
        
        for slot_name in state['clothes_slots']: # Iterate in correct order
            dropdown_rect = pygame.Rect(
                gear_content_rect.x + label_width + (padding * 2), 
                gear_content_rect.y + y_offset, 
                dropdown_width, 
                25
            )
            
            if dropdown_rect.bottom > gear_content_rect.top and dropdown_rect.top < gear_content_rect.bottom:
                gear_content_surface.blit(font.render(f"{slot_name.capitalize()}:", True, WHITE), (0, y_offset + 5))
                dropdown_draw_list.append((slot_name, dropdown_rect))
            
            y_offset += 35 # Use fixed line height


    # --- Column 2: Available Traits (Middle-Left) ---
    available_rect = pygame.Rect(col2_x, 50, col2_width, 640) # Full height
    avail_header_rect = pygame.Rect(available_rect.x, available_rect.y, available_rect.width, header_height)
    avail_body_rect = pygame.Rect(available_rect.x, available_rect.y + header_height, available_rect.width, available_rect.height - header_height)
    
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), avail_body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, avail_header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, available_rect, 1, border_radius=border_radius)
    game.virtual_screen.blit(font.render("Available Traits", True, WHITE), (avail_header_rect.x + 10, avail_header_rect.y + 7))

    y_offset = available_rect.y + 40
    for i, trait_name in enumerate(state['available_traits']):
        row_rect = pygame.Rect(available_rect.x + 10, y_offset, available_rect.width - 20, 30)
        game.virtual_screen.blit(font.render(trait_name.capitalize(), True, WHITE), (row_rect.x, row_rect.y))
        add_btn_rect = pygame.Rect(row_rect.right - 25, row_rect.y, 25, 25)
        pygame.draw.rect(game.virtual_screen, GREEN, add_btn_rect)
        game.virtual_screen.blit(font.render(">", True, WHITE), (add_btn_rect.x + 7, add_btn_rect.y + 2))
        clickable_rects["add_trait"].append((trait_name, add_btn_rect))
        y_offset += 35
        if y_offset > available_rect.bottom - 30: break


    # --- Column 3: Chosen Traits (Middle-Right) ---
    chosen_rect = pygame.Rect(col3_x, 50, col3_width, 640) # Full height
    # --- MODIFICATION: Draw styled panel (from your snippet) ---
    header_height = 30
    header_rect = pygame.Rect(chosen_rect.x, chosen_rect.y, chosen_rect.width, header_height)
    body_rect = pygame.Rect(chosen_rect.x, chosen_rect.y + header_height, chosen_rect.width, chosen_rect.height - header_height)
    
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, chosen_rect, 1, border_radius=border_radius)
    game.virtual_screen.blit(font.render("Chosen Traits", True, WHITE), (header_rect.x + 10, header_rect.y + 7)) # Adjusted y for padding

    y_offset = chosen_rect.y + 40
    for i, trait_name in enumerate(state['chosen_traits']):
        row_rect = pygame.Rect(chosen_rect.x + 10, y_offset, chosen_rect.width - 20, 30)
        remove_btn_rect = pygame.Rect(row_rect.x, row_rect.y, 25, 25)
        pygame.draw.rect(game.virtual_screen, RED, remove_btn_rect)
        game.virtual_screen.blit(font.render("<", True, WHITE), (remove_btn_rect.x + 7, remove_btn_rect.y + 2))
        clickable_rects["remove_trait"].append((trait_name, remove_btn_rect))
        game.virtual_screen.blit(font.render(trait_name.capitalize(), True, WHITE), (remove_btn_rect.right + 10, row_rect.y))
        y_offset += 35
        if y_offset > chosen_rect.bottom - 30: break


    # --- Column 4: Player Sprite (Top-Right) & Stats (Bottom-Right) ---
    
    # Block 4.1: Sprite
    sprite_rect_container = pygame.Rect(col4_x, 50, col4_width, 310) # Top half
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), sprite_rect_container)
    pygame.draw.rect(game.virtual_screen, WHITE, sprite_rect_container, 1,border_top_left_radius=4, border_top_right_radius=4,border_bottom_left_radius=4, border_bottom_right_radius=4)
    
    if state.get('player_sprite_large'):
        sprite_rect = state['player_sprite_large'].get_rect(center=sprite_rect_container.center)
        game.virtual_screen.blit(state['player_sprite_large'], sprite_rect)
        
        for slot in state['clothes_slots']: 
            item_name = state['chosen_clothes'].get(slot)
            if item_name and item_name != "None":
                clothing_img = state['clothing_sprites'].get(item_name)
                if clothing_img:
                    game.virtual_screen.blit(clothing_img, sprite_rect)

    # Block 4.2: Current Stats
    stats_rect = pygame.Rect(col4_x, sprite_rect_container.bottom + 20, col4_width, 240) # Bottom half (smaller)
    stats_header_rect = pygame.Rect(stats_rect.x, stats_rect.y, stats_rect.width, header_height)
    stats_body_rect = pygame.Rect(stats_rect.x, stats_rect.y + header_height, stats_rect.width, stats_rect.height - header_height)

    pygame.draw.rect(game.virtual_screen, (30, 30, 30), stats_body_rect, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, stats_header_rect, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, stats_rect, 1, border_radius=border_radius)
    game.virtual_screen.blit(font.render("Current Stats", True, WHITE), (stats_header_rect.x + 10, stats_header_rect.y + 7))

    stats_content_rect = pygame.Rect(stats_rect.x + padding, stats_rect.y + 40, stats_rect.width - (padding * 2) - 10, stats_rect.height - (padding * 2) - 30)
    state['stats_content_rect'] = stats_content_rect
    current_stats = state['base_data']['stats'].copy()
    current_attrs = state['base_data']['attributes'].copy()
    for trait_name in state['chosen_traits']:
        effects = TRAIT_DEFINITIONS.get(trait_name, {})
        if "stats" in effects:
            for stat, value in effects["stats"].items(): current_stats[stat] = current_stats.get(stat, 0) + value
        if "attributes" in effects:
            for attr, value in effects["attributes"].items(): current_attrs[attr] = current_attrs.get(attr, 0) + value
    state['final_stats'] = current_stats
    state['final_attrs'] = current_attrs
    line_height = 25
    state['stats_line_height'] = line_height
    total_text_height = (len(current_stats) + len(current_attrs)) * line_height
    visible_height = stats_content_rect.height
    max_scroll_offset = max(0, total_text_height - visible_height)
    state['stats_max_scroll'] = max_scroll_offset
    scroll_offset_y = max(0, min(state.get('stats_scroll_offset_y', 0), max_scroll_offset))
    state['stats_scroll_offset_y'] = scroll_offset_y
    
    drawable_stats_rect = game.virtual_screen.get_rect().clip(stats_content_rect)
    if drawable_stats_rect.width > 0 and drawable_stats_rect.height > 0:
        content_surface = game.virtual_screen.subsurface(drawable_stats_rect)
        content_surface.fill((30, 30, 30))
        y_offset = 0 - scroll_offset_y
        for stat, value in current_stats.items():
            icon = _stat_icons_cache.get(stat)
            if icon:
                content_surface.blit(icon, (0, y_offset + (line_height - icon.get_height()) // 2))
                text_x = icon_padding
            else:
                text_x = 0 # No icon, start text at left edge
            
            # Format value
            val_str = f"{value:.1f}" if value != 0 else "0.0"
            text_surf = font.render(f"{stat.capitalize()}: {val_str}", True, WHITE)
            content_surface.blit(text_surf, (text_x, y_offset +3))
            y_offset += line_height

        for attr, value in current_attrs.items():
            icon = _stat_icons_cache.get(attr)
            if icon:
                content_surface.blit(icon, (0, y_offset + (line_height - icon.get_height()) // 2))
                text_x = icon_padding
            else:
                text_x = 0
                
            val_str = f"{value:.1f}" if value != 0 else "0.0"
            text_surf = font.render(f"{attr.capitalize()}: {val_str}", True, WHITE)
            content_surface.blit(text_surf, (text_x, y_offset))
            y_offset += line_height
    
    # Draw Stats Scrollbar
    if total_text_height > visible_height:
        scrollbar_area_height = stats_content_rect.height
        scrollbar_area_rect = pygame.Rect(stats_content_rect.right + 2, stats_content_rect.top, 8, scrollbar_area_height)
        handle_height_ratio = visible_height / total_text_height
        handle_height = max(10, scrollbar_area_height * handle_height_ratio)
        handle_pos_ratio = 0
        if max_scroll_offset > 0: handle_pos_ratio = scroll_offset_y / max_scroll_offset
        handle_y = scrollbar_area_rect.top + (scrollbar_area_height - handle_height) * handle_pos_ratio
        
        stats_scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        pygame.draw.rect(game.virtual_screen, GRAY, stats_scrollbar_handle_rect, 0, 2)
        state['stats_scrollbar_handle_rect'] = stats_scrollbar_handle_rect 
    else:
        state['stats_scrollbar_handle_rect'] = None


    # --- Start Button (Bottom Right) ---
    start_btn_rect = pygame.Rect(col4_x, stats_rect.bottom + 20, col4_width, 70) # Below stats
    pygame.draw.rect(game.virtual_screen, (0, 100, 0), start_btn_rect, border_top_left_radius=4, border_top_right_radius=4,border_bottom_left_radius=4, border_bottom_right_radius=4)
    if start_btn_rect.collidepoint(mouse_pos):
        pygame.draw.rect(game.virtual_screen, (0, 150, 0), start_btn_rect.inflate(-4, -4))
    start_text = large_font.render("START GAME", True, WHITE)
    text_rect = start_text.get_rect(center=start_btn_rect.center)
    game.virtual_screen.blit(start_text, text_rect)
    clickable_rects["start_button"] = start_btn_rect

    # --- Draw dropdowns LAST (so they appear on top) ---
    active_dropdown_slot = state.get('active_dropdown')
    active_preset_dropdown = state.get('preset_dropdown_active', False)
    
    # 1. Draw Gear Dropdowns
    for slot_name, rect in dropdown_draw_list:
        dropdown_rects = _draw_dropdown(game.virtual_screen, state, slot_name, rect, mouse_pos)
        clickable_rects['dropdown_buttons'][slot_name] = dropdown_rects['button']

    # 2. Draw Load Preset Dropdown Button
    pygame.draw.rect(game.virtual_screen, (50, 50, 50), load_dd_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, load_dd_rect, 1)
    selected_preset = state.get('selected_preset', "None")
    game.virtual_screen.blit(font.render(selected_preset, True, WHITE), (load_dd_rect.x + 5, load_dd_rect.y + 5))
    pygame.draw.polygon(game.virtual_screen, WHITE, [(load_dd_rect.right - 15, load_dd_rect.y + 10), (load_dd_rect.right - 5, load_dd_rect.y + 10), (load_dd_rect.right - 10, load_dd_rect.y + 15)])
    
    # 3. Draw OPEN Gear Dropdown List
    if active_dropdown_slot:
        for slot_name, rect in dropdown_draw_list:
            if slot_name == active_dropdown_slot:
                # --- Manually draw the option list on top of everything ---
                options = state['available_clothes'].get(slot_name, [])
                option_height = 25
                max_options_visible = 6 
                max_list_height = max_options_visible * option_height
                total_options_height = len(options) * option_height
                list_height = min(max_list_height, total_options_height)
                list_rect = pygame.Rect(rect.x, rect.bottom, rect.width, list_height)
                if list_rect.bottom > VIRTUAL_GAME_HEIGHT:
                    list_rect.height = VIRTUAL_GAME_HEIGHT - list_rect.top
                
                content_rect = pygame.Rect(list_rect.x, list_rect.y, list_rect.width - 10, list_rect.height)
                pygame.draw.rect(game.virtual_screen, (30, 30, 30), list_rect)
                pygame.draw.rect(game.virtual_screen, WHITE, list_rect, 1)

                drawable_rect = game.virtual_screen.get_rect().clip(content_rect)
                if drawable_rect.width <= 0 or drawable_rect.height <= 0: break
                    
                content_surface = game.virtual_screen.subsurface(drawable_rect)
                content_surface.fill((30, 30, 30))
                
                scroll_state = state['gear_dropdown_scrolls'][slot_name]
                scroll_offset_y = scroll_state['offset']
                
                y_offset = 0 - scroll_offset_y
                clickable_rects["dropdown_options"] = [] 
                for option_name in options:
                    option_rect_rel = pygame.Rect(0, y_offset, content_rect.width, option_height)
                    option_rect_abs = pygame.Rect(content_rect.x, content_rect.y + y_offset, content_rect.width, option_height)
                    
                    if option_rect_abs.bottom > content_rect.top and option_rect_abs.top < content_rect.bottom:
                        if option_rect_abs.collidepoint(mouse_pos):
                            pygame.draw.rect(content_surface, (70, 70, 70), option_rect_rel)
                        text = font.render(option_name, True, WHITE)
                        content_surface.blit(text, (option_rect_rel.x + 5, option_rect_rel.y + 2))
                    
                    clickable_rects['dropdown_options'].append((slot_name, option_name, option_rect_abs))
                    y_offset += option_height
                
                handle_rect = scroll_state.get('handle_rect')
                if handle_rect:
                    pygame.draw.rect(game.virtual_screen, GRAY, handle_rect, 0, 2)
                break
    
    # 4. Draw OPEN Load Preset Dropdown List
    if active_preset_dropdown:
        options = state.get('preset_list', ["None"])
        option_height = 25
        list_height = len(options) * option_height
        list_rect = pygame.Rect(load_dd_rect.x, load_dd_rect.bottom, load_dd_rect.width, list_height)
        
        pygame.draw.rect(game.virtual_screen, (30, 30, 30), list_rect)
        pygame.draw.rect(game.virtual_screen, WHITE, list_rect, 1)
        
        y_offset = list_rect.y
        clickable_rects["load_dropdown_options"] = []
        for option_name in options:
            option_rect = pygame.Rect(list_rect.x, y_offset, list_rect.width, option_height)
            if option_rect.collidepoint(mouse_pos):
                pygame.draw.rect(game.virtual_screen, (70, 70, 70), option_rect)
            
            text = font.render(option_name, True, WHITE)
            game.virtual_screen.blit(text, (option_rect.x + 5, option_rect.y + 2))
            clickable_rects["load_dropdown_options"].append((option_name, option_rect))
            y_offset += option_height

    return clickable_rects

def run_player_setup(game):
    # Initialize state on the game object the first time
    if 'base_data' not in game.player_setup_state:
        state = game.player_setup_state
        try:
            # MODIFICATION: Use the imported parser
            state['base_data'], trait_names = data.player_xml_parser.parse_player_data()
        except Exception as e:
            print(f"FATAL: Could not parse player.xml: {e}")
            game.running = False # Can't continue if player file fails
            return
        state['all_traits'] = TRAIT_DEFINITIONS
        state['available_traits'] = [t for t in trait_names if t in TRAIT_DEFINITIONS]
        state['chosen_traits'] = []
        state['final_stats'] = state['base_data']['stats'].copy()
        state['final_attrs'] = state['base_data']['attributes'].copy()
        
        # Stats scroll
        state['stats_scroll_offset_y'] = 0
        state['stats_content_rect'] = None
        state['stats_line_height'] = 25
        state['stats_max_scroll'] = 0
        state['is_dragging_stats_scrollbar'] = False
        state['stats_scroll_drag_last_y'] = 0
        
        Item.load_item_templates()

        state['clothes_slots'] = ['head','legs', 'feet',  'torso' ,'body', 'hands']
        
        state['available_clothes'] = {slot: [] for slot in state['clothes_slots']}
        state['chosen_clothes'] = {slot: "None" for slot in state['clothes_slots']}
        state['active_dropdown'] = None
        
        state['gear_dropdown_scrolls'] = {
            slot: {
                'offset': 0, 
                'is_dragging': False, 
                'last_y': 0, 
                'handle_rect': None, 
                'max_scroll': 0
            } for slot in state['clothes_slots']
        }

        state['clothing_sprites'] = {} # Cache for clothing images


        state['gear_dropdown_scrolls'] = {
            slot: {
                'offset': 0, 'is_dragging': False, 'last_y': 0, 
                'handle_rect': None, 'max_scroll': 0
            } for slot in state['clothes_slots']
        }

        player_sprite_size = (128, 128) # Your original code used 128x128

        for item_name, template in ITEM_TEMPLATES.items():
            if template.get('type') == 'cloth':
                slot = template.get('properties', {}).get('slot', {}).get('value')

                if slot == 'hand': slot = 'hands' 
                
                if slot in state['available_clothes']:

                    if not item_name.startswith("Empty"):
                        state['available_clothes'][slot].append(item_name)
                  
                    # Pre-load and scale the sprite
                    sprite_file = template.get('properties', {}).get('sprite', {}).get('file')
                    if sprite_file:
                        try:
                            path = SPRITE_PATH + "clothes/" + sprite_file
                            img = pygame.image.load(path).convert_alpha()
                            scaled_img = pygame.transform.scale(img, (256, 256))
                            state['clothing_sprites'][item_name] = scaled_img
                        except Exception as e:
                            print(f"Error loading cloth sprite {sprite_file}: {e}")

        # Add "None" option to each slot
        for slot in state['available_clothes']:
            state['available_clothes'][slot].insert(0, "None")

    
        # Load the player sprite
        try:
            sprite_path = state['base_data']['visuals']['sprite']
            sprite_img = pygame.image.load(SPRITE_PATH + sprite_path).convert_alpha()
            state['player_sprite_large'] = pygame.transform.scale(sprite_img, (256, 256))
        except Exception as e:
            print(f"Error loading player sprite for setup: {e}")
            state['player_sprite_large'] = pygame.Surface((256, 256), pygame.SRCALPHA)
            state['player_sprite_large'].fill(BLUE) # Fallback


        state['player_name'] = fake.name()
        state['name_input_active'] = False
        state['preset_list'] = ["None"]
        state['selected_preset'] = "None"
        state['preset_dropdown_active'] = False
        _load_presets(state) # Load initial presets

    # Get state and mouse pos
    state = game.player_setup_state
    mouse_pos = game._get_scaled_mouse_pos()
    
    # We must call draw *before* the event loop to get the rects
    clickable_rects = _draw_player_build_screen(game, state, mouse_pos)
    
    # Handle Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            game.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            
        if event.type == pygame.MOUSEWHEEL:
            stats_rect = state.get('stats_content_rect')
            active_dropdown_slot = state.get('active_dropdown')
            
            if active_dropdown_slot:
                scroll_state = state['gear_dropdown_scrolls'][active_dropdown_slot]
                # Check if mouse is over the *open* dropdown list
                # We can approximate this by checking the button rect and below
                button_rect = clickable_rects['dropdown_buttons'][active_dropdown_slot]
                list_rect = pygame.Rect(button_rect.x, button_rect.bottom, button_rect.width, 6 * 25) # Approx 6 items
                
                if list_rect.collidepoint(mouse_pos):
                    line_height = 25
                    max_scroll = scroll_state['max_scroll']
                    current_offset = scroll_state['offset']
                    scroll_amount = event.y * line_height * 2 # Scroll 2 lines
                    new_offset = current_offset - scroll_amount
                    scroll_state['offset'] = max(0, min(new_offset, max_scroll))

            # If not scrolling dropdown, check stats panel
            elif stats_rect and stats_rect.collidepoint(mouse_pos):
                line_height = state.get('stats_line_height', 25)
                max_scroll = state.get('stats_max_scroll', 0)
                current_offset = state.get('stats_scroll_offset_y', 0)
                scroll_amount = event.y * line_height * 2 
                new_offset = current_offset - scroll_amount
                state['stats_scroll_offset_y'] = max(0, min(new_offset, max_scroll))
        
        if event.type == pygame.KEYDOWN:
            if state.get('name_input_active'):
                if event.key == pygame.K_BACKSPACE:
                    state['player_name'] = state['player_name'][:-1]
                elif event.key == pygame.K_RETURN:
                    state['name_input_active'] = False
                elif len(state['player_name']) <= 20: # Limit name length
                    state['player_name'] += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            dropdown_clicked = False
            scrollbar_clicked = False
            
            stats_scrollbar_rect = state.get('stats_scrollbar_handle_rect')
            if stats_scrollbar_rect and stats_scrollbar_rect.collidepoint(mouse_pos):
                state['is_dragging_stats_scrollbar'] = True
                state['stats_scroll_drag_last_y'] = mouse_pos[1] # Store initial mouse Y
                scrollbar_clicked = True
            
            active_dropdown_slot = state.get('active_dropdown')
            if active_dropdown_slot:
                scroll_state = state['gear_dropdown_scrolls'][active_dropdown_slot]
                handle_rect = scroll_state.get('handle_rect')
                if handle_rect and handle_rect.collidepoint(mouse_pos):
                    scroll_state['is_dragging'] = True
                    scroll_state['last_y'] = mouse_pos[1]
                    scrollbar_clicked = True

            if scrollbar_clicked: continue # Don't process other clicks if dragging scrollbar

            if clickable_rects['name_input'].collidepoint(mouse_pos):
                state['name_input_active'] = True
            else:
                state['name_input_active'] = False # Deactivate on any other click

            # 1. Check if an active dropdown's *options* were clicked
            if state.get('active_dropdown'):
                for slot_name, option_name, option_rect in clickable_rects["dropdown_options"]:
                    if option_rect.collidepoint(mouse_pos):
                        state['chosen_clothes'][slot_name] = option_name
                        state['active_dropdown'] = None # Close dropdown
                        dropdown_clicked = True
                        break
                if dropdown_clicked: continue # Skip other click checks

            # 2. Check if a dropdown *button* was clicked to open/close it
            for slot_name, rect in clickable_rects["dropdown_buttons"].items():
                if rect.collidepoint(mouse_pos):
                    if state.get('active_dropdown') == slot_name:
                        state['active_dropdown'] = None # Close it
                    else:
                        state['active_dropdown'] = slot_name # Open it
                        # Reset scroll on open
                        state['gear_dropdown_scrolls'][slot_name]['offset'] = 0 
                    dropdown_clicked = True
                    break
            
            # 3. Check if an active PRESET dropdown's *options* were clicked
            if state.get('preset_dropdown_active'):
                for option_name, option_rect in clickable_rects["load_dropdown_options"]:
                    if option_rect.collidepoint(mouse_pos):
                        state['selected_preset'] = option_name
                        state['preset_dropdown_active'] = False # Close
                        _load_preset(state) # Load the preset
                        dropdown_clicked = True
                        break
                if dropdown_clicked: continue

            # 4. Check if PRESET dropdown *button* was clicked
            if clickable_rects['load_dropdown_button'].collidepoint(mouse_pos):
                state['preset_dropdown_active'] = not state.get('preset_dropdown_active', False)
                state['active_dropdown'] = None # Close other dropdown
                dropdown_clicked = True
            
            # 5. If clicking anywhere else, close all dropdowns
            if not dropdown_clicked:
                state['active_dropdown'] = None
                state['preset_dropdown_active'] = False
            

            if dropdown_clicked: continue
            
            # (Check Add/Remove Trait buttons - unchanged)
            for trait_name, rect in clickable_rects["add_trait"]:
                if rect.collidepoint(mouse_pos):
                    if trait_name in state['available_traits']:
                        state['available_traits'].remove(trait_name)
                        state['chosen_traits'].append(trait_name)
                        break 
            for trait_name, rect in clickable_rects["remove_trait"]:
                if rect.collidepoint(mouse_pos):
                    if trait_name in state['chosen_traits']:
                        state['chosen_traits'].remove(trait_name)
                        state['available_traits'].append(trait_name)
                        break
            
            if clickable_rects['save_button'].collidepoint(mouse_pos):
                _save_preset(state)
            
            if clickable_rects['random_button'].collidepoint(mouse_pos):
                _randomize_character(state)

            if clickable_rects['delete_button'].collidepoint(mouse_pos):
                _delete_preset(state)

            # Check Start Button
            if clickable_rects["start_button"] and clickable_rects["start_button"].collidepoint(mouse_pos):
                final_player_data = state['base_data'].copy() # Start with base
                final_player_data['stats'] = state['final_stats']
                final_player_data['attributes'] = state['final_attrs']
                final_player_data['clothes'] = state['chosen_clothes']
                final_player_data['name'] = state.get('player_name', "Player") # Pass the name
                final_player_data['sex'] = state['base_data'].get('sex', 'Male') # Pass the sex
                final_player_data['traits'] = state['chosen_traits']

                game.start_new_game(final_player_data)
                game.game_state = 'PLAYING'
                return
        
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            state['is_dragging_stats_scrollbar'] = False
            # Also reset all dropdown scroll drags
            for slot in state['gear_dropdown_scrolls']:
                state['gear_dropdown_scrolls'][slot]['is_dragging'] = False


        if event.type == pygame.MOUSEMOTION:
            if state.get('is_dragging_stats_scrollbar'):
                mouse_delta_y = mouse_pos[1] - state['stats_scroll_drag_last_y']
                state['stats_scroll_drag_last_y'] = mouse_pos[1] 
                
                content_height = state['stats_content_rect'].height
                handle_rect = state['stats_scrollbar_handle_rect']
                track_height = content_height - handle_rect.height
                
                if track_height > 0:
                    scroll_per_pixel = state['stats_max_scroll'] / track_height
                    current_offset = state.get('stats_scroll_offset_y', 0)
                    new_offset = current_offset + (mouse_delta_y * scroll_per_pixel)
                    state['stats_scroll_offset_y'] = max(0, min(new_offset, state['stats_max_scroll']))

            active_dropdown_slot = state.get('active_dropdown')
            if active_dropdown_slot:
                scroll_state = state['gear_dropdown_scrolls'][active_dropdown_slot]
                if scroll_state.get('is_dragging'):
                    mouse_delta_y = mouse_pos[1] - scroll_state['last_y']
                    scroll_state['last_y'] = mouse_pos[1]
                    
                    handle_rect = scroll_state.get('handle_rect')
                    if handle_rect:
                        # Calculate track height
                        max_options_visible = 4
                        option_height = 25
                        max_list_height = max_options_visible * option_height
                        track_height = max_list_height - handle_rect.height
                        
                        if track_height > 0:
                            scroll_per_pixel = scroll_state['max_scroll'] / track_height
                            current_offset = scroll_state['offset']
                            new_offset = current_offset + (mouse_delta_y * scroll_per_pixel)
                            scroll_state['offset'] = max(0, min(new_offset, scroll_state['max_scroll']))



    # Draw the screen (updates highlights and dropdown states)
    _draw_player_build_screen(game, state, mouse_pos)
    game._update_screen()

def _load_presets(state):
    """Loads all .xml preset files from the save/player directory."""
    preset_dir = "save/player"
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
        return # Add a message to the user later

    preset_dir = "save/player"
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)
        
    filepath = os.path.join(preset_dir, f"{player_name}.xml")
    
    root = ET.Element("preset")
    
    # Save name
    ET.SubElement(root, "name").text = player_name
    
    # Save traits
    traits_node = ET.SubElement(root, "traits")
    for trait in state['chosen_traits']:
        ET.SubElement(traits_node, "trait").text = trait
        
    # Save clothes
    clothes_node = ET.SubElement(root, "clothes")
    for slot, item_name in state['chosen_clothes'].items():
        ET.SubElement(clothes_node, "slot", name=slot).text = item_name

    # Write to file
    try:
        raw_xml = ET.tostring(root, 'utf-8')
        pretty_xml = xml.dom.minidom.parseString(raw_xml).toprettyxml(indent="    ")
        
        with open(filepath, "w") as f:
            f.write(pretty_xml)
            
        print(f"Preset saved: {filepath}")
        _load_presets(state) # Refresh preset list
        state['selected_preset'] = player_name # Select the new preset
    except Exception as e:
        print(f"Error saving preset: {e}")

def _load_preset(state):
    """Loads traits and clothes from a selected preset file."""
    preset_name = state.get('selected_preset')
    if not preset_name or preset_name == "None":
        return

    filepath = os.path.join("save/player", f"{preset_name}.xml")
    if not os.path.exists(filepath):
        print(f"Error: Preset file not found: {filepath}")
        return

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Load name
        name_node = root.find('name')
        if name_node is not None:
            state['player_name'] = name_node.text
        
        # Load traits
        new_traits = []
        traits_node = root.find('traits')
        if traits_node is not None:
            new_traits = [node.text for node in traits_node.findall('trait')]
            
        # Reset available traits
        state['available_traits'] = [t for t in TRAIT_DEFINITIONS if t not in new_traits]
        state['chosen_traits'] = new_traits
        
        # Load clothes
        clothes_node = root.find('clothes')
        if clothes_node is not None:
            for node in clothes_node.findall('slot'):
                slot_name = node.attrib.get('name')
                item_name = node.text
                if slot_name in state['chosen_clothes']:
                    state['chosen_clothes'][slot_name] = item_name
                    
        print(f"Preset loaded: {preset_name}")
    except Exception as e:
        print(f"Error parsing preset file {filepath}: {e}")

def _delete_preset(state):
    """Deletes the currently selected preset file."""
    preset_name = state.get('selected_preset')
    if not preset_name or preset_name == "None":
        print("No preset selected to delete.")
        return

    filepath = os.path.join("save/player", f"{preset_name}.xml")
    if not os.path.exists(filepath):
        print(f"Error: Preset file not found: {filepath}")
        return
        
    try:
        os.remove(filepath)
        print(f"Preset deleted: {preset_name}")
        _load_presets(state) # Refresh preset list
        state['selected_preset'] = "None"
    except Exception as e:
        print(f"Error deleting preset: {e}")

def _randomize_character(state):
    """Randomizes the character's name, traits, and clothes."""
    print("Generating random character...")
    
    # 1. Randomize Name (simple)
    state['player_name'] = fake.name()
    
    # 2. Randomize Traits
    all_traits = list(state['all_traits'].keys())
    
    # Aim for a mix of positive and negative traits
    pos_traits = [t for t in all_traits if state['all_traits'][t]['cost'] > 0]
    neg_traits = [t for t in all_traits if state['all_traits'][t]['cost'] < 0]
    
    num_pos = random.randint(1, 2)
    num_neg = random.randint(0, 1)
    
    new_traits = []
    if pos_traits:
        new_traits.extend(random.sample(pos_traits, min(num_pos, len(pos_traits))))
    if neg_traits:
        new_traits.extend(random.sample(neg_traits, min(num_neg, len(neg_traits))))
    
    state['chosen_traits'] = new_traits
    state['available_traits'] = [t for t in all_traits if t not in new_traits]
    
    # 3. Randomize Clothes
    available_clothes = state['available_clothes']
    chosen_clothes = {}
    for slot, options in available_clothes.items():
        if options:
            # random.choice(options) will include "None" since it's in the list
            chosen_clothes[slot] = random.choice(options)
        else:
            chosen_clothes[slot] = "None"
    state['chosen_clothes'] = chosen_clothes
    
    # 4. Reset preset dropdown
    state['selected_preset'] = "None"