# core/update/entities.py
import pygame
import math
import random
from core.data.config import TILE_SIZE, CHUNK_SIZE
import core.data.config
from core.entities.zombie.zombie import Zombie
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Item
from core.update.utils import get_nearby_obstacles

def _process_entity_substepping(entity, nearby_obstacles, game):
    """Processes knockback physics and obstacle collisions for an entity."""
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

def _update_entity_batch(entity_list, player_x, player_y, lod_base_radius_sq, max_per_frame, grid_size, game, is_animal_batch=False):
    """Generic updater for both zombie and animal batches with LOD and spatial separation."""
    current_time = pygame.time.get_ticks()
    processed_count = 0

    all_p_coords = [(player_x, player_y)]
    for rp in getattr(game, 'remote_players', {}).values():
        if not getattr(rp, 'is_dead', False):
            all_p_coords.append((int(rp.x), int(rp.y)))

    def get_min_player_dist_sq(e):
        return min((px - e.rect.centerx)**2 + (py - e.rect.centery)**2 for px, py in all_p_coords)

    entities_by_dist = sorted(entity_list, key=get_min_player_dist_sq)

    for entity in entities_by_dist:
        dist_sq = get_min_player_dist_sq(entity)
        is_chasing = getattr(entity, 'state', None) == 'chasing'
        is_aggroed = getattr(entity, 'aggro_timer', 0) > 0

        if dist_sq > lod_base_radius_sq * 4 and not is_chasing and not is_aggroed:
            continue

        if dist_sq > lod_base_radius_sq:
            lod_skip = 3 if dist_sq <= lod_base_radius_sq * 2 else 6
            if current_time % (lod_skip * 16) > 16 and not is_aggroed:
                if hasattr(entity, 'knockback_timer') and entity.knockback_timer > 0:
                    entity.knockback_timer -= game.dt_ms
                continue

        processed_count += 1
        if processed_count > max_per_frame:
            break

        if dist_sq <= lod_base_radius_sq:
            nearby = [e for e in game.quadtree.query(entity.rect.inflate(grid_size, grid_size)) if e != entity]
            obstacles = get_nearby_obstacles(entity.rect, game.cached_obstacle_grid, grid_size)
        elif dist_sq <= lod_base_radius_sq * 2:
            nearby = [e for e in game.quadtree.query(entity.rect.inflate(grid_size // 2, grid_size // 2)) if e != entity]
            obstacles = []
        else:
            nearby, obstacles = [], []

        # Inter-entity soft collision/repulsion
        for other in nearby:
            if not getattr(other, 'is_dead', False) and entity.rect.colliderect(other.rect):
                if is_animal_batch and hasattr(entity, 'mask') and hasattr(other, 'mask') and entity.mask and other.mask:
                    if not entity.mask.overlap(other.mask, (other.rect.x - entity.rect.x, other.rect.y - entity.rect.y)):
                        continue
                dx = entity.rect.centerx - other.rect.centerx
                dy = entity.rect.centery - other.rect.centery
                overlap_dist_sq = dx*dx + dy*dy
                if overlap_dist_sq < TILE_SIZE**2:
                    if not hasattr(entity, 'knockback_velocity') or isinstance(entity.knockback_velocity, tuple):
                        entity.knockback_velocity = [0.0, 0.0]
                    dist = math.sqrt(overlap_dist_sq) if overlap_dist_sq > 0.001 else 0.001
                    push = max(0.2, min(2.0, (TILE_SIZE - dist) / TILE_SIZE))
                    entity.knockback_velocity[0] += (dx / dist) * push
                    entity.knockback_velocity[1] += (dy / dist) * push
                    entity.knockback_timer = max(getattr(entity, 'knockback_timer', 0), 50)

        if getattr(entity, 'aggro_timer', 0) > 0:
            entity.aggro_timer -= game.dt_ms

        _process_entity_substepping(entity, obstacles, game)
        ai_nearby = [z for z in nearby if isinstance(z, Zombie)]
        entity.update_ai(game.player.rect, obstacles, ai_nearby, game)

def update_entities(game, GRID_SIZE, zombies_to_remove):
    if getattr(game, 'is_client', False):
        return

    map_chunks = getattr(core.data.config, 'MAP_CHUNKS', 2)
    max_zombies = max(12, 25 - (map_chunks * 2))
    max_animals = max(6, max_zombies // 2)

    px, py = game.player.rect.centerx, game.player.rect.centery
    lod_radius_sq = int(CHUNK_SIZE * 22 * (1.0 + map_chunks * 0.15)) ** 2

    # Process batches
    _update_entity_batch(getattr(game, 'active_zombies', game.zombies[:]), px, py, lod_radius_sq, max_zombies, GRID_SIZE, game, is_animal_batch=False)
    _update_entity_batch(getattr(game, 'active_animals', []), px, py, lod_radius_sq, max_animals, GRID_SIZE, game, is_animal_batch=True)

    # Clean dead entities
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

    # Clean modals attached to dropped/distant items
    for modal in list(game.modals):
        if modal['type'] in ('container', 'text', 'big_map', 'mobile'):
            container_item = modal.get('item')
            if container_item and hasattr(container_item, 'rect') and (container_item in game.items_on_ground):
                if (px - container_item.rect.centerx)**2 + (py - container_item.rect.centery)**2 > (TILE_SIZE * 1.5) ** 2:
                    game.modals.remove(modal)
    
    current_time = pygame.time.get_ticks()
    game.splashes = [s for s in game.splashes if current_time - s['time'] < s['duration']][:150]
    if hasattr(game, 'blood_stains'):
        game.blood_stains = [s for s in game.blood_stains if current_time - s['time'] < s['duration']][:250]