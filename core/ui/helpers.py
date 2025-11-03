import pygame
from data.config import *
from data.player_xml_parser import parse_player_data

# Keep rect helper functions here as lightweight UI helpers used by Player logic.
# Modal drawing is moved to modals.py to separate rendering responsibilities.

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


def _parse_player_xml_data(xml_string):
    """Parses the player.xml string and returns base data."""
    root = ET.fromstring(xml_string)
    
    base_data = {
        "name": root.find("name").get("value"),
        "sex": root.find("sex").get("value"),
        "profession": root.find("profession").get("value"),
        "stats": {},
        "attributes": {},
        "initial_loot": [],
        "visuals": {}
    }
    
    # Parse base stats
    for stat in root.find("stats"):
        base_data["stats"][stat.tag] = float(stat.get("value"))
        
    # Parse base attributes
    for attr in root.find("attributes"):
        base_data["attributes"][attr.tag] = float(attr.get("value"))
        
    # Parse visuals
    sprite_node = root.find("visuals/sprite")
    if sprite_node is not None:
        base_data["visuals"]["sprite"] = sprite_node.get("file")
        
    # Parse trait names (effects are in TRAIT_DEFINITIONS)
    trait_names = [trait.tag for trait in root.find("traits")]
    
    return base_data, trait_names

