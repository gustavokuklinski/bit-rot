import pygame
from core.data.config import *

_inventory_img = None
_status_img = None
_nearby_img = None
_message_img = None
_gear_img = None
_crafting_img = None
_pause_img = None
_forward_img = None
_help_img = None
_slots_img = None

def draw_pause_button(surface, view_left, view_right, view_bottom):
    global _pause_img
    if _pause_img is None:
        try:
            _pause_img = pygame.image.load(SPRITE_PATH + 'ui/pause.png').convert_alpha()
            _pause_img = pygame.transform.scale(_pause_img, (15, 15))
        except pygame.error:
            _pause_img = pygame.Surface((15, 15), pygame.SRCALPHA)
            _pause_img.fill(GRAY)
    
    # Position relative to view_left
    button_rect = pygame.Rect(view_left + 10, 10, 15, 15)
    surface.blit(_pause_img, button_rect)
    return button_rect

def draw_status_button(surface, view_left, view_right, view_bottom):
    global _status_img
    if _status_img is None:
        try:
            _status_img = pygame.image.load(SPRITE_PATH + 'ui/status.png').convert_alpha()
            _status_img = pygame.transform.scale(_status_img, (40, 40))
        except pygame.error:
            _status_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _status_img.fill(GRAY)
    
    # Position relative to view_left
    button_rect = pygame.Rect(view_left + 10, 40, 40, 40)
    surface.blit(_status_img, button_rect)
    return button_rect

def draw_inventory_button(surface, view_left, view_right, view_bottom):
    global _inventory_img
    if _inventory_img is None:
        try:
            _inventory_img = pygame.image.load(SPRITE_PATH + 'ui/inventory.png').convert_alpha()
            _inventory_img = pygame.transform.scale(_inventory_img, (40, 40))
        except pygame.error:
            _inventory_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _inventory_img.fill(GRAY)
            
    # Position relative to view_left
    button_inventory_rect = pygame.Rect(view_left + 10, 90, 40, 40)
    surface.blit(_inventory_img, button_inventory_rect)
    return button_inventory_rect

def draw_gear_button(surface, view_left, view_right, view_bottom):
    global _gear_img
    if _gear_img is None:
        try:
            _gear_img = pygame.image.load(SPRITE_PATH + 'ui/gear.png').convert_alpha()
            _gear_img = pygame.transform.scale(_gear_img, (40, 40))
        except pygame.error:
            _gear_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _gear_img.fill(GRAY)
            
    # Position relative to view_left
    button_gear_rect = pygame.Rect(view_left + 10, 140, 40, 40)
    surface.blit(_gear_img, button_gear_rect)
    return button_gear_rect

def draw_slots_button(surface, view_left, view_right, view_bottom):
    global _slots_img
    if _slots_img is None:
        try:
            _slots_img = pygame.image.load(SPRITE_PATH + 'ui/slots.png').convert_alpha()
            _slots_img = pygame.transform.scale(_slots_img, (40, 40))
        except pygame.error:
            _slots_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _slots_img.fill(GRAY)
            
    # Position relative to view_left
    button_slots_rect = pygame.Rect(view_left + 10, 190, 40, 40)
    surface.blit(_slots_img, button_slots_rect)
    return button_slots_rect

def draw_nearby_button(surface, view_left, view_right, view_bottom):
    global _nearby_img
    if _nearby_img is None:
        try:
            _nearby_img = pygame.image.load(SPRITE_PATH + 'ui/nearby.png').convert_alpha()
            _nearby_img = pygame.transform.scale(_nearby_img, (40, 40))
        except pygame.error:
            _nearby_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _nearby_img.fill(GRAY)
            
    # Position relative to view_left
    button_nearby_rect = pygame.Rect(view_left + 10, 240, 40, 40)
    surface.blit(_nearby_img, button_nearby_rect)
    return button_nearby_rect

def draw_messages_button(surface, view_left, view_right, view_bottom):
    global _message_img
    if _message_img is None:
        try:
            _message_img = pygame.image.load(SPRITE_PATH + 'ui/messages.png').convert_alpha()
            _message_img = pygame.transform.scale(_message_img, (40, 40))
        except pygame.error as e:
            print(f"Warning: Could not load message icon: {e}")
            _message_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _message_img.fill(GRAY)
    
    # Position relative to view_left
    button_messages_rect = pygame.Rect(view_left + 10, 290, 40, 40)
    surface.blit(_message_img, button_messages_rect)
    return button_messages_rect

def draw_crafting_button(surface, view_left, view_right, view_bottom):
    global _crafting_img
    if _crafting_img is None:
        try:
            _crafting_img = pygame.image.load(SPRITE_PATH + 'ui/craft.png').convert_alpha()
            _crafting_img = pygame.transform.scale(_crafting_img, (40, 40))
        except pygame.error:
            _crafting_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _crafting_img.fill(GRAY)
            pygame.draw.rect(_crafting_img, (200, 200, 200), (5, 5, 30, 30), 1)
            
    # Position relative to view_left
    button_rect = pygame.Rect(view_left + 10, 340, 40, 40)
    surface.blit(_crafting_img, button_rect)
    return button_rect

def draw_help_button(surface, view_left, view_right, view_bottom):
    global _help_img
    if _help_img is None:
        try:
            _help_img = pygame.image.load(SPRITE_PATH + 'ui/help.png').convert_alpha()
            _help_img = pygame.transform.scale(_help_img, (40, 40))
        except pygame.error:
            _help_img = pygame.Surface((40, 40), pygame.SRCALPHA)
            _help_img.fill(GRAY)
            
    # Position relative to view_left
    button_rect = pygame.Rect(view_left + 10, 390, 40, 40)
    surface.blit(_help_img, button_rect)
    return button_rect