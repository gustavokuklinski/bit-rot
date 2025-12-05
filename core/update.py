import os
import pygame
import random
import math

from core.data.config import *
import core.data.config
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.entities.zombie.zombie import Zombie
from core.entities.player.player import Player
from core.placement import find_free_tile
from core.map.world_layers import check_for_layer_teleport
from core.map.spawn_manager import spawn_initial_zombies
from core.messages import display_message_zombie, display_message_player

def build_obstacle_grid(obstacles, grid_size):
    """
    Builds a static spatial grid for obstacles.
    This allows us to check only nearby walls instead of ALL walls.
    """
    grid = {}
    for ob in obstacles:
        # Determine which grid cell the obstacle belongs to
        # (Using center is safe because obstacles are usually 32x32 and grid is 128x128)
        grid_x = int(ob.centerx // grid_size)
        grid_y = int(ob.centery // grid_size)
        cell = (grid_x, grid_y)
        
        if cell not in grid:
            grid[cell] = [ob]
        else:
            grid[cell].append(ob)
    return grid

def get_nearby_obstacles(entity_rect, grid, grid_size):
    """
    Retrieves obstacles from the 9 grid cells surrounding the entity.
    """
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
    """Sorts all zombies into a spatial grid (dictionary)."""
    grid = {}
    for z in zombies:
        # Get the grid cell coordinates for the zombie's center
        grid_x = int(z.rect.centerx // grid_size)
        grid_y = int(z.rect.centery // grid_size)
        cell = (grid_x, grid_y)
        
        # Add the zombie to the list for that cell
        if cell not in grid:
            grid[cell] = [z]
        else:
            grid[cell].append(z)
    return grid


def get_nearby_zombies(entity, grid, grid_size):
    """Gets all zombies from the 9-cell area around a given entity (player, projectile, vehicle)."""
    nearby_zombies = []
    # Use the entity's bounding box center for grid lookup
    grid_x = int(entity.rect.centerx // grid_size)
    grid_y = int(entity.rect.centery // grid_size)
    
    # Loop through the 3x3 grid centered on the entity
    for i in range(-1, 2):
        for j in range(-1, 2):
            cell = (grid_x + i, grid_y + j)
            if cell in grid:
                nearby_zombies.extend(grid[cell])
                
    return nearby_zombies


def update_game_state(game):
    # Consolidate spatial grid initialization at the start.
    GRID_SIZE = 128
    
    # --- 1. Obstacle Grid (Cache check) ---
    current_obstacle_count = len(game.obstacles)
    if not hasattr(game, 'cached_obstacle_grid') or getattr(game, 'cached_obstacle_count', -1) != current_obstacle_count:
        game.cached_obstacle_grid = build_obstacle_grid(game.obstacles, GRID_SIZE)
        game.cached_obstacle_count = current_obstacle_count

    # 1.1 Update player movement using ONLY nearby obstacles
    nearby_player_obstacles = get_nearby_obstacles(game.player.rect, game.cached_obstacle_grid, GRID_SIZE)
    game.player.update_position(nearby_player_obstacles, game.zombies, game)

    check_for_layer_teleport(game)
    

    game.hovered_interactable_tile_rect = None # Reset
    facing_x, facing_y = game.get_player_facing_tile()
    target_tile = game.find_interactable_tile()
    if target_tile:
        tx, ty = target_tile
        game.hovered_interactable_tile_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    check_zombie_respawn(game)
    check_dynamic_zombie_spawns(game)
    if game.player.update_stats(game):
        game.game_state = 'GAME_OVER'

    # --- 2. Build Zombie Grid (Must rebuild every frame as zombies move) ---
    # This must be done *before* the projectile loop to support optimized projectile-zombie collision.
    zombie_grid = build_zombie_grid(game.zombies, GRID_SIZE)
    
    # --- Projectile update logic (Optimized for collision checks) ---
    projectiles_to_remove = []
    zombies_to_remove = []
    
    for p in game.projectiles:
        world_max_x = game.world_min_x + game.map_width_pixels
        world_max_y = game.world_min_y + game.map_height_pixels

        # 2.1. Fetch only nearby obstacles for collision check
        local_obstacles = get_nearby_obstacles(p.rect, game.cached_obstacle_grid, GRID_SIZE)

        # 2.2. Update projectile and check collisions against LOCAL obstacles only
        if p.update(game.world_min_x, game.world_min_y, world_max_x, world_max_y) or any(p.rect.colliderect(ob) for ob in local_obstacles):
            projectiles_to_remove.append(p)
            continue

        # 2.3. ⭐️ OPTIMIZATION: Check collisions against ONLY nearby zombies using the grid
        potential_hits = [z for z in get_nearby_zombies(p, zombie_grid, GRID_SIZE) if z not in zombies_to_remove]
        
        hit_zombie = next((z for z in potential_hits if p.rect.colliderect(z.rect)), None)

        if hit_zombie:
            if player_hit_zombie(game.player, hit_zombie, game):
                zombies_to_remove.append(hit_zombie)
                handle_zombie_death(game, hit_zombie, game.items_on_ground, game.obstacles, game.player.active_weapon)
                game.zombies_killed += 1
            projectiles_to_remove.append(p)

    game.projectiles = [p for p in game.projectiles if p not in projectiles_to_remove]
    game.zombies = [z for z in game.zombies if z not in zombies_to_remove]
    
    # --- Zombie AI Update (Already optimized) ---
    zombies_alive = game.zombies[:] 
    for zombie in zombies_alive:

        # 3.1. Get nearby zombies (already optimized)
        nearby_zombies = get_nearby_zombies(zombie, zombie_grid, GRID_SIZE)
        
        # 3.2. Get nearby obstacles (already optimized)
        nearby_obstacles = get_nearby_obstacles(zombie.rect, game.cached_obstacle_grid, GRID_SIZE)
        
        # 3.3. Call AI with reduced lists
        zombie.update_ai(game.player.rect, nearby_obstacles, nearby_zombies, game) 

        # 4. Handle attack logic
        distance_to_player = math.hypot(game.player.rect.centerx - zombie.rect.centerx, 
                                        game.player.rect.centery - zombie.rect.centery) 
        if distance_to_player < zombie.attack_range: 
            current_time = pygame.time.get_ticks() 
            if current_time - zombie.last_attack_time > 500: 
                zombie.attack(game.player, game) 
                zombie.last_attack_time = current_time

    now_ms = pygame.time.get_ticks()
    for ground_item in list(game.items_on_ground):
        if isinstance(ground_item, Corpse): 
            if ground_item.is_expired(now_ms):
                display_message_zombie(f"{getattr(ground_item,'name','Corpse')} decayed.")
                try:
                    game.items_on_ground.remove(ground_item)
                except ValueError:
                    pass

    # Auto-close container modals if player is too far
    for modal in list(game.modals):
        if modal['type'] == 'container':
            container_item = modal['item']
            

            # Only run the distance check if the container_item is an item
            # that is physically on the ground (like a corpse).
            # Worn backpacks or backpacks opened from inventory should not be checked.
            if container_item and hasattr(container_item, 'rect') and (container_item in game.items_on_ground):
                distance = math.hypot(game.player.rect.centerx - container_item.rect.centerx, game.player.rect.centery - container_item.rect.centery)
                if distance > TILE_SIZE * 1.5:
                    game.modals.remove(modal)
                    display_message_player(f"Closed {container_item.name} because you moved away.")
    
    # --- Vehicle Update and Roadkill Logic (Optimized for collision checks) ---
    if game.map_manager and hasattr(game.map_manager, 'vehicles'):
        roadkill_zombies = []
        
        for vehicle in game.map_manager.vehicles:
            vehicle.update()
            
            # Only check for collisions if the engine is on (active)
            if vehicle.active:
                # Calculate speed from velocity vector
                speed = math.hypot(vehicle.velocity[0], vehicle.velocity[1])
                
                # Threshold: Only damage if moving fast enough (e.g., > 2.0 pixels/frame)
                if speed > 2.0:
                    # ⭐️ OPTIMIZATION: Check collisions against ONLY nearby zombies
                    nearby_zombies_for_vehicle = [z for z in get_nearby_zombies(vehicle, zombie_grid, GRID_SIZE) if z not in zombies_to_remove]
                    
                    # Find zombies colliding with this vehicle among the nearby ones
                    hit_list = [z for z in nearby_zombies_for_vehicle if vehicle.rect.colliderect(z.rect)]
                    
                    for zombie in hit_list:
                        if zombie in roadkill_zombies: continue

                        # 1. Damage the Zombie (Roadkill)
                        # Damage scales with speed (e.g., speed 5.0 * 5 = 25 damage)
                        impact_damage = speed * 5.0 
                        
                        if zombie.take_damage(impact_damage, game):
                            # Zombie died
                            roadkill_zombies.append(zombie)
                            handle_zombie_death(game, zombie, game.items_on_ground, game.obstacles, None)
                            game.zombies_killed += 1
                            display_message_player(f"Roadkill! {zombie.name} squashed for {impact_damage:.1f} damage.")
                        else:
                             # Zombie survived but was hit
                             # Optional: push zombie away to prevent getting stuck inside car
                             pass

                        # 2. Damage the Vehicle Motor
                        # Fixed damage per hit (e.g., 2.0 points of durability/load)
                        vehicle.damage_motor(2.0)
                        
                        # Optional: Slow car down slightly on impact
                        vehicle.velocity[0] *= 0.8
                        vehicle.velocity[1] *= 0.8

        # Clean up roadkilled zombies
        if roadkill_zombies:
            game.zombies = [z for z in game.zombies if z not in roadkill_zombies and z not in zombies_to_remove]
    
    # Final cleanup (merging projectile deaths and roadkills if needed, 
    # though the list comprehension above handles roadkills separately)
    game.zombies = [z for z in game.zombies if z not in zombies_to_remove]

def player_hit_zombie(player, zombie, game):
    progression = player.progression
    active_weapon = player.active_weapon
    
    base_damage = 1
    damage_multiplier = 1.0
    is_headshot = False

    if active_weapon:
        base_damage = active_weapon.damage
        if active_weapon.item_type == 'weapon_ranged': # Ranged
            damage_multiplier = progression.get_ranged_damage_multiplier(player)
            if random.random() < progression.get_headshot_chance(player):
                is_headshot = True
                damage_multiplier *= 2.0 # Headshot bonus stacks
        else: # Melee
            damage_multiplier = progression.get_melee_damage_multiplier(player)
            durability_loss = progression.get_weapon_durability_loss(player)
            if active_weapon.durability is not None and active_weapon.durability > 0:
                active_weapon.durability -= durability_loss
                if active_weapon.durability <= 0:
                    display_message_player(f"{active_weapon.name} broke!")
                    player.progression._add_xp(player, player.progression.maintenance, 'maintenance', 50)
                    player.destroy_broken_weapon(active_weapon)
    else: # Unarmed
        base_damage = progression.get_unarmed_damage(player)

    final_damage = base_damage * damage_multiplier

    if zombie.take_damage(final_damage, game):
        return True

    hit_type = "Headshot" if is_headshot else "Hit"
    display_message_player(f"{hit_type}! Dealt {final_damage:.1f} damage.")
    return False

def handle_zombie_death(game, zombie, items_on_ground_list, obstacles, weapon):
    """Processes loot drops when a zombie dies."""
    display_message_zombie(f"A {zombie.name} died. Creating corpse and checking for loot...")
    # create corpse at zombie position
    dead_sprite_path = "./game/lib/sprites/zombie/dead.png"
    corpse = Corpse(name="Dead corpse", capacity=10, image_path=dead_sprite_path, pos=zombie.rect.center)
    
    if hasattr(zombie, 'inventory'):
        for item in zombie.inventory:
            corpse.inventory.append(item)

    # build its inventory from the zombie loot table
    if hasattr(zombie, 'loot_table'):
        for drop in zombie.loot_table:
            if random.random() < drop.get('chance', 0) * (core.data.config.ZOMBIE_DROP / 100.0):
                item_inst = Item.create_from_name(drop.get('item'))
                if item_inst:
                    corpse.inventory.append(item_inst)
                else:
                    print(f"Failed to create item: {drop.get('item')}")
    # append corpse to world items (it behaves like an item on ground)
    if find_free_tile(corpse.rect, obstacles, items_on_ground_list, initial_pos=zombie.rect.topleft):
        items_on_ground_list.append(corpse)

    if zombie.sound_dead:
        game.sound_manager.play_sound(zombie.sound_dead, subdir='zombie', game=game, source_pos=zombie.rect.center)

    game.player.process_kill(weapon, zombie)

    # Record killed zombie in map state
    current_map_filename = game.map_manager.current_map_filename
    if current_map_filename not in game.map_states:
        game.map_states[current_map_filename] = {'items': [], 'zombies': [], 'killed_zombies': [], 'picked_up_items': [], 'last_respawn_time': pygame.time.get_ticks()} # Ensure lists exist
    game.map_states[current_map_filename].setdefault('killed_zombies', []).append(zombie.id) # Use setdefault

def check_dynamic_zombie_spawns(game):
    """
    Checks for untriggered 'Z' spawn markers near the player and spawns zombies.
    """
    triggered_spawns_for_layer = game.layer_spawn_triggers.get(game.current_layer_index)
    if triggered_spawns_for_layer is None:
        # Failsafe: if set_active_layer didn't run, create the set.
        game.layer_spawn_triggers[game.current_layer_index] = set()
        triggered_spawns_for_layer = game.layer_spawn_triggers[game.current_layer_index]


    player_pos = game.player.rect.center
    GRID_SIZE_SPAWNS = getattr(game, 'SPAWN_GRID_SIZE', 512)
    player_grid_x = int(player_pos[0] // GRID_SIZE_SPAWNS)
    player_grid_y = int(player_pos[1] // GRID_SIZE_SPAWNS)
    spawn_grid = getattr(game, 'spawn_point_grid', {})

    potential_spawns = []
    for i in range(-1, 2):
        for j in range(-1, 2):
            cell = (player_grid_x + i, player_grid_y + j)
            if cell in spawn_grid:
                potential_spawns.extend(spawn_grid[cell])
    
    if not potential_spawns:
        return

   
    # Check for global zombie limit
    current_zombie_count = len(game.zombies)
    if current_zombie_count >= core.data.config.MAX_ZOMBIES_GLOBAL:
        return # Global limit reached, don't spawn more.

    # Combine all entities that a new zombie cannot spawn on top of
    entities_to_avoid = game.items_on_ground + game.zombies + [game.player]

    for spawn_pos in potential_spawns:
        # spawn_pos is an (x, y) tuple (pixel coordinates)
        # print(f"Checking potential spawn at: {spawn_pos}")
        if spawn_pos in triggered_spawns_for_layer:
            continue # Already spawned from this marker

        dist_to_player = math.hypot(player_pos[0] - spawn_pos[0], player_pos[1] - spawn_pos[1])
        
        # Use ZOMBIE_DETECTION_RADIUS as the trigger distance (with a small buffer)
        if dist_to_player < core.data.config.ZOMBIE_DETECTION_RADIUS * 1.5: 

            zombie_spawn_limit = max(0, core.data.config.MAX_ZOMBIES_GLOBAL - len(game.zombies))
            
            if zombie_spawn_limit == 0:
                print("Global zombie limit reached during dynamic spawn.")
                break # Stop spawning this frame

            print(f"Player near spawn marker at {spawn_pos}. Spawning zombie.")
            triggered_spawns_for_layer.add(spawn_pos)
            
            # This was the bug. We pass the *remaining global limit* to the spawner.
            # The spawner will correctly spawn *up to* ZOMBIES_PER_SPAWN
            # without exceeding the global limit.
            new_zombies = spawn_initial_zombies(
                game.obstacles, 
                [spawn_pos], # Only spawn at this one 'Z' marker
                entities_to_avoid,
                zombie_spawn_limit, # Pass the remaining global limit
                spawns_per_marker=core.data.config.ZOMBIES_PER_SPAWN,  # Tell it how many to spawn at this marker
                map_width_px=game.map_width_pixels,
                map_height_px=game.map_height_pixels
            )
            
            if new_zombies:
                game.zombies.extend(new_zombies)
                entities_to_avoid.extend(new_zombies) 
                game.layer_zombies[game.current_layer_index] = game.zombies[:]
                
            
               

def check_zombie_respawn(game):
    """
    Handles BOTH initial zombie spawn and respawning.
    - If timer is 0, it will only do the initial spawn (once per map).
    - If timer > 0, it will do the initial spawn AND respawn on the timer.
    """
    current_time = pygame.time.get_ticks()
    current_map = game.map_manager.current_map_filename
    
    zombie_spawns = game.current_zombie_spawns

    if not zombie_spawns:
        # No 'Z' markers on this map layer, nothing to do.
        # We still need to initialize map_states to prevent this from running again.
        if current_map not in game.map_states:
            game.map_states[current_map] = {
                'items': game.items_on_ground, 
                'zombies': game.zombies, # game.zombies is []
                'killed_zombies': [], 
                'picked_up_items': [],
                'last_respawn_time': current_time 
            }
        return

    # --- Check for INITIAL Spawn ---
    # If this is the first time visiting this map, map_states won't exist.
    if current_map not in game.map_states:
        print(f"First visit to {current_map}. Performing initial zombie spawn.")


        print(f"Initial zombie spawn skipped. Dynamic spawner will handle it.")
        # Initialize map state *after* spawning
        game.map_states[current_map] = {
            'items': game.items_on_ground, 
            'zombies': game.zombies, # Save the *newly spawned* zombies
            'killed_zombies': [], 
            'picked_up_items': [],
            'last_respawn_time': current_time # Initialize timer
        }
        return 
    
    # If timer is disabled, do not respawn.
    if core.data.config.ZOMBIE_RESPAWN_TIMER_MS <= 0:
        return # This now correctly skips *only* respawning

    # Check if timer has been initialized (for older save states)
    if 'last_respawn_time' not in game.map_states[current_map]:
        game.map_states[current_map]['last_respawn_time'] = current_time

    last_respawn = game.map_states[current_map]['last_respawn_time']

    # Check if respawn timer has elapsed
    if current_time - last_respawn > core.data.config.ZOMBIE_RESPAWN_TIMER_MS:
        print(f"Respawn timer expired for {current_map}. Respawning zombies.")
        
        
        # Reset the timer
        game.map_states[current_map]['last_respawn_time'] = current_time