# core/ui/modals.py
import pygame
from core.data.config import *
from core.data.localization import tr

MODAL_DIMENSIONS = {
    'inventory': (INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT),
    'status': (STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT),
    'container': (CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT),
    'nearby': (NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT),
    'messages': (MESSAGES_MODAL_WIDTH, MESSAGES_MODAL_HEIGHT),
    'text': (TEXT_MODAL_WIDTH, TEXT_MODAL_HEIGHT),
    'gear': (GEAR_MODAL_WIDTH, GEAR_MODAL_HEIGHT),
    'mobile': (MOBILE_MODAL_WIDTH, MOBILE_MODAL_HEIGHT),
    'vehicle': (VEHICLE_MODAL_WIDTH, VEHICLE_MODAL_HEIGHT),
    'crafting': (CRAFTING_MODAL_WIDTH, CRAFTING_MODAL_HEIGHT),
    'big_map': (MAP_MODAL_WIDTH, MAP_MODAL_HEIGHT),
    'help': (HELP_MODAL_WIDTH, HELP_MODAL_HEIGHT),
    'npc_dialog': (NPC_DIALOG_MODAL_WIDTH, NPC_DIALOG_MODAL_HEIGHT),
    'slots': (SLOTS_MODAL_WIDTH, SLOTS_MODAL_HEIGHT)
}

def draw_scrollbar(surface, modal, bar_rect, viewport_height, total_height, scroll_offset):
    """Standardized scrollbar pattern across UI modals."""
    max_scroll = max(0, total_height - viewport_height)
    modal['max_scroll_offset'] = max_scroll

    if max_scroll <= 0:
        modal['scrollbar_handle_rect'] = None
        return

    pygame.draw.rect(surface, DARK_GRAY, bar_rect, border_radius=3)

    handle_h = max(20, (viewport_height / total_height) * bar_rect.height)
    scroll_pct = scroll_offset / max_scroll if max_scroll > 0 else 0
    handle_y = bar_rect.y + scroll_pct * (bar_rect.height - handle_h)

    handle_rect = pygame.Rect(bar_rect.x, handle_y, bar_rect.width, handle_h)
    pygame.draw.rect(surface, GRAY, handle_rect, border_radius=3)
    modal['scrollbar_handle_rect'] = handle_rect

class BaseModal:
    def __init__(self, surface, modal, assets, title, w=None, h=None):
        self.surface = surface
        self.modal = modal
        self.assets = assets
        self.title = tr('modal', title)
        
        default_w, default_h = MODAL_DIMENSIONS.get(modal.get('type', ''), (244, 240))
        self.modal_w = w or default_w
        self.modal_h = h or default_h
        
        self.modal_x, self.modal_y = modal['position']
        self.header_h = 35
        self.is_active = modal.get('is_active', False)
        
        self.modal_rect = pygame.Rect(self.modal_x, self.modal_y, self.modal_w, self.modal_h)
        self.close_button_rect = self.assets['close_button'].get_rect(topright=(self.modal_x + self.modal_w - 10, self.modal_y + 10))
        self.modal['close_button_rect'] = self.close_button_rect

    def draw_header(self):
        self.modal_x, self.modal_y = self.modal['position']
        self.modal_rect.topleft = (self.modal_x, self.modal_y)
        self.close_button_rect.topright = (self.modal_x + self.modal_w - 10, self.modal_y + 10)
        self.modal['close_button_rect'] = self.close_button_rect
        header_rect = pygame.Rect(self.modal_x, self.modal_y, self.modal_w, self.header_h)
        header_color = GRAY if self.is_active else GRAY_60 
        border_color = WHITE if self.is_active else GRAY     
        
        pygame.draw.rect(self.surface, header_color, header_rect, 0, border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.rect(self.surface, border_color, header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)
        
        title_text = font_12.render(self.title, False, WHITE)
        self.surface.blit(title_text, (self.modal_x + 10, self.modal_y + 10))
        self.surface.blit(self.assets['close_button'], self.close_button_rect)

    def draw_base(self):
        s = pygame.Surface((self.modal_w, self.modal_h), pygame.SRCALPHA)
        s.fill((20, 20, 20, 250))
        self.surface.blit(s, (self.modal_x, self.modal_y))

        border_color = WHITE if self.is_active else GRAY
        pygame.draw.rect(self.surface, border_color, self.modal_rect, 1, 4)
        self.draw_header()

    def get_buttons(self):
        self.modal_x, self.modal_y = self.modal['position']
        self.close_button_rect.topright = (self.modal_x + self.modal_w - 10, self.modal_y + 10)
        return ({'id': self.modal.get('id'), 'type': 'close', 'rect': self.close_button_rect},)