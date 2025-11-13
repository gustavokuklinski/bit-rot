import os
import pygame
import random
import math

from data.config import *
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.entities.zombie.zombie import Zombie
from core.entities.player.player import Player
from core.placement import find_free_tile
from core.map.world_layers import check_for_layer_teleport
from core.map.spawn_manager import spawn_initial_zombies


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


def get_nearby_zombies(zombie, grid, grid_size):
    """Gets all zombies from the 9-cell area around a given zombie."""
    nearby_zombies = []
    grid_x = int(zombie.rect.centerx // grid_size)
    grid_y = int(zombie.rect.centery // grid_size)
    
    # Loop through the 3x3 grid centered on the zombie
    for i in range(-1, 2):
        for j in range(-1, 2):
            cell = (grid_x + i, grid_y + j)
            if cell in grid:
                nearby_zombies.extend(grid[cell])
                
    return nearby_zombies


def update_game_state(game):
    game.player.update_position(game.obstacles, game.zombies)

    check_for_layer_teleport(game)


    game.hovered_interactable_tile_rect = None # Reset
    facing_x, facing_y = game.get_player_facing_tile()
    if facing_x is not None:
        tile_def = game.map_manager.get_tile_at(facing_x, facing_y)
        if tile_def and tile_def.get('is_statable'):
            game.hovered_interactable_tile_rect = pygame.Rect(facing_x * TILE_SIZE, facing_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)


    check_zombie_respawn(game)
    check_dynamic_zombie_spawns(game)
    if game.player.update_stats(game):
        game.game_state = 'GAME_OVER'

    # --- Projectile update logic
    projectiles_to_remove = []
    zombies_to_remove = []
    for p in game.projectiles:
        if p.update(game.map_width_pixels, game.map_height_pixels) or any(p.rect.colliderect(ob) for ob in game.obstacles):
        #if p.update() or any(p.rect.colliderect(ob) for ob in game.obstacles):
            projectiles_to_remove.append(p)
            continue

        hit_zombie = next((z for z in game.zombies if z not in zombies_to_remove and p.rect.colliderect(z.rect)), None)

        if hit_zombie:
            if player_hit_zombie(game.player, hit_zombie):
                zombies_to_remove.append(hit_zombie)
                handle_zombie_death(game, hit_zombie, game.items_on_ground, game.obstacles, game.player.active_weapon)
                game.zombies_killed += 1
            projectiles_to_remove.append(p)

    game.projectiles = [p for p in game.projectiles if p not in projectiles_to_remove]
    game.zombies = [z for z in game.zombies if z not in zombies_to_remove]

    # TILE_SIZE * 3 = 48 * 3 = 144. Let's use 128.
    GRID_SIZE = 128 
    
    # 1. Build the spatial grid *once* per frame
    zombie_grid = build_zombie_grid(game.zombies, GRID_SIZE)

    zombies_alive = game.zombies[:] # 
    for zombie in zombies_alive:

        # 2. Get *only* the zombies in the 9-cell area around this zombie
        nearby_zombies = get_nearby_zombies(zombie, zombie_grid, GRID_SIZE)
        
        # 3. Call the AI function, passing the *small list*
        # This is the N*9 check (O(N)), which is much, much faster.
        zombie.update_ai(game.player.rect, game.obstacles, nearby_zombies) # 

        # 4. Handle attack logic (This is fine, no changes)
        distance_to_player = math.hypot(game.player.rect.centerx - zombie.rect.centerx, # 
                                        game.player.rect.centery - zombie.rect.centery) # 
        if distance_to_player < zombie.attack_range: # 
            current_time = pygame.time.get_ticks() # 
            if current_time - zombie.last_attack_time > 500: # 500ms cooldown # 
                zombie.attack(game.player, game) # 
                zombie.last_attack_time = current_time



    now_ms = pygame.time.get_ticks()
    for ground_item in list(game.items_on_ground):
        if isinstance(ground_item, Corpse): # Check specifically for Corpse objects
            if ground_item.is_expired(now_ms):
                print(f"{getattr(ground_item,'name','Corpse')} decayed.")
                try:
                    # Optional: Spill items before removing corpse
                    # ground_item.spill_contents_to_ground(game.items_on_ground)
                    game.items_on_ground.remove(ground_item)
                except ValueError:
                    pass # Already removed, ignore

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
                    print(f"Closed {container_item.name} because you moved away.")

def player_hit_zombie(player, zombie):
    progression = player.progression
    active_weapon = player.active_weapon
    
    base_damage = 1
    damage_multiplier = 1.0
    is_headshot = False

    if active_weapon:
        base_damage = active_weapon.damage
        if active_weapon.item_type == 'weapon_ranged': # Ranged
            damage_multiplier = progression.get_ranged_damage_multiplier(player)
            if random.random() < progression.get_headshot_chance():
                is_headshot = True
                damage_multiplier *= 2.0 # Headshot bonus stacks
        else: # Melee
            damage_multiplier = progression.get_melee_damage_multiplier(player)
            durability_loss = progression.get_weapon_durability_loss()
            if active_weapon.durability is not None and active_weapon.durability > 0:
                active_weapon.durability -= durability_loss
                if active_weapon.durability <= 0:
                    print(f"{active_weapon.name} broke!")
                    player.destroy_broken_weapon(active_weapon)
    else: # Unarmed
        base_damage = progression.get_unarmed_damage(player)

    final_damage = base_damage * damage_multiplier

    if zombie.take_damage(final_damage):
        return True

    hit_type = "Headshot" if is_headshot else "Hit"
    print(f"{hit_type}! Dealt {final_damage:.1f} damage.")
    return False

def handle_zombie_death(game, zombie, items_on_ground_list, obstacles, weapon):
    """Processes loot drops when a zombie dies."""
    print(f"A {zombie.name} died. Creating corpse and checking for loot...")
    # create corpse at zombie position
    dead_sprite_path = "./game/resources/sprites/zombie/dead.png"
    corpse = Corpse(name="Dead corpse", capacity=10, image_path=dead_sprite_path, pos=zombie.rect.center)
    # build its inventory from the zombie loot table
    if hasattr(zombie, 'loot_table'):
        for drop in zombie.loot_table:
            if random.random() < drop.get('chance', 0) * (ZOMBIE_DROP / 100.0):
                item_inst = Item.create_from_name(drop.get('item'))
                if item_inst:
                    corpse.inventory.append(item_inst)
                else:
                    print(f"Failed to create item: {drop.get('item')}")
    # append corpse to world items (it behaves like an item on ground)
    if find_free_tile(corpse.rect, obstacles, items_on_ground_list, initial_pos=zombie.rect.topleft):
        items_on_ground_list.append(corpse)

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
    if current_zombie_count >= MAX_ZOMBIES_GLOBAL:
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
        if dist_to_player < ZOMBIE_DETECTION_RADIUS * 1.5: 
        #if dist_to_player < (TILE_SIZE * 20):
            zombie_spawn_limit = max(0, MAX_ZOMBIES_GLOBAL - len(game.zombies))
            
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
                spawns_per_marker=ZOMBIES_PER_SPAWN # Tell it how many to spawn at this marker
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
    if ZOMBIE_RESPAWN_TIMER_MS <= 0:
        return # This now correctly skips *only* respawning

    # Check if timer has been initialized (for older save states)
    if 'last_respawn_time' not in game.map_states[current_map]:
        game.map_states[current_map]['last_respawn_time'] = current_time

    last_respawn = game.map_states[current_map]['last_respawn_time']

    # Check if respawn timer has elapsed
    if current_time - last_respawn > ZOMBIE_RESPAWN_TIMER_MS:
        print(f"Respawn timer expired for {current_map}. Respawning zombies.")
        
        
        # Reset the timer
        game.map_states[current_map]['last_respawn_time'] = current_time