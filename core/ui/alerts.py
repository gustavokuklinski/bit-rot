# core/ui/alerts.py
import pygame
from core.data.config import *
from core.data.localization import tr
from core.data.progression_loader import PROGRESSION_CONFIG

_alert_icons = {}

class AlertTooltipProxy:
    def __init__(self, text):
        self.name = text
        self.item_type = None
        self.durability = None
        self.defence = None
        self.load = None
        self.min_damage = None
        self.max_damage = None
        self.ammo_type = None

def _get_alert_icon(filename):
    if filename not in _alert_icons:
        try:
            path = SPRITE_PATH + filename
            img = pygame.image.load(path).convert_alpha()
            _alert_icons[filename] = pygame.transform.scale(img, (32, 32))
        except Exception as e:
            surf = pygame.Surface((32, 32))
            surf.fill(RED)
            _alert_icons[filename] = surf
    return _alert_icons[filename]

def draw_player_alerts(surface, player):
    if not player:
        return None

    active_alerts = []
    
    # Wrapped strings with tr()
    # Wrapped strings with tr() and dynamic thresholds
    if player.health <= PROGRESSION_CONFIG.get_stat('health', 'alert_threshold', 50.0):
        active_alerts.append(("ui/hp.png", RED, tr('alert', "You are hurt, use a Medkit.")))
    
    if player.stamina <= PROGRESSION_CONFIG.get_stat('stamina', 'alert_threshold', 25.0):
        active_alerts.append(("ui/stamina.png", GRAY, tr('alert', "You are tired, take a Rest.")))

    if player.water <= PROGRESSION_CONFIG.get_stat('water', 'alert_threshold', 20.0):
        active_alerts.append(("ui/water.png", BLUE, tr('alert', "You are thirsty.")))

    if player.food <= PROGRESSION_CONFIG.get_stat('food', 'alert_threshold', 20.0):
        active_alerts.append(("ui/food.png", GREEN, tr('alert', "You are hungry, try some MRE's.")))

    if player.anxiety >= PROGRESSION_CONFIG.get_stat('anxiety', 'alert_threshold', 30.0):
        active_alerts.append(("ui/axiety.png", (150, 0, 150), tr('alert', "You are anxious, try reading.")))
        
    if player.infection >= PROGRESSION_CONFIG.get_stat('infection', 'alert_threshold', 70.0): 
        active_alerts.append(("ui/infection.png", YELLOW, tr('alert', "Are you feeling sick or infected?")))

    if player.max_carry_weight > 0:
        weight_ratio = player.current_weight / player.max_carry_weight
        alert_threshold = PROGRESSION_CONFIG.get_stat('weight', 'alert_threshold', 0.75)
        
        if weight_ratio >= alert_threshold:
            if weight_ratio >= 1.0:
                active_alerts.append(("ui/weight.png", (205, 127, 50), tr('alert', "You are carrying too much weight.")))
            else:
                active_alerts.append(("ui/weight.png", (205, 127, 50), tr('alert', "You are carrying a heavy load.")))

    if not active_alerts:
        return None

    num_alerts = len(active_alerts)
    icon_size = 32
    padding = 15 
    
    total_width = (num_alerts * icon_size) + (max(0, num_alerts - 1) * padding)
    start_x = (GAME_WIDTH // 2) - (total_width // 2)
    fixed_y = 10 

    mouse_pos = pygame.mouse.get_pos()
    tooltip_proxy = None 

    for i, (icon_file, color, tooltip_text) in enumerate(active_alerts):
        x = start_x + (i * (icon_size + padding))
        y = fixed_y
        
        icon = _get_alert_icon(icon_file)
        
        draw_x = int(x)
        draw_y = int(y)

        bg_rect = pygame.Rect(draw_x - 2, draw_y - 2, icon_size + 4, icon_size + 4)
        pygame.draw.rect(surface, (20, 20, 20), bg_rect, border_radius=4)
        pygame.draw.rect(surface, color, bg_rect, 1, border_radius=4)
        surface.blit(icon, (draw_x, draw_y))

        if bg_rect.collidepoint(mouse_pos):
            tooltip_proxy = AlertTooltipProxy(tooltip_text)

    return tooltip_proxy