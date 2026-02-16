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
        # [OPTIMIZATION] Randomize initial time to stagger pathfinding updates across frames
        self.last_path_calc_time = pygame.time.get_ticks() + random.randint(-2000, 0)
        self.path_recalc_cooldown = 0
        self.stuck_timer = 0
        self.stuck_angle = 0
        # Initialize other necessary attributes if not present
        if not hasattr(self, 'wander_target'): self.wander_target = None
        if not hasattr(self, 'state'): self.state = 'wandering'
        if not hasattr(self, 'last_wander_change'): self.last_wander_change = 0
        if not hasattr(self, 'last_wander_sound_time'): self.last_wander_sound_time = 0
        if not hasattr(self, 'wander_sound_cooldown'): self.wander_sound_cooldown = 0
        if not hasattr(self, 'last_attack_time'): self.last_attack_time = 0
        
    def has_line_of_sight(self, target_rect, obstacles):
        """Checks if there is an uninterrupted line between zombie and target."""
        if not core.data.config.ZOMBIE_LINE_OF_SIGHT_CHECK:
            return True 

        start_pos = self.rect.center
        end_pos = target_rect.center

        for obs in obstacles:
            if obs.clipline(start_pos, end_pos):
                return False 

        return True 

    def _get_path_astar(self, start_pos, target_pos, game):
        """
        Calculates a path from start_pos to target_pos using A* algorithm.
        """
        start_grid = (int(start_pos[0] // TILE_SIZE), int(start_pos[1] // TILE_SIZE))
        target_grid = (int(target_pos[0] // TILE_SIZE), int(target_pos[1] // TILE_SIZE))
        
        if start_grid == target_grid:
            return [target_pos]
            
        # [OPTIMIZATION] Reduced max iterations to prevent lag spikes on complex maps
        MAX_ITERATIONS = 200 
        
        open_set = []
        heapq.heappush(open_set, (0, 0, start_grid, []))
        
        g_score = {start_grid: 0}
        visited = set()
        
        closest_dist = float('inf')
        closest_node = start_grid

        iterations = 0
        
        map_h = len(game.map_data)
        map_w = len(game.map_data[0]) if map_h > 0 else 0
        
        while open_set and iterations < MAX_ITERATIONS:
            iterations += 1
            _, _, current, path = heapq.heappop(open_set)
            
            if current in visited:
                continue
            visited.add(current)
            
            dist_to_target = abs(current[0] - target_grid[0]) + abs(current[1] - target_grid[1])
            if dist_to_target < closest_dist:
                closest_dist = dist_to_target
                closest_node = current

            if current == target_grid:
                pixel_path = []
                for node in path + [current]:
                    pixel_path.append((node[0] * TILE_SIZE + TILE_SIZE // 2, 
                                       node[1] * TILE_SIZE + TILE_SIZE // 2))
                return pixel_path

            neighbors = [
                (current[0], current[1] - 1),
                (current[0], current[1] + 1),
                (current[0] - 1, current[1]),
                (current[0] + 1, current[1]),
            ]
            
            for next_node in neighbors:
                if next_node in visited:
                    continue
                
                if not (0 <= next_node[1] < map_h and 0 <= next_node[0] < map_w):
                    continue
                
                tile_def = game.map_manager.get_tile_at(next_node[0], next_node[1])
                is_obstacle = tile_def and tile_def.get('is_obstacle', False)
                
                if is_obstacle and next_node != target_grid:
                    continue
                
                move_cost = 1.0
                new_g = g_score[current] + move_cost
                
                if next_node not in g_score or new_g < g_score[next_node]:
                    g_score[next_node] = new_g
                    h = abs(next_node[0] - target_grid[0]) + abs(next_node[1] - target_grid[1])
                    heapq.heappush(open_set, (new_g + h, h, next_node, path + [current]))

        if closest_node != start_grid:
             return [(closest_node[0] * TILE_SIZE + TILE_SIZE//2, closest_node[1] * TILE_SIZE + TILE_SIZE//2)]
        
        return None

    def update_ai(self, player_rect, obstacles, other_zombies, game):
        """Main AI logic: decide state (wander/chase) and target."""
        current_time = pygame.time.get_ticks()
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0

        if not hasattr(self, 'path'): self.path = []

        target_rect = player_rect
        target_entity = game.player
        
        dist_to_player = math.hypot(player_rect.centerx - self.rect.centerx,
                                    player_rect.centery - self.rect.centery)

        nearest_npc = None
        min_npc_dist = 9999
        
        if hasattr(game, 'npcs'):
            for npc in game.npcs:
                if npc.is_dead: continue
                d = math.hypot(npc.rect.centerx - self.rect.centerx, npc.rect.centery - self.rect.centery)
                if d < min_npc_dist:
                    min_npc_dist = d
                    nearest_npc = npc
        
        if nearest_npc and (min_npc_dist < dist_to_player):
            target_rect = nearest_npc.rect
            target_entity = nearest_npc
            dist_to_target = min_npc_dist
        else:
            dist_to_target = dist_to_player

        can_see_target = self.has_line_of_sight(target_rect, obstacles)
        target_pos = None

        if dist_to_target < core.data.config.ZOMBIE_DETECTION_RADIUS and (can_see_target or self.state == 'chasing'):
            self.state = 'chasing'
            target_pos = target_rect.center 
            
            if dist_to_target < self.attack_range:
                if current_time - self.last_attack_time > (1000.0 / multiplier): 
                    self.attack(target_entity, game)
                    self.last_attack_time = current_time
                    self.vx, self.vy = 0, 0 
                    return

        else:
            self.state = 'wandering'
            
            if self.is_ambiently_noisy and core.data.config.ZOMBIE_WANDER_ENABLED and self.sound_wander:
                if current_time - self.last_wander_sound_time > self.wander_sound_cooldown:
                    game.sound_manager.play_sound(
                        self.sound_wander, 
                        subdir='zombie', 
                        game=game, 
                        source_pos=self.rect.center, 
                        base_volume=random.uniform(0.05, 0.08)
                    )
                    self.last_wander_sound_time = current_time
                    self.wander_sound_cooldown = random.randint(4000, 12000)

            if core.data.config.ZOMBIE_WANDER_ENABLED:
                target_reached = self.wander_target and math.hypot(self.wander_target[0] - self.rect.centerx, self.wander_target[1] - self.rect.centery) < TILE_SIZE
                
                wander_interval = core.data.config.ZOMBIE_WANDER_CHANGE_INTERVAL / multiplier
                
                if (current_time - self.last_wander_change > wander_interval) or \
                   (self.wander_target is None) or target_reached:

                    for _ in range(5):
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
            else:
                target_pos = None

        if target_pos:
            self.move_towards(target_pos, obstacles, other_zombies, game, can_see_target=(can_see_target and self.state == 'chasing'))

    def move_towards(self, target_pos, obstacles, other_zombies, game, can_see_target=True):
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
        effective_speed = self.speed * multiplier
        current_time = pygame.time.get_ticks()

        move_x, move_y = 0, 0
        use_pathfinding = not can_see_target
        
        if self.stuck_timer > 0 and self.stuck_timer % 10 == 0:
             use_pathfinding = True

        if use_pathfinding:
            # [OPTIMIZATION] Increased recalc delay to 1.5s to reduce CPU load
            if current_time - self.last_path_calc_time > 1500 or not self.path:
                new_path = self._get_path_astar(self.rect.center, target_pos, game)
                if new_path:
                    self.path = new_path
                    self.last_path_calc_time = current_time
            
            if self.path:
                next_node = self.path[0]
                dx = next_node[0] - self.rect.centerx
                dy = next_node[1] - self.rect.centery
                dist = math.hypot(dx, dy)
                
                if dist < TILE_SIZE / 2:
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
                dx = target_pos[0] - self.rect.centerx
                dy = target_pos[1] - self.rect.centery
                dist = math.hypot(dx, dy)
                if dist > 0:
                    move_x = (dx / dist) * effective_speed
                    move_y = (dy / dist) * effective_speed
        else:
            self.path = [] 
            dx = target_pos[0] - self.rect.centerx
            dy = target_pos[1] - self.rect.centery
            dist = math.hypot(dx, dy)
            
            stop_distance = TILE_SIZE / 2
            if self.state == 'chasing':
                 stop_distance = self.attack_range * 0.8
            
            if dist > stop_distance:
                move_x = (dx / dist) * effective_speed
                move_y = (dy / dist) * effective_speed

        # --- SEPARATION LOGIC (OPTIMIZED) ---
        sep_x, sep_y = 0, 0
        separation_radius = TILE_SIZE * 0.9
        separation_radius_sq = separation_radius ** 2
        neighbor_count = 0
        
        for z in other_zombies:
            if z is self: continue
            
            dx = self.rect.centerx - z.rect.centerx
            dy = self.rect.centery - z.rect.centery
            
            if abs(dx) > separation_radius or abs(dy) > separation_radius:
                continue

            dist_sq = dx*dx + dy*dy
            if dist_sq < separation_radius_sq:
                # [OPTIMIZATION] Avoid sqrt when possible, use approximation for very close entities
                if dist_sq < 0.01:
                    angle = random.uniform(0, 6.28)
                    sep_x += math.cos(angle)
                    sep_y += math.sin(angle)
                else:
                    dist = math.sqrt(dist_sq)
                    force = (separation_radius - dist) / separation_radius
                    sep_x += (dx / dist) * force
                    sep_y += (dy / dist) * force
                neighbor_count += 1
        
        if neighbor_count > 0:
            separation_strength = effective_speed * 1.5 
            move_x += sep_x * separation_strength
            move_y += sep_y * separation_strength

        if self.stuck_timer > 0:
            self.stuck_timer -= 1
            rad = math.radians(self.stuck_angle)
            move_x += math.cos(rad) * effective_speed * 0.5
            move_y += -math.sin(rad) * effective_speed * 0.5

        self.vx = move_x 
        self.vy = move_y 
        
        is_moving = move_x != 0 or move_y != 0
        if is_moving:
            self.walk_anim_angle = math.sin(time.time() * 15) * 2
        else:
            self.walk_anim_angle = 0
            
        if is_moving and self.is_ambiently_noisy and self.sound_steps:
             if current_time > self.last_step_sound_time:
                game.sound_manager.play_sound(self.sound_steps, subdir='zombie', game=game, source_pos=self.rect.center, base_volume=random.uniform(0.02, 0.06))
                self.last_step_sound_time = current_time + (random.randint(300, 500) / max(1, multiplier * 0.1))

        # --- PHYSICS SUB-STEPPING ---
        safe_step_size = TILE_SIZE * 0.45
        total_dist_x, total_dist_y = abs(move_x), abs(move_y)
        steps = int(math.ceil(max(total_dist_x, total_dist_y) / safe_step_size))
        steps = max(1, steps)
        step_x, step_y = move_x / steps, move_y / steps
        
        for _ in range(steps):
            self.x += step_x
            self.rect.x = int(self.x)
            collided = False
            for obs in obstacles:
                if self.rect.colliderect(obs): collided = True; break
            
            if collided:
                self.x -= step_x
                self.rect.x = int(self.x)
                if abs(step_x) > 0.1:
                    self.stuck_timer = 10
                    self.stuck_angle = random.randint(0, 360)
            
            self.y += step_y
            self.rect.y = int(self.y)
            collided = False
            for obs in obstacles:
                if self.rect.colliderect(obs): collided = True; break

            if collided:
                self.y -= step_y
                self.rect.y = int(self.y)
                if abs(step_y) > 0.1:
                    self.stuck_timer = 10
                    self.stuck_angle = random.randint(0, 360)

        self.rect.topleft = (int(self.x), int(self.y))