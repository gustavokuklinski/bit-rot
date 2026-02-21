import os
import pygame
import random
import math

from core.data.config import *
import core.data.config
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.entities.zombie.zombie import Zombie
from core.entities.animal.animal import Animal 
from core.entities.player.player import Player
from core.placement import find_free_tile
from core.map.world_layers import check_for_layer_teleport
from core.map.spawn_manager import spawn_initial_zombies, spawn_animals
from core.messages import display_message_zombie, display_message_player


def build_obstacle_grid(obstacles, grid_size):
    """
    Builds a static spatial grid for STATIC obstacles (Walls).
    """
    grid = {}
    for ob in obstacles:
        grid_x = int(ob.centerx // grid_size)
        grid_y = int(ob.centery // grid_size)
        cell = (grid_x, grid_y)
        
        if cell not in grid:
            grid[cell] = [ob]
        else:
            grid[cell].append(ob)
    return grid

def get_nearby_obstacles(entity_rect, grid, grid_size):
    nearby = []
    grid_x = int(entity_rect.centerx // grid_size)
    grid_y = int(entity_rect.centery // grid_size)
    
    for i in range(-1, 2):
        for j in range(-1, 2):
            cell = (grid_x + i, grid_y + j)
            if cell in grid:
                nearby.extend(grid[cell])
    return nearby

def create_blood_splatter(game, target_rect, damage, direction_vector=None):
    if not hasattr(game, 'blood_stains'):
        return

    if direction_vector is None:
        angle = random.uniform(0, math.pi * 2)
        direction_vector = [math.cos(angle), math.sin(angle)]

    trail_dir_x, trail_dir_y = direction_vector[0], direction_vector[1]
    
    mag = math.hypot(trail_dir_x, trail_dir_y)
    if mag > 0:
        trail_dir_x /= mag
        trail_dir_y /= mag
    
    perp_dir_x, perp_dir_y = -trail_dir_y, trail_dir_x
    
    base_x, base_y = target_rect.centerx, target_rect.bottom

    # Fixed size for blood splatters (same as melee weapons)
    stain_size = 4

    for i in range(1, 7):
        offset_pixels = (i / 3.0) * (TILE_SIZE * 0.75) + random.uniform(-2, 5)
        lateral_scatter = random.uniform(-8, 8) 
        
        stain_pos_x = base_x - (trail_dir_x * offset_pixels) 
        stain_pos_y = base_y - (trail_dir_y * offset_pixels)

        stain_pos_x += perp_dir_x * lateral_scatter
        stain_pos_y += perp_dir_y * lateral_scatter
        
        stain_rect = pygame.Rect(stain_pos_x - 1, stain_pos_y - 1, 2, 2)
        
        collides_with_obstacle = False
        if hasattr(game, 'cached_obstacle_grid'):
            GRID_SIZE_CHECK = 128
            nearby_obs = get_nearby_obstacles(stain_rect, game.cached_obstacle_grid, GRID_SIZE_CHECK)
            if any(stain_rect.colliderect(obs) for obs in nearby_obs):
                collides_with_obstacle = True
        else:
            if any(stain_rect.colliderect(obs) for obs in game.obstacles):
                collides_with_obstacle = True
        
        if collides_with_obstacle:
            continue

        game.blood_stains.append({
            'pos': (stain_pos_x, stain_pos_y),
            'size': stain_size,
            'color': (139, 0, 0), 
            'time': pygame.time.get_ticks(),
            'duration': random.randint(30000, 60000) 
        })
    
    if len(game.blood_stains) > 250:
        game.blood_stains = game.blood_stains[-250:]

def update_game_state(game):
    
    GRID_SIZE = 128
    
    # Static Obstacle Grid (Walls)
    current_obstacle_count = len(game.obstacles)
    # [OPTIMIZATION NOTE] On huge maps, game.obstacles is HUGE. Rebuilding this every time a door opens 
    # causes a lag spike. Ideally, this should be segmented, but for now we rely on the caching check.
    if not hasattr(game, 'cached_obstacle_grid') or getattr(game, 'cached_obstacle_count', -1) != current_obstacle_count:
        game.cached_obstacle_grid = build_obstacle_grid(game.obstacles, GRID_SIZE)
        game.cached_obstacle_count = current_obstacle_count

    # Player Movement Update
    nearby_player_obstacles = get_nearby_obstacles(game.player.rect, game.cached_obstacle_grid, GRID_SIZE)
    game.player.update_position(nearby_player_obstacles, game.zombies, game)

    game.hovered_interactable_tile_rect = None 
    facing_x, facing_y = game.get_player_facing_tile()
    target_tile = game.find_interactable_tile()
    if target_tile:
        tx, ty = target_tile
        game.hovered_interactable_tile_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    check_zombie_respawn(game)
    check_animal_respawn(game) 
    check_dynamic_zombie_spawns(game, GRID_SIZE)
    
    if game.player.update_stats(game):
        game.game_state = 'GAME_OVER'

    projectiles_to_remove = []
    zombies_to_remove = []

    # --- Projectile Update Loop ---
    multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
    
    for p in game.projectiles:
        world_max_x = game.world_min_x + game.map_width_pixels
        world_max_y = game.world_min_y + game.map_height_pixels

        # Apply fast forward to projectile speed
        if multiplier > 1.0:
            p.vx *= multiplier
            p.vy *= multiplier

        local_obstacles = get_nearby_obstacles(p.rect, game.cached_obstacle_grid, GRID_SIZE)

        if p.update(game.world_min_x, game.world_min_y, world_max_x, world_max_y) or any(p.rect.colliderect(ob) for ob in local_obstacles):
            projectiles_to_remove.append(p)
            continue

        if getattr(p, 'hostile', False) and game.player and not game.player.is_dead:
            if p.rect.colliderect(game.player.rect):
                damage = getattr(p, 'damage', 5) 
                game.player.take_damage(game, damage, 0)
                display_message_player(f"You were hit!")
                game.splashes.append({
                    'pos': game.player.rect.center,
                    'time': pygame.time.get_ticks(),
                    'duration': 350,
                    'radius': 3,
                    'type': 'hit_puff' 
                })
                projectiles_to_remove.append(p)
                continue
        
        search_rect = p.rect.inflate(10, 10)
        potential_hits = game.quadtree.query(search_rect)
        
        hit_zombie = next((z for z in potential_hits if isinstance(z, Zombie) and z not in zombies_to_remove and p.rect.colliderect(z.rect)), None)

        if hit_zombie:
            # Check if it's an animal
            is_animal = getattr(hit_zombie, 'type', 'zombie') == 'animal'
            owner = getattr(p, 'owner', None)

            if owner is None or owner == game.player:
                if player_hit_zombie(game.player, hit_zombie, game):
                    if is_animal:
                        # Handle animal death
                        hit_zombie.die(game)
                        if hit_zombie in game.items_on_ground:
                            game.items_on_ground.remove(hit_zombie)
                        if hit_zombie in game.active_animals:
                            game.active_animals.remove(hit_zombie)
                    else:
                        # Handle zombie death
                        zombies_to_remove.append(hit_zombie)
                        handle_zombie_death(game, hit_zombie, game.items_on_ground, game.obstacles, game.player.active_weapon)
                        game.zombies_killed += 1

            else:
                damage = getattr(p, 'damage', 5)
                is_dead = hit_zombie.take_damage(damage, game, attacker=owner)

                game.splashes.append({
                    'pos': (hit_zombie.rect.centerx, hit_zombie.rect.bottom),
                    'time': pygame.time.get_ticks(),
                    'duration': 350, 'radius': 2, 'type': 'hit_puff'
                })

                if is_dead:
                    if is_animal:
                        # Handle animal death
                        hit_zombie.die(game)
                        if hit_zombie in game.items_on_ground:
                            game.items_on_ground.remove(hit_zombie)
                        if hit_zombie in game.active_animals:
                            game.active_animals.remove(hit_zombie)
                    else:
                        # Handle zombie death
                        zombies_to_remove.append(hit_zombie)
                        handle_zombie_death(game, hit_zombie, game.items_on_ground, game.obstacles, None)

                        game.splashes.append({
                            'pos': (hit_zombie.rect.centerx, hit_zombie.rect.bottom),
                            'time': pygame.time.get_ticks(),
                            'duration': 600, 'radius': 5, 'type': 'death_burst'
                        })

            projectiles_to_remove.append(p)
            continue
        
        hit_npc = next((n for n in potential_hits if n in game.npcs and not n.is_dead and p.rect.colliderect(n.rect)), None)
        
        if hit_npc:
             damage = getattr(p, 'damage', game.player.get_attack_damage())
             
             dx = hit_npc.rect.centerx - p.rect.centerx
             dy = hit_npc.rect.centery - p.rect.centery
             mag = math.hypot(dx, dy)
             direction = [dx/mag, dy/mag] if mag > 0 else None
             
             create_blood_splatter(game, hit_npc.rect, damage, direction)

             if game.player and game.player.active_weapon and game.player.active_weapon.item_type == 'weapon_ranged':
                  knockback_force = getattr(game.player.active_weapon, 'knockback', 0)
                  
                  dx = hit_npc.rect.centerx - game.player.rect.centerx
                  dy = hit_npc.rect.centery - game.player.rect.centery
                  dist = math.hypot(dx, dy)
                  if dist > 0:
                      ndx, ndy = dx/dist, dy/dist
                      hit_npc.knockback_velocity = [ndx * knockback_force, ndy * knockback_force]
                      hit_npc.knockback_timer = 200
             
             is_dead = hit_npc.take_damage(damage, game, attacker=game.player)
             display_message_player(f"You shot {hit_npc.name}")
             if is_dead:
                display_message_player(f"You killed {hit_npc.name}!")
             projectiles_to_remove.append(p)
             continue

    game.projectiles = [p for p in game.projectiles if p not in projectiles_to_remove]
    
    # [OPTIMIZATION] Only process ACTIVE zombies (those near the player)
    # The active list is pre-calculated in game.py
    zombies_alive = getattr(game, 'active_zombies', game.zombies[:])

    # [OPTIMIZATION] Dynamic MAX_ZOMBIES_PER_FRAME based on map size
    # Larger maps = fewer zombies processed per frame to maintain FPS
    map_chunks = getattr(core.data.config, 'MAP_CHUNKS', 2)
    MAX_ZOMBIES_PER_FRAME = max(12, 25 - (map_chunks * 2))

    # Also update animals (they're stored in items_on_ground but tracked in active_animals)
    animals_alive = getattr(game, 'active_animals', [])

    # [OPTIMIZATION] Separate limit for animals to ensure they get processed
    MAX_ANIMALS_PER_FRAME = max(6, MAX_ZOMBIES_PER_FRAME // 2)

    player_x, player_y = game.player.rect.centerx, game.player.rect.centery

    # [OPTIMIZATION] Dynamic LOD tiers based on map chunks
    # Larger maps = more aggressive LOD to maintain 60 FPS
    # LOD 1: Full update - every frame (AI, pathfinding, collisions)
    # LOD 2: Simplified update - every 3rd frame (reduced queries)
    # LOD 3: Minimal update - every 6th frame (only chasing zombies)
    lod_scale = 1.0 + (map_chunks * 0.15)  # Scale distances up for larger maps
    LOD_BASE_RADIUS_SQ = int(CHUNK_SIZE * 22 * lod_scale) ** 2

    current_time = pygame.time.get_ticks()
    zombies_processed = 0
    animals_processed = 0

    # [FIX] Sort zombies by distance to player - closest ones must be processed first
    # This ensures zombies near the player always get updated, even if we hit the frame limit
    zombies_by_distance = sorted(
        zombies_alive,
        key=lambda z: (z.rect.centerx - player_x)**2 + (z.rect.centery - player_y)**2
    )

    # Update zombies first (closest first)
    for zombie in zombies_by_distance:
        # [OPTIMIZATION] Skip zombies way too far from player
        dx = player_x - zombie.rect.centerx
        dy = player_y - zombie.rect.centery
        dist_sq = dx*dx + dy*dy

        # Absolute maximum range - skip entirely (unless actively chasing)
        is_chasing = getattr(zombie, 'state', None) == 'chasing'
        if dist_sq > LOD_BASE_RADIUS_SQ * 4 and not is_chasing:
            continue

        # [OPTIMIZATION] More aggressive LOD-based update frequency
        # LOD 2: Update every 3rd frame (reduced AI queries)
        # LOD 3: Update every 6th frame (only movement, no queries)
        if dist_sq > LOD_BASE_RADIUS_SQ:
            lod_skip = 3 if dist_sq <= LOD_BASE_RADIUS_SQ * 2 else 6
            frame_mod = current_time % (lod_skip * 16)

            # Skip full update but still process knockback
            if frame_mod > 16:
                if hasattr(zombie, 'knockback_timer') and zombie.knockback_timer > 0:
                    zombie.knockback_timer -= 16
                continue

        # [OPTIMIZATION] Limit zombies processed per frame
        zombies_processed += 1
        if zombies_processed > MAX_ZOMBIES_PER_FRAME:
            break

        # [OPTIMIZATION] Adaptive quadtree query and obstacle lookup based on LOD
        # LOD 1: Full queries (AI needs accurate data)
        # LOD 2: Smaller query radius, skip obstacles
        # LOD 3: Skip all queries (zombies far away)
        if dist_sq <= LOD_BASE_RADIUS_SQ:
            # LOD 1: Full queries
            search_area = zombie.rect.inflate(GRID_SIZE, GRID_SIZE)
            nearby_zombies = game.quadtree.query(search_area)
            nearby_zombies = [z for z in nearby_zombies if isinstance(z, Zombie) and z != zombie]
            nearby_obstacles = get_nearby_obstacles(zombie.rect, game.cached_obstacle_grid, GRID_SIZE)
        elif dist_sq <= LOD_BASE_RADIUS_SQ * 2:
            # LOD 2: Reduced queries, no obstacle lookup
            search_area = zombie.rect.inflate(GRID_SIZE // 2, GRID_SIZE // 2)
            nearby_zombies = game.quadtree.query(search_area)
            nearby_zombies = [z for z in nearby_zombies if isinstance(z, Zombie) and z != zombie]
            nearby_obstacles = []
        else:
            # LOD 3: Skip all spatial queries
            nearby_zombies = []
            nearby_obstacles = []

        kb_vel_x = getattr(zombie, 'knockback_velocity', [0, 0])[0]
        kb_vel_y = getattr(zombie, 'knockback_velocity', [0, 0])[1]

        if getattr(zombie, 'knockback_timer', 0) > 0:
            VELOCITY_MULTIPLIER = 0.25
            dx = kb_vel_x * VELOCITY_MULTIPLIER
            dy = kb_vel_y * VELOCITY_MULTIPLIER

            original_x = zombie.x
            zombie.x += dx
            zombie.rect.x = int(zombie.x)

            collision_x = False
            for obs in nearby_obstacles:
                if zombie.rect.colliderect(obs):
                    collision_x = True; break

            if collision_x:
                zombie.x = original_x; zombie.rect.x = int(zombie.x); zombie.knockback_velocity[0] = 0

            original_y = zombie.y
            zombie.y += dy
            zombie.rect.y = int(zombie.y)

            collision_y = False
            for obs in nearby_obstacles:
                if zombie.rect.colliderect(obs):
                    collision_y = True; break

            if collision_y:
                zombie.y = original_y; zombie.rect.y = int(zombie.y); zombie.knockback_velocity[1] = 0

            zombie.rect.topleft = (int(zombie.x), int(zombie.y))

            zombie.knockback_velocity[0] *= 0.9
            zombie.knockback_velocity[1] *= 0.9
            zombie.knockback_timer -= game.clock.get_time()

        zombie.update_ai(game.player.rect, nearby_obstacles, nearby_zombies, game)

        # [OPTIMIZATION] Removed redundant attack check - handled in update_ai

    # [FIX] Sort animals by distance to player - closest ones must be processed first
    animals_by_distance = sorted(
        animals_alive,
        key=lambda a: (a.rect.centerx - player_x)**2 + (a.rect.centery - player_y)**2
    )

    # Update animals separately (they use Zombie AI but need their own processing limit)
    for animal in animals_by_distance:
        # [OPTIMIZATION] Skip animals way too far from player
        dx = player_x - animal.rect.centerx
        dy = player_y - animal.rect.centery
        dist_sq = dx*dx + dy*dy

        # Absolute maximum range - skip entirely (unless actively chasing)
        is_chasing = getattr(animal, 'state', None) == 'chasing'
        if dist_sq > LOD_BASE_RADIUS_SQ * 4 and not is_chasing:
            continue

        # [OPTIMIZATION] More aggressive LOD-based update frequency
        if dist_sq > LOD_BASE_RADIUS_SQ:
            lod_skip = 3 if dist_sq <= LOD_BASE_RADIUS_SQ * 2 else 6
            frame_mod = current_time % (lod_skip * 16)

            # Skip full update but still process knockback
            if frame_mod > 16:
                if hasattr(animal, 'knockback_timer') and animal.knockback_timer > 0:
                    animal.knockback_timer -= 16
                continue

        # [OPTIMIZATION] Limit animals processed per frame
        animals_processed += 1
        if animals_processed > MAX_ANIMALS_PER_FRAME:
            break

        # [OPTIMIZATION] Adaptive quadtree query and obstacle lookup based on LOD
        if dist_sq <= LOD_BASE_RADIUS_SQ:
            # LOD 1: Full queries
            search_area = animal.rect.inflate(GRID_SIZE, GRID_SIZE)
            nearby_zombies = game.quadtree.query(search_area)
            nearby_zombies = [z for z in nearby_zombies if isinstance(z, Zombie) and z != animal]
            nearby_obstacles = get_nearby_obstacles(animal.rect, game.cached_obstacle_grid, GRID_SIZE)
        elif dist_sq <= LOD_BASE_RADIUS_SQ * 2:
            # LOD 2: Reduced queries, no obstacle lookup
            search_area = animal.rect.inflate(GRID_SIZE // 2, GRID_SIZE // 2)
            nearby_zombies = game.quadtree.query(search_area)
            nearby_zombies = [z for z in nearby_zombies if isinstance(z, Zombie) and z != animal]
            nearby_obstacles = []
        else:
            # LOD 3: Skip all spatial queries
            nearby_zombies = []
            nearby_obstacles = []

        kb_vel_x = getattr(animal, 'knockback_velocity', [0, 0])[0]
        kb_vel_y = getattr(animal, 'knockback_velocity', [0, 0])[1]

        if getattr(animal, 'knockback_timer', 0) > 0:
            VELOCITY_MULTIPLIER = 0.25
            dx = kb_vel_x * VELOCITY_MULTIPLIER
            dy = kb_vel_y * VELOCITY_MULTIPLIER

            original_x = animal.x
            animal.x += dx
            animal.rect.x = int(animal.x)

            collision_x = False
            for obs in nearby_obstacles:
                if animal.rect.colliderect(obs):
                    collision_x = True; break

            if collision_x:
                animal.x = original_x; animal.rect.x = int(animal.x); animal.knockback_velocity[0] = 0

            original_y = animal.y
            animal.y += dy
            animal.rect.y = int(animal.y)

            collision_y = False
            for obs in nearby_obstacles:
                if animal.rect.colliderect(obs):
                    collision_y = True; break

            if collision_y:
                animal.y = original_y; animal.rect.y = int(animal.y); animal.knockback_velocity[1] = 0

            animal.rect.topleft = (int(animal.x), int(animal.y))

            animal.knockback_velocity[0] *= 0.9
            animal.knockback_velocity[1] *= 0.9
            animal.knockback_timer -= game.clock.get_time()

        animal.update_ai(game.player.rect, nearby_obstacles, nearby_zombies, game)

    if zombies_to_remove:
        game.zombies = [z for z in game.zombies if z not in zombies_to_remove]
    
    if hasattr(game, 'npcs'):
        for npc in game.npcs:
            if not npc.is_dead:
                # Active NPCs are updated in game.py now
                pass

    now_ms = pygame.time.get_ticks()
    for ground_item in list(game.items_on_ground):
        if isinstance(ground_item, Corpse):
            if ground_item.is_expired(now_ms):
                display_message_zombie(f"{getattr(ground_item,'name','Corpse')} decayed.")
                try: game.items_on_ground.remove(ground_item)
                except ValueError: pass

    # Cleanup empty disposable containers on ground
    def ground_msg(text):
        display_message_player(text)
    Item.cleanup_disposables(game.items_on_ground, game.modals, ground_msg)

    # Cleanup empty disposable containers in game.containers (vehicles, etc.)
    if hasattr(game, 'containers') and game.containers:
        Item.cleanup_disposables(game.containers, game.modals, ground_msg)

    for modal in list(game.modals):
        if modal['type'] == 'container':
            container_item = modal['item']
            if container_item and hasattr(container_item, 'rect') and (container_item in game.items_on_ground):
                dx = game.player.rect.centerx - container_item.rect.centerx
                dy = game.player.rect.centery - container_item.rect.centery
                dist_sq = dx*dx + dy*dy
                if dist_sq > (TILE_SIZE * 1.5) ** 2:
                    game.modals.remove(modal)
    
    current_time = pygame.time.get_ticks()
    game.splashes = [s for s in game.splashes if current_time - s['time'] < s['duration']]

    if hasattr(game, 'blood_stains'):
        game.blood_stains = [s for s in game.blood_stains if current_time - s['time'] < s['duration']]

    # --- Vehicle Update ---
    if game.map_manager and hasattr(game.map_manager, 'vehicles'):
        roadkill_zombies = []
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0

        # [OPTIMIZATION] Only update vehicles near player?
        # For now we assume active_zombies logic covers the expensive parts.
        for vehicle in game.map_manager.vehicles:
            vehicle.update()
            # Apply fast forward to vehicle physics
            if multiplier > 1.0:
                vehicle.velocity = (vehicle.velocity[0] * multiplier, vehicle.velocity[1] * multiplier)
            
            detected_entities = []
            
            if hasattr(vehicle, 'hit_entities') and vehicle.hit_entities:
                detected_entities.extend(vehicle.hit_entities)
                vehicle.hit_entities = []

            search_rect = vehicle.rect.inflate(10, 10)
            potential = game.quadtree.query(search_rect)
            
            for entity in potential:
                if entity not in detected_entities and vehicle.rect.colliderect(entity.rect):
                     if entity == vehicle: continue
                     detected_entities.append(entity)
            
            if detected_entities:
                speed = math.hypot(vehicle.velocity[0], vehicle.velocity[1])
                
                if speed > 0.5: 
                    for entity in detected_entities:
                        if entity in roadkill_zombies: continue
                        if getattr(entity, 'is_dead', False): continue

                        current_time = pygame.time.get_ticks()
                        last_hit = getattr(entity, 'last_vehicle_hit_time', 0)
                        if current_time - last_hit < 500: continue
                        entity.last_vehicle_hit_time = current_time

                        impact_damage = 10000 
                        vehicle.damage_motor(2.0)

                        velocity_dir = None
                        if speed > 0:
                             velocity_dir = [vehicle.velocity[0]/speed, vehicle.velocity[1]/speed]
                        
                        # [FIX] Pass a smaller damage value (100) for visual splatter so it doesn't cover the whole map
                        create_blood_splatter(game, entity.rect, 20, velocity_dir)

                        if entity in game.zombies:
                             if entity.take_damage(impact_damage, game):
                                roadkill_zombies.append(entity)
                                handle_zombie_death(game, entity, game.items_on_ground, game.obstacles, None)
                                game.zombies_killed += 1
                             else:
                                 if speed > 0:
                                     push_x = (vehicle.velocity[0] / speed) * 15
                                     push_y = (vehicle.velocity[1] / speed) * 15
                                     entity.knockback_velocity = [push_x, push_y]
                                     entity.knockback_timer = 200

                        elif getattr(entity, 'type', 'zombie') == 'animal':
                             # Handle animal roadkill
                             if entity.take_damage(impact_damage, game):
                                 entity.die(game)
                                 if entity in game.items_on_ground:
                                     game.items_on_ground.remove(entity)
                                 if entity in game.active_animals:
                                     game.active_animals.remove(entity)
                                 display_message_player(f"You ran over an animal!")
                             else:
                                 if speed > 0:
                                     push_x = (vehicle.velocity[0] / speed) * 15
                                     push_y = (vehicle.velocity[1] / speed) * 15
                                     entity.knockback_velocity = [push_x, push_y]
                                     entity.knockback_timer = 200

                        elif hasattr(game, 'npcs') and entity in game.npcs:
                             is_dead = entity.take_damage(impact_damage, game, attacker=game.player)
                             if is_dead:
                                 handle_zombie_death(game, entity, game.items_on_ground, game.obstacles, None)
                                 display_message_player(f"You ran over {entity.name}!")
                             else:
                                 if speed > 0:
                                     push_x = (vehicle.velocity[0] / speed) * 15 
                                     push_y = (vehicle.velocity[1] / speed) * 15
                                     entity.knockback_velocity = [push_x, push_y]
                                     entity.knockback_timer = 200

        if roadkill_zombies:
            game.zombies = [z for z in game.zombies if z not in roadkill_zombies and z not in zombies_to_remove]
        
        if hasattr(game, 'npcs'):
            if hasattr(game.npcs, 'sprites'):
                for n in list(game.npcs):
                    if n.is_dead:
                        n.kill() 
            else:
                game.npcs = [n for n in game.npcs if not n.is_dead]

    game.zombies = [z for z in game.zombies if z not in zombies_to_remove]

def player_hit_zombie(player, zombie, game):
    progression = player.progression
    active_weapon = player.active_weapon
    base_damage = 1
    damage_multiplier = 1.0
    is_headshot = False
    is_ranged = False
    knockback_force = 0
    projectile_dir = [0, 0]

    if active_weapon:
        base_damage = active_weapon.damage
        if active_weapon.item_type == 'weapon_ranged': 
            damage_multiplier = progression.get_ranged_damage_multiplier(player)
            if random.random() < progression.get_headshot_chance(player):
                is_headshot = True
                damage_multiplier *= 2.0 

            dx = zombie.rect.centerx - player.rect.centerx
            dy = zombie.rect.centery - player.rect.centery
            magnitude = math.hypot(dx, dy)
            if magnitude > 0:
                projectile_dir = [dx / magnitude, dy / magnitude]
            knockback_force = getattr(active_weapon, 'knockback', 50)
            is_ranged = True 
        else: 
            damage_multiplier = progression.get_melee_damage_multiplier(player)
            durability_loss = progression.get_weapon_durability_loss(player)
            if active_weapon.durability is not None and active_weapon.durability > 0:
                active_weapon.durability -= durability_loss
                if active_weapon.durability <= 0:
                    player.active_weapon = None
                    display_message_player(f"{active_weapon.name} is broken and unequipped.")
    else: 
        base_damage = progression.get_unarmed_damage(player)

    final_damage = base_damage * damage_multiplier

    # Calculate hit direction for blood splatter and knockback
    dx = zombie.rect.centerx - player.rect.centerx
    dy = zombie.rect.centery - player.rect.centery
    magnitude = math.hypot(dx, dy)
    if magnitude > 0:
        projectile_dir = [dx / magnitude, dy / magnitude]

    if is_ranged and knockback_force > 0:
        zombie.knockback_velocity = [projectile_dir[0] * knockback_force, projectile_dir[1] * knockback_force]
        zombie.knockback_timer = 400

    # Create blood splatter for both ranged and melee attacks
    create_blood_splatter(game, zombie.rect, final_damage, projectile_dir)

    game.splashes.append({
        'pos': (zombie.rect.centerx, zombie.rect.bottom),
        'time': pygame.time.get_ticks(),
        'duration': 350, 
        'radius': 2,
        'type': 'hit_puff'
    })
    
    if zombie.take_damage(final_damage, game):
        game.splashes.append({
            'pos': (zombie.rect.centerx, zombie.rect.bottom), 
            'time': pygame.time.get_ticks(),
            'duration': 250, 
            'radius': 5,    
            'type': 'death_burst'
        })
        return True

    hit_type = "Headshot" if is_headshot else "Hit"
    display_message_player(f"{hit_type}! Dealt {final_damage:.1f} damage.")
    return False

def handle_zombie_death(game, zombie, items_on_ground_list, obstacles, weapon):
    zombie.die(game)
    if weapon:
        game.player.process_kill(weapon, zombie)

    current_map_filename = game.map_manager.current_map_filename
    if current_map_filename not in game.map_states:
        game.map_states[current_map_filename] = {'items': [], 'zombies': [], 'killed_zombies': [], 'picked_up_items': [], 'last_respawn_time': pygame.time.get_ticks()} 
    game.map_states[current_map_filename].setdefault('killed_zombies', []).append(zombie.id)

def check_dynamic_zombie_spawns(game, grid_size=128):
    triggered_spawns_for_layer = game.layer_spawn_triggers.get(game.current_layer_index)
    if triggered_spawns_for_layer is None:
        game.layer_spawn_triggers[game.current_layer_index] = set()
        triggered_spawns_for_layer = game.layer_spawn_triggers[game.current_layer_index]

    player_pos = game.player.rect.center
    GRID_SIZE_SPAWNS = getattr(game, 'SPAWN_GRID_SIZE', 512)
    player_grid_x = int(player_pos[0] // GRID_SIZE_SPAWNS)
    player_grid_y = int(player_pos[1] // GRID_SIZE_SPAWNS)
    spawn_grid = getattr(game, 'spawn_point_grid', {})

    potential_spawns = []
    # Expanded search range to ensure we find spawn points that are further away
    for i in range(-3, 4):
        for j in range(-3, 4):
            cell = (player_grid_x + i, player_grid_y + j)
            if cell in spawn_grid:
                potential_spawns.extend(spawn_grid[cell])
    
    if not potential_spawns: return

    current_zombie_count = len(game.zombies)
    if current_zombie_count >= core.data.config.MAX_ZOMBIES_GLOBAL: return

    SPAWN_ACTIVATION_RADIUS = 90 * TILE_SIZE 
    MIN_SPAWN_DISTANCE = 50 * TILE_SIZE

    entities_to_avoid = game.items_on_ground + game.zombies + [game.player]

    for spawn_pos in potential_spawns:
        if spawn_pos in triggered_spawns_for_layer: continue

        dist_to_player = math.hypot(player_pos[0] - spawn_pos[0], player_pos[1] - spawn_pos[1])
        
        # Spawn logic: Outside min view distance, inside activation radius
        if dist_to_player < SPAWN_ACTIVATION_RADIUS and dist_to_player > MIN_SPAWN_DISTANCE: 
            zombie_spawn_limit = max(0, core.data.config.MAX_ZOMBIES_GLOBAL - len(game.zombies))
            if zombie_spawn_limit == 0: break 

            triggered_spawns_for_layer.add(spawn_pos)
            
            # Passing cached_obstacle_grid and grid_size
            new_zombies = spawn_initial_zombies(
                game.obstacles, 
                [spawn_pos], 
                entities_to_avoid,
                zombie_spawn_limit, 
                spawns_per_marker=core.data.config.ZOMBIES_PER_SPAWN,
                map_width_px=game.map_width_pixels,
                map_height_px=game.map_height_pixels,
                obstacle_grid=getattr(game, 'cached_obstacle_grid', None),
                grid_size=grid_size
            )
            
            if new_zombies:
                game.zombies.extend(new_zombies)
                entities_to_avoid.extend(new_zombies) 
                game.layer_zombies[game.current_layer_index] = game.zombies[:]

def check_zombie_respawn(game):
    current_time = pygame.time.get_ticks()
    current_map = game.map_manager.current_map_filename
    
    zombie_spawns = game.current_zombie_spawns

    if not zombie_spawns:
        if current_map not in game.map_states:
            game.map_states[current_map] = {
                'items': game.items_on_ground, 
                'zombies': game.zombies, 
                'killed_zombies': [], 
                'picked_up_items': [],
                'last_respawn_time': current_time 
            }
        return

    if current_map not in game.map_states:
        print(f"Initial zombie spawn skipped. Dynamic spawner will handle it.")
        game.map_states[current_map] = {
            'items': game.items_on_ground, 
            'zombies': game.zombies, 
            'killed_zombies': [], 
            'picked_up_items': [],
            'last_respawn_time': current_time 
        }
        return 
    
    if core.data.config.ZOMBIE_RESPAWN_TIMER_MS <= 0: return

    if 'last_respawn_time' not in game.map_states[current_map]:
        game.map_states[current_map]['last_respawn_time'] = current_time

    last_respawn = game.map_states[current_map]['last_respawn_time']

    if current_time - last_respawn > core.data.config.ZOMBIE_RESPAWN_TIMER_MS:
        print(f"Respawn timer expired for {current_map}. Respawning zombies.")
        game.map_states[current_map]['last_respawn_time'] = current_time

def check_animal_respawn(game):
    current_time = pygame.time.get_ticks()
    current_map = game.map_manager.current_map_filename
    
    if current_map not in game.map_states:
        return

    if core.data.config.ANIMAL_RESPAWN_TIMER_MS <= 0: return
    
    if 'last_animal_respawn_time' not in game.map_states[current_map]:
        game.map_states[current_map]['last_animal_respawn_time'] = current_time

    last_respawn = game.map_states[current_map]['last_animal_respawn_time']

    if current_time - last_respawn > core.data.config.ANIMAL_RESPAWN_TIMER_MS:
        print(f"Respawn timer expired for animals on {current_map}.")
        game.map_states[current_map]['last_animal_respawn_time'] = current_time
        spawn_animals(game, count=core.data.config.ANIMAL_SPAWN_COUNT)