import os
import pygame
import random
import math

from data.config import *
from core.entities.item import Item
from core.entities.corpse import Corpse
from core.entities.zombie import Zombie
from core.placement import find_free_tile

def update_game_state(game):
    game.player.update_position(game.obstacles, game.zombies)
    if game.player.update_stats():
        game.game_state = 'GAME_OVER'
    
    projectiles_to_remove = []
    zombies_to_remove = []
    for p in game.projectiles:
        if p.update() or any(p.rect.colliderect(ob) for ob in game.obstacles):
            projectiles_to_remove.append(p)
            continue
        hit_zombie = next((z for z in game.zombies if p.rect.colliderect(z.rect)), None)
        if hit_zombie:
            if player_hit_zombie(game.player, hit_zombie):
                zombies_to_remove.append(hit_zombie)
                handle_zombie_death(game.player, hit_zombie, game.items_on_ground, game.obstacles)
                game.zombies_killed += 1
            projectiles_to_remove.append(p)
    game.projectiles = [p for p in game.projectiles if p not in projectiles_to_remove]
    game.zombies = [z for z in game.zombies if z not in zombies_to_remove]

    for zombie in game.zombies:
        zombie.move_towards(game.player.rect, game.obstacles, game.zombies)
        # Zombie attack logic
        distance_to_player = math.hypot(game.player.rect.centerx - zombie.rect.centerx, game.player.rect.centery - zombie.rect.centery)
        if distance_to_player < zombie.attack_range:
            # Implement a simple cooldown for zombie attacks
            current_time = pygame.time.get_ticks() # Get milliseconds since pygame.init()
            if current_time - zombie.last_attack_time > 500: # 500ms cooldown
                zombie.attack(game.player)
                zombie.last_attack_time = current_time
    
    if random.random() < 0.005 and len(game.zombies) < 10:
        game.zombies.append(Zombie.create_random(random.choice([0, GAME_WIDTH]), random.choice([0, GAME_HEIGHT])))

    # remove expired corpses (160 seconds = 160000 ms)
    now_ms = pygame.time.get_ticks()
    for ground_item in list(game.items_on_ground):
        if getattr(ground_item, 'spawn_time', None) is not None:
            if now_ms - ground_item.spawn_time > 160000:
                print(f"{getattr(ground_item,'name','Corpse')} decayed.")
                try:
                    game.items_on_ground.remove(ground_item)
                except ValueError:
                    pass

    # Auto-close container modals if player is too far
    for modal in list(game.modals):
        if modal['type'] == 'container':
            container_item = modal['item']
            if container_item in game.items_on_ground:
                distance = math.hypot(game.player.rect.centerx - container_item.rect.centerx, game.player.rect.centery - container_item.rect.centery)
                if distance > TILE_SIZE * 1.5:
                    game.modals.remove(modal)
                    print(f"Closed {container_item.name} because you moved away.")

def player_hit_zombie(player, zombie):
    """Calculates damage and processes the hit."""
    
    active_weapon = player.active_weapon
    base_damage = 1 # Unarmed base damage
    weapon_durability_loss = 0
    
    if active_weapon:
        base_damage = active_weapon.damage
        if active_weapon.item_type in ['weapon', 'tool']:
            if random.randint(0, 10) < player.skill_melee:
                weapon_durability_loss = 0.5
            else:
                weapon_durability_loss = 2.0
    else: # Unarmed
        base_damage = 1 + (player.skill_strength * 0.1)

    # RANGED WEAPON DURABILITY CHECK handled in shooting code

    # MELEE WEAPON DURABILITY CHECK
    if active_weapon and 'Gun' not in active_weapon.name:
        if active_weapon.durability is not None and active_weapon.durability > 0:
            active_weapon.durability -= weapon_durability_loss
            if active_weapon.durability <= 0:
                player.active_weapon = None
                # IMPORTANT: If the broken item was in the belt, also remove it from the belt
                for i, item in enumerate(player.belt):
                    if item == active_weapon:
                        player.belt[i] = None
                        break
                print(f"{active_weapon.name} broke! Unequipped and removed from belt/inventory.")


    is_headshot = False
    damage_multiplier = 1.0
    if active_weapon and 'Gun' in active_weapon.name:
        headshot_chance = 0.1 + (player.skill_ranged * 0.04) 
        if random.random() < headshot_chance:
            is_headshot = True
            damage_multiplier = 2.0
            
    # Apply melee skill multiplier for melee attacks
    if not (active_weapon and 'Gun' in active_weapon.name):
        damage_multiplier *= (1 + player.skill_melee * 0.1)
    final_damage = (base_damage * damage_multiplier)
    
    if zombie.take_damage(final_damage):
        return True 
    
    hit_type = "Headshot" if is_headshot else "Hit"
    print(f"{hit_type}! Dealt {final_damage:.1f} damage.")
    return False 

def handle_zombie_death(player, zombie, items_on_ground_list, obstacles):
    """Processes loot drops when a zombie dies."""
    print(f"A {zombie.name} died. Creating corpse and checking for loot...")
    # create corpse at zombie position
    dead_sprite_path = os.path.join('game', 'zombies', 'sprites', 'dead.png')
    corpse = Corpse(name="Dead corpse", capacity=10, image_path=dead_sprite_path, pos=zombie.rect.center)
    # build its inventory from the zombie loot table
    if hasattr(zombie, 'loot_table'):
        for drop in zombie.loot_table:
            if random.random() < drop.get('chance', 0):
                item_inst = Item.create_from_name(drop.get('item'))
                if item_inst:
                    corpse.inventory.append(item_inst)
                else:
                    print(f"Failed to create item: {drop.get('item')}")
    # append corpse to world items (it behaves like an item on ground)
    if find_free_tile(corpse.rect, obstacles, items_on_ground_list, initial_pos=zombie.rect.topleft):
        items_on_ground_list.append(corpse)

    # --- Experience Gain ---
    player.experience += zombie.xp_value
    print(f"Gained {zombie.xp_value} experience. Total XP: {player.experience}")
    # --- Level Up Check ---
    xp_needed = experience_for_level(player.level + 1)
    if player.experience >= xp_needed:
        player.level += 1
        player.skill_strength += 1
        player.skill_melee += 1
        player.skill_ranged += 1
        player.max_health += 10
        player.health = player.max_health # Full heal on level up
        print(f"LEVEL UP! You are now level {player.level}!")

def experience_for_level(level):
    """Calculates the experience needed for a given level."""
    return int(100 * (1.5 ** (level - 1)))
