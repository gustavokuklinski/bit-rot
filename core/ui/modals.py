import pygame
from core.data.config import *
from core.data.localization import tr

class BaseModal:
    def __init__(self, surface, modal, assets, title, w=None, h=None):
        self.surface = surface
        self.modal = modal
        self.assets = assets
        
        # --- THE FIX: Instantly translate any title passed to any modal ---
        self.title = tr('modal', title) 
        
        self.modal_w, self.modal_h = self.get_modal_dimensions()
        self.modal_x, self.modal_y = modal['position']
        self.header_h = 35
        self.minimized = modal.get('minimized', False)
        self.is_active = modal.get('is_active', False)
        self.modal_rect = pygame.Rect(self.modal_x, self.modal_y, self.modal_w, self.header_h if self.minimized else self.modal_h)
        self.close_button_rect = self.assets['close_button'].get_rect(topright=(self.modal_x + self.modal_w - 10, self.modal_y + 10))
        self.minimize_button_rect = self.assets['minimize_button'].get_rect(topright=(self.close_button_rect.left - 10, self.modal_y + 10))

    def get_modal_dimensions(self):
        if self.modal['type'] == 'inventory':
            return INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT
        elif self.modal['type'] == 'status':
            return STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT
        elif self.modal['type'] == 'container':
            return CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT
        elif self.modal['type'] == 'nearby':
            return NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT
        elif self.modal['type'] == 'messages':
            return MESSAGES_MODAL_WIDTH, MESSAGES_MODAL_HEIGHT
        elif self.modal['type'] == 'text':
            return TEXT_MODAL_WIDTH, TEXT_MODAL_HEIGHT
        elif self.modal['type'] == 'gear':
            return GEAR_MODAL_WIDTH, GEAR_MODAL_HEIGHT
        elif self.modal['type'] == 'mobile':
            return MOBILE_MODAL_WIDTH, MOBILE_MODAL_HEIGHT
        elif self.modal['type'] == 'vehicle':
            return VEHICLE_MODAL_WIDTH, VEHICLE_MODAL_HEIGHT
        elif self.modal['type'] == 'crafting':
            return CRAFTING_MODAL_WIDTH, CRAFTING_MODAL_HEIGHT
        elif self.modal['type'] == 'big_map':
            return MAP_MODAL_WIDTH, MAP_MODAL_HEIGHT
        elif self.modal['type'] == 'help':
            return HELP_MODAL_WIDTH, HELP_MODAL_HEIGHT
        elif self.modal['type'] == 'npc_dialog':
            return NPC_DIALOG_MODAL_WIDTH, NPC_DIALOG_MODAL_HEIGHT
        return 300, 300

    def draw_header(self):
        header_rect = pygame.Rect(self.modal_x, self.modal_y, self.modal_w, self.header_h)

        header_color = GRAY if self.is_active else GRAY_60 
        border_color = WHITE if self.is_active else GRAY     
        
        pygame.draw.rect(self.surface, header_color, header_rect, 0, border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.rect(self.surface, border_color, header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)
        
        title_text = font.render(self.title, True, WHITE)

        self.surface.blit(title_text, (self.modal_x + 10, self.modal_y + 10))
        self.surface.blit(self.assets['close_button'], self.close_button_rect)
        self.surface.blit(self.assets['minimize_button'], self.minimize_button_rect)

    def draw_base(self):
        height = self.header_h if self.minimized else self.modal_h
        s = pygame.Surface((self.modal_w, height), pygame.SRCALPHA)
        s.fill((20, 20, 20, 250))
        self.surface.blit(s, (self.modal_x, self.modal_y))

        border_color = WHITE if self.is_active else GRAY
        pygame.draw.rect(self.surface, border_color, self.modal_rect, 1, 4)

        self.draw_header()

    def get_buttons(self):
        return {'id': self.modal['id'], 'type': 'close', 'rect': self.close_button_rect}, \
               {'id': self.modal['id'], 'type': 'minimize', 'rect': self.minimize_button_rect}