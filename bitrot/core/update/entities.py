# In core/update/entities.py

import pygame
import math
from core.data.config import TILE_SIZE, CHUNK_SIZE
import core.data.config
from core.entities.zombie.zombie import Zombie
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Item
from core.update.utils import get_nearby_obstacles

def _process_entity_substepping(entity, nearby_obstacles, game):
    """Processes knockback physics and obstacle collisions for an active entity."""
    if getattr(entity, 'knockback_timer', 0) <= 0:
        return

    kb_vel_x = getattr(entity, 'knockback_velocity', [0, 0])[0]
    kb_vel_y = getattr(entity, 'knockback_velocity', [0, 0])[1]

    dx = kb_vel_x * 0.25
    dy = kb_vel_y * 0.25

    orig_x = entity.x
    entity.x += dx
    entity.rect.x = int(entity.x)
    if any(entity.rect.inflate(-4, -4).colliderect(obs) for obs in nearby_obstacles):
        entity.x = orig_x
        entity.rect.x = int(entity.x)
        entity.knockback_velocity[0] = 0

    orig_y = entity.y
    entity.y += dy
    entity.rect.y = int(entity.y)
    if any(entity.rect.inflate(-4, -4).colliderect(obs) for obs in nearby_obstacles):
        entity.y = orig_y
        entity.rect.y = int(entity.y)
        entity.knockback_velocity[1] = 0

    entity.rect.topleft = (int(entity.x), int(entity.y))

    decay = math.pow(0.9, game.dt_mult)
    entity.knockback_velocity[0] *= decay
    entity.knockback_velocity[1] *= decay
    entity.knockback_timer -= game.dt_ms

def _update_entity_batch(entity_list, player_x, player_y, view_radius, grid_size, game, is_animal_batch=False):
    """
    Performance-optimized updater:
    - Eliminates O(N log N) list sorting.
    - Entities outside (view_radius + 3 tiles) become completely DORMANT (0 CPU cost).
    """
    dormant_radius = view_radius + (3 * TILE_SIZE)
    dormant_radius_sq = dormant_radius * dormant_radius
    curr_layer = getattr(game, 'current_layer_index', 1)

    for entity in entity_list:
        if getattr(entity, 'is_dead', False) or getattr(entity, 'health', 0) <= 0:
            continue

        if getattr(entity, 'layer', 1) != curr_layer:
            continue

        dx = player_x - entity.rect.centerx
        dy = player_y - entity.rect.centery
        dist_sq = dx * dx + dy * dy

        is_chasing = getattr(entity, 'state', None) == 'chasing'
        is_aggroed = getattr(entity, 'aggro_timer', 0) > 0

        # --- DORMANT SLEEP STATE ---
        # When outside the view radius and not actively in combat, skip all simulation
        if dist_sq > dormant_radius_sq and not is_chasing and not is_aggroed:
            entity.vx = 0
            entity.vy = 0
            entity.walk_anim_angle = 0
            entity.is_dormant = True
            continue

        entity.is_dormant = False

        # Active entity updates
        nearby = [e for e in game.quadtree.query(entity.rect.inflate(grid_size, grid_size)) if e != entity]
        obstacles = get_nearby_obstacles(entity.rect, game.cached_obstacle_grid, grid_size)

        # Soft entity repulsion
        for other in nearby:
            if getattr(other, 'is_friendly', False) or getattr(entity, 'is_friendly', False):
                continue

            if not getattr(other, 'is_dead', False) and entity.rect.colliderect(other.rect):
                odx = entity.rect.centerx - other.rect.centerx
                ody = entity.rect.centery - other.rect.centery
                overlap_dist_sq = odx * odx + ody * ody
                if overlap_dist_sq < TILE_SIZE * TILE_SIZE:
                    if not hasattr(entity, 'knockback_velocity') or isinstance(entity.knockback_velocity, tuple):
                        entity.knockback_velocity = [0.0, 0.0]
                    dist = math.sqrt(overlap_dist_sq) if overlap_dist_sq > 0.001 else 0.001
                    push = max(0.2, min(2.0, (TILE_SIZE - dist) / TILE_SIZE))
                    entity.knockback_velocity[0] += (odx / dist) * push
                    entity.knockback_velocity[1] += (ody / dist) * push
                    entity.knockback_timer = max(getattr(entity, 'knockback_timer', 0), 50)

        if getattr(entity, 'aggro_timer', 0) > 0:
            entity.aggro_timer -= game.dt_ms

        _process_entity_substepping(entity, obstacles, game)
        ai_nearby = [z for z in nearby if isinstance(z, Zombie)]
        entity.update_ai(game.player.rect, obstacles, ai_nearby, game)

def update_entities(game, GRID_SIZE, zombies_to_remove):
    if getattr(game, 'player', None):
        px, py = game.player.rect.centerx, game.player.rect.centery
        view_radius = getattr(game, 'player_view_radius', 12 * TILE_SIZE)
    else:
        px, py = (0, 0)
        view_radius = 12 * TILE_SIZE

    # Process entities without global sort overhead
    _update_entity_batch(getattr(game, 'active_zombies', game.zombies), px, py, view_radius, GRID_SIZE, game, is_animal_batch=False)
    _update_entity_batch(getattr(game, 'active_animals', []), px, py, view_radius, GRID_SIZE, game, is_animal_batch=True)

    if zombies_to_remove:
        game.zombies = [z for z in game.zombies if z not in zombies_to_remove]
    
    if hasattr(game, 'npcs'):
        if hasattr(game.npcs, 'sprites'):
            for n in list(game.npcs):
                if n.is_dead:
                    n.kill()
        else:
            game.npcs = [n for n in game.npcs if not n.is_dead]

    # Corpse decay & container cleanups
    now_ms = pygame.time.get_ticks()
    for item in list(game.items_on_ground):
        if isinstance(item, Corpse) and item.is_expired(now_ms):
            try:
                game.items_on_ground.remove(item)
            except ValueError:
                pass

    Item.cleanup_disposables(game.items_on_ground, game.modals)
    if hasattr(game, 'containers') and game.containers:
        Item.cleanup_disposables(game.containers, game.modals)

    current_time = pygame.time.get_ticks()
    game.splashes = [s for s in game.splashes if current_time - s['time'] < s['duration']][:100]
    if hasattr(game, 'blood_stains'):
        game.blood_stains = [s for s in game.blood_stains if current_time - s['time'] < s['duration']][:150]
    if hasattr(game, 'ground_trails'):
        game.ground_trails = [t for t in game.ground_trails if current_time - t['time'] < t['duration']][:200]