def _draw_player_build_screen(game, state, mouse_pos):
    """Draws the three-column layout and returns clickable rects."""
    game.virtual_screen.fill(DARK_GRAY)
    clickable_rects = {
        "add_trait": [], # List of (trait_name, rect)
        "remove_trait": [], # List of (trait_name, rect)
        "start_button": None
    }
    
    # --- Column 1: Available Traits (Left) ---
    col1_x = 50
    col1_width = 300
    
    available_rect = pygame.Rect(col1_x, 50, col1_width, 620)
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), available_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, available_rect, 1)
    game.virtual_screen.blit(font.render("Available Traits", True, WHITE), (available_rect.x + 10, available_rect.y + 10))

    y_offset = available_rect.y + 40
    for i, trait_name in enumerate(state['available_traits']):
        row_rect = pygame.Rect(available_rect.x + 10, y_offset, available_rect.width - 20, 30)
        
        # Draw Trait Name
        game.virtual_screen.blit(font.render(trait_name.capitalize(), True, WHITE), (row_rect.x, row_rect.y))
        
        # Draw Add Button '>'
        add_btn_rect = pygame.Rect(row_rect.right - 25, row_rect.y, 25, 25)
        pygame.draw.rect(game.virtual_screen, GREEN, add_btn_rect)
        game.virtual_screen.blit(font.render(">", True, WHITE), (add_btn_rect.x + 7, add_btn_rect.y + 2))
        clickable_rects["add_trait"].append((trait_name, add_btn_rect))
        
        y_offset += 35
        if y_offset > available_rect.bottom - 30:
            break


    # --- Column 2: Chosen Traits (Middle) ---
    col2_x = col1_x + col1_width + 20
    col2_width = 300
    
    chosen_rect = pygame.Rect(col2_x, 50, col2_width, 620)
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), chosen_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, chosen_rect, 1)
    game.virtual_screen.blit(font.render("Chosen Traits", True, WHITE), (chosen_rect.x + 10, chosen_rect.y + 10))
    
    y_offset = chosen_rect.y + 40
    for i, trait_name in enumerate(state['chosen_traits']):
        row_rect = pygame.Rect(chosen_rect.x + 10, y_offset, chosen_rect.width - 20, 30)
        
        # Draw Remove Button '<'
        remove_btn_rect = pygame.Rect(row_rect.x, row_rect.y, 25, 25)
        pygame.draw.rect(game.virtual_screen, RED, remove_btn_rect)
        game.virtual_screen.blit(font.render("<", True, WHITE), (remove_btn_rect.x + 7, remove_btn_rect.y + 2))
        clickable_rects["remove_trait"].append((trait_name, remove_btn_rect))
        
        # Draw Trait Name
        game.virtual_screen.blit(font.render(trait_name.capitalize(), True, WHITE), (remove_btn_rect.right + 10, row_rect.y))
        
        y_offset += 35
        if y_offset > chosen_rect.bottom - 30:
            break # Stop drawing if out of space


    # --- Column 3: Player Sprite (Right-Top) & Stats (Right-Bottom) ---
    col3_x = col2_x + col2_width + 20
    col3_width = 400
    padding = 10 # Padding for content inside boxes
    
    # Block 3.1: Sprite
    sprite_rect_container = pygame.Rect(col3_x, 50, col3_width, 250)
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), sprite_rect_container)
    pygame.draw.rect(game.virtual_screen, WHITE, sprite_rect_container, 1)

    if state.get('player_sprite_large'):
        sprite_rect = state['player_sprite_large'].get_rect(center=sprite_rect_container.center)
        game.virtual_screen.blit(state['player_sprite_large'], sprite_rect)

    # Block 3.2: Current Stats
    stats_rect = pygame.Rect(col3_x, sprite_rect_container.bottom + 20, col3_width, 300)
    pygame.draw.rect(game.virtual_screen, (30, 30, 30), stats_rect)
    pygame.draw.rect(game.virtual_screen, WHITE, stats_rect, 1)
    game.virtual_screen.blit(font.render("Current Stats", True, WHITE), (stats_rect.x + 10, stats_rect.y + 10))

    # --- MODIFICATION: Scrollbar logic for Stats Box ---
    
    # 1. Define Content Area (inset, below title)
    stats_content_rect = pygame.Rect(
        stats_rect.x + padding,
        stats_rect.y + 40, 
        stats_rect.width - (padding * 2) - 10, # Make space for scrollbar (10px)
        stats_rect.height - (padding * 2) - 30 # Account for title and bottom padding
    )
    state['stats_content_rect'] = stats_content_rect # Store for input handler

    # 2. Calculate current stats (already done)
    current_stats = state['base_data']['stats'].copy()
    current_attrs = state['base_data']['attributes'].copy()
    
    for trait_name in state['chosen_traits']:
        effects = TRAIT_DEFINITIONS.get(trait_name, {})
        if "stats" in effects:
            for stat, value in effects["stats"].items():
                current_stats[stat] = current_stats.get(stat, 0) + value
        if "attributes" in effects:
            for attr, value in effects["attributes"].items():
                current_attrs[attr] = current_attrs.get(attr, 0) + value
    
    # Store calculated stats for starting the game
    state['final_stats'] = current_stats
    state['final_attrs'] = current_attrs

    # 3. Calculate Scroll parameters
    line_height = 25 # Height of one stat line
    state['stats_line_height'] = line_height # Store for input
    
    num_stats = len(current_stats)
    num_attrs = len(current_attrs)
    total_text_height = (num_stats + num_attrs) * line_height
    
    visible_height = stats_content_rect.height
    max_scroll_offset = max(0, total_text_height - visible_height)
    state['stats_max_scroll'] = max_scroll_offset # Store for input
    
    scroll_offset_y = state.get('stats_scroll_offset_y', 0)
    scroll_offset_y = max(0, min(scroll_offset_y, max_scroll_offset))
    state['stats_scroll_offset_y'] = scroll_offset_y

    # 4. Create Subsurface for clipping
    content_surface = game.virtual_screen.subsurface(stats_content_rect)
    content_surface.fill((30, 30, 30)) # Fill background

    # 5. Draw stats and attributes onto the subsurface
    y_offset = 0 - scroll_offset_y # Start relative to subsurface, offset by scroll
    
    for stat, value in current_stats.items():
        text_surf = font.render(f"{stat.capitalize()}: {value}", True, WHITE)
        content_surface.blit(text_surf, (0, y_offset))
        y_offset += line_height
    for attr, value in current_attrs.items():
        text_surf = font.render(f"{attr.capitalize()}: {value}", True, WHITE)
        content_surface.blit(text_surf, (0, y_offset))
        y_offset += line_height

    # 6. Draw Scrollbar
    if total_text_height > visible_height:
        scrollbar_area_height = stats_content_rect.height
        scrollbar_area_rect = pygame.Rect(stats_content_rect.right + 2, stats_content_rect.top, 8, scrollbar_area_height)
        
        handle_height_ratio = visible_height / total_text_height
        handle_height = max(10, scrollbar_area_height * handle_height_ratio)
        
        handle_pos_ratio = 0
        if max_scroll_offset > 0:
             handle_pos_ratio = scroll_offset_y / max_scroll_offset
        
        handle_y = scrollbar_area_rect.top + (scrollbar_area_height - handle_height) * handle_pos_ratio

        scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, scrollbar_area_rect.width, handle_height)
        pygame.draw.rect(game.virtual_screen, GRAY, scrollbar_handle_rect, 0, 2)
    
    # --- End of Scrollbar Modification ---


    # --- Start Button (Bottom Right) ---
    start_btn_rect = pygame.Rect(col3_x, 600, col3_width, 70)
    pygame.draw.rect(game.virtual_screen, (0, 100, 0), start_btn_rect)
    if start_btn_rect.collidepoint(mouse_pos):
        pygame.draw.rect(game.virtual_screen, (0, 150, 0), start_btn_rect.inflate(-4, -4))
    
    start_text = large_font.render("START GAME", True, WHITE)
    text_rect = start_text.get_rect(center=start_btn_rect.center)
    game.virtual_screen.blit(start_text, text_rect)
    clickable_rects["start_button"] = start_btn_rect
    
    return clickable_rects


