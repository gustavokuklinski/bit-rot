import pygame
import math
import core.data.config
from core.data.config import TILE_SIZE
from core.map.spawn_manager import spawn_initial_zombies, spawn_animals

def check_dynamic_zombie_spawns(game, grid_size=128):
    triggered_spawns_for_layer = game.layer_spawn_triggers.get(game.current_layer_index)
    if triggered_spawns_for_layer is None:
        game.layer_spawn_triggers[game.current_layer_index] = set()
        triggered_spawns_for_layer = game.layer_spawn_triggers[game.current_layer_index]

    player_pos = game.player.rect.center
    GRID_SIZE_SPAWNS = getattr(game, 'SPAWN_GRID_SIZE', 512)
    player_grid_x, player_grid_y = int(player_pos[0] // GRID_SIZE_SPAWNS), int(player_pos[1] // GRID_SIZE_SPAWNS)
    spawn_grid = getattr(game, 'spawn_point_grid', {})

    potential_spawns = []
    for i in range(-2, 3):
        for j in range(-2, 3):
            if (player_grid_x + i, player_grid_y + j) in spawn_grid:
                potential_spawns.extend(spawn_grid[(player_grid_x + i, player_grid_y + j)])
    
    if not potential_spawns or len(game.zombies) >= core.data.config.MAX_ZOMBIES_GLOBAL: return

    SPAWN_ACTIVATION_RADIUS, MIN_SPAWN_DISTANCE, MAX_SPAWNS_PER_FRAME = 90 * TILE_SIZE, 50 * TILE_SIZE, 1

    valid_points = []
    for spawn_pos in potential_spawns:
        if spawn_pos in triggered_spawns_for_layer: continue
        dist = math.hypot(player_pos[0] - spawn_pos[0], player_pos[1] - spawn_pos[1])
        if MIN_SPAWN_DISTANCE < dist < SPAWN_ACTIVATION_RADIUS:
            valid_points.append((dist, spawn_pos))

    valid_points.sort(key=lambda x: x[0])
    entities_to_avoid = game.items_on_ground + game.zombies + [game.player]
    spawns_this_frame = 0

    for dist, spawn_pos in valid_points:
        if spawns_this_frame >= MAX_SPAWNS_PER_FRAME: break
        zombie_spawn_limit = max(0, core.data.config.MAX_ZOMBIES_GLOBAL - len(game.zombies))
        if zombie_spawn_limit == 0: break 

        triggered_spawns_for_layer.add(spawn_pos)
        new_zombies = spawn_initial_zombies(
            game.obstacles, [spawn_pos], entities_to_avoid, zombie_spawn_limit, 
            spawns_per_marker=core.data.config.ZOMBIES_PER_SPAWN, map_width_px=game.map_width_pixels,
            map_height_px=game.map_height_pixels, obstacle_grid=getattr(game, 'cached_obstacle_grid', None), grid_size=grid_size
        )
        
        if new_zombies:
            game.zombies.extend(new_zombies)
            entities_to_avoid.extend(new_zombies) 
            game.layer_zombies[game.current_layer_index] = game.zombies[:]
            spawns_this_frame += 1

def check_zombie_respawn(game):
    current_time = pygame.time.get_ticks()
    current_map = game.map_manager.current_map_filename
    
    if not game.current_zombie_spawns or current_map not in game.map_states:
        if current_map not in game.map_states:
            game.map_states[current_map] = {'items': game.items_on_ground, 'zombies': game.zombies, 'killed_zombies': [], 'picked_up_items': [], 'last_respawn_time': current_time}
        return

    if core.data.config.ZOMBIE_RESPAWN_TIMER_MS <= 0: return

    if 'last_respawn_time' not in game.map_states[current_map]: game.map_states[current_map]['last_respawn_time'] = current_time
    if current_time - game.map_states[current_map]['last_respawn_time'] > core.data.config.ZOMBIE_RESPAWN_TIMER_MS:
        print(f"Respawn timer expired for {current_map}. Respawning zombies.")
        game.map_states[current_map]['last_respawn_time'] = current_time

def check_animal_respawn(game):
    current_time = pygame.time.get_ticks()
    current_map = game.map_manager.current_map_filename
    
    if current_map not in game.map_states or core.data.config.ANIMAL_RESPAWN_TIMER_MS <= 0: return
    if 'last_animal_respawn_time' not in game.map_states[current_map]: game.map_states[current_map]['last_animal_respawn_time'] = current_time

    if current_time - game.map_states[current_map]['last_animal_respawn_time'] > core.data.config.ANIMAL_RESPAWN_TIMER_MS:
        print(f"Respawn timer expired for animals on {current_map}.")
        game.map_states[current_map]['last_animal_respawn_time'] = current_time
        spawn_animals(game, count=core.data.config.ANIMAL_SPAWN_COUNT)