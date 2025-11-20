import pygame
import xml.etree.ElementTree as ET
import os
import xml.dom.minidom
from datetime import datetime
from data.config import *
import data.player_xml_parser
from core.entities.item.item import Item, ITEM_TEMPLATES
from core.entities.zombie.zombie import Zombie
import random
from faker import Faker
fake = Faker()

def load_trait_definitions():
    traits = {}
    # Assumes the file is at game/data/player/traits.xml
    # We use DATA_PATH from config.py
    filepath = os.path.join(DATA_PATH, 'player', 'traits.xml')
    
    if not os.path.exists(filepath):
        print(f"Warning: Traits definition file not found at {filepath}")
        return {}

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        for trait_node in root.findall('trait'):
            trait_id = trait_node.get('id')
            if not trait_id:
                continue
                
            try:
                cost = int(trait_node.get('cost', 0))
            except ValueError:
                cost = 0
                
            trait_data = {'cost': cost}
            
            # Parse 'stats' modifiers (e.g., infection, stamina)
            stats_node = trait_node.find('stats')
            if stats_node is not None:
                trait_data['stats'] = {}
                for stat_name, val in stats_node.attrib.items():
                    try:
                        trait_data['stats'][stat_name] = float(val)
                    except ValueError:
                        pass

            # Parse 'attributes' modifiers (e.g., strength, lucky)
            attrs_node = trait_node.find('attributes')
            if attrs_node is not None:
                trait_data['attributes'] = {}
                for attr_name, val in attrs_node.attrib.items():
                    try:
                        trait_data['attributes'][attr_name] = float(val)
                    except ValueError:
                        pass
            
            traits[trait_id] = trait_data

        print(f"Loaded {len(traits)} traits from XML.")
        
    except Exception as e:
        print(f"Error loading traits XML: {e}")
        
    return traits

# Load the definitions into the global constant
TRAIT_DEFINITIONS = load_trait_definitions()

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




def load_config_data(filepath):
    """Parses the config XML into a dictionary separated by blocks."""
    if not os.path.exists(filepath):
        print(f"Config file not found: {filepath}")
        return {}

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        data = {}
        
        # Parse blocks: game, player, spawning, zombie, etc.
        for child in root:
            block_name = child.tag
            data[block_name] = {}
            for setting in child:
                # Assumes structure <setting_name value="..."/>
                key = setting.tag
                val = setting.get('value')
                data[block_name][key] = val
        return data
    except Exception as e:
        print(f"Error loading config {filepath}: {e}")
        return {}

def save_config_xml(data, filepath):
    """Saves the settings dictionary back to XML."""
    root = ET.Element("config")
    
    for block_name, settings in data.items():
        block_node = ET.SubElement(root, block_name)
        for key, val in settings.items():
            ET.SubElement(block_node, key, value=str(val))

    try:
        raw_xml = ET.tostring(root, 'utf-8')
        # Pretty print hack
        parsed = xml.dom.minidom.parseString(raw_xml)
        pretty_xml = parsed.toprettyxml(indent="    ")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "w") as f:
            f.write(pretty_xml)
        print(f"Config saved to {filepath}")
    except Exception as e:
        print(f"Error saving config XML: {e}")

def _load_config_presets(state):
    """Loads list of config presets."""
    preset_dir = "./game/save/config"
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)
    
    presets = ["default"] # Always include default
    try:
        files = [f for f in os.listdir(preset_dir) if f.endswith('.xml')]
        for f in files:
            name = f.replace('.xml', '')
            if name != 'default':
                presets.append(name)
    except Exception:
        pass
    state['config_preset_list'] = presets




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


def draw_menu(screen, mouse_pos):
    global _logo_img
    screen.fill(DARK_GRAY)

    # try to load and draw logo image instead of text title
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load('./game/icons/logo.png').convert_alpha()
            logo_w = 400
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
    
    if start_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, GRAY, start_rect.inflate(20, 10))
    if quit_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, GRAY, quit_rect.inflate(20, 10))

    screen.blit(start_text, start_rect)
    screen.blit(quit_text, quit_rect)
    return start_rect, quit_rect

