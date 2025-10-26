import pygame
from data.config import *

class BaseModal:
    def __init__(self, surface, modal, assets, title):
        self.surface = surface
        self.modal = modal
        self.assets = assets
        self.title = title
        self.modal_w, self.modal_h = self.get_modal_dimensions()
        self.modal_x, self.modal_y = modal['position']
        self.header_h = 35
        self.minimized = modal.get('minimized', False)
        self.modal_rect = pygame.Rect(self.modal_x, self.modal_y, self.modal_w, self.header_h if self.minimized else self.modal_h)
        self.close_button_rect = self.assets['close_button'].get_rect(topright=(self.modal_x + self.modal_w - 10, self.modal_y + 10))
        self.minimize_button_rect = self.assets['minimize_button'].get_rect(topright=(self.close_button_rect.left - 10, self.modal_y + 10))

    def get_modal_dimensions(self):
        if self.modal['type'] == 'inventory':
            return INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT
        elif self.modal['type'] == 'status':
            return STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT
        elif self.modal['type'] == 'container':
            return 300, 300
        return 300, 300

    def draw_header(self):
        header_rect = pygame.Rect(self.modal_x, self.modal_y, self.modal_w, self.header_h)
        pygame.draw.rect(self.surface, GRAY_60, header_rect, 0, border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.rect(self.surface, WHITE, header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)
        title_text = font.render(self.title, True, WHITE)
        self.surface.blit(title_text, (self.modal_x + 10, self.modal_y + 10))
        self.surface.blit(self.assets['close_button'], self.close_button_rect)
        self.surface.blit(self.assets['minimize_button'], self.minimize_button_rect)

    def draw_base(self):
        height = self.header_h if self.minimized else self.modal_h
        s = pygame.Surface((self.modal_w, height), pygame.SRCALPHA)
        s.fill((20, 20, 20, 230))
        self.surface.blit(s, (self.modal_x, self.modal_y))
        pygame.draw.rect(self.surface, WHITE, self.modal_rect, 1, 4)
        self.draw_header()

    def get_buttons(self):
        return {'id': self.modal['id'], 'type': 'close', 'rect': self.close_button_rect}, \
               {'id': self.modal['id'], 'type': 'minimize', 'rect': self.minimize_button_rect}