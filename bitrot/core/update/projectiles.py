import pygame
import math
from core.data.config import TILE_SIZE
from core.entities.zombie.zombie import Zombie
from core.update.utils import get_nearby_obstacles
from core.update.combat import trigger_explosion, create_blood_splatter, player_hit_zombie, handle_zombie_death

def update_projectiles(game, GRID_SIZE, zombies_to_remove):
    projectiles_to_remove = []
    multiplier = 1.0
    
    for p in game.projectiles:
        world_max_x = game.world_min_x + game.map_width_pixels
        world_max_y = game.world_min_y + game.map_height_pixels

        local_obstacles = get_nearby_obstacles(p.rect, game.cached_obstacle_grid, GRID_SIZE)

        hit_wall = False
        for ob in local_obstacles:
            if p.rect.colliderect(ob):
                gx, gy = ob.centerx // TILE_SIZE, ob.centery // TILE_SIZE
                tile_def = game.map_manager.get_tile_at(gx, gy)
                if tile_def and tile_def.get('is_visible'): continue 
                hit_wall = True; break

        reached_max = p.update(game.world_min_x, game.world_min_y, world_max_x, world_max_y)
        
        if reached_max or hit_wall:
            projectiles_to_remove.append(p)
            if getattr(p, 'is_explosive', False):
                trigger_explosion(game, p.x, p.y, p.damage, getattr(p, 'explosion_radius', 3), p.owner, getattr(p, 'explosion_sound', None))
            continue
            
        if getattr(p, 'is_explosive', False): continue

        if getattr(p, 'hostile', False) and game.player and not game.player.is_dead:
            if p.rect.colliderect(game.player.rect):
                game.player.take_damage(game, getattr(p, 'damage', 5), 0)
                print(f"You were hit!")
                game.splashes.append({'pos': game.player.rect.center, 'time': pygame.time.get_ticks(), 'duration': 350, 'radius': 3, 'type': 'hit_puff'})
                projectiles_to_remove.append(p)
                continue
        
        search_rect = p.rect.inflate(10, 10)
        potential_hits = game.quadtree.query(search_rect)
        
        hit_zombie = next((z for z in potential_hits if isinstance(z, Zombie) and z not in zombies_to_remove and p.rect.colliderect(z.rect)), None)

        if hit_zombie:
            is_animal = getattr(hit_zombie, 'type', 'zombie') == 'animal'
            owner = getattr(p, 'owner', None)

            if owner is None or owner == game.player:
                if player_hit_zombie(game.player, hit_zombie, game):
                    if is_animal:
                        hit_zombie.die(game)
                        if hit_zombie in game.items_on_ground: game.items_on_ground.remove(hit_zombie)
                        if hit_zombie in game.active_animals: game.active_animals.remove(hit_zombie)
                    else:
                        zombies_to_remove.append(hit_zombie)
                        handle_zombie_death(game, hit_zombie, game.items_on_ground, game.obstacles, game.player.active_weapon)
                        game.zombies_killed += 1

                if not hit_zombie.is_dead:
                    hit_zombie.aggro_timer, hit_zombie.state = 10000, 'chasing'
                    for other_zombie in game.zombies:
                        if other_zombie != hit_zombie and not other_zombie.is_dead:
                            if (other_zombie.rect.centerx - hit_zombie.rect.centerx)**2 + (other_zombie.rect.centery - hit_zombie.rect.centery)**2 < (TILE_SIZE * 15) ** 2:
                                other_zombie.aggro_timer = max(other_zombie.aggro_timer, 8000)
                                other_zombie.state = 'chasing'

            else:
                is_dead = hit_zombie.take_damage(getattr(p, 'damage', 5), game, attacker=owner)
                if not is_dead:
                    hit_zombie.aggro_timer, hit_zombie.state = 10000, 'chasing'
                    for other_zombie in game.zombies:
                        if other_zombie != hit_zombie and not other_zombie.is_dead:
                            if (other_zombie.rect.centerx - hit_zombie.rect.centerx)**2 + (other_zombie.rect.centery - hit_zombie.rect.centery)**2 < (TILE_SIZE * 15) ** 2:
                                other_zombie.aggro_timer = max(other_zombie.aggro_timer, 8000)
                                other_zombie.state = 'chasing'

                game.splashes.append({'pos': (hit_zombie.rect.centerx, hit_zombie.rect.bottom), 'time': pygame.time.get_ticks(), 'duration': 350, 'radius': 2, 'type': 'hit_puff'})

                if is_dead:
                    if is_animal:
                        hit_zombie.die(game)
                        if hit_zombie in game.items_on_ground: game.items_on_ground.remove(hit_zombie)
                        if hit_zombie in game.active_animals: game.active_animals.remove(hit_zombie)
                    else:
                        zombies_to_remove.append(hit_zombie)
                        handle_zombie_death(game, hit_zombie, game.items_on_ground, game.obstacles, None)
                        game.splashes.append({'pos': (hit_zombie.rect.centerx, hit_zombie.rect.bottom), 'time': pygame.time.get_ticks(), 'duration': 600, 'radius': 5, 'type': 'death_burst'})

            projectiles_to_remove.append(p)
            continue
        
        hit_npc = next((n for n in potential_hits if n in getattr(game, 'npcs', []) and not n.is_dead and p.rect.colliderect(n.rect)), None)

        if hit_npc:
             damage = getattr(p, 'damage', game.player.get_attack_damage())
             dx, dy = hit_npc.rect.centerx - p.rect.centerx, hit_npc.rect.centery - p.rect.centery
             mag = math.hypot(dx, dy)
             create_blood_splatter(game, hit_npc.rect, damage, [dx/mag, dy/mag] if mag > 0 else None)

             attacker = getattr(p, 'owner', game.player) or game.player
             if game.player and game.player.active_weapon and game.player.active_weapon.item_type == 'weapon_ranged':
                  knockback_force = getattr(game.player.active_weapon, 'knockback', 0)
                  dx, dy = hit_npc.rect.centerx - game.player.rect.centerx, hit_npc.rect.centery - game.player.rect.centery
                  dist = math.hypot(dx, dy)
                  if dist > 0:
                      hit_npc.knockback_velocity = [(dx/dist) * knockback_force, (dy/dist) * knockback_force]
                      hit_npc.knockback_timer = 200

             if not hit_npc.is_dead:
                 hit_npc.aggro_timer, hit_npc.current_attacker, hit_npc.is_following, hit_npc.state = 10000, attacker, True, 'chasing'
                 for other_npc in game.npcs:
                     if other_npc != hit_npc and not other_npc.is_dead and (other_npc.rect.centerx - hit_npc.rect.centerx)**2 + (other_npc.rect.centery - hit_npc.rect.centery)**2 < (TILE_SIZE * 15) ** 2:
                         other_npc.aggro_timer, other_npc.is_following, other_npc.state = max(other_npc.aggro_timer, 8000), True, 'chasing'

             if hit_npc.take_damage(damage, game, attacker=attacker) and attacker == game.player:
                 print(f"You shot and killed {hit_npc.name}!")
             projectiles_to_remove.append(p)
             continue

    game.projectiles = [p for p in game.projectiles if p not in projectiles_to_remove]