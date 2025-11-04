import pygame
import xml.etree.ElementTree as ET
from data.config import *
# MODIFICATION: Import the parser from its correct location
import data.player_xml_parser
from core.entities.item.item import Item, ITEM_TEMPLATES

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
    "myopia": {"cost": -1, "attributes": {"ranged": -10}}, # View radius not handled here
}

# cached logo image
_logo_img = None

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

    # 2. Draw the open list if this dropdown is active
    if state.get('active_dropdown') == slot_name:
        options = state['available_clothes'].get(slot_name, [])
        if not options:
            return clickable_rects # No options to draw
            
        option_height = 25
        list_height = len(options) * option_height
        list_rect = pygame.Rect(rect.x, rect.bottom, rect.width, list_height)
        
        # --- FIX 1: This draw call is now at the END of the main draw function ---
        # We only return the rects here.
        
        y_offset = list_rect.y
        for option_name in options:
            # --- FIX 2: Option rect width now matches list_rect width ---
            option_rect = pygame.Rect(list_rect.x, y_offset, list_rect.width, option_height)
            clickable_rects['options'].append((option_name, option_rect))
            y_offset += option_height

    return clickable_rects

def _draw_player_build_screen(game, state, mouse_pos):
    """Draws the three-column layout and returns clickable rects."""
    game.virtual_screen.fill(DARK_GRAY)
    
    clickable_rects = {
        "add_trait": [], 
        "remove_trait": [],
        "start_button": None,
        "dropdown_buttons": {},
        "dropdown_options": [] 
    }
    
    padding = 10
    
    # --- Column 1: Available Traits (Left) ---
    col1_x = 50
    col1_width = 300
    available_rect = pygame.Rect(col1_x, 50, col1_width, 640) # Full height
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), available_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, available_rect, 1)
    game.virtual_screen.blit(font.render("Available Traits", True, WHITE), (available_rect.x + 10, available_rect.y + 10))

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


    # --- Column 2: Chosen Traits (Top-Middle) & Gear (Bottom-Middle) ---
    col2_x = col1_x + col1_width + 20
    col2_width = 300
    
    # Block 2.1: Chosen Traits
    chosen_rect = pygame.Rect(col2_x, 50, col2_width, 310) # Top half
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), chosen_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, chosen_rect, 1)
    game.virtual_screen.blit(font.render("Chosen Traits", True, WHITE), (chosen_rect.x + 10, chosen_rect.y + 10))
    
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

    # Block 2.2: Gear Selection
    gear_rect = pygame.Rect(col2_x, chosen_rect.bottom + 20, col2_width, 310) # Bottom half
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), gear_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, gear_rect, 1)
    game.virtual_screen.blit(font.render("Gear", True, WHITE), (gear_rect.x + 10, gear_rect.y + 10))

    y_offset = gear_rect.y + 40
    label_width = 80
    dropdown_width = col2_width - label_width - (padding * 3) # Use col2_width
    dropdown_draw_list = [] # Store (slot_name, rect) to draw buttons later
    
    for slot_name in state['chosen_clothes'].keys():
        game.virtual_screen.blit(font.render(f"{slot_name.capitalize()}:", True, WHITE), (gear_rect.x + padding, y_offset + 5))
        dropdown_rect = pygame.Rect(gear_rect.x + label_width + (padding * 2), y_offset, dropdown_width, 25)
        
        # --- FIX 1: Store rect to draw later, don't draw here ---
        dropdown_draw_list.append((slot_name, dropdown_rect))
        
        y_offset += 35 # Give more space for dropdowns
        if y_offset > gear_rect.bottom - 30: break


    # --- Column 3: Player Sprite (Top-Right) & Stats (Bottom-Right) ---
    col3_x = col2_x + col2_width + 20
    col3_width = 400
    
    # Block 3.1: Sprite
    sprite_rect_container = pygame.Rect(col3_x, 50, col3_width, 310) # Top half
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), sprite_rect_container)
    pygame.draw.rect(game.virtual_screen, WHITE, sprite_rect_container, 1)
    
    if state.get('player_sprite_large'):
        sprite_rect = state['player_sprite_large'].get_rect(center=sprite_rect_container.center)
        # Draw base sprite
        game.virtual_screen.blit(state['player_sprite_large'], sprite_rect)
        
        # --- FIX 3: Draw clothes on top of sprite ---
        for slot in state['clothes_slots']: # Use defined order for correct layering
            item_name = state['chosen_clothes'].get(slot)
            if item_name and item_name != "None":
                # Get the pre-loaded clothing sprite
                clothing_img = state['clothing_sprites'].get(item_name)
                if clothing_img:
                    # Blit the clothing image directly over the player sprite
                    game.virtual_screen.blit(clothing_img, sprite_rect)

    # Block 3.2: Current Stats
    stats_rect = pygame.Rect(col3_x, sprite_rect_container.bottom + 20, col3_width, 240) # Bottom half (smaller)
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), stats_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, stats_rect, 1)
    game.virtual_screen.blit(font.render("Current Stats", True, WHITE), (stats_rect.x + 10, stats_rect.y + 10))
    
    # (Stats calculation and scrolling logic - unchanged)
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
    content_surface = game.virtual_screen.subsurface(stats_content_rect)
    content_surface.fill((30, 30, 30))
    y_offset = 0 - scroll_offset_y
    for stat, value in current_stats.items():
        content_surface.blit(font.render(f"{stat.capitalize()}: {value}", True, WHITE), (0, y_offset)); y_offset += line_height
    for attr, value in current_attrs.items():
        content_surface.blit(font.render(f"{attr.capitalize()}: {value}", True, WHITE), (0, y_offset)); y_offset += line_height
    if total_text_height > visible_height:
        scrollbar_area_height = stats_content_rect.height
        scrollbar_area_rect = pygame.Rect(stats_content_rect.right + 2, stats_content_rect.top, 8, scrollbar_area_height)
        handle_height_ratio = visible_height / total_text_height
        handle_height = max(10, scrollbar_area_height * handle_height_ratio)
        handle_pos_ratio = 0
        if max_scroll_offset > 0: handle_pos_ratio = scroll_offset_y / max_scroll_offset
        handle_y = scrollbar_area_rect.top + (scrollbar_area_height - handle_height) * handle_pos_ratio
        pygame.draw.rect(game.virtual_screen, GRAY, pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height), 0, 2)
    # (End of unchanged stats logic)


    # --- Start Button (Bottom Right) ---
    start_btn_rect = pygame.Rect(col3_x, stats_rect.bottom + 20, col3_width, 70) # Below stats
    pygame.draw.rect(game.virtual_screen, (0, 100, 0), start_btn_rect)
    if start_btn_rect.collidepoint(mouse_pos):
        pygame.draw.rect(game.virtual_screen, (0, 150, 0), start_btn_rect.inflate(-4, -4))
    start_text = large_font.render("START GAME", True, WHITE)
    text_rect = start_text.get_rect(center=start_btn_rect.center)
    game.virtual_screen.blit(start_text, text_rect)
    clickable_rects["start_button"] = start_btn_rect

    # --- FIX 1: Draw dropdowns LAST (so they appear on top) ---
    active_dropdown_slot = state.get('active_dropdown')
    
    # First, draw all *inactive* buttons
    for slot_name, rect in dropdown_draw_list:
        if slot_name != active_dropdown_slot:
            dropdown_rects = _draw_dropdown(game.virtual_screen, state, slot_name, rect, mouse_pos)
            clickable_rects['dropdown_buttons'][slot_name] = dropdown_rects['button']

    # Then, draw the *active* button (so its list renders on top of all other elements)
    if active_dropdown_slot:
        for slot_name, rect in dropdown_draw_list:
            if slot_name == active_dropdown_slot:
                # Call _draw_dropdown, which will draw the button AND return the option rects
                dropdown_rects = _draw_dropdown(game.virtual_screen, state, slot_name, rect, mouse_pos)
                clickable_rects['dropdown_buttons'][slot_name] = dropdown_rects['button']
                
                # Now, manually draw the option list on top of everything
                options = state['available_clothes'].get(slot_name, [])
                option_height = 25
                list_height = len(options) * option_height
                list_rect = pygame.Rect(rect.x, rect.bottom, rect.width, list_height)
                
                pygame.draw.rect(game.virtual_screen, (30, 30, 30), list_rect)
                pygame.draw.rect(game.virtual_screen, WHITE, list_rect, 1)
                
                y_offset = list_rect.y
                # Clear and repopulate the clickable options
                clickable_rects["dropdown_options"] = [] 
                for option_name in options:
                    # FIX 2: Use list_rect.width for the option rect
                    option_rect = pygame.Rect(list_rect.x, y_offset, list_rect.width, option_height)
                    
                    if option_rect.collidepoint(mouse_pos):
                        pygame.draw.rect(game.virtual_screen, (70, 70, 70), option_rect)
                        
                    text = font.render(option_name, True, WHITE)
                    game.virtual_screen.blit(text, (option_rect.x + 5, option_rect.y + 2))
                    
                    clickable_rects['dropdown_options'].append((slot_name, option_name, option_rect))
                    y_offset += option_height
                break # Stop after drawing the active one
    
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
        
        state['stats_scroll_offset_y'] = 0
        state['stats_content_rect'] = None # Will be set by draw function
        state['stats_line_height'] = 25 # Default
        state['stats_max_scroll'] = 0 # Default

        Item.load_item_templates()

        state['clothes_slots'] = ['head',  'legs', 'feet','hand', 'torso', 'body']
        
        state['available_clothes'] = {slot: [] for slot in state['clothes_slots']}
        state['chosen_clothes'] = {slot: "None" for slot in state['clothes_slots']}
        state['active_dropdown'] = None # Stores the name of the active dropdown (e.g., 'head')

        state['clothing_sprites'] = {} # Cache for clothing images


        player_sprite_size = (128, 128) 

        for item_name, template in ITEM_TEMPLATES.items():
            if template.get('type') == 'cloth':
                slot = template.get('properties', {}).get('slot', {}).get('value')
                if slot in state['available_clothes']:

                    if not item_name.startswith("Empty"):
                        state['available_clothes'][slot].append(item_name)
                  

                    # Pre-load and scale the sprite
                    sprite_file = template.get('properties', {}).get('sprite', {}).get('file')
                    if sprite_file:
                        try:
                            path = SPRITE_PATH + "clothes/" + sprite_file
                            img = pygame.image.load(path).convert_alpha()
                            scaled_img = pygame.transform.scale(img, player_sprite_size)
                            state['clothing_sprites'][item_name] = scaled_img
                        except Exception as e:
                            print(f"Error loading cloth sprite {sprite_file}: {e}")

        # Add "None" option to each slot
        for slot in state['available_clothes']:
            state['available_clothes'][slot].insert(0, "None")

    
        # Load the player sprite
        try:
            # --- FIX 3: Correct path loading ---
            # The parser already prepends SPRITE_PATH + 'player/'
            sprite_path = SPRITE_PATH + state['base_data']['visuals']['sprite']
            sprite_img = pygame.image.load(sprite_path).convert_alpha()
            state['player_sprite_large'] = pygame.transform.scale(sprite_img, player_sprite_size)
        except Exception as e:
            print(f"Error loading player sprite for setup: {e}")
            state['player_sprite_large'] = pygame.Surface(player_sprite_size, pygame.SRCALPHA)
            state['player_sprite_large'].fill(BLUE) # Fallback

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
            if stats_rect and stats_rect.collidepoint(mouse_pos):
                line_height = state.get('stats_line_height', 25)
                max_scroll = state.get('stats_max_scroll', 0)
                current_offset = state.get('stats_scroll_offset_y', 0)
                scroll_amount = event.y * line_height * 2 
                new_offset = current_offset - scroll_amount
                state['stats_scroll_offset_y'] = max(0, min(new_offset, max_scroll))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            dropdown_clicked = False
            
            # 1. Check if an active dropdown's *options* were clicked
            if state.get('active_dropdown'):
                # Use the rects calculated and stored by the draw function
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
                    dropdown_clicked = True
                    break
            
            # 3. If clicking anywhere else (and not opening a new dropdown), close any active dropdown
            if not dropdown_clicked and state.get('active_dropdown'):
                state['active_dropdown'] = None
            
            if dropdown_clicked: continue
            # --- End Dropdown Logic ---

            # Check Add Trait buttons
            for trait_name, rect in clickable_rects["add_trait"]:
                if rect.collidepoint(mouse_pos):
                    if trait_name in state['available_traits']:
                        state['available_traits'].remove(trait_name)
                        state['chosen_traits'].append(trait_name)
                        break # Stop checking after one click
            
            # Check Remove Trait buttons
            for trait_name, rect in clickable_rects["remove_trait"]:
                if rect.collidepoint(mouse_pos):
                    if trait_name in state['chosen_traits']:
                        state['chosen_traits'].remove(trait_name)
                        state['available_traits'].append(trait_name)
                        break
            
            # Check Start Button
            if clickable_rects["start_button"] and clickable_rects["start_button"].collidepoint(mouse_pos):
                final_player_data = state['base_data'].copy() # Start with base
                final_player_data['stats'] = state['final_stats']
                final_player_data['attributes'] = state['final_attrs']
                final_player_data['clothes'] = state['chosen_clothes']
                
                game.start_new_game(final_player_data)
                game.game_state = 'PLAYING'
                return

    # Draw the screen (updates highlights and dropdown states)
    _draw_player_build_screen(game, state, mouse_pos)
    game._update_screen()