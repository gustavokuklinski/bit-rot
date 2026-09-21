# core/update/spawns.py

import math
import core.data.config
from core.data.config import TILE_SIZE
from core.map.spawn_manager import async_spawner


def check_dynamic_zombie_spawns(game, grid_size=128):
  triggered = game.layer_spawn_triggers.setdefault(
      game.current_layer_index, set()
  )

  if not game.player:
    return
  player_pos = game.player.rect.center
  grid_scale = getattr(game, 'SPAWN_GRID_SIZE', 512)
  px, py = int(player_pos[0] // grid_scale), int(player_pos[1] // grid_scale)
  spawn_grid = getattr(game, 'spawn_point_grid', {})

  potential = []
  for i in range(-2, 3):
    for j in range(-2, 3):
      cell = (px + i, py + j)
      if cell in spawn_grid:
        potential.extend(spawn_grid[cell])

  if not potential or len(game.zombies) >= core.data.config.MAX_ZOMBIES_GLOBAL:
    return

  activation_dist = 90 * TILE_SIZE
  min_dist = 50 * TILE_SIZE

  for sp in potential:
    if sp in triggered:
      continue
    dist = math.hypot(player_pos[0] - sp[0], player_pos[1] - sp[1])
    if min_dist < dist < activation_dist:
      triggered.add(sp)
      # Hand off calculation to the background thread
      count = core.data.config.ZOMBIES_PER_SPAWN if core.data.config.ZOMBIES_PER_SPAWN is not None else 2
      if count <= 0 or core.data.config.MAX_ZOMBIES_GLOBAL <= 0:
          return
      async_spawner.request_spawn(
          'zombie',
          count=count,
          layer=game.current_layer_index,
          target_pos=sp,
          obstacles=game.obstacles,
      )
      break