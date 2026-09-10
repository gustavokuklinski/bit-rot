import pygame
import math
import random
from core.data.config import TILE_SIZE, WHITE
from core.entities.zombie.zombie import Zombie
from core.entities.npc.npc import NPC
from core.entities.animal.animal import Animal

def draw_entities(game, surface, offset_x, offset_y, view_w, view_h, screen_rect, zoom):
    view_radius_sq = (game.player_view_radius + TILE_SIZE) ** 2

    for container in game.visible_containers:
        if not screen_rect.colliderect(container.rect): continue
        dx = container.rect.centerx - game.player.rect.centerx
        dy = container.rect.centery - game.player.rect.centery
        if (dx*dx + dy*dy) > view_radius_sq: continue
        draw_pos = container.rect.move(offset_x, offset_y)
        if getattr(container, 'image', None): surface.blit(container.image, draw_pos)
        else: pygame.draw.rect(surface, getattr(container, 'color', WHITE), draw_pos)

    for item in game.visible_items:
        if isinstance(item, Animal): continue
        if not screen_rect.colliderect(item.rect): continue
        dx = item.rect.centerx - game.player.rect.centerx
        dy = item.rect.centery - game.player.rect.centery
        if (dx*dx + dy*dy) > view_radius_sq: continue

        draw_pos = item.rect.move(offset_x, offset_y)
        # [FIX] Render Placed items full-size, otherwise downscale 8x8 Drops
        if getattr(item, 'is_placed', False):
            if getattr(item, 'image', None): surface.blit(item.image, draw_pos)
            else: pygame.draw.rect(surface, getattr(item, 'color', WHITE), draw_pos)
        else:
            if getattr(item, 'image', None):
                if not hasattr(item, 'ground_image_8x8'): item.ground_image_8x8 = pygame.transform.scale(item.image, (8, 8))
                surface.blit(item.ground_image_8x8, (draw_pos.x + (draw_pos.width // 2) - 4, draw_pos.y + (draw_pos.height // 2) - 4))
            else:
                pygame.draw.rect(surface, getattr(item, 'color', WHITE), (draw_pos.x + (draw_pos.width // 2) - 4, draw_pos.y + (draw_pos.height // 2) - 4, 8, 8))

    for p in game.projectiles:
        if screen_rect.colliderect(p.rect): p.draw(surface, offset_x, offset_y)

    visible_entities = game.quadtree.query(screen_rect.inflate(100, 100))
    current_time = pygame.time.get_ticks()

    if not hasattr(game, 'screen_obstacles') or game.frame_count % 15 == 0:
        game.screen_obstacles = [ob for ob in game.obstacles if screen_rect.inflate(200, 200).colliderect(ob)]
    
    for entity in visible_entities:
        if isinstance(entity, (Zombie, NPC, Animal)):
            if getattr(entity, 'is_dead', False): continue

            dx = entity.rect.centerx - game.player.rect.centerx
            dy = entity.rect.centery - game.player.rect.centery
            dist_sq = dx*dx + dy*dy
            dist = math.sqrt(dist_sq)

            in_vision = True
            if dist_sq > view_radius_sq: in_vision = False
            else:
                peripheral_radius_world = min(game.player_view_radius * 0.35, 100)
                if dist > peripheral_radius_world:
                    aim_angle = getattr(game.player, 'aim_angle', 0)
                    angle_to_entity = math.atan2(-dy, dx)
                    angle_diff = (angle_to_entity - aim_angle + math.pi) % (2 * math.pi) - math.pi
                    fov = math.radians(min(160, 50 + (game.player_view_radius * 0.1)) + 10)
                    if abs(angle_diff) > fov / 2: in_vision = False

            if not hasattr(entity, 'last_los_draw_check'):
                entity.last_los_draw_check = random.randint(0, 500) 
                entity.cached_los_draw_result = True
            
            if in_vision and (current_time - entity.last_los_draw_check > 500):
                entity.last_los_draw_check = current_time
                entity.cached_los_draw_result = game.player.has_line_of_sight(entity.rect, game.screen_obstacles, game)

            target_opacity = 255 if (in_vision and entity.cached_los_draw_result) else (80 if in_vision else 0)
            current_opacity = getattr(entity, 'render_opacity', 0.0)
            
            fade_in_speed = 6.0 * getattr(game, 'dt_mult', 1.0)
            fade_out_speed = 10.0 * getattr(game, 'dt_mult', 1.0)
            
            if current_opacity < target_opacity: current_opacity = min(float(target_opacity), current_opacity + fade_in_speed)
            elif current_opacity > target_opacity: current_opacity = max(float(target_opacity), current_opacity - fade_out_speed)
            entity.render_opacity = current_opacity

            if current_opacity > 0 and screen_rect.colliderect(entity.rect):
                entity.draw(surface, offset_x, offset_y, int(current_opacity))

    game.player.draw_highlight_stairs(surface, game, offset_x, offset_y)
    game.player.draw(surface, offset_x, offset_y, getattr(game.player, 'is_aiming', False))