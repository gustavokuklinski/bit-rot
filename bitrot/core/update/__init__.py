import pygame
from core.data.config import TILE_SIZE

# Internal Pipeline Steps
from core.update.utils import build_obstacle_grid, get_nearby_obstacles
from core.update.spawns import check_zombie_respawn, check_animal_respawn, check_dynamic_zombie_spawns
from core.update.projectiles import update_projectiles
from core.update.entities import update_entities
from core.update.vehicles import update_vehicles

# EXPOSE combat functions so external files don't break when importing from `core.update`
from core.update.combat import (
    player_hit_zombie, 
    handle_zombie_death, 
    create_blood_splatter, 
    trigger_explosion
)

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
    check_animal_respawn(game) 
    check_dynamic_zombie_spawns(game, GRID_SIZE)
    
    if game.player.update_stats(game):
        game.game_state = 'GAME_OVER'

    zombies_to_remove = []

    update_projectiles(game, GRID_SIZE, zombies_to_remove)
    update_entities(game, GRID_SIZE, zombies_to_remove)
    update_vehicles(game, zombies_to_remove)