import pygame
import math
import random
from core.data.config import TILE_SIZE, SPRITE_PATH, DARK_GRAY, YELLOW

class PlayerGraphics:
    def _load_sprite(self, sprite_path):
        if not sprite_path: return None
        try:
            path = SPRITE_PATH + "player/" + sprite_path
            image = pygame.image.load(path).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
            return image
        except pygame.error as e:
            print(f"Warning: Could not load player sprite '{sprite_path}': {e}")
            return None

    def update_aim(self, is_moving):
        if not self.is_aiming:
            self.current_aim_factor = 1.0
            return

        ranged_level = self.progression.get_ranged(self)
        shrink_speed = 0.01 + (ranged_level * 0.002)

        if is_moving:
            self.current_aim_factor = min(1.0, self.current_aim_factor + 0.05)
        else:
            self.current_aim_factor = max(0.0, self.current_aim_factor - shrink_speed)

    def draw(self, surface, offset_x, offset_y, is_aiming=False):
        if self.vehicle:
            veh_draw_pos = (self.vehicle.x + offset_x, self.vehicle.y + offset_y)
            surface.blit(self.vehicle.image, veh_draw_pos)
            return

        draw_rect = self.rect.move(offset_x, offset_y)

        current_image = None
        if self.facing_direction[0] < 0: 
            current_image = self.images.get('left')
        elif self.facing_direction[0] > 0: 
            current_image = self.images.get('right')
        
        if current_image is None:
            current_image = self.images.get('center')

        if current_image:
            if self.walk_anim_angle != 0:
                rotated_img = pygame.transform.rotate(current_image, self.walk_anim_angle)
                rot_rect = rotated_img.get_rect(center=draw_rect.center)
                surface.blit(rotated_img, rot_rect)
            else:
                surface.blit(current_image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)

        for slot in self.clothes_slots: 
            item = self.clothes.get(slot)
            if item and item.image:
                if self.walk_anim_angle != 0:
                    rotated_cloth = pygame.transform.rotate(item.image, self.walk_anim_angle)
                    rot_cloth_rect = rotated_cloth.get_rect(center=draw_rect.center)
                    surface.blit(rotated_cloth, rot_cloth_rect)
                else:
                    surface.blit(item.image, draw_rect)

        if self.active_weapon and self.active_weapon.image:
            is_swinging = (self.melee_swing_timer > 0)
            is_ranged_aiming = (is_aiming and self.active_weapon.item_type == 'weapon_ranged')
            
            if not is_swinging and not is_ranged_aiming:
                weapon_img = self.active_weapon.image
                angle_degrees = math.degrees(self.aim_angle)
                
                if math.cos(self.aim_angle) < 0:
                    weapon_img = pygame.transform.flip(weapon_img, False, True)
                
                rotated_image = pygame.transform.rotate(weapon_img, angle_degrees)
                offset_dist = TILE_SIZE * 0.4
                offset_x = math.cos(self.aim_angle) * offset_dist
                offset_y = -math.sin(self.aim_angle) * offset_dist
                
                rotated_rect = rotated_image.get_rect(center=draw_rect.center)
                rotated_rect.centerx += offset_x
                rotated_rect.centery += offset_y
                
                surface.blit(rotated_image, rotated_rect)

        if is_aiming and self.active_weapon and self.active_weapon.image and \
           self.active_weapon.item_type == 'weapon_ranged':
            
            weapon_img = self.active_weapon.image
            angle_degrees = math.degrees(self.aim_angle)

            if math.cos(self.aim_angle) < 0:
                weapon_img = pygame.transform.flip(weapon_img, False, True)

            rotated_image = pygame.transform.rotate(weapon_img, angle_degrees)
            offset_dist = TILE_SIZE * 0.8 
            offset_x = math.cos(self.aim_angle) * offset_dist
            offset_y = -math.sin(self.aim_angle) * offset_dist 
            
            rotated_rect = rotated_image.get_rect(center=draw_rect.center)
            rotated_rect.centerx += offset_x
            rotated_rect.centery += offset_y

            surface.blit(rotated_image, rotated_rect)

        if self.is_sleeping:
            if self.max_tireness < 0:
                progress = 1.0 - max(0.0, min(1.0, self.tireness / self.max_tireness))
            else:
                progress = 0.0
            
            bar_total_width = TILE_SIZE * 2
            bar_x = draw_rect.centerx - (bar_total_width / 2)
            bar_y = draw_rect.top - 20 
            
            bg_bar_rect = pygame.Rect(bar_x, bar_y, bar_total_width, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)
            
            bar_progress_width = int(bar_total_width * progress)
            bar_rect = pygame.Rect(bar_x, bar_y, bar_progress_width, 5)
            pygame.draw.rect(surface, (100, 150, 255), bar_rect)

        if self.action_timer > 0 and self.action_total_time > 0:
            progress = 1.0 - (self.action_timer / self.action_total_time)
            
            bar_total_width = TILE_SIZE * 2
            bar_x = draw_rect.centerx - (bar_total_width / 2)
            bar_y = draw_rect.top - 15 
            
            bg_bar_rect = pygame.Rect(bar_x, bar_y, bar_total_width, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)
            
            bar_progress_width = int(bar_total_width * progress)
            bar_rect = pygame.Rect(bar_x, bar_y, bar_progress_width, 5)
            pygame.draw.rect(surface, (50, 200, 50), bar_rect)

        if self.melee_swing_timer > 0:
            if self.active_weapon and self.active_weapon.image and \
               self.active_weapon.item_type in ['weapon_melee', 'tool']:
                
                original_image = self.active_weapon.image
                angle_degrees = math.degrees(self.melee_swing_angle)
                rotated_image = pygame.transform.rotate(original_image, angle_degrees) 
                rotated_rect = rotated_image.get_rect(center=draw_rect.center)
                
                offset_radius = TILE_SIZE * 0.8 
                offset_x_weapon = math.cos(self.melee_swing_angle) * offset_radius
                offset_y_weapon = -math.sin(self.melee_swing_angle) * offset_radius
                
                rotated_rect.centerx += offset_x_weapon
                rotated_rect.centery += offset_y_weapon
                
                surface.blit(rotated_image, rotated_rect)

            swing_radius = TILE_SIZE * 0.7
            center_x, center_y = draw_rect.center
            start_angle = self.melee_swing_angle - (3.1415 / 4)
            end_angle = self.melee_swing_angle + (3.1415 / 4)
            arc_surf = pygame.Surface((swing_radius * 2, swing_radius * 2), pygame.SRCALPHA)
            
            arc_rect = arc_surf.get_rect()
            pygame.draw.arc(arc_surf, (0, 0, 0, 80), arc_rect, start_angle, end_angle, 2)
            surface.blit(arc_surf, (center_x - swing_radius, center_y - swing_radius))
            
            self.melee_swing_timer -= 1

        if self.is_reloading:
            progress = 1.0 - (self.reload_timer / self.reload_duration)
            bar_total_width = TILE_SIZE * 2
            bar_x = draw_rect.centerx - (bar_total_width / 2)
            bar_y = draw_rect.top - 10
            
            bg_bar_rect = pygame.Rect(bar_x, bar_y, bar_total_width, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)
            
            bar_progress_width = int(bar_total_width * progress)
            bar_rect = pygame.Rect(bar_x, bar_y, bar_progress_width, 5)
            pygame.draw.rect(surface, YELLOW, bar_rect)