import math
import random
import time
import pygame
import heapq
from core.data.config import TILE_SIZE
import core.data.config

class ZombieAI:
    def __init__(self):
        # [FIX] Initialize the next class in the MRO chain (eventually pygame.sprite.Sprite)
        super().__init__()
        
        self.path = []
        self.path_step = 0
        self.last_path_calc_time = 0
        self.path_recalc_cooldown = 0
        
    def has_line_of_sight(self, target_rect, obstacles):
        """Checks if there is an uninterrupted line between zombie and target."""
        if not core.data.config.ZOMBIE_LINE_OF_SIGHT_CHECK:
            return True # Skip check if disabled in config

        start_pos = self.rect.center
        end_pos = target_rect.center

        # Simple line segment-rectangle intersection check
        for obs in obstacles:
            if obs.clipline(start_pos, end_pos):
                return False # Line of sight is blocked

        return True # Line of sight is clear

    def _get_path_astar(self, start_pos, target_pos, game):
        """
        Calculates a path from start_pos to target_pos using A* algorithm on the tile grid.
        Returns a list of (x, y) tuples in pixel coordinates (center of tiles).
        """
        start_grid = (int(start_pos[0] // TILE_SIZE), int(start_pos[1] // TILE_SIZE))
        target_grid = (int(target_pos[0] // TILE_SIZE), int(target_pos[1] // TILE_SIZE))
        
        # If start and target are the same tile, return simple path
        if start_grid == target_grid:
            return [target_pos]
            
        # Limits to prevent freezing on long paths
        MAX_ITERATIONS = 400 
        
        # Priority Queue: (f_score, h_score, current_node, path_so_far)
        # We include h_score in tuple for tie-breaking preference
        open_set = []
        heapq.heappush(open_set, (0, 0, start_grid, []))
        
        g_score = {start_grid: 0}
        visited = set()
        
        best_path = []
        closest_node = start_grid
        closest_dist = float('inf')

        iterations = 0
        
        while open_set and iterations < MAX_ITERATIONS:
            iterations += 1
            _, _, current, path = heapq.heappop(open_set)
            
            if current in visited:
                continue
            visited.add(current)
            
            # Update closest node fallback
            dist_to_target = abs(current[0] - target_grid[0]) + abs(current[1] - target_grid[1])
            if dist_to_target < closest_dist:
                closest_dist = dist_to_target
                closest_node = current

            # Check if reached target (or adjacent if target is obstacle)
            if current == target_grid:
                # Reconstruct path in pixels
                pixel_path = []
                for node in path + [current]:
                    pixel_path.append((node[0] * TILE_SIZE + TILE_SIZE // 2, 
                                       node[1] * TILE_SIZE + TILE_SIZE // 2))
                return pixel_path

            # Neighbors (Up, Down, Left, Right)
            neighbors = [
                (current[0], current[1] - 1),
                (current[0], current[1] + 1),
                (current[0] - 1, current[1]),
                (current[0] + 1, current[1]),
                # Diagonals (optional, costs more)
                (current[0] - 1, current[1] - 1),
                (current[0] + 1, current[1] - 1),
                (current[0] - 1, current[1] + 1),
                (current[0] + 1, current[1] + 1)
            ]
            
            for next_node in neighbors:
                if next_node in visited:
                    continue
                
                # Check bounds
                if not (0 <= next_node[1] < len(game.map_data) and 0 <= next_node[0] < len(game.map_data[0])):
                    continue
                
                # Check Walkability
                # We check the static map data. Dynamic obstacles are handled by physics/steering.
                tile_def = game.map_manager.get_tile_at(next_node[0], next_node[1])
                is_obstacle = tile_def and tile_def.get('is_obstacle', False)
                
                # Allow target tile to be an obstacle (e.g. attacking a door or player standing on an item)
                if is_obstacle and next_node != target_grid:
                    continue
                
                # Cost calculation
                is_diagonal = next_node[0] != current[0] and next_node[1] != current[1]
                move_cost = 1.4 if is_diagonal else 1.0
                
                new_g = g_score[current] + move_cost
                
                if next_node not in g_score or new_g < g_score[next_node]:
                    g_score[next_node] = new_g
                    h = abs(next_node[0] - target_grid[0]) + abs(next_node[1] - target_grid[1]) # Manhattan
                    heapq.heappush(open_set, (new_g + h, h, next_node, path + [current]))

        # Fallback: return path to closest reachable node
        pixel_path = []
        # Trace path? Simplified: just go to closest node found
        if closest_node != start_grid:
             return [(closest_node[0] * TILE_SIZE + TILE_SIZE//2, closest_node[1] * TILE_SIZE + TILE_SIZE//2)]
        
        return None

    def update_ai(self, player_rect, obstacles, other_zombies, game):
        """Main AI logic: decide state (wander/chase) and target."""
        current_time = pygame.time.get_ticks()
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0

        # Lazy Init Path
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
            
            # Logic: If we can't see the target, we should pathfind to it
            # If we CAN see it, we move directly, UNLESS we are stuck.
            
            if dist_to_target < self.attack_range:
                if current_time - self.last_attack_time > (1000.0 / multiplier): 
                    self.attack(target_entity, game)
                    self.last_attack_time = current_time
                    self.vx, self.vy = 0, 0 # Stop while attacking
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

                    # Find a valid wander target (not in a wall)
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
        """
        Calculates movement vector. Uses Pathfinding if target is not visible or complex.
        """
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
        effective_speed = self.speed * multiplier
        current_time = pygame.time.get_ticks()

        move_x, move_y = 0, 0
        
        # --- PATHFINDING LOGIC ---
        use_pathfinding = not can_see_target
        
        # If we have been stuck recently, force pathfinding to get out of corner
        if self.stuck_timer > 0 and self.stuck_timer % 10 == 0:
             use_pathfinding = True

        if use_pathfinding:
            # Recalculate path periodically
            if current_time - self.last_path_calc_time > 1000 or not self.path:
                new_path = self._get_path_astar(self.rect.center, target_pos, game)
                if new_path:
                    self.path = new_path
                    self.last_path_calc_time = current_time
            
            # Follow Path
            if self.path:
                next_node = self.path[0]
                dx = next_node[0] - self.rect.centerx
                dy = next_node[1] - self.rect.centery
                dist = math.hypot(dx, dy)
                
                if dist < TILE_SIZE / 2:
                    self.path.pop(0) # Reached node, go to next
                    if self.path:
                        next_node = self.path[0]
                        dx = next_node[0] - self.rect.centerx
                        dy = next_node[1] - self.rect.centery
                        dist = math.hypot(dx, dy)
                
                if dist > 0:
                    move_x = (dx / dist) * effective_speed
                    move_y = (dy / dist) * effective_speed
            else:
                # Fallback if no path found (go direct)
                dx = target_pos[0] - self.rect.centerx
                dy = target_pos[1] - self.rect.centery
                dist = math.hypot(dx, dy)
                if dist > 0:
                    move_x = (dx / dist) * effective_speed
                    move_y = (dy / dist) * effective_speed
        else:
            # Direct Movement (Visible Target)
            self.path = [] # Clear path if we can see target
            dx = target_pos[0] - self.rect.centerx
            dy = target_pos[1] - self.rect.centery
            dist = math.hypot(dx, dy)
            
            stop_distance = TILE_SIZE / 2
            if self.state == 'chasing':
                 stop_distance = self.attack_range * 0.8
            
            if dist > stop_distance:
                move_x = (dx / dist) * effective_speed
                move_y = (dy / dist) * effective_speed

        # --- SEPARATION LOGIC (Fix for stacking) ---
        # Look for other zombies close by and apply a repulsive force
        sep_x, sep_y = 0, 0
        separation_radius = TILE_SIZE * 0.9 # Slightly smaller than 1 tile
        neighbor_count = 0
        
        for z in other_zombies:
            if z is self: continue
            
            # Simple distance check
            dx = self.rect.centerx - z.rect.centerx
            dy = self.rect.centery - z.rect.centery
            
            # Quick bounds check optimization
            if abs(dx) > separation_radius or abs(dy) > separation_radius:
                continue

            dist_sq = dx*dx + dy*dy
            if dist_sq < separation_radius * separation_radius:
                dist = math.sqrt(dist_sq)
                if dist < 0.1: 
                    # If strictly overlapping (dist ~ 0), push in random direction
                    angle = random.uniform(0, 6.28)
                    sep_x += math.cos(angle)
                    sep_y += math.sin(angle)
                else:
                    # The closer they are, the stronger the push
                    force = (separation_radius - dist) / separation_radius
                    sep_x += (dx / dist) * force
                    sep_y += (dy / dist) * force
                neighbor_count += 1
        
        if neighbor_count > 0:
            # Apply the separation force to the movement
            separation_strength = effective_speed * 1.5 
            move_x += sep_x * separation_strength
            move_y += sep_y * separation_strength


        # --- STUCK / AVOIDANCE LOGIC ---
        if self.stuck_timer > 0:
            self.stuck_timer -= 1
            # If pathfinding fails, we might still be physically stuck on a dynamic object
            # Apply a small random force to wiggle out
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
            
        # Footstep sounds (omitted for brevity, same as before)
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
            # X Axis
            self.x += step_x
            self.rect.x = int(self.x)
            collided = False
            for obs in obstacles:
                if self.rect.colliderect(obs): collided = True; break
            
            # Removed strict zombie-zombie collision check here to allow separation to work
            # If we kept it, they would freeze when touching.
            
            if collided:
                self.x -= step_x
                self.rect.x = int(self.x)
                # Only trigger stuck timer if we were trying to move significantly
                if abs(step_x) > 0.1:
                    self.stuck_timer = 10
                    self.stuck_angle = random.randint(0, 360)
            
            # Y Axis
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