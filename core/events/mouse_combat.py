import math
import random
import time
import pygame
from core.data.config import *
from core.entities.item.item import Projectile
from core.update import player_hit_zombie, handle_zombie_death
from core.ui.inventory_modal import get_belt_hud_slot_rect
from core.messages import display_message

def handle_attack(game, mouse_pos):
    if any(modal['is_dragging'] for modal in game.modals):
        return

    click_in_modal = False
    for modal in reversed(game.modals):
        modal_rect = modal['rect']
        if modal_rect.collidepoint(mouse_pos):
            click_in_modal = True
            break
    
    if not click_in_modal:
        for i in range(5):
            if get_belt_hud_slot_rect(i).collidepoint(mouse_pos):
                click_in_modal = True
                break

    if click_in_modal:
        return

    if GAME_OFFSET_X <= mouse_pos[0] < GAME_OFFSET_X + GAME_WIDTH:
        weapon = game.player.active_weapon
        if game.player.is_reloading:
            print("Cannot shoot while reloading.")
            return

        if weapon and weapon.item_type == 'weapon_ranged' and weapon.ammo_type:
            firing_delay = getattr(weapon, 'firing_second', 0.0)
            if firing_delay > 0:
                if time.time() - game.player.last_shot_time < firing_delay:
                    return
            
            if weapon.load > 0 and weapon.durability > 0:
                game.player.last_shot_time = time.time()
                if 'shoot' in weapon.sounds and weapon.sounds['shoot']:
                    game.sound_manager.play_sound(
                        weapon.sounds['shoot'], 
                        subdir='items',
                        game=game,
                        source_pos=game.player.rect.center
                    )

                target_world_x, target_world_y = game.screen_to_world(mouse_pos)
                
                dx = target_world_x - game.player.rect.centerx
                dy = target_world_y - game.player.rect.centery
                base_angle = math.atan2(dy, dx)

                base_aim_inaccuracy = game.player.current_aim_factor * 25.0
                ranged_level = game.player.progression.get_ranged(game.player)
                skill_modifier = max(0.1, 1.0 - (ranged_level * 0.05))
                final_inaccuracy = base_aim_inaccuracy * skill_modifier
                total_spread_deg = weapon.spread_angle + final_inaccuracy

                distance_tiles = getattr(weapon, 'firing_distance', None)
                max_dist_pixels = None 
                
                calc_dist = 1000 
                
                if distance_tiles is not None:
                    max_dist_pixels = distance_tiles * TILE_SIZE
                    calc_dist = max_dist_pixels

                for _ in range(weapon.pellets):
                    spread = math.radians(random.uniform(-total_spread_deg / 2, total_spread_deg / 2))
                    angle = base_angle + spread
                    
                    target_x = game.player.rect.centerx + math.cos(angle) * calc_dist
                    target_y = game.player.rect.centery + math.sin(angle) * calc_dist

                    game.projectiles.append(Projectile(
                        game.player.rect.centerx, 
                        game.player.rect.centery, 
                        target_x, 
                        target_y,
                        max_distance=max_dist_pixels 
                    ))

                weapon.load -= 1

                dur_loss = game.player.progression.get_ranged_durability_loss(game.player)
                weapon.durability = max(0, weapon.durability - dur_loss)

                game.player.gun_flash_timer = 5
                if weapon.durability <= 0:
                    print(f"{weapon.name} broke!")
                    game.player.progression.add_xp(game.player, 'maintenance', 50)
                    game.player.active_weapon = None 
                    display_message(game, f"{weapon.name} is broken and unequipped.")
                    
            elif weapon.load <= 0: 
                if 'noammo' in weapon.sounds and weapon.sounds['noammo']:
                    game.sound_manager.play_sound(weapon.sounds['noammo'], subdir='items', game=game, source_pos=game.player.rect.center)
                print(f"**CLICK!** {weapon.name} is out of ammo.")
            else: print(f"**CLUNK!** {weapon.name} is broken.")

        else:
            # --- MELEE ATTACK LOGIC ---
            if game.player.progression.handle_melee_attack(game.player):
                if weapon and weapon.item_type in ['weapon_melee', 'tool'] and 'swing' in weapon.sounds and weapon.sounds['swing']:
                    game.sound_manager.play_sound(
                        weapon.sounds['swing'], 
                        subdir='items',
                        game=game,
                        source_pos=game.player.rect.center
                    )

                game.player.melee_swing_timer = 10
                player_screen_x = GAME_OFFSET_X + GAME_WIDTH / 2
                player_screen_y = GAME_HEIGHT / 2
                
                dx_swing = mouse_pos[0] - player_screen_x
                dy_swing = mouse_pos[1] - player_screen_y
                
                # Angle for Swing Animation (Inverted Y for Cartesian logic)
                game.player.melee_swing_angle = math.atan2(-dy_swing, dx_swing)
          
                hit_something = False
                world_pos = game.screen_to_world(mouse_pos)

                # Determine Attack Range
                attack_range = TILE_SIZE * 2.0 # Default melee reach
                if weapon and hasattr(weapon, 'reach'):
                     attack_range = weapon.reach * TILE_SIZE

                # --- ZOMBIE COLLISION ---
                for zombie in game.zombies:
                    # [FIX] Use Distance + Cone check instead of strict colliderect
                    dist = math.hypot(zombie.rect.centerx - game.player.rect.centerx, zombie.rect.centery - game.player.rect.centery)
                    
                    if dist <= attack_range:
                        # 1. Calculate angle to zombie (Inverted Y to match swing angle)
                        dx = zombie.rect.centerx - game.player.rect.centerx
                        dy_inv = game.player.rect.centery - zombie.rect.centery
                        z_angle = math.atan2(dy_inv, dx)
                        
                        angle_diff = abs(game.player.melee_swing_angle - z_angle)
                        if angle_diff > math.pi: angle_diff = 2 * math.pi - angle_diff
                        
                        # 2. Hit if clicked directly OR within cone
                        if zombie.rect.collidepoint(world_pos) or angle_diff < 1.0:
                            if player_hit_zombie(game.player, zombie, game):
                                handle_zombie_death(game, zombie, game.items_on_ground, game.obstacles, weapon)
                                game.zombies_killed += 1
                            
                            # [FIX] Apply Knockback to Zombie (Use Screen Coords)
                            dx_kb = zombie.rect.centerx - game.player.rect.centerx
                            dy_kb = zombie.rect.centery - game.player.rect.centery # Screen Y increases down
                            kb_angle = math.atan2(dy_kb, dx_kb)
                            
                            force = 7 # Knockback strength
                            zombie.knockback_velocity = [math.cos(kb_angle) * force, math.sin(kb_angle) * force]
                            zombie.knockback_timer = 200 # Duration

                            hit_something = True
                            break

                # --- NPC COLLISION ---
                if not hit_something: 
                    for npc in game.npcs:
                        if not npc.is_dead:
                            dist = math.hypot(game.player.rect.centerx - npc.rect.centerx, game.player.rect.centery - npc.rect.centery)
                            
                            if dist <= attack_range:
                                dx = npc.rect.centerx - game.player.rect.centerx
                                dy_inv = game.player.rect.centery - npc.rect.centery 
                                npc_angle = math.atan2(dy_inv, dx)
                                
                                angle_diff = abs(game.player.melee_swing_angle - npc_angle)
                                if angle_diff > math.pi: angle_diff = 2 * math.pi - angle_diff
                                
                                if npc.rect.collidepoint(world_pos) or angle_diff < 1.0:
                                    damage = game.player.get_attack_damage()
                                    npc.take_damage(damage, game, attacker=game.player)
                                    display_message(game, f"You attacked {npc.name} for {damage} damage!")
                                    
                                    # [FIX] Apply Knockback to NPC (Use Screen Coords)
                                    dx_kb = npc.rect.centerx - game.player.rect.centerx
                                    dy_kb = npc.rect.centery - game.player.rect.centery
                                    kb_angle = math.atan2(dy_kb, dx_kb)

                                    if dist > 0:
                                        force = 7
                                        npc.knockback_velocity = [math.cos(kb_angle) * force, math.sin(kb_angle) * force]
                                        npc.knockback_timer = 200

                                    hit_something = True
                                    break 

                # --- TILE/OBJECT COLLISION ---
                if not hit_something:
                     clicked_grid_x = int(world_pos[0] // TILE_SIZE)
                     clicked_grid_y = int(world_pos[1] // TILE_SIZE)
                     
                     target_found = False
                     
                     for offset_y in range(4): 
                         target_y = clicked_grid_y + offset_y
                         
                         tile_def = game.map_manager.get_tile_at(clicked_grid_x, target_y)
                         
                         if tile_def and tile_def.get('destructible'):
                             
                             tile_center_x = clicked_grid_x * TILE_SIZE + TILE_SIZE / 2
                             tile_center_y = target_y * TILE_SIZE + TILE_SIZE / 2
                             dist = math.hypot(game.player.rect.centerx - tile_center_x, game.player.rect.centery - tile_center_y)
                             
                             if dist <= TILE_SIZE * 2:
                                 if weapon is None:
                                     hand_part = game.player.body_parts.get('hand')
                                     if hand_part:
                                         if hand_part['value'] <= 10:
                                             display_message(game, "Your hands are too injured to hit this!")
                                             hit_something = True 
                                             break
                                         else:
                                             self_damage = random.randint(1, 2)
                                             game.player.take_damage_to_part('hand', self_damage)

                                 damage = game.player.get_attack_damage()
                                 result = game.map_manager.hit_tile(clicked_grid_x, target_y, damage, weapon=weapon)
                                 if result:
                                     hit_something = True
                                     target_found = True
                                     break 

                if not hit_something: print("Swung and missed!")