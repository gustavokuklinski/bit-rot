import pygame
from core.data.config import *

_inventory_img = None
_status_img = None
_nearby_img = None
_message_img = None
_gear_img = None

def draw_status_button(surface):
    global _status_img
    if _status_img is None:
        try:
            _status_img = pygame.image.load(SPRITE_PATH + 'ui/status.png').convert_alpha()
            _status_img = pygame.transform.scale(_status_img, (40, 40))
        except pygame.error:
            _status_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _status_img.fill(GRAY)
    
    # Position: 10 (Top)
    button_rect = pygame.Rect(10, 10, 40, 40)
    surface.blit(_status_img, button_rect)
    return button_rect

def draw_inventory_button(surface):
    global _inventory_img
    if _inventory_img is None:
        try:
            _inventory_img = pygame.image.load(SPRITE_PATH + 'ui/inventory.png').convert_alpha()
            _inventory_img = pygame.transform.scale(_inventory_img, (40, 40))
        except pygame.error:
            _inventory_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _inventory_img.fill(GRAY)
            
    # Previous: 50. New: 60 (Status 10+40=50 + 10 gap)
    button_inventory_rect = pygame.Rect(10, 60, 40, 40)
    surface.blit(_inventory_img, button_inventory_rect)
    return button_inventory_rect

def draw_gear_button(surface):
    global _gear_img
    if _gear_img is None:
        try:
            _gear_img = pygame.image.load(SPRITE_PATH + 'ui/gear.png').convert_alpha()
            _gear_img = pygame.transform.scale(_gear_img, (40, 40))
        except pygame.error:
            _gear_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _gear_img.fill(GRAY)
            
    # Previous: 90 (Overlap). New: 130 (Inventory 60+60=120 + 10 gap)
    button_gear_rect = pygame.Rect(10, 110, 40, 40)
    surface.blit(_gear_img, button_gear_rect)
    return button_gear_rect

def draw_nearby_button(surface):
    global _nearby_img
    if _nearby_img is None:
        try:
            _nearby_img = pygame.image.load(SPRITE_PATH + 'ui/nearby.png').convert_alpha()
            _nearby_img = pygame.transform.scale(_nearby_img, (40, 40))
        except pygame.error:
            _nearby_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _nearby_img.fill(GRAY)
            
    # Previous: 145. New: 200 (Gear 130+60=190 + 10 gap)
    button_nearby_rect = pygame.Rect(10, 160, 40, 40)
    surface.blit(_nearby_img, button_nearby_rect)
    return button_nearby_rect

def draw_messages_button(surface):
    global _message_img
    if _message_img is None:
        try:
            _message_img = pygame.image.load(SPRITE_PATH + 'ui/messages.png').convert_alpha()
            _message_img = pygame.transform.scale(_message_img, (40, 40))
        except pygame.error as e:
            print(f"Warning: Could not load message icon: {e}")
            _message_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _message_img.fill(GRAY)
    
    # Previous: 200. New: 270 (Nearby 200+60=260 + 10 gap)
    button_messages_rect = pygame.Rect(10, 210, 40, 40) 
    surface.blit(_message_img, button_messages_rect)
    return button_messages_rect