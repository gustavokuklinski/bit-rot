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
        
    def has_line_of_sight(self, target_rect, game, current_time):
        """Checks if there is an uninterrupted line between zombie and target."""
        if not core.data.config.ZOMBIE_LINE_OF_SIGHT_CHECK:
            return True
        
        # Use cached result if recently checked
        if not hasattr(self, 'last_los_check_time'):
            self.last_los_check_time = 0
            self.los_check_interval = 500
            self.cached_los_result = True
        
        if current_time - self.last_los_check_time < self.los_check_interval:
            return self.cached_los_result
        
        start_pos = self.rect.center
        end_pos = target_rect.center
        
        los_result = True
        for obs in game.obstacles:
            if obs.clipline(start_pos, end_pos):
                # Check if this obstacle tile allows visibility
                gx = obs.centerx // TILE_SIZE
                gy = obs.centery // TILE_SIZE
                tile_def = game.map_manager.get_tile_at(gx, gy)
                if tile_def and tile_def.get('is_visible'):
                    continue # It's a transparent obstacle, ignore for line-of-sight!
                
                los_result = False
                break
        
        # Cache the result
        self.last_los_check_time = current_time
        self.cached_los_result = los_result
        
        return los_result

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
                
                move_cost = 1.0
                if is_obstacle and next_node != target_grid:
                    tile_def = game.map_manager.get_tile_at(next_node[0], next_node[1])
                    if tile_def:
                        is_npc = hasattr(self, 'is_friendly') 
                        name = str(tile_def.get('name', '')).lower()
                        
                        # [ELEGANT FIX] Filter to only allow pathing through structural barriers
                        is_structural = (tile_def.get('is_statable') or tile_def.get('is_window') or 
                                       'door' in name or 'window' in name or 'barricate' in name)

                        if is_npc and tile_def.get('is_statable'):
                            move_cost = 2.0  # Slight delay cost for opening
                        elif tile_def.get('destructible') and is_structural:
                            move_cost = 15.0 # Cost of breaking barricades/doors
                        else:
                            continue
                    else:
                        continue
                
                new_g = g_score[current] + move_cost
                
                if next_node not in g_score or new_g < g_score[next_node]:
                    g_score[next_node] = new_g
                    h = abs(next_node[0] - target_grid[0]) + abs(next_node[1] - target_grid[1])
                    heapq.heappush(open_set, (new_g + h, h, next_node, path + [current]))

        if closest_node != start_grid:
             return [(closest_node[0] * TILE_SIZE + TILE_SIZE//2, closest_node[1] * TILE_SIZE + TILE_SIZE//2)]
        
        return None

    def _check_chase_triggers(self, player, game, dist_to_player, current_time):
        """
        Check if the zombie should enter chasing state based on player actions.
        Returns True if the zombie should chase, False otherwise.
        """
        # [NEW] Ignore triggers if player is in Godzen mode
        if getattr(player, 'godzen_mode', False):
            return False

        # Initialize cache attributes if not present
        if not hasattr(self, 'last_trigger_check_time'):
            self.last_trigger_check_time = 0
            self.trigger_check_interval = 300
            self.cached_trigger_result = False

        # Use cached result if recently checked (but always check if already chasing)
        if self.state != 'chasing' and current_time - self.last_trigger_check_time < self.trigger_check_interval:
            return self.cached_trigger_result

        base_detection_radius = core.data.config.ZOMBIE_DETECTION_RADIUS
        # [NEW] Increase detection radius by 3x when player shoots ranged weapon (gunshot noise)
        if getattr(player, 'gun_flash_timer', 0) > 0:
            detection_radius = base_detection_radius * 3
        else:
            detection_radius = base_detection_radius
        
        detection_radius_sq = detection_radius ** 2
        trigger_result = False

        # [FIX] Early exit: zombie too far from player to detect anything
        # But allow chase if zombie was recently damaged/aggroed
        dist_sq = dist_to_player * dist_to_player
        is_aggroed = getattr(self, 'aggro_timer', 0) > 0
        if dist_sq > detection_radius_sq and self.state != 'chasing' and not is_aggroed:
            return False

        # [FIX] Aggroed zombies always chase
        if is_aggroed:
            trigger_result = True

        # If zombie can see player within detection radius, always chase
        if dist_sq <= detection_radius_sq:
            if core.data.config.ZOMBIE_LINE_OF_SIGHT_CHECK:
                if self.has_line_of_sight(player.rect, game, current_time):
                    trigger_result = True
            else:
                trigger_result = True

        if not trigger_result:
            # Check if player is running (makes noise, attracts zombies)
            if getattr(player, 'is_running', False):
                if dist_sq <= detection_radius_sq:
                    trigger_result = True

            # Check if player is shooting ranged weapon (loud noise)
            if not trigger_result and getattr(player, 'gun_flash_timer', 0) > 0:
                if dist_sq <= detection_radius_sq:
                    trigger_result = True

            # Check if player is using melee weapon (quieter, only very close zombies hear)
            if not trigger_result and getattr(player, 'melee_swing_timer', 0) > 0:
                melee_noise_radius_sq = (TILE_SIZE * 3) ** 2
                if dist_sq < melee_noise_radius_sq:
                    trigger_result = True

            # Check for moving vehicles (loud noise, attracts zombies)
            # Only check if zombie is close to player area (optimization)
            if not trigger_result and dist_sq <= detection_radius_sq:
                if hasattr(game, 'map_manager') and hasattr(game.map_manager, 'vehicles'):
                    for vehicle in game.map_manager.vehicles:
                        if getattr(vehicle, 'active', False) or vehicle.current_speed_val > 0.5:
                            dx = vehicle.rect.centerx - self.rect.centerx
                            dy = vehicle.rect.centery - self.rect.centery
                            veh_dist_sq = dx*dx + dy*dy
                            if veh_dist_sq < detection_radius_sq:
                                trigger_result = True
                                break

        # Cache the result
        self.last_trigger_check_time = current_time
        self.cached_trigger_result = trigger_result

        return trigger_result

    def update_ai(self, player_rect, obstacles, nearby_entities, game):
        """Main AI logic: decide state (wander/chase) and target."""
        current_time = pygame.time.get_ticks()
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0

        if not hasattr(self, 'path'): self.path = []

        target_rect = player_rect
        target_entity = game.player

        dx = player_rect.centerx - self.rect.centerx
        dy = player_rect.centery - self.rect.centery
        dist_to_player_sq = dx*dx + dy*dy
        dist_to_player = math.sqrt(dist_to_player_sq)

        nearest_target = None
        min_target_dist_sq = dist_to_player_sq

        # --- QUADTREE TARGETING: Check nearby NPCs and Animals natively ---
        for entity in nearby_entities:
            if getattr(entity, 'is_dead', False): continue
            
            is_npc = hasattr(game, 'npcs') and entity in game.npcs
            is_animal = getattr(entity, 'type', '') == 'animal'
            
            if is_npc or is_animal:
                edx = entity.rect.centerx - self.rect.centerx
                edy = entity.rect.centery - self.rect.centery
                entity_dist_sq = edx*edx + edy*edy
                
                if entity_dist_sq < min_target_dist_sq:
                    # [NEW FIX]: Ensure zombies only target static NPCs if they have line of sight to them
                    if getattr(entity, 'is_static', False):
                        if not self.has_line_of_sight(entity.rect, game, current_time):
                            continue  # Skip targeting this static NPC if we can't see them
                            
                    min_target_dist_sq = entity_dist_sq
                    nearest_target = entity

        if nearest_target:
            target_rect = nearest_target.rect
            target_entity = nearest_target
            dist_to_target = math.sqrt(min_target_dist_sq)
            dist_to_target_sq = min_target_dist_sq
        else:
            dist_to_target = dist_to_player
            dist_to_target_sq = dist_to_player_sq

        can_see_target = self.has_line_of_sight(target_rect, game, current_time)
        target_pos = None

        should_chase = self._check_chase_triggers(game.player, game, dist_to_target, current_time)
        is_aggroed = getattr(self, 'aggro_timer', 0) > 0

        if target_entity == game.player and getattr(game.player, 'godzen_mode', False):
            can_see_target = False
            should_chase = False
            is_aggroed = False
            self.aggro_timer = 0
            dist_to_target_sq = float('inf')
            if self.state == 'chasing':
                self.state = 'wandering'

        detection_radius_sq = core.data.config.ZOMBIE_DETECTION_RADIUS ** 2
        if should_chase or is_aggroed or (dist_to_target_sq < detection_radius_sq and (can_see_target or self.state == 'chasing')):
            self.state = 'chasing'
            target_pos = target_rect.center

            attack_range_sq = self.attack_range ** 2
            if dist_to_target_sq < attack_range_sq:
                if current_time - self.last_attack_time > (1000.0 / multiplier):
                    self.attack(target_entity, game)
                    self.last_attack_time = current_time
                    self.vx, self.vy = 0, 0
                    return

        elif self.state == 'chasing':
            target_pos = target_rect.center
            self.state = 'chasing'

            attack_range_sq = self.attack_range ** 2
            if dist_to_target_sq < attack_range_sq:
                if current_time - self.last_attack_time > (1000.0 / multiplier):
                    self.attack(target_entity, game)
                    self.last_attack_time = current_time
                    self.vx, self.vy = 0, 0
                    return
        else:
            self.state = 'wandering'
            
            if self.is_ambiently_noisy and core.data.config.ZOMBIE_WANDER_ENABLED and self.sound_wander:
                if getattr(self, 'last_wander_sound_time', 0) == 0:
                    self.last_wander_sound_time = current_time + random.randint(0, 6000)
                    self.wander_sound_cooldown = random.randint(4000, 12000)

                if current_time - self.last_wander_sound_time > self.wander_sound_cooldown:
                    snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
                    game.sound_manager.play_sound(
                        self.sound_wander, 
                        subdir=snd_dir, 
                        game=game, 
                        source_pos=self.rect.center, 
                        base_volume=1.0,
                        pitch_variance=0.15
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
            self.move_towards(target_pos, obstacles, nearby_entities, game, can_see_target=(can_see_target and self.state == 'chasing'))

    def move_towards(self, target_pos, obstacles, nearby_entities, game, can_see_target=True):

        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
        
        speed_mult = 1.0
        gx = self.rect.centerx // TILE_SIZE
        gy = self.rect.centery // TILE_SIZE
        if hasattr(game, 'map_manager'):
            tile_def = game.map_manager.get_tile_at(gx, gy)
            if tile_def:
                name = tile_def.get('name', '').lower()
                if 'window' in name or tile_def.get('is_window'):
                    speed_mult = 0.35 

        effective_speed = self.speed * multiplier * game.dt_mult * speed_mult
        current_time = pygame.time.get_ticks()

        move_x, move_y = 0, 0
        use_pathfinding = not can_see_target
        
        if self.stuck_timer > 0:
             use_pathfinding = True

        if use_pathfinding:
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

        # --- SEPARATION LOGIC ---
        sep_x, sep_y = 0, 0
        separation_radius = TILE_SIZE * 0.9
        separation_radius_sq = separation_radius ** 2
        neighbor_count = 0
        
        for z in nearby_entities:
            if z is self: continue
            
            dx = self.rect.centerx - z.rect.centerx
            dy = self.rect.centery - z.rect.centery
            
            if abs(dx) > separation_radius or abs(dy) > separation_radius:
                continue

            dist_sq = dx*dx + dy*dy
            if dist_sq < separation_radius_sq:
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
            self.stuck_timer -= game.dt_ms
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
            if getattr(self, 'last_step_sound_time', 0) == 0:
                self.last_step_sound_time = current_time + random.randint(0, 500)

            if current_time > self.last_step_sound_time:
                snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
                game.sound_manager.play_sound(
                    self.sound_steps, 
                    subdir=snd_dir, 
                    game=game, 
                    source_pos=self.rect.center, 
                    base_volume=1.0, 
                    pitch_variance=0.15
                )
                self.last_step_sound_time = current_time + (random.randint(300, 500) / max(1, multiplier * 0.1))

        # --- PHYSICS SUB-STEPPING ---
        safe_step_size = TILE_SIZE * 0.45
        total_dist_x, total_dist_y = abs(move_x), abs(move_y)
        steps = int(math.ceil(max(total_dist_x, total_dist_y) / safe_step_size))
        steps = max(1, steps)
        step_x, step_y = move_x / steps, move_y / steps
        
        for _ in range(steps):
            # --- X AXIS ---
            self.x += step_x
            self.rect.x = int(self.x)
            collided = False
            hit_obstacle = None
            
            for obs in obstacles:
                if self.rect.colliderect(obs): 
                    collided = True
                    hit_obstacle = obs
                    break
                
            if not collided and getattr(game, 'player', None) and not game.player.is_dead and not getattr(game.player, 'godzen_mode', False):
                if self.rect.colliderect(game.player.rect.inflate(-12, -12)):
                    collided = True
            
            if collided:
                self.x -= step_x
                self.rect.x = int(self.x)
                if abs(step_x) > 0.1:
                    self.stuck_timer = 200
                    self.stuck_angle = random.randint(0, 360)
                
                # [NEW] Attack destructibles when path is blocked
                if hit_obstacle and self.state == 'chasing':
                    gx = hit_obstacle.x // TILE_SIZE
                    gy = hit_obstacle.y // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    
                    if tile_def and tile_def.get('destructible'):
                        name = str(tile_def.get('name', '')).lower()
                        is_structural = (tile_def.get('is_statable') or tile_def.get('is_window') or 
                                       'door' in name or 'window' in name or 'barricate' in name)
                        
                        if is_structural:
                            if current_time - getattr(self, 'last_attack_time', 0) > (1000.0 / multiplier):
                            damage = random.randint(self.min_attack, self.max_attack)
                            game.map_manager.hit_tile(gx, gy, attacker=self)
                            self.last_attack_time = current_time
                            self.melee_swing_timer = 10
                            
                            if getattr(self, 'sound_attack', None):
                                snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
                                game.sound_manager.play_sound(
                                    self.sound_attack, subdir=snd_dir, game=game, 
                                    source_pos=self.rect.center, base_volume=1.0, pitch_variance=0.15
                                )
                        
                        step_x = 0
                        step_y = 0
            
            # --- Y AXIS ---
            self.y += step_y
            self.rect.y = int(self.y)
            collided = False
            hit_obstacle = None
            
            for obs in obstacles:
                if self.rect.colliderect(obs): 
                    collided = True
                    hit_obstacle = obs
                    break

            if not collided and getattr(game, 'player', None) and not game.player.is_dead and not getattr(game.player, 'godzen_mode', False):
                if self.rect.colliderect(game.player.rect.inflate(-12, -12)):
                    collided = True

            if collided:
                self.y -= step_y
                self.rect.y = int(self.y)
                if abs(step_y) > 0.1:
                    self.stuck_timer = 200
                    self.stuck_angle = random.randint(0, 360)

                # [NEW] Attack destructibles when path is blocked
                if hit_obstacle and self.state == 'chasing':
                    gx = hit_obstacle.x // TILE_SIZE
                    gy = hit_obstacle.y // TILE_SIZE
                    tile_def = game.map_manager.get_tile_at(gx, gy)
                    
                    if tile_def and tile_def.get('destructible'):
                        name = str(tile_def.get('name', '')).lower()
                        is_structural = (tile_def.get('is_statable') or tile_def.get('is_window') or 
                                       'door' in name or 'window' in name or 'barricate' in name)
                        
                        if is_structural:
                            if current_time - getattr(self, 'last_attack_time', 0) > (1000.0 / multiplier):
                            damage = random.randint(self.min_attack, self.max_attack)
                            game.map_manager.hit_tile(gx, gy, attacker=self)
                            self.last_attack_time = current_time
                            self.melee_swing_timer = 10
                            
                            if getattr(self, 'sound_attack', None):
                                snd_dir = 'animals' if getattr(self, 'type', '') == 'animal' else 'zombie'
                                game.sound_manager.play_sound(
                                    self.sound_attack, subdir=snd_dir, game=game, 
                                    source_pos=self.rect.center, base_volume=1.0, pitch_variance=0.15
                                )

                        step_x = 0
                        step_y = 0

        self.rect.topleft = (int(self.x), int(self.y))