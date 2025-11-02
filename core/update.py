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
    
    if game.player.update_stats():
        game.game_state = 'GAME_OVER'

    # --- Projectile update logic
    projectiles_to_remove = []
    zombies_to_remove = []
    for p in game.projectiles:
        if p.update() or any(p.rect.colliderect(ob) for ob in game.obstacles):
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


    zombies_alive = game.zombies[:]
    for zombie in zombies_alive:

        # 1. Call the new AI function. This function ALSO handles movement.
        zombie.update_ai(game.player.rect, game.obstacles, game.zombies)

        # 2. Handle attack logic (checks distance AFTER AI movement)
        distance_to_player = math.hypot(game.player.rect.centerx - zombie.rect.centerx,
                                        game.player.rect.centery - zombie.rect.centery)
        if distance_to_player < zombie.attack_range:
            current_time = pygame.time.get_ticks()
            if current_time - zombie.last_attack_time > 500: # 500ms cooldown
                zombie.attack(game.player)
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
        if 'Gun' in active_weapon.name: # Ranged
            if random.random() < progression.get_headshot_chance():
                is_headshot = True
                damage_multiplier = 2.0
        else: # Melee
            damage_multiplier = progression.get_melee_damage_multiplier()
            durability_loss = progression.get_weapon_durability_loss()
            if active_weapon.durability is not None and active_weapon.durability > 0:
                active_weapon.durability -= durability_loss
                if active_weapon.durability <= 0:
                    print(f"{active_weapon.name} broke!")
                    player.destroy_broken_weapon(active_weapon)
    else: # Unarmed
        base_damage = progression.get_unarmed_damage()

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
    dead_sprite_path = "game/sprites/zombie/dead.png"
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

def check_zombie_respawn(game):
    """Checks if the respawn timer has elapsed for the current map and spawns zombies."""
    if ZOMBIE_RESPAWN_TIMER_MS <= 0: # Timer is disabled in config
        return

    current_time = pygame.time.get_ticks()
    current_map = game.map_manager.current_map_filename
    
    # Ensure map state exists, initializing if it's the first time.
    if current_map not in game.map_states:
        game.map_states[current_map] = {
            'items': game.items_on_ground, 
            'zombies': game.zombies, 
            'killed_zombies': [], 
            'picked_up_items': [],
            'last_respawn_time': current_time # Initialize timer
        }
        return

    # Check if timer has been initialized for this map (for older save states)
    if 'last_respawn_time' not in game.map_states[current_map]:
        game.map_states[current_map]['last_respawn_time'] = current_time
        return

    last_respawn = game.map_states[current_map]['last_respawn_time']

    if current_time - last_respawn > ZOMBIE_RESPAWN_TIMER_MS:
        print(f"Respawn timer expired for {current_map}. Respawning zombies.")
        
        # Re-extract zombie spawn points from the current layer's spawn data
        zombie_spawns = []
        if hasattr(game, 'spawn_data'):
            for y, row in enumerate(game.spawn_data):
                for x, char in enumerate(row):
                    if char == 'Z':
                        zombie_spawns.append((x * TILE_SIZE, y * TILE_SIZE))
        
        if not zombie_spawns:
            print("No 'Z' spawn points found for this layer. Cannot respawn.")
            game.map_states[current_map]['last_respawn_time'] = current_time # Reset timer anyway
            return

        # Get all entities to avoid spawning on top of them
        all_current_entities = game.items_on_ground + game.zombies
        
        # Spawn new zombies
        new_zombies = spawn_initial_zombies(game.obstacles, zombie_spawns, all_current_entities)
        
        game.zombies.extend(new_zombies)
        game.layer_zombies[current_map] = game.zombies[:] # Update the saved layer state
        
        print(f"Spawned {len(new_zombies)} new zombies. Total: {len(game.zombies)}")
        
        # Reset the timer
        game.map_states[current_map]['last_respawn_time'] = current_time