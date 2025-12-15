import pygame
import math
from core.data.config import *

# Cache for icons to prevent reloading every frame
_alert_icons = {}

def _get_alert_icon(filename):
    """Loads and caches alert icons."""
    if filename not in _alert_icons:
        try:
            path = SPRITE_PATH + filename
            img = pygame.image.load(path).convert_alpha()
            # Scale to a nice HUD size (e.g., 32x32)
            _alert_icons[filename] = pygame.transform.scale(img, (32, 32))
        except Exception as e:
            print(f"Error loading alert icon {filename}: {e}")
            # Create fallback colored surface
            surf = pygame.Surface((32, 32))
            surf.fill(RED)
            _alert_icons[filename] = surf
    return _alert_icons[filename]

def draw_player_alerts(surface, player):
    """
    Checks player stats and draws alerts at the top center of the screen.
    """
    if not player:
        return

    active_alerts = []

    # --- 1. Define Alert Rules ---
    # Format: (Condition, Icon Path, Background/Border Color, Pulse Speed)
    
    # Health (Low)
    if player.health <= 50:
        active_alerts.append(("ui/hp.png", RED))
    
    # Stamina (Low) - Exhausted
    if player.stamina <= 50:
        active_alerts.append(("ui/stamina.png", GRAY))

    # Water (Low) - Thirsty
    if player.water <= 50:
        active_alerts.append(("ui/water.png", BLUE))

    # Food (Low) - Hungry
    if player.food <= 50:
        active_alerts.append(("ui/food.png", GREEN))

    # Tireness (High) - Tired
    if player.tireness <= 50:
        active_alerts.append(("ui/tireness.png", (100, 100, 150)))

    # Anxiety (High) - Panicked
    if player.anxiety >= 10:
        active_alerts.append(("ui/axiety.png", (150, 0, 150)))
        
    # Infection (High) - Sick
    if player.infection >= 5: # 10% is significant for infection
        active_alerts.append(("ui/infection.png", YELLOW))

    if not active_alerts:
        return

    # --- 2. Calculate Layout (Center Top, Side-by-Side) ---
    num_alerts = len(active_alerts)
    icon_size = 32
    padding = 15  # Spacing between icons
    
    # Calculate total width of the entire alert block
    total_width = (num_alerts * icon_size) + (max(0, num_alerts - 1) * padding)
    
    # Calculate the starting X position to center the block
    start_x = (VIRTUAL_SCREEN_WIDTH // 2) - (total_width // 2)
    fixed_y = 10 # Fixed distance from the very top of the screen

    # --- 3. Draw Alerts ---
    current_time = pygame.time.get_ticks()
    
    for i, (icon_file, color) in enumerate(active_alerts):
        # Calculate X position for this specific icon (Side by Side)
        x = start_x + (i * (icon_size + padding))
        y = fixed_y
        
        icon = _get_alert_icon(icon_file)
        
        # Determine final positions
        draw_x = int(x)
        draw_y = int(y)

        # Draw Background Box
        bg_rect = pygame.Rect(draw_x - 2, draw_y - 2, icon_size + 4, icon_size + 4)
        pygame.draw.rect(surface, (20, 20, 20), bg_rect, border_radius=4)
        pygame.draw.rect(surface, color, bg_rect, 1, border_radius=4)
        
        # Draw Icon
        surface.blit(icon, (draw_x, draw_y))