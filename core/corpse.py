import pygame
import os
from config import TILE_SIZE, DARK_GRAY

class Corpse:
    """Lootable corpse container with automatic decay."""

    def __init__(self, name="Dead corpse", capacity=8, image_path=None, pos=(0, 0), decay_ms=160000):
        self.name = name
        self.capacity = capacity
        self.inventory = []
        self.image = None
        if image_path:
            try:
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (TILE_SIZE, TILE_SIZE))
            except Exception:
                self.image = None
        self.rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        self.rect.center = pos
        self.spawn_time = pygame.time.get_ticks()
        self.decay_ms = decay_ms
        self.color = DARK_GRAY

    def is_expired(self, now_ms=None):
        """Return True if corpse lifetime exceeded decay_ms."""
        if now_ms is None:
            now_ms = pygame.time.get_ticks()
        return (now_ms - self.spawn_time) > self.decay_ms

    def draw(self, surface, game_offset_x=0):
        """Draw corpse on provided surface (accounts for game offset)."""
        draw_rect = self.rect.move(game_offset_x, 0)
        if self.image:
            surface.blit(self.image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)

    def spill_contents_to_ground(self, items_on_ground, drop_pos=None):
        """Move contained items from this corpse to world items_on_ground.
        If drop_pos provided, place items near that position; otherwise use corpse center.
        """
        if drop_pos is None:
            drop_x, drop_y = self.rect.center
        else:
            drop_x, drop_y = drop_pos
        for it in list(self.inventory):
            try:
                it.rect.center = (drop_x + 4, drop_y + 4)
            except Exception:
                pass
            items_on_ground.append(it)
        self.inventory.clear()