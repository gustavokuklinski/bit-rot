# core/entities/zombie/zombie_ai.py

import math
import random
import time
import pygame
import heapq
from core.data.config import TILE_SIZE
import core.data.config

class ZombieAI:
    def __init__(self):
        super().__init__()

        self.path = []
        self.path_step = 0
        self.last_path_calc_time = pygame.time.get_ticks() + random.randint(-2000, 0)
        self.path_recalc_cooldown = 0
        self.stuck_timer = 0
        self.stuck_angle = 0
        
        # Noise tracking
        self.noise_target = None
        self.noise_timer = 0

    def alert_to_noise(self, sound_pos, source_type="noise"):
        """Alerts the entity to investigate a sound source."""
        if getattr(self, 'is_dead', False):
            return
        self.noise_target = (sound_pos[0], sound_pos[1])
        self.noise_timer = 9000  # Investigate for 9 seconds
        self.state = 'chasing'
        self.path = []  # Force immediate path calculation toward noise

    def alert_nearby_zombies(self, game, radius):
        """Alerts nearby zombies within the radius to converge on the player."""
        current_time = pygame.time.get_ticks()
        if current_time - getattr(self, '_last_alert_call_time', 0) < 2000:
            return
        self._last_alert_call_time = current_time

        rad_sq = radius * radius
        zombies_to_check = getattr(game, 'active_zombies', [])
        if not zombies_to_check:
            zombies_to_check = getattr(game, 'zombies', [])

        for z in zombies_to_check:
            if z is self or getattr(z, 'is_dead', False):
                continue
            dx = z.rect.centerx - self.rect.centerx
            dy = z.rect.centery - self.rect.centery
            if (dx * dx + dy * dy) <= rad_sq:
                z.aggro_timer = max(getattr(z, 'aggro_timer', 0), 8000)
                z.state = 'chasing'
                if hasattr(z, 'path'):
                    z.path = []

    def has_line_of_sight(self, target_rect, game, current_time):
        """Checks if there is an unobstructed body corridor (3-ray check) between entity and target."""
        if not target_rect:
            return False

        if not core.data.config.ZOMBIE_LINE_OF_SIGHT_CHECK:
            return True

        if not hasattr(self, 'last_los_check_time'):
            self.last_los_check_time = 0
            self.los_check_interval = 250
            self.cached_los_result = True

        if current_time - self.last_los_check_time < self.los_check_interval:
            return self.cached_los_result

        start_pos = self.rect.center
        end_pos = target_rect.center

        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            return True

        # Perpendicular normal for physical width check (5 px half-width)
        nx = (-dy / dist) * 5.0
        ny = (dx / dist) * 5.0

        rays = [
            (start_pos, end_pos),
            ((start_pos[0] + nx, start_pos[1] + ny), (end_pos[0] + nx, end_pos[1] + ny)),
            ((start_pos[0] - nx, start_pos[1] - ny), (end_pos[0] - nx, end_pos[1] - ny)),
        ]

        los_result = True
        obstacles = getattr(game, 'obstacles', [])
        for obs in obstacles:
            hit = any(obs.clipline(p1, p2) for p1, p2 in rays)
            if hit:
                gx = obs.centerx // TILE_SIZE
                gy = obs.centery // TILE_SIZE
                tile_def = game.map_manager.get_tile_at(gx, gy) if hasattr(game, 'map_manager') else None
                if tile_def and tile_def.get('is_visible'):
                    continue
                los_result = False
                break

        self.last_los_check_time = current_time
        self.cached_los_result = los_result
        return los_result

    def _get_path_astar(self, start_pos, target_pos, game, allow_break_obstacles=False):
        """
        Calculates an 8-directional smooth path from start_pos to target_pos using A*.
        When allow_break_obstacles=False, closed doors/windows/walls are strictly impassable.
        """
        start_grid = (int(start_pos[0] // TILE_SIZE), int(start_pos[1] // TILE_SIZE))
        target_grid = (int(target_pos[0] // TILE_SIZE), int(target_pos[1] // TILE_SIZE))

        if start_grid == target_grid:
            return [target_pos]

        map_h = len(game.map_data) if getattr(game, 'map_data', None) else 0
        map_w = len(game.map_data[0]) if map_h > 0 else 0
        if map_h == 0 or map_w == 0:
            return None

        # 8 directions: (dx, dy, cost)
        directions = [
            (0, -1, 1.0), (0, 1, 1.0), (-1, 0, 1.0), (1, 0, 1.0),
            (-1, -1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (1, 1, 1.414)
        ]

        def octile_heuristic(a, b):
            dx = abs(a[0] - b[0])
            dy = abs(a[1] - b[1])
            return (dx + dy) + (1.414 - 2.0) * min(dx, dy)

        MAX_ITERATIONS = 500
        open_set = []
        heapq.heappush(open_set, (0, 0, start_grid, []))

        g_score = {start_grid: 0}
        visited = set()
        closest_dist = float('inf')
        closest_node = start_grid
        iterations = 0

        map_mgr = getattr(game, 'map_manager', None)

        while open_set and iterations < MAX_ITERATIONS:
            iterations += 1
            _, _, current, path = heapq.heappop(open_set)

            if current in visited:
                continue
            visited.add(current)

            dist_to_target = octile_heuristic(current, target_grid)
            if dist_to_target < closest_dist:
                closest_dist = dist_to_target
                closest_node = current

            if current == target_grid:
                pixel_path = []
                for node in path + [current]:
                    pixel_path.append((node[0] * TILE_SIZE + TILE_SIZE // 2,
                                       node[1] * TILE_SIZE + TILE_SIZE // 2))
                return pixel_path

            cx, cy = current
            for dx, dy, step_cost in directions:
                nx, ny = cx + dx, cy + dy
                next_node = (nx, ny)

                if next_node in visited:
                    continue
                if not (0 <= ny < map_h and 0 <= nx < map_w):
                    continue

                # Corner-cutting check for diagonal moves
                if dx != 0 and dy != 0:
                    tile_card1 = map_mgr.get_tile_at(cx + dx, cy) if map_mgr else None
                    tile_card2 = map_mgr.get_tile_at(cx, cy + dy) if map_mgr else None
                    if (tile_card1 and tile_card1.get('is_obstacle', False)) or \
                       (tile_card2 and tile_card2.get('is_obstacle', False)):
                        continue

                tile_def = map_mgr.get_tile_at(nx, ny) if map_mgr else None
                is_obstacle = tile_def and tile_def.get('is_obstacle', False)

                cost_mod = step_cost
                if is_obstacle and next_node != target_grid:
                    if not allow_break_obstacles:
                        continue

                    name = str(tile_def.get('name', '')).lower() if tile_def else ''
                    char = game.map_data[ny][nx] if 0 <= ny < map_h and 0 <= nx < map_w else ''
                    is_barricaded = bool(map_mgr.get_barricade(nx, ny)) if map_mgr else False
                    is_structural = (is_barricaded or (tile_def and (tile_def.get('is_statable') or tile_def.get('is_window'))) or
                                     'door' in name or 'window' in name or '_close' in char or '_broke' in char)

                    if tile_def and tile_def.get('destructible') and is_structural:
                        cost_mod += 15.0
                    else:
                        continue

                new_g = g_score[current] + cost_mod
                if next_node not in g_score or new_g < g_score[next_node]:
                    g_score[next_node] = new_g
                    h = octile_heuristic(next_node, target_grid)
                    heapq.heappush(open_set, (new_g + h, h, next_node, path + [current]))

        if allow_break_obstacles and closest_node != start_grid:
            return [(closest_node[0] * TILE_SIZE + TILE_SIZE // 2, closest_node[1] * TILE_SIZE + TILE_SIZE // 2)]

        return None

    def update_ai(self, player_rect, obstacles, nearby_entities, game):
        current_time = pygame.time.get_ticks()

        # Update noise alert timer
        has_active_noise = False
        if getattr(self, 'noise_target', None):
            self.noise_timer -= getattr(game, 'dt_ms', 16)
            dist_to_noise = math.hypot(self.noise_target[0] - self.rect.centerx, self.noise_target[1] - self.rect.centery)
            if self.noise_timer <= 0 or dist_to_noise < TILE_SIZE * 1.2:
                self.noise_target = None
                self.noise_timer = 0
                self.state = 'wandering'
            else:
                has_active_noise = True

        # Target selection: prioritize LIVING players or nearby hostile entities
        all_players = []
        if game.player and not getattr(game.player, 'is_dead', False) and game.player.health > 0:
            all_players.append(game.player)
        for rp in getattr(game, 'remote_players', {}).values():
            if not getattr(rp, 'is_dead', False) and rp.health > 0:
                all_players.append(rp)

        target_entity = None
        target_rect = None
        min_target_dist_sq = float('inf')

        for p in all_players:
            pdx = p.rect.centerx - self.rect.centerx
            pdy = p.rect.centery - self.rect.centery
            pdist_sq = pdx * pdx + pdy * pdy
            if pdist_sq < min_target_dist_sq:
                min_target_dist_sq = pdist_sq
                target_entity = p
                target_rect = p.rect

        if target_entity is None:
            dist_to_player_sq = float('inf')
        else:
            dist_to_player_sq = min_target_dist_sq

        nearest_target = None

        for entity in nearby_entities:
            if getattr(entity, 'is_dead', False): 
                continue
            is_npc = hasattr(game, 'npcs') and entity in game.npcs

            if is_npc:
                edx = entity.rect.centerx - self.rect.centerx
                edy = entity.rect.centery - self.rect.centery
                entity_dist_sq = edx * edx + edy * edy
                if entity_dist_sq < min_target_dist_sq:
                    if getattr(entity, 'is_static', False):
                        if not self.has_line_of_sight(entity.rect, game, current_time):
                            continue
                    min_target_dist_sq = entity_dist_sq
                    nearest_target = entity

        if nearest_target:
            target_rect = nearest_target.rect
            target_entity = nearest_target
            dist_to_target_sq = min_target_dist_sq
        else:
            dist_to_target_sq = dist_to_player_sq

        detection_radius = getattr(core.data.config, 'ZOMBIE_DETECTION_RADIUS', 5 * TILE_SIZE)
        if target_entity and target_entity == game.player and getattr(game.player, 'is_aiming', False):
            detection_radius *= 0.5
        elif target_entity and target_entity == game.player and getattr(game.player, 'is_running', False):
            detection_radius *= 1.4

        detection_radius_sq = detection_radius ** 2
        is_aggroed = getattr(self, 'aggro_timer', 0) > 0
        can_see_target = self.has_line_of_sight(target_rect, game, current_time) if target_rect else False

        # Store for debug visualization
        self.current_detection_radius = detection_radius
        self.can_see_player = can_see_target

        target_pos = None

        # Player MUST be within the detection zone and a valid target must exist
        in_detection_zone = (dist_to_target_sq <= detection_radius_sq) and (target_rect is not None)
        player_is_reachable = False

        if in_detection_zone and target_rect:
            if can_see_target:
                player_is_reachable = True
            elif not has_active_noise:
                check_path = self._get_path_astar(self.rect.center, target_rect.center, game, allow_break_obstacles=False)
                if check_path is not None:
                    player_is_reachable = True

        # State Decision
        if has_active_noise:
            self.state = 'chasing'
            target_pos = self.noise_target
        elif is_aggroed and target_rect:
            self.state = 'chasing'
            target_pos = target_rect.center

            attack_range_sq = (self.attack_range) ** 2
            if dist_to_target_sq < attack_range_sq:
                if current_time - getattr(self, 'last_attack_time', 0) > 1000:
                    self.attack(target_entity, game)
                    self.last_attack_time = current_time
                    self.vx, self.vy = 0, 0
                    return
        elif in_detection_zone and player_is_reachable and target_rect:
            self.state = 'chasing'
            target_pos = target_rect.center

            if target_entity == game.player:
                self.alert_nearby_zombies(game, detection_radius)

            attack_range_sq = (self.attack_range) ** 2
            if dist_to_target_sq < attack_range_sq:
                if current_time - getattr(self, 'last_attack_time', 0) > 1000:
                    self.attack(target_entity, game)
                    self.last_attack_time = current_time
                    self.vx, self.vy = 0, 0
                    return
        else:
            # Clear expired or target-less aggro timer
            self.aggro_timer = 0
            self.state = 'wandering'

            if getattr(self, 'is_ambiently_noisy', False) and core.data.config.ZOMBIE_WANDER_ENABLED and getattr(self, 'sound_wander', None):
                if getattr(self, 'last_wander_sound_time', 0) == 0:
                    self.last_wander_sound_time = current_time + random.randint(0, 4000)
                    self.wander_sound_cooldown = random.randint(6000, 14000)

                if current_time - self.last_wander_sound_time > self.wander_sound_cooldown:
                    snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
                    game.sound_manager.play_sound(
                        self.sound_wander,
                        subdir=snd_dir,
                        game=game,
                        source_pos=self.rect.center,
                        base_volume=0.3,
                        pitch_variance=0.15
                    )
                    self.last_wander_sound_time = current_time
                    self.wander_sound_cooldown = random.randint(6000, 14000)

            if core.data.config.ZOMBIE_WANDER_ENABLED:
                target_reached = self.wander_target and math.hypot(self.wander_target[0] - self.rect.centerx, self.wander_target[1] - self.rect.centery) < TILE_SIZE
                wander_interval = core.data.config.ZOMBIE_WANDER_CHANGE_INTERVAL

                if (current_time - getattr(self, 'last_wander_change', 0) > wander_interval) or (self.wander_target is None) or target_reached:
                    for _ in range(6):
                        wander_radius = 5 * TILE_SIZE
                        new_target_x = self.rect.centerx + random.randint(-wander_radius, wander_radius)
                        new_target_y = self.rect.centery + random.randint(-wander_radius, wander_radius)

                        grid_x = int(new_target_x // TILE_SIZE)
                        grid_y = int(new_target_y // TILE_SIZE)

                        if 0 <= grid_y < len(game.map_data) and 0 <= grid_x < len(game.map_data[0]):
                            tile = game.map_manager.get_tile_at(grid_x, grid_y)
                            if not tile or not tile.get('is_obstacle', False):
                                self.wander_target = (new_target_x, new_target_y)
                                break

                    self.last_wander_change = current_time

                target_pos = self.wander_target

        if target_pos:
            allow_break = has_active_noise or is_aggroed
            self.move_towards(target_pos, obstacles, nearby_entities, game, can_see_target=can_see_target, allow_break_obstacles=allow_break)

    def move_towards(self, target_pos, obstacles, nearby_entities, game, can_see_target=True, allow_break_obstacles=False):
        from core.systems.utils import resolve_stuck_in_obstacle
        resolve_stuck_in_obstacle(self, obstacles, game)

        speed_mult = 1.0
        gx = self.rect.centerx // TILE_SIZE
        gy = self.rect.centery // TILE_SIZE
        if hasattr(game, 'map_manager'):
            tile_def = game.map_manager.get_tile_at(gx, gy)
            if tile_def:
                name = tile_def.get('name', '').lower()
                if 'window' in name or tile_def.get('is_window'):
                    speed_mult = 0.35

        effective_speed = self.speed * getattr(game, 'dt_mult', 1.0) * speed_mult
        current_time = pygame.time.get_ticks()

        dist_to_goal = math.hypot(target_pos[0] - self.rect.centerx, target_pos[1] - self.rect.centery)
        close_enough_for_direct = (dist_to_goal <= self.attack_range * 1.5)

        use_pathfinding = (not can_see_target) or (self.stuck_timer > 0) or (self.state == 'wandering') or (not close_enough_for_direct)

        move_x, move_y = 0, 0

        if use_pathfinding:
            recalc_time = 500 if self.state == 'chasing' else 1000
            if current_time - getattr(self, 'last_path_calc_time', 0) > recalc_time or not self.path:
                new_path = self._get_path_astar(self.rect.center, target_pos, game, allow_break_obstacles=allow_break_obstacles)
                if new_path:
                    self.path = new_path
                    self.last_path_calc_time = current_time

            while len(self.path) > 1:
                second_node = self.path[1]
                second_rect = pygame.Rect(second_node[0] - 2, second_node[1] - 2, 4, 4)
                if self.has_line_of_sight(second_rect, game, current_time):
                    self.path.pop(0)
                else:
                    break

            if self.path:
                next_node = self.path[0]
                dx = next_node[0] - self.rect.centerx
                dy = next_node[1] - self.rect.centery
                dist = math.hypot(dx, dy)

                node_tile = (next_node[0] // TILE_SIZE, next_node[1] // TILE_SIZE)
                my_tile = (self.rect.centerx // TILE_SIZE, self.rect.centery // TILE_SIZE)

                # Clear waypoint if close or inside the same grid tile
                if dist < TILE_SIZE * 0.75 or (node_tile == my_tile):
                    self.path.pop(0)
                    if self.path:
                        next_node = self.path[0]
                        dx = next_node[0] - self.rect.centerx
                        dy = next_node[1] - self.rect.centery
                        dist = math.hypot(dx, dy)

                if dist > 0:
                    move_x = (dx / dist) * effective_speed
                    move_y = (dy / dist) * effective_speed
        else:
            self.path = []
            dx = target_pos[0] - self.rect.centerx
            dy = target_pos[1] - self.rect.centery
            dist = math.hypot(dx, dy)
            stop_distance = self.attack_range * 0.75 if self.state == 'chasing' else TILE_SIZE * 0.5
            if dist > stop_distance:
                move_x = (dx / dist) * effective_speed
                move_y = (dy / dist) * effective_speed

        sep_x, sep_y = 0, 0
        separation_radius = TILE_SIZE * 0.9
        separation_radius_sq = separation_radius ** 2
        neighbor_count = 0

        for other in nearby_entities:
            if other is self: 
                continue
            dx = self.rect.centerx - other.rect.centerx
            dy = self.rect.centery - other.rect.centery
            if abs(dx) > separation_radius or abs(dy) > separation_radius:
                continue

            dist_sq = dx * dx + dy * dy
            if dist_sq < separation_radius_sq:
                dist = math.sqrt(dist_sq) if dist_sq > 0.001 else 0.001
                force = (separation_radius - dist) / separation_radius
                sep_x += (dx / dist) * force
                sep_y += (dy / dist) * force
                neighbor_count += 1

        if neighbor_count > 0:
            move_x += sep_x * effective_speed * 1.2
            move_y += sep_y * effective_speed * 1.2

        if self.stuck_timer > 0:
            self.stuck_timer -= getattr(game, 'dt_ms', 16)

        self.vx = move_x
        self.vy = move_y

        is_moving = move_x != 0 or move_y != 0
        self.walk_anim_angle = math.sin(time.time() * 15) * 2 if is_moving else 0

        def check_collision(rect_check):
            indices = rect_check.collidelistall(obstacles)
            for idx in indices:
                obstacle = obstacles[idx]
                gx = obstacle.x // TILE_SIZE
                gy = obstacle.y // TILE_SIZE
                tile_def = game.map_manager.get_tile_at(gx, gy) if hasattr(game, 'map_manager') else None
                if tile_def and 'mask' in tile_def and getattr(self, 'mask', None):
                    offset = (obstacle.x - rect_check.x, obstacle.y - rect_check.y)
                    if self.mask.overlap(tile_def['mask'], offset):
                        return obstacle
                else:
                    return obstacle

            player = getattr(game, 'player', None)
            if player and not getattr(player, 'is_dead', False) and player.health > 0:
                if rect_check.colliderect(player.rect.inflate(-10, -10)):
                    return player
            return None

        safe_step_size = TILE_SIZE * 0.45
        total_dist_x, total_dist_y = abs(move_x), abs(move_y)
        steps = max(1, int(math.ceil(max(total_dist_x, total_dist_y) / safe_step_size)))
        step_x, step_y = move_x / steps, move_y / steps
        max_slide = 6

        moved_any = False
        last_collider = None

        for _ in range(steps):
            # X Axis
            self.x += step_x
            self.rect.x = round(self.x)
            collider = check_collision(self.rect)
            if collider:
                last_collider = collider
                resolved = False
                orig_rect_y = self.rect.y
                for offset in range(1, max_slide + 1):
                    self.rect.y = orig_rect_y - offset
                    if not check_collision(self.rect):
                        self.y -= offset
                        self.rect.y = round(self.y)
                        resolved = True
                        break
                    self.rect.y = orig_rect_y + offset
                    if not check_collision(self.rect):
                        self.y += offset
                        self.rect.y = round(self.y)
                        resolved = True
                        break
                if not resolved:
                    self.rect.y = orig_rect_y
                    self.x -= step_x
                    self.rect.x = round(self.x)
                else:
                    moved_any = True
            else:
                moved_any = True

            # Y Axis
            self.y += step_y
            self.rect.y = round(self.y)
            collider = check_collision(self.rect)
            if collider:
                last_collider = collider
                resolved = False
                orig_rect_x = self.rect.x
                for offset in range(1, max_slide + 1):
                    self.rect.x = orig_rect_x - offset
                    if not check_collision(self.rect):
                        self.x -= offset
                        self.rect.x = round(self.x)
                        resolved = True
                        break
                    self.rect.x = orig_rect_x + offset
                    if not check_collision(self.rect):
                        self.x += offset
                        self.rect.x = round(self.x)
                        resolved = True
                        break
                if not resolved:
                    self.rect.x = orig_rect_x
                    self.y -= step_y
                    self.rect.y = round(self.y)
                else:
                    moved_any = True
            else:
                moved_any = True

        # Only register as stuck if movement was completely blocked on both axes
        if not moved_any and (abs(move_x) > 0.1 or abs(move_y) > 0.1):
            self.stuck_timer = 200
            self.path = []
            if allow_break_obstacles and last_collider and last_collider != getattr(game, 'player', None):
                self._try_attack_obstacle(last_collider, game, current_time, 1.0)

        self.rect.topleft = (round(self.x), round(self.y))

    def _try_attack_obstacle(self, hit_obstacle, game, current_time, multiplier):
        gx = hit_obstacle.x // TILE_SIZE
        gy = hit_obstacle.y // TILE_SIZE
        tile_def = game.map_manager.get_tile_at(gx, gy) if hasattr(game, 'map_manager') else None

        if hasattr(game, 'map_manager') and game.map_manager.is_tile_destructible(gx, gy):
            name = str(tile_def.get('name', '')).lower() if tile_def else ''
            char = game.map_data[gy][gx] if 0 <= gy < len(game.map_data) and 0 <= gx < len(game.map_data[0]) else ''
            has_barricade = bool(game.map_manager.get_barricade(gx, gy))
            is_structural = (has_barricade or (tile_def and (tile_def.get('is_statable') or tile_def.get('is_window'))) or
                             'door' in name or 'window' in name or 'barricate' in char or 'barricad' in char or
                             '_open' in char or '_close' in char or '_broke' in char)

            if is_structural:
                attack_delay = getattr(self, 'current_attack_delay', 1000.0) / multiplier
                if current_time - getattr(self, 'last_attack_time', 0) > attack_delay:
                    damage = random.randint(self.min_attack, self.max_attack)
                    game.map_manager.hit_tile(gx, gy, damage, attacker=self)
                    self.last_attack_time = current_time
                    self.current_attack_delay = random.randint(700, 1350)
                    self.melee_swing_timer = 10

                    if getattr(self, 'sound_attack', None):
                        snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
                        game.sound_manager.play_sound(
                            self.sound_attack, subdir=snd_dir, game=game,
                            source_pos=self.rect.center, base_volume=0.6, pitch_variance=0.35
                        )