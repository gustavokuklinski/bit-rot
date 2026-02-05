import math
import random
import time
import pygame
from core.data.config import TILE_SIZE
import core.data.config

class ZombieAI:
    def has_line_of_sight(self, target_rect, obstacles):
        """Checks if there is an uninterrupted line between zombie and target."""
        if not core.data.config.ZOMBIE_LINE_OF_SIGHT_CHECK:
            return True # Skip check if disabled in config

        start_pos = self.rect.center
        end_pos = target_rect.center

        # Simple line segment-rectangle intersection check using pygame's clipline
        # clipline returns the clipped points if it intersects, or empty tuple if not
        for obs in obstacles:
            if obs.clipline(start_pos, end_pos):
                return False # Line of sight is blocked

        return True # Line of sight is clear

    def update_ai(self, player_rect, obstacles, other_zombies, game):
        """Main AI logic: decide state (wander/chase) and target."""
        current_time = pygame.time.get_ticks()
        
        # [CHANGED] Get Time Multiplier for cooldown scaling
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0

        target_rect = player_rect
        target_entity = game.player  # Default target
        
        dist_to_player = math.hypot(player_rect.centerx - self.rect.centerx,
                                    player_rect.centery - self.rect.centery)

        nearest_npc = None
        min_npc_dist = 9999
        
        # Access NPCs from game instance
        if hasattr(game, 'npcs'):
            for npc in game.npcs:
                # [FIX] Skip targeting NPCs that are already dead (issue #1)
                if npc.is_dead:
                    continue

                d = math.hypot(npc.rect.centerx - self.rect.centerx, npc.rect.centery - self.rect.centery)
                if d < min_npc_dist:
                    min_npc_dist = d
                    nearest_npc = npc
        
        # Switch target to NPC if it is closer than player
        if nearest_npc and (min_npc_dist < dist_to_player):
            target_rect = nearest_npc.rect
            target_entity = nearest_npc # Set specific entity target
            dist_to_target = min_npc_dist
        else:
            dist_to_target = dist_to_player

        can_see_target = self.has_line_of_sight(target_rect, obstacles)
        target_pos = None

        # Decide state: Chasing or Wandering
        if dist_to_target < core.data.config.ZOMBIE_DETECTION_RADIUS and can_see_target:
            self.state = 'chasing'
            target_pos = target_rect.center 
            
            # Check attack range
            if dist_to_target < self.attack_range:
                # [CHANGED] Scale the cooldown logic
                # 1000ms real time cooldown. If FF is 50x, we wait 1000/50 = 20ms real time.
                if current_time - self.last_attack_time > (1000.0 / multiplier): 
                    self.attack(target_entity, game) # Attack the specific entity
                    self.last_attack_time = current_time

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
                
                # [CHANGED] Scale wander change interval too
                wander_interval = core.data.config.ZOMBIE_WANDER_CHANGE_INTERVAL / multiplier
                
                if (current_time - self.last_wander_change > wander_interval) or \
                   (self.wander_target is None) or target_reached:

                    wander_radius = 5 * TILE_SIZE
                    new_target_x = self.rect.centerx + random.randint(-wander_radius, wander_radius)
                    new_target_y = self.rect.centery + random.randint(-wander_radius, wander_radius)

                    self.wander_target = (new_target_x, new_target_y)
                    self.last_wander_change = current_time

                target_pos = self.wander_target 
            else:
                target_pos = None

        if target_pos:
            self.move_towards(target_pos, obstacles, other_zombies, game)

    def move_towards(self, target_pos, obstacles, other_zombies, game):
        """Calculates movement vector towards a target_pos and handles collisions."""
        
        # [CHANGED] 1. Get Multiplier
        multiplier = game.fast_forward_speed if getattr(game, 'is_fast_forwarding', False) else 1.0
        
        # [CHANGED] 2. Scale Speed
        effective_speed = self.speed * multiplier

        # [NEW] Check stuck timer
        if self.stuck_timer > 0:
            self.stuck_timer -= 1
            # Move in random stuck angle
            rad = math.radians(self.stuck_angle)
            move_x = math.cos(rad) * effective_speed
            move_y = -math.sin(rad) * effective_speed
        else:
            # Normal movement
            dx = target_pos[0] - self.rect.centerx
            dy = target_pos[1] - self.rect.centery
            dist = math.hypot(dx, dy)

            stop_distance = TILE_SIZE / 2 
            if self.state == 'chasing':
                stop_distance = self.attack_range * 1

            if dist > stop_distance:
                move_x = (dx / dist) * effective_speed
                move_y = (dy / dist) * effective_speed
            else:
                move_x, move_y = 0, 0
        
        self.vx = move_x 
        self.vy = move_y 
        
        is_moving = move_x != 0 or move_y != 0

        if is_moving:
            self.walk_anim_angle = math.sin(time.time() * 15) * 2
        else:
            self.walk_anim_angle = 0

        if is_moving and self.is_ambiently_noisy and self.sound_steps:
            current_time = pygame.time.get_ticks()
            if current_time > self.last_step_sound_time:
                game.sound_manager.play_sound(
                    self.sound_steps,
                    subdir='zombie', 
                    game=game,
                    source_pos=self.rect.center,
                    base_volume=random.uniform(0.02, 0.06)
                )

                if self.state == 'chasing':
                    next_delay = random.randint(280, 380)
                else:
                    next_delay = random.randint(420, 520)
                
                # Scale sound delay roughly
                self.last_step_sound_time = current_time + (next_delay / max(1, multiplier * 0.1))

        # [CHANGED] 3. Physics Sub-Stepping Loop to prevent tunneling
        # Determine number of steps needed. Safest is roughly half a tile size.
        safe_step_size = TILE_SIZE * 0.45
        total_dist_x = abs(move_x)
        total_dist_y = abs(move_y)
        
        steps = int(math.ceil(max(total_dist_x, total_dist_y) / safe_step_size))
        steps = max(1, steps)
        
        step_x = move_x / steps
        step_y = move_y / steps
        
        old_x, old_y = self.x, self.y

        for _ in range(steps):
            # --- Move X ---
            self.x += step_x
            self.rect.x = int(self.x)
            collided_x = False
            for obs in obstacles:
                if self.rect.colliderect(obs): collided_x = True; break
            if not collided_x:
                for z in other_zombies:
                    if z is not self and self.rect.colliderect(z.rect): collided_x = True; break

            if collided_x:
                self.x -= step_x # Revert step
                self.rect.x = int(self.x)
                if self.state == 'chasing':
                    self.stuck_timer = 20
                    self.stuck_angle = random.randint(0, 360)
            
            # --- Move Y ---
            self.y += step_y
            self.rect.y = int(self.y)
            collided_y = False
            for obs in obstacles:
                if self.rect.colliderect(obs): collided_y = True; break
            if not collided_y:
                for z in other_zombies:
                     if z is not self and self.rect.colliderect(z.rect): collided_y = True; break

            if collided_y:
                self.y -= step_y # Revert step
                self.rect.y = int(self.y)
                if self.state == 'chasing':
                    self.stuck_timer = 20
                    self.stuck_angle = random.randint(0, 360)
            
            # Optimization: If blocked on both axes, break loop (unlikely to unblock in same frame)
            if collided_x and collided_y:
                break

        self.rect.topleft = (int(self.x), int(self.y))