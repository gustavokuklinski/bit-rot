import pygame
import os
import math
from core.data.config import SPRITE_PATH, TILE_SIZE, RED, DARK_GRAY, GREEN
from core.entities.item.item import Item
from core.entities.item.item_data import ITEM_TEMPLATES
from core.systems.mod_manager import mod_manager

class ZombieGraphics:
    def load_sprite(self, sprite_file):
        """Robustly loads a sprite, checking multiple paths."""
        
        if not sprite_file: return None

        candidates = [
            mod_manager.get_override_path(os.path.join(SPRITE_PATH, "zombie", sprite_file)),
            mod_manager.get_override_path(os.path.join(SPRITE_PATH, sprite_file)),
            mod_manager.get_override_path(os.path.join(SPRITE_PATH, "player", sprite_file)),
            mod_manager.get_override_path(os.path.join(SPRITE_PATH, "animals", sprite_file))
        ]

        for path in candidates:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                except Exception as e:
                    print(f"Error loading sprite at {path}: {e}")

        print(f"Warning: Could not find sprite '{sprite_file}' in common paths.")
        return None

    def load_clothe_sprite(self, sprite_file):
        from core.systems.mod_manager import mod_manager
        if not sprite_file: return None
        try:
            path = mod_manager.get_override_path(os.path.join(SPRITE_PATH, "clothes", sprite_file))
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
            return None
        except Exception as e:
            print(f"Error loading clothe sprite {sprite_file}: {e}")
            return None

    def _get_composite_image(self, direction='center'):
        """Bakes base body and clothes into a single cached surface per direction."""
        if not hasattr(self, '_composite_cache'):
            self._composite_cache = {}

        if direction in self._composite_cache:
            return self._composite_cache[direction]

        base_img = self.images.get(direction) or self.images.get('center')
        if not base_img:
            return None

        composite = base_img.copy()

        if getattr(self, 'clothes', None):
            hidden_slots = set()
            for slot, clothe in self.clothes.items():
                if clothe:
                    item_name = clothe.name if isinstance(clothe, Item) else (
                        clothe.get('name') if isinstance(clothe, dict) else (clothe if isinstance(clothe, str) else None)
                    )
                    if item_name:
                        template = ITEM_TEMPLATES.get(item_name)
                        if template and 'properties' in template and 'hide_cloth' in template['properties']:
                            hidden_slots.update(template['properties']['hide_cloth'])

            for slot, clothe in self.clothes.items():
                if slot in hidden_slots or not clothe:
                    continue

                clothe_sprite = None
                if isinstance(clothe, Item) and getattr(clothe, 'image', None):
                    clothe_sprite = clothe.image
                elif isinstance(clothe, dict):
                    clothe_sprite = self.load_clothe_sprite(clothe.get('sprite'))

                if clothe_sprite:
                    composite.blit(clothe_sprite, (0, 0))

        self._composite_cache[direction] = composite
        return composite

    def draw(self, surface, offset_x, offset_y, opacity=255):
        wiggle_y = 0
        draw_angle = getattr(self, 'walk_anim_angle', 0)

        if draw_angle != 0:
            phase_shift = id(self) % 1000
            current_time = pygame.time.get_ticks()
            wiggle_y = int(math.sin(current_time * 0.015 + phase_shift) * 2)
            draw_angle = int(draw_angle + math.sin(current_time * 0.01 + phase_shift) * 5)

        self._current_wiggle_y = wiggle_y
        draw_rect = self.rect.move(offset_x, offset_y + wiggle_y)

        # Retrieve cached composite image for facing direction
        current_image = None
        if self.vx < -0.1: 
            current_image = self._get_composite_image('left')
        elif self.vx > 0.1: 
            current_image = self._get_composite_image('right')

        if current_image is None:
            current_image = self._get_composite_image('center')

        if current_image:
            # Skip copy/fill operations if fully opaque
            if opacity < 150:
                temp_image = current_image.copy()
                temp_image.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            elif opacity < 255:
                temp_image = current_image.copy()
                temp_image.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
            else:
                temp_image = current_image

            if draw_angle != 0:
                rotated_img = pygame.transform.rotate(temp_image, draw_angle)
                rot_rect = rotated_img.get_rect(center=draw_rect.center)
                surface.blit(rotated_img, rot_rect)
            else:
                surface.blit(temp_image, draw_rect)
        else:
            temp_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            if opacity < 150:
                temp_surface.fill((0, 0, 0, 255))
            else:
                temp_surface.fill((self.color[0], self.color[1], self.color[2], opacity))

            if draw_angle != 0:
                rotated_surf = pygame.transform.rotate(temp_surface, draw_angle)
                rot_rect = rotated_surf.get_rect(center=draw_rect.center)
                surface.blit(rotated_surf, rot_rect)
            else:
                surface.blit(temp_surface, draw_rect)

        if self.show_health_bar_timer > 0:
            bar_y = draw_rect.top - 7
            bg_bar_rect = pygame.Rect(draw_rect.left, bar_y, TILE_SIZE, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)

            health_percentage = max(0, self.health / self.max_health)
            health_bar_width = int(health_percentage * TILE_SIZE)
            health_bar_rect = pygame.Rect(draw_rect.left, bar_y, health_bar_width, 5)
            pygame.draw.rect(surface, GREEN, health_bar_rect)
            self.show_health_bar_timer -= 1

        if self.melee_swing_timer > 0:
            self.melee_swing_timer -= 1