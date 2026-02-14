import os
import pygame
import random
import math

from core.data.config import *
import core.data.config
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.entities.zombie.zombie import Zombie
from core.entities.animal.animal import Animal # [NEW] Added import
from core.entities.player.player import Player
from core.placement import find_free_tile
from core.map.world_layers import check_for_layer_teleport
from core.map.spawn_manager import spawn_initial_zombies, spawn_animals # [NEW] Added spawn_animals import
from core.messages import display_message_zombie, display_message_player


def build_obstacle_grid(obstacles, grid_size):
    """
    Builds a static spatial grid for obstacles.
    This allows us to check only nearby walls instead of ALL walls.
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

def build_zombie_grid(zombies, grid_size):
    grid = {}
    for z in zombies:
        grid_x = int(z.rect.centerx // grid_size)
        grid_y = int(z.rect.centery // grid_size)
        cell = (grid_x, grid_y)
        if cell not in grid:
            grid[cell] = [z]
        else:
            grid[cell].append(z)
    return grid

def get_nearby_zombies(entity, grid, grid_size):
    nearby_zombies = []
    grid_x = int(entity.rect.centerx // grid_size)
    grid_y = int(entity.rect.centery // grid_size)
    for i in range(-1, 2):
        for j in range(-1, 2):
            cell = (grid_x + i, grid_y + j)
            if cell in grid:
                nearby_zombies.extend(grid[cell])
    return nearby_zombies

def create_blood_splatter(game, target_rect, damage, direction_vector=None):
    """
    Generates blood stain particles on the ground.
    """
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
    stain_size = 4 + int(damage / 6)
    
    for i in range(1, 7): 
        offset_pixels = (i / 6.0) * (TILE_SIZE * 0.75) + random.uniform(-2, 5)
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
    
    current_obstacle_count = len(game.obstacles)
    if not hasattr(game, 'cached_obstacle_grid') or getattr(game, 'cached_obstacle_count', -1) != current_obstacle_count:
        game.cached_obstacle_grid = build_obstacle_grid(game.obstacles, GRID_SIZE)
        game.cached_obstacle_count = current_obstacle_count

    nearby_player_obstacles = get_nearby_obstacles(game.player.rect, game.cached_obstacle_grid, GRID_SIZE)
    game.player.update_position(nearby_player_obstacles, game.zombies, game)

    game.hovered_interactable_tile_rect = None 
    facing_x, facing_y = game.get_player_facing_tile()
    target_tile = game.find_interactable_tile()
    if target_tile:
        tx, ty = target_tile
        game.hovered_interactable_tile_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    check_zombie_respawn(game)
    check_animal_respawn(game) # [NEW] Added check
    check_dynamic_zombie_spawns(game, GRID_SIZE)
    
    if game.player.update_stats(game):
        game.game_state = 'GAME_OVER'

    zombie_grid = build_zombie_grid(game.zombies, GRID_SIZE)
    
    projectiles_to_remove = []
    zombies_to_remove = []
    
    for p in game.projectiles:
        world_max_x = game.world_min_x + game.map_width_pixels
        world_max_y = game.world_min_y + game.map_height_pixels

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

        potential_hits = [z for z in get_nearby_zombies(p, zombie_grid, GRID_SIZE) if z not in zombies_to_remove]
        hit_zombie = next((z for z in potential_hits if p.rect.colliderect(z.rect)), None)

        if hit_zombie:
            owner = getattr(p, 'owner', None)

            if owner is None or owner == game.player:
                if player_hit_zombie(game.player, hit_zombie, game):
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
                    zombies_to_remove.append(hit_zombie)
                    handle_zombie_death(game, hit_zombie, game.items_on_ground, game.obstacles, None)
                    
                    game.splashes.append({
                        'pos': (hit_zombie.rect.centerx, hit_zombie.rect.bottom), 
                        'time': pygame.time.get_ticks(),
                        'duration': 600, 'radius': 5, 'type': 'death_burst'
                    })

            projectiles_to_remove.append(p)
        
        hit_npc = next((n for n in game.npcs if not n.is_dead and p.rect.colliderect(n.rect)), None)
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
                # NPC death cleanup happens in the main cleanup block below
             projectiles_to_remove.append(p)
             continue

    game.projectiles = [p for p in game.projectiles if p not in projectiles_to_remove]
    game.zombies = [z for z in game.zombies if z not in zombies_to_remove]
    

    Item.cleanup_disposables(
        game.items_on_ground, 
        game.modals, 
        lambda t: display_message_player(t) if game.player else None
    )

    # --- Zombie AI Update (OPTIMIZED) ---
    zombies_alive = game.zombies[:] 
    
    player_x, player_y = game.player.rect.centerx, game.player.rect.centery
    ACTIVE_RADIUS_SQ = (1500)**2 
    DESPAWN_RADIUS_SQ = (2500)**2

    zombies_to_remove = [] 

    for zombie in zombies_alive:
        
        dx = zombie.rect.centerx - player_x
        dy = zombie.rect.centery - player_y
        dist_sq = dx*dx + dy*dy
        
        if dist_sq > DESPAWN_RADIUS_SQ:
            zombies_to_remove.append(zombie)
            continue
        
        if dist_sq > ACTIVE_RADIUS_SQ:
            continue

        nearby_zombies = get_nearby_zombies(zombie, zombie_grid, GRID_SIZE)
        nearby_obstacles = get_nearby_obstacles(zombie.rect, game.cached_obstacle_grid, GRID_SIZE)

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

        distance_to_player = math.hypot(game.player.rect.centerx - zombie.rect.centerx, 
                                        game.player.rect.centery - zombie.rect.centery)

        if distance_to_player < zombie.attack_range: 
            current_time = pygame.time.get_ticks() 
            if current_time - zombie.last_attack_time > 500: 
                zombie.attack(game.player, game) 
                zombie.last_attack_time = current_time
        
    if zombies_to_remove:
        game.zombies = [z for z in game.zombies if z not in zombies_to_remove]
    
    # [NEW] NPC Update Loop
    if hasattr(game, 'npcs'):
        for npc in game.npcs:
            if not npc.is_dead:
                npc.update(game)

    now_ms = pygame.time.get_ticks()
    for ground_item in list(game.items_on_ground):
        if isinstance(ground_item, Corpse): 
            if ground_item.is_expired(now_ms):
                display_message_zombie(f"{getattr(ground_item,'name','Corpse')} decayed.")
                try: game.items_on_ground.remove(ground_item)
                except ValueError: pass

    for modal in list(game.modals):
        if modal['type'] == 'container':
            container_item = modal['item']
            if container_item and hasattr(container_item, 'rect') and (container_item in game.items_on_ground):
                distance = math.hypot(game.player.rect.centerx - container_item.rect.centerx, game.player.rect.centery - container_item.rect.centery)
                if distance > TILE_SIZE * 1.5:
                    game.modals.remove(modal)
    
    current_time = pygame.time.get_ticks()
    game.splashes = [s for s in game.splashes if current_time - s['time'] < s['duration']]

    if hasattr(game, 'blood_stains'):
        game.blood_stains = [s for s in game.blood_stains if current_time - s['time'] < s['duration']]

    # --- Vehicle Update ---
    if game.map_manager and hasattr(game.map_manager, 'vehicles'):
        roadkill_zombies = []
        
        for vehicle in game.map_manager.vehicles:
            vehicle.update()
            
            # Detected entities logic
            detected_entities = []
            
            # 1. Grab any hits detected by move() (Useful for non-player driven vehicles or edge cases)
            if hasattr(vehicle, 'hit_entities') and vehicle.hit_entities:
                detected_entities.extend(vehicle.hit_entities)
                vehicle.hit_entities = []

            # 2. Manual Check vs Zombies
            nearby_zombies = get_nearby_zombies(vehicle, zombie_grid, GRID_SIZE)
            for z in nearby_zombies:
                if z not in detected_entities and vehicle.rect.colliderect(z.rect):
                    detected_entities.append(z)
            
            # 3. Manual Check vs NPCs
            if hasattr(game, 'npcs'):
                for npc in game.npcs:
                    if not npc.is_dead and npc not in detected_entities and vehicle.rect.colliderect(npc.rect):
                        detected_entities.append(npc)

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
                        create_blood_splatter(game, entity.rect, impact_damage, velocity_dir)

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
        
        # [FIX] Robust cleanup for ALL dead NPCs (from vehicle or player)
        if hasattr(game, 'npcs'):
            if hasattr(game.npcs, 'sprites'):
                # It's a SpriteGroup
                for n in list(game.npcs):
                    if n.is_dead:
                        n.kill() # Correct way to remove from Group
            else:
                # It's a List
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

    if is_ranged and knockback_force > 0:
        zombie.knockback_velocity = [projectile_dir[0] * knockback_force, projectile_dir[1] * knockback_force]
        zombie.knockback_timer = 400 
        
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

# ... [Keep handle_zombie_death, check_dynamic_zombie_spawns, check_zombie_respawn functions] ...
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