def run_player_setup(game):
    # Initialize state on the game object the first time
    if 'base_data' not in game.player_setup_state:
        state = game.player_setup_state
        try:
            state['base_data'], trait_names = parse_player_data()
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

        # Load the player sprite
        try:
            sprite_file = state['base_data']['visuals']['sprite']
            sprite_path = SPRITE_PATH + sprite_file
            sprite_img = pygame.image.load(sprite_path).convert_alpha()
            state['player_sprite_large'] = pygame.transform.scale(sprite_img, (256, 256))
        except Exception as e:
            print(f"Error loading player sprite for setup: {e}")
            state['player_sprite_large'] = pygame.Surface((256, 256), pygame.SRCALPHA)
            state['player_sprite_large'].fill(BLUE) # Fallback

    # Get state and mouse pos
    state = game.player_setup_state
    mouse_pos = game._get_scaled_mouse_pos()
    
    # Handle Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            game.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
        if event.type == pygame.MOUSEWHEEL:
            # Check if mouse is over the stats content rect
            stats_rect = state.get('stats_content_rect')
            if stats_rect and stats_rect.collidepoint(mouse_pos):
                # Get scroll info calculated by the last draw
                line_height = state.get('stats_line_height', 25)
                max_scroll = state.get('stats_max_scroll', 0)
                current_offset = state.get('stats_scroll_offset_y', 0)
                
                # Adjust scroll offset (event.y is 1 for up, -1 for down)
                scroll_amount = event.y * line_height * 2 # Scroll 2 lines
                new_offset = current_offset - scroll_amount # Subtract
                
                # Clamp and store
                state['stats_scroll_offset_y'] = max(0, min(new_offset, max_scroll))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check clicks against rects drawn in the draw function
            clickable_rects = _draw_player_build_screen(game, state, mouse_pos) # Get current rects

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
                # Construct the final player_data dictionary
                final_player_data = state['base_data'].copy() # Start with base
                final_player_data['stats'] = state['final_stats']
                final_player_data['attributes'] = state['final_attrs']
                
                # We can add name input here later if needed
                # For now, use default name
                
                # Call the modified start_new_game with the data dict
                game.start_new_game(final_player_data)
                game.game_state = 'PLAYING'
                return

    _draw_player_build_screen(game, state, mouse_pos)
    game._update_screen()