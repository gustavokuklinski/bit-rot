import pygame
import os
from data.config import TILE_SIZE, DARK_GRAY
from core.entities.item import Item

class Corpse(Item):
    """Lootable corpse container with automatic decay."""

    def __init__(self, name="Dead corpse", capacity=15, image_path=None, pos=(0, 0), decay_ms=160000):
        super().__init__(name, 'container', capacity=capacity, sprite_file=image_path)
        self.rect.center = pos
        self.spawn_time = pygame.time.get_ticks()
        self.decay_ms = decay_ms
        self.color = DARK_GRAY

    def is_expired(self, now_ms=None):
        """Return True if corpse lifetime exceeded decay_ms."""
        if now_ms is None:
            now_ms = pygame.time.get_ticks()
        return (now_ms - self.spawn_time) > self.decay_ms

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
