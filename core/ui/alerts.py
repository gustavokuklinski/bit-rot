import pygame
import math
from core.data.config import *
# [CHANGED] Removed draw_tooltip import as we now return the proxy instead of drawing it directly
# from core.ui.tooltip import draw_tooltip 

# Cache for icons to prevent reloading every frame
_alert_icons = {}

class AlertTooltipProxy:
    def __init__(self, text):
        self.name = text
        # Initialize attributes required by draw_tooltip to None to skip those logic blocks
        self.item_type = None
        self.durability = None
        self.defence = None
        self.load = None
        self.min_damage = None
        self.max_damage = None
        self.ammo_type = None

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
    Returns the tooltip proxy if an alert is hovered, otherwise None.
    """
    if not player:
        return None

    active_alerts = []

    # --- 1. Define Alert Rules ---
    # Format: (Icon Path, Color, Tooltip Text)
    
    # Health (Low)
    if player.health <= 80:
        active_alerts.append(("ui/hp.png", RED, "You are hurt, use a Medkit."))
    
    # Stamina (Low) - Exhausted
    if player.stamina <= 50:
        active_alerts.append(("ui/stamina.png", GRAY, "You are tired, take a Rest."))

    # Water (Low) - Thirsty
    if player.water <= 70:
        active_alerts.append(("ui/water.png", BLUE, "You are thirsty."))

    # Food (Low) - Hungry
    if player.food <= 50:
        active_alerts.append(("ui/food.png", GREEN, "You are hungry, try some MRE's."))

    # Tireness (High) - Tired
    if player.tireness <= 20:
        active_alerts.append(("ui/tireness.png", (100, 100, 150), "You are feeling sleepy, take a nap."))

    # Anxiety (High) - Panicked
    if player.anxiety >= 10:
        active_alerts.append(("ui/axiety.png", (150, 0, 150), "You are anxious, try reading."))
        
    # Infection (High) - Sick
    if player.infection >= 15: 
        active_alerts.append(("ui/infection.png", YELLOW, "Are you feeling sick or infected?"))

    # Overweight
    if player.current_weight > player.max_carry_weight:
        # Using an orange/brown color for the weight warning
        active_alerts.append(("ui/weight.png", (205, 127, 50), "You are carrying too much weight."))

    if not active_alerts:
        return None

    # --- 2. Calculate Layout (Center Top, Side-by-Side) ---
    num_alerts = len(active_alerts)
    icon_size = 32
    padding = 15 
    
    total_width = (num_alerts * icon_size) + (max(0, num_alerts - 1) * padding)
    start_x = (GAME_WIDTH // 2) - (total_width // 2)
    fixed_y = 10 

    # --- 3. Draw Alerts & Detect Hover ---
    current_time = pygame.time.get_ticks()
    mouse_pos = pygame.mouse.get_pos()
    tooltip_proxy = None # Store the proxy item if we need to draw it

    for i, (icon_file, color, tooltip_text) in enumerate(active_alerts):
        # Calculate X position
        x = start_x + (i * (icon_size + padding))
        y = fixed_y
        
        icon = _get_alert_icon(icon_file)
        
        draw_x = int(x)
        draw_y = int(y)

        # Draw Background Box
        bg_rect = pygame.Rect(draw_x - 2, draw_y - 2, icon_size + 4, icon_size + 4)
        pygame.draw.rect(surface, (20, 20, 20), bg_rect, border_radius=4)
        pygame.draw.rect(surface, color, bg_rect, 1, border_radius=4)
        
        # Draw Icon
        surface.blit(icon, (draw_x, draw_y))

        # [3] Check Hover
        if bg_rect.collidepoint(mouse_pos):
            # Create a lightweight proxy object for this specific alert
            tooltip_proxy = AlertTooltipProxy(tooltip_text)

    # --- 4. Return Proxy instead of drawing immediately ---
    return tooltip_proxy