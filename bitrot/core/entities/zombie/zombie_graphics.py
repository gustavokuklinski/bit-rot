import pygame
import os
import math  # NEW: Required for the wiggle math
from core.data.config import SPRITE_PATH, TILE_SIZE, RED, DARK_GRAY, GREEN
from core.entities.item.item import Item
from core.entities.item.item_data import ITEM_TEMPLATES

class ZombieGraphics:
    def load_sprite(self, sprite_file):
        """Robustly loads a sprite, checking multiple paths."""
        if not sprite_file: return None

        # Paths to check: 1. zombie/folder, 2. root sprite folder, 3. player folder, 4. animals folder
        candidates = [
            os.path.join(SPRITE_PATH, "zombie", sprite_file),
            os.path.join(SPRITE_PATH, sprite_file),
            os.path.join(SPRITE_PATH, "player", sprite_file),
            os.path.join(SPRITE_PATH, "animals", sprite_file)
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
        if not sprite_file: return None
        try:
            path = os.path.join(SPRITE_PATH, "clothes", sprite_file)
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
            return None
        except Exception as e:
            print(f"Error loading clothe sprite {sprite_file}: {e}")
            return None

    def draw(self, surface, offset_x, offset_y, opacity=255):
        # --- NEW: Desynchronized Positional and Rotational Wiggle ---
        wiggle_y = 0
        draw_angle = getattr(self, 'walk_anim_angle', 0)

        if draw_angle != 0:
            # Use object memory address as a unique phase offset for each entity
            phase_shift = id(self) % 1000
            current_time = pygame.time.get_ticks()
            
            # Vertical positional bounce
            wiggle_y = int(math.sin(current_time * 0.015 + phase_shift) * 2)
            # Add rotation desynchronization
            draw_angle += math.sin(current_time * 0.01 + phase_shift) * 5

        # Save this frame's wiggle so child classes (NPCs) can sync their weapons to it
        self._current_wiggle_y = wiggle_y
        
        # Apply the wiggle to the base drawing rect
        draw_rect = self.rect.move(offset_x, offset_y + wiggle_y)

        current_image = None
        if self.vx < -0.1: 
            current_image = self.images.get('left')
        elif self.vx > 0.1: 
            current_image = self.images.get('right')

        if current_image is None:
            current_image = self.images.get('center')

        if current_image:
            temp_image = current_image.copy()
            
            if opacity < 150:
                temp_image.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            else:
                temp_image.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
            
            if draw_angle != 0:
                rotated_img = pygame.transform.rotate(temp_image, draw_angle)
                rot_rect = rotated_img.get_rect(center=draw_rect.center)
                surface.blit(rotated_img, rot_rect)
            else:
                surface.blit(temp_image, draw_rect)

            if opacity >= 150:
                hidden_slots = set()
                for slot, clothe in self.clothes.items():
                    if clothe:
                        item_name = None
                        if isinstance(clothe, Item):
                            item_name = clothe.name
                        elif isinstance(clothe, dict):
                            item_name = clothe.get('name')
                        elif isinstance(clothe, str):
                            item_name = clothe
                        
                        if item_name:
                            template = ITEM_TEMPLATES.get(item_name)
                            if template and 'properties' in template and 'hide_cloth' in template['properties']:
                                hidden_slots.update(template['properties']['hide_cloth'])

                for slot, clothe in self.clothes.items():
                    if slot in hidden_slots:
                        continue
                    
                    if clothe:
                        clothe_sprite = None
                        if isinstance(clothe, Item):
                            if clothe.image:
                                clothe_sprite = clothe.image.copy()
                        elif isinstance(clothe, dict):
                            clothe_sprite = self.load_clothe_sprite(clothe.get('sprite'))

                        if clothe_sprite:
                            clothe_sprite.fill((255, 255, 255, opacity), special_flags=pygame.BLEND_RGBA_MULT)
                            if draw_angle != 0:
                                rotated_cloth = pygame.transform.rotate(clothe_sprite, draw_angle)
                                rot_cloth_rect = rotated_cloth.get_rect(center=draw_rect.center)
                                surface.blit(rotated_cloth, rot_cloth_rect)
                            else:
                                surface.blit(clothe_sprite, draw_rect)
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
            swing_radius = TILE_SIZE * 0.9
            center_x, center_y = draw_rect.center
            start_angle = self.melee_swing_angle - (3.1415 / 4)
            end_angle = self.melee_swing_angle + (3.1415 / 4)
            arc_bounds = pygame.Rect(center_x - swing_radius, center_y - swing_radius, swing_radius * 2, swing_radius * 2)
            pygame.draw.arc(surface, RED, arc_bounds, start_angle, end_angle, 1)
            self.melee_swing_timer -= 1