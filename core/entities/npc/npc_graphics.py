import os
import pygame
import math
from core.data.config import SPRITE_PATH, TILE_SIZE

class NPCGraphics:
    _base_cache = {} 

    def load_sprite(self, sprite_file):
        if not sprite_file: return None
        candidates = [
            os.path.join(SPRITE_PATH, "player", sprite_file),
            os.path.join(SPRITE_PATH, sprite_file),
            os.path.join(SPRITE_PATH, "zombie", sprite_file)
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                except Exception as e:
                    print(f"Error loading NPC sprite at {path}: {e}")
        return None

    def _load_base_sprite(self):
        candidates = ["player/base.png", "player/player.png", "player/idle.png", "zombie/zombie.png"]
        found_img = None
        for filename in candidates:
            if filename in NPCGraphics._base_cache:
                found_img = NPCGraphics._base_cache[filename]; break
            full_path_A = os.path.join(SPRITE_PATH, *filename.split('/'))
            full_path_B = os.path.join(SPRITE_PATH, filename)
            if os.path.exists(full_path_A):
                try:
                    img = pygame.image.load(full_path_A).convert_alpha()
                    found_img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                    NPCGraphics._base_cache[filename] = found_img
                    break
                except: pass
            elif os.path.exists(full_path_B):
                 try:
                    img = pygame.image.load(full_path_B).convert_alpha()
                    found_img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                    NPCGraphics._base_cache[filename] = found_img
                    break
                 except: pass
        if found_img:
            self.images['center'] = found_img
            self.images['left'] = found_img
            self.images['right'] = found_img
            self.image = found_img
        else:
             print("NPC Error: No valid sprite found! Rendering as Red Square.")

    def draw(self, surface, offset_x, offset_y, opacity=255):
        if self.is_dead and self.dead_image:
            draw_rect = self.rect.move(offset_x, offset_y)
            surface.blit(self.dead_image, draw_rect)
            return

        super().draw(surface, offset_x, offset_y, opacity)

        max_h = self.template.get('max_health', 100) if hasattr(self, 'template') else 100
        
        if self.health < max_h and self.health_bar_timer > 0:
            bar_width = TILE_SIZE
            bar_height = 4
            
            bar_x = self.rect.x + offset_x
            bar_y = self.rect.y + offset_y - 8 
            
            pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))
            
            health_ratio = max(0, self.health / max_h)
            current_width = int(bar_width * health_ratio)
            pygame.draw.rect(surface, (0, 255, 0), (bar_x, bar_y, current_width, bar_height))

        weapon = self.equipped_weapon
        if weapon and weapon.image:
            angle_rad = math.radians(self.angle)
            angle_deg = -self.angle

            if weapon.item_type == 'weapon_melee' and self.melee_swing_timer > 0:
                SWING_DURATION = 15
                swing_progress = (SWING_DURATION - self.melee_swing_timer) / SWING_DURATION
                base_angle_rad = self.melee_swing_angle
                SWING_ARC_RADIANS = math.pi / 2
                swing_offset = (swing_progress * SWING_ARC_RADIANS) - (SWING_ARC_RADIANS / 2) 
                current_weapon_angle_rad = base_angle_rad + swing_offset 
                weapon_distance_from_center = TILE_SIZE * 0.7 
                weapon_center_x = self.rect.centerx + math.cos(current_weapon_angle_rad) * weapon_distance_from_center
                weapon_center_y = self.rect.centery - math.sin(current_weapon_angle_rad) * weapon_distance_from_center
                angle_deg = -math.degrees(current_weapon_angle_rad)
            else:
                hand_offset_dist = TILE_SIZE * 0.4
                angle_rad = math.radians(self.angle)
                weapon_center_x = self.rect.centerx + math.cos(angle_rad) * hand_offset_dist
                weapon_center_y = self.rect.centery - math.sin(angle_rad) * hand_offset_dist
                angle_deg = -self.angle

            rotated_image = pygame.transform.rotate(weapon.image, angle_deg)
            new_rect = rotated_image.get_rect(center=(weapon_center_x + offset_x, weapon_center_y + offset_y))
            surface.blit(rotated_image, new_rect.topleft)