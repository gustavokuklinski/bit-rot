# core/entities/zombie/corpse.py

import pygame
import os
from core.data.config import TILE_SIZE, DARK_GRAY, YELLOW
from core.entities.item.item import Item

PLAYER_CORPSE_DECAY_MS = 30 * 60 * 1000  # 30 minutes in milliseconds (1,800,000 ms)

class Corpse(Item):
    """Lootable corpse container with automatic decay."""

    def __init__(self, name="Dead corpse", capacity=15, image_path=None, pos=(0, 0), decay_ms=160000, is_permanent=False, is_player_corpse=False):
        img_path = image_path or "zombie/dead.png"
        super().__init__(name, 'container', capacity=capacity, sprite_file=img_path)
        
        self.image_path = img_path
        self.rect.center = pos
        self.x = self.rect.x
        self.y = self.rect.y
        
        self.spawn_time = pygame.time.get_ticks()
        self.decay_ms = decay_ms
        self.is_permanent = is_permanent
        self.is_player_corpse = is_player_corpse

        # Dead player corpse is full size (16x16) and yellow; zombie corpses stay small (8x8)
        if self.is_player_corpse:
            self.is_placed = True
            self.color = YELLOW
            self.apply_yellow_tint()
        else:
            self.is_placed = False
            self.color = DARK_GRAY

    def apply_yellow_tint(self):
        """Tints the corpse sprite yellow (255, 255, 0)."""
        if self.image:
            tinted = self.image.copy()
            tinted.fill((255, 255, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.image = tinted
        else:
            surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            surf.fill((255, 255, 0, 255))
            self.image = surf

    def to_dict(self):
        """Serialize corpse data, preserving remaining decay time, player corpse flag, and color."""
        data = super().to_dict()
        data['image_path'] = self.image_path
        data['is_corpse'] = True
        data['is_permanent'] = getattr(self, 'is_permanent', False)
        data['is_player_corpse'] = getattr(self, 'is_player_corpse', False)
        data['is_placed'] = getattr(self, 'is_placed', False)
        data['decay_ms'] = getattr(self, 'decay_ms', None)

        # Track remaining lifetime so reloading doesn't reset or prematurely delete the corpse
        now_ms = pygame.time.get_ticks()
        elapsed = now_ms - getattr(self, 'spawn_time', now_ms)
        if self.decay_ms is not None:
            data['remaining_decay_ms'] = max(1000, self.decay_ms - elapsed)

        if hasattr(self, 'color'):
            data['color'] = self.color
        return data

    def is_expired(self, now_ms=None):
        """Return True if corpse lifetime exceeded decay_ms."""
        if getattr(self, 'is_permanent', False) or self.decay_ms is None or self.decay_ms == float('inf'):
            return False
        if now_ms is None:
            now_ms = pygame.time.get_ticks()
        return (now_ms - self.spawn_time) > self.decay_ms

    def spill_contents_to_ground(self, items_on_ground, drop_pos=None):
        if drop_pos is None:
            drop_x, drop_y = self.rect.center
        else:
            drop_x, drop_y = drop_pos
        for it in list(self.inventory):
            try:
                it.rect.center = (drop_x + 4, drop_y + 4)
                it.x = it.rect.x
                it.y = it.rect.y
            except Exception:
                pass
            items_on_ground.append(it)
        self.inventory.clear()