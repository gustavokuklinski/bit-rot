import pygame
import math
import random
from core.data.config import TILE_SIZE
from core.update.utils import get_nearby_obstacles
from core.messages import display_message

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
    stain_size = 4

    for i in range(1, 7):
        offset_pixels = (i / 3.0) * (TILE_SIZE * 0.75) + random.uniform(-2, 5)
        lateral_scatter = random.uniform(-8, 8) 
        
        stain_pos_x = base_x - (trail_dir_x * offset_pixels) + (perp_dir_x * lateral_scatter)
        stain_pos_y = base_y - (trail_dir_y * offset_pixels) + (perp_dir_y * lateral_scatter)
        
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
    
    if len(game.blood_stains) > 60:
        game.blood_stains = game.blood_stains[-60:]

def trigger_explosion(game, x, y, damage, radius, owner, explosion_sound=None):
    current_time = pygame.time.get_ticks()
    
    if not explosion_sound and owner and getattr(owner, 'active_weapon', None):
        if hasattr(owner.active_weapon, 'sounds'):
            explosion_sound = owner.active_weapon.sounds.get('explosion')
    
    if explosion_sound:
        game.sound_manager.play_sound(
            explosion_sound, subdir='items', game=game, source_pos=(x, y), 
            base_volume=0.5, pitch_variance=0.1, force=True, is_critical=True
        )
        
    game.splashes.append({
        'pos': (x, y), 'time': current_time, 'duration': 800,
        'radius': radius * TILE_SIZE, 'type': 'explosion'
    })
    
    hit_radius = radius * TILE_SIZE
    hit_rect = pygame.Rect(x - hit_radius, y - hit_radius, hit_radius*2, hit_radius*2)
    
    dead_zombies = []
    for z in game.zombies:
        if not getattr(z, 'is_dead', False) and hit_rect.colliderect(z.rect):
            dist = math.hypot(z.rect.centerx - x, z.rect.centery - y)
            if dist <= hit_radius:
                z.last_hit_sound_time = current_time 
                is_dead = z.take_damage(damage, game, attacker=owner)
                if is_dead: dead_zombies.append(z)
                else:
                    if dist > 0:
                        z.knockback_velocity = [((z.rect.centerx - x) / dist) * 15, ((z.rect.centery - y) / dist) * 15]
                        z.knockback_timer = 400
                    z.aggro_timer = 15000
                    z.state = 'chasing'
                    
    for z in dead_zombies:
        handle_zombie_death(game, z, game.items_on_ground, game.obstacles, getattr(owner, 'active_weapon', None))
        if owner == getattr(game, 'player', None):
            game.zombies_killed += 1
                
    dead_animals = []
    for a in getattr(game, 'active_animals', []):
        if not getattr(a, 'is_dead', False) and hit_rect.colliderect(a.rect):
            dist = math.hypot(a.rect.centerx - x, a.rect.centery - y)
            if dist <= hit_radius:
                a.last_hit_sound_time = current_time 
                is_dead = a.take_damage(damage, game, attacker=owner)
                if is_dead: dead_animals.append(a)
                else:
                    if dist > 0:
                        a.knockback_velocity = [((a.rect.centerx - x) / dist) * 15, ((a.rect.centery - y) / dist) * 15]
                        a.knockback_timer = 400
                    a.aggro_timer = 15000
                    a.state = 'chasing'
                    
    for a in dead_animals:
        a.die(game)
        if a in game.items_on_ground: game.items_on_ground.remove(a)
        if a in game.active_animals: game.active_animals.remove(a)

    dead_npcs = []
    if hasattr(game, 'npcs'):
        for n in game.npcs:
            if not getattr(n, 'is_dead', False) and hit_rect.colliderect(n.rect):
                dist = math.hypot(n.rect.centerx - x, n.rect.centery - y)
                if dist <= hit_radius:
                    n.last_hit_sound_time = current_time 
                    is_dead = n.take_damage(damage, game, attacker=owner)
                    if is_dead: dead_npcs.append(n)
                    else:
                        if dist > 0:
                            n.knockback_velocity = [((n.rect.centerx - x) / dist) * 15, ((n.rect.centery - y) / dist) * 15]
                            n.knockback_timer = 400
                        n.aggro_timer = 15000
                        n.state = 'chasing'
                        if owner == getattr(game, 'player', None):
                            n.is_friendly = False
                            
        for n in dead_npcs:
            handle_zombie_death(game, n, game.items_on_ground, game.obstacles, getattr(owner, 'active_weapon', None))
            if n in game.npcs: game.npcs.remove(n)

    if hasattr(game, 'player') and game.player and not getattr(game.player, 'is_dead', False) and hit_rect.colliderect(game.player.rect):
        dist = math.hypot(game.player.rect.centerx - x, game.player.rect.centery - y)
        if dist <= hit_radius:
            game.player.take_damage(game, damage // 2, 0)
            game.splashes.append({'pos': game.player.rect.center, 'time': current_time, 'duration': 350, 'radius': 3, 'type': 'hit_puff'})

    ALARM_RADIUS = TILE_SIZE * 30
    for other_zombie in getattr(game, 'active_zombies', game.zombies):
        if not getattr(other_zombie, 'is_dead', False):
            if (other_zombie.rect.centerx - x)**2 + (other_zombie.rect.centery - y)**2 < ALARM_RADIUS ** 2:
                other_zombie.aggro_timer = max(getattr(other_zombie, 'aggro_timer', 0), 10000)
                other_zombie.state = 'chasing'

    if hasattr(game, 'map_manager'):
        grid_x, grid_y = int(x // TILE_SIZE), int(y // TILE_SIZE)
        for gy in range(grid_y - radius, grid_y + radius + 1):
            for gx in range(grid_x - radius, grid_x + radius + 1):
                if math.hypot(gx - grid_x, gy - grid_y) <= radius:
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    if tile_def and tile_def.get('destructible'):
                        game.map_manager.hit_tile(gx, gy, damage, weapon=None, is_projectile=True)

def player_hit_zombie(player, zombie, game):
    progression = player.progression
    active_weapon = player.active_weapon
    base_damage, damage_multiplier, knockback_force = 1, 1.0, 0
    is_headshot, is_ranged = False, False
    projectile_dir = [0, 0]

    if active_weapon:
        base_damage = active_weapon.damage
        if active_weapon.item_type == 'weapon_ranged': 
            damage_multiplier = progression.get_ranged_damage_multiplier(player)
            if random.random() < progression.get_headshot_chance(player):
                is_headshot, damage_multiplier = True, damage_multiplier * 2.0 

            dx, dy = zombie.rect.centerx - player.rect.centerx, zombie.rect.centery - player.rect.centery
            magnitude = math.hypot(dx, dy)
            if magnitude > 0: projectile_dir = [dx / magnitude, dy / magnitude]
            knockback_force = getattr(active_weapon, 'knockback', 50)
            is_ranged = True 
        else: 
            damage_multiplier = progression.get_melee_damage_multiplier(player)
            durability_loss = progression.get_weapon_durability_loss(player)
            if active_weapon.durability is not None and active_weapon.durability > 0:
                active_weapon.durability -= durability_loss
                if active_weapon.durability <= 0:
                    player.active_weapon = None
                    display_message(f"{active_weapon.name} is broken and unequipped.")
    else: 
        base_damage = progression.get_unarmed_damage(player)

    final_damage = base_damage * damage_multiplier

    dx, dy = zombie.rect.centerx - player.rect.centerx, zombie.rect.centery - player.rect.centery
    magnitude = math.hypot(dx, dy)
    if magnitude > 0: projectile_dir = [dx / magnitude, dy / magnitude]

    if is_ranged and knockback_force > 0:
        zombie.knockback_velocity = [projectile_dir[0] * knockback_force, projectile_dir[1] * knockback_force]
        zombie.knockback_timer = 400

    create_blood_splatter(game, zombie.rect, final_damage, projectile_dir)

    game.splashes.append({'pos': (zombie.rect.centerx, zombie.rect.bottom), 'time': pygame.time.get_ticks(), 'duration': 350, 'radius': 2, 'type': 'hit_puff'})
    
    if zombie.take_damage(final_damage, game):
        game.splashes.append({'pos': (zombie.rect.centerx, zombie.rect.bottom), 'time': pygame.time.get_ticks(), 'duration': 250, 'radius': 5, 'type': 'death_burst'})
        return True

    print(f"{'Headshot' if is_headshot else 'Hit'}! Dealt {final_damage:.1f} damage.")
    return False

def handle_zombie_death(game, zombie, items_on_ground_list, obstacles, weapon):
    zombie.die(game)
    if weapon: game.player.process_kill(weapon, zombie)

    current_map_filename = game.map_manager.current_map_filename
    if current_map_filename not in game.map_states:
        game.map_states[current_map_filename] = {'items': [], 'zombies': [], 'killed_zombies': [], 'picked_up_items': [], 'last_respawn_time': pygame.time.get_ticks()} 
    game.map_states[current_map_filename].setdefault('killed_zombies', []).append(zombie.id)