def draw_game_over(screen, zombies_killed, mouse_pos):
    screen.fill(DARK_GRAY)
    # draw same logo at top for game over screen (fallback to text if missing)
    global _logo_img
    try:
        if _logo_img is None:
            _logo_img = pygame.image.load('./game/icons/logo.png').convert_alpha()
            logo_w = 500
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

    if restart_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, GRAY, restart_rect.inflate(20, 10))
    if quit_rect.collidepoint(mouse_pos):
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
        # Content rect needs to be clipped by the *screen* edge
        if list_rect.bottom > VIRTUAL_GAME_HEIGHT:
            list_rect.height = VIRTUAL_GAME_HEIGHT - list_rect.top
        
        content_rect = pygame.Rect(list_rect.x, list_rect.y, list_rect.width - 10, list_rect.height) # Room for scrollbar
        
        # Handle ValueError by clipping content_rect to surface
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
    # game.virtual_screen.fill(DARK_GRAY)
    
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


    col1_x = 170
    col1_width = 280
    col2_x = col1_x + col1_width + 20 # 350
    col2_width = 280
    col3_x = col2_x + col2_width + 20 # 650
    col3_width = 280
    col4_x = col3_x + col3_width + 20 # 950
    col4_width = 280 # Adjusted to fit

    padding = 10
    
    # --- Column 1, Block 1: Preset Management Panel (Top-Left) ---
    preset_rect = pygame.Rect(col1_x, 50, col1_width, 280)

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
    
    sex_y = load_dd_rect.bottom + 10
    game.virtual_screen.blit(font.render("Sex:", True, WHITE), (preset_body_rect.x + padding, sex_y))
    
    sex_btn_width = (preset_body_rect.width - (padding * 3)) // 2
    male_btn_rect = pygame.Rect(preset_body_rect.x + padding, sex_y + 25, sex_btn_width, 30)
    female_btn_rect = pygame.Rect(male_btn_rect.right + padding, sex_y + 25, sex_btn_width, 30)
    
    current_sex = state['base_data'].get('sex', 'Male')
    
    # Draw Male Button
    if current_sex == 'Male':
        pygame.draw.rect(game.virtual_screen, (80, 80, 80), male_btn_rect, 0, border_radius=3) # Highlight active
        pygame.draw.rect(game.virtual_screen, WHITE, male_btn_rect, 2, border_radius=3)
    else:
        pygame.draw.rect(game.virtual_screen, (50, 50, 50), male_btn_rect, 0, border_radius=3)
        pygame.draw.rect(game.virtual_screen, WHITE, male_btn_rect, 1, border_radius=3)
    game.virtual_screen.blit(font.render("Male", True, WHITE), (male_btn_rect.centerx - 20, male_btn_rect.y + 5))
    
    # Draw Female Button
    if current_sex == 'Female':
        pygame.draw.rect(game.virtual_screen, (80, 80, 80), female_btn_rect, 0, border_radius=3) # Highlight active
        pygame.draw.rect(game.virtual_screen, WHITE, female_btn_rect, 2, border_radius=3)
    else:
        pygame.draw.rect(game.virtual_screen, (50, 50, 50), female_btn_rect, 0, border_radius=3)
        pygame.draw.rect(game.virtual_screen, WHITE, female_btn_rect, 1, border_radius=3)
    game.virtual_screen.blit(font.render("Female", True, WHITE), (female_btn_rect.centerx - 28, female_btn_rect.y + 5))
    
    clickable_rects['sex_buttons'] = {'Male': male_btn_rect, 'Female': female_btn_rect}
 

    # --- Column 1, Block 2: Gear Selection (Bottom-Left) ---
    gear_rect = pygame.Rect(col1_x, preset_rect.bottom + 20, col1_width, 340) # Bottom half

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

    traits_content_rect = pygame.Rect(
        available_rect.x + padding, 
        available_rect.y + header_height + padding, 
        available_rect.width - (padding * 2) - 10, # -10 for scrollbar
        available_rect.height - header_height - (padding * 2)
    )
    state['traits_content_rect'] = traits_content_rect
    line_height = 35 # The existing loop uses this
    state['traits_line_height'] = line_height

    total_items = len(state['available_traits'])
    total_text_height = total_items * line_height
    
    visible_height = traits_content_rect.height
    max_scroll_offset = max(0, total_text_height - visible_height)
    state['traits_max_scroll'] = max_scroll_offset
    
    scroll_offset_y = max(0, min(state.get('traits_scroll_offset_y', 0), max_scroll_offset))
    state['traits_scroll_offset_y'] = scroll_offset_y

    # --- Create Subsurface for clipping ---
    drawable_traits_rect = game.virtual_screen.get_rect().clip(traits_content_rect)
    if drawable_traits_rect.width > 0 and drawable_traits_rect.height > 0:
        content_surface = game.virtual_screen.subsurface(drawable_traits_rect)
        content_surface.fill((30, 30, 30)) # Panel body color
    else:
        content_surface = None # Cannot draw

    # --- Modified Drawing Loop ---
    y_offset = 0 - scroll_offset_y # Start relative to subsurface
    
    if content_surface: # Only draw if surface is valid
        for i, trait_name in enumerate(state['available_traits']):
            # Calculate positions relative to the content_surface
            row_rect_rel = pygame.Rect(0, y_offset, traits_content_rect.width, 30)
            
            # Absolute rect for click detection
            row_rect_abs = pygame.Rect(
                traits_content_rect.x, 
                traits_content_rect.y + y_offset, 
                traits_content_rect.width, 
                30
            )
            
            add_btn_rect_rel = pygame.Rect(
                row_rect_rel.right - 25, 
                row_rect_rel.y, 
                25, 
                25
            )
            
            # Absolute rect for click detection
            add_btn_rect_abs = pygame.Rect(
                traits_content_rect.x + add_btn_rect_rel.x,
                traits_content_rect.y + add_btn_rect_rel.y,
                25,
                25
            )

            # --- Clipping Check ---
            # Only blit if the item is vertically visible
            if row_rect_rel.bottom > 0 and row_rect_rel.top < traits_content_rect.height:
                #content_surface.blit(font.render(trait_name.capitalize(), True, WHITE), (row_rect_rel.x, row_rect_rel.y))
                trait_cost = TRAIT_DEFINITIONS.get(trait_name, {}).get('cost', 0)
                cost_color = (100, 255, 100) if trait_cost > 0 else (255, 100, 100) if trait_cost < 0 else WHITE
                
                name_surf = font.render(trait_name.capitalize(), True, WHITE)
                cost_surf = font.render(f"({trait_cost:+})", True, cost_color)
                
                content_surface.blit(name_surf, (row_rect_rel.x, row_rect_rel.y))
                content_surface.blit(cost_surf, (row_rect_rel.x + name_surf.get_width() + 5, row_rect_rel.y))

                pygame.draw.rect(content_surface, GREEN, add_btn_rect_rel)
                content_surface.blit(font.render(">", True, WHITE), (add_btn_rect_rel.x + 7, add_btn_rect_rel.y + 2))
            
            # Add the *absolute* rect for clicking
            clickable_rects["add_trait"].append((trait_name, add_btn_rect_abs))
            
            y_offset += line_height # Use the stored line_height
            # (Old break condition removed)

    # --- Draw Traits Scrollbar ---
    if total_text_height > visible_height:
        scrollbar_area_height = traits_content_rect.height
        scrollbar_area_rect = pygame.Rect(traits_content_rect.right + 2, traits_content_rect.top, 8, scrollbar_area_height)
        
        handle_height_ratio = visible_height / total_text_height
        handle_height = max(10, scrollbar_area_height * handle_height_ratio)
        
        handle_pos_ratio = 0
        if max_scroll_offset > 0: 
            handle_pos_ratio = scroll_offset_y / max_scroll_offset
        
        handle_y = scrollbar_area_rect.top + (scrollbar_area_height - handle_height) * handle_pos_ratio
        
        traits_scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        pygame.draw.rect(game.virtual_screen, GRAY, traits_scrollbar_handle_rect, 0, 2)
        state['traits_scrollbar_handle_rect'] = traits_scrollbar_handle_rect 
    else:
        state['traits_scrollbar_handle_rect'] = None


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

    total_cost = 0
    for trait_name in state['chosen_traits']:
        total_cost += TRAIT_DEFINITIONS.get(trait_name, {}).get('cost', 0)
    state['total_trait_cost'] = total_cost # Store for event handler

    cost_text = f"Points: {total_cost}"
    cost_color = (100, 255, 100) if total_cost == 0 else (255, 100, 100) # Green if 0, else Red
    cost_surf = font.render(cost_text, True, cost_color)
    cost_rect = cost_surf.get_rect(right=header_rect.right - padding, centery=header_rect.centery)
    game.virtual_screen.blit(cost_surf, cost_rect)

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
    # total_text_height = (len(current_stats) + len(current_attrs)) * line_height
    total_items = len(current_stats) + len(current_attrs)
    total_text_height = total_items * line_height

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
            base_value = state['base_data']['stats'].get(stat, 100.0)
            trait_mod = value - base_value
            
            stat_name_str = f"{stat.capitalize()}" # Align stat names
        # Align base values
            trait_str = f"{int(trait_mod):+}%"  # Align trait modifiers
            
            # Set color based on modifier
            mod_color = WHITE
            if trait_mod > 0:
                mod_color = (100, 255, 100) # Green
            elif trait_mod < 0:
                mod_color = (255, 100, 100) # Red
            
            text_surf = font.render(f"{stat_name_str}", True, WHITE)
            mod_surf = font.render(f"{trait_str}", True, mod_color)
            
            content_surface.blit(text_surf, (text_x, y_offset + 3))
            content_surface.blit(mod_surf, (text_x + 100, y_offset + 3))
            
            y_offset += line_height
        
        # Loop 2: Draw ATTRIBUTES (base 0)
        for attr, value in current_attrs.items():
            icon = _stat_icons_cache.get(attr)
            if icon:
                content_surface.blit(icon, (0, y_offset + (line_height - icon.get_height()) // 2))
                text_x = icon_padding
            else:
                text_x = 0
            
            # Format value
            base_value = state['base_data']['attributes'].get(attr, 0.0) # Base is 0
            trait_mod = value - base_value
            
            stat_name_str = f"{attr.capitalize()}"
            base_str = f"{int(base_value)}"      # No percentage
            trait_str = f"{int(trait_mod):+}"    # No percentage
            
            # Set color based on modifier
            mod_color = WHITE
            if trait_mod > 0:
                mod_color = (100, 255, 100) # Green
            elif trait_mod < 0:
                mod_color = (255, 100, 100) # Red
            
            text_surf = font.render(f"{stat_name_str}", True, WHITE)
            mod_surf = font.render(f"{trait_str}", True, mod_color)
            
            content_surface.blit(text_surf, (text_x, y_offset + 3))
            content_surface.blit(mod_surf, (text_x + 100, y_offset + 3))
            
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
    is_balanced = (state.get('total_trait_cost', 0) == 0)
    
    if is_balanced:
        # Draw enabled button
        pygame.draw.rect(game.virtual_screen, (0, 100, 0), start_btn_rect, border_radius=border_radius)
        if start_btn_rect.collidepoint(mouse_pos):
            pygame.draw.rect(game.virtual_screen, (0, 150, 0), start_btn_rect.inflate(-4, -4), border_radius=border_radius)
        start_text = large_font.render("START GAME", True, WHITE)
    else:
        # Draw disabled button
        pygame.draw.rect(game.virtual_screen, (50, 50, 50), start_btn_rect, border_radius=border_radius) # Dark gray
        pygame.draw.rect(game.virtual_screen, GRAY, start_btn_rect, 1, border_radius=border_radius) # Gray border
        start_text = large_font.render("START GAME", True, (100, 100, 100)) # Gray text
    
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
            state['base_data'], trait_names = data.player_xml_parser.parse_player_data()
        except Exception as e:
            print(f"FATAL: Could not parse player.xml: {e}")
            game.running = False
            return
        state['all_traits'] = TRAIT_DEFINITIONS

        all_ids = list(TRAIT_DEFINITIONS.keys())
        
        # Sort traits
        pos_traits = sorted([t for t in all_ids if TRAIT_DEFINITIONS[t]['cost'] > 0], key=lambda t: (TRAIT_DEFINITIONS[t]['cost'], t))
        neg_traits = sorted([t for t in all_ids if TRAIT_DEFINITIONS[t]['cost'] < 0], key=lambda t: (abs(TRAIT_DEFINITIONS[t]['cost']), t))
        
        state['available_traits'] = []
        if pos_traits: state['available_traits'].extend(pos_traits)
        if neg_traits: state['available_traits'].extend(neg_traits)

        state['chosen_traits'] = []
        state['final_stats'] = state['base_data']['stats'].copy()
        state['final_attrs'] = state['base_data']['attributes'].copy()
        
        # Scroll states
        state['stats_scroll_offset_y'] = 0; state['stats_content_rect'] = None; state['stats_line_height'] = 25; state['stats_max_scroll'] = 0
        state['traits_scroll_offset_y'] = 0; state['traits_content_rect'] = None; state['traits_line_height'] = 35; state['traits_max_scroll'] = 0
        state['is_dragging_stats_scrollbar'] = False; state['stats_scroll_drag_last_y'] = 0
        state['is_dragging_traits_scrollbar'] = False; state['traits_scroll_drag_last_y'] = 0
        state['total_trait_cost'] = 0

        Item.load_item_templates()
        Zombie.load_templates()

        state['clothes_slots'] = ['head','legs', 'feet',  'torso' ,'body', 'hands']
        state['available_clothes'] = {slot: [] for slot in state['clothes_slots']}
        state['chosen_clothes'] = {slot: "None" for slot in state['clothes_slots']}
        state['active_dropdown'] = None
        state['gear_dropdown_scrolls'] = {slot: {'offset': 0, 'is_dragging': False, 'last_y': 0, 'handle_rect': None, 'max_scroll': 0} for slot in state['clothes_slots']}
        state['clothing_sprites'] = {}

        # Load clothes
        for item_name, template in ITEM_TEMPLATES.items():
            if template.get('type') == 'cloth':
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

        # Load player sprite
        try:
            sprite_path = state['base_data']['visuals']['sprite']
            sprite_img = pygame.image.load(SPRITE_PATH + sprite_path).convert_alpha()
            state['player_sprite_large'] = pygame.transform.scale(sprite_img, (256, 256))
        except Exception:
            state['player_sprite_large'] = pygame.Surface((256, 256), pygame.SRCALPHA); state['player_sprite_large'].fill(BLUE)

        state['player_name'] = fake.name()
        state['name_input_active'] = False
        state['preset_list'] = ["None"]
        state['selected_preset'] = "None"
        state['preset_dropdown_active'] = False
        _load_presets(state)

        # --- SETTINGS STATE INIT ---
        state['current_tab'] = 'Player'
        state['settings_data'] = load_config_data("./game/save/config/default.xml")
        state['config_name'] = ""
        state['config_name_active'] = False
        state['settings_scroll_y'] = 0
        state['active_setting'] = None
        state['config_dd_active'] = False
        _load_config_presets(state)

    state = game.player_setup_state
    mouse_pos = game._get_scaled_mouse_pos()
    
    # --- Draw Sidebar & Background ---
    game.virtual_screen.fill(DARK_GRAY)
    
    sidebar_width = 150
    btn_h = 40
    
    player_btn = pygame.Rect(10, 50, sidebar_width, btn_h)
    settings_btn = pygame.Rect(10, 100, sidebar_width, btn_h)
    
    # Highlight active tab
    p_col = GRAY_60 if state['current_tab'] == 'Player' else (40, 40, 40)
    s_col = GRAY_60 if state['current_tab'] == 'Settings' else (40, 40, 40)
    
    pygame.draw.rect(game.virtual_screen, p_col, player_btn, border_radius=4)
    pygame.draw.rect(game.virtual_screen, WHITE, player_btn, 1, border_radius=4)
    game.virtual_screen.blit(font.render("Player", True, WHITE), (player_btn.x + 10, player_btn.y + 10))
    
    pygame.draw.rect(game.virtual_screen, s_col, settings_btn, border_radius=4)
    pygame.draw.rect(game.virtual_screen, WHITE, settings_btn, 1, border_radius=4)
    game.virtual_screen.blit(font.render("Settings", True, WHITE), (settings_btn.x + 10, settings_btn.y + 10))

    clickable_rects = {}
    
    # Draw Content
    if state['current_tab'] == 'Player':
        clickable_rects = _draw_player_build_screen(game, state, mouse_pos)
    else:
        clickable_rects = _draw_settings_screen(game, state, mouse_pos)
    
    # Handle Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            game.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            
        # --- Scroll Handling ---
        if event.type == pygame.MOUSEWHEEL:
            if state['current_tab'] == 'Settings':
                 rect = state.get('settings_content_rect')
                 if rect and rect.collidepoint(mouse_pos):
                     state['settings_scroll_y'] = max(0, min(state['settings_scroll_y'] - (event.y * 30), state.get('settings_max_scroll', 0)))
            
            elif state['current_tab'] == 'Player':
                stats_rect = state.get('stats_content_rect')
                active_dropdown_slot = state.get('active_dropdown')
                if active_dropdown_slot:
                     scroll_state = state['gear_dropdown_scrolls'][active_dropdown_slot]
                     scroll_state['offset'] = max(0, min(scroll_state['offset'] - event.y * 50, scroll_state['max_scroll']))
                elif state.get('traits_content_rect') and state['traits_content_rect'].collidepoint(mouse_pos):
                     state['traits_scroll_offset_y'] = max(0, min(state['traits_scroll_offset_y'] - event.y * 70, state.get('traits_max_scroll', 0)))
                elif stats_rect and stats_rect.collidepoint(mouse_pos):
                     state['stats_scroll_offset_y'] = max(0, min(state['stats_scroll_offset_y'] - event.y * 50, state.get('stats_max_scroll', 0)))
        
        # --- Keyboard Handling ---
        if event.type == pygame.KEYDOWN:
            if state['current_tab'] == 'Settings':
                if state.get('config_name_active'):
                    if event.key == pygame.K_BACKSPACE: state['config_name'] = state['config_name'][:-1]
                    elif event.key == pygame.K_RETURN: state['config_name_active'] = False
                    else: state['config_name'] += event.unicode
                elif state.get('active_setting'):
                    block, key = state['active_setting']
                    current_val = state['settings_data'][block][key]
                    if event.key == pygame.K_BACKSPACE: state['settings_data'][block][key] = current_val[:-1]
                    elif event.key == pygame.K_RETURN: state['active_setting'] = None
                    else: state['settings_data'][block][key] = current_val + event.unicode

            elif state['current_tab'] == 'Player':
                if state.get('name_input_active'):
                    if event.key == pygame.K_BACKSPACE: state['player_name'] = state['player_name'][:-1]
                    elif event.key == pygame.K_RETURN: state['name_input_active'] = False
                    elif len(state['player_name']) <= 20: state['player_name'] += event.unicode

        # --- Mouse Click Handling ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Sidebar Navigation
            if player_btn.collidepoint(mouse_pos):
                state['current_tab'] = 'Player'
                continue
            elif settings_btn.collidepoint(mouse_pos):
                state['current_tab'] = 'Settings'
                continue

            # --- TAB SPECIFIC LOGIC ---
            if state['current_tab'] == 'Settings':
                state['config_name_active'] = False
                state['active_setting'] = None
                state['config_dd_active'] = False
                
                if clickable_rects.get('config_name_input') and clickable_rects['config_name_input'].collidepoint(mouse_pos):
                    state['config_name_active'] = True
                elif clickable_rects.get('save_config') and clickable_rects['save_config'].collidepoint(mouse_pos):
                    if state.get('config_name'):
                        save_config_xml(state['settings_data'], f"./game/save/config/{state['config_name']}.xml")
                        _load_config_presets(state)
                elif clickable_rects.get('delete_config') and clickable_rects['delete_config'].collidepoint(mouse_pos):
                     name = state.get('selected_config_preset')
                     if name and name != 'default':
                        try:
                            os.remove(f"./game/save/config/{name}.xml")
                            _load_config_presets(state)
                            state['selected_config_preset'] = 'default'
                        except: pass
                elif clickable_rects.get('load_config_dd') and clickable_rects['load_config_dd'].collidepoint(mouse_pos):
                    state['config_dd_active'] = not state.get('config_dd_active')
                elif state.get('config_dd_active'):
                    for opt, r in clickable_rects.get('load_config_options', []):
                        if r.collidepoint(mouse_pos):
                            state['selected_config_preset'] = opt
                            state['settings_data'] = load_config_data(f"./game/save/config/{opt}.xml")
                            state['config_name'] = opt if opt != 'default' else ""
                            state['config_dd_active'] = False
                            break
                else:
                    for block, key, rect in clickable_rects.get('config_inputs', []):
                        if rect.collidepoint(mouse_pos):
                            state['active_setting'] = (block, key)
                            break

            else: # Player Tab Logic (Restored)
                dropdown_clicked = False
                scrollbar_clicked = False
                
                # Scrollbars
                if state.get('stats_scrollbar_handle_rect') and state['stats_scrollbar_handle_rect'].collidepoint(mouse_pos):
                    state['is_dragging_stats_scrollbar'] = True; state['stats_scroll_drag_last_y'] = mouse_pos[1]; scrollbar_clicked = True
                
                if not scrollbar_clicked and state.get('traits_scrollbar_handle_rect') and state['traits_scrollbar_handle_rect'].collidepoint(mouse_pos):
                    state['is_dragging_traits_scrollbar'] = True; state['traits_scroll_drag_last_y'] = mouse_pos[1]; scrollbar_clicked = True

                active_dropdown_slot = state.get('active_dropdown')
                if active_dropdown_slot:
                    scroll_state = state['gear_dropdown_scrolls'][active_dropdown_slot]
                    if scroll_state.get('handle_rect') and scroll_state['handle_rect'].collidepoint(mouse_pos):
                        scroll_state['is_dragging'] = True; scroll_state['last_y'] = mouse_pos[1]; scrollbar_clicked = True

                if scrollbar_clicked: continue

                # Name Input
                if clickable_rects.get('name_input') and clickable_rects['name_input'].collidepoint(mouse_pos):
                    state['name_input_active'] = True
                else:
                    state['name_input_active'] = False

                # Dropdowns
                if state.get('active_dropdown'):
                    for slot_name, option_name, option_rect in clickable_rects["dropdown_options"]:
                        if option_rect.collidepoint(mouse_pos):
                            state['chosen_clothes'][slot_name] = option_name; state['active_dropdown'] = None; dropdown_clicked = True; break
                    if dropdown_clicked: continue

                for slot_name, rect in clickable_rects.get("dropdown_buttons", {}).items():
                    if rect.collidepoint(mouse_pos):
                        if state.get('active_dropdown') == slot_name: state['active_dropdown'] = None
                        else: state['active_dropdown'] = slot_name; state['gear_dropdown_scrolls'][slot_name]['offset'] = 0
                        dropdown_clicked = True; break
                
                # Presets
                if state.get('preset_dropdown_active'):
                    for option_name, option_rect in clickable_rects["load_dropdown_options"]:
                        if option_rect.collidepoint(mouse_pos):
                            state['selected_preset'] = option_name; state['preset_dropdown_active'] = False; _load_preset(state); dropdown_clicked = True; break
                    if dropdown_clicked: continue

                if clickable_rects.get('load_dropdown_button') and clickable_rects['load_dropdown_button'].collidepoint(mouse_pos):
                    state['preset_dropdown_active'] = not state.get('preset_dropdown_active', False); state['active_dropdown'] = None; dropdown_clicked = True

                if not dropdown_clicked:
                    state['active_dropdown'] = None; state['preset_dropdown_active'] = False

                # Sex
                if 'sex_buttons' in clickable_rects:
                    for sex, rect in clickable_rects['sex_buttons'].items():
                        if rect.collidepoint(mouse_pos):
                            state['base_data']['sex'] = sex
                            if state['player_name'] == "Survivor" or not state['player_name']:
                                 state['player_name'] = fake.name_male() if sex == 'Male' else fake.name_female()
                            break

                # Traits
                for trait_name, rect in clickable_rects["add_trait"]:
                    if rect.collidepoint(mouse_pos):
                        if trait_name in state['available_traits']:
                            state['available_traits'].remove(trait_name); state['chosen_traits'].append(trait_name); break 
                for trait_name, rect in clickable_rects["remove_trait"]:
                    if rect.collidepoint(mouse_pos):
                        if trait_name in state['chosen_traits']:
                            state['chosen_traits'].remove(trait_name); state['available_traits'].append(trait_name); break
                
                # Buttons
                if clickable_rects['save_button'].collidepoint(mouse_pos): _save_preset(state)
                if clickable_rects['random_button'].collidepoint(mouse_pos): _randomize_character(state)
                if clickable_rects['delete_button'].collidepoint(mouse_pos): _delete_preset(state)

                # Start Game
                if clickable_rects["start_button"] and clickable_rects["start_button"].collidepoint(mouse_pos):
                    if state.get('total_trait_cost', 0) == 0:
                        final_player_data = state['base_data'].copy()
                        final_player_data['attributes'] = state['final_attrs']
                        final_player_data['clothes'] = state['chosen_clothes']
                        final_player_data['name'] = state.get('player_name', "Player")
                        final_player_data['sex'] = state['base_data'].get('sex', 'Male')
                        final_player_data['traits'] = state['chosen_traits']
                        final_player_data['visuals'] = {'center': 'player.png', 'left': 'player_left.png', 'right': 'player_right.png'}
                        final_player_data['sounds'] = { 'steps': 'steps.ogg' }
                        game.start_new_game(final_player_data)
                        game.game_state = 'PLAYING'
                        return

        if event.type == pygame.MOUSEBUTTONUP:
            state['is_dragging_stats_scrollbar'] = False
            state['is_dragging_traits_scrollbar'] = False
            for slot in state.get('gear_dropdown_scrolls', {}):
                state['gear_dropdown_scrolls'][slot]['is_dragging'] = False

        if event.type == pygame.MOUSEMOTION:
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

            if state.get('active_dropdown'):
                scroll_state = state['gear_dropdown_scrolls'][state['active_dropdown']]
                if scroll_state.get('is_dragging'):
                    mouse_delta_y = mouse_pos[1] - scroll_state['last_y']; scroll_state['last_y'] = mouse_pos[1]
                    track_height = (4 * 25) - scroll_state['handle_rect'].height
                    if track_height > 0:
                        scroll_state['offset'] = max(0, min(scroll_state['offset'] + (mouse_delta_y * (scroll_state['max_scroll'] / track_height)), scroll_state['max_scroll']))

    game._update_screen()






def _draw_settings_screen(game, state, mouse_pos):
    """Draws the Settings configuration screen."""
    # Reuse styles from player build screen
    col_start_x = 170 # Offset for Sidebar
    col_width = 350
    header_height = 30
    border_radius = 4
    padding = 10
    
    clickable_rects = {
        "config_inputs": [], # list of (block, key, rect)
        "save_config": None,
        "delete_config": None,
        "load_config_dd": None,
        "load_config_options": []
    }

    # 1. Preset Management Panel (Top Left of content area)
    preset_rect = pygame.Rect(col_start_x, 50, col_width, 180)
    preset_header = pygame.Rect(preset_rect.x, preset_rect.y, preset_rect.width, header_height)
    preset_body = pygame.Rect(preset_rect.x, preset_rect.y + header_height, preset_rect.width, preset_rect.height - header_height)

    pygame.draw.rect(game.virtual_screen, (30, 30, 30), preset_body, border_bottom_left_radius=border_radius, border_bottom_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, GRAY_60, preset_header, border_top_left_radius=border_radius, border_top_right_radius=border_radius)
    pygame.draw.rect(game.virtual_screen, WHITE, preset_rect, 1, border_radius=border_radius)
    game.virtual_screen.blit(font.render("Config Preset", True, WHITE), (preset_header.x + 10, preset_header.y + 7))

    # Config Name Input
    game.virtual_screen.blit(font.render("Config Name:", True, WHITE), (preset_body.x + padding, preset_body.y + 10))
    name_input_rect = pygame.Rect(preset_body.x + padding, preset_body.y + 35, preset_body.width - padding*2, 30)
    pygame.draw.rect(game.virtual_screen, (50, 50, 50), name_input_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, name_input_rect, 1)
    
    conf_name = state.get('config_name', "")
    text_surf = font.render(conf_name, True, WHITE)
    game.virtual_screen.blit(text_surf, (name_input_rect.x + 5, name_input_rect.y + 5))
    
    if state.get('config_name_active') and int(pygame.time.get_ticks() / 500) % 2 == 0:
        cx = name_input_rect.x + 5 + text_surf.get_width()
        pygame.draw.line(game.virtual_screen, WHITE, (cx, name_input_rect.y+5), (cx, name_input_rect.bottom-5), 2)
    
    clickable_rects['config_name_input'] = name_input_rect

    # Buttons
    btn_w = 100
    save_rect = pygame.Rect(preset_body.x + padding, preset_body.y + 80, btn_w, 30)
    pygame.draw.rect(game.virtual_screen, GREEN, save_rect)
    game.virtual_screen.blit(font.render("Save", True, WHITE), (save_rect.x + 30, save_rect.y + 5))
    clickable_rects['save_config'] = save_rect

    del_rect = pygame.Rect(save_rect.right + padding, preset_body.y + 80, btn_w, 30)
    pygame.draw.rect(game.virtual_screen, RED, del_rect)
    game.virtual_screen.blit(font.render("Delete", True, WHITE), (del_rect.x + 25, del_rect.y + 5))
    clickable_rects['delete_config'] = del_rect

    # Load Dropdown
    load_rect = pygame.Rect(preset_body.x + padding, preset_body.y + 120, preset_body.width - padding*2, 30)
    clickable_rects['load_config_dd'] = load_rect
    pygame.draw.rect(game.virtual_screen, (50, 50, 50), load_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, load_rect, 1)
    curr_preset = state.get('selected_config_preset', 'default')
    game.virtual_screen.blit(font.render(curr_preset, True, WHITE), (load_rect.x + 5, load_rect.y + 5))

    # 2. Settings List (Scrollable Area)
    # Located to the right of the preset box, or below
    # Let's put it to the right to match the "3 column" feel of the player tab
    settings_area_x = col_start_x + col_width + 20
    settings_area_w = 600
    settings_rect = pygame.Rect(settings_area_x, 50, settings_area_w, 640)
    
    pygame.draw.rect(game.virtual_screen, (20, 20, 20), settings_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, settings_rect, 1)
    
    # Header for settings
    game.virtual_screen.blit(font.render("Configuration Values", True, WHITE), (settings_rect.x + 10, settings_rect.y - 25))

    # Content calculation
    content_rect = settings_rect.inflate(-20, -20)
    line_h = 40
    
    # Flatten data for drawing
    draw_items = []
    config_data = state.get('settings_data', {})
    
    # Order of blocks as requested
    block_order = ['game', 'player', 'spawning', 'zombie']
    # Add any others that might exist
    for k in config_data:
        if k not in block_order: block_order.append(k)

    for block in block_order:
        if block not in config_data: continue
        draw_items.append(('header', block))
        for key, val in config_data[block].items():
            draw_items.append(('item', block, key, val))

    total_h = len(draw_items) * line_h
    max_scroll = max(0, total_h - content_rect.height)
    state['settings_max_scroll'] = max_scroll
    scroll_y = state.get('settings_scroll_y', 0)
    
    # Clip surface
    clip_rect = game.virtual_screen.get_rect().clip(content_rect)
    if clip_rect.width > 0 and clip_rect.height > 0:
        sub = game.virtual_screen.subsurface(clip_rect)
        sub.fill((30, 30, 30))
        
        y_off = -scroll_y
        for item in draw_items:
            # Draw Item relative to sub
            if item[0] == 'header':
                pygame.draw.rect(sub, GRAY_60, (0, y_off, content_rect.width, line_h))
                text = font.render(item[1].upper(), True, YELLOW)
                sub.blit(text, (10, y_off + 10))
            else:
                block, key, val = item[1], item[2], item[3]
                # Label
                lbl = font_small.render(key + ":", True, WHITE)
                sub.blit(lbl, (20, y_off + 12))
                
                # Input Box
                input_w = 200
                input_rect = pygame.Rect(content_rect.width - input_w - 10, y_off + 5, input_w, 30)
                
                # Check active state
                is_active = (state.get('active_setting') == (block, key))
                col = WHITE if is_active else GRAY
                
                pygame.draw.rect(sub, (50, 50, 50), input_rect)
                pygame.draw.rect(sub, col, input_rect, 1)
                
                val_text = str(val)
                txt_surf = font_small.render(val_text, True, WHITE)
                
                # Text clipping inside input box
                txt_clip = pygame.Rect(input_rect.x + 5, input_rect.y, input_rect.width - 10, input_rect.height)
                # We need to calculate position relative to the 'sub' surface
                # input_rect is already relative to 'sub'
                
                sub.blit(txt_surf, (input_rect.x + 5, input_rect.y + 7))
                
                # Store absolute rect for clicking
                abs_rect = pygame.Rect(content_rect.x + input_rect.x, content_rect.y + input_rect.y, input_rect.width, input_rect.height)
                
                # Check if visible before adding to clickable
                if abs_rect.bottom > content_rect.top and abs_rect.top < content_rect.bottom:
                    clickable_rects['config_inputs'].append((block, key, abs_rect))
                
            y_off += line_h

    # Scrollbar
    if max_scroll > 0:
        bar_area = pygame.Rect(settings_rect.right - 10, settings_rect.y, 10, settings_rect.height)
        handle_h = max(20, (content_rect.height / total_h) * bar_area.height)
        scroll_pct = scroll_y / max_scroll
        handle_y = bar_area.y + (scroll_pct * (bar_area.height - handle_h))
        handle_rect = pygame.Rect(bar_area.x, handle_y, 10, handle_h)
        pygame.draw.rect(game.virtual_screen, GRAY, handle_rect, border_radius=2)
        state['settings_scroll_handle'] = handle_rect
    else:
        state['settings_scroll_handle'] = None
    
    state['settings_content_rect'] = content_rect

    # Draw dropdown list if active (on top)
    if state.get('config_dd_active'):
        opts = state.get('config_preset_list', [])
        dd_h = len(opts) * 25
        dd_rect = pygame.Rect(load_rect.x, load_rect.bottom, load_rect.width, dd_h)
        pygame.draw.rect(game.virtual_screen, (40,40,40), dd_rect)
        pygame.draw.rect(game.virtual_screen, WHITE, dd_rect, 1)
        
        dy = dd_rect.y
        for opt in opts:
            opt_r = pygame.Rect(dd_rect.x, dy, dd_rect.width, 25)
            if opt_r.collidepoint(mouse_pos):
                pygame.draw.rect(game.virtual_screen, GRAY, opt_r)
            game.virtual_screen.blit(font.render(opt, True, WHITE), (opt_r.x + 5, opt_r.y + 2))
            clickable_rects['load_config_options'].append((opt, opt_r))
            dy += 25

    return clickable_rects






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
        return # Add a message to the user later

    preset_dir = "./game/save/player"
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)
        
    filepath = os.path.join(preset_dir, f"{player_name}.xml")
    
    root = ET.Element("preset")
    
    # Save name
    ET.SubElement(root, "name").text = player_name

    ET.SubElement(root, "sex").text = state['base_data'].get('sex', 'Male')

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

    filepath = os.path.join("./game/save/player", f"{preset_name}.xml")
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
        
        sex_node = root.find('sex')
        if sex_node is not None:
            state['base_data']['sex'] = sex_node.text

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

    filepath = os.path.join("./game/save/player", f"{preset_name}.xml")
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
    
    state['base_data']['sex'] = random.choice(['Male', 'Female'])
    if state['base_data']['sex'] == 'Male':
        state['player_name'] = fake.name_male()
    else:
        state['player_name'] = fake.name_female()
 
    
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