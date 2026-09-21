# core/map/spawn_manager.py

import math
import queue
import random
import threading
import core.data.config
from core.data.config import *
from core.entities.animal.animal import Animal
from core.entities.animal.animal_loader import AnimalLoader
from core.entities.item.item import Item
from core.entities.npc.npc import NPC
from core.entities.vehicle.vehicle import Vehicle
from core.entities.vehicle.vehicle_data import VehicleData
from core.entities.zombie.zombie import Zombie
from core.placement import find_free_tile
import pygame

NPC_SPAWN_RADIUS = 70 * TILE_SIZE
NPC_DESPAWN_RADIUS = 80 * TILE_SIZE
NPC_MIN_SPAWN_DIST = 50 * TILE_SIZE


# =====================================================================
# --- ASYNCHRONOUS SPAWN WORKER (RUNS ON A DEDICATED THREAD) ---
# =====================================================================
class AsyncSpawnManager:

  def __init__(self):
    self.request_queue = queue.Queue()
    self.completed_queue = queue.Queue()
    self.running = True
    self.worker_thread = threading.Thread(
        target=self._worker_loop, daemon=True
    )
    self.worker_thread.start()

  def stop(self):
    self.running = False
    self.request_queue.put(None)

  def request_spawn(
      self,
      entity_type,
      count=1,
      layer=1,
      target_pos=None,
      obstacles=None,
      map_w=3000,
      map_h=3000,
      view_radius=240,
      player_pos=(0, 0),
  ):
    """Schedules an entity spawn on the background thread."""
    if not self.running:
      return
    req = {
        'type': entity_type,  # 'zombie', 'animal', 'npc'
        'count': count,
        'layer': layer,
        'target_pos': target_pos,
        'obstacles': [pygame.Rect(o) for o in (obstacles or [])],
        'map_w': map_w,
        'map_h': map_h,
        'view_radius': view_radius,
        'player_pos': player_pos,
    }
    self.request_queue.put(req)

  def _worker_loop(self):
    while self.running:
      try:
        req = self.request_queue.get(timeout=0.1)
        if req is None:
          break
        self._process_request(req)
      except queue.Empty:
        continue
      except Exception as e:
        print(f'[AsyncSpawner Worker Error]: {e}')

  def _process_request(self, req):
    e_type = req['type']
    count = req['count']
    layer = req['layer']
    px, py = req['player_pos']
    obstacles = req['obstacles']
    map_w, map_h = req['map_w'], req['map_h']
    view_r = req['view_radius']

    spawn_r = view_r + (10 * TILE_SIZE)

    for _ in range(count):
      pos = req['target_pos']
      if not pos:
        pos = self._find_out_of_sight(px, py, spawn_r, obstacles, map_w, map_h)

      if not pos:
        continue

      spawn_x, spawn_y = pos
      self.completed_queue.put({
          'type': e_type,
          'x': spawn_x,
          'y': spawn_y,
          'layer': layer,
      })

  def _find_out_of_sight(self, px, py, spawn_r, obstacles, map_w, map_h):
    start_angle = random.uniform(0, math.pi * 2)
    steps = 24
    offsets = [0, TILE_SIZE, -TILE_SIZE, 2 * TILE_SIZE]

    for r_off in offsets:
      cur_r = max(TILE_SIZE * 5, spawn_r + r_off)
      for i in range(steps):
        angle = start_angle + (i * (2 * math.pi / steps))
        tx = (int(px + math.cos(angle) * cur_r) // TILE_SIZE) * TILE_SIZE
        ty = (int(py + math.sin(angle) * cur_r) // TILE_SIZE) * TILE_SIZE

        if not (0 <= tx < map_w - TILE_SIZE and 0 <= ty < map_h - TILE_SIZE):
          continue

        test_rect = pygame.Rect(tx, ty, TILE_SIZE, TILE_SIZE)
        if any(test_rect.colliderect(ob) for ob in obstacles):
          continue

        return (tx, ty)
    return None

  def flush_to_game(self, game):
    if not hasattr(game, 'player') or not game.player:
      return

    while not self.completed_queue.empty():
      try:
        item = self.completed_queue.get_nowait()
      except queue.Empty:
        break

      e_type = item['type']
      x, y = item['x'], item['y']
      layer = item['layer']

      if e_type == 'zombie':
        max_z = getattr(core.data.config, 'MAX_ZOMBIES_GLOBAL', 500)
        max_chunk_z = getattr(core.data.config, 'ZOMBIE_MAX_CHUNK', 6)
        if max_z > 0 and max_chunk_z > 0 and len(game.zombies) < max_z:
          z = Zombie.create_random(x, y)
          z.layer = layer
          game.zombies.append(z)

      elif e_type == 'animal':
        max_anim = getattr(core.data.config, 'ANIMAL_MAX_CHUNK', 6)
        current_anim_count = len(getattr(game, 'active_animals', []))
        if max_anim > 0 and current_anim_count < max_anim:
          a_type = AnimalLoader.get_random_animal_type(layer=layer)
          animal = Animal(x, y, a_type, game=game, layer=layer)
          if hasattr(game, 'active_animals'):
            game.active_animals.append(animal)
          if hasattr(game, 'items_on_ground'):
            game.items_on_ground.append(animal)

      elif e_type == 'npc':
        max_npc = getattr(core.data.config, 'MAX_NPCS_GLOBAL', 1500)
        max_npc_chunk = getattr(core.data.config, 'NPC_MAX_CHUNK', 6)
        if max_npc > 0 and max_npc_chunk > 0 and len(game.npcs) < max_npc:
          is_friendly = random.random() > getattr(
              core.data.config, 'NPC_HOSTILE_PERCENT', 0.6
          )
          npc = NPC(x, y, game, is_static=False, layer=layer)
          npc.is_friendly = is_friendly
          game.npcs.add(npc)


# Global instance
async_spawner = AsyncSpawnManager()


# =====================================================================
# --- STANDARD SPAWNER HELPERS ---
# =====================================================================


def get_house_spawn_position(game):
  valid_spawns = []
  layer = game.current_layer_index
  ground_layer = game.all_ground_layers.get(layer)
  base_layer = game.all_map_layers.get(layer)

  if not ground_layer or not base_layer:
    return None

  map_height = len(ground_layer)
  defs = game.tile_manager.definitions

  for y in range(map_height):
    row_width = len(ground_layer[y])
    for x in range(row_width):
      g_char = ground_layer[y][x]
      if g_char and g_char != ' ':
        tile_def = defs.get(g_char)
        ground_name = (
            tile_def.get('name', '').lower() if tile_def else g_char.lower()
        )
        if g_char == 'house_floor_01' or 'house_floor_01' in ground_name:
          if (
              y < len(base_layer)
              and x < len(base_layer[y])
              and base_layer[y][x] == ' '
          ):
            valid_spawns.append((x, y))

  if valid_spawns:
    spawn_grid_x, spawn_grid_y = random.choice(valid_spawns)
    return spawn_grid_x * TILE_SIZE, spawn_grid_y * TILE_SIZE
  return None


def spawn_initial_items(obstacles, item_spawns):
  items_on_ground = []
  occupied_tiles = set((ob.x // TILE_SIZE, ob.y // TILE_SIZE) for ob in obstacles)

  for spawn_data in item_spawns:
    if len(spawn_data) == 3:
      x, y, name = spawn_data
      item = Item.create_from_name(name)
      if item:
        item.rect.topleft = (x, y)
        item.x, item.y = x, y
        item_tile = (x // TILE_SIZE, y // TILE_SIZE)
        stacked = False
        if item.is_stackable():
          for existing in items_on_ground:
            if existing.rect.topleft == (x, y) and existing.can_stack_with(
                item
            ):
              existing.load = (existing.load or 1) + (item.load or 1)
              stacked = True
              break
        if not stacked:
          items_on_ground.append(item)
          occupied_tiles.add(item_tile)
    else:
      pos = spawn_data
      item = Item.generate_random()
      if item:
        item.rect.topleft = pos
        item.x, item.y = pos[0], pos[1]
        item_tile = (item.rect.x // TILE_SIZE, item.rect.y // TILE_SIZE)
        stacked = False
        if item.is_stackable():
          for existing in items_on_ground:
            if existing.rect.topleft == pos and existing.can_stack_with(item):
              existing.load = (existing.load or 1) + (item.load or 1)
              stacked = True
              break
        if not stacked and item_tile not in occupied_tiles:
          items_on_ground.append(item)
          occupied_tiles.add(item_tile)
  return items_on_ground


def _find_spawn_spot_near(
    initial_pos_px,
    occupied_tiles,
    obstacles,
    map_width_px,
    map_height_px,
    max_radius=5,
):
  start_x_tile = initial_pos_px[0] // TILE_SIZE
  start_y_tile = initial_pos_px[1] // TILE_SIZE
  max_x_tile = (map_width_px or 99999) // TILE_SIZE
  max_y_tile = (map_height_px or 99999) // TILE_SIZE

  def is_physically_free(tx, ty):
    test_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
    return not any(test_rect.colliderect(ob) for ob in obstacles)

  tile_coord = (start_x_tile, start_y_tile)
  if (
      tile_coord not in occupied_tiles
      and 0 <= tile_coord[0] < max_x_tile
      and 0 <= tile_coord[1] < max_y_tile
  ):
    if is_physically_free(start_x_tile, start_y_tile):
      occupied_tiles.add(tile_coord)
      return (start_x_tile * TILE_SIZE, start_y_tile * TILE_SIZE)

  for radius in range(1, max_radius + 1):
    for i in range(-radius, radius + 1):
      for j in range(-radius, radius + 1):
        if abs(i) < radius and abs(j) < radius:
          continue
        cx = start_x_tile + i
        cy = start_y_tile + j
        if not (0 <= cx < max_x_tile and 0 <= cy < max_y_tile):
          continue
        tc = (cx, cy)
        if tc not in occupied_tiles and is_physically_free(cx, cy):
          occupied_tiles.add(tc)
          return (cx * TILE_SIZE, cy * TILE_SIZE)
  return None


def manage_dynamic_npcs(game):
    if not game.player:
        return
    
    max_npc_chunk = getattr(core.data.config, 'NPC_MAX_CHUNK', 6)
    max_npc_global = getattr(core.data.config, 'MAX_NPCS_GLOBAL', 1500)
    if max_npc_chunk <= 0 or max_npc_global <= 0 or getattr(core.data.config, 'NPC_SPAWN_CHANCE', 1.0) <= 0.0:
        return

    px, py = game.player.rect.centerx, game.player.rect.centery

    for npc in list(game.npcs):
        if not hasattr(npc, 'layer'):
            npc.layer = 1
        if npc.layer != game.current_layer_index:
            if hasattr(npc, 'is_following') and npc.is_following:
                npc.layer = game.current_layer_index
            else:
                game.layer_npcs.setdefault(npc.layer, []).append(npc)
                game.npcs.remove(npc)
                continue

        if hasattr(npc, 'is_following') and npc.is_following:
            continue
        dist_sq = (npc.rect.centerx - px) ** 2 + (npc.rect.centery - py) ** 2
        if dist_sq > NPC_DESPAWN_RADIUS**2:
            game.npcs.remove(npc)

    curr_layer = game.current_layer_index
    if curr_layer in getattr(game, 'layer_npcs', {}):
        for npc in game.layer_npcs[curr_layer]:
            if npc not in game.npcs:
                game.npcs.add(npc)
        game.layer_npcs[curr_layer] = []

    if len(game.npcs) >= max_npc_chunk:
        return

    async_spawner.request_spawn(
        'npc',
        count=1,
        layer=curr_layer,
        obstacles=getattr(game, 'obstacles', []),
        map_w=getattr(game, 'map_width_pixels', 3000),
        map_h=getattr(game, 'map_height_pixels', 3000),
        view_radius=getattr(game, 'player_view_radius', 240),
        player_pos=(px, py),
    )


def spawn_animals(game, count=None, target_layer=None):
    max_chunk = getattr(core.data.config, 'ANIMAL_MAX_CHUNK', 6)
    if max_chunk <= 0:
        return

    if count is None:
        count = max_chunk
    count = min(count, max_chunk)
    if count <= 0:
        return

    if target_layer is None:
        target_layer = getattr(game, 'current_layer_index', 1)

    px, py = (
        game.player.rect.centerx if game.player else 0,
        game.player.rect.centery if game.player else 0,
    )
    async_spawner.request_spawn(
        'animal',
        count=count,
        layer=target_layer,
        obstacles=getattr(game, 'obstacles', []),
        map_w=getattr(game, 'map_width_pixels', 3000),
        map_h=getattr(game, 'map_height_pixels', 3000),
        view_radius=getattr(game, 'player_view_radius', 240),
        player_pos=(px, py),
    )


def spawn_random_vehicles(game, count=10):
  max_veh = getattr(core.data.config, 'MAX_VEH_CHUNK', 6)
  if count <= 0 or max_veh <= 0:
    return

  if not VehicleData.VEHICLE_TEMPLATES:
    VehicleData.load_templates()
  if not VehicleData.VEHICLE_TEMPLATES:
    return

  layer_idx = game.current_layer_index
  valid_tiles = []
  spawn_layer = getattr(game, 'all_spawn_layers', {}).get(layer_idx)

  if spawn_layer:
    h = len(spawn_layer)
    w = len(spawn_layer[0]) if h > 0 else 0
    for y in range(h):
      for x in range(w):
        if spawn_layer[y][x] == 'VEH':
          valid_tiles.append((x, y))

  if not valid_tiles:
    map_data = getattr(game, 'all_ground_layers', {}).get(layer_idx, [])
    for y, row in enumerate(map_data):
      for x, char in enumerate(row):
        t_def = game.tile_manager.definitions.get(char)
        if t_def:
          t_name = t_def.get('name', '').lower()
          if 'road' in t_name or 'dirty_01' in t_name:
            valid_tiles.append((x, y))

  if not valid_tiles:
    return

  random.shuffle(valid_tiles)
  spawned = 0
  limit = count

  for tx, ty in valid_tiles:
    if spawned >= limit:
      break
    defn = VehicleData.get_random_definition()
    if not defn:
      break

    images = defn.get('images', {})
    random_facing = random.choice(['top', 'down', 'left', 'right'])
    base_img = images.get(random_facing) or (
        next(iter(images.values())) if images else None
    )

    w = base_img.get_width() if base_img else TILE_SIZE * 2
    h = base_img.get_height() if base_img else TILE_SIZE * 3
    px, py = tx * TILE_SIZE, ty * TILE_SIZE

    veh_rect = pygame.Rect(px, py, w, h)
    if any(veh_rect.colliderect(ob) for ob in game.obstacles):
      continue

    vehicle = Vehicle(
        name=defn['name'],
        x=px,
        y=py,
        width=w,
        height=h,
        image=images,
        stats=defn['stats'],
        capacity=defn['capacity'],
        loot_table=defn['loot_table'],
        facing=random_facing,
    )
    game.vehicles.append(vehicle)
    game.containers.append(vehicle)
    game.obstacles.append(vehicle.rect)
    spawned += 1


def spawn_l2_population(game, count=10, target_layer=None):
  if target_layer is None:
    target_layer = game.current_layer_index
  px, py = (
      game.player.rect.centerx if game.player else 0,
      game.player.rect.centery if game.player else 0,
  )
  async_spawner.request_spawn(
      'zombie',
      count=count,
      layer=target_layer,
      obstacles=getattr(game, 'obstacles', []),
      map_w=getattr(game, 'map_width_pixels', 3000),
      map_h=getattr(game, 'map_height_pixels', 3000),
      view_radius=getattr(game, 'player_view_radius', 240),
      player_pos=(px, py),
  )


def spawn_initial_zombies(
    obstacles,
    zombie_spawns,
    items_on_ground,
    limit=1000,
    spawns_per_marker=None,
    map_width_px=None,
    map_height_px=None,
    player=None,
    obstacle_grid=None,
    grid_size=128,
    game=None,
):
  if (
      core.data.config.MAX_ZOMBIES_GLOBAL <= 0
      or core.data.config.ZOMBIES_PER_SPAWN <= 0
  ):
    return []

  zombies = []
  if not zombie_spawns:
    return []

  occupied_tiles = set((ob.x // TILE_SIZE, ob.y // TILE_SIZE) for ob in obstacles)
  for entity in items_on_ground:
    occupied_tiles.add((entity.rect.x // TILE_SIZE, entity.rect.y // TILE_SIZE))
  if player:
    occupied_tiles.add((player.rect.x // TILE_SIZE, player.rect.y // TILE_SIZE))

  if spawns_per_marker is not None:
      spawns_count = spawns_per_marker
  else:
      spawns_count = getattr(core.data.config, 'ZOMBIES_PER_SPAWN', 3)

  for pos in zombie_spawns:
    if len(zombies) >= limit:
      break
    for _ in range(spawns_count):
      if len(zombies) >= limit:
        break
      spot = _find_spawn_spot_near(
          pos, occupied_tiles, obstacles, map_width_px, map_height_px
      )
      if spot:
        zombie = Zombie.create_random(spot[0], spot[1])
        zombies.append(zombie)
      else:
        break
  return zombies


def get_out_of_sight_spawn_pos(game):
  """Fast fallback that requests replacement spawns via the async worker."""
  if not game or not getattr(game, 'player', None):
    return None
  px, py = game.player.rect.centerx, game.player.rect.centery
  view_r = getattr(game, 'player_view_radius', 240)
  return async_spawner._find_out_of_sight(
      px,
      py,
      view_r + (10 * TILE_SIZE),
      getattr(game, 'obstacles', []),
      getattr(game, 'map_width_pixels', 3000),
      getattr(game, 'map_height_pixels', 3000),
  )