import pygame
import math
from core.data.config import WHITE, TILE_SIZE

class Projectile:
    """Represents a bullet fired by the player."""
    def __init__(self, start_x, start_y, target_x, target_y, speed=10, color=WHITE, max_distance=None, damage=1, game=None):
        self.start_x = start_x 
        self.start_y = start_y 
        self.x = start_x
        self.y = start_y
        self.rect = pygame.Rect(start_x, start_y, 1, 2)
        self.color = color
        self.speed = speed
        self.max_distance = max_distance 
        self.damage = damage
        self.game = game
        
        dx = target_x - start_x
        dy = target_y - start_y
        dist = (dx*dx + dy*dy) ** 0.5
        if dist > 0:
            self.vx = (dx / dist) * self.speed
            self.vy = (dy / dist) * self.speed
        else:
            self.vx = self.vy = 0

    def update(self, world_min_x=0, world_min_y=0, world_max_x=None, world_max_y=None):
        if world_max_x is None or world_max_y is None:
            print("Error: Projectile.update() called without game_width/game_height.")
            return True 

        self.x += self.vx
        self.y += self.vy
        self.rect.topleft = (int(self.x), int(self.y))

        # Check tile collision
        if self.game and hasattr(self.game, 'map_manager'):
            grid_x = int(self.x // TILE_SIZE)
            grid_y = int(self.y // TILE_SIZE)
            tile_def = self.game.map_manager.get_tile_at(grid_x, grid_y)
            
            if tile_def:
                # If bullet hits a destructible obstacle (tree/stone), hit it and destroy bullet
                if tile_def.get('destructible') and tile_def.get('is_obstacle'):
                    self.game.map_manager.hit_tile(grid_x, grid_y, self.damage, weapon=None, is_projectile=True)
                    return True
                # If bullet hits an indestructible wall, destroy bullet
                elif tile_def.get('is_obstacle'):
                    return True

        if self.max_distance is not None:
            dist_traveled = math.hypot(self.x - self.start_x, self.y - self.start_y)
            if dist_traveled >= self.max_distance:
                return True 

        if self.x < world_min_x or self.x > world_max_x or self.y < world_min_y or self.y > world_max_y:
            return True
        return False

    def draw(self, surface, offset_x=0, offset_y=0):
        draw_center = (int(self.x) + offset_x, int(self.y) + offset_y)
        pygame.draw.circle(surface, self.color, draw_center, 1)