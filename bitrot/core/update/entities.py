import pygame
import math
import random
from core.data.config import TILE_SIZE, CHUNK_SIZE
import core.data.config
from core.entities.zombie.zombie import Zombie
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Item
from core.update.utils import get_nearby_obstacles

def update_entities(game, GRID_SIZE, zombies_to_remove):
    zombies_alive = getattr(game, 'active_zombies', game.zombies[:])
    map_chunks = getattr(core.data.config, 'MAP_CHUNKS', 2)
    MAX_ZOMBIES_PER_FRAME = max(12, 25 - (map_chunks * 2))

    animals_alive = getattr(game, 'active_animals', [])
    MAX_ANIMALS_PER_FRAME = max(6, MAX_ZOMBIES_PER_FRAME // 2)

    player_x, player_y = game.player.rect.centerx, game.player.rect.centery
    lod_scale = 1.0 + (map_chunks * 0.15) 
    LOD_BASE_RADIUS_SQ = int(CHUNK_SIZE * 22 * lod_scale) ** 2

    current_time = pygame.time.get_ticks()
    zombies_processed, animals_processed, multiplier = 0, 0, 1.0

    zombies_by_distance = sorted(zombies_alive, key=lambda z: (z.rect.centerx - player_x)**2 + (z.rect.centery - player_y)**2)

    for zombie in zombies_by_distance:
        dist_sq = (player_x - zombie.rect.centerx)**2 + (player_y - zombie.rect.centery)**2
        is_chasing = getattr(zombie, 'state', None) == 'chasing'
        is_aggroed = getattr(zombie, 'aggro_timer', 0) > 0
        if dist_sq > LOD_BASE_RADIUS_SQ * 4 and not is_chasing and not is_aggroed: continue

        if dist_sq > LOD_BASE_RADIUS_SQ:
            lod_skip = 3 if dist_sq <= LOD_BASE_RADIUS_SQ * 2 else 6
            if current_time % (lod_skip * 16) > 16 and not is_aggroed:
                if hasattr(zombie, 'knockback_timer') and zombie.knockback_timer > 0: zombie.knockback_timer -= game.dt_ms
                continue

        zombies_processed += 1
        if zombies_processed > MAX_ZOMBIES_PER_FRAME: break

        if dist_sq <= LOD_BASE_RADIUS_SQ:
            nearby_entities = [e for e in game.quadtree.query(zombie.rect.inflate(GRID_SIZE, GRID_SIZE)) if e != zombie]
            nearby_obstacles = get_nearby_obstacles(zombie.rect, game.cached_obstacle_grid, GRID_SIZE)
        elif dist_sq <= LOD_BASE_RADIUS_SQ * 2:
            nearby_entities = [e for e in game.quadtree.query(zombie.rect.inflate(GRID_SIZE // 2, GRID_SIZE // 2)) if e != zombie]
            nearby_obstacles = []
        else:
            nearby_entities, nearby_obstacles = [], []

        for other_entity in nearby_entities:
            if not getattr(other_entity, 'is_dead', False) and zombie.rect.colliderect(other_entity.rect):
                dx, dy = zombie.rect.centerx - other_entity.rect.centerx, zombie.rect.centery - other_entity.rect.centery
                dist_sq = dx*dx + dy*dy
                if dist_sq < TILE_SIZE**2: 
                    if not hasattr(zombie, 'knockback_velocity') or isinstance(zombie.knockback_velocity, tuple): zombie.knockback_velocity = [0.0, 0.0]
                    if dist_sq > 0: zombie.knockback_velocity[0] += (dx / dist_sq); zombie.knockback_velocity[1] += (dy / dist_sq)
                    else: zombie.knockback_velocity[0] += random.uniform(-1.0, 1.0); zombie.knockback_velocity[1] += random.uniform(-1.0, 1.0)
                    zombie.knockback_timer = max(getattr(zombie, 'knockback_timer', 0), 50)

        kb_vel_x, kb_vel_y = getattr(zombie, 'knockback_velocity', [0, 0])[0], getattr(zombie, 'knockback_velocity', [0, 0])[1]

        if getattr(zombie, 'aggro_timer', 0) > 0: zombie.aggro_timer -= game.dt_ms

        if getattr(zombie, 'knockback_timer', 0) > 0:
            VELOCITY_MULTIPLIER = 0.25
            dx, dy = kb_vel_x * VELOCITY_MULTIPLIER, kb_vel_y * VELOCITY_MULTIPLIER

            original_x = zombie.x
            zombie.x += dx; zombie.rect.x = int(zombie.x)
            if any(zombie.rect.colliderect(obs) for obs in nearby_obstacles): zombie.x = original_x; zombie.rect.x = int(zombie.x); zombie.knockback_velocity[0] = 0

            original_y = zombie.y
            zombie.y += dy; zombie.rect.y = int(zombie.y)
            if any(zombie.rect.colliderect(obs) for obs in nearby_obstacles): zombie.y = original_y; zombie.rect.y = int(zombie.y); zombie.knockback_velocity[1] = 0

            zombie.rect.topleft = (int(zombie.x), int(zombie.y))

            decay_factor = math.pow(0.9, game.dt_mult * multiplier)
            zombie.knockback_velocity[0] *= decay_factor
            zombie.knockback_velocity[1] *= decay_factor
            zombie.knockback_timer -= game.dt_ms * multiplier

        zombie.update_ai(game.player.rect, nearby_obstacles, [z for z in nearby_entities if isinstance(z, Zombie)], game)

    animals_by_distance = sorted(animals_alive, key=lambda a: (a.rect.centerx - player_x)**2 + (a.rect.centery - player_y)**2)

    for animal in animals_by_distance:
        dist_sq = (player_x - animal.rect.centerx)**2 + (player_y - animal.rect.centery)**2
        is_chasing = getattr(animal, 'state', None) == 'chasing'
        is_aggroed = getattr(animal, 'aggro_timer', 0) > 0
        if dist_sq > LOD_BASE_RADIUS_SQ * 4 and not is_chasing and not is_aggroed: continue

        if dist_sq > LOD_BASE_RADIUS_SQ:
            lod_skip = 3 if dist_sq <= LOD_BASE_RADIUS_SQ * 2 else 6
            if current_time % (lod_skip * 16) > 16 and not is_aggroed:
                if hasattr(animal, 'knockback_timer') and animal.knockback_timer > 0: animal.knockback_timer -= game.dt_ms
                continue

        animals_processed += 1
        if animals_processed > MAX_ANIMALS_PER_FRAME: break

        if dist_sq <= LOD_BASE_RADIUS_SQ:
            nearby_zombies = [z for z in game.quadtree.query(animal.rect.inflate(GRID_SIZE, GRID_SIZE)) if isinstance(z, Zombie) and z != animal]
            nearby_obstacles = get_nearby_obstacles(animal.rect, game.cached_obstacle_grid, GRID_SIZE)
        elif dist_sq <= LOD_BASE_RADIUS_SQ * 2:
            nearby_zombies = [z for z in game.quadtree.query(animal.rect.inflate(GRID_SIZE // 2, GRID_SIZE // 2)) if isinstance(z, Zombie) and z != animal]
            nearby_obstacles = []
        else:
            nearby_zombies, nearby_obstacles = [], []

        for other_entity in nearby_zombies:
            if not getattr(other_entity, 'is_dead', False) and animal.rect.colliderect(other_entity.rect):
                if hasattr(animal, 'mask') and hasattr(other_entity, 'mask') and animal.mask and other_entity.mask:
                    if not animal.mask.overlap(other_entity.mask, (other_entity.rect.x - animal.rect.x, other_entity.rect.y - animal.rect.y)): continue

                dx, dy = animal.rect.centerx - other_entity.rect.centerx, animal.rect.centery - other_entity.rect.centery
                dist_sq = dx*dx + dy*dy
                if dist_sq < TILE_SIZE**2:
                    if not hasattr(animal, 'knockback_velocity') or isinstance(animal.knockback_velocity, tuple): animal.knockback_velocity = [0.0, 0.0]
                    if dist_sq > 0: animal.knockback_velocity[0] += (dx / dist_sq); animal.knockback_velocity[1] += (dy / dist_sq)
                    else: animal.knockback_velocity[0] += random.uniform(-1.0, 1.0); animal.knockback_velocity[1] += random.uniform(-1.0, 1.0)
                    animal.knockback_timer = max(getattr(animal, 'knockback_timer', 0), 50)

        kb_vel_x, kb_vel_y = getattr(animal, 'knockback_velocity', [0, 0])[0], getattr(animal, 'knockback_velocity', [0, 0])[1]

        if getattr(animal, 'aggro_timer', 0) > 0: animal.aggro_timer -= game.dt_ms

        if getattr(animal, 'knockback_timer', 0) > 0:
            VELOCITY_MULTIPLIER = 0.25
            dx, dy = kb_vel_x * VELOCITY_MULTIPLIER, kb_vel_y * VELOCITY_MULTIPLIER

            original_x = animal.x
            animal.x += dx; animal.rect.x = int(animal.x)
            if any(animal.rect.colliderect(obs) for obs in nearby_obstacles): animal.x = original_x; animal.rect.x = int(animal.x); animal.knockback_velocity[0] = 0

            original_y = animal.y
            animal.y += dy; animal.rect.y = int(animal.y)
            if any(animal.rect.colliderect(obs) for obs in nearby_obstacles): animal.y = original_y; animal.rect.y = int(animal.y); animal.knockback_velocity[1] = 0

            animal.rect.topleft = (int(animal.x), int(animal.y))

            decay_factor = math.pow(0.9, game.dt_mult * multiplier)
            animal.knockback_velocity[0] *= decay_factor
            animal.knockback_velocity[1] *= decay_factor
            animal.knockback_timer -= game.dt_ms * multiplier

        animal.update_ai(game.player.rect, nearby_obstacles, nearby_zombies, game)

    if zombies_to_remove: game.zombies = [z for z in game.zombies if z not in zombies_to_remove]
    
    if hasattr(game, 'npcs'):
        if hasattr(game.npcs, 'sprites'):
            for n in list(game.npcs):
                if n.is_dead: n.kill() 
        else:
            game.npcs = [n for n in game.npcs if not n.is_dead]

    now_ms = pygame.time.get_ticks()
    for ground_item in list(game.items_on_ground):
        if isinstance(ground_item, Corpse) and ground_item.is_expired(now_ms):
            print(f"{getattr(ground_item,'name','Corpse')} decayed.")
            try: game.items_on_ground.remove(ground_item)
            except ValueError: pass

    def ground_msg(text): print(text)
    Item.cleanup_disposables(game.items_on_ground, game.modals, ground_msg)
    if hasattr(game, 'containers') and game.containers: Item.cleanup_disposables(game.containers, game.modals, ground_msg)

    for modal in list(game.modals):
        if modal['type'] in ('container', 'text', 'big_map', 'mobile'):
            container_item = modal.get('item')
            if container_item and hasattr(container_item, 'rect') and (container_item in game.items_on_ground):
                if (game.player.rect.centerx - container_item.rect.centerx)**2 + (game.player.rect.centery - container_item.rect.centery)**2 > (TILE_SIZE * 1.5) ** 2:
                    game.modals.remove(modal)
    
    game.splashes = [s for s in game.splashes if current_time - s['time'] < s['duration']][:150]
    if hasattr(game, 'blood_stains'): game.blood_stains = [s for s in game.blood_stains if current_time - s['time'] < s['duration']][:250]